"""Lobbying data ingestion: registrations, communications, lobbyists, organizations."""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Add fedmcp package to path
FEDMCP_PATH = Path(__file__).parent.parent.parent.parent / "fedmcp" / "src"
sys.path.insert(0, str(FEDMCP_PATH))

from fedmcp.clients.lobbying import LobbyingRegistryClient

from ..utils.neo4j_client import Neo4jClient
from ..utils.progress import logger


def ingest_lobbying_data(neo4j_client: Neo4jClient, batch_size: int = 10000) -> Dict[str, int]:
    """
    Ingest lobbying registry data.

    Downloads ~90MB CSV data from Open Canada portal, caches locally,
    and loads into Neo4j.

    Args:
        neo4j_client: Neo4j client
        batch_size: Batch size for operations

    Returns:
        Dict with counts of created entities
    """
    logger.info("=" * 60)
    logger.info("LOBBYING DATA INGESTION")
    logger.info("=" * 60)

    # Use official source (lobbycanada.gc.ca) as the opendata URLs are outdated/broken
    # The official site is accessible from Cloud Run without any networking issues
    lobby_client = LobbyingRegistryClient(source="official")

    stats = {}

    # Clear existing lobbying data for full refresh (in batches to avoid Neo4j memory limits)
    logger.info("Clearing existing lobbying data...")
    for label in ["LobbyRegistration", "LobbyCommunication", "Organization", "Lobbyist"]:
        while True:
            result = neo4j_client.run_query(f"MATCH (n:{label}) WITH n LIMIT 10000 DETACH DELETE n RETURN count(n) as deleted")
            deleted = result[0]["deleted"] if result else 0
            if deleted == 0:
                break
            logger.info(f"  Deleted {deleted} {label} nodes...")
    logger.info("✓ Cleared existing lobbying data")

    # Track unique entities for later creation
    unique_organizations = {}
    unique_lobbyists = {}

    # 1. Lobby Registrations
    logger.info("Fetching lobby registrations (may download 90MB on first run)...")
    registrations = lobby_client.search_registrations(active_only=False, limit=None)
    logger.info(f"Found {len(registrations):,} registrations")

    # Transform to Neo4j format with ALL fields
    reg_data = []
    for i, reg in enumerate(registrations):
        # Extract organization
        org_name = reg.client_org_name
        if org_name and org_name not in unique_organizations:
            unique_organizations[org_name] = {
                "id": f"org-{len(unique_organizations)}",
                "name": org_name,
            }

        # Extract lobbyist
        lobbyist_name = reg.registrant_name
        if lobbyist_name and lobbyist_name not in unique_lobbyists:
            unique_lobbyists[lobbyist_name] = {
                "id": f"lobbyist-{len(unique_lobbyists)}",
                "name": lobbyist_name,
            }

        reg_props = {
            "id": reg.reg_id or f"reg-{i}",
            "reg_number": reg.reg_number,
            "client_org_name": reg.client_org_name,
            "registrant_name": reg.registrant_name,
            "effective_date": reg.effective_date,
            "end_date": reg.end_date if reg.end_date and reg.end_date != "null" else None,
            "active": reg.is_active,
            "subject_matters": reg.subject_matters if reg.subject_matters else [],
            "government_institutions": reg.government_institutions if reg.government_institutions else [],
            "updated_at": datetime.utcnow().isoformat(),
        }
        reg_props = {k: v for k, v in reg_props.items() if v is not None}
        reg_data.append(reg_props)

        # Log progress every 10,000 registrations
        if (i + 1) % 10000 == 0:
            logger.info(f"Processed {i + 1:,} registrations...")

    stats["lobby_registrations"] = neo4j_client.batch_create_nodes("LobbyRegistration", reg_data, batch_size)

    # 2. Lobby Communications
    logger.info("Fetching lobby communications...")
    communications = lobby_client.search_communications(limit=None)  # Process ALL
    logger.info(f"Found {len(communications):,} communications")

    comm_data = []
    for i, comm in enumerate(communications):
        # Extract organization
        org_name = comm.client_org_name
        if org_name and org_name not in unique_organizations:
            unique_organizations[org_name] = {
                "id": f"org-{len(unique_organizations)}",
                "name": org_name,
            }

        # Extract lobbyist
        lobbyist_name = comm.registrant_name
        if lobbyist_name and lobbyist_name not in unique_lobbyists:
            unique_lobbyists[lobbyist_name] = {
                "id": f"lobbyist-{len(unique_lobbyists)}",
                "name": lobbyist_name,
            }

        comm_props = {
            "id": comm.comlog_id or f"comm-{i}",
            "client_org_name": comm.client_org_name,
            "registrant_name": comm.registrant_name,
            "date": comm.comm_date,
            "dpoh_names": comm.dpoh_names if comm.dpoh_names else [],
            "dpoh_titles": comm.dpoh_titles if comm.dpoh_titles else [],
            "institutions": comm.institutions if comm.institutions else [],
            "subject_matters": comm.subject_matters if comm.subject_matters else [],
            "updated_at": datetime.utcnow().isoformat(),
        }
        comm_props = {k: v for k, v in comm_props.items() if v is not None}
        comm_data.append(comm_props)

        # Log progress every 10,000 communications
        if (i + 1) % 10000 == 0:
            logger.info(f"Processed {i + 1:,} communications...")

    stats["lobby_communications"] = neo4j_client.batch_create_nodes("LobbyCommunication", comm_data, batch_size)

    # 3. Create Organizations
    logger.info(f"Creating {len(unique_organizations):,} unique organizations...")
    org_data = list(unique_organizations.values())
    stats["organizations"] = neo4j_client.batch_create_nodes("Organization", org_data, batch_size)

    # 4. Create Lobbyists
    logger.info(f"Creating {len(unique_lobbyists):,} unique lobbyists...")
    lobbyist_data = list(unique_lobbyists.values())
    stats["lobbyists"] = neo4j_client.batch_create_nodes("Lobbyist", lobbyist_data, batch_size)

    # 5. Create Relationships
    logger.info("Creating relationships between entities...")

    # 5a. LobbyRegistration relationships
    logger.info("  Creating LobbyRegistration → Organization (ON_BEHALF_OF)...")
    reg_org_query = """
    MATCH (lr:LobbyRegistration)
    MATCH (o:Organization {name: lr.client_org_name})
    MERGE (lr)-[:ON_BEHALF_OF]->(o)
    """
    neo4j_client.run_query(reg_org_query)

    logger.info("  Creating Lobbyist → LobbyRegistration (REGISTERED_FOR)...")
    reg_lobbyist_query = """
    MATCH (lr:LobbyRegistration)
    MATCH (l:Lobbyist {name: lr.registrant_name})
    MERGE (l)-[:REGISTERED_FOR]->(lr)
    """
    neo4j_client.run_query(reg_lobbyist_query)

    # 5b. LobbyCommunication relationships
    logger.info("  Creating LobbyCommunication → Organization (COMMUNICATION_BY)...")
    comm_org_query = """
    MATCH (lc:LobbyCommunication)
    MATCH (o:Organization {name: lc.client_org_name})
    MERGE (lc)-[:COMMUNICATION_BY]->(o)
    """
    neo4j_client.run_query(comm_org_query)

    logger.info("  Creating LobbyCommunication → Lobbyist (CONDUCTED_BY)...")
    comm_lobbyist_query = """
    MATCH (lc:LobbyCommunication)
    WHERE lc.registrant_name IS NOT NULL
    MATCH (l:Lobbyist {name: lc.registrant_name})
    MERGE (lc)-[:CONDUCTED_BY]->(l)
    """
    neo4j_client.run_query(comm_lobbyist_query)

    # 5c. LobbyCommunication → MP (CONTACTED) relationships
    # This is the critical relationship for MP lobbying pages
    # Use Cypher's built-in matching capabilities for better performance
    logger.info("  Creating LobbyCommunication → MP (CONTACTED) relationships...")

    # Strategy: Use UNWIND to process dpoh_names and match to MPs in Cypher
    # This is much faster than Python loops with individual queries
    contacted_query = """
    MATCH (lc:LobbyCommunication)
    WHERE lc.dpoh_names IS NOT NULL AND size(lc.dpoh_names) > 0
    UNWIND lc.dpoh_names as dpoh_name
    MATCH (m:MP)
    WHERE
        // Exact match on name
        toLower(m.name) = toLower(dpoh_name)
        // Or match Given + Family
        OR toLower(m.given_name + ' ' + m.family_name) = toLower(dpoh_name)
        // Or match Family, Given (common format)
        OR toLower(m.family_name + ', ' + m.given_name) = toLower(dpoh_name)
        // Or match first name + family (e.g., "John Smith" for "John Robert Smith")
        OR (m.given_name IS NOT NULL AND m.family_name IS NOT NULL AND
            toLower(split(m.given_name, ' ')[0] + ' ' + m.family_name) = toLower(dpoh_name))
    MERGE (lc)-[:CONTACTED]->(m)
    """
    neo4j_client.run_query(contacted_query)

    # Count how many CONTACTED relationships were created
    count_query = """
    MATCH ()-[r:CONTACTED]->()
    RETURN count(r) as count
    """
    count_result = neo4j_client.run_query(count_query)
    contacted_count = count_result[0]['count'] if count_result else 0

    stats["contacted_relationships"] = contacted_count

    logger.info(f"  ✓ Created {contacted_count:,} CONTACTED relationships")

    logger.info("=" * 60)
    logger.success("✅ LOBBYING DATA INGESTION COMPLETE")
    logger.info(f"Registrations: {stats['lobby_registrations']:,}")
    logger.info(f"Communications: {stats['lobby_communications']:,}")
    logger.info(f"Organizations: {stats['organizations']:,}")
    logger.info(f"Lobbyists: {stats['lobbyists']:,}")
    logger.info(f"CONTACTED Relationships: {stats.get('contacted_relationships', 0):,}")
    if stats.get('unmatched_dpoh_names'):
        logger.info(f"Unmatched DPOH Names: {stats['unmatched_dpoh_names']:,}")
    logger.info("=" * 60)

    return stats
