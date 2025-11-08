// ============================================================
// Phase 2: Composite & Relationship Indexes
// ============================================================
// Advanced indexes for multi-column queries and graph traversals
//
// Impact: 5-20x faster for complex queries
// Run after Phase 1 and full-text indexes
// Estimated time: 5-10 minutes
// ============================================================

// ============================================================
// Composite Indexes (Multi-Column)
// ============================================================

-- MP + Fiscal Year queries
-- Critical for: mpScorecard, get_mp_expenses, analyze_spending
CREATE INDEX mp_fiscal_year IF NOT EXISTS
FOR (e:Expense)
ON (e.mp_id, e.fiscal_year);

-- MP + Fiscal Year + Quarter (even more specific)
CREATE INDEX mp_fiscal_year_quarter IF NOT EXISTS
FOR (e:Expense)
ON (e.mp_id, e.fiscal_year, e.quarter);

-- Vote Bill lookups
-- Finding all votes for a specific bill
CREATE INDEX vote_bill_session IF NOT EXISTS
FOR (v:Vote)
ON (v.bill_number, v.session);

-- Bill + Session + Status queries
CREATE INDEX bill_session_status IF NOT EXISTS
FOR (b:Bill)
ON (b.session, b.status);

-- Lobbying client + active status queries
CREATE INDEX lobby_client_active IF NOT EXISTS
FOR (l:LobbyRegistration)
ON (l.client_org_name, l.active);

-- Debate session + date queries (chronological within session)
CREATE INDEX debate_session_date IF NOT EXISTS
FOR (d:Debate)
ON (d.session, d.date);

-- Petition status + category queries
CREATE INDEX petition_status_category IF NOT EXISTS
FOR (p:Petition)
ON (p.status, p.category);

// ============================================================
// Relationship Property Indexes
// ============================================================
// These dramatically speed up relationship filtering
// e.g., finding all "yea" votes, recent lobbying meetings

-- VOTED relationship - position filtering
-- Used by: analyze_voting_patterns, compare_party_bills
CREATE INDEX rel_voted_position IF NOT EXISTS
FOR ()-[r:VOTED]->()
ON (r.position);

-- VOTED relationship - date filtering
CREATE INDEX rel_voted_date IF NOT EXISTS
FOR ()-[r:VOTED]->()
ON (r.date);

-- MET_WITH relationship - date filtering
-- Critical for: search_lobbying_communications, detect_conflicts_of_interest
CREATE INDEX rel_met_with_date IF NOT EXISTS
FOR ()-[r:MET_WITH]->()
ON (r.date);

-- MENTIONS relationship - stage filtering
-- Used for: analyze_bill_progress, search_bill_debates
CREATE INDEX rel_mentions_stage IF NOT EXISTS
FOR ()-[r:MENTIONS]->()
ON (r.debate_stage);

-- SERVES_ON relationship - role filtering
-- Committee membership queries
CREATE INDEX rel_serves_on_role IF NOT EXISTS
FOR ()-[r:SERVES_ON]->()
ON (r.role);

-- SERVES_ON relationship - date range
CREATE INDEX rel_serves_on_dates IF NOT EXISTS
FOR ()-[r:SERVES_ON]->()
ON (r.start_date, r.end_date);

-- SPONSORED relationship - date
-- Legislative activity timeline
CREATE INDEX rel_sponsored_date IF NOT EXISTS
FOR ()-[r:SPONSORED]->()
ON (r.date);

-- INCURRED relationship - fiscal year
-- Expense tracking
CREATE INDEX rel_incurred_fiscal_year IF NOT EXISTS
FOR ()-[r:INCURRED]->()
ON (r.fiscal_year);

-- LOBBIED_ON relationship - date
CREATE INDEX rel_lobbied_on_date IF NOT EXISTS
FOR ()-[r:LOBBIED_ON]->()
ON (r.date);

// ============================================================
// Verify Composite and Relationship Indexes
// ============================================================

CALL db.indexes()
YIELD name, type, state, populationPercent, indexProvider
WHERE type = 'RANGE'
ORDER BY name
RETURN name, type, state, populationPercent, indexProvider;

// ============================================================
// Performance Test Queries
// ============================================================

// Test composite index usage:
// PROFILE
// MATCH (e:Expense {mp_id: 'pierre-poilievre', fiscal_year: 2024})
// RETURN e;
// Should show: NodeIndexSeek (using mp_fiscal_year index)

// Test relationship index usage:
// PROFILE
// MATCH (:MP {id: 'pierre-poilievre'})-[v:VOTED {position: 'yea'}]->()
// RETURN count(v);
// Should show: DirectedRelationshipIndexSeek (using rel_voted_position index)
