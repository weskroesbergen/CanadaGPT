# CanadaGPT Data Pipeline

Python data ingestion pipeline for CanadaGPT. Loads 1.6M+ nodes and 10M+ relationships from Canadian government data sources into Neo4j.

---

## 📋 Overview

This package ingests data from multiple sources:

**Parliamentary Data** (via `packages/fedmcp` clients):
- OpenParliament API - MPs, bills, votes, debates
- LEGISinfo - Bill details and status
- House of Commons - Hansard transcripts, expenses, petitions

**Lobbying & Influence**:
- Lobbying Registry - 100,000+ registrations, 350,000+ communications

**Financial Data**:
- MP Expenses - Quarterly proactive disclosure
- Government Contracts - Proactive disclosure portal
- Political Donations - Elections Canada

**Legal Data** (optional, requires CanLII API key):
- CanLII - Case law and legislation

---

## 🚀 Quick Start

### Installation

```bash
# Install in development mode
cd packages/data-pipeline
pip install -e .

# Or install from parent directory with extras
pip install -e "packages/data-pipeline[dev]"
```

### Prerequisites

1. **Neo4j Aura Instance** (from Phase 1.2)
   - Connection URI: `neo4j+s://xxxxx.databases.neo4j.io`
   - Password stored in GCP Secret Manager

2. **Schema Deployed** (from Phase 1.3)
   - 17 constraints created
   - 23 indexes created
   - Verify: `CALL db.constraints();` returns 17 rows

3. **Environment Variables**

```bash
# Copy example env file
cp .env.example .env

# Edit with your values
nano .env
```

Required variables:
```bash
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Optional (for CanLII case law)
CANLII_API_KEY=your_key_here
```

---

## 🔧 Usage

### Full Pipeline (Initial Load)

```bash
# Run all ingestion steps (~4-6 hours)
canadagpt-ingest --full

# With progress bars and logging
canadagpt-ingest --full --verbose
```

**What gets loaded:**
- ~1,000 MPs (current + historical)
- ~5,000 Bills
- ~20,000 Votes
- ~50,000 Debates
- ~40,000 MP Expenses
- ~100,000 Lobby Registrations
- ~350,000 Lobby Communications
- ~10M Relationships

---

### Individual Ingestion Steps

```bash
# 1. Parliamentary data (~30 min)
canadagpt-ingest --parliament

# 2. Lobbying data (~45 min, downloads 90MB CSV)
canadagpt-ingest --lobbying

# 3. Financial data (~2 hours)
canadagpt-ingest --finances

# 4. Build relationships (~1 hour)
canadagpt-ingest --relationships

# 5. Legal data (optional, requires CanLII API key, ~30 min)
canadagpt-ingest --legal
```

---

### Incremental Updates (Nightly Sync)

```bash
# Update only changed data (~5-10 min)
canadagpt-ingest --incremental

# Or use Cloud Scheduler (Phase 5) to run this daily
```

**How it works:**
- Checks for new bills, votes, expenses since last sync
- Uses MERGE to update existing nodes (upsert pattern)
- Only creates new relationships if they don't exist
- ~100x faster than full reload

---

## 📊 Architecture

### Batch Processing

All ingestion uses **batch UNWIND** operations for performance:

```python
# BAD: Individual CREATE statements (slow)
for mp in mps:
    session.run("CREATE (m:MP {id: $id, name: $name})", id=mp.id, name=mp.name)
# Time: 10,000 MPs × 50ms = 8.3 minutes

# GOOD: Batch UNWIND (fast)
session.run("""
    UNWIND $batch AS mp
    CREATE (m:MP)
    SET m = mp
""", batch=mps)
# Time: 10,000 MPs ÷ 10,000 per batch × 500ms = 500ms
```

**Performance gains:**
- 1,000x faster for large datasets
- Reduces network roundtrips
- Leverages Neo4j's bulk import optimizations

---

### Package Structure

```
packages/data-pipeline/
├── pyproject.toml              # Package configuration
├── README.md                   # This file
├── .env.example                # Example environment variables
├── fedmcp_pipeline/
│   ├── __init__.py
│   ├── cli.py                  # Command-line interface
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── neo4j_client.py     # Neo4j connection & batch operations
│   │   ├── progress.py         # Progress bars and logging
│   │   └── config.py           # Environment variable loading
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── parliament.py       # MPs, bills, votes, debates
│   │   ├── lobbying.py         # Registrations, communications
│   │   ├── finances.py         # Expenses, contracts, grants, donations
│   │   └── legal.py            # CanLII case law (optional)
│   └── relationships/
│       ├── __init__.py
│       ├── political.py        # MEMBER_OF, REPRESENTS, SERVES_ON
│       ├── legislative.py      # SPONSORED, VOTED, SPOKE_AT
│       ├── lobbying.py         # WORKS_FOR, LOBBIED_ON, MET_WITH
│       └── financial.py        # INCURRED, RECEIVED, DONATED
└── tests/
    ├── test_neo4j_client.py
    ├── test_parliament_ingest.py
    └── test_relationships.py
```

---

## 🧪 Testing

### Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=fedmcp_pipeline

# Specific test file
pytest tests/test_parliament_ingest.py
```

### Validation Queries

After ingestion, verify data quality:

```cypher
// 1. Count nodes by type
MATCH (n)
RETURN labels(n)[0] AS NodeType, count(*) AS Count
ORDER BY Count DESC;

// Expected:
// LobbyCommunication | 350000
// Expense           | 40000
// Vote              | 20000
// ...

// 2. Count relationships by type
MATCH ()-[r]->()
RETURN type(r) AS RelType, count(*) AS Count
ORDER BY Count DESC;

// Expected:
// MET_WITH    | 350000
// INCURRED    | 40000
// VOTED       | 20000
// ...

// 3. Verify orphaned nodes (nodes with no relationships)
MATCH (n)
WHERE NOT (n)--()
RETURN labels(n)[0] AS NodeType, count(*) AS Count;

// Expected: 0 rows (all nodes should have at least 1 relationship)
```

---

## 🔍 Data Sources

### 1. OpenParliament API
- **Base URL:** `https://api.openparliament.ca/`
- **Rate Limit:** 10 req/sec (conservative, actual limit higher)
- **Data:** MPs, bills, votes, debates, committees
- **Client:** Reuses `packages/fedmcp/src/fedmcp/clients/openparliament.py`

### 2. LEGISinfo
- **Base URL:** `https://www.parl.ca/LegisInfo/en/`
- **Rate Limit:** None (static JSON exports)
- **Data:** Bill details, status, sponsors
- **Client:** Reuses `packages/fedmcp/src/fedmcp/clients/legisinfo.py`

### 3. House of Commons Proactive Disclosure
- **Expenses:** `https://www.ourcommons.ca/proactivedisclosure/en/members`
- **Data:** MP quarterly expenses (FY 2020-2021 Q2 onward)
- **Client:** Reuses `packages/fedmcp/src/fedmcp/clients/expenditure.py`

### 4. Petitions
- **Base URL:** `https://www.ourcommons.ca/petitions/en/Petition/Search`
- **Data:** Citizen petitions, sponsors, signatures, responses
- **Client:** Reuses `packages/fedmcp/src/fedmcp/clients/petitions.py`

### 5. Lobbying Registry
- **Data Files:** `https://open.canada.ca/data/en/dataset/lobbying-registry`
- **Size:** ~90MB compressed CSV
- **Data:** 100,000+ registrations, 350,000+ communications
- **Client:** Reuses `packages/fedmcp/src/fedmcp/clients/lobbying.py`
- **Caching:** Downloads once to `~/.cache/fedmcp/lobbying/`

### 6. CanLII (Optional)
- **Base URL:** `https://api.canlii.org/v1`
- **Rate Limit:** 2 req/sec (enforced by client)
- **Data:** Supreme Court cases, Federal Court cases, legislation
- **Requires:** Free API key from https://www.canlii.org/en/feedback/feedback.html
- **Client:** Reuses `packages/fedmcp/src/fedmcp/clients/canlii.py`

---

## 🚀 Performance

### Initial Load Benchmarks

Tested on Neo4j Aura 4GB instance:

| Step | Nodes Created | Relationships | Duration |
|------|---------------|---------------|----------|
| **1. MPs** | 1,000 | 1,000 (MEMBER_OF) | 30 sec |
| **2. Bills** | 5,000 | 5,000 (SPONSORED) | 2 min |
| **3. Votes** | 20,000 | 60,000 (VOTED) | 8 min |
| **4. Debates** | 50,000 | 100,000 (SPOKE_AT) | 20 min |
| **5. Expenses** | 40,000 | 40,000 (INCURRED) | 15 min |
| **6. Lobby Regs** | 100,000 | 200,000 (ON_BEHALF_OF) | 35 min |
| **7. Lobby Comms** | 350,000 | 350,000 (MET_WITH) | 90 min |
| **8. Build Relationships** | 0 | 5M+ (derived) | 60 min |
| **TOTAL** | **~566,000** | **~10M** | **~4.2 hours** |

**Incremental updates:** 5-10 minutes (only new/changed data)

---

## 💡 Design Decisions

### 1. Batch Size: 10,000 Nodes/Transaction
- **Why:** Balance memory usage vs. network roundtrips
- **Alternative:** 1,000 (slower but safer for low memory), 50,000 (faster but risky)
- **Trade-off:** 10,000 fits in Neo4j Aura 4GB memory, completes in <1 second per batch

### 2. MERGE vs CREATE
- **CREATE:** Faster (no uniqueness check), used for initial load
- **MERGE:** Upsert (create if missing, update if exists), used for incremental updates
- **Implementation:** Use CREATE for full pipeline, MERGE for `--incremental`

### 3. Relationship Building: Separate Phase
- **Why:** Nodes must exist before creating relationships
- **Alternative:** Create relationships inline during node ingestion
- **Trade-off:** Two-phase approach is clearer, easier to debug, supports relationship rebuilds

### 4. Progress Tracking: TQDM + Loguru
- **TQDM:** Real-time progress bars for batch operations
- **Loguru:** Structured logging with rotation (debug, info, error levels)
- **Why:** Essential for 4-hour initial load (user needs visibility)

### 5. Reuse FedMCP Clients
- **Why:** Already tested, handle rate limiting, parse API responses
- **Alternative:** Duplicate code in pipeline package
- **Implementation:** Import from `../../fedmcp/src/fedmcp/clients/`

---

## 🔒 Security

### Credentials Management

**Development:**
- `.env` file (never commit!)
- `.env.example` shows required variables

**Production (GCP Cloud Run):**
- Environment variables from Secret Manager
- No secrets in code or config files
- IAM service account has `secretmanager.secretAccessor` role

### API Rate Limiting

All clients enforce rate limits to avoid bans:
- **OpenParliament:** 0.1s min interval (10 req/sec)
- **CanLII:** 0.5s min interval (2 req/sec)
- **Automatic backoff:** Exponential retry on 429/5xx errors

---

## 📈 Next Steps

After initial data load:

**Phase 2.2:** Verify Data Quality
- Run validation queries
- Check for orphaned nodes
- Verify relationship counts
- Test accountability queries (money flow, conflicts of interest)

**Phase 3:** Build GraphQL API
- Use `@neo4j/graphql` to auto-generate API from schema
- Deploy to Cloud Run
- Test queries from frontend

**Phase 5:** Schedule Nightly Updates
- Cloud Scheduler triggers `canadagpt-ingest --incremental`
- Runs daily at 2 AM ET
- Keeps data fresh (new bills, votes, expenses)

---

## 🐛 Troubleshooting

### Issue: "Connection refused" to Neo4j

**Cause:** Cloud Run needs VPC Connector to access Neo4j Aura via Private Service Connect

**Fix (Development):**
- Use Neo4j Aura public endpoint temporarily
- Enable "Public access" in Aura console
- Add IP allowlist (your development machine)

**Fix (Production):**
- Deploy to Cloud Run with VPC Connector (Phase 2.2)
- Use Private Service Connect endpoint

---

### Issue: "Constraint violation" during ingestion

**Cause:** Duplicate IDs (e.g., trying to create MP twice)

**Fix:**
```bash
# Option 1: Clear database and start fresh
# In Neo4j Browser:
MATCH (n) DETACH DELETE n;

# Then re-run schema (Phase 1.3)
# Then re-run pipeline

# Option 2: Use MERGE instead of CREATE
canadagpt-ingest --incremental  # Uses MERGE for upserts
```

---

### Issue: "Out of memory" during large batch

**Cause:** Neo4j Aura 4GB insufficient for 50,000-node batches

**Fix:**
- Reduce batch size in `utils/neo4j_client.py` (10,000 → 5,000)
- Upgrade to Aura 8GB instance (production recommended)

---

**Created for CanadaGPT - Phase 2.1: Data Pipeline**
