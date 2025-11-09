# Scheduled Updates Setup Guide

This document describes the automated update system for CanadaGPT parliamentary data.

## Overview

We use a **hybrid approach** for updates:

### 1. Hourly Lightweight Updates (Cloud Run)
**Purpose:** Catch time-sensitive changes
**What it updates:**
- MP party affiliations (detects floor-crossers like Chris d'Entrement)
- Cabinet positions and shuffles
- New bills introduced (last 24 hours)
- Recent votes (last 24 hours)

**Runtime:** ~30-60 seconds
**Memory:** ~200MB
**Cost:** ~$0.01/day
**Schedule:** Every hour (0 * * * *)

### 2. Daily Hansard Import (Ingestion VM)
**Purpose:** Heavy data processing
**What it updates:**
- Full Hansard transcripts (new speeches)
- Historical backfills
- Data quality checks

**Runtime:** ~30-45 minutes
**Memory:** Up to 4GB
**Cost:** ~$0.15/day
**Schedule:** Daily at 3 AM ET (7 AM UTC)

---

## Deployment

### Step 1: Deploy Hourly Updater

```bash
cd /Users/matthewdufresne/FedMCP
chmod +x scripts/deploy-updater-cloudrun.sh
./scripts/deploy-updater-cloudrun.sh
```

This will:
1. Build Docker image for lightweight updater
2. Push to Google Container Registry
3. Deploy as Cloud Run job
4. Create Cloud Scheduler to run hourly

**Prompts:**
- Neo4j URI: `bolt://10.128.0.2:7687` (or your VM's internal IP)
- Neo4j Username: `neo4j`
- Neo4j Password: `canadagpt2024`

### Step 2: Setup Daily Hansard Import

```bash
chmod +x scripts/setup-daily-hansard-import.sh
./scripts/setup-daily-hansard-import.sh
```

This will:
1. Create Cloud Function to start/stop the ingestion VM
2. Create Cloud Scheduler job for daily 3 AM execution
3. Grant necessary IAM permissions

---

## What Gets Updated

### Hourly Updates (Lightweight)

**MP Party Affiliation:**
```cypher
MATCH (m:MP {id: "chris-d-entremont"})
RETURN m.party
// Before: "Conservative"
// After: "Liberal"
```

**Cabinet Changes:**
- Detects new appointments
- Detects resignations
- Detects portfolio shuffles

**Recent Legislation:**
- Bills introduced in last 24 hours
- Votes held in last 24 hours

### Daily Updates (Full Import)

**Hansard Transcripts:**
- New speeches from previous day's proceedings
- Full text content (English & French)
- Speaker attribution
- Topic classification

---

## Monitoring

### Check Hourly Update Status

```bash
# View recent executions
gcloud run jobs executions list \
    --job=canadagpt-updater \
    --region=us-central1

# View logs from latest execution
gcloud logging read \
    "resource.type=cloud_run_job AND resource.labels.job_name=canadagpt-updater" \
    --limit=100 \
    --format=json
```

### Check Daily Hansard Import Status

```bash
# View scheduler job status
gcloud scheduler jobs describe daily-hansard-import \
    --location=us-central1

# View function logs
gcloud functions logs read start-hansard-import \
    --region=us-central1 \
    --limit=50

# Check if VM is running
gcloud compute instances describe canadagpt-ingestion \
    --zone=us-central1-a \
    --format='value(status)'
```

### Check for Party Changes

```bash
# View logs for party change alerts
gcloud logging read \
    "resource.type=cloud_run_job \
    AND resource.labels.job_name=canadagpt-updater \
    AND textPayload=~\"PARTY CHANGES DETECTED\"" \
    --limit=20
```

---

## Manual Triggers

### Trigger Hourly Update Now

```bash
gcloud run jobs execute canadagpt-updater --region=us-central1
```

### Trigger Daily Hansard Import Now

```bash
gcloud scheduler jobs run daily-hansard-import --location=us-central1
```

---

## Cost Breakdown

| Service | Frequency | Cost/Run | Daily Cost | Monthly Cost |
|---------|-----------|----------|------------|--------------|
| Lightweight Updater | 24x/day | $0.0004 | $0.01 | $0.30 |
| Daily Hansard Import | 1x/day | $0.15 | $0.15 | $4.50 |
| **Total** | | | **$0.16/day** | **$4.80/month** |

**Breakdown:**
- Cloud Run job (hourly): $0.01/day (24 executions × 30 seconds × minimal memory)
- Ingestion VM (daily): $0.15/day (30 minutes × e2-standard-4 pricing)
- Cloud Scheduler: $0.10/month per job (2 jobs = $0.20/month)
- Cloud Function: <$0.01/month (1 invocation/day, minimal execution time)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     SCHEDULED UPDATES                        │
└─────────────────────────────────────────────────────────────┘

HOURLY (Every hour)
┌──────────────────┐
│ Cloud Scheduler  │
│  (0 * * * *)     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐      ┌──────────────────┐
│  Cloud Run Job   │─────▶│   Neo4j VM       │
│  (Lightweight    │      │   (Always-on)    │
│   Updater)       │      │                  │
│                  │      │ - MP parties     │
│ Runtime: 30s     │      │ - Cabinet posts  │
│ Memory: 200MB    │      │ - Recent bills   │
│ Cost: $0.0004    │      │ - Recent votes   │
└──────────────────┘      └──────────────────┘

DAILY (3 AM ET)
┌──────────────────┐
│ Cloud Scheduler  │
│  (0 7 * * *)     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  Cloud Function  │─────▶│  Ingestion VM    │─────▶│   Neo4j VM       │
│  (VM Starter)    │      │  (Auto-start)    │      │   (Always-on)    │
│                  │      │                  │      │                  │
│ Runtime: 10s     │      │ - Start VM       │      │ - Hansard import │
│ Memory: 256MB    │      │ - Run import     │      │ - 3.67M stmts    │
│                  │      │ - Auto-shutdown  │      │                  │
│                  │      │                  │      │                  │
│                  │      │ Runtime: 30-45m  │      │                  │
│                  │      │ Memory: 4GB      │      │                  │
└──────────────────┘      └──────────────────┘      └──────────────────┘
```

---

## Change Detection Examples

### Example 1: Floor-Crosser Detection

When Chris d'Entrement switches from Conservative to Liberal:

**Log Output:**
```
2025-11-08 14:00:00 | INFO | Checking for MP party changes...
2025-11-08 14:00:05 | WARNING | 🔄 Party change detected: Chris d'Entremont (Conservative → Liberal)
2025-11-08 14:00:06 | SUCCESS | ✅ Updated 338 MP records

==========================================================
⚠️  PARTY CHANGES DETECTED:
  • Chris d'Entremont: Conservative → Liberal
==========================================================
```

**Neo4j Update:**
```cypher
MATCH (m:MP {id: "chris-d-entremont"})
SET m.party = "Liberal",
    m.updated_at = datetime()
```

### Example 2: Cabinet Shuffle

When a minister changes portfolios:

**Log Output:**
```
2025-11-08 14:00:10 | WARNING | 🔄 Cabinet shuffle: François-Philippe Champagne
                                  (Minister of Innovation → Minister of Foreign Affairs)

==========================================================
📋 CABINET CHANGES DETECTED:
  • SHUFFLE: François-Philippe Champagne:
    Minister of Innovation → Minister of Foreign Affairs
==========================================================
```

---

## Troubleshooting

### Hourly Updates Not Running

**Check scheduler status:**
```bash
gcloud scheduler jobs describe canadagpt-updater-schedule \
    --location=us-central1
```

**Check recent executions:**
```bash
gcloud run jobs executions list \
    --job=canadagpt-updater \
    --region=us-central1 \
    --limit=5
```

### Daily Import Not Running

**Check if VM is accessible:**
```bash
gcloud compute ssh canadagpt-ingestion \
    --zone=us-central1-a \
    --command="echo 'VM is accessible'"
```

**Check Cloud Function logs:**
```bash
gcloud functions logs read start-hansard-import \
    --region=us-central1 \
    --limit=20
```

### High Costs

**Check actual usage:**
```bash
# View billing data for Cloud Run
gcloud billing accounts describe \
    $(gcloud config get-value project) \
    --format="table(displayName,open)"
```

---

## Next Steps

After deployment, you can:

1. **Test the hourly updater:**
   ```bash
   gcloud run jobs execute canadagpt-updater --region=us-central1
   ```

2. **Test the daily import:**
   ```bash
   gcloud scheduler jobs run daily-hansard-import --location=us-central1
   ```

3. **Set up alerting** (optional):
   - Create Pub/Sub topic for party change notifications
   - Send email/Slack alerts when floor-crossers detected
   - Monitor for failed executions

4. **Verify Neo4j data:**
   ```cypher
   // Check latest MP update timestamps
   MATCH (m:MP)
   RETURN m.name, m.party, m.updated_at
   ORDER BY m.updated_at DESC
   LIMIT 10
   ```

---

## Files Created

- `/packages/data-pipeline/scripts/lightweight_update.py` - Hourly updater script
- `/packages/data-pipeline/Dockerfile.updater` - Docker image for Cloud Run
- `/scripts/deploy-updater-cloudrun.sh` - Deployment script for hourly updates
- `/scripts/setup-daily-hansard-import.sh` - Setup script for daily VM automation
- `/SCHEDULED_UPDATES_SETUP.md` - This documentation file
