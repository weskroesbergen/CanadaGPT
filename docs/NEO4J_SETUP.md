# Neo4j Setup Guide

This guide covers three ways to set up Neo4j for CanadaGPT development.

## Option 1: Neo4j Aura (Recommended for Quick Start) ☁️

**Best for:** Quick setup, no local installation required
**Cost:** Free tier (2M nodes, 200K relationships) - sufficient for testing
**Time:** 5 minutes

### Steps:

1. **Create Free Account**
   - Go to https://neo4j.com/cloud/platform/aura-graph-database/
   - Sign up for a free account
   - Click "Create New Instance"

2. **Configure Instance**
   - Database name: `canadagpt-dev`
   - Region: Choose closest to you
   - Instance type: **AuraDB Free**
   - Click "Create"

3. **Save Credentials**
   - Download the `.txt` file with credentials (one-time only!)
   - Note the connection URI (format: `neo4j+s://xxxxx.databases.neo4j.io`)
   - Note the password (you can't view it again)

4. **Apply Schema**
   - Open Neo4j Browser (click "Query" in Aura console)
   - Copy contents of `docs/neo4j-schema.cypher`
   - Paste into query box and run

5. **Configure Pipeline**
   ```bash
   cd packages/data-pipeline
   cp .env.example .env
   ```

   Edit `.env`:
   ```bash
   NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password_from_aura
   ```

6. **Test Connection**
   ```bash
   pip install -e .
   canadagpt-ingest --test
   ```

---

## Option 2: Docker (Recommended for Local Development) 🐳

**Best for:** Full control, persistent local database
**Prerequisites:** Docker Desktop installed and running
**Time:** 10 minutes

### Steps:

1. **Start Docker Desktop**
   - Ensure Docker is running on your machine

2. **Run Setup Script**
   ```bash
   ./scripts/setup-neo4j.sh
   ```

   This script will:
   - Start Neo4j in Docker
   - Apply schema automatically
   - Show connection details

3. **Connection Details**
   - Browser UI: http://localhost:7474
   - Bolt URI: `bolt://localhost:7687`
   - Username: `neo4j`
   - Password: `canadagpt2024`

4. **Configure Pipeline**
   ```bash
   cd packages/data-pipeline
   cp .env.example .env
   ```

   Edit `.env`:
   ```bash
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=canadagpt2024
   ```

5. **Test Connection**
   ```bash
   pip install -e .
   canadagpt-ingest --test
   ```

### Useful Docker Commands

```bash
# View logs
docker-compose logs -f neo4j

# Stop Neo4j (data persists)
docker-compose down

# Stop and remove all data (fresh start)
docker-compose down -v

# Restart Neo4j
docker-compose restart neo4j

# Access Cypher shell
docker exec -it canadagpt-neo4j cypher-shell -u neo4j -p canadagpt2024
```

---

## Option 3: Neo4j Desktop (Visual GUI) 🖥️

**Best for:** GUI-based management, visual query building
**Prerequisites:** Download Neo4j Desktop
**Time:** 15 minutes

### Steps:

1. **Download Neo4j Desktop**
   - Go to https://neo4j.com/download/
   - Download Neo4j Desktop for your OS
   - Install and launch

2. **Create Database**
   - Click "New" → "Create Project"
   - Name: `CanadaGPT`
   - Click "Add" → "Local DBMS"
   - Name: `canadagpt-dev`
   - Password: `canadagpt2024`
   - Version: 5.14 or later
   - Click "Create"

3. **Start Database**
   - Click "Start" on your database
   - Wait for status to show "Active"

4. **Apply Schema**
   - Click "Open" on your database (opens Neo4j Browser)
   - Copy contents of `docs/neo4j-schema.cypher`
   - Paste into query box and run

5. **Get Connection Details**
   - Click "..." on your database → "Connection Details"
   - Note the Bolt URL (usually `bolt://localhost:7687`)

6. **Configure Pipeline**
   ```bash
   cd packages/data-pipeline
   cp .env.example .env
   ```

   Edit `.env`:
   ```bash
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=canadagpt2024
   ```

7. **Test Connection**
   ```bash
   pip install -e .
   canadagpt-ingest --test
   ```

---

## Next Steps

Once Neo4j is set up and tested:

1. **Install Pipeline Package**
   ```bash
   cd /Users/matthewdufresne/FedMCP
   pip install -e packages/fedmcp  # Install FedMCP clients first
   pip install -e packages/data-pipeline  # Install pipeline
   ```

2. **Run Initial Data Load**
   ```bash
   # Test connection
   canadagpt-ingest --test

   # Load parliament data only (~30 minutes)
   canadagpt-ingest --parliament

   # OR: Full pipeline (~4-6 hours)
   canadagpt-ingest --full
   ```

3. **Verify Data**
   - Open Neo4j Browser
   - Run: `MATCH (n) RETURN labels(n), count(n)`
   - Should see MPs, Bills, Parties, etc.

---

## Troubleshooting

### "Connection refused" Error
- **Docker:** Ensure container is running: `docker ps`
- **Desktop:** Ensure database is started (green "Active" status)
- **Aura:** Check if instance is paused (Aura auto-pauses after inactivity)

### "Authentication failed" Error
- Verify password in `.env` matches your Neo4j password
- For Aura, check that you're using the password from the initial download

### "Out of memory" Error
- **Docker:** Increase memory in `docker-compose.yml` (heap size)
- **Desktop:** Go to Settings → Resources → Memory
- **Aura:** Free tier has limited resources, may need to upgrade

### Schema Errors
- Ensure you're running Neo4j 5.x or later (not 4.x)
- Try dropping all constraints first:
  ```cypher
  CALL apoc.schema.assert({}, {})
  ```

---

## Comparison Table

| Feature | Aura ☁️ | Docker 🐳 | Desktop 🖥️ |
|---------|---------|-----------|------------|
| **Setup Time** | 5 min | 10 min | 15 min |
| **Prerequisites** | None | Docker | Neo4j Desktop |
| **Cost** | Free tier | Free | Free |
| **Internet Required** | Yes | No | No |
| **Data Persistence** | Cloud | Local volume | Local |
| **Performance** | Good | Excellent | Excellent |
| **GUI** | Web only | Web only | Desktop + Web |
| **Best For** | Testing | Development | Visual exploration |

---

## Production Setup (Future)

For production deployment on GCP:
- Use the Terraform configuration in `/terraform`
- Provisions Neo4j Aura with Private Service Connect
- Full setup guide in `terraform/README.md`
