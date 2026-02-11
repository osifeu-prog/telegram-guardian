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



_LAST_UPDATE_LOCK = asyncio.Lock()
_LAST_UPDATE = {"ts_utc": None, "chat_id": None, "from_user_id": None, "text": None, "update_id": None}
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = getattr(update, "effective_chat", None)
    if not chat:
        return
    await context.bot.send_message(chat_id=chat.id, text="telegram-guardian alive ط·آ·ط¢آ·ط·آ¢ط¢آ·ط·آ·ط¢آ¢ط·آ¢ط¢آ£ط·آ·ط¢آ·ط·آ¢ط¢آ¢ط·آ·ط¢آ¢ط·آ¢ط¢آ¢ط·آ·ط¢آ·ط·آ¢ط¢آ·ط·آ·ط¢آ¢ط·آ¢ط¢آ¥ط·آ·ط¢آ£ط·آ¢ط¢آ¢ط·آ£ط¢آ¢ط£آ¢أ¢â€ڑآ¬ط¹â€کط·آ¢ط¢آ¬ط·آ·ط¢آ¥ط£آ¢أ¢â€ڑآ¬ط¥â€œط·آ·ط¢آ·ط·آ¢ط¢آ£ط·آ·ط¢آ¢ط·آ¢ط¢آ¢ط·آ·ط¢آ£ط·آ¢ط¢آ¢ط·آ£ط¢آ¢ط£آ¢أ¢â‚¬ع‘ط¢آ¬ط·آ¹أ¢â‚¬ع©ط·آ·ط¢آ¢ط·آ¢ط¢آ¬ط·آ·ط¢آ·ط·آ¢ط¢آ¢ط·آ·ط¢آ¢ط·آ¢ط¢آ¦  (/whoami)")


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

    IMPORTANT:
    - Webhook handlers may call this repeatedly; it MUST be idempotent.
    - PTB can raise RuntimeError("This Application is already running!") on start().
    """
    global _STARTED
    async with _APP_LOCK:
        if _STARTED:
            return

        app = tg_get_app()

        # initialize() can also be called only once
        try:
            await app.initialize()
        except RuntimeError as e:
            msg = str(e)
            if "already" not in msg.lower():
                raise

        # start() must not crash if already running (can happen with repeated webhook calls)
        try:
            await app.start()
        except RuntimeError as e:
            msg = str(e)
            if "already running" not in msg.lower():
                raise

        _STARTED = True
        _log("TG_PTB: initialized+started (init_bot, idempotent)")

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

    await _capture_last_update(upd)
    if not upd:
        _log("TG: process_update: payload did not decode to Update")
        return

    msg = getattr(upd, "message", None)
    chat = getattr(msg, "chat", None) if msg else None
    frm = getattr(msg, "from_user", None) if msg else None

    chat_id = getattr(chat, "id", None) if chat else None
    from_user_id = getattr(frm, "id", None) if frm else None
    txt = getattr(msg, "text", None) if msg else None
    ent = getattr(msg, "entities", None) if msg else None

    # store last update (in-memory)
    async with _LAST_UPDATE_LOCK:
        _LAST_UPDATE["ts_utc"] = __import__("datetime").datetime.utcnow().isoformat() + "Z"
        _LAST_UPDATE["chat_id"] = chat_id
        _LAST_UPDATE["from_user_id"] = from_user_id
        _LAST_UPDATE["text"] = txt
        _LAST_UPDATE["update_id"] = getattr(upd, "update_id", None)

    _log(
        f"TG: update_id={getattr(upd,'update_id',None)} "
        f"chat_id={chat_id} from_user_id={from_user_id} "
        f"kind={'message' if msg else 'non-message'} "
        f"text={txt!r} entities={ent!r}"
    )

    # ensure PTB app started (idempotent)
    await init_bot()

    try:
        await app.process_update(upd)
    except Exception as e:
        _log(f"TG: app.process_update ERROR: {e!r}")
        raise

# ---- last update tracking (in-memory) ----
from datetime import datetime, timezone

_LAST_UPDATE = {"ts_utc": None, "chat_id": None, "from_user_id": None, "text": None, "update_id": None}
_LAST_UPDATE_LOCK = asyncio.Lock()

def get_last_update_snapshot() -> dict:
    # shallow copy for safe read
    return dict(_LAST_UPDATE)

async def _capture_last_update(upd) -> None:
    try:
        msg = getattr(upd, "message", None)
        chat = getattr(msg, "chat", None) if msg else None
        frm  = getattr(msg, "from_user", None) if msg else None
        async with _LAST_UPDATE_LOCK:
            _LAST_UPDATE["ts_utc"] = datetime.now(timezone.utc).isoformat()
            _LAST_UPDATE["update_id"] = getattr(upd, "update_id", None)
            _LAST_UPDATE["chat_id"] = getattr(chat, "id", None) if chat else None
            _LAST_UPDATE["from_user_id"] = getattr(frm, "id", None) if frm else None
            _LAST_UPDATE["text"] = getattr(msg, "text", None) if msg else None
    except Exception:
        # never crash app on telemetry
        return
