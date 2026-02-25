from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.database.models import User, Invoice

router = APIRouter(prefix="/api", tags=["api"])

@router.get("/user_data")
@router.post("/user_data")
async def get_user_data(request: Request, user_id: int = None, db: Session = Depends(get_db)):
    if user_id is None:
        try:
            body = await request.json()
            user_id = body.get("user_id")
        except:
            return {"error": "Missing user_id"}

    if user_id is None:
        return {"error": "Missing user_id"}

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "User not found"}

    invoices = db.query(Invoice).filter(Invoice.user_id == user_id).order_by(Invoice.created_at.desc()).limit(10).all()
    return {
        "balance_manh": str(user.balance_manh),
        "total_xp": user.total_xp,
        "invoices": [
            {
                "id": inv.id,
                "status": inv.status,
                "ils_amount": str(inv.ils_amount),
                "ton_amount": str(inv.ton_amount),
                "manh_amount": str(inv.manh_amount),
                "created_at": inv.created_at.isoformat()
            } for inv in invoices
        ]
    }

@router.get("/orders")
def get_orders(user_id: int = None, db: Session = Depends(get_db)):
    from app.database.models import P2POrder
    query = db.query(P2POrder).filter(P2POrder.status == 'open')
    if user_id:
        query = query.filter(P2POrder.user_id == user_id)
    orders = query.all()
    return [
        {
            "id": o.id,
            "type": o.type,
            "amount": str(o.amount),
            "price": str(o.price),
            "user_id": o.user_id
        }
        for o in orders
    ]


