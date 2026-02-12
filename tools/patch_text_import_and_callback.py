import re
from pathlib import Path

p = Path(r"web_portal\app\tg_bot.py")
s = p.read_text(encoding="utf-8").replace("\r\n","\n")

# 1) Ensure sqlalchemy.text is imported if text( is used
if "text(" in s and not re.search(r"(?m)^\s*from\s+sqlalchemy\s+import\s+.*\btext\b", s):
    # Try to insert near other sqlalchemy imports; otherwise near top
    m = re.search(r"(?m)^(from sqlalchemy[^\n]*\n)+", s)
    if m:
        block = m.group(0)
        if "text" not in block:
            # append text to the first from sqlalchemy import ... line if exists
            lines = block.splitlines(True)
            done = False
            for i, line in enumerate(lines):
                mm = re.match(r"(?m)^(from\s+sqlalchemy\s+import\s+)(.+)$", line.strip())
                if line.strip().startswith("from sqlalchemy import "):
                    if "text" not in line:
                        line = line.rstrip("\n") + ", text\n"
                        lines[i] = line
                        done = True
                        break
            if not done:
                block = block + "from sqlalchemy import text\n"
                s = s[:m.start()] + block + s[m.end():]
            else:
                s = s[:m.start()] + "".join(lines) + s[m.end():]
    else:
        # insert after last import
        imp_end = 0
        for mm in re.finditer(r"(?m)^(from .+ import .+|import .+)\s*$", s):
            imp_end = mm.end()
        s = s[:imp_end] + "\nfrom sqlalchemy import text\n" + s[imp_end:]

# 2) Patch on_menu_callback_v2 to accept both d:* and m:* for db/alembic (small safe edit)
pat = r"(?s)^async def on_menu_callback_v2\b.*?(?=^async def|^def|\Z)"
m = re.search(pat, s, flags=re.M)
if not m:
    raise SystemExit("on_menu_callback_v2 not found (after restoring).")

block = m.group(0)

# Normalize the condition checks (only if they exist)
block = re.sub(r'if\s+data\s*==\s*"m:db"\s*:', 'if data in ("m:db","d:db"):', block)
block = re.sub(r'if\s+data\s*==\s*"m:alembic"\s*:', 'if data in ("m:alembic","d:alembic"):', block)

s2 = s[:m.start()] + block + s[m.end():]
p.write_text(s2.replace("\n","\r\n"), encoding="utf-8")
print("PATCHED:", p)