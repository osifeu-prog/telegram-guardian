from web_portal.app.database.models import User, Referral
from sqlalchemy.orm import Session
from datetime import datetime
from uuid import uuid4

def set_referral_code(db: Session, user_id: int) -> str:
    import random
    import string
    code = 'R' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
    user = db.get(User, user_id)
    if user:
        user.referral_code = code
        db.commit()
        return code
    return None

def get_user_referrals(db: Session, user_id: int) -> list:
    return db.query(Referral).filter(Referral.referrer_id == user_id).all()

def process_referral(db: Session, referrer_code: str, new_user_id: int) -> dict:
    if not referrer_code:
        return {"ok": False, "reason": "no_code"}
    referrer = db.query(User).filter(User.referral_code == referrer_code).first()
    if not referrer:
        return {"ok": False, "reason": "invalid_code"}
    if referrer.id == new_user_id:
        return {"ok": False, "reason": "self_referral"}
    ref = Referral(id=uuid4().hex, referrer_id=referrer.id, referred_id=new_user_id,
                   created_at=datetime.utcnow(), reward_given=False)
    db.add(ref)
    referrer.balance_manh += 5
    db.add(referrer)
    db.commit()
    return {"ok": True, "referrer_id": referrer.id}


