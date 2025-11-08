#!/usr/bin/env python3
"""
Map OpenParliament politician IDs to Neo4j MP nodes.

This script:
1. Queries all MPs from Neo4j (id and slug)
2. Queries all politicians from PostgreSQL (id and slug)
3. Matches by slug and adds openparliament_politician_id property to MP nodes
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

def get_postgres_politicians(pg_client):
    """Fetch all politicians with slugs from PostgreSQL."""
    query = """
        SELECT id, name, slug
        FROM core_politician
        WHERE slug IS NOT NULL AND slug <> ''
        ORDER BY slug
    """

    results = pg_client.execute_query(query, dict_cursor=True)
    politicians = {}
    duplicates = []

    for row in results:
        politician_id = row['id']
        name = row['name']
        slug = row['slug']

        if slug in politicians:
            duplicates.append({
                'slug': slug,
                'existing': politicians[slug],
                'new': {'id': politician_id, 'name': name}
            })
            # Keep the one with most recent ID (higher ID = more recent)
            if politician_id > politicians[slug]['id']:
                politicians[slug] = {'id': politician_id, 'name': name, 'slug': slug}
        else:
            politicians[slug] = {'id': politician_id, 'name': name, 'slug': slug}

    return politicians, duplicates


def get_neo4j_mps(neo4j_client):
    """Fetch all MPs from Neo4j."""
    query = """
        MATCH (mp:MP)
        RETURN mp.id AS id, mp.name AS name, mp.slug AS slug
        ORDER BY mp.slug
    """

    results = neo4j_client.run_query(query)
    mps = {}

    for record in results:
        mp_id = record['id']
        name = record['name']
        slug = record['slug']

        if slug:
            mps[slug] = {'id': mp_id, 'name': name, 'slug': slug}

    return mps


def map_and_update_mps(neo4j_client, mps, politicians):
    """
    Map Neo4j MPs to PostgreSQL politicians and update with openparliament_politician_id.

    Returns:
        dict: Statistics on mapping results
    """
    matched = []
    unmatched = []

    for slug, mp_data in mps.items():
        if slug in politicians:
            politician = politicians[slug]
            matched.append({
                'mp_id': mp_data['id'],
                'mp_name': mp_data['name'],
                'politician_id': politician['id'],
                'politician_name': politician['name'],
                'slug': slug
            })
        else:
            unmatched.append({
                'mp_id': mp_data['id'],
                'mp_name': mp_data['name'],
                'slug': slug
            })

    # Update Neo4j MPs with OpenParliament politician IDs
    if matched:
        update_query = """
            UNWIND $mappings AS mapping
            MATCH (mp:MP {id: mapping.mp_id})
            SET mp.openparliament_politician_id = mapping.politician_id
            RETURN mp.id AS id, mp.name AS name, mp.openparliament_politician_id AS politician_id
        """

        mappings = [
            {'mp_id': m['mp_id'], 'politician_id': m['politician_id']}
            for m in matched
        ]

        neo4j_client.run_query(update_query, {'mappings': mappings})

    stats = {
        'total_mps': len(mps),
        'total_politicians': len(politicians),
        'matched': len(matched),
        'unmatched': len(unmatched),
        'match_rate': (len(matched) / len(mps) * 100) if mps else 0
    }

    return stats, matched, unmatched


def main():
    """Main execution function."""
    print("=" * 80)
    print("OPENPARLIAMENT POLITICIAN ID MAPPING")
    print("=" * 80)
    print()

    # Load configuration
    config = Config(env_file=env_file)

    # PostgreSQL connection parameters
    # Default to local OpenParliament database
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

        # Fetch politicians from PostgreSQL
        print("2. Fetching politicians from OpenParliament PostgreSQL...")
        politicians, duplicates = get_postgres_politicians(pg_client)
        print(f"   ✅ Found {len(politicians)} politicians with slugs")

        if duplicates:
            print(f"   ⚠️  Found {len(duplicates)} duplicate slugs (using most recent ID)")
            for dup in duplicates[:5]:  # Show first 5
                print(f"      - {dup['slug']}: ID {dup['existing']['id']} vs {dup['new']['id']}")
        print()

        # Fetch MPs from Neo4j
        print("3. Fetching MPs from Neo4j...")
        mps = get_neo4j_mps(neo4j_client)
        print(f"   ✅ Found {len(mps)} MPs with slugs")
        print()

        # Map and update
        print("4. Mapping MPs to politicians and updating Neo4j...")
        stats, matched, unmatched = map_and_update_mps(neo4j_client, mps, politicians)
        print(f"   ✅ Updated {stats['matched']} MPs with openparliament_politician_id")
        print()

        # Print statistics
        print("=" * 80)
        print("MAPPING STATISTICS")
        print("=" * 80)
        print(f"Total MPs in Neo4j:           {stats['total_mps']}")
        print(f"Total Politicians in PG:      {stats['total_politicians']}")
        print(f"Successfully Matched:         {stats['matched']}")
        print(f"Unmatched:                    {stats['unmatched']}")
        print(f"Match Rate:                   {stats['match_rate']:.1f}%")
        print()

        # Show sample matches
        if matched:
            print("Sample Matched MPs:")
            print("-" * 80)
            for match in matched[:10]:
                print(f"  MP: {match['mp_name']:30} → Politician ID: {match['politician_id']:6} ({match['politician_name']})")
            if len(matched) > 10:
                print(f"  ... and {len(matched) - 10} more")
            print()

        # Show unmatched
        if unmatched:
            print(f"⚠️  Unmatched MPs ({len(unmatched)}):")
            print("-" * 80)
            for um in unmatched[:20]:
                print(f"  {um['mp_name']:30} (slug: {um['slug']})")
            if len(unmatched) > 20:
                print(f"  ... and {len(unmatched) - 20} more")
            print()

        print("=" * 80)
        print("✅ MAPPING COMPLETE")
        print("=" * 80)

        # Verify a few high-profile MPs
        print()
        print("Verification - High-Profile MPs:")
        print("-" * 80)
        verify_query = """
            MATCH (mp:MP)
            WHERE mp.name IN ['Pierre Poilievre', 'Justin Trudeau', 'Jagmeet Singh', 'Mark Holland']
            RETURN mp.name AS name, mp.id AS mp_id, mp.openparliament_politician_id AS politician_id
            ORDER BY mp.name
        """
        results = neo4j_client.run_query(verify_query)
        for record in results:
            print(f"  {record['name']:25} → OpenParliament ID: {record['politician_id']}")

    finally:
        pg_client.close()
        neo4j_client.close()
        print()


if __name__ == "__main__":
    main()
