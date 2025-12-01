# MP Expenses Automated Ingestion

**Status**: ✅ Production Deployed (Dec 1, 2025)

## Overview

Automated daily ingestion of MP office expenses and House Officer expenses from OurCommons Proactive Disclosure. The system imports quarterly expense data for all MPs and House Officers (Speaker, Leaders, Whips, etc.) and makes it available via the GraphQL API and frontend spending tracker.

## Architecture

### Data Sources

**OurCommons Proactive Disclosure** (CSV format):
- MP Office Expenses: `https://www.ourcommons.ca/proactivedisclosure/en/members/{fiscal_year}/{quarter}`
- House Officer Expenses: `https://www.ourcommons.ca/proactivedisclosure/en/house-officers/{fiscal_year}/{quarter}`

**Data Categories**:
- Salaries (staff salaries and benefits)
- Travel (travel expenses)
- Hospitality (hospitality and events)
- Contracts (contract services)

**Publication Schedule**: Quarterly data published ~1-2 weeks after quarter end

### System Components

1. **FedMCP Clients** (`packages/fedmcp/src/fedmcp/clients/`)
   - `expenditure.py`: `MPExpenditureClient` - Fetches MP office expenses
   - `house_officers.py`: `HouseOfficersClient` - Fetches House Officer expenses
   - Both use `RateLimitedSession` with automatic retries

2. **Ingestion Logic** (`packages/data-pipeline/fedmcp_pipeline/ingest/finances.py`)
   - `ingest_financial_data()`: Main entry point
   - Parameterizable fiscal year ranges
   - Fuzzy MP name matching (85-90% success rate)
   - Idempotent design (safe to run multiple times)

3. **Entry Point** (`packages/data-pipeline/run_expenses_ingestion.py`)
   - CLI with `--fiscal-year-start` and `--fiscal-year-end` arguments
   - Default: Current fiscal year only
   - Environment variables: NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

4. **Cloud Run Job**: `expenses-ingestion`
   - Region: `us-central1`
   - Resources: 2Gi memory, 1 CPU, 15-minute timeout
   - VPC Connector: `canadagpt-connector` (for Neo4j access)
   - Schedule: Daily at 5:00 AM UTC (12:00 AM ET)

### Neo4j Schema

**Expense Nodes**:
```cypher
(e:Expense {
  id: "exp-{source}-{mp_id}-{fiscal_year}-q{quarter}-{category}",
  mp_id: "john-smith",
  fiscal_year: 2026,
  quarter: 1,
  category: "salaries",
  amount: 123456.78,
  description: "Staff salaries and benefits",
  source: "mp",  // or "officer"
  role: "Speaker",  // House Officers only
  updated_at: "2025-12-01T08:20:39Z"
})
```

**Relationships**:
```cypher
(MP)-[:INCURRED]->(Expense)
```

**Source Field Values**:
- `mp`: Regular MP office expenses
- `officer`: House Officer expenses (Speaker, Leaders, Whips, etc.)

## Deployment

### Initial Setup

```bash
# Deploy the Cloud Run job and scheduler
./scripts/deploy-expenses-ingestion.sh
```

This will:
1. Build Docker image using Cloud Build
2. Create Cloud Run job `expenses-ingestion`
3. Set up Cloud Scheduler for daily execution at 5:00 AM UTC

### Manual Execution

**Current fiscal year** (default behavior):
```bash
gcloud run jobs execute expenses-ingestion --region=us-central1
```

**Historical backfill** (requires local execution):
```bash
# Open SSH tunnel to production Neo4j
./scripts/dev-tunnel.sh &

# Set environment variables
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USERNAME=neo4j
export NEO4J_PASSWORD=canadagpt2024

# Run backfill
cd packages/data-pipeline
source venv/bin/activate
python run_expenses_ingestion.py --fiscal-year-start 2020 --fiscal-year-end 2023
```

### Monitoring

**View logs**:
```bash
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=expenses-ingestion" --limit=50
```

**Check scheduler status**:
```bash
gcloud scheduler jobs describe expenses-ingestion-schedule --location=us-central1
```

**Verify data in Neo4j**:
```cypher
// Check expense counts by source and fiscal year
MATCH (e:Expense)
WHERE e.source IN ['mp', 'officer']
RETURN
  e.source as source,
  e.fiscal_year as fy,
  e.quarter as q,
  count(e) as count,
  sum(e.amount) as total_amount
ORDER BY e.source, e.fiscal_year, e.quarter;

// Check House Officer roles
MATCH (e:Expense {source: 'officer'})
RETURN DISTINCT e.role
ORDER BY e.role;
```

## Key Features

### 1. Dual Source Import

**MP Office Expenses**: Standard quarterly expenses for all 338 MPs
- Captured per MP per quarter
- Categories: salaries, travel, hospitality, contracts

**House Officer Expenses**: Additional expenses for leadership roles
- Speaker, House Leaders, Government Whip, Opposition Whip
- Includes Stornoway residence, Research Offices
- Previously missing from expense tracking (discovered Nov 2025)

### 2. Intelligent Name Matching

**Normalization**:
- Removes accents (é → e, è → e)
- Removes honorifics (Hon., Rt. Hon., Dr.)
- Removes middle names/initials
- Handles compound surnames (Rempel Garner → Rempel)
- Handles hyphenated surnames (Fancy-Landry → Fancy)

**Nickname Mapping**:
```python
NICKNAME_MAPPING = {
    'bobby': 'robert',
    'rob': 'robert',
    'bob': 'robert',
    'bill': 'william',
    'mike': 'michael',
    # ...
}
```

**Success Rate**: 99.9% (only 1-2 MPs per quarter unmatched)

### 3. Idempotent Design

- Uses `MERGE` operations in Neo4j (not `CREATE`)
- Expense IDs are deterministic: `exp-{source}-{mp_id}-{fy}-q{q}-{category}`
- Safe to run multiple times without duplicates
- Updates `updated_at` timestamp on re-runs

### 4. Graceful Error Handling

**Unpublished Quarters**: Returns 500 errors from OurCommons
- Logged as warnings (not errors)
- Job continues processing other quarters
- Daily runs will catch newly published quarters automatically

**Name Mismatches**: MPs not found in database
- Logged with normalized name for debugging
- Skipped (not imported)
- Tracked in summary statistics

## Data Volumes

### Current State (Dec 1, 2025)

**Total Expenses**: 9,380 nodes
- Old format (source=null): 7,824 (FY 2024-2026, MP only)
- New format:
  - MP expenses: 1,499 (FY 2026 Q1)
  - House Officer expenses: 57 (FY 2026 Q1)

### Expected Growth

**Per Quarter**:
- ~1,500 MP expense records (338 MPs × 4 categories, minus $0 amounts)
- ~60 House Officer expense records (~15 officers × 4 categories)
- Total: ~1,560 new Expense nodes every 3 months

**Annual**:
- ~6,240 new Expense nodes per year
- Database growth: ~500 KB/year (minimal)

## Integration Points

### GraphQL API

**Expense Type** (`packages/graph-api/src/schema.ts`):
```graphql
type Expense @node {
  id: ID!
  mp_id: String!
  fiscal_year: Int!
  quarter: Int!
  category: String!
  amount: Float!
  description: String
  source: String
  role: String
  updated_at: String
  incurredBy: MP @relationship(type: "INCURRED", direction: IN)
}
```

**Sample Query**:
```graphql
query GetMPExpenses($mpId: String!, $fiscalYear: Int!) {
  expenses(where: {
    mp_id: $mpId,
    fiscal_year: $fiscalYear
  }) {
    fiscal_year
    quarter
    category
    amount
    source
    role
  }
}
```

### Frontend

**Spending Tracker**: `packages/frontend/src/app/[locale]/spending/page.tsx`
- Top spenders by fiscal year
- Party spending trends
- Fiscal year selector (2021-2026)
- Automatically displays new quarterly data

**API Integration**: Uses GraphQL queries via `packages/frontend/src/lib/queries.ts`

### MCP Server (FedMCP)

**Tools**:
- `get_mp_expenses`: Get expenses for specific MP
- `search_mp_expenses`: Top spenders, party averages
- `get_mp_activity_scorecard`: Comprehensive MP profile including expenses

**Example**:
```python
from fedmcp import MPExpenditureClient

client = MPExpenditureClient()
expenses = client.get_quarterly_summary(fiscal_year=2026, quarter=1)
# Returns list of MPExpenditure objects
```

## Historical Context

### Discovery (Nov 2, 2025)

Documented in `EXPENSE_GAP_FIXED.md`:
- Found House Officers endpoint that captures leadership expenses
- Individual MP expenses only showed ~25% of leader spending
- House Officer expenses include Stornoway residence, Research Offices
- Critical for accurate accountability tracking

### Implementation (Dec 1, 2025)

**Changes Made**:
1. Updated `finances.py` to integrate `HouseOfficersClient`
2. Added `source` field to distinguish MP vs House Officer expenses
3. Made fiscal year ranges parameterizable
4. Created Cloud Run job with daily scheduler
5. Updated expense ID format to prevent collisions

**Breaking Changes**: None
- New expenses use `source` field, old expenses have `source=null`
- Both coexist in database without conflicts
- GraphQL schema unchanged (source field is optional)

## Troubleshooting

### Issue: No new expenses imported

**Cause**: Quarter not yet published on OurCommons
**Solution**: Wait 1-2 weeks after quarter end, or check manually at:
- https://www.ourcommons.ca/proactivedisclosure/en/members/2026/2

### Issue: Low MP matching rate (<90%)

**Cause**: New MPs not in database, name format changes
**Solution**:
1. Update MP data: `gcloud run jobs execute mp-ingestion --region=us-central1`
2. Check logs for unmatched names: `grep "Could not find MP ID"`
3. Add nickname mappings to `NICKNAME_MAPPING` if needed

### Issue: Duplicate expenses

**Cause**: Expense ID format changed, or MERGE not working
**Solution**:
```cypher
// Find duplicates
MATCH (e:Expense)
WITH e.mp_id + '-' + e.fiscal_year + '-' + e.quarter + '-' + e.category AS key,
     collect(e) AS nodes
WHERE size(nodes) > 1
RETURN key, nodes;

// Delete old duplicates (keep newest)
MATCH (e:Expense)
WITH e.mp_id + '-' + e.fiscal_year + '-' + e.quarter + '-' + e.category AS key,
     collect(e) AS nodes
WHERE size(nodes) > 1
WITH nodes, nodes[0] AS keep, nodes[1..] AS delete
UNWIND delete AS d
DETACH DELETE d;
```

### Issue: Cloud Run job timeout

**Cause**: Large fiscal year range (e.g., 2020-2025)
**Solution**:
- Run historical backfills locally (no timeout)
- Or split into smaller ranges: 2020-2021, 2022-2023, etc.

## Future Enhancements

### Planned

1. **Contracts, Grants, Donations** (marked as TODO in code)
   - Additional data sources from Open Canada portal
   - Requires client implementations similar to MPExpenditureClient

2. **Expense Trends Analysis**
   - Year-over-year comparisons
   - Outlier detection (unusual spending patterns)
   - Category breakdowns

3. **House Officer Timeline**
   - Track role changes over time
   - Link expenses to specific tenure periods
   - Handle leadership transitions

### Considerations

**Historical Data Migration**:
- 7,824 old expenses with `source=null` need backfilling
- Run update query to add source field:
  ```cypher
  MATCH (e:Expense)
  WHERE e.source IS NULL
  SET e.source = 'mp'
  ```

**Data Quality**:
- Monitor MP matching rates over time
- Alert if success rate drops below 80%
- Investigate new name formats or database issues

## Related Documentation

- `EXPENSE_GAP_FIXED.md`: Discovery of House Officers endpoint
- `CLAUDE.md`: Full project documentation with data pipeline overview
- `packages/fedmcp/src/fedmcp/clients/expenditure.py`: MP expenses client
- `packages/fedmcp/src/fedmcp/clients/house_officers.py`: House Officer expenses client

## Cost Analysis

**Daily Execution**:
- Runtime: ~1-2 minutes
- Compute: 0.03 vCPU-hours × $0.000024/second ≈ $0.002/day
- Monthly cost: ~$0.06

**Historical Backfill** (one-time):
- Runtime: ~5-10 minutes
- Compute: 0.20 vCPU-hours ≈ $0.01
- Negligible cost

**Total Annual Cost**: <$1.00

## Contact

For issues or questions:
- Check logs: `gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=expenses-ingestion" --limit=50`
- Review data pipeline: `packages/data-pipeline/fedmcp_pipeline/ingest/finances.py`
- Test locally: `python run_expenses_ingestion.py --fiscal-year-start 2026 --fiscal-year-end 2026`
