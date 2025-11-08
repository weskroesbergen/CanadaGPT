// ============================================
// CanadaGPT - Neo4j Graph Schema
// ============================================
//
// This schema defines the graph structure for Canadian government accountability data.
//
// Nodes: MPs, Bills, Votes, Expenses, Lobbying, Contracts, Grants, Petitions, Cases
// Relationships: VOTED, SPONSORED, LOBBIED_ON, RECEIVED, DONATED, etc.
//
// Expected scale: 1M+ nodes, 10M+ relationships
//
// To execute:
// 1. Open Neo4j Browser: https://console.neo4j.io/ (for Aura)
// 2. Copy/paste each section below
// 3. Or use neo4j-driver in Python pipeline
//
// ============================================

// ============================================
// SECTION 1: Constraints (Unique IDs)
// ============================================
// Execute these FIRST before any data import
// Ensures data integrity and creates indexes automatically

// People & Organizations
CREATE CONSTRAINT mp_id IF NOT EXISTS FOR (m:MP) REQUIRE m.id IS UNIQUE;
CREATE CONSTRAINT party_code IF NOT EXISTS FOR (p:Party) REQUIRE p.code IS UNIQUE;
CREATE CONSTRAINT riding_id IF NOT EXISTS FOR (r:Riding) REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT lobbyist_id IF NOT EXISTS FOR (l:Lobbyist) REQUIRE l.id IS UNIQUE;
CREATE CONSTRAINT organization_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE;

// Legislative Entities
CREATE CONSTRAINT bill_composite IF NOT EXISTS FOR (b:Bill) REQUIRE (b.number, b.session) IS UNIQUE;
CREATE CONSTRAINT vote_id IF NOT EXISTS FOR (v:Vote) REQUIRE v.id IS UNIQUE;
CREATE CONSTRAINT debate_id IF NOT EXISTS FOR (d:Debate) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT committee_code IF NOT EXISTS FOR (c:Committee) REQUIRE c.code IS UNIQUE;
CREATE CONSTRAINT petition_number IF NOT EXISTS FOR (p:Petition) REQUIRE p.number IS UNIQUE;

// Financial Entities
CREATE CONSTRAINT expense_id IF NOT EXISTS FOR (e:Expense) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT contract_id IF NOT EXISTS FOR (c:Contract) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT grant_id IF NOT EXISTS FOR (g:Grant) REQUIRE g.id IS UNIQUE;
CREATE CONSTRAINT donation_id IF NOT EXISTS FOR (d:Donation) REQUIRE d.id IS UNIQUE;

// Lobbying
CREATE CONSTRAINT lobby_reg_id IF NOT EXISTS FOR (lr:LobbyRegistration) REQUIRE lr.id IS UNIQUE;
CREATE CONSTRAINT lobby_comm_id IF NOT EXISTS FOR (lc:LobbyCommunication) REQUIRE lc.id IS UNIQUE;

// Legal
CREATE CONSTRAINT case_id IF NOT EXISTS FOR (c:Case) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT legislation_id IF NOT EXISTS FOR (l:Legislation) REQUIRE l.id IS UNIQUE;

// ============================================
// SECTION 2: Indexes (Performance)
// ============================================
// Create indexes on frequently queried properties
// These are separate from constraints and improve query performance

// MPs - Search by name, party, status
CREATE INDEX mp_name IF NOT EXISTS FOR (m:MP) ON (m.name);
CREATE INDEX mp_party IF NOT EXISTS FOR (m:MP) ON (m.party);
CREATE INDEX mp_current IF NOT EXISTS FOR (m:MP) ON (m.current);

// Bills - Search by title, status, stage
CREATE INDEX bill_status IF NOT EXISTS FOR (b:Bill) ON (b.status);
CREATE INDEX bill_stage IF NOT EXISTS FOR (b:Bill) ON (b.stage);
CREATE INDEX bill_session IF NOT EXISTS FOR (b:Bill) ON (b.session);

// Votes - Query by date, result
CREATE INDEX vote_date IF NOT EXISTS FOR (v:Vote) ON (v.date);
CREATE INDEX vote_result IF NOT EXISTS FOR (v:Vote) ON (v.result);

// Expenses - Filter by fiscal year, quarter, category
CREATE INDEX expense_fiscal_year IF NOT EXISTS FOR (e:Expense) ON (e.fiscal_year);
CREATE INDEX expense_quarter IF NOT EXISTS FOR (e:Expense) ON (e.quarter);
CREATE INDEX expense_category IF NOT EXISTS FOR (e:Expense) ON (e.category);

// Contracts - Search by date, amount, department
CREATE INDEX contract_date IF NOT EXISTS FOR (c:Contract) ON (c.date);
CREATE INDEX contract_amount IF NOT EXISTS FOR (c:Contract) ON (c.amount);
CREATE INDEX contract_department IF NOT EXISTS FOR (c:Contract) ON (c.department);

// Grants - Filter by year, program, department
CREATE INDEX grant_year IF NOT EXISTS FOR (g:Grant) ON (g.agreement_year);
CREATE INDEX grant_program IF NOT EXISTS FOR (g:Grant) ON (g.program_name);
CREATE INDEX grant_department IF NOT EXISTS FOR (g:Grant) ON (g.owner_org);

// Donations - Query by year, party, amount
CREATE INDEX donation_year IF NOT EXISTS FOR (d:Donation) ON (d.contribution_year);
CREATE INDEX donation_party IF NOT EXISTS FOR (d:Donation) ON (d.political_party);
CREATE INDEX donation_amount IF NOT EXISTS FOR (d:Donation) ON (d.amount);

// Lobbying - Filter by date, active status
CREATE INDEX lobby_reg_active IF NOT EXISTS FOR (lr:LobbyRegistration) ON (lr.active);
CREATE INDEX lobby_comm_date IF NOT EXISTS FOR (lc:LobbyCommunication) ON (lc.date);

// Petitions - Search by status, signature count
CREATE INDEX petition_status IF NOT EXISTS FOR (p:Petition) ON (p.status);
CREATE INDEX petition_signatures IF NOT EXISTS FOR (p:Petition) ON (p.signatures);

// Organizations - Search by name, industry
CREATE INDEX org_name IF NOT EXISTS FOR (o:Organization) ON (o.name);

// Full-text search indexes (for natural language queries)
CREATE FULLTEXT INDEX search_bills IF NOT EXISTS FOR (b:Bill) ON EACH [b.title, b.summary];
CREATE FULLTEXT INDEX search_mps IF NOT EXISTS FOR (m:MP) ON EACH [m.name];
CREATE FULLTEXT INDEX search_orgs IF NOT EXISTS FOR (o:Organization) ON EACH [o.name];

// ============================================
// SECTION 3: Node Type Documentation
// ============================================
// This section documents the expected properties for each node type
// Use this as reference when building the data pipeline

/*
(:MP) - Member of Parliament
Properties:
  - id: STRING (unique, e.g., "pierre-poilievre")
  - name: STRING (e.g., "Pierre Poilievre")
  - party: STRING (e.g., "Conservative")
  - riding: STRING (e.g., "Carleton")
  - current: BOOLEAN (currently serving)
  - elected_date: DATE
  - photo_url: STRING (optional)
  - email: STRING (optional)
  - twitter: STRING (optional)
  - phone: STRING (optional)
  - updated_at: DATETIME

(:Party)
Properties:
  - code: STRING (unique, e.g., "CPC", "LPC", "NDP")
  - name: STRING (e.g., "Conservative Party of Canada")
  - leader_name: STRING (optional)
  - seats: INTEGER (current seat count)
  - updated_at: DATETIME

(:Riding)
Properties:
  - id: STRING (unique, e.g., "35001")
  - name: STRING (e.g., "Carleton")
  - province: STRING (e.g., "Ontario")
  - population: INTEGER (optional)

(:Bill)
Properties:
  - number: STRING (e.g., "C-11")
  - session: STRING (e.g., "44-1")
  - title: STRING
  - summary: TEXT (optional)
  - status: STRING (e.g., "Passed", "In Committee", "First Reading")
  - stage: STRING (current legislative stage)
  - sponsor_mp_id: STRING (references MP.id)
  - introduced_date: DATE
  - passed_date: DATE (optional)
  - royal_assent_date: DATE (optional)
  - updated_at: DATETIME

(:Vote)
Properties:
  - id: STRING (unique, e.g., "44-1-123")
  - date: DATE
  - number: INTEGER
  - session: STRING
  - bill_number: STRING (optional, if related to bill)
  - result: STRING (e.g., "Passed", "Defeated", "Tied")
  - yeas: INTEGER
  - nays: INTEGER
  - paired: INTEGER (optional)

(:Debate)
Properties:
  - id: STRING (unique, Hansard identifier)
  - date: DATE
  - topic: STRING
  - hansard_url: STRING
  - parliament: INTEGER
  - session: STRING

(:Committee)
Properties:
  - code: STRING (unique, e.g., "FINA")
  - name: STRING (e.g., "Standing Committee on Finance")
  - mandate: TEXT
  - chamber: STRING ("Commons" or "Senate")

(:Petition)
Properties:
  - number: STRING (unique, e.g., "e-4815")
  - title: STRING
  - text: TEXT
  - signatures: INTEGER
  - status: STRING (e.g., "Open", "Closed", "Response Received")
  - created_date: DATE
  - closed_date: DATE (optional)
  - category: STRING (e.g., "Environment", "Justice")

(:Expense)
Properties:
  - id: STRING (unique, composite of mp_id + fiscal_year + quarter + category)
  - mp_id: STRING (references MP.id)
  - fiscal_year: INTEGER (e.g., 2025)
  - quarter: INTEGER (1-4)
  - category: STRING (e.g., "Travel", "Office", "Salaries")
  - amount: FLOAT
  - description: STRING (optional)

(:Contract)
Properties:
  - id: STRING (unique, reference_number)
  - vendor: STRING (company name)
  - amount: FLOAT
  - department: STRING
  - date: DATE
  - delivery_date: DATE (optional)
  - description: TEXT
  - owner_org: STRING

(:Grant)
Properties:
  - id: STRING (unique)
  - recipient: STRING (organization/person name)
  - amount: FLOAT
  - program_name: STRING
  - program_purpose: TEXT
  - agreement_date: DATE
  - agreement_year: INTEGER
  - start_date: DATE (optional)
  - end_date: DATE (optional)
  - owner_org: STRING (department)
  - recipient_city: STRING (optional)
  - recipient_province: STRING (optional)

(:Donation)
Properties:
  - id: STRING (unique)
  - donor_name: STRING
  - amount: FLOAT
  - date: DATE
  - contribution_year: INTEGER
  - political_party: STRING
  - recipient_type: STRING (e.g., "Party", "Candidate", "EDA")
  - recipient_name: STRING
  - electoral_district: STRING (optional)
  - donor_city: STRING (optional)
  - donor_province: STRING (optional)

(:LobbyRegistration)
Properties:
  - id: STRING (unique, reg_id)
  - reg_number: STRING
  - client_org_name: STRING
  - registrant_name: STRING
  - effective_date: DATE
  - end_date: DATE (optional)
  - active: BOOLEAN
  - subject_matters: LIST<STRING>
  - government_institutions: LIST<STRING>

(:LobbyCommunication)
Properties:
  - id: STRING (unique, comlog_id)
  - client_org_name: STRING
  - registrant_name: STRING
  - date: DATE
  - dpoh_names: LIST<STRING> (designated public office holders met)
  - dpoh_titles: LIST<STRING>
  - institutions: LIST<STRING>
  - subject_matters: LIST<STRING>

(:Lobbyist)
Properties:
  - id: STRING (unique)
  - name: STRING
  - firm: STRING (optional, if consultant)

(:Organization)
Properties:
  - id: STRING (unique, normalized name)
  - name: STRING
  - industry: STRING (optional)
  - ceo: STRING (optional)

(:Case) - CanLII case law
Properties:
  - id: STRING (unique, CanLII ID)
  - citation: STRING
  - court: STRING
  - date: DATE
  - summary: TEXT
  - canlii_url: STRING

(:Legislation) - Acts and Regulations
Properties:
  - id: STRING (unique)
  - title: STRING
  - jurisdiction: STRING (e.g., "CA", "ON")
  - type: STRING (e.g., "Act", "Regulation")
  - date: DATE
*/

// ============================================
// SECTION 4: Relationship Type Documentation
// ============================================

/*
RELATIONSHIP TYPES AND THEIR PROPERTIES:

// Political Structure
(MP)-[:MEMBER_OF]->(Party)
(MP)-[:REPRESENTS]->(Riding)
(MP)-[:SERVES_ON {role: STRING, start_date: DATE}]->(Committee)

// Legislative Activity
(MP)-[:SPONSORED]->(Bill)
(MP)-[:VOTED {position: "yea"|"nay"|"paired"}]->(Vote)
(Vote)-[:SUBJECT_OF]->(Bill)
(MP)-[:SPOKE_AT {timestamp: DATETIME, excerpt: TEXT}]->(Debate)
(Debate)-[:DISCUSSED]->(Bill)
(Bill)-[:REFERRED_TO]->(Committee)
(MP)-[:SPONSORED]->(Petition)

// Lobbying & Influence
(Lobbyist)-[:WORKS_FOR]->(Organization)
(Lobbyist)-[:REGISTERED_FOR {start_date: DATE, end_date: DATE}]->(LobbyRegistration)
(LobbyRegistration)-[:ON_BEHALF_OF]->(Organization)
(Organization)-[:LOBBIED_ON {date: DATE, subject: STRING}]->(Bill)
(Lobbyist)-[:MET_WITH {date: DATE, topic: STRING, dpoh_title: STRING}]->(MP)

// Financial Flows
(MP)-[:INCURRED]->(Expense)
(Organization)-[:RECEIVED]->(Contract)
(Organization)-[:RECEIVED]->(Grant)
(Organization)-[:DONATED {via: "individual"|"corporate"}]->(Party)
(Party)-[:RECEIVED]->(Donation)

// Legal Citations
(Bill)-[:CITED_IN]->(Case)
(Case)-[:CITES]->(Legislation)
(Case)-[:CITES]->(Case)  // Case law precedent

// Network Analysis (derived relationships)
(MP)-[:COLLABORATED_WITH {bills_count: INTEGER}]->(MP)
  // Derived from co-sponsoring bills or voting similarly
(Organization)-[:SHARES_LOBBYIST]->(Organization)
  // Derived from using same lobbyist
*/

// ============================================
// SECTION 5: Sample Queries
// ============================================
// Use these to verify your schema after data load

// 1. Count nodes by type
MATCH (n)
RETURN labels(n)[0] AS NodeType, count(*) AS Count
ORDER BY Count DESC;

// 2. Count relationships by type
MATCH ()-[r]->()
RETURN type(r) AS RelationshipType, count(*) AS Count
ORDER BY Count DESC;

// 3. Find MP with most bills sponsored
MATCH (mp:MP)-[:SPONSORED]->(b:Bill)
RETURN mp.name, mp.party, count(b) AS bills_sponsored
ORDER BY bills_sponsored DESC
LIMIT 10;

// 4. Find organizations with most government contracts
MATCH (o:Organization)-[:RECEIVED]->(c:Contract)
RETURN o.name, count(c) AS contract_count, sum(c.amount) AS total_value
ORDER BY total_value DESC
LIMIT 20;

// 5. Trace money flow: Donation → Party → MP → Vote → Contract
MATCH path =
  (org:Organization)-[:DONATED]->(party:Party)<-[:MEMBER_OF]-(mp:MP)-[:VOTED]->(vote:Vote),
  (org)-[:RECEIVED]->(contract:Contract)
WHERE vote.date < contract.date
  AND duration.between(vote.date, contract.date).months < 6
RETURN
  org.name AS Organization,
  mp.name AS MP,
  vote.bill_number AS BillVoted,
  contract.amount AS ContractValue,
  duration.between(vote.date, contract.date).days AS DaysAfterVote
ORDER BY contract.amount DESC
LIMIT 10;

// 6. Find MPs with highest lobbying exposure
MATCH (mp:MP)<-[:MET_WITH]-(lobbyist:Lobbyist)-[:WORKS_FOR]->(org:Organization)
RETURN mp.name, mp.party,
       count(DISTINCT lobbyist) AS unique_lobbyists,
       count(DISTINCT org) AS unique_organizations,
       count(*) AS total_meetings
ORDER BY total_meetings DESC
LIMIT 20;

// 7. Detect potential conflicts of interest
MATCH (org:Organization)-[:LOBBIED_ON]->(bill:Bill)<-[:SUBJECT_OF]-(vote:Vote)
MATCH (org)-[:DONATED]->(party:Party)<-[:MEMBER_OF]-(mp:MP)-[v:VOTED]->(vote)
WHERE v.position = 'yea'
  AND (org)-[:RECEIVED]->(:Contract {amount_gte: 1000000})
RETURN mp.name, org.name, bill.number, bill.title,
       count(*) AS suspicion_score
ORDER BY suspicion_score DESC
LIMIT 20;

// 8. Find bills with most lobbying activity
MATCH (org:Organization)-[:LOBBIED_ON]->(bill:Bill)
RETURN bill.number, bill.title, bill.status,
       count(DISTINCT org) AS organizations_lobbying,
       collect(DISTINCT org.name)[0..5] AS top_lobbyists
ORDER BY organizations_lobbying DESC
LIMIT 20;

// 9. MP performance scorecard (comprehensive)
MATCH (mp:MP {name: "Pierre Poilievre"})
OPTIONAL MATCH (mp)-[:SPONSORED]->(bill:Bill)
OPTIONAL MATCH (mp)-[:VOTED]->(vote:Vote)
OPTIONAL MATCH (mp)-[:SPONSORED]->(petition:Petition)
OPTIONAL MATCH (mp)-[:INCURRED]->(expense:Expense {fiscal_year: 2025})
OPTIONAL MATCH (mp)<-[:MET_WITH]-(lobbyist:Lobbyist)
RETURN {
  name: mp.name,
  party: mp.party,
  riding: mp.riding,
  bills_sponsored: count(DISTINCT bill),
  bills_passed: count(DISTINCT bill {status: 'Passed'}),
  votes_participated: count(DISTINCT vote),
  petitions_sponsored: count(DISTINCT petition),
  total_petition_signatures: sum(petition.signatures),
  total_expenses_2025: sum(expense.amount),
  lobbyist_meetings: count(DISTINCT lobbyist),
  legislative_effectiveness: toFloat(count(DISTINCT bill {status: 'Passed'})) / count(DISTINCT bill) * 100
} AS scorecard;

// 10. Database statistics
CALL apoc.meta.stats() YIELD nodeCount, relCount, labelCount, relTypeCount
RETURN nodeCount, relCount, labelCount, relTypeCount;
// Note: Requires APOC plugin (installed by default in Neo4j Aura)

// ============================================
// SECTION 6: Performance Tuning
// ============================================

// Check query performance
// Always use PROFILE or EXPLAIN before complex queries
PROFILE
MATCH (mp:MP {name: "Pierre Poilievre"})-[:VOTED]->(vote:Vote)
RETURN count(vote);

// If queries are slow, check index usage
CALL db.indexes();

// For very large datasets, consider bloom filters
// (Advanced topic - see Neo4j documentation)

// ============================================
// END OF SCHEMA
// ============================================

// After executing all constraints and indexes above:
// 1. Verify with: CALL db.constraints(); and CALL db.indexes();
// 2. Expected: 17 constraints, 20+ indexes
// 3. Ready for data import via Python pipeline (Phase 2)
