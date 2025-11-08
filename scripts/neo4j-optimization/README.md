# Neo4j Database Optimization Scripts

Comprehensive optimization scripts for the FedMCP Neo4j database after bulk data import completes.

## Overview

These scripts apply **constraints, indexes, and full-text search** to optimize query performance for MCP services, GraphQL API, and frontend queries.

**Expected Performance Gains:**
- ID lookups: 20-30x faster (50-100ms → 1-5ms)
- Filtered queries: 10-50x faster (1-5s → 50-200ms)
- Text searches: 50-100x faster (10-30s → 200-500ms)
- Aggregations: 5-10x faster (500-1000ms → 100-300ms)

## Scripts

### Phase 1: Critical (Required for Production)

**01-constraints-critical.cypher** (5-10 min)
- Creates uniqueness constraints on all primary entity IDs
- Provides data integrity + automatic index creation
- **Must run first** - other scripts depend on these

**02-indexes-high-frequency.cypher** (10-15 min)
- Indexes for commonly filtered properties
- Based on actual MCP tool query patterns
- Covers: MP, Bill, Vote, Expense, Lobbying, Petition queries

### Phase 2: Search & Analytics

**03-fulltext-indexes.cypher** (15-20 min)
- Full-text search indexes for semantic queries
- Enables fast keyword/text searches
- Covers: Bill titles, MP names, petitions, lobbying orgs

**04-composite-relationship-indexes.cypher** (5-10 min)
- Multi-column indexes for complex queries
- Relationship property indexes for graph traversals
- Covers: Expense queries, vote analysis, lobbying patterns

### Verification

**05-verification-queries.cypher**
- Health checks for all indexes
- Performance testing queries (PROFILE)
- Index usage statistics
- Expected vs actual performance comparisons

## Quick Start

### Option 1: Manual Execution (Recommended for First Time)

Connect to your Neo4j database and run scripts sequentially:

```bash
# 1. Connect to Neo4j (adjust credentials)
cypher-shell -a bolt://10.128.0.3:7687 -u neo4j -p canadagpt2024

# 2. Run Phase 1 scripts
:source 01-constraints-critical.cypher
:source 02-indexes-high-frequency.cypher

# 3. Verify Phase 1
:source 05-verification-queries.cypher

# 4. Run Phase 2 scripts
:source 03-fulltext-indexes.cypher
:source 04-composite-relationship-indexes.cypher

# 5. Final verification
:source 05-verification-queries.cypher
```

### Option 2: Automated Python Script

```bash
# Run all optimizations automatically
python apply_optimizations.py

# Or run specific phase
python apply_optimizations.py --phase 1
python apply_optimizations.py --phase 2
```

### Option 3: Single Combined Script

```bash
# Generate combined script
cat 01-*.cypher 02-*.cypher 03-*.cypher 04-*.cypher > all-optimizations.cypher

# Execute
cypher-shell -a bolt://10.128.0.3:7687 -u neo4j -p canadagpt2024 < all-optimizations.cypher
```

## Timing & Progress

| Script | Estimated Time | Impact |
|--------|----------------|--------|
| 01-constraints-critical.cypher | 5-10 min | 20-30x faster ID lookups |
| 02-indexes-high-frequency.cypher | 10-15 min | 10-50x faster filters |
| 03-fulltext-indexes.cypher | 15-20 min | 50-100x faster text search |
| 04-composite-relationship-indexes.cypher | 5-10 min | 5-20x faster complex queries |
| **Total** | **35-55 min** | **Overall: 10-100x faster** |

## Monitoring Progress

```cypher
-- Check index creation progress
CALL db.indexes()
YIELD name, state, populationPercent
WHERE state <> 'ONLINE' OR populationPercent < 100
RETURN name, state, populationPercent;

-- Expected: All indexes should show state='ONLINE', populationPercent=100
```

## Storage Impact

- Total index overhead: ~3-5GB
- Current database: ~3M nodes
- Recommendation: Upgrade to 8GB Neo4j instance if running on 4GB

## Troubleshooting

### Index Creation Fails

```cypher
-- Drop failed index and retry
DROP INDEX index_name IF EXISTS;
-- Then re-run the specific CREATE INDEX command
```

### Slow Index Creation

Index building is CPU and I/O intensive. For 3M nodes:
- Constraints: 5-10 minutes
- Range indexes: 10-15 minutes
- Full-text indexes: 15-20 minutes (largest)

This is normal. Monitor with:

```cypher
CALL dbms.listQueries()
YIELD query, elapsedTimeMillis
WHERE query CONTAINS 'INDEX'
RETURN query, elapsedTimeMillis;
```

### Memory Issues

If Neo4j runs out of memory during index creation:

1. Run scripts sequentially (not all at once)
2. Restart Neo4j between phases
3. Upgrade to larger instance (8GB recommended)

### Verify Index Usage

After applying optimizations, test that indexes are actually being used:

```cypher
-- Should show NodeUniqueIndexSeek (not NodeByLabelScan)
PROFILE
MATCH (m:MP {id: 'pierre-poilievre'})
RETURN m;
```

## Next Steps

After all optimizations are applied:

1. **Verify**: Run `05-verification-queries.cypher` to confirm all indexes online
2. **Test**: Run MCP tools and check performance improvements
3. **Monitor**: Set up query monitoring for production
4. **Cache**: Implement application-level caching (Redis) for repeated queries
5. **Pre-compute**: Consider materializing complex aggregations (Phase 3)

## Performance Expectations

### Before Optimization

```cypher
// MP lookup by ID: ~50-100ms
MATCH (m:MP {id: 'pierre-poilievre'}) RETURN m;

// Bill search: ~2-5 seconds
MATCH (b:Bill) WHERE toLower(b.title) CONTAINS 'climate' RETURN b;

// Hansard search: ~10-30 seconds
MATCH (s:Statement) WHERE s.content_en CONTAINS 'carbon tax' RETURN s;

// MP scorecard: ~500-1000ms
MATCH (mp:MP {id: 'pierre-poilievre'})
CALL { WITH mp MATCH (mp)-[:SPONSORED]->(b:Bill) RETURN count(b) }
...
```

### After Optimization

```cypher
// MP lookup by ID: ~1-5ms (20-30x faster)
MATCH (m:MP {id: 'pierre-poilievre'}) RETURN m;

// Bill search: ~50-200ms (20x faster)
CALL db.index.fulltext.queryNodes('bill_title_search', 'climate')
YIELD node, score RETURN node ORDER BY score DESC;

// Hansard search: ~200-500ms (50x faster)
CALL db.index.fulltext.queryNodes('statement_content_en', 'carbon tax')
YIELD node, score RETURN node ORDER BY score DESC;

// MP scorecard: ~100-300ms (5x faster)
MATCH (mp:MP {id: 'pierre-poilievre'})
CALL { WITH mp MATCH (mp)-[:SPONSORED]->(b:Bill) RETURN count(b) }
...
```

## Support

For issues or questions:
1. Check `05-verification-queries.cypher` for diagnostics
2. Review Neo4j logs for errors
3. Consult Neo4j documentation: https://neo4j.com/docs/cypher-manual/current/indexes/

## References

- Neo4j Constraints: https://neo4j.com/docs/cypher-manual/current/constraints/
- Neo4j Indexes: https://neo4j.com/docs/cypher-manual/current/indexes/
- Full-Text Indexes: https://neo4j.com/docs/cypher-manual/current/indexes/search-performance-indexes/full-text-indexes/
- Query Tuning: https://neo4j.com/docs/cypher-manual/current/query-tuning/
