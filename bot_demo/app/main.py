from __future__ import annotations

import os
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

LOG_LEVEL = (os.environ.get("LOG_LEVEL") or "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
log = logging.getLogger("bot_demo")

START_TEXT = """<b>Telegram Guardian  Risk Hygiene (Local-First)</b>

<b>×‍×” ×–×”?</b>
×›×œ×™ ×œ×•×§×گ×œ×™ ×‘×œ×‘×“ ×©×،×•×¨×§ ×“×™×گ×œ×•×’×™×‌ ×‘-Telegram (Read-Only) ×•×‍×¤×™×§ ×“×•×— Risk Hygiene.

<b>×¤×¨×ک×™×•×ھ</b>
 ×¨×¥ ×¢×œ ×”×‍×—×©×‘ ×©×œ×ڑ
 ×گ×™×ں ×”×¢×œ×گ×” ×©×œ ×¦×گ×ک×™×‌/×”×•×“×¢×•×ھ ×œ×©×¨×ھ
 ×”×“×‍×• ×”×¦×™×‘×•×¨×™ ×”×•×گ × ×ھ×•× ×™×‌ ×،×™× ×ھ×ک×™×™×‌ ×‘×œ×‘×“

<b>×§×™×©×•×¨×™×‌</b>
 ×“×‍×•: https://osifeu-prog.github.io/telegram-guardian/
 ×§×•×“: https://github.com/osifeu-prog/telegram-guardian

<b>×¤×§×•×“×•×ھ</b>
/howto   ×”×ھ×§× ×” ×•×”×¨×¦×” (Windows)
/privacy ×‍×“×™× ×™×•×ھ ×¤×¨×ک×™×•×ھ ×§×¦×¨×”
/demo    ×§×™×©×•×¨ ×œ×“×‍×•
"""

HOWTO_TEXT = """<b>×”×ھ×§× ×” ×•×”×¨×¦×” (Windows)</b>
1) ×©×›×¤×œ ×گ×ھ ×”×¨×™×¤×•
2) ×¦×•×¨ venv ×•×”×ھ×§×ں requirements
3) ×”×’×“×¨ TELEGRAM_BOT_TOKEN
4) ×”×¨×¥ ×گ×ھ ×”×‘×•×ک (polling)

×¨×‍×–: ×–×” ×“×‍×•. ×گ×™×ں ×¤×” webhook.
"""

PRIVACY_TEXT = """<b>×¤×¨×ک×™×•×ھ  TL;DR</b>
×”×¤×¨×•×™×§×ک ×‍×ھ×•×›× ×ں ×œ×”×™×•×ھ Local-First.
×”×“×‍×•/×‍×،×›×™×‌ ×œ×گ ×گ×‍×•×¨×™×‌ ×œ×”×›×™×œ ×“×گ×ک×” ×گ×‍×™×ھ×™ ×©×œ Telegram.
"""

DEMO_TEXT = "×“×‍×•: https://osifeu-prog.github.io/telegram-guardian/"

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(START_TEXT, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

async def cmd_howto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(HOWTO_TEXT, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

async def cmd_privacy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(PRIVACY_TEXT, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

async def cmd_demo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(DEMO_TEXT, disable_web_page_preview=True)

def main() -> int:
    token = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        raise SystemExit("Missing TELEGRAM_BOT_TOKEN env var")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("howto", cmd_howto))
    app.add_handler(CommandHandler("privacy", cmd_privacy))
    app.add_handler(CommandHandler("demo", cmd_demo))

    log.info("bot_demo starting (polling)")
    app.run_polling(close_loop=False)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())