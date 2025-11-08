"""Client for accessing Canadian federal departmental travel and hospitality expenses (open.canada.ca)."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fedmcp.http import RateLimitedSession


# Travel expenses dataset
TRAVEL_URL = "https://open.canada.ca/data/dataset/009f9a49-c2d9-4d29-a6d4-1a228da335ce/resource/23144a1f-3e5d-4a78-916d-b59c7ab5595f/download/travelq.csv"

# Hospitality expenses dataset
HOSPITALITY_URL = "https://open.canada.ca/data/dataset/b9f51ef4-4605-4ef2-8231-62a2edda1b54/resource/a05ebc37-76f4-4d02-9b7d-3c15f4adb4ce/download/hospitalityq.csv"

# Cache directory
CACHE_DIR = Path.home() / ".cache" / "fedmcp" / "departmental_expenses"


@dataclass
class DepartmentalTravel:
    """Represents departmental travel expenses for public servants."""

    owner_org: str
    owner_org_title: str
    ref_number: str
    disclosure_group: str
    title_en: Optional[str]
    title_fr: Optional[str]
    name: str
    purpose_en: Optional[str]
    purpose_fr: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    destination_en: Optional[str]
    destination_fr: Optional[str]
    airfare: float
    other_transport: float
    lodging: float
    meals: float
    other_expenses: float
    total: float

    @property
    def travel_year(self) -> Optional[int]:
        """Extract year from start date."""
        if not self.start_date:
            return None
        try:
            return datetime.strptime(self.start_date, "%Y-%m-%d").year
        except (ValueError, TypeError):
            return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'owner_org': self.owner_org,
            'owner_org_title': self.owner_org_title,
            'ref_number': self.ref_number,
            'disclosure_group': self.disclosure_group,
            'title_en': self.title_en,
            'title_fr': self.title_fr,
            'name': self.name,
            'purpose_en': self.purpose_en,
            'purpose_fr': self.purpose_fr,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'travel_year': self.travel_year,
            'destination_en': self.destination_en,
            'destination_fr': self.destination_fr,
            'airfare': self.airfare,
            'other_transport': self.other_transport,
            'lodging': self.lodging,
            'meals': self.meals,
            'other_expenses': self.other_expenses,
            'total': self.total,
        }


@dataclass
class DepartmentalHospitality:
    """Represents departmental hospitality expenses."""

    owner_org: str
    owner_org_title: str
    ref_number: str
    disclosure_group: str
    title_en: Optional[str]
    title_fr: Optional[str]
    name: str
    purpose_en: Optional[str]
    purpose_fr: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    attendees: Optional[int]
    location_en: Optional[str]
    location_fr: Optional[str]
    total: float

    @property
    def hospitality_year(self) -> Optional[int]:
        """Extract year from start date."""
        if not self.start_date:
            return None
        try:
            return datetime.strptime(self.start_date, "%Y-%m-%d").year
        except (ValueError, TypeError):
            return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'owner_org': self.owner_org,
            'owner_org_title': self.owner_org_title,
            'ref_number': self.ref_number,
            'disclosure_group': self.disclosure_group,
            'title_en': self.title_en,
            'title_fr': self.title_fr,
            'name': self.name,
            'purpose_en': self.purpose_en,
            'purpose_fr': self.purpose_fr,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'hospitality_year': self.hospitality_year,
            'attendees': self.attendees,
            'location_en': self.location_en,
            'location_fr': self.location_fr,
            'total': self.total,
        }


class DepartmentalExpensesClient:
    """Client for accessing departmental travel and hospitality expenses."""

    def __init__(
        self,
        *,
        session: Optional[RateLimitedSession] = None,
        cache_dir: Optional[Path] = None,
        auto_update: bool = False
    ) -> None:
        """
        Initialize the departmental expenses client.

        Args:
            session: Optional HTTP session
            cache_dir: Directory for caching expense data
            auto_update: If True, check for updates and redownload if older than 30 days
        """
        self.session = session or RateLimitedSession()
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.auto_update = auto_update

        # Cached data
        self._travel: Optional[List[DepartmentalTravel]] = None
        self._hospitality: Optional[List[DepartmentalHospitality]] = None

    def _should_download(self, file_path: Path) -> bool:
        """Check if file should be downloaded."""
        if not file_path.exists():
            return True
        if not self.auto_update:
            return False
        # Redownload if older than 30 days (quarterly updates)
        age_days = (datetime.now().timestamp() - file_path.stat().st_mtime) / 86400
        return age_days > 30

    def _download_file(self, url: str, filename: str) -> Path:
        """Download CSV to cache."""
        csv_path = self.cache_dir / filename

        if self._should_download(csv_path):
            print(f"Downloading {filename} (~20MB)...")
            response = self.session.get(url, timeout=300)
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

    def _parse_int(self, value: str) -> Optional[int]:
        """Parse integer from string."""
        if not value or value.strip() == '':
            return None
        try:
            return int(value.replace(',', ''))
        except ValueError:
            return None

    def _load_travel(self) -> List[DepartmentalTravel]:
        """Load travel data from cache or download if needed."""
        if self._travel is not None:
            return self._travel

        csv_path = self._download_file(TRAVEL_URL, "travel.csv")

        travel_records = []
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                record = DepartmentalTravel(
                    owner_org=row.get('owner_org', ''),
                    owner_org_title=row.get('owner_org_title', ''),
                    ref_number=row.get('ref_number', ''),
                    disclosure_group=row.get('disclosure_group', ''),
                    title_en=row.get('title_en'),
                    title_fr=row.get('title_fr'),
                    name=row.get('name', ''),
                    purpose_en=row.get('purpose_en'),
                    purpose_fr=row.get('purpose_fr'),
                    start_date=row.get('start_date'),
                    end_date=row.get('end_date'),
                    destination_en=row.get('destination_en'),
                    destination_fr=row.get('destination_fr'),
                    airfare=self._parse_amount(row.get('airfare', '0')),
                    other_transport=self._parse_amount(row.get('other_transport', '0')),
                    lodging=self._parse_amount(row.get('lodging', '0')),
                    meals=self._parse_amount(row.get('meals', '0')),
                    other_expenses=self._parse_amount(row.get('other_expenses', '0')),
                    total=self._parse_amount(row.get('total', '0')),
                )
                travel_records.append(record)

        self._travel = travel_records
        print(f"Loaded {len(travel_records):,} departmental travel records")
        return self._travel

    def _load_hospitality(self) -> List[DepartmentalHospitality]:
        """Load hospitality data from cache or download if needed."""
        if self._hospitality is not None:
            return self._hospitality

        csv_path = self._download_file(HOSPITALITY_URL, "hospitality.csv")

        hospitality_records = []
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                record = DepartmentalHospitality(
                    owner_org=row.get('owner_org', ''),
                    owner_org_title=row.get('owner_org_title', ''),
                    ref_number=row.get('ref_number', ''),
                    disclosure_group=row.get('disclosure_group', ''),
                    title_en=row.get('title_en'),
                    title_fr=row.get('title_fr'),
                    name=row.get('name', ''),
                    purpose_en=row.get('purpose_en'),
                    purpose_fr=row.get('purpose_fr'),
                    start_date=row.get('start_date'),
                    end_date=row.get('end_date'),
                    attendees=self._parse_int(row.get('attendees')),
                    location_en=row.get('location_en'),
                    location_fr=row.get('location_fr'),
                    total=self._parse_amount(row.get('total', '0')),
                )
                hospitality_records.append(record)

        self._hospitality = hospitality_records
        print(f"Loaded {len(hospitality_records):,} departmental hospitality records")
        return self._hospitality

    def search_travel(
        self,
        department: Optional[str] = None,
        name: Optional[str] = None,
        destination: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        year: Optional[int] = None,
        disclosure_group: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[DepartmentalTravel]:
        """
        Search departmental travel expenses.

        Args:
            department: Department name to filter by
            name: Traveler name to search for
            destination: Destination to search for
            min_amount: Minimum expense amount
            max_amount: Maximum expense amount
            year: Travel year
            disclosure_group: Disclosure group (e.g., "Minister", "Deputy Minister")
            limit: Maximum number of results

        Returns:
            List of matching travel records
        """
        records = self._load_travel()
        results = records

        if department:
            dept_lower = department.lower()
            results = [
                r for r in results
                if dept_lower in r.owner_org_title.lower() or dept_lower in r.owner_org.lower()
            ]

        if name:
            name_lower = name.lower()
            results = [r for r in results if name_lower in r.name.lower()]

        if destination:
            dest_lower = destination.lower()
            results = [
                r for r in results
                if (r.destination_en and dest_lower in r.destination_en.lower()) or
                   (r.destination_fr and dest_lower in r.destination_fr.lower())
            ]

        if min_amount is not None:
            results = [r for r in results if r.total >= min_amount]

        if max_amount is not None:
            results = [r for r in results if r.total <= max_amount]

        if year is not None:
            results = [r for r in results if r.travel_year == year]

        if disclosure_group:
            group_lower = disclosure_group.lower()
            results = [r for r in results if group_lower in r.disclosure_group.lower()]

        # Sort by total (descending)
        results = sorted(results, key=lambda x: x.total, reverse=True)

        if limit:
            results = results[:limit]

        return results

    def search_hospitality(
        self,
        department: Optional[str] = None,
        name: Optional[str] = None,
        location: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        year: Optional[int] = None,
        disclosure_group: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[DepartmentalHospitality]:
        """
        Search departmental hospitality expenses.

        Args:
            department: Department name to filter by
            name: Host name to search for
            location: Location to search for
            min_amount: Minimum expense amount
            max_amount: Maximum expense amount
            year: Hospitality year
            disclosure_group: Disclosure group (e.g., "Minister", "Deputy Minister")
            limit: Maximum number of results

        Returns:
            List of matching hospitality records
        """
        records = self._load_hospitality()
        results = records

        if department:
            dept_lower = department.lower()
            results = [
                r for r in results
                if dept_lower in r.owner_org_title.lower() or dept_lower in r.owner_org.lower()
            ]

        if name:
            name_lower = name.lower()
            results = [r for r in results if name_lower in r.name.lower()]

        if location:
            loc_lower = location.lower()
            results = [
                r for r in results
                if (r.location_en and loc_lower in r.location_en.lower()) or
                   (r.location_fr and loc_lower in r.location_fr.lower())
            ]

        if min_amount is not None:
            results = [r for r in results if r.total >= min_amount]

        if max_amount is not None:
            results = [r for r in results if r.total <= max_amount]

        if year is not None:
            results = [r for r in results if r.hospitality_year == year]

        if disclosure_group:
            group_lower = disclosure_group.lower()
            results = [r for r in results if group_lower in r.disclosure_group.lower()]

        # Sort by total (descending)
        results = sorted(results, key=lambda x: x.total, reverse=True)

        if limit:
            results = results[:limit]

        return results

    def get_department_travel_spending(
        self,
        year: Optional[int] = None,
        limit: Optional[int] = 20
    ) -> List[Dict[str, Any]]:
        """
        Get total travel spending by department.

        Args:
            year: Filter by travel year
            limit: Number of departments to return

        Returns:
            List of dicts with department and total_spending
        """
        records = self._load_travel()

        if year is not None:
            records = [r for r in records if r.travel_year == year]

        # Sum by department
        dept_totals: Dict[str, float] = {}
        for record in records:
            dept = record.owner_org_title or record.owner_org
            dept_totals[dept] = dept_totals.get(dept, 0) + record.total

        # Sort and return top N
        sorted_depts = sorted(dept_totals.items(), key=lambda x: x[1], reverse=True)
        if limit:
            sorted_depts = sorted_depts[:limit]

        return [
            {"department": name, "total_spending": value}
            for name, value in sorted_depts
        ]

    def get_department_hospitality_spending(
        self,
        year: Optional[int] = None,
        limit: Optional[int] = 20
    ) -> List[Dict[str, Any]]:
        """
        Get total hospitality spending by department.

        Args:
            year: Filter by hospitality year
            limit: Number of departments to return

        Returns:
            List of dicts with department and total_spending
        """
        records = self._load_hospitality()

        if year is not None:
            records = [r for r in records if r.hospitality_year == year]

        # Sum by department
        dept_totals: Dict[str, float] = {}
        for record in records:
            dept = record.owner_org_title or record.owner_org
            dept_totals[dept] = dept_totals.get(dept, 0) + record.total

        # Sort and return top N
        sorted_depts = sorted(dept_totals.items(), key=lambda x: x[1], reverse=True)
        if limit:
            sorted_depts = sorted_depts[:limit]

        return [
            {"department": name, "total_spending": value}
            for name, value in sorted_depts
        ]

    def get_top_travelers(
        self,
        limit: int = 20,
        year: Optional[int] = None,
        department: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top travelers by total travel spending.

        Args:
            limit: Number of top travelers to return
            year: Filter by travel year
            department: Filter by department

        Returns:
            List of dicts with name, department, and total_spending
        """
        records = self._load_travel()

        if year is not None:
            records = [r for r in records if r.travel_year == year]

        if department:
            dept_lower = department.lower()
            records = [
                r for r in records
                if dept_lower in r.owner_org_title.lower() or dept_lower in r.owner_org.lower()
            ]

        # Sum by name and department
        traveler_data: Dict[tuple, Dict[str, Any]] = {}
        for record in records:
            key = (record.name, record.owner_org_title)
            if key not in traveler_data:
                traveler_data[key] = {'total_spending': 0.0}
            traveler_data[key]['total_spending'] += record.total

        # Format results
        results = [
            {
                'name': name,
                'department': dept,
                'total_spending': data['total_spending']
            }
            for (name, dept), data in traveler_data.items()
        ]

        # Sort by spending
        results = sorted(results, key=lambda x: x['total_spending'], reverse=True)

        if limit:
            results = results[:limit]

        return results
