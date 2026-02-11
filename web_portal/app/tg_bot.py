import os
import asyncio
from typing import Any, Optional

from telegram import Update
from telegram.error import TimedOut, NetworkError
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from telegram.request import HTTPXRequest


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


async def _safe_send(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str) -> None:
    """
    Send message with short retries so webhook flow isn't brittle.
    Never crash the webhook due to Telegram transient network issues.
    """
    # quick retries (total ~2-3s extra worst case)
    for attempt in range(3):
        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
            return
        except (TimedOut, NetworkError) as e:
            _log(f"TG_SEND retry={attempt+1}/3 err={e!r}")
            await asyncio.sleep(0.5 * (attempt + 1))
        except Exception as e:
            _log(f"TG_SEND fatal err={e!r}")
            return


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = getattr(update, "effective_chat", None)
    if not chat:
        return
    # use unicode escape to avoid mojibake forever
    await _safe_send(context, chat.id, "telegram-guardian alive \u2705  (/whoami)")


async def cmd_whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = getattr(update, "effective_chat", None)
    if not chat:
        return
    try:
        me = await context.bot.get_me()
        await _safe_send(context, chat.id, f"bot=@{me.username} id={me.id}")
    except Exception as e:
        _log(f"WHOAMI error: {e!r}")


async def _on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    # PTB global error handler
    err = getattr(context, "error", None)
    _log(f"TG_PTB_ERROR: {err!r}")


def tg_get_app() -> Application:
    global _APP
    if _APP is not None:
        return _APP

    token = _tg_pick_token()
    if not token:
        raise RuntimeError(
            "Telegram token missing (checked TELEGRAM_BOT_TOKEN/BOT_TOKEN/TELEGRAM_TOKEN/TG_BOT_TOKEN)"
        )

    # IMPORTANT: request timeouts tuned for webhook usage on Railway
    req = HTTPXRequest(
        connect_timeout=8.0,
        read_timeout=20.0,
        write_timeout=20.0,
        pool_timeout=8.0,
    )

    app = ApplicationBuilder().token(token).request(req).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("whoami", cmd_whoami))
    app.add_error_handler(_on_error)

    _APP = app
    return app


async def init_bot() -> None:
    """
    Ensures PTB Application is initialized and started exactly once (idempotent).
    PTB may raise RuntimeError("already running") on repeated calls.
    """
    global _STARTED
    async with _APP_LOCK:
        if _STARTED:
            return

        app = tg_get_app()

        try:
            await app.initialize()
        except RuntimeError as e:
            if "already" not in str(e).lower():
                raise

        try:
            await app.start()
        except RuntimeError as e:
            if "already running" not in str(e).lower():
                raise

        _STARTED = True
        _log("TG_PTB: initialized+started (init_bot, idempotent)")


async def shutdown_bot() -> None:
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
    await init_bot()
    app = tg_get_app()

    upd = Update.de_json(payload, app.bot)
    if not upd:
        _log("TG: process_update: payload did not decode to Update")
        return

    msg = getattr(upd, "message", None)
    txt = getattr(msg, "text", None) if msg else None
    ent = getattr(msg, "entities", None) if msg else None
    chat = getattr(msg, "chat", None) if msg else None
    frm = getattr(msg, "from_user", None) if msg else None

    _log(
        f"TG: update_id={getattr(upd,'update_id',None)} "
        f"chat_id={getattr(chat,'id',None)} from_user_id={getattr(frm,'id',None)} "
        f"kind={'message' if msg else 'non-message'} "
        f"text={txt!r} entities={ent!r}"
    )

    try:
        await app.process_update(upd)
    except Exception as e:
        _log(f"TG: app.process_update ERROR: {e!r}")
        # don't re-raise: webhook should stay healthy
        return
