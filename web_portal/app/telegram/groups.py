import logging
from telegram import Bot
from app.core.settings import settings

logger = logging.getLogger(__name__)

async def send_to_log_group(bot: Bot, text: str):
    """שולח הודעה לקבוצת הלוגים (אם הוגדרה)."""
    chat_id = settings.TG_LOG_GROUP
    if not chat_id:
        return
    try:
        await bot.send_message(chat_id=int(chat_id), text=text)
    except Exception as e:
        logger.error(f"Failed to send to log group: {e}")

async def send_to_payment_group(bot: Bot, text: str):
    """שולח הודעה לקבוצת התשלומים."""
    chat_id = settings.TG_PAYMENT_GROUP
    if not chat_id:
        return
    try:
        await bot.send_message(chat_id=int(chat_id), text=text)
    except Exception as e:
        logger.error(f"Failed to send to payment group: {e}")

async def send_to_referral_group(bot: Bot, text: str):
    """שולח הודעה לקבוצת ההפניות."""
    chat_id = settings.TG_REFERRAL_GROUP
    if not chat_id:
        return
    try:
        await bot.send_message(chat_id=int(chat_id), text=text)
    except Exception as e:
        logger.error(f"Failed to send to referral group: {e}")


