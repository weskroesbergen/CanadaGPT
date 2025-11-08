"""Test OpenParliament bulk import."""
import sys
from pathlib import Path

# Add packages to path
PIPELINE_PATH = Path(__file__).parent / "packages" / "data-pipeline"
sys.path.insert(0, str(PIPELINE_PATH))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.config import Config
from fedmcp_pipeline.ingest.bulk_import import OpenParliamentBulkImporter

# Load config
config = Config(env_file=Path("packages/data-pipeline/.env"))

print("=" * 60)
print("OpenParliament Bulk Import Test")
print("=" * 60)
print()
print("⚠️  PREREQUISITES:")
print("1. Install PostgreSQL: brew install postgresql@14")
print("2. Start PostgreSQL: brew services start postgresql@14")
print("3. Create database: createdb openparliament_temp")
print("4. Install bunzip2: brew install bzip2")
print()
print("This test will:")
print("  1. Download ~1.2GB PostgreSQL dump (if not cached)")
print("  2. Load into temporary PostgreSQL database (~10-20 min)")
print("  3. Import MPs, debates, statements, committees into Neo4j")
print()

response = input("Continue? [y/N]: ")
if response.lower() != 'y':
    print("Aborted.")
    sys.exit(0)

# PostgreSQL connection string
PG_CONN = "postgresql://localhost:5432/openparliament_temp"

with Neo4jClient(config.neo4j_uri, config.neo4j_user, config.neo4j_password) as neo4j:
    importer = OpenParliamentBulkImporter(neo4j, PG_CONN)

    # Run full import with limit for testing
    stats = importer.import_all(
        download=True,      # Download dump
        load_pg=True,       # Load into PostgreSQL
        batch_size=1000,    # Neo4j batch size
        limit=100           # Limit for testing (remove for full import)
    )

print("\n✅ Test complete!")
print("\nTo run full historical import (no limit):")
print("  stats = importer.import_all(download=False, load_pg=False, limit=None)")
