"""Tests for metric status classification."""

from src.visualization.metrics_status import classify_metric_status, get_gauge_range


def test_normal_status():
    config = {"warn_low": 2.0, "warn_high": 5.0, "danger_low": 1.0, "danger_high": 7.0}
    status, label, color = classify_metric_status(3.5, config)
    assert status == "normal"
    assert label == "正常"


def test_warning_high():
    config = {"warn_high": 5.0, "danger_high": 7.0}
    status, label, _ = classify_metric_status(5.5, config)
    assert status == "warning"
    assert label == "预警"


def test_danger_low():
    config = {"danger_low": 1.0}
    status, label, _ = classify_metric_status(0.5, config)
    assert status == "danger"
    assert label == "危险"


def test_gauge_range_explicit():
    config = {"min_val": 0, "max_val": 10}
    lo, hi = get_gauge_range(5.0, config)
    assert lo == 0
    assert hi == 10


def test_gauge_range_auto():
    config = {}
    lo, hi = get_gauge_range(100.0, config)
    assert lo < 100
    assert hi > 100
