"""Client for fetching House Officers and Presiding Officers expenditure data."""
from __future__ import annotations

import csv
import io
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from fedmcp.http import RateLimitedSession


BASE_URL = "https://www.ourcommons.ca/proactivedisclosure/en/house-officers"


@dataclass
class HouseOfficerExpenditure:
    """Represents a House Officer's quarterly expenditure summary."""

    name: str
    role: str
    caucus: str
    salaries: float
    travel: float
    hospitality: float
    contracts: float
    fiscal_year: Optional[int] = None
    quarter: Optional[int] = None

    @property
    def total(self) -> float:
        """Total expenditures across all categories."""
        return self.salaries + self.travel + self.hospitality + self.contracts

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'role': self.role,
            'caucus': self.caucus,
            'salaries': self.salaries,
            'travel': self.travel,
            'hospitality': self.hospitality,
            'contracts': self.contracts,
            'total': self.total,
            'fiscal_year': self.fiscal_year,
            'quarter': self.quarter,
        }


class HouseOfficersClient:
    """Client for fetching House Officers and Presiding Officers expenditure data."""

    def __init__(self, *, session: Optional[RateLimitedSession] = None) -> None:
        self.session = session or RateLimitedSession()
        self.base_url = BASE_URL

    def _parse_amount(self, value: str) -> float:
        """Parse monetary amount from string, handling empty values."""
        if not value or value.strip() == '':
            return 0.0
        try:
            # Remove commas and dollar signs
            return float(value.replace(',', '').replace('$', ''))
        except ValueError:
            return 0.0

    def get_quarterly_summary(
        self,
        fiscal_year: int = 2026,
        quarter: int = 1,
        summary_id: Optional[str] = None
    ) -> List[HouseOfficerExpenditure]:
        """
        Fetch quarterly expenditure summary for all House Officers.

        Args:
            fiscal_year: Fiscal year (e.g., 2026 for 2025-2026)
            quarter: Quarter number (1-4)
            summary_id: Optional summary UUID for direct access

        Returns:
            List of HouseOfficerExpenditure objects
        """
        # If summary_id not provided, fetch the main page to get the CSV UUID
        if not summary_id:
            # Fetch the quarter page to extract the CSV download UUID
            quarter_page_url = f"{self.base_url}/{fiscal_year}/{quarter}"
            page_response = self.session.get(quarter_page_url)
            page_response.raise_for_status()

            # Extract CSV UUID from the page HTML
            # Look for pattern: /proactivedisclosure/en/house-officers/<UUID>/summary-expenditures/csv
            import re
            match = re.search(r'/proactivedisclosure/en/house-officers/([a-f0-9\-]{36})/summary-expenditures/csv', page_response.text)
            if match:
                csv_uuid = match.group(1)
                # Use UUID-based URL directly
                url = f"https://www.ourcommons.ca/proactivedisclosure/en/house-officers/{csv_uuid}/summary-expenditures/csv"
            else:
                raise ValueError(f"Could not find CSV download link for FY {fiscal_year} Q{quarter}")
        else:
            # Use provided summary_id as the UUID
            url = f"https://www.ourcommons.ca/proactivedisclosure/en/house-officers/{summary_id}/summary-expenditures/csv"

        # Fetch CSV data
        response = self.session.get(url)
        response.raise_for_status()

        # Parse CSV
        # Note: CSV may have UTF-8 BOM, decode with utf-8-sig
        csv_text = response.content.decode('utf-8-sig')
        return self._parse_csv(csv_text, fiscal_year, quarter)

    def _parse_csv(self, csv_text: str, fiscal_year: int, quarter: int) -> List[HouseOfficerExpenditure]:
        """Parse CSV text into list of HouseOfficerExpenditure objects."""
        expenditures = []
        reader = csv.DictReader(io.StringIO(csv_text))

        for row in reader:
            exp = HouseOfficerExpenditure(
                name=row.get('Name', '').strip(),
                role=row.get('Role', '').strip(),
                caucus=row.get('Caucus', '').strip(),
                salaries=self._parse_amount(row.get('Salaries', '0')),
                travel=self._parse_amount(row.get('Travel', '0')),
                hospitality=self._parse_amount(row.get('Hospitality', '0')),
                contracts=self._parse_amount(row.get('Contracts', '0')),
                fiscal_year=fiscal_year,
                quarter=quarter,
            )
            expenditures.append(exp)

        return expenditures

    def search_by_name(
        self,
        name: str,
        fiscal_year: int = 2026,
        quarter: int = 1
    ) -> List[HouseOfficerExpenditure]:
        """
        Search for House Officers by name.

        Args:
            name: Full or partial name to search for (case-insensitive)
            fiscal_year: Fiscal year
            quarter: Quarter number

        Returns:
            List of matching HouseOfficerExpenditure objects
        """
        all_expenses = self.get_quarterly_summary(fiscal_year, quarter)
        name_lower = name.lower()

        return [
            exp for exp in all_expenses
            if name_lower in exp.name.lower()
        ]

    def search_by_role(
        self,
        role: str,
        fiscal_year: int = 2026,
        quarter: int = 1
    ) -> List[HouseOfficerExpenditure]:
        """
        Get all House Officers with a specific role.

        Args:
            role: Role to search for (e.g., "Leader, Official Opposition", "Speaker")
            fiscal_year: Fiscal year
            quarter: Quarter number

        Returns:
            List of HouseOfficerExpenditure objects for that role
        """
        all_expenses = self.get_quarterly_summary(fiscal_year, quarter)
        role_lower = role.lower()

        return [
            exp for exp in all_expenses
            if role_lower in exp.role.lower()
        ]

    def get_leader_expenses(
        self,
        leader_name: str,
        fiscal_year: int = 2026,
        quarter: int = 1
    ) -> Dict[str, Any]:
        """
        Get all expense reports for a party leader across their different roles.

        Args:
            leader_name: Leader's name
            fiscal_year: Fiscal year
            quarter: Quarter number

        Returns:
            Dict with expenses by role (Leader, Stornoway, Research Office, etc.)
        """
        all_matches = self.search_by_name(leader_name, fiscal_year, quarter)
        
        result = {
            'leader_name': leader_name,
            'fiscal_year': fiscal_year,
            'quarter': quarter,
            'roles': {},
            'total_all_roles': 0.0
        }

        for exp in all_matches:
            result['roles'][exp.role] = exp.to_dict()
            result['total_all_roles'] += exp.total

        return result
