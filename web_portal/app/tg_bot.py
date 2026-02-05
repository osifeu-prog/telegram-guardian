from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Optional

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

_app: Optional[Application] = None

def _token() -> str:
    return (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()

def _log(msg: str) -> None:
    # stdout -> Railway logs
    print(msg, flush=True)

def _admin_id() -> Optional[int]:
    raw = (os.getenv("ADMIN_TELEGRAM_ID") or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except Exception:
        return None

def _is_admin(user_id: Optional[int]) -> bool:
    aid = _admin_id()
    return bool(aid is not None and user_id is not None and int(user_id) == int(aid))

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return
    me = update.effective_user
    uid = me.id if me else None
    txt = (
        "✅ telegram-guardian is alive.\n"
        f"your_id={uid}\n"
        "Commands:\n"
        "/status\n"
        "/whoami\n"
        "/admin_status (requires ADMIN_TELEGRAM_ID env)\n"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=txt)

async def cmd_whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return
    u = update.effective_user
    txt = f"user_id={getattr(u,'id',None)} username={getattr(u,'username',None)} name={getattr(u,'first_name',None)}"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=txt)

def _db_ready() -> tuple[bool, Optional[str], Optional[str]]:
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
        return False, repr(e), None

def _redis_ready() -> tuple[Optional[bool], Optional[str]]:
    try:
        ru = (os.getenv("REDIS_URL") or "").strip()
        if not ru:
            return None, None
        import redis
        r = redis.from_url(ru, decode_responses=True)
        r.ping()
        return True, None
    except Exception as e:
        return False, repr(e)

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return

    db_ok, db_err, alembic_v = _db_ready()
    r_ok, r_err = _redis_ready()

    now = datetime.now(timezone.utc).isoformat()
    lines = [f"🧪 status @ {now}", f"DB: {db_ok}"]
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
        await context.bot.send_message(chat_id=update.effective_chat.id, text="403 (set ADMIN_TELEGRAM_ID)")
        return

    db_ok, db_err, alembic_v = _db_ready()
    r_ok, r_err = _redis_ready()
    lines = [
        "🔐 admin_status",
        f"DB_OK={db_ok}",
        f"ALEMBIC={alembic_v}",
        f"DB_ERR={db_err}",
        f"REDIS_OK={r_ok}",
        f"REDIS_ERR={r_err}",
    ]
    await context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join([x for x in lines if x is not None]))

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
    _app.add_handler(CommandHandler("status", cmd_status))
    _app.add_handler(CommandHandler("whoami", cmd_whoami))
    _app.add_handler(CommandHandler("admin_status", cmd_admin_status))
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
        return
    upd = Update.de_json(payload, app.bot)
    await app.process_update(upd)