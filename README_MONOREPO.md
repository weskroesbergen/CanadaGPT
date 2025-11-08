# CanadaGPT Monorepo

> AI-powered Canadian government accountability platform combining graph intelligence, comprehensive data sources, and an authoritative dark-themed interface.

## 🎯 Project Overview

**CanadaGPT** transforms raw Canadian government data into actionable intelligence through:

- **Neo4j Graph Database**: 1M+ nodes, 10M+ relationships linking MPs, bills, lobbying, spending
- **52+ MCP Tools**: Access to 11 official Canadian data sources
- **AI-Powered Analysis**: Trace money flows, detect conflicts of interest, analyze legislative patterns
- **Authoritative Design**: Canada dark theme with subtle neutrals (NYT Investigations aesthetic)

### Live Deployment
- **Production**: https://canadagpt.ca (coming soon)
- **API**: GraphQL endpoint at `/graphql`
- **MCP Server**: Available for Claude Desktop integration

---

## 📦 Repository Structure

```
FedMCP/
├── packages/
│   ├── fedmcp/              # Python MCP server (existing, production-ready)
│   ├── frontend/            # Next.js 15 web application
│   ├── graph-api/           # GraphQL API (Neo4j GraphQL Library)
│   ├── data-pipeline/       # Nightly ETL pipeline (Python)
│   └── design-system/       # Shared UI components (React + Tailwind)
│
├── terraform/               # GCP infrastructure as code
├── .github/workflows/       # CI/CD pipelines
├── docs/                    # Documentation
│
├── package.json             # Monorepo workspace configuration
└── README.md                # This file
```

### Package Dependency Graph

```
┌──────────────────┐
│  design-system   │  (Base: Tailwind config, Canada dark theme)
└────────┬─────────┘
         │
    ┌────┴────┬──────────────┐
    ↓         ↓              ↓
┌─────────┐ ┌──────────┐  ┌──────────┐
│frontend │ │graph-api │  │  fedmcp  │ (Independent)
└─────────┘ └──────────┘  └─────┬────┘
                                 │
                          ┌──────┴──────────┐
                          ↓
                    ┌──────────────┐
                    │data-pipeline │
                    └──────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Node.js** 20+ and npm 10+
- **Python** 3.11+
- **GCP Account** with billing enabled
- **Neo4j Aura** subscription (or local Neo4j instance)

### Installation

```bash
# 1. Clone repository
git clone https://github.com/yourusername/FedMCP.git
cd FedMCP

# 2. Install Node.js dependencies (all workspaces)
npm install

# 3. Install Python dependencies for MCP server
cd packages/fedmcp
pip install -e .
cd ../..

# 4. Install Python dependencies for data pipeline
cd packages/data-pipeline
pip install -r requirements.txt
cd ../..

# 5. Set up environment variables
cp .env.example .env
# Edit .env with your API keys:
# - NEO4J_URI
# - NEO4J_PASSWORD
# - CANLII_API_KEY (optional)
```

### Development Mode

```bash
# Run frontend (Next.js dev server)
npm run dev:frontend
# → http://localhost:3000

# Run GraphQL API
npm run dev:api
# → http://localhost:4000/graphql

# Run data pipeline (one-time manual sync)
cd packages/data-pipeline
python -m src.pipeline.nightly_update
```

### Building for Production

```bash
# Build all packages
npm run build:all

# Or build individually
npm run build:design-system  # First (others depend on it)
npm run build:api
npm run build:frontend
```

---

## 🎨 Design System - Canada Dark Theme

### Brand Identity

**Color Palette: Subtle Canada Neutrals**

```css
/* Backgrounds */
--bg-primary: #1E293B;      /* Dark slate */
--bg-secondary: #334155;    /* Lighter slate */
--bg-elevated: #475569;     /* Card backgrounds */
--bg-overlay: #0F172A;      /* Modals, overlays */

/* Accents */
--accent-red: #DC2626;      /* Muted Canadian red */
--accent-red-hover: #B91C1C;

/* Text */
--text-primary: #F1F5F9;    /* Off-white */
--text-secondary: #CBD5E1;  /* Muted gray */
--text-tertiary: #94A3B8;   /* Disabled/metadata */
```

**Typography: Authoritative & Clean**

- **Font Family**: Inter (display & body), JetBrains Mono (code)
- **Style**: NYT Investigations aesthetic - professional, serious, data-driven
- **Tone**: Government accountability is serious business

**Visual Elements**:
- Geometric maple leaf icon (SVG)
- Subtle Parliament silhouettes (hero sections only)
- Minimal borders, no shadows
- High contrast (WCAG AAA)

See `/packages/design-system` for full component library.

---

## 📊 Data Sources

### 11 Canadian Government APIs

| Source | Coverage | Records | Update Frequency |
|--------|----------|---------|------------------|
| **OpenParliament** | Bills, MPs, Votes, Debates | 10k+ bills, 338 MPs | Real-time |
| **LEGISinfo** | Detailed bill data | 5k+ bills | Daily |
| **OurCommons** | Hansard transcripts | 20+ years | Daily |
| **House Expenses** | MP office spending | 2020-present | Quarterly |
| **House Officers** | Leader/Speaker expenses | 2020-present | Quarterly |
| **Petitions** | Citizen petitions | 341+ active | Daily |
| **Lobbying Registry** | Corporate lobbying | 100k+ registrations, 350k+ communications | Weekly |
| **Federal Contracts** | Gov't procurement | 5-10M contracts | Monthly |
| **Grants & Contributions** | Program spending | 1M+ grants over $25k | Quarterly |
| **Political Contributions** | Party fundraising | 2004-present | Weekly |
| **CanLII** | Case law | Supreme Court, Federal Courts | Daily |

### Neo4j Graph Schema

**Nodes**: MP, Bill, Vote, Lobby Registration, Expense, Contract, Grant, Petition, Case

**Relationships**:
- `(MP)-[:VOTED]->(Vote)-[:SUBJECT_OF]->(Bill)`
- `(Lobbyist)-[:MET_WITH]->(MP)`
- `(Organization)-[:RECEIVED]->(Contract)`
- `(Organization)-[:DONATED]->(Party)`
- `(MP)-[:INCURRED]->(Expense)`

See `/docs/neo4j-schema.cypher` for full schema.

---

## 🔍 Key Features

### 1. Comprehensive MP Profiles

```graphql
query {
  mp(id: "pierre-poilievre") {
    name
    party
    riding
    billsSponsored { title status }
    expenses(fiscalYear: 2025) { total }
    lobbyingExposure {
      meetings { organization date topic }
    }
  }
}
```

**Shows**:
- Legislative activity (bills, votes, petitions)
- Quarterly expenses by category
- Lobbying meetings and exposure
- Committee memberships

### 2. Bill Tracking & Analysis

```graphql
query {
  bill(number: "C-11") {
    title
    status
    timeline { stage date }
    votes { date result breakdown }
    lobbiedByOrgs {
      name
      meetings { date topic }
    }
  }
}
```

**Shows**:
- Legislative timeline and status
- Voting record by party
- Lobbying activity on the bill
- Corporate influence patterns

### 3. Conflict of Interest Detection

```graphql
query {
  conflictOfInterest(billNumber: "C-18") {
    mp
    organization
    donated  # Amount donated to MP's party
    lobbied  # Met with MP about this bill
    votedYea # MP voted yes
    receivedContract  # Org received gov't contract
    suspicionLevel  # AI-calculated risk
  }
}
```

**Analyzes**:
- Donations → Lobbying → Voting patterns
- Contract awards after favorable votes
- Network clusters (shared lobbyists)

### 4. Money Flow Tracing

```graphql
query {
  traceMoneyFlow(entityName: "SNC-Lavalin") {
    politicalDonations { amount party year }
    lobbyingActivity { meetings bills }
    governmentContracts { amount department }
    timeline  # Chronological flow
  }
}
```

**Traces**:
- Corporation → Political donations → Lobbying → Contracts
- Multi-hop relationship paths in graph
- Temporal patterns (votes → contracts within 6 months)

---

## 🏗️ Architecture

### Technology Stack

**Frontend**:
- Next.js 15 (App Router, React Server Components)
- Tailwind CSS (Canada dark theme)
- TanStack Query + graphql-request
- Recharts (visualizations)

**API**:
- GraphQL Yoga + @neo4j/graphql
- Neo4j Bolt driver (connection pooling)
- Zod (validation)

**Database**:
- Neo4j Aura Professional (managed, GCP)
- 1M+ nodes, 10M+ relationships
- Nightly batch updates (2 AM ET)

**Infrastructure** (Google Cloud Platform):
- **Compute**: Cloud Run (serverless containers)
- **Database**: Neo4j Aura (Private Service Connect)
- **Networking**: VPC Connector + Cloud NAT
- **Secrets**: Secret Manager
- **CI/CD**: GitHub Actions + Cloud Build
- **IaC**: Terraform

### Deployment Diagram

```
┌─────────────┐
│   Internet  │
└──────┬──────┘
       │ HTTPS
       ▼
┌──────────────────────┐
│ Cloud Run: Frontend  │  (Next.js, public)
└──────────┬───────────┘
           │ Internal
           ▼
┌──────────────────────┐
│  Cloud Run: API      │  (GraphQL, VPC)
└──────────┬───────────┘
           │ Private Service Connect
           ▼
┌──────────────────────┐
│  Neo4j Aura          │  (Graph DB)
└──────────────────────┘

Cloud Scheduler (2 AM ET)
       │
       ▼
┌──────────────────────┐
│ Cloud Run Job:       │
│ Data Pipeline        │  (Python, fetches from 11 gov APIs)
└──────────────────────┘
```

---

## 📈 Development Roadmap

### Phase 1: Infrastructure ✅ (Week 1-2)
- [x] Monorepo restructuring
- [ ] GCP infrastructure (Terraform)
- [ ] Neo4j Aura setup + schema

### Phase 2: Data Pipeline (Week 2-3)
- [ ] Python ingestion scripts
- [ ] Batch UNWIND operations
- [ ] Initial 1M+ node load

### Phase 3: GraphQL API (Week 3-4)
- [ ] @neo4j/graphql integration
- [ ] Custom Cypher queries
- [ ] Deploy to Cloud Run

### Phase 4: Frontend (Week 4-6)
- [ ] Design system (Canada dark theme)
- [ ] Landing page + hero
- [ ] MP/Bill/Dashboard pages
- [ ] Deploy to Cloud Run

### Phase 5-8: Production (Week 6-8)
- [ ] Scheduled pipeline (Cloud Scheduler)
- [ ] CI/CD (GitHub Actions)
- [ ] Monitoring (Cloud Logging)
- [ ] Beta launch

---

## 🧪 Testing

```bash
# Run all tests
npm test

# Test individual packages
npm test --workspace=packages/frontend
npm test --workspace=packages/graph-api

# Python tests
cd packages/fedmcp
pytest tests/

cd packages/data-pipeline
pytest tests/
```

### E2E Testing

```bash
# Playwright (frontend)
cd packages/frontend
npx playwright test
```

---

## 📝 Documentation

- **Architecture**: `/docs/ARCHITECTURE.md`
- **API Reference**: `/docs/API.md` (GraphQL schema)
- **Design System**: `/packages/design-system/README.md`
- **Deployment**: `/docs/DEPLOYMENT.md` (GCP setup)
- **Neo4j Schema**: `/docs/neo4j-schema.cypher`

---

## 🤝 Contributing

This is currently a solo project preparing for beta launch. Contribution guidelines will be added post-launch.

For now:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with detailed description

---

## 📄 License

MIT License - see `LICENSE` file for details.

---

## 🙏 Acknowledgments

- **Data Sources**: OpenParliament.ca, Parliament of Canada, Elections Canada, CanLII
- **Inspiration**: ProPublica, NYT Investigations, OpenSecrets
- **Technology**: Anthropic (Claude), Neo4j, Google Cloud, Vercel

---

## 📧 Contact

- **Website**: https://canadagpt.ca
- **Email**: support@canadagpt.ca
- **Twitter**: @canadagpt

---

**Built with ❤️ for Canadian democracy and government accountability.**
