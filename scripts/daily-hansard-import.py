#!/usr/bin/env python3
"""Daily Hansard import job - checks for new debates and imports them with enhanced metadata."""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json
import requests

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'packages' / 'data-pipeline'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'packages' / 'fedmcp' / 'src'))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger
from fedmcp.clients.ourcommons import OurCommonsHansardClient
from fedmcp_pipeline.ingest.hansard import link_statements_to_mps_by_name


def parse_hansard_with_enhanced_metadata(xml_text: str, source_url: str) -> Dict[str, Any]:
    """Parse Hansard XML with enhanced metadata extraction using OurCommonsHansardClient."""
    client = OurCommonsHansardClient()
    sitting = client.parse_sitting(xml_text, source_url=source_url)

    logger.info(f"Parsing Hansard No. {sitting.number}, Date: {sitting.date}")

    # Extract speeches with enhanced metadata from all sections
    speeches = []
    for section in sitting.sections:
        # Use section title as h1_en
        h1_en = section.title

        for speech in section.speeches:
            speeches.append({
                # Basic fields
                "speaker_name": speech.speaker_name,
                "timecode": speech.timecode,
                "text": speech.text,
                "h1_en": h1_en,
                "h2_en": None,  # Not extracted in current structure
                # Enhanced metadata fields
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

    logger.info(f"Extracted {len(speeches)} speeches with enhanced metadata")

    return {
        "number": sitting.number,
        "date": sitting.date,
        "speeches": speeches,
        # Enhanced document metadata
        "creation_timestamp": sitting.creation_timestamp,
        "speaker_of_day": sitting.speaker_of_day,
        "hansard_document_id": sitting.hansard_document_id,
        "parliament_number": sitting.parliament_number,
        "session_number": sitting.session_number,
        "volume": sitting.volume,
    }


def import_hansard_to_neo4j(neo4j: Neo4jClient, hansard_data: Dict[str, Any], iso_date: str, document_id: int, sitting_number: str):
    """Import parsed Hansard to Neo4j with enhanced metadata."""
    logger.info(f"Importing Hansard to Neo4j as Document {document_id}...")

    # Delete existing document if it exists
    neo4j.run_query("MATCH (d:Document {id: $doc_id}) DETACH DELETE d", {"doc_id": document_id})

    # Create Document node with enhanced metadata
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

    # Add enhanced document metadata
    if hansard_data.get("creation_timestamp"):
        document_data["creation_timestamp"] = hansard_data["creation_timestamp"]
    if hansard_data.get("speaker_of_day"):
        document_data["speaker_of_day"] = hansard_data["speaker_of_day"]
    if hansard_data.get("hansard_document_id"):
        document_data["hansard_document_id"] = hansard_data["hansard_document_id"]
    if hansard_data.get("parliament_number") is not None:
        document_data["parliament_number"] = hansard_data["parliament_number"]
    if hansard_data.get("session_number") is not None:
        document_data["session_number"] = hansard_data["session_number"]
    if hansard_data.get("volume"):
        document_data["volume"] = hansard_data["volume"]

    cypher = """
        CREATE (d:Document)
        SET d = $doc
        SET d.updated_at = datetime()
        RETURN d.id as created_id
    """
    result = neo4j.run_query(cypher, {"doc": document_data})
    logger.success(f"✓ Created Document node: {result[0]['created_id']}")

    # Create Statement nodes with enhanced metadata
    statements_data = []
    mp_link_data = []  # For person_db_id-based MP linking

    for idx, speech in enumerate(hansard_data["speeches"], start=1):
        # Use intervention_id if available, otherwise generate
        statement_id = speech.get("intervention_id") or f"{document_id}-{idx}"
        wordcount = len(speech["text"].split()) if speech["text"] else 0

        statement = {
            "id": statement_id,
            "document_id": document_id,
            "time": f"{iso_date}T{speech['timecode']}" if speech.get("timecode") else None,
            "who_en": speech.get("speaker_name") or "",
            "content_en": (speech.get("text") or "")[:10000],  # Limit content size
            "h1_en": speech.get("h1_en"),
            "h2_en": speech.get("h2_en"),
            "statement_type": "speech",
            "wordcount": wordcount,
            "procedural": False,
        }

        # Add enhanced metadata fields
        if speech.get("person_db_id") is not None:
            statement["person_db_id"] = speech["person_db_id"]
            mp_link_data.append({
                "statement_id": statement_id,
                "person_db_id": speech["person_db_id"]
            })

        if speech.get("role_type_code") is not None:
            statement["role_type_code"] = speech["role_type_code"]

        if speech.get("intervention_id"):
            statement["intervention_id"] = speech["intervention_id"]

        if speech.get("paragraph_ids"):
            statement["paragraph_ids"] = json.dumps(speech["paragraph_ids"])

        if speech.get("timestamp_hour") is not None:
            statement["timestamp_hour"] = speech["timestamp_hour"]

        if speech.get("timestamp_minute") is not None:
            statement["timestamp_minute"] = speech["timestamp_minute"]

        if speech.get("floor_language"):
            statement["floor_language"] = speech["floor_language"]

        if speech.get("intervention_type"):
            statement["intervention_type"] = speech["intervention_type"]

        if speech.get("party"):
            statement["party"] = speech["party"]

        if speech.get("riding"):
            statement["riding"] = speech["riding"]

        statements_data.append(statement)

    cypher = """
        UNWIND $statements AS stmt
        CREATE (s:Statement)
        SET s = stmt
        SET s.updated_at = datetime()
        RETURN count(s) as created_count
    """
    result = neo4j.run_query(cypher, {"statements": statements_data})
    logger.success(f"✓ Created {result[0]['created_count']} Statement nodes with enhanced metadata")

    # Link statements to document
    cypher = """
        MATCH (s:Statement {document_id: $doc_id})
        MATCH (d:Document {id: $doc_id})
        MERGE (s)-[:PART_OF]->(d)
        RETURN count(*) as linked
    """
    result = neo4j.run_query(cypher, {"doc_id": document_id})
    logger.success(f"✓ Created {result[0]['linked']} PART_OF relationships")

    # Link statements to MPs using hansard_db_id (exact matching) with name matching fallback
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


def get_latest_document_id(neo4j: Neo4jClient) -> int:
    """Get the highest document ID currently in the database."""
    result = neo4j.run_query("""
        MATCH (d:Document)
        RETURN max(d.id) as max_id
    """)
    return result[0]['max_id'] if result and result[0]['max_id'] else 25000


def check_and_import_recent_debates(neo4j: Neo4jClient, lookback_days: int = 7):
    """Check for and import any missing debates from the last N days."""
    imported_count = 0

    # Get dates to check (last N days)
    dates_to_check = []
    for i in range(lookback_days, -1, -1):
        date = datetime.now() - timedelta(days=i)
        # Skip weekends (House doesn't sit on weekends)
        if date.weekday() < 5:  # Monday = 0, Friday = 4
            dates_to_check.append(date.strftime('%Y-%m-%d'))

    logger.info(f"Checking for debates on dates: {dates_to_check}")

    # Check which dates already exist
    result = neo4j.run_query("""
        MATCH (d:Document)
        WHERE d.date IN $dates
        RETURN d.date as date
    """, {"dates": dates_to_check})

    existing_dates = {row['date'] for row in result}
    missing_dates = [d for d in dates_to_check if d not in existing_dates]

    logger.info(f"Already imported: {existing_dates}")
    logger.info(f"Missing dates to check: {missing_dates}")

    # Try to import each missing date
    for date_str in missing_dates:
        # Try sitting numbers around expected range
        # House typically has 100-150 sittings per session
        # We'll try a range based on recent patterns
        latest_doc_id = get_latest_document_id(neo4j)

        # Try to find the XML by testing sitting numbers
        for sitting_offset in range(0, 10):  # Check up to 10 sitting numbers ahead
            # Estimate sitting number based on existing data
            # Get the latest sitting number we have
            result = neo4j.run_query("""
                MATCH (d:Document)
                WHERE d.number IS NOT NULL
                WITH d.number as num
                ORDER BY d.date DESC
                LIMIT 1
                RETURN num
            """)

            if result and result[0]['num']:
                # Extract sitting number from "No. 053"
                latest_sitting = int(result[0]['num'].replace('No. ', '').strip())
                sitting_num = latest_sitting + sitting_offset + 1
            else:
                # Fallback if we can't determine
                sitting_num = 50 + sitting_offset

            sitting_str = str(sitting_num).zfill(3)
            xml_url = f"https://www.ourcommons.ca/Content/House/451/Debates/{sitting_str}/HAN{sitting_str}-E.XML"

            logger.info(f"Checking {date_str} sitting {sitting_str}: {xml_url}")

            try:
                response = requests.head(xml_url, timeout=10)
                if response.status_code == 200:
                    logger.info(f"✓ Found XML for {date_str} at sitting {sitting_str}")

                    # Fetch and import
                    response = requests.get(xml_url, headers={"Accept": "application/xml"})
                    response.raise_for_status()
                    xml_text = response.content.decode('utf-8-sig')

                    hansard_data = parse_hansard_with_enhanced_metadata(xml_text, source_url=xml_url)

                    # Parse the verbose date from XML to ISO format
                    try:
                        # Parse date like "Monday, November 17, 2025" to ISO "2025-11-17"
                        parsed_date = datetime.strptime(hansard_data['date'], '%A, %B %d, %Y')
                        iso_date = parsed_date.strftime('%Y-%m-%d')

                        # Import if we don't already have this sitting number
                        # (date might not match expected due to recesses, but that's OK)
                        document_id = latest_doc_id + 1
                        stmt_count, linked_count = import_hansard_to_neo4j(
                            neo4j, hansard_data, iso_date,
                            document_id, sitting_str
                        )
                        logger.success(f"✅ Imported sitting {sitting_str} ({iso_date}): {stmt_count} statements, {linked_count} linked")
                        imported_count += 1
                        break
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not parse date '{hansard_data['date']}': {e}")

            except requests.exceptions.RequestException as e:
                if hasattr(e.response, 'status_code') and e.response.status_code == 404:
                    # 404 is expected, keep trying
                    continue
                logger.error(f"Error fetching {xml_url}: {e}")

    return imported_count


def main():
    """Main entry point for daily import job."""
    logger.info("=" * 80)
    logger.info("DAILY HANSARD IMPORT JOB")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("=" * 80)

    # Get Neo4j connection from environment
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://10.128.0.3:7687')
    neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD')

    if not neo4j_password:
        logger.error("NEO4J_PASSWORD environment variable not set")
        sys.exit(1)

    neo4j = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)

    try:
        # Check for debates from last 7 days
        imported = check_and_import_recent_debates(neo4j, lookback_days=7)

        logger.info("=" * 80)
        if imported > 0:
            logger.success(f"✅ Successfully imported {imported} new debate(s)")
        else:
            logger.info("ℹ️  No new debates found")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Job failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        neo4j.close()


if __name__ == "__main__":
    main()
