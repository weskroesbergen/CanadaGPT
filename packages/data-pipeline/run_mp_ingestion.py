#!/usr/bin/env python3
"""
MP Ingestion Cloud Run Job

This job runs the enhanced MP ingestion with OurCommons XML metadata.
It's designed to be run as a Cloud Run job on a schedule.

Environment variables required:
- NEO4J_URI: Neo4j connection URI (default: bolt://10.128.0.3:7687)
- NEO4J_USERNAME: Neo4j username (default: neo4j)
- NEO4J_PASSWORD: Neo4j password
"""

import sys
import os
from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger
from fedmcp_pipeline.ingest.parliament import ingest_mps, ingest_committee_memberships


def main():
    """Run MP ingestion job."""

    logger.info("=" * 80)
    logger.info("MP INGESTION CLOUD RUN JOB - STARTING")
    logger.info("=" * 80)
    print()

    # Get environment variables
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://10.128.0.3:7687')
    neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD')

    if not neo4j_password:
        logger.error("NEO4J_PASSWORD environment variable not set!")
        sys.exit(1)

    logger.info(f"Connecting to Neo4j at {neo4j_uri}...")
    neo4j = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)

    try:
        # Step 1: MP Ingestion
        logger.info("Running MP ingestion with OurCommons XML enhancement...")
        logger.info("This will:")
        logger.info("  - Fetch 343 MPs from OurCommons XML (1 request)")
        logger.info("  - Fetch contact details from OpenParliament API (343 requests)")
        logger.info("  - Merge enhanced metadata into Neo4j")
        logger.info("  - Capture honorifics, precise term dates, and province data")
        print()

        mp_count = ingest_mps(neo4j, batch_size=100)

        print()
        logger.success(f"✅ Successfully ingested {mp_count} MPs")
        print()

        # Step 2: Committee Membership Ingestion
        logger.info("Running committee membership ingestion...")
        logger.info("This will:")
        logger.info("  - Scrape committee pages from OurCommons")
        logger.info("  - Create SERVES_ON relationships with role information")
        logger.info("  - Use fuzzy name matching to link MPs to committees")
        print()

        committee_stats = ingest_committee_memberships(neo4j)

        print()
        logger.success(f"✅ Successfully created {committee_stats['serves_on_created']} committee memberships")
        if committee_stats['mp_not_found'] > 0:
            logger.warning(f"⚠️  {committee_stats['mp_not_found']} MPs could not be matched by name")
        print()

        # Final Summary
        logger.info("=" * 80)
        logger.info("MP INGESTION CLOUD RUN JOB - COMPLETED")
        logger.info("=" * 80)
        logger.info(f"MPs imported: {mp_count}")
        logger.info(f"Committee memberships: {committee_stats['serves_on_created']}")
        logger.info(f"MPs not found: {committee_stats['mp_not_found']}")
        logger.info("=" * 80)
        print()

    except Exception as e:
        logger.error(f"MP ingestion job failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        neo4j.close()


if __name__ == "__main__":
    main()
