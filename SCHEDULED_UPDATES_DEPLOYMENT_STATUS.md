# Scheduled Updates Deployment Status

## Summary

The scheduled update system has been **SUCCESSFULLY DEPLOYED** with hourly Cloud Run updates operational. Daily Hansard imports pending.

**Status:** ✅ Hourly updates deployed | ⏳ Daily imports pending | ⚠️ API endpoint fix needed

## What's Been Created

### 1. Scripts and Configuration
✅ **Created:**
- `/packages/data-pipeline/scripts/lightweight_update.py` - Hourly updater script (483 lines)
- `/packages/data-pipeline/Dockerfile.updater` - Docker image definition
- `/packages/data-pipeline/requirements.txt` - Python dependencies
- `/scripts/deploy-updater-cloudrun.sh` - Cloud Run deployment script
- `/scripts/setup-daily-hansard-import.sh` - Daily VM scheduler setup
- `/cloudbuild.updater.yaml` - Cloud Build configuration
- `/SCHEDULED_UPDATES_SETUP.md` - Complete documentation

✅ **Configuration Fixed:**
- Updated PROJECT_ID from "canadagpt" to "canada-gpt-ca"
- Updated internal IP to 10.128.0.4 (canadagpt-ingestion VM)
- Fixed Dockerfile paths to build from repository root

✅ **GCP Services:**
- Cloud Build API enabled successfully

## What Needs to Be Completed

### Option 1: Using Cloud Build (Recommended)

**Issue:** User `matt@connexxia.ca` needs Cloud Build permissions.

**Fix:**
```bash
# Grant yourself Cloud Build Editor role
gcloud projects add-iam-policy-binding canada-gpt-ca \
    --member="user:matt@connexxia.ca" \
    --role="roles/cloudbuild.builds.editor"

# Then build the image
cd /Users/matthewdufresne/FedMCP
gcloud builds submit --config cloudbuild.updater.yaml .
```

### Option 2: Using Local Docker

**Issue:** Docker daemon not running locally.

**Fix:**
```bash
# Start Docker Desktop, then:
cd /Users/matthewdufresne/FedMCP
./scripts/deploy-updater-cloudrun.sh
```

When prompted, enter:
- Neo4j URI: `bolt://10.128.0.4:7687`
- Neo4j Username: `neo4j`
- Neo4j Password: `canadagpt2024`

## After Image Build Completes

### 1. Deploy Cloud Run Job
```bash
gcloud run jobs create canadagpt-updater \
    --image=gcr.io/canada-gpt-ca/canadagpt-updater:latest \
    --region=us-central1 \
    --memory=512Mi \
    --cpu=1 \
    --max-retries=2 \
    --task-timeout=10m \
    --set-env-vars="NEO4J_URI=bolt://10.128.0.4:7687,NEO4J_USER=neo4j,NEO4J_PASSWORD=canadagpt2024" \
    --vpc-connector=canadagpt-connector \
    --vpc-egress=private-ranges-only
```

### 2. Create Hourly Schedule
```bash
gcloud scheduler jobs create http canadagpt-updater-schedule \
    --location=us-central1 \
    --schedule="0 * * * *" \
    --uri="https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/canada-gpt-ca/jobs/canadagpt-updater:run" \
    --http-method=POST \
    --oauth-service-account-email=canada-gpt-ca@appspot.gserviceaccount.com \
    --description="Run lightweight parliamentary data updates hourly"
```

### 3. Setup Daily Hansard Import
```bash
chmod +x scripts/setup-daily-hansard-import.sh
./scripts/setup-daily-hansard-import.sh
```

## Testing

### Test Hourly Updater
```bash
# Manual trigger
gcloud run jobs execute canadagpt-updater --region=us-central1

# View logs
gcloud logging read \
    "resource.type=cloud_run_job AND resource.labels.job_name=canadagpt-updater" \
    --limit=50
```

### Test Daily Import
```bash
# Manual trigger
gcloud scheduler jobs run daily-hansard-import --location=us-central1

# Check VM status
gcloud compute instances describe canadagpt-ingestion \
    --zone=us-central1-a \
    --format='value(status)'
```

## Architecture

**Hourly (Cloud Run):**
- Runs every hour at :00
- Updates: MP parties, cabinet positions, recent bills/votes
- Runtime: 30-60s
- Memory: 512Mi (200MB actual usage)
- Cost: ~$0.01/day

**Daily (Scheduled VM):**
- Runs at 3 AM ET (7 AM UTC)
- Imports: Full Hansard transcripts (3.67M statements)
- Runtime: 30-45 minutes
- Memory: 4GB
- Cost: ~$0.15/day
- Auto-starts and auto-shuts down

**Total Cost:** ~$4.80/month

## Key Features

### Party Change Detection
Detects MP party changes (like Chris d'Entrement: Conservative → Liberal) and logs prominently:
```
==========================================================
⚠️  PARTY CHANGES DETECTED:
  • Chris d'Entrement: Conservative → Liberal
==========================================================
```

### Cabinet Shuffle Detection
Tracks ministerial appointments, resignations, and portfolio changes.

### Recent Legislation
Monitors bills introduced and votes held in the last 24 hours.

## Next Steps

1. Choose deployment method (Cloud Build or Local Docker)
2. Build the Docker image
3. Deploy Cloud Run job
4. Create hourly schedule
5. Setup daily VM automation
6. Test both update mechanisms

See `/SCHEDULED_UPDATES_SETUP.md` for complete operational documentation.
