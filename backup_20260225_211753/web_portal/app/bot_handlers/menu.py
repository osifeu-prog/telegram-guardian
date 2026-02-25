from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from web_portal.app.core.settings import settings

async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(" MANH", callback_data='menu_manh')],
        [InlineKeyboardButton(" Leaderboard", callback_data='menu_leaderboard')],
        [InlineKeyboardButton(" Buy", callback_data='menu_buy')],
        [InlineKeyboardButton(" Invoices", callback_data='menu_invoices')],
        [InlineKeyboardButton(" Withdraw", callback_data='menu_withdraw')],
        [InlineKeyboardButton(" Referrals", callback_data='menu_referrals')],
        [InlineKeyboardButton(" Help", callback_data='menu_help')],
    ]
    if update.effective_user.id in settings.ADMIN_IDS:
        keyboard.append([InlineKeyboardButton(" Admin", callback_data='menu_admin')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Main Menu', reply_markup=reply_markup)

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    texts = {
        'menu_manh': "Use /manh to see your balance.\nUse /leaderboard for rankings.",
        'menu_leaderboard': "Daily: /leaderboard daily\nWeekly: /leaderboard weekly",
        'menu_buy': "Use /buy <ILS> to purchase MANH.",
        'menu_invoices': "Use /invoices to see your invoices.",
        'menu_withdraw': "Use /withdraw <amount> <address>.",
        'menu_referrals': "Use /referral to get your link.\nUse /referrals to see referred users.",
        'menu_help': "/help for all commands.",
        'menu_admin': "/admin_stats\n/admin_users\n/admin_orders\n/admin_broadcast",
    }
    text = texts.get(data, "Unknown option")
    await query.edit_message_text(text, reply_markup=query.message.reply_markup)


