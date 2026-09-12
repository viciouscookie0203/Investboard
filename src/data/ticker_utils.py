"""Ticker normalization for yfinance and other data sources."""

from __future__ import annotations

import re
from typing import Any

# Common index aliases → yfinance symbols
INDEX_MAP = {
    "SPX500": "^GSPC",
    "SPX": "^GSPC",
    "GSPC": "^GSPC",
    "DJI": "^DJI",
    "NDX": "^NDX",
    "IXIC": "^IXIC",
    "HSI": "^HSI",
    "VIX": "^VIX",
}

# TwelveData-style expressions → yfinance fallback
YFINANCE_FALLBACK = {
    "DXY": "DX-Y.NYB",
    "VIX": "^VIX",
    "MOVE": "^MOVE",  # may not always resolve
}


def normalize_stock_ticker(ticker: str, market: str = "", asset_type: str = "") -> str:
    """Convert Feishu ticker to yfinance-compatible symbol."""
    ticker = ticker.strip().upper()
    market = (market or "").upper()
    asset_type = (asset_type or "").lower()

    if ticker in INDEX_MAP or asset_type == "index":
        return INDEX_MAP.get(ticker, f"^{ticker}")

    # Hong Kong: 00005 → 0005.HK or 00005.HK
    if market == "HK" or re.match(r"^\d{4,5}$", ticker):
        code = ticker.lstrip("0") or "0"
        code = code.zfill(4)
        return f"{code}.HK"

    return ticker


def parse_fred_series(calc_expression: str) -> str | None:
    """Extract FRED series ID from calc_expression like 'FRED:DGS10'."""
    if not calc_expression:
        return None
    match = re.match(r"^FRED:([A-Z0-9_]+)$", calc_expression.strip(), re.I)
    return match.group(1).upper() if match else None


def parse_yfinance_fallback(calc_expression: str) -> str | None:
    """Extract yfinance symbol from TwelveData expression like 'TwelveData:DXY'."""
    if not calc_expression:
        return None
    match = re.match(r"^TwelveData:([A-Z0-9^!/.\-]+)$", calc_expression.strip(), re.I)
    if not match:
        return None
    symbol = match.group(1).upper()
    # Strip futures suffixes we can't resolve on yfinance
    if "!" in symbol or "/" in symbol:
        return None
    return YFINANCE_FALLBACK.get(symbol, symbol)


def parse_threshold_json(threshold_json: str | dict | None) -> dict[str, float | None]:
    """
    Normalize heterogeneous threshold JSON from Feishu into standard keys.
    Returns warn_low, warn_high, danger_low, danger_high where possible.
    """
    import json

    if threshold_json is None:
        return {}
    if isinstance(threshold_json, str):
        try:
            data = json.loads(threshold_json)
        except json.JSONDecodeError:
            return {}
    else:
        data = threshold_json

    result: dict[str, float | None] = {
        "warn_low": None,
        "warn_high": None,
        "danger_low": None,
        "danger_high": None,
    }

    mapping = {
        "low_alert": "warn_low",
        "support": "warn_low",
        "calm_level": "warn_low",
        "risk_on": "warn_low",
        "gold_bullish": "warn_low",
        "value_zone": "warn_low",
        "low_defensive": "warn_low",
        "high_alert": "warn_high",
        "resistance": "warn_high",
        "stress_level": "warn_high",
        "panic_level": "warn_high",
        "risk_off": "warn_high",
        "concentration_alert": "warn_high",
        "bubble_zone": "danger_high",
        "extreme_panic": "danger_high",
        "gold_bearish": "danger_high",
        "high_economic_growth": "warn_high",
        "reversion_trigger": "warn_low",
    }

    for src_key, dst_key in mapping.items():
        if src_key in data and isinstance(data[src_key], (int, float)):
            result[dst_key] = float(data[src_key])

    return result
