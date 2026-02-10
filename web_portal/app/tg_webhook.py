# TG_PTB_WEBHOOK_ENSURE_V1
_TG_INIT_LOCK = asyncio.Lock()
_TG_INIT_DONE = False

async def _tg_ensure_started() -> Application:
    global _TG_INIT_DONE
    async with _TG_INIT_LOCK:
        if _TG_INIT_DONE:
            return tg_get_app()
        app = tg_get_app()
        await app.initialize()
        await app.start()
        _TG_INIT_DONE = True
        print("TG_PTB: ensured initialized+started (webhook)")
        return app

from app.tg_bot import tg_get_app
from telegram.ext import Application
import asyncio
# TG_WEBHOOK_SECRET_CHECK_V1
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()



# TG_SECRET_BOOT_V1
# TG_BUILD_MARKER_V1
import hashlib

def _secret_fingerprint(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]

if TELEGRAM_WEBHOOK_SECRET:
    print("TG_SECRET_BOOT present=1 fp=" + _secret_fingerprint(TELEGRAM_WEBHOOK_SECRET))
else:
    print("TG_SECRET_BOOT present=0")



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
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
) -> dict[str, Any]:
    # Secret check (optional)
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
