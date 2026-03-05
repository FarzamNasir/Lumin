"""
SQLAlchemy database connection and session management.
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)

LOCAL_DEFAULT = "postgresql://aggregator:aggregator_pass@127.0.0.1:5433/news_aggregator"

_raw_url = os.getenv("DATABASE_URL")

if _raw_url:
    # Render uses postgres:// but SQLAlchemy needs postgresql://
    DATABASE_URL = _raw_url.replace("postgres://", "postgresql://", 1)
else:
    env = os.getenv("ENVIRONMENT", "local")
    if env == "production":
        raise RuntimeError(
            "DATABASE_URL is required in production! "
            "Set it in the Render dashboard."
        )
    DATABASE_URL = LOCAL_DEFAULT
    logger.info("Using local database: %s", LOCAL_DEFAULT)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def get_session() -> Session:
    """Create and return a new database session."""
    return SessionLocal()
