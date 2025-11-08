# Complete Guide: FedMCP Data Ingestion VM

## Status
- ✅ VM Created: `canadagpt-ingestion` (n2-standard-4, 150GB disk)
- ✅ Dependencies Installed: PostgreSQL 14, Python 3.11, Git
- ✅ PostgreSQL Database Created: `openparliament_temp`
- ⏳ Repository Transfer: In progress (or complete by now)

## VM Details
- **Name**: canadagpt-ingestion
- **Zone**: us-central1-a
- **Internal IP**: 10.128.0.4
- **External IP**: 35.193.249.101
- **Machine Type**: n2-standard-4 (4 vCPU, 16GB RAM)
- **Disk**: 150GB SSD

## Quick Start: Complete the Setup

### Step 1: SSH into the VM
```bash
gcloud compute ssh canadagpt-ingestion --zone=us-central1-a --project=canada-gpt-ca
```

### Step 2: Extract the Repository (if transfer completed)
```bash
cd ~
tar xzf fedmcp-repo.tar.gz
cd FedMCP
```

**If transfer didn't complete**, clone directly:
```bash
cd ~
git clone https://github.com/MattDuf/FedMCP.git
cd FedMCP
```

### Step 3: Install Python Dependencies
```bash
# Install for data pipeline
cd ~/FedMCP/packages/data-pipeline
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install neo4j psycopg2-binary requests beautifulsoup4 lxml tqdm python-dotenv pandas

# Also install for root-level scripts
cd ~/FedMCP
pip install neo4j psycopg2-binary requests beautifulsoup4 lxml tqdm python-dotenv pandas
```

### Step 4: Configure Environment
```bash
cat > ~/FedMCP/packages/data-pipeline/.env << 'EOF'
# Neo4j GCP Connection (internal IP - fast and free!)
NEO4J_URI=bolt://10.128.0.3:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=canadagpt2024

# PostgreSQL (local)
POSTGRES_URI=postgresql://localhost:5432/openparliament_temp

# Environment
NODE_ENV=production
EOF
```

### Step 5: Test Connections
```bash
# Test Neo4j
python3 << 'PYEOF'
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://10.128.0.3:7687', auth=('neo4j', 'canadagpt2024'))
driver.verify_connectivity()
print('✅ Neo4j connected!')
driver.close()
PYEOF

# Test PostgreSQL
psql -U postgres -d openparliament_temp -c "SELECT version();"
```

### Step 6: Create Log Directory
```bash
mkdir -p ~/ingestion_logs
```

## Running the Full Ingestion

### Option A: Complete Historical Import (1901-Present) - 3-4 hours

**Prerequisites**: Download Lipad data manually (see below)

```bash
# Start a tmux session (so it keeps running if you disconnect)
tmux new -s ingestion

# Run complete import
cd ~/FedMCP
python3 test_complete_historical_import.py 2>&1 | tee ~/ingestion_logs/full_import.log

# Detach from tmux: Press Ctrl+b then d
# Reattach later: tmux attach -t ingestion
```

### Option B: Recent Data Only (2022-Present) - 20 minutes

**No prerequisites needed - starts immediately!**

```bash
cd ~/FedMCP
python3 test_recent_import.py 2>&1 | tee ~/ingestion_logs/recent_import.log
```

### Option C: Modern Bulk (1994-Present) - 90 minutes

```bash
cd ~/FedMCP
python3 test_bulk_import.py 2>&1 | tee ~/ingestion_logs/bulk_import.log
```

## Lipad Historical Data Download (For Option A Only)

### Manual Download Steps
1. On your local machine, visit: https://www.lipad.ca/data/
2. Download CSV format (2-5GB compressed)
3. Upload to GCS bucket:
   ```bash
   # From your Mac
   gsutil mb -p canada-gpt-ca -l us-central1 gs://canada-gpt-ca-lipad-data
   gsutil cp ~/Downloads/lipad_*.csv gs://canada-gpt-ca-lipad-data/
   ```

4. Download to VM:
   ```bash
   # On the VM
   mkdir -p ~/lipad_data
   gsutil -m cp gs://canada-gpt-ca-lipad-data/* ~/lipad_data/
   ```

## Adding Accountability Data (30 minutes)

After the main import, add lobbying, expenses, and petitions:

```bash
cd ~/FedMCP/packages/data-pipeline
source venv/bin/activate

# Import lobbying registry (~15 min, ~90MB download)
python3 -m fedmcp_pipeline.ingest.lobbying 2>&1 | tee ~/ingestion_logs/lobbying.log

# Import MP expenses (~10 min)
python3 -m fedmcp_pipeline.ingest.finances 2>&1 | tee ~/ingestion_logs/expenses.log

# Import petitions (~5 min)
python3 -m fedmcp_pipeline.ingest.parliament --petitions 2>&1 | tee ~/ingestion_logs/petitions.log
```

## Verification

### Check Database Statistics
```bash
# Connect to Neo4j and run these queries
python3 << 'PYEOF'
from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://10.128.0.3:7687', auth=('neo4j', 'canadagpt2024'))
session = driver.session()

# Node counts by label
result = session.run("MATCH (n) RETURN labels(n)[0] as label, count(*) as count ORDER BY count DESC")
print("\n=== Node Counts ===")
for record in result:
    print(f"{record['label']:20s}: {record['count']:>10,}")

# Relationship counts
result = session.run("MATCH ()-[r]->() RETURN type(r) as rel_type, count(*) as count ORDER BY count DESC")
print("\n=== Relationship Counts ===")
for record in result:
    print(f"{record['rel_type']:30s}: {record['count']:>10,}")

# Date coverage
result = session.run("MATCH (d:Debate) RETURN min(d.date) as earliest, max(d.date) as latest")
record = result.single()
if record:
    print(f"\n=== Debate Coverage ===")
    print(f"Earliest: {record['earliest']}")
    print(f"Latest: {record['latest']}")

session.close()
driver.close()
PYEOF
```

### Expected Results (Complete Historical Import)
```
Total Nodes: ~6,000,000
Total Relationships: ~7,000,000
Earliest Debate: 1901-XX-XX
Latest Debate: 2025-XX-XX
```

## Ongoing Operations

### Weekly Update Script

Create `~/FedMCP/update_weekly.sh`:
```bash
#!/bin/bash
LOG_FILE=~/ingestion_logs/update_$(date +%Y%m%d).log

echo "========================================="  | tee $LOG_FILE
echo "Weekly Update: $(date)" | tee -a $LOG_FILE
echo "=========================================" | tee -a $LOG_FILE

cd ~/FedMCP

# Update recent data
python3 test_recent_import.py 2>&1 | tee -a $LOG_FILE

# Update accountability data
cd packages/data-pipeline
source venv/bin/activate
python3 -m fedmcp_pipeline.ingest.lobbying --update 2>&1 | tee -a $LOG_FILE
python3 -m fedmcp_pipeline.ingest.finances --update 2>&1 | tee -a $LOG_FILE

echo "✅ Update complete: $(date)" | tee -a $LOG_FILE
```

Make it executable and schedule:
```bash
chmod +x ~/FedMCP/update_weekly.sh

# Add to crontab (runs every Sunday at 2 AM)
crontab -e
# Add this line:
0 2 * * 0 /home/$USER/FedMCP/update_weekly.sh
```

## Cost Management

### Option A: Keep VM Running
- **Cost**: ~$100/month
- **Benefit**: Always ready for updates
- **Best for**: Production with frequent updates

### Option B: Stop When Not Needed (RECOMMENDED)
- **Cost**: ~$5/month (disk storage only)
- **Benefit**: Much cheaper
- **Best for**: Occasional updates

```bash
# Stop VM (from your local machine)
gcloud compute instances stop canadagpt-ingestion --zone=us-central1-a --project=canada-gpt-ca

# Start when needed
gcloud compute instances start canadagpt-ingestion --zone=us-central1-a --project=canada-gpt-ca
```

## Troubleshooting

### Check Logs
```bash
# View ingestion logs
ls -lh ~/ingestion_logs/

# Tail a running import
tail -f ~/ingestion_logs/full_import.log
```

### Reattach to tmux Session
```bash
tmux list-sessions
tmux attach -t ingestion
```

### PostgreSQL Issues
```bash
# Restart PostgreSQL
sudo systemctl restart postgresql

# Check status
sudo systemctl status postgresql

# View PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-14-main.log
```

### Neo4j Connection Issues
```bash
# Check if Neo4j VM is running
gcloud compute instances describe canadagpt-neo4j --zone=us-central1-a --format="value(status)"

# Test connection
python3 -c "from neo4j import GraphDatabase; driver = GraphDatabase.driver('bolt://10.128.0.3:7687', auth=('neo4j', 'canadagpt2024')); driver.verify_connectivity(); print('OK')"
```

## Next Steps After Ingestion

1. **Verify data via GraphQL API**:
   ```bash
   curl -X POST https://canadagpt-graph-api-213428056473.us-central1.run.app/graphql \
     -H "Content-Type: application/json" \
     -d '{"query": "{ petitions(options: {limit: 5}) { petitionNumber title } }"}'
   ```

2. **Test frontend queries** at http://localhost:3000

3. **Stop VM to save costs** (if using Option B above)

4. **Schedule weekly updates** using cron job

5. **Monitor disk usage**:
   ```bash
   df -h
   du -sh ~/FedMCP
   du -sh /var/lib/postgresql
   ```

## Quick Reference

**SSH to VM**:
```bash
gcloud compute ssh canadagpt-ingestion --zone=us-central1-a --project=canada-gpt-ca
```

**Start tmux session**:
```bash
tmux new -s ingestion
```

**Detach from tmux**: `Ctrl+b` then `d`

**Reattach to tmux**:
```bash
tmux attach -t ingestion
```

**Check running processes**:
```bash
ps aux | grep python
```

**Disk usage**:
```bash
df -h
```

**Stop VM** (from local machine):
```bash
gcloud compute instances stop canadagpt-ingestion --zone=us-central1-a
```
