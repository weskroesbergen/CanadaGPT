#!/usr/bin/env python3
"""Backfill cross-references (MENTIONS relationships) for existing statements.

This script processes existing Statement nodes to extract entity mentions
and create MENTIONS relationships to Bills, MPs, Committees, etc.

Usage:
    # Process all statements (with batch processing)
    python scripts/backfill_cross_references.py

    # Process statements from a specific date range
    python scripts/backfill_cross_references.py --from-date 2024-01-01 --to-date 2024-12-31

    # Process only statements without existing MENTIONS relationships
    python scripts/backfill_cross_references.py --unprocessed-only

    # Dry run (don't create relationships, just log what would be created)
    python scripts/backfill_cross_references.py --dry-run

    # Limit processing for testing
    python scripts/backfill_cross_references.py --limit 100

Environment Variables:
    NEO4J_URI - Neo4j connection URI
    NEO4J_USERNAME - Neo4j username
    NEO4J_PASSWORD - Neo4j password
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger, ProgressTracker
from fedmcp_pipeline.ingest.cross_reference_agent import CrossReferenceAgent, EntityType


def get_statements_to_process(
    neo4j: Neo4jClient,
    *,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    unprocessed_only: bool = False,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Fetch statements to process from Neo4j.

    Args:
        neo4j: Neo4j client
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        unprocessed_only: Only fetch statements without MENTIONS relationships
        limit: Maximum number of statements to return
        offset: Offset for pagination

    Returns:
        List of statement dicts with id, content_en, document_date
    """
    # Build WHERE clauses
    where_clauses = []
    params: Dict[str, Any] = {}

    if from_date:
        where_clauses.append("s.time >= datetime($from_date)")
        params["from_date"] = from_date

    if to_date:
        where_clauses.append("s.time <= datetime($to_date)")
        params["to_date"] = to_date

    if unprocessed_only:
        where_clauses.append("NOT (s)-[:MENTIONS]->()")

    where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

    query = f"""
    MATCH (s:Statement)
    WHERE {where_clause}
    AND s.content_en IS NOT NULL
    AND length(s.content_en) > 50
    WITH s
    ORDER BY s.time DESC
    SKIP $offset
    LIMIT $limit
    OPTIONAL MATCH (s)-[:PART_OF]->(d:Document)
    RETURN s.id AS id,
           s.content_en AS content_en,
           s.h1_en AS h1_en,
           s.h2_en AS h2_en,
           d.date AS document_date
    """

    params["offset"] = offset
    params["limit"] = limit or 1000

    return neo4j.run_query(query, params)


def get_total_statement_count(
    neo4j: Neo4jClient,
    *,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    unprocessed_only: bool = False,
) -> int:
    """Get total count of statements matching criteria."""
    where_clauses = []
    params: Dict[str, Any] = {}

    if from_date:
        where_clauses.append("s.time >= datetime($from_date)")
        params["from_date"] = from_date

    if to_date:
        where_clauses.append("s.time <= datetime($to_date)")
        params["to_date"] = to_date

    if unprocessed_only:
        where_clauses.append("NOT (s)-[:MENTIONS]->()")

    where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

    query = f"""
    MATCH (s:Statement)
    WHERE {where_clause}
    AND s.content_en IS NOT NULL
    AND length(s.content_en) > 50
    RETURN count(s) AS total
    """

    result = neo4j.run_query(query, params)
    return result[0]["total"] if result else 0


def detect_debate_stage(h1: Optional[str], h2: Optional[str]) -> Optional[str]:
    """Detect debate stage from statement headers.

    Args:
        h1: First level heading (e.g., "Government Orders")
        h2: Second level heading (e.g., "Second Reading")

    Returns:
        Debate stage: "1", "2", "3", "committee", or None
    """
    headings = f"{h1 or ''} {h2 or ''}".lower()

    if "first reading" in headings:
        return "1"
    if "second reading" in headings:
        return "2"
    if "third reading" in headings:
        return "3"
    if "committee of the whole" in headings or "report stage" in headings:
        return "committee"

    return None


def process_statement_batch(
    neo4j: Neo4jClient,
    agent: CrossReferenceAgent,
    statements: List[Dict[str, Any]],
    *,
    dry_run: bool = False,
) -> Dict[str, int]:
    """Process a batch of statements.

    Args:
        neo4j: Neo4j client
        agent: Cross-reference agent
        statements: List of statement dicts
        dry_run: If True, don't create relationships

    Returns:
        Statistics dict
    """
    stats = {
        "processed": 0,
        "with_mentions": 0,
        "relationships_created": 0,
        "by_type": {
            "bill": 0,
            "mp": 0,
            "committee": 0,
            "petition": 0,
            "vote": 0,
        },
    }

    for stmt in statements:
        statement_id = stmt["id"]
        content = stmt.get("content_en", "")
        h1 = stmt.get("h1_en")
        h2 = stmt.get("h2_en")

        # Extract mentions
        mentions = agent.extract_mentions(content, statement_id)

        stats["processed"] += 1

        if mentions:
            stats["with_mentions"] += 1

            # Count by type
            for mention in mentions:
                if mention.normalized_id:
                    type_key = mention.entity_type.value
                    if type_key in stats["by_type"]:
                        stats["by_type"][type_key] += 1

            # Create relationships (unless dry run)
            if not dry_run:
                debate_stage = detect_debate_stage(h1, h2)
                properties = {"debate_stage": debate_stage} if debate_stage else {}

                created = agent.create_mention_relationships(
                    statement_id,
                    "Statement",
                    mentions,
                    properties=properties,
                )
                stats["relationships_created"] += created

    return stats


def run_backfill(
    neo4j: Neo4jClient,
    *,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    unprocessed_only: bool = False,
    limit: Optional[int] = None,
    batch_size: int = 500,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Run the cross-reference backfill process.

    Args:
        neo4j: Neo4j client
        from_date: Start date filter
        to_date: End date filter
        unprocessed_only: Only process statements without MENTIONS relationships
        limit: Total limit on statements to process
        batch_size: Batch size for processing
        dry_run: If True, don't create relationships

    Returns:
        Overall statistics
    """
    logger.info("=" * 60)
    logger.info("CROSS-REFERENCE BACKFILL")
    logger.info("=" * 60)

    if dry_run:
        logger.info("DRY RUN MODE - no relationships will be created")

    # Get total count
    total = get_total_statement_count(
        neo4j,
        from_date=from_date,
        to_date=to_date,
        unprocessed_only=unprocessed_only,
    )

    if limit:
        total = min(total, limit)

    logger.info(f"Found {total:,} statements to process")

    if total == 0:
        return {"total": 0, "processed": 0}

    # Initialize agent
    agent = CrossReferenceAgent(neo4j, resolve_entities=True)

    # Overall statistics
    overall_stats = {
        "total": total,
        "processed": 0,
        "with_mentions": 0,
        "relationships_created": 0,
        "by_type": {
            "bill": 0,
            "mp": 0,
            "committee": 0,
            "petition": 0,
            "vote": 0,
        },
    }

    # Process in batches
    progress = ProgressTracker(total=total, desc="Processing statements", unit="stmts")
    offset = 0
    remaining = total

    while remaining > 0:
        current_batch_size = min(batch_size, remaining)

        statements = get_statements_to_process(
            neo4j,
            from_date=from_date,
            to_date=to_date,
            unprocessed_only=unprocessed_only,
            limit=current_batch_size,
            offset=offset,
        )

        if not statements:
            break

        batch_stats = process_statement_batch(neo4j, agent, statements, dry_run=dry_run)

        # Update overall stats
        overall_stats["processed"] += batch_stats["processed"]
        overall_stats["with_mentions"] += batch_stats["with_mentions"]
        overall_stats["relationships_created"] += batch_stats["relationships_created"]
        for type_key in overall_stats["by_type"]:
            overall_stats["by_type"][type_key] += batch_stats["by_type"].get(type_key, 0)

        progress.update(len(statements))
        offset += len(statements)
        remaining -= len(statements)

        # Clear agent caches periodically to avoid memory buildup
        if offset % 5000 == 0:
            agent.clear_caches()

    progress.close()

    # Print summary
    logger.info("=" * 60)
    logger.info("BACKFILL COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total statements processed: {overall_stats['processed']:,}")
    logger.info(f"Statements with mentions: {overall_stats['with_mentions']:,}")
    logger.info(f"Relationships created: {overall_stats['relationships_created']:,}")
    logger.info("")
    logger.info("Mentions by type:")
    for type_key, count in overall_stats["by_type"].items():
        logger.info(f"  {type_key}: {count:,}")

    return overall_stats


def main():
    parser = argparse.ArgumentParser(
        description="Backfill cross-references (MENTIONS relationships) for statements"
    )
    parser.add_argument(
        "--from-date",
        type=str,
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--to-date",
        type=str,
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--unprocessed-only",
        action="store_true",
        help="Only process statements without existing MENTIONS relationships",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit total number of statements to process",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Batch size for processing (default: 500)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't create relationships, just log what would be created",
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

    # Connect to Neo4j
    logger.info(f"Connecting to Neo4j at {args.neo4j_uri}...")
    neo4j = Neo4jClient(
        uri=args.neo4j_uri,
        user=args.neo4j_user,
        password=args.neo4j_password,
    )

    try:
        neo4j.test_connection()

        results = run_backfill(
            neo4j,
            from_date=args.from_date,
            to_date=args.to_date,
            unprocessed_only=args.unprocessed_only,
            limit=args.limit,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )

        return 0 if results.get("processed", 0) >= 0 else 1

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        neo4j.close()


if __name__ == "__main__":
    sys.exit(main())
