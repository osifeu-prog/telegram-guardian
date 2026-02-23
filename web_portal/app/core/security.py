from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Optional


def normalize_token(token: Optional[str]) -> str:
    if not token:
        return ""
    return token.strip()


def token_fingerprint(token: str) -> str:
    token = normalize_token(token)
    if not token:
        return ""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def looks_like_base64_token(token: str) -> bool:
    token = normalize_token(token)
    if not token:
        return False
    try:
        raw = base64.b64decode(token, validate=True)
        return len(raw) >= 16
    except Exception:
        return False
