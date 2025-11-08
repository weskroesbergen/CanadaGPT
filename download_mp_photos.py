#!/usr/bin/env python3
"""
Download all MP photos from OpenParliament.
"""
import os
from pathlib import Path
import requests
from datetime import datetime

# Add packages to path
import sys
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

    # Get all MPs with photo URLs
    query = """
    MATCH (m:MP)
    WHERE m.photo_url IS NOT NULL
    RETURN m.id as id, m.name as name, m.photo_url as photo_url
    ORDER BY m.name
    """

    mps = neo4j_client.run_query(query)
    logger.info(f"Found {len(mps)} MPs with photos")

    # Create output directory
    output_dir = Path("/Users/matthewdufresne/FedMCP/packages/frontend/public/mp-photos")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Download photos
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Connexxia-Agent (matt@thoughtforge.com)"
    })

    success_count = 0
    fail_count = 0

    for i, mp in enumerate(mps):
        if i % 50 == 0:
            logger.info(f"Progress: {i}/{len(mps)}")

        photo_url = mp['photo_url']
        mp_id = mp['id']
        mp_name = mp['name']

        # Build full URL
        if photo_url.startswith('/'):
            full_url = f"https://api.openparliament.ca{photo_url}"
        else:
            full_url = photo_url

        # Determine file extension
        ext = Path(photo_url).suffix or '.jpg'
        output_path = output_dir / f"{mp_id}{ext}"

        # Skip if already exists
        if output_path.exists():
            success_count += 1
            continue

        try:
            response = session.get(full_url, timeout=10)
            response.raise_for_status()

            # Save photo
            with open(output_path, 'wb') as f:
                f.write(response.content)

            # Update Neo4j with local path
            update_query = """
            MATCH (m:MP {id: $id})
            SET m.photo_local_path = $local_path,
                m.photo_url_original = m.photo_url,
                m.photo_url = $web_path,
                m.updated_at = $timestamp
            """
            neo4j_client.run_query(update_query, {
                "id": mp_id,
                "local_path": str(output_path),
                "web_path": f"/mp-photos/{mp_id}{ext}",
                "timestamp": datetime.utcnow().isoformat()
            })

            success_count += 1
            logger.debug(f"✓ {mp_name}")

        except Exception as e:
            fail_count += 1
            logger.warning(f"✗ Failed to download {mp_name}: {e}")

    neo4j_client.close()

    logger.success(f"✅ Downloaded {success_count} photos")
    logger.info(f"❌ Failed: {fail_count}")
    logger.info(f"📁 Photos saved to: {output_dir}")

if __name__ == "__main__":
    main()
