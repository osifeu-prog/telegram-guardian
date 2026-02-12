import re
from pathlib import Path

p = Path(r"web_portal\app\tg_bot.py")
s = p.read_text(encoding="utf-8").replace("\r\n","\n")

# A) ensure SQLAlchemy text import exists
if not re.search(r"(?m)^\s*from\s+sqlalchemy\s+import\s+text\s*$", s):
    # insert after first 'from sqlalchemy' or near imports
    m = re.search(r"(?m)^(from\s+sqlalchemy[^\n]*\n)", s)
    if m:
        ins = m.end()
        s = s[:ins] + "from sqlalchemy import text\n" + s[ins:]
    else:
        # fallback: after last import line
        imp_end = 0
        for mm in re.finditer(r"(?m)^(from .+ import .+|import .+)\s*$", s):
            imp_end = mm.end()
        s = s[:imp_end] + "\nfrom sqlalchemy import text\n" + s[imp_end:]

# B) replace/ensure _safe_send with UTF-16 safe chunking
safe_impl = r'''
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
        # number of UTF-16 code units (Telegram counts roughly like this)
        return len(x.encode("utf-16-le")) // 2

    # Keep a conservative ceiling (Telegram hard is 4096 UTF-16 units)
    MAX_U16 = 1500

    s = str(text)
    chunks = []
    while u16_len(s) > MAX_U16:
        # try split at newline within budget
        lo, hi = 0, len(s)
        # binary search cut by UTF-16 size
        l, r = 1, len(s)
        best = 1
        while l <= r:
            mid = (l + r) // 2
            if u16_len(s[:mid]) <= MAX_U16:
                best = mid
                l = mid + 1
            else:
                r = mid - 1

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

m = re.search(r"(?s)^async def _safe_send\([^\)]*\):.*?(?=^async def|^def|\Z)", s, flags=re.M)
if m:
    s = s[:m.start()] + safe_impl + s[m.end():]
else:
    # inject after imports
    imp_end = 0
    for mm in re.finditer(r"(?m)^(from .+ import .+|import .+)\s*$", s):
        imp_end = mm.end()
    s = s[:imp_end] + "\n\n" + safe_impl + s[imp_end:]

p.write_text(s.replace("\n","\r\n"), encoding="utf-8")
print("PATCHED:", p)