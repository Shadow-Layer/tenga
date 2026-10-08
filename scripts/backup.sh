#!/bin/bash

# Tenga Inventory POS - Backup and Restore Script
# Manages PostgreSQL backups and restore operations
# Usage: ./scripts/backup.sh [--backup|--restore|--list|--prune]

set -euo pipefail

# Default values
OPERATION="backup"
BACKUP_DIR="backups"
BACKUP_RETENTION_DAYS=30
ENV_FILE=".env"
RESTORE_FILE=""

# Color codes
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
    echo -e "${RED}[ERROR]${NC} $*"
}

print_help() {
    cat << 'EOF'
Usage: ./scripts/backup.sh [OPERATION] [OPTIONS]

Operations:
  --backup              Create a new database backup (default)
  --restore FILE        Restore from a backup file
  --list               List all available backups
  --prune              Remove backups older than retention period
  --help               Show this help message

Options:
  --backup-dir DIR      Backup directory (default: backups)
  --retention DAYS      Backup retention in days (default: 30)
  --env-file FILE       Environment file (default: .env)

Examples:
  # Create a backup
  ./scripts/backup.sh --backup

  # List all backups
  ./scripts/backup.sh --list

  # Restore from specific backup
  ./scripts/backup.sh --restore backups/tenga_20240101_120000.sql

  # Prune old backups
  ./scripts/backup.sh --prune

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --backup)
            OPERATION="backup"
            shift
            ;;
        --restore)
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
            BACKUP_DIR="$2"
            shift 2
            ;;
        --retention)
            BACKUP_RETENTION_DAYS="$2"
            shift 2
            ;;
        --env-file)
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

# Validate environment file
if [[ ! -f "$ENV_FILE" ]]; then
    log_error "Environment file not found: $ENV_FILE"
    exit 1
fi

# Load environment
export $(grep -v '^#' "$ENV_FILE" | grep -v '^$' | xargs)

# Verify Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    log_error "docker-compose not found"
    exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Perform operation
case "$OPERATION" in
    backup)
        log_info "Creating database backup..."
        
        # Check if postgres container is running
        if ! docker-compose ps postgres | grep -q "Up"; then
            log_error "PostgreSQL container is not running"
            exit 1
        fi
        
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        BACKUP_FILE="$BACKUP_DIR/tenga_${TIMESTAMP}.sql"
        
        log_info "Backup file: $BACKUP_FILE"
        
        # Create backup using pg_dump
        if docker-compose exec -T postgres pg_dump \
            -U "${POSTGRES_USER:-tenga_user}" \
            -h localhost \
            "${POSTGRES_DB:-tenga}" > "$BACKUP_FILE" 2>/dev/null; then
            
            # Compress backup
            gzip "$BACKUP_FILE"
            BACKUP_FILE="${BACKUP_FILE}.gz"
            
            BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
            log_success "Backup created successfully: $BACKUP_FILE ($BACKUP_SIZE)"
            
            # Display backup info
            ls -lh "$BACKUP_FILE"
        else
            log_error "Backup failed"
            rm -f "$BACKUP_FILE"
            exit 1
        fi
        ;;
        
    restore)
        if [[ -z "$RESTORE_FILE" ]]; then
            log_error "No restore file specified"
            print_help
            exit 1
        fi
        
        if [[ ! -f "$RESTORE_FILE" ]]; then
            log_error "Restore file not found: $RESTORE_FILE"
            exit 1
        fi
        
        log_warning "This will overwrite the current database. Are you sure? (type 'yes' to confirm)"
        read -r CONFIRM
        if [[ "$CONFIRM" != "yes" ]]; then
            log_info "Restore cancelled"
            exit 0
        fi
        
        log_info "Restoring database from: $RESTORE_FILE"
        
        # Check if postgres container is running
        if ! docker-compose ps postgres | grep -q "Up"; then
            log_error "PostgreSQL container is not running"
            exit 1
        fi
        
        # Determine if file is compressed
        if [[ "$RESTORE_FILE" == *.gz ]]; then
            gunzip -c "$RESTORE_FILE" | docker-compose exec -T postgres psql \
                -U "${POSTGRES_USER:-tenga_user}" \
                "${POSTGRES_DB:-tenga}" 2>/dev/null
        else
            docker-compose exec -T postgres psql \
                -U "${POSTGRES_USER:-tenga_user}" \
                "${POSTGRES_DB:-tenga}" < "$RESTORE_FILE" 2>/dev/null
        fi
        
        if [[ $? -eq 0 ]]; then
            log_success "Database restored successfully from: $RESTORE_FILE"
        else
            log_error "Database restore failed"
            exit 1
        fi
        ;;
        
    list)
        log_info "Available backups:"
        echo ""
        if ls "$BACKUP_DIR"/*.sql* 1> /dev/null 2>&1; then
            ls -lh "$BACKUP_DIR"/*.sql* | awk '{print $9, "(" $5 ")"}'
        else
            log_warning "No backups found in $BACKUP_DIR"
        fi
        ;;
        
    prune)
        log_info "Pruning backups older than $BACKUP_RETENTION_DAYS days..."
        
        PRUNED=0
        while IFS= read -r file; do
            rm -f "$file"
            log_info "Pruned: $file"
            ((PRUNED++))
        done < <(find "$BACKUP_DIR" -name "*.sql*" -mtime "+$BACKUP_RETENTION_DAYS" 2>/dev/null)
        
        if [[ $PRUNED -gt 0 ]]; then
            log_success "Pruned $PRUNED backup(s)"
        else
            log_info "No backups to prune"
        fi
        ;;
        
    *)
        log_error "Unknown operation: $OPERATION"
        print_help
        exit 1
        ;;
esac
