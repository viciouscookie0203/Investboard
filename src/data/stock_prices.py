"""Stock price fetcher using yfinance."""

from __future__ import annotations

import logging
from typing import Any

import yfinance as yf

logger = logging.getLogger(__name__)


class StockPriceFetcher:
    """Fetch latest prices for watchlist tickers."""

    def fetch_prices(self, stocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results = []

        for stock in stocks:
            ticker = stock["ticker"]
            yf_ticker = stock.get("yf_ticker", ticker)
            try:
                info = self._get_price_info(yf_ticker)
                results.append({**stock, **info})
            except Exception as e:
                logger.error("Failed to fetch price for %s (%s): %s", ticker, yf_ticker, e)
                results.append(
                    {
                        **stock,
                        "price": None,
                        "change": None,
                        "change_pct": None,
                        "currency": None,
                        "last_updated": None,
                        "error": str(e),
                    }
                )

        return results

    @staticmethod
    def _get_price_info(ticker: str) -> dict[str, Any]:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")

        if hist.empty:
            raise ValueError(f"No price data for {ticker}")

        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else latest

        price = float(latest["Close"])
        prev_close = float(prev["Close"])
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0.0

        fast_info = {}
        try:
            fast_info = t.fast_info
        except Exception:
            pass

        currency = getattr(fast_info, "currency", None) or getattr(
            fast_info, "last_currency", "USD"
        )
        if isinstance(fast_info, dict):
            currency = fast_info.get("currency", "USD")

        return {
            "price": round(price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "currency": currency if isinstance(currency, str) else "USD",
            "last_updated": str(hist.index[-1].date()),
            "volume": int(latest.get("Volume", 0)),
        }
