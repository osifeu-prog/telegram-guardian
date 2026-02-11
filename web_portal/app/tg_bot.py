import os
from typing import Any, Optional

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes


def _log(msg: str) -> None:
    print(msg, flush=True)


def _tg_pick_token() -> str:
    for k in ("TELEGRAM_BOT_TOKEN", "BOT_TOKEN", "TELEGRAM_TOKEN", "TG_BOT_TOKEN"):
        v = (os.getenv(k) or "").strip()
        if v:
            return v
    return ""


_APP: Optional[Application] = None


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = getattr(getattr(update, "effective_user", None), "id", None)
    _log(f"TG: cmd_start user={uid}")
    chat = getattr(update, "effective_chat", None)
    if not chat:
        return
    await context.bot.send_message(chat_id=chat.id, text="telegram-guardian alive ✅ (/whoami)")


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
        raise RuntimeError("Telegram token missing (checked TELEGRAM_BOT_TOKEN/BOT_TOKEN/TELEGRAM_TOKEN/TG_BOT_TOKEN)")

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("whoami", cmd_whoami))

    _APP = app
    return app


async def process_update(payload: dict[str, Any]) -> None:
    app = tg_get_app()

    upd = Update.de_json(payload, app.bot)
    if not upd:
        _log("TG: process_update: payload did not decode to Update")
        return

    _log(f"TG: process_update dispatch update_id={getattr(upd,'update_id',None)}")
    await app.process_update(upd)
