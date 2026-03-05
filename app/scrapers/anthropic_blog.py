"""
Anthropic Blog RSS Scraper

Fetches and parses Anthropic's News, Engineering, and Research RSS feeds,
returning a combined list of articles filtered by date.
"""

import logging
import xml.etree.ElementTree as ET
from datetime import datetime

from pydantic import BaseModel

from app.scrapers.base import RSSScraperBase

logger = logging.getLogger(__name__)

ANTHROPIC_FEEDS = [
    "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml",
    "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_engineering.xml",
    "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_research.xml",
]


class AnthropicArticle(BaseModel):
    """A single article from an Anthropic RSS feed."""

    title: str
    url: str
    category: str | None = None
    description: str | None = None
    published_at: datetime
    feed_source: str  # "news", "engineering", or "research"
    content: str | None = None


class AnthropicScraper(RSSScraperBase):
    """
    Scrapes Anthropic's News, Engineering, and Research RSS feeds.

    Usage:
        scraper = AnthropicScraper()
        articles = scraper.get_latest_articles(since=datetime(...))
    """

    def __init__(self, feed_urls: list[str] | None = None):
        super().__init__()
        self._feed_urls = feed_urls or ANTHROPIC_FEEDS

    @property
    def feed_urls(self) -> list[str]:
        return self._feed_urls

    @property
    def source_name(self) -> str:
        return "Anthropic"

    def get_latest_articles(self, since: datetime) -> list[AnthropicArticle]:
        """Override to add cross-feed URL deduplication."""
        articles = super().get_latest_articles(since)

        # Deduplicate by URL (article may appear in multiple feeds)
        seen: set[str] = set()
        unique: list[AnthropicArticle] = []
        for article in articles:
            if article.url not in seen:
                seen.add(article.url)
                unique.append(article)

        return unique

    def _parse_item(self, item: ET.Element, **kwargs) -> AnthropicArticle | None:
        """Parse a single <item> into an AnthropicArticle."""
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub_date_str = item.findtext("pubDate", "").strip()

        if not title or not link or not pub_date_str:
            return None

        # Derive feed source from the feed's <title>
        root = kwargs.get("root")
        feed_title = root.findtext(".//channel/title", "").strip().lower() if root else ""
        if "engineering" in feed_title:
            feed_source = "engineering"
        elif "research" in feed_title:
            feed_source = "research"
        else:
            feed_source = "news"

        return AnthropicArticle(
            title=title,
            url=link,
            category=item.findtext("category", "").strip() or None,
            description=item.findtext("description", "").strip() or None,
            published_at=self.parse_rss_date(pub_date_str),
            feed_source=feed_source,
        )
