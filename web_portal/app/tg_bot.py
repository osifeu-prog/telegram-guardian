import os
import asyncio
from typing import Any, Optional

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)


def _log(msg: str) -> None:
    print(msg, flush=True)


def _tg_pick_token() -> str:
    # deterministic: first match wins
    for k in ("TELEGRAM_BOT_TOKEN", "BOT_TOKEN", "TELEGRAM_TOKEN", "TG_BOT_TOKEN"):
        v = (os.getenv(k) or "").strip()
        if v:
            return v
    return ""


_APP: Optional[Application] = None
_APP_LOCK = asyncio.Lock()
_STARTED = False


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = getattr(update, "effective_chat", None)
    if not chat:
        return
    await context.bot.send_message(chat_id=chat.id, text="telegram-guardian alive ✅  (/whoami)")


async def cmd_whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = getattr(update, "effective_chat", None)
    if not chat:
        return
    me = await context.bot.get_me()
    await context.bot.send_message(chat_id=chat.id, text=f"bot=@{me.username} id={me.id}")


def tg_get_app() -> Application:
    global _APP
    if _APP is not None:
        return _APP

    token = _tg_pick_token()
    if not token:
        raise RuntimeError(
            "Telegram token missing (checked TELEGRAM_BOT_TOKEN/BOT_TOKEN/TELEGRAM_TOKEN/TG_BOT_TOKEN)"
        )

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("whoami", cmd_whoami))

    _APP = app
    return app


async def init_bot() -> None:
    """
    Compatibility shim for app.main import.
    Ensures PTB Application is initialized and started exactly once.
    """
    global _STARTED
    async with _APP_LOCK:
        if _STARTED:
            return
        app = tg_get_app()
        await app.initialize()
        await app.start()
        _STARTED = True
        _log("TG_PTB: initialized+started (init_bot)")


async def shutdown_bot() -> None:
    """
    Compatibility shim for app.main import.
    Stops PTB cleanly if it was started.
    """
    global _STARTED
    async with _APP_LOCK:
        if not _STARTED:
            return
        app = tg_get_app()
        try:
            await app.stop()
        finally:
            await app.shutdown()
        _STARTED = False
        _log("TG_PTB: stopped+shutdown (shutdown_bot)")


async def process_update(payload: dict[str, Any]) -> None:
    """
    Called by FastAPI webhook endpoint with raw Telegram update JSON.
    Dispatches into PTB so handlers run.
    """
    app = tg_get_app()

    upd = Update.de_json(payload, app.bot)
    if not upd:
        _log("TG: process_update: payload did not decode to Update")
        _log(f"TG: raw keys={list(payload.keys())[:20]}")
        return

    msg = getattr(upd, "message", None)
    txt = getattr(msg, "text", None) if msg else None
    ent = getattr(msg, "entities", None) if msg else None

    _log(
        f"TG: update_id={getattr(upd,'update_id',None)} "
        f"kind={'message' if msg else 'non-message'} "
        f"text={txt!r} entities={ent!r}"
    )

    try:
        await app.process_update(upd)
    except Exception as e:
        _log(f"TG: app.process_update ERROR: {e!r}")
        raise
