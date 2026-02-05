from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, Request, status

from .tg_bot import process_update, get_bot_app

router = APIRouter()

def _want_secret() -> str:
    return (os.getenv("TELEGRAM_WEBHOOK_SECRET") or "").strip()

@router.post("/tg/webhook")
async def tg_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
) -> dict[str, Any]:
    want = _want_secret()
    got = (x_telegram_bot_api_secret_token or "").strip()

    if want and got != want:
        # do NOT log token
        print("WEBHOOK_REJECT: secret mismatch; got_present=", bool(got))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")

    payload = await request.json()

    # Minimal safe debug
    msg = payload.get("message") or payload.get("edited_message") or {}
    txt = msg.get("text")
    print("WEBHOOK_ACCEPT:",
          "secret_present=", bool(got),
          "keys=", list(payload.keys()),
          "text=", txt)

    app = get_bot_app()
    print("BOT_APP_PRESENT=", bool(app))

    try:
        await process_update(payload)
        print("WEBHOOK_PROCESS_OK")
    except Exception as e:
        print("WEBHOOK_PROCESS_ERROR:", repr(e))

    return {"ok": True}