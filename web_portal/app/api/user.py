from fastapi import APIRouter, Request, HTTPException, Query
from sqlalchemy.orm import Session
from app.database.models import User, Invoice
from app.db import get_db

router = APIRouter()

@router.get("/api/user_data")
async def get_user_data(user_id: int = Query(None, description="Telegram user ID"), request: Request = None):
    # If not provided as query parameter, try to get from request query string
    if user_id is None and request:
        try:
            user_id = request.query_params.get("user_id")
            if user_id:
                user_id = int(user_id)
        except:
            pass

    if user_id is None:
        raise HTTPException(status_code=400, detail="user_id required")

    db: Session = next(get_db())
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")

    invoices = db.query(Invoice).filter_by(user_id=user_id).order_by(Invoice.created_at.desc()).limit(10).all()
    invoice_list = [{
        'id': inv.id,
        'status': inv.status,
        'ils_amount': float(inv.ils_amount) if inv.ils_amount else 0,
        'ton_amount': float(inv.ton_amount) if inv.ton_amount else None,
        'manh_amount': float(inv.manh_amount) if inv.manh_amount else None,
        'created_at': inv.created_at.isoformat() if inv.created_at else None
    } for inv in invoices]

    return {
        'user_id': user.id,
        'manh_balance': float(user.balance_manh or 0),
        'xp': user.total_xp or 0,
        'invoices': invoice_list,
        'leaderboard': []
    }
