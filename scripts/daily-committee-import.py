#!/usr/bin/env python3
"""Daily committee meeting import job - discovers and imports new committee meetings."""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import re
import requests
from bs4 import BeautifulSoup

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'packages' / 'data-pipeline'))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger


def parse_meeting_html(html: str, meeting_date: str) -> List[Dict[str, Any]]:
    """Parse FilteredMeetings HTML to extract meeting metadata."""
    soup = BeautifulSoup(html, 'html.parser')
    meetings = []

    # Find all meeting items
    meeting_items = soup.find_all('div', class_=re.compile(r'accordion-item meeting-item'))

    logger.info(f"Found {len(meeting_items)} meeting items in HTML")

    for item in meeting_items:
        try:
            # Extract meeting ID from element ID
            meeting_id_match = re.search(r'meeting-item-(\d+)', item.get('id', ''))
            if not meeting_id_match:
                continue

            meeting_id = meeting_id_match.group(1)

            # Extract committee acronym
            acronym_elem = item.find('span', class_='meeting-acronym')
            if not acronym_elem:
                continue

            committee_acronym = acronym_elem.text.strip()

            # Extract time
            time_elem = item.find('div', class_='the-time')
            time_str = time_elem.text.strip() if time_elem else ""

            # Extract subject/bill
            subject_elem = item.find('div', class_='studies-activities-item')
            subject = subject_elem.text.strip() if subject_elem else ""

            # Extract status
            status_elem = item.find('div', class_='meeting-card-meeting-status')
            status = status_elem.text.strip() if status_elem else "Unknown"

            # Check for webcast
            webcast = bool(item.find('i', class_='icon-web-video-cast'))

            meeting = {
                'meeting_id': meeting_id,
                'committee_acronym': committee_acronym,
                'date': meeting_date,
                'time_str': time_str,
                'subject': subject,
                'status': status,
                'webcast': webcast,
            }

            meetings.append(meeting)

        except Exception as e:
            logger.warning(f"Error parsing meeting item: {e}")
            continue

    return meetings


def fetch_meetings_for_date(date_str: str) -> List[Dict[str, Any]]:
    """Fetch committee meetings for a specific date using FilteredMeetings endpoint."""
    url = f"https://www.ourcommons.ca/committees/en/FilteredMeetings?meetingDate={date_str}"

    try:
        logger.info(f"Fetching meetings for {date_str}: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        meetings = parse_meeting_html(response.text, date_str)
        logger.info(f"Found {len(meetings)} meetings on {date_str}")

        return meetings

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching meetings for {date_str}: {e}")
        return []


def import_meeting_to_neo4j(neo4j: Neo4jClient, meeting: Dict[str, Any]):
    """Import or update a meeting in Neo4j."""

    # Check if meeting already exists
    check_query = """
        MATCH (m:Meeting {ourcommons_meeting_id: $meeting_id})
        RETURN m.ourcommons_meeting_id as id
    """
    result = neo4j.run_query(check_query, {"meeting_id": meeting['meeting_id']})

    if result and len(result) > 0:
        logger.info(f"Meeting {meeting['meeting_id']} already exists, skipping")
        return False

    # Ensure committee exists
    committee_query = """
        MERGE (c:Committee {code: $code})
        ON CREATE SET c.created_at = datetime()
        RETURN c.code as code
    """
    neo4j.run_query(committee_query, {"code": meeting['committee_acronym']})

    # Create meeting node
    meeting_data = {
        'ourcommons_meeting_id': meeting['meeting_id'],
        'committee_code': meeting['committee_acronym'],
        'date': meeting['date'],
        'time_description': meeting['time_str'],
        'subject': meeting['subject'],
        'status': meeting['status'],
        'webcast_available': meeting['webcast'],
        'source': 'ourcommons_filtered_meetings',
        'imported_at': datetime.utcnow().isoformat(),
    }

    # Parse meeting number if available (will be null initially)
    meeting_data['number'] = None

    create_query = """
        CREATE (m:Meeting)
        SET m = $meeting_data
        SET m.created_at = datetime()

        WITH m
        MATCH (c:Committee {code: $committee_code})
        MERGE (c)-[:HELD_MEETING]->(m)

        RETURN m.ourcommons_meeting_id as id
    """

    result = neo4j.run_query(create_query, {
        "meeting_data": meeting_data,
        "committee_code": meeting['committee_acronym']
    })

    logger.success(f"✓ Created Meeting {meeting['meeting_id']} for {meeting['committee_acronym']}")
    return True


def check_and_import_recent_meetings(neo4j: Neo4jClient, lookback_days: int = 7):
    """Check for and import any missing committee meetings from the last N days."""
    imported_count = 0

    # Get dates to check (last N days, including weekends since committees can meet then)
    dates_to_check = []
    for i in range(lookback_days, -1, -1):
        date = datetime.now() - timedelta(days=i)
        dates_to_check.append(date.strftime('%Y-%m-%d'))

    logger.info(f"Checking for committee meetings on {len(dates_to_check)} dates")
    logger.info(f"Date range: {dates_to_check[0]} to {dates_to_check[-1]}")

    # Fetch meetings for each date
    for date_str in dates_to_check:
        meetings = fetch_meetings_for_date(date_str)

        for meeting in meetings:
            try:
                if import_meeting_to_neo4j(neo4j, meeting):
                    imported_count += 1
            except Exception as e:
                logger.error(f"Failed to import meeting {meeting.get('meeting_id')}: {e}")

    return imported_count


def main():
    """Main entry point for daily committee import job."""
    logger.info("=" * 80)
    logger.info("DAILY COMMITTEE MEETING IMPORT JOB")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("=" * 80)

    # Get Neo4j connection from environment
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://10.128.0.3:7687')
    neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD')

    if not neo4j_password:
        logger.error("NEO4J_PASSWORD environment variable not set")
        sys.exit(1)

    neo4j = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)

    try:
        # Check for meetings from last 7 days
        imported = check_and_import_recent_meetings(neo4j, lookback_days=7)

        logger.info("=" * 80)
        if imported > 0:
            logger.success(f"✅ Successfully imported {imported} new committee meeting(s)")
        else:
            logger.info("ℹ️  No new committee meetings found")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Job failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        neo4j.close()


if __name__ == "__main__":
    main()
