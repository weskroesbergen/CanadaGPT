# Check Data Freshness

This skill validates that production data is up-to-date and ingestion jobs are functioning correctly.

## Overview

Queries Neo4j database to check when data was last updated and alerts if data is stale based on the parliamentary calendar.

## Data Freshness Checks

### 1. Connect to Production Database

```bash
# Open SSH tunnel to Neo4j VM
./scripts/dev-tunnel.sh &

# Set connection variables
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USERNAME=neo4j
export NEO4J_PASSWORD=canadagpt2024
```

### 2. Check Hansard Debates

Most recent House debates:

```bash
NEO4J_URI=bolt://localhost:7687 \
NEO4J_USERNAME=neo4j \
NEO4J_PASSWORD=canadagpt2024 \
cypher-shell "
MATCH (d:Document)
RETURN d.date, d.id, d.number, count{(d)<-[:PART_OF]-(s:Statement)} as statements
ORDER BY d.date DESC
LIMIT 10
"
```

**Expected:**
- Latest debate within 1-2 days of most recent sitting
- Hansard typically published 1-2 days after sitting day
- 100-300 statements per debate

**Alert if:**
- No debates in last 7 days during sitting weeks
- Most recent debate is >3 days old during active parliament

### 3. Check Vote Records

Most recent parliamentary votes:

```bash
cypher-shell "
MATCH (v:Vote)
RETURN v.vote_number, v.date_time, v.subject, v.result
ORDER BY v.date_time DESC
LIMIT 10
"
```

**Expected:**
- Votes occur on sitting days (typically Mon-Thu)
- Multiple votes per sitting day (5-15 common)

**Alert if:**
- No votes in last 14 days during sitting weeks

### 4. Check Committee Activity

Recent committee meetings:

```bash
cypher-shell "
MATCH (m:Meeting)
RETURN m.committee_code, m.date, m.subject, m.status
ORDER BY m.date DESC
LIMIT 15
"
```

Recent committee evidence:

```bash
cypher-shell "
MATCH (ce:CommitteeEvidence)
RETURN ce.committee_code, ce.meeting_number, ce.date,
       count{(ce)<-[:GIVEN_IN]-(t:CommitteeTestimony)} as testimonies
ORDER BY ce.date DESC
LIMIT 10
"
```

**Expected:**
- Committee meetings scheduled/held regularly during sitting weeks
- Evidence published 1-3 days after meeting
- 20-100 testimonies per evidence document

**Alert if:**
- No new meetings in last 7 days during sitting weeks
- Meetings scheduled but evidence not imported after 5 days

### 5. Check MP Data

MP records last updated:

```bash
cypher-shell "
MATCH (mp:MP)
RETURN count(mp) as total_mps,
       count(CASE WHEN mp.current_party IS NOT NULL THEN 1 END) as with_party,
       count(CASE WHEN mp.current_riding IS NOT NULL THEN 1 END) as with_riding
"
```

**Expected:**
- 338 MPs (current House size)
- All MPs have current_party and current_riding
- Photos available for most MPs

**Alert if:**
- Total MPs ≠ 338
- MPs missing party or riding data
- New MPs not in database (check recent by-elections)

### 6. Check Lobbying Data

Lobbying registry freshness:

```bash
cypher-shell "
MATCH (lr:LobbyRegistration)
WITH lr ORDER BY lr.initial_filing_date DESC LIMIT 1
RETURN lr.initial_filing_date as most_recent_registration
"

cypher-shell "
MATCH (lc:LobbyCommunication)
WITH lc ORDER BY lc.communication_date DESC LIMIT 1
RETURN lc.communication_date as most_recent_communication
"

cypher-shell "
MATCH (lr:LobbyRegistration)
RETURN count(lr) as total_registrations
"
```

**Expected:**
- 163K+ registrations
- 343K+ communications
- Most recent data within 1 week (weekly refresh)

**Alert if:**
- Last refresh >14 days ago
- Significant drop in total counts (indicates failed import)

### 7. Check MP Expenses

Latest expense data:

```bash
cypher-shell "
MATCH (e:MPExpense)
RETURN e.fiscal_year, e.quarter, count(*) as records
ORDER BY e.fiscal_year DESC, e.quarter DESC
LIMIT 5
"
```

**Expected:**
- Current fiscal year + quarter available
- ~1,500 records per quarter (338 MPs × 4 categories)
- Quarterly data published ~45 days after quarter end

**Alert if:**
- Missing current quarter (after publication deadline)
- Fewer than 1,000 records for recent quarter

### 8. Check SPOKE_AT Relationships

Verify MP-to-Document/Evidence linkages:

```bash
# Hansard SPOKE_AT
cypher-shell "
MATCH (mp:MP)-[r:SPOKE_AT]->(d:Document)
WHERE d.date >= date('2024-11-01')
RETURN count(DISTINCT mp) as unique_mps,
       count(r) as total_spoke_at_relations,
       count(DISTINCT d) as debates_covered
"

# Committee SPOKE_AT
cypher-shell "
MATCH (mp:MP)-[r:SPOKE_AT]->(ce:CommitteeEvidence)
WHERE ce.date >= date('2024-11-01')
RETURN count(DISTINCT mp) as unique_mps,
       count(r) as total_spoke_at_relations,
       count(DISTINCT ce) as evidence_docs_covered
"
```

**Expected:**
- High MP participation (100+ unique MPs speaking per month)
- Multiple SPOKE_AT relations per debate/evidence

**Alert if:**
- Very low unique MP count (indicates linking failure)
- SPOKE_AT relations missing for recent debates

## Parliamentary Calendar Context

### Sitting Weeks vs. Constituency Weeks

Check House calendar to determine expectations:

```bash
# Fetch current House calendar
curl -s "https://www.ourcommons.ca/en/sitting-calendar" | grep -A 5 "sitting-week"
```

**Sitting weeks:** Parliament in session (Mon-Thu typically)
- Expect daily debates, votes, committee meetings

**Constituency weeks:** Parliament adjourned
- No debates or votes
- Minimal committee activity
- Data staleness is normal

**Summer/Winter breaks:**
- Extended adjournments (weeks/months)
- Only urgent recalls generate data

### By-elections

Check for recent by-elections:

```bash
# List MPs with recent start dates
cypher-shell "
MATCH (mp:MP)
WHERE mp.elected_date >= date('2024-01-01')
RETURN mp.name, mp.current_party, mp.current_riding, mp.elected_date
ORDER BY mp.elected_date DESC
"
```

## Automated Health Check Script

Create a comprehensive check:

```python
#!/usr/bin/env python3
# scripts/check-data-freshness.py

from datetime import datetime, timedelta
from fedmcp_pipeline.utils.neo4j_client import Neo4jClient

neo4j = Neo4jClient(uri='bolt://localhost:7687', user='neo4j', password='canadagpt2024')

def check_debates():
    result = neo4j.run_query("""
        MATCH (d:Document)
        RETURN d.date ORDER BY d.date DESC LIMIT 1
    """)
    if result:
        latest = result[0]['d.date']
        days_old = (datetime.now().date() - datetime.fromisoformat(latest)).days
        print(f"✓ Latest Hansard: {latest} ({days_old} days old)")
        if days_old > 7:
            print(f"⚠️  WARNING: Debate data may be stale")
    else:
        print("✗ No debate data found!")

def check_votes():
    result = neo4j.run_query("""
        MATCH (v:Vote)
        RETURN v.date_time ORDER BY v.date_time DESC LIMIT 1
    """)
    if result:
        latest = result[0]['v.date_time']
        print(f"✓ Latest Vote: {latest}")
    else:
        print("✗ No vote data found!")

# Add checks for other data types...

if __name__ == "__main__":
    check_debates()
    check_votes()
    # ... more checks
```

## Integration with Monitoring

### Set Up Alerts

Use Cloud Monitoring to alert on:

```bash
# Create log-based metric for failed ingestion jobs
gcloud logging metrics create ingestion_failures \
  --description="Count of failed ingestion job executions" \
  --log-filter='resource.type="cloud_run_job" AND severity="ERROR"'

# Create alert policy
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Ingestion Job Failures" \
  --condition-threshold-value=1 \
  --condition-threshold-duration=300s
```

## Related Skills

- `/deploy-ingestion` - Redeploy jobs if data is stale
- `/debug-ingestion` - Troubleshoot pipeline issues

## Documentation

See `CLAUDE.md` for expected data volumes and publication schedules.
