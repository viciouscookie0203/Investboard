"""Tests for data cache."""

import json
from pathlib import Path

from src.data.cache import DataCache


def test_save_and_load(tmp_path: Path):
    cache = DataCache(tmp_path)
    cache.save("metrics", [{"name": "CPI", "value": 3.2}])
    data = cache.load("metrics")
    assert len(data) == 1
    assert data[0]["name"] == "CPI"


def test_metadata(tmp_path: Path):
    cache = DataCache(tmp_path)
    cache.update_metadata(status="success")
    assert cache.get_last_updated() is not None
    meta = cache.load("metadata")
    assert meta["status"] == "success"


def test_exists(tmp_path: Path):
    cache = DataCache(tmp_path)
    assert not cache.exists("stocks")
    cache.save("stocks", [])
    assert cache.exists("stocks")
