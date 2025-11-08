"""Import historical Hansard data from Lipad project (1901-1993)."""

import os
import sys
import csv
import zipfile
import requests
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Iterator
from xml.etree import ElementTree as ET

from ..utils.neo4j_client import Neo4jClient
from ..utils.progress import logger, ProgressTracker, batch_iterator


class LipadHistoricalImporter:
    """
    Import historical Hansard data from Lipad project (1901-1993).

    Fills the gap between Confederation and OpenParliament's coverage.

    Data Sources:
    - CSV: Daily Hansard files in UTF-8
    - XML: Digitized Hansard (1901-1993)
    - PostgreSQL: Complete database dump

    Coverage: 1901-1993 (93 years of historical data)
    """

    # Note: These URLs are placeholders - actual URLs from lipad.ca/data/
    LIPAD_DATA_URL = "https://www.lipad.ca/data/"
    CSV_PACKAGE_URL = "https://www.lipad.ca/data/lipad-csv-package.zip"  # Hypothetical
    XML_PACKAGE_URL = "https://www.lipad.ca/data/lipad-xml-package.zip"  # Hypothetical

    def __init__(self, neo4j_client: Neo4jClient):
        """
        Initialize Lipad importer.

        Args:
            neo4j_client: Neo4j client instance
        """
        self.neo4j = neo4j_client
        self.download_dir = Path(tempfile.gettempdir()) / "lipad_import"
        self.download_dir.mkdir(exist_ok=True)

    def download_csv_package(self, output_dir: Optional[Path] = None) -> Path:
        """
        Download Lipad CSV package.

        Note: This is a placeholder. Actual implementation depends on
        Lipad's current download structure.

        Args:
            output_dir: Where to save files (default: temp directory)

        Returns:
            Path to extracted CSV files
        """
        if output_dir is None:
            output_dir = self.download_dir / "csv"
        output_dir.mkdir(exist_ok=True, parents=True)

        logger.info(f"Lipad CSV download placeholder")
        logger.info(f"Visit {self.LIPAD_DATA_URL} to download CSV package manually")
        logger.info(f"Extract to: {output_dir}")

        return output_dir

    def import_from_csv_directory(self, csv_dir: Path, batch_size: int = 1000, limit: Optional[int] = None) -> Dict[str, int]:
        """
        Import Hansard from Lipad CSV files.

        Expected CSV structure (based on Lipad documentation):
        - One file per sitting day
        - Columns: date, speaker, speech_text, etc.

        Args:
            csv_dir: Directory containing CSV files
            batch_size: Batch size for Neo4j operations
            limit: Limit number of files to process (for testing)

        Returns:
            Dict with import statistics
        """
        logger.info(f"Importing Lipad CSV files from {csv_dir}...")

        csv_files = sorted(csv_dir.glob("*.csv"))

        if limit:
            csv_files = csv_files[:limit]

        logger.info(f"Found {len(csv_files):,} CSV files to process")

        stats = {"debates": 0, "statements": 0, "speakers": 0}

        debates_data = []
        statements_data = []
        speaker_ids = set()

        for i, csv_file in enumerate(csv_files):
            if (i + 1) % 100 == 0:
                logger.info(f"Processed {i + 1}/{len(csv_files)} files...")

            try:
                with open(csv_file, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)

                    # Extract date from filename or first row
                    sitting_date = None
                    current_debate = None

                    for row in reader:
                        # Extract debate metadata
                        if sitting_date is None:
                            sitting_date = row.get('date') or row.get('sitting_date')

                            if sitting_date:
                                debate_id = f"lipad-{sitting_date}"
                                current_debate = {
                                    "id": debate_id,
                                    "date": sitting_date,
                                    "source": "lipad",
                                    "parliament": self._extract_parliament_from_date(sitting_date),
                                    "updated_at": datetime.utcnow().isoformat(),
                                }
                                debates_data.append(current_debate)
                                stats["debates"] += 1

                        # Extract statement
                        speaker = row.get('speaker') or row.get('speakername')
                        content = row.get('speechtext') or row.get('content') or row.get('text')

                        if content:
                            statement_id = f"lipad-stmt-{sitting_date}-{stats['statements']}"
                            statement = {
                                "id": statement_id,
                                "content": content[:10000],  # Limit content length
                                "speaker_name": speaker,
                                "debate_id": debate_id if current_debate else None,
                                "source": "lipad",
                                "updated_at": datetime.utcnow().isoformat(),
                            }

                            # Filter None values
                            statement = {k: v for k, v in statement.items() if v is not None}
                            statements_data.append(statement)
                            stats["statements"] += 1

                            if speaker:
                                speaker_ids.add(speaker)

            except Exception as e:
                logger.warning(f"Failed to process {csv_file}: {e}")
                continue

        # Batch import debates
        if debates_data:
            created = self.neo4j.batch_create_nodes("Debate", debates_data, batch_size=batch_size)
            logger.success(f"✅ Imported {created:,} historical debates (1901-1993)")

        # Batch import statements
        if statements_data:
            created = self.neo4j.batch_create_nodes("Statement", statements_data, batch_size=batch_size)
            logger.success(f"✅ Imported {created:,} historical statements")

        stats["speakers"] = len(speaker_ids)
        logger.success(f"✅ Found {stats['speakers']:,} unique speakers")

        return stats

    def import_from_xml_files(self, xml_dir: Path, batch_size: int = 1000, limit: Optional[int] = None) -> Dict[str, int]:
        """
        Import Hansard from Lipad XML files.

        Args:
            xml_dir: Directory containing XML files
            batch_size: Batch size for Neo4j operations
            limit: Limit number of files (for testing)

        Returns:
            Dict with import statistics
        """
        logger.info(f"Importing Lipad XML files from {xml_dir}...")

        xml_files = sorted(xml_dir.glob("*.xml"))

        if limit:
            xml_files = xml_files[:limit]

        logger.info(f"Found {len(xml_files):,} XML files to process")

        stats = {"debates": 0, "statements": 0}

        debates_data = []
        statements_data = []

        for i, xml_file in enumerate(xml_files):
            if (i + 1) % 100 == 0:
                logger.info(f"Processed {i + 1}/{len(xml_files)} files...")

            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()

                # Extract debate metadata from XML
                date_elem = root.find(".//date")
                sitting_date = date_elem.text if date_elem is not None else None

                if sitting_date:
                    debate_id = f"lipad-{sitting_date}"
                    debate = {
                        "id": debate_id,
                        "date": sitting_date,
                        "source": "lipad",
                        "parliament": self._extract_parliament_from_date(sitting_date),
                        "updated_at": datetime.utcnow().isoformat(),
                    }
                    debates_data.append(debate)
                    stats["debates"] += 1

                # Extract speeches/statements
                for speech in root.findall(".//speech"):
                    speaker_elem = speech.find("speaker")
                    content_elem = speech.find("content")

                    speaker = speaker_elem.text if speaker_elem is not None else None
                    content = content_elem.text if content_elem is not None else None

                    if content:
                        statement_id = f"lipad-stmt-{sitting_date}-{stats['statements']}"
                        statement = {
                            "id": statement_id,
                            "content": content[:10000],
                            "speaker_name": speaker,
                            "debate_id": debate_id,
                            "source": "lipad",
                            "updated_at": datetime.utcnow().isoformat(),
                        }

                        statement = {k: v for k, v in statement.items() if v is not None}
                        statements_data.append(statement)
                        stats["statements"] += 1

            except Exception as e:
                logger.warning(f"Failed to process {xml_file}: {e}")
                continue

        # Batch import
        if debates_data:
            created = self.neo4j.batch_create_nodes("Debate", debates_data, batch_size=batch_size)
            logger.success(f"✅ Imported {created:,} historical debates")

        if statements_data:
            created = self.neo4j.batch_create_nodes("Statement", statements_data, batch_size=batch_size)
            logger.success(f"✅ Imported {created:,} historical statements")

        return stats

    def _extract_parliament_from_date(self, date_str: str) -> Optional[int]:
        """
        Estimate parliament number from date.

        Canadian parliaments since 1867:
        - 1st Parliament: 1867-1872
        - Each parliament ~4 years
        - Simple estimation: (year - 1867) / 4 + 1

        Args:
            date_str: ISO date string (YYYY-MM-DD)

        Returns:
            Estimated parliament number
        """
        try:
            year = int(date_str.split('-')[0])
            if year < 1867:
                return None

            # Rough estimation (actual dates vary)
            parliament = ((year - 1867) // 4) + 1
            return parliament
        except:
            return None

    def import_all(self, source: str = "csv", data_dir: Optional[Path] = None, batch_size: int = 1000, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Run complete Lipad historical import.

        Args:
            source: Data source ("csv" or "xml")
            data_dir: Directory with Lipad data files
            batch_size: Batch size for Neo4j operations
            limit: Limit records for testing

        Returns:
            Dict with import statistics
        """
        logger.info("=" * 60)
        logger.info("LIPAD HISTORICAL HANSARD IMPORT (1901-1993)")
        logger.info("=" * 60)

        if data_dir is None:
            logger.warning("No data_dir specified. Please download Lipad data manually from:")
            logger.warning(f"  {self.LIPAD_DATA_URL}")
            logger.warning("Extract and provide path via data_dir parameter")
            return {"error": "No data directory provided"}

        data_path = Path(data_dir)
        if not data_path.exists():
            raise FileNotFoundError(f"Data directory not found: {data_path}")

        if source == "csv":
            stats = self.import_from_csv_directory(data_path, batch_size, limit)
        elif source == "xml":
            stats = self.import_from_xml_files(data_path, batch_size, limit)
        else:
            raise ValueError(f"Unknown source: {source}. Use 'csv' or 'xml'")

        logger.info("=" * 60)
        logger.success("✅ LIPAD HISTORICAL IMPORT COMPLETE")
        logger.info(f"Debates: {stats.get('debates', 0):,}")
        logger.info(f"Statements: {stats.get('statements', 0):,}")
        logger.info(f"Speakers: {stats.get('speakers', 0):,}")
        logger.info("=" * 60)

        return stats


class CombinedHistoricalImporter:
    """
    Combined importer for complete 1901-present coverage.

    Coordinates:
    - Lipad (1901-1993)
    - OpenParliament (1994-present)
    """

    def __init__(self, neo4j_client: Neo4jClient, pg_connection_string: str):
        """
        Initialize combined importer.

        Args:
            neo4j_client: Neo4j client
            pg_connection_string: PostgreSQL connection for OpenParliament dump
        """
        self.neo4j = neo4j_client
        self.pg_conn = pg_connection_string

    def import_complete_history(self, lipad_data_dir: Optional[Path] = None, batch_size: int = 1000) -> Dict[str, Any]:
        """
        Import complete 1901-present historical record.

        Args:
            lipad_data_dir: Path to Lipad CSV/XML data
            batch_size: Batch size for operations

        Returns:
            Combined statistics
        """
        logger.info("=" * 60)
        logger.info("COMPLETE HISTORICAL IMPORT: 1901-PRESENT")
        logger.info("=" * 60)

        stats = {
            "lipad": {},
            "openparliament": {},
            "total_years": 0,
        }

        # Phase 1: Lipad (1901-1993)
        if lipad_data_dir:
            logger.info("\nPhase 1: Importing Lipad historical data (1901-1993)...")
            from .lipad_import import LipadHistoricalImporter

            lipad = LipadHistoricalImporter(self.neo4j)
            stats["lipad"] = lipad.import_all(
                source="csv",
                data_dir=lipad_data_dir,
                batch_size=batch_size
            )
            stats["total_years"] = 93
        else:
            logger.warning("Skipping Lipad import (no data_dir provided)")

        # Phase 2: OpenParliament (1994-present)
        logger.info("\nPhase 2: Importing OpenParliament dump (1994-present)...")
        from .bulk_import import OpenParliamentBulkImporter

        op = OpenParliamentBulkImporter(self.neo4j, self.pg_conn)
        stats["openparliament"] = op.import_all(
            download=True,
            load_pg=True,
            batch_size=batch_size
        )
        stats["total_years"] += 31  # 1994-2025

        logger.info("=" * 60)
        logger.success("✅ COMPLETE HISTORICAL IMPORT FINISHED")
        logger.info(f"Total coverage: {stats['total_years']} years (1901-present)")
        logger.info(f"Lipad debates: {stats['lipad'].get('debates', 0):,}")
        logger.info(f"OpenParliament debates: {stats['openparliament'].get('debates', {}).get('debates', 0):,}")
        logger.info("=" * 60)

        return stats
