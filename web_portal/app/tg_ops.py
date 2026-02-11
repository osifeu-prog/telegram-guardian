import os
from fastapi import APIRouter, Header, HTTPException
from telegram import Update

from .tg_bot import tg_get_app, process_update

router = APIRouter(prefix="/tg", tags=["tg-ops"])


def _require_secret(x_secret: str | None) -> None:
    expected = (os.getenv("TELEGRAM_WEBHOOK_SECRET") or "").strip()
    if not expected:
        raise HTTPException(status_code=500, detail="server missing TELEGRAM_WEBHOOK_SECRET")
    if not x_secret or x_secret.strip() != expected:
        raise HTTPException(status_code=401, detail="unauthorized")


@router.post("/ping")
async def tg_ping(
    chat_id: int,
    text: str = "ping",
    x_telegram_bot_api_secret_token: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
):
    _require_secret(x_telegram_bot_api_secret_token)

    app = tg_get_app()
    me = await app.bot.get_me()
    msg = await app.bot.send_message(chat_id=chat_id, text=text)
    return {"ok": True, "bot": {"username": me.username, "id": me.id}, "message_id": msg.message_id}


@router.post("/simulate")
async def tg_simulate(
    chat_id: int,
    from_user_id: int,
    text: str = "/whoami",
    x_telegram_bot_api_secret_token: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
):
    _require_secret(x_telegram_bot_api_secret_token)

    # Build a minimal Telegram Update payload
    payload = {
        "update_id": 999999999,
        "message": {
            "message_id": 1,
            "date": 0,
            "chat": {"id": chat_id, "type": "private"},
            "from": {"id": from_user_id, "is_bot": False, "first_name": "smoke"},
            "text": text,
            "entities": [{"offset": 0, "length": len(text.split()[0]), "type": "bot_command"}]
            if text.startswith("/")
            else [],
        },
    }

    await process_update(payload)
    return {"ok": True}
