#!/usr/bin/env python3
"""
Votes Ingestion Cloud Run Job

This job imports parliamentary votes and ballots from OurCommons XML data.
It's designed to be run as a Cloud Run job on a schedule.

Features:
- Fetches vote summaries from OurCommons bulk XML
- Imports detailed vote data with individual MP ballots
- Links votes to bills and MPs in Neo4j
- Captures full voting records and metadata

Environment variables required:
- NEO4J_URI: Neo4j connection URI (default: bolt://10.128.0.3:7687)
- NEO4J_USERNAME: Neo4j username (default: neo4j)
- NEO4J_PASSWORD: Neo4j password
- VOTES_LIMIT: Max votes to import (default: None = all new votes)
"""

import sys
import os
from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger
from fedmcp_pipeline.ingest.votes_xml_import import VotesXMLImporter


def main():
    """Run votes ingestion job."""

    logger.info("=" * 80)
    logger.info("VOTES INGESTION CLOUD RUN JOB - STARTING")
    logger.info("=" * 80)
    print()

    # Get environment variables
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://10.128.0.3:7687')
    neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD')
    votes_limit = os.getenv('VOTES_LIMIT')

    if not neo4j_password:
        logger.error("NEO4J_PASSWORD environment variable not set!")
        sys.exit(1)

    # Parse votes limit
    limit = None
    if votes_limit:
        try:
            limit = int(votes_limit)
            logger.info(f"Votes limit set to: {limit}")
        except ValueError:
            logger.warning(f"Invalid VOTES_LIMIT value: {votes_limit}, using None (all votes)")

    logger.info(f"Connecting to Neo4j at {neo4j_uri}...")
    neo4j = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)

    try:
        logger.info("Running votes ingestion from OurCommons XML...")
        logger.info("This will:")
        logger.info("  - Fetch vote summaries from bulk XML")
        logger.info("  - Import detailed vote data with individual ballots")
        logger.info("  - Link votes to bills and MPs in Neo4j")
        logger.info("  - Skip votes that already exist in database")
        print()

        # Create importer and run
        importer = VotesXMLImporter(neo4j)
        stats = importer.import_votes(limit=limit, skip_existing=True)

        print()
        logger.success(f"✅ Successfully imported {stats['votes']} votes, {stats['ballots']} ballots")
        if stats['skipped'] > 0:
            logger.info(f"ℹ️  Skipped {stats['skipped']} existing votes")
        if stats['errors'] > 0:
            logger.warning(f"⚠️  {stats['errors']} errors occurred")

        logger.info("=" * 80)
        logger.info("VOTES INGESTION CLOUD RUN JOB - COMPLETED")
        logger.info("=" * 80)
        print()

        # Exit with error code if there were errors
        if stats['errors'] > 0:
            sys.exit(1)

    except Exception as e:
        logger.error(f"Votes ingestion job failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        neo4j.close()


if __name__ == "__main__":
    main()
