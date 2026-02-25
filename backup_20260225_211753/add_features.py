import os
import re

def update_file(file_path, pattern, replacement):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"? {file_path} ?????.")
    else:
        print(f"? {file_path} ?? ????.")

# 1. ????? LedgerEvent ???????
models_path = "web_portal/app/database/models.py"
with open(models_path, 'r', encoding='utf-8') as f:
    models_content = f.read()

if "class LedgerEvent" not in models_content:
    ledger_model = '''
class LedgerEvent(Base):
    __tablename__ = 'ledger_events'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    event_type = Column(String, nullable=False)  # 'referral', 'purchase', 'withdrawal', 'xp_award'
    amount = Column(Numeric(20, 9), nullable=False)
    balance_after = Column(Numeric(20, 9), nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    meta = Column(JSON, nullable=True)
'''
    models_content = re.sub(r'(?=class SecurityLog)', ledger_model + '\n\n', models_content, flags=re.DOTALL)
    with open(models_path, 'w', encoding='utf-8') as f:
        f.write(models_content)
    print("? LedgerEvent ????.")
else:
    print("? LedgerEvent ??? ????.")

# 2. ????? ???? ledger.py
ledger_utils = '''from sqlalchemy.orm import Session
from web_portal.app.database.models import LedgerEvent, User
from decimal import Decimal
import json

def add_ledger_event(db: Session, user_id: int, event_type: str, amount: Decimal, description: str = None, meta: dict = None):
    user = db.get(User, user_id)
    balance_after = user.balance_manh if user else Decimal(0)
    event = LedgerEvent(
        user_id=user_id,
        event_type=event_type,
        amount=amount,
        balance_after=balance_after,
        description=description,
        meta=json.dumps(meta) if meta else None
    )
    db.add(event)
    db.commit()
    return event

def get_user_ledger(db: Session, user_id: int, limit: int = 10):
    return db.query(LedgerEvent).filter_by(user_id=user_id).order_by(LedgerEvent.created_at.desc()).limit(limit).all()
'''
ledger_path = "web_portal/app/manh/ledger.py"
with open(ledger_path, 'w', encoding='utf-8') as f:
    f.write(ledger_utils)
print("? ledger.py ????.")

# 3. ????? tg_bot.py
tg_bot_path = "web_portal/app/tg_bot.py"
with open(tg_bot_path, 'r', encoding='utf-8') as f:
    tg_content = f.read()

# ????? ???? ledger
tg_content = re.sub(
    r'(from app\.manh\.referrals import .*)',
    r'\1\nfrom web_portal.app.manh.ledger import add_ledger_event',
    tg_content
)

# ????? XP ?????? ?-ledger ?-cmd_start (???????)
pattern_start = r'(if referral_code:.*?referrer\.balance_manh \+= 5.*?db\.add\(referrer\))'
replacement_start = r'''\1
                # ????? XP ?????
                referrer.total_xp += 5
                add_ledger_event(db, referrer.id, 'referral', 5, f'Referral bonus for inviting user {user_id}')'''
tg_content = re.sub(pattern_start, replacement_start, tg_content, flags=re.DOTALL)

# ????? ???????? cmd_level
cmd_level = '''

@_with_db
async def cmd_level(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    user = db.get(User, user_id)
    if not user:
        await update.message.reply_text("User not found.")
        return
    xp = user.total_xp or 0
    level = int((xp / 100) ** 0.5) + 1
    next_level_xp = ((level) ** 2) * 100
    xp_needed = next_level_xp - xp
    await update.message.reply_text(
        f"Level: {level}\\n"
        f"XP: {xp}\\n"
        f"XP to next level: {xp_needed}"
    )
'''
if "async def cmd_level" not in tg_content:
    tg_content = re.sub(r'(?=async def cmd_faq)', cmd_level + '\n\n', tg_content)

# ????? ???????? cmd_history
cmd_history = '''

@_with_db
async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session):
    user_id = update.effective_user.id
    from web_portal.app.manh.ledger import get_user_ledger
    events = get_user_ledger(db, user_id, limit=10)
    if not events:
        await update.message.reply_text("No history yet.")
        return
    lines = ["Your recent activity:"]
    for e in events:
        date = e.created_at.strftime('%Y-%m-%d %H:%M')
        lines.append(f"{date} | {e.event_type} | {e.amount} MANH | {e.description or ''}")
    await update.message.reply_text("\\n".join(lines))
'''
if "async def cmd_history" not in tg_content:
    tg_content = re.sub(r'(?=async def cmd_faq)', cmd_history + '\n\n', tg_content)

# ????? ??????? ?????? ?-init_bot
tg_content = re.sub(
    r'(app\.add_handler\(CommandHandler\("faq", cmd_faq\)\))',
    r'\1\n    app.add_handler(CommandHandler("level", cmd_level))\n    app.add_handler(CommandHandler("history", cmd_history))',
    tg_content
)

# ????? ????? ????? ?-10
tg_content = re.sub(r'(referrer\.balance_manh \+= )5', r'\g<1>10', tg_content)

with open(tg_bot_path, 'w', encoding='utf-8') as f:
    f.write(tg_content)
print("? tg_bot.py ????? ?? XP, level, history, referral reward=10.")

# 4. ????? service.py (?????? ledger ?????? ?????)
service_path = "web_portal/app/payments/ton/service.py"
with open(service_path, 'r', encoding='utf-8') as f:
    service_content = f.read()

# ????? ???? ledger
service_content = re.sub(
    r'(from app\.database\.models import Invoice, User)',
    r'\1\nfrom web_portal.app.manh.ledger import add_ledger_event',
    service_content
)

# ????? ????? ?-ledger ???? ????? ?????
pattern_service = r'(if user:.*?user\.balance_manh \+= inv\.manh_amount.*?db\.add\(user\))'
replacement_service = r'''\1
                add_ledger_event(db, user.id, 'purchase', inv.manh_amount, f'Payment confirmed for invoice {inv.invoice_id}')'''
service_content = re.sub(pattern_service, replacement_service, service_content, flags=re.DOTALL)

with open(service_path, 'w', encoding='utf-8') as f:
    f.write(service_content)
print("? service.py ????? (ledger ?????? ?????).")

# 5. ????? settings.py  ???? class Config
settings_path = "web_portal/app/core/settings.py"
with open(settings_path, 'r', encoding='utf-8') as f:
    settings_content = f.read()
settings_content = re.sub(
    r'class Config:.*?extra = "allow"',
    'model_config = ConfigDict(env_file=".env", case_sensitive=True, extra="allow")',
    settings_content,
    flags=re.DOTALL
)
with open(settings_path, 'w', encoding='utf-8') as f:
    f.write(settings_content)
print("? settings.py ???? (model_config).")

print("\n? ?? ??????? ????? ??????!")
print("??? ???: pytest tests/ -v ??? ????? ???? ????.")
