# Bill C-12 Data Investigation Summary

**Investigation Date**: December 2025
**Bill**: C-12, Session 45-1
**Test URL**: `http://localhost:3000/en/bills/45-1/C-12`

## Executive Summary

Investigation of bill C-12 revealed **data ingestion issues** preventing votes and lobbying information from displaying on the bill detail page. The root cause is missing Neo4j relationships between Vote/Organization nodes and the Bill node, despite the raw data existing in the database.

## Issues Discovered

### 1. Votes Not Connected to Bill ❌

**Symptom**: Votes tab shows empty state despite votes existing

**Investigation**:
```cypher
// Check if bill exists
MATCH (b:Bill {number: "C-12", session: "45-1"})
RETURN b
// ✅ Result: Bill node exists

// Check for votes via relationship (as GraphQL schema expects)
MATCH (v:Vote)-[:SUBJECT_OF]->(b:Bill {number: "C-12", session: "45-1"})
RETURN v.date, v.result, v.description, v.yeas, v.nays
// ❌ Result: No results (0 rows)

// Check for votes with bill_number property
MATCH (v:Vote {bill_number: "C-12"})
RETURN v.date, v.result, v.description
// ✅ Result: Votes exist with bill_number property
```

**Root Cause**:
- GraphQL schema at `packages/graph-api/src/schema.ts:246` expects:
  ```typescript
  votes: [Vote!]! @relationship(type: "SUBJECT_OF", direction: IN)
  ```
- Votes exist in Neo4j with `bill_number` property but **lack the `:SUBJECT_OF` relationship** connecting them to Bill nodes
- This is a **data ingestion pipeline issue** in `packages/data-pipeline/fedmcp_pipeline/ingest/votes_xml_import.py`

**Required Fix**: Update votes ingestion to create relationship:
```cypher
MATCH (v:Vote {bill_number: "C-12"})
MATCH (b:Bill {number: "C-12", session: "45-1"})
MERGE (v)-[:SUBJECT_OF]->(b)
```

### 2. No Lobbying Data for C-12 ❌

**Investigation**:
```cypher
// Check lobbying organizations
MATCH (org:Organization)-[r:LOBBIED_ON]->(b:Bill {number: "C-12", session: "45-1"})
RETURN org.name, org.industry, count(r) as lobbying_count
ORDER BY lobbying_count DESC
// ❌ Result: No results (0 rows)

// Check if any lobbying data exists in database
MATCH (org:Organization)-[r:LOBBIED_ON]->(b:Bill)
RETURN count(r) as total_lobbying_events
// Result: TBD (query not yet run)
```

**Possible Causes**:
1. No lobbying has occurred on C-12 (unlikely for a major bill)
2. Lobbying data not ingested yet for this session
3. Bill matching issue in ingestion (e.g., lowercase vs uppercase bill numbers)

**Required Investigation**: Check lobbying ingestion pipeline in `packages/data-pipeline/fedmcp_pipeline/ingest/lobbying.py`

### 3. Committee Reference Exists ✅

**Investigation**:
```cypher
// Check committee references
MATCH (b:Bill {number: "C-12", session: "45-1"})-[:REFERRED_TO]->(c:Committee)
RETURN c.code, c.name
// ✅ Result: SECU committee found
```

**Status**: Working correctly - frontend displays committee card

## Frontend Fixes Applied

Despite backend data issues, the following frontend improvements were made:

1. **Votes Tab Loading State** (completed):
   - Added proper loading state: `{billLoading ? <Loading /> : ...}`
   - Improved null checking: `bill?.votes && Array.isArray(bill.votes) && bill.votes.length > 0`
   - Better UX when no votes available

2. **Clickable Committee Cards** (completed):
   - Changed from plain `<div>` to `<Link>` component
   - Links to: `/${locale}/committees/${committee.code}?bill=${bill.session}/${bill.number}`
   - Added hover effects

3. **LEGISinfo External Link** (completed):
   - Added external reference in bill header
   - Link format: `https://www.parl.ca/legisinfo/${locale}/bill/${bill.session}/${bill.number.toLowerCase()}`

## Recommended Actions

### Immediate (Data Pipeline Fixes)

1. **Fix Votes Relationship Creation**:
   - File: `packages/data-pipeline/fedmcp_pipeline/ingest/votes_xml_import.py`
   - Action: After creating Vote nodes, create `:SUBJECT_OF` relationships to Bill nodes
   - Query pattern:
     ```cypher
     MATCH (v:Vote)
     WHERE v.bill_number IS NOT NULL
     MATCH (b:Bill)
     WHERE b.number = v.bill_number AND b.session = v.session
     MERGE (v)-[:SUBJECT_OF]->(b)
     ```

2. **Investigate Lobbying Data**:
   - File: `packages/data-pipeline/fedmcp_pipeline/ingest/lobbying.py`
   - Check if lobbying data is being ingested for session 45-1
   - Verify bill number matching logic (case sensitivity, formatting)

3. **Run Backfill Script**:
   - Create one-time migration script to connect existing Vote nodes to Bill nodes
   - Test on local Neo4j before running on production

### Short-term (Frontend Implementation)

4. **Complete Lobbying Timeline Feature**:
   - Update GET_BILL_LOBBYING query to include `communications` field
   - Create BillLobbyingTimeline and LobbyingCommunicationCard components
   - Feature will work once backend data is fixed

5. **Add Committee Evidence**:
   - Create GET_BILL_COMMITTEE_EVIDENCE query
   - Display meeting cards and testimony excerpts
   - Feature ready for when committee evidence data is available

## Testing Checklist

After data pipeline fixes:

- [ ] Verify votes display for C-12: `http://localhost:3000/en/bills/45-1/C-12`
- [ ] Check vote result badges (Passed/Failed) styled correctly
- [ ] Verify yea/nay counts display
- [ ] Confirm lobbying organizations list appears
- [ ] Verify lobbying communications timeline displays
- [ ] Test with other bills (C-11, C-13) to ensure fix is general

## Related Files

**Frontend**:
- `/packages/frontend/src/app/[locale]/bills/[session]/[number]/page.tsx` (lines 536-590: Votes tab)
- `/packages/frontend/src/lib/queries.ts` (line 449: GET_BILL query)

**Backend**:
- `/packages/graph-api/src/schema.ts` (line 246: Bill.votes relationship)
- `/packages/data-pipeline/fedmcp_pipeline/ingest/votes_xml_import.py` (votes ingestion)
- `/packages/data-pipeline/fedmcp_pipeline/ingest/lobbying.py` (lobbying ingestion)

**Deployment**:
- `./scripts/deploy-votes-ingestion.sh`
- `./scripts/deploy-lobbying-ingestion.sh`

## Neo4j Manual Fix (Temporary)

If you need to manually connect existing votes to C-12 for testing:

```cypher
// Connect all votes with bill_number = "C-12" to the Bill node
MATCH (v:Vote {bill_number: "C-12"})
MATCH (b:Bill {number: "C-12", session: "45-1"})
MERGE (v)-[:SUBJECT_OF]->(b)
RETURN count(*) as relationships_created;

// Verify
MATCH (v:Vote)-[:SUBJECT_OF]->(b:Bill {number: "C-12", session: "45-1"})
RETURN v.date, v.result, v.description, v.yeas, v.nays
ORDER BY v.date DESC;
```

---

**Status**: Document created December 2025
**Next Steps**: Fix data ingestion pipeline, then continue with lobbying timeline and committee evidence UI implementation
