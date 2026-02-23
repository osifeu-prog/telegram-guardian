import asyncio
import logging
from telegram import Bot

logger = logging.getLogger(__name__)

async def safe_send_message(bot: Bot, chat_id: int, text: str, **kwargs):
    logger.info(f"safe_send_message: text type={type(text)}, length={len(text)}")
    if not isinstance(text, str):
        logger.error(f"safe_send_message: text is not str! converting...")
        # אם זה bytes, ננסה להמיר ל-UTF-8
        text = text.decode('utf-8', errors='replace') if isinstance(text, bytes) else str(text)
    max_len = 4000
    if len(text) <= max_len:
        return await bot.send_message(chat_id, text, **kwargs)

    parts = [text[i:i+max_len] for i in range(0, len(text), max_len)]
    for idx, part in enumerate(parts):
        logger.info(f"safe_send_message: sending part {idx+1}/{len(parts)} (len={len(part)})")
        await bot.send_message(chat_id, part, **kwargs)
        await asyncio.sleep(0.5)


def safe_decimal(value: str, default=None):
    """ממיר מחרוזת לערך Decimal, מסיר תווים לא מספריים."""
    import re
    from decimal import Decimal, InvalidOperation
    if not isinstance(value, str):
        return default
    # הסרת כל התווים שאינם ספרות, נקודה, מינוס
    cleaned = re.sub(r'[^\d.-]', '', value)
    try:
        return Decimal(cleaned)
    except (InvalidOperation, TypeError):
        return default


