// ============================================================
// Phase 1: High-Frequency Property Indexes
// ============================================================
// Indexes for the most commonly filtered properties
// Based on actual MCP tool query patterns
//
// Impact: 10-50x faster WHERE clause filtering
// Run after constraints complete
// Estimated time: 10-15 minutes
// ============================================================

// ============================================================
// MP Indexes (57 MCP tools use MP queries)
// ============================================================

-- Name searches (searchMPs, case-insensitive)
CREATE INDEX mp_name IF NOT EXISTS
FOR (m:MP) ON (m.name);

CREATE INDEX mp_family_name IF NOT EXISTS
FOR (m:MP) ON (m.family_name);

CREATE INDEX mp_given_name IF NOT EXISTS
FOR (m:MP) ON (m.given_name);

-- Party filtering (extremely common - party comparisons, caucus queries)
CREATE INDEX mp_party IF NOT EXISTS
FOR (m:MP) ON (m.party);

-- Current/former MP filtering
CREATE INDEX mp_current IF NOT EXISTS
FOR (m:MP) ON (m.current);

-- Cabinet position queries
CREATE INDEX mp_cabinet IF NOT EXISTS
FOR (m:MP) ON (m.cabinet_position);

-- Riding/province filtering
CREATE INDEX mp_riding IF NOT EXISTS
FOR (m:MP) ON (m.riding);

CREATE INDEX mp_province IF NOT EXISTS
FOR (m:MP) ON (m.province);

// ============================================================
// Bill Indexes (searchBills is heavily used)
// ============================================================

-- Status filtering (active, passed, defeated)
CREATE INDEX bill_status IF NOT EXISTS
FOR (b:Bill) ON (b.status);

-- Session filtering (parliament-session format)
CREATE INDEX bill_session IF NOT EXISTS
FOR (b:Bill) ON (b.session);

-- Bill type filtering (government vs private member)
CREATE INDEX bill_type IF NOT EXISTS
FOR (b:Bill) ON (b.bill_type);

-- Chronological queries
CREATE INDEX bill_introduced_date IF NOT EXISTS
FOR (b:Bill) ON (b.introduced_date);

-- Sponsor lookups
CREATE INDEX bill_sponsor IF NOT EXISTS
FOR (b:Bill) ON (b.sponsor_mp_id);

-- Number queries (combine with session for unique lookup)
CREATE INDEX bill_number IF NOT EXISTS
FOR (b:Bill) ON (b.number);

// ============================================================
// Vote Indexes (list_votes, analyze_voting_patterns)
// ============================================================

-- Date range queries (very common)
CREATE INDEX vote_date IF NOT EXISTS
FOR (v:Vote) ON (v.date);

-- Result filtering (passed/failed)
CREATE INDEX vote_result IF NOT EXISTS
FOR (v:Vote) ON (v.result);

-- Session filtering
CREATE INDEX vote_session IF NOT EXISTS
FOR (v:Vote) ON (v.session);

-- Vote number lookups
CREATE INDEX vote_number IF NOT EXISTS
FOR (v:Vote) ON (v.number);

// ============================================================
// Expense Indexes (accountability queries)
// ============================================================

-- Fiscal year/quarter filtering (extremely common)
CREATE INDEX expense_fiscal_year IF NOT EXISTS
FOR (e:Expense) ON (e.fiscal_year);

CREATE INDEX expense_quarter IF NOT EXISTS
FOR (e:Expense) ON (e.quarter);

-- MP expense lookups
CREATE INDEX expense_mp_id IF NOT EXISTS
FOR (e:Expense) ON (e.mp_id);

-- Amount-based queries (top spenders)
CREATE INDEX expense_amount IF NOT EXISTS
FOR (e:Expense) ON (e.amount);

-- Category filtering
CREATE INDEX expense_category IF NOT EXISTS
FOR (e:Expense) ON (e.category);

// ============================================================
// Lobbying Indexes (transparency/accountability queries)
// ============================================================

-- Active registration filtering (very common)
CREATE INDEX lobby_reg_active IF NOT EXISTS
FOR (l:LobbyRegistration) REQUIRE l.active;

-- Date range queries
CREATE INDEX lobby_reg_effective_date IF NOT EXISTS
FOR (l:LobbyRegistration) ON (l.effective_date);

CREATE INDEX lobby_reg_termination_date IF NOT EXISTS
FOR (l:LobbyRegistration) ON (l.termination_date);

-- Client/registrant lookups
CREATE INDEX lobby_reg_client_org IF NOT EXISTS
FOR (l:LobbyRegistration) ON (l.client_org_name);

CREATE INDEX lobby_reg_registrant IF NOT EXISTS
FOR (l:LobbyRegistration) ON (l.registrant_name);

-- Communication date queries
CREATE INDEX lobby_comm_date IF NOT EXISTS
FOR (l:LobbyCommunication) ON (l.date);

-- Subject matter filtering
CREATE INDEX lobby_comm_subject IF NOT EXISTS
FOR (l:LobbyCommunication) ON (l.subject);

// ============================================================
// Petition Indexes
// ============================================================

-- Status filtering
CREATE INDEX petition_status IF NOT EXISTS
FOR (p:Petition) ON (p.status);

-- Date queries
CREATE INDEX petition_created IF NOT EXISTS
FOR (p:Petition) ON (p.created_date);

CREATE INDEX petition_closed IF NOT EXISTS
FOR (p:Petition) ON (p.closed_date);

-- Category filtering
CREATE INDEX petition_category IF NOT EXISTS
FOR (p:Petition) ON (p.category);

// ============================================================
// Committee Indexes
// ============================================================

-- Name/code lookups
CREATE INDEX committee_name IF NOT EXISTS
FOR (c:Committee) ON (c.name);

-- Chamber filtering (House vs Senate)
CREATE INDEX committee_chamber IF NOT EXISTS
FOR (c:Committee) ON (c.chamber);

-- Active committee filtering
CREATE INDEX committee_active IF NOT EXISTS
FOR (c:Committee) ON (c.active);

// ============================================================
// Debate/Statement Indexes (Hansard queries)
// ============================================================

-- Date range queries (very common)
CREATE INDEX debate_date IF NOT EXISTS
FOR (d:Debate) ON (d.date);

-- Session filtering
CREATE INDEX debate_session IF NOT EXISTS
FOR (d:Debate) ON (d.session);

-- Parliament filtering
CREATE INDEX debate_parliament IF NOT EXISTS
FOR (d:Debate) ON (d.parliament);

// Statement time-based queries (chronological retrieval)
CREATE INDEX statement_time IF NOT EXISTS
FOR (s:Statement) ON (s.time);

// ============================================================
// Verify all indexes
// ============================================================
CALL db.indexes()
YIELD name, type, state, populationPercent
WHERE type = 'RANGE'
ORDER BY name
RETURN name, state, populationPercent;
