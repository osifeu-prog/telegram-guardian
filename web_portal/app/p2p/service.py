from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database.models import User, SellOrder, BuyOrder, Trade
from decimal import Decimal
from uuid import uuid4
from datetime import datetime, timedelta

def create_sell_order(
    db: Session,
    user_id: int,
    amount_manh: Decimal,
    price_per_manh: Decimal,
    expires_in_hours: int = 24
) -> SellOrder:
    """×™×•×¦×¨ ×”×–×‍× ×ھ ×‍×›×™×¨×”."""
    user = db.get(User, user_id)
    if not user or user.balance_manh < amount_manh:
        raise ValueError("Insufficient balance")
    total = amount_manh * price_per_manh
    order = SellOrder(
        id=uuid4().hex,
        user_id=user_id,
        amount_manh=amount_manh,
        price_per_manh=price_per_manh,
        total_price=total,
        expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours)
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order

def create_buy_order(
    db: Session,
    user_id: int,
    amount_manh: Decimal,
    price_per_manh: Decimal,
    expires_in_hours: int = 24
) -> BuyOrder:
    """×™×•×¦×¨ ×”×–×‍× ×ھ ×§× ×™×™×”."""
    total = amount_manh * price_per_manh
    order = BuyOrder(
        id=uuid4().hex,
        user_id=user_id,
        amount_manh=amount_manh,
        price_per_manh=price_per_manh,
        total_price=total,
        expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours)
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order

def match_orders(db: Session) -> list[Trade]:
    """×”×ھ×گ×‍×ھ ×”×–×‍× ×•×ھ ×¤×ھ×•×—×•×ھ ×•×،×’×™×¨×ھ×ں."""
    trades = []
    sell_orders = db.execute(
        select(SellOrder).where(SellOrder.status == "open").order_by(SellOrder.price_per_manh.asc())
    ).scalars().all()
    buy_orders = db.execute(
        select(BuyOrder).where(BuyOrder.status == "open").order_by(BuyOrder.price_per_manh.desc())
    ).scalars().all()

    i = j = 0
    while i < len(sell_orders) and j < len(buy_orders):
        sell = sell_orders[i]
        buy = buy_orders[j]
        if sell.price_per_manh <= buy.price_per_manh:
            amount = min(sell.amount_manh - sell.filled_amount, buy.amount_manh - buy.filled_amount)
            if amount <= 0:
                i += 1 if sell.amount_manh - sell.filled_amount <= 0 else 0
                j += 1 if buy.amount_manh - buy.filled_amount <= 0 else 0
                continue

            trade = Trade(
                id=uuid4().hex,
                sell_order_id=sell.id,
                buy_order_id=buy.id,
                seller_id=sell.user_id,
                buyer_id=buy.user_id,
                amount_manh=amount,
                price_per_manh=sell.price_per_manh,
                total_price=amount * sell.price_per_manh
            )
            db.add(trade)

            sell.filled_amount += amount
            buy.filled_amount += amount
            if sell.filled_amount >= sell.amount_manh:
                sell.status = "filled"
            else:
                sell.status = "partial"
            if buy.filled_amount >= buy.amount_manh:
                buy.status = "filled"
            else:
                buy.status = "partial"

            seller = db.get(User, sell.user_id)
            buyer = db.get(User, buy.user_id)
            seller.balance_manh -= amount
            buyer.balance_manh += amount

            trades.append(trade)

            if sell.status == "filled":
                i += 1
            if buy.status == "filled":
                j += 1
        else:
            break

    db.commit()
    return trades

def get_open_orders(db: Session, type: str = "all") -> dict:
    """×‍×—×–×™×¨ ×”×–×‍× ×•×ھ ×¤×ھ×•×—×•×ھ."""
    result = {}
    if type in ("all", "sell"):
        result["sell"] = db.execute(
            select(SellOrder).where(SellOrder.status.in_(["open", "partial"])).order_by(SellOrder.price_per_manh.asc())
        ).scalars().all()
    if type in ("all", "buy"):
        result["buy"] = db.execute(
            select(BuyOrder).where(BuyOrder.status.in_(["open", "partial"])).order_by(BuyOrder.price_per_manh.desc())
        ).scalars().all()
    return result

def cancel_order(db: Session, user_id: int, order_id: str, order_type: str) -> bool:
    """×‍×‘×ک×œ ×”×–×‍× ×” (×¨×§ ×©×œ ×”×‍×©×ھ×‍×© ×¢×¦×‍×•)."""
    if order_type == "sell":
        order = db.get(SellOrder, order_id)
    else:
        order = db.get(BuyOrder, order_id)
    if not order or order.user_id != user_id or order.status not in ("open", "partial"):
        return False
    order.status = "cancelled"
    db.commit()
    return True

