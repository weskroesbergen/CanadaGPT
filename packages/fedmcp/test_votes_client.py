#!/usr/bin/env python3
"""
Test script to demonstrate Votes XML extraction.

This script fetches recent parliamentary votes and displays:
- Vote metadata (number, date, subject, result)
- Individual MP ballots with person IDs for linking
- Statistics on metadata capture
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fedmcp.clients.ourcommons_votes import OurCommonsVotesClient


def main():
    print("=" * 70)
    print("Votes XML Extraction Test")
    print("=" * 70)
    print()

    client = OurCommonsVotesClient()

    print("Fetching recent votes...")
    try:
        summaries = client.get_recent_votes(limit=5)
    except Exception as e:
        print(f"❌ Error fetching votes: {e}")
        return

    print(f"✅ Found {len(summaries)} recent votes")
    print()

    # Display recent votes
    print("📊 Recent Votes")
    print("-" * 70)
    for summary in summaries:
        print(f"Vote #{summary.vote_number} - {summary.date_time}")
        print(f"  Subject: {summary.subject}")
        print(f"  Result: {summary.result}")
        print(f"  Yeas: {summary.num_yeas}, Nays: {summary.num_nays}, Paired: {summary.num_paired}")
        if summary.bill_number:
            print(f"  Bill: {summary.bill_number}")
        if summary.vote_type:
            print(f"  Type: {summary.vote_type}")
        print()

    # Fetch detailed vote with ballots
    if summaries:
        latest = summaries[0]
        print(f"📋 Detailed Vote: #{latest.vote_number}")
        print("-" * 70)

        try:
            vote = client.get_vote(
                latest.parliament_number,
                latest.session_number,
                latest.vote_number,
                include_metadata=True
            )
        except Exception as e:
            print(f"❌ Error fetching detailed vote: {e}")
            return

        print(f"Parliament: {vote.parliament_number}, Session: {vote.session_number}")
        print(f"Date: {vote.date_time}")
        print(f"Subject: {vote.subject}")
        print(f"Result: {vote.result}")
        print(f"Bill: {vote.bill_number or 'N/A'}")
        print()
        print(f"Ballots: {len(vote.ballots)} total")
        print(f"  Yeas: {vote.num_yeas}")
        print(f"  Nays: {vote.num_nays}")
        print(f"  Paired: {vote.num_paired}")
        print()

        # Show sample ballots
        print("Sample Ballots:")
        for ballot in vote.ballots[:5]:
            print(f"  {ballot.person_salutation} {ballot.person_first_name} {ballot.person_last_name}")
            print(f"    PersonId: {ballot.person_id} ✅")
            print(f"    Constituency: {ballot.constituency_name}")
            print(f"    Party: {ballot.caucus_short_name}")
            print(f"    Vote: {ballot.vote_value}")
            print()

        # Statistics
        print("📊 Metadata Capture Statistics")
        print("-" * 70)
        person_ids = sum(1 for b in vote.ballots if b.person_id > 0)
        percentage = (person_ids / len(vote.ballots) * 100) if vote.ballots else 0
        print(f"PersonId (for MP linking): {person_ids}/{len(vote.ballots)} ({percentage:.1f}%) {'✅' if percentage > 95 else '⚠️'}")

        constituencies = sum(1 for b in vote.ballots if b.constituency_name)
        percentage = (constituencies / len(vote.ballots) * 100) if vote.ballots else 0
        print(f"Constituency:              {constituencies}/{len(vote.ballots)} ({percentage:.1f}%) {'✅' if percentage > 95 else '⚠️'}")

        parties = sum(1 for b in vote.ballots if b.caucus_short_name)
        percentage = (parties / len(vote.ballots) * 100) if vote.ballots else 0
        print(f"Party:                     {parties}/{len(vote.ballots)} ({percentage:.1f}%) {'✅' if percentage > 95 else '⚠️'}")

    print()
    print("=" * 70)
    print("✅ Votes XML extraction successful!")
    print("=" * 70)


if __name__ == "__main__":
    main()
