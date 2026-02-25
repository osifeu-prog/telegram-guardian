#!/usr/bin/env python
"""
Health check script  בדיקת תקינות המערכת.
ניתן להפעיל ישירות או לקרוא מתוך הבוט.
"""
import sys
import os
from pathlib import Path

# הוספת הפרויקט לנתיב
sys.path.insert(0, str(Path(__file__).parent))

def check_database():
    try:
        from web_portal.app.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Database connection OK"
    except Exception as e:
        return False, f"Database error: {e}"

def check_redis():
    try:
        from web_portal.app.tg_bot import get_redis
        import asyncio
        r = asyncio.run(get_redis())
        if r:
            asyncio.run(r.ping())
            return True, "Redis connection OK"
        else:
            return False, "Redis not configured"
    except Exception as e:
        return False, f"Redis error: {e}"

def check_env():
    required_vars = ['BOT_TOKEN', 'DATABASE_URL', 'TON_TREASURY_ADDRESS']
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        return False, f"Missing env vars: {missing}"
    return True, "All required env vars set"

if __name__ == "__main__":
    print("Running health checks...")
    results = {}
    for name, func in [("Database", check_database), ("Redis", check_redis), ("Environment", check_env)]:
        ok, msg = func()
        results[name] = (ok, msg)
        status = "✅" if ok else "❌"
        print(f"{status} {name}: {msg}")
    if all(ok for ok, _ in results.values()):
        print("\n✅ All checks passed!")
        sys.exit(0)
    else:
        print("\n❌ Some checks failed.")
        sys.exit(1)
