"""Client for fetching MP expenditure data from House of Commons Proactive Disclosure."""
from __future__ import annotations

import csv
import io
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from fedmcp.http import RateLimitedSession


BASE_URL = "https://www.ourcommons.ca/proactivedisclosure/en/members"


@dataclass
class MPExpenditure:
    """Represents an MP's quarterly expenditure summary."""

    name: str
    constituency: str
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
            'constituency': self.constituency,
            'caucus': self.caucus,
            'salaries': self.salaries,
            'travel': self.travel,
            'hospitality': self.hospitality,
            'contracts': self.contracts,
            'total': self.total,
            'fiscal_year': self.fiscal_year,
            'quarter': self.quarter,
        }


class MPExpenditureClient:
    """Client for fetching MP expenditure data from House of Commons."""

    def __init__(self, *, session: Optional[RateLimitedSession] = None) -> None:
        self.session = session or RateLimitedSession()
        self.base_url = BASE_URL

    def _parse_amount(self, value: str) -> float:
        """Parse monetary amount from string, handling empty values."""
        if not value or value.strip() == '':
            return 0.0
        try:
            # Remove commas and convert to float
            return float(value.replace(',', ''))
        except ValueError:
            return 0.0

    def get_quarterly_summary(
        self,
        fiscal_year: int = 2026,
        quarter: int = 1,
        summary_id: Optional[str] = None
    ) -> List[MPExpenditure]:
        """
        Fetch quarterly expenditure summary for all MPs.

        Args:
            fiscal_year: Fiscal year (e.g., 2026 for 2025-2026)
            quarter: Quarter number (1-4)
            summary_id: Optional summary UUID for direct access

        Returns:
            List of MPExpenditure objects
        """
        # If summary_id not provided, fetch the main page to get the CSV UUID
        if not summary_id:
            # Fetch the quarter page to extract the CSV download UUID
            quarter_page_url = f"{self.base_url}/{fiscal_year}/{quarter}"
            page_response = self.session.get(quarter_page_url)
            page_response.raise_for_status()

            # Extract CSV UUID from the page HTML
            # Look for pattern: /proactivedisclosure/en/members/<UUID>/csv
            import re
            match = re.search(r'/proactivedisclosure/en/members/([a-f0-9\-]{36})/csv', page_response.text)
            if match:
                csv_uuid = match.group(1)
                # Use UUID-based URL directly
                url = f"https://www.ourcommons.ca/proactivedisclosure/en/members/{csv_uuid}/csv"
            else:
                raise ValueError(f"Could not find CSV download link for FY {fiscal_year} Q{quarter}")
        else:
            # Use provided summary_id as the UUID
            url = f"https://www.ourcommons.ca/proactivedisclosure/en/members/{summary_id}/csv"

        # Fetch CSV data
        response = self.session.get(url)
        response.raise_for_status()

        # Parse CSV
        # Note: CSV may have UTF-8 BOM, decode with utf-8-sig
        csv_text = response.content.decode('utf-8-sig')
        return self._parse_csv(csv_text, fiscal_year, quarter)

    def _parse_csv(self, csv_text: str, fiscal_year: int, quarter: int) -> List[MPExpenditure]:
        """Parse CSV text into list of MPExpenditure objects."""
        expenditures = []
        reader = csv.DictReader(io.StringIO(csv_text))

        for row in reader:
            exp = MPExpenditure(
                name=row.get('Name', '').strip(),
                constituency=row.get('Constituency', '').strip(),
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
    ) -> List[MPExpenditure]:
        """
        Search for MPs by name.

        Args:
            name: Full or partial MP name to search for (case-insensitive)
            fiscal_year: Fiscal year
            quarter: Quarter number

        Returns:
            List of matching MPExpenditure objects
        """
        all_expenses = self.get_quarterly_summary(fiscal_year, quarter)
        name_lower = name.lower()

        return [
            exp for exp in all_expenses
            if name_lower in exp.name.lower()
        ]

    def search_by_party(
        self,
        party: str,
        fiscal_year: int = 2026,
        quarter: int = 1
    ) -> List[MPExpenditure]:
        """
        Get all MPs from a specific party/caucus.

        Args:
            party: Party/caucus name (Liberal, Conservative, NDP, etc.)
            fiscal_year: Fiscal year
            quarter: Quarter number

        Returns:
            List of MPExpenditure objects for that party
        """
        all_expenses = self.get_quarterly_summary(fiscal_year, quarter)
        party_lower = party.lower()

        return [
            exp for exp in all_expenses
            if party_lower in exp.caucus.lower()
        ]

    def search_by_constituency(
        self,
        constituency: str,
        fiscal_year: int = 2026,
        quarter: int = 1
    ) -> List[MPExpenditure]:
        """
        Search for MPs by constituency.

        Args:
            constituency: Full or partial constituency name
            fiscal_year: Fiscal year
            quarter: Quarter number

        Returns:
            List of matching MPExpenditure objects
        """
        all_expenses = self.get_quarterly_summary(fiscal_year, quarter)
        constituency_lower = constituency.lower()

        return [
            exp for exp in all_expenses
            if constituency_lower in exp.constituency.lower()
        ]

    def get_top_spenders(
        self,
        category: str,
        fiscal_year: int = 2026,
        quarter: int = 1,
        limit: int = 10
    ) -> List[MPExpenditure]:
        """
        Get top spenders in a specific category.

        Args:
            category: One of 'salaries', 'travel', 'hospitality', 'contracts', 'total'
            fiscal_year: Fiscal year
            quarter: Quarter number
            limit: Number of results to return

        Returns:
            List of top spending MPs in that category
        """
        all_expenses = self.get_quarterly_summary(fiscal_year, quarter)

        # Determine which field to sort by
        if category.lower() == 'salaries':
            key_func = lambda x: x.salaries
        elif category.lower() == 'travel':
            key_func = lambda x: x.travel
        elif category.lower() == 'hospitality':
            key_func = lambda x: x.hospitality
        elif category.lower() == 'contracts':
            key_func = lambda x: x.contracts
        elif category.lower() == 'total':
            key_func = lambda x: x.total
        else:
            raise ValueError(f"Invalid category: {category}. Must be one of: salaries, travel, hospitality, contracts, total")

        # Sort by category (descending) and take top N
        sorted_expenses = sorted(all_expenses, key=key_func, reverse=True)
        return sorted_expenses[:limit]

    def get_party_averages(
        self,
        fiscal_year: int = 2026,
        quarter: int = 1
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate average expenses by party/caucus.

        Returns:
            Dict mapping party name to average expenses by category
        """
        all_expenses = self.get_quarterly_summary(fiscal_year, quarter)

        # Group by party
        party_expenses: Dict[str, List[MPExpenditure]] = {}
        for exp in all_expenses:
            if exp.caucus not in party_expenses:
                party_expenses[exp.caucus] = []
            party_expenses[exp.caucus].append(exp)

        # Calculate averages
        averages = {}
        for party, expenses in party_expenses.items():
            count = len(expenses)
            averages[party] = {
                'count': count,
                'avg_salaries': sum(e.salaries for e in expenses) / count,
                'avg_travel': sum(e.travel for e in expenses) / count,
                'avg_hospitality': sum(e.hospitality for e in expenses) / count,
                'avg_contracts': sum(e.contracts for e in expenses) / count,
                'avg_total': sum(e.total for e in expenses) / count,
            }

        return averages
