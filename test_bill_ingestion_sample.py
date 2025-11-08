"""Test bill ingestion with sponsor details on a small sample."""
import sys
from pathlib import Path

# Add packages to path
PIPELINE_PATH = Path(__file__).parent / "packages" / "data-pipeline"
sys.path.insert(0, str(PIPELINE_PATH))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.config import Config
from fedmcp_pipeline.ingest.parliament import ingest_bills, link_bill_sponsors

# Load config
config = Config(env_file=Path("packages/data-pipeline/.env"))

print("=" * 60)
print("Testing Bill Ingestion with Sponsor Details (100 bills)")
print("=" * 60)

with Neo4jClient(config.neo4j_uri, config.neo4j_user, config.neo4j_password) as client:
    # Test with just 100 bills
    print("\n1. Ingesting 100 bills with detailed sponsor information...")
    bill_count = ingest_bills(client, limit=100, fetch_details=True)
    print(f"✅ Ingested {bill_count} bills")

    # Check how many have sponsor data
    print("\n2. Checking sponsor data...")
    result = client.run_query("""
        MATCH (b:Bill)
        WHERE b.sponsor_politician_url IS NOT NULL
        RETURN count(b) AS bills_with_sponsors
    """)
    sponsor_count = result[0].get("bills_with_sponsors", 0)
    print(f"Bills with sponsor_politician_url: {sponsor_count}")

    # Create SPONSORED relationships
    print("\n3. Creating SPONSORED relationships...")
    rel_count = link_bill_sponsors(client)
    print(f"✅ Created {rel_count} SPONSORED relationships")

    # Sample some sponsored bills
    print("\n4. Sample sponsored bills:")
    samples = client.run_query("""
        MATCH (m:MP)-[:SPONSORED]->(b:Bill)
        RETURN m.name AS mp_name, b.number AS bill_number, b.session AS session, b.title AS title
        LIMIT 5
    """)
    for s in samples:
        print(f"  {s.get('mp_name')} sponsored {s.get('bill_number')} ({s.get('session')})")
        print(f"    {s.get('title')[:60]}...")

print("\n✅ Test complete!")
