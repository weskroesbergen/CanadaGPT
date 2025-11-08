"""Client for scraping committee membership from House of Commons website."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from bs4 import BeautifulSoup
from fedmcp.http import RateLimitedSession


BASE_URL = "https://www.ourcommons.ca/Committees/en"


@dataclass
class CommitteeMember:
    """Represents a committee member with their role."""

    name: str
    role: str  # Chair, Vice-Chair, Member
    party: Optional[str] = None
    riding: Optional[str] = None
    province: Optional[str] = None
    mp_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'role': self.role,
            'party': self.party,
            'riding': self.riding,
            'province': self.province,
            'mp_url': self.mp_url,
        }


class CommitteeMembershipClient:
    """Client for scraping committee membership from House of Commons."""

    def __init__(self, *, session: Optional[RateLimitedSession] = None) -> None:
        self.session = session or RateLimitedSession()
        self.base_url = BASE_URL

    def get_committee_members(self, committee_code: str) -> List[CommitteeMember]:
        """
        Fetch all members of a committee.

        Args:
            committee_code: Committee acronym (e.g., "ETHI", "FINA")

        Returns:
            List of CommitteeMember objects
        """
        url = f"{self.base_url}/{committee_code}"
        response = self.session.get(url)
        response.raise_for_status()

        return self._parse_members(response.text)

    def _parse_members(self, html: str) -> List[CommitteeMember]:
        """Parse committee members from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        members = []
        seen_urls = set()  # Deduplicate by URL since each member appears twice in HTML

        # Compile role matching regex
        role_pattern = re.compile(r'^(Chair|Co-Chair|Vice-Chairs?|Members?)s?$', re.IGNORECASE)

        # Find all h2 tags and filter by role headings manually
        # (BeautifulSoup's string parameter with regex is unreliable)
        all_h2_tags = soup.find_all('h2')
        role_headings = [h2 for h2 in all_h2_tags if role_pattern.match(h2.get_text(strip=True))]

        for heading in role_headings:
            heading_text = heading.get_text(strip=True)

            # Normalize role names
            if heading_text.lower() in ['member', 'members']:
                role = 'Member'
            elif heading_text.lower() in ['vice-chair', 'vice-chairs']:
                role = 'Vice-Chair'
            elif heading_text.lower() in ['co-chair']:
                role = 'Co-Chair'
            elif heading_text.lower() == 'chair':
                role = 'Chair'
            else:
                role = heading_text.capitalize()

            # Find all member links that come after this heading
            # They are siblings of the heading until we hit another h2
            current = heading.find_next_sibling()

            while current and current.name != 'h2':
                # Find all member links within this sibling
                if current.name:
                    links = current.find_all('a', href=re.compile(r'/members/en/'))

                    for link in links:
                        href = link.get('href', '')

                        # Deduplicate by URL
                        if href and href not in seen_urls:
                            seen_urls.add(href)
                            member = self._parse_member_link(link, role)
                            if member:
                                members.append(member)

                current = current.find_next_sibling()

        return members

    def _parse_member_link(self, link, role: str) -> Optional[CommitteeMember]:
        """
        Parse a member from an anchor tag.

        The text typically contains: "FirstName LastName Party Riding Province"
        Example: "John Brassard Conservative Barrie South—Innisfil Ontario"
        """
        text = link.get_text(strip=True)
        href = link.get('href', '')

        if not text:
            return None

        # Extract the full URL
        mp_url = href if href.startswith('http') else f"https://www.ourcommons.ca{href}"

        # Parse the text - it's space-separated with name first
        # Try to extract name from the URL first since it's more reliable
        # URL format: /members/en/FirstName-LastName(ID)
        name_match = re.search(r'/members/en/([^(]+)\(', href)
        if name_match:
            # Convert "FirstName-LastName" to "FirstName LastName"
            name = name_match.group(1).replace('-', ' ')
        else:
            # Fallback: assume first two words are the name
            parts = text.split()
            if len(parts) >= 2:
                name = f"{parts[0]} {parts[1]}"
            else:
                name = text

        # Try to parse party, riding, province from the text
        # This is harder because they're not delimited, but we can make educated guesses
        # Common parties: Conservative, Liberal, NDP, Bloc Québécois, Green
        party_match = re.search(r'\b(Conservative|Liberal|NDP|Bloc Qu[ée]b[ée]cois|Green)\b', text, re.IGNORECASE)
        party = party_match.group(1) if party_match else None

        # Common provinces (abbreviated or full name at the end)
        province_match = re.search(r'\b(Ontario|Quebec|British Columbia|Alberta|Saskatchewan|Manitoba|'
                                   r'Nova Scotia|New Brunswick|Newfoundland and Labrador|'
                                   r'Prince Edward Island|Northwest Territories|Nunavut|Yukon|'
                                   r'ON|QC|BC|AB|SK|MB|NS|NB|NL|PE|NT|NU|YT)\b', text, re.IGNORECASE)
        province = province_match.group(1) if province_match else None

        # Riding is whatever's between party and province (if both exist)
        riding = None
        if party_match and province_match:
            # Extract the text between party and province
            start_idx = party_match.end()
            end_idx = province_match.start()
            riding = text[start_idx:end_idx].strip()

        return CommitteeMember(
            name=name,
            role=role,
            party=party,
            riding=riding,
            province=province,
            mp_url=mp_url
        )
