#!/usr/bin/env python3
"""
Backfill Committee Evidence from Historical Evidence IDs

This script uses the backed-up evidence_id mappings to import historical
committee testimony that was recorded before the schema migration.

Usage:
    python scripts/backfill_committee_evidence.py [--limit N] [--session SESSION]

Examples:
    # Backfill all historical evidence
    python scripts/backfill_committee_evidence.py

    # Backfill only 45-1 session
    python scripts/backfill_committee_evidence.py --session 45-1

    # Test with 10 meetings
    python scripts/backfill_committee_evidence.py --limit 10
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Add packages to path
PIPELINE_PATH = Path(__file__).parent.parent
sys.path.insert(0, str(PIPELINE_PATH))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger, ProgressTracker
from fedmcp_pipeline.ingest.committee_evidence_xml_import import CommitteeEvidenceXMLImporter


def load_evidence_mappings(backup_file: str) -> List[Dict[str, Any]]:
    """Load evidence ID mappings from backup file."""
    logger.info(f"Loading evidence mappings from: {backup_file}")

    with open(backup_file, 'r') as f:
        mappings = json.load(f)

    logger.info(f"Loaded {len(mappings):,} meeting mappings")
    return mappings


def find_committee_for_evidence(
    neo4j: Neo4jClient,
    evidence_id: int,
    meeting_number: int,
    session_id: str
) -> str:
    """
    Try to find the committee code for a meeting.

    Strategy:
    1. Look for existing Meeting with same number/session (from daily-import)
    2. Query OpenParliament API as fallback
    """
    # Try to find matching meeting in Neo4j (from daily-import)
    query = """
        MATCH (c:Committee)-[:HELD_MEETING]->(m:Meeting)
        WHERE m.number = $meeting_number
        AND m.session_id = $session_id
        RETURN c.code as committee_code
        LIMIT 1
    """

    result = neo4j.run_query(query, {
        'meeting_number': meeting_number,
        'session_id': session_id
    })

    if result and len(result) > 0:
        return result[0]['committee_code']

    # Could add OpenParliament API lookup here as fallback
    return None


def backfill_evidence(
    neo4j: Neo4jClient,
    mappings: List[Dict[str, Any]],
    limit: int = None,
    session_filter: str = None
) -> Dict[str, int]:
    """
    Backfill historical committee evidence.

    Args:
        neo4j: Neo4j client
        mappings: List of evidence ID mappings
        limit: Optional limit on number to process
        session_filter: Optional session ID to filter (e.g., '45-1')

    Returns:
        Dict with import statistics
    """
    stats = {
        'total': len(mappings),
        'processed': 0,
        'imported': 0,
        'skipped_no_committee': 0,
        'skipped_exists': 0,
        'errors': 0
    }

    # Filter by session if specified
    if session_filter:
        mappings = [m for m in mappings if m.get('session_id') == session_filter]
        logger.info(f"Filtered to {len(mappings)} meetings in session {session_filter}")
        stats['total'] = len(mappings)

    # Apply limit
    if limit:
        mappings = mappings[:limit]
        logger.info(f"Limited to {limit} meetings")
        stats['total'] = len(mappings)

    # Sort by date descending (newest first)
    mappings = sorted(mappings, key=lambda m: m.get('date', ''), reverse=True)

    logger.info(f"Starting backfill of {len(mappings):,} meetings...")
    print()

    importer = CommitteeEvidenceXMLImporter(neo4j)
    tracker = ProgressTracker(total=len(mappings), desc="Backfilling evidence")

    for mapping in mappings:
        stats['processed'] += 1
        tracker.update(1)

        evidence_id = mapping.get('evidence_id')
        meeting_number = mapping.get('meeting_number')
        session_id = mapping.get('session_id')
        date = mapping.get('date')

        if not evidence_id or not meeting_number or not session_id:
            logger.warning(f"Skipping incomplete mapping: {mapping}")
            stats['errors'] += 1
            continue

        # Try to find committee code
        committee_code = find_committee_for_evidence(
            neo4j, evidence_id, meeting_number, session_id
        )

        if not committee_code:
            logger.debug(f"No committee found for meeting {meeting_number} ({session_id})")
            stats['skipped_no_committee'] += 1
            continue

        try:
            # Check if evidence already exists
            check_query = """
                MATCH (e:CommitteeEvidence)
                WHERE e.evidence_id = $evidence_id
                RETURN e.id as id
            """
            existing = neo4j.run_query(check_query, {'evidence_id': evidence_id})

            if existing and len(existing) > 0:
                logger.debug(f"Evidence {evidence_id} already exists, skipping")
                stats['skipped_exists'] += 1
                continue

            # Import evidence for this meeting
            # The importer will fetch from DocumentViewer XML using committee_code + meeting_number
            result = importer.import_evidence_for_meetings(
                committee_code=committee_code,
                meeting_numbers=[meeting_number],
                skip_existing=True
            )

            if result['meetings'] > 0:
                stats['imported'] += 1
                logger.success(f"✓ Imported {committee_code} meeting {meeting_number} ({date})")

        except Exception as e:
            logger.error(f"Error importing evidence {evidence_id}: {e}")
            stats['errors'] += 1

    tracker.close()
    return stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Backfill historical committee evidence')
    parser.add_argument('--limit', type=int, help='Limit number of meetings to process')
    parser.add_argument('--session', type=str, help='Filter to specific session (e.g., 45-1)')
    parser.add_argument(
        '--backup-file',
        type=str,
        default='packages/data-pipeline/backups/committee_evidence_backup_*.json',
        help='Path to backup JSON file'
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("COMMITTEE EVIDENCE BACKFILL SCRIPT")
    logger.info("=" * 80)
    print()

    # Find backup file
    backup_file = None
    if '*' in args.backup_file:
        # Find most recent backup
        import glob
        backups = glob.glob(args.backup_file)
        if backups:
            backup_file = sorted(backups)[-1]  # Most recent
    else:
        backup_file = args.backup_file

    if not backup_file or not Path(backup_file).exists():
        logger.error(f"Backup file not found: {args.backup_file}")
        logger.info("Create backup with: packages/data-pipeline/scripts/extract_evidence_mappings.py")
        sys.exit(1)

    # Load mappings
    mappings = load_evidence_mappings(backup_file)

    # Connect to Neo4j
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://10.128.0.3:7687')
    neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD')

    if not neo4j_password:
        logger.error("NEO4J_PASSWORD environment variable not set")
        sys.exit(1)

    neo4j = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)

    try:
        # Run backfill
        stats = backfill_evidence(
            neo4j=neo4j,
            mappings=mappings,
            limit=args.limit,
            session_filter=args.session
        )

        # Print summary
        print()
        logger.info("=" * 80)
        logger.info("BACKFILL COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Total mappings: {stats['total']:,}")
        logger.info(f"Processed: {stats['processed']:,}")
        logger.success(f"✅ Imported: {stats['imported']:,}")
        logger.info(f"Skipped (no committee): {stats['skipped_no_committee']:,}")
        logger.info(f"Skipped (already exists): {stats['skipped_exists']:,}")
        if stats['errors'] > 0:
            logger.warning(f"⚠️  Errors: {stats['errors']:,}")

    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        neo4j.close()


if __name__ == "__main__":
    main()
