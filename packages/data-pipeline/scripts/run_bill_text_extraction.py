#!/usr/bin/env python3
"""
Extract and store full narrative text for bills from LEGISinfo XML.

This script automates the extraction of continuous, readable bill text
and stores it in Neo4j for display in the frontend "Full Text" tab.

Usage:
    # Single bill
    python scripts/run_bill_text_extraction.py --session 45-1 --bill C-12

    # All bills in a session
    python scripts/run_bill_text_extraction.py --session 45-1 --all

    # Specific list
    python scripts/run_bill_text_extraction.py --session 45-1 --bills C-12,C-13,C-234

Examples:
    # Extract C-12 from current parliament (testing)
    python scripts/run_bill_text_extraction.py --session 45-1 --bill C-12

    # Backfill all government bills in 45-1
    python scripts/run_bill_text_extraction.py --session 45-1 --all

    # Extract specific bills with custom Neo4j connection
    NEO4J_URI=bolt://10.128.0.3:7687 \\
    NEO4J_USERNAME=neo4j \\
    NEO4J_PASSWORD=canadagpt2024 \\
    python scripts/run_bill_text_extraction.py --session 45-1 --bills C-2,C-3,C-12
"""

import argparse
import os
import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "fedmcp" / "src"))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.ingest.bill_structure import ingest_bill_structure
from fedmcp_pipeline.utils.progress import logger


def get_bills_from_neo4j(neo4j_client: Neo4jClient, session: str) -> list:
    """Query Neo4j for all bills in a session.

    Args:
        neo4j_client: Neo4j client instance
        session: Session string (e.g., "45-1")

    Returns:
        List of bill numbers
    """
    logger.info(f"Querying Neo4j for bills in session {session}...")
    result = neo4j_client.run_query("""
        MATCH (b:Bill {session: $session})
        RETURN b.number as number
        ORDER BY b.number
    """, {"session": session})

    bills = [row["number"] for row in result]
    logger.info(f"Found {len(bills)} bills in session {session}")
    return bills


def is_government_bill(bill_number: str) -> bool:
    """Determine if a bill is a government bill.

    Args:
        bill_number: Bill number (e.g., "C-12", "C-234", "S-5")

    Returns:
        True for government bills, False for private member's bills

    Note:
        Government bills: C-1 to C-200 (House) or S-1 to S-200 (Senate)
        Private member's bills: C-201+ or S-201+
    """
    bill_number = bill_number.upper()

    # Senate bills
    if bill_number.startswith("S-"):
        try:
            number = int(bill_number.split("-")[1])
            return number <= 200
        except (IndexError, ValueError):
            return False

    # House bills
    if bill_number.startswith("C-"):
        try:
            number = int(bill_number.split("-")[1])
            return number <= 200
        except (IndexError, ValueError):
            return False

    return False


def extract_bill_text(
    neo4j_client: Neo4jClient,
    parliament: int,
    session: int,
    bill_number: str,
    verbose: bool = True,
) -> dict:
    """Extract full text for a single bill.

    Args:
        neo4j_client: Neo4j client instance
        parliament: Parliament number
        session: Session number
        bill_number: Bill number
        verbose: Print detailed logs

    Returns:
        Result dictionary with extraction status
    """
    is_gov = is_government_bill(bill_number)

    try:
        # Use ingest_bill_structure with include_full_text=True
        # Note: This will also re-ingest structure if not present
        result = ingest_bill_structure(
            neo4j_client,
            parliament=parliament,
            session=session,
            bill_number=bill_number,
            version=1,  # Default to first reading version
            is_government=is_gov,
            include_all_versions=False,  # Don't need all versions for full text
            include_full_text=True,  # Enable full text extraction
        )

        return result

    except Exception as e:
        logger.error(f"❌ {bill_number}: Extraction failed - {e}")
        return {"error": str(e), "bill": bill_number}


def main():
    """Main entry point for bill text extraction script."""
    parser = argparse.ArgumentParser(
        description="Extract full text for Canadian bills from LEGISinfo XML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--session", required=True, help="Session (e.g., 45-1)")
    parser.add_argument("--bill", help="Single bill number (e.g., C-12)")
    parser.add_argument("--bills", help="Comma-separated bill numbers (e.g., C-12,C-13,C-234)")
    parser.add_argument("--all", action="store_true", help="Process all bills in session")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Parse session
    try:
        parliament, session_num = map(int, args.session.split("-"))
    except ValueError:
        logger.error(f"Invalid session format: {args.session}. Use format like '45-1'")
        return 1

    # Get bill list
    if args.bill:
        bills = [args.bill.upper()]
    elif args.bills:
        bills = [b.strip().upper() for b in args.bills.split(",")]
    elif args.all:
        # Query Neo4j for all bills in session
        neo4j_temp = Neo4jClient(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            user=os.getenv("NEO4J_USERNAME", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password"),
        )
        bills = get_bills_from_neo4j(neo4j_temp, args.session)
        if not bills:
            logger.error(f"No bills found in session {args.session}")
            return 1
    else:
        logger.error("Must specify --bill, --bills, or --all")
        parser.print_help()
        return 1

    logger.info(f"\n{'='*70}")
    logger.info(f"Bill Text Extraction - Session {args.session}")
    logger.info(f"{'='*70}\n")
    logger.info(f"Processing {len(bills)} bills: {', '.join(bills)}\n")

    # Connect to Neo4j
    neo4j = Neo4jClient(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("NEO4J_USERNAME", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password"),
    )

    # Track results
    results = {
        "total": len(bills),
        "successful_en": 0,
        "successful_fr": 0,
        "failed": 0,
        "errors": [],
    }

    # Process each bill
    for i, bill_number in enumerate(bills, 1):
        logger.info(f"\n{'='*70}")
        logger.info(f"[{i}/{len(bills)}] Bill {bill_number} ({args.session})")
        logger.info(f"{'='*70}")

        result = extract_bill_text(
            neo4j,
            parliament=parliament,
            session=session_num,
            bill_number=bill_number,
            verbose=args.verbose,
        )

        # Track results
        if result.get("error"):
            results["failed"] += 1
            results["errors"].append((bill_number, result["error"]))
        else:
            if result.get("full_text_en_extracted"):
                results["successful_en"] += 1
            if result.get("full_text_fr_extracted"):
                results["successful_fr"] += 1

            # Log success
            status_en = "✅" if result.get("full_text_en_extracted") else "❌"
            status_fr = "✅" if result.get("full_text_fr_extracted") else "❌"
            logger.info(f"\nExtraction Summary for {bill_number}:")
            logger.info(f"  English: {status_en}")
            logger.info(f"  French:  {status_fr}")

    # Print final summary
    logger.info(f"\n{'='*70}")
    logger.info(f"Final Summary")
    logger.info(f"{'='*70}")
    logger.info(f"Total bills:        {results['total']}")
    logger.info(f"English extracted:  {results['successful_en']} ({results['successful_en']/results['total']*100:.1f}%)")
    logger.info(f"French extracted:   {results['successful_fr']} ({results['successful_fr']/results['total']*100:.1f}%)")
    logger.info(f"Failed:             {results['failed']}")

    if results["errors"]:
        logger.info(f"\nErrors:")
        for bill, error in results["errors"]:
            logger.error(f"  {bill}: {error}")

    # Exit code
    if results["failed"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
