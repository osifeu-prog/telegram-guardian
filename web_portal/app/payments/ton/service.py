from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_CEILING
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.manh.service import award_manh


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _signing_secret() -> str:
    s = (os.getenv("INTERNAL_SIGNING_SECRET") or "").strip()
    if not s:
        raise RuntimeError("INTERNAL_SIGNING_SECRET missing")
    return s


def _hmac_hex(msg: str) -> str:
    key = bytes.fromhex(_signing_secret()) if all(c in "0123456789abcdef" for c in _signing_secret().lower()) and len(_signing_secret()) >= 32 else _signing_secret().encode("utf-8")
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).hexdigest()


def _treasury_address() -> str:
    v = (os.getenv("TON_TREASURY_ADDRESS") or "").strip()
    if not v:
        raise RuntimeError("TON_TREASURY_ADDRESS missing")
    return v


def _manh_price_ils() -> Decimal:
    v = (os.getenv("MANH_PRICE_ILS") or "1.00").strip()
    return Decimal(v)


def _min_buy_for_withdrawal() -> Decimal:
    v = (os.getenv("MIN_BUY_FOR_WITHDRAWAL") or "10").strip()
    return Decimal(v)


def _withdrawals_mode() -> str:
    return (os.getenv("WITHDRAWALS_MODE") or "manual").strip().lower()


def require_internal_secret(x_internal_secret: Optional[str]) -> None:
    # Guard sensitive endpoints (/poll, admin approvals, etc.)
    expected = (os.getenv("INTERNAL_API_SECRET") or "").strip()
    if not expected:
        # allow using INTERNAL_SIGNING_SECRET as fallback guard if INTERNAL_API_SECRET not set
        expected = _signing_secret()
    if not x_internal_secret or x_internal_secret.strip() != expected:
        raise PermissionError("unauthorized")


@dataclass
class InvoiceCreated:
    invoice_id: str
    user_id: int
    ils_amount: Decimal
    manh_amount: Decimal
    ton_amount: Decimal
    comment: str
    expires_at_utc: str
    treasury_address: str


def _make_invoice_id(user_id: int) -> str:
    base = f"{user_id}|{_utcnow().isoformat()}|{os.urandom(8).hex()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]


def create_invoice(
    db: Session,
    *,
    user_id: int,
    username: Optional[str],
    ils_amount: Decimal,
    ton_ils_rate: Decimal,
    ttl_minutes: int = 15,
) -> InvoiceCreated:
    if ils_amount <= 0:
        raise ValueError("ils_amount must be > 0")

    price = _manh_price_ils()
    manh_amount = (ils_amount / price).quantize(Decimal("0.000000001"))
    # ton amount: ILS / (ILS per TON)
    ton_amount = (ils_amount / ton_ils_rate).quantize(Decimal("0.000000001"), rounding=ROUND_CEILING)

    invoice_id = _make_invoice_id(user_id)
    exp = _utcnow() + timedelta(minutes=ttl_minutes)

    sig = _hmac_hex(f"{invoice_id}|{user_id}|{str(ils_amount)}|{exp.isoformat()}")
    comment = f"MANH|{invoice_id}|{sig[:16]}"

    db.execute(
        text(
            """
            INSERT INTO manh_invoices(invoice_id, user_id, username, ils_amount, manh_amount, ton_amount,
                                      ton_ils_rate, ton_treasury_address, comment, sig16, status, created_at, expires_at)
            VALUES (:id, :u, :name, :ils, :manh, :ton, :rate, :addr, :cmt, :sig16, 'PENDING', now(), :exp)
            """
        ),
        {
            "id": invoice_id,
            "u": user_id,
            "name": username,
            "ils": str(ils_amount),
            "manh": str(manh_amount),
            "ton": str(ton_amount),
            "rate": str(ton_ils_rate),
            "addr": _treasury_address(),
            "cmt": comment,
            "sig16": sig[:16],
            "exp": exp,
        },
    )
    db.commit()

    return InvoiceCreated(
        invoice_id=invoice_id,
        user_id=user_id,
        ils_amount=ils_amount,
        manh_amount=manh_amount,
        ton_amount=ton_amount,
        comment=comment,
        expires_at_utc=exp.isoformat(),
        treasury_address=_treasury_address(),
    )


def list_invoices(db: Session, *, user_id: int, limit: int = 10) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT invoice_id, status, ils_amount::numeric, manh_amount::numeric, ton_amount::numeric,
                   comment, created_at, expires_at, confirmed_at
            FROM manh_invoices
            WHERE user_id=:u
            ORDER BY created_at DESC
            LIMIT :lim
            """
        ),
        {"u": user_id, "lim": limit},
    ).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "invoice_id": r[0],
                "status": r[1],
                "ils_amount": str(r[2]),
                "manh_amount": str(r[3]),
                "ton_amount": str(r[4]),
                "comment": r[5],
                "created_at": r[6].isoformat() if r[6] else None,
                "expires_at": r[7].isoformat() if r[7] else None,
                "confirmed_at": r[8].isoformat() if r[8] else None,
            }
        )
    return out


def _parse_comment(tx: dict[str, Any]) -> str:
    # best effort across formats
    # TON tx structure varies; attempt common keys
    if "in_msg" in tx and isinstance(tx["in_msg"], dict):
        c = tx["in_msg"].get("message")
        if isinstance(c, str) and c:
            return c
    c2 = tx.get("comment")
    if isinstance(c2, str):
        return c2
    return ""


def _parse_amount_ton(tx: dict[str, Any]) -> Optional[Decimal]:
    # amount is often in nanotons in "value" fields
    val = None
    if "in_msg" in tx and isinstance(tx["in_msg"], dict):
        val = tx["in_msg"].get("value")
    if val is None:
        val = tx.get("amount")
    try:
        if val is None:
            return None
        # if nanotons integer
        if isinstance(val, (int, float)) or (isinstance(val, str) and val.isdigit()):
            nano = Decimal(str(val))
            return (nano / Decimal("1000000000")).quantize(Decimal("0.000000001"))
        # if already TON decimal string
        return Decimal(str(val)).quantize(Decimal("0.000000001"))
    except Exception:
        return None


def poll_and_confirm_invoices(db: Session, *, ton_transactions: list[dict[str, Any]]) -> dict[str, Any]:
    # Find pending invoices not expired
    inv_rows = db.execute(
        text(
            """
            SELECT invoice_id, user_id, username, ton_amount::numeric, manh_amount::numeric, comment, sig16
            FROM manh_invoices
            WHERE status='PENDING' AND expires_at > now()
            ORDER BY created_at ASC
            LIMIT 200
            """
        )
    ).fetchall()

    pending = []
    for r in inv_rows:
        pending.append(
            {
                "invoice_id": r[0],
                "user_id": int(r[1]),
                "username": r[2],
                "ton_amount": Decimal(str(r[3])),
                "manh_amount": Decimal(str(r[4])),
                "comment": r[5],
                "sig16": r[6],
            }
        )

    if not pending:
        return {"ok": True, "confirmed": 0, "checked": 0}

    confirmed = 0
    checked = 0

    for tx in ton_transactions:
        checked += 1
        cmt = _parse_comment(tx)
        amt = _parse_amount_ton(tx)
        if not cmt or amt is None:
            continue

        for inv in pending:
            if inv["comment"] != cmt:
                continue
            # tolerance: allow small fee variance
            tol = inv["ton_amount"] * Decimal("0.01")  # 1%
            if abs(amt - inv["ton_amount"]) > tol:
                continue

            # mark confirmed
            db.execute(
                text("""UPDATE manh_invoices SET status='CONFIRMED', confirmed_at=now() WHERE invoice_id=:id AND status='PENDING'"""),
                {"id": inv["invoice_id"]},
            )

            # add purchased tracker
            db.execute(
                text(
                    """
                    INSERT INTO manh_purchases(invoice_id, user_id, manh_amount, ils_amount, created_at)
                    SELECT invoice_id, user_id, manh_amount, ils_amount, now()
                    FROM manh_invoices
                    WHERE invoice_id=:id
                    """
                ),
                {"id": inv["invoice_id"]},
            )

            # mint MANH via existing manh service
            # bucket fingerprint: invoice_id => unique
            from zoneinfo import ZoneInfo
            from datetime import datetime as _dt
            tzname = (os.getenv("LEADERBOARD_TZ") or "Asia/Jerusalem").strip()
            tz = ZoneInfo(tzname)
            now_tz = _dt.now(tz)
            bucket = now_tz.strftime("%Y-%m-%d")
            fp = {"v": 1, "invoice_id": inv["invoice_id"]}

            award_manh(
                db,
                user_id=inv["user_id"],
                username=inv["username"],
                event_type="buy",
                amount_manh=inv["manh_amount"],
                bucket=bucket,
                fingerprint_obj=fp,
                meta={"src": "ton", "invoice_id": inv["invoice_id"], "bucket": bucket, "tz": tzname},
            )

            confirmed += 1
            break

    db.commit()
    return {"ok": True, "confirmed": confirmed, "checked": checked}


def eligible_for_withdrawal(db: Session, user_id: int) -> bool:
    # must have purchased >= MIN_BUY_FOR_WITHDRAWAL (from owner)
    row = db.execute(
        text("""SELECT COALESCE(SUM(manh_amount),0)::numeric FROM manh_purchases WHERE user_id=:u"""),
        {"u": user_id},
    ).fetchone()
    total = Decimal(str(row[0])) if row else Decimal("0")
    return total >= _min_buy_for_withdrawal()


def create_withdrawal_request(
    db: Session,
    *,
    user_id: int,
    username: Optional[str],
    amount_manh: Decimal,
    target_ton_address: str,
) -> dict[str, Any]:
    if _withdrawals_mode() != "manual":
        raise RuntimeError("WITHDRAWALS_MODE must be manual in V1")

    if amount_manh <= 0:
        return {"ok": False, "reason": "bad_amount"}

    if not eligible_for_withdrawal(db, user_id):
        return {"ok": False, "reason": "not_eligible_min_buy"}

    # ensure opted-in is NOT required for withdrawal (privacy)
    # balance check using manh ledger
    row = db.execute(
        text("""SELECT COALESCE(SUM(amount_manh),0)::numeric FROM manh_ledger WHERE user_id=:u"""),
        {"u": user_id},
    ).fetchone()
    bal = Decimal(str(row[0])) if row else Decimal("0")
    if bal < amount_manh:
        return {"ok": False, "reason": "insufficient_balance", "balance": str(bal)}

    wid = hashlib.sha256(f"wd|{user_id}|{_utcnow().isoformat()}|{os.urandom(8).hex()}".encode("utf-8")).hexdigest()[:24]

    db.execute(
        text(
            """
            INSERT INTO manh_withdrawals(withdrawal_id, user_id, username, amount_manh, target_ton_address, status, created_at)
            VALUES (:id, :u, :name, :amt, :addr, 'REQUESTED', now())
            """
        ),
        {"id": wid, "u": user_id, "name": username, "amt": str(amount_manh), "addr": target_ton_address},
    )
    db.commit()
    return {"ok": True, "withdrawal_id": wid, "status": "REQUESTED"}


def list_withdrawals(db: Session, *, user_id: int, limit: int = 10) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT withdrawal_id, status, amount_manh::numeric, target_ton_address, created_at, decided_at
            FROM manh_withdrawals
            WHERE user_id=:u
            ORDER BY created_at DESC
            LIMIT :lim
            """
        ),
        {"u": user_id, "lim": limit},
    ).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "withdrawal_id": r[0],
                "status": r[1],
                "amount_manh": str(r[2]),
                "target_ton_address": r[3],
                "created_at": r[4].isoformat() if r[4] else None,
                "decided_at": r[5].isoformat() if r[5] else None,
            }
        )
    return out
