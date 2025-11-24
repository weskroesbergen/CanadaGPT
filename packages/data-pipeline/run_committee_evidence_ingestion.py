#!/usr/bin/env python3
"""
Committee Evidence Ingestion Cloud Run Job

This job imports committee evidence (witness testimony and MP questions) from OurCommons XML data.
It's designed to be run as a Cloud Run job on a schedule or on-demand.

Features:
- Fetches committee meeting evidence from OurCommons DocumentViewer XML
- Imports witness testimony with organization and role metadata
- Captures MP questions and interventions
- Links testimonies to MPs via person database IDs
- Links evidence to Committee and Meeting nodes

Environment variables:
- NEO4J_URI: Neo4j connection URI (default: bolt://10.128.0.3:7687)
- NEO4J_USERNAME: Neo4j username (default: neo4j)
- NEO4J_PASSWORD: Neo4j password (required)
- COMMITTEE_CODE: Specific committee to import (default: None = all committees)
- MEETINGS_LIMIT: Max meetings per committee (default: None = all new meetings)
"""

import sys
import os
from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger
from fedmcp_pipeline.ingest.committee_evidence_xml_import import CommitteeEvidenceXMLImporter


def main():
    """Run committee evidence ingestion job."""

    logger.info("=" * 80)
    logger.info("COMMITTEE EVIDENCE INGESTION CLOUD RUN JOB - STARTING")
    logger.info("=" * 80)
    print()

    # Get environment variables
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://10.128.0.3:7687')
    neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD')
    committee_code = os.getenv('COMMITTEE_CODE')  # Optional: specific committee
    meetings_limit = os.getenv('MEETINGS_LIMIT')  # Optional: limit meetings per committee

    if not neo4j_password:
        logger.error("NEO4J_PASSWORD environment variable not set!")
        sys.exit(1)

    # Parse meetings limit
    limit = None
    if meetings_limit:
        try:
            limit = int(meetings_limit)
            logger.info(f"Meetings limit set to: {limit} per committee")
        except ValueError:
            logger.warning(f"Invalid MEETINGS_LIMIT value: {meetings_limit}, using None (all meetings)")

    logger.info(f"Connecting to Neo4j at {neo4j_uri}...")
    neo4j = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)

    try:
        logger.info("Running committee evidence ingestion from OurCommons XML...")
        logger.info("This will:")
        logger.info("  - Fetch committee meeting evidence from DocumentViewer")
        logger.info("  - Import witness testimony and MP questions")
        logger.info("  - Link testimonies to MPs via person database IDs")
        logger.info("  - Link evidence to Committee and Meeting nodes")
        logger.info("  - Skip meetings that already have evidence imported")
        print()

        # Create importer
        importer = CommitteeEvidenceXMLImporter(neo4j)

        # Import evidence
        if committee_code:
            logger.info(f"Importing evidence for committee: {committee_code}")
            stats = importer.import_evidence_for_meetings(
                committee_code=committee_code,
                limit=limit,
                skip_existing=True
            )
        else:
            logger.info("Importing evidence for all committees in Neo4j")
            stats = importer.import_all_committees(
                limit_per_committee=limit,
                skip_existing=True
            )

        print()
        logger.success(f"✅ Successfully imported evidence for {stats['meetings']} meetings")
        logger.success(f"✅ Imported {stats['testimonies']} testimonies total")
        if stats['skipped'] > 0:
            logger.info(f"ℹ️  Skipped {stats['skipped']} meetings with existing evidence")
        if stats['errors'] > 0:
            logger.warning(f"⚠️  {stats['errors']} errors occurred (likely 404s for unpublished evidence)")

        logger.info("=" * 80)
        logger.info("COMMITTEE EVIDENCE INGESTION CLOUD RUN JOB - COMPLETED")
        logger.info("=" * 80)
        print()

        # 404s are expected for meetings without published evidence
        # Only log a warning if no meetings were imported
        if stats['meetings'] == 0 and stats['errors'] > 0:
            logger.warning(f"⚠️  No evidence imported - {stats['errors']} meetings returned 404 (likely unpublished evidence)")
            logger.info("This is expected behavior for committees without published evidence")

    except Exception as e:
        logger.error(f"Committee evidence ingestion job failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        neo4j.close()


if __name__ == "__main__":
    main()
