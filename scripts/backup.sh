#!/usr/bin/env bash

# Tenga Inventory POS - Backup and Restore Script
# Usage: ./scripts/backup.sh [--backup|--restore FILE|--list|--prune]

set -euo pipefail

OPERATION="backup"
BACKUP_DIR="backups"
BACKUP_RETENTION_DAYS=30
ENV_FILE=".env"
RESTORE_FILE=""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

print_help() {
    cat <<'EOF'
Usage: ./scripts/backup.sh [OPERATION] [OPTIONS]

Operations:
  --backup              Create a database backup (default)
  --restore FILE        Restore a backup file
  --list                List available backups
  --prune               Remove backups older than the retention period
  --help                Show this help message

Options:
  --backup-dir DIR      Backup directory (default: backups)
  --retention DAYS      Backup retention in days (default: 30)
  --env-file FILE       Compose environment file (default: .env)
EOF
}

require_value() {
    if [[ $# -lt 2 ]]; then
        log_error "Missing value for $1"
        print_help
        exit 1
    fi
    if [[ -z "$2" ]]; then
        log_error "Missing value for $1"
        print_help
        exit 1
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --backup)
            OPERATION="backup"
            shift
            ;;
        --restore)
            require_value "$@"
            OPERATION="restore"
            RESTORE_FILE="$2"
            shift 2
            ;;
        --list)
            OPERATION="list"
            shift
            ;;
        --prune)
            OPERATION="prune"
            shift
            ;;
        --backup-dir)
            require_value "$@"
            BACKUP_DIR="$2"
            shift 2
            ;;
        --retention)
            require_value "$@"
            BACKUP_RETENTION_DAYS="$2"
            shift 2
            ;;
        --env-file)
            require_value "$@"
            ENV_FILE="$2"
            shift 2
            ;;
        --help)
            print_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            print_help
            exit 1
            ;;
    esac
done

if [[ ! "$BACKUP_RETENTION_DAYS" =~ ^[0-9]+$ ]]; then
    log_error "Retention must be a non-negative number of days"
    exit 1
fi

if [[ "$OPERATION" == "list" ]]; then
    log_info "Available backups:"
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_warning "No backups found in $BACKUP_DIR"
        exit 0
    fi
    shopt -s nullglob
    BACKUP_FILES=("$BACKUP_DIR"/*.sql "$BACKUP_DIR"/*.sql.gz)
    if [[ ${#BACKUP_FILES[@]} -eq 0 ]]; then
        log_warning "No backups found in $BACKUP_DIR"
    else
        for file in "${BACKUP_FILES[@]}"; do
            ls -lh -- "$file" | awk '{print $9, "(" $5 ")"}'
        done
    fi
    exit 0
fi

if [[ "$OPERATION" == "prune" ]]; then
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_info "No backups to prune"
        exit 0
    fi
    log_info "Pruning backups older than $BACKUP_RETENTION_DAYS days..."
    PRUNED=0
    while IFS= read -r -d '' file; do
        rm -f -- "$file"
        log_info "Pruned: $file"
        PRUNED=$((PRUNED + 1))
    done < <(find "$BACKUP_DIR" -type f \( -name "*.sql" -o -name "*.sql.gz" \) -mtime "+$BACKUP_RETENTION_DAYS" -print0)

    if [[ $PRUNED -gt 0 ]]; then
        log_success "Pruned $PRUNED backup(s)"
    else
        log_info "No backups to prune"
    fi
    exit 0
fi

if [[ ! -f "$ENV_FILE" ]]; then
    log_error "Environment file not found: $ENV_FILE"
    exit 1
fi

# Prefer the supported Compose v2 plugin; retain Compose v1 for older hosts.
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    COMPOSE=(docker compose --env-file "$ENV_FILE")
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose --env-file "$ENV_FILE")
else
    log_error "Docker Compose v2 or docker-compose v1 is required"
    exit 1
fi

compose() {
    "${COMPOSE[@]}" "$@"
}

if ! compose config --quiet; then
    log_error "Invalid Docker Compose configuration; verify required environment values in $ENV_FILE"
    exit 1
fi

service_is_running() {
    local service="$1"
    local container_id
    local running
    local found=false
    local container_ids

    if ! container_ids="$(compose ps -q "$service")"; then
        return 1
    fi
    while IFS= read -r container_id; do
        [[ -n "$container_id" ]] || continue
        running="$(docker inspect --format '{{.State.Running}}' "$container_id" 2>/dev/null || true)"
        if [[ "$running" == "true" ]]; then
            found=true
            break
        fi
    done <<<"$container_ids"
    [[ "$found" == "true" ]]
}

if ! service_is_running postgres; then
    log_error "PostgreSQL service is not running. Start it with: docker compose --env-file \"$ENV_FILE\" up -d"
    exit 1
fi

case "$OPERATION" in
    backup)
        mkdir -p "$BACKUP_DIR"
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        BACKUP_FILE="$BACKUP_DIR/tenga_${TIMESTAMP}.sql"
        log_info "Creating database backup: $BACKUP_FILE"

        if ! compose exec -T postgres sh -c 'pg_dump --clean --if-exists -U "$POSTGRES_USER" "$POSTGRES_DB"' >"$BACKUP_FILE"; then
            log_error "Backup failed; removing incomplete file"
            rm -f -- "$BACKUP_FILE"
            exit 1
        fi
        if ! gzip -- "$BACKUP_FILE"; then
            log_error "Could not compress backup: $BACKUP_FILE"
            rm -f -- "$BACKUP_FILE"
            exit 1
        fi

        BACKUP_FILE="${BACKUP_FILE}.gz"
        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        log_success "Backup created successfully: $BACKUP_FILE ($BACKUP_SIZE)"
        ls -lh -- "$BACKUP_FILE"
        ;;

    restore)
        if [[ ! -f "$RESTORE_FILE" ]]; then
            log_error "Restore file not found: $RESTORE_FILE"
            exit 1
        fi

        log_warning "This will overwrite the current database. Are you sure? (type 'yes' to confirm)"
        if ! read -r CONFIRM || [[ "$CONFIRM" != "yes" ]]; then
            log_info "Restore cancelled"
            exit 0
        fi

        log_info "Restoring database from: $RESTORE_FILE"
        if [[ "$RESTORE_FILE" == *.gz ]]; then
            if ! gzip -dc -- "$RESTORE_FILE" | compose exec -T postgres sh -c 'psql --single-transaction -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" "$POSTGRES_DB"'; then
                log_error "Database restore failed; PostgreSQL reported an error"
                exit 1
            fi
        else
            if ! compose exec -T postgres sh -c 'psql --single-transaction -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" "$POSTGRES_DB"' <"$RESTORE_FILE"; then
                log_error "Database restore failed; PostgreSQL reported an error"
                exit 1
            fi
        fi
        log_success "Database restored successfully from: $RESTORE_FILE"
        ;;

    *)
        log_error "Unknown operation: $OPERATION"
        print_help
        exit 1
        ;;
esac
