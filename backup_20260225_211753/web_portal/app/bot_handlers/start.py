from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime

from web_portal.app.db import SessionLocal
from web_portal.app.database.models import User, Referral

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
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
    finally:
        db.close()


