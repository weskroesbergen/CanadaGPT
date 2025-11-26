"""Helpers for fetching Hansard XML exports from the House of Commons."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from fedmcp.http import RateLimitedSession


DOCUMENTVIEWER_BASE = "https://www.ourcommons.ca/DocumentViewer/en/house/"


@dataclass
class HansardSpeech:
    """A single Hansard speech entry extracted from the XML document."""

    speaker_name: Optional[str]
    intervention_id: Optional[str]  # Renamed from speaker_id - this is the Intervention ID
    party: Optional[str]
    riding: Optional[str]
    timecode: Optional[str]
    text: str

    # Enhanced metadata fields
    person_db_id: Optional[int] = None  # Stable House of Commons person database ID
    role_type_code: Optional[int] = None  # Parliamentary role classification (1=PM, 2=MP, 15=Speaker, etc.)
    paragraph_ids: List[str] = field(default_factory=list)  # IDs for precise paragraph citations
    timestamp_hour: Optional[int] = None  # Structured hour from Timestamp element
    timestamp_minute: Optional[int] = None  # Structured minute from Timestamp element
    floor_language: Optional[str] = None  # Language spoken on floor (en/fr)
    intervention_type: Optional[str] = None  # Type of intervention from XML


@dataclass
class HansardSection:
    """A logical section of the Hansard (e.g., Oral Questions)."""

    title: str
    speeches: List[HansardSpeech] = field(default_factory=list)


@dataclass
class HansardSitting:
    """Parsed representation of a House of Commons sitting."""

    date: Optional[str]
    number: Optional[str]
    language: Optional[str]
    source_xml_url: str
    sections: List[HansardSection] = field(default_factory=list)

    # Enhanced document metadata
    creation_timestamp: Optional[str] = None  # When document was created/published
    speaker_of_day: Optional[str] = None  # Speaker of the House for this sitting
    hansard_document_id: Optional[str] = None  # Official Hansard document identifier
    parliament_number: Optional[int] = None  # Parliament number (e.g., 45)
    session_number: Optional[int] = None  # Session number (e.g., 1)
    volume: Optional[str] = None  # Hansard volume number


class OurCommonsHansardClient:
    """Retrieve and parse the Commons Hansard XML exports."""

    def __init__(
        self,
        *,
        session: Optional[RateLimitedSession] = None,
    ) -> None:
        self.session = session or RateLimitedSession()

    def build_documentviewer_url(self, slug: str) -> str:
        """Normalise a DocumentViewer slug into a fully-qualified URL."""

        slug = slug.lstrip("/")
        return urljoin(DOCUMENTVIEWER_BASE, slug)

    # ------------------------------------------------------------------
    # Fetch helpers
    # ------------------------------------------------------------------
    def fetch_documentviewer(self, slug_or_url: str) -> str:
        url = (
            slug_or_url
            if slug_or_url.startswith("http")
            else self.build_documentviewer_url(slug_or_url)
        )
        response = self.session.get(url)
        response.raise_for_status()
        return response.text

    def find_xml_link(self, documentviewer_html: str) -> str:
        """Extract the XML download link from a DocumentViewer HTML page."""

        soup = BeautifulSoup(documentviewer_html, "html.parser")
        link = soup.find("a", string=re.compile(r"XML", re.I))
        if not link or not link.get("href"):
            raise ValueError("Unable to locate XML download link on page")
        href = link["href"]
        if href.startswith("http"):
            return href
        return urljoin("https://www.ourcommons.ca", href)

    def fetch_sitting_xml(self, slug_or_url: str) -> Tuple[str, str]:
        html = self.fetch_documentviewer(slug_or_url)
        xml_url = self.find_xml_link(html)
        response = self.session.get(xml_url, headers={"Accept": "application/xml"})
        response.raise_for_status()
        # Decode with utf-8-sig to automatically strip BOM
        xml_text = response.content.decode('utf-8-sig')
        return xml_text, xml_url

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------
    def parse_sitting(self, xml_text: str, *, source_url: str) -> HansardSitting:
        """Parse a Hansard XML document into simplified Python data structures."""

        from xml.etree import ElementTree as ET

        # Strip UTF-8 BOM if present
        if xml_text.startswith('\ufeff'):
            xml_text = xml_text[1:]

        tree = ET.fromstring(xml_text)

        # Extract metadata from ExtractedInformation
        date = None
        number = None
        language = tree.attrib.get('{http://www.w3.org/XML/1998/namespace}lang', None)

        # Enhanced document metadata
        creation_timestamp = None
        speaker_of_day = None
        hansard_document_id = None
        parliament_number = None
        session_number = None
        volume = None

        extracted_info = tree.find(".//ExtractedInformation")
        if extracted_info is not None:
            for item in extracted_info.findall("ExtractedItem"):
                name = item.get("Name", "")
                value = item.text
                if name == "Date":
                    date = value
                elif name == "Number":
                    number = value
                elif name == "MetaCreationTime":
                    creation_timestamp = value
                elif name == "SpeakerName":
                    speaker_of_day = value
                elif name == "DocumentId":
                    hansard_document_id = value
                elif name == "ParliamentNumber":
                    try:
                        parliament_number = int(value) if value else None
                    except ValueError:
                        pass
                elif name == "SessionNumber":
                    try:
                        session_number = int(value) if value else None
                    except ValueError:
                        pass
                elif name == "Volume":
                    volume = value

        # Parse interventions as speeches, grouped by sections if available
        sections: List[HansardSection] = []

        # Try to find sections first (some formats may have them)
        section_elements = tree.findall(".//section")
        if section_elements:
            for section_el in section_elements:
                title = section_el.findtext("title") or "Untitled section"
                speeches = [self._parse_speech(speech_el) for speech_el in section_el.findall(".//Intervention")]
                sections.append(HansardSection(title=title, speeches=speeches))
        else:
            # No explicit sections, collect all interventions
            interventions = tree.findall(".//Intervention")
            if interventions:
                speeches = [self._parse_speech(interv) for interv in interventions]
                sections.append(HansardSection(title="Hansard Proceedings", speeches=speeches))

        return HansardSitting(
            date=date,
            number=number,
            language=language,
            source_xml_url=source_url,
            sections=sections,
            # Enhanced document metadata
            creation_timestamp=creation_timestamp,
            speaker_of_day=speaker_of_day,
            hansard_document_id=hansard_document_id,
            parliament_number=parliament_number,
            session_number=session_number,
            volume=volume,
        )

    def _parse_speech(self, speech_el) -> HansardSpeech:
        # Handle actual Hansard XML structure (Intervention elements)
        person = speech_el.find("PersonSpeaking")
        speaker_name = None
        intervention_id = None
        party = None
        riding = None
        person_db_id = None
        role_type_code = None
        floor_language = None

        if person is not None:
            # Get Affiliation element to extract DbId and Type attributes
            affiliation_el = person.find("Affiliation")
            if affiliation_el is not None:
                # Extract stable person database ID (critical for MP linking)
                db_id_str = affiliation_el.get("DbId")
                if db_id_str:
                    try:
                        person_db_id = int(db_id_str)
                    except ValueError:
                        pass

                # Extract role type code (1=PM, 2=MP, 15=Speaker, etc.)
                type_str = affiliation_el.get("Type")
                if type_str:
                    try:
                        role_type_code = int(type_str)
                    except ValueError:
                        pass

                # Parse affiliation text for backward compatibility
                affiliation = affiliation_el.text or ""
                if affiliation:
                    # Try to parse affiliation string: "Name (Riding, Party)"
                    speaker_name = affiliation.split("(")[0].strip() if "(" in affiliation else affiliation
                    if "(" in affiliation and ")" in affiliation:
                        paren_content = affiliation[affiliation.index("(") + 1:affiliation.rindex(")")]
                        parts = paren_content.split(",")
                        if len(parts) >= 2:
                            riding = parts[0].strip()
                            party = parts[1].strip()
                        elif len(parts) == 1:
                            # Could be just riding or just party
                            riding = parts[0].strip()

            # Extract floor language from FloorLanguage element
            floor_lang_el = person.find("FloorLanguage")
            if floor_lang_el is not None:
                floor_language = floor_lang_el.text

        # Intervention ID (not the same as person DB ID!)
        intervention_id = speech_el.get("id")

        # Extract intervention type attribute
        intervention_type = speech_el.get("Type")

        # Extract time from Timestamp element with structured Hr/Mn attributes
        timecode = None
        timestamp_hour = None
        timestamp_minute = None
        timestamp_el = speech_el.find(".//Timestamp")
        if timestamp_el is not None:
            # Get structured hour/minute attributes
            hr_str = timestamp_el.get("Hr")
            mn_str = timestamp_el.get("Mn")
            if hr_str:
                try:
                    timestamp_hour = int(hr_str)
                except ValueError:
                    pass
            if mn_str:
                try:
                    timestamp_minute = int(mn_str)
                except ValueError:
                    pass

            # Format timecode as HH:MM:SS if we have structured attributes
            if timestamp_hour is not None and timestamp_minute is not None:
                timecode = f"{timestamp_hour:02d}:{timestamp_minute:02d}:00"
            else:
                # Fallback: parse text content, removing parentheses if present
                text = timestamp_el.text
                if text:
                    # Remove parentheses: "(1020)" -> "1020"
                    text = text.strip().strip('()')
                    # Parse as HHMM format: "1020" -> "10:20:00"
                    if len(text) == 4 and text.isdigit():
                        hour = int(text[:2])
                        minute = int(text[2:])
                        timecode = f"{hour:02d}:{minute:02d}:00"
                    else:
                        # Keep original if we can't parse
                        timecode = text

        # Extract text and paragraph IDs from Content/ParaText elements
        content = speech_el.find("Content")
        paragraphs = []
        paragraph_ids = []
        if content is not None:
            # Get all ParaText elements
            for para_text in content.findall(".//ParaText"):
                text = "".join(para_text.itertext()).strip()
                if text:
                    paragraphs.append(text)
                    # Capture paragraph ID for precise citations
                    para_id = para_text.get("id")
                    if para_id:
                        paragraph_ids.append(para_id)

        text = "\n\n".join(paragraphs)

        return HansardSpeech(
            speaker_name=speaker_name,
            intervention_id=intervention_id,
            party=party,
            riding=riding,
            timecode=timecode,
            text=text,
            # Enhanced metadata
            person_db_id=person_db_id,
            role_type_code=role_type_code,
            paragraph_ids=paragraph_ids,
            timestamp_hour=timestamp_hour,
            timestamp_minute=timestamp_minute,
            floor_language=floor_language,
            intervention_type=intervention_type,
        )

    # ------------------------------------------------------------------
    # Convenience API
    # ------------------------------------------------------------------
    def get_sitting(
        self, slug_or_url: str, *, parse: bool = True
    ) -> HansardSitting | str:
        xml_text, xml_url = self.fetch_sitting_xml(slug_or_url)
        if not parse:
            return xml_text
        return self.parse_sitting(xml_text, source_url=xml_url)
