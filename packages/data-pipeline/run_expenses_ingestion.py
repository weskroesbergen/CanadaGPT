#!/usr/bin/env python3
"""
MP Expenses Ingestion Cloud Run Job

This job imports MP and House Officer expense data from OurCommons Proactive Disclosure.
It's designed to be run as a Cloud Run job on a schedule or on-demand.

Features:
- Imports MP office expenses (salaries, travel, hospitality, contracts)
- Imports House Officer expenses (Speaker, Leaders, Whips, etc.)
- Fetches CSV data from OurCommons quarterly proactive disclosure
- Idempotent design: safe to run multiple times (skips existing expenses)
- Parameterizable fiscal year range for historical backfilling

Environment variables:
- NEO4J_URI: Neo4j connection URI (default: bolt://10.128.0.3:7687)
- NEO4J_USERNAME: Neo4j username (default: neo4j)
- NEO4J_PASSWORD: Neo4j password (required)

Usage:
  # Daily run (current fiscal year)
  python run_expenses_ingestion.py

  # Historical backfill
  python run_expenses_ingestion.py --fiscal-year-start 2020 --fiscal-year-end 2023

  # Single fiscal year
  python run_expenses_ingestion.py --fiscal-year-start 2024 --fiscal-year-end 2024
"""

import sys
import os
import argparse
from datetime import datetime
from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger
from fedmcp_pipeline.ingest.finances import ingest_financial_data


def main():
    """Run MP expenses ingestion job."""

    parser = argparse.ArgumentParser(description='Import MP and House Officer expenses')
    parser.add_argument(
        '--fiscal-year-start',
        type=int,
        default=datetime.now().year,
        help='Starting fiscal year (default: current year)'
    )
    parser.add_argument(
        '--fiscal-year-end',
        type=int,
        default=None,
        help='Ending fiscal year (default: same as start year)'
    )

    args = parser.parse_args()

    # Default end year to start year if not specified
    if args.fiscal_year_end is None:
        args.fiscal_year_end = args.fiscal_year_start

    logger.info("=" * 80)
    logger.info("MP EXPENSES INGESTION CLOUD RUN JOB - STARTING")
    logger.info("=" * 80)
    logger.info(f"Fiscal year range: FY {args.fiscal_year_start} to FY {args.fiscal_year_end}")
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
        logger.info("Running expenses ingestion...")
        logger.info("This will:")
        logger.info("  - Fetch MP office expense data from OurCommons Proactive Disclosure")
        logger.info("  - Fetch House Officer expense data (Speaker, Leaders, Whips, etc.)")
        logger.info("  - Create Expense nodes with INCURRED relationships to MPs")
        logger.info(f"  - Process {(args.fiscal_year_end - args.fiscal_year_start + 1) * 4} quarters")
        logger.info("  - Skip quarters that are not yet published (no error)")
        print()

        # Run ingestion
        stats = ingest_financial_data(
            neo4j_client=neo4j,
            fiscal_year_start=args.fiscal_year_start,
            fiscal_year_end=args.fiscal_year_end,
            batch_size=10000
        )

        print()
        mp_expenses = stats.get('mp_expenses', 0)
        officer_expenses = stats.get('officer_expenses', 0)
        total_expenses = mp_expenses + officer_expenses

        logger.success(f"✅ Successfully imported {mp_expenses:,} MP expense records")
        logger.success(f"✅ Successfully imported {officer_expenses:,} House Officer expense records")
        logger.success(f"✅ Total expenses imported: {total_expenses:,}")

        logger.info("=" * 80)
        logger.info("MP EXPENSES INGESTION CLOUD RUN JOB - COMPLETED")
        logger.info("=" * 80)
        print()

    except Exception as e:
        logger.error(f"Expenses ingestion job failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        neo4j.close()


if __name__ == "__main__":
    main()
