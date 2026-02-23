from .payments.ton.router import router as pay_router
from .manh.router import router as manh_router
from .tg_ops import router as tg_ops_router
from .tg_webhook import router as tg_router
from .api.router import router as api_router
from .api.router_diagnostic import router as diag_router
from .api.user import router as user_router

# TG_BUILDSTAMP_ENV_V1
import os as _os
import os
import sys
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy import inspect, text, create_engine

from .core.settings import settings
from .db import engine, get_db, SessionLocal
from .database.models import Base
from .tg_bot import (
    tg_get_app, init_bot, shutdown_bot, process_update,
    get_last_update_snapshot, _STARTED, _LAST_UPDATE, _with_db
)
from .manh.storage import get_db as manh_get_db
from .manh.service import get_balance, leaderboard, set_opt_in
from .payments.ton.service import list_invoices
from .payments.ton.price_feed import get_ton_ils_cached
from .payments.ton.withdrawals import create_withdrawal, get_user_withdrawals
from .manh.leaderboard import get_leaderboard
from .manh.referrals import set_referral_code, get_user_referrals
from .p2p.service import create_sell_order, create_buy_order, get_open_orders, cancel_order

# ---------- Logging Configuration ----------
logging.basicConfig(
    level=logging.DEBUG,  # ניתן לשנות ל-INFO בייצור
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ---------- Constants ----------
BUILD_STAMP = "2026-02-06T21:29:14+02:00"

def _build_stamp() -> str:
    return (_os.getenv("APP_BUILD_STAMP", "") or "").strip() or "unknown"

# ---------- Lifespan ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("APP: lifespan startup")
    
    # ✅ בדיקת חיבור למסד הנתונים
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("✅ DB connection successful")
    except Exception as e:
        logger.error(f"❌ DB connection failed: {e}", exc_info=True)
    
    # בדיקת קיום טבלאות (ללא מיגרציות)
    try:
        inspector = inspect(engine)
        if not inspector.has_table("chat_ids"):
            logger.info("APP: creating tables...")
            Base.metadata.create_all(bind=engine)
        else:
            logger.info("APP: tables already exist")
    except Exception as e:
        logger.error(f"APP: table check error: {e}", exc_info=True)

    try:
        await init_bot()
        logger.info("APP: bot initialized successfully")
    except Exception as e:
        logger.error("APP: init_bot error: " + repr(e), exc_info=True)

    yield

    logger.info("APP: lifespan shutdown")
    try:
        await shutdown_bot()
        logger.info("APP: bot shut down successfully")
    except Exception as e:
        logger.error("APP: shutdown_bot error: " + repr(e), exc_info=True)

# ---------- FastAPI app ----------
app = FastAPI(title="telegram-guardian", version="tg-guardian-1", lifespan=lifespan)

# ---------- Templates ----------
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)
logger.debug(f"Templates directory set to: {templates_dir}")

# ---------- Include routers ----------
app.include_router(user_router)
app.include_router(api_router)
app.include_router(diag_router)
app.include_router(tg_ops_router)
app.include_router(manh_router)
app.include_router(pay_router)
app.include_router(tg_router)
logger.debug(f"All routers included. Total routes: {len(app.router.routes)}")

# ---------- Middleware ----------
@app.middleware("http")
async def _no_cache_openapi(request, call_next):
    resp = await call_next(request)
    p = request.url.path
    if p in ("/openapi.json", "/docs", "/redoc"):
        resp.headers["Cache-Control"] = "no-store"
    return resp

# ---------- API endpoints ----------
@app.get('/api/user_data')
async def api_user_data(request: Request):
    logger.debug('api_user_data: called')
    user_id = 224223270
    balance = await _with_db(lambda db: get_balance(db, user_id))
    if isinstance(balance, dict):
        manh_value = balance['manh']
    else:
        manh_value = balance
    invoices = await _with_db(lambda db: list_invoices(db, user_id=user_id, limit=10))
    bucket_key = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    lb = await _with_db(lambda db: leaderboard(db, bucket_scope='daily', bucket_key=bucket_key, limit=10))
    return JSONResponse({
        'balance': manh_value,
        'invoices': invoices,
        'leaderboard': lb
    })

@app.post('/api/buy/{amount}')
async def api_buy(amount: int):
    logger.debug(f"api_buy called with amount={amount}")
    return JSONResponse({'status': 'ok'})

@app.post('/api/optin')
async def api_optin():
    logger.debug("api_optin called")
    with next(get_db()) as db:
        set_opt_in(db, 224223270, True)
    return JSONResponse({'status': 'ok'})

@app.post('/api/optout')
async def api_optout():
    logger.debug("api_optout called")
    with next(get_db()) as db:
        set_opt_in(db, 224223270, False)
    return JSONResponse({'status': 'ok'})

@app.post('/api/poll')
async def api_poll():
    logger.debug("api_poll called")
    return JSONResponse({'status': 'poll triggered'})

# ---------- Mini-app endpoints ----------
@app.get('/mini_app')
async def mini_app(request: Request):
    import os
    logger.debug('=== mini_app debug ===')
    logger.debug(f'Current working dir: {os.getcwd()}')
    if hasattr(templates, 'env') and hasattr(templates.env, 'loader'):
        try:
            paths = templates.env.loader.searchpath
            logger.debug(f'Loader searchpath: {paths}')
        except Exception as e:
            logger.debug(f'Cannot get searchpath: {e}')
    try:
        files = os.listdir(os.path.join(os.path.dirname(__file__), "templates"))
        logger.debug(f'Files in app/templates: {files}')
    except Exception as e:
        logger.debug(f'Cannot list app/templates: {e}')
    try:
        return templates.TemplateResponse('dashboard.html', {'request': request})
    except Exception as e:
        logger.error(f'!!! mini_app error: {e}', exc_info=True)
        return {'error': str(e)}

@app.get("/new_mini_app")
async def new_mini_app():
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    path = os.path.join(templates_dir, "mini_app.html")
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)

# ---------- Telegram diagnostics ----------
@app.get("/tg/diagnostics")
async def tg_diagnostics():
    app_instance = tg_get_app()
    handlers = {}
    if app_instance and hasattr(app_instance, 'handlers'):
        for group, hlist in app_instance.handlers.items():
            handlers[str(group)] = [str(h.callback.__name__) for h in hlist if hasattr(h, 'callback')]
    return {
        "bot_started": _STARTED,
        "handlers": handlers,
        "last_update": _LAST_UPDATE,
    }

# ---------- Health & info endpoints ----------
@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/healthz")
def healthz():
    return {
        "ok": True,
        "build_stamp": BUILD_STAMP,
        "app_title": getattr(app, "title", None),
        "app_version": getattr(app, "version", None),
        "file": __file__,
    }

@app.get("/version")
def get_version():
    import os
    return {
        "build_stamp": os.getenv("APP_BUILD_STAMP", "unknown"),
        "cachebust": os.getenv("CACHEBUST", "unknown"),
        "mini_app_updated": True
    }

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

@app.get("/ops/runtime")
def ops_runtime(token: str = Query(..., description="OPS token")):
    from .core.ops_auth import require_ops_token
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

@app.get("/ops/health")
def ops_health():
    from .core.ops_db import _ops_db_check, _ops_uptime_seconds
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

@app.get("/ops/build")
def ops_build():
    import subprocess
    def _git_sha_short() -> str:
        try:
            out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL, text=True).strip()
            return out or "unknown"
        except Exception:
            return "unknown"
    return {"git_sha": _git_sha_short()}

@app.get("/build")
def build_info():
    return {
        "app_build_stamp": os.getenv("APP_BUILD_STAMP", ""),
        "railway_git_commit_sha": os.getenv("RAILWAY_GIT_COMMIT_SHA", ""),
    }

# ---------- Debug template endpoints ----------
@app.get("/debug/templates")
def debug_templates():
    import os
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    files = os.listdir(templates_dir) if os.path.exists(templates_dir) else []
    mini_app_path = os.path.join(templates_dir, "mini_app.html")
    mini_app_exists = os.path.exists(mini_app_path)
    mini_app_content = ""
    if mini_app_exists:
        try:
            with open(mini_app_path, "r", encoding="utf-8") as f:
                mini_app_content = f.read()[:500]
        except:
            mini_app_content = "Error reading file"
    return {
        "templates_dir": templates_dir,
        "files": files,
        "mini_app_exists": mini_app_exists,
        "mini_app_preview": mini_app_content
    }

@app.get("/debug/templates-full")
def debug_templates_full():
    import os
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    result = {}
    if os.path.exists(templates_dir):
        for f in os.listdir(templates_dir):
            path = os.path.join(templates_dir, f)
            try:
                with open(path, "r", encoding="utf-8") as file:
                    result[f] = file.read()[:200]
            except:
                result[f] = "Error reading file"
    return result

# ---------- Post init ----------
logger.info(f"TG_GUARDIAN_MAIN_LOADED build={BUILD_STAMP} file={__file__}")
