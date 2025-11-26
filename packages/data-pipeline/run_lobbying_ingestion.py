#!/usr/bin/env python3
"""
Lobbying Data Ingestion Cloud Run Job

This job imports lobbying registry data from the Open Canada portal.
It's designed to be run as a Cloud Run job on a schedule or on-demand.

Features:
- Downloads ~90MB CSV data from Open Canada portal
- Caches data locally for subsequent runs
- Imports lobby registrations and communications
- Creates Organization and Lobbyist nodes
- Full refresh of all lobbying data

Environment variables:
- NEO4J_URI: Neo4j connection URI (default: bolt://10.128.0.3:7687)
- NEO4J_USERNAME: Neo4j username (default: neo4j)
- NEO4J_PASSWORD: Neo4j password (required)
"""

import sys
import os
from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger
from fedmcp_pipeline.ingest.lobbying import ingest_lobbying_data


def main():
    """Run lobbying data ingestion job."""

    logger.info("=" * 80)
    logger.info("LOBBYING DATA INGESTION CLOUD RUN JOB - STARTING")
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
        logger.info("Running lobbying data ingestion...")
        logger.info("This will:")
        logger.info("  - Download ~90MB CSV data from Open Canada portal")
        logger.info("  - Import lobby registrations and communications")
        logger.info("  - Create Organization and Lobbyist nodes")
        logger.info("  - Full refresh of all lobbying data")
        print()

        # Run ingestion
        stats = ingest_lobbying_data(neo4j, batch_size=10000)

        print()
        logger.success(f"✅ Successfully imported {stats['lobby_registrations']:,} lobby registrations")
        logger.success(f"✅ Successfully imported {stats['lobby_communications']:,} lobby communications")
        logger.success(f"✅ Created {stats['organizations']:,} organization nodes")
        logger.success(f"✅ Created {stats['lobbyists']:,} lobbyist nodes")

        logger.info("=" * 80)
        logger.info("LOBBYING DATA INGESTION CLOUD RUN JOB - COMPLETED")
        logger.info("=" * 80)
        print()

    except Exception as e:
        logger.error(f"Lobbying data ingestion job failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        neo4j.close()


if __name__ == "__main__":
    main()
