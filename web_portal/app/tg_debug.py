import os
import time
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, Query
from telegram import Update

from .tg_bot import init_bot, process_update, tg_get_app

router = APIRouter(prefix="/tg", tags=["tg-debug"])


def _need_secret(x_telegram_bot_api_secret_token: Optional[str]) -> None:
    expected = (os.getenv("TELEGRAM_WEBHOOK_SECRET") or "").strip()
    if not expected:
        raise HTTPException(status_code=500, detail="TELEGRAM_WEBHOOK_SECRET missing")
    if (x_telegram_bot_api_secret_token or "").strip() != expected:
        raise HTTPException(status_code=401, detail="unauthorized")


@router.post("/ping")
async def tg_ping(
    chat_id: int = Query(..., description="Target chat_id to send ping to"),
    text: str = Query("ping ✅ telegram-guardian", description="Message to send"),
    x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
):
    """
    Outbound test: send a message to a known chat_id using bot token on server.
    Requires X-Telegram-Bot-Api-Secret-Token.
    """
    _need_secret(x_telegram_bot_api_secret_token)
    await init_bot()
    app = tg_get_app()
    await app.bot.send_message(chat_id=chat_id, text=text)
    return {"ok": True}


@router.post("/simulate")
async def tg_simulate(
    chat_id: int = Query(...),
    from_user_id: int = Query(1),
    text: str = Query("/start"),
    x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
):
    """
    Inbound test: fabricate a Telegram Update and run it through process_update().
    Requires X-Telegram-Bot-Api-Secret-Token.
    """
    _need_secret(x_telegram_bot_api_secret_token)

    # minimal-ish update payload compatible with Update.de_json
    payload: dict[str, Any] = {
        "update_id": int(time.time()),
        "message": {
            "message_id": int(time.time()) % 1000000,
            "date": int(time.time()),
            "chat": {"id": chat_id, "type": "private"},
            "from": {"id": from_user_id, "is_bot": False, "first_name": "debug"},
            "text": text,
            "entities": [
                {"type": "bot_command", "offset": 0, "length": len(text)}
            ] if text.startswith("/") else [],
        },
    }

    # quick decode check (so failures show clearly)
    app = tg_get_app()
    upd = Update.de_json(payload, app.bot)
    if not upd:
        raise HTTPException(status_code=400, detail="Update.de_json failed")

    await process_update(payload)
    return {"ok": True, "simulated_text": text, "chat_id": chat_id}
