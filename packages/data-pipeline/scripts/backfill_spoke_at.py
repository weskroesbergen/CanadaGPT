#!/usr/bin/env python3
"""
Backfill SPOKE_AT relationships for existing statements and committee testimonies.

This script creates direct MP → Document/CommitteeEvidence relationships
to enable efficient queries like "which MPs spoke in this debate?"

The script is idempotent and can be run multiple times safely.
"""

import sys
from pathlib import Path

# Add fedmcp_pipeline to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger, ProgressTracker


def backfill_hansard_spoke_at(neo4j: Neo4jClient, batch_size: int = 10000) -> int:
    """
    Create SPOKE_AT relationships for Hansard statements.

    Creates (MP)-[:SPOKE_AT]->(Document) relationships by traversing:
    (Statement)-[:MADE_BY]->(MP) and (Statement)-[:PART_OF]->(Document)

    Args:
        neo4j: Neo4j client instance
        batch_size: Number of relationships to create per batch

    Returns:
        Total number of SPOKE_AT relationships created
    """
    logger.info("Backfilling SPOKE_AT relationships for Hansard statements...")

    # Count total statements that need SPOKE_AT
    # Check if SPOKE_AT with this specific statement_id already exists
    count_query = """
    MATCH (s:Statement)-[:MADE_BY]->(mp:MP)
    MATCH (s)-[:PART_OF]->(d:Document)
    WHERE NOT exists {
        MATCH (mp)-[r:SPOKE_AT]->(d)
        WHERE r.statement_id = s.id
    }
    RETURN count(*) as total
    """
    result = neo4j.run_query(count_query)
    total = result[0]['total'] if result else 0
    logger.info(f"Found {total:,} statements needing SPOKE_AT relationships")

    if total == 0:
        logger.success("✅ All Hansard SPOKE_AT relationships already exist")
        return 0

    # Create SPOKE_AT relationships in batches
    # Creates ONE relationship per statement (multiple per MP-Document pair)
    create_query = """
    MATCH (s:Statement)-[:MADE_BY]->(mp:MP)
    MATCH (s)-[:PART_OF]->(d:Document)
    WHERE NOT exists {
        MATCH (mp)-[r:SPOKE_AT]->(d)
        WHERE r.statement_id = s.id
    }
    WITH s, mp, d
    LIMIT $batch_size

    CREATE (mp)-[r:SPOKE_AT]->(d)
    SET r.timestamp = s.time,
        r.statement_id = s.id,
        r.intervention_id = s.intervention_id,
        r.person_db_id = s.person_db_id

    RETURN count(*) as created
    """

    total_created = 0
    tracker = ProgressTracker(total, "SPOKE_AT relationships")

    while True:
        result = neo4j.run_query(create_query, {"batch_size": batch_size})
        created = result[0]['created'] if result else 0

        if created == 0:
            break

        total_created += created
        tracker.update(total_created)

    logger.success(f"✅ Created {total_created:,} Hansard SPOKE_AT relationships")
    return total_created


def backfill_committee_spoke_at(neo4j: Neo4jClient, batch_size: int = 10000) -> int:
    """
    Create SPOKE_AT relationships for committee testimonies.

    Creates (MP)-[:SPOKE_AT]->(CommitteeEvidence) relationships by traversing:
    (CommitteeTestimony)-[:TESTIFIED_BY]->(MP) and
    (CommitteeTestimony)-[:GIVEN_IN]->(CommitteeEvidence)

    Args:
        neo4j: Neo4j client instance
        batch_size: Number of relationships to create per batch

    Returns:
        Total number of SPOKE_AT relationships created
    """
    logger.info("Backfilling SPOKE_AT relationships for committee testimonies...")

    # Count total testimonies that need SPOKE_AT
    # Check if SPOKE_AT with this specific testimony_id already exists
    count_query = """
    MATCH (ct:CommitteeTestimony)-[:TESTIFIED_BY]->(mp:MP)
    MATCH (ct)-[:GIVEN_IN]->(ce:CommitteeEvidence)
    WHERE NOT exists {
        MATCH (mp)-[r:SPOKE_AT]->(ce)
        WHERE r.testimony_id = ct.id
    }
    RETURN count(*) as total
    """
    result = neo4j.run_query(count_query)
    total = result[0]['total'] if result else 0
    logger.info(f"Found {total:,} testimonies needing SPOKE_AT relationships")

    if total == 0:
        logger.success("✅ All committee SPOKE_AT relationships already exist")
        return 0

    # Create SPOKE_AT relationships in batches
    # Creates ONE relationship per testimony (multiple per MP-CommitteeEvidence pair)
    create_query = """
    MATCH (ct:CommitteeTestimony)-[:TESTIFIED_BY]->(mp:MP)
    MATCH (ct)-[:GIVEN_IN]->(ce:CommitteeEvidence)
    WHERE NOT exists {
        MATCH (mp)-[r:SPOKE_AT]->(ce)
        WHERE r.testimony_id = ct.id
    }
    WITH ct, mp, ce
    LIMIT $batch_size

    CREATE (mp)-[r:SPOKE_AT]->(ce)
    SET r.testimony_id = ct.id,
        r.intervention_id = ct.intervention_id,
        r.person_db_id = ct.person_db_id,
        r.timestamp_hour = ct.timestamp_hour,
        r.timestamp_minute = ct.timestamp_minute

    RETURN count(*) as created
    """

    total_created = 0
    tracker = ProgressTracker(total, "committee SPOKE_AT relationships")

    while True:
        result = neo4j.run_query(create_query, {"batch_size": batch_size})
        created = result[0]['created'] if result else 0

        if created == 0:
            break

        total_created += created
        tracker.update(total_created)

    logger.success(f"✅ Created {total_created:,} committee SPOKE_AT relationships")
    return total_created


def verify_spoke_at(neo4j: Neo4jClient) -> None:
    """
    Verify SPOKE_AT relationships were created correctly.

    Args:
        neo4j: Neo4j client instance
    """
    logger.info("Verifying SPOKE_AT relationships...")

    # Count total SPOKE_AT relationships
    count_query = """
    MATCH ()-[r:SPOKE_AT]->()
    RETURN count(r) as total
    """
    result = neo4j.run_query(count_query)
    total = result[0]['total'] if result else 0
    logger.info(f"Total SPOKE_AT relationships: {total:,}")

    # Count by target type
    by_type_query = """
    MATCH (mp:MP)-[r:SPOKE_AT]->(target)
    WITH labels(target) AS target_labels, count(r) AS count
    RETURN target_labels[0] AS target_type, count
    ORDER BY count DESC
    """
    result = neo4j.run_query(by_type_query)

    logger.info("SPOKE_AT relationships by target type:")
    for row in result:
        logger.info(f"  - {row['target_type']}: {row['count']:,}")

    # Sample 5 MPs with most speeches
    top_speakers_query = """
    MATCH (mp:MP)-[r:SPOKE_AT]->(d)
    WITH mp, count(r) AS speech_count
    ORDER BY speech_count DESC
    LIMIT 5
    RETURN mp.name AS mp_name, speech_count
    """
    result = neo4j.run_query(top_speakers_query)

    logger.info("Top 5 MPs by speaking activity:")
    for row in result:
        logger.info(f"  - {row['mp_name']}: {row['speech_count']:,} speeches")

    logger.success("✅ Verification complete")


def main():
    """Main execution function."""
    import os

    # Get Neo4j connection details from environment
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD')

    if not neo4j_password:
        logger.error("NEO4J_PASSWORD environment variable not set")
        sys.exit(1)

    logger.info(f"Connecting to Neo4j at {neo4j_uri}...")
    neo4j = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)

    try:
        # Backfill Hansard SPOKE_AT relationships
        hansard_count = backfill_hansard_spoke_at(neo4j, batch_size=10000)

        # Backfill Committee SPOKE_AT relationships
        committee_count = backfill_committee_spoke_at(neo4j, batch_size=10000)

        # Verify results
        verify_spoke_at(neo4j)

        # Summary
        total = hansard_count + committee_count
        logger.success(f"""
╔═══════════════════════════════════════╗
║   SPOKE_AT Backfill Complete         ║
╠═══════════════════════════════════════╣
║  Hansard: {hansard_count:>10,} relationships    ║
║  Committee: {committee_count:>8,} relationships    ║
║  Total: {total:>12,} relationships    ║
╚═══════════════════════════════════════╝
        """)

    except Exception as e:
        logger.error(f"Error during backfill: {e}")
        raise
    finally:
        neo4j.close()


if __name__ == "__main__":
    main()
