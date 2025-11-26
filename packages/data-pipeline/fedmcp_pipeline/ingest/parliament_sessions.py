"""Parliament and Session data ingestion from curated JSON metadata."""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from ..utils.neo4j_client import Neo4jClient
from ..utils.progress import logger, ProgressTracker, batch_iterator


def load_parliament_data() -> Dict[str, Any]:
    """
    Load parliament and session data from JSON file.

    Returns:
        Dictionary with 'parliaments' and 'sessions' lists
    """
    data_file = Path(__file__).parent.parent / "data" / "parliaments.json"
    if not data_file.exists():
        raise FileNotFoundError(f"Parliament data file not found: {data_file}")

    with open(data_file, 'r') as f:
        data = json.load(f)

    logger.info(f"Loaded {len(data['parliaments'])} parliaments and {len(data['sessions'])} sessions from {data_file}")
    return data


def ingest_parliaments(neo4j_client: Neo4jClient, batch_size: int = 50) -> int:
    """
    Ingest all 45 Canadian federal parliaments into Neo4j.

    Uses MERGE to be idempotent - can be run multiple times safely.

    Args:
        neo4j_client: Neo4j client instance
        batch_size: Number of parliaments to import per batch

    Returns:
        Number of parliaments created/updated
    """
    logger.info("=" * 80)
    logger.info("INGESTING PARLIAMENTS (1st-45th)")
    logger.info("=" * 80)

    # Load data
    data = load_parliament_data()
    parliaments = data['parliaments']

    # Create Cypher query for batch import
    cypher = """
    UNWIND $parliaments AS p
    MERGE (parl:Parliament {number: p.number})
    SET parl.ordinal = p.ordinal,
        parl.election_date = date(p.election_date),
        parl.opening_date = CASE WHEN p.opening_date IS NOT NULL THEN date(p.opening_date) ELSE null END,
        parl.dissolution_date = CASE WHEN p.dissolution_date IS NOT NULL THEN date(p.dissolution_date) ELSE null END,
        parl.party_in_power = p.party_in_power,
        parl.prime_minister = p.prime_minister,
        parl.total_seats = p.total_seats,
        parl.is_current = p.is_current,
        parl.updated_at = datetime()
    RETURN count(parl) AS created_count
    """

    # Determine current parliament (most recent)
    current_parliament_number = max(p['number'] for p in parliaments)
    for p in parliaments:
        p['is_current'] = (p['number'] == current_parliament_number)

    logger.info(f"Importing {len(parliaments)} parliaments...")
    logger.info(f"Current parliament: {current_parliament_number}th")

    # Import in batches
    total_created = 0
    progress = ProgressTracker(total=len(parliaments), desc="Importing parliaments")

    for batch in batch_iterator(parliaments, batch_size=batch_size):
        result = neo4j_client.run_query(cypher, {'parliaments': batch})
        created_count = result[0]['created_count'] if result else len(batch)
        total_created += created_count
        progress.update(len(batch))

    progress.close()
    logger.info(f"✓ Successfully imported {total_created} parliaments")
    return total_created


def ingest_sessions(neo4j_client: Neo4jClient, batch_size: int = 50) -> int:
    """
    Ingest all sessions (37-1 through 45-1) into Neo4j.

    Creates Session nodes and links them to their Parliament nodes.
    Uses MERGE to be idempotent.

    Args:
        neo4j_client: Neo4j client instance
        batch_size: Number of sessions to import per batch

    Returns:
        Number of sessions created/updated
    """
    logger.info("=" * 80)
    logger.info("INGESTING SESSIONS (37-1 through 45-1)")
    logger.info("=" * 80)

    # Load data
    data = load_parliament_data()
    sessions = data['sessions']

    # Create Cypher query for batch import
    cypher = """
    UNWIND $sessions AS s
    MERGE (sess:Session {id: s.id})
    SET sess.parliament_number = s.parliament_number,
        sess.session_number = s.session_number,
        sess.start_date = date(s.start_date),
        sess.end_date = CASE WHEN s.end_date IS NOT NULL THEN date(s.end_date) ELSE null END,
        sess.prorogation_date = CASE WHEN s.prorogation_date IS NOT NULL THEN date(s.prorogation_date) ELSE null END,
        sess.is_current = s.is_current,
        sess.updated_at = datetime()

    // Link to Parliament
    WITH sess, s
    MATCH (parl:Parliament {number: s.parliament_number})
    MERGE (parl)-[:HAS_SESSION]->(sess)

    RETURN count(sess) AS created_count
    """

    # Determine current session (most recent)
    # Parse session IDs like "45-1" to find max
    current_session_id = max(sessions, key=lambda s: (s['parliament_number'], s['session_number']))['id']
    for s in sessions:
        s['is_current'] = (s['id'] == current_session_id)

    logger.info(f"Importing {len(sessions)} sessions...")
    logger.info(f"Current session: {current_session_id}")

    # Import in batches
    total_created = 0
    progress = ProgressTracker(total=len(sessions), desc="Importing sessions")

    for batch in batch_iterator(sessions, batch_size=batch_size):
        result = neo4j_client.run_query(cypher, {'sessions': batch})
        created_count = result[0]['created_count'] if result else len(batch)
        total_created += created_count
        progress.update(len(batch))

    progress.close()
    logger.info(f"✓ Successfully imported {total_created} sessions")
    return total_created


def link_bills_to_sessions(neo4j_client: Neo4jClient) -> int:
    """
    Create FROM_SESSION and FROM_PARLIAMENT relationships for existing Bill nodes.

    Uses Bill.session field (e.g., "45-1") to link to Session nodes.
    Uses Bill.parliament field to link to Parliament nodes.

    Returns:
        Number of Bills linked
    """
    logger.info("=" * 80)
    logger.info("LINKING BILLS TO SESSIONS AND PARLIAMENTS")
    logger.info("=" * 80)

    cypher = """
    MATCH (b:Bill)
    WHERE b.session IS NOT NULL

    // Link to Session
    WITH b
    MATCH (s:Session {id: b.session})
    MERGE (b)-[:FROM_SESSION]->(s)

    // Link to Parliament
    WITH b
    MATCH (p:Parliament {number: b.parliament})
    MERGE (b)-[:FROM_PARLIAMENT]->(p)

    RETURN count(DISTINCT b) AS linked_count
    """

    logger.info("Creating FROM_SESSION and FROM_PARLIAMENT relationships for Bills...")
    result = neo4j_client.run_query(cypher)
    linked_count = result[0]['linked_count'] if result else 0

    logger.info(f"✓ Linked {linked_count} bills to sessions and parliaments")
    return linked_count


def link_votes_to_sessions(neo4j_client: Neo4jClient) -> int:
    """
    Create FROM_SESSION relationships for existing Vote nodes.

    Uses Vote.parliament_number and Vote.session_number to construct session ID.

    Returns:
        Number of Votes linked
    """
    logger.info("=" * 80)
    logger.info("LINKING VOTES TO SESSIONS")
    logger.info("=" * 80)

    cypher = """
    MATCH (v:Vote)
    WHERE v.parliament_number IS NOT NULL AND v.session_number IS NOT NULL

    // Construct session ID (e.g., "45-1")
    WITH v, toString(v.parliament_number) + '-' + toString(v.session_number) AS session_id
    MATCH (s:Session {id: session_id})
    MERGE (v)-[:FROM_SESSION]->(s)

    RETURN count(DISTINCT v) AS linked_count
    """

    logger.info("Creating FROM_SESSION relationships for Votes...")
    result = neo4j_client.run_query(cypher)
    linked_count = result[0]['linked_count'] if result else 0

    logger.info(f"✓ Linked {linked_count} votes to sessions")
    return linked_count


def link_documents_to_sessions(neo4j_client: Neo4jClient) -> int:
    """
    Create FROM_SESSION relationships for existing Document nodes (Hansard).

    Uses Document.parliament_number and Document.session_number to construct session ID.

    Returns:
        Number of Documents linked
    """
    logger.info("=" * 80)
    logger.info("LINKING DOCUMENTS (HANSARD) TO SESSIONS")
    logger.info("=" * 80)

    cypher = """
    MATCH (d:Document)
    WHERE d.parliament_number IS NOT NULL AND d.session_number IS NOT NULL

    // Construct session ID (e.g., "45-1")
    WITH d, toString(d.parliament_number) + '-' + toString(d.session_number) AS session_id
    MATCH (s:Session {id: session_id})
    MERGE (d)-[:FROM_SESSION]->(s)

    RETURN count(DISTINCT d) AS linked_count
    """

    logger.info("Creating FROM_SESSION relationships for Documents...")
    result = neo4j_client.run_query(cypher)
    linked_count = result[0]['linked_count'] if result else 0

    logger.info(f"✓ Linked {linked_count} documents to sessions")
    return linked_count


def run_full_import(neo4j_client: Neo4jClient) -> Dict[str, int]:
    """
    Run complete Parliament/Session import and linking process.

    Args:
        neo4j_client: Neo4j client instance

    Returns:
        Dictionary with counts of created/linked nodes
    """
    logger.info("=" * 80)
    logger.info("PARLIAMENT & SESSION FULL IMPORT")
    logger.info("=" * 80)

    results = {}

    # 1. Import Parliaments
    results['parliaments'] = ingest_parliaments(neo4j_client)

    # 2. Import Sessions
    results['sessions'] = ingest_sessions(neo4j_client)

    # 3. Link existing data
    results['bills_linked'] = link_bills_to_sessions(neo4j_client)
    results['votes_linked'] = link_votes_to_sessions(neo4j_client)
    results['documents_linked'] = link_documents_to_sessions(neo4j_client)

    logger.info("=" * 80)
    logger.info("IMPORT COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Parliaments: {results['parliaments']}")
    logger.info(f"Sessions: {results['sessions']}")
    logger.info(f"Bills linked: {results['bills_linked']}")
    logger.info(f"Votes linked: {results['votes_linked']}")
    logger.info(f"Documents linked: {results['documents_linked']}")
    logger.info("=" * 80)

    return results
