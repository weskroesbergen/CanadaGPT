"""Test bill text sample import from PostgreSQL to Neo4j."""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages/data-pipeline"))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.postgres_client import PostgresClient
from fedmcp_pipeline.ingest.bill_text import ingest_bill_text_sample

# Load environment
load_dotenv(Path(__file__).parent / "packages/data-pipeline/.env")

print("=" * 80)
print("BILL TEXT SAMPLE IMPORT TEST")
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
print("\n2. Running sample import (10 bill texts)...")
try:
    results = ingest_bill_text_sample(
        neo4j_client=neo4j_client,
        postgres_client=postgres_client,
        text_limit=10
    )

    print("\n3. Validating import...")

    # Verify bill texts were created
    text_count = neo4j_client.run_query("MATCH (bt:BillText) RETURN count(bt) as count")
    print(f"   BillText nodes in Neo4j: {text_count[0]['count']:,}")

    # Verify relationships
    has_text = neo4j_client.run_query("MATCH ()-[r:HAS_TEXT]->() RETURN count(r) as count")
    print(f"   HAS_TEXT relationships: {has_text[0]['count']:,}")

    # Sample a bill text
    print("\n4. Sample bill text:")
    sample = neo4j_client.run_query("""
        MATCH (bt:BillText)
        WHERE bt.text_en IS NOT NULL AND bt.text_en <> ''
        RETURN bt.id as id,
               bt.docid as docid,
               substring(bt.text_en, 0, 200) as text_snippet,
               substring(bt.summary_en, 0, 150) as summary
        LIMIT 1
    """)

    if sample:
        text = sample[0]
        print(f"   ID: {text['id']}")
        print(f"   DocID: {text['docid']}")
        print(f"   Summary: {text['summary']}...")
        print(f"   Text: {text['text_snippet']}...")

    # Check which bills have text
    print("\n5. Checking Bill->BillText relationships:")
    bill_text_links = neo4j_client.run_query("""
        MATCH (b:Bill)-[:HAS_TEXT]->(bt:BillText)
        RETURN b.number as bill_number,
               b.name_en as bill_name,
               length(bt.text_en) as text_length
        LIMIT 5
    """)

    if bill_text_links:
        print(f"   Found {len(bill_text_links)} bills with text:")
        for link in bill_text_links:
            print(f"      {link['bill_number']}: {link['bill_name'][:50]}... ({link['text_length']:,} chars)")
    else:
        print("   ⚠️  No bills linked to text yet (bills may not be imported)")

    # Test full-text search
    print("\n6. Testing full-text search...")
    try:
        search_results = neo4j_client.run_query("""
            CALL db.index.fulltext.queryNodes("bill_text_en", "climate")
            YIELD node, score
            RETURN count(node) as matches
        """)
        print(f"   Full-text search working: {search_results[0]['matches']} matches for 'climate'")
    except Exception as e:
        print(f"   Full-text index not yet ready (this is normal): {e}")

    print("\n" + "=" * 80)
    print("✅ BILL TEXT SAMPLE IMPORT TEST COMPLETE")
    print("=" * 80)
    print(f"\nResults:")
    print(f"  BillText nodes: {results.get('bill_texts', 0):,}")
    print(f"  HAS_TEXT links: {results.get('has_text_links', 0):,}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    postgres_client.close()
    neo4j_client.close()
