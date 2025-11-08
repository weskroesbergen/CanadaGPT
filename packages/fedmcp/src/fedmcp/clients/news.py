"""Client for fetching news articles about MPs from Canadian news sources."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urlencode

from fedmcp.http import RateLimitedSession


class NewsClient:
    """
    Fetch news articles mentioning Canadian politicians.

    Uses Google News RSS feeds which are free and don't require an API key.
    Focuses on Canadian news sources for relevant political coverage.
    """

    # Canadian news sources for filtering
    CANADIAN_SOURCES = [
        "cbc.ca",
        "globalnews.ca",
        "ctvnews.ca",
        "theglobeandmail.com",
        "nationalpost.com",
        "thestar.com",
        "hilltimes.com",
        "macleans.ca",
        "winnipegfreepress.com",
        "calgaryherald.com",
        "montrealgazette.com",
        "ottawacitizen.com",
    ]

    def __init__(
        self,
        *,
        session: Optional[RateLimitedSession] = None,
    ) -> None:
        self.session = session or RateLimitedSession()

    def search_mp_news(
        self,
        mp_name: str,
        *,
        limit: int = 10,
        days_back: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Search for news articles mentioning an MP.

        Args:
            mp_name: Full name of the MP
            limit: Maximum number of articles to return
            days_back: How many days back to search (not enforced by Google News RSS)

        Returns:
            List of article dictionaries with keys:
            - title: Article title
            - url: Article URL
            - source: News source domain
            - published_date: Publication date
            - description: Article snippet/description
        """
        # Build search query
        # Add "Canada" and "MP" to improve relevance
        search_query = f'"{mp_name}" MP Canada'

        # Google News RSS feed URL
        base_url = "https://news.google.com/rss/search"
        params = {
            "q": search_query,
            "hl": "en-CA",  # Canadian English
            "gl": "CA",     # Canada region
            "ceid": "CA:en",
        }

        url = f"{base_url}?{urlencode(params)}"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            # Parse RSS XML
            articles = self._parse_rss(response.text, limit=limit)

            # Filter to Canadian sources if possible
            filtered = [
                article for article in articles
                if any(source in article["url"].lower() for source in self.CANADIAN_SOURCES)
            ]

            # If we filtered out too many, fall back to unfiltered results
            if len(filtered) < min(5, limit) and len(articles) > len(filtered):
                return articles[:limit]

            return filtered[:limit]

        except Exception as e:
            # Return empty list on error, but log it
            print(f"Error fetching news for {mp_name}: {e}")
            return []

    def _parse_rss(self, rss_content: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Parse Google News RSS feed XML."""
        articles = []

        try:
            root = ET.fromstring(rss_content)

            # Google News RSS structure: <rss><channel><item>...</item></channel></rss>
            for item in root.findall(".//item")[:limit]:
                title_elem = item.find("title")
                link_elem = item.find("link")
                pub_date_elem = item.find("pubDate")
                description_elem = item.find("description")
                source_elem = item.find("source")

                # Extract data
                title = title_elem.text if title_elem is not None else "No title"
                url = link_elem.text if link_elem is not None else ""
                description = description_elem.text if description_elem is not None else ""
                source = source_elem.text if source_elem is not None else self._extract_source_from_url(url)

                # Parse date
                published_date = None
                if pub_date_elem is not None and pub_date_elem.text:
                    try:
                        # Google News RSS uses RFC 822 format
                        # Example: "Wed, 01 Nov 2025 12:00:00 GMT"
                        published_date = datetime.strptime(
                            pub_date_elem.text, "%a, %d %b %Y %H:%M:%S %Z"
                        ).isoformat()
                    except ValueError:
                        # Fallback: try to parse whatever format we got
                        published_date = pub_date_elem.text

                # Clean up Google News redirect URL
                # Google News often wraps URLs, try to extract the actual article URL
                if url and "news.google.com" in url:
                    # Keep the Google URL as is - it redirects to the actual article
                    pass

                articles.append({
                    "title": title,
                    "url": url,
                    "source": source,
                    "published_date": published_date,
                    "description": description,
                })

        except ET.ParseError as e:
            print(f"Error parsing RSS feed: {e}")

        return articles

    def _extract_source_from_url(self, url: str) -> str:
        """Extract news source name from URL."""
        if not url:
            return "Unknown"

        try:
            # Extract domain from URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Remove www. prefix
            domain = domain.replace("www.", "")

            # Map common domains to readable names
            source_map = {
                "cbc.ca": "CBC News",
                "globalnews.ca": "Global News",
                "ctvnews.ca": "CTV News",
                "theglobeandmail.com": "The Globe and Mail",
                "nationalpost.com": "National Post",
                "thestar.com": "Toronto Star",
                "hilltimes.com": "The Hill Times",
                "macleans.ca": "Maclean's",
                "winnipegfreepress.com": "Winnipeg Free Press",
                "calgaryherald.com": "Calgary Herald",
                "montrealgazette.com": "Montreal Gazette",
                "ottawacitizen.com": "Ottawa Citizen",
            }

            return source_map.get(domain, domain.split(".")[0].title())

        except Exception:
            return "Unknown"
