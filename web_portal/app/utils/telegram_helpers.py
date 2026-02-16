import asyncio
from telegram import Bot

async def safe_send_message(bot: Bot, chat_id: int, text: str, **kwargs):
    """Sends long messages by splitting into parts (max 4000 chars)."""
    max_len = 4000
    if len(text) <= max_len:
        return await bot.send_message(chat_id, text, **kwargs)

    parts = [text[i:i+max_len] for i in range(0, len(text), max_len)]
    for part in parts:
        await bot.send_message(chat_id, part, **kwargs)
        await asyncio.sleep(0.5)  # small delay to avoid flooding
