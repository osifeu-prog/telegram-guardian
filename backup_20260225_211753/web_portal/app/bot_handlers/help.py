from telegram import Update
from telegram.ext import ContextTypes

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Available commands:\\n"
        "/start - Start the bot\\n"
        "/help - Show this help\\n"
        "/all - Show all commands\\n"
        "/manh - Show your MANH balance\\n"
        "/leaderboard [daily|weekly] - Show leaderboard\\n"
        "/buy <ILS> - Buy MANH\\n"
        "/invoices - Show your invoices\\n"
        "/poll_confirm - Check for pending payments\\n"
        "/miniapp - Open dashboard\\n"
        "/withdraw <amount> <address> - Request withdrawal\\n"
        "/withdrawals - List your withdrawals\\n"
        "/chatid - Get chat ID\\n"
        "/p2p_buy <amount> <price> - Place P2P buy order\\n"
        "/sell <amount> <price> - Place P2P sell order\\n"
        "/orders - Show open orders\\n"
        "/cancel <id> <sell|buy> - Cancel order\\n"
        "/referral - Get referral link\\n"
        "/referrals - Show referred users\\n"
        "/menu - Open interactive menu\\n"
        "/faq - Frequently asked questions\\n"
        "/admin - Admin panel\\n"
        "/admin_stats - Admin statistics\\n"
        "/admin_users - List users\\n"
        "/admin_orders - All orders\\n"
        "/admin_broadcast - Broadcast message"
    )
    await update.message.reply_text(text)

async def cmd_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_help(update, context)
