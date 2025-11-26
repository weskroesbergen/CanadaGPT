"""
Direct Votes XML import with full metadata extraction.

This module provides direct XML-to-Neo4j ingestion for parliamentary votes,
capturing:
- Vote metadata (number, date, subject, result, bill number)
- Individual MP ballots with person database IDs
- Vote types and classifications
- Complete MP voting records
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add fedmcp package to path
FEDMCP_PATH = Path(__file__).parent.parent.parent.parent / "fedmcp" / "src"
sys.path.insert(0, str(FEDMCP_PATH))

from fedmcp.clients.ourcommons_votes import OurCommonsVotesClient

from ..utils.neo4j_client import Neo4jClient
from ..utils.progress import logger, ProgressTracker


class VotesXMLImporter:
    """
    Import parliamentary votes directly from XML with full metadata.

    This importer:
    1. Fetches vote summaries from bulk XML
    2. For each vote, fetches detailed ballot data
    3. Creates Vote nodes in Neo4j
    4. Creates Ballot nodes linked to MPs via person_db_id
    5. Links votes to Bills where applicable
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient,
        votes_client: Optional[OurCommonsVotesClient] = None
    ):
        """
        Initialize Votes XML importer.

        Args:
            neo4j_client: Neo4j client instance
            votes_client: Optional OurCommonsVotesClient
        """
        self.neo4j = neo4j_client
        self.votes_client = votes_client or OurCommonsVotesClient()

    def import_votes(
        self,
        limit: Optional[int] = None,
        skip_existing: bool = True
    ) -> Dict[str, int]:
        """
        Import votes and ballots from XML.

        Args:
            limit: Maximum number of votes to import (None = all)
            skip_existing: Skip votes that already exist in Neo4j

        Returns:
            Dict with import statistics
        """
        logger.info("Importing votes from XML...")

        stats = {
            "votes": 0,
            "ballots": 0,
            "skipped": 0,
            "errors": 0
        }

        # Get vote summaries from bulk XML
        logger.info("Fetching vote summaries from bulk XML...")
        try:
            summaries = self.votes_client.get_vote_summaries()
        except Exception as e:
            logger.error(f"Error fetching vote summaries: {e}")
            stats["errors"] += 1
            return stats

        logger.info(f"Found {len(summaries)} votes in bulk XML")

        # Sort by vote number descending (newest first)
        summaries.sort(key=lambda v: v.vote_number, reverse=True)

        if limit:
            summaries = summaries[:limit]
            logger.info(f"Limited to {limit} most recent votes")

        # Get existing vote numbers if skipping
        existing_votes = set()
        if skip_existing:
            result = self.neo4j.run_query("""
                MATCH (v:Vote)
                RETURN v.vote_number as vote_number
            """)
            existing_votes = {row['vote_number'] for row in result}
            logger.info(f"Found {len(existing_votes)} existing votes in Neo4j")

        # Process each vote
        tracker = ProgressTracker(
            total=len(summaries),
            desc="Importing votes"
        )

        for summary in summaries:
            try:
                # Skip if already exists
                if skip_existing and summary.vote_number in existing_votes:
                    stats["skipped"] += 1
                    tracker.update(1)
                    continue

                # Fetch detailed vote with ballots
                vote = self.votes_client.get_vote(
                    summary.parliament_number,
                    summary.session_number,
                    summary.vote_number,
                    include_metadata=True
                )

                # Import vote and ballots to Neo4j
                ballot_count = self._import_vote(vote)
                stats["votes"] += 1
                stats["ballots"] += ballot_count

                tracker.update(1)

            except Exception as e:
                logger.error(f"Error importing vote {summary.vote_number}: {e}")
                stats["errors"] += 1
                tracker.update(1)
                continue

        tracker.close()

        logger.success(f"✅ Imported {stats['votes']} votes, {stats['ballots']} ballots")
        if stats["skipped"] > 0:
            logger.info(f"ℹ️  Skipped {stats['skipped']} existing votes")
        if stats["errors"] > 0:
            logger.warning(f"⚠️  {stats['errors']} errors occurred")

        return stats

    def _import_vote(self, vote: Any) -> int:
        """Import a single vote with all ballots."""

        # Create Vote node
        vote_data = {
            "vote_number": vote.vote_number,
            "parliament_number": vote.parliament_number,
            "session_number": vote.session_number,
            "date_time": vote.date_time,
            "result": vote.result,
            "num_yeas": vote.num_yeas,
            "num_nays": vote.num_nays,
            "num_paired": vote.num_paired,
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Add optional fields
        if vote.subject:
            vote_data["subject"] = vote.subject

        if vote.bill_number:
            vote_data["bill_number"] = vote.bill_number

        if vote.vote_type:
            vote_data["vote_type"] = vote.vote_type

        if vote.vote_type_id is not None:
            vote_data["vote_type_id"] = vote.vote_type_id

        # Create/merge Vote node
        cypher = """
            MERGE (v:Vote {vote_number: $vote_number})
            SET v = $vote_data
            SET v.updated_at = datetime()
            RETURN v.vote_number as vote_number
        """
        result = self.neo4j.run_query(cypher, {
            "vote_number": vote.vote_number,
            "vote_data": vote_data
        })
        logger.debug(f"Created Vote node for vote #{vote.vote_number}")

        # Create Ballot nodes
        ballots_data = []
        mp_link_data = []

        for ballot in vote.ballots:
            ballot_id = f"{vote.vote_number}-{ballot.person_id}"

            ballot_props = {
                "id": ballot_id,
                "vote_number": vote.vote_number,
                "person_id": ballot.person_id,
                "vote_value": ballot.vote_value,
                "is_yea": ballot.is_yea,
                "is_nay": ballot.is_nay,
                "is_paired": ballot.is_paired,
                "person_first_name": ballot.person_first_name,
                "person_last_name": ballot.person_last_name,
                "constituency_name": ballot.constituency_name,
                "province_territory": ballot.province_territory,
                "caucus_short_name": ballot.caucus_short_name,
                "updated_at": datetime.utcnow().isoformat(),
            }

            if ballot.person_salutation:
                ballot_props["person_salutation"] = ballot.person_salutation

            ballots_data.append(ballot_props)

            # Track for MP linking (person_id -> parl_mp_id)
            mp_link_data.append({
                "ballot_id": ballot_id,
                "person_id": ballot.person_id
            })

        # Batch create ballots
        if ballots_data:
            cypher = """
                UNWIND $ballots AS ballot
                MERGE (b:Ballot {id: ballot.id})
                SET b = ballot
                SET b.updated_at = datetime()
            """
            self.neo4j.run_query(cypher, {"ballots": ballots_data})
            logger.debug(f"Created {len(ballots_data)} Ballot nodes")

            # Link ballots to vote
            cypher = """
                MATCH (v:Vote {vote_number: $vote_number})
                MATCH (b:Ballot)
                WHERE b.vote_number = $vote_number
                MERGE (b)-[:CAST_IN]->(v)
            """
            self.neo4j.run_query(cypher, {"vote_number": vote.vote_number})
            logger.debug(f"Linked {len(ballots_data)} ballots to vote")

            # Link ballots to MPs using person_id
            if mp_link_data:
                self._link_ballots_to_mps(mp_link_data)

            # Link vote to Bill if applicable
            if vote.bill_number:
                self._link_vote_to_bill(vote.vote_number, vote.bill_number)

        return len(ballots_data)

    def _link_ballots_to_mps(self, link_data: List[Dict[str, Any]]) -> None:
        """
        Link ballots to MPs using person_id.

        This uses the stable House of Commons person database ID to match
        ballots to MPs, which is the same ID used in Hansard.
        """
        if not link_data:
            return

        # Link using person_id -> parl_mp_id
        link_query = """
        UNWIND $links AS link
        MATCH (b:Ballot {id: link.ballot_id})
        MATCH (mp:MP {parl_mp_id: link.person_id})
        MERGE (b)-[:CAST_BY]->(mp)
        """

        result = self.neo4j.run_query(link_query, {"links": link_data})
        logger.debug(f"Linked {len(link_data)} ballots to MPs using person_id")

    def _link_vote_to_bill(self, vote_number: int, bill_number: str) -> None:
        """Link a vote to a bill if the bill exists in Neo4j."""
        if not bill_number:
            return

        # Try to find the bill (bills are stored with various formats)
        # Try exact match first, then case-insensitive
        link_query = """
        MATCH (v:Vote {vote_number: $vote_number})
        MATCH (bill:Bill)
        WHERE bill.number = $bill_number
           OR toLower(bill.number) = toLower($bill_number)
           OR bill.code = $bill_number
           OR toLower(bill.code) = toLower($bill_number)
        MERGE (v)-[:CONCERNS]->(bill)
        RETURN count(*) as linked
        """

        result = self.neo4j.run_query(link_query, {
            "vote_number": vote_number,
            "bill_number": bill_number
        })

        if result and result[0]['linked'] > 0:
            logger.debug(f"Linked vote #{vote_number} to Bill {bill_number}")
        else:
            logger.debug(f"Bill {bill_number} not found in Neo4j for vote #{vote_number}")

    def import_recent_votes(self, days: int = 30) -> Dict[str, int]:
        """
        Import votes from the last N days.

        Args:
            days: Number of days to look back

        Returns:
            Dict with import statistics
        """
        from datetime import timedelta

        cutoff_date = datetime.now() - timedelta(days=days)
        logger.info(f"Importing votes since {cutoff_date.strftime('%Y-%m-%d')}...")

        stats = {
            "votes": 0,
            "ballots": 0,
            "skipped": 0,
            "errors": 0
        }

        # Get all vote summaries
        summaries = self.votes_client.get_vote_summaries()

        # Filter by date
        recent_summaries = [
            s for s in summaries
            if datetime.fromisoformat(s.date_time.replace('T', ' ')) >= cutoff_date
        ]

        logger.info(f"Found {len(recent_summaries)} votes since {cutoff_date.strftime('%Y-%m-%d')}")

        if not recent_summaries:
            return stats

        # Import each vote
        tracker = ProgressTracker(
            total=len(recent_summaries),
            desc="Importing recent votes"
        )

        for summary in recent_summaries:
            try:
                # Fetch detailed vote
                vote = self.votes_client.get_vote(
                    summary.parliament_number,
                    summary.session_number,
                    summary.vote_number,
                    include_metadata=True
                )

                # Import to Neo4j
                ballot_count = self._import_vote(vote)
                stats["votes"] += 1
                stats["ballots"] += ballot_count

                tracker.update(1)

            except Exception as e:
                logger.error(f"Error importing vote {summary.vote_number}: {e}")
                stats["errors"] += 1
                tracker.update(1)
                continue

        tracker.close()

        logger.success(f"✅ Imported {stats['votes']} votes, {stats['ballots']} ballots")
        if stats["errors"] > 0:
            logger.warning(f"⚠️  {stats['errors']} errors occurred")

        return stats
