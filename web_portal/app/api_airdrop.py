from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import User, LedgerEvent
from .core.tg_initdata import verify_telegram_init_data

router = APIRouter(prefix="/api", tags=["api"])

AIRDROP_AMOUNT = int(os.getenv("AIRDROP_AMOUNT", "100"))
BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()


def utcnow():
    return datetime.now(timezone.utc)


def get_db():
    with SessionLocal() as db:
        yield db


def _get_init_data(request: Request, body: dict[str, Any] | None) -> str:
    h = (request.headers.get("X-Tg-Init-Data") or "").strip()
    if h:
        return h
    if body and body.get("initData"):
        return str(body["initData"]).strip()
    return ""


def _parse_tg_user(d: dict[str, Any]) -> dict[str, Any]:
    user_json = d.get("user", "{}")
    try:
        return json.loads(user_json)
    except Exception:
        return {}


@router.post("/auth/telegram")
async def auth_telegram(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    if not BOT_TOKEN:
        raise HTTPException(status_code=500, detail="Missing TELEGRAM_BOT_TOKEN on server")

    body = None
    try:
        body = await request.json()
    except Exception:
        body = None

    init_data = _get_init_data(request, body)
    if not init_data:
        raise HTTPException(status_code=400, detail="Missing initData")

    try:
        d = verify_telegram_init_data(init_data, BOT_TOKEN)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"unauthorized: {e}")

    u = _parse_tg_user(d)
    telegram_id = int(u.get("id") or 0)
    if not telegram_id:
        raise HTTPException(status_code=400, detail="missing telegram user id")

    username = (u.get("username") or "").strip() or None
    first_name = (u.get("first_name") or "").strip() or None
    lang = (u.get("language_code") or "").strip() or None

    user = db.execute(select(User).where(User.telegram_id == telegram_id)).scalar_one_or_none()
    if not user:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            language_code=lang,
            airdrop_claimed=False,
            balance=0,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        changed = False
        if username and getattr(user, "username", None) != username:
            user.username = username; changed = True
        if first_name and getattr(user, "first_name", None) != first_name:
            user.first_name = first_name; changed = True
        if lang and getattr(user, "language_code", None) != lang:
            user.language_code = lang; changed = True
        if changed:
            db.add(user)
            db.commit()
            db.refresh(user)

    return {
        "ok": True,
        "telegram_id": user.telegram_id,
        "username": getattr(user, "username", None),
        "language_code": getattr(user, "language_code", None),
        "balance": int(getattr(user, "balance", 0)),
        "airdrop_claimed": bool(getattr(user, "airdrop_claimed", False)),
    }


@router.post("/airdrop/claim")
async def airdrop_claim(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    if not BOT_TOKEN:
        raise HTTPException(status_code=500, detail="Missing TELEGRAM_BOT_TOKEN on server")

    body = None
    try:
        body = await request.json()
    except Exception:
        body = None

    init_data = _get_init_data(request, body)
    if not init_data:
        raise HTTPException(status_code=400, detail="Missing initData")

    try:
        d = verify_telegram_init_data(init_data, BOT_TOKEN)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"unauthorized: {e}")

    u = _parse_tg_user(d)
    telegram_id = int(u.get("id") or 0)
    if not telegram_id:
        raise HTTPException(status_code=400, detail="missing telegram user id")

    user = db.execute(select(User).where(User.telegram_id == telegram_id)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="user not found (call /api/auth/telegram first)")

    if bool(getattr(user, "airdrop_claimed", False)):
        return {"ok": True, "already": True, "balance": int(getattr(user, "balance", 0))}

    amt = AIRDROP_AMOUNT
    user.airdrop_claimed = True
    user.balance = int(getattr(user, "balance", 0)) + amt

    db.add(user)
    db.add(LedgerEvent(
        telegram_id=user.telegram_id,
        event_type="AIRDROP_CLAIM",
        amount=amt,
        meta={"reason": "Hello World Drop"},
        created_at=utcnow(),
    ))
    db.commit()
    db.refresh(user)

    return {"ok": True, "claimed": True, "amount": amt, "balance": int(getattr(user, "balance", 0))}
