# TG_TOKEN_PICKER_V1
def _tg_pick_token() -> str:
    for k in ("TELEGRAM_BOT_TOKEN","BOT_TOKEN","TELEGRAM_TOKEN","TG_BOT_TOKEN"):
        v = os.getenv(k, "").strip()
        if v:
            return v
    return ""
from __future__ import annotations

import os
from typing import Optional, Any
try:
    from telegram import Update
except Exception:  # pragma: no cover
    Update = object  # allows server startup even if dependency missing
from telegram.ext import Application, CommandHandler, ContextTypes

_app: Optional[Application] = None

def _log(msg: str) -> None:
    print(msg, flush=True)

def _token() -> str:
    return (_tg_pick_token() or "").strip()

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _log(f"TG: cmd_start from user={getattr(update.effective_user,'id',None)}")
    if not update.effective_chat:
        return
    await context.bot.send_message(chat_id=update.effective_chat.id, text="ط£آ¢ط¥â€œأ¢â‚¬آ¦ telegram-guardian alive. /whoami")

async def cmd_whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _log(f"TG: cmd_whoami from user={getattr(update.effective_user,'id',None)}")
    if not update.effective_chat:
        return
    u = update.effective_user
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"user_id={getattr(u,'id',None)} username={getattr(u,'username',None)}"
    )

def get_bot_app() -> Optional[Application]:
    global _app
    if _app is not None:
        return _app

    tok = _token()
    if not tok:
        _log("TG: TELEGRAM_BOT_TOKEN missing -> bot disabled")
        return None

    _app = Application.builder().token(tok).build()
    _app.add_handler(CommandHandler("start", cmd_start))
    _app.add_handler(CommandHandler("whoami", cmd_whoami))
    return _app

async def init_bot() -> None:
    app = get_bot_app()
    if app is None:
        return
    await app.initialize()
    await app.start()
    _log("TG: bot initialized+started (webhook mode)")

async def shutdown_bot() -> None:
    global _app
    if _app is None:
        return
    try:
        await _app.stop()
        await _app.shutdown()
        _log("TG: bot stopped+shutdown")
    finally:
        _app = None

async def process_update(payload: dict[str, Any]) -> None:
    app = get_bot_app()
    if app is None:
        _log("TG: process_update called but bot is None")
        return
    upd = Update.de_json(payload, app.bot)
    _log(f"TG: process_update update_id={getattr(upd,'update_id',None)}")
    await app.process_update(upd)