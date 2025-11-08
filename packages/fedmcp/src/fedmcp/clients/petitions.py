"""Client for fetching House of Commons petition data."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

from fedmcp.http import RateLimitedSession


BASE_URL = "https://www.ourcommons.ca/petitions/en/Petition/Search"


@dataclass
class PetitionSponsor:
    """Represents the MP sponsor of a petition."""

    first_name: str
    last_name: str
    constituency: str
    caucus: str
    province_code: str
    honorific: Optional[str] = None

    @property
    def full_name(self) -> str:
        """Full name with honorific if present."""
        if self.honorific:
            return f"{self.honorific} {self.first_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"


@dataclass
class ProvincialSignatures:
    """Signature breakdown by province/territory."""

    province: str
    signature_count: int


@dataclass
class Petition:
    """Represents a House of Commons petition."""

    petition_id: str
    petition_number: str
    title: str
    petition_type_id: str
    parliament_number: int
    session: int
    signature_count: int
    status_id: str
    status_name: str
    status_reached_date: Optional[str] = None
    petitioner_first_name: Optional[str] = None
    petitioner_last_name: Optional[str] = None
    sponsor: Optional[PetitionSponsor] = None
    signature_opening_date: Optional[str] = None
    signature_closing_date: Optional[str] = None
    presented_date: Optional[str] = None
    certification_date: Optional[str] = None
    government_response_date: Optional[str] = None
    prayer_text: Optional[str] = None
    grievances_text: Optional[str] = None
    response_text: Optional[str] = None
    index_terms: List[str] = field(default_factory=list)
    provincial_signatures: List[ProvincialSignatures] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'petition_id': self.petition_id,
            'petition_number': self.petition_number,
            'title': self.title,
            'parliament': f"{self.parliament_number}-{self.session}",
            'signature_count': self.signature_count,
            'status': self.status_name,
            'status_reached_date': self.status_reached_date,
            'petitioner_name': f"{self.petitioner_first_name or ''} {self.petitioner_last_name or ''}".strip() or None,
            'sponsor': self.sponsor.full_name if self.sponsor else None,
            'sponsor_constituency': self.sponsor.constituency if self.sponsor else None,
            'sponsor_party': self.sponsor.caucus if self.sponsor else None,
            'signature_period': f"{self.signature_opening_date} to {self.signature_closing_date}" if self.signature_opening_date else None,
            'presented_date': self.presented_date,
            'certification_date': self.certification_date,
            'government_response_date': self.government_response_date,
            'prayer': self.prayer_text,
            'grievances': self.grievances_text,
            'response': self.response_text,
            'topics': self.index_terms,
            'provincial_signatures': [
                {'province': ps.province, 'signatures': ps.signature_count}
                for ps in self.provincial_signatures
            ],
        }


class PetitionsClient:
    """Client for fetching House of Commons petition data."""

    def __init__(self, *, session: Optional[RateLimitedSession] = None) -> None:
        self.session = session or RateLimitedSession()
        self.base_url = BASE_URL

    def list_petitions(
        self,
        category: str = "All",
        limit: Optional[int] = None
    ) -> List[Petition]:
        """
        Fetch all petitions, optionally filtered by category.

        Args:
            category: One of "All", "Open", "Closed", "Responses" (default: "All")
            limit: Maximum number of petitions to return

        Returns:
            List of Petition objects
        """
        params = {
            'Category': category,
            'output': 'xml'
        }

        response = self.session.get(self.base_url, params=params)
        response.raise_for_status()

        petitions = self._parse_xml(response.text)

        if limit:
            return petitions[:limit]
        return petitions

    def search_petitions(
        self,
        keyword: Optional[str] = None,
        sponsor_name: Optional[str] = None,
        category: str = "All",
        limit: Optional[int] = None
    ) -> List[Petition]:
        """
        Search for petitions by keyword and/or sponsor.

        Args:
            keyword: Search term for petition title, prayer text, or topics (case-insensitive)
            sponsor_name: MP sponsor name (full or partial, case-insensitive)
            category: One of "All", "Open", "Closed", "Responses"
            limit: Maximum number of results

        Returns:
            List of matching Petition objects
        """
        # Fetch all petitions in the category
        all_petitions = self.list_petitions(category=category)

        # Apply client-side filtering
        results = all_petitions

        if keyword:
            keyword_lower = keyword.lower()
            results = [
                p for p in results
                if (keyword_lower in p.title.lower()
                    or (p.prayer_text and keyword_lower in p.prayer_text.lower())
                    or (p.grievances_text and keyword_lower in p.grievances_text.lower())
                    or any(keyword_lower in term.lower() for term in p.index_terms))
            ]

        if sponsor_name:
            sponsor_lower = sponsor_name.lower()
            results = [
                p for p in results
                if p.sponsor and sponsor_lower in p.sponsor.full_name.lower()
            ]

        if limit:
            return results[:limit]
        return results

    def get_petition(self, petition_number: str) -> Optional[Petition]:
        """
        Get a specific petition by its number (e.g., "e-6629" or "451-00231").

        Args:
            petition_number: Petition number

        Returns:
            Petition object if found, None otherwise
        """
        # Fetch all petitions and filter
        all_petitions = self.list_petitions()

        for petition in all_petitions:
            if petition.petition_number.lower() == petition_number.lower():
                return petition

        return None

    def search_by_topic(
        self,
        topic: str,
        category: str = "All",
        limit: Optional[int] = None
    ) -> List[Petition]:
        """
        Search petitions by topic/subject area.

        Args:
            topic: Topic keyword (e.g., "environment", "taxation", "fisheries")
            category: One of "All", "Open", "Closed", "Responses"
            limit: Maximum number of results

        Returns:
            List of matching Petition objects
        """
        all_petitions = self.list_petitions(category=category)
        topic_lower = topic.lower()

        matching = [
            p for p in all_petitions
            if any(topic_lower in term.lower() for term in p.index_terms)
            or topic_lower in p.title.lower()
        ]

        if limit:
            return matching[:limit]
        return matching

    def get_petitions_by_mp(
        self,
        mp_name: str,
        category: str = "All"
    ) -> List[Petition]:
        """
        Get all petitions sponsored by a specific MP.

        Args:
            mp_name: MP name (full or partial, case-insensitive)
            category: One of "All", "Open", "Closed", "Responses"

        Returns:
            List of Petition objects sponsored by the MP
        """
        return self.search_petitions(sponsor_name=mp_name, category=category)

    def _parse_xml(self, xml_text: str) -> List[Petition]:
        """Parse petition XML into list of Petition objects."""
        petitions = []

        # Strip BOM if present
        if xml_text.startswith('\ufeff'):
            xml_text = xml_text[1:]

        # Handle empty responses
        if not xml_text or not xml_text.strip():
            return petitions

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            raise ValueError(f"Failed to parse petition XML: {e}")

        for petition_el in root.findall(".//Petition"):
            try:
                petition = self._parse_petition_element(petition_el)
                # Only include petitions with valid data
                if petition.petition_number and petition.title:
                    petitions.append(petition)
            except Exception as e:
                # Skip malformed petition entries
                continue

        return petitions

    def _parse_petition_element(self, el: ET.Element) -> Petition:
        """Parse a single Petition XML element."""
        # Extract attributes
        petition_id = el.get('Id', '')
        title = el.get('Title', '')
        petition_type_id = el.get('TypeId', '')
        parliament_number = int(el.get('ParliamentNumber', '0'))
        session = int(el.get('Session', '0'))
        signature_count = int(el.get('SignatureCount', '0'))

        # Extract child elements
        petition_number = self._get_text(el, 'PetitionNumber')
        status_id = self._get_text(el, 'StatusId')
        status_name = self._get_text(el, 'StatusName')
        status_reached_date = self._get_text(el, 'StatusReachedDateTime')

        petitioner_first = self._get_text(el, 'PetitionerFirstName')
        petitioner_last = self._get_text(el, 'PetitionerLastName')

        # Parse sponsor
        sponsor = None
        sponsor_el = el.find('Sponsor')
        if sponsor_el is not None:
            sponsor = PetitionSponsor(
                honorific=self._get_text(sponsor_el, 'ShortHonorific') or None,
                first_name=self._get_text(sponsor_el, 'FirstName', ''),
                last_name=self._get_text(sponsor_el, 'LastName', ''),
                constituency=self._get_text(sponsor_el, 'Constituency', ''),
                caucus=self._get_text(sponsor_el, 'Caucus', ''),
                province_code=self._get_text(sponsor_el, 'ProvinceCode', ''),
            )

        # Parse dates
        signature_opening = self._get_text(el, 'SignatureOpeningDateTime')
        signature_closing = self._get_text(el, 'SignatureClosingDateTime')
        presented_date = self._get_text(el, 'PresentedDateTime')
        certification_date = self._get_text(el, 'CertificationDateTime')
        government_response_date = self._get_text(el, 'GovernmentResponseDateTime')

        # Parse provincial signatures
        provincial_sigs = []
        for prov_el in el.findall('.//ProvinceSignatures'):
            provincial_sigs.append(
                ProvincialSignatures(
                    province=prov_el.get('Province', ''),
                    signature_count=int(prov_el.get('SignatureCount', '0')),
                )
            )

        # Parse prayer (petition text)
        prayer_text = None
        grievances_text = None
        prayer_el = el.find('.//Prayer')
        if prayer_el is not None:
            # Extract grievances
            grievances_el = prayer_el.find('.//Grievances')
            if grievances_el is not None:
                grievances_parts = []
                for whereas in grievances_el.findall('.//WhereAs'):
                    text = ''.join(whereas.itertext()).strip()
                    if text:
                        grievances_parts.append(text)
                if grievances_parts:
                    grievances_text = '\n\n'.join(grievances_parts)

            # Extract prayer/call to action
            prayer_parts = []
            for para in prayer_el.findall('.//Para'):
                text = ''.join(para.itertext()).strip()
                if text and text != '<?xm-replace_text Para?>':
                    prayer_parts.append(text)
            if prayer_parts:
                prayer_text = '\n\n'.join(prayer_parts)

        # Parse government response
        response_text = None
        response_el = el.find('.//Response')
        if response_el is not None:
            response_parts = []
            for para in response_el.findall('.//para'):
                text = ''.join(para.itertext()).strip()
                if text:
                    response_parts.append(text)
            if response_parts:
                response_text = '\n\n'.join(response_parts)

        # Parse index terms
        index_terms = []
        for term_el in el.findall('.//Term'):
            term_text = term_el.text
            if term_text:
                index_terms.append(term_text.strip())

        return Petition(
            petition_id=petition_id,
            petition_number=petition_number or '',
            title=title,
            petition_type_id=petition_type_id,
            parliament_number=parliament_number,
            session=session,
            signature_count=signature_count,
            status_id=status_id or '',
            status_name=status_name or '',
            status_reached_date=status_reached_date,
            petitioner_first_name=petitioner_first if petitioner_first else None,
            petitioner_last_name=petitioner_last if petitioner_last else None,
            sponsor=sponsor,
            signature_opening_date=signature_opening,
            signature_closing_date=signature_closing,
            presented_date=presented_date,
            certification_date=certification_date,
            government_response_date=government_response_date,
            prayer_text=prayer_text,
            grievances_text=grievances_text,
            response_text=response_text,
            index_terms=index_terms,
            provincial_signatures=provincial_sigs,
        )

    @staticmethod
    def _get_text(element: ET.Element, tag: str, default: str = '') -> str:
        """Safely extract text from an XML element."""
        child = element.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return default
