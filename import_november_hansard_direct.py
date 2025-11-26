#!/usr/bin/env python3
"""
Import November 2025 Hansard using OurCommonsHansardClient (XML from DocumentViewer).

Simplified version - directly fetches Hansard XML for November dates without OpenParliament API.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages" / "fedmcp" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "packages" / "data-pipeline"))

from fedmcp.clients.ourcommons import OurCommonsHansardClient
from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger


def generate_november_weekdays() -> List[str]:
    """Generate list of weekdays in November 2025 when Parliament was likely sitting."""
    dates = []
    start_date = datetime(2025, 11, 1)
    end_date = datetime(2025, 11, 30)

    current = start_date
    while current <= end_date:
        # Only weekdays (Monday=0, Friday=4)
        if current.weekday() < 5:
            dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    return dates


def parse_hansard_xml(hansard_client: OurCommonsHansardClient, date: str) -> Any:
    """Fetch and parse Hansard XML for a specific date."""
    try:
        # Try common Hansard slug formats
        slug = f"house-sitting/{date}/hansard"
        sitting = hansard_client.get_sitting(slug, parse=True)
        return sitting
    except Exception as e:
        logger.debug(f"Failed to parse Hansard for {date}: {e}")
        return None


def import_sitting_to_neo4j(neo4j: Neo4jClient, sitting: Any, date: str) -> Dict[str, int]:
    """Import a parsed Hansard sitting to Neo4j."""
    stats = {"documents": 0, "statements": 0}

    if not sitting or not sitting.sections:
        return stats

    # Create Document node
    document_id = f"hansard-{date}"
    document_data = [{
        "id": document_id,
        "date": date,
        "session_id": "45-1",  # Current parliament session
        "document_type": "D",  # Debates
        "public": True,
        "source": "ourcommons_xml",
        "updated_at": datetime.utcnow().isoformat(),
    }]

    neo4j.batch_merge_nodes("Document", document_data, merge_keys=["id"])
    stats["documents"] = 1
    logger.info(f"  ✓ Created Document: {document_id}")

    # Create Statement nodes from speeches
    statements_data = []
    stmt_counter = 0

    for section in sitting.sections:
        h1 = section.heading_en or ""

        for speech in section.speeches:
            stmt_counter += 1
            statement_id = f"{document_id}-stmt-{stmt_counter}"

            statements_data.append({
                "id": statement_id,
                "document_id": document_id,
                "time": f"{date}T{speech.time}" if speech.time else f"{date}T12:00:00",
                "who_en": speech.speaker_en or "",
                "who_fr": speech.speaker_fr or "",
                "content_en": "\n\n".join(speech.paragraphs_en) if speech.paragraphs_en else "",
                "content_fr": "\n\n".join(speech.paragraphs_fr) if speech.paragraphs_fr else "",
                "h1_en": h1,
                "h2_en": speech.topic_en or "",
                "statement_type": "speech",
                "wordcount": len(" ".join(speech.paragraphs_en).split()) if speech.paragraphs_en else 0,
                "procedural": False,
                "updated_at": datetime.utcnow().isoformat(),
            })

    if statements_data:
        neo4j.batch_merge_nodes("Statement", statements_data, merge_keys=["id"], batch_size=1000)
        stats["statements"] = len(statements_data)
        logger.info(f"  ✓ Created {len(statements_data)} statements")

    # Create PART_OF relationships
    if statements_data:
        rel_query = """
        MATCH (d:Document {id: $doc_id})
        MATCH (s:Statement)
        WHERE s.document_id = $doc_id
          AND NOT exists((s)-[:PART_OF]->())
        MERGE (s)-[:PART_OF]->(d)
        """
        neo4j.run_query(rel_query, {"doc_id": document_id})
        logger.info(f"  ✓ Linked statements to document")

    return stats


def main():
    logger.info("=" * 80)
    logger.info("NOVEMBER 2025 HANSARD IMPORT (from XML)")
    logger.info("=" * 80)

    # Initialize clients
    logger.info("Initializing clients...")
    hansard_client = OurCommonsHansardClient()

    neo4j_uri = os.getenv("NEO4J_URI", "bolt://10.128.0.3:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "canadagpt2024")

    neo4j = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
    neo4j.test_connection()

    try:
        # Generate November weekdays
        dates = generate_november_weekdays()
        logger.info(f"Checking {len(dates)} potential sitting days in November 2025...")

        # Import each date
        total_docs = 0
        total_stmts = 0
        successful_dates = []

        for date in dates:
            logger.info(f"\nTrying {date}...")

            # Fetch and parse XML
            sitting = parse_hansard_xml(hansard_client, date)

            if sitting:
                stats = import_sitting_to_neo4j(neo4j, sitting, date)
                total_docs += stats["documents"]
                total_stmts += stats["statements"]
                successful_dates.append(date)
            else:
                logger.debug(f"  No Hansard found for {date}")

        # Summary
        logger.info("=" * 80)
        if total_docs > 0:
            logger.success("✅ NOVEMBER 2025 IMPORT COMPLETE")
            logger.info(f"Documents created: {total_docs}")
            logger.info(f"Statements created: {total_stmts}")
            logger.info(f"Successful dates: {', '.join(successful_dates)}")
        else:
            logger.warning("⚠️  No Hansard documents found for November 2025")
        logger.info("=" * 80)

    finally:
        neo4j.close()


if __name__ == "__main__":
    main()
