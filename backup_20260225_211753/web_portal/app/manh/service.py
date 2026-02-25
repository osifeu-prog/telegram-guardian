from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

# optional redis rate-limit
try:
    import redis  # type: ignore
except Exception:
    redis = None  # type: ignore

# in-memory fallback (per process)
_RL_MEM: dict[str, list[float]] = {}

@dataclass
class RateLimit:
    window_sec: int
    max_events: int

DEFAULT_RL = RateLimit(window_sec=60, max_events=8)

def _log(msg: str) -> None:
    print(msg, flush=True)

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def compute_event_hash(*, user_id: int, event_type: str, bucket: str, fingerprint: str) -> str:
    base = f"{user_id}|{event_type}|{bucket}|{fingerprint}"
    return _sha256(base)

def _rl_key(user_id: int, event_type: str) -> str:
    return f"manh:rl:{user_id}:{event_type}"

def rate_limit_check(user_id: int, event_type: str, rl: RateLimit = DEFAULT_RL) -> bool:
    key = _rl_key(user_id, event_type)
    now = time.time()

    redis_url = (os.getenv("REDIS_URL") or "").strip()
    if redis_url and redis is not None:
        r = redis.Redis.from_url(redis_url, decode_responses=True)
        bucket = int(now // rl.window_sec)
        rk = f"{key}:{bucket}"
        pipe = r.pipeline()
        pipe.incr(rk, 1)
        pipe.expire(rk, rl.window_sec + 5)
        count, _ = pipe.execute()
        return int(count) <= rl.max_events

    arr = _RL_MEM.get(key, [])
    cutoff = now - rl.window_sec
    arr = [t for t in arr if t >= cutoff]
    arr.append(now)
    _RL_MEM[key] = arr
    return len(arr) <= rl.max_events

# -------------------------
# DB bootstrap (NO ALEMBIC)
# -------------------------
def ensure_schema(db: Session) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS manh_users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS manh_accounts (
            user_id BIGINT PRIMARY KEY,
            opted_in BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS manh_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT PRIMARY KEY,
            user_id BIGINT NOT NULL,
            event_hash TEXT NOT NULL,
            event_type TEXT NOT NULL,
            bucket TEXT NOT NULL,
            fingerprint_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_manh_event_user_hash UNIQUE (user_id, event_hash)
        );
    """))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS manh_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT PRIMARY KEY,
            user_id BIGINT NOT NULL,
            event_hash TEXT NOT NULL,
            amount_manh REAL NOT NULL,
            bucket_scope TEXT NOT NULL DEFAULT 'daily',
            bucket_key TEXT NOT NULL DEFAULT 'UNKNOWN',
            meta_json TEXT NOT NULL DEFAULT '{}'::TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """))

    db.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_manh_ledger_scope_key
        ON manh_ledger(bucket_scope, bucket_key);
    """))

    db.commit()

def ensure_opt_in(db: Session, user_id: int) -> bool:
    ensure_schema(db)
    row = db.execute(text("SELECT opted_in FROM manh_accounts WHERE user_id=:u"), {"u": user_id}).fetchone()
    return bool(row[0]) if row else False

def set_opt_in(db: Session, user_id: int, opted_in: bool) -> None:
    ensure_schema(db)
    db.execute(text("""
        INSERT INTO manh_accounts(user_id, opted_in, created_at)
        VALUES (:u, :o, now())
        ON CONFLICT (user_id) DO UPDATE SET opted_in=EXCLUDED.opted_in
    """), {"u": user_id, "o": opted_in})
    db.commit()

def award_manh(
    db: Session,
    *,
    user_id: int,
    username: Optional[str],
    event_type: str,
    amount_manh: Decimal,
    bucket: str,
    bucket_scope: str,
    bucket_key: str,
    fingerprint_obj: dict[str, Any],
    meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    ensure_schema(db)

    if not rate_limit_check(user_id, event_type):
        return {"ok": False, "reason": "rate_limited"}

    if not ensure_opt_in(db, user_id):
        return {"ok": False, "reason": "not_opted_in"}

    fingerprint = json.dumps(fingerprint_obj, sort_keys=True, separators=(",", ":"))
    eh = compute_event_hash(user_id=user_id, event_type=event_type, bucket=bucket, fingerprint=fingerprint)

    db.execute(text("""
        INSERT INTO manh_users(user_id, username, created_at)
        VALUES (:u, :name, now())
        ON CONFLICT (user_id) DO UPDATE SET username=COALESCE(EXCLUDED.username, manh_users.username)
    """), {"u": user_id, "name": username})

    try:
        db.execute(text("""
            INSERT INTO manh_events(user_id, event_hash, event_type, bucket, fingerprint_json, created_at)
            VALUES (:u, :h, :t, :b, CAST(:f AS TEXT), now())
        """), {"u": user_id, "h": eh, "t": event_type, "b": bucket, "f": fingerprint})

        db.execute(text("""
            INSERT INTO manh_ledger(user_id, event_hash, amount_manh, bucket_scope, bucket_key, meta_json, created_at)
            VALUES (:u, :h, :amt, :scope, :bkey, CAST(:m AS TEXT), now())
        """), {
            "u": user_id,
            "h": eh,
            "amt": str(amount_manh),
            "scope": bucket_scope,
            "bkey": bucket_key,
            "m": json.dumps(meta or {}, separators=(",", ":")),
        })

        db.commit()
        return {"ok": True, "event_hash": eh}
    except Exception as e:
        db.rollback()
        _log(f"MANH award error: {e!r}")
        return {"ok": False, "reason": "duplicate_or_error", "event_hash": eh}

def get_balance(db: Session, user_id: int) -> dict[str, Any]:
    ensure_schema(db)
    row = db.execute(text("""
        SELECT COALESCE(SUM(amount_manh), 0)
        FROM manh_ledger
        WHERE user_id=:u
    """), {"u": user_id}).fetchone()
    bal = Decimal(str(row[0])) if row else Decimal("0")
    xp = int((bal * Decimal("100")).to_integral_value(rounding=ROUND_FLOOR))
    return {"manh": str(bal), "xp_points": xp}

def leaderboard(db: Session, *, bucket_scope: str, bucket_key: str, limit: int = 10) -> list[dict[str, Any]]:
    ensure_schema(db)
    rowset = db.execute(text("""
        SELECT u.user_id, COALESCE(u.username,'') AS username, SUM(l.amount_manh) AS total
        FROM manh_ledger l
        JOIN manh_users u ON u.user_id=l.user_id
        JOIN manh_accounts a ON a.user_id=l.user_id
        WHERE a.opted_in = TRUE
          AND l.bucket_scope = :s
          AND l.bucket_key = :k
        GROUP BY u.user_id, u.username
        ORDER BY total DESC
        LIMIT :lim
    """), {"s": bucket_scope, "k": bucket_key, "lim": int(limit)}).fetchall()

    return [{"user_id": int(r[0]), "username": r[1], "total_manh": str(r[2])} for r in rowset]





