"""Helpers for fetching MP XML exports from the House of Commons."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from fedmcp.http import RateLimitedSession


MP_SEARCH_XML_URL = "https://www.ourcommons.ca/Members/en/search/xml"


@dataclass
class MPRecord:
    """A single MP record from OurCommons XML."""

    person_id: int  # PersonId - stable House of Commons database ID
    first_name: str  # PersonOfficialFirstName
    last_name: str  # PersonOfficialLastName
    constituency: str  # ConstituencyName
    province: str  # ConstituencyProvinceTerritoryName
    party: str  # CaucusShortName
    term_start: str  # FromDateTime (ISO datetime)
    honorific: Optional[str] = None  # PersonShortHonorific - "Hon.", "Right Hon.", or None
    term_end: Optional[str] = None  # ToDateTime (ISO datetime or None if current)

    @property
    def is_current(self) -> bool:
        """Check if this MP is currently serving (no term end date)."""
        return self.term_end is None

    @property
    def full_name(self) -> str:
        """Return full name with honorific if present."""
        if self.honorific:
            return f"{self.honorific} {self.first_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"


class OurCommonsMPsClient:
    """Retrieve and parse MP data from OurCommons XML."""

    def __init__(
        self,
        *,
        session: Optional[RateLimitedSession] = None,
    ) -> None:
        self.session = session or RateLimitedSession()

    # ------------------------------------------------------------------
    # Fetch helpers
    # ------------------------------------------------------------------
    def fetch_mps_xml(self) -> str:
        """Fetch the bulk MPs XML."""
        response = self.session.get(MP_SEARCH_XML_URL, headers={"Accept": "application/xml"})
        response.raise_for_status()
        return response.content.decode('utf-8-sig')

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------
    def parse_mps(self, xml_text: str) -> List[MPRecord]:
        """Parse MP XML into list of MPRecord objects."""
        from xml.etree import ElementTree as ET

        # Strip UTF-8 BOM if present
        if xml_text.startswith('\ufeff'):
            xml_text = xml_text[1:]

        root = ET.fromstring(xml_text)

        mps = []
        for mp_el in root.findall("MemberOfParliament"):
            person_id = int(mp_el.findtext("PersonId", "0"))
            first_name = mp_el.findtext("PersonOfficialFirstName", "")
            last_name = mp_el.findtext("PersonOfficialLastName", "")
            constituency = mp_el.findtext("ConstituencyName", "")
            province = mp_el.findtext("ConstituencyProvinceTerritoryName", "")
            party = mp_el.findtext("CaucusShortName", "")
            term_start = mp_el.findtext("FromDateTime", "")

            # Handle honorific - empty element means no honorific
            honorific_el = mp_el.find("PersonShortHonorific")
            honorific = None
            if honorific_el is not None and honorific_el.text:
                honorific = honorific_el.text.strip()

            # Handle ToDateTime - check for xsi:nil="true"
            term_end_el = mp_el.find("ToDateTime")
            term_end = None
            if term_end_el is not None:
                # Check for xsi:nil attribute
                nil_attr = term_end_el.get("{http://www.w3.org/2001/XMLSchema-instance}nil")
                if nil_attr != "true" and term_end_el.text:
                    term_end = term_end_el.text.strip()

            mps.append(MPRecord(
                person_id=person_id,
                first_name=first_name,
                last_name=last_name,
                constituency=constituency,
                province=province,
                party=party,
                term_start=term_start,
                honorific=honorific,
                term_end=term_end
            ))

        return mps

    # ------------------------------------------------------------------
    # Convenience API
    # ------------------------------------------------------------------
    def get_all_mps(self) -> List[MPRecord]:
        """Get all MPs from XML (current and former)."""
        xml = self.fetch_mps_xml()
        return self.parse_mps(xml)

    def get_current_mps(self) -> List[MPRecord]:
        """Get only current MPs (no term end date)."""
        all_mps = self.get_all_mps()
        return [mp for mp in all_mps if mp.is_current]

    def get_mp_by_person_id(self, person_id: int) -> Optional[MPRecord]:
        """Get a specific MP by their PersonId."""
        all_mps = self.get_all_mps()
        matching = [mp for mp in all_mps if mp.person_id == person_id]
        return matching[0] if matching else None

    def get_mps_by_party(self, party: str) -> List[MPRecord]:
        """Get all MPs from a specific party."""
        all_mps = self.get_all_mps()
        return [mp for mp in all_mps if mp.party.lower() == party.lower()]

    def get_mps_with_honorific(self, honorific: str) -> List[MPRecord]:
        """
        Get MPs with a specific honorific.

        Args:
            honorific: "Hon.", "Right Hon.", etc.

        Returns:
            List of MPs with that honorific
        """
        all_mps = self.get_all_mps()
        return [mp for mp in all_mps if mp.honorific and mp.honorific == honorific]

    def get_former_pms(self) -> List[MPRecord]:
        """Get MPs with 'Right Hon.' honorific (former Prime Ministers)."""
        return self.get_mps_with_honorific("Right Hon.")

    def get_ministers(self) -> List[MPRecord]:
        """Get MPs with 'Hon.' honorific (current and former ministers)."""
        return self.get_mps_with_honorific("Hon.")
