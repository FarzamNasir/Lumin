"""
Article Summarizer Agent

Uses OpenAI's Responses API with GPT-4.1 mini to generate
structured digest summaries (title + 2-3 sentence summary)
for scraped articles and videos.
"""

import os
import logging

from openai import OpenAI, APIError
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

logger = logging.getLogger(__name__)

# Retry OpenAI API errors: up to 4 attempts, 2s → 4s → 8s → 16s backoff
_openai_retry = retry(
    retry=retry_if_exception_type(APIError),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)

SYSTEM_PROMPT = """\
You are an AI news digest summarizer. Your job is to read articles and videos \
about AI, machine learning, and technology, then produce a concise digest entry.

Rules:
- "title": Create a short, catchy, informative title (max 15 words). \
  Do NOT just copy the original title — rephrase it to highlight the key takeaway.
- "summary": Write exactly 2-3 sentences that capture the most important points. \
  Be specific about what was announced, discovered, or built. \
  Write for a technical audience who wants to stay informed quickly.

If the content is a YouTube video transcript, focus on the main topic discussed.
If the content is a blog post, focus on the key announcement or finding.
"""


class DigestOutput(BaseModel):
    """Structured output from the summarizer."""

    title: str
    summary: str


class Summarizer:
    """
    Generates digest summaries using OpenAI's Responses API.

    Usage:
        summarizer = Summarizer()
        result = summarizer.summarize(title, content)
        print(result.title, result.summary)
    """

    def __init__(self, model: str = "gpt-4.1-mini"):
        self.model = model
        self._client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def summarize(
        self,
        title: str,
        content: str | None = None,
        description: str | None = None,
        source_type: str = "article",
    ) -> DigestOutput | None:
        """
        Generate a digest for a single article/video.

        Args:
            title:       Original title of the article/video.
            content:     Full text (article body or transcript).
            description: Short description/excerpt if content is unavailable.
            source_type: "youtube", "openai", or "anthropic".

        Returns:
            DigestOutput with generated title and summary, or None on failure.
        """
        # Build the input text
        parts = [f"Source: {source_type}", f"Original Title: {title}"]

        if content:
            # Truncate very long content to stay within context limits
            text = content[:15000] if len(content) > 15000 else content
            parts.append(f"Content:\n{text}")
        elif description:
            parts.append(f"Description:\n{description}")
        else:
            parts.append("(No content available — summarize based on title only)")

        user_input = "\n\n".join(parts)

        try:
            result = self._call_api(user_input)
            logger.info("Summarized: %s", title[:60])
            return result
        except Exception as exc:
            logger.error("Failed to summarize '%s' after retries: %s", title[:60], exc)
            return None

    @_openai_retry
    def _call_api(self, user_input: str) -> DigestOutput:
        """Internal: call OpenAI API with automatic retry."""
        response = self._client.responses.parse(
            model=self.model,
            instructions=SYSTEM_PROMPT,
            input=[{"role": "user", "content": user_input}],
            text_format=DigestOutput,
        )
        return response.output_parsed
