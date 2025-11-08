"""
Client for scraping committee membership data from parl.ca.

The House of Commons provides committee membership information at:
https://www.parl.ca/Committees/en/{COMMITTEE_CODE}/Members

This client scrapes these pages to extract:
- Committee names and codes
- Member names and parties
- Member roles (Chair, Vice-Chair, Member)
"""

from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import re

from fedmcp.http import RateLimitedSession


class CommitteeClient:
    """
    Client for fetching committee membership data from parl.ca.
    """

    BASE_URL = "https://www.parl.ca/Committees/en"

    # Committee codes from https://www.ourcommons.ca/Committees/en/List
    COMMITTEE_CODES = [
        "ACVA",  # Veterans Affairs
        "AGRI",  # Agriculture
        "BILI",  # Library of Parliament (Joint)
        "CHPC",  # Canadian Heritage
        "CIIT",  # International Trade
        "CIMM",  # Immigration
        "ENVI",  # Environment
        "ETHI",  # Ethics
        "FAAE",  # Foreign Affairs
        "FINA",  # Finance
        "FOPO",  # Fisheries
        "HESA",  # Health
        "HUMA",  # Human Resources
        "INAN",  # Indigenous Affairs
        "INDU",  # Industry
        "JUST",  # Justice
        "LANG",  # Official Languages
        "NDDN",  # National Defence
        "OGGO",  # Government Operations
        "PACP",  # Public Accounts
        "PROC",  # Procedure and House Affairs
        "RNNR",  # Natural Resources
        "SECU",  # Public Safety
        "SRSR",  # Science and Research
        "TRAN",  # Transport
        "FEWO",  # Status of Women
        "HOIR",  # Standing Committee on House Officers (internal)
        "BOIE",  # Board of Internal Economy
        "LIBR",  # Library (internal)
        "DEDC",  # Special Committee on the Defence Policy
        "REGS",  # Scrutiny of Regulations (Joint)
    ]

    def __init__(self, session: Optional[RateLimitedSession] = None):
        """
        Initialize the committee client.

        Args:
            session: Optional rate-limited session to use
        """
        self.session = session or RateLimitedSession(min_request_interval=0.5)

    def list_committees(self) -> List[Dict[str, str]]:
        """
        Get a list of all committee codes and names.

        Returns:
            List of dicts with 'code' and 'name' keys
        """
        # For now, return the hardcoded list
        # In the future, could scrape from https://www.ourcommons.ca/Committees/en/List
        return [{"code": code} for code in self.COMMITTEE_CODES]

    def get_committee_members(self, committee_code: str) -> Dict:
        """
        Fetch committee membership for a specific committee.

        Args:
            committee_code: Committee code (e.g., 'BILI', 'FINA')

        Returns:
            Dict with committee info and members:
            {
                'code': 'BILI',
                'name': 'Standing Joint Committee on the Library of Parliament',
                'parliament': '45',
                'session': '1',
                'members': [
                    {
                        'name': 'Terry Beech',
                        'party': 'Liberal',
                        'role': 'Member',  # or 'Chair', 'Vice-Chair'
                        'chamber': 'House'  # or 'Senate'
                    },
                    ...
                ]
            }
        """
        url = f"{self.BASE_URL}/{committee_code}/Members"

        try:
            response = self.session.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract committee name
            committee_name = self._extract_committee_name(soup)

            # Extract parliament and session
            parliament, session = self._extract_parliament_session(soup)

            # Extract members
            members = self._extract_members(soup)

            return {
                'code': committee_code,
                'name': committee_name,
                'parliament': parliament,
                'session': session,
                'members': members
            }

        except Exception as e:
            print(f"Error fetching committee {committee_code}: {e}")
            return {
                'code': committee_code,
                'name': None,
                'parliament': None,
                'session': None,
                'members': []
            }

    def _extract_committee_name(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract committee name from the page."""
        # Try to find the committee name in the heading
        heading = soup.find('h1')
        if heading:
            text = heading.get_text(strip=True)
            # Remove " - Members" suffix if present
            return re.sub(r'\s*-\s*Members.*$', '', text)
        return None

    def _extract_parliament_session(self, soup: BeautifulSoup) -> tuple:
        """Extract parliament number and session from the page."""
        # Look for session information in the page
        # Usually in format like "45th Parliament, 1st Session"
        session_text = soup.find(string=re.compile(r'\d+(?:st|nd|rd|th)\s+Parliament'))

        if session_text:
            # Extract parliament number (e.g., "45")
            parl_match = re.search(r'(\d+)(?:st|nd|rd|th)\s+Parliament', session_text)
            # Extract session number (e.g., "1")
            sess_match = re.search(r'(\d+)(?:st|nd|rd|th)\s+Session', session_text)

            parliament = parl_match.group(1) if parl_match else None
            session = sess_match.group(1) if sess_match else None

            return parliament, session

        return None, None

    def _extract_members(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Extract member information from the committee page.

        Returns list of member dicts with name, party, role, and chamber.
        """
        members = []

        # Find all member sections (Senate and House)
        # Look for sections with headings like "Senate Members" or "House of Commons Members"

        # Strategy: Find all <h2> or <h3> tags with "Members" in them
        # Then find the following list/table of names

        current_chamber = None
        current_party = None

        # Find all elements that might contain member info
        for element in soup.find_all(['h2', 'h3', 'h4', 'li', 'p', 'div']):
            text = element.get_text(strip=True)

            # Check if this is a chamber heading
            if 'Senate' in text and 'Member' in text:
                current_chamber = 'Senate'
                continue
            elif 'House of Commons' in text and 'Member' in text:
                current_chamber = 'House'
                continue
            elif 'House' in text and 'Member' in text and 'Senate' not in text:
                current_chamber = 'House'
                continue

            # Check if this is a party grouping
            party_match = re.match(r'^(Liberal|Conservative|NDP|New Democratic|Bloc Qu[ée]b[ée]cois|Green|Independent)', text, re.IGNORECASE)
            if party_match and 'Party' in text:
                current_party = self._normalize_party_name(party_match.group(1))
                continue

            # Check if this looks like a member name
            # Names typically have Hon., Mr., Ms., Dr., or are capitalized
            if current_chamber and self._looks_like_name(text):
                # Extract role if present (Chair, Vice-Chair)
                role = 'Member'  # default
                if 'Chair' in text:
                    if 'Vice' in text:
                        role = 'Vice-Chair'
                    else:
                        role = 'Chair'

                # Clean the name (remove titles, roles, etc.)
                name = self._clean_name(text)

                if name:
                    # Try to infer party from context if not explicitly set
                    party = current_party or self._infer_party_from_element(element)

                    members.append({
                        'name': name,
                        'party': party,
                        'role': role,
                        'chamber': current_chamber
                    })

        return members

    def _looks_like_name(self, text: str) -> bool:
        """Check if text looks like a person's name."""
        # Skip obvious non-names
        if not text or len(text) < 3:
            return False
        if text.lower() in ['member', 'members', 'chair', 'vice-chair', 'the', 'of', 'and']:
            return False

        # Names usually have capital letters and may have titles
        has_title = any(title in text for title in ['Hon.', 'Mr.', 'Ms.', 'Dr.', 'Mrs.'])
        has_capitals = any(c.isupper() for c in text)
        has_space_or_dash = ' ' in text or '-' in text

        return (has_title or has_capitals) and (has_space_or_dash or len(text.split()) >= 2)

    def _clean_name(self, text: str) -> str:
        """Clean a name by removing titles, roles, and extra whitespace."""
        # Remove titles
        name = re.sub(r'\b(Hon\.|Mr\.|Ms\.|Mrs\.|Dr\.)\s*', '', text)

        # Remove role indicators
        name = re.sub(r'\s*[\(\[]?(Chair|Vice-Chair|Member)[\)\]]?\s*', '', name, flags=re.IGNORECASE)

        # Remove extra whitespace
        name = ' '.join(name.split())

        return name

    def _normalize_party_name(self, party: str) -> str:
        """Normalize party names to standard forms."""
        party_lower = party.lower()

        if 'liberal' in party_lower:
            return 'Liberal'
        elif 'conservative' in party_lower or 'tory' in party_lower:
            return 'Conservative'
        elif 'ndp' in party_lower or 'new democratic' in party_lower:
            return 'NDP'
        elif 'bloc' in party_lower or 'québécois' in party_lower:
            return 'Bloc Québécois'
        elif 'green' in party_lower:
            return 'Green'
        elif 'independent' in party_lower:
            return 'Independent'
        else:
            return party

    def _infer_party_from_element(self, element) -> Optional[str]:
        """Try to infer party affiliation from nearby elements."""
        # Look at parent elements for party information
        parent = element.parent
        if parent:
            parent_text = parent.get_text()
            for party in ['Liberal', 'Conservative', 'NDP', 'Bloc Québécois', 'Green', 'Independent']:
                if party in parent_text:
                    return party
        return None

    def get_all_committee_members(self) -> List[Dict]:
        """
        Fetch membership data for all committees.

        Returns:
            List of committee dicts with membership info
        """
        results = []

        for committee in self.list_committees():
            code = committee['code']
            print(f"Fetching members for {code}...")

            members_data = self.get_committee_members(code)
            if members_data['members']:
                results.append(members_data)

        return results
