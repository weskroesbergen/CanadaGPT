"""Import a working dataset for frontend development.

This imports a meaningful subset of OpenParliament data:
- 25,000 recent Hansard statements
- 500 recent bill texts
- ALL politician info (only 2,958 records)
- 2,000 recent election candidacies

Should take 5-10 minutes vs hours for the full dataset.
"""

import sys
import time
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages/data-pipeline"))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.postgres_client import PostgresClient
from fedmcp_pipeline.ingest.hansard import ingest_hansard_sample
from fedmcp_pipeline.ingest.bill_text import ingest_bill_text_sample
from fedmcp_pipeline.ingest.politician_info import ingest_politician_info_full
from fedmcp_pipeline.ingest.elections import ingest_elections_sample


def main():
    print("=" * 80)
    print("OPENPARLIAMENT WORKING DATASET IMPORT")
    print("=" * 80)
    print()
    print("This will import a working dataset for frontend development:")
    print("  • Hansard: 25,000 recent statements")
    print("  • Bill texts: 500 texts")
    print("  • Politician info: ALL 2,958 politicians")
    print("  • Elections: 2,000 candidacies")
    print()
    print("Estimated time: 5-10 minutes")
    print("=" * 80)
    print()

    # Get confirmation
    response = input("Proceed with import? (y/n): ")
    if response.lower() != 'y':
        print("Import cancelled.")
        return

    start_time = time.time()

    # Connect to databases
    print("\n1. Connecting to databases...")
    try:
        postgres = PostgresClient(
            dbname="openparliament",
            user="fedmcp",
            password="",
            host="localhost",
            port=5432
        )
        print("   ✅ Connected to PostgreSQL")
    except Exception as e:
        print(f"   ❌ PostgreSQL connection failed: {e}")
        return

    try:
        neo4j = Neo4jClient(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="canadagpt2024"
        )
        print("   ✅ Connected to Neo4j")
    except Exception as e:
        print(f"   ❌ Neo4j connection failed: {e}")
        return

    results = {}

    # Import Hansard data (25,000 statements)
    print("\n" + "=" * 80)
    print("2. Importing Hansard data (25,000 statements)...")
    print("=" * 80)
    try:
        results["hansard"] = ingest_hansard_sample(
            neo4j,
            postgres,
            statement_limit=25000
        )
        print(f"\n   ✅ Hansard import complete")
        print(f"      Documents: {results['hansard']['documents']:,}")
        print(f"      Statements: {results['hansard']['statements']:,}")
        print(f"      PART_OF links: {results['hansard']['part_of_links']:,}")
    except Exception as e:
        print(f"\n   ❌ Hansard import failed: {e}")
        import traceback
        traceback.print_exc()

    # Import bill texts (500 texts)
    print("\n" + "=" * 80)
    print("3. Importing bill texts (500 texts)...")
    print("=" * 80)
    try:
        results["bill_texts"] = ingest_bill_text_sample(
            neo4j,
            postgres,
            text_limit=500
        )
        print(f"\n   ✅ Bill text import complete")
        print(f"      Texts: {results['bill_texts']['bill_texts']:,}")
        print(f"      HAS_TEXT links: {results['bill_texts']['has_text_links']:,}")
    except Exception as e:
        print(f"\n   ❌ Bill text import failed: {e}")
        import traceback
        traceback.print_exc()

    # Import ALL politician info (only 2,958 records)
    print("\n" + "=" * 80)
    print("4. Importing ALL politician info (2,958 politicians)...")
    print("=" * 80)
    try:
        results["politician_info"] = ingest_politician_info_full(
            neo4j,
            postgres
        )
        print(f"\n   ✅ Politician info import complete")
        print(f"      Politicians enriched: {results['politician_info']['politicians_enriched']:,}")
    except Exception as e:
        print(f"\n   ❌ Politician info import failed: {e}")
        import traceback
        traceback.print_exc()

    # Import elections (2,000 candidacies)
    print("\n" + "=" * 80)
    print("5. Importing election data (2,000 candidacies)...")
    print("=" * 80)
    try:
        results["elections"] = ingest_elections_sample(
            neo4j,
            postgres,
            candidacy_limit=2000
        )
        print(f"\n   ✅ Elections import complete")
        print(f"      Candidacies: {results['elections']['candidacies']:,}")
        print(f"      RAN_IN links: {results['elections']['ran_in_links']:,}")
        print(f"      Enriched: {results['elections']['enriched']:,}")
    except Exception as e:
        print(f"\n   ❌ Elections import failed: {e}")
        import traceback
        traceback.print_exc()

    # Summary
    elapsed = time.time() - start_time
    minutes = int(elapsed / 60)
    seconds = int(elapsed % 60)

    print("\n" + "=" * 80)
    print("WORKING DATASET IMPORT COMPLETE")
    print("=" * 80)
    print(f"\nTotal time: {minutes}m {seconds}s")
    print("\nImported:")

    if "hansard" in results:
        print(f"  • Hansard: {results['hansard']['statements']:,} statements")

    if "bill_texts" in results:
        print(f"  • Bill texts: {results['bill_texts']['bill_texts']:,} texts")

    if "politician_info" in results:
        print(f"  • Politician info: {results['politician_info']['politicians_enriched']:,} politicians")

    if "elections" in results:
        print(f"  • Elections: {results['elections']['candidacies']:,} candidacies")

    print("\n✅ You can now develop and test the frontend with this dataset!")
    print("   Run the full import later when you're ready for production data.")

    # Close connections
    postgres.close()
    neo4j.close()


if __name__ == "__main__":
    main()
