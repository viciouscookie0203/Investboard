"""JSON file cache for daily dashboard data."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytz


class DataCache:
    """Read/write cached dashboard payloads to disk."""

    CACHE_FILES = {
        "metrics": "metrics.json",
        "metrics_config": "metrics_config.json",
        "stocks": "stocks.json",
        "stocks_config": "stocks_config.json",
        "macro_news": "macro_news.json",
        "stock_news": "stock_news.json",
        "news_summary": "news_summary.json",
        "metadata": "metadata.json",
    }

    def __init__(self, cache_dir: Path, timezone: str = "Asia/Shanghai"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.tz = pytz.timezone(timezone)

    def _path(self, key: str) -> Path:
        if key not in self.CACHE_FILES:
            raise KeyError(f"Unknown cache key: {key}")
        return self.cache_dir / self.CACHE_FILES[key]

    def save(self, key: str, data: Any) -> None:
        path = self._path(key)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    def load(self, key: str, default: Any = None) -> Any:
        path = self._path(key)
        if not path.exists():
            return default
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def update_metadata(self, status: str = "success", errors: list[str] | None = None) -> None:
        meta = {
            "last_updated": datetime.now(self.tz).isoformat(),
            "status": status,
            "errors": errors or [],
        }
        self.save("metadata", meta)

    def get_last_updated(self) -> str | None:
        meta = self.load("metadata")
        if meta:
            return meta.get("last_updated")
        return None

    def exists(self, key: str) -> bool:
        return self._path(key).exists()
