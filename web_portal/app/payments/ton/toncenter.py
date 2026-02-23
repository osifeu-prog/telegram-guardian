from __future__ import annotations

import os
from typing import Any, Optional

import httpx


def _ton_api_key() -> str:
    return (os.getenv("TON_API_KEY") or "").strip()


def _ton_base_url() -> str:
    # toncenter endpoints vary; keep configurable
    return (os.getenv("TONCENTER_BASE_URL") or "https://toncenter.com/api/v2").strip()


class TonCenter:
    def __init__(self) -> None:
        self.base = _ton_base_url()
        self.key = _ton_api_key()
        if not self.key:
            raise RuntimeError("TON_API_KEY missing")
        self.client = httpx.Client(timeout=15.0)

    def _params(self, extra: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        p = {"api_key": self.key}
        if extra:
            p.update(extra)
        return p

    def get_transactions(self, address: str, limit: int = 20) -> list[dict[str, Any]]:
        # Docs: getTransactions?address=...&limit=...
        url = f"{self.base}/getTransactions"
        r = self.client.get(url, params=self._params({"address": address, "limit": limit}))
        r.raise_for_status()
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError(f"toncenter not ok: {data!r}")
        return data.get("result") or []

# ---- compatibility export (bot/menu expects fetch_transactions) ----
def fetch_transactions(*args, **kwargs):
    """
    Compatibility wrapper.
    Expected to return list[dict] with at least:
    - 'to' (dest address)
    - 'comment' (payload/comment)
    - 'amount_ton' or 'amount' (numeric)
    - 'ts' (timestamp)
    """
    if "get_transactions" in globals():
        return get_transactions(*args, **kwargs)
    if "list_transactions" in globals():
        return list_transactions(*args, **kwargs)
    raise ImportError("fetch_transactions is not implemented (no underlying tx function found)")
