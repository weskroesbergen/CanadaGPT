"""Debug script to compare MP names from database vs expenditure API."""
import sys
from pathlib import Path

# Add packages to path
FEDMCP_PATH = Path(__file__).parent / "packages" / "fedmcp" / "src"
PIPELINE_PATH = Path(__file__).parent / "packages" / "data-pipeline"
sys.path.insert(0, str(FEDMCP_PATH))
sys.path.insert(0, str(PIPELINE_PATH))

from fedmcp.clients.expenditure import MPExpenditureClient
from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.config import Config

# Load config
config = Config(env_file=Path("packages/data-pipeline/.env"))

# Get MPs from database
print("=" * 60)
print("MPs from Neo4j database:")
print("=" * 60)
with Neo4jClient(config.neo4j_uri, config.neo4j_user, config.neo4j_password) as client:
    mp_records = client.run_query("""
        MATCH (m:MP)
        RETURN m.id AS id, m.name AS name, m.given_name AS given_name, m.family_name AS family_name
        ORDER BY m.name
        LIMIT 10
    """)
    db_names = []
    for record in mp_records:
        db_names.append(record.get("name"))
        print(f"  ID: {record.get('id')}")
        print(f"  Name: {record.get('name')}")
        print(f"  Given: {record.get('given_name')}")
        print(f"  Family: {record.get('family_name')}")
        print()

# Get MPs from expenditure API
print("=" * 60)
print("MPs from Expenditure API (FY 2025 Q1):")
print("=" * 60)
expense_client = MPExpenditureClient()
try:
    summary = expense_client.get_quarterly_summary(2025, 1)
    api_names = []
    for i, mp_expenses in enumerate(summary[:10]):
        api_names.append(mp_expenses.name)
        print(f"  Name: {mp_expenses.name}")
        print(f"  Constituency: {mp_expenses.constituency}")
        print(f"  Caucus: {mp_expenses.caucus}")
        print()

    print("=" * 60)
    print("Name format comparison:")
    print("=" * 60)
    print(f"Database names (first 3): {db_names[:3]}")
    print(f"API names (first 3): {api_names[:3]}")

    # Check for matches
    print("\n" + "=" * 60)
    print("Checking for matches (case-insensitive):")
    print("=" * 60)
    matches = 0
    for api_name in api_names[:10]:
        found = api_name.lower() in [n.lower() for n in db_names]
        print(f"  {api_name}: {'✅ FOUND' if found else '❌ NOT FOUND'}")
        if found:
            matches += 1
    print(f"\nMatch rate: {matches}/10")

except Exception as e:
    print(f"Error: {e}")
