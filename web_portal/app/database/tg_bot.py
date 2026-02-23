import logging
from typing import Optional, Any, Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

from app.db import get_db
from app.config import settings
from app.manh.service import get_balance
from app.payments.ton.price_feed import get_ton_ils_cached
from app.payments.ton.service import create_invoice, list_invoices, poll_and_confirm_invoices
from app.payments.ton.withdrawals import create_withdrawal, get_user_withdrawals
from app.manh.leaderboard import get_leaderboard

# ==================== ????? ====================
logger = logging.getLogger(__name__)

# ==================== ?????? ???????? ====================
application: Optional[Application] = None
last_update_snapshot: Optional[Dict[str, Any]] = None

# Legacy globals for main.py compatibility
_APP: Optional[Application] = None
_LAST_UPDATE: Optional[Dict[str, Any]] = None
_STARTED: bool = False

# Legacy globals for main.py compatibility
_APP: Optional[Application] = None
_LAST_UPDATE: Optional[Dict[str, Any]] = None
_STARTED: bool = False

# ==================== ???????? ??? ====================
async def _with_db(func):
    """???? ??????? ?????????? ?? session ?? DB."""
    async with get_db() as db:
        return await func(db)

def _safe_decimal(value) -> str:
    """???? ????? ?? Decimal ???????."""
    from decimal import Decimal, InvalidOperation
    try:
        d = Decimal(str(value))
        return format(d, 'f')
    except (InvalidOperation, ValueError, TypeError):
        return "0"

# ==================== Handlers ====================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        "Welcome to Telegram Guardian!\n"
        "Use /help to see available commands."
    )

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
        "/withdrawals - List your withdrawals"
    )
    await update.message.reply_text(text)

async def cmd_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ??? ?-/help
    await cmd_help(update, context)

async def cmd_manh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    balance = await _with_db(lambda db: get_balance(db, user_id, username))
    await update.message.reply_text(f"MANH balance: {_safe_decimal(balance)}")

async def cmd_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    scope = args[0] if args and args[0] in ("daily", "weekly") else "daily"
    lb = await _with_db(lambda db: get_leaderboard(db, bucket_scope=scope, bucket_key=scope, limit=10))
    if not lb:
        await update.message.reply_text(f"?? Leaderboard ({scope}) is empty right now.")
        return
    lines = [f"{i+1}. {row.get('username', row['user_id'])}  {row['total_manh']} MANH" for i, row in enumerate(lb)]
    await update.message.reply_text(f"?? {scope.capitalize()} Leaderboard:\n" + "\n".join(lines))

async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
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
        # ????? ????
        if hasattr(rate_data, 'ton_ils'):
            ton_per_ils = Decimal(str(rate_data.ton_ils))
        elif hasattr(rate_data, 'rate'):
            ton_per_ils = Decimal(str(rate_data.rate))
        else:
            ton_per_ils = Decimal("0.192307693")  # fallback
        print(f"ton_per_ils = {ton_per_ils}", flush=True)

        inv = await _with_db(lambda db: create_invoice(
            db=db,
            user_id=user_id,
            username=username,
            ils_amount=ils_amount,
            ton_ils_rate=ton_per_ils
        ))
        msg = (
            f"?? Invoice created!\n"
            f"ILS amount: {ils_amount}\n"
            f"TON amount: {inv.ton_amount}\n"
            f"MANH amount: {inv.manh_amount}\n\n"
            f"?? Send to:\n{inv.treasury_address}\n"
            f"With memo (required): {inv.comment}\n\n"
            f"After payment, click /poll_confirm for auto-confirmation.\n"
            f"Current status: pending"
        )
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def cmd_invoices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    invoices = await _with_db(lambda db: list_invoices(db, user_id=user_id, limit=10))
    if not invoices:
        await update.message.reply_text("No invoices found.")
        return
    lines = ["?? Your invoices:"]
    for inv in invoices:
        lines.append(f"{inv.id[:8]}: {inv.status} {inv.ils_amount} ILS ({inv.created_at.date()})")
    await update.message.reply_text("\n".join(lines))

async def cmd_poll_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text("?? Checking for pending payments...")
    confirmed = await _with_db(lambda db: poll_and_confirm_invoices(db))
    if confirmed:
        await update.message.reply_text(f"? {len(confirmed)} payment(s) confirmed.")
    else:
        await update.message.reply_text("? No new payments found.")

async def cmd_miniapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    keyboard = [[InlineKeyboardButton("?? Open Dashboard", web_app=WebAppInfo(url="https://telegram-guardian-production.up.railway.app/mini_app"))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Click the button to open dashboard:", reply_markup=reply_markup)

async def cmd_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

        async with get_db() as db:
            withdrawal = await create_withdrawal(db, user_id, amount, address)
        msg = f"? Withdrawal request created!\nID: {withdrawal.id}\nAmount: {amount} MANH\nAddress: {address}\nStatus: pending"
        await update.message.reply_text(msg)
    except ValueError as e:
        await update.message.reply_text(f"Error: {e}")
    except Exception as e:
        await update.message.reply_text(f"Unexpected error: {e}")

async def cmd_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    async with get_db() as db:
        withdrawals = await get_user_withdrawals(db, user_id)
    if not withdrawals:
        await update.message.reply_text("No withdrawal requests found.")
        return
    lines = ["?? Your withdrawals:"]
    for w in withdrawals[:10]:
        lines.append(f"{w.id[:8]}: {w.amount_manh} MANH to {w.destination_address[:10]}... ({w.status})")
    await update.message.reply_text("\n".join(lines))

# ==================== ???????? ?????? ?-tg_ops ====================
def tg_get_app() -> Optional[Application]:
    """????? ?? ??????? ?-Application ?? ????."""
    return application

def get_last_update_snapshot() -> Optional[Dict[str, Any]]:
    """????? snapshot ?? ?????? ??????."""
    return last_update_snapshot

# ==================== ????? ?????? ====================
async def init_bot() -> Application:
    """???? ?????? ?? ????."""
    global application
    if application is not None:
        return application
    print('init_bot: creating new application', flush=True)

    # ????? ????????
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    print('init_bot: application created', flush=True)
    global _APP, _STARTED

    global _APP, _STARTED

    application.add_handler(CommandHandler("start", cmd_start))

    # ????? handlers
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("all", cmd_all))
    application.add_handler(CommandHandler("manh", cmd_manh))
    application.add_handler(CommandHandler("leaderboard", cmd_leaderboard))
    application.add_handler(CommandHandler("buy", cmd_buy))
    application.add_handler(CommandHandler("invoices", cmd_invoices))
    application.add_handler(CommandHandler("poll_confirm", cmd_poll_confirm))
    application.add_handler(CommandHandler("miniapp", cmd_miniapp))
    application.add_handler(CommandHandler("withdraw", cmd_withdraw))
    application.add_handler(CommandHandler("withdrawals", cmd_withdrawals))

    # ?????
    await application.initialize()
    print('init_bot: application initialized', flush=True)
    _APP = application
    _STARTED = True

    _APP = application
    _STARTED = True

    
    return application

async def shutdown_bot():
    """???? ?? ????."""
    global application
    if application:
        await application.shutdown()
        application = None

# ==================== ????? ??????? ?-webhook ====================
async def process_update(update_dict: Dict[str, Any]) -> Any:
    """×‍×¢×‘×“ ×¢×“×›×•×ں ×©×”×ھ×§×‘×œ ×‍-webhook ×•×©×•×‍×¨ snapshot."""
    global _LAST_UPDATE, last_update_snapshot
    _LAST_UPDATE = update_dict
    last_update_snapshot = update_dict

    if application is None:
        logger.error("process_update called but application not initialized")
        return {"ok": False, "error": "bot not initialized"}

    update = Update.de_json(update_dict, application.bot)
    await application.process_update(update)
    return {"ok": True}







