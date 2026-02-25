from .payments.ton.router import router as pay_router
from .manh.router import router as manh_router
from .tg_ops import router as tg_ops_router
# TG_BUILDSTAMP_ENV_V1
import os as _os
def _build_stamp() -> str:
    return (_os.getenv("APP_BUILD_STAMP","") or "").strip() or "unknown"
import os
import sys
from contextlib import asynccontextmanager

BUILD_STAMP = "2026-02-06T21:29:14+02:00"
from fastapi import Query, FastAPI, Request, Request, Request

from .tg_bot import tg_get_app, _APP, _LAST_UPDATE, _STARTED
from fastapi.templating import Jinja2Templates

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

import os
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

app.include_router(tg_ops_router)
app.include_router(manh_router)
app.include_router(pay_router)
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

# Using tg_bot.init_bot and tg_get_app from tg_botn@app.on_event("startup")
async def _tg_startup():
    try:
        tg_app = tg_get_app()n    from .tg_bot import init_botn    await init_bot()
        print("TG_PTB: initialized+started")
    except Exception as e:
        print(f"TG_PTB_STARTUP_ERROR: {e!r}")

@app.on_event("shutdown")
async def _tg_shutdown():
    try:
        tg_app = tg_get_app()n    from .tg_bot import shutdown_botn    await shutdown_bot()
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
        from web_portal.app.db import engine as _engine  # type: ignore
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

from fastapi import Request

from .tg_bot import tg_get_app, _APP, _LAST_UPDATE, _STARTED
from fastapi.responses import JSONResponse
from .manh.storage import get_db
from .manh.service import get_balance, leaderboard, set_opt_in
from .payments.ton.service import list_invoices
from .tg_bot import _with_db

@app.get('/api/user_data')
async def api_user_data(request: Request):
    print('api_user_data: called', flush=True)
    # ×œ×¦×•×¨×ڑ ×”×“×’×‍×”, × ×©×ھ×‍×© ×‘-user_id ×§×‘×•×¢ (×™×© ×œ×”×—×œ×™×£ ×‘×–×™×”×•×™ ×گ×‍×™×ھ×™)
    user_id = 224223270
    balance = await _with_db(lambda db: get_balance(db, user_id))
    invoices = await _with_db(lambda db: list_invoices(db, user_id=user_id, limit=10))
    from datetime import datetime, timezone
    bucket_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lb = await _with_db(lambda db: leaderboard(db, bucket_scope='daily', bucket_key=bucket_key, limit=10))
    return JSONResponse({
        'balance': balance,
        'invoices': invoices,
        'leaderboard': lb
    })

@app.post('/api/buy/{amount}')
async def api_buy(amount: int):
    return JSONResponse({'status': 'ok'})

@app.post('/api/optin')
async def api_optin():
    await _with_db(lambda db: set_opt_in(db, 224223270, True))
    return JSONResponse({'status': 'ok'})

@app.post('/api/optout')
async def api_optout():
    await _with_db(lambda db: set_opt_in(db, 224223270, False))
    return JSONResponse({'status': 'ok'})

@app.post('/api/poll')
async def api_poll():
    return JSONResponse({'status': 'poll triggered'})

@app.get('/mini_app')
async def mini_app(request: Request):
    import os
    print('=== mini_app debug ===', flush=True)
    print(f'Current working dir: {os.getcwd()}', flush=True)
    if hasattr(templates, 'env') and hasattr(templates.env, 'loader'):
        try:
            paths = templates.env.loader.searchpath
            print(f'Loader searchpath: {paths}', flush=True)
        except:
            print('Cannot get searchpath', flush=True)
    try:
        files = os.listdir(os.path.join(os.path.dirname(__file__), "templates"))
        print(f'Files in app/templates: {files}', flush=True)
    except Exception as e:
        print(f'Cannot list app/templates: {e}', flush=True)
    try:
        return templates.TemplateResponse('dashboard.html', {'request': request})
    except Exception as e:
        print(f'!!! mini_app error: {e}', flush=True)
        return {'error': str(e)}

@app.get("/tg/diagnostics")
async def tg_diagnostics():
    from .tg_bot import tg_get_app, _STARTED, _LAST_UPDATE
    app = tg_get_app()
    handlers = {}
    if app and hasattr(app, 'handlers'):
        for group, hlist in app.handlers.items():
            handlers[str(group)] = [str(h.callback.__name__) for h in hlist if hasattr(h, 'callback')]
    return {
        "bot_started": _STARTED,
        "handlers": handlers,
        "last_update": _LAST_UPDATE,
    }
        "bot_started": _STARTED,
        "handlers": handlers,
        "last_update": _LAST_UPDATE,
    }



