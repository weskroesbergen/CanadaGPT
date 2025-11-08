"""Client for fetching Canadian federal lobbying registry data."""
from __future__ import annotations

import csv
import io
import os
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fedmcp.http import RateLimitedSession


# Official lobbycanada.gc.ca sources (primary, most up-to-date)
OFFICIAL_REGISTRATIONS_URL = "https://lobbycanada.gc.ca/media/zwcjycef/registrations_enregistrements_ocl_cal.zip"
OFFICIAL_COMMUNICATIONS_URL = "https://lobbycanada.gc.ca/media/mqbbmaqk/communications_ocl_cal.zip"

# Open.canada.ca alternative sources (republished data, may have different update schedule)
OPENDATA_REGISTRATIONS_URL = "https://open.canada.ca/data/dataset/e1d38370-1687-44d1-86a3-8ae3bbbbb945/resource/0c00bb16-4edf-48b4-90ab-30f11e5f5caa/download/registrations.zip"
OPENDATA_COMMUNICATIONS_URL = "https://open.canada.ca/data/dataset/e1d38370-1687-44d1-86a3-8ae3bbbbb945/resource/9c8ab367-c8f4-4c8e-9b8f-7cfb7f1f3c8f/download/communications.zip"

# Cache directory for downloaded data
CACHE_DIR = Path.home() / ".cache" / "fedmcp" / "lobbying"


@dataclass
class LobbyingRegistration:
    """Represents a lobbying registration."""

    reg_id: str
    reg_type: str
    reg_number: str
    client_org_name: str
    registrant_last_name: str
    registrant_first_name: str
    effective_date: Optional[str] = None
    end_date: Optional[str] = None
    subject_matters: List[str] = field(default_factory=list)
    government_institutions: List[str] = field(default_factory=list)
    posted_date: Optional[str] = None

    @property
    def registrant_name(self) -> str:
        """Full registrant name."""
        return f"{self.registrant_first_name} {self.registrant_last_name}".strip()

    @property
    def is_active(self) -> bool:
        """Check if registration is currently active."""
        if not self.end_date or self.end_date == "null":
            return True
        try:
            end = datetime.strptime(self.end_date, "%Y-%m-%d")
            return end >= datetime.now()
        except (ValueError, TypeError):
            return True


@dataclass
class LobbyingCommunication:
    """Represents a lobbying communication report."""

    comlog_id: str
    client_org_name: str
    registrant_last_name: str
    registrant_first_name: str
    comm_date: str
    reg_type: str
    submission_date: str
    posted_date: str
    dpoh_names: List[str] = field(default_factory=list)
    dpoh_titles: List[str] = field(default_factory=list)
    institutions: List[str] = field(default_factory=list)
    subject_matters: List[str] = field(default_factory=list)

    @property
    def registrant_name(self) -> str:
        """Full registrant name."""
        return f"{self.registrant_first_name} {self.registrant_last_name}".strip()


class LobbyingRegistryClient:
    """Client for accessing Canadian federal lobbying registry data."""

    def __init__(
        self,
        *,
        session: Optional[RateLimitedSession] = None,
        cache_dir: Optional[Path] = None,
        auto_update: bool = False,
        source: str = "official"
    ) -> None:
        """
        Initialize the lobbying registry client.

        Args:
            session: Optional HTTP session
            cache_dir: Directory for caching data files
            auto_update: If True, check for updates and redownload if older than 7 days
            source: Data source - "official" for lobbycanada.gc.ca (default, most current)
                    or "opendata" for open.canada.ca (alternative source)
        """
        self.session = session or RateLimitedSession()
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.auto_update = auto_update
        self.source = source

        # Set URLs based on source
        if source == "opendata":
            self.registrations_url = OPENDATA_REGISTRATIONS_URL
            self.communications_url = OPENDATA_COMMUNICATIONS_URL
        else:
            self.registrations_url = OFFICIAL_REGISTRATIONS_URL
            self.communications_url = OFFICIAL_COMMUNICATIONS_URL

        # Cached data
        self._registrations: Optional[List[LobbyingRegistration]] = None
        self._communications: Optional[List[LobbyingCommunication]] = None
        self._subject_matters: Optional[Dict[str, List[str]]] = None
        self._government_institutions: Optional[Dict[str, List[str]]] = None

    def _should_download(self, file_path: Path) -> bool:
        """Check if file should be downloaded."""
        if not file_path.exists():
            return True
        if not self.auto_update:
            return False
        # Redownload if older than 7 days
        age_days = (datetime.now().timestamp() - file_path.stat().st_mtime) / 86400
        return age_days > 7

    def _download_and_extract(self, url: str, zip_name: str) -> Path:
        """Download and extract a ZIP file to cache."""
        zip_path = self.cache_dir / zip_name
        extract_dir = self.cache_dir / zip_name.replace(".zip", "")

        if self._should_download(zip_path):
            print(f"Downloading {zip_name}...")
            response = self.session.get(url)
            response.raise_for_status()
            zip_path.write_bytes(response.content)

            # Extract
            extract_dir.mkdir(exist_ok=True)
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(extract_dir)

        return extract_dir

    def _load_registrations(self) -> List[LobbyingRegistration]:
        """Load registration data from cache or download if needed."""
        if self._registrations is not None:
            return self._registrations

        zip_name = f"registrations_{self.source}.zip"
        extract_dir = self._download_and_extract(self.registrations_url, zip_name)

        # Load primary registrations
        primary_file = extract_dir / "Registration_PrimaryExport.csv"
        registrations_dict = {}

        # Try different encodings (lobbying data uses latin-1)
        with open(primary_file, "r", encoding="latin-1") as f:
            reader = csv.DictReader(f)
            for row in reader:
                reg_id = row["REG_ID_ENR"]
                registrations_dict[reg_id] = LobbyingRegistration(
                    reg_id=reg_id,
                    reg_type=row["REG_TYPE_ENR"],
                    reg_number=row["REG_NUM_ENR"],
                    client_org_name=row.get("EN_CLIENT_ORG_CORP_NM_AN", "N/A"),
                    registrant_last_name=row.get("RGSTRNT_LAST_NM_DCLRNT", ""),
                    registrant_first_name=row.get("RGSTRNT_1ST_NM_PRENOM_DCLRNT", ""),
                    effective_date=row.get("EFFECTIVE_DATE_VIGUEUR"),
                    end_date=row.get("END_DATE_FIN"),
                    posted_date=row.get("POSTED_DATE_PUBLICATION"),
                )

        # Load subject matters
        subject_file = extract_dir / "Registration_SubjectMatterDetailsExport.csv"
        if subject_file.exists():
            with open(subject_file, "r", encoding="latin-1") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    reg_id = row["REG_ID_ENR"]
                    description = row.get("DESCRIPTION", "")
                    if reg_id in registrations_dict and description:
                        registrations_dict[reg_id].subject_matters.append(description)

        # Load government institutions
        inst_file = extract_dir / "Registration_GovernmentInstExport.csv"
        if inst_file.exists():
            with open(inst_file, "r", encoding="latin-1") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    reg_id = row["REG_ID_ENR"]
                    institution = row.get("INSTITUTION", "")
                    if reg_id in registrations_dict and institution:
                        if institution not in registrations_dict[reg_id].government_institutions:
                            registrations_dict[reg_id].government_institutions.append(institution)

        self._registrations = list(registrations_dict.values())
        return self._registrations

    def _load_communications(self) -> List[LobbyingCommunication]:
        """Load communication reports from cache or download if needed."""
        if self._communications is not None:
            return self._communications

        zip_name = f"communications_{self.source}.zip"
        extract_dir = self._download_and_extract(self.communications_url, zip_name)

        # Load primary communications
        primary_file = extract_dir / "Communication_PrimaryExport.csv"
        communications_dict = {}

        with open(primary_file, "r", encoding="latin-1") as f:
            reader = csv.DictReader(f)
            for row in reader:
                comlog_id = row["COMLOG_ID"]
                communications_dict[comlog_id] = LobbyingCommunication(
                    comlog_id=comlog_id,
                    client_org_name=row.get("EN_CLIENT_ORG_CORP_NM_AN", "N/A"),
                    registrant_last_name=row.get("RGSTRNT_LAST_NM_DCLRNT", ""),
                    registrant_first_name=row.get("RGSTRNT_1ST_NM_PRENOM_DCLRNT", ""),
                    comm_date=row.get("COMM_DATE", ""),
                    reg_type=row.get("REG_TYPE_ENR", ""),
                    submission_date=row.get("SUBMISSION_DATE_SOUMISSION", ""),
                    posted_date=row.get("POSTED_DATE_PUBLICATION", ""),
                )

        # Load DPOHs
        dpoh_file = extract_dir / "Communication_DpohExport.csv"
        if dpoh_file.exists():
            with open(dpoh_file, "r", encoding="latin-1") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    comlog_id = row["COMLOG_ID"]
                    if comlog_id in communications_dict:
                        dpoh_name = f"{row.get('DPOH_FIRST_NM_PRENOM_TCPD', '')} {row.get('DPOH_LAST_NM_TCPD', '')}".strip()
                        dpoh_title = row.get("DPOH_TITLE_TITRE_TCPD", "")
                        institution = row.get("INSTITUTION", "")

                        if dpoh_name:
                            communications_dict[comlog_id].dpoh_names.append(dpoh_name)
                        if dpoh_title:
                            communications_dict[comlog_id].dpoh_titles.append(dpoh_title)
                        if institution and institution not in communications_dict[comlog_id].institutions:
                            communications_dict[comlog_id].institutions.append(institution)

        # Load subject matters
        subject_file = extract_dir / "Communication_SubjectMatterDetailsExport.csv"
        if subject_file.exists():
            with open(subject_file, "r", encoding="latin-1") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    comlog_id = row["COMLOG_ID"]
                    description = row.get("DESCRIPTION", "")
                    if comlog_id in communications_dict and description:
                        communications_dict[comlog_id].subject_matters.append(description)

        self._communications = list(communications_dict.values())
        return self._communications

    def search_registrations(
        self,
        client_name: Optional[str] = None,
        lobbyist_name: Optional[str] = None,
        subject_keyword: Optional[str] = None,
        institution: Optional[str] = None,
        active_only: bool = True,
        limit: Optional[int] = None
    ) -> List[LobbyingRegistration]:
        """
        Search lobbying registrations.

        Args:
            client_name: Client/organization name to search for
            lobbyist_name: Lobbyist name to search for
            subject_keyword: Keyword in subject matter descriptions
            institution: Government institution name
            active_only: Only return active registrations
            limit: Maximum number of results

        Returns:
            List of matching registrations
        """
        registrations = self._load_registrations()
        results = registrations

        if active_only:
            results = [r for r in results if r.is_active]

        if client_name:
            client_lower = client_name.lower()
            results = [r for r in results if client_lower in r.client_org_name.lower()]

        if lobbyist_name:
            lobbyist_lower = lobbyist_name.lower()
            results = [
                r for r in results
                if lobbyist_lower in r.registrant_name.lower()
            ]

        if subject_keyword:
            keyword_lower = subject_keyword.lower()
            results = [
                r for r in results
                if any(keyword_lower in sm.lower() for sm in r.subject_matters)
            ]

        if institution:
            inst_lower = institution.lower()
            results = [
                r for r in results
                if any(inst_lower in gi.lower() for gi in r.government_institutions)
            ]

        if limit:
            results = results[:limit]

        return results

    def search_communications(
        self,
        client_name: Optional[str] = None,
        lobbyist_name: Optional[str] = None,
        official_name: Optional[str] = None,
        institution: Optional[str] = None,
        subject_keyword: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[LobbyingCommunication]:
        """
        Search lobbying communications.

        Args:
            client_name: Client/organization name
            lobbyist_name: Lobbyist name
            official_name: Government official (DPOH) name
            institution: Government institution
            subject_keyword: Keyword in subject matter
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            limit: Maximum number of results

        Returns:
            List of matching communications
        """
        communications = self._load_communications()
        results = communications

        if client_name:
            client_lower = client_name.lower()
            results = [c for c in results if client_lower in c.client_org_name.lower()]

        if lobbyist_name:
            lobbyist_lower = lobbyist_name.lower()
            results = [
                c for c in results
                if lobbyist_lower in c.registrant_name.lower()
            ]

        if official_name:
            official_lower = official_name.lower()
            results = [
                c for c in results
                if any(official_lower in name.lower() for name in c.dpoh_names)
            ]

        if institution:
            inst_lower = institution.lower()
            results = [
                c for c in results
                if any(inst_lower in inst.lower() for inst in c.institutions)
            ]

        if subject_keyword:
            keyword_lower = subject_keyword.lower()
            results = [
                c for c in results
                if any(keyword_lower in sm.lower() for sm in c.subject_matters)
            ]

        if date_from:
            results = [c for c in results if c.comm_date >= date_from]

        if date_to:
            results = [c for c in results if c.comm_date <= date_to]

        # Sort by date (most recent first)
        results = sorted(results, key=lambda x: x.comm_date, reverse=True)

        if limit:
            results = results[:limit]

        return results

    def get_top_clients(self, limit: int = 20, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get top clients by number of active registrations.

        Args:
            limit: Number of top clients to return
            active_only: Only count active registrations

        Returns:
            List of dicts with client_name and count
        """
        registrations = self._load_registrations()

        if active_only:
            registrations = [r for r in registrations if r.is_active]

        # Count by client
        client_counts: Dict[str, int] = {}
        for reg in registrations:
            client_counts[reg.client_org_name] = client_counts.get(reg.client_org_name, 0) + 1

        # Sort and return top N
        sorted_clients = sorted(client_counts.items(), key=lambda x: x[1], reverse=True)
        return [
            {"client_name": name, "registration_count": count}
            for name, count in sorted_clients[:limit]
        ]

    def get_top_lobbyists(self, limit: int = 20, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get top lobbyists by number of registrations.

        Args:
            limit: Number of top lobbyists to return
            active_only: Only count active registrations

        Returns:
            List of dicts with lobbyist_name and count
        """
        registrations = self._load_registrations()

        if active_only:
            registrations = [r for r in registrations if r.is_active]

        # Count by lobbyist
        lobbyist_counts: Dict[str, int] = {}
        for reg in registrations:
            name = reg.registrant_name
            if name:
                lobbyist_counts[name] = lobbyist_counts.get(name, 0) + 1

        # Sort and return top N
        sorted_lobbyists = sorted(lobbyist_counts.items(), key=lambda x: x[1], reverse=True)
        return [
            {"lobbyist_name": name, "registration_count": count}
            for name, count in sorted_lobbyists[:limit]
        ]
