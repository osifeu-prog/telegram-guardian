import os
from datetime import datetime, timezone

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

def utcnow_iso():
    return datetime.now(timezone.utc).isoformat()

GITHUB_REPO = "https://github.com/osifeu-prog/telegram-guardian"
DEMO_SITE   = "https://osifeu-prog.github.io/telegram-guardian/"

TEXT_START = f"""\
<b>Telegram Guardian  Risk Hygiene (Local-First)</b>

 מה זה?
כלי לוקאלי בלבד שסורק דיאלוגים ב-Telegram (Read-Only) ומפיק דוח Risk Hygiene.

 פרטיות
 רץ על המחשב שלך
 אין העלאה של צאטים/הודעות לשרת
 הדמו הציבורי הוא נתונים סינתטיים בלבד

 דמו: {DEMO_SITE}
 קוד: {GITHUB_REPO}

פקודות:
 /howto   התקנה והרצה (Windows)
 /privacy  מדיניות פרטיות קצרה
 /demo    קישור לדמו
"""

TEXT_HOWTO = """\
<b>Install & Run (Windows)</b>

1) Clone:
<code>git clone https://github.com/osifeu-prog/telegram-guardian.git</code>

2) Create venv:
<code>py -m venv .venv</code>
<code>.\.venv\Scripts\Activate.ps1</code>

3) Install:
<code>pip install -r requirements.txt</code>

4) Run:
<code>powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_all.ps1</code>

Outputs:
 out/scan_report.json
 out/risk_report.csv
 out/risk_report.excel.csv
"""

TEXT_PRIVACY = """\
<b>Privacy Promise</b>

 Local-first: הסריקה והדוחות נוצרים אצלך מקומית.
 הבוט הזה הוא תדמיתי/מדריך בלבד: לא סורק, לא קורא, לא שומר מידע מה-Telegram שלך.
 כל דמו ציבורי מבוסס נתונים סינתטיים בלבד.
"""

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(TEXT_START, parse_mode=ParseMode.HTML, disable_web_page_preview=False)

async def cmd_howto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(TEXT_HOWTO, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

async def cmd_privacy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(TEXT_PRIVACY, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

async def cmd_demo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Demo (synthetic): {DEMO_SITE}", disable_web_page_preview=False)

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Missing TELEGRAM_BOT_TOKEN env var")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("howto", cmd_howto))
    app.add_handler(CommandHandler("privacy", cmd_privacy))
    app.add_handler(CommandHandler("demo", cmd_demo))

    # simplest: long polling (no webhook setup required)
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
