from sqlalchemy.orm import Session
from web_portal.app.database.models import LedgerEvent, User
from decimal import Decimal
import json

def add_ledger_event(db: Session, user_id: int, event_type: str, amount: Decimal, description: str = None, meta: dict = None):
    user = db.get(User, user_id)
    balance_after = user.balance_manh if user else Decimal(0)
    event = LedgerEvent(
        user_id=user_id,
        event_type=event_type,
        amount=amount,
        balance_after=balance_after,
        description=description,
        meta=json.dumps(meta) if meta else None
    )
    db.add(event)
    db.commit()
    return event

def get_user_ledger(db: Session, user_id: int, limit: int = 10):
    return db.query(LedgerEvent).filter_by(user_id=user_id).order_by(LedgerEvent.created_at.desc()).limit(limit).all()
