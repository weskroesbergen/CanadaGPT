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

    lobby_client = LobbyingRegistryClient()

    stats = {}

    # 1. Lobby Registrations
    logger.info("Fetching lobby registrations (may download 90MB on first run)...")
    registrations = lobby_client.search_registrations(active_only=False, limit=None)
    logger.info(f"Found {len(registrations):,} registrations")

    # Transform to Neo4j format
    reg_data = []
    for reg in registrations[:1000]:  # TODO: Process all, this is just a sample
        reg_props = {
            "id": reg.get("reg_id") or f"reg-{len(reg_data)}",
            "reg_number": reg.get("Registration Number"),
            "client_org_name": reg.get("Client Organization Name"),
            "registrant_name": reg.get("Registrant Name"),
            "effective_date": reg.get("Effective Date of Registration"),
            "active": reg.get("Registration Status") == "Active",
            "updated_at": datetime.utcnow().isoformat(),
        }
        reg_props = {k: v for k, v in reg_props.items() if v is not None}
        reg_data.append(reg_props)

    stats["lobby_registrations"] = neo4j_client.batch_create_nodes("LobbyRegistration", reg_data, batch_size)

    # 2. Lobby Communications
    logger.info("Fetching lobby communications...")
    communications = lobby_client.search_communications(limit=1000)  # TODO: Process all
    logger.info(f"Found {len(communications):,} communications")

    comm_data = []
    for comm in communications:
        comm_props = {
            "id": comm.get("comlog_id") or f"comm-{len(comm_data)}",
            "client_org_name": comm.get("Client Organization Name"),
            "date": comm.get("Communication Date"),
            "updated_at": datetime.utcnow().isoformat(),
        }
        comm_props = {k: v for k, v in comm_props.items() if v is not None}
        comm_data.append(comm_props)

    stats["lobby_communications"] = neo4j_client.batch_create_nodes("LobbyCommunication", comm_data, batch_size)

    logger.info("=" * 60)
    logger.success("✅ LOBBYING DATA INGESTION COMPLETE")
    logger.info(f"Registrations: {stats['lobby_registrations']:,}")
    logger.info(f"Communications: {stats['lobby_communications']:,}")
    logger.info("=" * 60)

    return stats
