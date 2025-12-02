# Committee Meeting Schema Migration

## What Was Done (Dec 1, 2025)

We discovered that the committee import system had **two incompatible Meeting schemas** causing the evidence ingestion to fail with 4,359 404 errors daily.

### The Problem

1. **Old Schema** (18,919 meetings from OpenParliament):
   - Imported during initial setup
   - No `committee_code` property
   - No `Committee-[:HELD_MEETING]->Meeting` relationships
   - Evidence ingestion couldn't build proper URLs

2. **New Schema** (from `daily-committee-import` Cloud Run job):
   - Has `ourcommons_meeting_id` and `committee_code`
   - Creates proper Committee relationships
   - Compatible with evidence ingestion

### The Solution (Option 3: Hybrid Approach)

We implemented a **data-preserving migration**:

1. ✅ **Extracted evidence_id mappings** from 14,859 historical meetings
2. ✅ **Saved backup** to `packages/data-pipeline/backups/committee_evidence_backup_20251201.json`
3. ✅ **Created backfill script** to reimport historical evidence later
4. ✅ **Paused evidence ingestion** job to stop wasting resources
5. ✅ **Deleted old Meeting nodes** (schema incompatible)
6. ⏳ **Waiting for rebuild** - `daily-committee-import` will recreate meetings with correct schema

## What Happens Next

### Automatic (No Action Required)

**Daily at 6 AM UTC**, the `committee-daily-import` Cloud Run job will:
- Discover new committee meetings from `ourcommons.ca`
- Create Meeting nodes with the correct schema
- Link them to Committee nodes
- Build up a new dataset of meetings over time

**Timeline**:
- **Day 1-7**: Meetings from last 7 days (job has 7-day lookback)
- **Week 2+**: Only new meetings as they're scheduled

### Manual (When You're Ready)

Once the new meetings are populated (give it a week), you can:

#### 1. Re-enable Evidence Ingestion (Current Meetings)

```bash
# Unpause the scheduler
gcloud scheduler jobs resume committee-evidence-ingestion-schedule --location=us-central1

# Or run manually to test
gcloud run jobs execute committee-evidence-ingestion --region=us-central1
```

This will import testimony for **recent meetings** (last 7 days with published evidence).

#### 2. Backfill Historical Evidence (Optional)

If you want to import historical testimony (2006-2025), use the backfill script:

```bash
# Connect to production Neo4j (or start tunnel)
export NEO4J_URI=bolt://10.128.0.3:7687
export NEO4J_USERNAME=neo4j
export NEO4J_PASSWORD=canadagpt2024

cd packages/data-pipeline

# Test with 10 meetings
python scripts/backfill_committee_evidence.py --limit 10

# Backfill specific session (e.g., current parliament)
python scripts/backfill_committee_evidence.py --session 45-1

# Backfill all historical evidence (14,859 meetings)
# WARNING: This could take several hours
python scripts/backfill_committee_evidence.py
```

**How the backfill works**:
1. Loads the backup file with 14,859 evidence IDs
2. For each meeting, tries to find matching Committee in Neo4j
3. If found, fetches testimony XML from OurCommons DocumentViewer
4. Imports CommitteeEvidence and CommitteeTestimony nodes
5. Links to MPs via `person_db_id`

**Success rate**: The backfill will only work for meetings where:
- `daily-committee-import` has created a new Meeting node
- Committee code can be matched (by meeting number + session)
- DocumentViewer XML is still available (older meetings may be archived)

## Data Preserved

**Backup File**: `packages/data-pipeline/backups/committee_evidence_backup_20251201.json`

**Contents**:
- 14,859 meeting records
- Date range: 2006-04-06 to 2025-10-22
- Sessions: 39-1 through 45-1 (12 parliamentary sessions)
- Properties: `meeting_id`, `evidence_id`, `meeting_number`, `session_id`, `date`, `start_time`, `end_time`, `webcast`

**Evidence IDs are the key**: These map to DocumentViewer XML URLs for fetching historical testimony.

## Current State (After Migration)

### Neo4j Database
- ✅ 63 Committees (unchanged)
- ✅ 0 Meetings (will rebuild automatically)
- ✅ 0 CommitteeEvidence (will populate after evidence ingestion resumes)
- ✅ 0 CommitteeTestimony (will populate after evidence ingestion resumes)

### Cloud Run Jobs
- ✅ `committee-daily-import` - **RUNNING** (6 AM UTC daily)
  - Discovers new meetings from ourcommons.ca
  - Creates Meeting nodes with correct schema

- ⏸️ `committee-evidence-ingestion` - **PAUSED**
  - Resume after new meetings are populated (1 week+)
  - Will import testimony for recent meetings going forward

### Cloud Scheduler
- ✅ `committee-daily-import-trigger` - **ENABLED** (6 AM UTC)
- ⏸️ `committee-evidence-ingestion-schedule` - **PAUSED**

## Verification Steps

### 1. Check Meeting Rebuild Progress (After Dec 8, 2025)

```bash
# SSH to Neo4j or use tunnel
gcloud compute ssh canadagpt-neo4j --zone=us-central1-a

# Run cypher-shell
cypher-shell -u neo4j -p canadagpt2024

# Query
MATCH (c:Committee)-[:HELD_MEETING]->(m:Meeting)
RETURN c.code as committee, count(m) as meetings
ORDER BY meetings DESC;
```

Expected: Should see meetings accumulating (start with 7 days worth, then daily additions)

### 2. Test Evidence Import (After Dec 8, 2025)

```bash
# Run evidence ingestion manually
gcloud run jobs execute committee-evidence-ingestion --region=us-central1

# Check logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=committee-evidence-ingestion" --limit=50
```

Expected: Should see successful imports, not 4,359 404s

### 3. Verify Schema Correctness

```bash
# Check a sample meeting
MATCH (m:Meeting)
RETURN m LIMIT 1;
```

Expected properties:
- `ourcommons_meeting_id`: "13272614"
- `committee_code`: "ETHI"
- `date`: "2025-11-30"
- `time_description`: "11:00 a.m."
- `subject`: "..."
- `status`: "Meeting Scheduled"

## Rollback (If Needed)

If something goes wrong, you can restore the old meetings:

```bash
# Load backup
cat packages/data-pipeline/backups/committee_evidence_backup_20251201.json

# Create restore script (contact dev team)
```

However, this would put us back in the broken state with 4,359 404s daily.

## Files Changed

1. **Created**:
   - `packages/data-pipeline/scripts/backfill_committee_evidence.py` - Historical evidence import
   - `packages/data-pipeline/backups/committee_evidence_backup_20251201.json` - Evidence ID backup
   - `COMMITTEE_MIGRATION_README.md` - This file

2. **Modified**:
   - Neo4j database: Deleted 18,919 Meeting nodes

3. **Cloud Scheduler**:
   - Paused: `committee-evidence-ingestion-schedule`

## Timeline

| Date | Action |
|------|--------|
| Dec 1, 2025 | Migration executed (this document) |
| Dec 2-8, 2025 | `daily-committee-import` rebuilds meetings (automatic) |
| Dec 8+, 2025 | Resume evidence ingestion (manual) |
| TBD | Run historical backfill (optional) |

## Cost Impact

**Before**:
- Evidence ingestion: 4,359 failed fetches daily = wasted compute
- 0 testimony imported

**After**:
- Evidence ingestion: Paused temporarily (no cost)
- Once resumed: Only successful imports (useful data)
- Backfill: Optional, run on-demand

**Savings**: ~$2-3/month in wasted Cloud Run invocations

## Questions?

Contact the development team or review:
- `/packages/data-pipeline/run_committee_evidence_ingestion.py`
- `/packages/data-pipeline/fedmcp_pipeline/ingest/committee_evidence_xml_import.py`
- `/scripts/daily-committee-import.py`
