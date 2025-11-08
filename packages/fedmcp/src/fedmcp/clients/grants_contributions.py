"""Client for accessing Canadian federal grants and contributions database (open.canada.ca)."""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fedmcp.http import RateLimitedSession


BASE_URL = "https://open.canada.ca/data/en/dataset/432527ab-7aac-45b5-81d6-7597107a7013"
# Direct CSV download URL (consolidated dataset from all departments)
CSV_URL = "https://open.canada.ca/data/dataset/432527ab-7aac-45b5-81d6-7597107a7013/resource/1d15a62f-5656-49ad-8c88-f40ce689d831/download/grants.csv"

# Cache directory
CACHE_DIR = Path.home() / ".cache" / "fedmcp" / "grants"


@dataclass
class GrantContribution:
    """Represents a federal grant or contribution over $25,000."""

    recipient_name: str
    recipient_city: Optional[str]
    recipient_province: Optional[str]
    recipient_postal_code: Optional[str]
    recipient_country: str
    agreement_date: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    agreement_value: float
    program_name: str
    program_purpose: str
    owner_org: str
    owner_org_title: str
    
    @property
    def agreement_year(self) -> Optional[int]:
        """Extract year from agreement date."""
        if not self.agreement_date:
            return None
        try:
            return datetime.strptime(self.agreement_date, "%Y-%m-%d").year
        except (ValueError, TypeError):
            return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'recipient_name': self.recipient_name,
            'recipient_city': self.recipient_city,
            'recipient_province': self.recipient_province,
            'recipient_postal_code': self.recipient_postal_code,
            'recipient_country': self.recipient_country,
            'agreement_date': self.agreement_date,
            'agreement_year': self.agreement_year,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'agreement_value': self.agreement_value,
            'program_name': self.program_name,
            'program_purpose': self.program_purpose,
            'owner_org': self.owner_org,
            'owner_org_title': self.owner_org_title,
        }


class GrantsContributionsClient:
    """Client for accessing Canadian federal grants and contributions database."""

    def __init__(
        self,
        *,
        session: Optional[RateLimitedSession] = None,
        cache_dir: Optional[Path] = None,
        auto_update: bool = False
    ) -> None:
        """
        Initialize the grants and contributions client.

        Args:
            session: Optional HTTP session
            cache_dir: Directory for caching grant data
            auto_update: If True, check for updates and redownload if older than 30 days
        """
        self.session = session or RateLimitedSession()
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.auto_update = auto_update
        self.csv_url = CSV_URL

        # Cached data
        self._grants: Optional[List[GrantContribution]] = None

    def _should_download(self, file_path: Path) -> bool:
        """Check if file should be downloaded."""
        if not file_path.exists():
            return True
        if not self.auto_update:
            return False
        # Redownload if older than 30 days (quarterly updates)
        age_days = (datetime.now().timestamp() - file_path.stat().st_mtime) / 86400
        return age_days > 30

    def _download_grants(self) -> Path:
        """Download grants CSV to cache."""
        csv_path = self.cache_dir / "grants.csv"

        if self._should_download(csv_path):
            print(f"Downloading federal grants database (~50MB)...")
            response = self.session.get(self.csv_url, timeout=300)
            response.raise_for_status()
            csv_path.write_bytes(response.content)
            print(f"Downloaded {len(response.content) / 1024 / 1024:.1f} MB")

        return csv_path

    def _parse_amount(self, value: str) -> float:
        """Parse monetary amount from string."""
        if not value or value.strip() == '':
            return 0.0
        try:
            return float(value.replace(',', '').replace('$', ''))
        except ValueError:
            return 0.0

    def _load_grants(self) -> List[GrantContribution]:
        """Load grant data from cache or download if needed."""
        if self._grants is not None:
            return self._grants

        csv_path = self._download_grants()

        grants = []
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                grant = GrantContribution(
                    recipient_name=row.get('recipient_legal_name', row.get('recipient_name', '')),
                    recipient_city=row.get('recipient_city', row.get('city')),
                    recipient_province=row.get('recipient_province', row.get('province')),
                    recipient_postal_code=row.get('recipient_postal_code', row.get('postal_code')),
                    recipient_country=row.get('recipient_country', row.get('country', '')),
                    agreement_date=row.get('agreement_date'),
                    start_date=row.get('expected_start_date', row.get('start_date')),
                    end_date=row.get('expected_end_date', row.get('end_date')),
                    agreement_value=self._parse_amount(row.get('agreement_value', row.get('value', '0'))),
                    program_name=row.get('program_name_en', row.get('program_name', '')),
                    program_purpose=row.get('program_purpose_en', row.get('program_purpose', '')),
                    owner_org=row.get('owner_org', ''),
                    owner_org_title=row.get('owner_org_title', ''),
                )
                grants.append(grant)

        self._grants = grants
        print(f"Loaded {len(grants):,} grants and contributions")
        return self._grants

    def search_grants(
        self,
        recipient_name: Optional[str] = None,
        program_name: Optional[str] = None,
        department: Optional[str] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        year: Optional[int] = None,
        province: Optional[str] = None,
        country: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[GrantContribution]:
        """
        Search grants and contributions.

        Args:
            recipient_name: Recipient organization/person name
            program_name: Program name to search for
            department: Department/owner organization name
            min_value: Minimum grant value
            max_value: Maximum grant value
            year: Agreement year
            province: Recipient province
            country: Recipient country
            limit: Maximum number of results

        Returns:
            List of matching grants
        """
        grants = self._load_grants()
        results = grants

        if recipient_name:
            name_lower = recipient_name.lower()
            results = [g for g in results if name_lower in g.recipient_name.lower()]

        if program_name:
            program_lower = program_name.lower()
            results = [
                g for g in results
                if program_lower in g.program_name.lower() or program_lower in g.program_purpose.lower()
            ]

        if department:
            dept_lower = department.lower()
            results = [
                g for g in results
                if dept_lower in g.owner_org_title.lower() or dept_lower in g.owner_org.lower()
            ]

        if min_value is not None:
            results = [g for g in results if g.agreement_value >= min_value]

        if max_value is not None:
            results = [g for g in results if g.agreement_value <= max_value]

        if year is not None:
            results = [g for g in results if g.agreement_year == year]

        if province:
            prov_lower = province.lower()
            results = [
                g for g in results
                if g.recipient_province and prov_lower in g.recipient_province.lower()
            ]

        if country:
            country_lower = country.lower()
            results = [g for g in results if country_lower in g.recipient_country.lower()]

        # Sort by value (descending)
        results = sorted(results, key=lambda x: x.agreement_value, reverse=True)

        if limit:
            results = results[:limit]

        return results

    def get_top_recipients(
        self,
        limit: int = 20,
        year: Optional[int] = None,
        department: Optional[str] = None,
        program_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top grant recipients by total funding.

        Args:
            limit: Number of top recipients to return
            year: Filter by agreement year
            department: Filter by department
            program_name: Filter by program

        Returns:
            List of dicts with recipient_name and total_value
        """
        grants = self._load_grants()
        
        # Apply filters
        if year is not None:
            grants = [g for g in grants if g.agreement_year == year]
        
        if department:
            dept_lower = department.lower()
            grants = [
                g for g in grants
                if dept_lower in g.owner_org_title.lower() or dept_lower in g.owner_org.lower()
            ]

        if program_name:
            program_lower = program_name.lower()
            grants = [
                g for g in grants
                if program_lower in g.program_name.lower() or program_lower in g.program_purpose.lower()
            ]

        # Sum by recipient
        recipient_totals: Dict[str, float] = {}
        for grant in grants:
            recipient_totals[grant.recipient_name] = (
                recipient_totals.get(grant.recipient_name, 0) + grant.agreement_value
            )

        # Sort and return top N
        sorted_recipients = sorted(recipient_totals.items(), key=lambda x: x[1], reverse=True)
        return [
            {"recipient_name": name, "total_value": value}
            for name, value in sorted_recipients[:limit]
        ]

    def get_program_spending(
        self,
        year: Optional[int] = None,
        department: Optional[str] = None,
        limit: Optional[int] = 20
    ) -> List[Dict[str, Any]]:
        """
        Get total spending by program.

        Args:
            year: Filter by agreement year
            department: Filter by department
            limit: Number of programs to return

        Returns:
            List of dicts with program_name, total_value, and recipient_count
        """
        grants = self._load_grants()
        
        if year is not None:
            grants = [g for g in grants if g.agreement_year == year]

        if department:
            dept_lower = department.lower()
            grants = [
                g for g in grants
                if dept_lower in g.owner_org_title.lower() or dept_lower in g.owner_org.lower()
            ]

        # Aggregate by program
        program_data: Dict[str, Dict[str, Any]] = {}
        for grant in grants:
            program = grant.program_name
            if program not in program_data:
                program_data[program] = {'total_value': 0.0, 'recipients': set()}
            
            program_data[program]['total_value'] += grant.agreement_value
            program_data[program]['recipients'].add(grant.recipient_name)

        # Format results
        results = [
            {
                'program_name': program,
                'total_value': data['total_value'],
                'recipient_count': len(data['recipients'])
            }
            for program, data in program_data.items()
        ]

        # Sort by total value
        results = sorted(results, key=lambda x: x['total_value'], reverse=True)
        
        if limit:
            results = results[:limit]
        
        return results

    def get_department_spending(
        self,
        year: Optional[int] = None,
        limit: Optional[int] = 20
    ) -> List[Dict[str, Any]]:
        """
        Get total grant spending by department.

        Args:
            year: Filter by agreement year
            limit: Number of departments to return

        Returns:
            List of dicts with department and total_value
        """
        grants = self._load_grants()
        
        if year is not None:
            grants = [g for g in grants if g.agreement_year == year]

        # Sum by department
        dept_totals: Dict[str, float] = {}
        for grant in grants:
            dept = grant.owner_org_title or grant.owner_org
            dept_totals[dept] = dept_totals.get(dept, 0) + grant.agreement_value

        # Sort and return top N
        sorted_depts = sorted(dept_totals.items(), key=lambda x: x[1], reverse=True)
        if limit:
            sorted_depts = sorted_depts[:limit]
        
        return [
            {"department": name, "total_value": value}
            for name, value in sorted_depts
        ]
