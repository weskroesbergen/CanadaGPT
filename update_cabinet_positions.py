#!/usr/bin/env python3
"""
Update existing MPs with cabinet positions.
"""
import os
import json
from pathlib import Path

# Add packages to path
import sys
sys.path.insert(0, str(Path(__file__).parent / "packages" / "fedmcp" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "packages" / "data-pipeline"))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from loguru import logger

def main():
    # Connect to Neo4j
    neo4j_client = Neo4jClient(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "canadagpt2024"),
    )

    # Load cabinet positions
    cabinet_file = Path(__file__).parent / "packages" / "data-pipeline" / "fedmcp_pipeline" / "data" / "cabinet_positions.json"
    with open(cabinet_file, 'r') as f:
        cabinet_data = json.load(f)

    cabinet_ministers = cabinet_data.get("cabinet_ministers", [])
    logger.info(f"Found {len(cabinet_ministers)} cabinet positions")

    updated_count = 0
    failed_count = 0

    for minister in cabinet_ministers:
        mp_id = minister["slug"]
        position = minister["position"]

        try:
            query = """
            MATCH (m:MP {id: $id})
            SET m.cabinet_position = $position,
                m.updated_at = $timestamp
            RETURN m
            """

            params = {
                "id": mp_id,
                "position": position,
                "timestamp": "2025-11-03T06:45:00Z"
            }

            result = neo4j_client.run_query(query, params)
            if result:
                updated_count += 1
                logger.info(f"✅ Updated {mp_id}: {position}")
            else:
                logger.warning(f"MP not found in database: {mp_id}")
                failed_count += 1

        except Exception as e:
            failed_count += 1
            logger.warning(f"Failed to update {mp_id}: {e}")

    neo4j_client.close()

    logger.success(f"✅ Updated {updated_count} cabinet ministers")
    logger.info(f"❌ Failed: {failed_count}")

if __name__ == "__main__":
    main()
