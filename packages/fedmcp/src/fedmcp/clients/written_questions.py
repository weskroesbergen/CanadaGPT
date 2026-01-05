"""Client for scraping Written Questions from House of Commons website."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

from bs4 import BeautifulSoup
from fedmcp.http import RateLimitedSession


BASE_URL = "https://www.ourcommons.ca/written-questions"


@dataclass
class WrittenQuestion:
    """Represents a Written Question from OurCommons."""

    question_number: str  # "Q-1", "Q-762"
    parliament_number: int  # 45
    session_number: int  # 1
    date_asked: Optional[str] = None  # "2025-05-27" ISO format
    asker_name: str = ""
    asker_constituency: str = ""
    responding_department: str = ""
    status: str = ""  # "Awaiting response", "Answered"
    due_date: Optional[str] = None  # ISO format
    answer_date: Optional[str] = None  # ISO format
    sessional_paper: Optional[str] = None  # "8555-451-1"
    question_text_preview: Optional[str] = None  # Truncated text from list
    topics: List[str] = field(default_factory=list)
    ourcommons_url: str = ""

    @property
    def session_id(self) -> str:
        """Returns session ID in format '45-1'."""
        return f"{self.parliament_number}-{self.session_number}"

    @property
    def id(self) -> str:
        """Unique identifier for this question."""
        # Normalize question number to just the number part
        num = self.question_number.upper().replace('Q-', '').replace('Q', '')
        return f"wq-{self.session_id}-{num}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Neo4j."""
        return {
            'id': self.id,
            'question_number': self.question_number,
            'parliament_number': self.parliament_number,
            'session_number': self.session_number,
            'session_id': self.session_id,
            'date_asked': self.date_asked,
            'asker_name': self.asker_name,
            'asker_constituency': self.asker_constituency,
            'responding_department': self.responding_department,
            'status': self.status,
            'due_date': self.due_date,
            'answer_date': self.answer_date,
            'sessional_paper': self.sessional_paper,
            'topics': self.topics,
            'ourcommons_url': self.ourcommons_url,
        }


class WrittenQuestionsClient:
    """Client for scraping Written Questions from House of Commons."""

    def __init__(
        self,
        *,
        session: Optional[RateLimitedSession] = None,
        min_request_interval: float = 0.5  # 2 req/sec rate limit
    ) -> None:
        self.session = session or RateLimitedSession(
            min_request_interval=min_request_interval
        )
        self.base_url = BASE_URL

    def list_questions(
        self,
        parliament_session: str = "45-1",
        status: Optional[str] = None,  # "answered", "awaiting"
        limit: Optional[int] = None,
    ) -> List[WrittenQuestion]:
        """
        Fetch all written questions, handling pagination.

        Args:
            parliament_session: Session ID (e.g., "45-1")
            status: Filter by status ("answered" or "awaiting")
            limit: Max questions to return

        Returns:
            List of WrittenQuestion objects
        """
        questions = []
        page = 1

        while True:
            page_questions = self._fetch_page(
                parliament_session,
                page,
                status
            )

            if not page_questions:
                break

            questions.extend(page_questions)

            if limit and len(questions) >= limit:
                return questions[:limit]

            page += 1

        return questions

    def _fetch_page(
        self,
        parliament_session: str,
        page: int,
        status: Optional[str]
    ) -> List[WrittenQuestion]:
        """Fetch a single page of questions."""
        url = f"{self.base_url}/questions"
        params = {
            'ParliamentSession': parliament_session,
            'Page': str(page),
        }
        if status:
            # Map to OurCommons filter format
            if status.lower() == 'answered':
                params['Status'] = 'Answered'
            elif status.lower() in ('awaiting', 'unanswered'):
                params['Status'] = 'AwaitingResponse'

        response = self.session.get(url, params=params)
        response.raise_for_status()

        return self._parse_list_page(response.text, parliament_session)

    def _parse_list_page(
        self,
        html: str,
        parliament_session: str
    ) -> List[WrittenQuestion]:
        """Parse question list from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        questions = []

        # Parse parliament/session from parameter
        parts = parliament_session.split('-')
        parliament_number = int(parts[0])
        session_number = int(parts[1])

        # Find question cards - they are <a> elements linking to question detail pages
        # Pattern: /written-questions/45-1/q-762
        question_links = soup.find_all('a', href=re.compile(rf'/written-questions/{parliament_session}/q-\d+', re.IGNORECASE))

        for link in question_links:
            question = self._parse_question_from_list(
                link,
                parliament_number,
                session_number,
                parliament_session
            )
            if question:
                questions.append(question)

        return questions

    def _parse_question_from_list(
        self,
        card_link,
        parliament: int,
        session: int,
        parliament_session: str
    ) -> Optional[WrittenQuestion]:
        """Parse individual question from list card.

        HTML Structure:
        <a class="question-tile-container" href="/written-questions/45-1/q-762">
          <div class="question-tile">
            <div class="top-section">
              <h3 class="question-number">Q-762</h3>
              <div class="row attributes">
                <div class="attribute">
                  <div class="label">Date asked</div>
                  <div class="value">December 10, 2025</div>
                </div>
              </div>
              <div class="question-text">...</div>
            </div>
            <div class="bottom-section">
              <div class="row attributes">
                <div class="attribute">
                  <div class="label">Asked by</div>
                  <div class="value">Leah Gazan</div>
                </div>
              </div>
              <div class="row attributes status awaitingresponse">
                <div class="attribute">
                  <div class="label">Awaiting response</div>
                  <div class="value">N/A</div>
                </div>
              </div>
            </div>
          </div>
        </a>
        """
        try:
            href = card_link.get('href', '')

            # Extract question number from URL (most reliable)
            url_match = re.search(r'/q-(\d+)', href, re.IGNORECASE)
            if not url_match:
                return None
            question_number = f"Q-{url_match.group(1)}"

            # Build full URL
            if href.startswith('/'):
                url = f"https://www.ourcommons.ca{href}"
            else:
                url = href

            date_asked = None
            status = ""
            asker_name = ""

            # Extract data using CSS class selectors
            # Find all attribute sections with label/value pairs
            attributes = card_link.find_all('div', class_='attribute')

            for attr in attributes:
                label_elem = attr.find('div', class_='label')
                value_elem = attr.find('div', class_='value')

                if label_elem and value_elem:
                    label = label_elem.get_text(strip=True).lower()
                    value = value_elem.get_text(strip=True)

                    if 'date asked' in label:
                        # Parse date
                        try:
                            date_parsed = datetime.strptime(value, '%B %d, %Y')
                            date_asked = date_parsed.strftime('%Y-%m-%d')
                        except ValueError:
                            pass
                    elif 'asked by' in label:
                        asker_name = value

            # Extract status from the status row
            status_row = card_link.find('div', class_='status')
            if status_row:
                label_elem = status_row.find('div', class_='label')
                if label_elem:
                    status = label_elem.get_text(strip=True)

            # Fallback: if no structured data found, try text patterns
            if not asker_name:
                card_text = card_link.get_text(separator='\n', strip=True)
                mp_match = re.search(r'Asked\s+by\s*\n?\s*([^\n]+)', card_text)
                if mp_match:
                    asker_name = mp_match.group(1).strip()

            if not status:
                card_text = card_link.get_text(strip=True)
                status_keywords = ['Awaiting response', 'Answered', 'Withdrawn', 'Transferred']
                for keyword in status_keywords:
                    if keyword.lower() in card_text.lower():
                        status = keyword
                        break

            return WrittenQuestion(
                question_number=question_number,
                parliament_number=parliament,
                session_number=session,
                date_asked=date_asked,
                asker_name=asker_name,
                status=status,
                ourcommons_url=url,
            )

        except Exception as e:
            # Silently skip malformed cards
            return None

    def get_question_details(
        self,
        parliament_session: str,
        question_number: str
    ) -> Optional[WrittenQuestion]:
        """
        Fetch detailed information for a single question.

        Args:
            parliament_session: e.g., "45-1"
            question_number: e.g., "Q-1" or "q-1" or "1"

        Returns:
            WrittenQuestion with full details
        """
        # Normalize question number
        q_num = str(question_number).lower().replace('q-', '').replace('q', '')
        url = f"{self.base_url}/{parliament_session}/q-{q_num}"

        response = self.session.get(url)
        response.raise_for_status()

        return self._parse_detail_page(response.text, parliament_session, q_num, url)

    def _parse_detail_page(
        self,
        html: str,
        parliament_session: str,
        q_num: str,
        source_url: str
    ) -> Optional[WrittenQuestion]:
        """Parse detailed question page."""
        soup = BeautifulSoup(html, 'html.parser')

        # Parse parliament/session
        parts = parliament_session.split('-')
        parliament_number = int(parts[0])
        session_number = int(parts[1])

        question_number = f"Q-{q_num}"

        # Extract various metadata
        date_asked = None
        answer_date = None
        status = ""
        asker_name = ""
        asker_constituency = ""
        responding_department = ""
        sessional_paper = None
        topics = []

        # Look for metadata in the page
        # Common patterns: definition lists, metadata tables, or labeled spans

        # Try to find date asked
        date_elem = soup.find('time')
        if date_elem:
            datetime_attr = date_elem.get('datetime')
            if datetime_attr:
                date_asked = datetime_attr[:10]

        # Look for "Asked by" or MP link
        mp_link = soup.find('a', href=re.compile(r'/members/'))
        if mp_link:
            asker_name = mp_link.get_text(strip=True)
            # Check for constituency in parent text
            parent_text = mp_link.find_parent().get_text() if mp_link.find_parent() else ""
            const_match = re.search(r'\(([^)]+)\)', parent_text)
            if const_match:
                asker_constituency = const_match.group(1)

        # Look for responding department/minister
        dept_patterns = [
            re.compile(r'minister\s+of\s+[\w\s]+', re.IGNORECASE),
            re.compile(r'responding\s+(?:minister|department|ministry)', re.IGNORECASE),
        ]
        for pattern in dept_patterns:
            dept_match = soup.find(string=pattern)
            if dept_match:
                responding_department = dept_match.strip()
                break

        # Look for status
        status_patterns = ['Awaiting response', 'Answered', 'Withdrawn']
        for s in status_patterns:
            if soup.find(string=re.compile(s, re.IGNORECASE)):
                status = s
                break

        # Look for answer date (if answered)
        answer_patterns = [
            re.compile(r'answered[:\s]+(\w+ \d+, \d{4})', re.IGNORECASE),
            re.compile(r'response\s+date[:\s]+(\w+ \d+, \d{4})', re.IGNORECASE),
        ]
        page_text = soup.get_text()
        for pattern in answer_patterns:
            match = pattern.search(page_text)
            if match:
                try:
                    answer_parsed = datetime.strptime(match.group(1), '%B %d, %Y')
                    answer_date = answer_parsed.strftime('%Y-%m-%d')
                except ValueError:
                    pass
                break

        # Look for sessional paper reference (e.g., "8555-451-1")
        paper_match = re.search(r'8555-\d+-\d+', page_text)
        if paper_match:
            sessional_paper = paper_match.group()

        # Look for topics (usually in tag links or a topics section)
        topic_links = soup.find_all('a', href=re.compile(r'topic'))
        for topic_link in topic_links:
            topic_text = topic_link.get_text(strip=True)
            if topic_text and topic_text not in topics:
                topics.append(topic_text)

        return WrittenQuestion(
            question_number=question_number,
            parliament_number=parliament_number,
            session_number=session_number,
            date_asked=date_asked,
            asker_name=asker_name,
            asker_constituency=asker_constituency,
            responding_department=responding_department,
            status=status,
            answer_date=answer_date,
            sessional_paper=sessional_paper,
            topics=topics,
            ourcommons_url=source_url,
        )

    def get_question_count(self, parliament_session: str = "45-1") -> int:
        """
        Get total count of questions in a session.

        Args:
            parliament_session: Session ID (e.g., "45-1")

        Returns:
            Total number of questions
        """
        url = f"{self.base_url}/questions"
        params = {'ParliamentSession': parliament_session}

        response = self.session.get(url, params=params)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for "Results X of Y" or similar count text
        count_match = re.search(r'of\s+(\d+)', soup.get_text())
        if count_match:
            return int(count_match.group(1))

        return 0
