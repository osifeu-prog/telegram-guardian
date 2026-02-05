from __future__ import annotations

import os
from typing import Optional, Any
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# We build ONE bot application for webhook processing.
_app: Optional[Application] = None

def _token() -> str:
    return (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()

def _log_level() -> str:
    return (os.getenv("LOG_LEVEL") or "INFO").strip().upper()

def _is_admin(user_id: Optional[int]) -> bool:
    # Optional allowlist. If not set, admin-only commands are disabled (safer).
    raw = (os.getenv("ADMIN_TELEGRAM_ID") or "").strip()
    if not raw:
        return False
    try:
        return user_id is not None and int(raw) == int(user_id)
    except Exception:
        return False

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        print("CMD_START: no effective_chat")
        return
    me = update.effective_user
    uid = me.id if me else None
    txt = (
        "telegram-guardian webhook bot is alive.\n"
        f"your_id={uid}\n"
        "Commands:\n"
        "/status\n"
        "/whoami\n"
        "/admin_status\n"
    )
    try:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=txt)
        print(f"CMD_START: replied chat_id={update.effective_chat.id} user_id={uid}")
    except Exception as e:
        print("CMD_START_SEND_ERROR:", repr(e))async def cmd_whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        print("CMD_WHOAMI: no effective_chat")
        return
    u = update.effective_user
    txt = f"user_id={getattr(u,'id',None)} username={getattr(u,'username',None)} name={getattr(u,'first_name',None)}"
    try:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=txt)
        print(f"CMD_WHOAMI: replied chat_id={update.effective_chat.id}")
    except Exception as e:
        print("CMD_WHOAMI_SEND_ERROR:", repr(e))def _db_ready() -> tuple[bool, Optional[str], Optional[str]]:
    # returns: ok, error, alembic_version
    try:
        from sqlalchemy import text
        from .db import get_engine
        with get_engine().connect() as c:
            c.execute(text("SELECT 1"))
            v = None
            try:
                v = c.execute(text("SELECT version_num FROM alembic_version")).scalar()
            except Exception:
                v = None
        return True, None, (str(v) if v is not None else None)
    except Exception as e:
        return False, str(e), None

def _redis_ready() -> tuple[Optional[bool], Optional[str]]:
    try:
        ru = (os.getenv("REDIS_URL") or "").strip()
        if not ru:
            return None, None  # optional
        import redis
        r = redis.from_url(ru, decode_responses=True)
        r.ping()
        return True, None
    except Exception as e:
        return False, str(e)

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return

    db_ok, db_err, alembic_v = _db_ready()
    r_ok, r_err = _redis_ready()

    now = datetime.now(timezone.utc).isoformat()
    lines = [f"ظ‹ع؛ع؛آ¢ status @ {now}", f"DB: {db_ok}"]
    if alembic_v:
        lines.append(f"Alembic: {alembic_v}")
    if db_err:
        lines.append(f"DB_ERROR: {db_err}")

    if r_ok is None:
        lines.append("Redis: (not configured)")
    else:
        lines.append(f"Redis: {r_ok}")
        if r_err:
            lines.append(f"REDIS_ERROR: {r_err}")

    await context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join(lines))

async def cmd_admin_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return
    uid = update.effective_user.id if update.effective_user else None
    if not _is_admin(uid):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="403 (set ADMIN_TELEGRAM_ID to enable admin commands)")
        return

    # extended info (still no secrets)
    db_ok, db_err, alembic_v = _db_ready()
    r_ok, r_err = _redis_ready()
    lines = [
        "ظ‹ع؛â€‌ع¯ admin_status",
        f"DB_OK={db_ok}",
        f"ALEMBIC={alembic_v}",
        f"DB_ERR={db_err}",
        f"REDIS_OK={r_ok}",
        f"REDIS_ERR={r_err}",
        f"ENV: LOG_LEVEL={_log_level()}",
    ]
    await context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join([x for x in lines if x is not None]))

def get_bot_app() -> Optional[Application]:
    global _app
    if _app is not None:
        return _app

    tok = _token()
    if not tok:
        return None

    _app = Application.builder().token(tok).build()
    _app.add_handler(CommandHandler("start", cmd_start))
    _app.add_handler(CommandHandler("status", cmd_status))
    _app.add_handler(CommandHandler("whoami", cmd_whoami))
    _app.add_handler(CommandHandler("admin_status", cmd_admin_status))
    return _app

async def init_bot() -> None:
    tok = _token()
    print(f"BOT_INIT: token_set={bool(tok)}")app = get_bot_app()
    if app is None:
        return
    # Initialize PTB internals for webhook processing (no polling/getUpdates)
    await app.initialize()
    await app.start()
async def shutdown_bot() -> None:
    global _app
    if _app is None:
        return
    try:
        await _app.stop()
        await _app.shutdown()
    finally:
        _app = None
async def process_update(payload: dict[str, Any]) -> None:app = get_bot_app()
    if app is None:
        return
    # Convert dict -> telegram.Update and process via PTB
        try:
        upd = Update.de_json(payload, app.bot)
    except Exception as e:
        print("PROCESS_UPDATE_DEJSON_ERROR:", repr(e))
        return

    try:
        await app.process_update(upd)
        print(f"PROCESS_UPDATE_OK: update_id={uid}")
    except Exception as e:
        print("PROCESS_UPDATE_HANDLER_ERROR:", repr(e))