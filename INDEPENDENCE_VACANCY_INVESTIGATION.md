# Investigation: Vacancies and Independent MPs in CanadaGPT System

## Executive Summary

This report documents how the CanadaGPT system currently handles independent MPs and vacant seats across the data pipeline, GraphQL API, and frontend UI. Key findings reveal **several gaps and potential issues**:

1. **Vacancies are partially handled**: Explicitly filtered in MP expenses but never stored in MP nodes
2. **Independent MPs are recognized**: Hardcoded as fallback party with gray color scheme
3. **Party field can be null**: GraphQL schema allows nullable party values, but no handling for this edge case
4. **No vacancy tracking**: No special node type or flag for vacant seats
5. **UI assumes all MPs have parties**: Components don't gracefully handle null party values
6. **Seat count mismatch risk**: No mechanism to track actual vs. expected seat counts

---

## 1. Database Schema (Neo4j)

### GraphQL Type Definition
**File**: `/packages/graph-api/src/schema.ts`

```typescript
type MP @node {
  id: ID! @unique
  name: String!
  party: String              // <-- NULLABLE! Not required
  riding: String
  current: Boolean!
  // ... other fields
  memberOf: Party @relationship(type: "MEMBER_OF", direction: OUT)
  // ...
}

type Party @node {
  code: ID! @unique
  name: String!
  // ...
  members: [MP!]! @relationship(type: "MEMBER_OF", direction: IN)
}
```

**Key Observations**:
- Party field is nullable (not `String!`)
- No special handling for null party values in schema
- No Vacancy node type defined
- SearchMPs query can filter by party: `WHERE ($party IS NULL OR mp.party = $party)` (line 529)

### Current Party Handling in Data Model
**Expected parties** (from parliament.py):
```python
party_mapping = {
    "Conservative": {"code": "CPC", "name": "Conservative Party of Canada"},
    "Liberal": {"code": "LPC", "name": "Liberal Party of Canada"},
    "NDP": {"code": "NDP", "name": "New Democratic Party"},
    "Bloc Québécois": {"code": "BQ", "name": "Bloc Québécois"},
    "Green": {"code": "GPC", "name": "Green Party of Canada"},
    "Independent": {"code": "IND", "name": "Independent"},
    "People's Party": {"code": "PPC", "name": "People's Party of Canada"},
}
```

---

## 2. Data Ingestion Pipeline

### MP Ingestion
**File**: `/packages/data-pipeline/fedmcp_pipeline/ingest/parliament.py` (lines 21-139)

#### Current Party Extraction (Lines 64-69):
```python
current_party = mp_data.get("current_party") or {}
party_name = current_party.get("short_name", {}).get("en") \
    if isinstance(current_party.get("short_name"), dict) \
    else current_party.get("short_name")
```

**Issues**:
- If `current_party` is None/empty dict, `party_name` becomes None
- No special handling for vacant seats
- No check if party is a valid entry

#### Fallback on Error (Lines 119-120):
```python
current_party = mp_summary.get("current_party") or {}
party_name = current_party.get("short_name", {}).get("en") \
    if isinstance(current_party.get("short_name"), dict) \
    else current_party.get("short_name")
```

#### Storage (Lines 90-114):
```python
mp_props = {
    "id": mp_id,
    "name": mp_data.get("name"),
    "party": party_name,  # <-- Can be None
    "current": mp_summary.get("current", True),
    # ... other fields
}

# Filter out None values
mp_props = {k: v for k, v in mp_props.items() if v is not None}
```

**Critical Issue**: When `party_name` is None, it gets filtered out and NOT stored as null. This means MPs with no party are indistinguishable from MPs with data errors.

### Party Node Creation
**File**: `/packages/data-pipeline/fedmcp_pipeline/ingest/parliament.py` (lines 142-197)

```python
def ingest_parties(neo4j_client: Neo4jClient) -> int:
    # Query existing MPs to get unique parties
    result = neo4j_client.run_query(
        """
        MATCH (m:MP)
        WHERE m.party IS NOT NULL
        WITH DISTINCT m.party AS party_name
        RETURN party_name
        ORDER BY party_name
        """
    )
    
    parties = [record["party_name"] for record in result]
```

**Important**: Only NON-NULL party values are extracted. This means no "party" node is created for MPs with null party values.

### MP-Party Relationships
No explicit relationship creation code found for MP->Party connections in parliament.py. Party relationships appear to be managed through the GraphQL relationship definition only.

### Vacant Seat Handling in Expenses
**File**: `/packages/data-pipeline/fedmcp_pipeline/ingest/finances.py` (lines 69-71)

```python
# Skip vacant seats
if mp_expenses.name == "Vacant":
    continue
```

**Issue**: Vacancies are filtered out but NEVER stored as a separate entity or flag. This means:
- No record of which seats are vacant
- No way to query vacant ridings
- Seat counts in party pages will be inaccurate vs. actual parliamentary seats

---

## 3. GraphQL API

### Schema Query for MPs
**File**: `/packages/graph-api/src/schema.ts` (lines 518-542)

```typescript
searchMPs(
  searchTerm: String
  party: String
  current: Boolean
  cabinetOnly: Boolean
  limit: Int = 500
): [MP!]!
  @cypher(
    statement: """
    MATCH (mp:MP)
    WHERE ($current IS NULL OR mp.current = $current)
      AND ($party IS NULL OR mp.party = $party)
      AND ($cabinetOnly IS NULL OR $cabinetOnly = false OR mp.cabinet_position IS NOT NULL)
      AND (
        $searchTerm IS NULL OR $searchTerm = '' OR
        toLower(mp.name) CONTAINS toLower($searchTerm) OR
        toLower(COALESCE(mp.given_name, '')) CONTAINS toLower($searchTerm) OR
        toLower(COALESCE(mp.family_name, '')) CONTAINS toLower($searchTerm)
      )
    RETURN mp
    ORDER BY mp.name ASC
    LIMIT $limit
    """
  )
```

**Implications**:
- Query will NOT return MPs where `party IS NULL`
- No way to fetch independent MPs if party field is null
- Party filter `($party IS NULL OR mp.party = $party)` allows searching with null party, but won't find MPs with null party

---

## 4. Frontend UI

### Party Filter Configuration
**File**: `/packages/frontend/src/lib/partyConstants.ts`

```typescript
export const PARTIES: Record<string, PartyInfo> = {
  'Liberal': { /* ... */ },
  'Conservative': { /* ... */ },
  'NDP': { /* ... */ },
  'Bloc Québécois': { /* ... */ },
  'Green': { /* ... */ },
  'Independent': {
    name: 'Independent',
    slug: 'independent',
    color: '#6B7280',  // Gray
    darkColor: '#4B5563',
    lightColor: '#F3F4F6',
    textColor: '#FFFFFF',
    fullName: 'Independent',
  },
};
```

**Key Functions**:

1. `getPartyInfo()` (lines 92-118):
   - Returns Independent (gray color) as fallback if party not found
   - Handles null/undefined by returning null (line 92)
   - Will NOT return Independent if party is explicitly null

2. `getMajorParties()` (lines 158-160):
   - Filters to exclude Independent
   - Used for party filter buttons
   - **Issue**: Independent MPs won't appear in filter if party is null

### Party Filter Buttons
**File**: `/packages/frontend/src/components/PartyFilterButtons.tsx`

```typescript
const parties = getMajorParties();  // Excludes Independent

return (
  <div className={`flex items-center gap-2 overflow-x-auto pb-2 py-1 justify-end`}>
    {/* "All Parties" button */}
    {showAllOption && (
      <button onClick={() => onSelect([])}>All Parties</button>
    )}
    
    {/* Individual party buttons - NO Independent option! */}
    {parties.map((party) => (
      <button key={party.slug} onClick={() => handleToggle(party.name)}>
        {party.name.charAt(0)}
      </button>
    ))}
  </div>
);
```

**Critical Issues**:
1. No "Independent" filter button visible to users
2. Independent MPs can only be shown by filtering for "All Parties"
3. If frontend hardcodes "Independent" string, but backend returns null, filter won't work

### MP Display Components
**File**: `/packages/frontend/src/components/MPCard.tsx`

```typescript
<div className="flex-1 min-w-0 pr-8">
  <h3 className="font-semibold text-text-primary truncate">{mp.name}</h3>
  
  {/* Party display - will be empty if mp.party is null! */}
  <p className="text-sm text-text-secondary">{mp.party}</p>
  
  <p className="text-sm text-text-tertiary truncate">{mp.riding}</p>
</div>
```

**Issue**: If `mp.party` is null, the party line will display nothing or "null" - not user-friendly.

### Chamber View
**File**: `/packages/frontend/src/app/chamber/page.tsx` (lines 32-38)

```typescript
data.searchMPs.forEach((mp: any) => {
  const party = mp.party || 'Independent';  // <-- Default to Independent
  if (!mpsByParty.has(party)) {
    mpsByParty.set(party, []);
  }
  mpsByParty.get(party)!.push(mp);
});
```

**Good**: Falls back to "Independent" if party is null. However:
- Only works if getPartyInfo('Independent') returns valid info
- Seat count will be incorrect if any actual vacancies exist

### Party Page
**File**: `/packages/frontend/src/app/parties/[slug]/page.tsx` (lines 38-45)

```typescript
const parties = ['Liberal', 'Conservative', 'NDP', 'Bloc Québécois', 'Green', 'Independent'];
for (const partyName of parties) {
  if (getPartySlug(partyName) === params.slug) {
    matchedPartyName = partyName;
    break;
  }
}
```

**Issue**: Hardcoded party list doesn't account for:
- People's Party
- Any unrecognized parties in the database
- No dynamic party discovery

### MPs Page
**File**: `/packages/frontend/src/app/mps/page.tsx` (lines 34-38)

```typescript
const filteredMPs = partyFilter.length === 0
  ? data?.searchMPs || []
  : (data?.searchMPs || []).filter((mp: any) =>
      partyFilter.includes(mp.party || mp.memberOf?.name)  // <-- Fallback to memberOf
    );
```

**Good**: Falls back to memberOf relationship. However:
- This only works if MPs have actual party relationships in database
- Doesn't account for null party values in filter logic

---

## 5. Critical Issues Summary

### Issue 1: No Vacancy Tracking
**Severity**: HIGH

**Problem**:
- Expenses pipeline explicitly skips vacant seats (line 70, finances.py)
- No Vacancy node type created
- No flag on Riding nodes for vacancy
- Seat count in party pages will be inaccurate

**Impact**:
- Can't answer: "Which ridings are currently vacant?"
- Can't calculate: "How many vacancies exist?"
- Party seat counts include only MPs, not accounting for empty seats

**Example**:
```
House of Commons: 338 total seats
If 5 seats are vacant:
- Party A: 100 MPs (but represents 100 seats out of 338)
- Frontend shows 100 seats, but 105 seats are actually empty
- Total displayed: 330 MPs vs 338 actual seats
```

### Issue 2: Null vs. String 'Independent' Mismatch
**Severity**: HIGH

**Problem**:
- Data pipeline stores `party: null` for independent MPs (None values filtered out)
- Frontend hardcodes `party: 'Independent'` string as fallback
- Mismatch causes filter/display issues

**Impact**:
```
Database: {name: "John Smith", party: null}
Frontend receives: {name: "John Smith"}  // party key missing
Falls back to: {party: 'Independent'}   // string value

Query: searchMPs(party: "Independent") 
Result: EMPTY - because DB has null, not "Independent" string
```

### Issue 3: Party Filter Button Missing Independent
**Severity**: MEDIUM

**Problem**:
- `getMajorParties()` excludes Independent
- No visual way for users to filter for just independent MPs
- Users can only see independents by viewing "All Parties"

**Impact**:
- Can't analyze just independent MPs
- Can't count independent representation

### Issue 4: GraphQL Query Excludes Null Party MPs
**Severity**: HIGH

**Problem**:
- SearchMPs query: `WHERE ($party IS NULL OR mp.party = $party)`
- If user passes `party: "Independent"` but DB has `null`, no match
- If user passes no party filter but wants independents, get empty results

**Impact**:
```cypher
# What user might try:
searchMPs(party: "Independent")

# What database has:
MP {id: "john-smith", party: null}

# Result: No match! Because:
# "Independent" != null
# AND null != "Independent"
```

### Issue 5: No Party Relationship for Independent MPs
**Severity**: MEDIUM

**Problem**:
- Party ingestion only extracts non-null parties (parliament.py line 154)
- If MP has `party: null`, no Party node is created
- MP->Party relationship cannot be created
- Graph queries relying on memberOf will fail

**Impact**:
```
GraphQL query:
{
  mps {
    name
    memberOf {  // <-- Will be null for independents
      name
    }
  }
}
```

### Issue 6: Hard-Coded Party Lists in UI
**Severity**: LOW

**Problem**:
- Party page hardcodes 6 parties (parties/[slug]/page.tsx line 39)
- Excludes People's Party and others

**Impact**:
- People's Party members won't have a dedicated party page
- Unknown future parties won't be displayed

---

## 6. Data Flow Diagram

### Current Flow (BROKEN):
```
OpenParliament API
  ↓
  MP with current_party: null
  ↓
parliament.py: ingest_mps()
  party_name = None
  filtered out ← None values removed!
  ↓
Neo4j: MP {id, name, ...}  ← NO party field!
  ↓
GraphQL searchMPs
  Returns MPs without party field
  ↓
Frontend: mp.party = undefined
  Falls back to 'Independent' string
  ↓
Display: Shows "Independent" but DB has null
```

### Desired Flow:
```
OpenParliament API
  ↓
  MP with current_party: null (or missing)
  ↓
parliament.py: ingest_mps()
  party_name = "Independent"  ← Explicitly set
  ↓
Neo4j: MP {id, name, party: "Independent"}
  ↓
Parties: Extract "Independent" and create Party node
  ↓
Relationships: MP -[MEMBER_OF]-> Party (Independent)
  ↓
GraphQL: searchMPs(party: "Independent") returns results
  ↓
Frontend: Consistent display with database
```

---

## 7. Specific File Locations and Line Numbers

### Database Schema
- `/packages/graph-api/src/schema.ts`
  - MP type with nullable party: Line 19
  - Party type: Line 56
  - searchMPs query: Lines 518-542

### Data Ingestion
- `/packages/data-pipeline/fedmcp_pipeline/ingest/parliament.py`
  - MP ingestion: Lines 21-139
  - Party ingestion: Lines 142-197
  - Party extraction query: Lines 152-159
  - None filtering: Lines 113, 133

- `/packages/data-pipeline/fedmcp_pipeline/ingest/finances.py`
  - Vacant seat skip: Lines 69-71

### Frontend
- `/packages/frontend/src/lib/partyConstants.ts`
  - Party definitions: Lines 25-86
  - getPartyInfo(): Lines 92-118
  - getMajorParties(): Lines 158-160

- `/packages/frontend/src/components/PartyFilterButtons.tsx`
  - Filter logic: Lines 20-37
  - No Independent button: Line 26 (uses getMajorParties)

- `/packages/frontend/src/components/MPCard.tsx`
  - Party display: Line 61
  - No null handling

- `/packages/frontend/src/app/chamber/page.tsx`
  - Fallback to Independent: Line 33
  - Seat count calculation: Lines 29-48

- `/packages/frontend/src/app/parties/[slug]/page.tsx`
  - Hard-coded party list: Line 39
  - No People's Party: Lines 38-45

### GraphQL Queries
- `/packages/frontend/src/lib/queries.ts`
  - SEARCH_MPS query: Lines 76-83
  - No party field explicitly requested (relies on fragment)

---

## 8. Recommended Fixes

### Priority 1 (Critical - Fixes Data Integrity)

1. **Explicit Independent Party Handling**
   ```python
   # In parliament.py, ingest_mps()
   if party_name is None or party_name.strip() == "":
       party_name = "Independent"
   ```

2. **Don't Filter Out None Party Values**
   ```python
   # Instead of filtering all None values:
   # mp_props = {k: v for k, v in mp_props.items() if v is not None}
   
   # Keep party: null relationships in database for tracking
   # OR explicitly set to "Independent"
   ```

3. **Create Vacancy Node Type**
   ```typescript
   type Vacancy @node {
     id: ID! @unique
     riding_id: String!
     riding_name: String!
     opened_date: Date!
     updated_at: DateTime!
     
     affectsRiding: Riding @relationship(type: "AFFECTS", direction: OUT)
   }
   ```

### Priority 2 (High - Ensures Consistency)

4. **Ensure Independent Party Node Always Exists**
   ```python
   # In parliament.py, ingest_parties()
   # Ensure Independent party is always created
   parties_data = [
       {"code": "IND", "name": "Independent", ...},
       # ... other parties
   ]
   ```

5. **Create MP->Party Relationships for Independents**
   ```python
   # Link independent MPs to Independent party
   query = """
   MATCH (m:MP {party: "Independent"})
   MATCH (p:Party {code: "IND"})
   MERGE (m)-[:MEMBER_OF]->(p)
   """
   ```

### Priority 3 (Medium - Improves UX)

6. **Add Independent to Filter Buttons**
   ```typescript
   // In partyConstants.ts
   export function getAllParties(): PartyInfo[] {
     return Object.values(PARTIES);  // Include Independent
   }
   
   // In PartyFilterButtons.tsx
   const parties = getAllParties();  // Not getMajorParties()
   ```

7. **Dynamic Party List from Database**
   ```typescript
   // In parties/[slug]/page.tsx
   const { data } = useQuery(GET_ALL_PARTIES);
   const matchedPartyName = data?.parties?.find(p => 
     getPartySlug(p.name) === params.slug
   )?.name;
   ```

8. **Explicit Null Handling in Components**
   ```typescript
   // In MPCard.tsx
   const partyDisplay = mp.party || 'Independent';
   <p className="text-sm text-text-secondary">{partyDisplay}</p>
   ```

---

## 9. Testing Recommendations

### Test Cases Needed

1. **Independent MP Flow**
   ```python
   # Test: Fetch MP with null party from OpenParliament
   mp = op_client.get_mp("url-to-independent-mp")
   # Verify: mp['current_party'] is None/empty
   
   # After ingest: Query database
   result = neo4j.run_query("MATCH (m:MP) RETURN m.party")
   # Verify: mp.party = "Independent"
   ```

2. **Party Filter Test**
   ```graphql
   query {
     searchMPs(party: "Independent") {
       id
       name
       party
     }
   }
   # Expected: Returns 1+ MPs with party: "Independent"
   ```

3. **Seat Count Accuracy**
   ```python
   # Test: Count all MPs should = 338 (current seats)
   total_mps = neo4j.run_query("MATCH (m:MP) RETURN count(m)")
   expected_seats = 338
   vacant_seats = neo4j.run_query("MATCH (v:Vacancy) RETURN count(v)")
   
   assert total_mps + vacant_seats == expected_seats
   ```

4. **UI Fallback Test**
   ```
   When frontend receives: {name: "John Smith", party: null}
   Component should display: Party: "Independent"
   Not: Party: "null" or Party: "" (blank)
   ```

---

## 10. Conclusion

The CanadaGPT system recognizes the concept of "Independent" parties but has several critical gaps:

1. **No explicit storage** of independent MP designation - relies on null handling
2. **No vacancy tracking** - empty seats are ignored entirely
3. **Inconsistent representation** - null in database vs. "Independent" string in UI
4. **No graph relationships** - independents can't be queried reliably
5. **UI limitations** - no dedicated filter for independent MPs

These gaps should be addressed with priority to ensure:
- Accurate parliamentary representation
- Reliable independent MP identification
- Queryable vacancy information
- Consistent frontend-backend behavior
