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
    want = _want_secret()

    # minimal header diagnostics (no secrets printed)
    if want:
        got = (x_telegram_bot_api_secret_token or "").strip()
        if got != want:
            print("WEBHOOK_AUTH_FAIL: secret header mismatch")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")

    payload = await request.json()
    uid = payload.get("update_id")
    has_msg = "message" in payload
    has_cbq = "callback_query" in payload
    print(f"WEBHOOK_OK: update_id={uid} message={has_msg} callback_query={has_cbq}")

    try:
        await process_update(payload)
    except Exception as e:
        # keep 200 to avoid retries storm, but log the real reason
        print("WEBHOOK_PROCESS_ERROR:", repr(e))

    return {"ok": True}