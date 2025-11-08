#!/usr/bin/env python3
"""
Import ALL Hansard statements from PostgreSQL to Neo4j.

This script imports the complete dataset:
- 3,673,748 statements from 1994-present
- All associated documents
- Creates all relationships (MADE_BY, PART_OF, MENTIONS)
- Creates full-text search indexes

Estimated runtime: 2-3 hours
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages" / "data-pipeline"))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.postgres_client import PostgresClient
from fedmcp_pipeline.utils.config import Config
from fedmcp_pipeline.ingest.hansard import ingest_hansard_full


def main():
    """Main execution function."""
    start_time = datetime.now()

    print("=" * 80)
    print("HANSARD COMPLETE IMPORT (ALL STATEMENTS)")
    print("=" * 80)
    print(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("This will import:")
    print("  - ~3.67 million statements")
    print("  - ~25,000 documents")
    print("  - All relationships (MADE_BY, PART_OF, MENTIONS)")
    print("  - Full-text search indexes")
    print()
    print("Estimated time: 2-3 hours")
    print("=" * 80)
    print()

    # Load configuration
    env_file = Path(__file__).parent / "packages" / "data-pipeline" / ".env"
    config = Config(env_file=env_file)

    # Connect to databases
    print("1. Connecting to databases...")
    try:
        # Use Config postgres_uri for connection
        # Config class handles reading from .env or environment
        import psycopg2
        from urllib.parse import urlparse

        # Parse the PostgreSQL URI from config
        pg_uri = config.postgres_uri
        parsed = urlparse(pg_uri)

        pg_client = PostgresClient(
            dbname=parsed.path.lstrip('/'),
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port or 5432
        )
        print(f"   ✅ Connected to PostgreSQL ({parsed.hostname})")
    except Exception as e:
        print(f"   ❌ Failed to connect to PostgreSQL: {e}")
        print()
        print("Make sure packages/data-pipeline/.env has POSTGRES_URI set:")
        print("  POSTGRES_URI=postgresql://user:password@host:port/database")
        return 1

    try:
        neo4j_client = Neo4jClient(
            uri=config.neo4j_uri,
            user=config.neo4j_user,
            password=config.neo4j_password
        )
        print("   ✅ Connected to Neo4j")
    except Exception as e:
        print(f"   ❌ Failed to connect to Neo4j: {e}")
        pg_client.close()
        return 1

    print()

    try:
        # Check current Neo4j statement count
        print("2. Checking current Neo4j status...")
        result = neo4j_client.run_query("MATCH (s:Statement) RETURN count(s) as count")
        current_count = result[0]["count"] if result else 0
        print(f"   Current statements in Neo4j: {current_count:,}")

        # Check PostgreSQL statement count
        pg_result = pg_client.execute_query(
            "SELECT COUNT(*) as count FROM hansards_statement WHERE time < '4000-01-01'",
            dict_cursor=True
        )
        total_pg_statements = pg_result[0]['count'] if pg_result else 0
        print(f"   Total statements in PostgreSQL: {total_pg_statements:,}")
        print(f"   Missing statements: {total_pg_statements - current_count:,}")
        print()

        # Confirm before proceeding
        if current_count > 0:
            print("⚠️  WARNING: Neo4j already has some statements.")
            print("   This import will MERGE (update existing, create new).")
            print()

        response = input("Continue with full import? [y/N]: ")
        if response.lower() != 'y':
            print("Aborted.")
            return 0

        print()
        print("=" * 80)
        print("Starting full import... (This will take 2-3 hours)")
        print("=" * 80)
        print()

        # Run the full import
        results = ingest_hansard_full(neo4j_client, pg_client)

        # Calculate duration
        end_time = datetime.now()
        duration = end_time - start_time
        hours = int(duration.total_seconds() / 3600)
        minutes = int((duration.total_seconds() % 3600) / 60)
        seconds = int(duration.total_seconds() % 60)

        # Print summary
        print()
        print("=" * 80)
        print("✅ IMPORT COMPLETE")
        print("=" * 80)
        print(f"Duration: {hours}h {minutes}m {seconds}s")
        print(f"Documents: {results.get('documents', 0):,}")
        print(f"Statements: {results.get('statements', 0):,}")
        print(f"MADE_BY links: {results.get('made_by_links', 0):,}")
        print(f"PART_OF links: {results.get('part_of_links', 0):,}")
        print(f"MENTIONS links: {results.get('mentions_links', 0):,}")
        print()
        print("🎉 All Hansard data successfully imported to Neo4j!")
        print("=" * 80)

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ ERROR DURING IMPORT")
        print("=" * 80)
        print(f"Error: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        return 1

    finally:
        pg_client.close()
        neo4j_client.close()

    return 0


if __name__ == "__main__":
    exit(main())
