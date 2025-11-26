#!/usr/bin/env python3
"""
Discover Parliament and Session data coverage in production Neo4j.

This script queries the production database to find:
- Earliest/latest parliament numbers
- All unique parliament/session combinations
- Count of data per parliament/session
- Date ranges for our data

Run: python3 scripts/discover_parliament_data_coverage.py
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'packages' / 'data-pipeline'))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger


def analyze_bills(neo4j: Neo4jClient) -> Dict[str, Any]:
    """Analyze Bill nodes for parliament/session coverage."""
    logger.info("Analyzing Bill nodes...")

    # Get parliament range
    range_query = """
        MATCH (b:Bill)
        WHERE b.parliament IS NOT NULL
        RETURN MIN(b.parliament) AS min_parliament,
               MAX(b.parliament) AS max_parliament,
               count(*) AS total_bills
    """
    range_result = neo4j.run_query(range_query)

    # Get unique sessions
    sessions_query = """
        MATCH (b:Bill)
        WHERE b.session IS NOT NULL
        RETURN DISTINCT b.session AS session_id
        ORDER BY session_id
    """
    sessions_result = neo4j.run_query(sessions_query)

    # Get counts per parliament
    parliament_query = """
        MATCH (b:Bill)
        WHERE b.parliament IS NOT NULL
        RETURN b.parliament AS parliament,
               count(*) AS bill_count
        ORDER BY parliament
    """
    parliament_result = neo4j.run_query(parliament_query)

    # Get counts per session
    session_count_query = """
        MATCH (b:Bill)
        WHERE b.session IS NOT NULL
        RETURN b.session AS session_id,
               count(*) AS bill_count
        ORDER BY session_id
    """
    session_count_result = neo4j.run_query(session_count_query)

    return {
        'min_parliament': range_result[0]['min_parliament'] if range_result else None,
        'max_parliament': range_result[0]['max_parliament'] if range_result else None,
        'total_bills': range_result[0]['total_bills'] if range_result else 0,
        'unique_sessions': [row['session_id'] for row in sessions_result],
        'by_parliament': {row['parliament']: row['bill_count'] for row in parliament_result},
        'by_session': {row['session_id']: row['bill_count'] for row in session_count_result}
    }


def analyze_votes(neo4j: Neo4jClient) -> Dict[str, Any]:
    """Analyze Vote nodes for parliament/session coverage."""
    logger.info("Analyzing Vote nodes...")

    # Get parliament range
    range_query = """
        MATCH (v:Vote)
        WHERE v.parliament_number IS NOT NULL
        RETURN MIN(v.parliament_number) AS min_parliament,
               MAX(v.parliament_number) AS max_parliament,
               count(*) AS total_votes
    """
    range_result = neo4j.run_query(range_query)

    # Get unique sessions
    sessions_query = """
        MATCH (v:Vote)
        WHERE v.parliament_number IS NOT NULL AND v.session_number IS NOT NULL
        RETURN DISTINCT toString(v.parliament_number) + '-' + toString(v.session_number) AS session_id
        ORDER BY session_id
    """
    sessions_result = neo4j.run_query(sessions_query)

    # Get counts per parliament
    parliament_query = """
        MATCH (v:Vote)
        WHERE v.parliament_number IS NOT NULL
        RETURN v.parliament_number AS parliament,
               count(*) AS vote_count
        ORDER BY parliament
    """
    parliament_result = neo4j.run_query(parliament_query)

    return {
        'min_parliament': range_result[0]['min_parliament'] if range_result else None,
        'max_parliament': range_result[0]['max_parliament'] if range_result else None,
        'total_votes': range_result[0]['total_votes'] if range_result else 0,
        'unique_sessions': [row['session_id'] for row in sessions_result],
        'by_parliament': {row['parliament']: row['vote_count'] for row in parliament_result}
    }


def analyze_documents(neo4j: Neo4jClient) -> Dict[str, Any]:
    """Analyze Document nodes (Hansard) for parliament/session coverage."""
    logger.info("Analyzing Document nodes (Hansard)...")

    # Get parliament range
    range_query = """
        MATCH (d:Document)
        WHERE d.parliament_number IS NOT NULL
        RETURN MIN(d.parliament_number) AS min_parliament,
               MAX(d.parliament_number) AS max_parliament,
               count(*) AS total_documents,
               MIN(d.date) AS earliest_date,
               MAX(d.date) AS latest_date
    """
    range_result = neo4j.run_query(range_query)

    # Get unique sessions
    sessions_query = """
        MATCH (d:Document)
        WHERE d.parliament_number IS NOT NULL AND d.session_number IS NOT NULL
        RETURN DISTINCT toString(d.parliament_number) + '-' + toString(d.session_number) AS session_id
        ORDER BY session_id
    """
    sessions_result = neo4j.run_query(sessions_query)

    # Get counts per parliament
    parliament_query = """
        MATCH (d:Document)
        WHERE d.parliament_number IS NOT NULL
        RETURN d.parliament_number AS parliament,
               count(*) AS document_count
        ORDER BY parliament
    """
    parliament_result = neo4j.run_query(parliament_query)

    return {
        'min_parliament': range_result[0]['min_parliament'] if range_result else None,
        'max_parliament': range_result[0]['max_parliament'] if range_result else None,
        'total_documents': range_result[0]['total_documents'] if range_result else 0,
        'earliest_date': range_result[0]['earliest_date'] if range_result else None,
        'latest_date': range_result[0]['latest_date'] if range_result else None,
        'unique_sessions': [row['session_id'] for row in sessions_result],
        'by_parliament': {row['parliament']: row['document_count'] for row in parliament_result}
    }


def analyze_committee_evidence(neo4j: Neo4jClient) -> Dict[str, Any]:
    """Analyze CommitteeEvidence nodes for parliament/session coverage."""
    logger.info("Analyzing CommitteeEvidence nodes...")

    # Get parliament range
    range_query = """
        MATCH (ce:CommitteeEvidence)
        WHERE ce.parliament_number IS NOT NULL
        RETURN MIN(ce.parliament_number) AS min_parliament,
               MAX(ce.parliament_number) AS max_parliament,
               count(*) AS total_evidence
    """
    range_result = neo4j.run_query(range_query)

    # Get unique sessions
    sessions_query = """
        MATCH (ce:CommitteeEvidence)
        WHERE ce.parliament_number IS NOT NULL AND ce.session_number IS NOT NULL
        RETURN DISTINCT toString(ce.parliament_number) + '-' + toString(ce.session_number) AS session_id
        ORDER BY session_id
    """
    sessions_result = neo4j.run_query(sessions_query)

    return {
        'min_parliament': range_result[0]['min_parliament'] if range_result else None,
        'max_parliament': range_result[0]['max_parliament'] if range_result else None,
        'total_evidence': range_result[0]['total_evidence'] if range_result else 0,
        'unique_sessions': [row['session_id'] for row in sessions_result]
    }


def aggregate_all_sessions(bills: Dict, votes: Dict, documents: Dict, evidence: Dict) -> List[str]:
    """Aggregate all unique sessions across all node types."""
    all_sessions = set()
    all_sessions.update(bills.get('unique_sessions', []))
    all_sessions.update(votes.get('unique_sessions', []))
    all_sessions.update(documents.get('unique_sessions', []))
    all_sessions.update(evidence.get('unique_sessions', []))

    # Sort sessions properly (35-1, 35-2, 36-1, etc.)
    def session_sort_key(session_id):
        try:
            parl, sess = session_id.split('-')
            return (int(parl), int(sess))
        except:
            return (0, 0)

    return sorted(list(all_sessions), key=session_sort_key)


def print_summary(bills: Dict, votes: Dict, documents: Dict, evidence: Dict):
    """Print formatted summary of data coverage."""
    print("\n" + "=" * 80)
    print("PARLIAMENT AND SESSION DATA COVERAGE REPORT")
    print("=" * 80)

    # Overall ranges
    print("\n📊 OVERALL COVERAGE:")
    print(f"   Bills:              Parliaments {bills['min_parliament']}-{bills['max_parliament']} ({bills['total_bills']:,} bills)")
    print(f"   Votes:              Parliaments {votes['min_parliament']}-{votes['max_parliament']} ({votes['total_votes']:,} votes)")
    print(f"   Hansard Debates:    Parliaments {documents['min_parliament']}-{documents['max_parliament']} ({documents['total_documents']:,} documents)")
    print(f"   Committee Evidence: Parliaments {evidence['min_parliament']}-{evidence['max_parliament']} ({evidence['total_evidence']:,} evidence)")

    # Date ranges
    if documents['earliest_date'] and documents['latest_date']:
        print(f"\n📅 DATE RANGE (Hansard):")
        print(f"   Earliest: {documents['earliest_date']}")
        print(f"   Latest:   {documents['latest_date']}")

    # All unique sessions
    all_sessions = aggregate_all_sessions(bills, votes, documents, evidence)
    print(f"\n📋 UNIQUE SESSIONS FOUND: {len(all_sessions)}")
    print(f"   Sessions: {', '.join(all_sessions)}")

    # Per-parliament breakdown
    print(f"\n📈 DATA BY PARLIAMENT:")
    all_parliaments = set()
    all_parliaments.update(bills['by_parliament'].keys())
    all_parliaments.update(votes['by_parliament'].keys())
    all_parliaments.update(documents['by_parliament'].keys())

    for parl in sorted(all_parliaments):
        bill_count = bills['by_parliament'].get(parl, 0)
        vote_count = votes['by_parliament'].get(parl, 0)
        doc_count = documents['by_parliament'].get(parl, 0)
        print(f"   Parliament {parl:2d}: {bill_count:4d} bills, {vote_count:4d} votes, {doc_count:4d} debates")

    # Session recommendations
    print(f"\n💡 RECOMMENDATION:")
    print(f"   Create Parliament nodes: 1-45 (all historical parliaments)")
    print(f"   Create Session nodes: {all_sessions[0]} through {all_sessions[-1]} (where we have data)")
    print(f"   Total sessions to create: {len(all_sessions)}")

    print("\n" + "=" * 80)


def main():
    """Main entry point."""
    logger.info("=" * 80)
    logger.info("DISCOVERING PARLIAMENT AND SESSION DATA COVERAGE")
    logger.info("=" * 80)

    # Connect to production Neo4j
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://10.128.0.3:7687')
    neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD')

    if not neo4j_password:
        logger.error("NEO4J_PASSWORD environment variable not set")
        logger.info("For production: Get password from GCP Secret Manager")
        logger.info("For local: export NEO4J_PASSWORD=canadagpt2024")
        sys.exit(1)

    logger.info(f"Connecting to Neo4j at {neo4j_uri}...")
    neo4j = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)

    try:
        # Analyze each node type
        bills = analyze_bills(neo4j)
        votes = analyze_votes(neo4j)
        documents = analyze_documents(neo4j)
        evidence = analyze_committee_evidence(neo4j)

        # Print summary
        print_summary(bills, votes, documents, evidence)

    except Exception as e:
        logger.error(f"Error analyzing data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        neo4j.close()


if __name__ == "__main__":
    main()
