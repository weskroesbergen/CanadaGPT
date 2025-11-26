"""
Direct Committee Evidence XML import with full testimony extraction.

This module provides direct XML-to-Neo4j ingestion for committee evidence,
capturing:
- Meeting metadata (date, committee, parliament/session)
- Witness testimony with organization and role
- MP questions and interventions
- Speaker person database IDs for linking
- Testimony text and timestamps
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add fedmcp package to path
FEDMCP_PATH = Path(__file__).parent.parent.parent.parent / "fedmcp" / "src"
sys.path.insert(0, str(FEDMCP_PATH))

from fedmcp.clients.ourcommons_committee_evidence import OurCommonsCommitteeEvidenceClient

from ..utils.neo4j_client import Neo4jClient
from ..utils.progress import logger, ProgressTracker


class CommitteeEvidenceXMLImporter:
    """
    Import committee evidence directly from XML with full metadata.

    This importer:
    1. Fetches committee meeting evidence from DocumentViewer XML
    2. Parses witness testimony and MP interventions
    3. Creates CommitteeEvidence nodes in Neo4j
    4. Creates CommitteeTestimony nodes linked to MPs via person_db_id
    5. Links evidence to Committee and Meeting nodes
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient,
        evidence_client: Optional[OurCommonsCommitteeEvidenceClient] = None
    ):
        """
        Initialize Committee Evidence XML importer.

        Args:
            neo4j_client: Neo4j client instance
            evidence_client: Optional OurCommonsCommitteeEvidenceClient
        """
        self.neo4j = neo4j_client
        self.evidence_client = evidence_client or OurCommonsCommitteeEvidenceClient()

    def import_evidence_for_meetings(
        self,
        committee_code: str,
        meeting_numbers: Optional[List[int]] = None,
        limit: Optional[int] = None,
        skip_existing: bool = True
    ) -> Dict[str, int]:
        """
        Import evidence for committee meetings.

        Args:
            committee_code: Committee acronym (e.g., "FINA", "HESA")
            meeting_numbers: List of meeting numbers to import (None = get from Neo4j)
            limit: Maximum number of meetings to import (None = all)
            skip_existing: Skip meetings that already have evidence in Neo4j

        Returns:
            Dict with import statistics
        """
        logger.info(f"Importing committee evidence for {committee_code}...")

        stats = {
            "meetings": 0,
            "testimonies": 0,
            "skipped": 0,
            "errors": 0
        }

        # If no meeting numbers provided, get them from Neo4j
        if meeting_numbers is None:
            meeting_numbers = self._get_meeting_numbers_from_neo4j(committee_code)
            logger.info(f"Found {len(meeting_numbers)} meetings for {committee_code} in Neo4j")

        if not meeting_numbers:
            logger.warning(f"No meetings found for {committee_code}")
            return stats

        # Sort descending (newest first)
        meeting_numbers = sorted(meeting_numbers, reverse=True)

        if limit:
            meeting_numbers = meeting_numbers[:limit]
            logger.info(f"Limited to {limit} most recent meetings")

        # Get existing evidence if skipping
        existing_evidence = set()
        if skip_existing:
            result = self.neo4j.run_query("""
                MATCH (e:CommitteeEvidence)
                WHERE e.committee_code = $committee_code
                RETURN e.meeting_number as meeting_number
            """, {"committee_code": committee_code})
            existing_evidence = {row['meeting_number'] for row in result}
            logger.info(f"Found {len(existing_evidence)} existing evidence records in Neo4j")

        # Process each meeting
        tracker = ProgressTracker(
            total=len(meeting_numbers),
            desc=f"Importing {committee_code} evidence"
        )

        for meeting_number in meeting_numbers:
            try:
                # Skip if already exists
                if skip_existing and meeting_number in existing_evidence:
                    stats["skipped"] += 1
                    tracker.update(1)
                    continue

                # Fetch evidence XML and parse
                meeting = self.evidence_client.get_evidence(
                    committee_code=committee_code,
                    meeting_number=meeting_number,
                    parse=True
                )

                # Import evidence and testimonies to Neo4j
                testimony_count = self._import_evidence(meeting)
                stats["meetings"] += 1
                stats["testimonies"] += testimony_count

                tracker.update(1)

            except Exception as e:
                logger.error(f"Error importing evidence for {committee_code}/{meeting_number}: {e}")
                stats["errors"] += 1
                tracker.update(1)
                continue

        tracker.close()

        logger.success(f"✅ Imported evidence for {stats['meetings']} meetings, {stats['testimonies']} testimonies")
        if stats["skipped"] > 0:
            logger.info(f"ℹ️  Skipped {stats['skipped']} existing meetings")
        if stats["errors"] > 0:
            logger.warning(f"⚠️  {stats['errors']} errors occurred")

        return stats

    def _get_meeting_numbers_from_neo4j(self, committee_code: str) -> List[int]:
        """Get meeting numbers for a committee from Neo4j."""
        result = self.neo4j.run_query("""
            MATCH (m:Meeting)
            WHERE m.committee_code = $committee_code
              AND m.number IS NOT NULL
            RETURN DISTINCT m.number as meeting_number
            ORDER BY meeting_number DESC
        """, {"committee_code": committee_code})

        return [row['meeting_number'] for row in result]

    def _import_evidence(self, meeting: Any) -> int:
        """Import evidence and testimonies for a single meeting."""

        # Generate unique ID for evidence
        evidence_id = f"{meeting.committee_code}-{meeting.meeting_number}"

        # Create CommitteeEvidence node
        evidence_data = {
            "id": evidence_id,
            "committee_code": meeting.committee_code,
            "meeting_number": int(meeting.meeting_number) if meeting.meeting_number else 0,
            "source_xml_url": meeting.source_xml_url,
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Add optional fields
        if meeting.date:
            evidence_data["date"] = meeting.date

        if meeting.title:
            evidence_data["title"] = meeting.title

        if meeting.parliament_number:
            evidence_data["parliament_number"] = meeting.parliament_number

        if meeting.session_number:
            evidence_data["session_number"] = meeting.session_number

        if meeting.publication_status:
            evidence_data["publication_status"] = meeting.publication_status

        # Create/merge CommitteeEvidence node
        cypher = """
            MERGE (e:CommitteeEvidence {id: $evidence_id})
            SET e = $evidence_data
            SET e.updated_at = datetime()
            RETURN e.id as evidence_id
        """
        self.neo4j.run_query(cypher, {
            "evidence_id": evidence_id,
            "evidence_data": evidence_data
        })
        logger.debug(f"Created CommitteeEvidence node: {evidence_id}")

        # Link to Committee
        self._link_evidence_to_committee(evidence_id, meeting.committee_code)

        # Link to Meeting
        self._link_evidence_to_meeting(
            evidence_id,
            meeting.committee_code,
            int(meeting.meeting_number) if meeting.meeting_number else None
        )

        # Create CommitteeTestimony nodes
        testimony_count = 0
        for section in meeting.sections:
            for testimony in section.testimonies:
                testimony_count += 1
                self._import_testimony(evidence_id, testimony, section.title)

        return testimony_count

    def _import_testimony(
        self,
        evidence_id: str,
        testimony: Any,
        section_title: str
    ) -> None:
        """Import a single testimony."""

        # Generate unique ID for testimony
        if testimony.intervention_id:
            testimony_id = f"{evidence_id}-{testimony.intervention_id}"
        else:
            # Fallback: use hash of speaker name and first 50 chars of text
            import hashlib
            hash_input = f"{testimony.speaker_name or 'unknown'}-{testimony.text[:50]}"
            testimony_hash = hashlib.md5(hash_input.encode()).hexdigest()[:12]
            testimony_id = f"{evidence_id}-{testimony_hash}"

        # Create testimony data
        testimony_data = {
            "id": testimony_id,
            "text": testimony.text,
            "is_witness": testimony.is_witness,
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Add optional fields
        if testimony.intervention_id:
            testimony_data["intervention_id"] = testimony.intervention_id

        if testimony.speaker_name:
            testimony_data["speaker_name"] = testimony.speaker_name

        if testimony.organization:
            testimony_data["organization"] = testimony.organization

        if testimony.role:
            testimony_data["role"] = testimony.role

        if testimony.person_db_id:
            testimony_data["person_db_id"] = testimony.person_db_id

        if testimony.timestamp_hour is not None:
            testimony_data["timestamp_hour"] = testimony.timestamp_hour

        if testimony.timestamp_minute is not None:
            testimony_data["timestamp_minute"] = testimony.timestamp_minute

        if testimony.floor_language:
            testimony_data["floor_language"] = testimony.floor_language

        # Create/merge CommitteeTestimony node
        cypher = """
            MERGE (t:CommitteeTestimony {id: $testimony_id})
            SET t = $testimony_data
            SET t.updated_at = datetime()
        """
        self.neo4j.run_query(cypher, {
            "testimony_id": testimony_id,
            "testimony_data": testimony_data
        })

        # Link to CommitteeEvidence
        cypher = """
            MATCH (e:CommitteeEvidence {id: $evidence_id})
            MATCH (t:CommitteeTestimony {id: $testimony_id})
            MERGE (t)-[:GIVEN_IN]->(e)
        """
        self.neo4j.run_query(cypher, {
            "evidence_id": evidence_id,
            "testimony_id": testimony_id
        })

        # Link to MP if person_db_id exists
        if testimony.person_db_id:
            self._link_testimony_to_mp(testimony_id, testimony.person_db_id)

    def _link_evidence_to_committee(self, evidence_id: str, committee_code: str) -> None:
        """Link CommitteeEvidence to Committee."""
        cypher = """
            MATCH (e:CommitteeEvidence {id: $evidence_id})
            MATCH (c:Committee {code: $committee_code})
            MERGE (e)-[:EVIDENCE_FOR]->(c)
        """
        result = self.neo4j.run_query(cypher, {
            "evidence_id": evidence_id,
            "committee_code": committee_code
        })
        logger.debug(f"Linked evidence to committee {committee_code}")

    def _link_evidence_to_meeting(
        self,
        evidence_id: str,
        committee_code: str,
        meeting_number: Optional[int]
    ) -> None:
        """Link CommitteeEvidence to Meeting."""
        if meeting_number is None:
            return

        # Find matching Meeting node
        cypher = """
            MATCH (e:CommitteeEvidence {id: $evidence_id})
            MATCH (m:Meeting)
            WHERE m.committee_code = $committee_code
              AND m.number = $meeting_number
            MERGE (m)-[:HAS_EVIDENCE]->(e)
            RETURN count(*) as linked
        """
        result = self.neo4j.run_query(cypher, {
            "evidence_id": evidence_id,
            "committee_code": committee_code,
            "meeting_number": meeting_number
        })

        if result and result[0]['linked'] > 0:
            logger.debug(f"Linked evidence to meeting {committee_code}/{meeting_number}")
        else:
            logger.debug(f"Meeting {committee_code}/{meeting_number} not found in Neo4j")

    def _link_testimony_to_mp(self, testimony_id: str, person_db_id: int) -> None:
        """Link CommitteeTestimony to MP using person_db_id."""
        cypher = """
            MATCH (t:CommitteeTestimony {id: $testimony_id})
            MATCH (mp:MP {parl_mp_id: $person_db_id})
            MERGE (t)-[:TESTIFIED_BY]->(mp)
        """
        self.neo4j.run_query(cypher, {
            "testimony_id": testimony_id,
            "person_db_id": person_db_id
        })
        logger.debug(f"Linked testimony to MP with person_id {person_db_id}")

        # Create SPOKE_AT relationship from MP to CommitteeEvidence
        # Creates ONE relationship per testimony (multiple per MP-CommitteeEvidence pair)
        # Enables detailed tracking of when/what MPs said in committee meetings
        spoke_at_cypher = """
            MATCH (t:CommitteeTestimony {id: $testimony_id})
            MATCH (mp:MP {parl_mp_id: $person_db_id})
            MATCH (t)-[:GIVEN_IN]->(ce:CommitteeEvidence)
            WHERE NOT exists {
                MATCH (mp)-[r:SPOKE_AT]->(ce)
                WHERE r.testimony_id = t.id
            }
            CREATE (mp)-[r:SPOKE_AT]->(ce)
            SET r.testimony_id = t.id,
                r.intervention_id = t.intervention_id,
                r.person_db_id = $person_db_id,
                r.timestamp_hour = t.timestamp_hour,
                r.timestamp_minute = t.timestamp_minute
        """
        self.neo4j.run_query(spoke_at_cypher, {
            "testimony_id": testimony_id,
            "person_db_id": person_db_id
        })
        logger.debug(f"Created SPOKE_AT relationship for MP {person_db_id}")

    def import_all_committees(
        self,
        limit_per_committee: Optional[int] = None,
        skip_existing: bool = True
    ) -> Dict[str, int]:
        """
        Import evidence for all committees found in Neo4j.

        Args:
            limit_per_committee: Max meetings per committee (None = all)
            skip_existing: Skip meetings that already have evidence

        Returns:
            Dict with import statistics
        """
        logger.info("Importing evidence for all committees...")

        # Get all committee codes from Neo4j
        result = self.neo4j.run_query("""
            MATCH (c:Committee)
            WHERE c.code IS NOT NULL
            RETURN DISTINCT c.code as committee_code
            ORDER BY committee_code
        """)

        committee_codes = [row['committee_code'] for row in result]
        logger.info(f"Found {len(committee_codes)} committees in Neo4j")

        total_stats = {
            "meetings": 0,
            "testimonies": 0,
            "skipped": 0,
            "errors": 0
        }

        # Process each committee
        for committee_code in committee_codes:
            logger.info(f"Processing committee: {committee_code}")

            stats = self.import_evidence_for_meetings(
                committee_code=committee_code,
                limit=limit_per_committee,
                skip_existing=skip_existing
            )

            # Aggregate stats
            for key in total_stats:
                total_stats[key] += stats[key]

        logger.success(f"✅ Total: {total_stats['meetings']} meetings, {total_stats['testimonies']} testimonies")
        if total_stats["skipped"] > 0:
            logger.info(f"ℹ️  Skipped {total_stats['skipped']} existing meetings")
        if total_stats["errors"] > 0:
            logger.warning(f"⚠️  {total_stats['errors']} errors occurred")

        return total_stats
