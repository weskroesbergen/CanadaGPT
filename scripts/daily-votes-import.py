#!/usr/bin/env python3
"""Daily votes import job - checks for new parliamentary votes and imports them."""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'packages' / 'data-pipeline'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'packages' / 'fedmcp' / 'src'))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger
from fedmcp_pipeline.ingest.votes_xml_import import VotesXMLImporter


def main():
    """Main entry point for daily votes import job."""
    logger.info("=" * 80)
    logger.info("DAILY VOTES IMPORT JOB")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("=" * 80)

    # Get Neo4j connection from environment
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://10.128.0.3:7687')
    neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD')

    if not neo4j_password:
        logger.error("NEO4J_PASSWORD environment variable not set")
        sys.exit(1)

    neo4j = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)

    try:
        # Create importer
        importer = VotesXMLImporter(neo4j)

        # Import votes from last 30 days (catches any recent votes)
        logger.info("Importing votes from last 30 days...")
        stats = importer.import_recent_votes(days=30)

        logger.info("=" * 80)
        if stats['votes'] > 0:
            logger.success(f"✅ Successfully imported {stats['votes']} vote(s), {stats['ballots']} ballot(s)")
        else:
            logger.info("ℹ️  No new votes found")

        if stats['errors'] > 0:
            logger.warning(f"⚠️  {stats['errors']} error(s) occurred")

        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Job failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        neo4j.close()


if __name__ == "__main__":
    main()
