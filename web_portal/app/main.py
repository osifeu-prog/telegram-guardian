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