#!/usr/bin/env python3
"""
Update existing MPs with full contact and social media information.
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
from loguru import logger

def main():
    # Connect to Neo4j
    neo4j_client = Neo4jClient(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "canadagpt2024"),
    )

    op_client = OpenParliamentClient()

    # Get all MPs
    logger.info("Fetching MPs from OpenParliament...")
    mps_list = list(op_client.list_mps())
    logger.info(f"Found {len(mps_list)} MPs")

    updated_count = 0
    failed_count = 0

    for i, mp_summary in enumerate(mps_list):
        if i % 50 == 0:
            logger.info(f"Progress: {i}/{len(mps_list)}")

        mp_url = mp_summary.get("url", "")
        mp_id = mp_url.split("/")[-2]

        try:
            # Fetch full MP details
            mp_data = op_client._request(mp_url)

            # Extract additional info from other_info
            other_info = mp_data.get("other_info", {})
            twitter_handles = other_info.get("twitter", [])
            twitter_handle = twitter_handles[0] if twitter_handles else None

            wikipedia_ids = other_info.get("wikipedia_id", [])
            wikipedia_id = wikipedia_ids[0] if wikipedia_ids else None

            constituency_offices = other_info.get("constituency_offices", [])
            constituency_office = constituency_offices[0] if constituency_offices else None

            # Extract OurCommons link
            links = mp_data.get("links", [])
            ourcommons_url = next((link["url"] for link in links if "ourcommons.ca" in link.get("url", "")), None)

            # Build dynamic SET clause only for fields that exist
            set_clauses = []
            params = {"id": mp_id}

            if mp_data.get("email"):
                set_clauses.append("m.email = $email")
                params["email"] = mp_data.get("email")

            if mp_data.get("voice"):
                set_clauses.append("m.phone = $phone")
                params["phone"] = mp_data.get("voice")

            if twitter_handle:
                set_clauses.append("m.twitter = $twitter")
                params["twitter"] = twitter_handle

            if mp_data.get("given_name"):
                set_clauses.append("m.given_name = $given_name")
                params["given_name"] = mp_data.get("given_name")

            if mp_data.get("family_name"):
                set_clauses.append("m.family_name = $family_name")
                params["family_name"] = mp_data.get("family_name")

            if mp_data.get("gender"):
                set_clauses.append("m.gender = $gender")
                params["gender"] = mp_data.get("gender")

            if wikipedia_id:
                set_clauses.append("m.wikipedia_id = $wikipedia_id")
                params["wikipedia_id"] = wikipedia_id

            if constituency_office:
                set_clauses.append("m.constituency_office = $constituency_office")
                params["constituency_office"] = constituency_office

            if ourcommons_url:
                set_clauses.append("m.ourcommons_url = $ourcommons_url")
                params["ourcommons_url"] = ourcommons_url

            set_clauses.append("m.updated_at = $timestamp")
            params["timestamp"] = "2025-11-03T06:35:00Z"

            if len(set_clauses) <= 1:  # Only timestamp
                continue

            query = f"""
            MATCH (m:MP {{id: $id}})
            SET {', '.join(set_clauses)}
            RETURN m
            """

            result = neo4j_client.run_query(query, params)
            if result:
                updated_count += 1
            else:
                logger.warning(f"MP not found in database: {mp_id}")

            # Be nice to the API
            time.sleep(0.1)

        except Exception as e:
            failed_count += 1
            logger.warning(f"Failed to update {mp_id}: {e}")

    neo4j_client.close()

    logger.success(f"✅ Updated {updated_count} MPs")
    logger.info(f"❌ Failed: {failed_count}")

if __name__ == "__main__":
    main()
