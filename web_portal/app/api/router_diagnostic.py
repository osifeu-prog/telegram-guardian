from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.database.models import User, Invoice, Withdrawal, ChatId
from app.core.settings import settings
import os
from datetime import datetime

router = APIRouter(prefix="/diagnostic", tags=["diagnostic"])

def verify_secret(x_internal_secret: str = Header(..., alias="X-Internal-Secret")):
    expected = os.getenv("INTERNAL_API_SECRET") or os.getenv("INTERNAL_SIGNING_SECRET")
    if not expected or x_internal_secret != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

@router.get("/status")
async def diagnostic_status(authorized: bool = Depends(verify_secret), db: Session = Depends(get_db)):
    users_count = db.query(User).count()
    invoices_pending = db.query(Invoice).filter(Invoice.status == "pending").count()
    withdrawals_pending = db.query(Withdrawal).filter(Withdrawal.status == "pending").count()
    chat_ids_count = db.query(ChatId).count()
    return {
        "version": "2.0",
        "timestamp": datetime.utcnow().isoformat(),
        "counts": {
            "users": users_count,
            "pending_invoices": invoices_pending,
            "pending_withdrawals": withdrawals_pending,
            "chat_ids": chat_ids_count
        },
        "env": {
            "TON_NETWORK": os.getenv("TON_NETWORK", "unknown"),
            "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO")
        }
    }
