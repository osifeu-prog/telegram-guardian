from __future__ import annotations

import os
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
log = logging.getLogger("bot_demo")

START_TEXT = """<b>Telegram Guardian  Risk Hygiene (Local-First)</b>

<b>מה זה?</b>
כלי לוקאלי בלבד שסורק דיאלוגים ב-Telegram (Read-Only) ומפיק דוח Risk Hygiene.

<b>פרטיות</b>
 רץ על המחשב שלך
 אין העלאה של צאטים/הודעות לשרת
 הדמו הציבורי הוא נתונים סינתטיים בלבד

<b>קישורים</b>
 דמו: https://osifeu-prog.github.io/telegram-guardian/
 קוד: https://github.com/osifeu-prog/telegram-guardian

<b>פקודות</b>
/howto   התקנה והרצה (Windows)
/privacy מדיניות פרטיות קצרה
/demo    קישור לדמו
"""

HOWTO_TEXT = """<b>התקנה והרצה (Windows)</b>
1) שכפל את הריפו
2) צור venv והתקן requirements
3) הגדר TELEGRAM_BOT_TOKEN
4) הרץ את הבוט (polling)

רמז: זה דמו. אין פה webhook.
"""

PRIVACY_TEXT = """<b>פרטיות  TL;DR</b>
הפרויקט מתוכנן להיות Local-First.
הדמו/מסכים לא אמורים להכיל דאטה אמיתי של Telegram.
"""

DEMO_TEXT = "דמו: https://osifeu-prog.github.io/telegram-guardian/"

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