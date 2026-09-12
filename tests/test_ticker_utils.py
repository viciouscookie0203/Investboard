"""Tests for ticker normalization."""

from src.data.ticker_utils import (
    normalize_stock_ticker,
    parse_fred_series,
    parse_threshold_json,
    parse_yfinance_fallback,
)


def test_index_ticker():
    assert normalize_stock_ticker("SPX500", "US", "index") == "^GSPC"
    assert normalize_stock_ticker("DJI", "US", "index") == "^DJI"


def test_hk_ticker():
    assert normalize_stock_ticker("00005", "HK", "stock") == "0005.HK"


def test_us_stock():
    assert normalize_stock_ticker("MSFT", "US", "stock") == "MSFT"


def test_parse_fred():
    assert parse_fred_series("FRED:DGS10") == "DGS10"
    assert parse_fred_series("TwelveData:DXY") is None


def test_parse_yfinance_fallback():
    assert parse_yfinance_fallback("TwelveData:DXY") == "DX-Y.NYB"
    assert parse_yfinance_fallback("TwelveData:VIX") == "^VIX"


def test_parse_threshold_json():
    t = parse_threshold_json('{"high_alert":4.5,"low_alert":3.5}')
    assert t["warn_high"] == 4.5
    assert t["warn_low"] == 3.5
