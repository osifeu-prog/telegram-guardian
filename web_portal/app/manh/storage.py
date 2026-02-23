from __future__ import annotations
import os
from typing import Iterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Try to reuse existing project DB if present; else fallback to DATABASE_URL
try:
    from app.db import get_db as _get_db  # type: ignore
    def get_db() -> Iterator[Session]:
        yield from _get_db()
except Exception:
    _ENGINE = None
    _SessionLocal: Optional[sessionmaker] = None

    def _ensure():
        global _ENGINE, _SessionLocal
        if _ENGINE is not None and _SessionLocal is not None:
            return
        url = (os.getenv("DATABASE_URL") or "").strip()
        if not url:
            raise RuntimeError("DATABASE_URL missing")
        _ENGINE = create_engine(url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_ENGINE)

    def get_db() -> Iterator[Session]:
        _ensure()
        assert _SessionLocal is not None
        db = _SessionLocal()
        try:
            yield db
        finally:
            db.close()
