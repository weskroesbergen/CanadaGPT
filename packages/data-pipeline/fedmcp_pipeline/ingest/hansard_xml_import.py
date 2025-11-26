"""
Direct Hansard XML import with enhanced metadata extraction.

This module provides direct XML-to-Neo4j ingestion for Hansard documents,
capturing all rich metadata that was previously ignored, including:
- Person database IDs (Affiliation@DbId)
- Role type codes (1=PM, 2=MP, 15=Speaker, etc.)
- Paragraph IDs for precise citations
- Structured timestamps (hour/minute)
- Floor language and intervention types
- Document-level metadata (creation time, parliament/session numbers, etc.)
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add fedmcp package to path
FEDMCP_PATH = Path(__file__).parent.parent.parent.parent / "fedmcp" / "src"
sys.path.insert(0, str(FEDMCP_PATH))

from fedmcp.clients.ourcommons import OurCommonsHansardClient
from fedmcp.clients.openparliament import OpenParliamentClient

from ..utils.neo4j_client import Neo4jClient
from ..utils.progress import logger, ProgressTracker


class HansardXMLImporter:
    """
    Import Hansard data directly from XML with enhanced metadata.

    This importer:
    1. Fetches document list from OpenParliament API (for document IDs/dates)
    2. Downloads XML directly from House of Commons
    3. Parses with enhanced metadata extraction
    4. Imports to Neo4j with full fidelity
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient,
        start_date: str = "2024-01-01",
        op_client: Optional[OpenParliamentClient] = None
    ):
        """
        Initialize Hansard XML importer.

        Args:
            neo4j_client: Neo4j client instance
            start_date: Import documents from this date forward (YYYY-MM-DD)
            op_client: Optional OpenParliamentClient (for document list)
        """
        self.neo4j = neo4j_client
        self.start_date = start_date
        self.op_client = op_client or OpenParliamentClient()
        self.hansard_client = OurCommonsHansardClient()

    def import_hansard_documents(
        self,
        limit: Optional[int] = None,
        batch_size: int = 1000
    ) -> Dict[str, int]:
        """
        Import Hansard documents and statements from XML.

        Args:
            limit: Maximum number of documents to import (None = all)
            batch_size: Batch size for Neo4j operations

        Returns:
            Dict with import statistics
        """
        logger.info(f"Importing Hansard documents since {self.start_date} from XML...")

        stats = {
            "documents": 0,
            "statements": 0,
            "skipped": 0,
            "errors": 0
        }

        # Get list of Hansard documents from OpenParliament API
        logger.info("Fetching document list from OpenParliament API...")
        documents_to_import = []

        for debate in self.op_client.list_debates():
            debate_date = debate.get("date")

            # Filter by date
            if debate_date and debate_date < self.start_date:
                continue

            # Get document URL/slug
            url = debate.get("url", "")
            doc_id = url.split("/")[-2] if url else None

            if not doc_id:
                logger.warning(f"Skipping debate with no ID: {debate}")
                continue

            documents_to_import.append({
                "id": doc_id,
                "date": debate_date,
                "url": url,
                "session": debate.get("session"),
                "parliament": debate.get("parliament")
            })

            if limit and len(documents_to_import) >= limit:
                break

        logger.info(f"Found {len(documents_to_import)} documents to import")

        if not documents_to_import:
            logger.warning("No documents found to import")
            return stats

        # Process each document
        tracker = ProgressTracker(
            total=len(documents_to_import),
            desc="Importing Hansard documents"
        )

        for doc_info in documents_to_import:
            try:
                # Fetch and parse XML
                logger.debug(f"Fetching XML for {doc_info['id']}...")
                sitting = self.hansard_client.get_sitting(doc_info['url'], parse=True)

                # Import document
                self._import_document(sitting, doc_info, batch_size)
                stats["documents"] += 1

                # Import statements from document
                stmt_count = self._import_statements(sitting, doc_info, batch_size)
                stats["statements"] += stmt_count

                tracker.update(1)

            except Exception as e:
                logger.error(f"Error importing {doc_info['id']}: {e}")
                stats["errors"] += 1
                tracker.update(1)
                continue

        tracker.close()

        logger.success(f"✅ Imported {stats['documents']} documents, {stats['statements']} statements")
        if stats["errors"] > 0:
            logger.warning(f"⚠️  {stats['errors']} errors occurred")

        return stats

    def _import_document(
        self,
        sitting: Any,
        doc_info: Dict[str, Any],
        batch_size: int
    ) -> None:
        """Import a single Hansard document with enhanced metadata."""

        document_data = {
            "id": doc_info["id"],
            "date": sitting.date or doc_info["date"],
            "number": sitting.number,
            "session_id": doc_info.get("session"),
            "document_type": "D",  # Debates
            "source_id": doc_info.get("parliament"),
            "downloaded": True,
            "public": True,
            "xml_source_url": sitting.source_xml_url,
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Enhanced document metadata
        if sitting.creation_timestamp:
            document_data["creation_timestamp"] = sitting.creation_timestamp

        if sitting.speaker_of_day:
            document_data["speaker_of_day"] = sitting.speaker_of_day

        if sitting.hansard_document_id:
            document_data["hansard_document_id"] = sitting.hansard_document_id

        if sitting.parliament_number is not None:
            document_data["parliament_number"] = sitting.parliament_number

        if sitting.session_number is not None:
            document_data["session_number"] = sitting.session_number

        if sitting.volume:
            document_data["volume"] = sitting.volume

        # Filter None values
        document_data = {k: v for k, v in document_data.items() if v is not None}

        # Import to Neo4j
        self.neo4j.batch_merge_nodes(
            "Document",
            [document_data],
            merge_keys=["id"],
            batch_size=batch_size
        )

    def _import_statements(
        self,
        sitting: Any,
        doc_info: Dict[str, Any],
        batch_size: int
    ) -> int:
        """Import statements from a sitting with enhanced metadata."""

        all_speeches = [
            speech
            for section in sitting.sections
            for speech in section.speeches
        ]

        if not all_speeches:
            return 0

        statements_data = []
        mp_link_data = []  # For creating MADE_BY relationships using person_db_id

        for idx, speech in enumerate(all_speeches):
            # Generate statement ID (use intervention_id if available, else generate)
            stmt_id = speech.intervention_id or f"{doc_info['id']}-{idx}"

            statement_props = {
                "id": stmt_id,
                "document_id": doc_info["id"],
                "who_en": speech.speaker_name,
                "content_en": speech.text[:10000] if speech.text else "",  # Limit size
                "statement_type": "debate",
                "wordcount": len(speech.text.split()) if speech.text else 0,
                "updated_at": datetime.utcnow().isoformat(),
            }

            # Add party and riding if available
            if speech.party:
                statement_props["party"] = speech.party

            if speech.riding:
                statement_props["riding"] = speech.riding

            # Add timecode
            if speech.timecode:
                statement_props["time"] = speech.timecode

            # Enhanced metadata fields
            if speech.person_db_id is not None:
                statement_props["person_db_id"] = speech.person_db_id
                # Track for MP linking
                mp_link_data.append({
                    "statement_id": stmt_id,
                    "person_db_id": speech.person_db_id
                })

            if speech.role_type_code is not None:
                statement_props["role_type_code"] = speech.role_type_code

            if speech.intervention_id:
                statement_props["intervention_id"] = speech.intervention_id

            if speech.paragraph_ids:
                # Store as JSON array string
                import json
                statement_props["paragraph_ids"] = json.dumps(speech.paragraph_ids)

            if speech.timestamp_hour is not None:
                statement_props["timestamp_hour"] = speech.timestamp_hour

            if speech.timestamp_minute is not None:
                statement_props["timestamp_minute"] = speech.timestamp_minute

            if speech.floor_language:
                statement_props["floor_language"] = speech.floor_language

            if speech.intervention_type:
                statement_props["intervention_type"] = speech.intervention_type

            # Filter None values
            statement_props = {k: v for k, v in statement_props.items() if v is not None}
            statements_data.append(statement_props)

        # Batch import statements
        if statements_data:
            self.neo4j.batch_merge_nodes(
                "Statement",
                statements_data,
                merge_keys=["id"],
                batch_size=batch_size
            )

            # Create PART_OF relationships (statements -> document)
            rel_query = """
            MATCH (d:Document {id: $doc_id})
            UNWIND $stmt_ids AS stmt_id
            MATCH (s:Statement {id: stmt_id})
            MERGE (s)-[:PART_OF]->(d)
            """
            self.neo4j.run_query(rel_query, {
                "doc_id": doc_info["id"],
                "stmt_ids": [s["id"] for s in statements_data]
            })

            # Create MADE_BY relationships using person_db_id
            if mp_link_data:
                self._link_statements_to_mps(mp_link_data)

        return len(statements_data)

    def _link_statements_to_mps(self, link_data: List[Dict[str, Any]]) -> None:
        """
        Link statements to MPs using person_db_id.

        This uses the stable House of Commons person database ID to match
        statements to MPs, which is more reliable than name matching.
        """
        if not link_data:
            return

        # Link using person_db_id -> parl_mp_id
        link_query = """
        UNWIND $links AS link
        MATCH (s:Statement {id: link.statement_id})
        MATCH (mp:MP {parl_mp_id: link.person_db_id})
        MERGE (s)-[:MADE_BY]->(mp)
        """

        result = self.neo4j.run_query(link_query, {"links": link_data})
        logger.debug(f"Linked {len(link_data)} statements to MPs using person_db_id")

        # Create SPOKE_AT relationships from MP to Document
        # Creates ONE relationship per statement (multiple per MP-Document pair)
        # Enables detailed tracking of when/what MPs said in each debate
        spoke_at_query = """
        UNWIND $links AS link
        MATCH (s:Statement {id: link.statement_id})
        MATCH (mp:MP {parl_mp_id: link.person_db_id})
        MATCH (s)-[:PART_OF]->(d:Document)
        WHERE NOT exists {
            MATCH (mp)-[r:SPOKE_AT]->(d)
            WHERE r.statement_id = s.id
        }
        CREATE (mp)-[r:SPOKE_AT]->(d)
        SET r.timestamp = s.time,
            r.statement_id = s.id,
            r.intervention_id = s.intervention_id,
            r.person_db_id = s.person_db_id
        """

        self.neo4j.run_query(spoke_at_query, {"links": link_data})
        logger.debug(f"Created SPOKE_AT relationships for {len(link_data)} statements")
