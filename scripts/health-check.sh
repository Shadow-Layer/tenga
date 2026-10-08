#!/bin/bash

# Tenga Inventory POS - Health Check and Verification Script
# Verifies all services are healthy and running
# Usage: ./scripts/health-check.sh [--env-file .env] [--watch]

set -euo pipefail

# Default values
ENV_FILE=".env"
WATCH_MODE=false
CHECK_INTERVAL=5
CONTINUOUS=false

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
    echo -e "${GREEN}[✓]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $*"
}

log_error() {
    echo -e "${RED}[✗]${NC} $*"
}

print_help() {
    cat << 'EOF'
Usage: ./scripts/health-check.sh [OPTIONS]

Options:
  --env-file FILE        Environment file to use (default: .env)
  --watch               Continuously monitor health (updates every 5s)
  --help                Show this help message

Examples:
  # Check health once
  ./scripts/health-check.sh

  # Continuously monitor health
  ./scripts/health-check.sh --watch

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        --watch)
            WATCH_MODE=true
            CONTINUOUS=true
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

# Load environment
export $(grep -v '^#' "$ENV_FILE" | grep -v '^$' | xargs)

# Verify Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    log_error "docker-compose not found"
    exit 1
fi

# Function to perform health checks
perform_checks() {
    local all_healthy=true
    
    echo -e "\n${BLUE}=== Health Check Report ===${NC}\n"
    
    # Check Docker services status
    log_info "Checking Docker services..."
    echo ""
    
    SERVICES=("postgres" "api" "frontend")
    for service in "${SERVICES[@]}"; do
        STATUS=$(docker-compose ps $service 2>/dev/null | tail -1 | awk '{print $NF}' || echo "unknown")
        if [[ "$STATUS" == "Up"* ]]; then
            log_success "$service: Running"
        else
            log_error "$service: Not running ($STATUS)"
            all_healthy=false
        fi
    done
    
    echo ""
    
    # Check PostgreSQL health
    if docker-compose ps postgres | grep -q "Up"; then
        log_info "Checking PostgreSQL connectivity..."
        if docker-compose exec -T postgres pg_isready -U "${POSTGRES_USER:-tenga_user}" 2>/dev/null >/dev/null; then
            log_success "PostgreSQL: Connected"
        else
            log_error "PostgreSQL: Not accessible"
            all_healthy=false
        fi
    else
        log_warning "PostgreSQL: Container not running"
        all_healthy=false
    fi
    
    # Check API health
    if docker-compose ps api | grep -q "Up"; then
        log_info "Checking API health endpoint..."
        if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
            log_success "API: Healthy"
        else
            log_warning "API: Health check failed (may still be starting)"
        fi
        
        # Check API readiness
        if curl -sf http://localhost:8000/ready >/dev/null 2>&1; then
            log_success "API: Ready"
        else
            log_warning "API: Not ready yet (database may not be initialized)"
        fi
    else
        log_warning "API: Container not running"
        all_healthy=false
    fi
    
    # Check Frontend health
    if docker-compose ps frontend | grep -q "Up"; then
        log_info "Checking Frontend health..."
        if curl -sf http://localhost/health >/dev/null 2>&1; then
            log_success "Frontend: Healthy"
        else
            log_warning "Frontend: Health check failed"
        fi
    else
        log_warning "Frontend: Container not running"
        all_healthy=false
    fi
    
    echo ""
    
    # Check disk usage
    log_info "Checking disk space..."
    DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [[ $DISK_USAGE -lt 80 ]]; then
        log_success "Disk usage: ${DISK_USAGE}%"
    else
        log_warning "Disk usage: ${DISK_USAGE}% (getting full)"
    fi
    
    echo ""
    log_info "Docker Compose status:"
    docker-compose ps
    
    echo ""
    
    if [[ "$all_healthy" == "true" ]]; then
        log_success "All services are healthy!"
        return 0
    else
        log_warning "Some services may not be healthy. Check logs with: docker-compose logs"
        return 1
    fi
}

# Main loop
if [[ "$CONTINUOUS" == "true" ]]; then
    log_info "Health check mode: CONTINUOUS (updates every ${CHECK_INTERVAL}s, Ctrl+C to exit)"
    while true; do
        clear
        perform_checks || true
        sleep "$CHECK_INTERVAL"
    done
else
    perform_checks
    exit $?
fi
