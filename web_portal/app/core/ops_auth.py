from __future__ import annotations

import os
from fastapi import HTTPException, Query, status

from .security import constant_time_equals, looks_like_base64_token, token_fingerprint


def _want_ops_hash() -> str:
    # preferred: OPS_TOKEN_HASH, fallback: OPS_TOKEN (hashed)
    raw = (os.getenv("OPS_TOKEN_HASH") or "").strip()
    if raw:
        return raw
    legacy = (os.getenv("OPS_TOKEN") or "").strip()
    return token_fingerprint(legacy) if legacy else ""


def require_ops_token(token: str = Query(..., description="OPS token")) -> dict:
    want_hash = _want_ops_hash()
    if not want_hash:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ops_not_configured")

    if not looks_like_base64_token(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")

    got_hash = token_fingerprint(token)
    if not got_hash or not constant_time_equals(got_hash, want_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")

    return {"ok": True, "ops_hash_prefix": want_hash[:8]}