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