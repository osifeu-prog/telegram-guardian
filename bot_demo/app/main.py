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

 ×‍×” ×–×”?
×›×œ×™ ×œ×•×§×گ×œ×™ ×‘×œ×‘×“ ×©×،×•×¨×§ ×“×™×گ×œ×•×’×™×‌ ×‘-Telegram (Read-Only) ×•×‍×¤×™×§ ×“×•×— Risk Hygiene.

 ×¤×¨×ک×™×•×ھ
 ×¨×¥ ×¢×œ ×”×‍×—×©×‘ ×©×œ×ڑ
 ×گ×™×ں ×”×¢×œ×گ×” ×©×œ ×¦×گ×ک×™×‌/×”×•×“×¢×•×ھ ×œ×©×¨×ھ
 ×”×“×‍×• ×”×¦×™×‘×•×¨×™ ×”×•×گ × ×ھ×•× ×™×‌ ×،×™× ×ھ×ک×™×™×‌ ×‘×œ×‘×“

 ×“×‍×•: {DEMO_SITE}
 ×§×•×“: {GITHUB_REPO}

×¤×§×•×“×•×ھ:
 /howto   ×”×ھ×§× ×” ×•×”×¨×¦×” (Windows)
 /privacy  ×‍×“×™× ×™×•×ھ ×¤×¨×ک×™×•×ھ ×§×¦×¨×”
 /demo    ×§×™×©×•×¨ ×œ×“×‍×•
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

 Local-first: ×”×،×¨×™×§×” ×•×”×“×•×—×•×ھ × ×•×¦×¨×™×‌ ×گ×¦×œ×ڑ ×‍×§×•×‍×™×ھ.
 ×”×‘×•×ک ×”×–×” ×”×•×گ ×ھ×“×‍×™×ھ×™/×‍×“×¨×™×ڑ ×‘×œ×‘×“: ×œ×گ ×،×•×¨×§, ×œ×گ ×§×•×¨×گ, ×œ×گ ×©×•×‍×¨ ×‍×™×“×¢ ×‍×”-Telegram ×©×œ×ڑ.
 ×›×œ ×“×‍×• ×¦×™×‘×•×¨×™ ×‍×‘×•×،×، × ×ھ×•× ×™×‌ ×،×™× ×ھ×ک×™×™×‌ ×‘×œ×‘×“.
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
