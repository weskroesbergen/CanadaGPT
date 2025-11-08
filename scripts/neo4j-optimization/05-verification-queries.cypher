// ============================================================
// Verification & Performance Testing Queries
// ============================================================
// Run these after all optimizations to verify:
// 1. All indexes are online
// 2. Indexes are being used correctly
// 3. Performance improvements are realized
// ============================================================

// ============================================================
// 1. Index Health Check
// ============================================================

// Show all indexes and their status
CALL db.indexes()
YIELD name, type, state, populationPercent, lastRead, readCount
ORDER BY type, name
RETURN
  type,
  name,
  state,
  populationPercent,
  lastRead,
  readCount;

// Count indexes by type
CALL db.indexes()
YIELD type
RETURN type, count(*) as count
ORDER BY type;

// Find any failed or populating indexes
CALL db.indexes()
YIELD name, state, populationPercent
WHERE state <> 'ONLINE' OR populationPercent < 100
RETURN name, state, populationPercent;

// ============================================================
// 2. Constraint Verification
// ============================================================

// Show all constraints
SHOW CONSTRAINTS;

// Count constraints by type
SHOW CONSTRAINTS
YIELD name, type
RETURN type, count(*) as count;

// ============================================================
// 3. Database Statistics
// ============================================================

// Total nodes and relationships
MATCH (n)
RETURN count(n) as total_nodes;

MATCH ()-[r]->()
RETURN count(r) as total_relationships;

// Nodes by label (top 20)
MATCH (n)
RETURN labels(n)[0] as label, count(*) as count
ORDER BY count DESC
LIMIT 20;

// Relationships by type (top 20)
MATCH ()-[r]->()
RETURN type(r) as relationship, count(*) as count
ORDER BY count DESC
LIMIT 20;

// ============================================================
// 4. Performance Testing - BEFORE vs AFTER
// ============================================================

// Test 1: MP Lookup by ID
// BEFORE optimization: ~50-100ms (label scan)
// AFTER optimization: ~1-5ms (constraint index)
PROFILE
MATCH (m:MP {id: 'pierre-poilievre'})
RETURN m;
// Verify: Should show "NodeUniqueIndexSeek" (not NodeByLabelScan)

// Test 2: Bill Search with Filter
// BEFORE: ~2-5 seconds (full scan)
// AFTER: ~50-200ms (range index)
PROFILE
MATCH (b:Bill)
WHERE b.status = 'Passed' AND b.session = '44-1'
RETURN b
LIMIT 10;
// Verify: Should show "NodeIndexSeek" on bill_session_status

// Test 3: Full-Text Search
// BEFORE: ~10-30 seconds (regex/CONTAINS)
// AFTER: ~200-500ms (fulltext index)
PROFILE
CALL db.index.fulltext.queryNodes('bill_title_search', 'climate change')
YIELD node, score
RETURN node.title, score
ORDER BY score DESC
LIMIT 10;
// Verify: Should show "NodeIndexFullTextSeek"

// Test 4: MP Expenses by Fiscal Year
// BEFORE: ~500-1000ms (full expense scan)
// AFTER: ~50-100ms (composite index)
PROFILE
MATCH (e:Expense {mp_id: 'pierre-poilievre', fiscal_year: 2024})
RETURN sum(e.amount) as total;
// Verify: Should show "NodeIndexSeek" on mp_fiscal_year

// Test 5: Relationship Filtering
// BEFORE: ~1-2 seconds (scan all VOTED relationships)
// AFTER: ~50-100ms (relationship index)
PROFILE
MATCH (:MP {id: 'pierre-poilievre'})-[v:VOTED {position: 'yea'}]->(vote:Vote)
WHERE vote.date > date('2024-01-01')
RETURN count(v);
// Verify: Should show "DirectedRelationshipIndexSeek"

// ============================================================
// 5. Slow Query Detection
// ============================================================

// Find currently running queries taking > 1 second
CALL dbms.listQueries()
YIELD queryId, elapsedTimeMillis, query, username
WHERE elapsedTimeMillis > 1000
RETURN queryId, elapsedTimeMillis, substring(query, 0, 100) as query_preview, username
ORDER BY elapsedTimeMillis DESC;

// ============================================================
// 6. Index Usage Statistics
// ============================================================

// Show which indexes are actually being used
CALL db.indexes()
YIELD name, type, readCount
WHERE readCount > 0
RETURN name, type, readCount
ORDER BY readCount DESC
LIMIT 20;

// Show unused indexes (might need to remove or investigate)
CALL db.indexes()
YIELD name, type, readCount, lastRead
WHERE readCount = 0 OR lastRead IS NULL
RETURN name, type, readCount, lastRead
ORDER BY name;

// ============================================================
// 7. Full-Text Index Testing
// ============================================================

// Test bill search
CALL db.index.fulltext.queryNodes('bill_title_search', 'climate carbon emissions')
YIELD node, score
RETURN node.number, node.title, score
ORDER BY score DESC
LIMIT 5;

// Test MP search
CALL db.index.fulltext.queryNodes('mp_name_search', 'justin trudeau')
YIELD node, score
RETURN node.name, node.party, score
ORDER BY score DESC
LIMIT 5;

// Test petition search
CALL db.index.fulltext.queryNodes('petition_text_search', 'healthcare funding')
YIELD node, score
RETURN node.number, node.title, score
ORDER BY score DESC
LIMIT 5;

// ============================================================
// 8. Storage Impact Assessment
// ============================================================

// Approximate database size
CALL apoc.meta.stats()
YIELD nodeCount, relCount, labels, relTypes
RETURN nodeCount, relCount, size(keys(labels)) as label_count, size(keys(relTypes)) as rel_type_count;

// Note: To see actual disk usage, run this on the Neo4j server:
// CALL dbms.queryJmx('org.neo4j:instance=kernel#0,name=Store file sizes')
// YIELD attributes
// RETURN attributes;

// ============================================================
// 9. MCP Query Performance Tests
// ============================================================

// Simulate common MCP queries and measure performance

// Test: searchMPs by party
PROFILE
MATCH (m:MP {party: 'Conservative', current: true})
RETURN m.name, m.riding
ORDER BY m.name
LIMIT 20;

// Test: searchBills by keyword (full-text)
PROFILE
CALL db.index.fulltext.queryNodes('bill_title_search', 'environment protection')
YIELD node, score
WHERE node.session = '44-1'
RETURN node.number, node.title, node.status, score
ORDER BY score DESC
LIMIT 10;

// Test: MP accountability scorecard aggregation
PROFILE
MATCH (mp:MP {id: 'pierre-poilievre'})
CALL {
  WITH mp
  OPTIONAL MATCH (mp)-[:SPONSORED]->(bill:Bill)
  RETURN count(bill) as bills_sponsored
}
CALL {
  WITH mp
  OPTIONAL MATCH (mp)-[:VOTED]->(vote:Vote)
  RETURN count(vote) as votes_cast
}
CALL {
  WITH mp
  MATCH (mp)-[:INCURRED]->(expense:Expense {fiscal_year: 2024})
  RETURN sum(expense.amount) as total_expenses
}
RETURN mp.name, bills_sponsored, votes_cast, total_expenses;

// Test: Lobbying search
PROFILE
MATCH (l:LobbyRegistration {active: true})
WHERE l.client_org_name CONTAINS 'Pharmaceutical'
RETURN l.client_org_name, l.registrant_name, l.effective_date
ORDER BY l.effective_date DESC
LIMIT 10;

// ============================================================
// Expected Results Summary
// ============================================================

// After running all optimization scripts, you should see:
//
// 1. Constraints: ~20-25 unique constraints
// 2. Range Indexes: ~50-60 property indexes
// 3. Full-Text Indexes: ~10 text search indexes
// 4. All indexes: state = 'ONLINE', populationPercent = 100
//
// Performance Improvements:
// - ID lookups: 50-100ms → 1-5ms (20-30x faster)
// - Filtered queries: 1-5 seconds → 50-200ms (10-50x faster)
// - Text searches: 10-30 seconds → 200-500ms (50-100x faster)
// - Scorecard aggregations: 500-1000ms → 100-300ms (5-10x faster)
//
// Total index overhead: ~3-5GB
