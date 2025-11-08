#!/usr/bin/env python3
"""
Re-ingest bills to add sponsor_politician_url field.
"""
import os
from pathlib import Path

# Add packages to path
import sys
sys.path.insert(0, str(Path(__file__).parent / "packages" / "data-pipeline"))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.ingest.parliament import ingest_bills, link_bill_sponsors
from loguru import logger

def main():
    # Connect to Neo4j
    neo4j_client = Neo4jClient(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "canadagpt2024"),
    )

    logger.info("Re-ingesting bills to add sponsor information...")
    ingest_bills(neo4j_client, batch_size=10000)

    logger.info("Creating SPONSORED relationships...")
    count = link_bill_sponsors(neo4j_client)

    neo4j_client.close()
    logger.success(f"Done! Created {count:,} SPONSORED relationships")

if __name__ == "__main__":
    main()
