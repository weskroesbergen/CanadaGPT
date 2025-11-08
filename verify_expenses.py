"""Verify expense data is in database and test GraphQL query."""
import sys
from pathlib import Path

# Add packages to path
PIPELINE_PATH = Path(__file__).parent / "packages" / "data-pipeline"
sys.path.insert(0, str(PIPELINE_PATH))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.config import Config

# Load config
config = Config(env_file=Path("packages/data-pipeline/.env"))

print("=" * 60)
print("Verifying Expense Data")
print("=" * 60)

with Neo4jClient(config.neo4j_uri, config.neo4j_user, config.neo4j_password) as client:
    # Count total expenses
    count_result = client.run_query("""
        MATCH (e:Expense)
        RETURN count(e) AS total
    """)
    total_expenses = count_result[0].get("total")
    print(f"\n✅ Total Expense nodes: {total_expenses:,}")

    # Count MPs with expenses
    mp_count_result = client.run_query("""
        MATCH (m:MP)-[:INCURRED]->(e:Expense)
        RETURN count(DISTINCT m) AS mp_count
    """)
    mp_count = mp_count_result[0].get("mp_count")
    print(f"✅ MPs with expense data: {mp_count}")

    # Get sample MP with expenses
    print("\n" + "=" * 60)
    print("Sample: MP with Most Expenses")
    print("=" * 60)
    sample_result = client.run_query("""
        MATCH (m:MP)-[:INCURRED]->(e:Expense)
        WITH m, count(e) AS expense_count, sum(e.amount) AS total_amount
        RETURN m.id AS mp_id, m.name AS mp_name, expense_count, total_amount
        ORDER BY expense_count DESC
        LIMIT 1
    """)
    if sample_result:
        record = sample_result[0]
        print(f"MP: {record.get('mp_name')} ({record.get('mp_id')})")
        print(f"Expense records: {record.get('expense_count')}")
        print(f"Total amount: ${record.get('total_amount'):,.2f}")

        # Get their individual expenses
        expenses_result = client.run_query("""
            MATCH (m:MP {id: $mp_id})-[:INCURRED]->(e:Expense)
            RETURN e.fiscal_year AS year, e.quarter AS quarter, e.category AS category, e.amount AS amount
            ORDER BY e.fiscal_year DESC, e.quarter DESC, e.category
            LIMIT 10
        """, {"mp_id": record.get("mp_id")})

        print("\nRecent expenses:")
        for exp in expenses_result:
            print(f"  FY{exp.get('year')} Q{exp.get('quarter')} - {exp.get('category')}: ${exp.get('amount'):,.2f}")

    # Test expense categories
    print("\n" + "=" * 60)
    print("Expenses by Category")
    print("=" * 60)
    category_result = client.run_query("""
        MATCH (e:Expense)
        RETURN e.category AS category, count(e) AS count, sum(e.amount) AS total
        ORDER BY total DESC
    """)
    for cat in category_result:
        print(f"  {cat.get('category')}: {cat.get('count')} records, ${cat.get('total'):,.2f} total")

print("\n✅ Expense data verification complete!")
