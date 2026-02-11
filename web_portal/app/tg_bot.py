import os
import asyncio
from typing import Any, Optional

from telegram import Update
from telegram.error import TimedOut, NetworkError
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes
from telegram.request import HTTPXRequest

from .manh.storage import get_db
from .manh.service import set_opt_in, get_balance, leaderboard
def _log(msg: str) -> None:
    print(msg, flush=True)


def _tg_pick_token() -> str:
    for k in ("TELEGRAM_BOT_TOKEN", "BOT_TOKEN", "TELEGRAM_TOKEN", "TG_BOT_TOKEN"):
        v = (os.getenv(k) or "").strip()
        if v:
            return v
    return ""


_APP: Optional[Application] = None
_APP_LOCK = asyncio.Lock()
_STARTED = False

_LAST_UPDATE = {"ts_utc": None, "chat_id": None, "from_user_id": None, "text": None, "update_id": None}
_LAST_UPDATE_LOCK = asyncio.Lock()


def get_last_update_snapshot() -> dict:
    return dict(_LAST_UPDATE)


async def _safe_send(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str) -> None:
    for attempt in range(3):
        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
            return
        except (TimedOut, NetworkError) as e:
            _log(f"TG_SEND retry={attempt+1}/3 err={e!r}")
            await asyncio.sleep(0.6 * (attempt + 1))
        except Exception as e:
            _log(f"TG_SEND fatal err={e!r}")
            return


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = getattr(update, "effective_chat", None)
    if not chat:
        return
    # use unicode escape to avoid encoding glitches
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
    err = getattr(context, "error", None)
    _log(f"TG_PTB_ERROR: {err!r}")



async def _with_db(fn):
    it = get_db()
    db = next(it)
    try:
        return fn(db)
    finally:
        try:
            next(it)
        except StopIteration:
            pass

async def cmd_optin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = getattr(update, "effective_chat", None)
    user = getattr(update, "effective_user", None)
    if not chat or not user:
        return
    def _do(db):
        set_opt_in(db, int(user.id), True)
        return True
    await _with_db(_do)
    await _safe_send(context, chat.id, "✅ Opt-in enabled. You are now on the MANH leaderboard.")

async def cmd_optout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = getattr(update, "effective_chat", None)
    user = getattr(update, "effective_user", None)
    if not chat or not user:
        return
    def _do(db):
        set_opt_in(db, int(user.id), False)
        return True
    await _with_db(_do)
    await _safe_send(context, chat.id, "✅ Opt-out enabled. You are no longer on the MANH leaderboard.")

async def cmd_manh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = getattr(update, "effective_chat", None)
    user = getattr(update, "effective_user", None)
    if not chat or not user:
        return
    def _do(db):
        return get_balance(db, int(user.id))
    bal = await _with_db(_do)
    await _safe_send(context, chat.id, f"MANH={bal['manh']} | XP={bal['xp_points']}")

async def cmd_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = getattr(update, "effective_chat", None)
    if not chat:
        return
    scope = "daily"
    try:
        txt = getattr(getattr(update, "message", None), "text", "") or ""
        parts = txt.split()
        if len(parts) > 1 and parts[1].lower() in ("daily", "weekly"):
            scope = parts[1].lower()
    except Exception:
        pass

    # compute bucket key same as router
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from .manh.constants import LEADERBOARD_TZ
    tz = ZoneInfo(LEADERBOARD_TZ)
    now = datetime.now(tz)
    if scope == "daily":
        bucket_key = now.strftime("%Y-%m-%d")
    else:
        y, w, _ = now.isocalendar()
        bucket_key = f"{y}-W{w:02d}"

    def _do(db):
        return leaderboard(db, bucket_scope=scope, bucket_key=bucket_key, limit=10)
    rows = await _with_db(_do)

    if not rows:
        await _safe_send(context, chat.id, f"Leaderboard ({scope}) is empty right now.")
        return

    lines = [f"🏆 MANH Leaderboard ({scope}) {bucket_key}"]
    for i, r in enumerate(rows, start=1):
        name = r["username"] or str(r["user_id"])
        lines.append(f"{i}. {name} — {r['total_manh']}")
    await _safe_send(context, chat.id, "\n".join(lines))

def tg_get_app() -> Application:
    global _APP
    if _APP is not None:
        return _APP

    token = _tg_pick_token()
    if not token:
        raise RuntimeError("Telegram token missing (TELEGRAM_BOT_TOKEN/BOT_TOKEN/TELEGRAM_TOKEN/TG_BOT_TOKEN)")

    req = HTTPXRequest(connect_timeout=12.0, read_timeout=35.0, write_timeout=35.0, pool_timeout=12.0)

    app = ApplicationBuilder().token(token).request(req).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("whoami", cmd_whoami))
    app.add_handler(CommandHandler("optin", cmd_optin))
    app.add_handler(CommandHandler("optout", cmd_optout))
    app.add_handler(CommandHandler("manh", cmd_manh))
    app.add_handler(CommandHandler("leaderboard", cmd_leaderboard))
    app.add_error_handler(_on_error)

    _APP = app
    return app


async def init_bot() -> None:
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
        _log("TG_PTB: initialized+started (idempotent)")


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
        _log("TG_PTB: stopped+shutdown")


async def process_update(payload: dict[str, Any]) -> None:
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

    chat_id = getattr(chat, "id", None)
    from_user_id = getattr(frm, "id", None)

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

    try:
        await app.process_update(upd)
    except Exception as e:
        _log(f"WEBHOOK_PROCESS_ERROR: {e!r}")
        return
