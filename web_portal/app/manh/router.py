from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session

from .constants import LEADERBOARD_TZ
from .storage import get_db
from .service import set_opt_in, get_balance, award_manh, leaderboard

router = APIRouter(prefix="/manh", tags=["manh"])

def _bucket(scope: str) -> tuple[str, str]:
    tz = ZoneInfo(LEADERBOARD_TZ)
    now = datetime.now(tz)
    if scope == "daily":
        return ("daily", now.strftime("%Y-%m-%d"))
    if scope == "weekly":
        y, w, _ = now.isocalendar()
        return ("weekly", f"{y}-W{w:02d}")
    raise ValueError("bad scope")

@router.post("/optin")
def manh_optin(opt_in: bool, user_id: int, db: Session = Depends(get_db)):
    set_opt_in(db, user_id, opt_in)
    return {"ok": True, "user_id": user_id, "opted_in": opt_in}

@router.get("/balance")
def manh_balance(user_id: int, db: Session = Depends(get_db)):
    return {"ok": True, **get_balance(db, user_id)}

@router.post("/award")
def manh_award(
    user_id: int,
    username: Optional[str],
    event_type: str,
    amount_manh: str,
    scope: str = "daily",
    db: Session = Depends(get_db),
):
    bucket_scope, bucket_key = _bucket(scope)
    bucket = bucket_key
    amt = Decimal(amount_manh)

    fp = {"v": 1, "scope": bucket_scope, "bucket": bucket_key}
    meta = {"scope": bucket_scope, "bucket": bucket_key, "tz": LEADERBOARD_TZ}

    return award_manh(
        db,
        user_id=user_id,
        username=username,
        event_type=event_type,
        amount_manh=amt,
        bucket=bucket,
        bucket_scope=bucket_scope,
        bucket_key=bucket_key,
        fingerprint_obj=fp,
        meta=meta,
    )

@router.get("/leaderboard")
def manh_leaderboard(scope: str = "daily", db: Session = Depends(get_db)):
    bucket_scope, bucket_key = _bucket(scope)
    rows = leaderboard(db, bucket_scope=bucket_scope, bucket_key=bucket_key, limit=10)
    return {"ok": True, "scope": bucket_scope, "bucket": bucket_key, "rows": rows}
