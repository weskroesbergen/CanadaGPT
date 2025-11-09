// ============================================
// Link Evidence Documents to Committees
// ============================================
// This migration creates PRESENTED_TO relationships between Evidence documents
// and their respective committees based on session_id patterns.
//
// Evidence documents have session_ids in format: "45-1-ETHI-5" where ETHI is the committee code
// This script extracts the committee code and creates relationships.
//
// Run with: cypher-shell -u neo4j -p <password> -f link_evidence_to_committees.cypher

// First, let's see how many Evidence documents exist
MATCH (d:Document {document_type: 'E'})
RETURN count(d) as total_evidence_docs;

// Create relationships between Evidence documents and Committees
// Extract committee code from session_id (format: "45-1-ETHI-5")
MATCH (d:Document {document_type: 'E'})
WHERE d.session_id IS NOT NULL
WITH d, split(d.session_id, '-') as parts
WHERE size(parts) >= 3
WITH d, parts[2] as committee_code
MATCH (c:Committee {code: committee_code})
MERGE (d)-[:PRESENTED_TO]->(c)
RETURN count(*) as relationships_created;

// Verify the results
MATCH (d:Document {document_type: 'E'})-[:PRESENTED_TO]->(c:Committee)
RETURN c.code as committee_code, c.name as committee_name, count(d) as evidence_count
ORDER BY evidence_count DESC;

// Show Evidence documents that couldn't be linked (for debugging)
MATCH (d:Document {document_type: 'E'})
WHERE d.session_id IS NOT NULL AND NOT exists((d)-[:PRESENTED_TO]->())
WITH d, split(d.session_id, '-') as parts
RETURN d.id, d.session_id,
       CASE WHEN size(parts) >= 3 THEN parts[2] ELSE 'INVALID' END as extracted_code
LIMIT 10;
