"""Client for accessing Canadian federal contracts database (open.canada.ca)."""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from fedmcp.http import RateLimitedSession


BASE_URL = "https://open.canada.ca/data/en/dataset/d8f85d91-7dec-4fd1-8055-483b77225d8b"
# Direct CSV download URL (updated periodically by open.canada.ca)
CSV_URL = "https://open.canada.ca/data/dataset/d8f85d91-7dec-4fd1-8055-483b77225d8b/resource/fac950c0-00d5-4ec1-a4d3-9cbebf98a305/download/contracts.csv"

# Cache directory for downloaded contract data
CACHE_DIR = Path.home() / ".cache" / "fedmcp" / "contracts"


@dataclass
class FederalContract:
    """Represents a federal government contract."""

    reference_number: str
    procurement_id: str
    vendor_name: str
    vendor_postal_code: Optional[str]
    buyer_name: str
    contract_date: Optional[str]
    delivery_date: Optional[str]
    contract_value: float
    original_value: Optional[float]
    amendment_value: Optional[float]
    comments: Optional[str]
    owner_org: str
    owner_org_title: str
    
    @property
    def contract_year(self) -> Optional[int]:
        """Extract year from contract date."""
        if not self.contract_date:
            return None
        try:
            return datetime.strptime(self.contract_date, "%Y-%m-%d").year
        except (ValueError, TypeError):
            return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'reference_number': self.reference_number,
            'procurement_id': self.procurement_id,
            'vendor_name': self.vendor_name,
            'vendor_postal_code': self.vendor_postal_code,
            'buyer_name': self.buyer_name,
            'contract_date': self.contract_date,
            'delivery_date': self.delivery_date,
            'contract_value': self.contract_value,
            'original_value': self.original_value,
            'amendment_value': self.amendment_value,
            'comments': self.comments,
            'owner_org': self.owner_org,
            'owner_org_title': self.owner_org_title,
            'contract_year': self.contract_year,
        }


class FederalContractsClient:
    """Client for accessing Canadian federal contracts database."""

    def __init__(
        self,
        *,
        session: Optional[RateLimitedSession] = None,
        cache_dir: Optional[Path] = None,
        auto_update: bool = False
    ) -> None:
        """
        Initialize the federal contracts client.

        Args:
            session: Optional HTTP session
            cache_dir: Directory for caching contract data
            auto_update: If True, check for updates and redownload if older than 30 days
        """
        self.session = session or RateLimitedSession()
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.auto_update = auto_update
        self.csv_url = CSV_URL

        # Cached data
        self._contracts: Optional[List[FederalContract]] = None

    def _should_download(self, file_path: Path) -> bool:
        """Check if file should be downloaded."""
        if not file_path.exists():
            return True
        if not self.auto_update:
            return False
        # Redownload if older than 30 days
        age_days = (datetime.now().timestamp() - file_path.stat().st_mtime) / 86400
        return age_days > 30

    def _download_contracts(self) -> Path:
        """Download contracts CSV to cache."""
        csv_path = self.cache_dir / "contracts.csv"

        if self._should_download(csv_path):
            print(f"Downloading federal contracts database (~200MB)...")
            response = self.session.get(self.csv_url, timeout=300)  # 5 min timeout for large file
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

    def _load_contracts(self) -> List[FederalContract]:
        """Load contract data from cache or download if needed."""
        if self._contracts is not None:
            return self._contracts

        csv_path = self._download_contracts()

        contracts = []
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                contract = FederalContract(
                    reference_number=row.get('reference_number', ''),
                    procurement_id=row.get('procurement_id', ''),
                    vendor_name=row.get('vendor_name', ''),
                    vendor_postal_code=row.get('vendor_postal_code'),
                    buyer_name=row.get('buyer_name', ''),
                    contract_date=row.get('contract_date'),
                    delivery_date=row.get('delivery_date'),
                    contract_value=self._parse_amount(row.get('contract_value', '0')),
                    original_value=self._parse_amount(row.get('original_value', '')) if row.get('original_value') else None,
                    amendment_value=self._parse_amount(row.get('amendment_value', '')) if row.get('amendment_value') else None,
                    comments=row.get('comments'),
                    owner_org=row.get('owner_org', ''),
                    owner_org_title=row.get('owner_org_title', ''),
                )
                contracts.append(contract)

        self._contracts = contracts
        print(f"Loaded {len(contracts):,} federal contracts")
        return self._contracts

    def search_contracts(
        self,
        vendor_name: Optional[str] = None,
        buyer_name: Optional[str] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        year: Optional[int] = None,
        department: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[FederalContract]:
        """
        Search federal contracts.

        Args:
            vendor_name: Vendor/contractor name to search for
            buyer_name: Buyer organization name
            min_value: Minimum contract value
            max_value: Maximum contract value
            year: Contract year (extracted from contract_date)
            department: Department/owner organization name
            limit: Maximum number of results

        Returns:
            List of matching contracts
        """
        contracts = self._load_contracts()
        results = contracts

        if vendor_name:
            vendor_lower = vendor_name.lower()
            results = [c for c in results if vendor_lower in c.vendor_name.lower()]

        if buyer_name:
            buyer_lower = buyer_name.lower()
            results = [c for c in results if buyer_lower in c.buyer_name.lower()]

        if min_value is not None:
            results = [c for c in results if c.contract_value >= min_value]

        if max_value is not None:
            results = [c for c in results if c.contract_value <= max_value]

        if year is not None:
            results = [c for c in results if c.contract_year == year]

        if department:
            dept_lower = department.lower()
            results = [
                c for c in results
                if dept_lower in c.owner_org_title.lower() or dept_lower in c.owner_org.lower()
            ]

        # Sort by value (descending)
        results = sorted(results, key=lambda x: x.contract_value, reverse=True)

        if limit:
            results = results[:limit]

        return results

    def get_top_vendors(
        self,
        limit: int = 20,
        year: Optional[int] = None,
        department: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top vendors by total contract value.

        Args:
            limit: Number of top vendors to return
            year: Filter by contract year
            department: Filter by department

        Returns:
            List of dicts with vendor_name and total_value
        """
        contracts = self._load_contracts()
        
        # Apply filters
        if year is not None:
            contracts = [c for c in contracts if c.contract_year == year]
        
        if department:
            dept_lower = department.lower()
            contracts = [
                c for c in contracts
                if dept_lower in c.owner_org_title.lower() or dept_lower in c.owner_org.lower()
            ]

        # Sum by vendor
        vendor_totals: Dict[str, float] = {}
        for contract in contracts:
            vendor_totals[contract.vendor_name] = vendor_totals.get(contract.vendor_name, 0) + contract.contract_value

        # Sort and return top N
        sorted_vendors = sorted(vendor_totals.items(), key=lambda x: x[1], reverse=True)
        return [
            {"vendor_name": name, "total_value": value}
            for name, value in sorted_vendors[:limit]
        ]

    def get_department_spending(
        self,
        year: Optional[int] = None,
        limit: Optional[int] = 20
    ) -> List[Dict[str, Any]]:
        """
        Get total contract spending by department.

        Args:
            year: Filter by contract year
            limit: Number of departments to return

        Returns:
            List of dicts with department and total_value
        """
        contracts = self._load_contracts()
        
        if year is not None:
            contracts = [c for c in contracts if c.contract_year == year]

        # Sum by department
        dept_totals: Dict[str, float] = {}
        for contract in contracts:
            dept = contract.owner_org_title or contract.owner_org
            dept_totals[dept] = dept_totals.get(dept, 0) + contract.contract_value

        # Sort and return top N
        sorted_depts = sorted(dept_totals.items(), key=lambda x: x[1], reverse=True)
        if limit:
            sorted_depts = sorted_depts[:limit]
        
        return [
            {"department": name, "total_value": value}
            for name, value in sorted_depts
        ]
