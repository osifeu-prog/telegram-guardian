from __future__ import annotations
from typing import Any, Dict

# Unicode-escape only (ASCII source) => prevents encoding/mojibake forever.

LANG_DEFAULT = "en"

T: Dict[str, Dict[str, str]] = {
  "en": {
    "menu.title": "\U0001F9EA Diagnostics Menu (telegram-guardian)\nChoose an action:",
    "menu.hint": "Tip: You can also type commands.",
    "btn.optin": "\u2705 Opt-in",
    "btn.optout": "\u274C Opt-out",
    "btn.balance": "\U0001F4B0 MANH Balance",
    "btn.lb_daily": "\U0001F3C6 LB Daily",
    "btn.lb_weekly": "\U0001F3C6 LB Weekly",
    "btn.buy10": "\U0001F6D2 Buy MANH (10)",
    "btn.invoices": "\U0001F9FE My Invoices",
    "btn.poll": "\U0001F50E Poll Confirm",
    "btn.db": "\U0001FA7A DB Ping",
    "btn.alembic": "\U0001F4CC Alembic",
    "ok.optin": "\u2705 Opt-in enabled. You are now on the MANH leaderboard.",
    "ok.optout": "\u2705 Opt-out enabled. You are no longer on the MANH leaderboard.",
    "manh.balance": "MANH={manh} | XP={xp}",
    "lb.empty": "\U0001F3C6 Leaderboard ({scope}) is empty right now.",
    "db.ok": "\U0001FA7A DB Ping: OK",
    "alembic.ver": "\U0001F4CC Alembic: {ver}",
    "err.price": "\u26A0 Price feed failed: {err}",
    "err.ton": "\u26A0 Fetch TON tx failed: {err}",
    "lang.set": "\U0001F310 Language set to: {lang}",
  },
  "he": {
    "menu.title": "\U0001F9EA \u05EA\u05E4\u05E8\u05D9\u05D8 \u05D1\u05D3\u05D9\u05E7\u05D5\u05EA (telegram-guardian)\n\u05D1\u05D7\u05E8 \u05E4\u05E2\u05D5\u05DC\u05D4:",
    "menu.hint": "\u05D8\u05D9\u05E4: \u05D0\u05E4\u05E9\u05E8 \u05D2\u05DD \u05DC\u05D4\u05E7\u05DC\u05D9\u05D3 \u05E4\u05E7\u05D5\u05D3\u05D5\u05EA.",
    "btn.optin": "\u2705 \u05D4\u05E6\u05D8\u05E8\u05E4\u05D5\u05EA",
    "btn.optout": "\u274C \u05D4\u05E1\u05E8\u05D4",
    "btn.balance": "\U0001F4B0 \u05D9\u05EA\u05E8\u05EA MANH",
    "btn.lb_daily": "\U0001F3C6 \u05DC\u05D5\u05D7 \u05D9\u05D5\u05DE\u05D9",
    "btn.lb_weekly": "\U0001F3C6 \u05DC\u05D5\u05D7 \u05E9\u05D1\u05D5\u05E2\u05D9",
    "btn.buy10": "\U0001F6D2 \u05E8\u05DB\u05D9\u05E9\u05EA MANH (10)",
    "btn.invoices": "\U0001F9FE \u05D4\u05D7\u05E9\u05D1\u05D5\u05E0\u05D9\u05D5\u05EA \u05E9\u05DC\u05D9",
    "btn.poll": "\U0001F50E \u05D1\u05D3\u05D9\u05E7\u05EA \u05D0\u05D9\u05E9\u05D5\u05E8",
    "btn.db": "\U0001FA7A \u05D1\u05D3\u05D9\u05E7\u05EA DB",
    "btn.alembic": "\U0001F4CC Alembic",
    "ok.optin": "\u2705 \u05D4\u05E6\u05D8\u05E8\u05E4\u05EA \u05D4\u05D5\u05E4\u05E2\u05DC\u05D4. \u05D0\u05EA\u05D4 \u05D1\u05DC\u05D5\u05D7 \u05D4\u05D3\u05E8\u05D2\u05D5\u05EA MANH.",
    "ok.optout": "\u2705 \u05D4\u05E1\u05E8\u05EA \u05D4\u05D5\u05E4\u05E2\u05DC\u05D4. \u05D0\u05EA\u05D4 \u05DC\u05D0 \u05D1\u05DC\u05D5\u05D7 \u05D4\u05D3\u05E8\u05D2\u05D5\u05EA MANH.",
    "manh.balance": "MANH={manh} | XP={xp}",
    "lb.empty": "\U0001F3C6 \u05DC\u05D5\u05D7 \u05D4\u05D3\u05E8\u05D2\u05D5\u05EA ({scope}) \u05E8\u05D9\u05E7 \u05DB\u05E8\u05D2\u05E2.",
    "db.ok": "\U0001FA7A \u05D1\u05D3\u05D9\u05E7\u05EA DB: OK",
    "alembic.ver": "\U0001F4CC Alembic: {ver}",
    "err.price": "\u26A0 \u05E9\u05D2\u05D9\u05D0\u05D4 \u05D1\u05DE\u05D7\u05D9\u05E8: {err}",
    "err.ton": "\u26A0 \u05E9\u05D2\u05D9\u05D0\u05D4 \u05D1\u05E9\u05DC\u05D9\u05E4\u05EA \u05D8\u05E8\u05E0\u05D6\u05E7\u05E6\u05D9\u05D5\u05EA TON: {err}",
    "lang.set": "\U0001F310 \u05E9\u05E4\u05D4 \u05E0\u05E7\u05D1\u05E2\u05D4: {lang}",
  },
  "ru": {
    "menu.title": "\U0001F9EA \u041C\u0435\u043D\u044E \u0434\u0438\u0430\u0433\u043D\u043E\u0441\u0442\u0438\u043A\u0438 (telegram-guardian)\n\u0412\u044B\u0431\u0435\u0440\u0438\u0442\u0435 \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0435:",
    "menu.hint": "\u0421\u043E\u0432\u0435\u0442: \u043C\u043E\u0436\u043D\u043E \u0442\u0430\u043A\u0436\u0435 \u0432\u0432\u043E\u0434\u0438\u0442\u044C \u043A\u043E\u043C\u0430\u043D\u0434\u044B.",
    "btn.optin": "\u2705 Opt-in",
    "btn.optout": "\u274C Opt-out",
    "btn.balance": "\U0001F4B0 \u0411\u0430\u043B\u0430\u043D\u0441 MANH",
    "btn.lb_daily": "\U0001F3C6 \u041B\u0438\u0434\u0435\u0440\u044B (\u0434\u0435\u043D\u044C)",
    "btn.lb_weekly": "\U0001F3C6 \u041B\u0438\u0434\u0435\u0440\u044B (\u043D\u0435\u0434\u0435\u043B\u044F)",
    "btn.buy10": "\U0001F6D2 \u041A\u0443\u043F\u0438\u0442\u044C MANH (10)",
    "btn.invoices": "\U0001F9FE \u041C\u043E\u0438 \u0441\u0447\u0435\u0442\u0430",
    "btn.poll": "\U0001F50E \u041F\u0440\u043E\u0432\u0435\u0440\u043A\u0430",
    "btn.db": "\U0001FA7A DB",
    "btn.alembic": "\U0001F4CC Alembic",
    "ok.optin": "\u2705 Opt-in \u0432\u043A\u043B\u044E\u0447\u0435\u043D. \u0412\u044B \u0442\u0435\u043F\u0435\u0440\u044C \u0432 \u0442\u0430\u0431\u043B\u0438\u0446\u0435 \u043B\u0438\u0434\u0435\u0440\u043E\u0432 MANH.",
    "ok.optout": "\u2705 Opt-out \u0432\u043A\u043B\u044E\u0447\u0435\u043D. \u0412\u044B \u0431\u043E\u043B\u044C\u0448\u0435 \u043D\u0435 \u0432 \u0442\u0430\u0431\u043B\u0438\u0446\u0435 \u043B\u0438\u0434\u0435\u0440\u043E\u0432 MANH.",
    "manh.balance": "MANH={manh} | XP={xp}",
    "lb.empty": "\U0001F3C6 \u0422\u0430\u0431\u043B\u0438\u0446\u0430 \u043B\u0438\u0434\u0435\u0440\u043E\u0432 ({scope}) \u043F\u0443\u0441\u0442\u0430.",
    "db.ok": "\U0001FA7A DB: OK",
    "alembic.ver": "\U0001F4CC Alembic: {ver}",
    "err.price": "\u26A0 \u041E\u0448\u0438\u0431\u043A\u0430 \u0446\u0435\u043D\u044B: {err}",
    "err.ton": "\u26A0 \u041E\u0448\u0438\u0431\u043A\u0430 TON tx: {err}",
    "lang.set": "\U0001F310 \u042F\u0437\u044B\u043A: {lang}",
  },
  "ar": {
    "menu.title": "\U0001F9EA \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u062A\u0634\u062E\u064A\u0635 (telegram-guardian)\n\u0627\u062E\u062A\u0631 \u0625\u062C\u0631\u0627\u0621:",
    "menu.hint": "\u0646\u0635\u064A\u062D\u0629: \u064A\u0645\u0643\u0646\u0643 \u0623\u064A\u0636\u0627\u064B \u0643\u062A\u0627\u0628\u0629 \u0623\u0648\u0627\u0645\u0631.",
    "btn.optin": "\u2705 Opt-in",
    "btn.optout": "\u274C Opt-out",
    "btn.balance": "\U0001F4B0 \u0631\u0635\u064A\u062F MANH",
    "btn.lb_daily": "\U0001F3C6 \u0627\u0644\u0635\u062F\u0627\u0631\u0629 (\u064A\u0648\u0645\u064A)",
    "btn.lb_weekly": "\U0001F3C6 \u0627\u0644\u0635\u062F\u0627\u0631\u0629 (\u0623\u0633\u0628\u0648\u0639\u064A)",
    "btn.buy10": "\U0001F6D2 \u0634\u0631\u0627\u0621 MANH (10)",
    "btn.invoices": "\U0001F9FE \u0641\u0648\u0627\u062A\u064A\u0631\u064A",
    "btn.poll": "\U0001F50E \u062A\u062D\u0642\u0642",
    "btn.db": "\U0001FA7A DB",
    "btn.alembic": "\U0001F4CC Alembic",
    "ok.optin": "\u2705 \u062A\u0645 \u062A\u0641\u0639\u064A\u0644 Opt-in. \u0623\u0646\u062A \u0627\u0644\u0622\u0646 \u0641\u064A \u0644\u0648\u062D\u0629 MANH.",
    "ok.optout": "\u2705 \u062A\u0645 \u062A\u0641\u0639\u064A\u0644 Opt-out. \u0644\u0633\u062A \u0645\u0648\u062C\u0648\u062F\u064B\u0627 \u0641\u064A \u0644\u0648\u062D\u0629 MANH.",
    "manh.balance": "MANH={manh} | XP={xp}",
    "lb.empty": "\U0001F3C6 \u0644\u0648\u062D\u0629 \u0627\u0644\u0635\u062F\u0627\u0631\u0629 ({scope}) \u0641\u0627\u0631\u063A\u0629 \u0627\u0644\u0622\u0646.",
    "db.ok": "\U0001FA7A DB: OK",
    "alembic.ver": "\U0001F4CC Alembic: {ver}",
    "err.price": "\u26A0 \u062E\u0637\u0623 \u0641\u064A \u0627\u0644\u0633\u0639\u0631: {err}",
    "err.ton": "\u26A0 \u062E\u0637\u0623 \u0641\u064A TON tx: {err}",
    "lang.set": "\U0001F310 \u062A\u0645 \u062A\u062D\u062F\u064A\u062F \u0627\u0644\u0644\u063A\u0629: {lang}",
  },
}

def t(lang: str, key: str, **kw: Any) -> str:
  lang = (lang or LANG_DEFAULT).lower()
  table = T.get(lang) or T[LANG_DEFAULT]
  s = table.get(key) or T["en"].get(key) or key
  return s.format(**kw)




