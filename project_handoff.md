# AI News Aggregator — Project Handoff Summary

**Repo:** `c:\Users\PMLS\Desktop\projects\ai-news-aggregator-local`  
**GitHub:** `github.com/FarzamNasir/ai-news-aggregator-local`  
**Branch:** `main` (only branch)  
**Date:** June 11, 2026  

---

## What This Project Does

An automated Python 3.12 pipeline that:
1. **Scrapes** AI news from 3 sources: YouTube RSS (with transcripts), OpenAI Blog RSS, Anthropic Blog RSS (3 feeds: news, engineering, research)
2. **Summarizes** each article using GPT-4.1 mini via OpenAI Responses API with Pydantic structured output
3. **Stores** articles + digests in PostgreSQL (SQLAlchemy ORM, UUID primary keys)
4. **Curates** by batch-scoring all digests against a hardcoded user interest profile (1-10 relevance) in a single API call
5. **Emails** the top-10 ranked articles as a styled HTML email via Gmail SMTP with a GPT-generated personalized intro

## Architecture

```
app/
├── config.py              # YouTube channel IDs, lookback hours (24h), env detection
├── user_profile.py        # Hardcoded user name ("Farzam") + interest profile for curator
├── runner.py              # Pipeline orchestrator (scrape → digest → curate → email)
│                          # CLI: --schedule (24h loop), --reset (drop/recreate tables)
├── scrapers/
│   ├── base.py            # Abstract RSSScraperBase (httpx client, HTML→MD, XML parsing)
│   ├── youtube.py         # YouTubeScraper class (Atom feed + youtube-transcript-api)
│   ├── openai_blog.py     # OpenAIScraper extends RSSScraperBase
│   └── anthropic_blog.py  # AnthropicScraper extends RSSScraperBase (3 feeds, cross-feed dedup)
├── database/
│   ├── models.py          # Article + Digest SQLAlchemy models, SourceType enum
│   ├── connection.py      # Engine + session factory (handles postgres:// → postgresql://)
│   ├── repository.py      # ArticleRepository with generic _save_items() + URL dedup
│   └── create_tables.py   # Standalone table creation script
└── agent/
    ├── summarizer.py      # Summarizer class → DigestOutput (title + summary)
    ├── digest_service.py  # Finds articles without digests, runs Summarizer
    ├── curator.py         # Curator class → batch scores against user profile
    ├── curation_service.py# Pulls unsent digests, runs curator, merges scores
    ├── email_agent.py     # EmailAgent → generates personalized intro + EmailContent
    └── email_sender.py    # Renders HTML email + sends via Gmail SMTP
```

**Tech Stack:** Python 3.12, uv (package manager), PostgreSQL 16, SQLAlchemy, httpx, OpenAI SDK (Responses API), feedparser, html2text, youtube-transcript-api, Gmail SMTP

**Deployment:** Render (Docker cron job at 8am UTC + free managed Postgres)

---

## What Was Done (Completed Fixes)

### 1. Fixed Session Management in `runner.py`
- All database sessions now use `try/finally` blocks to guarantee cleanup
- Prevents connection leaks when any pipeline stage throws an error
- Moved the `Digest` model import from a late import inside the function body to the top-level imports

### 2. Added OpenAI Article Content Fetching in `runner.py`
- Previously, OpenAI articles were only summarized from RSS title + description (very sparse)
- Now calls `openai.fetch_article_content(article.url)` for each article (same pattern Anthropic already had)
- Gives the summarizer full article text → dramatically better summaries

### 3. Fixed Broken Test File `test_youtube.py`
- The YouTube scraper was refactored from standalone functions to a `YouTubeScraper` class, but the test file still imported the old function-based API
- Updated all imports and calls to use the class instance methods

### 4. Fixed Render Deployment Config `render.yaml`
- Added `branch: main` (was unspecified, possibly defaulting to a non-existent branch)
- Added `dockerfilePath: ./Dockerfile` for explicit Dockerfile discovery
- **Result: Build now succeeds on Render ✅**

### 5. Deployment Status
- **Render Blueprint created and build succeeds** ✅
- Cron job runs daily at 8:00 AM UTC
- Env vars set: `OPENAI_API_KEY`, `SMTP_EMAIL`, `SMTP_APP_PASSWORD`, `RECIPIENT_EMAIL`
- Free managed PostgreSQL provisioned

---

## What Was NOT Done Yet (Planned Next Steps)

These are prioritized improvements discussed but not yet implemented:

### High Priority
1. **Add retry logic** — All HTTP calls (httpx) and OpenAI API calls have zero retry. A single transient failure permanently skips that article. Consider using `tenacity` library. Affects: `summarizer.py`, `curator.py`, `email_agent.py`, and all scrapers.

2. **Rotate exposed credentials** — The `.env` file contains real OpenAI API key and Gmail app password. They're gitignored but should be rotated for safety. OpenAI key at platform.openai.com/api-keys, Gmail app password at myaccount.google.com/apppasswords.

3. **Add error recovery for failed summarizations** — Currently if `Summarizer.summarize()` fails for an article, it returns `None` and that article is silently skipped forever. Should track failures and allow re-processing.

### Medium Priority
4. **Add more news sources** — The scraper architecture is extensible (just extend `RSSScraperBase`). Good candidates:
   - Google DeepMind blog
   - Hugging Face blog
   - arXiv RSS (cs.AI, cs.CL, cs.LG)
   - Meta AI blog
   - More YouTube channels (AI Explained, Yannic Kilcher, etc.)

5. **Make user profile configurable** — Currently hardcoded in `user_profile.py`. Could move to env var, database, or a config file.

6. **Add run history / audit log** — Track pipeline runs (start time, end time, counts, errors) in the database for debugging and monitoring.

### Lower Priority
7. **Replace `time.sleep()` scheduler** — The `--schedule` mode uses a naive `time.sleep(24h)` loop. Could use APScheduler, or just rely entirely on Render cron.

8. **Add health check endpoint** — Simple HTTP server so you can monitor if the service is alive.

9. **Improve email template** — Add unsubscribe link, better mobile responsiveness.

10. **Add a web dashboard** — View past digests, scores, and pipeline status in a browser.

---

## Key Files to Know

| File | Why It Matters |
|------|---------------|
| `app/runner.py` | Entry point — `run_full_pipeline()` orchestrates everything |
| `app/config.py` | YouTube channel IDs and lookback hours live here |
| `app/user_profile.py` | The curator scoring profile — edit this to change what's "relevant" |
| `app/scrapers/base.py` | Extend this to add new RSS sources |
| `render.yaml` | Render deployment config — cron schedule, env vars, DB |
| `Dockerfile` | Multi-stage build with uv for fast deps |
| `.env` | Local credentials (gitignored) |

---

## How to Run Locally

```bash
# Start local Postgres
docker compose -f docker/docker-compose.yml up -d

# Install deps
uv sync

# One-shot pipeline run
uv run python -m app.runner

# With scheduling (every 24h)
uv run python -m app.runner --schedule

# Reset database
uv run python -m app.runner --reset
```
