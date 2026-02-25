from fastapi import APIRouter, Request, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from app.database.models import User, Invoice
from app.db import get_db
from app.core.tg_initdata import verify_telegram_init_data, _parse_tg_user
from app.core.settings import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/user_data")
async def get_user_data(
    request: Request,
    user_id: int = Query(None, description="Telegram user ID"),
    db: Session = Depends(get_db)
):
    # ?? user_id ?? ????, ???? ???? ??-initData
    if user_id is None:
        init_data = request.headers.get("X-Tg-Init-Data") or request.query_params.get("initData")
        if init_data and settings.BOT_TOKEN:
            try:
                data = verify_telegram_init_data(init_data, settings.BOT_TOKEN)
                user_data = _parse_tg_user(data)
                user_id = user_data.get("id")
                logger.info(f"Extracted user_id from initData: {user_id}")
            except Exception as e:
                logger.warning(f"Failed to extract user_id from initData: {e}")
    
    if user_id is None:
        raise HTTPException(status_code=400, detail="user_id required or initData missing")
    
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

@router.post("/api/get_user_id_from_initdata")
async def get_user_id_from_initdata(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    init_data = body.get("initData")
    if not init_data:
        raise HTTPException(status_code=400, detail="initData missing")
    try:
        data = verify_telegram_init_data(init_data, settings.BOT_TOKEN)
        user_data = _parse_tg_user(data)
        user_id = user_data.get("id")
        if not user_id:
            raise HTTPException(status_code=400, detail="user id not found")
        # ????? ????? ?? ?? ????
        user = db.get(User, user_id)
        if not user:
            user = User(
                id=user_id,
                username=user_data.get("username"),
                first_name=user_data.get("first_name"),
                balance_manh=0,
                total_xp=0
            )
            db.add(user)
            db.commit()
        return {"user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


