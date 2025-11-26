#!/usr/bin/env python3
"""
Enhanced November 2025 Hansard import with proper topic extraction.

Extracts full metadata from Hansard XML:
- OrderOfBusiness titles for h1_en (e.g., "Government Orders", "Oral Questions")
- SubjectOfBusiness titles for h2_en (e.g., "The Budget", "Agriculture and Agri-Food")
- Proper integer document IDs
- Fixed date handling (no timezone issues)
"""

import os
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from xml.etree import ElementTree as ET

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
    match = re.search(r'(\w+)\s+(\d+),\s+(\d+)$', date_str)
    if match:
        month_name, day, year = match.groups()
        parsed = datetime.strptime(f"{month_name} {day}, {year}", "%B %d, %Y")
        return parsed.strftime("%Y-%m-%d")
    return date_str


def get_next_document_id(neo4j: Neo4jClient) -> int:
    """Get the next available document ID."""
    result = neo4j.run_query("""
        MATCH (d:Document)
        WHERE d.id IS NOT NULL AND toString(d.id) =~ '\\d+'
        RETURN max(toInteger(d.id)) as max_id
    """)
    max_id = result[0]['max_id'] if result else 0
    return (max_id or 0) + 1


def parse_hansard_with_topics(xml_text: str) -> Dict[str, Any]:
    """Parse Hansard XML extracting full hierarchy: OrderOfBusiness > SubjectOfBusiness > Intervention."""

    # Strip UTF-8 BOM if present
    if xml_text.startswith('\ufeff'):
        xml_text = xml_text[1:]

    tree = ET.fromstring(xml_text)

    # Extract metadata
    date = None
    number = None
    extracted_info = tree.find(".//ExtractedInformation")
    if extracted_info is not None:
        for item in extracted_info.findall("ExtractedItem"):
            name = item.get("Name", "")
            if name == "Date":
                date = item.text
            elif name == "Number":
                number = item.text

    # Parse hierarchical structure
    speeches_with_topics = []

    # Find all OrderOfBusiness elements
    orders = tree.findall(".//OrderOfBusiness")

    for order in orders:
        # Get OrderOfBusiness title (h1_en)
        order_title_el = order.find("OrderOfBusinessTitle")
        order_title = "".join(order_title_el.itertext()).strip() if order_title_el is not None else "Hansard Proceedings"

        # Get all SubjectOfBusiness under this order
        subjects = order.findall(".//SubjectOfBusiness")

        for subject in subjects:
            # Get SubjectOfBusiness title (h2_en)
            subject_title_el = subject.find("SubjectOfBusinessTitle")
            subject_title = "".join(subject_title_el.itertext()).strip() if subject_title_el is not None else ""

            # Get all interventions under this subject
            content = subject.find("SubjectOfBusinessContent")
            if content is not None:
                interventions = content.findall(".//Intervention")

                for interv in interventions:
                    # Parse speaker info
                    person = interv.find("PersonSpeaking")
                    speaker_name = None
                    speaker_id = None
                    party = None
                    riding = None

                    if person is not None:
                        affiliation = person.findtext("Affiliation", "")
                        if affiliation:
                            speaker_name = affiliation.split("(")[0].strip() if "(" in affiliation else affiliation
                            if "(" in affiliation and ")" in affiliation:
                                paren_content = affiliation[affiliation.index("(") + 1:affiliation.rindex(")")]
                                parts = paren_content.split(",")
                                if len(parts) >= 2:
                                    riding = parts[0].strip()
                                    party = parts[1].strip()
                                elif len(parts) == 1:
                                    riding = parts[0].strip()

                    # Extract timecode
                    timecode = interv.findtext("time")

                    # Extract text from Content/ParaText elements
                    content_el = interv.find("Content")
                    paragraphs = []
                    if content_el is not None:
                        for para_text in content_el.findall(".//ParaText"):
                            text = "".join(para_text.itertext()).strip()
                            if text:
                                paragraphs.append(text)

                    speech_text = "\n\n".join(paragraphs)

                    speeches_with_topics.append({
                        "h1_en": order_title,
                        "h2_en": subject_title if subject_title else None,
                        "speaker_name": speaker_name,
                        "speaker_id": speaker_id,
                        "party": party,
                        "riding": riding,
                        "timecode": timecode,
                        "text": speech_text,
                    })

    return {
        "date": date,
        "number": number,
        "speeches": speeches_with_topics,
    }


def import_hansard_to_neo4j(neo4j: Neo4jClient, hansard_data: Dict[str, Any], iso_date: str, document_id: int) -> Dict[str, int]:
    """Import parsed Hansard to Neo4j with full metadata."""
    stats = {"documents": 0, "statements": 0}

    if not hansard_data["speeches"]:
        return stats

    # Create Document node with INTEGER ID
    document_data = [{
        "id": document_id,  # INTEGER
        "date": iso_date,
        "session_id": "45-1",
        "document_type": "D",
        "public": True,
        "source": "ourcommons_xml_enhanced",
        "number": hansard_data["number"],  # Keep as string "No. 053"
        "updated_at": datetime.utcnow().isoformat(),
    }]

    neo4j.batch_merge_nodes("Document", document_data, merge_keys=["id"])
    stats["documents"] = 1
    logger.info(f"  ✓ Created Document: {document_id}")

    # Create Statement nodes from speeches
    statements_data = []
    for idx, speech in enumerate(hansard_data["speeches"], 1):
        statement_id = f"{document_id}-{idx}"
        wordcount = len(speech["text"].split()) if speech["text"] else 0

        statements_data.append({
            "id": statement_id,
            "document_id": document_id,  # INTEGER reference
            "time": f"{iso_date}T{speech['timecode']}" if speech["timecode"] else f"{iso_date}T12:00:00",
            "who_en": speech["speaker_name"] or "",
            "politician_id": speech["speaker_id"],
            "content_en": speech["text"] or "",
            "h1_en": speech["h1_en"],  # e.g., "Government Orders", "Oral Questions"
            "h2_en": speech["h2_en"],  # e.g., "The Budget", "Agriculture and Agri-Food"
            "statement_type": "speech",
            "wordcount": wordcount,
            "procedural": False,
            "updated_at": datetime.utcnow().isoformat(),
        })

    if statements_data:
        neo4j.batch_merge_nodes("Statement", statements_data, merge_keys=["id"], batch_size=1000)
        stats["statements"] = len(statements_data)
        logger.info(f"  ✓ Created {len(statements_data)} statements with topics")

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
    logger.info("NOVEMBER 2025 HANSARD IMPORT - ENHANCED WITH TOPICS")
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
        # Get next available document ID
        document_id = get_next_document_id(neo4j)
        logger.info(f"Using document ID: {document_id}")

        # Fetch latest Hansard XML (unparsed)
        logger.info("Fetching latest Hansard XML...")
        xml_text = hansard_client.get_sitting("latest/hansard", parse=False)

        if not xml_text:
            logger.warning("No Hansard XML found")
            return

        # Parse with enhanced topic extraction
        logger.info("Parsing Hansard with topic extraction...")
        hansard_data = parse_hansard_with_topics(xml_text)

        logger.info(f"Found Hansard: {hansard_data['date']} ({hansard_data['number']})")
        logger.info(f"Extracted {len(hansard_data['speeches'])} speeches with topics")

        # Parse date
        iso_date = parse_hansard_date(hansard_data['date'])
        logger.info(f"Parsed date: {iso_date}")

        # Delete old import if it exists (in case we're re-running)
        logger.info("Checking for existing document 25598...")
        delete_result = neo4j.run_query("""
            MATCH (d:Document {id: 25598})
            OPTIONAL MATCH (s:Statement)-[:PART_OF]->(d)
            DETACH DELETE s, d
            RETURN count(d) as deleted
        """)
        if delete_result and delete_result[0]['deleted'] > 0:
            logger.info("  ✓ Deleted old document 25598")

        # Import to Neo4j
        stats = import_hansard_to_neo4j(neo4j, hansard_data, iso_date, document_id)

        # Summary
        logger.info("=" * 80)
        logger.success(f"✅ IMPORTED HANSARD FOR {iso_date}")
        logger.info(f"Document ID: {document_id}")
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
