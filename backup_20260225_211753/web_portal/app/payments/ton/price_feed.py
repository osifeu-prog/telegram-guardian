from __future__ import annotations

import os
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

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
        # ברירת מחדל זמנית לפיתוח
        return Decimal("5.0")
    v = v.replace(",", ".")
    try:
        return Decimal(v)
    except InvalidOperation as e:
        raise RuntimeError(f"price_feed: bad decimal value={v!r}") from e


def get_ton_ils_cached(ttl_sec: int = 120) -> PriceQuote:
    print("DEBUG: get_ton_ils_cached called")
    print(f"DEBUG: provider from env: {_provider()}")
    global _CACHE
    now = time.time()
    if _CACHE and (now - _CACHE.ts) < ttl_sec:
        return _CACHE

    prov = _provider()
    print(f"DEBUG: resolved provider = {prov}")
    if prov == "manual":
        print("DEBUG: using manual provider")
        q = PriceQuote(ton_ils=_manual_ton_ils(), ts=now, source="manual")
        _CACHE = q
        return q

    if prov == "coingecko":
        print("DEBUG: using coingecko provider")
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

    print(f"DEBUG: unsupported provider {prov}")
    raise RuntimeError(f"Unsupported PRICE_FEED_PROVIDER={prov!r}")

def get_price_quote() -> PriceQuote:
    return get_ton_ils_cached(ttl_sec=120)
