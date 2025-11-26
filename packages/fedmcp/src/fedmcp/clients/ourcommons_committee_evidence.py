"""
Client for fetching and parsing committee evidence (testimony) from OurCommons XML.

Committee evidence is published at:
https://www.ourcommons.ca/DocumentViewer/en/{COMMITTEE_CODE}/{MEETING_NUMBER}/evidence

This client:
- Fetches committee meeting evidence XML
- Parses witness testimony and MP questions
- Extracts speaker information, topics, and timestamps
- Provides structured access to committee proceedings
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from fedmcp.http import RateLimitedSession


DOCUMENTVIEWER_BASE = "https://www.ourcommons.ca/DocumentViewer/en/"


@dataclass
class CommitteeTestimony:
    """A single testimony/intervention in a committee meeting."""

    speaker_name: Optional[str]
    intervention_id: Optional[str]
    organization: Optional[str]  # Witness organization/affiliation
    role: Optional[str]  # Witness role/title
    text: str

    # Enhanced metadata
    person_db_id: Optional[int] = None  # House of Commons person database ID
    is_witness: bool = False  # True if external witness, False if MP/committee member
    paragraph_ids: List[str] = field(default_factory=list)
    timestamp_hour: Optional[int] = None
    timestamp_minute: Optional[int] = None
    floor_language: Optional[str] = None
    intervention_type: Optional[str] = None


@dataclass
class CommitteeSection:
    """A logical section of committee evidence (e.g., witness panel)."""

    title: str
    testimonies: List[CommitteeTestimony] = field(default_factory=list)


@dataclass
class CommitteeMeeting:
    """Parsed representation of a committee meeting/evidence session."""

    committee_code: str
    meeting_number: Optional[str]
    date: Optional[str]
    title: Optional[str]
    source_xml_url: str
    sections: List[CommitteeSection] = field(default_factory=list)

    # Enhanced document metadata
    parliament_number: Optional[int] = None
    session_number: Optional[int] = None
    creation_timestamp: Optional[str] = None
    publication_status: Optional[str] = None  # Draft, Final, etc.


class OurCommonsCommitteeEvidenceClient:
    """Client for fetching and parsing committee evidence from OurCommons."""

    def __init__(
        self,
        *,
        session: Optional[RateLimitedSession] = None,
    ) -> None:
        """
        Initialize the committee evidence client.

        Args:
            session: Optional rate-limited session to use
        """
        self.session = session or RateLimitedSession()

    def build_evidence_url(self, committee_code: str, meeting_number: int) -> str:
        """
        Build DocumentViewer URL for committee evidence.

        Args:
            committee_code: Committee acronym (e.g., "FINA", "HESA")
            meeting_number: Meeting number

        Returns:
            Full DocumentViewer URL
        """
        slug = f"{committee_code}/{meeting_number}/evidence"
        return urljoin(DOCUMENTVIEWER_BASE, slug)

    def get_evidence(
        self,
        committee_code: str,
        meeting_number: int,
        parse: bool = True
    ) -> CommitteeMeeting | str:
        """
        Fetch committee evidence XML and optionally parse it.

        Args:
            committee_code: Committee acronym (e.g., "FINA")
            meeting_number: Meeting number
            parse: If True, return parsed CommitteeMeeting object. If False, return raw XML string.

        Returns:
            CommitteeMeeting object if parse=True, raw XML string if parse=False
        """
        # Build the DocumentViewer URL
        doc_url = self.build_evidence_url(committee_code, meeting_number)

        # Fetch the HTML page first to extract the XML link
        resp = self.session.get(doc_url)
        resp.raise_for_status()

        # Parse HTML to find XML link
        soup = BeautifulSoup(resp.text, "html.parser")

        # Look for XML download link (pattern from Hansard client)
        xml_link = None
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "xml" in href.lower() or "export" in href.lower():
                xml_link = urljoin(doc_url, href)
                break

        if not xml_link:
            # Fallback: construct XML URL directly
            xml_link = doc_url.replace("/evidence", "/evidence/xml")

        # Fetch the XML
        xml_resp = self.session.get(xml_link)
        xml_resp.raise_for_status()

        # Decode with UTF-8-sig to handle BOM
        raw_xml = xml_resp.content.decode("utf-8-sig")

        if not parse:
            return raw_xml

        # Parse the XML
        return self._parse_evidence_xml(
            raw_xml,
            committee_code=committee_code,
            meeting_number=str(meeting_number),
            source_url=xml_link
        )

    def _parse_evidence_xml(
        self,
        xml_content: str,
        committee_code: str,
        meeting_number: str,
        source_url: str
    ) -> CommitteeMeeting:
        """
        Parse committee evidence XML into structured CommitteeMeeting object.

        Args:
            xml_content: Raw XML content
            committee_code: Committee acronym
            meeting_number: Meeting number
            source_url: Source XML URL

        Returns:
            CommitteeMeeting object with parsed data
        """
        root = ET.fromstring(xml_content)

        # Extract document-level metadata
        meeting = CommitteeMeeting(
            committee_code=committee_code,
            meeting_number=meeting_number,
            source_xml_url=source_url,
            date=None,
            title=None
        )

        # Parse metadata elements (similar to Hansard structure)
        for metadata in root.findall(".//Metadata"):
            date_elem = metadata.find("SittingDate")
            if date_elem is not None and date_elem.text:
                meeting.date = date_elem.text.strip()

            # Extract parliament/session info
            parl_elem = metadata.find("Parliament")
            if parl_elem is not None and parl_elem.text:
                meeting.parliament_number = int(parl_elem.text.strip())

            session_elem = metadata.find("Session")
            if session_elem is not None and session_elem.text:
                meeting.session_number = int(session_elem.text.strip())

        # Parse committee evidence structure
        # Committee evidence uses similar XML structure to Hansard
        sections_dict = {}  # title -> CommitteeSection

        for intervention in root.findall(".//Intervention"):
            # Extract intervention metadata
            interv_id = intervention.get("id")
            person_elem = intervention.find("PersonSpeaking")

            speaker_name = None
            person_db_id = None
            organization = None
            role = None
            is_witness = False

            if person_elem is not None:
                # Extract name
                name_elem = person_elem.find("Name")
                if name_elem is not None:
                    speaker_name = name_elem.text.strip() if name_elem.text else None

                # Extract person database ID
                person_id_elem = person_elem.find("PersonId")
                if person_id_elem is not None and person_id_elem.text:
                    try:
                        person_db_id = int(person_id_elem.text.strip())
                    except (ValueError, AttributeError):
                        pass

                # Extract organization/affiliation (for witnesses)
                org_elem = person_elem.find("Affiliation")
                if org_elem is not None and org_elem.text:
                    organization = org_elem.text.strip()
                    is_witness = True  # External witnesses have affiliations

                # Extract role/title
                role_elem = person_elem.find("Role")
                if role_elem is not None and role_elem.text:
                    role = role_elem.text.strip()

            # Extract text content from paragraphs
            paragraphs = []
            paragraph_ids = []

            for para in intervention.findall(".//ParaText"):
                para_id = para.get("id")
                if para_id:
                    paragraph_ids.append(para_id)

                if para.text:
                    paragraphs.append(para.text.strip())

            # Join paragraphs with double newlines (preserve structure)
            text = "\n\n".join(paragraphs)

            if not text.strip():
                continue  # Skip empty interventions

            # Extract section/topic heading
            section_title = "General Discussion"  # Default
            heading_elem = intervention.find(".//Heading")
            if heading_elem is not None and heading_elem.text:
                section_title = heading_elem.text.strip()

            # Get or create section
            if section_title not in sections_dict:
                sections_dict[section_title] = CommitteeSection(title=section_title)

            # Create testimony object
            testimony = CommitteeTestimony(
                speaker_name=speaker_name,
                intervention_id=interv_id,
                organization=organization,
                role=role,
                text=text,
                person_db_id=person_db_id,
                is_witness=is_witness,
                paragraph_ids=paragraph_ids
            )

            sections_dict[section_title].testimonies.append(testimony)

        # Convert sections dict to list
        meeting.sections = list(sections_dict.values())

        return meeting

    def list_recent_meetings(
        self,
        committee_code: str,
        limit: int = 10
    ) -> List[dict]:
        """
        List recent meetings for a committee.

        Note: This is a placeholder. A full implementation would scrape
        the committee's meeting list page or use an API.

        Args:
            committee_code: Committee acronym
            limit: Maximum number of meetings to return

        Returns:
            List of meeting metadata dicts
        """
        # Placeholder: In production, this would scrape the committee meeting list
        # from https://www.ourcommons.ca/Committees/en/{COMMITTEE_CODE}/Meetings
        return []
