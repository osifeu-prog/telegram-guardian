import subprocess
import os
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from app.db import SessionLocal

async def cmd_admin_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # הגבלה למשתמש מסוים (החלף ל-ID שלך)
    if update.effective_user.id != 224223270:
        await update.message.reply_text("⛔ Access denied.")
        return
    try:
        await update.message.reply_text("🔄 Starting backup...")
        
        # 1. גיבוי מסד נתונים (דורש pg_dump במערכת)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_file = f"/tmp/backup_{timestamp}.sql"
        
        # קבלת DATABASE_URL מהסביבה
        db_url = os.getenv("DATABASE_URL", "")
        if not db_url:
            await update.message.reply_text("❌ DATABASE_URL not set.")
            return
        
        # הרצת pg_dump
        cmd = ["pg_dump", db_url, "--clean", "--if-exists", "-f", backup_file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            await update.message.reply_text(f"❌ Backup failed: {result.stderr}")
            return
        
        # 2. שליחת הקובץ למשתמש
        with open(backup_file, 'rb') as f:
            await context.bot.send_document(chat_id=update.effective_chat.id, document=f, filename=f"backup_{timestamp}.sql")
        
        # 3. ניקוי
        os.remove(backup_file)
        
        await update.message.reply_text("✅ Backup completed and sent.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
