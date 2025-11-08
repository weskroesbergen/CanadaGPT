# Neo4j GCP Migration Guide

This directory contains scripts to migrate your local Neo4j database to Google Cloud Platform.

## Overview

**Goal:** Move Neo4j from local Docker to a Google Compute Engine VM with automated backups.

**Estimated Cost:** $50-65/month
**Migration Time:** 1-2 hours (mostly automated)
**Downtime:** ~30 minutes during database export

## Architecture

```
┌─────────────────┐
│   Local Docker  │
│     Neo4j       │──┐
└─────────────────┘  │
                     │ Export & Upload
                     ↓
              ┌──────────────┐
              │     GCS      │
              │   Backups    │
              └──────────────┘
                     ↑ │
         Upload      │ │ Download
         Backups     │ ↓
                ┌────────────────┐
                │   GCE VM       │
                │  Neo4j 5.14    │
                │  2 vCPU, 8GB   │
                └────────────────┘
                     ↑
                     │ Bolt Protocol
                     │
              ┌──────────────┐
              │  GraphQL API │
              └──────────────┘
```

## Prerequisites

- [x] Docker Desktop installed and running
- [x] gcloud CLI installed
- [x] GCP account with billing enabled
- [x] Local Neo4j database running (canadagpt-neo4j)

## Migration Steps

### Step 1: GCP Project Setup

```bash
chmod +x scripts/gcp-migration/*.sh
./scripts/gcp-migration/01-setup-gcp.sh
```

This script will:
- Authenticate with Google Cloud
- Create or select a GCP project
- Enable required APIs (Compute, Storage, Secret Manager)
- Set default region (us-central1)
- Create configuration file

### Step 2: Create Backup Bucket

```bash
./scripts/gcp-migration/02-create-backup-bucket.sh
```

Creates a GCS bucket for:
- Database backups (automated daily)
- Migration dump files
- 30-day retention policy

### Step 3: Export Database

```bash
./scripts/gcp-migration/03-export-database.sh
```

**⚠️ WARNING:** This will temporarily stop your local Neo4j!

The script will:
1. Stop Docker container
2. Create database dump (~3GB)
3. Compress the dump
4. Upload to GCS
5. Restart local Neo4j

Expected file size: ~500MB-1GB compressed

### Step 4: Create GCE VM

```bash
./scripts/gcp-migration/04-create-vm.sh
```

Creates a VM with:
- Machine type: n2-standard-2 (2 vCPU, 8GB RAM)
- Disk: 50GB SSD
- OS: Ubuntu 22.04
- Neo4j 5.14 Community Edition
- APOC plugin pre-installed

Installation takes 5-10 minutes.

### Step 5: Restore Database

```bash
./scripts/gcp-migration/05-restore-database.sh
```

Restores your database to the VM:
1. Downloads dump from GCS
2. Stops Neo4j on VM
3. Loads database
4. Starts Neo4j
5. Verifies data integrity

### Step 6: Setup Automated Backups

```bash
./scripts/gcp-migration/06-setup-backups.sh
```

Configures:
- Daily backups at 2:00 AM
- Automatic upload to GCS
- 30-day retention (GCS lifecycle)
- 7-day local retention
- Backup logging

### Step 7: Configure Firewall

```bash
./scripts/gcp-migration/07-setup-firewall.sh
```

Creates firewall rules:
- Bolt (7687): Internal network only
- Browser (7474): Your IP only (temporary)
- SSH (22): Your IP only

### Step 8: Update Application

```bash
./scripts/gcp-migration/08-update-app-config.sh
```

Updates:
- `packages/graph-api/.env` with VM IP
- Stores password in Secret Manager
- Creates test connection script
- Backs up old configuration

## Testing

### Test Neo4j Connection

```bash
./scripts/gcp-migration/test-connection.sh
```

### Test GraphQL API

```bash
# Restart GraphQL API
cd packages/graph-api
pnpm dev

# Should connect to cloud Neo4j
# Check logs for connection success
```

### Access Neo4j Browser

```bash
# Get VM external IP
source scripts/gcp-migration/.env
echo "http://$NEO4J_VM_EXTERNAL_IP:7474"

# Login:
# Username: neo4j
# Password: canadagpt2024
```

## Rollback to Local

If you need to revert to local Docker:

```bash
# Restore backup
cp packages/graph-api/.env.backup.* packages/graph-api/.env

# Or manually edit
# NEO4J_URI=bolt://localhost:7687

# Restart GraphQL API
cd packages/graph-api
pnpm dev
```

## Maintenance

### Manual Backup

```bash
gcloud compute ssh canadagpt-neo4j --zone=us-central1-a \
  --command='sudo /usr/local/bin/neo4j-backup.sh'
```

### View Backup Logs

```bash
gcloud compute ssh canadagpt-neo4j --zone=us-central1-a \
  --command='sudo tail -f /var/log/neo4j-backup.log'
```

### List Backups

```bash
source scripts/gcp-migration/.env
gsutil ls -lh gs://$BACKUP_BUCKET/backups/
```

### Restore from Backup

```bash
# Download specific backup
gsutil cp gs://$BACKUP_BUCKET/backups/neo4j-backup-YYYYMMDD-HHMMSS.dump.gz .

# Follow restore process from Step 5
```

## Cost Breakdown

| Resource | Specification | Monthly Cost |
|----------|--------------|--------------|
| GCE VM | n2-standard-2 (2 vCPU, 8GB) | $46-72 |
| SSD Disk | 50GB pd-ssd | ~$8 |
| GCS Storage | ~30 backups @ 1GB each | ~$0.60 |
| Network Egress | Minimal (internal) | ~$1 |
| **Total** | | **$50-65/month** |

## Security Considerations

1. **Firewall:** Bolt access restricted to internal network only
2. **Password:** Stored in Secret Manager, not in code
3. **SSH:** Limited to your IP address
4. **Backups:** Encrypted at rest in GCS
5. **Network:** VM uses internal IP for application access

## Production Recommendations

For production deployment:

1. **Remove external browser access:**
   ```bash
   gcloud compute firewall-rules delete allow-neo4j-browser
   ```

2. **Use Cloud VPN or IAP for SSH:**
   ```bash
   gcloud compute firewall-rules delete allow-ssh-neo4j
   # Use: gcloud compute ssh --tunnel-through-iap
   ```

3. **Change default password:**
   ```bash
   # Connect to VM and change password
   cypher-shell -u neo4j -p canadagpt2024
   ALTER USER neo4j SET PASSWORD 'new-secure-password';
   ```

4. **Enable monitoring:**
   ```bash
   # Install Cloud Monitoring agent
   curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
   sudo bash add-google-cloud-ops-agent-repo.sh --also-install
   ```

5. **Set up alerting:**
   - VM uptime
   - Disk usage
   - Backup failures
   - Neo4j service status

## Troubleshooting

### VM won't start
```bash
gcloud compute instances start canadagpt-neo4j --zone=us-central1-a
```

### Neo4j service down
```bash
gcloud compute ssh canadagpt-neo4j --zone=us-central1-a \
  --command='sudo systemctl status neo4j'

# Restart if needed
gcloud compute ssh canadagpt-neo4j --zone=us-central1-a \
  --command='sudo systemctl restart neo4j'
```

### Can't connect from GraphQL API
```bash
# Check firewall rules
gcloud compute firewall-rules list --filter="targetTags:neo4j"

# Check VM internal IP
gcloud compute instances describe canadagpt-neo4j \
  --zone=us-central1-a \
  --format="value(networkInterfaces[0].networkIP)"
```

### Backups not running
```bash
# Check cron job
gcloud compute ssh canadagpt-neo4j --zone=us-central1-a \
  --command='crontab -l'

# Check logs
gcloud compute ssh canadagpt-neo4j --zone=us-central1-a \
  --command='sudo tail -50 /var/log/neo4j-backup.log'
```

## Support

For issues:
1. Check logs: `/var/log/neo4j-backup.log` (on VM)
2. Check Neo4j logs: `/var/log/neo4j/` (on VM)
3. Review GCP Console: https://console.cloud.google.com

## Next Steps

After successful migration:

1. Monitor for 1 week to ensure stability
2. Verify backups are running daily
3. Test restore from backup
4. Deploy GraphQL API to Cloud Run
5. Deploy Frontend to Cloud Run or App Engine
6. Consider upgrading to Neo4j Enterprise for clustering

## File Structure

```
scripts/gcp-migration/
├── README.md (this file)
├── .env (generated - Git ignored)
├── 01-setup-gcp.sh
├── 02-create-backup-bucket.sh
├── 03-export-database.sh
├── 04-create-vm.sh
├── 05-restore-database.sh
├── 06-setup-backups.sh
├── 07-setup-firewall.sh
├── 08-update-app-config.sh
├── neo4j-install.sh (VM startup script)
└── test-connection.sh (generated)
```

## Configuration File

After running setup, `.env` contains:

```bash
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
GCP_ZONE=us-central1-a
NEO4J_VERSION=5.14
NEO4J_PASSWORD=canadagpt2024
VM_NAME=canadagpt-neo4j
VM_MACHINE_TYPE=n2-standard-2
VM_DISK_SIZE=50GB
BACKUP_BUCKET=your-project-neo4j-backups
BACKUP_RETENTION_DAYS=30
NEO4J_VM_INTERNAL_IP=10.x.x.x (generated)
NEO4J_VM_EXTERNAL_IP=x.x.x.x (generated)
```
