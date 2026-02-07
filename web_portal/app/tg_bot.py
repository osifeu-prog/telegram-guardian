# TG_ENV_PRESENT_V1
def _tg_env_present() -> None:
    keys = ("TELEGRAM_BOT_TOKEN","BOT_TOKEN","TELEGRAM_TOKEN","TG_BOT_TOKEN","TELEGRAM_WEBHOOK_SECRET")
    present = {k: bool(os.getenv(k, "").strip()) for k in keys}
    print(f"TG_ENV_PRESENT={present}")
# TG_ENV_PRESENCE_LOG_V1
def _log_token_env_presence():
    keys = ("TELEGRAM_BOT_TOKEN","BOT_TOKEN","TELEGRAM_TOKEN","TG_BOT_TOKEN")
    present = {k: bool(os.getenv(k, "").strip()) for k in keys}
    # no values printed
    print(f"TG_ENV_PRESENT={present}")
# TG_TOKEN_PICKER_V2
def _tg_pick_token() -> str:
    for k in ("TELEGRAM_BOT_TOKEN","BOT_TOKEN","TELEGRAM_TOKEN","TG_BOT_TOKEN"):
        v = os.getenv(k, "").strip()
        if v:
            return v
    return ""
# TG_PTB_SINGLETON_V2
# Single source of truth for python-telegram-bot Application (webhook mode)
from telegram.ext import Application

_TG_APP: Application | None = None

def tg_get_app() -> Application:
    global _TG_APP
    if _TG_APP is None:
        tok = _token()
        if not tok:
            raise RuntimeError("Telegram token missing (checked TELEGRAM_BOT_TOKEN/BOT_TOKEN/TELEGRAM_TOKEN/TG_BOT_TOKEN)")
        _TG_APP = Application.builder().token(tok).build()
    return _TG_APP

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
    return (_tg_pick_token() or '').strip()


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _log(f"TG: cmd_start from user={getattr(update.effective_user,'id',None)}")
    if not update.effective_chat:
        return
    await context.bot.send_message(chat_id=update.effective_chat.id, text="ط·آ·ط¢آ·ط·آ¢ط¢آ·ط·آ·ط¢آ¢ط·آ¢ط¢آ·ط·آ·ط¢آ·ط·آ¢ط¢آ¢ط·آ·ط¢آ¢ط·آ¢ط¢آ·ط·آ·ط¢آ·ط·آ¢ط¢آ·ط·آ·ط¢آ¢ط·آ¢ط¢آ¢ط·آ·ط¢آ·ط·آ¢ط¢آ¢ط·آ·ط¢آ¢ط·آ¢ط¢آ£ط·آ·ط¢آ·ط·آ¢ط¢آ·ط·آ·ط¢آ¢ط·آ¢ط¢آ·ط·آ·ط¢آ·ط·آ¢ط¢آ¢ط·آ·ط¢آ¢ط·آ¢ط¢آ¢ط·آ·ط¢آ·ط·آ¢ط¢آ·ط·آ·ط¢آ¢ط·آ¢ط¢آ¢ط·آ·ط¢آ·ط·آ¢ط¢آ¢ط·آ·ط¢آ¢ط·آ¢ط¢آ¢ط·آ·ط¢آ·ط·آ¢ط¢آ·ط·آ·ط¢آ¢ط·آ¢ط¢آ·ط·آ·ط¢آ·ط·آ¢ط¢آ¢ط·آ·ط¢آ¢ط·آ¢ط¢آ·ط·آ·ط¢آ·ط·آ¢ط¢آ·ط·آ·ط¢آ¢ط·آ¢ط¢آ¢ط·آ·ط¢آ·ط·آ¢ط¢آ¢ط·آ·ط¢آ¢ط·آ¢ط¢آ¥ط·آ·ط¢آ·ط·آ¢ط¢آ·ط·آ·ط¢آ¢ط·آ¢ط¢آ£ط·آ·ط¢آ·ط·آ¢ط¢آ¢ط·آ·ط¢آ¢ط·آ¢ط¢آ¢ط·آ·ط¢آ·ط·آ¢ط¢آ£ط·آ·ط¢آ¢ط·آ¢ط¢آ¢ط·آ·ط¢آ£ط·آ¢ط¢آ¢ط·آ£ط¢آ¢ط£آ¢أ¢â€ڑآ¬ط¹â€کط·آ¢ط¢آ¬ط·آ·ط¢آ¹ط£آ¢أ¢â€ڑآ¬ط¹آ©ط·آ·ط¢آ·ط·آ¢ط¢آ¢ط·آ·ط¢آ¢ط·آ¢ط¢آ¬ط·آ·ط¢آ·ط·آ¢ط¢آ·ط·آ·ط¢آ¢ط·آ¢ط¢آ¥ط·آ·ط¢آ£ط·آ¢ط¢آ¢ط·آ£ط¢آ¢ط£آ¢أ¢â€ڑآ¬ط¹â€کط·آ¢ط¢آ¬ط·آ·ط¢آ¥ط£آ¢أ¢â€ڑآ¬ط¥â€œط·آ·ط¢آ·ط·آ¢ط¢آ·ط·آ·ط¢آ¢ط·آ¢ط¢آ·ط·آ·ط¢آ·ط·آ¢ط¢آ¢ط·آ·ط¢آ¢ط·آ¢ط¢آ£ط·آ·ط¢آ·ط·آ¢ط¢آ·ط·آ·ط¢آ¢ط·آ¢ط¢آ¢ط·آ·ط¢آ·ط·آ¢ط¢آ¢ط·آ·ط¢آ¢ط·آ¢ط¢آ¢ط·آ·ط¢آ·ط·آ¢ط¢آ·ط·آ·ط¢آ¢ط·آ¢ط¢آ£ط·آ·ط¢آ·ط·آ¢ط¢آ¢ط·آ·ط¢آ¢ط·آ¢ط¢آ¢ط·آ·ط¢آ·ط·آ¢ط¢آ£ط·آ·ط¢آ¢ط·آ¢ط¢آ¢ط·آ·ط¢آ£ط·آ¢ط¢آ¢ط·آ£ط¢آ¢ط£آ¢أ¢â‚¬ع‘ط¢آ¬ط·آ¹أ¢â‚¬ع©ط·آ·ط¢آ¢ط·آ¢ط¢آ¬ط·آ·ط¢آ·ط·آ¢ط¢آ¹ط·آ£ط¢آ¢ط£آ¢أ¢â‚¬ع‘ط¢آ¬ط·آ¹ط¢آ©ط·آ·ط¢آ·ط·آ¢ط¢آ·ط·آ·ط¢آ¢ط·آ¢ط¢آ¢ط·آ·ط¢آ·ط·آ¢ط¢آ¢ط·آ·ط¢آ¢ط·آ¢ط¢آ¬ط·آ·ط¢آ·ط·آ¢ط¢آ·ط·آ·ط¢آ¢ط·آ¢ط¢آ·ط·آ·ط¢آ·ط·آ¢ط¢آ¢ط·آ·ط¢آ¢ط·آ¢ط¢آ¢ط·آ·ط¢آ·ط·آ¢ط¢آ·ط·آ·ط¢آ¢ط·آ¢ط¢آ¢ط·آ·ط¢آ·ط·آ¢ط¢آ¢ط·آ·ط¢آ¢ط·آ¢ط¢آ¦ telegram-guardian alive. /whoami")

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
        _log("TG: bot token missing -> bot disabled (checked TELEGRAM_BOT_TOKEN/BOT_TOKEN/TELEGRAM_TOKEN/TG_BOT_TOKEN)")
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
    await tg_get_app().process_update(upd)

_tg_env_present()
