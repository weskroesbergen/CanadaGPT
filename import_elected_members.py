"""
Import ElectedMember (historical parliamentary terms) from OpenParliament to Neo4j.

This script creates Term nodes representing each period an MP served in Parliament,
with relationships showing which riding they represented and which party they belonged to.

Model:
  (MP)-[:SERVED_TERM]->(Term)-[:REPRESENTS]->(Riding)
                       (Term)-[:MEMBER_OF]->(Party)
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
BATCH_SIZE = 500
LIMIT = None  # Set to number for testing, None for all records

def main():
    print("=" * 80)
    print("IMPORTING ELECTED MEMBER TERMS FROM OPENPARLIAMENT")
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
        print("\n1. Counting ElectedMember records...")
        count_query = "SELECT COUNT(*) as total FROM core_electedmember"
        total_terms = pg.execute_query(count_query)[0]['total']
        print(f"   Total terms to import: {total_terms:,}")

        if LIMIT:
            print(f"   LIMIT set to {LIMIT:,} for testing")
            total_terms = min(total_terms, LIMIT)

        # Step 2: Create MP slug mapping (skip empty/null slugs)
        print("\n2. Building MP slug mapping from Neo4j...")
        neo4j_mps = neo4j.run_query("""
            MATCH (mp:MP)
            WHERE mp.slug IS NOT NULL AND mp.slug <> ''
            RETURN mp.slug as slug, mp.name as name
        """)
        slug_to_name = {mp['slug']: mp['name'] for mp in neo4j_mps if mp['slug'] and mp['slug'].strip()}
        print(f"   Found {len(slug_to_name):,} MPs with valid slugs")

        # Step 3: Fetch and process terms
        print(f"\n3. Fetching ElectedMember data with joins...")

        query = f"""
        SELECT
            em.id as term_id,
            em.start_date,
            em.end_date,
            p.slug as politician_slug,
            p.name as politician_name,
            r.name_en as riding_name,
            r.slug as riding_slug,
            r.province,
            party.short_name_en as party_name,
            party.name_en as party_full_name
        FROM core_electedmember em
        JOIN core_politician p ON em.politician_id = p.id
        JOIN core_riding r ON em.riding_id = r.id
        JOIN core_party party ON em.party_id = party.id
        WHERE p.slug IS NOT NULL AND p.slug <> ''
        ORDER BY em.start_date DESC
        {f"LIMIT {LIMIT}" if LIMIT else ""}
        """

        terms = pg.execute_query(query)
        print(f"   Fetched {len(terms):,} term records from PostgreSQL")

        # Step 4: Create Term nodes and relationships
        print("\n4. Creating Term nodes and relationships...")

        matched_mps = 0
        missing_mps = 0
        terms_created = 0

        for i in range(0, len(terms), BATCH_SIZE):
            batch = terms[i:i + BATCH_SIZE]

            # Prepare Term nodes
            term_nodes = []
            mp_term_rels = []
            riding_rels = []
            party_rels = []

            for term in batch:
                politician_slug = term['politician_slug']

                # Check if MP exists in Neo4j
                if politician_slug not in slug_to_name:
                    missing_mps += 1
                    continue

                mp_name = slug_to_name[politician_slug]
                matched_mps += 1

                # Create Term node data
                term_node = {
                    "term_id": term['term_id'],
                    "start_date": term['start_date'].isoformat() if term['start_date'] else None,
                    "end_date": term['end_date'].isoformat() if term['end_date'] else None,
                    "riding_name": term['riding_name'],
                    "riding_province": term['province'],
                    "party_name": term['party_name']
                }
                term_nodes.append(term_node)

                # MP-[:SERVED_TERM]->Term relationship
                mp_term_rels.append({
                    "from_id": mp_name,
                    "to_id": term['term_id'],
                    "properties": {}
                })

                # Term-[:REPRESENTS]->Riding relationship
                riding_rels.append({
                    "from_id": term['term_id'],
                    "to_id": term['riding_name'],
                    "properties": {
                        "province": term['province']
                    }
                })

                # Term-[:MEMBER_OF]->Party relationship
                party_rels.append({
                    "from_id": term['term_id'],
                    "to_id": term['party_name'],
                    "properties": {}
                })

            # Create Term nodes
            if term_nodes:
                for term_node in term_nodes:
                    neo4j.run_query("""
                        MERGE (t:Term {term_id: $term_id})
                        SET t.start_date = $start_date,
                            t.end_date = $end_date,
                            t.riding_name = $riding_name,
                            t.riding_province = $riding_province,
                            t.party_name = $party_name
                    """, term_node)
                    terms_created += 1

                # Create MP->Term relationships
                created = neo4j.batch_create_relationships(
                    rel_type="SERVED_TERM",
                    relationships=mp_term_rels,
                    from_label="MP",
                    to_label="Term",
                    from_key="name",
                    to_key="term_id",
                    batch_size=BATCH_SIZE
                )

                # Create Riding nodes if they don't exist and link them
                ridings = list(set(term['riding_name'] for term in batch))
                for riding in ridings:
                    neo4j.run_query("""
                        MERGE (r:Riding {name: $name})
                    """, {"name": riding})

                # Create Term->Riding relationships
                neo4j.batch_create_relationships(
                    rel_type="REPRESENTS",
                    relationships=riding_rels,
                    from_label="Term",
                    to_label="Riding",
                    from_key="term_id",
                    to_key="name",
                    batch_size=BATCH_SIZE
                )

                # Create Party nodes if they don't exist and link them
                parties = list(set(term['party_name'] for term in batch if term['party_name']))
                for party in parties:
                    neo4j.run_query("""
                        MERGE (p:Party {name: $name})
                    """, {"name": party})

                # Create Term->Party relationships
                neo4j.batch_create_relationships(
                    rel_type="MEMBER_OF",
                    relationships=party_rels,
                    from_label="Term",
                    to_label="Party",
                    from_key="term_id",
                    to_key="name",
                    batch_size=BATCH_SIZE
                )

            print(f"   Progress: {min(i + BATCH_SIZE, len(terms)):,}/{len(terms):,} terms processed")

        print(f"\n   Matched MPs: {matched_mps:,}")
        print(f"   Skipped (missing MP): {missing_mps:,}")
        print(f"   Terms created: {terms_created:,}")

        # Step 5: Verify results
        print("\n5. Verification...")
        stats = neo4j.run_query("""
            MATCH (t:Term)
            OPTIONAL MATCH (mp:MP)-[:SERVED_TERM]->(t)
            OPTIONAL MATCH (t)-[:REPRESENTS]->(r:Riding)
            OPTIONAL MATCH (t)-[:MEMBER_OF]->(p:Party)
            RETURN
                count(t) as total_terms,
                count(DISTINCT mp) as mps_with_terms,
                count(DISTINCT r) as ridings,
                count(DISTINCT p) as parties
        """)

        if stats:
            print(f"   Total Term nodes: {stats[0]['total_terms']:,}")
            print(f"   MPs with terms: {stats[0]['mps_with_terms']:,}")
            print(f"   Unique ridings: {stats[0]['ridings']:,}")
            print(f"   Unique parties: {stats[0]['parties']:,}")

        # Step 6: Sample data
        print("\n6. Sample terms:")
        sample = neo4j.run_query("""
            MATCH (mp:MP)-[:SERVED_TERM]->(t:Term)-[:REPRESENTS]->(r:Riding)
            OPTIONAL MATCH (t)-[:MEMBER_OF]->(p:Party)
            RETURN
                mp.name as mp_name,
                t.start_date as start_date,
                t.end_date as end_date,
                r.name as riding,
                p.name as party
            ORDER BY t.start_date DESC
            LIMIT 5
        """)

        for s in sample:
            end = s['end_date'] or 'present'
            print(f"\n   {s['mp_name']} ({s['party']})")
            print(f"   {s['riding']}: {s['start_date']} to {end}")

        # Step 7: Check for MPs with multiple terms
        print("\n7. MPs with multiple terms:")
        multi_term = neo4j.run_query("""
            MATCH (mp:MP)-[:SERVED_TERM]->(t:Term)
            WITH mp, count(t) as term_count
            WHERE term_count > 1
            RETURN mp.name as mp_name, term_count
            ORDER BY term_count DESC
            LIMIT 5
        """)

        for mt in multi_term:
            print(f"   {mt['mp_name']}: {mt['term_count']} terms")

    finally:
        pg.close()
        neo4j.close()

    print("\n" + "=" * 80)
    print(f"✅ IMPORT COMPLETE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

if __name__ == "__main__":
    main()
