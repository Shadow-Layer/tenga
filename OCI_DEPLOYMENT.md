# Tenga Inventory POS - OCI Deployment Guide

## Oracle Cloud Infrastructure Deployment

This guide explains how to deploy Tenga Inventory POS on Oracle Cloud Infrastructure.

## Prerequisites

1. OCI account with appropriate permissions
2. OCI CLI installed and configured
3. SSH key pair generated
4. Compartment where resources will be created
5. VCN (Virtual Cloud Network) with subnet

## VM Creation on OCI

### Using OCI Console

1. **Compute → Instances → Create Instance**
   - Name: `tenga-inventory-prod` (or client name)
   - Image: Ubuntu 22.04 LTS
   - Shape: VM.Standard.E4.Flex (recommended)
   - Networking: Select appropriate VCN and subnet
   - Storage: 100GB block storage (min 50GB)

2. **SSH Configuration:**
   - Upload your public key in "Add SSH keys"
   - Note the public IP address

### Using OCI CLI

```bash
# List available images
oci compute image list --output table

# Create instance
oci compute instance launch \
  --display-name tenga-inventory-prod \
  --image-id ocid1.image.oc1.* \
  --shape VM.Standard.E4.Flex \
  --shape-config '{"ocpus": 2, "memory_in_gbs": 4}' \
  --subnet-id <SUBNET_OCID> \
  --ssh-authorized-keys-file ~/.ssh/tenga.pub \
  --compartment-id <COMPARTMENT_OCID>

# Get instance IP
oci compute instance list --compartment-id <COMPARTMENT_OCID> --output table
```

## Post-Deployment Setup

### 1. Connect to VM

```bash
ssh -i ~/.ssh/tenga ubuntu@<PUBLIC_IP>
```

### 2. Update System

```bash
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y curl wget git htop iotop net-tools
```

### 3. Install Docker & Docker Compose

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker ubuntu
newgrp docker

# Verify Docker
docker --version

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify
docker-compose --version
```

### 4. Clone Application

```bash
# Create application directory
mkdir -p /opt/tenga-inventory
cd /opt/tenga-inventory

# Clone repository
git clone <REPOSITORY_URL> .

# Or copy from local
# scp -r -i ~/.ssh/tenga local/app/* ubuntu@<IP>:/opt/tenga-inventory/
```

### 5. Configure Firewall (OCI Security Lists)

In OCI Console:

1. **VCN → Virtual Cloud Networks → your VCN → Security Lists**
2. **Add Ingress Rules:**
   - Protocol: TCP, Source: 0.0.0.0/0, Destination Port: 80 (HTTP)
   - Protocol: TCP, Source: 0.0.0.0/0, Destination Port: 443 (HTTPS - when configured)
   - Protocol: TCP, Source: your IP, Destination Port: 22 (SSH)

### 6. Configure Domain (Optional)

1. **DNS Configuration (your domain registrar):**
   ```
   A record: tenga.yourdomain.com -> <PUBLIC_IP>
   ```

2. **Update CORS Origins:**
   ```bash
   CORS_ORIGINS=https://tenga.yourdomain.com
   ```

## Deployment

Follow the [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) quick start section:

```bash
cd /opt/tenga-inventory

# Initialize deployment
./scripts/deploy-init.sh --env prod --client-id client-name

# Start services
docker-compose --env-file .env.deployment.client-name up -d

# Verify
./scripts/health-check.sh --env-file .env.deployment.client-name
```

## HTTPS/TLS Setup (Recommended)

### Using Let's Encrypt with Certbot

```bash
# Install certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Generate certificate (requires domain)
sudo certbot certonly --standalone -d tenga.yourdomain.com

# Update docker-compose.yml to mount certificates
volumes:
  - /etc/letsencrypt/live/tenga.yourdomain.com/fullchain.pem:/etc/nginx/certs/cert.pem
  - /etc/letsencrypt/live/tenga.yourdomain.com/privkey.pem:/etc/nginx/certs/key.pem

# Update nginx.conf to use HTTPS
listen 443 ssl http2;
ssl_certificate /etc/nginx/certs/cert.pem;
ssl_certificate_key /etc/nginx/certs/key.pem;

# Auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

## OCI-Specific Considerations

### Storage

1. **Block Volume** (recommended for databases):
   ```bash
   # Attach block volume to instance
   # In OCI Console: Compute → Instances → Attached Block Volumes
   
   # Mount in VM
   sudo fdisk -l  # Find device
   sudo mkfs.ext4 /dev/sdb
   sudo mkdir -p /mnt/data
   sudo mount /dev/sdb /mnt/data
   
   # Make permanent
   echo '/dev/sdb /mnt/data ext4 defaults,nofail,discard 0 0' | sudo tee -a /etc/fstab
   
   # Update docker volumes to use mounted path
   - /mnt/data/postgres:/var/lib/postgresql/data
   ```

2. **Object Storage** (for backups):
   ```bash
   # Install OCI CLI
   sudo apt-get install -y python3-oci-sdk
   oci setup config  # Configure credentials
   
   # Backup to Object Storage
   ./scripts/backup.sh --backup
   oci os object put --bucket-name tenga-backups --file backups/tenga_*.sql.gz
   ```

### Load Balancing (Multi-Instance)

For high availability across multiple VMs:

1. **Create Network Load Balancer:**
   ```bash
   oci nlb network-load-balancer create \
     --display-name tenga-nlb \
     --subnet-id <SUBNET_OCID> \
     --scheme INTERNET
   ```

2. **Create Backend Set:**
   - Health Check: POST to /health
   - Policy: Round Robin
   - Add instances

3. **DNS:**
   ```
   A record: tenga.yourdomain.com -> NLB public IP
   ```

### Auto Scaling

For CPU/Memory-based scaling:

1. **Create Instance Configuration** from existing instance
2. **Create Instance Pool** using configuration
3. **Create Autoscaling Policy:**
   - Target metric: CPU > 70%
   - Scale up: +1 instance
   - Scale down: -1 instance (minimum 1)

### Monitoring (OCI Monitoring)

```bash
# Enable advanced monitoring
oci compute instance update \
  --instance-id <INSTANCE_OCID> \
  --instance-options '{"are_legacy_imds_endpoints_disabled": false}'

# View metrics in OCI Console
# Compute → Instances → Metrics
```

### Backup Strategy

1. **Database Backups** (to Object Storage):
   ```bash
   # Cron job to backup to Object Storage
   crontab -e
   
   0 2 * * * cd /opt/tenga-inventory && \
     ./scripts/backup.sh --backup --env-file .env.production && \
     oci os object put --bucket-name tenga-backups \
       --file backups/tenga_*.sql.gz
   ```

2. **Block Volume Snapshots**:
   ```bash
   # In OCI Console or CLI
   oci bv volume create \
     --availability-domain <AD> \
     --compartment-id <COMPARTMENT> \
     --size-in-gbs 100
   ```

3. **Instance Image Backup**:
   ```bash
   # Create image from running instance
   oci compute image create-from-instance \
     --instance-id <INSTANCE_OCID> \
     --display-name tenga-backup-$(date +%Y%m%d)
   ```

## Cost Optimization

### Recommended Settings

1. **Flex Shape** (cost-effective):
   - 2 OCPUs / 4GB RAM for small deployments
   - 4 OCPUs / 8GB RAM for medium deployments

2. **Resource Monitoring:**
   ```bash
   # Check actual usage
   docker stats --no-stream
   
   # Right-size based on actual usage
   # Update OCI shape if needed
   ```

3. **Reserved Instances** (for committed capacity):
   - Consider 12-month or 36-month commitment
   - Up to 50% cost savings

4. **Spot Instances** (for non-critical workloads):
   - Up to 70% discount
   - Not recommended for production databases

## Security Best Practices

1. **OCI Security Groups/Network Security Lists:**
   - Restrict SSH to known IPs
   - Only allow necessary ports (80, 443)
   - Use VPN for admin access

2. **Enable OCI Data Safe:**
   - Monitor database activity
   - Detect anomalies
   - Mask sensitive data

3. **Enable OCI Cloud Guard:**
   - Security posture management
   - Threat detection
   - Compliance monitoring

4. **Vault for Secrets:**
   ```bash
   # Store secrets in OCI Vault
   oci vault secret create \
     --secret-name tenga-jwt-secret \
     --secret-content-type PLAINTEXT \
     --secret-content $(openssl rand -hex 32)
   ```

## Disaster Recovery

### Backup Region (Cross-Region)

```bash
# Create backup in another region
./scripts/backup.sh --backup

# Copy to Object Storage in different region
oci os object put \
  --bucket-name tenga-backups \
  --region us-phoenix-1 \
  --file backups/tenga_*.sql.gz
```

### Recovery Procedure

```bash
# If primary VM fails:
1. Create new VM in same region
2. Install Docker/Docker Compose
3. Deploy application
4. Restore database from backup
5. Update DNS to point to new VM
```

## Troubleshooting OCI-Specific Issues

### Instance Connectivity

```bash
# Check instance status
oci compute instance get --instance-id <INSTANCE_OCID> --output table

# Check network connectivity
ping -c 4 <PUBLIC_IP>

# SSH debug
ssh -v -i ~/.ssh/tenga ubuntu@<PUBLIC_IP>
```

### Storage Issues

```bash
# Check disk usage
df -h /

# Check I/O performance
iostat -x 1 5

# Expand volume if needed
# (Create snapshot, create larger volume, restore)
```

### Networking

```bash
# Check VCN routes
oci vcn route-table list --vcn-id <VCN_OCID>

# Check security list rules
oci vcn security-list list --vcn-id <VCN_OCID>

# Test port connectivity
nc -zv <IP> 80
nc -zv <IP> 443
nc -zv <IP> 5432  # Should fail (internal only)
```

## OCI Resource Cleanup

When decommissioning:

```bash
# Backup data first!
./scripts/backup.sh --backup

# Delete snapshots
oci bv boot-volume-backup delete --boot-volume-backup-id <OCID>

# Detach block volumes
oci compute volume-attachment detach --volume-attachment-id <OCID>

# Terminate instance
oci compute instance terminate --instance-id <INSTANCE_OCID> --force

# Release public IP
oci network public-ip delete --public-ip-id <OCID>

# Delete VCN (if not used by others)
oci vcn delete --vcn-id <VCN_OCID> --force
```

---

**Version:** T013  
**For detailed deployment instructions, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**
