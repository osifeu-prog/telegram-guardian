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
    return url

def get_engine():
    global _engine
    if _engine is None:
        url = _normalize_db_url(DATABASE_URL)
        if not url:
            raise RuntimeError("Missing DATABASE_URL")
        _engine = create_engine(url, pool_pre_ping=True)
    return _engine

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()