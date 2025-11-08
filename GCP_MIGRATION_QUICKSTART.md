# Neo4j GCP Migration - Quick Start Guide

## 🚀 Ready to Migrate!

All migration scripts have been created in `scripts/gcp-migration/`. You're now ready to move your Neo4j database to Google Cloud.

## 📋 Pre-Flight Checklist

Before you begin, ensure:

- [x] gcloud CLI installed and authenticated ✅
- [x] Docker Desktop running
- [ ] GCP project created (or ready to create one)
- [ ] GCP billing enabled on your project
- [ ] ~30 minutes of time available
- [ ] Local Neo4j database is healthy

## 🎯 Migration in 8 Steps

### Step 1: Setup GCP Project (5 min)

```bash
cd /Users/matthewdufresne/FedMCP
./scripts/gcp-migration/01-setup-gcp.sh
```

**What it does:**
- Authenticates with GCP (if needed)
- Creates or selects a project
- Enables required APIs
- Configures defaults
- Creates config file

**You'll need:**
- GCP project ID (or it will create one)
- Billing must be enabled

---

### Step 2: Create Backup Bucket (2 min)

```bash
./scripts/gcp-migration/02-create-backup-bucket.sh
```

**What it does:**
- Creates GCS bucket for backups
- Sets 30-day retention policy
- Enables versioning

**Cost:** ~$1/month for 30GB of backups

---

### Step 3: Export Database (10 min)

```bash
./scripts/gcp-migration/03-export-database.sh
```

**⚠️ WARNING:** This temporarily stops your local Neo4j!

**What it does:**
- Stops Docker Neo4j
- Creates database dump
- Compresses (~500MB-1GB)
- Uploads to GCS
- Restarts local Neo4j

**Downtime:** ~5 minutes

---

### Step 4: Create GCE VM (10 min)

```bash
./scripts/gcp-migration/04-create-vm.sh
```

**What it does:**
- Creates n2-standard-2 VM (2 vCPU, 8GB RAM)
- Installs Ubuntu 22.04
- Installs Neo4j 5.14
- Installs APOC plugin
- Configures memory settings

**Cost:** ~$50-65/month

---

### Step 5: Restore Database (10 min)

```bash
./scripts/gcp-migration/05-restore-database.sh
```

**What it does:**
- Downloads dump from GCS
- Loads into Neo4j on VM
- Verifies data integrity
- Shows database statistics

**Expected:** 370,309 nodes, 1,343,098 relationships

---

### Step 6: Setup Automated Backups (5 min)

```bash
./scripts/gcp-migration/06-setup-backups.sh
```

**What it does:**
- Creates backup script on VM
- Schedules daily backups (2 AM)
- Runs test backup
- Configures retention

**Backup schedule:** Daily at 2:00 AM

---

### Step 7: Configure Firewall (2 min)

```bash
./scripts/gcp-migration/07-setup-firewall.sh
```

**What it does:**
- Creates Bolt access rule (internal only)
- Creates SSH rule (your IP only)
- Creates Browser rule (your IP only)

**Security:** Production-ready defaults

---

### Step 8: Update Application (2 min)

```bash
./scripts/gcp-migration/08-update-app-config.sh
```

**What it does:**
- Updates `packages/graph-api/.env`
- Stores password in Secret Manager
- Creates test script
- Backs up old config

**Changes:** NEO4J_URI points to cloud VM

---

## ✅ Verification

### Test Connection

```bash
./scripts/gcp-migration/test-connection.sh
```

### Start GraphQL API

```bash
cd packages/graph-api
pnpm dev
```

**Look for:**
```
✅ Connected to Neo4j Kernel 5.14.0
📊 Database Statistics:
   Nodes: 370,309
   Relationships: 1,343,098
```

### Access Neo4j Browser

```bash
source scripts/gcp-migration/.env
echo "http://$NEO4J_VM_EXTERNAL_IP:7474"
```

Login with:
- **Username:** neo4j
- **Password:** canadagpt2024

---

## 🔄 Rollback Plan

If something goes wrong:

```bash
# Restore local configuration
cp packages/graph-api/.env.backup.* packages/graph-api/.env

# Or manually edit .env
# NEO4J_URI=bolt://localhost:7687

# Restart GraphQL API
cd packages/graph-api
pnpm dev
```

Your local Docker Neo4j is still intact!

---

## 💰 Cost Summary

| Resource | Monthly Cost |
|----------|-------------|
| GCE VM (n2-standard-2) | $46-72 |
| SSD Disk (50GB) | ~$8 |
| GCS Backups (30GB) | ~$1 |
| Network | ~$1 |
| **Total** | **$50-65/month** |

---

## 🛠 Maintenance Commands

### View Backups

```bash
source scripts/gcp-migration/.env
gsutil ls -lh gs://$BACKUP_BUCKET/backups/
```

### Manual Backup

```bash
source scripts/gcp-migration/.env
gcloud compute ssh $VM_NAME --zone=$GCP_ZONE \
  --command='sudo /usr/local/bin/neo4j-backup.sh'
```

### Check VM Status

```bash
source scripts/gcp-migration/.env
gcloud compute instances describe $VM_NAME --zone=$GCP_ZONE
```

### SSH to VM

```bash
source scripts/gcp-migration/.env
gcloud compute ssh $VM_NAME --zone=$GCP_ZONE
```

### Check Neo4j Logs

```bash
source scripts/gcp-migration/.env
gcloud compute ssh $VM_NAME --zone=$GCP_ZONE \
  --command='sudo journalctl -u neo4j -f'
```

---

## 📚 Full Documentation

See `scripts/gcp-migration/README.md` for:
- Detailed architecture
- Troubleshooting guide
- Production recommendations
- Security best practices
- Cost optimization tips

---

## 🆘 Troubleshooting

### Script fails during execution

Each script is idempotent - you can safely re-run it.

### Can't connect to VM

```bash
# Check firewall rules
gcloud compute firewall-rules list --filter="targetTags:neo4j"

# Check VM is running
gcloud compute instances list --filter="name:canadagpt-neo4j"
```

### GraphQL API can't connect

```bash
# Verify VM internal IP in .env
cat packages/graph-api/.env | grep NEO4J_URI

# Test connection
source scripts/gcp-migration/.env
gcloud compute ssh $VM_NAME --zone=$GCP_ZONE \
  --command='sudo systemctl status neo4j'
```

---

## 🎉 You're Ready!

When you're ready to migrate, just run:

```bash
cd /Users/matthewdufresne/FedMCP
./scripts/gcp-migration/01-setup-gcp.sh
```

Then follow steps 2-8 in sequence.

**Estimated total time:** 1-2 hours
**Actual active time:** ~15 minutes (rest is automated)

Good luck! 🚀
