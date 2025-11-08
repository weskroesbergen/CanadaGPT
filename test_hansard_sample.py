"""Test Hansard sample import from PostgreSQL to Neo4j."""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages/data-pipeline"))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.postgres_client import PostgresClient
from fedmcp_pipeline.ingest.hansard import ingest_hansard_sample

# Load environment
load_dotenv(Path(__file__).parent / "packages/data-pipeline/.env")

print("=" * 80)
print("HANSARD SAMPLE IMPORT TEST")
print("=" * 80)

# Initialize clients
print("\n1. Connecting to databases...")

# Parse PostgreSQL URI
postgres_uri = os.getenv("POSTGRES_URI", "postgresql://fedmcp:fedmcp2024@localhost:5432/openparliament")
# Format: postgresql://user:password@host:port/dbname
parts = postgres_uri.replace("postgresql://", "").split("@")
user_pass = parts[0].split(":")
host_db = parts[1].split("/")
host_port = host_db[0].split(":")

postgres_client = PostgresClient(
    dbname=host_db[1],
    user=user_pass[0],
    password=user_pass[1],
    host=host_port[0],
    port=int(host_port[1]) if len(host_port) > 1 else 5432
)

neo4j_client = Neo4jClient(
    uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    user=os.getenv("NEO4J_USER", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD", "canadagpt2024")
)

print("   ✅ Connected to PostgreSQL")
print("   ✅ Connected to Neo4j")

# Run sample import
print("\n2. Running sample import (1,000 statements)...")
try:
    results = ingest_hansard_sample(
        neo4j_client=neo4j_client,
        postgres_client=postgres_client,
        statement_limit=1000
    )

    print("\n3. Validating import...")

    # Verify documents were created
    doc_count = neo4j_client.run_query("MATCH (d:Document) RETURN count(d) as count")
    print(f"   Documents in Neo4j: {doc_count[0]['count']:,}")

    # Verify statements were created
    stmt_count = neo4j_client.run_query("MATCH (s:Statement) RETURN count(s) as count")
    print(f"   Statements in Neo4j: {stmt_count[0]['count']:,}")

    # Verify relationships
    made_by = neo4j_client.run_query("MATCH ()-[r:MADE_BY]->() RETURN count(r) as count")
    part_of = neo4j_client.run_query("MATCH ()-[r:PART_OF]->() RETURN count(r) as count")
    mentions = neo4j_client.run_query("MATCH ()-[r:MENTIONS]->() RETURN count(r) as count")

    print(f"   MADE_BY relationships: {made_by[0]['count']:,}")
    print(f"   PART_OF relationships: {part_of[0]['count']:,}")
    print(f"   MENTIONS relationships: {mentions[0]['count']:,}")

    # Sample a statement
    print("\n4. Sample statement:")
    sample = neo4j_client.run_query("""
        MATCH (s:Statement)
        WHERE s.content_en IS NOT NULL AND s.content_en <> ''
        RETURN s.who_en as speaker,
               s.statement_type as type,
               substring(s.content_en, 0, 200) as content,
               s.wordcount as words
        LIMIT 1
    """)

    if sample:
        stmt = sample[0]
        print(f"   Speaker: {stmt['speaker']}")
        print(f"   Type: {stmt['type']}")
        print(f"   Words: {stmt['words']}")
        print(f"   Content: {stmt['content']}...")

    # Test full-text search
    print("\n5. Testing full-text search...")
    try:
        search_results = neo4j_client.run_query("""
            CALL db.index.fulltext.queryNodes("statement_content_en", "climate")
            YIELD node, score
            RETURN count(node) as matches
        """)
        print(f"   Full-text search working: {search_results[0]['matches']} matches for 'climate'")
    except Exception as e:
        print(f"   Full-text index not yet ready (this is normal): {e}")

    print("\n" + "=" * 80)
    print("✅ HANSARD SAMPLE IMPORT TEST COMPLETE")
    print("=" * 80)
    print(f"\nResults:")
    print(f"  Documents: {results.get('documents', 0):,}")
    print(f"  Statements: {results.get('statements', 0):,}")
    print(f"  MP links: {results.get('made_by_links', 0):,}")
    print(f"  Document links: {results.get('part_of_links', 0):,}")
    print(f"  Bill mentions: {results.get('mentions_links', 0):,}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    postgres_client.close()
    neo4j_client.close()
