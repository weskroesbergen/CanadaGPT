"""
Import individual MP votes from OpenParliament to Neo4j.

This script creates (MP)-[:CAST_VOTE]->(Vote) relationships with vote position.
Handles 1.46M individual vote records with batching and progress tracking.
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path.home() / "FedMCP/packages/data-pipeline"))

from fedmcp_pipeline.utils.postgres_client import PostgresClient
from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
import os
from dotenv import load_dotenv

load_dotenv(Path.home() / "FedMCP/packages/data-pipeline/.env")

# Configuration
BATCH_SIZE = 10000
LIMIT = None  # Set to number for testing, None for all records

def main():
    print("=" * 80)
    print("IMPORTING INDIVIDUAL MP VOTES FROM OPENPARLIAMENT")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Connect to databases
    pg = PostgresClient(
        dbname="openparliament",
        user="fedmcp",
        password="fedmcp2024",
        host="localhost",
        port=5432
    )

    neo4j = Neo4jClient(
        uri=os.getenv("NEO4J_URI"),
        user=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD")
    )

    try:
        # Step 1: Get total count
        print("\n1. Counting vote records...")
        count_query = "SELECT COUNT(*) as total FROM bills_membervote"
        total_votes = pg.execute_query(count_query)[0]['total']
        print(f"   Total individual votes to import: {total_votes:,}")

        if LIMIT:
            print(f"   LIMIT set to {LIMIT:,} for testing")
            total_votes = min(total_votes, LIMIT)

        # Step 2: Create mapping of PostgreSQL Vote IDs in Neo4j
        print("\n2. Building PostgreSQL Vote ID mapping from Neo4j...")
        neo4j_votes = neo4j.run_query("""
            MATCH (v:Vote)
            WHERE v.pg_vote_id IS NOT NULL
            RETURN v.pg_vote_id as pg_vote_id
        """)
        valid_vote_ids = {v['pg_vote_id'] for v in neo4j_votes}
        print(f"   Found {len(valid_vote_ids):,} Vote nodes with PostgreSQL IDs")

        # Step 3: Create slug-to-name mapping for MPs
        print("\n3. Building MP slug mapping from Neo4j...")
        neo4j_mps = neo4j.run_query("""
            MATCH (mp:MP)
            WHERE mp.slug IS NOT NULL
            RETURN mp.slug as slug, mp.name as name
        """)
        slug_to_name = {mp['slug']: mp['name'] for mp in neo4j_mps}
        print(f"   Found {len(slug_to_name):,} MPs with slugs")

        # Step 4: Fetch and process votes in batches
        print(f"\n4. Processing votes in batches of {BATCH_SIZE:,}...")

        # Query to get votes with politician and vote question details
        query = f"""
        SELECT
            mv.id,
            mv.vote,
            mv.dissent,
            pol.slug as politician_slug,
            vq.id as vote_question_id
        FROM bills_membervote mv
        JOIN core_politician pol ON mv.politician_id = pol.id
        JOIN bills_votequestion vq ON mv.votequestion_id = vq.id
        WHERE pol.slug IS NOT NULL
        ORDER BY mv.id
        {"LIMIT " + str(LIMIT) if LIMIT else ""}
        """

        votes = pg.execute_query(query)
        print(f"   Fetched {len(votes):,} vote records from PostgreSQL")

        # Step 5: Filter and batch import
        print("\n5. Creating CAST_VOTE relationships...")

        relationships = []
        matched = 0
        missing_mp = 0
        missing_vote = 0

        for vote in votes:
            vote_question_id = vote['vote_question_id']
            politician_slug = vote['politician_slug']

            # Check if Vote exists in Neo4j
            if vote_question_id not in valid_vote_ids:
                missing_vote += 1
                continue

            # Check if MP exists in Neo4j
            if politician_slug not in slug_to_name:
                missing_mp += 1
                continue

            mp_name = slug_to_name[politician_slug]

            relationships.append({
                "from_id": mp_name,  # MP.name
                "to_id": vote_question_id,  # Vote.pg_vote_id
                "properties": {
                    "position": vote['vote'],  # Y, N, or P (paired)
                    "dissent": vote['dissent']  # Whether voted against party line
                }
            })
            matched += 1

        print(f"   Matched votes: {matched:,}")
        print(f"   Skipped (missing MP): {missing_mp:,}")
        print(f"   Skipped (missing Vote): {missing_vote:,}")

        # Import in batches
        if relationships:
            print(f"\n6. Importing {len(relationships):,} relationships in batches...")
            created = neo4j.batch_create_relationships(
                rel_type="CAST_VOTE",
                relationships=relationships,
                from_label="MP",
                to_label="Vote",
                from_key="name",  # Match MPs by name
                to_key="pg_vote_id",  # Match Votes by PostgreSQL ID
                batch_size=BATCH_SIZE
            )
            print(f"   Created {created:,} CAST_VOTE relationships")
        else:
            print("\n6. No relationships to import!")

        # Step 7: Verify results
        print("\n7. Verification...")
        stats = neo4j.run_query("""
            MATCH (mp:MP)-[r:CAST_VOTE]->(v:Vote)
            RETURN
                count(r) as total_votes,
                count(DISTINCT mp) as mps_with_votes,
                count(DISTINCT v) as votes_with_mps
        """)

        if stats:
            print(f"   Total CAST_VOTE relationships: {stats[0]['total_votes']:,}")
            print(f"   MPs with votes: {stats[0]['mps_with_votes']:,}")
            print(f"   Votes with MP votes: {stats[0]['votes_with_mps']:,}")

        # Sample query
        print("\n8. Sample data:")
        sample = neo4j.run_query("""
            MATCH (mp:MP)-[r:CAST_VOTE]->(v:Vote)
            RETURN
                mp.name as mp_name,
                r.position as position,
                r.dissent as dissent,
                v.date as vote_date,
                v.description as description
            LIMIT 3
        """)

        for s in sample:
            print(f"\n   {s['mp_name']} voted {s['position']} on {s['vote_date']}")
            print(f"   Dissent: {s['dissent']}")
            desc = s.get('description') or 'No description'
            print(f"   Description: {desc[:80]}...")

    finally:
        pg.close()
        neo4j.close()

    print("\n" + "=" * 80)
    print(f"✅ IMPORT COMPLETE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

if __name__ == "__main__":
    main()
