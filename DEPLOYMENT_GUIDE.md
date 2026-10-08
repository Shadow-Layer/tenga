# Tenga Inventory POS - Containerized Deployment Guide (T013)

## Overview

This document provides comprehensive guidance for deploying Tenga Inventory POS in a containerized environment, suitable for client installations on Oracle Cloud Infrastructure (OCI) or other cloud providers.

**Target Architecture:**
```
Client Installation (OCI VM)
  ↓
Docker Compose
  ├── PostgreSQL 16 (persistent database)
  ├── FastAPI Application (Python)
  ├── Frontend (React/Nginx)
  └── Persistent Volumes (data, logs, backups)
```

## Table of Contents

1. [Requirements](#requirements)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Detailed Deployment](#detailed-deployment)
5. [Configuration](#configuration)
6. [Persistence & Backup](#persistence--backup)
7. [Client Isolation](#client-isolation)
8. [Security](#security)
9. [Operations](#operations)
10. [Troubleshooting](#troubleshooting)

## Requirements

### Hardware (Minimum)
- **CPU:** 2 vCPUs
- **Memory:** 4GB RAM
- **Storage:** 50GB (20GB for OS, 30GB for application/data)
- **Network:** Public IP with port 80/443 accessible

### Software
- **OS:** Ubuntu 20.04 LTS, 22.04 LTS, or similar Linux
- **Docker:** 20.10+ ([install guide](https://docs.docker.com/engine/install/))
- **Docker Compose:** 2.0+ ([install guide](https://docs.docker.com/compose/install/))
- **OpenSSL:** For secret generation
- **curl/wget:** For health checks and API testing

### Credentials/Access
- OCI account and API credentials (if deploying to OCI)
- SSH access to the VM
- Port forwarding for 80 (HTTP), 443 (HTTPS - when configured)

## Architecture

### Components

#### PostgreSQL (Database)
- **Image:** `postgres:16-alpine`
- **Port:** 5432 (internal only, not exposed)
- **Volume:** `postgres_data` (persistent storage)
- **Init Script:** `scripts/init-db.sql`
- **Health Check:** `pg_isready`

#### FastAPI Application (API)
- **Image:** Built from `Dockerfile`
- **Port:** 8000 (internal, proxied through Nginx)
- **Volumes:**
  - `app_data`: `/data` for persistent storage
  - `app_logs`: `/app/logs` for application logs
- **Dependencies:** PostgreSQL, environment variables
- **User:** `appuser` (non-root, UID 1000)
- **Health Checks:** `/health` (liveness), `/ready` (readiness)

#### Frontend (React + Nginx)
- **Image:** Built from `Dockerfile.frontend`
- **Port:** 80 (exposed to public)
- **Volumes:** `frontend_logs` for access/error logs
- **Security:** Non-root user, security headers (X-Frame-Options, CSP, etc.)
- **Proxy:** Routes `/api/*` to API service

#### Persistent Volumes
- `postgres_data`: PostgreSQL database files
- `app_data`: Application data, uploads
- `app_logs`: Application and Nginx logs
- `frontend_logs`: Frontend access/error logs

### Network
- **Type:** Bridge network (`tenga-network`)
- **Subnet:** 172.20.0.0/16
- **DNS Resolution:** Services communicate via container names
- **External Access:** Only Nginx (port 80) is publicly accessible

### Logging
- **Driver:** JSON file
- **Limits:** 10MB per file, max 3 files per container
- **Location:** `/var/lib/docker/containers/<container-id>/`

## Quick Start

### 1. Prerequisites

```bash
# Verify Docker installation
docker --version
docker-compose --version

# Verify sufficient disk space
df -h /

# Verify sudo access
sudo docker ps
```

### 2. Clone/Prepare Application

```bash
# If not already done
cd /opt/tenga-inventory
git clone <repository-url> .
cd tenga-inventory
```

### 3. Initialize Deployment

```bash
# Run initialization script (interactive)
./scripts/deploy-init.sh --env prod --client-id "client-name"

# This will:
# - Validate Docker setup
# - Build Docker images
# - Create environment file (.env.deployment.client-name)
# - Create necessary directories
# - Generate security secrets if needed
```

### 4. Start Services

```bash
# Load environment
export $(grep -v '^#' .env.deployment.client-name | grep -v '^$' | xargs)

# Start services
docker-compose --env-file .env.deployment.client-name up -d

# Watch startup
docker-compose logs -f
```

### 5. Run Migrations

```bash
./scripts/migrate-db.sh --env-file .env.deployment.client-name
```

### 6. Verify Health

```bash
./scripts/health-check.sh --env-file .env.deployment.client-name

# Continuous monitoring
./scripts/health-check.sh --env-file .env.deployment.client-name --watch
```

### 7. Access Application

- **Frontend:** http://your-vm-ip/
- **API Docs:** http://your-vm-ip/api/docs
- **Health:** http://your-vm-ip/health

## Detailed Deployment

### Step 1: OCI VM Setup

#### Create VM Instance

```bash
# Using OCI CLI
oci compute instance launch \
  --compartment-id <COMPARTMENT_ID> \
  --image-id <UBUNTU_IMAGE_ID> \
  --shape VM.Standard.E4.Flex \
  --shape-config ocpus=2,memory_in_gbs=4 \
  --ssh-authorized-keys-file ~/.ssh/id_rsa.pub \
  --subnet-id <SUBNET_ID>
```

#### Connect to VM

```bash
ssh -i ~/.ssh/id_rsa ubuntu@<PUBLIC_IP>

# Update system
sudo apt-get update
sudo apt-get upgrade -y
```

### Step 2: Install Docker & Docker Compose

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker ubuntu

# Install Docker Compose (if not included)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify
docker --version
docker-compose --version
```

### Step 3: Prepare Application

```bash
# Create application directory
sudo mkdir -p /opt/tenga-inventory
sudo chown ubuntu:ubuntu /opt/tenga-inventory

cd /opt/tenga-inventory

# Clone repository
git clone <repository-url> .

# OR copy application files
# scp -r local/path/to/app ubuntu@<IP>:/opt/tenga-inventory/
```

### Step 4: Generate Secrets

```bash
# Generate secure passwords and keys
POSTGRES_PASSWORD=$(openssl rand -hex 16)
JWT_SECRET=$(openssl rand -hex 32)

echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD"
echo "JWT_SECRET=$JWT_SECRET"

# Save these securely!
```

### Step 5: Configure Deployment

```bash
# Copy and edit environment file
cp .env.example .env.production

# Edit with your values
nano .env.production
```

**Key variables to configure:**

```bash
ENVIRONMENT=prod
DEBUG=false
POSTGRES_PASSWORD=<YOUR_SECURE_PASSWORD>
JWT_SECRET_KEY=<YOUR_SECURE_SECRET>
CORS_ORIGINS=https://your-domain.com
ORGANIZATION_ID=client-name
ORGANIZATION_NAME="Client Display Name"
```

### Step 6: Build & Deploy

```bash
# Build images
docker-compose -f docker-compose.yml build

# Start services
docker-compose --env-file .env.production up -d

# Verify startup
docker-compose logs -f

# Wait for services to be ready (1-2 minutes)
./scripts/health-check.sh --env-file .env.production

# Run migrations
./scripts/migrate-db.sh --env-file .env.production

# Final health check
./scripts/health-check.sh --env-file .env.production
```

## Configuration

### Environment Variables

All configuration is done via environment variables. Key variables:

**Deployment:**
```bash
ENVIRONMENT=prod                    # dev, test, or prod
DEBUG=false                         # Enable debug logging
```

**Database:**
```bash
POSTGRES_HOST=postgres              # Container name or hostname
POSTGRES_PORT=5432                  # PostgreSQL port
POSTGRES_DB=tenga                   # Database name
POSTGRES_USER=tenga_user            # Database user
POSTGRES_PASSWORD=<secure>          # MUST be changed in production
DB_POOL_SIZE=20                     # Connection pool size
DB_MAX_OVERFLOW=30                  # Max overflow connections
SQL_ECHO=false                      # Log SQL queries (verbose)
```

**API:**
```bash
API_TITLE=Tenga Inventory POS
API_VERSION=T013
API_PORT=8000
CORS_ORIGINS=http://localhost,https://your-domain.com
CORS_ALLOW_CREDENTIALS=false
```

**Security:**
```bash
JWT_SECRET_KEY=<secure_random_value>      # MUST be changed!
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=480       # 8 hours
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7           # 7 days
```

**Organization/Client:**
```bash
ORGANIZATION_ID=client-unique-id          # For multi-tenant isolation
ORGANIZATION_NAME=Client Display Name
```

### Ports

- **80 (HTTP):** Frontend (Nginx) - public
- **443 (HTTPS):** Frontend with reverse proxy - requires additional setup
- **8000 (Internal):** API service
- **5432 (Internal):** PostgreSQL database

### Volumes

Mount points inside containers:

```
API Container:
  /data              -> app_data volume
  /app/logs          -> app_logs volume
  /app               -> application code (read-only)

PostgreSQL Container:
  /var/lib/postgresql/data -> postgres_data volume

Frontend Container:
  /usr/share/nginx/html    -> built application
  /var/log/nginx           -> frontend_logs volume
```

## Persistence & Backup

### Data Persistence

All data is persisted in Docker volumes:

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect tenga-inventory_postgres_data

# Backup volume data
docker run --rm -v tenga-inventory_postgres_data:/data -v $(pwd)/backup:/backup alpine tar czf /backup/postgres_data.tar.gz -C /data .
```

### Database Backups

**Manual Backup:**
```bash
./scripts/backup.sh --backup --env-file .env.production
```

**Scheduled Backups (Cron):**
```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM UTC
0 2 * * * cd /opt/tenga-inventory && ./scripts/backup.sh --backup --env-file .env.production

# Add weekly cleanup (remove backups older than 30 days)
0 3 * * 0 cd /opt/tenga-inventory && ./scripts/backup.sh --prune --env-file .env.production
```

**List Available Backups:**
```bash
./scripts/backup.sh --list --env-file .env.production
```

**Restore from Backup:**
```bash
./scripts/backup.sh --restore backups/tenga_20240101_120000.sql.gz --env-file .env.production
```

### Backup Storage

For production:
1. Store backups on separate volume or external storage
2. Encrypt backups for transmission
3. Test restore procedures regularly
4. Maintain backups in multiple locations (at minimum: local + cloud)

```bash
# Example: Backup to S3 (after backup is created)
aws s3 cp backups/tenga_*.sql.gz s3://your-bucket/backups/
```

## Client Isolation

### Single-Tenant Architecture

Each client installation is completely isolated:

1. **Separate Database:** Each client has their own PostgreSQL database
2. **Separate Application Instance:** Each client runs their own API container
3. **Separate Configuration:** Each client has their own `.env` file
4. **Separate Data:** Data volumes are not shared

### Deploying Multiple Clients on One Server

If deploying multiple clients on the same server, use Docker Compose with different services/ports:

```bash
# Client A
docker-compose --env-file .env.client-a \
  -p tenga-client-a \
  --file docker-compose.yml \
  up -d

# Client B
docker-compose --env-file .env.client-b \
  -p tenga-client-b \
  --file docker-compose.yml \
  up -d
```

**Important:** Use different ports for each client:

```bash
# .env.client-a
POSTGRES_PORT=5432
API_PORT=8000
FRONTEND_PORT=80

# .env.client-b
POSTGRES_PORT=5433
API_PORT=8001
FRONTEND_PORT=81
```

### Preventing Data Leaks

- Container network isolation (bridge network per deployment)
- Database-level isolation (separate databases)
- Separate configuration files with sensitive data
- No shared volumes between clients
- Encrypted backups with access control

## Security

### Container Security

1. **Non-root Users:** All services run as non-root users
   - API: `appuser` (UID 1000)
   - Frontend: `appuser` (UID 1000)

2. **Security Options:**
   ```yaml
   security_opt:
     - no-new-privileges:true
   ```

3. **Read-only Filesystems:** Where practical
   ```bash
   # Example (if implemented)
   read_only: true
   tmpfs:
     - /run
   ```

### Secret Management

1. **Never commit secrets to git:**
   ```bash
   # .gitignore
   .env*
   !.env.example
   docker-compose.override.yml
   ```

2. **Generate strong secrets:**
   ```bash
   # PostgreSQL password (16+ chars)
   openssl rand -hex 16

   # JWT secret (32+ chars, typically 64)
   openssl rand -hex 32
   ```

3. **Store secrets securely:**
   - Use Docker secrets (swarm mode) or Docker configs
   - Use environment variable files with restricted permissions
   - Use HashiCorp Vault or similar for production
   - Never share `.env` files

4. **Rotate secrets periodically:**
   - JWT keys: Every 90 days
   - Database passwords: Every 180 days
   - API keys: As needed

### Network Security

1. **Only expose necessary ports:**
   - Port 80: Frontend (HTTP)
   - Port 443: Frontend (HTTPS) - when configured
   - Other ports: Internal only

2. **Use firewall rules:**
   ```bash
   # Allow only specific IPs (example)
   sudo ufw allow from 203.0.113.0/24 to any port 22
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

3. **HTTPS/TLS Setup (recommended for production):**
   - Use reverse proxy with SSL certificate
   - Get certificate from Let's Encrypt (free)
   - Auto-renewal with certbot

### Database Security

1. **Non-public access:**
   - PostgreSQL port 5432 only accessible internally
   - No external database connections

2. **Strong credentials:**
   - Unique username and password
   - Follow password policy (16+ characters)

3. **Database-level access control:**
   ```sql
   -- Least privilege principle
   GRANT CONNECT ON DATABASE tenga TO tenga_user;
   GRANT USAGE ON SCHEMA public TO tenga_user;
   GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO tenga_user;
   ```

### CORS Configuration

Configure for your specific domain:

```bash
# Production
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com

# Development only
CORS_ORIGINS=http://localhost,http://localhost:3000
```

Never use `*` in production.

### Logging & Monitoring

1. **View Application Logs:**
   ```bash
   docker-compose logs api
   docker-compose logs postgres
   docker-compose logs frontend
   docker-compose logs -f         # Follow logs
   ```

2. **Log Rotation (automatic):**
   ```bash
   # Configured in docker-compose.yml
   logging:
     driver: "json-file"
     options:
       max-size: "10m"
       max-file: "3"
   ```

3. **Monitoring:**
   - Check resource usage: `docker stats`
   - Monitor errors: `docker-compose logs --tail 100`
   - Health checks: `./scripts/health-check.sh --watch`

## Operations

### Starting & Stopping

```bash
# Start all services
docker-compose --env-file .env.production up -d

# Stop all services
docker-compose --env-file .env.production down

# Graceful restart
docker-compose --env-file .env.production restart

# Full restart (clears caches)
docker-compose --env-file .env.production down
docker-compose --env-file .env.production up -d
```

### Viewing Logs

```bash
# Real-time logs (all services)
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f postgres

# Last N lines
docker-compose logs --tail 50

# Since specific time
docker-compose logs --since 2024-01-15T10:00:00
```

### Updating Application

```bash
# Pull latest code
git pull origin main

# Rebuild image
docker-compose build api frontend

# Restart services
docker-compose --env-file .env.production up -d

# Verify
./scripts/health-check.sh --env-file .env.production
```

### Rollback Strategy

```bash
# Tag current deployment
TAG=$(date +%Y%m%d_%H%M%S)
git tag "deployment-$TAG"
docker tag tenga-inventory_api:latest tenga-inventory_api:$TAG
docker tag tenga-inventory_frontend:latest tenga-inventory_frontend:$TAG

# Create backup before major updates
./scripts/backup.sh --backup --env-file .env.production

# If update fails, rollback:
docker-compose down
git reset --hard deployment-$TAG
docker build -t tenga-inventory_api:latest .
docker-compose --env-file .env.production up -d
./scripts/health-check.sh --env-file .env.production
```

### Database Operations

```bash
# Connect to database
docker-compose exec postgres psql -U tenga_user -d tenga

# Backup
./scripts/backup.sh --backup

# Restore
./scripts/backup.sh --restore backups/tenga_20240101_120000.sql.gz

# Check database size
docker-compose exec postgres psql -U tenga_user -d tenga -c "SELECT pg_database.datname, pg_size_pretty(pg_database_size(pg_database.datname)) FROM pg_database;"
```

## Troubleshooting

### Services Not Starting

```bash
# Check service status
docker-compose ps

# View startup logs
docker-compose logs --tail 100

# Check container logs
docker logs <container-id>

# Common issues:
# 1. Port already in use
sudo lsof -i :80  # Check port
sudo lsof -i :5432

# 2. Volume permission issues
docker-compose down
sudo chown -R 1000:1000 data logs backups
docker-compose up -d

# 3. Out of disk space
df -h

# 4. Memory issues
docker stats
```

### Database Connection Issues

```bash
# Test connection from API container
docker-compose exec api psql postgresql://tenga_user:password@postgres:5432/tenga

# Check PostgreSQL logs
docker-compose logs postgres

# Verify PostgreSQL is healthy
docker-compose exec postgres pg_isready -U tenga_user
```

### API Not Responding

```bash
# Check if container is running
docker-compose ps api

# View API logs
docker-compose logs api

# Check if it's listening on port 8000
docker-compose exec api netstat -tlnp | grep 8000

# Test health endpoint
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

### Frontend Not Loading

```bash
# Check nginx logs
docker-compose logs frontend

# Check if frontend is serving files
docker-compose exec frontend ls -la /usr/share/nginx/html

# Test frontend health
curl http://localhost/health

# Check nginx configuration
docker-compose exec frontend cat /etc/nginx/conf.d/default.conf
```

### Performance Issues

```bash
# Monitor resource usage
docker stats

# Check disk I/O
iostat -x 1 5

# Database query performance
docker-compose exec postgres psql -U tenga_user -d tenga -c "EXPLAIN ANALYZE <your_query>;"

# Clear Docker logs
docker system prune -a --volumes
```

### Backup/Restore Issues

```bash
# Check backup directory
ls -la backups/

# Test restore on copy of database
./scripts/backup.sh --restore backups/tenga_test.sql.gz --env-file .env.production

# Verify backup integrity
gunzip -t backups/tenga_*.sql.gz

# Monitor backup process
./scripts/backup.sh --backup --env-file .env.production
# (Should complete without errors)
```

## Health Checks & Monitoring

### Manual Health Check

```bash
# One-time check
./scripts/health-check.sh --env-file .env.production

# Continuous monitoring (updates every 5s)
./scripts/health-check.sh --env-file .env.production --watch
```

### Automated Monitoring (Cron)

```bash
# Add health check to crontab
crontab -e

# Check every 5 minutes, log if unhealthy
*/5 * * * * cd /opt/tenga-inventory && ./scripts/health-check.sh --env-file .env.production >> /var/log/tenga-health.log 2>&1 || echo "Health check failed at $(date)" >> /var/log/tenga-health.log
```

### System Resource Monitoring

```bash
# Real-time resource usage
docker stats --no-stream

# Detailed container info
docker inspect <container-id>

# Storage usage
docker system df

# Clean up unused resources
docker system prune
```

## Production Hardening (Post-T013)

The following are recommended for production hardening after T013:

1. **HTTPS/TLS Setup**
   - Install SSL certificate (Let's Encrypt)
   - Configure reverse proxy (nginx/traefik)
   - Enforce HTTPS redirect

2. **Advanced Monitoring**
   - Prometheus + Grafana for metrics
   - ELK stack or similar for centralized logging
   - Alerting system (PagerDuty, Slack, etc.)

3. **Kubernetes Migration**
   - Move to Kubernetes for high availability
   - Horizontal scaling
   - Service mesh (Istio)

4. **Secrets Management**
   - HashiCorp Vault
   - AWS Secrets Manager
   - GCP Secret Manager

5. **Database Replication**
   - PostgreSQL streaming replication
   - Read replicas for reporting
   - Multi-region backup strategy

6. **Load Balancing**
   - Multiple API instances
   - Load balancer (nginx, HAProxy, cloud LB)
   - Session management

7. **Security Scanning**
   - Container image scanning (Trivy, Snyk)
   - Vulnerability management
   - Security patches automation

8. **Compliance & Audit**
   - Audit logging
   - Compliance dashboards (SOC2, HIPAA, etc.)
   - Regular security assessments

## Support & Updates

For issues, questions, or updates:
- GitHub Issues: <repository-url>/issues
- Documentation: See README.md and API_DOCS.md
- API Specification: http://your-vm-ip/api/docs
- Database Schema: See DATABASE_CONFIGURATION.md

---

**Version:** T013  
**Last Updated:** 2024-01-15  
**Maintainer:** Tenga Inventory Team
