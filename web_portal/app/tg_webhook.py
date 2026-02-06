# TG_WEBHOOK_SECRET_CHECK_V1
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()

def _check_telegram_secret(x_telegram_bot_api_secret_token: str | None) -> None:
    # If secret is configured, enforce it. If not configured, allow (dev mode).
    if TELEGRAM_WEBHOOK_SECRET:
        if not x_telegram_bot_api_secret_token or x_telegram_bot_api_secret_token.strip() != TELEGRAM_WEBHOOK_SECRET:
            # do not leak expected secret
            raise ValueError("bad secret")

from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, Request, status

from .tg_bot import process_update

router = APIRouter()

def _want_secret() -> str:
    return (os.getenv("TELEGRAM_WEBHOOK_SECRET") or "").strip()

@router.post("/tg/webhook")
async def tg_webhook(
    try:
        _check_telegram_secret(x_telegram_bot_api_secret_token)
    except ValueError:
        print('WEBHOOK: 401 bad secret')
        raise HTTPException(status_code=401, detail='Unauthorized')

    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
) -> dict[str, Any]:
    want = _want_secret()
    if want:
        got = (x_telegram_bot_api_secret_token or "").strip()
        if got != want:
            print("WEBHOOK: 401 bad secret", flush=True)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")

    payload = await request.json()
    try:
        await process_update(payload)
    except Exception as e:
        print("WEBHOOK_PROCESS_ERROR:", repr(e), flush=True)
    return {"ok": True}