# 🚀 Local Development Setup Guide for CanadaGPT

## Prerequisites

**Required Software:**
- **Node.js** 20+ and **pnpm** package manager
- **Python** 3.11+
- **Docker** (for local Neo4j)
- **Git**

**Optional:**
- **Google Cloud SDK** (`gcloud` CLI) - for connecting to production Neo4j via SSH tunnel

---

## 📁 Environment Files Setup

There are **3 main .env files** needed for local development:

### 1. **Frontend** (`packages/frontend/.env.local`)
Location: `packages/frontend/.env.local`

This file already exists with all credentials configured. It contains:
- GraphQL API connection (`http://localhost:4000/graphql`)
- Supabase credentials (auth/storage)
- NextAuth OAuth providers (Google, GitHub, Facebook, LinkedIn)
- Anthropic API key
- Encryption keys for secure token storage

**✅ No action needed** - file is already configured.

---

### 2. **Graph API** (`packages/graph-api/.env`)
Location: `packages/graph-api/.env`

This file already exists with:
- Neo4j connection via SSH tunnel (`bolt://localhost:7687`)
- API keys for authentication
- CORS configuration for local development

**✅ No action needed** - file is already configured.

---

### 3. **Data Pipeline** (`packages/data-pipeline/.env`)
Location: `packages/data-pipeline/.env`

This file already exists with:
- Neo4j connection via SSH tunnel
- PostgreSQL connection (optional - for OpenParliament integration)
- Pipeline configuration

**✅ No action needed** - file is already configured.

---

## 🔧 Initial Setup Commands

```bash
# 1. Clone repository (if not already done)
cd /path/to/CanadaGPT

# 2. Install Node.js dependencies
pnpm install

# 3. Setup Python environment for data pipeline
cd packages/data-pipeline
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
cd ../..
```

---

## 🐳 Neo4j Database Setup

You have **two options** for Neo4j:

### **Option A: Connect to Production Database (Recommended)**

Use the provided `dev-tunnel.sh` script to create an SSH tunnel to the production Neo4j VM:

```bash
# Start SSH tunnel (runs in background)
./scripts/dev-tunnel.sh

# The tunnel forwards localhost:7687 → production Neo4j (10.128.0.3:7687)
# Credentials: neo4j / canadagpt2024
```

**✅ Advantage:** Access to real production data for development/testing.

---

### **Option B: Run Local Neo4j (Alternative)**

If you prefer a local Neo4j instance:

```bash
# Start local Neo4j with Docker
docker-compose up -d neo4j

# View logs
docker-compose logs -f neo4j

# Update .env files to use local Neo4j:
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USERNAME=neo4j
# NEO4J_PASSWORD=your_local_password
```

**⚠️ Note:** Local database will be empty initially. You'll need to run ingestion scripts to populate it.

---

## 🏃 Running the Development Servers

Once environment files and Neo4j are configured:

```bash
# Terminal 1: Start Frontend (Next.js)
pnpm dev:frontend
# → Frontend runs at http://localhost:3000

# Terminal 2: Start Graph API (GraphQL)
pnpm dev:api
# → GraphQL API runs at http://localhost:4000
# → GraphQL Playground: http://localhost:4000/graphql
```

**Or run both together:**
```bash
pnpm dev:frontend &
pnpm dev:api &
```

---

## 🧪 Testing Data Pipeline (Optional)

If you need to test data ingestion locally:

```bash
cd packages/data-pipeline
source venv/bin/activate

# Set environment variables (if using production tunnel)
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USERNAME=neo4j
export NEO4J_PASSWORD=canadagpt2024

# Run ingestion scripts
python scripts/daily-hansard-import.py     # Import Hansard debates
python run_mp_ingestion.py                 # Import MPs + committee memberships
python run_votes_ingestion.py              # Import votes
```

---

## 📋 Quick Reference

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | N/A |
| **GraphQL API** | http://localhost:4000/graphql | API Key in .env.local |
| **Neo4j (via tunnel)** | bolt://localhost:7687 | neo4j / canadagpt2024 |
| **Supabase** | https://pbxyhcdzdovsdlsyixsk.supabase.co | Keys in .env.local |

---

## 🔑 Environment File Locations Summary

All three required `.env` files are already configured at:

1. **Frontend**: `packages/frontend/.env.local` ✅
2. **Graph API**: `packages/graph-api/.env` ✅
3. **Data Pipeline**: `packages/data-pipeline/.env` ✅

**No manual .env file creation or editing is needed** - everything is already set up!

---

## 🛠️ Additional Commands

```bash
# Type checking
pnpm --filter @canadagpt/frontend type-check

# Build for production
pnpm build:all

# Run specific package
pnpm --filter @canadagpt/frontend dev
pnpm --filter @canadagpt/graph-api build

# View database status
./scripts/check-dev-status.sh
```

---

## ⚠️ Important Notes

1. **SSH Tunnel**: If using production database, ensure `./scripts/dev-tunnel.sh` is running before starting servers
2. **OAuth Providers**: All OAuth credentials (Google, GitHub, etc.) are already configured in `.env.local`
3. **API Keys**: All API keys are already set - no additional signup needed
4. **Port Conflicts**: Ensure ports 3000 (frontend) and 4000 (graph-api) are available

---

## 🚀 Quick Start (TL;DR)

```bash
# Start Neo4j tunnel
./scripts/dev-tunnel.sh

# Start frontend
pnpm dev:frontend

# Start API (in another terminal)
pnpm dev:api

# Visit http://localhost:3000
```

That's it! You now have a fully functional local development environment with access to production data.

---

## 📚 Additional Documentation

- **Full Project Documentation**: See `CLAUDE.md`
- **Deployment Guide**: See `DEPLOYMENT.md`
- **Mobile/Voice Features**: See `MOBILE_IMPLEMENTATION_GUIDE.md`
