#!/usr/bin/env bash

# Tenga Inventory POS - Database Migration Script
# Usage: ./scripts/migrate-db.sh [--env-file .env] [--rollback REVISION] [--dry-run]

set -euo pipefail

ENV_FILE=".env"
ROLLBACK_REVISION=""
DRY_RUN=false

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

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

print_help() {
    cat <<'EOF'
Usage: ./scripts/migrate-db.sh [OPTIONS]

Options:
  --env-file FILE         Compose environment file (default: .env)
  --rollback REVISION     Preview a downgrade (applying downgrades is disabled)
  --dry-run               Show migration SQL without applying it
  --help                  Show this help message
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
        --env-file)
            require_value "$@"
            ENV_FILE="$2"
            shift 2
            ;;
        --rollback)
            require_value "$@"
            ROLLBACK_REVISION="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
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

log_info "Using environment file: $ENV_FILE"
log_info "Checking that the API and PostgreSQL services are running..."
if ! service_is_running api; then
    log_error "API service is not running. Start it with: docker compose --env-file \"$ENV_FILE\" up -d"
    exit 1
fi
if ! service_is_running postgres; then
    log_error "PostgreSQL service is not running. Start it with: docker compose --env-file \"$ENV_FILE\" up -d"
    exit 1
fi

log_info "Waiting for PostgreSQL to be ready..."
MAX_ATTEMPTS=30
ATTEMPT=0
while [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; do
    if compose exec -T postgres sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
        log_success "Database is ready"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    sleep 1
done

if [[ $ATTEMPT -eq $MAX_ATTEMPTS ]]; then
    log_error "Database did not become ready after $MAX_ATTEMPTS seconds"
    exit 1
fi

if [[ -n "$ROLLBACK_REVISION" ]]; then
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Dry run: generating downgrade SQL to revision $ROLLBACK_REVISION (no changes will be applied)"
        if ! compose exec -T api alembic downgrade --sql "head:$ROLLBACK_REVISION"; then
            log_error "Could not generate downgrade SQL for revision: $ROLLBACK_REVISION"
            exit 1
        fi
    else
        log_error "Database downgrades are disabled to preserve live history; restore a verified backup instead"
        exit 1
    fi
elif [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry run: generating upgrade SQL (no changes will be applied)"
    if ! compose exec -T api alembic upgrade --sql head; then
        log_error "Could not generate migration SQL"
        exit 1
    fi
else
    log_info "Applying pending Alembic migrations..."
    if ! compose exec -T api alembic upgrade head; then
        log_error "Database migration failed"
        exit 1
    fi
    log_success "Database migrations applied"
fi

log_success "Migration process complete"
