# CanadaGPT Developer Guide

Quick start guide for local development on the CanadaGPT platform.

## Quick Start

Get up and running in 3 commands:

```bash
# 1. Install dependencies
pnpm install

# 2. Start development environment (frontend + GraphQL API + Neo4j tunnel)
./scripts/dev-start.sh

# 3. Open your browser to http://localhost:3000
```

Press `Ctrl+C` to stop all services gracefully.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture Overview](#architecture-overview)
- [Development Environment](#development-environment)
- [Development Scripts](#development-scripts)
- [Development Workflow](#development-workflow)
- [Project Structure](#project-structure)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required

- **Node.js 18+** and **pnpm** - For running the frontend and GraphQL API
- **gcloud CLI** - For SSH tunnel to production Neo4j
  ```bash
  # Install gcloud CLI
  curl https://sdk.cloud.google.com | bash

  # Authenticate
  gcloud auth login

  # Set project
  gcloud config set project canada-gpt-ca
  ```

### Optional (for data pipeline work)

- **Python 3.9+** and **pip** - For data ingestion scripts
- **Docker** - For running local services (alternative to production tunnel)

## Architecture Overview

CanadaGPT is a full-stack application for exploring Canadian parliamentary data:

```
┌─────────────────────────────────────────────────────────────┐
│                    Development Environment                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Frontend (Next.js)          GraphQL API (Apollo)            │
│  Port: 3000                  Port: 4000                      │
│  ├─ React Components         ├─ Schema & Resolvers           │
│  ├─ Apollo Client            ├─ Neo4j Connection             │
│  └─ Tailwind CSS             └─ @neo4j/graphql              │
│         │                             │                      │
│         └──────────────┬──────────────┘                      │
│                        │                                      │
│                   SSH Tunnel                                 │
│                   Port: 7687                                 │
│                        │                                      │
│         ┌──────────────┴──────────────┐                      │
│         │                             │                      │
│  Neo4j Database (GCP)     Supabase (Production)             │
│  - MPs & Politicians      - User Profiles                    │
│  - Debates & Statements   - Bookmarks                        │
│  - Bills & Votes          - Preferences                      │
│  - Committees                                                │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

1. **Frontend** (`packages/frontend/`)
   - Next.js 14 with App Router
   - TypeScript + React 18
   - Tailwind CSS with design system
   - Apollo Client for GraphQL

2. **GraphQL API** (`packages/graph-api/`)
   - Apollo Server
   - @neo4j/graphql for schema generation
   - Custom Cypher queries and resolvers
   - Authentication via API keys

3. **Neo4j Database** (Production GCP VM)
   - Graph database with parliamentary data
   - Accessed via SSH tunnel for local development
   - Internal IP: `10.128.0.3`

4. **Supabase** (Production)
   - User authentication and profiles
   - Bookmarks and user preferences
   - PostgreSQL with Git-synced migrations

## Development Environment

### Environment Variables

The development environment uses **production databases** with local services:

**Frontend** (`packages/frontend/.env.local`):
```bash
# Next.js
NEXT_PUBLIC_API_URL=http://localhost:4000/graphql
NEXT_PUBLIC_API_KEY=<frontend_api_key>

# Supabase (Production)
NEXT_PUBLIC_SUPABASE_URL=https://pbxyhcdzdovsdlsyixsk.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon_key>

# NextAuth
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=<secret>
```

**GraphQL API** (`packages/graph-api/.env`):
```bash
# Neo4j (via SSH tunnel to production)
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=canadagpt2024

# Server
PORT=4000
NODE_ENV=development

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:5173

# Authentication
FRONTEND_API_KEY=<key>
PUBLIC_API_KEY=<key>
ADMIN_API_KEY=<key>
```

### Database Access

**Production Neo4j** (via SSH Tunnel):
- The development environment uses an SSH tunnel to access the production Neo4j database
- This avoids maintaining a separate local database
- All GraphQL queries run against real production data
- **READ-ONLY**: Be careful not to modify production data

**Production Supabase**:
- User authentication and preferences use production Supabase
- Migrations are Git-synced from `supabase/migrations/`
- Test accounts should use `+test` email suffix (e.g., `yourname+test@example.com`)

## Development Scripts

CanadaGPT includes several helper scripts for managing the development environment:

### `./scripts/dev-start.sh`

**One-command startup** for the entire development stack.

```bash
./scripts/dev-start.sh
```

**What it does:**
1. Checks for existing SSH tunnel on port 7687
2. Starts SSH tunnel to production Neo4j (if not running)
3. Starts GraphQL API on port 4000
4. Starts Frontend on port 3000
5. Displays service URLs and log file locations
6. Waits for `Ctrl+C` to shut down gracefully

**Logs:**
- GraphQL API: `/tmp/canadagpt-graphql.log`
- Frontend: `/tmp/canadagpt-frontend.log`

### `./scripts/dev-stop.sh`

**Graceful shutdown** of all development services.

```bash
./scripts/dev-stop.sh
```

**What it does:**
1. Stops Frontend (port 3000)
2. Stops GraphQL API (port 4000)
3. Stops SSH Tunnel (port 7687)
4. Cleans up lingering processes (pnpm, gcloud SSH)
5. Reports success/failure

### `./scripts/check-dev-status.sh`

**Health check** for all development services.

```bash
./scripts/check-dev-status.sh
```

**What it shows:**
- Process status (running/not running) with PIDs
- HTTP endpoint checks for GraphQL and Frontend
- Neo4j connectivity test
- Service URLs
- Log file locations
- Recent errors in logs
- Instructions for starting missing services

### `./scripts/dev-tunnel.sh`

**SSH tunnel** to production Neo4j (used by `dev-start.sh`).

```bash
# Run in foreground
./scripts/dev-tunnel.sh

# Run in background
./scripts/dev-tunnel.sh &
```

**What it does:**
1. Checks for port conflicts on 7687
2. Verifies gcloud authentication
3. Checks if Neo4j VM is running
4. Establishes SSH tunnel with keepalive
5. Forwards `localhost:7687` → `canadagpt-neo4j:7687`

## Development Workflow

### Starting Development

```bash
# 1. Start all services
./scripts/dev-start.sh

# 2. Check status (in another terminal)
./scripts/check-dev-status.sh

# 3. Open browser
open http://localhost:3000          # Frontend
open http://localhost:4000/graphql  # GraphQL Playground
```

### Making Changes

**Frontend Changes:**
- Edit files in `packages/frontend/src/`
- Next.js hot reload will update automatically
- Check browser console for errors
- Monitor logs: `tail -f /tmp/canadagpt-frontend.log`

**GraphQL Schema Changes:**
- Edit schema in `packages/graph-api/src/schema.ts`
- Server will restart automatically
- Test queries in GraphQL Playground
- Monitor logs: `tail -f /tmp/canadagpt-graphql.log`

**Database Schema Changes (Supabase):**
- Create migration in `supabase/migrations/`
- Supabase Git sync will auto-deploy to production
- Test locally using Supabase CLI (optional)

### Testing Changes

```bash
# Frontend type checking
cd packages/frontend
pnpm type-check

# GraphQL API type checking
cd packages/graph-api
pnpm type-check

# Build test (ensure production build works)
pnpm build
```

### Stopping Development

```bash
# Graceful shutdown
./scripts/dev-stop.sh

# Or use Ctrl+C in the dev-start.sh terminal
```

## Project Structure

```
CanadaGPT/
├── packages/
│   ├── frontend/              # Next.js frontend application
│   │   ├── src/
│   │   │   ├── app/          # Next.js App Router pages
│   │   │   ├── components/   # React components
│   │   │   ├── contexts/     # React contexts
│   │   │   ├── hooks/        # Custom React hooks
│   │   │   ├── lib/          # Utilities and helpers
│   │   │   └── styles/       # Global styles
│   │   └── public/           # Static assets
│   │
│   ├── graph-api/            # GraphQL API server
│   │   └── src/
│   │       ├── schema.ts     # GraphQL schema & resolvers
│   │       └── index.ts      # Apollo Server setup
│   │
│   ├── design-system/        # Shared UI components
│   │   └── src/
│   │       └── components/   # Reusable components
│   │
│   ├── data-pipeline/        # Data ingestion scripts
│   │   ├── fedmcp_pipeline/
│   │   │   ├── ingest/       # Ingestion modules
│   │   │   └── utils/        # Neo4j client, helpers
│   │   └── scripts/          # Ad-hoc import scripts
│   │
│   └── fedmcp/               # FedMCP server (parliamentary data API)
│       └── src/fedmcp/
│           ├── clients/      # API clients (OpenParliament, etc.)
│           └── server.py     # MCP server
│
├── scripts/                  # Development and deployment scripts
│   ├── dev-start.sh         # Start development environment
│   ├── dev-stop.sh          # Stop development environment
│   ├── dev-tunnel.sh        # SSH tunnel to Neo4j
│   ├── check-dev-status.sh  # Health check
│   └── deploy-*.sh          # Deployment scripts
│
├── supabase/
│   └── migrations/          # Database migrations (Git-synced)
│
├── CLAUDE.md                # Project documentation for Claude
└── README-DEV.md            # This file
```

## Common Tasks

### Querying Neo4j Data

**Via GraphQL Playground** (`http://localhost:4000/graphql`):

```graphql
# Get recent debates
query GetDebates {
  documents(
    where: { document_type: "D" }
    options: { limit: 10, sort: [{ date: DESC }] }
  ) {
    id
    date
    number
    statements(options: { limit: 5 }) {
      who_en
      content_en
    }
  }
}

# Get committees with latest meetings
query GetCommittees {
  committees {
    code
    name
    latestMeetingDate
    latestMeetingNumber
    totalMeetingsCount
  }
}
```

### Adding New Components

```bash
# Create component in design system (for shared components)
cd packages/design-system/src/components
mkdir MyComponent
touch MyComponent/MyComponent.tsx
touch MyComponent/index.ts

# Create component in frontend (for app-specific components)
cd packages/frontend/src/components
mkdir my-feature
touch my-feature/MyComponent.tsx
touch my-feature/index.ts
```

### Adding New GraphQL Queries

1. **Define query in schema** (`packages/graph-api/src/schema.ts`):
   ```typescript
   type Query {
     myNewQuery(param: String!): [Result!]!
       @cypher(
         statement: """
         MATCH (n:Node)
         WHERE n.field = $param
         RETURN n
         """
         columnName: "n"
       )
   }
   ```

2. **Add query to frontend** (`packages/frontend/src/lib/queries.ts`):
   ```typescript
   export const GET_MY_DATA = gql`
     query GetMyData($param: String!) {
       myNewQuery(param: $param) {
         id
         field
       }
     }
   `;
   ```

3. **Use in component**:
   ```typescript
   import { useQuery } from '@apollo/client';
   import { GET_MY_DATA } from '@/lib/queries';

   function MyComponent() {
     const { data, loading, error } = useQuery(GET_MY_DATA, {
       variables: { param: 'value' },
     });
     // ...
   }
   ```

### Creating Supabase Migrations

```bash
# Create new migration file
touch supabase/migrations/$(date +%Y%m%d%H%M%S)_my_migration.sql

# Edit the SQL file
# Git commit will trigger auto-deployment to production
```

### Updating User Preferences

When adding new user preferences:

1. **Create migration** (`supabase/migrations/YYYYMMDDHHMMSS_add_preference.sql`):
   ```sql
   ALTER TABLE public.user_preferences
   ADD COLUMN IF NOT EXISTS my_preference VARCHAR(50)
     DEFAULT 'default_value'
     CHECK (my_preference IN ('option1', 'option2'));
   ```

2. **Update context** (`packages/frontend/src/contexts/UserPreferencesContext.tsx`):
   ```typescript
   export interface UserPreferences {
     // ... existing fields
     myPreference: 'option1' | 'option2';
   }

   export const DEFAULT_PREFERENCES: UserPreferences = {
     // ... existing defaults
     myPreference: 'option1',
   };
   ```

3. **Use in components**:
   ```typescript
   import { useUserPreferences } from '@/contexts/UserPreferencesContext';

   function MyComponent() {
     const { preferences, updatePreferences } = useUserPreferences();

     const handleChange = async (value: string) => {
       await updatePreferences({ myPreference: value });
     };
     // ...
   }
   ```

## Troubleshooting

### SSH Tunnel Issues

**Problem:** "Port 7687 is already in use"

**Solution:**
```bash
# Find and kill existing process
lsof -ti:7687 | xargs kill -9

# Or use dev-stop.sh
./scripts/dev-stop.sh
```

**Problem:** "gcloud not authenticated"

**Solution:**
```bash
gcloud auth login
gcloud config set project canada-gpt-ca
```

**Problem:** "Could not fetch resource: neo4j-vm was not found"

**Solution:**
The VM name is `canadagpt-neo4j`, not `neo4j-vm`. The scripts use the correct name.

### GraphQL API Issues

**Problem:** "Failed to start GraphQL API"

**Solution:**
```bash
# Check logs
tail -f /tmp/canadagpt-graphql.log

# Common issues:
# 1. Neo4j connection failed - check SSH tunnel
# 2. Port 4000 in use - kill existing process
lsof -ti:4000 | xargs kill -9
```

**Problem:** GraphQL queries return empty results

**Solution:**
- Verify SSH tunnel is running: `lsof -i :7687`
- Test Neo4j connection: `timeout 2 bash -c "</dev/tcp/localhost/7687"`
- Check GraphQL schema matches database structure

### Frontend Issues

**Problem:** "Module not found" errors

**Solution:**
```bash
# Reinstall dependencies
pnpm install

# Clear Next.js cache
rm -rf packages/frontend/.next
```

**Problem:** "Can't resolve '@/lib/utils'"

**Solution:**
Use `@canadagpt/design-system` for the `cn` utility:
```typescript
import { cn } from '@canadagpt/design-system';
```

**Problem:** Authentication not working

**Solution:**
- Check Supabase environment variables in `.env.local`
- Verify `NEXTAUTH_URL` matches `http://localhost:3000`
- Clear browser cookies for localhost

### Process Management

**Problem:** Services won't stop

**Solution:**
```bash
# Nuclear option - kill all related processes
pkill -f "pnpm dev"
pkill -f "gcloud compute ssh"
lsof -ti:3000 | xargs kill -9
lsof -ti:4000 | xargs kill -9
lsof -ti:7687 | xargs kill -9
```

**Problem:** "Address already in use"

**Solution:**
```bash
# Check what's using the port
lsof -i :3000
lsof -i :4000
lsof -i :7687

# Kill specific process
kill -9 <PID>
```

### Health Check

**When in doubt, run the status check:**
```bash
./scripts/check-dev-status.sh
```

This will diagnose most common issues and provide specific remediation steps.

## Additional Resources

- **Main README**: See `README.md` for project overview
- **CLAUDE.md**: Comprehensive project documentation
- **GraphQL Playground**: `http://localhost:4000/graphql` (when running)
- **Supabase Dashboard**: `https://supabase.com/dashboard/project/pbxyhcdzdovsdlsyixsk`

## Getting Help

1. Check this guide first
2. Run `./scripts/check-dev-status.sh` for diagnostics
3. Check log files in `/tmp/canadagpt-*.log`
4. Review CLAUDE.md for architecture details
5. Create an issue in the GitHub repository

---

**Happy coding!**
