"""
Telegram bot module for Telegram Guardian.
Handles all bot commands and interactions.
"""

import asyncio
import logging
import qrcode
import io
import os
import sys
import time
import json
import functools
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, Any, Dict
from uuid import uuid4

import redis.asyncio as redis
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.settings import settings
from app.db import SessionLocal
from app.database.models import User, Referral, P2POrder, Invoice, SecurityLog
from app.manh.service import get_balance
from app.payments.ton.price_feed import get_ton_ils_cached
from app.payments.ton.service import create_invoice, list_invoices, poll_and_confirm_invoices
from app.payments.ton.withdrawals import create_withdrawal, get_user_withdrawals, approve_withdrawal, reject_withdrawal
from app.manh.leaderboard import get_leaderboard
from app.manh.referrals import set_referral_code, get_user_referrals, process_referral
from app.p2p.service import create_sell_order, create_buy_order, get_open_orders, cancel_order, match_orders
from app.manh.admin_backup import cmd_admin_backup

# ---------- Logging Configuration ----------
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler('bot.log', maxBytes=10*1024*1024, backupCount=5)
    ]
)
logger = logging.getLogger(__name__)

# -------------------- Global State --------------------
_STARTED: Optional[str] = None
_LAST_UPDATE: Optional[str] = None
_application: Optional[Application] = None

# -------------------- Redis Client (Rate Limiting) --------------------
_redis_client: Optional[redis.Redis] = None

async def get_redis():
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        try:
            _redis_client = await redis.from_url(redis_url)
            await _redis_client.ping()
            logger.info(f"Redis connected: {redis_url}")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            _redis_client = None
    return _redis_client

# ---------- Helper Decorator ----------
def _with_db(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        db = SessionLocal()
        try:
            return await func(update, context, db)
        finally:
            db.close()
    return wrapper

def _safe_decimal(value) -> str:
    try:
        d = Decimal(str(value))
        return format(d, 'f')
    except (InvalidOperation, ValueError, TypeError):
        return '0'

# ---------- Rate Limiting Decorator ----------
def rate_limit(key_prefix: str, max_calls: int, period: int):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            key = f"rate_limit:{key_prefix}:{user_id}"
            r = await get_redis()
            if not r:
                return await func(update, context, *args, **kwargs)
            now = time.time()
            pipe = r.pipeline()
            pipe.zadd(key, {str(now): now})
            pipe.zremrangebyscore(key, 0, now - period)
            pipe.zcard(key)
            pipe.expire(key, period)
            results = await pipe.execute()
            current_calls = results[3]
            if current_calls > max_calls:
                try:
                    db = SessionLocal()
                    log = SecurityLog(
                        event_type='rate_limit_exceeded',
                        user_id=user_id,
                        details={'command': key_prefix, 'calls': current_calls, 'limit': max_calls, 'period': period}
                    )
                    db.add(log)
                    db.commit()
                    db.close()
                except Exception as e:
                    logger.error(f"Failed to log rate limit event: {e}")
                security_group = os.getenv("TG_SECURITY_GROUP")
                if security_group:
                    try:
                        await context.bot.send_message(
                            chat_id=security_group,
                            text=f"Rate limit exceeded: {key_prefix} by user {user_id} ({current_calls} calls in {period}s)"
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify security group: {e}")
                await update.message.reply_text("Too many requests. Please try again later.")
                return
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator

async def log_security_event(db, event_type: str, user_id: int = None, details: dict = None):
    log = SecurityLog(
        event_type=event_type,
        user_id=user_id,
        details=details
    )
    db.add(log)
    db.commit()

# ---------- Command Handlers ----------
@_with_db
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    args = update.message.text.split()
    referral_code = args[1] if len(args) > 1 and args[1].startswith("R") else None

    user = db.get(User, user_id)
    if not user:
        user = User(id=user_id, username=username, first_name=first_name, balance_manh=0, total_xp=0)
        if referral_code:
            referrer = db.query(User).filter(User.referral_code == referral_code).first()
            if referrer and referrer.id != user_id:
                user.referred_by = referrer.id
                ref = Referral(
                    id=uuid4().hex,
                    referrer_id=referrer.id,
                    referred_id=user_id,
                    created_at=datetime.utcnow(),
                    reward_given=False
                )
                db.add(ref)
                referrer.balance_manh += 5
                db.add(referrer)
        db.add(user)
        db.commit()
        await update.message.reply_text("Welcome to Telegram Guardian! Use /help to see available commands.")
    else:
        await update.message.reply_text("Welcome back! Use /help to see available commands.")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Available commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/all - Show all commands\n"
        "/manh - Show your MANH balance\n"
        "/leaderboard [daily|weekly] - Show leaderboard\n"
        "/buy <ILS> - Buy MANH\n"
        "/invoices - Show your invoices\n"
        "/poll_confirm - Check for pending payments\n"
        "/miniapp - Open dashboard\n"
        "/withdraw <amount> <address> - Request withdrawal\n"
        "/withdrawals - List your withdrawals\n"
        "/chatid - Get chat ID\n"
        "/p2p_buy <amount> <price> - Place P2P buy order\n"
        "/sell <amount> <price> - Place P2P sell order\n"
        "/orders - Show open orders\n"
        "/cancel <id> <sell|buy> - Cancel order\n"
        "/referral - Get referral link\n"
        "/referrals - Show referred users\n"
        "/menu - Open interactive menu\n"
        "/faq - Frequently asked questions\n"
        "/admin - Admin panel\n"
        "/admin_stats - Admin statistics\n"
        "/admin_users - List users\n"
        "/admin_orders - All orders\n"
        "/admin_broadcast - Broadcast message"
    )
    await update.message.reply_text(text)

async def cmd_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_help(update, context)

@_with_db
async def cmd_manh(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    balance = get_balance(db, user_id)
    await update.message.reply_text(f"MANH balance: {_safe_decimal(balance)}")

@_with_db
async def cmd_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    args = context.args
    scope = args[0] if args and args[0] in ("daily", "weekly") else "daily"
    lb = get_leaderboard(db, bucket_scope=scope, bucket_key=scope, limit=10)
    if not lb:
        await update.message.reply_text(f"Leaderboard ({scope}) is empty right now.")
        return
    lines = [f"{i+1}. {row.get('username', row['user_id'])}  {row['total_manh']} MANH" for i, row in enumerate(lb)]
    await update.message.reply_text(f"{scope.capitalize()} Leaderboard:\n" + "\n".join(lines))

@_with_db
async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    username = update.effective_user.username
    parts = update.message.text.split()
    if len(parts) < 2:
        await update.message.reply_text("Usage: /buy <ILS amount>")
        return
    try:
        from decimal import Decimal
        ils_amount = Decimal(parts[1])
        rate_data = get_ton_ils_cached()
        if hasattr(rate_data, 'ton_ils'):
            ton_per_ils = Decimal(str(rate_data.ton_ils))
        elif hasattr(rate_data, 'rate'):
            ton_per_ils = Decimal(str(rate_data.rate))
        else:
            ton_per_ils = Decimal("0.192307693")
        inv = create_invoice(
            db=db,
            user_id=user_id,
            username=username,
            ils_amount=ils_amount,
            ton_ils_rate=ton_per_ils
        )
        msg = (
            f"Invoice created!\n"
            f"ILS amount: {ils_amount}\n"
            f"TON amount: {inv.ton_amount}\n"
            f"MANH amount: {inv.manh_amount}\n\n"
            f"Send to:\n{inv.treasury_address}\n"
            f"With memo (required): {inv.comment}\n\n"
            f"After payment, click /poll_confirm for auto-confirmation.\n"
            f"Current status: pending"
        )
        await update.message.reply_text(msg)
    except Exception as e:
        logger.error(f"Error in /buy: {e}", exc_info=True)
        await update.message.reply_text(f"Error: {e}")

@_with_db
async def cmd_invoices(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    invoices = list_invoices(db, user_id=user_id, limit=10)
    if not invoices:
        await update.message.reply_text("No invoices found.")
        return
    lines = ["Your invoices:"]
    for inv in invoices:
        inv_id = inv.id[:8] if inv.id else '?'
        lines.append(f"{inv_id}: {inv.status} {inv.ils_amount} ILS ({inv.created_at.date()})")
    await update.message.reply_text("\n".join(lines))

@_with_db
async def cmd_poll_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    await update.message.reply_text("Checking for pending payments...")
    result = poll_and_confirm_invoices(db)
    if result.get("confirmed", 0) > 0:
        await update.message.reply_text(f"{result['confirmed']} payment(s) confirmed.")
    else:
        await update.message.reply_text("No new payments found.")

async def cmd_miniapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton(
            "Open Dashboard",
            web_app=WebAppInfo(url="https://telegram-guardian-production.up.railway.app/mini_app")
        )
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Click the button to open dashboard:", reply_markup=reply_markup)

@rate_limit("withdraw", 3, 3600)
@_with_db
async def cmd_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    parts = update.message.text.split()
    if len(parts) < 3:
        await update.message.reply_text("Usage: /withdraw <amount MANH> <TON address>")
        return
    try:
        amount = float(parts[1])
        address = parts[2]
        if not (address.startswith("UQ") or address.startswith("EQ")):
            await update.message.reply_text("Invalid TON address. Should start with UQ or EQ.")
            return
        min_amount = float(os.getenv("MIN_BUY_FOR_WITHDRAWAL", "0.000001"))
        if amount < min_amount:
            await update.message.reply_text(f"Minimum withdrawal is {min_amount} MANH")
            return
        from decimal import Decimal
        amount_decimal = Decimal(str(amount))
        withdrawal = create_withdrawal(db, user_id, amount_decimal, address)
        msg = f"Withdrawal request created!\nID: {withdrawal.id}\nAmount: {amount} MANH\nAddress: {address}\nStatus: pending"
        await update.message.reply_text(msg)
        payment_group = os.getenv("TG_PAYMENT_GROUP")
        if payment_group:
            try:
                await context.bot.send_message(
                    chat_id=payment_group,
                    text=f"New withdrawal request:\nUser: {user_id}\nAmount: {amount} MANH\nAddress: {address}"
                )
            except Exception as e:
                logger.error(f"Failed to send to payment group: {e}")
    except ValueError as e:
        await update.message.reply_text(f"Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in /withdraw: {e}", exc_info=True)
        await update.message.reply_text(f"Unexpected error: {e}")

@_with_db
async def cmd_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    withdrawals = get_user_withdrawals(db, user_id)
    if not withdrawals:
        await update.message.reply_text("No withdrawal requests found.")
        return
    lines = ["Your withdrawals:"]
    for w in withdrawals[:10]:
        lines.append(f"{w.id[:8]}: {w.amount_manh} MANH to {w.destination_address[:10]}... ({w.status})")
    await update.message.reply_text("\n".join(lines))

async def cmd_chatid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await update.message.reply_text(f"Chat ID: {chat.id}\nType: {chat.type}")

@rate_limit("p2p_buy", 10, 60)
@_with_db
async def cmd_p2p_buy(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Usage: /p2p_buy <amount MANH> <price per MANH in TON>")
        return
    try:
        amount = float(args[0])
        price = float(args[1])
    except ValueError:
        await update.message.reply_text("Invalid numbers.")
        return
    user_id = update.effective_user.id
    order = P2POrder(
        id=uuid4().hex,
        user_id=user_id,
        type='buy',
        amount=amount,
        price=price,
        status='open',
        created_at=datetime.utcnow()
    )
    db.add(order)
    db.commit()
    await update.message.reply_text(f"Buy order created: {amount} MANH @ {price} TON")

@rate_limit("sell", 5, 60)
@_with_db
async def cmd_sell(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Usage: /sell <amount MANH> <price per MANH in TON>")
        return
    try:
        amount = float(args[0])
        price = float(args[1])
    except ValueError:
        await update.message.reply_text("Invalid numbers.")
        return
    user_id = update.effective_user.id
    user = db.get(User, user_id)
    if not user or user.balance_manh < amount:
        await update.message.reply_text("Insufficient MANH balance.")
        return
    order = P2POrder(
        id=uuid4().hex,
        user_id=user_id,
        type='sell',
        amount=amount,
        price=price,
        status='open',
        created_at=datetime.utcnow()
    )
    db.add(order)
    db.commit()
    await update.message.reply_text(f"Sell order created: {amount} MANH @ {price} TON")

@_with_db
async def cmd_orders(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    orders = db.query(P2POrder).filter_by(status='open').all()
    if not orders:
        await update.message.reply_text("No open orders.")
        return
    buy_lines = ["Buy orders:"]
    sell_lines = ["Sell orders:"]
    for o in orders:
        line = f"  {o.id[:8]}  {o.amount} MANH @ {o.price} TON"
        if o.type == 'buy':
            buy_lines.append(line)
        else:
            sell_lines.append(line)
    await update.message.reply_text("\n".join(buy_lines + sell_lines))

@_with_db
async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Usage: /cancel <order_id> <sell|buy>")
        return
    order_id_prefix = args[0].strip().replace(':', '').replace(',', '')
    order_type = args[1].lower()
    user_id = update.effective_user.id
    order = db.query(P2POrder).filter(
        P2POrder.id.startswith(order_id_prefix),
        P2POrder.user_id == user_id,
        P2POrder.type == order_type
    ).first()
    if not order:
        await update.message.reply_text("Order not found or not yours.")
        return
    if order.status != 'open':
        await update.message.reply_text("Order is not open.")
        return
    order.status = 'cancelled'
    db.commit()
    await update.message.reply_text(f"Order {order.id[:8]} cancelled.")

@_with_db
async def cmd_referral(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    user = db.get(User, user_id)
    if not user:
        await update.message.reply_text("User not found.")
        return
    if not user.referral_code:
        code = set_referral_code(db, user_id)
    else:
        code = user.referral_code
    link = f"https://t.me/{context.bot.username}?start={code}"
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = io.BytesIO()
    bio.name = 'qr.png'
    img.save(bio, 'PNG')
    bio.seek(0)
    await update.message.reply_photo(photo=InputFile(bio), caption=f"Scan or tap:\n{link}")

@_with_db
async def cmd_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    try:
        referrals = db.query(Referral).filter(Referral.referrer_id == user_id).all()
        if not referrals:
            await update.message.reply_text("You haven't referred anyone yet.")
            return
        lines = ["Your referrals:"]
        for ref in referrals:
            referred = db.get(User, ref.referred_id)
            username = f"@{referred.username}" if referred and referred.username else f"User {ref.referred_id}"
            lines.append(f"{username} - joined {ref.created_at.strftime('%Y-%m-%d')}")
        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        logger.error(f"Error in cmd_referrals: {e}", exc_info=True)
        await update.message.reply_text("An error occurred. Please try again later.")

@_with_db
async def cmd_approve_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    if update.effective_user.id not in settings.ADMIN_IDS:
        return
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("Usage: /approve_withdrawal <withdrawal_id>")
        return
    withdrawal_id = args[0]
    try:
        withdrawal = approve_withdrawal(db, withdrawal_id, update.effective_user.id)
        await update.message.reply_text(f"Withdrawal {withdrawal.id[:8]} approved.")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

@_with_db
async def cmd_reject_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    if update.effective_user.id not in settings.ADMIN_IDS:
        return
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("Usage: /reject_withdrawal <withdrawal_id>")
        return
    withdrawal_id = args[0]
    try:
        withdrawal = reject_withdrawal(db, withdrawal_id, update.effective_user.id)
        await update.message.reply_text(f"Withdrawal {withdrawal.id[:8]} rejected.")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

@_with_db
async def cmd_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    if update.effective_user.id not in settings.ADMIN_IDS:
        return
    user_count = db.query(User).count()
    invoice_count = db.query(Invoice).count()
    order_count = db.query(P2POrder).count()
    await update.message.reply_text(f"Stats:\nUsers: {user_count}\nInvoices: {invoice_count}\nOrders: {order_count}")

@_with_db
async def cmd_admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    if update.effective_user.id not in settings.ADMIN_IDS:
        return
    users = db.query(User).limit(10).all()
    lines = ["Page 1:"]
    for u in users:
        lines.append(f"ID: {u.id} | @{u.username} | MANH: {_safe_decimal(u.balance_manh)} | XP: {u.total_xp}")
    await update.message.reply_text("\n".join(lines))

@_with_db
async def cmd_admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    if update.effective_user.id not in settings.ADMIN_IDS:
        return
    orders = db.query(P2POrder).filter_by(status='open').all()
    if not orders:
        await update.message.reply_text("No open orders.")
        return
    lines = ["All open orders:"]
    for o in orders:
        lines.append(f"{o.id[:8]} | {o.type} | {o.amount} MANH @ {o.price} TON | User: {o.user_id}")
    await update.message.reply_text("\n".join(lines))

@_with_db
async def cmd_admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    if update.effective_user.id not in settings.ADMIN_IDS:
        return
    msg = ' '.join(context.args)
    if not msg:
        await update.message.reply_text("Usage: /admin_broadcast <message>")
        return
    users = db.query(User).all()
    sent = 0
    for user in users:
        try:
            await context.bot.send_message(chat_id=user.id, text=f"Broadcast:\n{msg}")
            sent += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to {user.id}: {e}")
    await update.message.reply_text(f"Broadcast sent to {sent}/{len(users)} users.")

async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("General", callback_data='menu_general')],
        [InlineKeyboardButton("MANH", callback_data='menu_manh')],
        [InlineKeyboardButton("Wallet & Trade", callback_data='menu_wallet')],
    ]
    if update.effective_user.id in settings.ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("Admin", callback_data='menu_admin')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Main Menu\nChoose category:', reply_markup=reply_markup)

async def cmd_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "**Frequently Asked Questions**\n\n"
        "**What is MANH?**\n"
        "MANH is a digital token based on TON, used within the system.\n\n"
        "**How to buy MANH?**\n"
        "Use /buy <ILS amount>. An invoice will be created for payment in TON.\n\n"
        "**How long does payment confirmation take?**\n"
        "Usually a few minutes. Check with /poll_confirm.\n\n"
        "**What is P2P?**\n"
        "Peer-to-peer trading – you can buy or sell MANH directly with other users."
    )
    await update.message.reply_text(text)

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == 'menu_general':
        text = "/help - Help\n/faq - FAQ\n/start - Start"
    elif data == 'menu_manh':
        text = "/manh - Balance\n/leaderboard - Leaderboard\n/buy - Buy\n/sell - Sell"
    elif data == 'menu_wallet':
        text = "/invoices - Invoices\n/withdraw - Withdraw\n/withdrawals - Withdrawals\n/p2p_buy - P2P Buy"
    elif data == 'menu_admin':
        text = "/admin_stats - Stats\n/admin_users - Users\n/admin_orders - Orders\n/admin_broadcast - Broadcast"
    else:
        text = "Unknown option"
    await query.edit_message_text(text, reply_markup=query.message.reply_markup)

async def init_bot():
    global _STARTED, _application
    _STARTED = datetime.now().isoformat()
    app = Application.builder().token(settings.BOT_TOKEN).build()

    # --- תיקון אוטומטי של טור id (ניתן להסיר אחרי ריצה מוצלחת) ---
    try:
        db = SessionLocal()
        db.execute(text("ALTER TABLE users ALTER COLUMN id TYPE BIGINT;"))
        db.commit()
        logger.info("Column 'id' in table 'users' altered to BIGINT successfully.")
    except Exception as e:
        logger.warning(f"Could not alter column (might already be BIGINT): {e}")
        db.rollback()
    finally:
        db.close()
    # -------------------------------------------------------------

    # Command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("all", cmd_all))
    app.add_handler(CommandHandler("manh", cmd_manh))
    app.add_handler(CommandHandler("leaderboard", cmd_leaderboard))
    app.add_handler(CommandHandler("buy", cmd_buy))
    app.add_handler(CommandHandler("invoices", cmd_invoices))
    app.add_handler(CommandHandler("poll_confirm", cmd_poll_confirm))
    app.add_handler(CommandHandler("miniapp", cmd_miniapp))
    app.add_handler(CommandHandler("withdraw", cmd_withdraw))
    app.add_handler(CommandHandler("withdrawals", cmd_withdrawals))
    app.add_handler(CommandHandler("chatid", cmd_chatid))
    app.add_handler(CommandHandler("p2p_buy", cmd_p2p_buy))
    app.add_handler(CommandHandler("sell", cmd_sell))
    app.add_handler(CommandHandler("orders", cmd_orders))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CommandHandler("referral", cmd_referral))
    app.add_handler(CommandHandler("referrals", cmd_referrals))
    app.add_handler(CommandHandler("approve_withdrawal", cmd_approve_withdrawal))
    app.add_handler(CommandHandler("reject_withdrawal", cmd_reject_withdrawal))
    app.add_handler(CommandHandler("admin_stats", cmd_admin_stats))
    app.add_handler(CommandHandler("admin_users", cmd_admin_users))
    app.add_handler(CommandHandler("admin_orders", cmd_admin_orders))
    app.add_handler(CommandHandler("admin_broadcast", cmd_admin_broadcast))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("faq", cmd_faq))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern='^menu_'))

    await app.initialize()
    _application = app
    logger.info("Bot initialized successfully")
    return app

async def shutdown_bot():
    global _application
    if _application:
        await _application.shutdown()
        _application = None
        logger.info("Bot shut down")

def tg_get_app():
    return _application

async def process_update(update_dict: dict) -> dict:
    global _LAST_UPDATE
    _LAST_UPDATE = datetime.now().isoformat()
    if _application is None:
        logger.error("process_update called but bot not initialized")
        return {"ok": False, "error": "Bot not initialized"}
    update = Update.de_json(update_dict, _application.bot)
    await _application.process_update(update)
    return {"ok": True}

def get_last_update_snapshot():
    return {"started": _STARTED, "last_update": _LAST_UPDATE}
