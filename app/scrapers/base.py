"""
Base RSS Scraper

Shared logic for RSS-based blog scrapers (OpenAI, Anthropic, etc.).
Handles HTTP client setup, HTML-to-Markdown conversion, RSS parsing,
and date filtering.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET

import httpx
import html2text
from pydantic import BaseModel

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


class RSSScraperBase(ABC):
    """
    Base class for RSS feed scrapers.

    Subclasses must implement:
        - feed_urls: property returning list of RSS feed URLs
        - source_name: property returning a human-readable name
        - _parse_item(item, **kwargs): parse an XML <item> into a Pydantic model
    """

    def __init__(self):
        self._http_client = httpx.Client(
            timeout=15,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
        self._html2text = html2text.HTML2Text()
        self._html2text.ignore_links = False
        self._html2text.ignore_images = True
        self._html2text.body_width = 0  # no wrapping

    @property
    @abstractmethod
    def feed_urls(self) -> list[str]:
        """List of RSS feed URLs to scrape."""
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable source name for logging."""
        ...

    @abstractmethod
    def _parse_item(self, item: ET.Element, **kwargs) -> BaseModel | None:
        """Parse a single <item> XML element into a Pydantic model."""
        ...

    def get_latest_articles(self, since: datetime) -> list[BaseModel]:
        """
        Fetch articles from all feeds published after *since*.

        Returns:
            List of parsed articles, sorted newest-first.
        """
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)

        all_articles = []

        for feed_url in self.feed_urls:
            articles = self._fetch_feed(feed_url)
            all_articles.extend(a for a in articles if a.published_at >= since)

        all_articles.sort(key=lambda a: a.published_at, reverse=True)

        logger.info(
            "%s: %d articles since %s",
            self.source_name,
            len(all_articles),
            since.isoformat(),
        )
        return all_articles

    def _fetch_feed(self, feed_url: str) -> list[BaseModel]:
        """Fetch and parse a single RSS feed."""
        try:
            resp = self._http_client.get(feed_url)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("Error fetching %s: %s", feed_url, exc)
            return []

        root = ET.fromstring(resp.text)
        articles = []

        for item in root.findall(".//item"):
            article = self._parse_item(item, feed_url=feed_url, root=root)
            if article:
                articles.append(article)

        return articles

    def fetch_article_content(self, url: str) -> str | None:
        """
        Fetch an article's page and convert it to Markdown.

        Args:
            url: The full URL of the article.

        Returns:
            Markdown string of the article content, or None on failure.
        """
        try:
            resp = self._http_client.get(url)
            resp.raise_for_status()
            markdown = self._html2text.handle(resp.text).strip()
            logger.info("Fetched content for %s (%d chars)", url, len(markdown))
            return markdown
        except Exception as exc:
            logger.warning("Could not fetch content for %s: %s", url, exc)
            return None

    @staticmethod
    def parse_rss_date(date_str: str) -> datetime:
        """Parse an RFC 2822 date string from an RSS feed."""
        return parsedate_to_datetime(date_str)
