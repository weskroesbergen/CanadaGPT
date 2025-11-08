"""Test recent data import (2022-present) - fast and lightweight."""
import sys
from pathlib import Path

# Add packages to path
PIPELINE_PATH = Path(__file__).parent / "packages" / "data-pipeline"
sys.path.insert(0, str(PIPELINE_PATH))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.config import Config
from fedmcp_pipeline.ingest.recent_import import RecentDataImporter

# Load config
config = Config(env_file=Path("packages/data-pipeline/.env"))

print("=" * 60)
print("Recent Data Import (2022-Present)")
print("=" * 60)
print()
print("This will import:")
print("  ✅ All current MPs (343)")
print("  ✅ All current bills (111)")
print("  ✅ Debates since 2022 (~300-500)")
print("  ✅ Statements since 2022 (~50,000)")
print("  ✅ Votes since 2022 (~500)")
print("  ✅ All committees (~25)")
print("  ✅ Recent MP expenses")
print()
print("Requirements:")
print("  ⚡ No PostgreSQL needed!")
print("  ⚡ Direct API → Neo4j import")
print("  ⚡ ~3 GB disk space")
print("  ⚡ ~15-20 minutes total")
print()
print("Data coverage:")
print("  📅 2022-01-01 to present")
print("  📊 ~3 years of complete data")
print("  🇨🇦 All current parliament info")
print()

response = input("Continue with import? [y/N]: ")
if response.lower() != 'y':
    print("Aborted.")
    sys.exit(0)

print("\n" + "=" * 60)
print("Starting import...")
print("=" * 60)

with Neo4jClient(config.neo4j_uri, config.neo4j_user, config.neo4j_password) as neo4j:
    importer = RecentDataImporter(
        neo4j,
        start_date="2022-01-01"  # Change this to import different date range
    )

    # Run import
    stats = importer.import_all(batch_size=1000)

print("\n✅ Import complete!")
print("\nYou now have:")
print(f"  - {stats.get('mps', 0):,} MPs")
print(f"  - {stats.get('bills', 0):,} current bills")
print(f"  - {stats.get('debates', {}).get('debates', 0):,} recent debates")
print(f"  - {stats.get('debates', {}).get('statements', 0):,} statements")
print(f"  - {stats.get('votes', 0):,} votes")
print(f"  - {stats.get('committees', 0)} committees")
print()
print("🎉 Ready to use! No historical bulk import needed.")
print()
print("To change date range, edit test_recent_import.py:")
print("  start_date='2022-01-01'  # Change to '2020-01-01' for more data")
