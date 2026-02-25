from app.db import Base
from sqlalchemy import Column, String, BigInteger, Numeric, DateTime, ForeignKey, Boolean, Integer, JSON, JSON
from sqlalchemy import JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    balance_manh = Column(Numeric(20, 9), default=0)
    total_xp = Column(BigInteger, default=0)
    referral_code = Column(String, unique=True, nullable=True)
    referred_by = Column(BigInteger, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    withdrawals = relationship("Withdrawal", back_populates="user")
    invoices = relationship('Invoice', back_populates='user')
    sell_orders = relationship("SellOrder", back_populates="user")
    buy_orders = relationship("BuyOrder", back_populates="user")
    p2p_orders = relationship("P2POrder", back_populates="user")  # added for unified P2P

class Withdrawal(Base):
    __tablename__ = "withdrawals"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    amount_manh = Column(Numeric(20, 9), nullable=False)
    destination_address = Column(String, nullable=False)
    status = Column(String, default="pending")
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    processed_by = Column(BigInteger, nullable=True)
    tx_hash = Column(String, nullable=True)
    memo = Column(String, nullable=True)

    user = relationship("User", back_populates="withdrawals")

class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    ils_amount = Column(Numeric(20, 9), nullable=False)
    ton_amount = Column(Numeric(20, 9), nullable=False)
    manh_amount = Column(Numeric(20, 9), nullable=False)
    status = Column(String, default="pending")
    comment = Column(String, nullable=True)
    treasury_address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="invoices")

class Referral(Base):
    __tablename__ = "referrals"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    referrer_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    referred_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reward_given = Column(Boolean, default=False)

    referrer = relationship("User", foreign_keys=[referrer_id], backref="referrals_made")
    referred = relationship("User", foreign_keys=[referred_id], backref="referred_by_user")

# Unified P2P Order model (used by current tg_bot.py)
class P2POrder(Base):
    __tablename__ = 'p2p_orders'
    __table_args__ = {'extend_existing': True}
    
    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    type = Column(String, nullable=False)  # 'buy' or 'sell'
    amount = Column(Numeric(20, 9), nullable=False)
    price = Column(Numeric(20, 9), nullable=False)  # price per MANH in TON
    status = Column(String, nullable=False, default='open')  # open, completed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="p2p_orders")

# Legacy models (for backward compatibility)
class SellOrder(Base):
    __tablename__ = "sell_orders"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    amount_manh = Column(Numeric(20, 9), nullable=False)
    price_per_manh = Column(Numeric(20, 9), nullable=False)  # price per MANH in TON
    total_price = Column(Numeric(20, 9), nullable=False)    # amount_manh * price_per_manh
    status = Column(String, default="open")  # open, partial, filled, cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    filled_amount = Column(Numeric(20, 9), default=0)

    user = relationship("User", back_populates="sell_orders")

class BuyOrder(Base):
    __tablename__ = "buy_orders"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    amount_manh = Column(Numeric(20, 9), nullable=False)
    price_per_manh = Column(Numeric(20, 9), nullable=False)
    total_price = Column(Numeric(20, 9), nullable=False)
    status = Column(String, default="open")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    filled_amount = Column(Numeric(20, 9), default=0)

    user = relationship("User", back_populates="buy_orders")

class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    sell_order_id = Column(String, ForeignKey("sell_orders.id"), nullable=True)
    buy_order_id = Column(String, ForeignKey("buy_orders.id"), nullable=True)
    seller_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    buyer_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    amount_manh = Column(Numeric(20, 9), nullable=False)
    price_per_manh = Column(Numeric(20, 9), nullable=False)
    total_price = Column(Numeric(20, 9), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    seller = relationship("User", foreign_keys=[seller_id], backref="trades_sold")
    buyer = relationship("User", foreign_keys=[buyer_id], backref="trades_bought")


class SecurityLog(Base):
    __tablename__ = 'security_logs'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    event_type = Column(String, nullable=False)
    user_id = Column(BigInteger, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatId(Base):
    __tablename__ = 'chat_ids'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, unique=True, nullable=False)
    user_id = Column(BigInteger, nullable=True)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_interaction = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)








