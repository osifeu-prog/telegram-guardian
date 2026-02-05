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
    x_telegram_bot_api_secret_token: Optional[str] = Header(
        None, alias="X-Telegram-Bot-Api-Secret-Token"
    ),
) -> dict[str, Any]:
    want = _want_secret()
    if want:
        got = (x_telegram_bot_api_secret_token or "").strip()
        if got != want:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized"
            )

    payload = await request.json()

    try:
        await process_update(payload)
    except Exception as e:
        # debug only (no secrets)
        print("WEBHOOK_PROCESS_ERROR:", repr(e))

    return {"ok": True}