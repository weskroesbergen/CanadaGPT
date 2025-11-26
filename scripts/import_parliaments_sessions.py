#!/usr/bin/env python3
"""
Import Parliament and Session nodes into Neo4j.

This script:
1. Imports all 45 Canadian federal parliaments (1st through 45th)
2. Imports all 16 sessions where we have data (37-1 through 45-1)
3. Links existing Bills, Votes, and Documents to their respective sessions

Usage:
    python3 scripts/import_parliaments_sessions.py

Environment Variables:
    NEO4J_URI      - Neo4j connection URI (default: bolt://localhost:7687)
    NEO4J_USERNAME - Neo4j username (default: neo4j)
    NEO4J_PASSWORD - Neo4j password (required)
"""

import sys
import os
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'packages' / 'data-pipeline'))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger
from fedmcp_pipeline.ingest.parliament_sessions import run_full_import


def main():
    """Main entry point."""
    logger.info("=" * 80)
    logger.info("PARLIAMENT & SESSION IMPORT SCRIPT")
    logger.info("=" * 80)

    # Get Neo4j connection details from environment
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD')

    if not neo4j_password:
        logger.error("NEO4J_PASSWORD environment variable not set")
        logger.info("For production: Get password from GCP Secret Manager")
        logger.info("For local: export NEO4J_PASSWORD=canadagpt2024")
        sys.exit(1)

    logger.info(f"Connecting to Neo4j at {neo4j_uri}...")
    neo4j_client = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)

    try:
        # Run the full import process
        results = run_full_import(neo4j_client)

        # Summary
        logger.info("=" * 80)
        logger.info("IMPORT SUMMARY")
        logger.info("=" * 80)
        logger.info(f"✓ {results['parliaments']} parliaments imported (1st through 45th)")
        logger.info(f"✓ {results['sessions']} sessions imported (37-1 through 45-1)")
        logger.info(f"✓ {results['bills_linked']} bills linked to sessions/parliaments")
        logger.info(f"✓ {results['votes_linked']} votes linked to sessions")
        logger.info(f"✓ {results['documents_linked']} documents linked to sessions")
        logger.info("=" * 80)

        logger.info("Import complete! You can now query Parliament and Session nodes in GraphQL.")
        logger.info("")
        logger.info("Example queries:")
        logger.info("  - currentParliament: Get the active parliament")
        logger.info("  - currentSession: Get the active session")
        logger.info("  - parliamentStats(parliamentNumber: 45): Get stats for 45th Parliament")
        logger.info("  - sessionStats(sessionId: \"45-1\"): Get stats for Session 45-1")
        logger.info("")

    except Exception as e:
        logger.error(f"Error during import: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        neo4j_client.close()


if __name__ == "__main__":
    main()
