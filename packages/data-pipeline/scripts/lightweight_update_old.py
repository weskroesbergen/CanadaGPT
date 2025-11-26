#!/usr/bin/env python3
"""
Lightweight hourly update job for Cloud Run.

Updates only critical data that changes frequently:
- MP party affiliations (e.g., floor-crossers like Chris d'Entrement)
- Cabinet positions
- New bills introduced
- Recent votes (last 24 hours)

Designed to be fast (<1 minute) and low-memory (<200MB).
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

# Add packages to path
SCRIPT_DIR = Path(__file__).parent
PIPELINE_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PIPELINE_DIR))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.config import Config
from fedmcp_pipeline.utils.progress import logger

# Add fedmcp clients
FEDMCP_PATH = PIPELINE_DIR.parent / "fedmcp" / "src"
sys.path.insert(0, str(FEDMCP_PATH))

from fedmcp.clients.openparliament import OpenParliamentClient


class LightweightUpdater:
    """Fast hourly updates for critical parliamentary data."""

    def __init__(self, neo4j_client: Neo4jClient):
        self.neo4j = neo4j_client
        self.op_client = OpenParliamentClient()
        self.stats = {
            "mps_updated": 0,
            "party_changes": [],
            "cabinet_changes": [],
            "new_bills": 0,
            "new_votes": 0,
        }

    def update_mp_parties(self) -> int:
        """
        Update MP party affiliations.

        Returns count of MPs updated.
        """
        logger.info("Checking for MP party changes...")

        updated_count = 0

        # Fetch all current MPs from OpenParliament
        mps_list = list(self.op_client.list_mps())
        logger.info(f"Fetched {len(mps_list)} current MPs from OpenParliament")

        # Get current party affiliations from Neo4j for comparison
        current_parties_query = """
        MATCH (m:MP)
        RETURN m.id as id, m.name as name, m.party as party
        """
        current_parties = {row["id"]: row for row in self.neo4j.run_query(current_parties_query)}

        for mp_data in mps_list:
            mp_id = mp_data.get("url", "").split("/")[-2]
            mp_name = mp_data.get("name")
            # OpenParliament API returns short_name as either a string or dict {'en': 'Party Name'}
            party_data = mp_data.get("current_party", {}).get("short_name")
            new_party = party_data.get("en") if isinstance(party_data, dict) else party_data

            if not mp_id or not new_party:
                continue

            # Check if party changed
            old_record = current_parties.get(mp_id, {})
            old_party = old_record.get("party")

            if old_party and old_party != new_party:
                logger.warning(f"🔄 Party change detected: {mp_name} ({old_party} → {new_party})")
                self.stats["party_changes"].append({
                    "mp_name": mp_name,
                    "old_party": old_party,
                    "new_party": new_party,
                    "timestamp": datetime.utcnow().isoformat()
                })

            # Update MP record
            update_query = """
            MATCH (m:MP {id: $id})
            SET m.party = $party,
                m.name = $name,
                m.updated_at = datetime()
            RETURN m
            """

            result = self.neo4j.run_query(update_query, {
                "id": mp_id,
                "party": new_party,
                "name": mp_name
            })

            if result:
                updated_count += 1

        logger.success(f"✅ Updated {updated_count} MP records")
        return updated_count

    def update_cabinet_positions(self) -> int:
        """
        Update cabinet positions from OpenParliament current_role field.

        Returns count of cabinet ministers updated.
        """
        logger.info("Checking for cabinet changes...")

        updated_count = 0

        # Get current cabinet positions from Neo4j
        current_cabinet_query = """
        MATCH (m:MP)
        WHERE m.cabinet_position IS NOT NULL
        RETURN m.id as id, m.name as name, m.cabinet_position as position
        """
        current_cabinet = {row["id"]: row for row in self.neo4j.run_query(current_cabinet_query)}

        # Fetch MPs with cabinet roles from OpenParliament
        mps_list = list(self.op_client.list_mps())

        for mp_data in mps_list:
            mp_id = mp_data.get("url", "").split("/")[-2]
            mp_name = mp_data.get("name")
            current_role = mp_data.get("current_role")

            if not mp_id:
                continue

            # Extract cabinet position if exists
            new_position = None
            if current_role and "Minister" in current_role:
                new_position = current_role

            old_record = current_cabinet.get(mp_id, {})
            old_position = old_record.get("position")

            # Detect changes
            if old_position != new_position:
                if old_position and not new_position:
                    logger.warning(f"📉 Cabinet exit: {mp_name} (was {old_position})")
                    self.stats["cabinet_changes"].append({
                        "mp_name": mp_name,
                        "type": "exit",
                        "old_position": old_position,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                elif not old_position and new_position:
                    logger.warning(f"📈 New cabinet minister: {mp_name} → {new_position}")
                    self.stats["cabinet_changes"].append({
                        "mp_name": mp_name,
                        "type": "appointment",
                        "new_position": new_position,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                elif old_position and new_position:
                    logger.warning(f"🔄 Cabinet shuffle: {mp_name} ({old_position} → {new_position})")
                    self.stats["cabinet_changes"].append({
                        "mp_name": mp_name,
                        "type": "shuffle",
                        "old_position": old_position,
                        "new_position": new_position,
                        "timestamp": datetime.utcnow().isoformat()
                    })

            # Update record
            if new_position:
                update_query = """
                MATCH (m:MP {id: $id})
                SET m.cabinet_position = $position,
                    m.updated_at = datetime()
                RETURN m
                """
            else:
                # Remove cabinet position if no longer in cabinet
                update_query = """
                MATCH (m:MP {id: $id})
                REMOVE m.cabinet_position
                SET m.updated_at = datetime()
                RETURN m
                """

            result = self.neo4j.run_query(update_query, {
                "id": mp_id,
                "position": new_position
            } if new_position else {"id": mp_id})

            if result:
                updated_count += 1

        logger.success(f"✅ Updated {updated_count} cabinet positions")
        return updated_count

    def check_new_bills(self, since_hours: int = 24) -> int:
        """
        Check for bills introduced in the last N hours.

        Args:
            since_hours: Look back this many hours

        Returns count of new bills.
        """
        logger.info(f"Checking for bills introduced in last {since_hours} hours...")

        cutoff_date = (datetime.utcnow() - timedelta(hours=since_hours)).date().isoformat()
        new_count = 0

        # Get latest bills from OpenParliament
        for bill in self.op_client.list_bills():
            introduced_date = bill.get("introduced")

            if not introduced_date or introduced_date < cutoff_date:
                continue

            # Check if bill already exists in Neo4j
            bill_number = bill.get("number")
            bill_session = bill.get("session")

            check_query = """
            MATCH (b:Bill {number: $number, session: $session})
            RETURN b
            """

            existing = self.neo4j.run_query(check_query, {
                "number": bill_number,
                "session": bill_session
            })

            if not existing:
                # Create new bill node
                create_query = """
                MERGE (b:Bill {number: $number, session: $session})
                SET b.name_en = $name_en,
                    b.name_fr = $name_fr,
                    b.introduced = $introduced,
                    b.sponsor_politician_id = $sponsor_id,
                    b.status_code = $status,
                    b.updated_at = datetime()
                RETURN b
                """

                self.neo4j.run_query(create_query, {
                    "number": bill_number,
                    "session": bill_session,
                    "name_en": bill.get("name", {}).get("en"),
                    "name_fr": bill.get("name", {}).get("fr"),
                    "introduced": introduced_date,
                    "sponsor_id": bill.get("sponsor_politician_url", "").split("/")[-2] if bill.get("sponsor_politician_url") else None,
                    "status": bill.get("status_code")
                })

                new_count += 1
                logger.info(f"📜 New bill: {bill_number} - {bill.get('name', {}).get('en', 'Unknown')}")

        logger.success(f"✅ Found {new_count} new bills")
        return new_count

    def check_recent_votes(self, since_hours: int = 24) -> int:
        """
        Check for votes in the last N hours.

        Args:
            since_hours: Look back this many hours

        Returns count of new votes.
        """
        logger.info(f"Checking for votes in last {since_hours} hours...")

        cutoff_date = (datetime.utcnow() - timedelta(hours=since_hours)).date().isoformat()
        new_count = 0

        for vote in self.op_client.list_votes():
            vote_date = vote.get("date")

            if not vote_date or vote_date < cutoff_date:
                continue

            # Check if vote already exists
            vote_id = f"{vote.get('session')}-{vote.get('number')}"

            check_query = """
            MATCH (v:Vote {id: $id})
            RETURN v
            """

            existing = self.neo4j.run_query(check_query, {"id": vote_id})

            if not existing:
                # Create new vote node
                create_query = """
                MERGE (v:Vote {id: $id})
                SET v.number = $number,
                    v.session = $session,
                    v.date = $date,
                    v.result = $result,
                    v.yeas = $yeas,
                    v.nays = $nays,
                    v.paired = $paired,
                    v.updated_at = datetime()
                RETURN v
                """

                self.neo4j.run_query(create_query, {
                    "id": vote_id,
                    "number": vote.get("number"),
                    "session": vote.get("session"),
                    "date": vote_date,
                    "result": vote.get("result"),
                    "yeas": vote.get("yeas"),
                    "nays": vote.get("nays"),
                    "paired": vote.get("paired")
                })

                new_count += 1
                logger.info(f"🗳️  New vote: {vote_id} - {vote.get('result')}")

        logger.success(f"✅ Found {new_count} new votes")
        return new_count

    def run_all(self) -> Dict[str, Any]:
        """
        Run all lightweight updates.

        Returns statistics dictionary.
        """
        start_time = datetime.utcnow()

        logger.info("=" * 60)
        logger.info("LIGHTWEIGHT HOURLY UPDATE")
        logger.info(f"Started: {start_time.isoformat()}")
        logger.info("=" * 60)

        # Update MP parties (most important - catches floor-crossers)
        self.stats["mps_updated"] = self.update_mp_parties()

        # Update cabinet positions
        cabinet_count = self.update_cabinet_positions()

        # Check for new bills (last 24 hours)
        self.stats["new_bills"] = self.check_new_bills(since_hours=24)

        # Check for new votes (last 24 hours)
        self.stats["new_votes"] = self.check_recent_votes(since_hours=24)

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        logger.info("=" * 60)
        logger.success("✅ LIGHTWEIGHT UPDATE COMPLETE")
        logger.info(f"Duration: {duration:.1f} seconds")
        logger.info(f"MPs updated: {self.stats['mps_updated']}")
        logger.info(f"Party changes: {len(self.stats['party_changes'])}")
        logger.info(f"Cabinet changes: {len(self.stats['cabinet_changes'])}")
        logger.info(f"New bills: {self.stats['new_bills']}")
        logger.info(f"New votes: {self.stats['new_votes']}")

        # Log any party changes prominently
        if self.stats["party_changes"]:
            logger.warning("=" * 60)
            logger.warning("⚠️  PARTY CHANGES DETECTED:")
            for change in self.stats["party_changes"]:
                logger.warning(f"  • {change['mp_name']}: {change['old_party']} → {change['new_party']}")
            logger.warning("=" * 60)

        # Log any cabinet changes
        if self.stats["cabinet_changes"]:
            logger.warning("=" * 60)
            logger.warning("📋 CABINET CHANGES DETECTED:")
            for change in self.stats["cabinet_changes"]:
                if change["type"] == "appointment":
                    logger.warning(f"  • NEW: {change['mp_name']} → {change['new_position']}")
                elif change["type"] == "exit":
                    logger.warning(f"  • EXIT: {change['mp_name']} (was {change['old_position']})")
                elif change["type"] == "shuffle":
                    logger.warning(f"  • SHUFFLE: {change['mp_name']}: {change['old_position']} → {change['new_position']}")
            logger.warning("=" * 60)

        logger.info("=" * 60)

        return self.stats


def main():
    """Main entry point for Cloud Run job."""

    # Load config from environment or .env file
    config = Config()

    # Connect to Neo4j
    neo4j_client = Neo4jClient(
        uri=config.neo4j_uri,
        user=config.neo4j_user,
        password=config.neo4j_password
    )

    try:
        # Run lightweight updates
        updater = LightweightUpdater(neo4j_client)
        stats = updater.run_all()

        # Return success
        logger.success("Lightweight update completed successfully")
        return 0

    except Exception as e:
        logger.error(f"Lightweight update failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        neo4j_client.close()


if __name__ == "__main__":
    exit(main())
