#!/bin/bash

# Tenga Inventory POS - Deployment Initialization Script
# This script initializes a fresh deployment on an OCI VM
# Usage: ./scripts/deploy-init.sh [--client-id CLIENT_ID] [--env prod|dev] [--help]

set -euo pipefail

# Default values
ENVIRONMENT="prod"
CLIENT_ID="default"
SKIP_VALIDATION=false
INTERACTIVE=true

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
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
Usage: ./scripts/deploy-init.sh [OPTIONS]

Options:
  --client-id ID          Client/Organization identifier (default: default)
  --env ENVIRONMENT       Deployment environment: dev, test, prod (default: prod)
  --skip-validation       Skip validation checks
  --non-interactive       Run without prompts
  --help                  Show this help message

Environment Variables:
  Set these before running for non-interactive deployment:
  - POSTGRES_PASSWORD      PostgreSQL password (required in prod)
  - JWT_SECRET_KEY         JWT secret key (required, generate with: openssl rand -hex 32)
  - ORGANIZATION_NAME      Organization display name

Examples:
  # Interactive production deployment
  ./scripts/deploy-init.sh --env prod --client-id acme-corp

  # Non-interactive deployment
  POSTGRES_PASSWORD=secure_password JWT_SECRET_KEY=$(openssl rand -hex 32) \
    ./scripts/deploy-init.sh --env prod --non-interactive

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --client-id)
            CLIENT_ID="$2"
            shift 2
            ;;
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --skip-validation)
            SKIP_VALIDATION=true
            shift
            ;;
        --non-interactive)
            INTERACTIVE=false
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

log_info "=========================================="
log_info "Tenga Inventory POS - Deployment Init"
log_info "=========================================="
log_info "Environment: $ENVIRONMENT"
log_info "Client ID: $CLIENT_ID"

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|test|prod)$ ]]; then
    log_error "Invalid environment: $ENVIRONMENT"
    exit 1
fi

# Check Docker and Docker Compose
log_info "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

DOCKER_VERSION=$(docker --version)
COMPOSE_VERSION=$(docker-compose --version)
log_success "Docker found: $DOCKER_VERSION"
log_success "Docker Compose found: $COMPOSE_VERSION"

# Check disk space
log_info "Checking available disk space..."
AVAILABLE_SPACE=$(df -B1 / | tail -1 | awk '{print $4}')
REQUIRED_SPACE=$((10 * 1024 * 1024 * 1024))  # 10GB minimum
if [[ $AVAILABLE_SPACE -lt $REQUIRED_SPACE ]]; then
    log_error "Insufficient disk space. Required: 10GB, Available: $((AVAILABLE_SPACE / 1024 / 1024 / 1024))GB"
    exit 1
fi
log_success "Sufficient disk space available"

# Create environment file
log_info "Setting up environment configuration..."

ENV_FILE=".env.deployment.${CLIENT_ID}"

if [[ -f "$ENV_FILE" ]]; then
    if [[ "$INTERACTIVE" == "true" ]]; then
        log_warning ".env file already exists: $ENV_FILE"
        read -p "Overwrite? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Using existing environment file"
            exit 0
        fi
    fi
fi

# Prompt for or generate secrets if interactive
if [[ "$INTERACTIVE" == "true" ]]; then
    if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
        log_warning "PostgreSQL password not set"
        read -sp "Enter PostgreSQL password (min 16 chars): " POSTGRES_PASSWORD
        echo
        if [[ ${#POSTGRES_PASSWORD} -lt 16 ]]; then
            log_error "Password too short (minimum 16 characters)"
            exit 1
        fi
    fi
    
    if [[ -z "${JWT_SECRET_KEY:-}" ]]; then
        log_warning "JWT secret key not set"
        log_info "Generating secure JWT secret key..."
        JWT_SECRET_KEY=$(openssl rand -hex 32)
        log_success "Generated JWT secret: ${JWT_SECRET_KEY:0:8}..."
    fi
    
    if [[ -z "${ORGANIZATION_NAME:-}" ]]; then
        read -p "Organization name [$CLIENT_ID]: " ORGANIZATION_NAME
        ORGANIZATION_NAME="${ORGANIZATION_NAME:-$CLIENT_ID}"
    fi
else
    # Non-interactive mode - require environment variables
    if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
        log_error "POSTGRES_PASSWORD not set"
        exit 1
    fi
    if [[ -z "${JWT_SECRET_KEY:-}" ]]; then
        log_error "JWT_SECRET_KEY not set"
        exit 1
    fi
    ORGANIZATION_NAME="${ORGANIZATION_NAME:-$CLIENT_ID}"
fi

# Validate JWT secret key
if [[ ${#JWT_SECRET_KEY} -lt 32 ]]; then
    log_error "JWT_SECRET_KEY too short (minimum 32 characters, typically 64)"
    exit 1
fi

# Create environment file from template
log_info "Creating environment file: $ENV_FILE"

cp .env.example "$ENV_FILE"

# Update environment file with specific values
if [[ "$ENVIRONMENT" == "prod" ]]; then
    sed -i "s/^ENVIRONMENT=.*/ENVIRONMENT=prod/" "$ENV_FILE"
    sed -i "s/^DEBUG=.*/DEBUG=false/" "$ENV_FILE"
else
    sed -i "s/^ENVIRONMENT=.*/ENVIRONMENT=$ENVIRONMENT/" "$ENV_FILE"
    sed -i "s/^DEBUG=.*/DEBUG=true/" "$ENV_FILE"
fi

sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$POSTGRES_PASSWORD/" "$ENV_FILE"
sed -i "s/^JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$JWT_SECRET_KEY/" "$ENV_FILE"
sed -i "s/^ORGANIZATION_ID=.*/ORGANIZATION_ID=$CLIENT_ID/" "$ENV_FILE"
sed -i "s/^ORGANIZATION_NAME=.*/ORGANIZATION_NAME=$ORGANIZATION_NAME/" "$ENV_FILE"

log_success "Environment file created"

# Create deployment directories
log_info "Creating deployment directories..."
mkdir -p data logs backups docker-volumes/postgres docker-volumes/app

# Set proper permissions
chmod 700 data logs backups docker-volumes/postgres docker-volumes/app

log_success "Directories created"

# Build Docker images
log_info "Building Docker images..."
if docker-compose -f docker-compose.yml build --no-cache 2>&1 | tee docker-build.log; then
    log_success "Docker images built successfully"
else
    log_error "Docker image build failed. See docker-build.log for details."
    exit 1
fi

# Validate build
log_info "Validating Docker Compose configuration..."
if docker-compose -f docker-compose.yml config > /dev/null 2>&1; then
    log_success "Docker Compose configuration is valid"
else
    log_error "Docker Compose configuration is invalid"
    exit 1
fi

# Create backup of .env file
cp "$ENV_FILE" "$ENV_FILE.backup"
log_success "Backup created: $ENV_FILE.backup"

log_info ""
log_success "=========================================="
log_success "Deployment initialization complete!"
log_success "=========================================="
log_info ""
log_info "Next steps:"
log_info "1. Review environment configuration: $ENV_FILE"
log_info "2. Start services: docker-compose --env-file $ENV_FILE up -d"
log_info "3. Run database migrations: ./scripts/migrate-db.sh --env-file $ENV_FILE"
log_info "4. Verify health: ./scripts/health-check.sh --env-file $ENV_FILE"
log_info ""
log_warning "IMPORTANT: Securely back up $ENV_FILE and keep the JWT_SECRET_KEY safe!"
log_info ""
