#!/usr/bin/env python3
"""
Test Hansard relationship creation for existing statements.

This script tests the link_statements_to_mps() and link_statements_to_bills()
functions on the existing 25K statements in Neo4j.
"""

from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "packages" / "data-pipeline"))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.config import Config
from fedmcp_pipeline.ingest.hansard import (
    link_statements_to_mps,
    link_statements_to_bills,
)


def check_current_state(neo4j_client):
    """Check current state of statements and relationships."""
    print("=" * 80)
    print("CURRENT STATE")
    print("=" * 80)

    # Count statements
    result = neo4j_client.run_query("MATCH (s:Statement) RETURN count(s) as count")
    statement_count = result[0]["count"] if result else 0
    print(f"Total Statements:             {statement_count:,}")

    # Count statements with politician_id
    result = neo4j_client.run_query(
        "MATCH (s:Statement) WHERE s.politician_id IS NOT NULL RETURN count(s) as count"
    )
    with_politician_id = result[0]["count"] if result else 0
    print(f"Statements with politician_id: {with_politician_id:,}")

    # Count statements with bill_debated_id
    result = neo4j_client.run_query(
        "MATCH (s:Statement) WHERE s.bill_debated_id IS NOT NULL RETURN count(s) as count"
    )
    with_bill_id = result[0]["count"] if result else 0
    print(f"Statements with bill_debated_id: {with_bill_id:,}")

    # Count existing MADE_BY relationships
    result = neo4j_client.run_query(
        "MATCH ()-[r:MADE_BY]->() RETURN count(r) as count"
    )
    made_by_count = result[0]["count"] if result else 0
    print(f"Existing MADE_BY relationships: {made_by_count:,}")

    # Count existing MENTIONS relationships
    result = neo4j_client.run_query(
        "MATCH ()-[r:MENTIONS]->() RETURN count(r) as count"
    )
    mentions_count = result[0]["count"] if result else 0
    print(f"Existing MENTIONS relationships: {mentions_count:,}")

    # Count MPs with openparliament_politician_id
    result = neo4j_client.run_query(
        "MATCH (mp:MP) WHERE mp.openparliament_politician_id IS NOT NULL RETURN count(mp) as count"
    )
    mps_with_id = result[0]["count"] if result else 0
    print(f"MPs with openparliament_politician_id: {mps_with_id:,}")

    # Count Bills with openparliament_bill_id
    result = neo4j_client.run_query(
        "MATCH (b:Bill) WHERE b.openparliament_bill_id IS NOT NULL RETURN count(b) as count"
    )
    bills_with_id = result[0]["count"] if result else 0
    print(f"Bills with openparliament_bill_id: {bills_with_id:,}")

    print()
    return {
        "statements": statement_count,
        "with_politician_id": with_politician_id,
        "with_bill_id": with_bill_id,
        "made_by": made_by_count,
        "mentions": mentions_count,
        "mps_mapped": mps_with_id,
        "bills_mapped": bills_with_id,
    }


def main():
    """Main execution function."""
    print("=" * 80)
    print("HANSARD RELATIONSHIP CREATION TEST")
    print("=" * 80)
    print()

    # Load configuration
    env_file = Path(__file__).parent / "packages" / "data-pipeline" / ".env"
    config = Config(env_file=env_file)

    # Connect to Neo4j
    print("1. Connecting to Neo4j...")
    neo4j_client = Neo4jClient(
        uri=config.neo4j_uri,
        user=config.neo4j_user,
        password=config.neo4j_password
    )

    try:
        print("   ✅ Connected to Neo4j")
        print()

        # Check current state
        print("2. Checking current state...")
        initial_state = check_current_state(neo4j_client)

        # Create MADE_BY relationships
        print("3. Creating MADE_BY relationships (Statement → MP)...")
        print("-" * 80)
        made_by_created = link_statements_to_mps(neo4j_client, batch_size=5000)
        print(f"✅ Created {made_by_created:,} MADE_BY relationships")
        print()

        # Create MENTIONS relationships
        print("4. Creating MENTIONS relationships (Statement → Bill)...")
        print("-" * 80)
        mentions_created = link_statements_to_bills(neo4j_client, batch_size=5000)
        print(f"✅ Created {mentions_created:,} MENTIONS relationships")
        print()

        # Check final state
        print("5. Checking final state...")
        final_state = check_current_state(neo4j_client)

        # Print summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"MADE_BY relationships:   {initial_state['made_by']:,} → {final_state['made_by']:,} (+{made_by_created:,})")
        print(f"MENTIONS relationships:  {initial_state['mentions']:,} → {final_state['mentions']:,} (+{mentions_created:,})")
        print()

        # Calculate coverage
        if final_state['with_politician_id'] > 0:
            mp_coverage = (final_state['made_by'] / final_state['with_politician_id']) * 100
            print(f"MP Coverage:    {mp_coverage:.1f}% ({final_state['made_by']:,} / {final_state['with_politician_id']:,} statements)")

        if final_state['with_bill_id'] > 0:
            bill_coverage = (final_state['mentions'] / final_state['with_bill_id']) * 100
            print(f"Bill Coverage:  {bill_coverage:.1f}% ({final_state['mentions']:,} / {final_state['with_bill_id']:,} statements)")

        print()

        # Sample queries to verify
        print("=" * 80)
        print("VERIFICATION QUERIES")
        print("=" * 80)

        # Get a sample MP's recent speeches
        print("\nSample: Pierre Poilievre's recent speeches:")
        print("-" * 80)
        query = """
            MATCH (mp:MP {name: 'Pierre Poilievre'})<-[:MADE_BY]-(s:Statement)
            RETURN s.time as time, s.h2_en as context, s.wordcount as words
            ORDER BY s.time DESC
            LIMIT 5
        """
        results = neo4j_client.run_query(query)
        if results:
            for r in results:
                time = str(r['time'])[:19] if r['time'] else 'No time'
                context = r['context'][:50] if r['context'] else 'No context'
                words = r['words'] or 0
                print(f"  {time} | {context:50} | {words:4} words")
        else:
            print("  No speeches found")

        # Get a sample bill's debates
        print("\nSample: Bill C-12 (45-1) debate statements:")
        print("-" * 80)
        query = """
            MATCH (b:Bill {number: 'C-12', session: '45-1'})<-[r:MENTIONS]-(s:Statement)
            RETURN s.time as time, r.debate_stage as stage, s.wordcount as words
            ORDER BY s.time
            LIMIT 5
        """
        results = neo4j_client.run_query(query)
        if results:
            for r in results:
                time = str(r['time'])[:19] if r['time'] else 'No time'
                stage = r['stage'] or 'Unknown'
                words = r['words'] or 0
                print(f"  {time} | Reading {stage:2} | {words:4} words")
        else:
            print("  No debates found")

        print()
        print("=" * 80)
        print("✅ RELATIONSHIP CREATION TEST COMPLETE")
        print("=" * 80)

    finally:
        neo4j_client.close()


if __name__ == "__main__":
    main()
