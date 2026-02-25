import os
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database.models import Withdrawal, User
from app.core.settings import settings
from datetime import datetime

def create_withdrawal(
    db: Session,
    user_id: int,
    amount_manh: float,
    destination_address: str
) -> Withdrawal:
    """×™×•×¦×¨ ×‘×§×©×ھ ×‍×©×™×›×” ×—×“×©×”."""
    user = db.get(User, user_id)
    if not user or user.balance_manh < amount_manh:
        raise ValueError("Insufficient balance")

    min_amount = float(os.getenv("MIN_BUY_FOR_WITHDRAWAL", "0.000001"))
    if amount_manh < min_amount:
        raise ValueError(f"Minimum withdrawal is {min_amount} MANH")

    from uuid import uuid4
    withdrawal = Withdrawal(
        id=uuid4().hex,
        user_id=user_id,
        amount_manh=amount_manh,
        destination_address=destination_address,
        status="pending"
    )
    db.add(withdrawal)

    user.balance_manh -= amount_manh
    db.add(user)

    db.commit()
    db.refresh(withdrawal)
    return withdrawal

def approve_withdrawal(db: Session, withdrawal_id: str, operator_id: int) -> Withdrawal:
    withdrawal = db.get(Withdrawal, withdrawal_id)
    if not withdrawal:
        raise ValueError("Withdrawal not found")
    if withdrawal.status != "pending":
        raise ValueError(f"Withdrawal already {withdrawal.status}")

    withdrawal.status = "approved"
    withdrawal.processed_by = operator_id
    withdrawal.processed_at = datetime.utcnow()
    db.add(withdrawal)
    db.commit()
    db.refresh(withdrawal)
    return withdrawal

def reject_withdrawal(db: Session, withdrawal_id: str, operator_id: int) -> Withdrawal:
    withdrawal = db.get(Withdrawal, withdrawal_id)
    if not withdrawal:
        raise ValueError("Withdrawal not found")
    if withdrawal.status != "pending":
        raise ValueError(f"Withdrawal already {withdrawal.status}")

    user = db.get(User, withdrawal.user_id)
    if user:
        user.balance_manh += withdrawal.amount_manh
        db.add(user)

    withdrawal.status = "rejected"
    withdrawal.processed_by = operator_id
    withdrawal.processed_at = datetime.utcnow()
    db.add(withdrawal)
    db.commit()
    db.refresh(withdrawal)
    return withdrawal

def complete_withdrawal(db: Session, withdrawal_id: str, tx_hash: str) -> Withdrawal:
    withdrawal = db.get(Withdrawal, withdrawal_id)
    if not withdrawal:
        raise ValueError("Withdrawal not found")
    if withdrawal.status != "approved":
        raise ValueError(f"Withdrawal not approved")

    withdrawal.status = "completed"
    withdrawal.tx_hash = tx_hash
    db.add(withdrawal)
    db.commit()
    db.refresh(withdrawal)
    return withdrawal

def get_user_withdrawals(db: Session, user_id: int) -> list[Withdrawal]:
    return db.execute(
        select(Withdrawal).where(Withdrawal.user_id == user_id).order_by(Withdrawal.requested_at.desc())
    ).scalars().all()




