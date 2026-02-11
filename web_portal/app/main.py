from .tg_ops import router as tg_ops_router
# TG_BUILDSTAMP_ENV_V1
import os as _os
def _build_stamp() -> str:
    return (_os.getenv("APP_BUILD_STAMP","") or "").strip() or "unknown"
import os
import sys
from contextlib import asynccontextmanager

BUILD_STAMP = "2026-02-06T21:29:14+02:00"
from fastapi import Query, FastAPI

from .tg_webhook import router as tg_router
from .tg_bot import init_bot, shutdown_bot


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("APP: lifespan startup", flush=True)
    try:
        await init_bot()
    except Exception as e:
        print("APP: init_bot error: " + repr(e), flush=True)
    yield
    print("APP: lifespan shutdown", flush=True)
    try:
        await shutdown_bot()
    except Exception as e:
        print("APP: shutdown_bot error: " + repr(e), flush=True)
app = FastAPI(title="telegram-guardian", version="tg-guardian-1")
app.include_router(tg_ops_router)
app.include_router(tg_debug_router)
@app.middleware("http")
async def _no_cache_openapi(request, call_next):
    resp = await call_next(request)
    p = request.url.path
    if p == "/openapi.json" or p == "/docs" or p == "/redoc":
        resp.headers["Cache-Control"] = "no-store"
    return resp
app.include_router(tg_router)


@app.get("/health")
def health():
    return {"ok": True, "TG_SIGNATURE": "TG_SIGNATURE__ed99ea6"}


@app.get("/debug/runtime")
def debug_runtime():
    return {
        "cwd": os.getcwd(),
        "py": sys.version,
        "path0": sys.path[0],
        "env_has_token": bool((os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()),
        "env_has_secret": bool((os.getenv("TELEGRAM_WEBHOOK_SECRET") or "").strip()),
    }
@app.get("/__whoami")
def __whoami():
    import os, sys
    return {
        "module": __name__,
        "file": __file__,
        "cwd": os.getcwd(),
        "python": sys.version,
        "build_signature": os.getenv("BUILD_SIGNATURE", ""),
        "routes": [getattr(r, "path", None) for r in app.router.routes],
    }


print(f"TG_GUARDIAN_MAIN_LOADED build={BUILD_STAMP} file={__file__}")
@app.get("/healthz")
def healthz():
    return {
        "ok": True,
        "build_stamp": BUILD_STAMP,
        "app_title": getattr(app, "title", None),
        "app_version": getattr(app, "version", None),
        "file": __file__,
    }

print(f"TG_GUARDIAN_MAIN_LOADED build={BUILD_STAMP} file={__file__}")

@app.get("/ops/runtime")
def ops_runtime(token: str = Query(..., description="OPS token")):
    _ = require_ops_token(token)  # raises 401/503
    import os, sys
    return {
        "ok": True,
        "build_stamp": BUILD_STAMP,
        "app_title": getattr(app, "title", None),
        "app_version": getattr(app, "version", None),
        "cwd": os.getcwd(),
        "file": __file__,
        "python": sys.version,
        "route_count": len(getattr(app.router, "routes", [])),
    }

# TG_PTB_LIFECYCLE_V1
# Ensure python-telegram-bot Application is initialized for webhook mode (PTB v21+)
import os
from telegram.ext import Application

_TG_APP = None

def _tg_get_token() -> str:
    # prefer one canonical env, but allow legacy names (no secrets printed)
    for k in ("TELEGRAM_BOT_TOKEN","BOT_TOKEN","TELEGRAM_TOKEN","TG_BOT_TOKEN"):
        v = os.getenv(k, "").strip()
        if v:
            return v
    return ""

def tg_get_app() -> Application:
    global _TG_APP
    if _TG_APP is None:
        token = _tg_get_token()
        if not token:
            raise RuntimeError("Missing Telegram bot token env (TELEGRAM_BOT_TOKEN/BOT_TOKEN/...)")
        _TG_APP = Application.builder().token(token).build()
    return _TG_APP

@app.on_event("startup")
async def _tg_startup():
    try:
        tg_app = tg_get_app()
        await tg_app.initialize()
        await tg_app.start()
        print("TG_PTB: initialized+started")
    except Exception as e:
        print(f"TG_PTB_STARTUP_ERROR: {e!r}")

@app.on_event("shutdown")
async def _tg_shutdown():
    try:
        tg_app = tg_get_app()
        await tg_app.stop()
        await tg_app.shutdown()
        print("TG_PTB: stopped+shutdown")
    except Exception as e:
        print(f"TG_PTB_SHUTDOWN_ERROR: {e!r}")

# OPS_BUILD_INFO_V1
import subprocess

def _git_sha_short() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL, text=True).strip()
        return out or "unknown"
    except Exception:
        return "unknown"

@app.get("/ops/build")
def ops_build():
    # No secrets: only commit id + file path (already shown in healthz)
    return {"git_sha": _git_sha_short()}
import os

@app.get("/build")
def build_info():
    return {
        "app_build_stamp": os.getenv("APP_BUILD_STAMP", ""),
        "railway_git_commit_sha": os.getenv("RAILWAY_GIT_COMMIT_SHA", ""),
    }

# =========================
# OPS / HEALTH (DB CHECK)
# =========================
import os
import time
from datetime import datetime, timezone

from sqlalchemy import text, create_engine

_OPS_STARTED_AT = datetime.now(timezone.utc)
_OPS_STARTED_TS = time.time()

def _ops_uptime_seconds() -> int:
    return int(time.time() - _OPS_STARTED_TS)

def _ops_db_check() -> dict:
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        return {
            "ok": False,
            "skipped": True,
            "reason": "DATABASE_URL missing",
        }

    # try reuse app.db.engine if exists (preferred), else build a local engine
    eng = None
    try:
        from app.db import engine as _engine  # type: ignore
        eng = _engine
    except Exception:
        eng = create_engine(url, pool_pre_ping=True)

    out: dict = {"ok": False, "skipped": False}
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
            out["select1_ok"] = True

            # optional: check alembic version table (if migrations ran)
            try:
                v = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
                out["alembic_version"] = v
                out["alembic_version_ok"] = True
            except Exception as e:
                out["alembic_version_ok"] = False
                out["alembic_version_error"] = str(e)

        out["ok"] = True
        return out
    except Exception as e:
        out["error"] = str(e)
        return out

@app.get("/ops/health")
def ops_health():
    db = _ops_db_check()
    ok = bool(db.get("ok"))
    return {
        "ok": ok,
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": _ops_uptime_seconds(),
        "app_build_stamp": os.getenv("APP_BUILD_STAMP", ""),
        "railway_git_commit_sha": os.getenv("RAILWAY_GIT_COMMIT_SHA", ""),
        "db": db,
    }
