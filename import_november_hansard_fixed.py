#!/usr/bin/env python3
"""
Import November 2025 Hansard using OurCommonsHansardClient (XML from DocumentViewer).

Uses correct OurCommonsHansardClient dataclass attributes.
"""

import os
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages" / "fedmcp" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "packages" / "data-pipeline"))

from fedmcp.clients.ourcommons import OurCommonsHansardClient
from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger


def parse_hansard_date(date_str: str) -> str:
    """Parse Hansard date string to YYYY-MM-DD format.

    Input: "Friday, November 7, 2025"
    Output: "2025-11-07"
    """
    # Try to extract date components from string like "Friday, November 7, 2025"
    match = re.search(r'(\w+)\s+(\d+),\s+(\d+)$', date_str)
    if match:
        month_name, day, year = match.groups()
        # Parse using strptime
        parsed = datetime.strptime(f"{month_name} {day}, {year}", "%B %d, %Y")
        return parsed.strftime("%Y-%m-%d")

    # Fallback - return as-is if parsing fails
    return date_str


def import_sitting_to_neo4j(neo4j: Neo4jClient, sitting: Any, iso_date: str) -> Dict[str, int]:
    """Import a parsed Hansard sitting to Neo4j."""
    stats = {"documents": 0, "statements": 0}

    if not sitting or not sitting.sections:
        return stats

    # Create Document node
    document_id = f"hansard-{iso_date}"
    document_data = [{
        "id": document_id,
        "date": iso_date,
        "session_id": "45-1",  # Current parliament session
        "document_type": "D",  # Debates
        "public": True,
        "source": "ourcommons_xml",
        "number": sitting.number,
        "updated_at": datetime.utcnow().isoformat(),
    }]

    neo4j.batch_merge_nodes("Document", document_data, merge_keys=["id"])
    stats["documents"] = 1
    logger.info(f"  ✓ Created Document: {document_id}")

    # Create Statement nodes from speeches
    statements_data = []
    stmt_counter = 0

    for section in sitting.sections:
        section_title = section.title or "Hansard Proceedings"

        for speech in section.speeches:
            stmt_counter += 1
            statement_id = f"{document_id}-stmt-{stmt_counter}"

            # Calculate word count from text
            wordcount = len(speech.text.split()) if speech.text else 0

            statements_data.append({
                "id": statement_id,
                "document_id": document_id,
                "time": f"{iso_date}T{speech.timecode}" if speech.timecode else f"{iso_date}T12:00:00",
                "who_en": speech.speaker_name or "",
                "politician_id": speech.speaker_id,
                "content_en": speech.text or "",
                "h1_en": section_title,
                "statement_type": "speech",
                "wordcount": wordcount,
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
        # Fetch latest Hansard
        logger.info("Fetching latest Hansard...")
        sitting = hansard_client.get_sitting("latest/hansard", parse=True)

        if not sitting:
            logger.warning("No Hansard data found")
            return

        # Parse date
        logger.info(f"Found Hansard: {sitting.date} (No. {sitting.number})")
        iso_date = parse_hansard_date(sitting.date)
        logger.info(f"Parsed date: {iso_date}")

        # Import to Neo4j
        stats = import_sitting_to_neo4j(neo4j, sitting, iso_date)

        # Summary
        logger.info("=" * 80)
        logger.success(f"✅ IMPORTED HANSARD FOR {iso_date}")
        logger.info(f"Documents created: {stats['documents']}")
        logger.info(f"Statements created: {stats['statements']}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Import failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        neo4j.close()


if __name__ == "__main__":
    main()
