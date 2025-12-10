"""Client for fetching and parsing bill text XML from Parliament.ca.

Bill XML structure follows the LEGISinfo format with these main elements:
- Bill > Identification (metadata, sponsor, history)
- Bill > Introduction > Summary, Preamble, Enacts
- Bill > Body > Heading, Section, Subsection, Paragraph, Subparagraph, Clause

Amendment Tracking:
- LEGISinfo JSON tracks amendment events at committee/report stages
- Bill versions (1, 2, 3...) represent different readings/amendments
- "As amended by committee" is typically version 3
- Detailed amendment text comes from committee reports (HTML, not structured)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

from fedmcp.http import RateLimitedSession


PARL_BASE = "https://www.parl.ca"
LEGISINFO_BASE = "https://www.parl.ca/LegisInfo/en"


class BillStage(Enum):
    """Legislative stages/readings for bill versions."""
    FIRST_READING = "first-reading"
    SECOND_READING = "second-reading"
    COMMITTEE = "committee"
    REPORT_STAGE = "report-stage"
    THIRD_READING = "third-reading"
    SENATE_FIRST = "senate-first-reading"
    SENATE_SECOND = "senate-second-reading"
    SENATE_COMMITTEE = "senate-committee"
    SENATE_THIRD = "senate-third-reading"
    ROYAL_ASSENT = "royal-assent"

    @classmethod
    def from_path_segment(cls, segment: str) -> Optional["BillStage"]:
        """Map path segments like 'C-234_1' to stages."""
        mapping = {
            "1": cls.FIRST_READING,
            "2": cls.SECOND_READING,
            "3": cls.COMMITTEE,
            "4": cls.REPORT_STAGE,
            "5": cls.THIRD_READING,
        }
        match = re.search(r"_(\d+)$", segment)
        if match:
            return mapping.get(match.group(1))
        return None

    @classmethod
    def from_publication_type(cls, type_id: int, type_name: str) -> Optional["BillStage"]:
        """Map LEGISinfo publication types to stages."""
        # Common type IDs from LEGISinfo
        type_mapping = {
            80701: cls.FIRST_READING,  # "As introduced"
            80702: cls.COMMITTEE,       # "As amended by committee"
            80703: cls.THIRD_READING,   # "As passed by House"
            80704: cls.ROYAL_ASSENT,    # "Royal Assent"
        }
        if type_id in type_mapping:
            return type_mapping[type_id]
        # Fallback to name matching
        name_lower = type_name.lower()
        if "introduced" in name_lower or "first" in name_lower:
            return cls.FIRST_READING
        if "amended" in name_lower:
            return cls.COMMITTEE
        if "passed" in name_lower or "third" in name_lower:
            return cls.THIRD_READING
        if "royal" in name_lower:
            return cls.ROYAL_ASSENT
        return None


@dataclass
class BillAmendmentEvent:
    """An amendment-related event in the bill's history."""
    event_type: str  # "committee_report_with_amendments", "senate_amendment", etc.
    description_en: str
    description_fr: Optional[str]
    event_date: Optional[datetime]
    chamber: str  # "House" or "Senate"
    stage: str  # "Consideration in committee", "Report stage", etc.
    committee_code: Optional[str]
    committee_name: Optional[str]
    report_id: Optional[int]
    report_number: Optional[int]
    number_of_amendments: Optional[int]


@dataclass
class BillElement:
    """Base class for bill structural elements."""
    id: str
    anchor_id: str
    sequence: int


@dataclass
class BillSubparagraph(BillElement):
    """Deepest level: subparagraphs (i), (ii), (iii)."""
    numeral: str
    text_en: str
    text_fr: Optional[str] = None


@dataclass
class BillParagraph(BillElement):
    """Paragraphs: (a), (b), (c)."""
    letter: str
    text_en: str
    text_fr: Optional[str] = None
    subparagraphs: List[BillSubparagraph] = field(default_factory=list)


@dataclass
class BillSubsection(BillElement):
    """Subsections: (1), (2), (3)."""
    number: str
    text_en: str
    text_fr: Optional[str] = None
    paragraphs: List[BillParagraph] = field(default_factory=list)


@dataclass
class BillSection(BillElement):
    """Sections: 1, 2, 3 - the main numbered divisions."""
    number: str
    marginal_note_en: Optional[str]
    text_en: str
    text_fr: Optional[str] = None
    marginal_note_fr: Optional[str] = None
    subsections: List[BillSubsection] = field(default_factory=list)


@dataclass
class BillPart(BillElement):
    """Parts: Part I, Part II - top-level divisions."""
    number: int
    title_en: str
    title_fr: Optional[str] = None
    sections: List[BillSection] = field(default_factory=list)


@dataclass
class BillDefinition:
    """A definition within a bill section."""
    term_en: str
    definition_en: str
    term_fr: Optional[str] = None
    definition_fr: Optional[str] = None


@dataclass
class BillVersion:
    """A specific version of a bill at a legislative stage.

    Bill versions track changes through the legislative process:
    - version 1: First reading (as introduced)
    - version 2: Second reading
    - version 3: As amended by committee (if applicable)
    - version 4: Report stage
    - version 5: Third reading / as passed

    The publication_type from LEGISinfo indicates the nature of changes.
    """
    stage: BillStage
    version_number: int
    xml_url: str
    pdf_url: Optional[str] = None
    publication_type_id: Optional[int] = None  # LEGISinfo type ID
    publication_type_name: Optional[str] = None  # "As introduced", "As amended by committee"
    publication_date: Optional[datetime] = None
    has_amendments: bool = False  # True if this version contains amendments


@dataclass
class ParsedBill:
    """Complete parsed bill structure with version and amendment history."""
    bill_number: str
    parliament: int
    session: int
    session_str: str  # e.g., "45-1"
    stage: BillStage
    version_number: int

    # Identification
    title_en: str
    title_fr: Optional[str]
    short_title_en: Optional[str]
    short_title_fr: Optional[str]
    sponsor_name: Optional[str]
    sponsor_riding: Optional[str]

    # Introduction
    summary_en: Optional[str]
    summary_fr: Optional[str]
    preamble_en: Optional[str]
    preamble_fr: Optional[str]
    enacting_clause_en: Optional[str]
    enacting_clause_fr: Optional[str]

    # Body structure
    parts: List[BillPart] = field(default_factory=list)
    sections: List[BillSection] = field(default_factory=list)  # Sections not in parts
    definitions: List[BillDefinition] = field(default_factory=list)

    # Version history (all available versions of this bill)
    available_versions: List[BillVersion] = field(default_factory=list)

    # Amendment history (events where amendments were made)
    amendment_events: List[BillAmendmentEvent] = field(default_factory=list)

    # Current version metadata
    publication_type_name: Optional[str] = None  # "As introduced", "As amended by committee"
    has_amendments: bool = False

    # Source
    xml_url: str = ""
    legisinfo_url: str = ""


class BillTextXMLClient:
    """Fetch and parse bill XML from Parliament.ca.

    Bill XML URL patterns:
    - Government bills: /Content/Bills/{parliament}/Government/{bill}/{bill}_{version}/{bill}_E.xml
    - Private bills: /Content/Bills/{parliament}/Private/{bill}/{bill}_{version}/{bill}_E.xml
    - Private Member's bills: /Content/Bills/{parliament}/Private/{bill}/{bill}_{version}/{bill}_E.xml

    Examples:
    - https://www.parl.ca/Content/Bills/451/Private/C-234/C-234_1/C-234_E.xml
    - https://www.parl.ca/Content/Bills/441/Government/C-2/C-2_3/C-2_E.xml
    """

    def __init__(
        self,
        *,
        session: Optional[RateLimitedSession] = None,
        base_url: str = PARL_BASE,
    ) -> None:
        self.session = session or RateLimitedSession()
        self.base_url = base_url.rstrip("/")

    def build_xml_url(
        self,
        parliament: int,
        bill_number: str,
        version: int = 1,
        *,
        is_government: bool = False,
        language: str = "E",
    ) -> str:
        """Build the direct XML URL for a bill version.

        Args:
            parliament: Parliament number (e.g., 45 for 45th Parliament)
            bill_number: Bill code (e.g., "C-234", "S-12")
            version: Version number (1=first reading, 2=second, etc.)
            is_government: True for government bills, False for private member's bills
            language: "E" for English, "F" for French

        Returns:
            Full URL to the bill XML file
        """
        bill_type = "Government" if is_government else "Private"
        bill_upper = bill_number.upper()
        # Parliament session as 3 digits (e.g., 451 for parliament 45 session 1)
        parl_str = f"{parliament}1"

        return (
            f"{self.base_url}/Content/Bills/{parl_str}/{bill_type}/"
            f"{bill_upper}/{bill_upper}_{version}/{bill_upper}_{language}.xml"
        )

    def list_available_versions(
        self,
        parliament: int,
        session: int,
        bill_number: str,
        *,
        is_government: bool = False,
    ) -> List[BillVersion]:
        """Discover available versions of a bill.

        Attempts to fetch versions 1-5 and returns those that exist.
        """
        versions = []
        bill_upper = bill_number.upper()
        bill_type = "Government" if is_government else "Private"
        parl_str = f"{parliament}{session}"

        # Try versions 1-5 (covers most bills)
        for v in range(1, 6):
            xml_url = (
                f"{self.base_url}/Content/Bills/{parl_str}/{bill_type}/"
                f"{bill_upper}/{bill_upper}_{v}/{bill_upper}_E.xml"
            )
            try:
                response = self.session.get(xml_url, timeout=10)
                if response.status_code == 200:
                    stage = BillStage.from_path_segment(f"{bill_upper}_{v}")
                    versions.append(BillVersion(
                        stage=stage or BillStage.FIRST_READING,
                        version_number=v,
                        xml_url=xml_url,
                        pdf_url=xml_url.replace("_E.xml", f"_{v}.PDF"),
                    ))
            except Exception:
                pass  # Version doesn't exist

        return versions

    def fetch_xml(self, url: str) -> str:
        """Fetch raw XML content from a URL."""
        response = self.session.get(url, timeout=60)
        response.raise_for_status()
        # Handle BOM
        content = response.content.decode("utf-8-sig")
        return content

    def parse_bill(
        self,
        parliament: int,
        session: int,
        bill_number: str,
        version: int = 1,
        *,
        is_government: bool = False,
    ) -> ParsedBill:
        """Fetch and parse a bill into structured data.

        Args:
            parliament: Parliament number (e.g., 45)
            session: Session number (e.g., 1)
            bill_number: Bill code (e.g., "C-234")
            version: Version number (1=first reading, etc.)
            is_government: True for government bills

        Returns:
            ParsedBill with full structured content
        """
        bill_upper = bill_number.upper()
        bill_type = "Government" if is_government else "Private"
        parl_str = f"{parliament}{session}"
        session_str = f"{parliament}-{session}"

        xml_url = (
            f"{self.base_url}/Content/Bills/{parl_str}/{bill_type}/"
            f"{bill_upper}/{bill_upper}_{version}/{bill_upper}_E.xml"
        )

        xml_content = self.fetch_xml(xml_url)
        root = ET.fromstring(xml_content)

        return self._parse_root(
            root,
            bill_number=bill_upper,
            parliament=parliament,
            session=session,
            session_str=session_str,
            version=version,
            xml_url=xml_url,
        )

    def parse_from_xml(
        self,
        xml_content: str,
        *,
        bill_number: str,
        parliament: int,
        session: int,
        version: int = 1,
        xml_url: str = "",
    ) -> ParsedBill:
        """Parse bill from raw XML content (for testing or pre-fetched content)."""
        session_str = f"{parliament}-{session}"
        root = ET.fromstring(xml_content)
        return self._parse_root(
            root,
            bill_number=bill_number,
            parliament=parliament,
            session=session,
            session_str=session_str,
            version=version,
            xml_url=xml_url,
        )

    def _parse_root(
        self,
        root: ET.Element,
        *,
        bill_number: str,
        parliament: int,
        session: int,
        session_str: str,
        version: int,
        xml_url: str,
    ) -> ParsedBill:
        """Parse the root Bill element into structured data."""
        # Helper to get text from an element
        def get_text(parent: Optional[ET.Element], tag: str) -> Optional[str]:
            if parent is None:
                return None
            elem = parent.find(f".//{tag}")
            return elem.text.strip() if elem is not None and elem.text else None

        def get_all_text(elem: Optional[ET.Element]) -> str:
            """Get all text content including nested elements."""
            if elem is None:
                return ""
            return "".join(elem.itertext()).strip()

        # Identification section
        ident = root.find(".//Identification")
        title_en = get_text(ident, "LongTitle") or get_text(ident, "Title") or bill_number
        short_title_en = get_text(ident, "ShortTitle")
        sponsor_name = get_text(ident, "Sponsor")
        sponsor_riding = get_text(ident, "SponsorRiding")

        # Introduction section
        intro = root.find(".//Introduction")
        summary_en = get_text(intro, "Summary")
        preamble_parts = []
        preamble_elem = intro.find(".//Preamble") if intro is not None else None
        if preamble_elem is not None:
            for provision in preamble_elem.findall(".//Provision"):
                text = get_all_text(provision)
                if text:
                    preamble_parts.append(text)
        preamble_en = "\n\n".join(preamble_parts) if preamble_parts else None

        enacts = intro.find(".//Enacts") if intro is not None else None
        enacting_clause_en = get_all_text(enacts) if enacts is not None else None

        # Determine stage from version
        stage = BillStage.from_path_segment(f"_{version}") or BillStage.FIRST_READING

        # Parse body structure
        body = root.find(".//Body")
        parts, sections, definitions = self._parse_body(
            body, bill_number, session_str
        )

        return ParsedBill(
            bill_number=bill_number,
            parliament=parliament,
            session=session,
            session_str=session_str,
            stage=stage,
            version_number=version,
            title_en=title_en,
            title_fr=None,  # Would need separate French XML
            short_title_en=short_title_en,
            short_title_fr=None,
            sponsor_name=sponsor_name,
            sponsor_riding=sponsor_riding,
            summary_en=summary_en,
            summary_fr=None,
            preamble_en=preamble_en,
            preamble_fr=None,
            enacting_clause_en=enacting_clause_en,
            enacting_clause_fr=None,
            parts=parts,
            sections=sections,
            definitions=definitions,
            xml_url=xml_url,
        )

    def _parse_body(
        self,
        body: Optional[ET.Element],
        bill_number: str,
        session_str: str,
    ) -> tuple[List[BillPart], List[BillSection], List[BillDefinition]]:
        """Parse the Body element into Parts, Sections, and Definitions."""
        parts: List[BillPart] = []
        loose_sections: List[BillSection] = []
        definitions: List[BillDefinition] = []

        if body is None:
            return parts, loose_sections, definitions

        # Track current part context
        current_part: Optional[BillPart] = None
        part_num = 0
        section_seq = 0

        for child in body:
            tag = child.tag

            # Part heading (level 1)
            if tag == "Heading" and child.get("level") == "1":
                part_num += 1
                title = "".join(child.itertext()).strip()
                part_anchor = f"bill:{session_str}:{bill_number.lower()}:part-{part_num}"
                current_part = BillPart(
                    id=f"{session_str}:{bill_number}:part:{part_num}",
                    anchor_id=part_anchor,
                    sequence=part_num,
                    number=part_num,
                    title_en=title,
                )
                parts.append(current_part)

            # Section
            elif tag == "Section":
                section_seq += 1
                parsed_section = self._parse_section(
                    child, bill_number, session_str, section_seq
                )

                # Extract definitions from this section
                section_defs = self._extract_definitions(child)
                definitions.extend(section_defs)

                if current_part:
                    current_part.sections.append(parsed_section)
                else:
                    loose_sections.append(parsed_section)

        return parts, loose_sections, definitions

    def _parse_section(
        self,
        section_elem: ET.Element,
        bill_number: str,
        session_str: str,
        sequence: int,
    ) -> BillSection:
        """Parse a Section element with its subsections and paragraphs."""
        label_elem = section_elem.find("Label")
        section_num = label_elem.text.strip() if label_elem is not None and label_elem.text else str(sequence)

        marginal_note = section_elem.find("MarginalNote")
        marginal_note_en = "".join(marginal_note.itertext()).strip() if marginal_note is not None else None

        # Get direct text content (not in subsections)
        text_elem = section_elem.find("Text")
        text_en = "".join(text_elem.itertext()).strip() if text_elem is not None else ""

        # Build anchor ID
        section_anchor = f"bill:{session_str}:{bill_number.lower()}:s{section_num}"

        section = BillSection(
            id=f"{session_str}:{bill_number}:s:{section_num}",
            anchor_id=section_anchor,
            sequence=sequence,
            number=section_num,
            marginal_note_en=marginal_note_en,
            text_en=text_en,
        )

        # Parse subsections
        subsection_seq = 0
        for subsection_elem in section_elem.findall("Subsection"):
            subsection_seq += 1
            parsed_sub = self._parse_subsection(
                subsection_elem, bill_number, session_str, section_num, subsection_seq
            )
            section.subsections.append(parsed_sub)

        return section

    def _parse_subsection(
        self,
        subsection_elem: ET.Element,
        bill_number: str,
        session_str: str,
        section_num: str,
        sequence: int,
    ) -> BillSubsection:
        """Parse a Subsection element with its paragraphs."""
        label_elem = subsection_elem.find("Label")
        sub_num = label_elem.text.strip("()") if label_elem is not None and label_elem.text else str(sequence)

        text_elem = subsection_elem.find("Text")
        text_en = "".join(text_elem.itertext()).strip() if text_elem is not None else ""

        anchor_id = f"bill:{session_str}:{bill_number.lower()}:s{section_num}.{sub_num}"

        subsection = BillSubsection(
            id=f"{session_str}:{bill_number}:s:{section_num}:{sub_num}",
            anchor_id=anchor_id,
            sequence=sequence,
            number=sub_num,
            text_en=text_en,
        )

        # Parse paragraphs
        para_seq = 0
        for para_elem in subsection_elem.findall("Paragraph"):
            para_seq += 1
            parsed_para = self._parse_paragraph(
                para_elem, bill_number, session_str, section_num, sub_num, para_seq
            )
            subsection.paragraphs.append(parsed_para)

        return subsection

    def _parse_paragraph(
        self,
        para_elem: ET.Element,
        bill_number: str,
        session_str: str,
        section_num: str,
        subsection_num: str,
        sequence: int,
    ) -> BillParagraph:
        """Parse a Paragraph element with its subparagraphs."""
        label_elem = para_elem.find("Label")
        letter = label_elem.text.strip("()") if label_elem is not None and label_elem.text else chr(ord('a') + sequence - 1)

        text_elem = para_elem.find("Text")
        text_en = "".join(text_elem.itertext()).strip() if text_elem is not None else ""

        anchor_id = f"bill:{session_str}:{bill_number.lower()}:s{section_num}.{subsection_num}.{letter}"

        paragraph = BillParagraph(
            id=f"{session_str}:{bill_number}:s:{section_num}:{subsection_num}:{letter}",
            anchor_id=anchor_id,
            sequence=sequence,
            letter=letter,
            text_en=text_en,
        )

        # Parse subparagraphs
        subpara_seq = 0
        for subpara_elem in para_elem.findall("Subparagraph"):
            subpara_seq += 1
            parsed_subpara = self._parse_subparagraph(
                subpara_elem, bill_number, session_str,
                section_num, subsection_num, letter, subpara_seq
            )
            paragraph.subparagraphs.append(parsed_subpara)

        return paragraph

    def _parse_subparagraph(
        self,
        subpara_elem: ET.Element,
        bill_number: str,
        session_str: str,
        section_num: str,
        subsection_num: str,
        para_letter: str,
        sequence: int,
    ) -> BillSubparagraph:
        """Parse a Subparagraph element."""
        label_elem = subpara_elem.find("Label")
        # Roman numerals: i, ii, iii, iv, v...
        roman_numerals = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"]
        numeral = label_elem.text.strip("()") if label_elem is not None and label_elem.text else roman_numerals[min(sequence - 1, 9)]

        text_elem = subpara_elem.find("Text")
        text_en = "".join(text_elem.itertext()).strip() if text_elem is not None else ""

        anchor_id = f"bill:{session_str}:{bill_number.lower()}:s{section_num}.{subsection_num}.{para_letter}.{numeral}"

        return BillSubparagraph(
            id=f"{session_str}:{bill_number}:s:{section_num}:{subsection_num}:{para_letter}:{numeral}",
            anchor_id=anchor_id,
            sequence=sequence,
            numeral=numeral,
            text_en=text_en,
        )

    def _extract_definitions(self, section_elem: ET.Element) -> List[BillDefinition]:
        """Extract definitions from a section element."""
        definitions = []
        for defn_elem in section_elem.findall(".//Definition"):
            term_elem = defn_elem.find("DefinedTermEn")
            term_en = term_elem.text.strip() if term_elem is not None and term_elem.text else None

            # Get definition text (all text after the term)
            text_parts = []
            for child in defn_elem:
                if child.tag != "DefinedTermEn" and child.tag != "DefinedTermFr":
                    text = "".join(child.itertext()).strip()
                    if text:
                        text_parts.append(text)

            definition_en = " ".join(text_parts) if text_parts else ""

            if term_en:
                definitions.append(BillDefinition(
                    term_en=term_en,
                    definition_en=definition_en,
                ))

        return definitions

    # ------------------------------------------------------------------
    # LEGISinfo JSON methods for version and amendment history
    # ------------------------------------------------------------------

    def get_legisinfo_metadata(
        self,
        parliament: int,
        session: int,
        bill_number: str,
    ) -> Dict[str, Any]:
        """Fetch bill metadata from LEGISinfo JSON API.

        Returns the full JSON response containing:
        - Publications (versions with type IDs)
        - BillStages with amendment events
        - Committee information
        """
        bill_lower = bill_number.lower()
        url = f"{LEGISINFO_BASE}/bill/{parliament}-{session}/{bill_lower}/json"
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        # LEGISinfo returns a list with one item
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return data

    def extract_versions_from_legisinfo(
        self,
        metadata: Dict[str, Any],
        parliament: int,
        session: int,
        bill_number: str,
        *,
        is_government: bool = False,
    ) -> List[BillVersion]:
        """Extract version information from LEGISinfo JSON metadata.

        Publications in LEGISinfo include:
        - TypeId 80701: "As introduced" (first reading)
        - TypeId 80702: "As amended by committee"
        - TypeId 80703: "As passed by House"
        - TypeId 80704: "Royal Assent"
        """
        versions = []
        publications = metadata.get("Publications", [])
        bill_upper = bill_number.upper()
        bill_type = "Government" if is_government else "Private"
        parl_str = f"{parliament}{session}"

        for i, pub in enumerate(publications, start=1):
            type_id = pub.get("PublicationTypeId") or pub.get("TypeId")
            type_name_en = pub.get("PublicationTypeNameEn") or pub.get("TypeNameEn", "")

            # Parse publication date
            pub_date = None
            pub_date_str = pub.get("PublicationDate")
            if pub_date_str:
                try:
                    pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

            # Determine stage from publication type
            stage = BillStage.from_publication_type(type_id, type_name_en)
            if stage is None:
                stage = BillStage.FIRST_READING

            # Check if this version has amendments
            has_amendments = "amended" in type_name_en.lower()

            # Build XML URL for this version
            xml_url = (
                f"{self.base_url}/Content/Bills/{parl_str}/{bill_type}/"
                f"{bill_upper}/{bill_upper}_{i}/{bill_upper}_E.xml"
            )

            versions.append(BillVersion(
                stage=stage,
                version_number=i,
                xml_url=xml_url,
                pdf_url=xml_url.replace("_E.xml", f"_{i}.PDF"),
                publication_type_id=type_id,
                publication_type_name=type_name_en,
                publication_date=pub_date,
                has_amendments=has_amendments,
            ))

        return versions

    def extract_amendment_events(
        self,
        metadata: Dict[str, Any],
    ) -> List[BillAmendmentEvent]:
        """Extract amendment events from LEGISinfo JSON metadata.

        Looks for events like:
        - "Committee report presented with amendments"
        - "Senate amendment"
        - "Report stage amendments"

        LEGISinfo uses multiple places for events:
        - SignificantEvents: Major events like committee reports with amendments
        - Sittings: Sitting-level events with descriptions
        - Decisions: Amendment decisions (if any)
        """
        events = []

        # Check House and Senate bill stages
        bill_stages = metadata.get("BillStages", {})

        for chamber_key in ["HouseBillStages", "SenateBillStages"]:
            chamber = "House" if "House" in chamber_key else "Senate"
            stages = bill_stages.get(chamber_key, [])

            for stage_data in stages:
                stage_name = stage_data.get("BillStageNameEn", "")

                # Get committee info if available
                committee = stage_data.get("Committee", {}) or {}
                committee_code = committee.get("CommitteeAcronym")
                committee_name = committee.get("CommitteeNameEn")

                # Check SignificantEvents (main source for amendment events)
                significant_events = stage_data.get("SignificantEvents", []) or []
                for event in significant_events:
                    event_name = event.get("EventNameEn", "")

                    # Check if this is an amendment-related event
                    if any(term in event_name.lower() for term in ["amendment", "amended"]):
                        # Parse event date
                        event_date = None
                        event_date_str = event.get("EventDateTime")
                        if event_date_str:
                            try:
                                # Handle date-only strings
                                if "T" in event_date_str:
                                    event_date = datetime.fromisoformat(
                                        event_date_str.replace("Z", "+00:00")
                                    )
                                else:
                                    event_date = datetime.fromisoformat(event_date_str)
                            except (ValueError, TypeError):
                                pass

                        events.append(BillAmendmentEvent(
                            event_type=event_name.lower().replace(" ", "_"),
                            description_en=event_name,
                            description_fr=event.get("EventNameFr"),
                            event_date=event_date,
                            chamber=chamber,
                            stage=stage_name,
                            committee_code=committee_code,
                            committee_name=committee_name,
                            report_id=event.get("CommitteeReportId"),
                            report_number=event.get("CommitteeReportNumber"),
                            number_of_amendments=event.get("NumberOfAmendments"),
                        ))

                # Also check Sittings for amendment-related descriptions
                sittings = stage_data.get("Sittings", []) or []
                for sitting in sittings:
                    sitting_name = sitting.get("NameEn", "")

                    # Only add if amendment-related and not already captured
                    if any(term in sitting_name.lower() for term in ["amendment", "amended"]):
                        # Parse sitting date
                        sitting_date = None
                        sitting_date_str = sitting.get("Date")
                        if sitting_date_str:
                            try:
                                if "T" in sitting_date_str:
                                    sitting_date = datetime.fromisoformat(
                                        sitting_date_str.replace("Z", "+00:00")
                                    )
                                else:
                                    sitting_date = datetime.fromisoformat(sitting_date_str)
                            except (ValueError, TypeError):
                                pass

                        # Check if we already have this event from SignificantEvents
                        is_duplicate = any(
                            e.description_en == sitting_name and e.event_date == sitting_date
                            for e in events
                        )

                        if not is_duplicate:
                            events.append(BillAmendmentEvent(
                                event_type=sitting_name.lower().replace(" ", "_"),
                                description_en=sitting_name,
                                description_fr=sitting.get("NameFr"),
                                event_date=sitting_date,
                                chamber=chamber,
                                stage=stage_name,
                                committee_code=committee_code,
                                committee_name=committee_name,
                                report_id=None,
                                report_number=None,
                                number_of_amendments=None,
                            ))

        return events

    def parse_bill_with_history(
        self,
        parliament: int,
        session: int,
        bill_number: str,
        version: int = 1,
        *,
        is_government: bool = False,
        include_all_versions: bool = True,
    ) -> ParsedBill:
        """Fetch and parse a bill with full version and amendment history.

        This is the main entry point that combines:
        1. Bill structure parsing from XML
        2. Version history from LEGISinfo JSON
        3. Amendment events from LEGISinfo JSON

        Args:
            parliament: Parliament number (e.g., 45)
            session: Session number (e.g., 1)
            bill_number: Bill code (e.g., "C-234")
            version: Version number to parse (1=first reading, etc.)
            is_government: True for government bills
            include_all_versions: If True, fetch all available versions metadata

        Returns:
            ParsedBill with full structured content and history
        """
        # Parse the XML structure
        bill = self.parse_bill(
            parliament, session, bill_number, version, is_government=is_government
        )

        # Fetch LEGISinfo metadata for version and amendment history
        try:
            metadata = self.get_legisinfo_metadata(parliament, session, bill_number)

            # Extract version information
            if include_all_versions:
                bill.available_versions = self.extract_versions_from_legisinfo(
                    metadata, parliament, session, bill_number, is_government=is_government
                )

            # Extract amendment events
            bill.amendment_events = self.extract_amendment_events(metadata)

            # Set current version metadata
            for ver in bill.available_versions:
                if ver.version_number == version:
                    bill.publication_type_name = ver.publication_type_name
                    bill.has_amendments = ver.has_amendments
                    break

            # Set LEGISinfo URL
            bill.legisinfo_url = f"{LEGISINFO_BASE}/bill/{parliament}-{session}/{bill_number.lower()}"

        except Exception:
            # LEGISinfo metadata is optional, continue without it
            pass

        return bill


def to_dict(obj: Any) -> Dict[str, Any]:
    """Convert dataclass to dict recursively (for JSON serialization)."""
    if isinstance(obj, list):
        return [to_dict(item) for item in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if hasattr(obj, "__dataclass_fields__"):
        result = {}
        for key in obj.__dataclass_fields__:
            value = getattr(obj, key)
            if isinstance(value, Enum):
                result[key] = value.value
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, list):
                result[key] = [to_dict(item) for item in value]
            elif hasattr(value, "__dataclass_fields__"):
                result[key] = to_dict(value)
            else:
                result[key] = value
        return result
    return obj
