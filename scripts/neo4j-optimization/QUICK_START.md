# Quick Start: Neo4j Optimization

Execute these commands after the bulk import completes to optimize your Neo4j database.

## Prerequisites

- Bulk import must be complete (~3M nodes loaded)
- Neo4j must be running and accessible
- Python 3.11+ with neo4j and python-dotenv packages

## Option 1: Automated (Recommended)

```bash
cd /Users/matthewdufresne/FedMCP/scripts/neo4j-optimization

# Install dependencies
pip install neo4j python-dotenv

# Run all optimizations (35-55 minutes)
python apply_optimizations.py

# Or run phase by phase
python apply_optimizations.py --phase 1  # Critical (15-25 min)
python apply_optimizations.py --phase 2  # Search/Analytics (20-30 min)

# Verify
python apply_optimizations.py --verify
```

## Option 2: Manual Cypher Shell

```bash
# Connect to Neo4j
cypher-shell -a bolt://10.128.0.3:7687 -u neo4j -p canadagpt2024

# Run scripts sequentially
:source /Users/matthewdufresne/FedMCP/scripts/neo4j-optimization/01-constraints-critical.cypher
:source /Users/matthewdufresne/FedMCP/scripts/neo4j-optimization/02-indexes-high-frequency.cypher
:source /Users/matthewdufresne/FedMCP/scripts/neo4j-optimization/03-fulltext-indexes.cypher
:source /Users/matthewdufresne/FedMCP/scripts/neo4j-optimization/04-composite-relationship-indexes.cypher

# Verify
:source /Users/matthewdufresne/FedMCP/scripts/neo4j-optimization/05-verification-queries.cypher
```

## Option 3: Python from VM

```bash
# SSH to Neo4j VM (if needed)
gcloud compute ssh canadagpt-neo4j --zone=us-central1-a --project=canada-gpt-ca

# Upload scripts
cd ~
git clone https://github.com/MattDuf/FedMCP.git
# Or: gcloud compute scp --recurse scripts/neo4j-optimization canadagpt-neo4j:~/

# Run locally on VM
cd ~/neo4j-optimization
python3 apply_optimizations.py --uri bolt://localhost:7687
```

## Monitoring Progress

```bash
# Check index creation status
cypher-shell -a bolt://10.128.0.3:7687 -u neo4j -p canadagpt2024 \
  -c "CALL db.indexes() YIELD name, state, populationPercent WHERE state <> 'ONLINE' RETURN name, state, populationPercent;"

# Expected: All indexes show state='ONLINE', populationPercent=100
```

## Timeline

| Phase | Time | Description |
|-------|------|-------------|
| Phase 1 | 15-25 min | Constraints + High-frequency indexes |
| Phase 2 | 20-30 min | Full-text + Composite indexes |
| **Total** | **35-55 min** | Complete optimization |

## Expected Results

**Performance Improvements:**
- ID lookups: 50-100ms → 1-5ms (20-30x)
- Filtered queries: 1-5s → 50-200ms (10-50x)
- Text searches: 10-30s → 200-500ms (50-100x)
- Aggregations: 500-1000ms → 100-300ms (5-10x)

**Storage Impact:**
- Index overhead: ~3-5GB
- Total database size: ~10-12GB (from ~7GB before indexes)

## Verification Commands

```bash
# Quick health check
python apply_optimizations.py --verify

# Detailed verification
cypher-shell -a bolt://10.128.0.3:7687 -u neo4j -p canadagpt2024 \
  < /Users/matthewdufresne/FedMCP/scripts/neo4j-optimization/05-verification-queries.cypher
```

## Test Query Performance

```cypher
// Test MP lookup (should be ~1-5ms)
PROFILE MATCH (m:MP {id: 'pierre-poilievre'}) RETURN m;

// Test bill search (should be ~50-200ms)
PROFILE CALL db.index.fulltext.queryNodes('bill_title_search', 'climate change')
YIELD node, score RETURN node LIMIT 10;

// Verify index usage (should show "NodeIndexSeek" not "NodeByLabelScan")
EXPLAIN MATCH (m:MP {party: 'Conservative'}) RETURN m LIMIT 10;
```

## Troubleshooting

### Slow Index Creation
- Normal for 3M nodes
- Constraints: 5-10 min
- Range indexes: 10-15 min
- Full-text indexes: 15-20 min

### Memory Issues
Run phases sequentially with restarts:
```bash
python apply_optimizations.py --phase 1
# Restart Neo4j if needed
python apply_optimizations.py --phase 2
```

### Connection Errors
Check Neo4j is running and accessible:
```bash
gcloud compute instances describe canadagpt-neo4j --zone=us-central1-a --format="value(status)"
# Should show: RUNNING
```

## Next Steps

After optimization completes:

1. **Test MCP tools** - Verify query performance improvements
2. **Monitor production** - Set up query logging
3. **Consider upgrades** - May need 8GB Neo4j instance
4. **Enable caching** - Redis for repeated LLM queries
5. **Pre-compute metrics** - Phase 3 optimization (optional)

## Support

See full documentation in `README.md` for:
- Detailed script descriptions
- Performance benchmarks
- Advanced troubleshooting
- Phase 3 optimization plans
