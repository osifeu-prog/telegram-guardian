import re
from pathlib import Path

def has_main_import_app_tg_bot() -> bool:
    p = Path("app/main.py")
    if not p.exists():
        return False
    s = p.read_text(encoding="utf-8", errors="replace").replace("\r\n","\n")
    return bool(re.search(r"(?m)^\s*from\s+\.\s*tg_bot\s+import|^\s*from\s+app\.tg_bot\s+import|^\s*import\s+app\.tg_bot", s))

# Prefer the runtime file (app/tg_bot.py) if main imports it
cands = []
if Path("app/tg_bot.py").exists():
    cands.append(Path("app/tg_bot.py"))
if Path("web_portal/app/tg_bot.py").exists():
    cands.append(Path("web_portal/app/tg_bot.py"))

if not cands:
    raise SystemExit("No tg_bot.py found in app/ or web_portal/app/")

if has_main_import_app_tg_bot():
    # make sure app/tg_bot.py is first
    cands = sorted(cands, key=lambda p: (0 if str(p).replace("\\","/")=="app/tg_bot.py" else 1, str(p)))

SAFE_SEND = r'''
async def _safe_send(context, chat_id: int, text: str, reply_markup=None) -> None:
    """
    Safe sender:
    - retries
    - splits long texts using UTF-16 unit budget (Telegram limit)
    - keeps reply_markup only on first chunk
    """
    if text is None:
        return

    def u16_len(x: str) -> int:
        return len(x.encode("utf-16-le")) // 2

    MAX_U16 = 3500  # margin under Telegram limit (~4096 UTF-16 units)
    s = str(text)

    chunks = []
    while u16_len(s) > MAX_U16:
        # binary search best cut by UTF-16 units
        lo, hi = 1, len(s)
        best = 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if u16_len(s[:mid]) <= MAX_U16:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1

        cut = s.rfind("\n", 0, best)
        if cut < 1:
            cut = best
        chunks.append(s[:cut])
        s = s[cut:].lstrip("\n")
    chunks.append(s)

    for idx, part in enumerate(chunks):
        rm = reply_markup if idx == 0 else None
        for attempt in range(1, 4):
            try:
                await context.bot.send_message(chat_id=chat_id, text=part, reply_markup=rm)
                break
            except Exception as e:
                _log(f"TG_SEND retry={attempt}/3 err={e!r}")
                if attempt == 3:
                    raise
'''.strip("\n") + "\n\n"

CALLBACK_V2 = r'''
async def on_menu_callback_v2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = getattr(update, "callback_query", None)
    if not q:
        return

    data = (getattr(q, "data", "") or "").strip()
    msg = getattr(q, "message", None)
    chat = getattr(msg, "chat", None) if msg is not None else None
    chat_id = getattr(chat, "id", None)

    user = getattr(update, "effective_user", None)
    uid = getattr(user, "id", None)
    lang = _get_lang(int(uid)) if uid is not None else "he"

    async def _run_cmd(cmd, args=None):
        old = getattr(context, "args", None)
        try:
            context.args = args or []
            await cmd(update, context)
        finally:
            context.args = old

    try:
        await q.answer()

        if chat_id is None:
            _log(f"MENU callback no chat_id; data={data!r}")
            return

        # ---- Diagnostics ----
        if data in ("d:db", "m:db"):
            try:
                await _with_db(lambda db: db.execute(text("SELECT 1")).fetchone())
                await _safe_send(context, chat_id, t(lang, "db.ok"))
            except Exception as e:
                await _safe_send(context, chat_id, f"DB Ping failed: {e!r}")
            return

        if data in ("d:alembic", "m:alembic"):
            try:
                ver = await _with_db(lambda db: db.execute(text("SELECT version_num FROM alembic_version")).fetchone())
                v = ver[0] if ver else "unknown"
                await _safe_send(context, chat_id, t(lang, "alembic.ver", ver=v))
            except Exception as e:
                await _safe_send(context, chat_id, f"Alembic failed: {e!r}")
            return

        # ---- Menu actions (m:) ----
        if data == "m:optin":
            await _run_cmd(cmd_optin)
            return

        if data == "m:optout":
            await _run_cmd(cmd_optout)
            return

        if data == "m:bal":
            await _run_cmd(cmd_manh)
            return

        if data == "m:lbd":
            await _run_cmd(cmd_leaderboard, ["daily"])
            return

        if data == "m:lbw":
            await _run_cmd(cmd_leaderboard, ["weekly"])
            return

        # ---- Payments / Poll (p:) ----
        if data in ("p:inv:list",):
            await _run_cmd(cmd_invoices)
            return

        if data in ("p:inv:10", "p:buy10"):
            await _run_cmd(cmd_buy, ["10"])
            return

        if data in ("p:poll", "p:poll:confirm"):
            await _safe_send(context, chat_id, t(lang, "menu.hint"))
            return

        await _safe_send(context, chat_id, f"Unknown action: {data}")

    except Exception as e:
        _log(f"MENU callback error: {e!r}")
'''.strip("\n") + "\n\n"

def ensure_import_text(s: str) -> str:
    if "text(" not in s:
        return s
    if re.search(r"(?m)^\s*from\s+sqlalchemy\s+import\s+.*\btext\b", s):
        return s
    # insert after first from sqlalchemy import ... OR after last import
    m = re.search(r"(?m)^from\s+sqlalchemy\s+import\s+.+\n", s)
    if m:
        ins = m.end()
        return s[:ins] + "from sqlalchemy import text\n" + s[ins:]
    imp_end = 0
    for mm in re.finditer(r"(?m)^(from .+ import .+|import .+)\s*$", s):
        imp_end = mm.end()
    return s[:imp_end] + "\nfrom sqlalchemy import text\n" + s[imp_end:]

def replace_or_insert_block(s: str, name: str, new_block: str) -> str:
    pat = rf"(?s)^async def {re.escape(name)}\b.*?(?=^async def|^def|\Z)"
    m = re.search(pat, s, flags=re.M)
    if m:
        return s[:m.start()] + new_block + s[m.end():]
    # insert near other handlers: after cmd_help if exists, else near menu keyboard
    mh = re.search(r"(?s)^async def cmd_help\b.*?(?=^async def|^def|\Z)", s, flags=re.M)
    if mh:
        return s[:mh.end()] + "\n\n" + new_block + s[mh.end():]
    mk = re.search(r"(?s)^def _menu_keyboard\b.*?(?=^async def|^def|\Z)", s, flags=re.M)
    if mk:
        return s[:mk.end()] + "\n\n" + new_block + s[mk.end():]
    return new_block + s

def ensure_callback_handler_points_v2(s: str) -> str:
    # replace handler target if exists
    s = re.sub(
        r'CallbackQueryHandler\(\s*on_menu_callback(?:_v2)?\s*,\s*pattern\s*=\s*"\^\(m:\|p:\|d:\)"\s*\)',
        'CallbackQueryHandler(on_menu_callback_v2, pattern="^(m:|p:|d:)")',
        s
    )
    s = re.sub(
        r'CallbackQueryHandler\(\s*on_menu_callback(?:_v2)?\s*,\s*pattern\s*=\s*"\^\(m:\|p:\|d:\)"\s*\)',
        'CallbackQueryHandler(on_menu_callback_v2, pattern="^(m:|p:|d:)")',
        s
    )
    # if there is a CallbackQueryHandler line with pattern, normalize it
    s = re.sub(
        r'CallbackQueryHandler\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*pattern\s*=\s*"\^\(m:\|p:\|d:\)"\s*\)',
        'CallbackQueryHandler(on_menu_callback_v2, pattern="^(m:|p:|d:)")',
        s
    )
    # Also handle the common correct pattern already present but pointing wrong fn:
    s = re.sub(
        r'CallbackQueryHandler\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*pattern\s*=\s*"\^\(m:\|p:\|d:\)"\s*\)',
        'CallbackQueryHandler(on_menu_callback_v2, pattern="^(m:|p:|d:)")',
        s
    )
    s = re.sub(
        r'CallbackQueryHandler\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*pattern\s*=\s*"\^\(m:\|p:\|d:\)"\s*\)',
        'CallbackQueryHandler(on_menu_callback_v2, pattern="^(m:|p:|d:)")',
        s
    )
    # finally: if the exact desired line exists, do nothing.
    return s

def ensure_safe_send(s: str) -> str:
    if re.search(r"(?m)^async def _safe_send\b", s):
        # replace existing _safe_send block
        pat = r"(?s)^async def _safe_send\b.*?(?=^async def|^def|\Z)"
        return re.sub(pat, SAFE_SEND, s, flags=re.M)
    # insert after imports
    imp_end = 0
    for mm in re.finditer(r"(?m)^(from .+ import .+|import .+)\s*$", s):
        imp_end = mm.end()
    return s[:imp_end] + "\n\n" + SAFE_SEND + s[imp_end:]

for p in cands:
    s = p.read_text(encoding="utf-8", errors="replace").replace("\r\n","\n")

    s = ensure_import_text(s)
    s = ensure_safe_send(s)

    # Ensure callback v2 exists and mapped
    s = replace_or_insert_block(s, "on_menu_callback_v2", CALLBACK_V2)

    # Ensure handler line points to v2 (best-effort)
    # Replace any line that uses CallbackQueryHandler with our desired target+pattern
    s = re.sub(
        r'CallbackQueryHandler\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*pattern\s*=\s*"\^\(m:\|p:\|d:\)"\s*\)',
        'CallbackQueryHandler(on_menu_callback_v2, pattern="^(m:|p:|d:)")',
        s
    )
    s = re.sub(
        r'CallbackQueryHandler\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*pattern\s*=\s*"\^\(m:\|p:\|d:\)"\s*\)',
        'CallbackQueryHandler(on_menu_callback_v2, pattern="^(m:|p:|d:)")',
        s
    )
    s = re.sub(
        r'CallbackQueryHandler\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*pattern\s*=\s*"\^\(m:\|p:\|d:\)"\s*\)',
        'CallbackQueryHandler(on_menu_callback_v2, pattern="^(m:|p:|d:)")',
        s
    )
    # And also fix the exact common current form:
    s = re.sub(
        r'CallbackQueryHandler\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*pattern\s*=\s*"\^\(m:\|p:\|d:\)"\s*\)',
        'CallbackQueryHandler(on_menu_callback_v2, pattern="^(m:|p:|d:)")',
        s
    )
    s = re.sub(
        r'CallbackQueryHandler\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*pattern\s*=\s*"\^\(m:\|p:\|d:\)"\s*\)',
        'CallbackQueryHandler(on_menu_callback_v2, pattern="^(m:|p:|d:)")',
        s
    )

    # Normalize final newline (keep CRLF in working copy if you prefer; git will LF-normalize)
    p.write_text(s.replace("\n","\r\n"), encoding="utf-8")
    print("PATCHED:", p)
