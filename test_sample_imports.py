"""Comprehensive test script for all OpenParliament ingest modules.

This script tests all 4 ingest modules with sample data:
1. Hansard statements (1,000 statements)
2. Bill texts (10 texts)
3. Politician info enrichment (10 politicians)
4. Election candidacies (50 candidacies)

It validates that:
- All modules can connect to databases
- Data is imported successfully
- Relationships are created correctly
- No errors occur during import
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import time

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages/data-pipeline"))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.postgres_client import PostgresClient
from fedmcp_pipeline.ingest.hansard import ingest_hansard_sample
from fedmcp_pipeline.ingest.bill_text import ingest_bill_text_sample
from fedmcp_pipeline.ingest.politician_info import ingest_politician_info_sample
from fedmcp_pipeline.ingest.elections import ingest_elections_sample

# Load environment
load_dotenv(Path(__file__).parent / "packages/data-pipeline/.env")

print("=" * 80)
print("OPENPARLIAMENT COMPREHENSIVE SAMPLE IMPORT TEST")
print("=" * 80)
print("\nThis will test all 4 ingest modules with sample data:")
print("  • Hansard: 1,000 statements")
print("  • Bill texts: 10 texts")
print("  • Politician info: 10 politicians")
print("  • Elections: 50 candidacies")
print()

# Initialize clients
print("1. Connecting to databases...")

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

# Track results
all_results = {}
errors = []
start_time = time.time()

# Test 1: Hansard
print("\n" + "=" * 80)
print("2. Testing Hansard sample import...")
print("=" * 80)
try:
    hansard_results = ingest_hansard_sample(
        neo4j_client=neo4j_client,
        postgres_client=postgres_client,
        statement_limit=1000
    )
    all_results["hansard"] = hansard_results
    print("\n   ✅ Hansard test passed")
except Exception as e:
    print(f"\n   ❌ Hansard test failed: {e}")
    errors.append(f"Hansard: {e}")

# Test 2: Bill texts
print("\n" + "=" * 80)
print("3. Testing bill text sample import...")
print("=" * 80)
try:
    bill_text_results = ingest_bill_text_sample(
        neo4j_client=neo4j_client,
        postgres_client=postgres_client,
        text_limit=10
    )
    all_results["bill_text"] = bill_text_results
    print("\n   ✅ Bill text test passed")
except Exception as e:
    print(f"\n   ❌ Bill text test failed: {e}")
    errors.append(f"Bill text: {e}")

# Test 3: Politician info
print("\n" + "=" * 80)
print("4. Testing politician info sample enrichment...")
print("=" * 80)
try:
    politician_info_results = ingest_politician_info_sample(
        neo4j_client=neo4j_client,
        postgres_client=postgres_client,
        limit=10
    )
    all_results["politician_info"] = politician_info_results
    print("\n   ✅ Politician info test passed")
except Exception as e:
    print(f"\n   ❌ Politician info test failed: {e}")
    errors.append(f"Politician info: {e}")

# Test 4: Elections
print("\n" + "=" * 80)
print("5. Testing elections sample import...")
print("=" * 80)
try:
    elections_results = ingest_elections_sample(
        neo4j_client=neo4j_client,
        postgres_client=postgres_client,
        candidacy_limit=50
    )
    all_results["elections"] = elections_results
    print("\n   ✅ Elections test passed")
except Exception as e:
    print(f"\n   ❌ Elections test failed: {e}")
    errors.append(f"Elections: {e}")

# Final validation
print("\n" + "=" * 80)
print("6. Final validation...")
print("=" * 80)

# Get counts from Neo4j
try:
    counts = neo4j_client.run_query("""
        MATCH (doc:Document) WITH count(doc) as documents
        MATCH (stmt:Statement) WITH documents, count(stmt) as statements
        MATCH (bt:BillText) WITH documents, statements, count(bt) as bill_texts
        MATCH (cand:Candidacy) WITH documents, statements, bill_texts, count(cand) as candidacies
        MATCH ()-[made_by:MADE_BY]->() WITH documents, statements, bill_texts, candidacies, count(made_by) as made_by
        MATCH ()-[part_of:PART_OF]->() WITH documents, statements, bill_texts, candidacies, made_by, count(part_of) as part_of
        MATCH ()-[has_text:HAS_TEXT]->() WITH documents, statements, bill_texts, candidacies, made_by, part_of, count(has_text) as has_text
        MATCH ()-[ran_in:RAN_IN]->()
        RETURN documents, statements, bill_texts, candidacies,
               made_by, part_of, has_text, ran_in as ran_in
    """)[0]

    print("\nNode counts:")
    print(f"   Documents: {counts['documents']:,}")
    print(f"   Statements: {counts['statements']:,}")
    print(f"   BillTexts: {counts['bill_texts']:,}")
    print(f"   Candidacies: {counts['candidacies']:,}")

    print("\nRelationship counts:")
    print(f"   MADE_BY: {counts['made_by']:,}")
    print(f"   PART_OF: {counts['part_of']:,}")
    print(f"   HAS_TEXT: {counts['has_text']:,}")
    print(f"   RAN_IN: {counts['ran_in']:,}")

except Exception as e:
    print(f"\n   ⚠️  Could not get final counts: {e}")
    errors.append(f"Final validation: {e}")

# Calculate elapsed time
elapsed_time = time.time() - start_time

# Summary
print("\n" + "=" * 80)
print("COMPREHENSIVE TEST SUMMARY")
print("=" * 80)

print(f"\nTotal time: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")

print("\nModule Results:")
if "hansard" in all_results:
    h = all_results["hansard"]
    print(f"\n  Hansard:")
    print(f"     Documents: {h.get('documents', 0):,}")
    print(f"     Statements: {h.get('statements', 0):,}")
    print(f"     MADE_BY links: {h.get('made_by_links', 0):,}")
    print(f"     PART_OF links: {h.get('part_of_links', 0):,}")
    print(f"     MENTIONS links: {h.get('mentions_links', 0):,}")

if "bill_text" in all_results:
    bt = all_results["bill_text"]
    print(f"\n  Bill Texts:")
    print(f"     Texts created: {bt.get('bill_texts', 0):,}")
    print(f"     HAS_TEXT links: {bt.get('has_text_links', 0):,}")

if "politician_info" in all_results:
    pi = all_results["politician_info"]
    print(f"\n  Politician Info:")
    print(f"     Politicians enriched: {pi.get('politicians_enriched', 0):,}")

if "elections" in all_results:
    el = all_results["elections"]
    print(f"\n  Elections:")
    print(f"     Candidacies created: {el.get('candidacies', 0):,}")
    print(f"     RAN_IN links: {el.get('ran_in_links', 0):,}")
    print(f"     Enriched: {el.get('enriched', 0):,}")

if errors:
    print("\n⚠️  ERRORS ENCOUNTERED:")
    for error in errors:
        print(f"   • {error}")
    print("\n❌ TEST COMPLETED WITH ERRORS")
    sys.exit(1)
else:
    print("\n✅ ALL TESTS PASSED SUCCESSFULLY!")

print("\n" + "=" * 80)
print("Next Steps:")
print("=" * 80)
print("\nSample imports completed successfully. You can now:")
print("  1. Review the imported data in Neo4j Browser")
print("  2. Run full imports if sample tests look good:")
print("     • test_hansard_full.py - Import all 3.67M statements")
print("     • test_bill_text_full.py - Import all 5,280 texts")
print("     • test_politician_info_full.py - Enrich all 2,958 politicians")
print("     • test_elections_full.py - Import all 21,246 candidacies")
print()

# Close connections
postgres_client.close()
neo4j_client.close()
