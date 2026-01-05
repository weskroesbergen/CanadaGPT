#!/usr/bin/env python3
"""Written Questions Ingestion Cloud Run Job.

This script imports Written Questions metadata from the House of Commons
website into Neo4j, creating WrittenQuestion nodes and linking them to MPs.

Usage:
    # Import new questions only (incremental)
    python run_written_questions_ingestion.py

    # Full refresh (re-import all)
    python run_written_questions_ingestion.py --full-refresh

    # Specific session
    python run_written_questions_ingestion.py --parliament-session 44-1

    # Limit for testing
    python run_written_questions_ingestion.py --limit 50

Environment Variables:
    NEO4J_URI: Neo4j connection URI (default: bolt://10.128.0.3:7687)
    NEO4J_USERNAME: Neo4j username (default: neo4j)
    NEO4J_PASSWORD: Neo4j password (required)
"""

import sys
import os
import argparse
from datetime import datetime

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger
from fedmcp_pipeline.ingest.written_questions import (
    ingest_written_questions,
    update_question_statuses,
)


def main():
    """Run written questions ingestion job."""
    parser = argparse.ArgumentParser(
        description='Import Written Questions from House of Commons website'
    )
    parser.add_argument(
        '--parliament-session',
        type=str,
        default='45-1',
        help='Parliament session to import (e.g., "45-1"). Default: 45-1'
    )
    parser.add_argument(
        '--full-refresh',
        action='store_true',
        help='Re-import all questions (not just new ones)'
    )
    parser.add_argument(
        '--update-status',
        action='store_true',
        help='Update status of existing questions only (check if answered)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of questions to import (for testing)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Batch size for Neo4j operations. Default: 100'
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("WRITTEN QUESTIONS INGESTION CLOUD RUN JOB")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info(f"Parliament Session: {args.parliament_session}")
    logger.info(f"Mode: {'Full Refresh' if args.full_refresh else 'Status Update' if args.update_status else 'Incremental'}")
    if args.limit:
        logger.info(f"Limit: {args.limit} questions")
    logger.info("=" * 80)

    # Get Neo4j connection from environment
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://10.128.0.3:7687')
    neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD')

    if not neo4j_password:
        logger.error("NEO4J_PASSWORD environment variable not set!")
        sys.exit(1)

    logger.info(f"Connecting to Neo4j at {neo4j_uri}...")
    neo4j = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)

    try:
        if args.update_status:
            # Just update statuses of existing questions
            stats = update_question_statuses(
                neo4j_client=neo4j,
                parliament_session=args.parliament_session,
            )
            logger.success(f"Updated {stats.get('updated', 0)} question statuses")
        else:
            # Full ingestion
            stats = ingest_written_questions(
                neo4j_client=neo4j,
                parliament_session=args.parliament_session,
                batch_size=args.batch_size,
                full_refresh=args.full_refresh,
                limit=args.limit,
            )

            questions_created = stats.get('questions_created', 0)
            asked_by_links = stats.get('asked_by_links', 0)

            logger.info("")
            logger.info("=" * 80)
            if questions_created > 0:
                logger.success(f"Successfully imported {questions_created} questions")
                logger.success(f"Created {asked_by_links} MP links")
            else:
                logger.info("No new questions to import")
            logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        neo4j.close()
        logger.info(f"Completed at: {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
