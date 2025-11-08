# CanadaGPT Packages

This directory contains all packages for the CanadaGPT monorepo.

## Package Structure

### `fedmcp/` (Python)
**FedMCP Server** - Model Context Protocol server providing 52+ tools for Canadian government data.

- **Language**: Python 3.11+
- **Purpose**: MCP server for Claude Desktop integration
- **Status**: ✅ Production (existing codebase)
- **Tools**: 52 tools across 11 Canadian government APIs
- **Build**: `cd fedmcp && pip install -e .`

### `frontend/` (TypeScript/Next.js)
**CanadaGPT Frontend** - Public-facing web application with Canada dark theme.

- **Language**: TypeScript + Next.js 15 (App Router)
- **Purpose**: User interface for graph-powered government accountability
- **Status**: 🚧 In Development
- **Features**: MP profiles, bill tracking, lobbying analysis, expense tracking
- **Build**: `npm run build:frontend`
- **Dev**: `npm run dev:frontend`

### `graph-api/` (TypeScript/Node.js)
**GraphQL API** - Graph database API layer using Neo4j GraphQL Library.

- **Language**: TypeScript + GraphQL Yoga
- **Purpose**: API layer over Neo4j graph database
- **Status**: 🚧 In Development
- **Features**: Auto-generated CRUD + custom Cypher queries
- **Build**: `npm run build:api`
- **Dev**: `npm run dev:api`

### `data-pipeline/` (Python)
**Data Ingestion Pipeline** - Nightly batch ETL from government APIs to Neo4j.

- **Language**: Python 3.11+
- **Purpose**: Scheduled data synchronization (2 AM ET daily)
- **Status**: 🚧 In Development
- **Sources**: 11 Canadian government APIs
- **Run**: Deployed as Cloud Run Job (scheduled via Cloud Scheduler)

### `design-system/` (TypeScript/React)
**Canada Dark Theme Design System** - Shared UI components and styling.

- **Language**: TypeScript + React + Tailwind CSS
- **Purpose**: Reusable components for authoritative Canadian government aesthetic
- **Status**: 🚧 In Development
- **Theme**: Subtle Canada neutrals (dark slate + muted red)
- **Components**: MapleLeaf icon, Parliament imagery, Cards, Buttons, Metrics
- **Build**: `npm run build:design-system`

## Development Workflow

### Initial Setup
```bash
# Install Node.js dependencies (workspaces)
npm install

# Install Python dependencies for fedmcp
cd packages/fedmcp
pip install -e .

# Install Python dependencies for data-pipeline
cd packages/data-pipeline
pip install -r requirements.txt
```

### Running Services Locally

```bash
# Frontend (Next.js dev server)
npm run dev:frontend
# → http://localhost:3000

# GraphQL API
npm run dev:api
# → http://localhost:4000/graphql

# Data pipeline (manual run)
cd packages/data-pipeline
python -m src.pipeline.nightly_update
```

### Building for Production

```bash
# Build all packages
npm run build:all

# Or build individually
npm run build:design-system
npm run build:api
npm run build:frontend
```

## Package Dependencies

```
design-system (base)
    ↓
    ├─→ frontend (depends on design-system)
    └─→ graph-api (independent, but shares types)

fedmcp (independent Python)
    ↓
data-pipeline (imports fedmcp clients)
```

## Technology Stack

### Frontend Stack
- **Framework**: Next.js 15 (App Router, React Server Components)
- **Styling**: Tailwind CSS (Canada dark theme)
- **Data Fetching**: TanStack Query + graphql-request
- **Charts**: Recharts
- **Deployment**: Google Cloud Run (containerized)

### API Stack
- **GraphQL**: GraphQL Yoga + @neo4j/graphql
- **Database**: Neo4j Aura Professional (graph database)
- **Validation**: Zod
- **Deployment**: Google Cloud Run (containerized)

### Data Pipeline Stack
- **Language**: Python 3.11
- **Neo4j Driver**: neo4j-driver (official)
- **Scheduling**: Cloud Scheduler → Cloud Run Jobs
- **Sources**: FedMCP clients (reused from existing codebase)

### Infrastructure
- **Cloud Provider**: Google Cloud Platform
- **Compute**: Cloud Run (serverless containers)
- **Database**: Neo4j Aura (managed graph database)
- **Networking**: VPC Connector + Private Service Connect
- **Secrets**: Secret Manager
- **CI/CD**: GitHub Actions + Cloud Build
- **IaC**: Terraform

## License

MIT
