"""FRED API client for macro economic indicators."""

from __future__ import annotations

import logging
from typing import Any

import requests

from config.settings import FredConfig
from src.visualization.metrics_status import classify_metric_status

logger = logging.getLogger(__name__)


class FredClient:
    """Fetch latest observations from FRED API."""

    def __init__(self, config: FredConfig):
        self.config = config

    def get_latest_observation(self, series_id: str) -> dict[str, Any] | None:
        """Return the most recent non-missing observation for a series."""
        params = {
            "series_id": series_id,
            "api_key": self.config.api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 10,
        }
        resp = requests.get(self.config.base_url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        observations = data.get("observations", [])
        for obs in observations:
            value_str = obs.get("value", ".")
            if value_str != ".":
                try:
                    return {
                        "date": obs["date"],
                        "value": float(value_str),
                    }
                except ValueError:
                    continue
        return None

    def fetch_metrics(self, metrics_config: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Fetch all configured metrics with status classification."""
        results = []

        for cfg in metrics_config:
            if cfg.get("source") == "yfinance":
                results.append(self._fetch_yfinance_metric(cfg))
                continue

            series_id = cfg["series_id"]
            try:
                obs = self.get_latest_observation(series_id)
                if obs is None:
                    results.append(
                        {
                            **cfg,
                            "value": None,
                            "date": None,
                            "status": "unknown",
                            "status_label": "无数据",
                            "status_color": "#94a3b8",
                        }
                    )
                    continue

                value = obs["value"]
                status, label, color = classify_metric_status(value, cfg)

                results.append(
                    {
                        **cfg,
                        "value": value,
                        "date": obs["date"],
                        "status": status,
                        "status_label": label,
                        "status_color": color,
                    }
                )
            except Exception as e:
                logger.error("Failed to fetch FRED series %s: %s", series_id, e)
                results.append(
                    {
                        **cfg,
                        "value": None,
                        "date": None,
                        "status": "error",
                        "status_label": "获取失败",
                        "status_color": "#64748b",
                        "error": str(e),
                    }
                )

        return results

    @staticmethod
    def _fetch_yfinance_metric(cfg: dict[str, Any]) -> dict[str, Any]:
        """Fetch latest value via yfinance for TwelveData-style indicators."""
        import yfinance as yf

        symbol = cfg["series_id"]
        try:
            hist = yf.Ticker(symbol).history(period="5d")
            if hist.empty:
                raise ValueError(f"No data for {symbol}")
            value = float(hist.iloc[-1]["Close"])
            date = str(hist.index[-1].date())
            status, label, color = classify_metric_status(value, cfg)
            return {
                **cfg,
                "value": value,
                "date": date,
                "status": status,
                "status_label": label,
                "status_color": color,
            }
        except Exception as e:
            logger.error("Failed yfinance fetch for %s: %s", symbol, e)
            return {
                **cfg,
                "value": None,
                "date": None,
                "status": "error",
                "status_label": "获取失败",
                "status_color": "#64748b",
                "error": str(e),
            }
