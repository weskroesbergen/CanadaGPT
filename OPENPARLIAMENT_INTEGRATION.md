# OpenParliament Database Integration

## Overview

This document tracks the integration of the complete OpenParliament PostgreSQL database into FedMCP's Neo4j knowledge graph. This adds 500K+ individual MP votes, historical MP terms, election results, Hansard debates, and political contributions to enable deep accountability analysis.

## Current Status: Phase 1 - Setup ✅

### Completed
- ✅ Analyzed OpenParliament SQL dump (1.3GB, 63 tables, 6.3M lines)
- ✅ Reviewed OpenParliament source code (Django models, importers)
- ✅ Created integration plan with 6-week phased rollout
- ✅ Installed PostgreSQL 14
- ✅ Created database setup script (`scripts/setup_openparliament_db.sh`)

### Next Steps
1. **Run the setup script** to load the OpenParliament dump:
   ```bash
   cd /Users/matthewdufresne/FedMCP
   ./scripts/setup_openparliament_db.sh
   ```
   ⚠️ This will take 15-30 minutes to decompress and load ~1.3GB of data

2. **Add PostgreSQL credentials** to `packages/data-pipeline/.env`:
   ```
   POSTGRES_URI=postgresql://fedmcp:fedmcp2024@localhost:5432/openparliament
   ```

3. **Create PostgreSQL client utilities** (`packages/data-pipeline/fedmcp_pipeline/clients/postgres_client.py`)

4. **Begin data import** starting with MemberVote records (highest ROI)

## Integration Plan

### Phase 1: Core Accountability Data (Weeks 1-2) 🔵 IN PROGRESS
**Goal:** Enable corruption detection and MP performance analysis

| Task | Status | Est. Rows | Impact |
|------|--------|-----------|--------|
| PostgreSQL setup | ✅ Complete | - | Foundation |
| Import MemberVote | ⏳ Pending | 500K | Individual vote records |
| Import ElectedMember | ⏳ Pending | 5K | Historical MP terms |
| Enhance MP nodes | ⏳ Pending | 350 | Add historical fields |
| Test queries | ⏳ Pending | - | Verify "How did X vote on Y?" |

**Deliverables:**
- Query "How did MP X vote on Bill Y?"
- Track party-switching and riding changes
- Analyze party loyalty and dissent patterns

### Phase 2: Electoral Context (Week 3) ⚪ PLANNED
**Goal:** Understand electoral competitiveness

- Create `:Election` and `:Candidacy` node types
- Import 50K candidacy records
- Enable electoral history queries per riding

### Phase 3: Debate Search (Weeks 4-5) ⚪ PLANNED
**Goal:** Enable natural language search of speeches

- Import recent Hansard statements (~400K, last 2 parliaments)
- Set up Neo4j full-text search
- Create `(MP)-[:SPOKE]->(Statement)-[:MENTIONED]->(Bill)` chains

### Phase 4: Financial Transparency (Week 6) ⚪ PLANNED
**Goal:** Track donation patterns

- Import 200K political contributions
- Create donor network relationships
- Enable donation-vote correlation analysis

## Database Schema

### New Node Types

```cypher
// Phase 1
(:Term {
  id: STRING,
  start_date: DATE,
  end_date: DATE,
  parliament: INTEGER,
  session: STRING
})

// Phase 2
(:Election {id: STRING, date: DATE, type: STRING})
(:Candidacy {vote_total: INTEGER, vote_percent: FLOAT, elected: BOOLEAN})

// Phase 3
(:Statement {content_en: TEXT, time: DATETIME, wordcount: INTEGER})
(:Document {date: DATE, type: STRING, parliament: INTEGER})

// Phase 4
(:Donor {name: STRING, city: STRING, province: STRING})
(:Contribution {amount: FLOAT, date: DATE, recipient_type: STRING})
```

### New Relationships

```cypher
// Phase 1
(MP)-[:CAST_VOTE {position: STRING, dissent: BOOLEAN}]->(Vote)
(MP)-[:SERVED_TERM]->(Term)-[:IN_PARTY]->(Party)
(Term)-[:REPRESENTED]->(Riding)

// Phase 2
(MP)-[:RAN_AS]->(Candidacy)-[:IN_ELECTION]->(Election)

// Phase 3
(MP)-[:SPOKE {wordcount: INT}]->(Statement)
(Statement)-[:MENTIONED]->(Bill)

// Phase 4
(Donor)-[:DONATED]->(Contribution)-[:TO_PARTY|TO_MP]->
```

## Data Sources & Update Strategy

### Primary Sources
1. **OpenParliament PostgreSQL dump** - Complete historical data (1994-present)
   - Frequency: Monthly full sync
   - Coverage: 500K votes, 2M statements, 50K elections, 200K contributions
   - Source of truth for conflicts

2. **OpenParliament API** - Current session only
   - Frequency: Daily incremental updates
   - Coverage: Latest bills, votes, MPs
   - Fast, reliable

3. **LEGISinfo JSON** - Bill details
   - Frequency: Daily
   - Coverage: Current parliament bills

### Update Schedule (Recommended)
- **Daily (6am ET):** API-based incremental sync
- **Monthly (1st Sunday, 2am ET):** Full PostgreSQL sync

## Key Findings from Analysis

### Critical Missing Data (Now Available)
1. **Individual Vote Records** - How each MP voted (Y/N/P) on every question
2. **Historical Terms** - MP party switches, riding changes over time
3. **Hansard Speeches** - 2M+ statements with full text
4. **Election Results** - Vote totals, margins, competitiveness
5. **Political Contributions** - 200K donations with amounts and dates

### Database Statistics
- **Total Size:** 1.3GB compressed, ~6GB uncompressed
- **Total Tables:** 63 (13 core, 5 bills, 5 hansard, 7 committees, etc.)
- **Largest Tables:**
  - `hansards_statement`: 2M+ rows (speeches)
  - `bills_membervote`: 500K+ rows (individual votes)
  - `financials_contribution`: 200K+ rows (donations)
  - `elections_candidacy`: 50K+ rows (election results)

## Success Metrics

### After Phase 1
- ✅ Can answer "How did every MP vote on Bill C-11?"
- ✅ Can track "When did MP X switch from Party A to Party B?"
- ✅ Can detect "MPs who voted against party line"

### After All Phases
- ✅ Can search "Find Trudeau speeches mentioning climate"
- ✅ Can analyze "Who donated to Conservatives in 2019?"
- ✅ Can correlate "Donations → Votes → Party loyalty"

## Technical Considerations

### Performance
- **Expected Neo4j Scale:** 5M+ nodes, 15M+ relationships
- **Storage:** ~50GB (with full Hansard text)
- **RAM Recommendation:** ≥16GB for Neo4j

### Preservation of Existing Functionality
- **Zero breaking changes** - All existing queries work unchanged
- **Additive approach** - New relationships supplement existing ones
- **Backward compatible** - `mp.party` and `mp.riding` remain for current lookup

## OpenParliament Source Code Insights

### Django Models (Most Relevant)
- **core/models.py** - Politician, Party, Session, ElectedMember
- **bills/models.py** - Bill, VoteQuestion, MemberVote, PartyVote
- **hansards/models.py** - Document, Statement (with bill/politician links)
- **committees/models.py** - Committee, CommitteeMeeting, CommitteeReport
- **elections/models.py** - Election, Candidacy

### Import Scripts
- **legisinfo.py** - Fetches bills from parl.ca API
- **parl_document.py** - Downloads Hansard XML
- **parl_cmte.py** - Scrapes committee data
- **parlvotes.py** - Imports voting records
- **mps.py** - Updates MP information
- **election.py** - Election results

## Files Created

### Scripts
- `scripts/setup_openparliament_db.sh` - PostgreSQL database setup and dump load

### Documentation
- `OPENPARLIAMENT_INTEGRATION.md` (this file) - Integration tracking doc

### To Be Created
- `packages/data-pipeline/fedmcp_pipeline/clients/postgres_client.py` - PostgreSQL connection utilities
- `packages/data-pipeline/fedmcp_pipeline/ingest/openparliament.py` - Import functions
- `packages/data-pipeline/scripts/openparliament_sync.py` - Monthly sync script

## Resources

- **OpenParliament GitHub:** https://github.com/michaelmulley/openparliament
- **SQL Dump Location:** `/Users/matthewdufresne/FedMCP/openparliament.public.sql.bz2`
- **PostgreSQL Path:** `/opt/homebrew/opt/postgresql@14/bin`
- **Database Name:** `openparliament`
- **Database User:** `fedmcp` / `fedmcp2024`

## Contact

For questions or to continue implementation, refer to:
1. This document for current status
2. The comprehensive analysis report generated by the Plan agent
3. The 6-week implementation plan in the ExitPlanMode output

---

**Last Updated:** 2025-11-05
**Status:** Phase 1 - PostgreSQL Setup Complete
**Next Action:** Run `./scripts/setup_openparliament_db.sh`
