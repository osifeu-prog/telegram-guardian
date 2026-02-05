from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI

from .tg_webhook import router as tg_router
from .tg_bot import init_bot, shutdown_bot

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("APP: lifespan startup", flush=True)
    await init_bot()
    yield
    print("APP: lifespan shutdown", flush=True)
    await shutdown_bot()

app = FastAPI(title="telegram-guardian", lifespan=lifespan)
app.include_router(tg_router)

@app.get("/health")
def health():
    return {"ok": True, "TG_SIGNATURE": "TG_SIGNATURE__7efb7f4"}
@app.get("/debug/runtime")
def debug_runtime():
    import os, sys
    return {
        "cwd": os.getcwd(),
        "py": sys.version,
        "path0": sys.path[0],
        "env_has_token": bool((os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()),
        "env_has_secret": bool((os.getenv("TELEGRAM_WEBHOOK_SECRET") or "").strip()),
    }