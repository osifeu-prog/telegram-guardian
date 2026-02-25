import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Add project path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'web_portal')))

# Set a fake DATABASE_URL
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

# Import bot modules (only what we need)
from app.tg_bot import (
    cmd_start, cmd_help, cmd_manh, cmd_leaderboard, cmd_buy, cmd_invoices,
    cmd_poll_confirm, cmd_miniapp, cmd_withdraw, cmd_withdrawals, cmd_chatid,
    cmd_p2p_buy, cmd_sell, cmd_orders, cmd_cancel, cmd_referral, cmd_faq
)
from app.core.settings import settings

# Mock Redis
@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    import redis.asyncio
    class MockRedis:
        async def ping(self): return True
        def pipeline(self): return self
        async def execute(self):
            return [1, 2, 0, True]
        def zadd(self, *args, **kwargs): return self
        def zremrangebyscore(self, *args, **kwargs): return self
        def zcard(self, *args, **kwargs): return self
        def expire(self, *args, **kwargs): return self
    monkeypatch.setattr(redis.asyncio, 'from_url', lambda *a, **kw: MockRedis())
    monkeypatch.setattr('app.tg_bot.get_redis', AsyncMock(return_value=MockRedis()))

# Mock settings
@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    monkeypatch.setattr(settings, 'BOT_TOKEN', 'FAKE_TOKEN')
    monkeypatch.setattr(settings, 'ADMIN_IDS', [])
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    def fake_getenv(key, default=None):
        if key == 'DATABASE_URL':
            return 'sqlite:///:memory:'
        if key == 'INTERNAL_SIGNING_SECRET':
            return 'a'*32  # dummy secret
        return default
    monkeypatch.setattr(os, 'getenv', fake_getenv)

# Mock DB session
@pytest.fixture
def mock_db():
    with patch('app.tg_bot.SessionLocal') as mock_session:
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        yield mock_db

# Helper to call handlers with db mock (since _with_db expects 2 args and adds db)
async def call_with_db(handler, update, context, db_mock):
    with patch('app.tg_bot.SessionLocal', return_value=db_mock):
        await handler(update, context)

# -------------------- Handler Tests --------------------
@pytest.mark.asyncio
async def test_cmd_start(mock_db):
    from telegram import Update, Message
    from telegram.ext import ContextTypes
    update = MagicMock(spec=Update)
    update.effective_user.id = 12345
    update.effective_user.username = 'testuser'
    update.effective_user.first_name = 'Test'
    update.message = MagicMock(spec=Message)
    update.message.text = '/start'
    update.message.reply_text = AsyncMock()
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_db.get.return_value = None
    await call_with_db(cmd_start, update, context, mock_db)
    update.message.reply_text.assert_awaited_once()
    args = update.message.reply_text.call_args[0][0]
    assert "Welcome" in args or "Welcome back" in args

@pytest.mark.asyncio
async def test_cmd_help():
    from telegram import Update, Message
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    await cmd_help(update, context)
    update.message.reply_text.assert_awaited_once()
    args = update.message.reply_text.call_args[0][0]
    assert "Available commands:" in args

@pytest.mark.asyncio
async def test_cmd_manh(mock_db):
    from telegram import Update, Message
    update = MagicMock(spec=Update)
    update.effective_user.id = 12345
    update.effective_user.username = 'testuser'
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    with patch('app.tg_bot.get_balance', return_value=100):
        await call_with_db(cmd_manh, update, context, mock_db)
    update.message.reply_text.assert_awaited_once()
    assert "MANH balance" in update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_cmd_leaderboard(mock_db):
    from telegram import Update, Message
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = []
    mock_leaderboard = [{'user_id': 1, 'username': 'user1', 'total_manh': 50}]
    with patch('app.tg_bot.get_leaderboard', return_value=mock_leaderboard):
        await call_with_db(cmd_leaderboard, update, context, mock_db)
    update.message.reply_text.assert_awaited_once()
    assert "Leaderboard" in update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_cmd_buy(mock_db):
    from telegram import Update, Message
    update = MagicMock(spec=Update)
    update.effective_user.id = 12345
    update.effective_user.username = 'testuser'
    update.message = MagicMock(spec=Message)
    update.message.text = '/buy 100'
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    with patch('app.tg_bot.create_invoice') as mock_create:
        mock_inv = MagicMock()
        mock_inv.ton_amount = 5.2
        mock_inv.manh_amount = 520
        mock_inv.treasury_address = 'treasury'
        mock_inv.comment = 'memo'
        mock_create.return_value = mock_inv
        await call_with_db(cmd_buy, update, context, mock_db)
    update.message.reply_text.assert_awaited_once()
    assert "Invoice created" in update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_cmd_invoices(mock_db):
    from telegram import Update, Message
    update = MagicMock(spec=Update)
    update.effective_user.id = 12345
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    mock_invoice = MagicMock()
    mock_invoice.id = 'testid123'
    mock_invoice.status = 'pending'
    mock_invoice.ils_amount = 100
    mock_invoice.created_at = MagicMock()
    mock_invoice.created_at.date.return_value = '2026-01-01'
    with patch('app.tg_bot.list_invoices', return_value=[mock_invoice]):
        await call_with_db(cmd_invoices, update, context, mock_db)
    update.message.reply_text.assert_awaited_once()
    assert "invoices" in update.message.reply_text.call_args[0][0].lower()

@pytest.mark.asyncio
async def test_cmd_poll_confirm(mock_db):
    from telegram import Update, Message
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    with patch('app.tg_bot.poll_and_confirm_invoices', return_value={'confirmed': 1}):
        await call_with_db(cmd_poll_confirm, update, context, mock_db)
    update.message.reply_text.assert_called()

@pytest.mark.asyncio
async def test_cmd_miniapp():
    from telegram import Update, Message
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    await cmd_miniapp(update, context)
    update.message.reply_text.assert_awaited_once()
    args = update.message.reply_text.call_args[0][0]
    assert "dashboard" in args.lower()

@pytest.mark.asyncio
async def test_cmd_withdraw(mock_db):
    from telegram import Update, Message
    update = MagicMock(spec=Update)
    update.effective_user.id = 12345
    update.message = MagicMock(spec=Message)
    update.message.text = '/withdraw 10 UQtest123'
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    with patch('app.tg_bot.create_withdrawal') as mock_create:
        mock_withdrawal = MagicMock()
        mock_withdrawal.id = 'wd123'
        mock_create.return_value = mock_withdrawal
        await call_with_db(cmd_withdraw, update, context, mock_db)
    update.message.reply_text.assert_awaited_once()
    assert "Withdrawal request created" in update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_cmd_withdrawals(mock_db):
    from telegram import Update, Message
    update = MagicMock(spec=Update)
    update.effective_user.id = 12345
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    mock_w = MagicMock()
    mock_w.id = 'wd123'
    mock_w.amount_manh = 10
    mock_w.destination_address = 'UQtest123'
    mock_w.status = 'pending'
    with patch('app.tg_bot.get_user_withdrawals', return_value=[mock_w]):
        await call_with_db(cmd_withdrawals, update, context, mock_db)
    update.message.reply_text.assert_awaited_once()
    assert "withdrawals" in update.message.reply_text.call_args[0][0].lower()

@pytest.mark.asyncio
async def test_cmd_chatid():
    from telegram import Update, Message, Chat
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    update.effective_chat.type = 'private'
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    await cmd_chatid(update, context)
    update.message.reply_text.assert_awaited_once()
    assert "Chat ID: 12345" in update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_cmd_p2p_buy(mock_db):
    from telegram import Update, Message
    update = MagicMock(spec=Update)
    update.effective_user.id = 12345
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ['10', '5']
    await call_with_db(cmd_p2p_buy, update, context, mock_db)
    update.message.reply_text.assert_awaited_once()
    assert "Buy order created" in update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_cmd_sell(mock_db):
    from telegram import Update, Message
    update = MagicMock(spec=Update)
    update.effective_user.id = 12345
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ['10', '5']
    mock_db.get.return_value = MagicMock(balance_manh=100)
    await call_with_db(cmd_sell, update, context, mock_db)
    update.message.reply_text.assert_awaited_once()
    assert "Sell order created" in update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_cmd_orders(mock_db):
    from telegram import Update, Message
    from app.database.models import P2POrder
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    mock_order = MagicMock(spec=P2POrder)
    mock_order.id = 'order123'
    mock_order.type = 'buy'
    mock_order.amount = 10
    mock_order.price = 5
    mock_db.query.return_value.filter_by.return_value.all.return_value = [mock_order]
    await call_with_db(cmd_orders, update, context, mock_db)
    update.message.reply_text.assert_awaited_once()
    assert "Buy orders" in update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_cmd_cancel(mock_db):
    from telegram import Update, Message
    from app.database.models import P2POrder
    update = MagicMock(spec=Update)
    update.effective_user.id = 12345
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ['order123', 'buy']
    mock_order = MagicMock(spec=P2POrder)
    mock_order.status = 'open'
    mock_db.query.return_value.filter.return_value.first.return_value = mock_order
    await call_with_db(cmd_cancel, update, context, mock_db)
    update.message.reply_text.assert_awaited_once()
    assert "cancelled" in update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_cmd_referral(mock_db):
    from telegram import Update, Message
    update = MagicMock(spec=Update)
    update.effective_user.id = 12345
    update.message = MagicMock(spec=Message)
    update.message.reply_photo = AsyncMock()
    context = MagicMock()
    context.bot.username = 'testbot'
    mock_user = MagicMock()
    mock_user.referral_code = None
    mock_db.get.return_value = mock_user
    with patch('app.tg_bot.set_referral_code', return_value='R12345'):
        await call_with_db(cmd_referral, update, context, mock_db)
    update.message.reply_photo.assert_awaited_once()

@pytest.mark.asyncio
async def test_cmd_faq():
    from telegram import Update, Message
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    await cmd_faq(update, context)
    update.message.reply_text.assert_awaited_once()
    assert "Frequently Asked Questions" in update.message.reply_text.call_args[0][0]
