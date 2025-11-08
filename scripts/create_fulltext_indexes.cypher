// Create full-text search indexes for Hansard content
// Run this on the Neo4j instance to enable searchHansard functionality

// Drop existing indexes if they exist
DROP INDEX statement_content_en IF EXISTS;
DROP INDEX statement_content_fr IF EXISTS;

// Create English content index
CREATE FULLTEXT INDEX statement_content_en
FOR (s:Statement)
ON EACH [s.content_en, s.who_en, s.h2_en, s.h3_en];

// Create French content index
CREATE FULLTEXT INDEX statement_content_fr
FOR (s:Statement)
ON EACH [s.content_fr, s.who_fr, s.h2_fr, s.h3_fr];

// Verify indexes were created
SHOW INDEXES;
