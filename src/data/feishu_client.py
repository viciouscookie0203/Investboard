"""Feishu (Lark) Bitable API client for stock and metric configuration."""

from __future__ import annotations

import logging
from typing import Any

import requests

from config.settings import FeishuConfig
from src.data.ticker_utils import (
    normalize_stock_ticker,
    parse_fred_series,
    parse_threshold_json,
    parse_yfinance_fallback,
)

logger = logging.getLogger(__name__)


class FeishuClient:
    """Fetch records from Feishu Bitable tables."""

    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, config: FeishuConfig):
        self.config = config
        self._token: str | None = None

    def _get_tenant_access_token(self) -> str:
        if self._token:
            return self._token

        url = f"{self.BASE_URL}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.config.app_id,
            "app_secret": self.config.app_secret,
        }
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Feishu auth failed: {data.get('msg')}")

        self._token = data["tenant_access_token"]
        return self._token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._get_tenant_access_token()}"}

    def _list_all_records(self, table_id: str) -> list[dict[str, Any]]:
        """Paginate through all records in a Bitable table."""
        records: list[dict[str, Any]] = []
        page_token: str | None = None

        while True:
            url = (
                f"{self.BASE_URL}/bitable/v1/apps/{self.config.app_token}"
                f"/tables/{table_id}/records"
            )
            params: dict[str, str | int] = {"page_size": 500}
            if page_token:
                params["page_token"] = page_token

            resp = requests.get(url, headers=self._headers(), params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != 0:
                raise RuntimeError(f"Feishu bitable error: {data.get('msg')}")

            items = data.get("data", {}).get("items", [])
            records.extend(items)

            page_token = data.get("data", {}).get("page_token")
            if not page_token:
                break

        return records

    @staticmethod
    def _extract_field(fields: dict[str, Any], *candidates: str) -> str:
        """Extract text value from a Feishu field, trying multiple key names."""
        for key in candidates:
            if key in fields:
                val = fields[key]
                if isinstance(val, str):
                    return val.strip()
                if isinstance(val, (int, float)):
                    return str(val)
                if isinstance(val, list) and val:
                    first = val[0]
                    if isinstance(first, dict):
                        return first.get("text", str(first))
                    return str(first)
                if isinstance(val, dict):
                    return val.get("text", str(val))
        return ""

    @staticmethod
    def _extract_number(fields: dict[str, Any], *candidates: str) -> float | None:
        for key in candidates:
            if key in fields:
                val = fields[key]
                if isinstance(val, (int, float)):
                    return float(val)
                if isinstance(val, str):
                    try:
                        return float(val)
                    except ValueError:
                        continue
        return None

    def get_stocks(self) -> list[dict[str, Any]]:
        """Return stock watchlist from Feishu table."""
        records = self._list_all_records(self.config.stock_table_id)
        stocks = []

        for rec in records:
            fields = rec.get("fields", {})
            if fields.get("enabled") is False:
                continue

            ticker = self._extract_field(
                fields, "ticker", "Ticker", "代码", "股票代码", "Symbol", "symbol"
            )
            name = self._extract_field(
                fields, "Name", "name", "名称", "股票名称", "Company"
            )
            market = self._extract_field(
                fields, "market", "Market", "市场", "Exchange"
            )
            asset_type = self._extract_field(
                fields, "asset_type", "Asset Type", "资产类型"
            )

            if ticker:
                yf_ticker = normalize_stock_ticker(ticker, market, asset_type)
                stocks.append(
                    {
                        "record_id": rec.get("record_id"),
                        "ticker": ticker.upper(),
                        "yf_ticker": yf_ticker,
                        "name": name or ticker,
                        "market": market,
                        "asset_type": asset_type,
                    }
                )

        logger.info("Loaded %d stocks from Feishu", len(stocks))
        return stocks

    def get_metrics_config(self) -> list[dict[str, Any]]:
        """Return metric configuration with thresholds from Feishu table."""
        records = self._list_all_records(self.config.metric_table_id)
        metrics = []

        for rec in records:
            fields = rec.get("fields", {})
            if fields.get("enabled") is False:
                continue

            calc_expression = self._extract_field(
                fields, "calc_expression", "Calc Expression", "计算表达式"
            )
            data_source = self._extract_field(
                fields, "data_source", "Data Source", "数据源"
            )
            name = self._extract_field(
                fields, "name", "Name", "名称", "指标名称", "Metric"
            )
            indicator_id = self._extract_field(
                fields, "indicator_id", "Indicator ID", "指标ID"
            )
            category = self._extract_field(fields, "category", "Category", "分类")
            threshold_raw = fields.get("threshold_json") or fields.get("Threshold JSON")

            series_id = parse_fred_series(calc_expression)
            yf_symbol = parse_yfinance_fallback(calc_expression) if not series_id else None
            source = "fred" if series_id else ("yfinance" if yf_symbol else None)

            if not source:
                logger.debug("Skipping unsupported metric: %s (%s)", name, calc_expression)
                continue

            thresholds = parse_threshold_json(threshold_raw)
            # Legacy column overrides
            for key, candidates in [
                ("warn_low", ("Warn Low", "warn_low", "预警下限", "下限")),
                ("warn_high", ("Warn High", "warn_high", "预警上限", "上限")),
                ("danger_low", ("Danger Low", "danger_low", "危险下限")),
                ("danger_high", ("Danger High", "danger_high", "危险上限")),
                ("min_val", ("Min", "min", "最小值", "Gauge Min")),
                ("max_val", ("Max", "max", "最大值", "Gauge Max")),
            ]:
                val = self._extract_number(fields, *candidates)
                if val is not None:
                    thresholds[key] = val

            metrics.append(
                {
                    "record_id": rec.get("record_id"),
                    "indicator_id": indicator_id,
                    "series_id": series_id or yf_symbol,
                    "calc_expression": calc_expression,
                    "data_source": data_source,
                    "source": source,
                    "name": name or indicator_id or calc_expression,
                    "category": category,
                    "unit": self._extract_field(fields, "unit", "Unit", "单位"),
                    "direction": self._extract_field(fields, "direction", "Direction") or "neutral",
                    **thresholds,
                }
            )

        logger.info("Loaded %d metrics config from Feishu", len(metrics))
        return metrics
