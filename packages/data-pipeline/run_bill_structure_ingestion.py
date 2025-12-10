#!/usr/bin/env python3
"""Run bill structure ingestion from command line.

Usage:
    # Ingest a single bill
    python run_bill_structure_ingestion.py --session 44-1 --bill C-2

    # Ingest multiple bills
    python run_bill_structure_ingestion.py --session 44-1 --bill C-2 --bill C-3

    # Ingest all bills in a session (with optional limit)
    python run_bill_structure_ingestion.py --session 44-1 --all --limit 10

    # Use environment variables for Neo4j connection (recommended)
    NEO4J_URI=bolt://localhost:7687 NEO4J_USERNAME=neo4j NEO4J_PASSWORD=password \\
        python run_bill_structure_ingestion.py --session 44-1 --bill C-2
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger
from fedmcp_pipeline.ingest.bill_structure import (
    run_bill_structure_ingestion,
    ingest_bill_structure,
)


def main():
    parser = argparse.ArgumentParser(
        description="Ingest bill structure from Parliament.ca XML to Neo4j"
    )
    parser.add_argument(
        "--session",
        type=str,
        help="Parliamentary session (e.g., '44-1')",
    )
    parser.add_argument(
        "--bill",
        type=str,
        action="append",
        dest="bills",
        help="Bill number to ingest (can be specified multiple times)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Ingest all bills in the session",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of bills to process (for --all)",
    )
    parser.add_argument(
        "--version",
        type=int,
        default=1,
        help="Bill version to parse (1=first reading, default)",
    )
    parser.add_argument(
        "--government",
        action="store_true",
        help="Bill is a government bill (default: private member's bill)",
    )
    parser.add_argument(
        "--neo4j-uri",
        type=str,
        default=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        help="Neo4j connection URI",
    )
    parser.add_argument(
        "--neo4j-user",
        type=str,
        default=os.environ.get("NEO4J_USERNAME", "neo4j"),
        help="Neo4j username",
    )
    parser.add_argument(
        "--neo4j-password",
        type=str,
        default=os.environ.get("NEO4J_PASSWORD", ""),
        help="Neo4j password",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.session and not args.bills:
        parser.error("Must specify --session and/or --bill")

    if args.all and not args.session:
        parser.error("--all requires --session")

    if args.all and args.bills:
        parser.error("Cannot use --all with --bill")

    # Connect to Neo4j
    logger.info(f"Connecting to Neo4j at {args.neo4j_uri}...")
    neo4j = Neo4jClient(
        uri=args.neo4j_uri,
        user=args.neo4j_user,
        password=args.neo4j_password,
    )

    try:
        neo4j.test_connection()

        if args.all:
            # Ingest all bills in session
            results = run_bill_structure_ingestion(
                neo4j,
                session_str=args.session,
                limit=args.limit,
            )
        elif args.session and args.bills:
            # Ingest specific bills
            results = run_bill_structure_ingestion(
                neo4j,
                session_str=args.session,
                bill_numbers=args.bills,
            )
        elif args.bills:
            # Bills with embedded session (e.g., "44-1:C-2")
            results = run_bill_structure_ingestion(
                neo4j,
                bill_numbers=args.bills,
            )
        else:
            parser.error("Invalid argument combination")
            return 1

        # Print summary
        if "error" in results:
            logger.error(f"Error: {results['error']}")
            return 1

        logger.info("=" * 60)
        logger.info("INGESTION COMPLETE")
        logger.info("=" * 60)

        if "totals" in results:
            logger.info(f"Bills processed: {results.get('successful', 0)}/{results.get('total_bills', 0)}")
            logger.info("Node counts:")
            for key, value in results["totals"].items():
                logger.info(f"  {key}: {value}")

        return 0

    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

    finally:
        neo4j.close()


if __name__ == "__main__":
    sys.exit(main())
