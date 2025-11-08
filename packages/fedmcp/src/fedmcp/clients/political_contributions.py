"""Client for accessing Elections Canada political contributions data (open.canada.ca)."""
from __future__ import annotations

import csv
import io
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fedmcp.http import RateLimitedSession


# Direct ZIP download URLs from Elections Canada
CONTRIBUTIONS_URL_EN = "https://www.elections.ca/fin/oda/od_cntrbtn_audt_e.zip"
CONTRIBUTIONS_URL_FR = "https://www.elections.ca/fin/oda/od_cntrbtn_audt_f.zip"

# Cache directory
CACHE_DIR = Path.home() / ".cache" / "fedmcp" / "political_contributions"


@dataclass
class PoliticalContribution:
    """Represents a political contribution to federal parties/candidates."""

    contributor_name: str
    contributor_city: Optional[str]
    contributor_province: Optional[str]
    contributor_postal_code: Optional[str]
    contribution_date: str
    contribution_amount: float
    recipient_type: str  # Party, Candidate, Electoral District Association
    recipient_name: str
    political_party: str
    electoral_district: Optional[str]
    fiscal_year: int
    
    @property
    def contribution_year(self) -> Optional[int]:
        """Extract year from contribution date."""
        try:
            return datetime.strptime(self.contribution_date, "%Y-%m-%d").year
        except (ValueError, TypeError):
            return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'contributor_name': self.contributor_name,
            'contributor_city': self.contributor_city,
            'contributor_province': self.contributor_province,
            'contributor_postal_code': self.contributor_postal_code,
            'contribution_date': self.contribution_date,
            'contribution_year': self.contribution_year,
            'contribution_amount': self.contribution_amount,
            'recipient_type': self.recipient_type,
            'recipient_name': self.recipient_name,
            'political_party': self.political_party,
            'electoral_district': self.electoral_district,
            'fiscal_year': self.fiscal_year,
        }


class PoliticalContributionsClient:
    """Client for accessing Elections Canada political contributions data."""

    def __init__(
        self,
        *,
        session: Optional[RateLimitedSession] = None,
        cache_dir: Optional[Path] = None,
        auto_update: bool = False,
        language: str = 'en'
    ) -> None:
        """
        Initialize the political contributions client.

        Args:
            session: Optional HTTP session
            cache_dir: Directory for caching contribution data
            auto_update: If True, check for updates and redownload if older than 7 days
            language: 'en' or 'fr' for English or French data
        """
        self.session = session or RateLimitedSession()
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.auto_update = auto_update
        self.language = language
        self.zip_url = CONTRIBUTIONS_URL_EN if language == 'en' else CONTRIBUTIONS_URL_FR

        # Cached data
        self._contributions: Optional[List[PoliticalContribution]] = None

    def _should_download(self, file_path: Path) -> bool:
        """Check if file should be downloaded."""
        if not file_path.exists():
            return True
        if not self.auto_update:
            return False
        # Redownload if older than 7 days (weekly updates)
        age_days = (datetime.now().timestamp() - file_path.stat().st_mtime) / 86400
        return age_days > 7

    def _download_and_extract(self) -> Path:
        """Download and extract contributions ZIP to cache."""
        zip_path = self.cache_dir / f"contributions_{self.language}.zip"
        extract_dir = self.cache_dir / f"contributions_{self.language}"

        if self._should_download(zip_path):
            print(f"Downloading political contributions database (~100MB)...")
            response = self.session.get(self.zip_url, timeout=300)
            response.raise_for_status()
            zip_path.write_bytes(response.content)
            print(f"Downloaded {len(response.content) / 1024 / 1024:.1f} MB")

            # Extract
            extract_dir.mkdir(exist_ok=True)
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(extract_dir)
                print(f"Extracted to {extract_dir}")

        return extract_dir

    def _parse_amount(self, value: str) -> float:
        """Parse monetary amount from string."""
        if not value or value.strip() == '':
            return 0.0
        try:
            return float(value.replace(',', '').replace('$', ''))
        except ValueError:
            return 0.0

    def _load_contributions(self) -> List[PoliticalContribution]:
        """Load contribution data from cache or download if needed."""
        if self._contributions is not None:
            return self._contributions

        extract_dir = self._download_and_extract()

        # Find the main CSV file (name varies)
        csv_files = list(extract_dir.glob("*.csv"))
        if not csv_files:
            raise ValueError(f"No CSV files found in {extract_dir}")
        
        csv_file = csv_files[0]  # Use first CSV file found
        print(f"Loading contributions from {csv_file.name}...")

        contributions = []
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Field names vary - try multiple possible column names
                contrib = PoliticalContribution(
                    contributor_name=row.get('Contributor name', row.get('contributor_name', '')),
                    contributor_city=row.get('Contributor city', row.get('contributor_city')),
                    contributor_province=row.get('Contributor prov.', row.get('contributor_province')),
                    contributor_postal_code=row.get('Contributor postal code', row.get('contributor_postal_code')),
                    contribution_date=row.get('Contribution date', row.get('contribution_date', '')),
                    contribution_amount=self._parse_amount(
                        row.get('Contribution amount', row.get('contribution_amount', '0'))
                    ),
                    recipient_type=row.get('Recipient type', row.get('recipient_type', '')),
                    recipient_name=row.get('Recipient name', row.get('recipient_name', '')),
                    political_party=row.get('Political party', row.get('political_party', '')),
                    electoral_district=row.get('Electoral district', row.get('electoral_district')),
                    fiscal_year=int(row.get('Fiscal year', row.get('fiscal_year', 0))),
                )
                contributions.append(contrib)

        self._contributions = contributions
        print(f"Loaded {len(contributions):,} political contributions")
        return self._contributions

    def search_contributions(
        self,
        contributor_name: Optional[str] = None,
        recipient_name: Optional[str] = None,
        political_party: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        year: Optional[int] = None,
        province: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[PoliticalContribution]:
        """
        Search political contributions.

        Args:
            contributor_name: Donor name to search for
            recipient_name: Candidate/party name
            political_party: Party name (Liberal, Conservative, NDP, etc.)
            min_amount: Minimum contribution amount
            max_amount: Maximum contribution amount
            year: Contribution year
            province: Contributor province
            limit: Maximum number of results

        Returns:
            List of matching contributions
        """
        contributions = self._load_contributions()
        results = contributions

        if contributor_name:
            name_lower = contributor_name.lower()
            results = [c for c in results if name_lower in c.contributor_name.lower()]

        if recipient_name:
            recipient_lower = recipient_name.lower()
            results = [c for c in results if recipient_lower in c.recipient_name.lower()]

        if political_party:
            party_lower = political_party.lower()
            results = [c for c in results if party_lower in c.political_party.lower()]

        if min_amount is not None:
            results = [c for c in results if c.contribution_amount >= min_amount]

        if max_amount is not None:
            results = [c for c in results if c.contribution_amount <= max_amount]

        if year is not None:
            results = [c for c in results if c.contribution_year == year]

        if province:
            prov_lower = province.lower()
            results = [
                c for c in results
                if c.contributor_province and prov_lower in c.contributor_province.lower()
            ]

        # Sort by amount (descending) then date
        results = sorted(results, key=lambda x: (x.contribution_amount, x.contribution_date), reverse=True)

        if limit:
            results = results[:limit]

        return results

    def get_top_donors(
        self,
        limit: int = 20,
        year: Optional[int] = None,
        political_party: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top donors by total contribution amount.

        Args:
            limit: Number of top donors to return
            year: Filter by contribution year
            political_party: Filter by recipient party

        Returns:
            List of dicts with donor_name and total_amount
        """
        contributions = self._load_contributions()
        
        # Apply filters
        if year is not None:
            contributions = [c for c in contributions if c.contribution_year == year]
        
        if political_party:
            party_lower = political_party.lower()
            contributions = [
                c for c in contributions
                if party_lower in c.political_party.lower()
            ]

        # Sum by donor
        donor_totals: Dict[str, float] = {}
        for contrib in contributions:
            donor_totals[contrib.contributor_name] = (
                donor_totals.get(contrib.contributor_name, 0) + contrib.contribution_amount
            )

        # Sort and return top N
        sorted_donors = sorted(donor_totals.items(), key=lambda x: x[1], reverse=True)
        return [
            {"donor_name": name, "total_amount": amount}
            for name, amount in sorted_donors[:limit]
        ]

    def get_party_fundraising(
        self,
        year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get total fundraising by political party.

        Args:
            year: Filter by contribution year

        Returns:
            List of dicts with party_name, total_amount, and contributor_count
        """
        contributions = self._load_contributions()
        
        if year is not None:
            contributions = [c for c in contributions if c.contribution_year == year]

        # Aggregate by party
        party_data: Dict[str, Dict[str, Any]] = {}
        for contrib in contributions:
            party = contrib.political_party
            if party not in party_data:
                party_data[party] = {'total_amount': 0.0, 'contributors': set()}
            
            party_data[party]['total_amount'] += contrib.contribution_amount
            party_data[party]['contributors'].add(contrib.contributor_name)

        # Format results
        results = [
            {
                'party_name': party,
                'total_amount': data['total_amount'],
                'contributor_count': len(data['contributors'])
            }
            for party, data in party_data.items()
        ]

        # Sort by total amount
        results = sorted(results, key=lambda x: x['total_amount'], reverse=True)
        return results
