"""
OpenAI Blog RSS Scraper

Fetches and parses the OpenAI News RSS feed, returning
a list of articles filtered by date.
"""

import xml.etree.ElementTree as ET
from datetime import datetime

from pydantic import BaseModel

from app.scrapers.base import RSSScraperBase

OPENAI_RSS_URL = "https://openai.com/news/rss.xml"


class ArticleInfo(BaseModel):
    """A single article from the OpenAI blog RSS feed."""

    title: str
    url: str
    category: str | None = None
    description: str | None = None
    published_at: datetime
    content: str | None = None


class OpenAIScraper(RSSScraperBase):
    """
    Scrapes the OpenAI News RSS feed for recent articles.

    Usage:
        scraper = OpenAIScraper()
        articles = scraper.get_latest_articles(since=datetime(...))
    """

    @property
    def feed_urls(self) -> list[str]:
        return [OPENAI_RSS_URL]

    @property
    def source_name(self) -> str:
        return "OpenAI"

    def _parse_item(self, item: ET.Element, **kwargs) -> ArticleInfo | None:
        """Parse a single <item> into an ArticleInfo."""
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub_date_str = item.findtext("pubDate", "").strip()

        if not title or not link or not pub_date_str:
            return None

        return ArticleInfo(
            title=title,
            url=link,
            category=item.findtext("category", "").strip() or None,
            description=item.findtext("description", "").strip() or None,
            published_at=self.parse_rss_date(pub_date_str),
        )
