#!/usr/bin/env python3
"""
Backfill Hansard Statement→MP Links for November 2025

This script re-links existing Hansard statements from November 2025 using the newly populated
MP.hansard_db_id field. It uses exact DbId matching for high accuracy.

Run after extract_hansard_dbids.py has populated the hansard_db_id values.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'packages' / 'data-pipeline'))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger


def backfill_hansard_links(neo4j: Neo4jClient, start_date: str = '2025-11-01', end_date: str = '2025-12-01') -> dict:
    """
    Backfill MP links for existing Hansard statements using hansard_db_id.

    Args:
        neo4j: Neo4j client
        start_date: Start date for backfill (ISO format)
        end_date: End date for backfill (ISO format)

    Returns:
        Dict with statistics
    """
    logger.info(f"Backfilling Hansard statements from {start_date} to {end_date}...")

    # Step 1: Count total statements in date range
    count_query = """
    MATCH (d:Document)
    WHERE d.date >= $start_date AND d.date < $end_date
    MATCH (s:Statement)-[:PART_OF]->(d)
    RETURN count(s) as total_statements, count(DISTINCT d) as total_documents
    """
    result = neo4j.run_query(count_query, {"start_date": start_date, "end_date": end_date})
    total_statements = result[0]['total_statements'] if result else 0
    total_documents = result[0]['total_documents'] if result else 0

    logger.info(f"Found {total_statements} statements across {total_documents} documents to backfill")

    if total_statements == 0:
        logger.warning("No statements found in date range")
        return {"total_statements": 0, "linked": 0, "spoke_at": 0}

    # Step 2: Remove existing MADE_BY relationships (to allow clean re-linking)
    clear_query = """
    MATCH (d:Document)
    WHERE d.date >= $start_date AND d.date < $end_date
    MATCH (s:Statement)-[:PART_OF]->(d)
    MATCH (s)-[r:MADE_BY]->(:MP)
    DELETE r
    RETURN count(r) as removed_links
    """
    result = neo4j.run_query(clear_query, {"start_date": start_date, "end_date": end_date})
    removed_links = result[0]['removed_links'] if result else 0
    logger.info(f"Removed {removed_links} existing MADE_BY links")

    # Step 3: Remove existing SPOKE_AT relationships
    clear_spoke_at = """
    MATCH (mp:MP)-[r:SPOKE_AT]->(d:Document)
    WHERE d.date >= $start_date AND d.date < $end_date
    DELETE r
    RETURN count(r) as removed_spoke_at
    """
    result = neo4j.run_query(clear_spoke_at, {"start_date": start_date, "end_date": end_date})
    removed_spoke_at = result[0]['removed_spoke_at'] if result else 0
    logger.info(f"Removed {removed_spoke_at} existing SPOKE_AT relationships")

    # Step 4: Link statements to MPs using hansard_db_id (exact matching)
    link_query = """
    MATCH (d:Document)
    WHERE d.date >= $start_date AND d.date < $end_date
    MATCH (s:Statement)-[:PART_OF]->(d)
    WHERE s.person_db_id IS NOT NULL
    MATCH (mp:MP {hansard_db_id: s.person_db_id})
    MERGE (s)-[:MADE_BY]->(mp)
    RETURN count(*) as linked_count
    """
    result = neo4j.run_query(link_query, {"start_date": start_date, "end_date": end_date})
    linked_count = result[0]['linked_count'] if result else 0
    logger.success(f"✓ Linked {linked_count} statements to MPs using hansard_db_id")

    # Step 5: Create SPOKE_AT relationships
    spoke_at_query = """
    MATCH (d:Document)
    WHERE d.date >= $start_date AND d.date < $end_date
    MATCH (s:Statement)-[:PART_OF]->(d)
    MATCH (s)-[:MADE_BY]->(mp:MP)
    MERGE (mp)-[r:SPOKE_AT]->(d)
    SET r.statement_id = s.id, r.person_db_id = s.person_db_id
    RETURN count(DISTINCT r) as spoke_at_count
    """
    result = neo4j.run_query(spoke_at_query, {"start_date": start_date, "end_date": end_date})
    spoke_at_count = result[0]['spoke_at_count'] if result else 0
    logger.success(f"✓ Created {spoke_at_count} SPOKE_AT relationships")

    return {
        "total_statements": total_statements,
        "total_documents": total_documents,
        "linked": linked_count,
        "spoke_at": spoke_at_count,
        "link_percentage": round(100.0 * linked_count / total_statements, 1) if total_statements > 0 else 0
    }


def verify_results(neo4j: Neo4jClient, start_date: str = '2025-11-01', end_date: str = '2025-12-01'):
    """
    Verify backfill results with detailed statistics.

    Args:
        neo4j: Neo4j client
        start_date: Start date for verification
        end_date: End date for verification
    """
    logger.info("Verifying backfill results...")

    # Get per-document statistics
    doc_stats_query = """
    MATCH (d:Document)
    WHERE d.date >= $start_date AND d.date < $end_date
    MATCH (s:Statement)-[:PART_OF]->(d)
    WITH d, count(s) as total
    OPTIONAL MATCH (s2:Statement)-[:PART_OF]->(d)
    OPTIONAL MATCH (s2)-[:MADE_BY]->(:MP)
    RETURN d.date as date, d.number as number, total, count(s2) as linked,
           round(100.0 * count(s2) / total, 1) as percentage
    ORDER BY d.date
    """
    results = neo4j.run_query(doc_stats_query, {"start_date": start_date, "end_date": end_date})

    logger.info("\nPer-document link statistics:")
    logger.info("=" * 80)
    for row in results:
        date = row['date']
        number = row['number'] or 'N/A'
        total = row['total']
        linked = row['linked']
        percentage = row['percentage']
        logger.info(f"  {date} {number:>8}: {linked:>4}/{total:>4} linked ({percentage:>5.1f}%)")
    logger.info("=" * 80)

    # Get unmatched speakers
    unmatched_query = """
    MATCH (d:Document)
    WHERE d.date >= $start_date AND d.date < $end_date
    MATCH (s:Statement)-[:PART_OF]->(d)
    WHERE NOT exists((s)-[:MADE_BY]->())
      AND s.who_en IS NOT NULL
      AND s.person_db_id IS NOT NULL
    RETURN DISTINCT s.who_en as speaker, s.person_db_id as db_id, count(*) as count
    ORDER BY count DESC
    LIMIT 20
    """
    results = neo4j.run_query(unmatched_query, {"start_date": start_date, "end_date": end_date})

    if results:
        logger.warning("\nTop unmatched speakers (with person_db_id):")
        logger.info("=" * 80)
        for row in results:
            speaker = row['speaker']
            db_id = row['db_id']
            count = row['count']
            logger.warning(f"  DbId={db_id}: {speaker} ({count} statements)")
        logger.info("=" * 80)
    else:
        logger.success("✓ All statements with person_db_id successfully linked!")


def main():
    """Main entry point."""
    logger.info("=" * 80)
    logger.info("HANSARD NOVEMBER BACKFILL - RE-LINK STATEMENTS")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("=" * 80)
    print()

    # Get Neo4j connection from environment
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://10.128.0.3:7687')
    neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD')

    if not neo4j_password:
        logger.error("NEO4J_PASSWORD environment variable not set")
        sys.exit(1)

    neo4j = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)

    try:
        # Backfill November 2025 statements
        stats = backfill_hansard_links(neo4j, start_date='2025-11-01', end_date='2025-12-01')

        # Verify results
        verify_results(neo4j, start_date='2025-11-01', end_date='2025-12-01')

        logger.info("=" * 80)
        logger.success(f"✅ Backfill complete!")
        logger.info(f"Documents: {stats['total_documents']}")
        logger.info(f"Total statements: {stats['total_statements']}")
        logger.info(f"Linked statements: {stats['linked']} ({stats['link_percentage']}%)")
        logger.info(f"SPOKE_AT relationships: {stats['spoke_at']}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Backfill failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        neo4j.close()


if __name__ == "__main__":
    main()
