from __future__ import annotations

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.environ.get("DATABASE_URL", "")

class Base(DeclarativeBase):
    pass

def get_engine():
    if not DATABASE_URL:
        raise RuntimeError("Missing DATABASE_URL")
    return create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
