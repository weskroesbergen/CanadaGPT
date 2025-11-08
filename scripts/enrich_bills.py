#!/usr/bin/env python3
"""
Enrich bill data with missing fields from LEGISinfo individual bill API.

This script fetches detailed bill information from LEGISinfo and populates:
- summary: Legislative summary text
- bill_type: Bill document type (e.g., "Government Bill", "Private Member's Bill")
- is_government_bill: Boolean flag
- is_private_member_bill: Boolean flag
- originating_chamber: House or Senate
- latest_event: Most recent bill event
- is_proforma: Pro forma bill flag
- statute_year: Year if passed into law
- statute_chapter: Chapter number if passed into law

Committee relationships are also created if available in bill stages.

Usage:
    python scripts/enrich_bills.py [--limit N] [--dry-run]

Options:
    --limit N: Only process first N bills (for testing)
    --dry-run: Show what would be updated without making changes
"""

import sys
import os
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add packages to path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "data-pipeline"))

from dotenv import load_dotenv
from fedmcp.clients.legisinfo import LegisInfoClient
from fedmcp_pipeline.utils.neo4j_client import Neo4jClient


class BillEnricher:
    """Enriches bill data from LEGISinfo API."""

    def __init__(self, neo4j_client: Neo4jClient, dry_run: bool = False):
        self.neo4j = neo4j_client
        self.legis = LegisInfoClient()
        self.dry_run = dry_run
        self.stats = {
            "total_bills": 0,
            "enriched": 0,
            "already_complete": 0,
            "errors": 0,
            "committee_relationships": 0,
        }

    def get_bills_needing_enrichment(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get bills from database that need enrichment (missing summary or bill_type)."""
        query = """
        MATCH (b:Bill)
        WHERE b.summary IS NULL OR b.bill_type IS NULL
        RETURN b.number AS number, b.session AS session
        ORDER BY b.introduced_date DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        results = self.neo4j.run_query(query)
        print(f"\n📊 Found {len(results):,} bills needing enrichment")
        return results

    def enrich_bill(self, bill_number: str, session: str) -> bool:
        """
        Fetch detailed bill data and update the database.

        Returns:
            True if bill was enriched, False if skipped or error
        """
        try:
            # Fetch detailed bill data from LEGISinfo
            bill_data = self.legis.get_bill(session, bill_number)

            # Handle case where API returns a list instead of dict
            if isinstance(bill_data, list):
                if not bill_data:
                    print(f"   ⚠️  Empty list returned for {bill_number}")
                    self.stats["errors"] += 1
                    return False
                # Take the first bill if multiple returned (likely different versions)
                bill_data = bill_data[0]

            # Validate we have a dict
            if not bill_data or not isinstance(bill_data, dict):
                print(f"   ⚠️  Invalid data type for {bill_number}: {type(bill_data)}")
                self.stats["errors"] += 1
                return False

            # Extract enrichment fields
            updates = self._extract_enrichment_fields(bill_data)

            if not updates:
                print(f"   ✓ {bill_number} already complete")
                self.stats["already_complete"] += 1
                return False

            # Update database
            if self.dry_run:
                print(f"   [DRY RUN] Would update {bill_number} with: {list(updates.keys())}")
            else:
                self._update_bill(bill_number, session, updates)

            # Extract and create committee relationships
            committees = self._extract_committees(bill_data)
            if committees and not self.dry_run:
                self._create_committee_relationships(bill_number, session, committees)
            elif committees:
                print(f"   [DRY RUN] Would create {len(committees)} committee relationships")

            self.stats["enriched"] += 1
            return True

        except ValueError as e:
            # JSON decode errors - older bills may not have data available
            if "Expecting value" in str(e) or "JSON" in str(e):
                print(f"   ⚠️  No JSON data available for {bill_number} (likely too old)")
                self.stats["errors"] += 1
                return False
            else:
                print(f"   ❌ ValueError enriching {bill_number}: {e}")
                self.stats["errors"] += 1
                return False
        except Exception as e:
            print(f"   ❌ Error enriching {bill_number}: {e}")
            self.stats["errors"] += 1
            return False

    def _extract_enrichment_fields(self, bill_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract fields to enrich from bill detail JSON."""
        updates = {}

        # Summary
        summary = bill_data.get("ShortLegislativeSummaryEn")
        if summary:
            updates["summary"] = summary
            updates["summary_fr"] = bill_data.get("ShortLegislativeSummaryFr")
            updates["full_summary_available"] = bill_data.get("IsFullLegislativeSummaryAvailable", False)

        # Bill type classification
        bill_type = bill_data.get("BillDocumentTypeNameEn")
        if bill_type:
            updates["bill_type"] = bill_type
            updates["bill_type_fr"] = bill_data.get("BillDocumentTypeNameFr")

        # Government vs private member
        is_gov = bill_data.get("IsGovernmentBill")
        if is_gov is not None:
            updates["is_government_bill"] = is_gov
            updates["is_private_member_bill"] = not is_gov

        # Originating chamber
        chamber = bill_data.get("OriginatingChamberNameEn")
        if chamber:
            updates["originating_chamber"] = chamber
            updates["originating_chamber_fr"] = bill_data.get("OriginatingChamberNameFr")

        # Latest event
        latest_event = bill_data.get("LatestBillEventTypeName")
        if latest_event:
            updates["latest_event"] = latest_event

        # Pro forma flag
        is_proforma = bill_data.get("IsProForma")
        if is_proforma is not None:
            updates["is_proforma"] = is_proforma

        bill_form = bill_data.get("BillFormName")
        if bill_form:
            updates["bill_form"] = bill_form

        # Statute info (if passed into law)
        statute_year = bill_data.get("StatuteYear")
        if statute_year:
            updates["statute_year"] = statute_year

        statute_chapter = bill_data.get("StatuteChapter")
        if statute_chapter:
            updates["statute_chapter"] = statute_chapter

        # Reinstated info
        reinstated = bill_data.get("DidReinstateFromPreviousSession")
        if reinstated is not None:
            updates["reinstated_from_previous"] = reinstated

        reinstated_from = bill_data.get("ReinstatedFromBillNumberCode")
        if reinstated_from:
            updates["reinstated_from_bill"] = reinstated_from

        return updates

    def _extract_committees(self, bill_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract committee referrals from bill stages."""
        committees = []

        # Check House stages
        bill_stages = bill_data.get("BillStages", {})
        house_stages = bill_stages.get("HouseBillStages", [])

        for stage in house_stages:
            committee_data = stage.get("Committee")
            if committee_data:
                committees.append({
                    "code": committee_data.get("CommitteeAcronym", ""),
                    "name": committee_data.get("CommitteeNameEn", ""),
                    "stage": stage.get("BillStageName", ""),
                })

        # Check Senate stages
        senate_stages = bill_stages.get("SenateBillStages", [])

        for stage in senate_stages:
            committee_data = stage.get("Committee")
            if committee_data:
                committees.append({
                    "code": committee_data.get("CommitteeAcronym", ""),
                    "name": committee_data.get("CommitteeNameEn", ""),
                    "stage": stage.get("BillStageName", ""),
                })

        return committees

    def _update_bill(self, bill_number: str, session: str, updates: Dict[str, Any]):
        """Update bill in Neo4j with enrichment fields."""
        # Build SET clause
        set_parts = [f"b.{key} = ${key}" for key in updates.keys()]
        set_parts.append("b.updated_at = $updated_at")
        set_clause = ", ".join(set_parts)

        query = f"""
        MATCH (b:Bill {{number: $number, session: $session}})
        SET {set_clause}
        RETURN b
        """

        params = {
            "number": bill_number,
            "session": session,
            "updated_at": datetime.utcnow().isoformat(),
            **updates
        }

        self.neo4j.run_query(query, params)
        print(f"   ✅ Enriched {bill_number} with {len(updates)} fields")

    def _create_committee_relationships(
        self,
        bill_number: str,
        session: str,
        committees: List[Dict[str, str]]
    ):
        """Create REFERRED_TO relationships between bills and committees."""
        for committee in committees:
            if not committee.get("code"):
                continue

            # Infer chamber from committee name
            name = committee.get("name", "")
            if "Senate" in name:
                chamber = "Senate"
            elif "Committee of the Whole" in name:
                chamber = "House"
            else:
                chamber = "House"

            query = """
            MATCH (b:Bill {number: $number, session: $session})
            MERGE (c:Committee {code: $code})
            ON CREATE SET
                c.name = $name,
                c.chamber = $chamber,
                c.created_at = datetime()
            MERGE (b)-[r:REFERRED_TO]->(c)
            ON CREATE SET
                r.stage = $stage,
                r.created_at = datetime()
            """

            params = {
                "number": bill_number,
                "session": session,
                "code": committee["code"],
                "name": committee["name"],
                "chamber": chamber,
                "stage": committee["stage"],
            }

            self.neo4j.run_query(query, params)
            self.stats["committee_relationships"] += 1

    def run(self, limit: Optional[int] = None):
        """Run the enrichment process."""
        print("=" * 80)
        print("BILLS DATA ENRICHMENT")
        print("=" * 80)

        if self.dry_run:
            print("⚠️  DRY RUN MODE - No changes will be made")

        # Get bills needing enrichment
        bills = self.get_bills_needing_enrichment(limit=limit)
        self.stats["total_bills"] = len(bills)

        if not bills:
            print("\n✅ All bills already enriched!")
            return

        print(f"\n🔄 Enriching {len(bills):,} bills...")
        print("")

        # Process each bill
        start_time = time.time()
        for i, bill in enumerate(bills, 1):
            if i % 10 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                remaining = (len(bills) - i) / rate if rate > 0 else 0
                print(f"\n📊 Progress: {i}/{len(bills)} ({i/len(bills)*100:.1f}%) | "
                      f"Rate: {rate:.1f} bills/sec | ETA: {remaining/60:.1f}min")

            bill_number = bill["number"]
            session = bill["session"]

            print(f"{i:4d}. Enriching {session}/{bill_number}...", end="")
            self.enrich_bill(bill_number, session)

            # Be respectful of LEGISinfo (no explicit rate limit, but don't hammer)
            time.sleep(0.1)

        # Print summary
        elapsed = time.time() - start_time
        print("\n" + "=" * 80)
        print("ENRICHMENT COMPLETE")
        print("=" * 80)
        print(f"Total bills processed: {self.stats['total_bills']:,}")
        print(f"Bills enriched: {self.stats['enriched']:,}")
        print(f"Already complete: {self.stats['already_complete']:,}")
        print(f"Errors: {self.stats['errors']:,}")
        print(f"Committee relationships: {self.stats['committee_relationships']:,}")
        print(f"Time elapsed: {elapsed/60:.1f} minutes")
        print(f"Rate: {self.stats['total_bills']/elapsed:.1f} bills/sec")
        print("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Enrich bills with detailed LEGISinfo data")
    parser.add_argument("--limit", type=int, help="Only process first N bills (for testing)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be updated without making changes")
    parser.add_argument("--env-file", default=None, help="Path to .env file (default: packages/data-pipeline/.env)")

    args = parser.parse_args()

    # Load environment
    env_file = args.env_file or PROJECT_ROOT / "packages" / "data-pipeline" / ".env"
    if Path(env_file).exists():
        load_dotenv(env_file)
        print(f"✅ Loaded environment from {env_file}")
    else:
        print(f"⚠️  No .env file found at {env_file}, using system environment")

    # Connect to Neo4j
    neo4j_client = Neo4jClient(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password")
    )

    # Run enrichment
    enricher = BillEnricher(neo4j_client, dry_run=args.dry_run)
    enricher.run(limit=args.limit)

    # Cleanup
    neo4j_client.close()


if __name__ == "__main__":
    main()
