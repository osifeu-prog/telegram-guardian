import os
from fastapi import APIRouter, Request
from .tg_bot import process_update

router = APIRouter()

@router.post("/tg/webhook")
async def tg_webhook(request: Request):
    print(">>> tg_webhook called", flush=True)
    payload = await request.json()
    print(f">>> payload: {payload}", flush=True)
    await process_update(payload)
    print(">>> process_update finished", flush=True)
    return {"ok": True}
