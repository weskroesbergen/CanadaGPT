"""Test elections sample import from PostgreSQL to Neo4j."""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages/data-pipeline"))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.postgres_client import PostgresClient
from fedmcp_pipeline.ingest.elections import ingest_elections_sample

# Load environment
load_dotenv(Path(__file__).parent / "packages/data-pipeline/.env")

print("=" * 80)
print("ELECTIONS SAMPLE IMPORT TEST")
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
print("\n2. Running sample import (50 candidacies)...")
try:
    results = ingest_elections_sample(
        neo4j_client=neo4j_client,
        postgres_client=postgres_client,
        candidacy_limit=50
    )

    print("\n3. Validating import...")

    # Verify candidacies were created
    candidacy_count = neo4j_client.run_query("MATCH (c:Candidacy) RETURN count(c) as count")
    print(f"   Candidacy nodes in Neo4j: {candidacy_count[0]['count']:,}")

    # Verify relationships
    ran_in = neo4j_client.run_query("MATCH ()-[r:RAN_IN]->() RETURN count(r) as count")
    print(f"   RAN_IN relationships: {ran_in[0]['count']:,}")

    # Check elected vs defeated
    elected_stats = neo4j_client.run_query("""
        MATCH (c:Candidacy)
        RETURN
            count(CASE WHEN c.elected = true THEN 1 END) as elected,
            count(CASE WHEN c.elected = false THEN 1 END) as defeated,
            count(c) as total
    """)
    if elected_stats:
        stats = elected_stats[0]
        print(f"   Elected: {stats['elected']:,}")
        print(f"   Defeated: {stats['defeated']:,}")

    # Sample a candidacy
    print("\n4. Sample candidacy:")
    sample = neo4j_client.run_query("""
        MATCH (c:Candidacy)
        WHERE c.votetotal IS NOT NULL
        RETURN c.riding_name as riding,
               c.party_name as party,
               c.votetotal as votes,
               c.votepercent as percent,
               c.elected as elected,
               c.election_date as election_date
        LIMIT 1
    """)

    if sample:
        cand = sample[0]
        print(f"   Riding: {cand['riding']}")
        print(f"   Party: {cand['party']}")
        print(f"   Votes: {cand['votes']:,} ({cand['percent']:.2f}%)")
        print(f"   Elected: {'Yes' if cand['elected'] else 'No'}")
        print(f"   Election Date: {cand['election_date']}")

    # Check Politician->Candidacy links
    print("\n5. Checking Politician->Candidacy relationships:")
    politician_links = neo4j_client.run_query("""
        MATCH (p:Politician)-[:RAN_IN]->(c:Candidacy)
        WHERE c.elected = true
        RETURN p.name as name,
               c.riding_name as riding,
               c.election_date as date
        LIMIT 3
    """)

    if politician_links:
        print(f"   Found {len(politician_links)} elected politicians with candidacies:")
        for link in politician_links:
            print(f"      {link['name']} - {link['riding']} ({link['date']})")
    else:
        print("   ⚠️  No politicians linked to candidacies yet (politicians may not be imported)")

    # Party distribution
    print("\n6. Party distribution:")
    party_dist = neo4j_client.run_query("""
        MATCH (c:Candidacy)
        WHERE c.party_name IS NOT NULL
        RETURN c.party_name as party, count(c) as count
        ORDER BY count DESC
        LIMIT 5
    """)

    if party_dist:
        for record in party_dist:
            print(f"      {record['party']}: {record['count']} candidacies")

    print("\n" + "=" * 80)
    print("✅ ELECTIONS SAMPLE IMPORT TEST COMPLETE")
    print("=" * 80)
    print(f"\nResults:")
    print(f"  Candidacies created: {results.get('candidacies', 0):,}")
    print(f"  RAN_IN links: {results.get('ran_in_links', 0):,}")
    print(f"  Enriched with metadata: {results.get('enriched', 0):,}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    postgres_client.close()
    neo4j_client.close()
