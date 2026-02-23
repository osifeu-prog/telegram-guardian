# Telegram Guardian

A Telegram bot for MANH token with FastAPI portal.

## Quick Start
1. Copy `.env.example` to `.env` and edit
2. Install: `pip install -r web_portal/requirements.txt`
3. Run: `python -m app.main`
4. Test: `.\run_checks.ps1`

See full docs in the repository.

ניתוח סופי: פרויקט Telegram Guardian
לאחר קבלת כל הקבצים, ניתן להציג תמונה מלאה ומפורטת של המערכת. להלן סיכום מקיף הכולל ארכיטקטורה, רכיבים, זרימת נתונים, אבטחה, פיתוח, בדיקות ופריסה.

1. מטרת הפרויקט
Telegram Guardian הוא בוט טלגרם לניהול טוקן מסוג MANH (מבוסס על רשת TON) הכולל:

קנייה ומכירה של MANH תמורת TON.

מסחר P2P בין משתמשים.

מערכת referral עם בונוסים.

לידרבורד יומי/שבועי.

ממשק ניהול למנהלים.

Mini App (דף אינטרנט) המוטמע בטלגרם להצגת נתוני המשתמש.

המערכת בנויה כשירות Web (FastAPI) המאפשר גם ממשק API וגם Webhook לקבלת עדכונים מטלגרם.

2. ארכיטקטורה כללית











שכבת ממשק: בוט טלגרם (פקודות) + Mini App (דפדפן מוטמע).

שכבת אפליקציה: FastAPI עם נתיבי API, טיפול ב-Webhook, ניהול משתמשים ותשלומים.

שכבת תשתית: PostgreSQL (נתונים), Redis (מגבלות קצב), TON Center API (אימות תשלומים).

3. רכיבים עיקריים
3.1. בוט טלגרם (tg_bot.py)
פקודות נתמכות: למעלה מ-25 פקודות, כולל /start, /help, /buy, /sell, /leaderboard, /referral, /withdraw, /admin_stats ועוד.

תכונות מיוחדות:

Rate limiting באמצעות Redis (דקורטור @rate_limit).

ניהול סשן DB אוטומטי (_with_db).

יצירת חשבוניות ואישור תשלומים מול TON Center.

ניהול הזמנות P2P והתאמה אוטומטית.

שליחת הודעות לקבוצות ייעודיות (לוגים, תשלומים, אבטחה).

אבטחה: בדיקת הרשאות מנהל, רישום אירועי אבטחה (SecurityLog).

3.2. FastAPI (main.py ו-database/main.py)
נקודת כניסה: web_portal/app/main.py (הגרסה העדכנית) מגדיר lifespan, כולל ראוטרים ומספק נקודות קצה.

ראוטרים:

user_router, api_router – API למשתמשים.

diag_router – אבחון.

tg_ops_router, tg_router – ניהול בוט ו-webhook.

manh_router – פעולות MANH.

pay_router – תשלומים.

נקודות קצה בולטות:

/api/user_data – החזרת יתרה, חשבוניות ולידרבורד.

/mini_app – הצגת ממשק המשתמש (dashboard.html).

/tg/diagnostics – מידע על הבוט.

/ops/* – נקודות למפעיל (דורשות טוקן OPS).

בעיה קלה: קיים קובץ כפול database/main.py שנראה כשארית ישנה ולא פעיל.

3.3. ניהול משתמשים ו-MANH (manh/)
מודלים: User, Referral, LedgerEvent (ב-models.py הנכון).

שירותים:

get_balance, award_manh – ניהול יתרה.

leaderboard – חישוב לידרבורד לפי bucket יומי/שבועי.

set_opt_in – בחירת משתמש להשתתפות בלידרבורד.

ראוטר: /manh/optin, /manh/balance, /manh/award, /manh/leaderboard.

3.4. מערכת תשלומים TON (payments/ton/)
יצירת חשבונית (create_invoice):

מחשבת כמויות TON ו-MANH לפי שער ILS.

מייצרת memo ייחודי עם HMAC לזיהוי.

שומרת ב-manh_invoices.

אישור תשלומים (poll_and_confirm_invoices):

מביא עסקאות מ-TON Center ל-treasury address.

משווה memo ומעדכן סטטוס ל-"paid".

מזכה את המשתמש ב-MANH ומוסיף XP.

משיכות (withdrawals.py):

יצירת בקשת משיכה (רק אם עמד בתנאי סף).

אישור/דחייה על ידי מנהל.

עדכון יתרה בהתאם.

שער (price_feed.py): מקבל שער TON/ILS מ-Coingecko או ידני (cache ל-120 שניות).

3.5. מסחר P2P (p2p/service.py)
הזמנות: SellOrder, BuyOrder, P2POrder (מאוחד).

פונקציות:

create_sell_order, create_buy_order.

match_orders – התאמת הזמנות לפי מחיר (סוחר BEST).

get_open_orders, cancel_order.

שימוש: הפקודות /p2p_buy, /sell, /orders, /cancel קוראות לפונקציות אלו.

3.6. מערכת referral (referrals.py)
יצירת קוד referral אקראי (מתחיל ב-'R').

עיבוד referral בפקודת /start עם קוד: מוסיף רשומת Referral, מעניק 5 MANH למזמין.

רשימת מוזמנים: /referrals.

3.7. API ציבורי (api/)
user.py: /api/user_data – מחזיר פרטי משתמש וחשבוניות.

router.py: /api/user_data (גם GET וגם POST), /api/orders.

router_diagnostic.py: /diagnostic/status – סטטוס כללי (דורש סוד פנימי).

3.8. מודלים (models.py)
המודלים העדכניים כוללים:

User: id (BIGINT), username, first_name, balance_manh, total_xp, referral_code, referred_by.

Withdrawal: id, user_id, amount_manh, destination_address, status.

Invoice: id, user_id, ils_amount, ton_amount, manh_amount, status, comment.

Referral: id, referrer_id, referred_id, reward_given.

P2POrder: id, user_id, type, amount, price, status (משמש בבוט).

SellOrder, BuyOrder, Trade – למודל P2P מורחב.

SecurityLog: אירועי אבטחה.

ChatId: תיעוד chat_ids (נוסף במיגרציה).

3.9. תצורה ואבטחה (core/)
settings.py: ניהול משתני סביבה עם Pydantic (כולל ADMIN_IDS כמספרים).

security.py: פונקציות קריפטוגרפיות (constant_time_equals, token_fingerprint).

ops_auth.py: אימות טוקן OPS (משווה hash).

tg_initdata.py: אימות initData ממיני-אפ טלגרם (חתימת HMAC).

3.10. בדיקות (tests/test_bot_handlers.py)
pytest עם מוקים ל-Redis, Settings ו-DB.

כיסוי: 15 בדיקות ל-handlers עיקריים (cmd_start, cmd_buy, cmd_withdraw וכו').

משתמש ב-sqlite:///:memory: לבדיקות DB.

3.11. ניהול גרסאות מסד נתונים (Alembic)
מיגרציות: add_chat_ids_20260219_145003.py – הוספת טבלת chat_ids.

תיקון היסטוריה: stamp_final_20260219_153823.py – איפוס alembic_version ל-revision יחיד (פתרון לבעיות מיזוג).

קונפיגורציה: alembic.ini ו-env.py – טוענים DATABASE_URL מסביבה ומבצעים מיגרציות.

3.12. תשתית ופריסה
Dockerfile (לא נשלח אך מוזכר ב-railway.toml).

Railway: קובץ railway.toml מגדיר build ו-healthcheck.

משתני סביבה: .env.example מכיל דוגמה לכל המשתנים הנדרשים.

3.13. תיעוד (docs/)
קבצי ADR, OVERVIEW, ARCHITECTURE, COMPONENTS, DATA_FLOW, SECURITY_GUARDRAILS, DEV_WORKFLOW, DEPLOYMENT, OPERATIONS, TROUBLESHOOTING, GLOSSARY, STATE, NEXT, RUNBOOK, SECURITY.

חלקם ריקים כרגע – שלד לתיעוד עתידי.

4. זרימת נתונים עיקריות
4.1. קניית MANH
משתמש שולח /buy 100 (ILS).

הבוט יוצר חשבונית באמצעות create_invoice:

מחשב ton_amount לפי שער TON/ILS.

מחשב manh_amount לפי MANH_PRICE_ILS.

יוצר memo ייחודי (מכיל invoice ID וחתימה חלקית).

שומר ב-manh_invoices סטטוס PENDING.

הבוט משיב עם כתובת treasury, memo והנחיות.

משתמש שולח TON לכתובת עם memo נכון.

(אוטומציה או מנהל) מפעיל /poll_confirm או קריאת API /pay/ton/poll עם סוד פנימי.

poll_and_confirm_invoices:

מביא עסקאות מ-TON Center.

משווה memo, מוצא חשבונית מתאימה.

מעדכן סטטוס ל-paid, confirmed_at.

מוסיף ל-user.balance_manh ו-user.total_xp.

המשתמש מקבל אישור.

4.2. מכירת MANH ב-P2P
משתמש שולח /sell 50 0.5 (50 MANH במחיר 0.5 TON כל אחד).

הבוט בודק יתרה, יוצר P2POrder עם type='sell', status='open'.

בפקודה נפרדת (/orders) ניתן לראות הזמנות פתוחות.

פונקציית match_orders (מופעלת ידנית או אוטומטית) מתאימה בין הזמנות קנייה למכירה לפי מחיר, ומבצעת טריידים.

לאחר התאמה, היתרות מתעדכנות וההזמנות נסגרות.

4.3. משיכת MANH
משתמש שולח /withdraw 10 UQ....

create_withdrawal בודק יתרה ומינימום, מקטין יתרה ומוסיף רשומת Withdrawal בסטטוס pending.

מנהל מאשר באמצעות /approve_withdrawal (רק ADMIN_IDS).

לאחר אישור, ניתן לבצע העברת TON בפועל (לא אוטומטי) ולעדכן את הבקשה ל-completed עם tx_hash.

4.4. Mini App
דף dashboard.html (או mini_app.html) נטען דרך /mini_app.

המשתמש מתחבר דרך Telegram Init Data (מאומת ב-api_airdrop.py).

ניתן לתבוע איירדרופ דרך /api/airdrop/claim (אם מוגדר).

5. אבטחה והגנות
Rate limiting: Redis מונע הצפה בפקודות רגישות (/withdraw, /p2p_buy).

אימות Webhook: X-Telegram-Bot-Api-Secret-Token (מוגדר ב-TELEGRAM_WEBHOOK_SECRET).

סודות פנימיים: INTERNAL_API_SECRET / INTERNAL_SIGNING_SECRET מגנים על /poll ועל נקודות רגישות.

אימות Mini App: verify_telegram_init_data מוודא חתימת HMAC של נתוני ההתחברות.

טוקן OPS: OPS_TOKEN_HASH מגן על נקודות /ops/* (השוואה באמצעות constant_time_equals).

HMAC ל-memo: חתימת memo בחשבונית מונעת שימוש חוזר או זיוף.

לוגי אבטחה: SecurityLog מתעד אירועים כמו חריגות rate limit.

6. פיתוח ובדיקות
סביבת פיתוח: דורש Python 3.11+, Redis, PostgreSQL.

הרצה מקומית: python -m app.main לאחר הגדרת .env.

בדיקות: pytest tests/test_bot_handlers.py (עם מוקים).

סקריפטים: run_checks.ps1 (מוזכר ב-README) – כנראה מריץ בדיקות ולינט.

נקודות תורפה קלות:

כפילות בין main.py ל-database/main.py – יש לאחד.

חלק מהפונקציות מחזירות dict, אחרות זורקות exceptions – כדאי לאחד סגנון.

match_orders לא מופעל אוטומטית – יש לשקול תזמון רקע.

poll_and_confirm_invoices נקרא רק ידנית – כדאי להפוך לאוטומטי (למשל, job רץ כל דקה).

7. פריסה (Railway)
תבנית: railway.toml מגדיר build דרך Dockerfile ו-healthcheck path /health.

משתני סביבה: כל ההגדרות נטענות מ-.env או משתני Railway.

מסד נתונים: PostgreSQL מנוהל על ידי Railway (או חיצוני).

Redis: אופציונלי, משתנה REDIS_URL.

8. סיכום והמלצות
הפרויקט בנוי היטב, עם הפרדה ברורה בין רכיבים, שימוש בטכנולוגיות עדכניות, ותיעוד בסיסי. קיימת מערכת שלמה לניהול טוקן MANH הכוללת קנייה, מכירה P2P, רפראנים ולידרבורד. האבטחה מטופלת ברמה טובה (HMAC, rate limiting, אימות נתונים).

המלצות לשיפור:

לאחד את שני קבצי main.py ולהסיר את המיותר.

להוסיף job רקע (למשל, FastAPI BackgroundTasks או Celery) לבדיקה אוטומטית של חשבוניות pending.

להפעיל את match_orders באופן אוטומטי עם כל הזמנה חדשה או ב-task周期י.

להשלים את קבצי התיעוד הריקים ב-docs/.

להוסיף בדיקות נוספות, במיוחד לוגיקת P2P ותשלומים.

לשקול מעבר ל-SQLAlchemy async לביצועים טובים יותר תחת FastAPI.

בסך הכל, הפרויקט במצב מתקדם ומוכן להמשך פיתוח והשקה.

