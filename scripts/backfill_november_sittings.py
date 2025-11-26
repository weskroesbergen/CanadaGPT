#!/usr/bin/env python3
"""Backfill specific sitting numbers for November 2025."""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'packages' / 'data-pipeline'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'packages' / 'fedmcp' / 'src'))

# Import after path setup
from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger
from fedmcp.clients.ourcommons import OurCommonsHansardClient
from fedmcp_pipeline.ingest.hansard import link_statements_to_mps_by_name

# Import functions from daily-hansard-import.py
sys.path.insert(0, str(Path(__file__).parent))
from daily_hansard_import import (
    parse_hansard_with_enhanced_metadata,
    import_hansard_to_neo4j,
    get_latest_document_id
)

def main():
    """Import sittings 050-057."""
    logger.info("=" * 80)
    logger.info("NOVEMBER 2025 HANSARD BACKFILL")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("=" * 80)

    # Get Neo4j connection
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD')

    if not neo4j_password:
        logger.error("NEO4J_PASSWORD environment variable not set")
        sys.exit(1)

    neo4j = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
    client = OurCommonsHansardClient()

    # Import sittings 050-057
    imported_count = 0
    for sitting_num in range(50, 58):
        sitting = f"{sitting_num:03d}"
        url = f"https://www.ourcommons.ca/Content/House/451/Debates/{sitting}/HAN{sitting}-E.XML"

        logger.info(f"Fetching sitting {sitting} from {url}...")

        try:
            # Fetch XML
            response = client.session.get(url, timeout=30)
            if response.status_code != 200:
                logger.warning(f"✗ Sitting {sitting}: HTTP {response.status_code}")
                continue

            logger.success(f"✓ Found XML for sitting {sitting}")

            # Parse
            hansard_data = parse_hansard_with_enhanced_metadata(response.text, url)
            iso_date = hansard_data['date']

            # Check if already exists
            result = neo4j.run_query(
                "MATCH (d:Document) WHERE d.date = $date RETURN d.id as id",
                {"date": iso_date}
            )

            if result:
                logger.info(f"⏭  Sitting {sitting} ({iso_date}) already exists, skipping")
                continue

            # Get next document ID
            latest_doc_id = get_latest_document_id(neo4j)
            document_id = latest_doc_id + 1

            # Import
            stmt_count, linked_count = import_hansard_to_neo4j(
                neo4j, hansard_data, iso_date, document_id, sitting
            )

            logger.success(
                f"✅ Imported sitting {sitting} ({iso_date}): "
                f"{stmt_count} statements, {linked_count} linked"
            )
            imported_count += 1

        except Exception as e:
            logger.error(f"Failed to import sitting {sitting}: {e}")
            import traceback
            traceback.print_exc()

    neo4j.close()

    logger.info("=" * 80)
    if imported_count > 0:
        logger.success(f"✅ Successfully imported {imported_count} new debate(s)")
    else:
        logger.info("ℹ️  No new debates imported")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
