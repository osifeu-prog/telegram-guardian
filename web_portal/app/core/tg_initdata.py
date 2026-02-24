from __future__ import annotations

import hashlib
import hmac
import os
import time
from urllib.parse import parse_qsl
from typing import Any


def _parse_init_data(init_data: str) -> dict[str, str]:
    # init_data is querystring: a=1&b=2...
    return dict(parse_qsl(init_data, keep_blank_values=True))


def _build_data_check_string(d: dict[str, str]) -> str:
    # Exclude 'hash', sort by key, join as "k=v\n"
    items = [(k, v) for k, v in d.items() if k != "hash"]
    items.sort(key=lambda x: x[0])
    return "\n".join([f"{k}={v}" for k, v in items])


def verify_telegram_init_data(init_data: str, bot_token: str, max_age_sec: int = 300) -> dict[str, Any]:
    """
    Verifies Telegram WebApp initData (HMAC-SHA256).
    Returns parsed payload if valid; raises ValueError otherwise.
    """
    if not init_data or not bot_token:
        raise ValueError("missing init_data or bot_token")

    d = _parse_init_data(init_data)
    their_hash = d.get("hash", "")
    if not their_hash:
        raise ValueError("missing hash")

    # optional freshness check (auth_date)
    auth_date = int(d.get("auth_date", "0") or "0")
    now = int(time.time())
    if auth_date and (now - auth_date) > max_age_sec:
        raise ValueError("init_data too old")

    data_check_string = _build_data_check_string(d)

    # secret_key = HMAC_SHA256(key="WebAppData", message=bot_token)
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calc_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calc_hash, their_hash):
        raise ValueError("bad hash")

    return d


def _parse_tg_user(data: dict) -> dict:
    \"\"\"
    Extract user data from the verified init data.
    The 'user' field is a JSON string inside the data.
    \"\"\"
    user_json = data.get('user', '{}')
    try:
        return json.loads(user_json)
    except Exception:
        return {}
