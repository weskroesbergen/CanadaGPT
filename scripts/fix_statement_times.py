#!/usr/bin/env python3
"""
Fix Statement.time field format to be valid ISO-8601 DateTime.

This script updates time values like "2025-11-05T10:00" to "2025-11-05T10:00:00"
to ensure they are valid Neo4j DateTime values.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'packages' / 'data-pipeline'))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger


def fix_time_formats(neo4j: Neo4jClient, document_id: int = None) -> int:
    """
    Fix Statement.time field format to include seconds.

    Args:
        neo4j: Neo4j client
        document_id: Optional specific document ID to fix (None = fix all)

    Returns:
        Number of statements updated
    """
    if document_id:
        logger.info(f"Fixing time formats for document {document_id}...")
    else:
        logger.info("Fixing time formats for all statements...")

    # Query to find statements with invalid time format (missing seconds)
    # Time values like "2025-11-05T10:00" need to become "2025-11-05T10:00:00"

    if document_id:
        query = """
        MATCH (s:Statement {document_id: $doc_id})
        WHERE s.time IS NOT NULL
        RETURN s.id as statement_id, s.time as old_time
        """
        params = {"doc_id": document_id}
    else:
        query = """
        MATCH (s:Statement)
        WHERE s.time IS NOT NULL
        RETURN s.id as statement_id, s.time as old_time
        LIMIT 10000
        """
        params = {}

    result = neo4j.run_query(query, params)

    logger.info(f"Found {len(result)} statements with time values")

    # Process and fix time values
    updates = []
    for row in result:
        statement_id = row['statement_id']
        old_time = row['old_time']

        # Convert to string if it's a datetime object
        if hasattr(old_time, 'isoformat'):
            # Already a valid datetime object, skip
            continue

        time_str = str(old_time)
        new_time = None

        # Check for malformed time with parentheses: "2025-11-05T(1020)"
        if 'T(' in time_str:
            date_part, time_part = time_str.split('T', 1)
            # Remove parentheses and parse HHMM format
            time_part = time_part.strip('()')
            if len(time_part) == 4 and time_part.isdigit():
                hour = time_part[:2]
                minute = time_part[2:]
                new_time = f"{date_part}T{hour}:{minute}:00"
                logger.debug(f"Will fix (parentheses): {time_str} → {new_time}")

        # Check if time string is missing seconds (e.g., "2025-11-05T10:00")
        elif 'T' in time_str:
            date_part, time_part = time_str.split('T', 1)
            # Count colons in time part
            if time_part.count(':') == 1:
                # Missing seconds, add ":00"
                new_time = f"{date_part}T{time_part}:00"
                logger.debug(f"Will fix (missing seconds): {time_str} → {new_time}")

        if new_time:
            updates.append({
                "statement_id": statement_id,
                "new_time": new_time
            })

    logger.info(f"Need to fix {len(updates)} statements")

    if not updates:
        logger.success("✓ All time values are already valid!")
        return 0

    # Batch update statements
    update_query = """
    UNWIND $updates AS update
    MATCH (s:Statement {id: update.statement_id})
    SET s.time = datetime(update.new_time)
    RETURN count(*) as updated_count
    """

    result = neo4j.run_query(update_query, {"updates": updates})
    updated_count = result[0]['updated_count'] if result else 0

    logger.success(f"✓ Updated {updated_count} statement time values")
    return updated_count


def main():
    """Main entry point."""
    logger.info("=" * 80)
    logger.info("FIX STATEMENT TIME FIELD FORMAT")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("=" * 80)
    print()

    # Get Neo4j connection from environment
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD')

    if not neo4j_password:
        logger.error("NEO4J_PASSWORD environment variable not set")
        sys.exit(1)

    neo4j = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)

    try:
        # Fix all documents with malformed time values
        logger.info("Fixing all documents with malformed time values...")
        total_updated = fix_time_formats(neo4j)

        logger.info("=" * 80)
        logger.success(f"✅ Fix complete! Updated {total_updated} statements")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Fix failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        neo4j.close()


if __name__ == "__main__":
    main()
