// ============================================================
// Phase 2: Full-Text Search Indexes
// ============================================================
// Creates full-text indexes for semantic/keyword searches
// Dramatically improves CONTAINS queries and text search
//
// Impact: 50-100x faster text searches
// Run after Phase 1 completes
// Estimated time: 15-20 minutes (text indexes are large)
// ============================================================

// ============================================================
// Bill Text Search
// ============================================================

-- Bill title and summary search
-- Used by: searchBills MCP tool (keyword searches)
CREATE FULLTEXT INDEX bill_title_search IF NOT EXISTS
FOR (b:Bill)
ON EACH [b.title, b.summary]
OPTIONS {
  indexConfig: {
    `fulltext.analyzer`: 'english',
    `fulltext.eventually_consistent`: false
  }
};

// ============================================================
// MP Name Search
// ============================================================

-- MP name search with partial matching
-- Used by: searchMPs, get_politician_profile
CREATE FULLTEXT INDEX mp_name_search IF NOT EXISTS
FOR (m:MP)
ON EACH [m.name, m.given_name, m.family_name]
OPTIONS {
  indexConfig: {
    `fulltext.analyzer`: 'standard',
    `fulltext.eventually_consistent`: false
  }
};

// ============================================================
// Committee Search
// ============================================================

-- Committee name and code search
CREATE FULLTEXT INDEX committee_search IF NOT EXISTS
FOR (c:Committee)
ON EACH [c.name, c.short_name, c.code]
OPTIONS {
  indexConfig: {
    `fulltext.analyzer`: 'english',
    `fulltext.eventually_consistent`: false
  }
};

// ============================================================
// Lobbying Organization Search
// ============================================================

-- Organization name search for lobbying queries
-- Used by: search_lobbying_registrations, get_top_lobbying_clients
CREATE FULLTEXT INDEX lobby_org_search IF NOT EXISTS
FOR (l:LobbyRegistration)
ON EACH [l.client_org_name, l.registrant_name]
OPTIONS {
  indexConfig: {
    `fulltext.analyzer`: 'standard',
    `fulltext.eventually_consistent`: false
  }
};

-- Lobbying subject search
CREATE FULLTEXT INDEX lobby_subject_search IF NOT EXISTS
FOR (l:LobbyCommunication)
ON EACH [l.subject, l.responsible_officer]
OPTIONS {
  indexConfig: {
    `fulltext.analyzer`: 'english',
    `fulltext.eventually_consistent`: false
  }
};

// ============================================================
// Petition Text Search
// ============================================================

-- Petition title and text search
-- Used by: search_petitions, search_by_topic
CREATE FULLTEXT INDEX petition_text_search IF NOT EXISTS
FOR (p:Petition)
ON EACH [p.title, p.text]
OPTIONS {
  indexConfig: {
    `fulltext.analyzer`: 'english',
    `fulltext.eventually_consistent`: false
  }
};

// ============================================================
// Organization/Party Search
// ============================================================

-- Organization name search (for contracts, grants, lobbying)
CREATE FULLTEXT INDEX organization_name_search IF NOT EXISTS
FOR (o:Organization)
ON EACH [o.name, o.legal_name]
OPTIONS {
  indexConfig: {
    `fulltext.analyzer`: 'standard',
    `fulltext.eventually_consistent`: false
  }
};

-- Party name search
CREATE FULLTEXT INDEX party_name_search IF NOT EXISTS
FOR (p:Party)
ON EACH [p.name, p.short_name]
OPTIONS {
  indexConfig: {
    `fulltext.analyzer`: 'standard',
    `fulltext.eventually_consistent`: false
  }
};

// ============================================================
// Riding Name Search
// ============================================================

-- Riding/constituency name search
CREATE FULLTEXT INDEX riding_name_search IF NOT EXISTS
FOR (r:Riding)
ON EACH [r.name, r.name_en, r.name_fr]
OPTIONS {
  indexConfig: {
    `fulltext.analyzer`: 'standard',
    `fulltext.eventually_consistent`: false
  }
};

// ============================================================
// Verify Full-Text Indexes
// ============================================================

CALL db.indexes()
YIELD name, type, state, populationPercent
WHERE type = 'FULLTEXT'
ORDER BY name
RETURN name, state, populationPercent;

// ============================================================
// Usage Examples
// ============================================================

// BEFORE (slow - full table scan with CONTAINS):
// MATCH (b:Bill)
// WHERE toLower(b.title) CONTAINS toLower($searchTerm)
// RETURN b;

// AFTER (fast - uses full-text index):
// CALL db.index.fulltext.queryNodes('bill_title_search', $searchTerm)
// YIELD node, score
// RETURN node ORDER BY score DESC LIMIT 20;
