# CanadaGPT Production Architecture

Complete system architecture for **https://canadagpt.ca**

**Last Updated**: 2025-11-08

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRODUCTION ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐                                               │
│  │   USERS      │                                               │
│  │ canadagpt.ca │                                               │
│  └──────┬───────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  CLOUD RUN: Frontend (Next.js)                           │  │
│  │  Service: canadagpt-frontend                             │  │
│  │  URL: https://canadagpt-frontend-*.run.app               │  │
│  │  - Bilingual (EN/FR) routing                             │  │
│  │  - Server-side rendering                                 │  │
│  │  - Scale-to-zero (cost efficient)                        │  │
│  └────────────┬─────────────────────┬──────────────────────┘  │
│               │                     │                           │
│               ▼                     ▼                           │
│  ┌────────────────────┐  ┌──────────────────────────────────┐  │
│  │  CLOUD RUN:        │  │  SUPABASE (Managed PostgreSQL)   │  │
│  │  GraphQL API       │  │  Project: lbyqmjcqbwfeglfkiqpd   │  │
│  │                    │  │                                   │  │
│  │  Service:          │  │  DATABASES:                       │  │
│  │  canadagpt-graph-  │  │  • auth.users (OAuth profiles)   │  │
│  │  api               │  │  • public.profiles               │  │
│  │                    │  │  • public.forums                 │  │
│  │  Port: 4000        │  │  • hansards_* (staging mirror)   │  │
│  │  Uses: Neo4j       │  │  • bills_* (metadata)            │  │
│  │  @neo4j/graphql    │  │  • mps_* (basic data)            │  │
│  └────────┬───────────┘  └───────────────────────────────────┘  │
│           │                                                      │
│           │ Internal Network (10.128.0.0/24)                    │
│           ▼                                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  VM: Neo4j Database                                      │  │
│  │  Name: canadagpt-neo4j                                   │  │
│  │  Type: n2-standard-2 (2 vCPU, 8GB RAM)                  │  │
│  │  Internal IP: 10.128.0.3                                 │  │
│  │  Port: 7687 (Bolt)                                       │  │
│  │                                                           │  │
│  │  DATA:                                                    │  │
│  │  • 3.67M Hansard statements (importing)                 │  │
│  │  • 338 MPs with relationships                            │  │
│  │  • 1,200+ Bills                                          │  │
│  │  • Committees, Votes, Lobbying data                      │  │
│  │  • Full-text search indexes                              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  VM: Data Ingestion                                      │  │
│  │  Name: canadagpt-ingestion                               │  │
│  │  Type: n2-standard-4 (4 vCPU, 16GB RAM, 150GB SSD)      │  │
│  │  Internal IP: 10.128.0.4                                 │  │
│  │                                                           │  │
│  │  LOCAL POSTGRESQL:                                        │  │
│  │  • Database: openparliament_temp                         │  │
│  │  • Complete OpenParliament mirror (3.67M statements)     │  │
│  │  • Used for: Bulk imports to Neo4j                       │  │
│  │                                                           │  │
│  │  SCRIPTS:                                                 │  │
│  │  • ~/FedMCP/import_all_hansard_statements.py            │  │
│  │  • Connects: PostgreSQL → Neo4j (internal network)      │  │
│  │  • Status: RUNNING (2-3 hours to complete)              │  │
│  │  • tmux session: hansard_import                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. Frontend (Cloud Run)

**Service**: `canadagpt-frontend`
**Technology**: Next.js 14 (App Router)
**URL**: https://canadagpt.ca

### Features
- ✅ Bilingual routing (`/en/*`, `/fr/*`)
- ✅ Server-side rendering (SSR)
- ✅ OAuth authentication (Google, GitHub, Facebook, LinkedIn)
- ✅ Responsive design with dark mode
- ✅ SEO optimized (sitemap, robots.txt, OpenGraph)

### Configuration
- **Min Instances**: 0 (scale-to-zero)
- **Max Instances**: 10
- **Memory**: 512Mi
- **CPU**: 1
- **Region**: us-central1

### Environment Variables
```bash
NEXT_PUBLIC_GRAPHQL_URL=https://canadagpt-graph-api-*.run.app/graphql
NEXT_PUBLIC_SUPABASE_URL=https://lbyqmjcqbwfeglfkiqpd.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=[secret]
NEXT_PUBLIC_BASE_URL=https://canadagpt.ca
NODE_ENV=production
```

### Deployment
- **Method**: GitHub Actions (on push to `main`)
- **Workflow**: `.github/workflows/deploy-frontend.yml`
- **Build**: Multi-stage Docker build
- **Registry**: Artifact Registry (`us-central1-docker.pkg.dev`)

---

## 2. GraphQL API (Cloud Run)

**Service**: `canadagpt-graph-api`
**Technology**: @neo4j/graphql (auto-generated from schema)
**Port**: 4000

### Features
- ✅ Auto-generated resolvers from Neo4j schema
- ✅ Custom queries (mpSpeeches, searchHansard, billDebates, billLobbying)
- ✅ Real-time graph traversal
- ✅ Pagination support
- ✅ Full-text search

### Configuration
- **Min Instances**: 0
- **Max Instances**: 10
- **Memory**: 1Gi
- **CPU**: 1
- **Region**: us-central1

### Environment Variables
```bash
NEO4J_URI=bolt://10.128.0.3:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=[secret]
PORT=4000
NODE_ENV=production
```

### Key Queries
- `mPs`: List all MPs with pagination
- `bills`: Search bills by session/number
- `mpSpeeches`: Get speeches by MP (uses APOC)
- `searchHansard`: Full-text search across statements
- `billDebates`: Get debates for specific bill
- `billLobbying`: Get lobbying activity for bill

---

## 3. Neo4j Database (VM)

**VM**: `canadagpt-neo4j`
**Type**: n2-standard-2 (2 vCPU, 8GB RAM)
**Internal IP**: 10.128.0.3
**Version**: Neo4j Community 2025.10.1

### Data Model

**Nodes**:
- `MP` (338 current MPs)
- `Statement` (3.67M Hansard speeches - importing)
- `Document` (~25K Hansard documents)
- `Bill` (1,200+ legislative bills)
- `Committee` (parliamentary committees)
- `Vote` (recorded votes)
- `LobbyingRegistration` (100K+ registrations)

**Relationships**:
- `(Statement)-[:MADE_BY]->(MP)`
- `(Statement)-[:PART_OF]->(Document)`
- `(Statement)-[:MENTIONS]->(Bill)`
- `(MP)-[:SPONSORED]->(Bill)`
- `(MP)-[:MEMBER_OF]->(Committee)`
- `(MP)-[:VOTED]->(Vote)`

### Indexes
- Full-text: `statement_content_en`, `statement_content_fr`
- Constraints: Unique IDs on all node types
- Composite: Date + session for efficient queries

### Plugins
- ✅ APOC Core 2025.10.1 (required for @neo4j/graphql DateTime fields)

### Access
- **Internal**: bolt://10.128.0.3:7687 (from Cloud Run)
- **External**: Blocked by firewall (secure)

---

## 4. Supabase (Managed PostgreSQL)

**Project**: lbyqmjcqbwfeglfkiqpd
**URL**: https://lbyqmjcqbwfeglfkiqpd.supabase.co
**Region**: us-west-1

### Databases

#### `auth` Schema (Supabase managed)
- `users`: OAuth profiles, email verification
- `sessions`: Active user sessions
- `identities`: OAuth provider mappings

#### `public` Schema
- `profiles`: Extended user profiles
- `forums`: Discussion categories
- `forum_topics`: User-created topics
- `forum_posts`: Comments and replies
- `forum_votes`: Upvotes/downvotes

#### `hansards_*` Tables (OpenParliament mirror)
- `hansards_statement`: 3.67M parliamentary speeches
- `hansards_document`: ~25K Hansard documents
- **Purpose**: Staging area for Neo4j imports

#### `bills_*` Tables
- `bills_bill`: Bill metadata (title, status, session)
- **Purpose**: Basic bill info, complemented by Neo4j graph

#### `mps_*` Tables
- `mps_mp`: Basic MP information
- **Purpose**: Backup/reference, primary data in Neo4j

### OAuth Providers (Configured)
- ✅ Google OAuth
- ✅ GitHub OAuth
- ✅ Facebook OAuth
- ✅ LinkedIn OAuth (OIDC)

### Callback URL
```
https://lbyqmjcqbwfeglfkiqpd.supabase.co/auth/v1/callback
```

---

## 5. Ingestion VM

**VM**: `canadagpt-ingestion`
**Type**: n2-standard-4 (4 vCPU, 16GB RAM, 150GB SSD)
**Internal IP**: 10.128.0.4

### Purpose
Dedicated VM for processing bulk data imports without affecting production services.

### Local PostgreSQL
- **Database**: `openparliament_temp`
- **User**: `fedmcp` (password: fedmcp2024)
- **Data**: Complete OpenParliament mirror (3.67M statements)

### Current Operation
```bash
# Running in tmux session: hansard_import
cd ~/FedMCP
source packages/data-pipeline/venv/bin/activate
python3 import_all_hansard_statements.py

# Status: Importing 3.37M statements to Neo4j
# Progress: Check with: tmux attach -t hansard_import
# ETA: 2-3 hours from start (04:43 UTC)
```

### Data Flow
```
OpenParliament PostgreSQL (local)
  ↓
Python import script
  ↓
Neo4j (10.128.0.3:7687 via internal network)
```

### Cost Management
- **When idle**: Stop VM (`gcloud compute instances stop`)
- **Storage cost**: ~$5/month (150GB SSD)
- **Compute cost**: ~$100/month (when running)
- **Recommendation**: Stop after imports complete

---

## Data Architecture

### User Flow
```
User → Frontend → Supabase Auth → User Profile
                → GraphQL API → Neo4j → Graph Data
```

### Data Sync Flow
```
External Sources
  ↓
Ingestion VM (OpenParliament PostgreSQL)
  ↓
Neo4j (Graph Database)
  ↓
GraphQL API
  ↓
Frontend
```

### Data Separation

| Data Type | Primary Storage | Backup/Mirror | Purpose |
|-----------|----------------|---------------|---------|
| User accounts | Supabase (auth.users) | - | OAuth, profiles |
| Forum posts | Supabase (public.forums) | - | User-generated content |
| MPs graph | Neo4j | Supabase (mps_mp) | Relationships, votes |
| Hansard | Neo4j | Supabase (hansards_*) | Full-text search, threads |
| Bills | Neo4j | Supabase (bills_*) | Legislative tracking |
| Lobbying | Neo4j | - | Corporate influence |

---

## Deployment Workflows

### Frontend Deployment
```bash
# Automated via GitHub Actions
git push origin main

# Manual trigger
gh workflow run deploy-frontend.yml
```

**Triggers**:
- Push to `main` branch
- Changes in:
  - `packages/frontend/**`
  - `packages/design-system/**`
  - `.github/workflows/deploy-frontend.yml`

**Process**:
1. Build Docker image (multi-stage)
2. Push to Artifact Registry
3. Deploy to Cloud Run
4. ~5-10 minutes total

### GraphQL API Deployment
```bash
# Similar to frontend
git push origin main
# (if .github/workflows/deploy-graphql.yml exists)
```

### Data Imports
```bash
# SSH to ingestion VM
gcloud compute ssh canadagpt-ingestion --zone=us-central1-a

# Run import
tmux new -s import
cd ~/FedMCP
source packages/data-pipeline/venv/bin/activate
python3 import_all_hansard_statements.py
```

---

## Monitoring & Logs

### Cloud Run Logs
```bash
# Frontend logs
gcloud run services logs read canadagpt-frontend --region=us-central1 --limit=50

# GraphQL API logs
gcloud run services logs read canadagpt-graph-api --region=us-central1 --limit=50
```

### Neo4j Monitoring
```bash
# SSH to Neo4j VM
gcloud compute ssh canadagpt-neo4j --zone=us-central1-a

# Check Neo4j status
sudo systemctl status neo4j

# View logs
sudo journalctl -u neo4j -f
```

### Supabase Dashboard
https://supabase.com/dashboard/project/lbyqmjcqbwfeglfkiqpd

- Auth logs
- Database activity
- API usage

---

## Security

### Network
- ✅ Cloud Run services: Public HTTPS only
- ✅ Neo4j: Internal network only (10.128.0.0/24)
- ✅ Ingestion VM: SSH access only
- ✅ Supabase: Managed security + Row Level Security (RLS)

### Authentication
- ✅ OAuth 2.0 (Google, GitHub, Facebook, LinkedIn)
- ✅ JWT tokens (Supabase managed)
- ✅ Secure cookies (httpOnly, sameSite)

### Secrets Management
- ✅ GitHub Secrets (deployment)
- ✅ Cloud Run environment variables
- ✅ Supabase Dashboard (OAuth secrets)

---

## Cost Breakdown (Monthly)

| Service | Type | Cost |
|---------|------|------|
| Cloud Run (Frontend) | Serverless | $0-5 (scale-to-zero) |
| Cloud Run (GraphQL) | Serverless | $0-10 (scale-to-zero) |
| Neo4j VM (n2-standard-2) | Always on | ~$50 |
| Ingestion VM (n2-standard-4) | When running | ~$100 (stop when idle = $5) |
| Supabase (Free tier) | Managed | $0 (upgrade at $25/mo for more) |
| Artifact Registry | Storage | $1-2 |
| **Total (active)** | | **~$150-170/month** |
| **Total (idle ingestion VM)** | | **~$55-70/month** |

---

## Quick Reference

### Production URLs
- **Website**: https://canadagpt.ca
- **GraphQL**: https://canadagpt-graph-api-213428056473.us-central1.run.app/graphql
- **Supabase**: https://lbyqmjcqbwfeglfkiqpd.supabase.co

### VM Access
```bash
# Neo4j
gcloud compute ssh canadagpt-neo4j --zone=us-central1-a

# Ingestion
gcloud compute ssh canadagpt-ingestion --zone=us-central1-a
```

### Database Connections
```bash
# Neo4j (from Cloud Run internal network)
bolt://10.128.0.3:7687

# Supabase
postgresql://postgres:[password]@aws-0-us-west-1.pooler.supabase.com:6543/postgres
```

---

**Maintained By**: Claude Code
**Documentation**: `/Users/matthewdufresne/FedMCP/PRODUCTION_ARCHITECTURE.md`
**OAuth Setup**: `/Users/matthewdufresne/FedMCP/PRODUCTION_OAUTH_SETUP.md`
