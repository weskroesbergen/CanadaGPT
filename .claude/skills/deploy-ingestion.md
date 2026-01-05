# Deploy Ingestion Jobs

This skill deploys all CanadaGPT data ingestion jobs to Google Cloud Run.

## Overview

Deploys containerized Python jobs that import parliamentary data into Neo4j on scheduled intervals.

## Ingestion Jobs

### 1. Hansard Daily Import

**Purpose:** Import House of Commons debate transcripts

```bash
./scripts/deploy-hansard-importer.sh
```

**Schedule:** Daily at 4:00 AM ET (9:00 AM UTC)
**Runtime:** ~5-10 minutes
**Memory:** 2Gi
**Timeout:** 30 minutes

**What it imports:**
- Hansard debate XML (7-day lookback)
- Statements linked to MPs
- SPOKE_AT relationships

**Verify:**
```bash
# Check latest execution
gcloud run jobs executions list --job=hansard-daily-import --region=us-central1 --limit=5

# View logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=hansard-daily-import" --limit=50
```

### 2. Committee Daily Import

**Purpose:** Discover and import scheduled committee meetings

```bash
./scripts/deploy-committee-importer.sh
```

**Schedule:** Daily at 6:00 AM ET (11:00 AM UTC)
**Runtime:** ~2-3 minutes
**Memory:** 2Gi

**What it imports:**
- Meeting metadata (committee code, date, subject, status)
- Webcast availability

### 3. MP Ingestion

**Purpose:** Import MP biographical data, ridings, parties, committee memberships

```bash
./scripts/deploy-mp-ingestion.sh
```

**Schedule:** Daily at 6:00 AM UTC
**Runtime:** ~3-5 minutes
**Memory:** 2Gi

**What it imports:**
- MP profiles (name, party, riding, photo URL)
- Committee memberships with roles
- Party affiliations

### 4. Votes Ingestion

**Purpose:** Import parliamentary votes and ballots

```bash
./scripts/deploy-votes-ingestion.sh
```

**Schedule:** Daily at 7:00 AM UTC
**Runtime:** ~5-8 minutes
**Memory:** 2Gi

**What it imports:**
- Vote records (subject, result, date)
- Individual MP ballots (yea/nay/paired)
- Bill linkages

### 5. Committee Evidence Ingestion

**Purpose:** Import witness testimony from committee meetings

```bash
./scripts/deploy-committee-importer.sh
```

**Schedule:** Daily at 8:00 AM UTC
**Runtime:** ~5-10 minutes
**Memory:** 2Gi

**What it imports:**
- CommitteeEvidence nodes
- CommitteeTestimony (witness/MP speeches)
- SPOKE_AT relationships

### 6. Lobbying Registry

**Purpose:** Full refresh of lobbying data

```bash
./scripts/deploy-lobbying-ingestion.sh
```

**Schedule:** Weekly Sundays at 2:00 AM UTC
**Runtime:** ~5 minutes
**Memory:** 4Gi
**CPU:** 2 cores

**What it imports:**
- 163K+ lobby registrations
- 343K+ lobby communications
- Organizations and lobbyists

### 7. MP Expenses Ingestion

**Purpose:** Import MP office and House Officer expenses

```bash
./scripts/deploy-expenses-ingestion.sh
```

**Schedule:** Daily at 5:00 AM UTC
**Runtime:** ~1-2 minutes
**Memory:** 2Gi

**What it imports:**
- Quarterly expense data (salaries, travel, hospitality, contracts)
- MP and House Officer expenses

## Deploy All Jobs

To deploy all ingestion jobs at once:

```bash
# Deploy all jobs
./scripts/deploy-hansard-importer.sh
./scripts/deploy-committee-importer.sh
./scripts/deploy-mp-ingestion.sh
./scripts/deploy-votes-ingestion.sh
./scripts/deploy-lobbying-ingestion.sh
./scripts/deploy-expenses-ingestion.sh
```

## Verify Cloud Scheduler

Check that all scheduled jobs are enabled:

```bash
# List all scheduler jobs
gcloud scheduler jobs list --location=us-central1

# Expected jobs:
# - hansard-daily-import-trigger
# - committee-daily-import-trigger
# - mp-ingestion-trigger
# - votes-ingestion-trigger
# - committee-evidence-ingestion-trigger
# - lobbying-ingestion-trigger (weekly)
# - expenses-ingestion-trigger
```

**Enable/disable schedulers:**
```bash
# Pause a job
gcloud scheduler jobs pause hansard-daily-import-trigger --location=us-central1

# Resume a job
gcloud scheduler jobs resume hansard-daily-import-trigger --location=us-central1
```

## Manual Triggers

Trigger jobs manually for testing or backfills:

```bash
# Trigger Hansard import now
gcloud run jobs execute hansard-daily-import --region=us-central1

# Trigger with custom args (if supported)
gcloud run jobs execute hansard-daily-import \
  --region=us-central1 \
  --args="--start-date=2024-11-01,--end-date=2024-11-30"

# Watch execution
gcloud run jobs executions describe EXECUTION_NAME --region=us-central1
```

## Monitoring

### Check Job Status

```bash
# List recent executions
gcloud run jobs executions list --job=hansard-daily-import --region=us-central1 --limit=10

# Get execution details
gcloud run jobs executions describe EXECUTION_NAME --region=us-central1
```

### View Logs

```bash
# Real-time logs during execution
gcloud logging tail "resource.type=cloud_run_job AND resource.labels.job_name=hansard-daily-import"

# Recent logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=hansard-daily-import" \
  --limit=100 \
  --format=json
```

### Check Data Freshness

After jobs run, verify data in Neo4j:

```bash
# Connect to Neo4j
./scripts/dev-tunnel.sh

# Query latest data
NEO4J_URI=bolt://localhost:7687 \
NEO4J_USERNAME=neo4j \
NEO4J_PASSWORD=canadagpt2024 \
cypher-shell "MATCH (d:Document) RETURN d.date ORDER BY d.date DESC LIMIT 5"
```

## Troubleshooting

### Job Fails

```bash
# Check execution logs
gcloud run jobs executions describe EXECUTION_NAME --region=us-central1

# Common issues:
# - Neo4j connection timeout → Check VPC connector
# - XML 404 errors → Verify source data availability
# - Memory exceeded → Increase memory allocation
# - Timeout → Increase timeout or optimize batch size
```

### Low MP Linking Rate

If Hansard import shows <80% MP linking:

1. Check for new MPs not in database
2. Update MP ingestion data
3. Add nickname mappings in `fedmcp_pipeline/ingest/hansard.py`

### Scheduler Not Triggering

```bash
# Check scheduler status
gcloud scheduler jobs describe hansard-daily-import-trigger --location=us-central1

# Check IAM permissions
gcloud run jobs get-iam-policy hansard-daily-import --region=us-central1

# Ensure service account has Cloud Run Invoker role
```

## Environment Variables

All jobs require:
- `NEO4J_URI`: `bolt://10.128.0.3:7687`
- `NEO4J_USERNAME`: `neo4j`
- `NEO4J_PASSWORD`: (from Secret Manager)
- `VPC_CONNECTOR`: `canadagpt-vpc-connector`

## Related Skills

- `/deploy-production` - Deploy main application services
- `/check-data-freshness` - Verify ingestion job results
- `/debug-ingestion` - Troubleshoot pipeline issues

## Documentation

- Data Pipeline: `packages/data-pipeline/README.md`
- Ingestion Details: `CLAUDE.md` (Data Pipeline section)
- Deployment Guide: `DEPLOYMENT.md`
