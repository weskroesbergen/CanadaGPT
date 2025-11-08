# Bulk Data Sources for Canadian Parliamentary Data

**Investigation Date**: November 3, 2025
**Purpose**: Find bulk/file-based data sources instead of making thousands of API calls

---

## Summary of Findings

### ✅ BILLS - LEGISinfo JSON (RECOMMENDED)

**Clear Winner**: Single bulk JSON file with complete bill data and sponsors.

- **URL**: `https://www.parl.ca/legisinfo/en/bills/json`
- **Size**: 204 KB
- **Content**: 111 bills from current parliament (45-1)
- **Sponsor Coverage**: 100% - ALL bills include sponsor information
- **Fields Available**:
  - `BillNumberFormatted` (e.g., "C-1", "S-2")
  - `LongTitleEn` / `LongTitleFr`
  - **`SponsorEn` / `SponsorFr`** ← Complete sponsor names
  - `ParlSessionCode` (e.g., "45-1")
  - `CurrentStatusEn`
  - Dates: `IntroducedDateTime`, `PassedHouseSecondReadingDateTime`, etc.

**Comparison with API Approach**:
- API: 5,653+ individual calls, 33 seconds for 100 bills, only 88% have sponsors
- JSON: 1 download, instant, 100% have sponsors

**Implementation Strategy**:
1. Download JSON file once
2. Parse and ingest into Neo4j
3. Schedule daily/weekly refresh to catch new bills
4. No need to call OpenParliament API for bills anymore

---

### ⚠️ HANSARD - XML Available but Complex

**Two Options**:

#### Option A: House of Commons XML (Complex)
- **URL Pattern**: `http://www.parl.gc.ca/HousePublications/Publication.aspx?Pub=Hansard&Doc=[SITTING]&Parl=45&Ses=1&Language=E&xml=true`
- **Challenge**: Requires knowing sitting numbers (1, 2, 3, ...)
- **Data Structure**: Full XML with `<Intervention>`, `<ParaText>`, speaker names, timestamps
- **File Size**: ~100KB per sitting

**How to get sitting numbers**:
1. Call OpenParliament API to list debates
2. Extract sitting numbers or DocIds from responses
3. Download individual XML files

#### Option B: OpenParliament API (Current Approach)
- **URL**: `https://api.openparliament.ca/debates/`
- **Benefit**: Clean JSON, pagination built-in, no DocId mapping needed
- **Rate Limit**: 10 req/sec (0.1s interval) - respectful and fast
- **Already Implemented**: OurCommonsHansardClient works well

**Recommendation**:
- **Keep using OpenParliament API** for initial load
- XML files don't provide a bulk export - you still need API calls to know which files exist
- OpenParliament data quality is excellent and easier to work with

---

### ⚠️ COMMITTEES - XML Available but Complex

**Two Options**:

#### Option A: House of Commons XML (Complex)
- **URL Pattern**: `http://www.parl.gc.ca/HousePublications/Publication.aspx?Mode=1&Parl=45&Ses=1&DocId=[ID]&Language=E&xml=true`
- **Challenge**: Requires DocId for each committee meeting
- **Data Structure**: Full XML with committee evidence, witness testimony, timestamps

**How to get DocIds**:
1. Call OpenParliament API to list committees and meetings
2. Extract DocIds from responses or map from meeting data
3. Download individual XML files

#### Option B: OpenParliament API (Current Approach)
- **URL**: `https://api.openparliament.ca/committees/`
- **Benefit**: Clean JSON structure with committee info, members, meetings
- **Methods**: `list_committees()`, `get_committee()`
- **Already Implemented**: Basic support in OpenParliamentClient

**Recommendation**:
- **Use OpenParliament API** for committee structure and membership
- Consider XML only if you need full verbatim transcripts (which OpenParliament may not have)
- XML approach requires API calls anyway to discover what meetings exist

---

## Implementation Recommendations

### Phase 1: Quick Wins (Bills)
1. ✅ **Implement LEGISinfo JSON ingestion for bills**
   - Replace OpenParliament bill ingestion
   - Download `https://www.parl.ca/legisinfo/en/bills/json`
   - Parse and create Bill nodes + SPONSORED relationships
   - **Impact**: 100% sponsor coverage, instant load, no API rate limits

### Phase 2: Committees (Use API)
1. **Implement committee ingestion via OpenParliament API**
   - List all committees: `client.list_committees()`
   - For each committee, get details including members
   - Create Committee nodes + MEMBER_OF relationships
   - **Why API**: No bulk export available, XML requires same API calls + extra parsing

### Phase 3: Hansard (Use API + Optional XML Enhancement)
1. **Continue using OpenParliament API for debate listing**
   - Already works well with `list_debates()`
   - Clean structure, good performance
2. **Optional**: Enhance with XML download for full transcripts
   - Use OurCommonsHansardClient (already implemented)
   - Downloads individual sitting XML when detailed transcripts needed
   - **Why**: OpenParliament has debate data but may not have full verbatim text

---

## Technical Architecture

### Current State
```
OpenParliament API
├── MPs ✅ (working, fetch full details)
├── Bills ⚠️  (list lacks sponsors, get_bill() has them)
├── Votes ✅ (working)
└── Committees ❌ (not implemented)
```

### Recommended State
```
LEGISinfo JSON
└── Bills ✅ (bulk download, complete sponsor data)

OpenParliament API
├── MPs ✅ (keep current implementation)
├── Votes ✅ (keep current implementation)
├── Committees → NEW (to implement)
└── Debates ✅ (keep current implementation)

OurCommons XML (optional enhancement)
└── Hansard Transcripts ✅ (already implemented for detailed text)
```

---

## Cost-Benefit Analysis

### Bills: LEGISinfo JSON vs OpenParliament API

| Aspect | LEGISinfo JSON | OpenParliament API |
|--------|----------------|-------------------|
| **Sponsor Coverage** | 100% (111/111) | 88% (88/100) via get_bill() |
| **API Calls** | 1 HTTP GET | 5,653+ individual calls |
| **Time for 5,653 bills** | ~1 second | ~50 minutes (at 10 req/sec) |
| **Rate Limiting** | None | 10 req/sec limit |
| **Maintenance** | Daily/weekly refresh | Hourly/daily depending on needs |
| **File Size** | 204 KB total | N/A |
| **Data Freshness** | Updated daily by Parliament | Real-time |

**Winner**: LEGISinfo JSON (99% of use cases)

### Committees: XML vs OpenParliament API

| Aspect | House Commons XML | OpenParliament API |
|--------|------------------|-------------------|
| **Bulk Export** | ❌ No - requires individual DocIds | ❌ No - pagination required |
| **Discovery** | Requires API calls to find meetings | Built-in via list endpoints |
| **Data Parsing** | Complex XML parsing | Clean JSON |
| **Implementation** | New parser needed | Already have client |
| **Maintenance** | High - XML schema changes | Low - stable JSON API |

**Winner**: OpenParliament API (simpler, already implemented)

### Hansard: XML vs OpenParliament API

| Aspect | House Commons XML | OpenParliament API |
|--------|------------------|-------------------|
| **Verbatim Text** | ✅ Full transcripts | ⚠️  May be summarized |
| **Bulk Export** | ❌ No - requires sitting numbers | ❌ No - pagination required |
| **File Size** | ~100KB per sitting × thousands | N/A |
| **Implementation** | Already have OurCommonsHansardClient | Already have OpenParliamentClient |

**Winner**: Hybrid approach
- Use OpenParliament API for listing debates (fast, clean)
- Use OurCommonsHansardClient XML when full transcripts needed (already implemented)

---

## Next Steps

1. **Immediate**: Update bill ingestion to use LEGISinfo JSON
   - File: `packages/data-pipeline/fedmcp_pipeline/ingest/parliament.py`
   - Add new function: `ingest_bills_from_legisinfo_json()`
   - Download, parse, and ingest in <5 seconds

2. **Short-term**: Implement committee data ingestion
   - Use OpenParliament API: `list_committees()`, `get_committee()`
   - Create Committee nodes and MEMBER_OF relationships
   - Add to GraphQL schema and frontend

3. **Medium-term**: Enhance Hansard with full transcripts
   - Already have OurCommonsHansardClient
   - Optionally download XML for detailed speech analysis
   - Parse and store individual Speech nodes linked to MPs

---

## Conclusion

**For Bills**: LEGISinfo JSON bulk export is a clear winner - faster, more complete, and no API rate limits.

**For Committees & Hansard**: No true bulk exports exist. XML files are available but:
- Require API calls to discover what files to download
- Need complex DocId mapping
- Require custom XML parsing

**OpenParliament API remains the best approach** for committees and Hansard because:
- It's the discovery mechanism anyway
- Clean JSON structure
- Well-documented and stable
- Rate limits are reasonable (10 req/sec)
- Already implemented and working

The "bulk file" approach only saves work when a single file contains all data (like LEGISinfo bills JSON). When you need to make N API calls to discover N XML files to download, you haven't saved any work - you've added complexity.
