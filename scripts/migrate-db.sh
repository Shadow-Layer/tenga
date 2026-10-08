#!/bin/bash

# Tenga Inventory POS - Database Migration Script
# Runs database migrations using Alembic
# Usage: ./scripts/migrate-db.sh [--env-file .env] [--rollback REVISION]

set -euo pipefail

# Default values
ENV_FILE=".env"
ROLLBACK_REVISION=""
DRY_RUN=false

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

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

print_help() {
    cat << 'EOF'
Usage: ./scripts/migrate-db.sh [OPTIONS]

Options:
  --env-file FILE         Environment file to use (default: .env)
  --rollback REVISION     Rollback to specific revision
  --dry-run              Show what would be migrated without applying
  --help                 Show this help message

Examples:
  # Run all pending migrations
  ./scripts/migrate-db.sh

  # Run migrations with specific env file
  ./scripts/migrate-db.sh --env-file .env.production

  # Rollback to previous revision
  ./scripts/migrate-db.sh --rollback -1

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        --rollback)
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

# Validate environment file
if [[ ! -f "$ENV_FILE" ]]; then
    log_error "Environment file not found: $ENV_FILE"
    exit 1
fi

log_info "Using environment file: $ENV_FILE"

# Load environment
export $(grep -v '^#' "$ENV_FILE" | grep -v '^$' | xargs)

# Verify Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    log_error "docker-compose not found"
    exit 1
fi

# Check if containers are running
log_info "Checking if services are running..."
if ! docker-compose ps | grep -q "Up"; then
    log_error "Services are not running. Start them with: docker-compose --env-file $ENV_FILE up -d"
    exit 1
fi

# Wait for database to be ready
log_info "Waiting for database to be ready..."
MAX_ATTEMPTS=30
ATTEMPT=0
while [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; do
    if docker-compose exec -T postgres pg_isready -U "$POSTGRES_USER" 2>/dev/null; then
        log_success "Database is ready"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    sleep 1
done

if [[ $ATTEMPT -eq $MAX_ATTEMPTS ]]; then
    log_error "Database did not become ready in time"
    exit 1
fi

# Run migrations
log_info "Running database migrations..."

if [[ -n "$ROLLBACK_REVISION" ]]; then
    log_info "Rolling back to revision: $ROLLBACK_REVISION"
    docker-compose exec -T api alembic downgrade "$ROLLBACK_REVISION"
else
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Dry run - showing SQL that would be executed"
        docker-compose exec -T api alembic upgrade --sql head
    else
        if docker-compose exec -T api python -c "from src.database.config import init_db; init_db()" 2>&1 | tee migration.log; then
            log_success "Database initialization complete"
        else
            log_error "Database initialization failed. See migration.log for details."
            exit 1
        fi
    fi
fi

log_info ""
log_success "Migration process complete"
log_info ""
