from __future__ import annotations

import os
import time
from dataclasses import dataclass
from decimal import Decimal

import httpx


@dataclass
class PriceQuote:
    ton_ils: Decimal
    ts: float
    source: str


_CACHE: PriceQuote | None = None


def _provider() -> str:
    return (os.getenv("PRICE_FEED_PROVIDER") or "manual").strip().lower()


def _manual_ton_ils() -> Decimal:
    v = (os.getenv("TON_ILS_MANUAL") or "").strip()
    if not v:
        # safe default: force user to set it if provider=manual
        raise RuntimeError("TON_ILS_MANUAL missing (set PRICE_FEED_PROVIDER=manual and TON_ILS_MANUAL=...)")
    return Decimal(v)


def get_ton_ils_cached(ttl_sec: int = 120) -> PriceQuote:
    global _CACHE
    now = time.time()
    if _CACHE and (now - _CACHE.ts) < ttl_sec:
        return _CACHE

    prov = _provider()
    if prov == "manual":
        q = PriceQuote(ton_ils=_manual_ton_ils(), ts=now, source="manual")
        _CACHE = q
        return q

    # V1: example with CoinGecko. You may need an API key depending on plan.
    # If coingecko fails, raise (so invoices can't be created with stale price).
    if prov == "coingecko":
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": "the-open-network", "vs_currencies": "ils"}
        headers = {}
        key = (os.getenv("COINGECKO_API_KEY") or "").strip()
        if key:
            headers["x-cg-pro-api-key"] = key
        r = httpx.get(url, params=params, headers=headers, timeout=15.0)
        r.raise_for_status()
        js = r.json()
        ils = js.get("the-open-network", {}).get("ils")
        if ils is None:
            raise RuntimeError(f"bad coingecko response: {js!r}")
        q = PriceQuote(ton_ils=Decimal(str(ils)), ts=now, source="coingecko")
        _CACHE = q
        return q

    raise RuntimeError(f"Unsupported PRICE_FEED_PROVIDER={prov!r}")
