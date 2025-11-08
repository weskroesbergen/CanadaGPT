"""Client for House of Commons government roles (Cabinet ministers, Parliamentary Secretaries)."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from fedmcp.http import RateLimitedSession


DEFAULT_BASE_URL = "https://www.ourcommons.ca/Members/en"


@dataclass
class Minister:
    """A Cabinet minister or Prime Minister."""

    person_id: int
    first_name: str
    last_name: str
    title: str
    from_date: datetime
    to_date: Optional[datetime]
    order_of_precedence: int
    honorific: str

    @property
    def full_name(self) -> str:
        """Full name with honorific."""
        return f"{self.honorific} {self.first_name} {self.last_name}".strip()

    @property
    def is_current(self) -> bool:
        """Whether this is a current role."""
        return self.to_date is None


@dataclass
class ParliamentarySecretary:
    """A Parliamentary Secretary."""

    person_id: int
    first_name: str
    last_name: str
    title: str
    constituency: str
    province: str
    party: str
    honorific: str

    @property
    def full_name(self) -> str:
        """Full name with honorific."""
        return f"{self.honorific} {self.first_name} {self.last_name}".strip()


class GovernmentRolesClient:
    """Client for fetching Cabinet ministers and Parliamentary Secretaries.

    Data is fetched from House of Commons Open Data XML feeds:
    - Cabinet Ministers: https://www.ourcommons.ca/Members/en/ministries/XML
    - Parliamentary Secretaries: https://www.ourcommons.ca/Members/en/parliamentary-secretaries/XML

    Note:
        No rate limiting needed - these are static XML exports updated infrequently.
    """

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        session: Optional[RateLimitedSession] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or RateLimitedSession()

    def get_ministers(self) -> List[Minister]:
        """Fetch all current and historical Cabinet ministers.

        Returns:
            List of Minister objects ordered by precedence.

        Example:
            >>> client = GovernmentRolesClient()
            >>> ministers = client.get_ministers()
            >>> pm = ministers[0]
            >>> print(pm.title)
            Prime Minister
        """
        url = f"{self.base_url}/ministries/XML"
        response = self.session.get(url)
        response.raise_for_status()

        # Parse XML
        root = ET.fromstring(response.content)
        ministers = []

        for minister_elem in root.findall(".//{http://www.w3.org/2001/XMLSchema}Minister") or root.findall(".//Minister"):
            # Handle both namespaced and non-namespaced XML
            person_id = self._get_text(minister_elem, "PersonId")
            first_name = self._get_text(minister_elem, "PersonOfficialFirstName")
            last_name = self._get_text(minister_elem, "PersonOfficialLastName")
            title = self._get_text(minister_elem, "Title")
            from_date_str = self._get_text(minister_elem, "FromDateTime")
            to_date_str = self._get_text(minister_elem, "ToDateTime")
            order = self._get_text(minister_elem, "OrderOfPrecedence")
            honorific = self._get_text(minister_elem, "PersonShortHonorific")

            # Parse dates
            from_date = datetime.fromisoformat(from_date_str.replace("Z", "+00:00")) if from_date_str else None
            to_date = None
            if to_date_str and to_date_str.strip():
                try:
                    to_date = datetime.fromisoformat(to_date_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass

            if person_id and first_name and last_name and title and from_date:
                ministers.append(Minister(
                    person_id=int(person_id),
                    first_name=first_name,
                    last_name=last_name,
                    title=title,
                    from_date=from_date,
                    to_date=to_date,
                    order_of_precedence=int(order) if order else 999,
                    honorific=honorific or ""
                ))

        # Sort by order of precedence
        ministers.sort(key=lambda m: m.order_of_precedence)
        return ministers

    def get_parliamentary_secretaries(self) -> List[ParliamentarySecretary]:
        """Fetch all current Parliamentary Secretaries.

        Returns:
            List of ParliamentarySecretary objects.

        Example:
            >>> client = GovernmentRolesClient()
            >>> pss = client.get_parliamentary_secretaries()
            >>> for ps in pss[:5]:
            ...     print(f"{ps.full_name} - {ps.title}")
        """
        url = f"{self.base_url}/parliamentary-secretaries/XML"
        response = self.session.get(url)
        response.raise_for_status()

        # Parse XML
        root = ET.fromstring(response.content)
        secretaries = []

        for ps_elem in root.findall(".//{http://www.w3.org/2001/XMLSchema}ParliamentarySecretary") or root.findall(".//ParliamentarySecretary"):
            person_id = self._get_text(ps_elem, "PersonId")
            first_name = self._get_text(ps_elem, "PersonOfficialFirstName")
            last_name = self._get_text(ps_elem, "PersonOfficialLastName")
            title = self._get_text(ps_elem, "Title")
            constituency = self._get_text(ps_elem, "ConstituencyName")
            province = self._get_text(ps_elem, "ProvinceTerritoryName")
            party = self._get_text(ps_elem, "CaucusShortName")
            honorific = self._get_text(ps_elem, "PersonShortHonorific")

            if person_id and first_name and last_name and title:
                secretaries.append(ParliamentarySecretary(
                    person_id=int(person_id),
                    first_name=first_name,
                    last_name=last_name,
                    title=title,
                    constituency=constituency or "",
                    province=province or "",
                    party=party or "",
                    honorific=honorific or ""
                ))

        return secretaries

    def _get_text(self, element: ET.Element, tag: str) -> str:
        """Safely extract text from XML element."""
        # Try with namespace
        ns_elem = element.find(f".//{{http://www.w3.org/2001/XMLSchema}}{tag}")
        if ns_elem is not None and ns_elem.text:
            return ns_elem.text.strip()

        # Try without namespace
        elem = element.find(f".//{tag}")
        if elem is not None and elem.text:
            return elem.text.strip()

        return ""
