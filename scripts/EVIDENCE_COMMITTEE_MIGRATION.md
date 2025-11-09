# Evidence-Committee Relationship Migration

## Overview

This migration creates `PRESENTED_TO` relationships between Evidence documents (`Document` nodes with `document_type: 'E'`) and their respective `Committee` nodes.

## Schema Changes

### Document Type
Added relationship:
```graphql
presentedTo: Committee @relationship(type: "PRESENTED_TO", direction: OUT)
```

### Committee Type
Added relationship:
```graphql
evidence: [Document!]! @relationship(type: "PRESENTED_TO", direction: IN)
```

## Running the Migration

### Prerequisites
- Neo4j database is running
- You have admin credentials
- Evidence documents have been ingested with proper `session_id` format

### Local Development

```bash
# Using cypher-shell with environment variables
NEO4J_URI=bolt://localhost:7687 NEO4J_USERNAME=neo4j NEO4J_PASSWORD=canadagpt2024 \
cypher-shell -f /Users/matthewdufresne/FedMCP/scripts/link_evidence_to_committees.cypher
```

### Production (GCP VM)

```bash
# SSH into the ingestion VM
gcloud compute ssh canadagpt-ingestion-vm --zone us-central1-a

# Run the migration
cypher-shell -u neo4j -p <production-password> \
-f /path/to/link_evidence_to_committees.cypher
```

## Data Pattern

Evidence documents use `session_id` format: `"45-1-ETHI-5"`
- `45` = Parliament number
- `1` = Session number
- `ETHI` = Committee code
- `5` = Meeting number

The migration extracts the committee code (3rd segment) and links to the matching `Committee` node.

## Verification

After running the migration, verify the results:

```cypher
// Count Evidence documents per committee
MATCH (d:Document {document_type: 'E'})-[:PRESENTED_TO]->(c:Committee)
RETURN c.code, c.name, count(d) as evidence_count
ORDER BY evidence_count DESC;

// Check for unlinked Evidence documents
MATCH (d:Document {document_type: 'E'})
WHERE d.session_id IS NOT NULL AND NOT exists((d)-[:PRESENTED_TO]->())
RETURN count(d) as unlinked_count;
```

## Impact on GraphQL API

After this migration, committees can query their evidence:

```graphql
query GetCommitteeEvidence($code: ID!) {
  committees(where: { code: $code }) {
    code
    name
    evidence(options: { limit: 20, sort: [{ date: DESC }] }) {
      id
      date
      session_id
      statements {
        content_en
        who_en
      }
    }
  }
}
```

## Rollback

To remove the relationships (if needed):

```cypher
MATCH (d:Document)-[r:PRESENTED_TO]->(c:Committee)
WHERE d.document_type = 'E'
DELETE r;
```

## Next Steps

After running this migration:
1. GraphQL schema has been updated with the relationships
2. Frontend can query evidence documents by committee
3. Committee testimony queries will be more efficient
4. Witness tracking can be implemented based on Evidence documents
