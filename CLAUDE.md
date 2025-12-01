# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ IMPORTANT: Deploying to Production

**Before deploying to production**, read [DEPLOYMENT.md](DEPLOYMENT.md) for:
- Pre-deployment checklist
- Environment variable configuration
- Rollback procedures
- Post-deployment verification

**Quick validation**: Run `./scripts/validate-deployment.sh` to check for common deployment issues.

## Project Overview

CanadaGPT is an AI-powered Canadian government accountability platform built as a TypeScript/Python monorepo with four core packages:

- **Frontend** (`packages/frontend`): Next.js 14 application with mobile-first UI, voice features, and i18n support
- **Graph API** (`packages/graph-api`): Neo4j GraphQL API using @neo4j/graphql for parliamentary data queries
- **FedMCP** (`packages/fedmcp`): Python MCP (Model Context Protocol) server providing Claude Desktop integration with Canadian parliamentary and legal data
- **Data Pipeline** (`packages/data-pipeline`): Automated daily ingestion of Hansard debates, votes, committee evidence, and MP data into Neo4j

**Tech Stack**: Next.js 14, TypeScript, Neo4j, GraphQL, Python 3.11, Supabase, Google Cloud Run

## Project Structure

```
CanadaGPT/
├── packages/
│   ├── frontend/              # Next.js web application
│   │   ├── src/
│   │   │   ├── app/          # Next.js 14 app router pages
│   │   │   ├── components/   # React components (mobile/, voice/, debates/, committees/)
│   │   │   ├── hooks/        # Custom React hooks (useMobileDetect, useSwipeGesture)
│   │   │   └── lib/          # GraphQL queries, utilities
│   │   └── public/           # Static assets, PWA manifest
│   ├── graph-api/            # GraphQL API server
│   │   └── src/schema.ts     # Neo4j GraphQL schema definitions
│   ├── fedmcp/               # Python MCP server
│   │   └── src/fedmcp/
│   │       ├── clients/      # API clients (openparliament, ourcommons, canlii, lobbying)
│   │       └── server.py     # MCP protocol server
│   ├── data-pipeline/        # Data ingestion
│   │   ├── fedmcp_pipeline/
│   │   │   ├── ingest/       # Ingestion scripts (hansard.py, parliament.py, votes_xml_import.py)
│   │   │   └── utils/        # Neo4j client utilities
│   │   └── scripts/          # Entry point scripts
│   └── design-system/        # Shared UI components (future)
├── scripts/                  # Deployment & utility scripts
│   ├── deploy-*.sh          # Cloud Run deployment scripts
│   ├── daily-*.py           # Daily import scripts
│   └── dev-*.sh             # Local development helpers
├── supabase/                # Database migrations & config
├── Dockerfile.*             # Container definitions for Cloud Run jobs
└── cloudbuild-*.yaml        # Google Cloud Build configurations
```

## Quick Start

**Prerequisites**:
- Node.js 20+, pnpm, Python 3.11+
- Neo4j instance (local or remote)
- Supabase project (for auth/storage)

```bash
# Install dependencies
pnpm install

# Setup Python environment for data pipeline
cd packages/data-pipeline
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .
cd ../..

# Setup environment variables
cp packages/frontend/.env.example packages/frontend/.env
# Edit .env with your Neo4j, Supabase credentials

# Run development servers
pnpm dev:frontend    # → http://localhost:3000
pnpm dev:api         # → http://localhost:4000 (GraphQL)

# Run specific package
pnpm --filter @canadagpt/frontend dev
pnpm --filter @canadagpt/graph-api build

# Build all packages
pnpm build:all       # Builds design-system, graph-api, frontend in order
```

## Development Commands

```bash
# Frontend
pnpm dev:frontend              # Start Next.js dev server
pnpm build:frontend            # Production build
pnpm --filter @canadagpt/frontend type-check  # TypeScript check

# Graph API
pnpm dev:api                   # Start GraphQL server
pnpm build:api                 # Compile TypeScript

# Data Pipeline (Python)
cd packages/data-pipeline
source venv/bin/activate
python scripts/daily-hansard-import.py     # Import latest Hansard
python run_mp_ingestion.py                 # Import MP data
python run_votes_ingestion.py              # Import votes

# Docker (local development)
docker-compose up -d           # Start Neo4j locally
docker-compose logs -f neo4j   # View Neo4j logs

# GCP Deployment
./scripts/deploy-cloud-run.sh              # Deploy Graph API
./scripts/deploy-hansard-importer.sh       # Deploy Hansard ingestion job
gcloud run jobs execute hansard-daily-import --region=us-central1  # Manual trigger
```

## Core Package Details

### Frontend (Next.js)

**Location**: `packages/frontend/`

**Key Features**:
- Server-side rendering with Next.js 14 App Router
- Internationalization (en/fr) using next-intl
- Mobile-first responsive design with PWA support
- Voice search/chat using browser Web Speech API
- Twitter/Instagram-style debate viewer with swipe gestures
- GraphQL client for Neo4j data

**Important Files**:
- `src/app/[locale]/` - App router pages (debates, committees, MPs, bills)
- `src/components/mobile/` - Mobile UI components (MobileStatementCard, MobileDebateViewer)
- `src/components/voice/` - Voice features (VoiceSearch, VoiceChat, VoiceNotes)
- `src/lib/queries.ts` - GraphQL queries
- `src/contexts/UserPreferencesContext.tsx` - User settings (language, theme)

**Mobile/Voice System**: See `MOBILE_IMPLEMENTATION_GUIDE.md` for detailed component usage. Key components include:
- **Voice**: VoiceSearch, VoiceChat, VoiceNotes (Web Speech API)
- **Mobile**: MobileStatementCard, MobileDebateViewer, MobileBottomNav
- **Hooks**: useMobileDetect, useSwipeGesture
- **Design**: Party-color coding (Liberal: #DC2626, Conservative: #2563EB, NDP: #F59E0B)

### Graph API (Neo4j GraphQL)

**Location**: `packages/graph-api/`

**Purpose**: GraphQL API layer over Neo4j database using @neo4j/graphql OGM (Object Graph Mapper)

**Schema**: `src/schema.ts` - Defines GraphQL types mapped to Neo4j nodes/relationships

**Key Types**:
- `Parliament`, `Session` - Parliamentary hierarchy
- `MP`, `Riding`, `Party` - Politician data
- `Document`, `Statement` - Hansard debates
- `Vote`, `Ballot` - Voting records
- `Committee`, `Meeting`, `CommitteeEvidence`, `CommitteeTestimony` - Committee data
- `Bill` - Legislation

**Deployment**:
- Production: Google Cloud Run (`canadagpt-graph-api`)
- Build: `docker build --platform linux/amd64` (required for Cloud Run)
- Connects to Neo4j VM at `bolt://10.128.0.3:7687`

### FedMCP (MCP Server)

**Location**: `packages/fedmcp/`

**Purpose**: Model Context Protocol server providing Claude Desktop with access to Canadian parliamentary and legal data

**Installation**:
```bash
cd packages/fedmcp
pip install -e .
```

**Running**:
```bash
python -m fedmcp.server
# Or: fedmcp
```

**Claude Desktop Configuration**:
```json
{
  "mcpServers": {
    "fedmcp": {
      "command": "python",
      "args": ["-m", "fedmcp.server"],
      "env": {
        "CANLII_API_KEY": "your_key_here"
      }
    }
  }
}
```

**Architecture**:

All clients in `src/fedmcp/clients/` use `RateLimitedSession` (http.py):
- Proactive rate limiting: `min_request_interval` enforces delays between requests
- Reactive retry: Automatic exponential backoff for 429/5xx errors
- Shared session management

**API Clients**:

- **OpenParliamentClient** (openparliament.py): `list_debates()`, `get_debate()`, `list_bills()`, `get_bill()`, `list_mps()`, `list_votes()`, `list_committees()`
  - Pagination-aware iterators, 10 req/s rate limit
- **OurCommonsHansardClient** (ourcommons.py): `get_sitting(slug_or_url, parse=True)`
  - Two-step fetch: HTML → extract XML link → parse XML
- **OurCommonsVotesClient** (ourcommons_votes.py): `get_vote_summaries()`, `get_vote(parliament, session, vote_number)`
- **OurCommonsCommitteeEvidenceClient** (ourcommons_committee_evidence.py): `get_evidence(committee_code, meeting_number)`
- **LegisInfoClient** (legisinfo.py): `get_bill(parliament_session, bill_code)`, `list_bills(chamber=None)`
- **CanLIIClient** (canlii.py): `search_cases_by_keyword()`, `get_case()`, `search_legislation()`
  - Requires `CANLII_API_KEY`, 2 req/s rate limit
- **MPExpenditureClient** (expenditure.py): `search_by_name(name, fiscal_year, quarter)`
- **PetitionsClient** (petitions.py): `search_petitions(keyword)`, `get_petition(petition_number)`
- **LobbyingRegistryClient** (lobbying.py): `search_registrations()`, `search_communications()`
  - Downloads ~90MB data on first use, caches to `~/.cache/fedmcp/lobbying/`

**MCP Tools** (40+ tools exposed via server.py):
- Parliamentary: `search_debates`, `search_bills`, `list_mps`, `list_votes`, `get_committee_details`
- Accountability: `get_mp_expenses`, `search_mp_expenses`, `get_mp_activity_scorecard`, `analyze_mp_bills`
- Petitions: `search_petitions`, `get_petition_details`, `get_mp_petitions`
- Lobbying: `search_lobbying_registrations`, `analyze_bill_lobbying`, `detect_conflicts_of_interest`
- Legal (CanLII): `search_cases`, `get_case`, `search_legislation`

**Testing Clients**:
```python
from fedmcp import OpenParliamentClient, OurCommonsHansardClient
from fedmcp.clients.expenditure import MPExpenditureClient

# OpenParliament
op = OpenParliamentClient()
for debate in op.list_debates(limit=10):
    print(debate)

# Hansard
commons = OurCommonsHansardClient()
sitting = commons.get_sitting("latest/hansard", parse=True)
print(f"Date: {sitting.date}, Sections: {len(sitting.sections)}")

# MP Expenses
expenses = MPExpenditureClient()
mp_expenses = expenses.search_by_name("Poilievre", fiscal_year=2026, quarter=1)
```

**Key Implementation Notes**:
- Bill codes in LEGISinfo should be lowercase (e.g., "c-249" not "C-249")
- DocumentViewer slugs can be relative (e.g., "latest/hansard") or full URLs
- OpenParliament list methods return iterators - use `list()` to materialize all results
- Hansard parsing preserves paragraph structure with double-newline separation
- CanLII tools only exposed if `CANLII_API_KEY` is set

**Common CanLII Database IDs**:
- `csc-scc` - Supreme Court of Canada
- `fca-caf` - Federal Court of Appeal
- `onca`, `bcca`, `abca`, `qcca` - Provincial Courts of Appeal
- `ca` - Federal acts, `car` - Federal regulations
- `on`, `bc` - Provincial statutes

### Data Pipeline (Python)

**Location**: `packages/data-pipeline/`

**Purpose**: Automated daily imports of parliamentary data into Neo4j

**Components**:
1. **Python Client** - Fetches data from API/XML (`packages/fedmcp/src/fedmcp/clients/`)
2. **Ingestion Script** - Processing logic (`fedmcp_pipeline/ingest/`)
3. **Cloud Run Job** - Containerized job on GCP
4. **Cloud Scheduler** - Daily cron trigger

**Person ID Linking**: All data uses House of Commons `person_db_id`/`parl_mp_id` to link to MP nodes

**Ingestion Pipelines**:

| Pipeline | Schedule | Purpose | Files |
|----------|----------|---------|-------|
| **MP Ingestion** | Daily 6:00 AM UTC | Import MP biographical data, ridings, parties | `run_mp_ingestion.py`, `fedmcp_pipeline/ingest/parliament.py` |
| **Hansard** | Daily 4:00 AM ET | Import House debates (7-day lookback) | `scripts/daily-hansard-import.py`, `Dockerfile.hansard-importer` |
| **Committee Meetings** | Daily 6:00 AM ET | Discover/import scheduled meetings (7-day lookback) | `scripts/daily-committee-import.py`, `Dockerfile.committee-importer` |
| **Votes** | Daily 7:00 AM UTC | Import vote records & ballots | `run_votes_ingestion.py`, `fedmcp_pipeline/ingest/votes_xml_import.py` |
| **Committee Evidence** | Daily 8:00 AM UTC | Import witness testimony | `run_committee_evidence_ingestion.py`, `fedmcp_pipeline/ingest/committee_evidence_xml_import.py` |
| **Lobbying Registry** | Weekly Sundays 2:00 AM UTC | Full refresh of lobbying data (registrations, communications, organizations, lobbyists) | `run_lobbying_ingestion.py`, `fedmcp_pipeline/ingest/lobbying.py`, `Dockerfile.lobbying-ingestion` |
| **MP Expenses** | Daily 5:00 AM UTC | Import MP office & House Officer expenses (quarterly data) | `run_expenses_ingestion.py`, `fedmcp_pipeline/ingest/finances.py`, `Dockerfile.expenses-ingestion` |

**Hansard Ingestion Details**:
- **Data Source**: Direct XML URLs - `https://www.ourcommons.ca/Content/House/451/Debates/{sitting}/HAN{sitting}-E.XML`
  - ⚠️ Important: DocumentViewer HTML pages return 404 programmatically - always use direct XML
- **XML Structure**: `HansardBody → OrderOfBusiness (h1) → SubjectOfBusiness (h2) → Intervention`
- **MP Name Matching**: Sophisticated fuzzy matching with 85-90% success rate
  - Accent removal, hyphen handling, honorific removal (Hon., Rt. Hon.)
  - Nickname mapping (Bobby ↔ Robert, Bill ↔ William)
- **Publication Pattern**: Hansard published 1-2 days after sitting, typically 8-10 PM ET
- **Deployment**: `./scripts/deploy-hansard-importer.sh` (2Gi memory, 30-min timeout)

**Committee Meeting Discovery**:
- **Data Source**: `https://www.ourcommons.ca/committees/en/FilteredMeetings?meetingDate=YYYY-MM-DD`
- **HTML Parsing**: BeautifulSoup extracts meeting ID, committee code, date, time, subject, status, webcast availability
- **Idempotent**: Skips meetings already in database (by `ourcommons_meeting_id`)
- **Deployment**: `./scripts/deploy-committee-importer.sh`

**Lobbying Registry Ingestion**:
- **Data Source**: `https://lobbycanada.gc.ca` (Office of the Commissioner of Lobbying)
  - Registrations: `https://lobbycanada.gc.ca/media/zwcjycef/registrations_enregistrements_ocl_cal.zip` (~77MB)
  - Communications: `https://lobbycanada.gc.ca/media/mqbbmaqk/communications_ocl_cal.zip` (~19MB)
  - ⚠️ Important: Use `source="official"` (lobbycanada.gc.ca), NOT `source="opendata"` (broken URLs)
- **Import Strategy**: Full refresh weekly - clears all existing lobbying data before import
- **Data Cleanup**: Batched deletions (10,000 nodes at a time) to avoid Neo4j transaction memory limits
- **Resource Requirements**:
  - Memory: 4Gi (handles 163K registrations + 343K communications)
  - CPU: 2 cores
  - Runtime: ~5 minutes
- **Typical Import Volumes**:
  - 163,459 lobby registrations
  - 343,862 lobby communications
  - 19,639 organization nodes
  - 13,847 lobbyist nodes
- **Deployment**: `./scripts/deploy-lobbying-ingestion.sh` (Cloud Run job + weekly Cloud Scheduler)
- **Key Implementation Notes**:
  - Cleanup runs in batches: `MATCH (n:LobbyRegistration) WITH n LIMIT 10000 DETACH DELETE n`
  - Downloads cached locally in container during first run
  - All data indexed by unique `id` property

**MP Expenses Ingestion**:
- **Data Source**: OurCommons Proactive Disclosure (CSV format, quarterly updates)
  - MP Expenses: `https://www.ourcommons.ca/proactivedisclosure/en/members/{fiscal_year}/{quarter}`
  - House Officer Expenses: `https://www.ourcommons.ca/proactivedisclosure/en/house-officers/{fiscal_year}/{quarter}`
- **Dual Source Import**: MP office expenses + House Officer expenses (Speaker, Leaders, Whips, etc.)
- **MP Name Matching**: Fuzzy matching with 99.9% success rate (nickname mapping, accent removal, compound surnames)
- **Idempotent Design**: Safe to run multiple times (uses MERGE, deterministic IDs)
- **Resource Requirements**:
  - Memory: 2Gi, CPU: 1, Timeout: 15 minutes
  - Runtime: ~1-2 minutes for daily check
- **Typical Import Volumes**:
  - ~1,500 MP expense records per quarter (338 MPs × 4 categories)
  - ~60 House Officer expense records per quarter (~15 officers × 4 categories)
- **Expense Categories**: salaries, travel, hospitality, contracts
- **Deployment**: `./scripts/deploy-expenses-ingestion.sh` (Cloud Run job + daily Cloud Scheduler)
- **Historical Backfill**: Run locally with `--fiscal-year-start 2020 --fiscal-year-end 2023`
- **Documentation**: See `EXPENSES_INGESTION.md` for full details

**Common Operations**:
```bash
# Deploy pipeline
gcloud builds submit --config packages/data-pipeline/cloudbuild-{JOB_NAME}.yaml

# Manual trigger
gcloud run jobs execute {JOB_NAME} --region=us-central1

# View logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name={JOB_NAME}" --limit=50

# Test locally
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USERNAME=neo4j
export NEO4J_PASSWORD=your_password
python scripts/daily-hansard-import.py
```

**Troubleshooting**:

| Issue | Causes | Solutions |
|-------|--------|-----------|
| 404 errors fetching XML | DocumentViewer URL used, wrong sitting number, cancelled debate | Use direct XML pattern, check Commons calendar, try ±1-2 sitting numbers |
| Low MP linking rate (<80%) | New MPs not in DB, non-MP speakers, name variations | Update MP data, check `who_en` field, add nickname mappings |
| Duplicate debates | Multiple imports of same date | Process is idempotent (DETACH DELETE), check: `MATCH (d:Document {date: '2025-11-03'}) RETURN count(*)` |

## Neo4j Database Schema

**Connection**:
- Production: `bolt://10.128.0.3:7687` (internal VM on GCP)
- Local dev: `bolt://localhost:7687`

**Core Node Types**:

```cypher
# Parliament Hierarchy
(Parliament {number, ordinal, election_date, is_current})
  -[:HAS_SESSION]->
(Session {id, parliament_number, session_number, start_date, is_current})

# MPs and Affiliations
(MP {id, name, parl_mp_id, current_party, current_riding})
  -[:REPRESENTS {start_date, end_date}]->
(Riding {id, name, province})

(MP)-[:MEMBER_OF {start_date, end_date}]->(Party {id, name})

# Hansard Debates
(Document {id, date, session_id, number})
  <-[:PART_OF]-
(Statement {id, document_id, time, who_en, content_en, h1_en, h2_en, wordcount})
  -[:MADE_BY]->
(MP)

# Votes
(Vote {vote_number, date_time, result, num_yeas, num_nays, subject, bill_number})
  <-[:CAST_IN]-
(Ballot {id, vote_number, person_id, vote_value, is_yea, is_nay})
  -[:CAST_BY]->
(MP)

(Vote)-[:CONCERNS]->(Bill)

# Committee System
(Committee {code, name})
  -[:HELD_MEETING]->
(Meeting {ourcommons_meeting_id, committee_code, date, subject, status})
  -[:HAS_EVIDENCE]->
(CommitteeEvidence {id, committee_code, meeting_number, date})
  <-[:GIVEN_IN]-
(CommitteeTestimony {id, speaker_name, text, is_witness, organization, role})
  -[:TESTIFIED_BY]->
(MP)

# SPOKE_AT Relationships (Direct MP → Document Shortcuts)
# Enable efficient queries like "which MPs spoke in this debate?"
(MP)-[:SPOKE_AT {timestamp, statement_id, intervention_id, person_db_id}]->(Document)
(MP)-[:SPOKE_AT {testimony_id, intervention_id, person_db_id, timestamp_hour, timestamp_minute}]->(CommitteeEvidence)

# Note: SPOKE_AT creates multiple relationships per MP-Document pair
# (one per Statement/Testimony) for detailed tracking
```

**GraphQL Schema**: `packages/graph-api/src/schema.ts` maps these nodes to GraphQL types with `@neo4j/graphql` directives

**Manual Queries**:
```python
#!/usr/bin/env python3
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd() / 'packages' / 'data-pipeline'))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient

neo4j = Neo4jClient(uri='bolt://10.128.0.3:7687', user='neo4j', password='...')

# Check November debates
result = neo4j.run_query("""
    MATCH (d:Document)
    WHERE d.date STARTS WITH '2025-11'
    RETURN d.id, d.date, d.number
    ORDER BY d.date
""")

for row in result:
    print(f"{row['d.date']}: Document {row['d.id']} - {row['d.number']}")
```

## Infrastructure

**Google Cloud Platform**:
- Project: `canada-gpt-ca`
- Region: `us-central1`
- VPC Connector: `canadagpt-vpc-connector`
- Artifact Registry: `us-central1-docker.pkg.dev/canada-gpt-ca/canadagpt/`

**Production Services**:
- Neo4j VM: `bolt://10.128.0.3:7687` (internal, via VPC connector)
- Graph API: Cloud Run service `canadagpt-graph-api`
- Ingestion Jobs: Cloud Run jobs (hansard-daily-import, mp-ingestion, votes-ingestion, committee-daily-import, committee-evidence-ingestion, lobbying-ingestion)
- Supabase: Database, Auth, Storage

**Deployment Notes**:
- Always compile Graph API with `--platform linux/amd64` for Cloud Run
- Cloud Run jobs require VPC connector for Neo4j access
- Environment variables set via `--set-env-vars` in gcloud commands
- Screenshots located at: `~/Desktop/Screenshot*.png`

## Common Development Tasks

### Running Locally

```bash
# Start Neo4j (Docker)
docker-compose up -d neo4j

# Start frontend + API
pnpm dev:frontend &
pnpm dev:api &

# Or use dev helper script
./scripts/dev-start.sh
```

### Adding a New MCP Tool

1. Define tool in `packages/fedmcp/src/fedmcp/server.py` → `list_tools()` function
2. Add input schema (JSON Schema)
3. Implement handler in `call_tool()` function
4. Return results as `TextContent` objects
5. Handle errors with try/except blocks
6. Test with Claude Desktop

### Adding a New Data Source

1. Create client in `packages/fedmcp/src/fedmcp/clients/new_source.py`
   - Extend `RateLimitedSession` from `http.py`
   - Define rate limiting: `min_request_interval`
2. Create ingestion script in `packages/data-pipeline/fedmcp_pipeline/ingest/new_source.py`
3. Define Neo4j schema in `packages/graph-api/src/schema.ts`
4. Create Dockerfile: `Dockerfile.new-source-importer`
5. Create Cloud Build config: `cloudbuild-new-source.yaml`
6. Create deployment script: `scripts/deploy-new-source-importer.sh`
7. Set up Cloud Scheduler cron job

### Deploying to Production

```bash
# Frontend (Cloud Run)
cd packages/frontend
./scripts/deploy-frontend-cloudrun.sh

# Graph API (Cloud Run)
./scripts/deploy-cloud-run.sh

# Ingestion Jobs
./scripts/deploy-hansard-importer.sh
./scripts/deploy-committee-importer.sh
./scripts/deploy-votes-importer.sh

# Manual trigger ingestion
gcloud run jobs execute hansard-daily-import --region=us-central1
```

### Debugging Ingestion

```bash
# View Cloud Run job logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=hansard-daily-import" --limit=50 --format=json

# Test locally with production DB (via tunnel)
./scripts/dev-tunnel.sh  # Opens SSH tunnel to Neo4j VM
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USERNAME=neo4j
export NEO4J_PASSWORD=...
python scripts/daily-hansard-import.py

# Check database status
./scripts/check-dev-status.sh
```

### Backfilling SPOKE_AT Relationships

If SPOKE_AT relationships are missing or need to be recreated:

```bash
# Connect to production DB via tunnel
./scripts/dev-tunnel.sh &
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USERNAME=neo4j
export NEO4J_PASSWORD=canadagpt2024

# Run backfill script
cd packages/data-pipeline
python scripts/backfill_spoke_at.py

# The script will:
# 1. Create (MP)-[:SPOKE_AT]->(Document) from Hansard statements
# 2. Create (MP)-[:SPOKE_AT]->(CommitteeEvidence) from committee testimonies
# 3. Report statistics and verify results

# Expected output:
# - Hansard: ~1.2M relationships
# - Committee: varies based on testimony data
# - Script is idempotent (safe to re-run)
```

### Common Issues

**Issue**: Type errors in frontend after schema changes
```bash
pnpm --filter @canadagpt/frontend codegen  # Regenerate GraphQL types
pnpm --filter @canadagpt/frontend type-check
```

**Issue**: Graph API not reflecting Neo4j changes
- Restart the server (schema is cached)
- Verify Neo4j connection with Cypher query
- Check `packages/graph-api/src/schema.ts` for type definitions

**Issue**: Hansard import finding no new debates
- Check OurCommons calendar: `https://www.ourcommons.ca/`
- Verify sitting numbers: debates use sequential numbers (050, 051, 052...)
- Check logs for 404 errors (might be wrong sitting number)

## Mobile/Voice System Reference

**Relevant when**: Building mobile UI, implementing voice features, creating PWA

**Location**: `packages/frontend/src/components/{mobile,voice}/` and `src/hooks/`

**Complete Documentation**: See `MOBILE_IMPLEMENTATION_GUIDE.md` (850 lines)

**Quick Reference**:

**Components**:
- `VoiceSearch`, `VoiceChat`, `VoiceNotes` - Browser Web Speech API integration
- `MobileStatementCard`, `MobileDebateViewer` - Twitter/Instagram-style UI
- `MobileBottomNav`, `MobileHeader`, `SwipeableDrawer` - Navigation
- `MobileMPCard`, `MobileDebateCard`, `MobileBillCard` - Card components

**Hooks**:
- `useMobileDetect()` - Device type, OS, screen size, orientation
- `useSwipeGesture()` - Swipe detection for navigation

**Design System**:
- Party colors: Liberal #DC2626, Conservative #2563EB, NDP #F59E0B, Bloc #3B82F6, Green #10B981
- Touch targets: 44-48px minimum (iOS HIG)
- iOS safe areas: `env(safe-area-inset-top)`, `env(safe-area-inset-bottom)`
- Voice API: Requires HTTPS in production

**PWA**: `packages/frontend/public/manifest.json`

**Browser Support**:
- Voice: iOS Safari 14.5+, Chrome Android 33+, Edge Android 79+ (HTTPS required)
- UI: All modern mobile browsers

## Frontend Bug Fixes

**Timezone Issue** (Fixed Nov 2025): Changed date parsing from UTC to local timezone in `packages/frontend/src/app/[locale]/debates/page.tsx` to prevent date display issues across timezones (e.g., Nov 7 showing as Nov 6 in PST/PDT).

## FedMCP Bug Fixes

These fixes were ported from the original canfedinfo library:

**OpenParliamentClient** (clients/openparliament.py:52-54):
- Fixed pagination to handle relative URLs from API responses
- Fetcher prepends `base_url` to relative URLs starting with '/'

**OurCommonsHansardClient** (clients/ourcommons.py:89-96, 101-149):
- Fixed UTF-8 BOM handling by decoding with 'utf-8-sig' encoding
- Updated XML parsing to match actual structure using `<ExtractedInformation>`, `<Intervention>`, `<ParaText>` elements
