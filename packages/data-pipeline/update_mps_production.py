#!/usr/bin/env python3
"""
Update MP data in production Neo4j with enhanced OurCommons XML metadata.

This script is meant to be run on the ingestion VM where it has network access
to the production Neo4j database at 10.128.0.3:7687.

Enhanced fields captured:
- honorific ("Hon.", "Right Hon.")
- term_start_date (precise swearing-in from OurCommons XML)
- term_end_date (or None if current)
- province (directly from XML, not inferred)
"""

import sys
import os
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger
from fedmcp_pipeline.ingest.parliament import ingest_mps


def main():
    """Update MPs in production with enhanced metadata."""

    logger.info("=" * 80)
    logger.info("UPDATING MPs IN PRODUCTION - ENHANCED METADATA")
    logger.info("=" * 80)
    print()

    # Production Neo4j connection
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://10.128.0.3:7687')
    neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD', 'canadagpt2024')

    logger.info(f"Connecting to production Neo4j at {neo4j_uri}...")
    neo4j = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)

    try:
        # Run MP ingestion with enhanced OurCommons XML metadata
        logger.info("Running MP ingestion with OurCommons XML enhancement...")
        logger.info("This will:")
        logger.info("  - Fetch 343 MPs from OurCommons XML (1 request)")
        logger.info("  - Fetch contact details from OpenParliament API (343 requests, ~10 min)")
        logger.info("  - Merge enhanced metadata into production Neo4j")
        logger.info("  - Capture honorifics, precise term dates, and province data")
        print()

        count = ingest_mps(neo4j, batch_size=100)

        print()
        logger.success(f"✅ Successfully updated {count} MPs in production")
        logger.info("=" * 80)
        print()
        logger.info("Enhanced metadata now available in production:")
        logger.info("  - Honorifics (Right Hon., Hon.)")
        logger.info("  - Precise term dates (FromDateTime/ToDateTime from OurCommons)")
        logger.info("  - Province data (directly from XML)")
        logger.info("  - All contact fields (email, phone, twitter, constituency office)")
        print()

    except Exception as e:
        logger.error(f"MP ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        neo4j.close()


if __name__ == "__main__":
    main()
