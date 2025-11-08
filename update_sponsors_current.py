#!/usr/bin/env python3
"""
Fetch sponsor info for bills from current parliament and create relationships.
"""
import os
from pathlib import Path
import time

# Add packages to path
import sys
sys.path.insert(0, str(Path(__file__).parent / "packages" / "fedmcp" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "packages" / "data-pipeline"))

from fedmcp.clients.openparliament import OpenParliamentClient
from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.ingest.parliament import link_bill_sponsors
from loguru import logger

def main():
    # Connect to Neo4j
    neo4j_client = Neo4jClient(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "canadagpt2024"),
    )

    op_client = OpenParliamentClient()

    # Get bills from current session
    logger.info("Fetching bills from session 45-1...")
    bills_to_update = []
    for bill in op_client.list_bills():
        if bill.get("session") == "45-1":
            bills_to_update.append(bill)

    logger.info(f"Found {len(bills_to_update)} bills from session 45-1")

    # Fetch details for each bill to get sponsor info
    logger.info("Fetching bill details to get sponsor information...")
    updated = 0
    for i, bill in enumerate(bills_to_update):
        if i % 10 == 0:
            logger.info(f"Progress: {i}/{len(bills_to_update)}")

        # Get detailed bill info
        bill_url = bill.get("url")  # e.g., "/bills/45-1/C-249/"
        try:
            detail = op_client._request(bill_url)
            sponsor_url = detail.get("sponsor_politician_url")

            if sponsor_url:
                # Update bill in Neo4j
                query = """
                MATCH (b:Bill {number: $number, session: $session})
                SET b.sponsor_politician_url = $sponsor_url
                RETURN b
                """
                neo4j_client.run_query(query, {
                    "number": bill.get("number"),
                    "session": bill.get("session"),
                    "sponsor_url": sponsor_url
                })
                updated += 1

            # Be nice to the API
            time.sleep(0.1)

        except Exception as e:
            logger.warning(f"Failed to fetch {bill_url}: {e}")

    logger.success(f"✅ Updated {updated} bills with sponsor information")

    # Now create SPONSORED relationships
    logger.info("Creating SPONSORED relationships...")
    count = link_bill_sponsors(neo4j_client)

    neo4j_client.close()
    logger.success(f"Done! Created {count:,} SPONSORED relationships")

if __name__ == "__main__":
    main()
