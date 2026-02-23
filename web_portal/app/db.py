from __future__ import annotations

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.settings import settings

logger = logging.getLogger(__name__)

DATABASE_URL = settings.DATABASE_URL


class Base(DeclarativeBase):
    pass


_engine = None


def _normalize_db_url(url: str) -> str:
    url = (url or "").strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    # Log the normalized URL (without password)
    log_url = url.split('@')[0] if '@' in url else url
    logger.debug(f"Normalized DB URL: {log_url}")
    return url


def get_engine():
    global _engine
    if _engine is None:
        raw_url = DATABASE_URL
        logger.debug(f"Raw DATABASE_URL from settings: {raw_url.split('@')[0] if '@' in raw_url else raw_url}")
        url = _normalize_db_url(raw_url)
        if not url:
            raise RuntimeError("Missing DATABASE_URL")
        log_url = url.split('@')[0] if '@' in url else url
        logger.debug(f"Creating database engine for URL: {log_url}")
        # Force sslmode=disable both in URL and connect_args
        # First ensure URL has sslmode=disable
        if "sslmode=" not in url:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}sslmode=disable"
            logger.debug(f"Added sslmode=disable to URL: {url.split('@')[0] if '@' in url else url}")
        _engine = create_engine(url, pool_pre_ping=True, connect_args={"sslmode": "disable"})
    return _engine


engine = get_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Return a database session to be used as a context manager."""
    db = SessionLocal()
    try:
        logger.debug("Yielding database session")
        yield db
    finally:
        logger.debug("Closing database session")
        db.close()
