"""
Telegram bot module for Telegram Guardian.
Aggregates all handlers from bot_handlers package.
"""

import logging
import os
import sys
import time
import functools
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

import redis.asyncio as redis
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from sqlalchemy import text

from app.core.settings import settings
from app.db import SessionLocal
from app.database.models import SecurityLog

# יבוא כל ה-handlers מהתיקייה החדשה
from .bot_handlers.start import cmd_start
from .bot_handlers.help import cmd_help, cmd_all
from .bot_handlers.menu import cmd_menu, menu_callback
# TODO: הוסף יבוא לשאר ה-handlers לפי הצורך

# ---------- Logging Configuration ----------
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler('bot.log', maxBytes=10*1024*1024, backupCount=5)
    ]
)
logger = logging.getLogger(__name__)

# -------------------- Global State --------------------
_STARTED: Optional[str] = None
_LAST_UPDATE: Optional[str] = None
_application: Optional[Application] = None

# -------------------- Redis Client (Rate Limiting) --------------------
_redis_client: Optional[redis.Redis] = None

async def get_redis():
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        try:
            _redis_client = await redis.from_url(redis_url)
            await _redis_client.ping()
            logger.info(f"Redis connected: {redis_url}")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            _redis_client = None
    return _redis_client

# ---------- Helper Decorator ----------
def _with_db(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        db = SessionLocal()
        try:
            return await func(update, context, db)
        finally:
            db.close()
    return wrapper

def _safe_decimal(value) -> str:
    try:
        d = Decimal(str(value))
        return format(d, 'f')
    except (InvalidOperation, ValueError, TypeError):
        return '0'

# ---------- Rate Limiting Decorator ----------
def rate_limit(key_prefix: str, max_calls: int, period: int):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            key = f"rate_limit:{key_prefix}:{user_id}"
            r = await get_redis()
            if not r:
                return await func(update, context, *args, **kwargs)
            now = time.time()
            pipe = r.pipeline()
            pipe.zadd(key, {str(now): now})
            pipe.zremrangebyscore(key, 0, now - period)
            pipe.zcard(key)
            pipe.expire(key, period)
            results = await pipe.execute()
            current_calls = results[3]
            if current_calls > max_calls:
                try:
                    db = SessionLocal()
                    log = SecurityLog(
                        event_type='rate_limit_exceeded',
                        user_id=user_id,
                        details={'command': key_prefix, 'calls': current_calls, 'limit': max_calls, 'period': period}
                    )
                    db.add(log)
                    db.commit()
                    db.close()
                except Exception as e:
                    logger.error(f"Failed to log rate limit event: {e}")
                security_group = os.getenv("TG_SECURITY_GROUP")
                if security_group:
                    try:
                        await context.bot.send_message(
                            chat_id=security_group,
                            text=f"Rate limit exceeded: {key_prefix} by user {user_id} ({current_calls} calls in {period}s)"
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify security group: {e}")
                await update.message.reply_text("Too many requests. Please try again later.")
                return
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator

async def log_security_event(db, event_type: str, user_id: int = None, details: dict = None):
    log = SecurityLog(
        event_type=event_type,
        user_id=user_id,
        details=details
    )
    db.add(log)
    db.commit()

# ---------- Initialization ----------
async def init_bot():
    global _STARTED, _application
    _STARTED = datetime.now().isoformat()
    app = Application.builder().token(settings.BOT_TOKEN).build()

    # --- תיקון אוטומטי של טור id (ניתן להסיר אחרי ריצה מוצלחת) ---
    try:
        db = SessionLocal()
        db.execute(text("ALTER TABLE users ALTER COLUMN id TYPE BIGINT;"))
        db.commit()
        logger.info("Column 'id' in table 'users' altered to BIGINT successfully.")
    except Exception as e:
        logger.warning(f"Could not alter column (might already be BIGINT): {e}")
        db.rollback()
    finally:
        db.close()
    # -------------------------------------------------------------

    # הוספת כל ה-handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("all", cmd_all))
    # TODO: הוסף את שאר ה-handlers

    await app.initialize()
    _application = app
    logger.info("Bot initialized successfully")
    return app

async def shutdown_bot():
    global _application
    if _application:
        await _application.shutdown()
        _application = None
        logger.info("Bot shut down")

def tg_get_app():
    return _application

async def process_update(update_dict: dict) -> dict:
    global _LAST_UPDATE
    _LAST_UPDATE = datetime.now().isoformat()
    if _application is None:
        logger.error("process_update called but bot not initialized")
        return {"ok": False, "error": "Bot not initialized"}
    update = Update.de_json(update_dict, _application.bot)
    await _application.process_update(update)
    return {"ok": True}

def get_last_update_snapshot():
    return {"started": _STARTED, "last_update": _LAST_UPDATE}

