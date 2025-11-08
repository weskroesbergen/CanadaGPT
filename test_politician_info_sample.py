"""Test politician info sample enrichment from PostgreSQL to Neo4j."""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages/data-pipeline"))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.postgres_client import PostgresClient
from fedmcp_pipeline.ingest.politician_info import ingest_politician_info_sample

# Load environment
load_dotenv(Path(__file__).parent / "packages/data-pipeline/.env")

print("=" * 80)
print("POLITICIAN INFO SAMPLE ENRICHMENT TEST")
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

# Run sample enrichment
print("\n2. Running sample enrichment (10 politicians)...")
try:
    results = ingest_politician_info_sample(
        neo4j_client=neo4j_client,
        postgres_client=postgres_client,
        limit=10
    )

    print("\n3. Validating enrichment...")

    # Verify politicians were enriched with email
    email_count = neo4j_client.run_query("""
        MATCH (p:Politician)
        WHERE p.email IS NOT NULL
        RETURN count(p) as count
    """)
    print(f"   Politicians with email: {email_count[0]['count']:,}")

    # Verify politicians with phone
    phone_count = neo4j_client.run_query("""
        MATCH (p:Politician)
        WHERE p.phone IS NOT NULL
        RETURN count(p) as count
    """)
    print(f"   Politicians with phone: {phone_count[0]['count']:,}")

    # Verify politicians with twitter
    twitter_count = neo4j_client.run_query("""
        MATCH (p:Politician)
        WHERE p.twitter_id IS NOT NULL
        RETURN count(p) as count
    """)
    print(f"   Politicians with twitter: {twitter_count[0]['count']:,}")

    # Sample an enriched politician
    print("\n4. Sample enriched politician:")
    sample = neo4j_client.run_query("""
        MATCH (p:Politician)
        WHERE p.email IS NOT NULL OR p.phone IS NOT NULL
        RETURN p.name as name,
               p.email as email,
               p.phone as phone,
               p.twitter_id as twitter,
               p.parl_id as parl_id
        LIMIT 1
    """)

    if sample:
        pol = sample[0]
        print(f"   Name: {pol['name']}")
        if pol['email']:
            print(f"   Email: {pol['email']}")
        if pol['phone']:
            print(f"   Phone: {pol['phone']}")
        if pol['twitter']:
            print(f"   Twitter: {pol['twitter']}")
        if pol['parl_id']:
            print(f"   Parliament ID: {pol['parl_id']}")

    # Check available info schema types
    print("\n5. Checking info schema types added:")
    schema_check = neo4j_client.run_query("""
        MATCH (p:Politician)
        RETURN
            count(CASE WHEN p.email IS NOT NULL THEN 1 END) as has_email,
            count(CASE WHEN p.phone IS NOT NULL THEN 1 END) as has_phone,
            count(CASE WHEN p.twitter_id IS NOT NULL THEN 1 END) as has_twitter,
            count(CASE WHEN p.parl_id IS NOT NULL THEN 1 END) as has_parl_id,
            count(CASE WHEN p.alternate_name IS NOT NULL THEN 1 END) as has_alternate_name
    """)

    if schema_check:
        stats = schema_check[0]
        print(f"   Politicians with email: {stats['has_email']:,}")
        print(f"   Politicians with phone: {stats['has_phone']:,}")
        print(f"   Politicians with twitter: {stats['has_twitter']:,}")
        print(f"   Politicians with parl_id: {stats['has_parl_id']:,}")
        print(f"   Politicians with alternate_name: {stats['has_alternate_name']:,}")

    print("\n" + "=" * 80)
    print("✅ POLITICIAN INFO SAMPLE ENRICHMENT TEST COMPLETE")
    print("=" * 80)
    print(f"\nResults:")
    print(f"  Politicians enriched: {results.get('politicians_enriched', 0):,}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    postgres_client.close()
    neo4j_client.close()
