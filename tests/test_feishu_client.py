"""Tests for Feishu client field extraction."""

from src.data.feishu_client import FeishuClient
from config.settings import FeishuConfig


def test_extract_field_string():
    fields = {"Ticker": "AAPL", "Name": "Apple"}
    assert FeishuClient._extract_field(fields, "Ticker", "ticker") == "AAPL"
    assert FeishuClient._extract_field(fields, "Name") == "Apple"


def test_extract_field_list():
    fields = {"Ticker": [{"text": "MSFT"}]}
    assert FeishuClient._extract_field(fields, "Ticker") == "MSFT"


def test_extract_number():
    fields = {"Warn High": 5.0, "Min": "0"}
    assert FeishuClient._extract_number(fields, "Warn High") == 5.0
    assert FeishuClient._extract_number(fields, "Min") == 0.0
    assert FeishuClient._extract_number(fields, "Missing") is None
