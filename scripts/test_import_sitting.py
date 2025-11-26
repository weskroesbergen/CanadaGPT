#!/usr/bin/env python3
"""Test import of a specific sitting with the new hansard_db_id matching."""

import sys
import os
from pathlib import Path
from datetime import datetime
import requests

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'packages' / 'data-pipeline'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'packages' / 'fedmcp' / 'src'))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger
from fedmcp.clients.ourcommons import OurCommonsHansardClient
from fedmcp_pipeline.ingest.hansard import link_statements_to_mps_by_name
from typing import Dict, Any
import json


def parse_hansard_with_enhanced_metadata(xml_text: str, source_url: str) -> Dict[str, Any]:
    """Parse Hansard XML with enhanced metadata extraction."""
    client = OurCommonsHansardClient()
    sitting = client.parse_sitting(xml_text, source_url=source_url)

    speeches = []
    for section in sitting.sections:
        h1_en = section.title
        for speech in section.speeches:
            speeches.append({
                "speaker_name": speech.speaker_name,
                "timecode": speech.timecode,
                "text": speech.text,
                "h1_en": h1_en,
                "h2_en": None,
                "person_db_id": speech.person_db_id,
                "role_type_code": speech.role_type_code,
                "intervention_id": speech.intervention_id,
                "paragraph_ids": speech.paragraph_ids,
                "timestamp_hour": speech.timestamp_hour,
                "timestamp_minute": speech.timestamp_minute,
                "floor_language": speech.floor_language,
                "intervention_type": speech.intervention_type,
                "party": speech.party,
                "riding": speech.riding,
            })

    return {
        "number": sitting.number,
        "date": sitting.date,
        "speeches": speeches,
        "creation_timestamp": sitting.creation_timestamp,
        "speaker_of_day": sitting.speaker_of_day,
        "hansard_document_id": sitting.hansard_document_id,
        "parliament_number": sitting.parliament_number,
        "session_number": sitting.session_number,
        "volume": sitting.volume,
    }


def import_hansard_to_neo4j(neo4j: Neo4jClient, hansard_data: Dict[str, Any], iso_date: str, document_id: int, sitting_number: str):
    """Import parsed Hansard to Neo4j with hansard_db_id matching."""
    # Create Document node
    document_data = {
        "id": document_id,
        "date": iso_date,
        "session_id": "45-1",
        "document_type": "D",
        "public": True,
        "source": "ourcommons_xml_enhanced",
        "number": f"No. {sitting_number}",
        "updated_at": datetime.utcnow().isoformat(),
    }

    cypher = "CREATE (d:Document) SET d = $doc SET d.updated_at = datetime() RETURN d.id as created_id"
    result = neo4j.run_query(cypher, {"doc": document_data})
    logger.success(f"✓ Created Document node: {result[0]['created_id']}")

    # Create Statement nodes
    statements_data = []
    mp_link_data = []

    for idx, speech in enumerate(hansard_data["speeches"], start=1):
        statement_id = speech.get("intervention_id") or f"{document_id}-{idx}"
        wordcount = len(speech["text"].split()) if speech["text"] else 0

        # Format time as ISO-8601 DateTime (Neo4j requires seconds)
        time_value = None
        if speech.get("timecode"):
            timecode = speech["timecode"]
            # Ensure timecode has seconds (HH:MM -> HH:MM:00)
            if len(timecode) == 5 and timecode.count(":") == 1:
                timecode = f"{timecode}:00"
            time_value = f"{iso_date}T{timecode}"

        statement = {
            "id": statement_id,
            "document_id": document_id,
            "time": time_value,
            "who_en": speech.get("speaker_name") or "",
            "content_en": (speech.get("text") or "")[:10000],
            "h1_en": speech.get("h1_en"),
            "h2_en": speech.get("h2_en"),
            "statement_type": "speech",
            "wordcount": wordcount,
            "procedural": False,
        }

        if speech.get("person_db_id") is not None:
            statement["person_db_id"] = speech["person_db_id"]
            mp_link_data.append({
                "statement_id": statement_id,
                "person_db_id": speech["person_db_id"]
            })

        statements_data.append(statement)

    cypher = "UNWIND $statements AS stmt CREATE (s:Statement) SET s = stmt SET s.updated_at = datetime() RETURN count(s) as created_count"
    result = neo4j.run_query(cypher, {"statements": statements_data})
    logger.success(f"✓ Created {result[0]['created_count']} Statement nodes")

    # Link statements to document
    cypher = "MATCH (s:Statement {document_id: $doc_id}) MATCH (d:Document {id: $doc_id}) MERGE (s)-[:PART_OF]->(d) RETURN count(*) as linked"
    result = neo4j.run_query(cypher, {"doc_id": document_id})
    logger.success(f"✓ Created {result[0]['linked']} PART_OF relationships")

    # Link statements to MPs using hansard_db_id with name matching fallback
    linked_by_dbid = 0
    linked_by_name = 0

    if mp_link_data:
        # Try exact DbId matching FIRST
        link_query = """
        UNWIND $links AS link
        MATCH (s:Statement {id: link.statement_id})
        MATCH (mp:MP {hansard_db_id: link.person_db_id})
        MERGE (s)-[:MADE_BY]->(mp)
        RETURN count(*) as linked_count
        """
        result = neo4j.run_query(link_query, {"links": mp_link_data})
        linked_by_dbid = result[0]['linked_count'] if result else 0
        logger.success(f"✓ Linked {linked_by_dbid} statements to MPs using hansard_db_id (exact matching)")

        # Fall back to name matching for unlinked statements
        total_statements = len(hansard_data["speeches"])
        if linked_by_dbid < total_statements:
            logger.info(f"Attempting name matching for {total_statements - linked_by_dbid} unlinked statements...")
            linked_by_name = link_statements_to_mps_by_name(neo4j, document_id)
            logger.success(f"✓ Linked {linked_by_name} statements to MPs using name matching (fallback)")
    else:
        logger.warning("⚠️  No person_db_id data available, using name matching only")
        linked_by_name = link_statements_to_mps_by_name(neo4j, document_id)
        logger.success(f"✓ Linked {linked_by_name} statements to MPs using name matching")

    # Create SPOKE_AT relationships
    spoke_at_query = """
    MATCH (s:Statement)-[:MADE_BY]->(mp:MP), (s)-[:PART_OF]->(d:Document {id: $doc_id})
    MERGE (mp)-[r:SPOKE_AT]->(d)
    SET r.statement_id = s.id, r.person_db_id = s.person_db_id
    RETURN count(DISTINCT r) as spoke_at_count
    """
    result = neo4j.run_query(spoke_at_query, {"doc_id": document_id})
    spoke_at_count = result[0]['spoke_at_count'] if result else 0
    logger.success(f"✓ Created {spoke_at_count} SPOKE_AT relationships")

    total_linked = linked_by_dbid + linked_by_name
    return len(hansard_data["speeches"]), total_linked


def test_import_sitting(neo4j: Neo4jClient, sitting_num: int, document_id: int):
    """Import a specific sitting for testing."""
    sitting_str = str(sitting_num).zfill(3)
    xml_url = f"https://www.ourcommons.ca/Content/House/451/Debates/{sitting_str}/HAN{sitting_str}-E.XML"

    logger.info(f"Fetching sitting {sitting_str} from {xml_url}...")

    try:
        response = requests.get(xml_url, headers={"Accept": "application/xml"}, timeout=30)
        response.raise_for_status()
        xml_text = response.content.decode('utf-8-sig')

        logger.info("Parsing Hansard XML with enhanced metadata...")
        hansard_data = parse_hansard_with_enhanced_metadata(xml_text, source_url=xml_url)

        # Parse date
        parsed_date = datetime.strptime(hansard_data['date'], '%A, %B %d, %Y')
        iso_date = parsed_date.strftime('%Y-%m-%d')

        logger.info(f"Importing {len(hansard_data['speeches'])} speeches for {iso_date}...")
        stmt_count, linked_count = import_hansard_to_neo4j(
            neo4j, hansard_data, iso_date, document_id, sitting_str
        )

        logger.success(f"✅ Import complete: {stmt_count} statements, {linked_count} linked ({linked_count/stmt_count*100:.1f}%)")

        return stmt_count, linked_count

    except Exception as e:
        logger.error(f"Import failed: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0


def main():
    """Main entry point."""
    logger.info("=" * 80)
    logger.info("TEST IMPORT - SITTING 058 (October 30, 2025)")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("=" * 80)
    print()

    # Get Neo4j connection
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD')

    if not neo4j_password:
        logger.error("NEO4J_PASSWORD environment variable not set")
        sys.exit(1)

    neo4j = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)

    try:
        # Import sitting 058 as document 25591 (original ID)
        stmt_count, linked_count = test_import_sitting(neo4j, sitting_num=58, document_id=25591)

        # Verify results
        if stmt_count > 0:
            logger.info("=" * 80)
            logger.info("VERIFICATION")
            logger.info("=" * 80)

            # Check linking by method
            result = neo4j.run_query("""
                MATCH (s:Statement {document_id: 25591})
                WITH count(s) as total
                MATCH (s2:Statement {document_id: 25591})-[:MADE_BY]->(mp:MP)
                WHERE mp.hansard_db_id = s2.person_db_id
                RETURN total, count(s2) as linked_by_dbid
            """)

            if result:
                total = result[0]['total']
                linked_by_dbid = result[0]['linked_by_dbid']
                linked_by_name = linked_count - linked_by_dbid

                logger.info(f"Total statements: {total}")
                logger.info(f"Linked by hansard_db_id (exact): {linked_by_dbid} ({linked_by_dbid/total*100:.1f}%)")
                logger.info(f"Linked by name matching (fallback): {linked_by_name} ({linked_by_name/total*100:.1f}%)")
                logger.info(f"Total linked: {linked_count} ({linked_count/total*100:.1f}%)")

            logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        neo4j.close()


if __name__ == "__main__":
    main()
