from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.manh.storage import get_db
from .price_feed import get_ton_ils_cached
from .toncenter import TonCenter
from .service import (
    create_invoice,
    list_invoices,
    poll_and_confirm_invoices,
    require_internal_secret,
    create_withdrawal_request,
    list_withdrawals,
)

router = APIRouter(prefix="/pay", tags=["payments"])

def _parse_ils_amount(raw: str) -> Decimal:
    s = (raw or "").strip()
    s = s.replace(",", ".")
    if not s:
        raise HTTPException(status_code=400, detail="ils_amount is required")
    try:
        v = Decimal(s)
    except InvalidOperation:
        raise HTTPException(status_code=400, detail="ils_amount must be a valid decimal")
    if v <= 0:
        raise HTTPException(status_code=400, detail="ils_amount must be > 0")
    return v.quantize(Decimal("0.01"))


@router.post("/invoice")
def pay_create_invoice(
    user_id: int,
    username: Optional[str] = None,
    ils_amount: str = "10",
    db: Session = Depends(get_db),
):
    try:
        amt = _parse_ils_amount(ils_amount)
        q = get_ton_ils_cached()
        inv = create_invoice(db, user_id=user_id, username=username, ils_amount=amt, ton_ils_rate=q.ton_ils)
        return {"ok": True, "price": {"ton_ils": str(q.ton_ils), "source": q.source}, "invoice": inv.__dict__}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/invoices")
def pay_list_invoices(user_id: int, db: Session = Depends(get_db)):
    return {"ok": True, "invoices": list_invoices(db, user_id=user_id)}


@router.post("/ton/poll")
def pay_poll_ton(
    x_internal_secret: Optional[str] = Header(default=None, alias="X-Internal-Secret"),
    db: Session = Depends(get_db),
):
    try:
        require_internal_secret(x_internal_secret)
    except Exception:
        raise HTTPException(status_code=401, detail="unauthorized")

    result = poll_and_confirm_invoices(db)
    return res


@router.post("/withdraw")
def pay_withdraw_request(
    user_id: int,
    username: Optional[str],
    amount_manh: str,
    target_ton_address: str,
    db: Session = Depends(get_db),
):
    try:
        amt = Decimal(amount_manh)
        return create_withdrawal_request(db, user_id=user_id, username=username, amount_manh=amt, target_ton_address=target_ton_address)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/withdrawals")
def pay_list_withdrawals(user_id: int, db: Session = Depends(get_db)):
    return {"ok": True, "withdrawals": list_withdrawals(db, user_id=user_id)}




