#!/usr/bin/env python3
"""
Map OpenParliament bill IDs to Neo4j Bill nodes.

This script:
1. Queries all Bills from Neo4j (number and session)
2. Queries all bills from PostgreSQL (id, number_only, session_id)
3. Matches by number and session, adds openparliament_bill_id property to Bill nodes
4. Reports statistics on matching success
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent / "packages" / "data-pipeline"))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.postgres_client import PostgresClient
from fedmcp_pipeline.utils.config import Config

# Load environment variables
env_file = Path(__file__).parent / "packages" / "data-pipeline" / ".env"
load_dotenv(env_file)


def normalize_bill_number(number: str) -> str:
    """
    Normalize bill number for comparison.
    Examples: "C-1" -> "c-1", "S-201" -> "s-201"
    """
    return number.lower().strip()


def get_postgres_bills(pg_client):
    """Fetch all bills from PostgreSQL."""
    query = """
        SELECT id, number_only, session_id, name_en
        FROM bills_bill
        WHERE number_only IS NOT NULL AND session_id IS NOT NULL
        ORDER BY session_id DESC, number_only
    """

    results = pg_client.execute_query(query, dict_cursor=True)
    bills = {}

    for row in results:
        bill_id = row['id']
        number_only = row['number_only']
        session_id = row['session_id']
        name = row['name_en']

        # Bills can be C (Commons) or S (Senate)
        # PostgreSQL stores just the number, we need to infer the prefix
        # For now, create keys with both possible prefixes
        for prefix in ['c', 's']:
            bill_number = f"{prefix}-{number_only}"
            key = (session_id, bill_number)

            # Keep track of all possible matches
            if key not in bills:
                bills[key] = []

            bills[key].append({
                'id': bill_id,
                'number_only': number_only,
                'session': session_id,
                'name': name
            })

    return bills


def get_neo4j_bills(neo4j_client):
    """Fetch all Bills from Neo4j."""
    query = """
        MATCH (b:Bill)
        WHERE b.number IS NOT NULL AND b.session IS NOT NULL
        RETURN b.number AS number, b.session AS session, b.title AS title
        ORDER BY b.session, b.number
    """

    results = neo4j_client.run_query(query)
    bills = {}

    for record in results:
        number = normalize_bill_number(record['number'])
        session = record['session']
        title = record['title']

        key = (session, number)
        bills[key] = {
            'number': number,
            'session': session,
            'title': title
        }

    return bills


def map_and_update_bills(neo4j_client, neo4j_bills, pg_bills):
    """
    Map Neo4j Bills to PostgreSQL bills and update with openparliament_bill_id.

    Returns:
        dict: Statistics on mapping results
    """
    matched = []
    unmatched = []
    ambiguous = []

    for (session, number), neo4j_bill in neo4j_bills.items():
        key = (session, number)

        if key in pg_bills:
            candidates = pg_bills[key]

            if len(candidates) == 1:
                # Exact match
                pg_bill = candidates[0]
                matched.append({
                    'session': session,
                    'number': number,
                    'neo4j_title': neo4j_bill['title'],
                    'pg_bill_id': pg_bill['id'],
                    'pg_name': pg_bill['name']
                })
            else:
                # Multiple matches (ambiguous)
                ambiguous.append({
                    'session': session,
                    'number': number,
                    'candidates': candidates
                })
                # Use the first candidate for now
                matched.append({
                    'session': session,
                    'number': number,
                    'neo4j_title': neo4j_bill['title'],
                    'pg_bill_id': candidates[0]['id'],
                    'pg_name': candidates[0]['name']
                })
        else:
            unmatched.append({
                'session': session,
                'number': number,
                'title': neo4j_bill['title']
            })

    # Update Neo4j Bills with OpenParliament bill IDs
    if matched:
        update_query = """
            UNWIND $mappings AS mapping
            MATCH (b:Bill {number: mapping.number, session: mapping.session})
            SET b.openparliament_bill_id = mapping.pg_bill_id
            RETURN b.number AS number, b.session AS session, b.openparliament_bill_id AS bill_id
        """

        mappings = [
            {
                'number': m['number'].upper(),  # Convert back to uppercase for Neo4j
                'session': m['session'],
                'pg_bill_id': m['pg_bill_id']
            }
            for m in matched
        ]

        neo4j_client.run_query(update_query, {'mappings': mappings})

    stats = {
        'total_neo4j_bills': len(neo4j_bills),
        'total_pg_bill_keys': len(pg_bills),
        'matched': len(matched),
        'unmatched': len(unmatched),
        'ambiguous': len(ambiguous),
        'match_rate': (len(matched) / len(neo4j_bills) * 100) if neo4j_bills else 0
    }

    return stats, matched, unmatched, ambiguous


def main():
    """Main execution function."""
    print("=" * 80)
    print("OPENPARLIAMENT BILL ID MAPPING")
    print("=" * 80)
    print()

    # Load configuration
    config = Config(env_file=env_file)

    # PostgreSQL connection parameters
    pg_host = os.getenv("POSTGRES_HOST", "localhost")
    pg_port = int(os.getenv("POSTGRES_PORT", "5432"))
    pg_db = os.getenv("POSTGRES_DB", "openparliament")
    pg_user = os.getenv("POSTGRES_USER", "fedmcp")
    pg_password = os.getenv("POSTGRES_PASSWORD", "fedmcp2024")

    # Connect to databases
    print("1. Connecting to databases...")

    pg_client = PostgresClient(
        dbname=pg_db,
        user=pg_user,
        password=pg_password,
        host=pg_host,
        port=pg_port
    )

    neo4j_client = Neo4jClient(
        uri=config.neo4j_uri,
        user=config.neo4j_user,
        password=config.neo4j_password
    )

    try:
        print("   ✅ Connected to PostgreSQL")
        print("   ✅ Connected to Neo4j")
        print()

        # Fetch bills from PostgreSQL
        print("2. Fetching bills from OpenParliament PostgreSQL...")
        pg_bills = get_postgres_bills(pg_client)
        print(f"   ✅ Found {len(pg_bills)} bill keys (session, number) combinations")
        print()

        # Fetch Bills from Neo4j
        print("3. Fetching Bills from Neo4j...")
        neo4j_bills = get_neo4j_bills(neo4j_client)
        print(f"   ✅ Found {len(neo4j_bills)} Bills")
        print()

        # Map and update
        print("4. Mapping Bills to PostgreSQL bills and updating Neo4j...")
        stats, matched, unmatched, ambiguous = map_and_update_bills(neo4j_client, neo4j_bills, pg_bills)
        print(f"   ✅ Updated {stats['matched']} Bills with openparliament_bill_id")
        print()

        # Print statistics
        print("=" * 80)
        print("MAPPING STATISTICS")
        print("=" * 80)
        print(f"Total Bills in Neo4j:         {stats['total_neo4j_bills']}")
        print(f"Total Bill Keys in PG:        {stats['total_pg_bill_keys']}")
        print(f"Successfully Matched:         {stats['matched']}")
        print(f"Unmatched:                    {stats['unmatched']}")
        print(f"Ambiguous (multiple matches): {stats['ambiguous']}")
        print(f"Match Rate:                   {stats['match_rate']:.1f}%")
        print()

        # Show sample matches
        if matched:
            print("Sample Matched Bills:")
            print("-" * 80)
            for match in matched[:10]:
                print(f"  {match['session']:6} {match['number']:8} → PostgreSQL ID: {match['pg_bill_id']:6}")
                if match['neo4j_title'] and len(match['neo4j_title']) > 60:
                    print(f"    {match['neo4j_title'][:60]}...")
                elif match['neo4j_title']:
                    print(f"    {match['neo4j_title']}")
            if len(matched) > 10:
                print(f"  ... and {len(matched) - 10} more")
            print()

        # Show unmatched
        if unmatched:
            print(f"⚠️  Unmatched Bills ({len(unmatched)}):")
            print("-" * 80)
            for um in unmatched[:20]:
                print(f"  {um['session']:6} {um['number']:8} - {um['title'][:60] if um['title'] else 'No title'}...")
            if len(unmatched) > 20:
                print(f"  ... and {len(unmatched) - 20} more")
            print()

        # Show ambiguous
        if ambiguous:
            print(f"⚠️  Ambiguous Matches ({len(ambiguous)}):")
            print("-" * 80)
            for amb in ambiguous[:10]:
                print(f"  {amb['session']:6} {amb['number']:8} - {len(amb['candidates'])} candidates in PostgreSQL")
            print()

        print("=" * 80)
        print("✅ MAPPING COMPLETE")
        print("=" * 80)

        # Verify a few well-known bills
        print()
        print("Verification - Sample Bills:")
        print("-" * 80)
        verify_query = """
            MATCH (b:Bill)
            WHERE b.session = '45-1' AND b.number IN ['C-1', 'C-2', 'C-3', 'C-12']
            RETURN b.number AS number, b.session AS session, b.openparliament_bill_id AS bill_id
            ORDER BY b.number
        """
        results = neo4j_client.run_query(verify_query)
        for record in results:
            print(f"  {record['session']} {record['number']:8} → OpenParliament ID: {record['bill_id']}")

    finally:
        pg_client.close()
        neo4j_client.close()
        print()


if __name__ == "__main__":
    main()
