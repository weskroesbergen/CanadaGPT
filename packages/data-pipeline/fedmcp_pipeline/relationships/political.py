"""Political structure relationships: MEMBER_OF, REPRESENTS, SERVES_ON."""

from typing import Dict, Any

from ..utils.neo4j_client import Neo4jClient
from ..utils.progress import logger


def build_political_structure(neo4j_client: Neo4jClient, batch_size: int = 10000) -> Dict[str, int]:
    """
    Build political structure relationships.

    Creates:
    - (MP)-[:MEMBER_OF]->(Party)
    - (MP)-[:REPRESENTS]->(Riding)

    Args:
        neo4j_client: Neo4j client
        batch_size: Batch size for operations

    Returns:
        Dict with counts of created relationships
    """
    logger.info("=" * 60)
    logger.info("BUILDING POLITICAL STRUCTURE RELATIONSHIPS")
    logger.info("=" * 60)

    stats = {}

    # 1. MP MEMBER_OF Party
    logger.info("Creating (MP)-[:MEMBER_OF]->(Party) relationships...")

    # Query MPs with party affiliations
    result = neo4j_client.run_query(
        """
        MATCH (m:MP), (p:Party)
        WHERE m.party = p.short_name
        RETURN m.id AS mp_id, p.code AS party_code
        """
    )

    member_of_rels = [
        {"from_id": record["mp_id"], "to_id": record["party_code"]}
        for record in result
    ]

    logger.info(f"Found {len(member_of_rels):,} MP-Party relationships")
    stats["member_of"] = neo4j_client.batch_create_relationships(
        "MEMBER_OF",
        member_of_rels,
        from_label="MP",
        to_label="Party",
        from_key="id",
        to_key="code",
        batch_size=batch_size,
    )

    # 2. MP REPRESENTS Riding
    logger.info("Creating (MP)-[:REPRESENTS]->(Riding) relationships...")

    result = neo4j_client.run_query(
        """
        MATCH (m:MP), (r:Riding)
        WHERE m.riding = r.name
        RETURN m.id AS mp_id, r.id AS riding_id
        """
    )

    represents_rels = [
        {"from_id": record["mp_id"], "to_id": record["riding_id"]}
        for record in result
    ]

    logger.info(f"Found {len(represents_rels):,} MP-Riding relationships")
    stats["represents"] = neo4j_client.batch_create_relationships(
        "REPRESENTS",
        represents_rels,
        from_label="MP",
        to_label="Riding",
        batch_size=batch_size,
    )

    logger.info("=" * 60)
    logger.success("✅ POLITICAL STRUCTURE COMPLETE")
    logger.info(f"MEMBER_OF: {stats['member_of']:,}")
    logger.info(f"REPRESENTS: {stats['represents']:,}")
    logger.info("=" * 60)

    return stats
