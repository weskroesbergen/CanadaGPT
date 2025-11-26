"""Helpers for fetching Votes XML exports from the House of Commons."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

from fedmcp.http import RateLimitedSession


VOTES_BASE = "https://www.ourcommons.ca/Members/en/votes"


@dataclass
class Ballot:
    """A single MP's ballot in a vote."""

    person_id: int  # House of Commons person database ID
    person_first_name: str
    person_last_name: str
    person_salutation: Optional[str]
    constituency_name: str
    province_territory: str
    caucus_short_name: str
    vote_value: str  # "Yea", "Nay", or "Paired"
    is_yea: bool
    is_nay: bool
    is_paired: bool


@dataclass
class Vote:
    """A single parliamentary vote with all ballots."""

    parliament_number: int
    session_number: int
    vote_number: int  # DecisionDivisionNumber
    date_time: str  # ISO format
    result: str  # "Agreed To", "Negatived"
    subject: Optional[str] = None
    bill_number: Optional[str] = None
    vote_type: Optional[str] = None  # DecisionDivisionDocumentTypeName
    vote_type_id: Optional[int] = None  # DecisionDivisionDocumentTypeId
    num_yeas: int = 0
    num_nays: int = 0
    num_paired: int = 0
    ballots: List[Ballot] = field(default_factory=list)


@dataclass
class VoteSummary:
    """Summary of a vote from the bulk XML (without individual ballots)."""

    parliament_number: int
    session_number: int
    vote_number: int
    date_time: str
    subject: str
    result: str
    num_yeas: int
    num_nays: int
    num_paired: int
    vote_type: Optional[str] = None
    vote_type_id: Optional[int] = None
    bill_number: Optional[str] = None


class OurCommonsVotesClient:
    """Retrieve and parse Commons Votes XML exports."""

    def __init__(
        self,
        *,
        session: Optional[RateLimitedSession] = None,
    ) -> None:
        self.session = session or RateLimitedSession()

    # ------------------------------------------------------------------
    # Fetch helpers
    # ------------------------------------------------------------------
    def fetch_bulk_votes_xml(self) -> str:
        """Fetch the bulk votes XML with all vote summaries (no ballots)."""
        url = f"{VOTES_BASE}/xml"
        response = self.session.get(url, headers={"Accept": "application/xml"})
        response.raise_for_status()
        return response.content.decode('utf-8-sig')

    def fetch_vote_xml(
        self,
        parliament: int,
        session: int,
        vote_number: int
    ) -> str:
        """Fetch XML for a single vote with all ballots."""
        url = f"{VOTES_BASE}/{parliament}/{session}/{vote_number}/xml"
        response = self.session.get(url, headers={"Accept": "application/xml"})
        response.raise_for_status()
        return response.content.decode('utf-8-sig')

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------
    def parse_bulk_votes(self, xml_text: str) -> List[VoteSummary]:
        """Parse bulk votes XML into vote summaries (no ballots)."""
        from xml.etree import ElementTree as ET

        # Strip UTF-8 BOM if present
        if xml_text.startswith('\ufeff'):
            xml_text = xml_text[1:]

        root = ET.fromstring(xml_text)

        summaries = []
        for vote_el in root.findall("Vote"):
            parliament = int(vote_el.findtext("ParliamentNumber", "0"))
            session = int(vote_el.findtext("SessionNumber", "0"))
            vote_num = int(vote_el.findtext("DecisionDivisionNumber", "0"))
            date_time = vote_el.findtext("DecisionEventDateTime", "")
            subject = vote_el.findtext("DecisionDivisionSubject", "")
            result = vote_el.findtext("DecisionResultName", "")
            num_yeas = int(vote_el.findtext("DecisionDivisionNumberOfYeas", "0"))
            num_nays = int(vote_el.findtext("DecisionDivisionNumberOfNays", "0"))
            num_paired = int(vote_el.findtext("DecisionDivisionNumberOfPaired", "0"))
            vote_type = vote_el.findtext("DecisionDivisionDocumentTypeName")
            vote_type_id_str = vote_el.findtext("DecisionDivisionDocumentTypeId")
            vote_type_id = int(vote_type_id_str) if vote_type_id_str else None
            bill_number = vote_el.findtext("BillNumberCode") or None

            summaries.append(VoteSummary(
                parliament_number=parliament,
                session_number=session,
                vote_number=vote_num,
                date_time=date_time,
                subject=subject,
                result=result,
                num_yeas=num_yeas,
                num_nays=num_nays,
                num_paired=num_paired,
                vote_type=vote_type,
                vote_type_id=vote_type_id,
                bill_number=bill_number
            ))

        return summaries

    def parse_vote(self, xml_text: str) -> Vote:
        """Parse a single vote XML with all ballots."""
        from xml.etree import ElementTree as ET

        # Strip UTF-8 BOM if present
        if xml_text.startswith('\ufeff'):
            xml_text = xml_text[1:]

        root = ET.fromstring(xml_text)

        # Parse ballot elements
        ballots = []
        parliament = 0
        session = 0
        vote_number = 0
        date_time = ""
        result = ""

        for participant_el in root.findall("VoteParticipant"):
            # Get vote-level info from first participant
            if not parliament:
                parliament = int(participant_el.findtext("ParliamentNumber", "0"))
                session = int(participant_el.findtext("SessionNumber", "0"))
                vote_number = int(participant_el.findtext("DecisionDivisionNumber", "0"))
                date_time = participant_el.findtext("DecisionEventDateTime", "")
                result = participant_el.findtext("DecisionResultName", "")

            # Parse ballot info
            person_id = int(participant_el.findtext("PersonId", "0"))
            first_name = participant_el.findtext("PersonOfficialFirstName", "")
            last_name = participant_el.findtext("PersonOfficialLastName", "")
            salutation = participant_el.findtext("PersonShortSalutation")
            constituency = participant_el.findtext("ConstituencyName", "")
            province = participant_el.findtext("ConstituencyProvinceTerritoryName", "")
            caucus = participant_el.findtext("CaucusShortName", "")
            vote_value = participant_el.findtext("VoteValueName", "")
            is_yea = participant_el.findtext("IsVoteYea", "false").lower() == "true"
            is_nay = participant_el.findtext("IsVoteNay", "false").lower() == "true"
            is_paired = participant_el.findtext("IsVotePaired", "false").lower() == "true"

            ballots.append(Ballot(
                person_id=person_id,
                person_first_name=first_name,
                person_last_name=last_name,
                person_salutation=salutation,
                constituency_name=constituency,
                province_territory=province,
                caucus_short_name=caucus,
                vote_value=vote_value,
                is_yea=is_yea,
                is_nay=is_nay,
                is_paired=is_paired
            ))

        # Calculate counts from ballots
        num_yeas = sum(1 for b in ballots if b.is_yea)
        num_nays = sum(1 for b in ballots if b.is_nay)
        num_paired = sum(1 for b in ballots if b.is_paired)

        # Note: We don't have subject or bill info in individual vote XML,
        # those come from the bulk XML. Caller should merge if needed.
        return Vote(
            parliament_number=parliament,
            session_number=session,
            vote_number=vote_number,
            date_time=date_time,
            result=result,
            ballots=ballots,
            num_yeas=num_yeas,
            num_nays=num_nays,
            num_paired=num_paired
        )

    # ------------------------------------------------------------------
    # Convenience API
    # ------------------------------------------------------------------
    def get_vote_summaries(self) -> List[VoteSummary]:
        """Get all vote summaries from bulk XML (no ballots)."""
        xml = self.fetch_bulk_votes_xml()
        return self.parse_bulk_votes(xml)

    def get_vote(
        self,
        parliament: int,
        session: int,
        vote_number: int,
        include_metadata: bool = True
    ) -> Vote:
        """
        Get a single vote with all ballots.

        Args:
            parliament: Parliament number (e.g., 45)
            session: Session number (e.g., 1)
            vote_number: Vote/division number
            include_metadata: If True, fetch bulk XML to get subject/bill info

        Returns:
            Vote object with ballots and optional metadata
        """
        xml = self.fetch_vote_xml(parliament, session, vote_number)
        vote = self.parse_vote(xml)

        # Enrich with metadata from bulk XML if requested
        if include_metadata:
            summaries = self.get_vote_summaries()
            matching = [
                s for s in summaries
                if s.parliament_number == parliament
                and s.session_number == session
                and s.vote_number == vote_number
            ]
            if matching:
                summary = matching[0]
                vote.subject = summary.subject
                vote.bill_number = summary.bill_number
                vote.vote_type = summary.vote_type
                vote.vote_type_id = summary.vote_type_id

        return vote

    def get_recent_votes(self, limit: int = 50) -> List[VoteSummary]:
        """
        Get the most recent vote summaries.

        Args:
            limit: Maximum number of votes to return

        Returns:
            List of vote summaries, most recent first
        """
        summaries = self.get_vote_summaries()
        # Sort by date descending
        summaries.sort(
            key=lambda v: datetime.fromisoformat(v.date_time.replace('T', ' ')),
            reverse=True
        )
        return summaries[:limit]
