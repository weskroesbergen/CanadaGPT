# Phase 2.2 Complete: Initial Data Load Setup

**Completed:** 2025-11-02

## Overview

Phase 2.2 prepared the infrastructure and tooling for initial data loading into Neo4j. While the actual data load requires a running Neo4j instance (which needs to be set up manually), all automation and documentation has been created to make the process straightforward.

## Files Created

### 1. Docker Compose Configuration (`docker-compose.yml`)
**Lines:** 50 | **Purpose:** Local Neo4j development environment

**Features:**
- Neo4j 5.14 Community Edition
- APOC plugin pre-configured
- Optimized memory settings for data loading
- Persistent volumes for data, logs, and imports
- Health checks and auto-restart
- Password: `canadagpt2024`
- Ports: 7474 (HTTP), 7687 (Bolt)

**Memory Configuration:**
```yaml
NEO4J_dbms_memory_pagecache_size=2G
NEO4J_dbms_memory_heap_initial__size=2G
NEO4J_dbms_memory_heap_max__size=4G
```

**Volumes:**
- `neo4j_data` - Database files (persistent)
- `neo4j_logs` - Log files
- `neo4j_import` - Import directory
- `neo4j_plugins` - APOC and other plugins
- Schema file mounted at `/var/lib/neo4j/import/schema.cypher`

---

### 2. Setup Script (`scripts/setup-neo4j.sh`)
**Lines:** 90 | **Purpose:** Automated Neo4j initialization

**What It Does:**
1. Checks if Docker is running
2. Starts Neo4j container via docker-compose
3. Waits for Neo4j to be healthy (up to 60 seconds)
4. Applies schema from `docs/neo4j-schema.cypher`
5. Displays connection details and next steps

**Usage:**
```bash
chmod +x scripts/setup-neo4j.sh
./scripts/setup-neo4j.sh
```

**Output:**
- Connection details (URI, username, password)
- Next steps for data loading
- Useful Docker commands

---

### 3. Comprehensive Setup Guide (`docs/NEO4J_SETUP.md`)
**Lines:** 300+ | **Purpose:** Complete Neo4j setup documentation

**Three Setup Options Covered:**

#### Option 1: Neo4j Aura (Cloud) ☁️
- **Best for:** Quick setup, no local installation
- **Time:** 5 minutes
- **Cost:** Free tier (2M nodes, 200K relationships)
- **Steps:** Create account → Save credentials → Apply schema → Configure pipeline

#### Option 2: Docker (Local) 🐳
- **Best for:** Full control, persistent local database
- **Time:** 10 minutes
- **Prerequisites:** Docker Desktop
- **Steps:** Run setup script → Configure .env → Test connection

#### Option 3: Neo4j Desktop (GUI) 🖥️
- **Best for:** Visual exploration, query building
- **Time:** 15 minutes
- **Steps:** Download Desktop → Create database → Apply schema → Configure

**Additional Sections:**
- Troubleshooting guide (connection errors, auth errors, memory issues)
- Comparison table of all three options
- Production setup notes (GCP deployment)

---

## Data Pipeline Package Review

The data pipeline package (`packages/data-pipeline`) was created in Phase 2.1 and is ready for use:

### Package Structure
```
packages/data-pipeline/
├── fedmcp_pipeline/
│   ├── cli.py                     # Command-line interface
│   ├── ingest/
│   │   ├── parliament.py          # MPs, bills, votes, debates
│   │   ├── lobbying.py            # Lobbying registry data
│   │   └── finances.py            # MP expenses
│   ├── relationships/
│   │   ├── political.py           # MP→Party, MP→Riding
│   │   ├── legislative.py         # Bill→Sponsor, Vote→MP
│   │   ├── lobbying.py            # Lobbyist→Organization
│   │   └── financial.py           # MP→Expense
│   └── utils/
│       ├── config.py              # Configuration management
│       ├── neo4j_client.py        # Neo4j connection wrapper
│       └── progress.py            # Progress bars and logging
├── pyproject.toml                 # Package configuration
├── .env.example                   # Environment template
└── README.md                      # Package documentation
```

### CLI Commands Available

```bash
# Test connection and show database stats
canadagpt-ingest --test

# Run full pipeline (all data + relationships)
canadagpt-ingest --full

# Ingest only parliamentary data
canadagpt-ingest --parliament

# Ingest only lobbying data
canadagpt-ingest --lobbying

# Ingest only financial data
canadagpt-ingest --finances

# Build relationships only (assumes data loaded)
canadagpt-ingest --relationships

# Validate configuration
canadagpt-ingest --validate
```

### Environment Variables

Create `packages/data-pipeline/.env`:
```bash
# Neo4j Connection (Required)
NEO4J_URI=bolt://localhost:7687  # or neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here

# CanLII API (Optional - for legal data)
CANLII_API_KEY=your_api_key_here

# Pipeline Configuration (Optional)
BATCH_SIZE=10000                  # Nodes per transaction
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
INCREMENTAL_LOOKBACK_DAYS=7       # For incremental updates
```

---

## Data Sources and Expected Data Volume

### Parliamentary Data (`--parliament`)
**Estimated Time:** 30-45 minutes
**Data Sources:**
- OpenParliament API (https://api.openparliament.ca)
- LEGISinfo (https://parl.ca/LegisInfo)

**Expected Nodes:**
- MPs: ~1,500 (current + historical)
- Parties: ~10
- Ridings: ~338
- Bills: ~10,000
- Votes: ~5,000
- Debates: ~50,000
- Committees: ~30

**Expected Relationships:**
- MEMBER_OF (MP→Party): ~1,500
- REPRESENTS (MP→Riding): ~1,500
- SPONSORED (MP→Bill): ~10,000
- VOTED_ON (MP→Vote): ~1M
- SPOKE_IN (MP→Debate): ~500K

---

### Lobbying Data (`--lobbying`)
**Estimated Time:** 20-30 minutes
**Data Source:**
- Office of the Commissioner of Lobbying (lobbycanada.gc.ca)

**Expected Nodes:**
- Lobbyists: ~15,000
- Organizations: ~8,000
- LobbyRegistrations: ~100,000
- LobbyCommunications: ~350,000

**Expected Relationships:**
- WORKS_FOR (Lobbyist→Organization): ~15,000
- LOBBIES_FOR (Lobbyist→Registration): ~100,000
- COMMUNICATED_WITH (Lobbyist→MP): ~350,000

---

### Financial Data (`--finances`)
**Estimated Time:** 15-20 minutes
**Data Source:**
- House of Commons Proactive Disclosure

**Expected Nodes:**
- Expenses: ~50,000 (quarterly since 2020)
- Contracts: ~10,000
- Grants: ~5,000

**Expected Relationships:**
- INCURRED (MP→Expense): ~50,000
- AWARDED (MP→Contract): ~10,000
- RECEIVED (Organization→Grant): ~5,000

---

### Full Pipeline (`--full`)
**Estimated Time:** 4-6 hours
**Total Expected:**
- **Nodes:** ~1.6M
- **Relationships:** ~10M

**Breakdown:**
1. Ingest parliament data (30-45 min)
2. Ingest lobbying data (20-30 min)
3. Ingest financial data (15-20 min)
4. Build political relationships (5 min)
5. Build legislative relationships (30-60 min)
6. Build lobbying network (45-90 min)
7. Build financial flows (15-30 min)

---

## Installation Steps

### 1. Set Up Neo4j

Choose one option from `docs/NEO4J_SETUP.md`:
- **Quick:** Neo4j Aura (5 min)
- **Local:** Docker (10 min)
- **GUI:** Neo4j Desktop (15 min)

### 2. Install FedMCP Package (Dependency)

The pipeline uses FedMCP clients to fetch data:
```bash
cd /Users/matthewdufresne/FedMCP
pip install -e packages/fedmcp
```

### 3. Install Pipeline Package

```bash
pip install -e packages/data-pipeline
```

Installs dependencies:
- `neo4j` (Python driver)
- `python-dotenv` (Environment variables)
- `tqdm` (Progress bars)
- `loguru` (Better logging)

### 4. Configure Environment

```bash
cd packages/data-pipeline
cp .env.example .env
# Edit .env with your Neo4j credentials
```

### 5. Test Connection

```bash
canadagpt-ingest --test
```

Expected output:
```
🔍 Testing Neo4j connection...

✅ Connection successful!
Server: Neo4j 5.14.0 (community)
Total nodes: 0
Total relationships: 0
```

---

## Running the Initial Data Load

### Recommended Sequence

**For Development/Testing (Quick):**
```bash
# Load parliament data only (~30 minutes)
canadagpt-ingest --parliament
```

This gives you enough data to test the GraphQL API and frontend without waiting 4-6 hours.

**For Full Dataset:**
```bash
# Full pipeline (~4-6 hours)
canadagpt-ingest --full
```

### Monitoring Progress

The pipeline shows real-time progress:
```
🚀 Starting FULL PIPELINE
Neo4j URI: bolt://localhost:7687
Batch size: 10,000

📥 Ingesting MPs from OpenParliament...
Found 1,500 MPs
Batching: 100%|████████████████| 1500/1500 [00:05<00:00, 300 nodes/s]
✅ Created 1,500 MPs

📥 Ingesting Bills from OpenParliament...
Found 10,000 bills
Batching: 100%|████████████████| 10000/10000 [00:30<00:00, 333 nodes/s]
✅ Created 10,000 Bills

...

========================================
✅ FULL PIPELINE COMPLETE
Total nodes: 1,600,000
Total relationships: 10,000,000

Top node types:
  Vote: 1,000,000
  Debate: 500,000
  LobbyCommunication: 350,000
  LobbyRegistration: 100,000
  Bill: 10,000
  ...
========================================
```

### Verification Queries

After data load, run these Cypher queries in Neo4j Browser:

```cypher
// Count all nodes by label
MATCH (n)
RETURN labels(n)[0] AS label, count(n) AS count
ORDER BY count DESC

// Count all relationships by type
MATCH ()-[r]->()
RETURN type(r) AS relationship, count(r) AS count
ORDER BY count DESC

// Check current MPs
MATCH (m:MP {current: true})
RETURN m.name, m.party, m.riding
LIMIT 10

// Check recent bills
MATCH (b:Bill)
WHERE b.introduced_date IS NOT NULL
RETURN b.number, b.title, b.introduced_date
ORDER BY b.introduced_date DESC
LIMIT 10

// Check lobbying activity
MATCH (l:Lobbyist)-[:LOBBIES_FOR]->(r:LobbyRegistration)
RETURN l.name, count(r) AS registrations
ORDER BY registrations DESC
LIMIT 10
```

---

## Troubleshooting

### Import Errors

**"ModuleNotFoundError: No module named 'fedmcp'"**
- Install FedMCP package first: `pip install -e packages/fedmcp`

**"Connection refused"**
- Ensure Neo4j is running
- Check URI in .env file
- Test with: `canadagpt-ingest --test`

### Performance Issues

**Slow data loading**
- Increase batch size: `canadagpt-ingest --full --batch-size 20000`
- Increase Neo4j memory in docker-compose.yml

**Out of memory errors**
- Reduce batch size: `--batch-size 5000`
- Increase Neo4j heap size in Docker or Desktop settings

### Data Quality Issues

**Missing data**
- Check API responses (some government APIs have rate limits)
- Re-run specific ingesters: `canadagpt-ingest --parliament`

**Duplicate data**
- Schema constraints prevent duplicates
- If needed, clear database: `docker-compose down -v`

---

## Next Steps

Once data load is complete:

1. **Verify Data**
   - Run verification queries in Neo4j Browser
   - Check node and relationship counts

2. **Test GraphQL API**
   - Start GraphQL API: `cd packages/graph-api && npm run dev`
   - Open GraphQL Playground: http://localhost:4000
   - Test queries against loaded data

3. **Test Frontend**
   - Start frontend: `cd packages/frontend && npm run dev`
   - Open browser: http://localhost:3000
   - Verify pages load with real data

4. **Deploy to GCP (Phase 3.2 & 4.4)**
   - Deploy GraphQL API to Cloud Run
   - Deploy frontend to Cloud Run
   - Connect to production Neo4j Aura

---

## Status Summary

**✅ Completed:**
- Docker Compose configuration for local Neo4j
- Automated setup script
- Comprehensive Neo4j setup guide
- Environment configuration templates
- Data pipeline package ready

**⏸️ Pending (User Action Required):**
- Set up Neo4j instance (Aura, Docker, or Desktop)
- Install pipeline package
- Run initial data load

**Recommended Next Action:**
1. Choose Neo4j setup option from `docs/NEO4J_SETUP.md`
2. Follow setup steps for chosen option
3. Run `canadagpt-ingest --test` to verify connection
4. Run `canadagpt-ingest --parliament` for quick test load
5. Run `canadagpt-ingest --full` for complete dataset

**Time to Beta:**
- If using `--parliament` only: Ready to test GraphQL/frontend in ~30 minutes
- If using `--full`: Ready to test GraphQL/frontend in ~4-6 hours

---

## Files Modified/Created in Phase 2.2

```
/Users/matthewdufresne/FedMCP/
├── docker-compose.yml                          # ✨ NEW - Neo4j container config
├── scripts/
│   └── setup-neo4j.sh                          # ✨ NEW - Automated setup script
└── docs/
    └── NEO4J_SETUP.md                          # ✨ NEW - Comprehensive setup guide
```

**Total New Files:** 3
**Total Lines:** ~440 lines
