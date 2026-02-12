import re
from pathlib import Path

p = Path(r"web_portal\app\tg_bot.py")
s = p.read_text(encoding="utf-8").replace("\r\n","\n")

# -------------------------
# A) Ensure a robust safe sender exists (split long messages)
# We'll replace an existing async def _safe_send(...) if present;
# otherwise, we inject it near top (after imports).
# -------------------------
safe_impl = '''
async def _safe_send(context, chat_id: int, text: str, reply_markup=None) -> None:
    """
    Safe sender:
    - retries
    - splits long texts to avoid Telegram 'Message is too long'
    - keeps reply_markup only on first chunk
    """
    if text is None:
        return

    MAX_CHUNK = 3500  # keep margin under 4096
    s = str(text)

    chunks = []
    while len(s) > MAX_CHUNK:
        cut = s.rfind("\\n", 0, MAX_CHUNK)
        if cut < 0:
            cut = MAX_CHUNK
        chunks.append(s[:cut])
        s = s[cut:].lstrip("\\n")
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

m = re.search(r"(?s)^async def _safe_send\([^\)]*\):.*?(?=^\w|^async def|^def|\Z)", s, flags=re.M)
if m:
    s = s[:m.start()] + safe_impl + s[m.end():]
else:
    # inject after last import/from block
    imp_end = 0
    for mm in re.finditer(r"(?m)^(from .+ import .+|import .+)\s*$", s):
        imp_end = mm.end()
    s = s[:imp_end] + "\n\n" + safe_impl + s[imp_end:]

# -------------------------
# B) Remove mojibake huge literal _safe_send in cmd_menu (if any)
# remove any line: await _safe_send(..., "VERY LONG ...",)
# -------------------------
def strip_mojibake_in_cmd_menu(text: str) -> str:
    # isolate cmd_menu block
    m = re.search(r"(?s)async def cmd_menu\b.*?(?=^async def|^def|\Z)", text, flags=re.M)
    if not m:
        return text
    block = text[m.start():m.end()]
    # drop any await _safe_send with a quoted literal longer than 200 chars
    block2 = re.sub(r'(?m)^\s*await\s+_safe_send\([^,]+,\s*chat\.id\s*,\s*"(?:[^"\\]|\\.){200,}"\s*,?\s*\)\s*$\n?', "", block)
    # also drop any weird "Diagnostics Menu" literal if present
    block2 = re.sub(r'(?m)^\s*await\s+_safe_send\([^,]+,\s*chat\.id\s*,\s*".*Diagnostics Menu.*"\s*,?\s*\)\s*$\n?', "", block2)
    return text[:m.start()] + block2 + text[m.end():]

s = strip_mojibake_in_cmd_menu(s)

# -------------------------
# C) Add cmd_chatid + cmd_all (if missing)
# We'll inject after cmd_help block if exists, otherwise near other cmd_*.
# -------------------------
cmds = '''
async def cmd_chatid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = getattr(update, "effective_chat", None)
    if not chat:
        return
    user = getattr(update, "effective_user", None)
    uid = getattr(user, "id", None)
    lang = _get_lang(int(uid)) if uid is not None else "he"
    await _safe_send(context, chat.id, f"chat_id={chat.id}\\nuser_id={uid}\\nlang={lang}")

async def cmd_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = getattr(update, "effective_chat", None)
    if not chat:
        return
    lines = [
        "/start",
        "/menu",
        "/help",
        "/whoami",
        "/chatid",
        "/all",
        "/optin",
        "/optout",
        "/manh",
        "/leaderboard daily",
        "/leaderboard weekly",
        "/buy",
        "/invoices",
        "/withdraw",
        "/withdrawals",
    ]
    await _safe_send(context, chat.id, "Commands:\\n" + "\\n".join(lines))
'''.strip("\n") + "\n\n"

if not re.search(r"(?m)^async def cmd_chatid\b", s):
    mh = re.search(r"(?s)async def cmd_help\b.*?(?=^async def|^def|\Z)", s, flags=re.M)
    if mh:
        s = s[:mh.end()] + "\n\n" + cmds + s[mh.end():]
    else:
        # put near other commands (after first cmd_*)
        mcmd = re.search(r"(?s)(async def cmd_\w+\b.*?\n)", s)
        if mcmd:
            s = s[:mcmd.end()] + "\n\n" + cmds + s[mcmd.end():]
        else:
            s = cmds + s

# -------------------------
# D) Add stable on_menu_callback_v2 + handler registration
# We'll not depend on existing on_menu_callback signature.
# We'll add a new function and then ensure CallbackQueryHandler points to it.
# -------------------------
callback_v2 = '''
async def on_menu_callback_v2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = getattr(update, "callback_query", None)
    if not q:
        return

    data = getattr(q, "data", "") or ""
    msg = getattr(q, "message", None)
    chat = getattr(msg, "chat", None) if msg is not None else None
    chat_id = getattr(chat, "id", None)

    user = getattr(update, "effective_user", None)
    uid = getattr(user, "id", None)
    lang = _get_lang(int(uid)) if uid is not None else "he"

    try:
        await q.answer()
        if chat_id is None:
            _log(f"MENU callback no chat_id; data={data!r}")
            return

        if data == "m:db":
            try:
                await _with_db(lambda db: db.execute(text("SELECT 1")).fetchone())
                await _safe_send(context, chat_id, t(lang, "db.ok"))
            except Exception as e:
                await _safe_send(context, chat_id, f"DB Ping failed: {e!r}")
            return

        if data == "m:alembic":
            try:
                ver = await _with_db(lambda db: db.execute(text("SELECT version_num FROM alembic_version")).fetchone())
                v = ver[0] if ver else "unknown"
                await _safe_send(context, chat_id, t(lang, "alembic.ver", ver=v))
            except Exception as e:
                await _safe_send(context, chat_id, f"Alembic failed: {e!r}")
            return

        await _safe_send(context, chat_id, f"Unknown action: {data}")

    except Exception as e:
        _log(f"MENU callback error: {e!r}")
'''.strip("\n") + "\n\n"

if "async def on_menu_callback_v2" not in s:
    # inject near existing callback handler or near menu defs
    mcb = re.search(r"(?s)async def on_menu_callback\b.*?(?=^async def|^def|\Z)", s, flags=re.M)
    if mcb:
        s = s[:mcb.end()] + "\n\n" + callback_v2 + s[mcb.end():]
    else:
        s = s + "\n\n" + callback_v2

# Ensure CallbackQueryHandler uses on_menu_callback_v2
s = re.sub(
    r'CallbackQueryHandler\(\s*on_menu_callback\s*,\s*pattern="?\^\(m:\|p:\|d:\)"?\s*\)',
    'CallbackQueryHandler(on_menu_callback_v2, pattern="^(m:|p:|d:)")',
    s
)

# Add CommandHandler for /chatid and /all (next to existing help handler)
if 'CommandHandler("chatid"' not in s:
    s = re.sub(
        r'(?m)^(?P<indent>\s*)app\.add_handler\(CommandHandler\("help",\s*cmd_help\)\)\s*$',
        r'\g<indent>app.add_handler(CommandHandler("help", cmd_help))\n\g<indent>app.add_handler(CommandHandler("chatid", cmd_chatid))\n\g<indent>app.add_handler(CommandHandler("all", cmd_all))',
        s
    )

# normalize final newline + ensure LF only
s = s.replace("\r\n","\n").rstrip("\n") + "\n"
p.write_text(s, encoding="utf-8")
print("PATCHED:", p)