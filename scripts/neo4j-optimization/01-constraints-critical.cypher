// ============================================================
// Phase 1: Critical Uniqueness Constraints
// ============================================================
// Creates unique constraints on all primary entity IDs
// Benefits:
// - Data integrity (prevents duplicates)
// - Automatic index creation for ultra-fast lookups
// - 20-30x performance improvement for ID-based queries
//
// Run this FIRST after bulk import completes
// Estimated time: 5-10 minutes for 3M nodes
// ============================================================

// People & Political Entities
CREATE CONSTRAINT mp_id IF NOT EXISTS
FOR (m:MP) REQUIRE m.id IS UNIQUE;

CREATE CONSTRAINT politician_id IF NOT EXISTS
FOR (p:Politician) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT senator_id IF NOT EXISTS
FOR (s:Senator) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT party_code IF NOT EXISTS
FOR (p:Party) REQUIRE p.code IS UNIQUE;

CREATE CONSTRAINT riding_id IF NOT EXISTS
FOR (r:Riding) REQUIRE r.id IS UNIQUE;

CREATE CONSTRAINT role_id IF NOT EXISTS
FOR (r:Role) REQUIRE r.id IS UNIQUE;

// Lobbying Entities
CREATE CONSTRAINT lobbyist_id IF NOT EXISTS
FOR (l:Lobbyist) REQUIRE l.id IS UNIQUE;

CREATE CONSTRAINT organization_id IF NOT EXISTS
FOR (o:Organization) REQUIRE o.id IS UNIQUE;

CREATE CONSTRAINT lobby_registration_id IF NOT EXISTS
FOR (l:LobbyRegistration) REQUIRE l.id IS UNIQUE;

CREATE CONSTRAINT lobby_communication_id IF NOT EXISTS
FOR (l:LobbyCommunication) REQUIRE l.id IS UNIQUE;

// Legislative Entities
CREATE CONSTRAINT bill_composite IF NOT EXISTS
FOR (b:Bill) REQUIRE (b.number, b.session) IS UNIQUE;

CREATE CONSTRAINT vote_id IF NOT EXISTS
FOR (v:Vote) REQUIRE v.id IS UNIQUE;

CREATE CONSTRAINT debate_id IF NOT EXISTS
FOR (d:Debate) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT statement_id IF NOT EXISTS
FOR (s:Statement) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT document_id IF NOT EXISTS
FOR (doc:Document) REQUIRE doc.id IS UNIQUE;

CREATE CONSTRAINT committee_code IF NOT EXISTS
FOR (c:Committee) REQUIRE c.code IS UNIQUE;

CREATE CONSTRAINT petition_number IF NOT EXISTS
FOR (p:Petition) REQUIRE p.number IS UNIQUE;

// Financial Entities
CREATE CONSTRAINT expense_id IF NOT EXISTS
FOR (e:Expense) REQUIRE e.id IS UNIQUE;

CREATE CONSTRAINT contract_id IF NOT EXISTS
FOR (c:Contract) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT grant_id IF NOT EXISTS
FOR (g:Grant) REQUIRE g.id IS UNIQUE;

CREATE CONSTRAINT donation_id IF NOT EXISTS
FOR (d:Donation) REQUIRE d.id IS UNIQUE;

// Legal Entities (CanLII)
CREATE CONSTRAINT case_id IF NOT EXISTS
FOR (c:Case) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT legislation_id IF NOT EXISTS
FOR (l:Legislation) REQUIRE l.id IS UNIQUE;

// Verify all constraints were created
SHOW CONSTRAINTS;
