import os
import asyncio
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, Request, status

from .tg_bot import process_update, tg_get_app

router = APIRouter()

_TG_INIT_LOCK = asyncio.Lock()
_TG_INIT_DONE = False

async def _tg_ensure_started():
    global _TG_INIT_DONE
    async with _TG_INIT_LOCK:
        if _TG_INIT_DONE:
            return tg_get_app()
        app = tg_get_app()
        await app.initialize()
        await app.start()
        _TG_INIT_DONE = True
        print("TG_PTB: ensured initialized+started (webhook)", flush=True)
        return app

def _want_secret() -> str:
    return (os.getenv("TELEGRAM_WEBHOOK_SECRET") or "").strip()

@router.post("/tg/webhook")
async def tg_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
) -> dict[str, Any]:
    # Ensure PTB app is started (best effort)
    try:
        await _tg_ensure_started()
    except Exception as e:
        print("TG_PTB_START_ERROR:", repr(e), flush=True)

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
