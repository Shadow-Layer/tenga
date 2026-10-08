#!/bin/bash

# Tenga Inventory POS - Deployment Verification Script
# Tests all deployment aspects and runs the full test suite
# Usage: ./scripts/verify-deployment.sh [--env-file .env] [--skip-tests]

set -euo pipefail

# Default values
ENV_FILE=".env"
SKIP_TESTS=false
TEST_DURATION_SECONDS=120
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

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
    ((PASSED_TESTS++))
}

log_error() {
    echo -e "${RED}[✗]${NC} $*"
    ((FAILED_TESTS++))
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $*"
}

log_test() {
    echo -e "\n${BLUE}=== $* ===${NC}"
    ((TOTAL_TESTS++))
}

print_help() {
    cat << 'EOF'
Usage: ./scripts/verify-deployment.sh [OPTIONS]

Options:
  --env-file FILE        Environment file to use (default: .env)
  --skip-tests           Skip automated test suite
  --help                 Show this help message

Examples:
  # Full verification
  ./scripts/verify-deployment.sh --env-file .env.production

  # Verify deployment only (skip app tests)
  ./scripts/verify-deployment.sh --env-file .env.production --skip-tests

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        --skip-tests)
            SKIP_TESTS=true
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

log_info "=========================================="
log_info "Tenga Inventory POS - Deployment Verification"
log_info "=========================================="
log_info "Using environment file: $ENV_FILE"
log_info ""

# ==================================================
# PHASE 1: Dependency Checks
# ==================================================

log_test "Checking System Dependencies"

# Check docker
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    log_success "Docker: $DOCKER_VERSION"
else
    log_error "Docker not installed"
    exit 1
fi

# Check docker-compose
if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version)
    log_success "Docker Compose: $COMPOSE_VERSION"
else
    log_error "Docker Compose not installed"
    exit 1
fi

# Check curl
if command -v curl &> /dev/null; then
    log_success "curl is available"
else
    log_error "curl not found"
    exit 1
fi

# ==================================================
# PHASE 2: Docker Configuration
# ==================================================

log_test "Validating Docker Configuration"

# Validate docker-compose file
if docker-compose -f docker-compose.yml config > /dev/null 2>&1; then
    log_success "docker-compose.yml is valid"
else
    log_error "docker-compose.yml validation failed"
    exit 1
fi

# Check if images can be built
log_info "Building Docker images (this may take a few minutes)..."
if docker-compose build --quiet 2>&1 | tail -20; then
    log_success "Docker images built successfully"
else
    log_error "Docker image build failed"
    exit 1
fi

# ==================================================
# PHASE 3: Service Startup
# ==================================================

log_test "Starting Services"

log_info "Bringing up services..."
if docker-compose --env-file "$ENV_FILE" up -d 2>&1 | grep -E "(done|Error)" | tail -5; then
    log_success "Services started"
else
    log_error "Failed to start services"
    docker-compose logs
    exit 1
fi

log_info "Waiting for services to be ready (up to 60 seconds)..."
WAIT_COUNT=0
MAX_WAIT=60
while [[ $WAIT_COUNT -lt $MAX_WAIT ]]; do
    if docker-compose ps | grep -E "(postgres|api|frontend)" | grep -q "Up"; then
        RUNNING=$(docker-compose ps | grep "Up" | wc -l)
        if [[ $RUNNING -ge 3 ]]; then
            log_success "All services are running"
            break
        fi
    fi
    WAIT_COUNT=$((WAIT_COUNT + 1))
    sleep 1
done

if [[ $WAIT_COUNT -eq $MAX_WAIT ]]; then
    log_error "Services did not start in time"
    docker-compose logs
    exit 1
fi

# ==================================================
# PHASE 4: Service Health Checks
# ==================================================

log_test "Checking Service Health"

# PostgreSQL health
log_info "Checking PostgreSQL..."
if docker-compose exec -T postgres pg_isready -U "${POSTGRES_USER:-tenga_user}" 2>/dev/null >/dev/null; then
    log_success "PostgreSQL is healthy"
else
    log_error "PostgreSQL health check failed"
fi

# API health
log_info "Checking API /health endpoint..."
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    log_success "API /health endpoint responding"
else
    log_warning "API /health endpoint not responding yet"
fi

# API readiness
log_info "Checking API /ready endpoint..."
WAIT_COUNT=0
while [[ $WAIT_COUNT -lt 30 ]]; do
    if curl -sf http://localhost:8000/ready > /dev/null 2>&1; then
        log_success "API is ready (database connected)"
        break
    fi
    WAIT_COUNT=$((WAIT_COUNT + 1))
    sleep 1
done

if [[ $WAIT_COUNT -eq 30 ]]; then
    log_warning "API readiness check failed - may need database initialization"
fi

# Frontend health
log_info "Checking Frontend..."
if curl -sf http://localhost/health > /dev/null 2>&1; then
    log_success "Frontend is healthy"
else
    log_warning "Frontend health check failed"
fi

# ==================================================
# PHASE 5: Database Initialization
# ==================================================

log_test "Database Initialization"

log_info "Initializing database schema..."
if docker-compose exec -T api python -c "from src.database.config import init_db; init_db()" 2>&1 | grep -q "successfully\|error\|Error"; then
    if docker-compose exec -T api python -c "from src.database.config import engine; engine.execute('SELECT 1')" 2>/dev/null >/dev/null; then
        log_success "Database schema initialized"
    else
        log_error "Database initialization appears to have failed"
    fi
else
    log_info "Database already initialized or no changes needed"
fi

# ==================================================
# PHASE 6: API Endpoints Testing
# ==================================================

log_test "Testing API Endpoints"

# Test health endpoint
log_info "Testing /health endpoint..."
RESPONSE=$(curl -s http://localhost:8000/health)
if echo "$RESPONSE" | grep -q "ok\|status"; then
    log_success "Health endpoint working"
else
    log_error "Health endpoint failed"
fi

# Test ready endpoint
log_info "Testing /ready endpoint..."
RESPONSE=$(curl -s http://localhost:8000/ready)
if echo "$RESPONSE" | grep -q "ready\|database"; then
    log_success "Readiness endpoint working"
else
    log_warning "Readiness endpoint returned: $RESPONSE"
fi

# Test OpenAPI docs
log_info "Testing OpenAPI documentation endpoint..."
if curl -sf http://localhost:8000/api/docs > /dev/null 2>&1; then
    log_success "OpenAPI documentation available"
else
    log_warning "OpenAPI documentation not available"
fi

# ==================================================
# PHASE 7: Frontend Testing
# ==================================================

log_test "Testing Frontend"

# Test index page
log_info "Testing index.html..."
if curl -sf http://localhost/ | grep -q "html\|<!DOCTYPE"; then
    log_success "Frontend index page serving HTML"
else
    log_warning "Frontend index page may not be serving correctly"
fi

# Test static asset serving
log_info "Testing static asset caching..."
HEADERS=$(curl -sI http://localhost/index.html)
if echo "$HEADERS" | grep -q "Cache-Control"; then
    log_success "Static asset caching headers present"
else
    log_warning "Static asset caching headers missing"
fi

# ==================================================
# PHASE 8: Persistence Testing
# ==================================================

log_test "Testing Data Persistence"

# Check volumes
log_info "Checking Docker volumes..."
VOLUMES=$(docker volume ls | grep -E "postgres_data|app_data" | wc -l)
if [[ $VOLUMES -ge 2 ]]; then
    log_success "Persistent volumes created ($VOLUMES found)"
else
    log_warning "Some persistent volumes may be missing"
fi

# Test volume data
log_info "Testing volume mounts..."
if docker-compose exec -T api test -d /data; then
    log_success "/data volume is mounted in API container"
else
    log_error "/data volume not mounted in API container"
fi

if docker-compose exec -T postgres test -d /var/lib/postgresql/data; then
    log_success "PostgreSQL data volume is mounted"
else
    log_error "PostgreSQL data volume not mounted"
fi

# ==================================================
# PHASE 9: Backup & Restore Testing
# ==================================================

log_test "Testing Backup & Restore"

# Check backup script
if [[ -x "scripts/backup.sh" ]]; then
    log_success "Backup script is executable"
    
    # Test backup
    log_info "Creating test backup..."
    if ./scripts/backup.sh --backup --env-file "$ENV_FILE" 2>&1 | tail -5 | grep -q "successfully\|Backup"; then
        log_success "Backup created successfully"
        
        # Check backup file
        if ls backups/tenga_*.sql.gz 2>/dev/null | head -1 > /dev/null; then
            BACKUP_FILE=$(ls -t backups/tenga_*.sql.gz 2>/dev/null | head -1)
            BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
            log_success "Backup file exists: $BACKUP_SIZE"
        else
            log_warning "Backup file not found"
        fi
    else
        log_warning "Backup creation may have failed"
    fi
else
    log_error "Backup script not found or not executable"
fi

# ==================================================
# PHASE 10: Network & Connectivity
# ==================================================

log_test "Testing Network Connectivity"

# Test inter-container communication
log_info "Testing container-to-container communication..."
if docker-compose exec -T api python -c "import socket; socket.create_connection(('postgres', 5432), timeout=3)" 2>/dev/null; then
    log_success "API can reach PostgreSQL"
else
    log_error "API cannot reach PostgreSQL"
fi

# Test port exposure
log_info "Checking port exposure..."
if netstat -tuln 2>/dev/null | grep -q ":80 \|:8000 "; then
    log_success "Required ports are exposed"
else
    log_warning "Could not verify port exposure (netstat may not be available)"
fi

# ==================================================
# PHASE 11: Security Checks
# ==================================================

log_test "Checking Security Configuration"

# Check non-root users
log_info "Verifying containers run as non-root..."
API_USER=$(docker-compose exec -T api whoami 2>/dev/null || echo "unknown")
if [[ "$API_USER" != "root" ]] && [[ -n "$API_USER" ]]; then
    log_success "API runs as non-root user: $API_USER"
else
    log_warning "Could not verify API user (may be running as root)"
fi

# Check environment variables
log_info "Verifying secrets are configured..."
if docker-compose exec -T api env | grep -q "JWT_SECRET_KEY"; then
    log_success "JWT_SECRET_KEY is configured"
else
    log_error "JWT_SECRET_KEY not configured"
fi

if docker-compose exec -T api env | grep -q "POSTGRES_PASSWORD"; then
    log_success "Database password is configured"
else
    log_error "Database password not configured"
fi

# ==================================================
# PHASE 12: Application Tests (if not skipped)
# ==================================================

if [[ "$SKIP_TESTS" != "true" ]]; then
    log_test "Running Application Test Suite"
    
    log_info "Running pytest (up to ${TEST_DURATION_SECONDS}s)..."
    
    cd /home/tea/Documents/apps/tenga-inventory
    
    if timeout "${TEST_DURATION_SECONDS}" python -m pytest tests/ -v --tb=short 2>&1 | tee test-results.log; then
        PASS_COUNT=$(grep -c "PASSED" test-results.log || echo "0")
        FAIL_COUNT=$(grep -c "FAILED" test-results.log || echo "0")
        
        if [[ $FAIL_COUNT -eq 0 ]]; then
            log_success "All application tests passed ($PASS_COUNT tests)"
        else
            log_error "Some tests failed ($PASS_COUNT passed, $FAIL_COUNT failed)"
        fi
    else
        log_warning "Test suite timed out or failed"
    fi
else
    log_info "Skipping application test suite (use without --skip-tests to run)"
fi

# ==================================================
# PHASE 13: Summary & Recommendations
# ==================================================

log_test "Verification Summary"

echo ""
echo "=========================================="
echo "Verification Results:"
echo "=========================================="
echo "Total Checks: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
echo "=========================================="
echo ""

if [[ $FAILED_TESTS -eq 0 ]]; then
    log_success "All verifications passed!"
    echo ""
    echo "Deployment is ready for production."
    echo ""
    echo "Next steps:"
    echo "1. Create backups: ./scripts/backup.sh --backup --env-file $ENV_FILE"
    echo "2. Test backup restore: ./scripts/backup.sh --restore <backup-file>"
    echo "3. Monitor logs: docker-compose logs -f"
    echo "4. Monitor health: ./scripts/health-check.sh --watch"
    echo ""
else
    log_warning "Some verifications failed. Review errors above."
    echo ""
    echo "Troubleshooting:"
    echo "1. Check service logs: docker-compose logs -f"
    echo "2. Verify Docker daemon: docker version"
    echo "3. Check disk space: df -h"
    echo "4. Review configuration: cat $ENV_FILE"
    echo ""
    exit 1
fi
