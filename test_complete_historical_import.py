"""Test complete historical import: Lipad (1901-1993) + OpenParliament (1994-present)."""
import sys
from pathlib import Path

# Add packages to path
PIPELINE_PATH = Path(__file__).parent / "packages" / "data-pipeline"
sys.path.insert(0, str(PIPELINE_PATH))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.config import Config
from fedmcp_pipeline.ingest.lipad_import import CombinedHistoricalImporter

# Load config
config = Config(env_file=Path("packages/data-pipeline/.env"))

print("=" * 60)
print("Complete Historical Import: 1901-Present")
print("=" * 60)
print()
print("This will import 120+ years of Canadian parliamentary data:")
print("  - Lipad: 1901-1993 (93 years)")
print("  - OpenParliament: 1994-present (31 years)")
print()
print("⚠️  PREREQUISITES:")
print("1. PostgreSQL installed and running")
print("   brew install postgresql@14")
print("   brew services start postgresql@14")
print("   createdb openparliament_temp")
print()
print("2. Lipad data downloaded (OPTIONAL)")
print("   Visit: https://www.lipad.ca/data/")
print("   Download CSV or XML package")
print("   Extract to local directory")
print()
print("3. ~20GB free disk space")
print("   - OpenParliament dump: 1.2GB + 6GB extracted")
print("   - Lipad data: varies by format")
print("   - PostgreSQL database: ~7GB")
print()

# PostgreSQL connection
PG_CONN = "postgresql://localhost:5432/openparliament_temp"

# Lipad data directory (optional - set to None to skip)
LIPAD_DIR = input("Enter Lipad data directory path (or press Enter to skip): ").strip()
if LIPAD_DIR == "":
    LIPAD_DIR = None
    print("⚠️  Skipping Lipad import - will only import 1994-present")
else:
    LIPAD_DIR = Path(LIPAD_DIR)
    if not LIPAD_DIR.exists():
        print(f"❌ Directory not found: {LIPAD_DIR}")
        sys.exit(1)

print()
response = input("Continue with import? [y/N]: ")
if response.lower() != 'y':
    print("Aborted.")
    sys.exit(0)

print("\n" + "=" * 60)
print("Starting import... This will take 1-2 hours")
print("=" * 60)

with Neo4jClient(config.neo4j_uri, config.neo4j_user, config.neo4j_password) as neo4j:
    importer = CombinedHistoricalImporter(neo4j, PG_CONN)

    # Run complete import
    stats = importer.import_complete_history(
        lipad_data_dir=LIPAD_DIR,
        batch_size=1000
    )

print("\n✅ Complete historical import finished!")
print(f"\nTotal coverage: {stats['total_years']} years")

if stats.get('lipad'):
    print(f"\nLipad (1901-1993):")
    print(f"  Debates: {stats['lipad'].get('debates', 0):,}")
    print(f"  Statements: {stats['lipad'].get('statements', 0):,}")
    print(f"  Speakers: {stats['lipad'].get('speakers', 0):,}")

if stats.get('openparliament'):
    print(f"\nOpenParliament (1994-present):")
    print(f"  MPs: {stats['openparliament'].get('mps', 0):,}")
    print(f"  Debates: {stats['openparliament'].get('debates', {}).get('debates', 0):,}")
    print(f"  Statements: {stats['openparliament'].get('debates', {}).get('statements', 0):,}")
    print(f"  Committees: {stats['openparliament'].get('committees', {}).get('committees', 0):,}")

print("\n🎉 You now have 120+ years of Canadian parliamentary history in Neo4j!")
