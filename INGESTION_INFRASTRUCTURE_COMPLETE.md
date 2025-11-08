# FedMCP Data Ingestion Infrastructure - COMPLETE ✅

## Summary

Your complete data ingestion infrastructure is now operational on GCP! The VM is fully configured and ready to load 120+ years of Canadian parliamentary data into Neo4j.

## What Was Built

### 1. Ingestion VM (canadagpt-ingestion)
- **Machine Type**: n2-standard-4 (4 vCPU, 16GB RAM, 150GB SSD)
- **Zone**: us-central1-a
- **Internal IP**: 10.128.0.4 (connects to Neo4j via internal network)
- **External IP**: 35.193.249.101

### 2. Fully Configured Environment
✅ PostgreSQL 14 installed with `openparliament_temp` database
✅ Python 3.11 with virtual environment
✅ All Python dependencies installed (neo4j, psycopg2-binary, pandas, etc.)
✅ FedMCP repository cloned (2.0GB)
✅ Environment variables configured (.env file)
✅ Neo4j connection tested (bolt://10.128.0.3:7687)
✅ Log directory created (~/ingestion_logs/)

### 3. Automated Scripts Created

**Master Ingestion Script**: `~/FedMCP/scripts/run-full-ingestion.sh`
- Runs complete historical import (1901-present with Lipad)
- Includes all accountability data (lobbying, expenses, petitions)
- Logs everything to timestamped files
- Estimated time: 3-4 hours

**Weekly Update Script**: `~/FedMCP/scripts/update-recent-data.sh`
- Updates recent parliamentary data (2022-present)
- Updates lobbying registry, expenses, and petitions
- Can be automated with cron for ongoing operations
- Estimated time: 20 minutes

### 4. Documentation
- Complete guide on VM: `~/README_INGESTION.md`
- Setup guide (this file): `INGESTION_INFRASTRUCTURE_COMPLETE.md`
- Original planning doc: `INGESTION_VM_COMPLETE_GUIDE.md`

## Next Steps: Choose Your Option

### Option A: Quick Start (1994-Present) - 90 minutes
**No prerequisites needed - start immediately!**

```bash
# 1. SSH to the VM
gcloud compute ssh canadagpt-ingestion --zone=us-central1-a --project=canada-gpt-ca

# 2. Start a tmux session (so it keeps running if you disconnect)
tmux new -s ingestion

# 3. Run the modern bulk import
cd ~/FedMCP
source packages/data-pipeline/venv/bin/activate
python3 test_bulk_import.py 2>&1 | tee ~/ingestion_logs/bulk_import.log

# 4. Detach from tmux (Ctrl+b then d)
# You can disconnect from SSH - it will keep running!
# To reattach later: tmux attach -t ingestion
```

**Expected Results:**
- ~3,000,000 nodes
- Parliamentary data from 1994-2025
- Debates, MPs, Bills, Votes, Committees
- Plus lobbying, expenses, petitions

### Option B: Complete History (1901-Present) - 3-4 hours
**Requires Lipad data download first**

#### Step 1: Download Lipad Data (on your Mac)
```bash
# Visit https://www.lipad.ca/data/ and download CSV format
# Then upload to Google Cloud Storage:

gsutil mb -p canada-gpt-ca -l us-central1 gs://canada-gpt-ca-lipad-data
gsutil cp ~/Downloads/lipad_*.csv gs://canada-gpt-ca-lipad-data/
```

#### Step 2: Run Complete Import (on VM)
```bash
# SSH to VM
gcloud compute ssh canadagpt-ingestion --zone=us-central1-a --project=canada-gpt-ca

# Download Lipad data from GCS
mkdir -p ~/lipad_data
gsutil -m cp gs://canada-gpt-ca-lipad-data/* ~/lipad_data/

# Start tmux and run complete import
tmux new -s ingestion
cd ~/FedMCP
bash scripts/run-full-ingestion.sh

# Detach: Ctrl+b then d
```

**Expected Results:**
- ~6,000,000 nodes
- Parliamentary data from 1901-2025
- Complete historical coverage
- Plus lobbying, expenses, petitions

## Monitoring Progress

### Check Running Status
```bash
# Reattach to tmux
gcloud compute ssh canadagpt-ingestion --zone=us-central1-a --project=canada-gpt-ca
tmux attach -t ingestion

# Or check processes
ps aux | grep python
```

### View Logs
```bash
# SSH to VM
gcloud compute ssh canadagpt-ingestion --zone=us-central1-a --project=canada-gpt-ca

# List logs
ls -lh ~/ingestion_logs/

# Tail current log
tail -f ~/ingestion_logs/*.log
```

### Query Neo4j Stats
```bash
# SSH to VM and run Python
gcloud compute ssh canadagpt-ingestion --zone=us-central1-a --project=canada-gpt-ca

cd ~/FedMCP
source packages/data-pipeline/venv/bin/activate
python3 << 'EOF'
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://10.128.0.3:7687', auth=('neo4j', 'canadagpt2024'))
session = driver.session()

# Node counts by label
result = session.run("MATCH (n) RETURN labels(n)[0] as label, count(*) as count ORDER BY count DESC LIMIT 20")
print("\nTop Node Types:")
for record in result:
    print(f"  {record['label']:20s}: {record['count']:>10,}")

# Total
result = session.run("MATCH (n) RETURN count(n) as total")
print(f"\nTotal Nodes: {result.single()['total']:,}")

session.close()
driver.close()
EOF
```

## Cost Management

### Stop VM When Not Needed (RECOMMENDED)
Saves money - only pay for disk storage (~$5/month) instead of compute (~$100/month)

```bash
# Stop VM (from your Mac)
gcloud compute instances stop canadagpt-ingestion --zone=us-central1-a --project=canada-gpt-ca

# Start when needed
gcloud compute instances start canadagpt-ingestion --zone=us-central1-a --project=canada-gpt-ca
```

### Weekly Updates
After the initial load completes, run weekly updates to keep data current:

```bash
# SSH to VM
gcloud compute ssh canadagpt-ingestion --zone=us-central1-a --project=canada-gpt-ca

# Run update script
cd ~/FedMCP
bash scripts/update-recent-data.sh
```

**Automate with Cron** (optional):
```bash
# SSH to VM
gcloud compute ssh canadagpt-ingestion --zone=us-central1-a --project=canada-gpt-ca

# Add weekly cron job (Sundays at 2 AM)
crontab -e
# Add this line:
0 2 * * 0 /home/$USER/FedMCP/scripts/update-recent-data.sh
```

## Verifying Success

After the import completes:

1. **Check Neo4j node count** (should be 3M or 6M depending on option)
2. **Test GraphQL API**:
   ```bash
   curl -X POST https://canadagpt-graph-api-213428056473.us-central1.run.app/graphql \
     -H "Content-Type: application/json" \
     -d '{"query": "{ politicians(options: {limit: 5}) { name party } }"}'
   ```
3. **Test frontend** at http://localhost:3000 (if running locally)
4. **Check logs** for any errors in `~/ingestion_logs/`

## Troubleshooting

### Neo4j Connection Fails
```bash
# SSH to VM and test connection
cd ~/FedMCP
source packages/data-pipeline/venv/bin/activate
python3 << 'EOF'
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://10.128.0.3:7687', auth=('neo4j', 'canadagpt2024'))
driver.verify_connectivity()
print('✅ Connected!')
driver.close()
EOF
```

### PostgreSQL Not Running
```bash
# SSH to VM
sudo systemctl status postgresql
sudo systemctl restart postgresql
```

### Out of Disk Space
```bash
# Check disk usage
df -h
du -sh ~/FedMCP
du -sh /var/lib/postgresql

# Clean up old logs
rm ~/ingestion_logs/old_*.log
```

### Import Fails Mid-Way
```bash
# Check logs for specific error
tail -100 ~/ingestion_logs/*.log

# Most imports are idempotent - safe to re-run
cd ~/FedMCP
bash scripts/run-full-ingestion.sh
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    GCP Infrastructure                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────┐         ┌─────────────────────┐   │
│  │ canadagpt-ingestion │         │  canadagpt-neo4j    │   │
│  │ (n2-standard-4)     │─────────│  (e2-standard-8)    │   │
│  │                     │ Internal│                     │   │
│  │ - PostgreSQL temp   │  VPC    │ - Neo4j 5.x         │   │
│  │ - Python scripts    │         │ - 370k nodes        │   │
│  │ - Data ingestion    │         │ → millions soon     │   │
│  └─────────────────────┘         └─────────────────────┘   │
│           ↑                                ↑                │
│           │                                │                │
│           │                                │                │
│  ┌─────────────────────┐         ┌─────────────────────┐   │
│  │  Data Sources       │         │  GraphQL API        │   │
│  │                     │         │  (Cloud Run)        │   │
│  │ - OpenParliament    │         │                     │   │
│  │ - LEGISinfo         │         │ https://canada...   │   │
│  │ - Lipad             │         │ /graphql            │   │
│  │ - Lobbying Registry │         │                     │   │
│  └─────────────────────┘         └─────────────────────┘   │
│                                            ↓                │
│                                   ┌─────────────────────┐   │
│                                   │  Next.js Frontend   │   │
│                                   │  (your Mac / Cloud) │   │
│                                   └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Quick Reference Commands

**SSH to VM:**
```bash
gcloud compute ssh canadagpt-ingestion --zone=us-central1-a --project=canada-gpt-ca
```

**Start tmux:**
```bash
tmux new -s ingestion
```

**Detach from tmux:** `Ctrl+b` then `d`

**Reattach to tmux:**
```bash
tmux attach -t ingestion
```

**Stop VM:**
```bash
gcloud compute instances stop canadagpt-ingestion --zone=us-central1-a --project=canada-gpt-ca
```

**Start VM:**
```bash
gcloud compute instances start canadagpt-ingestion --zone=us-central1-a --project=canada-gpt-ca
```

## Files on VM

```
~/
├── FedMCP/                          # Repository (2.0GB)
│   ├── packages/data-pipeline/      # Main data pipeline
│   │   ├── venv/                   # Python virtual environment
│   │   └── .env                    # Neo4j connection config
│   ├── scripts/
│   │   ├── run-full-ingestion.sh   # Master ingestion script
│   │   └── update-recent-data.sh   # Weekly update script
│   ├── test_bulk_import.py         # 1994-present import
│   ├── test_complete_historical_import.py  # 1901-present
│   └── test_recent_import.py       # 2022-present only
├── ingestion_logs/                 # All import logs
├── lipad_data/                     # Lipad historical data (if downloaded)
├── fedmcp-repo.tar.gz             # Original upload (can delete)
└── README_INGESTION.md            # This guide
```

## Success! 🎉

Your data ingestion infrastructure is **fully operational**. You can now:

1. **Start importing data** using Option A or B above
2. **Monitor progress** via tmux, logs, or Neo4j queries
3. **Verify results** through GraphQL API or frontend
4. **Schedule weekly updates** to keep data current
5. **Manage costs** by stopping VM when not in use

The complete pipeline is ready to populate Neo4j with decades of Canadian parliamentary data, accountability records, and ongoing updates.

---

**Infrastructure Status**: ✅ COMPLETE
**VM Status**: 🟢 RUNNING
**Neo4j Connection**: ✅ TESTED
**Ready to Ingest**: ✅ YES
