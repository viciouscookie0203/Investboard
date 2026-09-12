"""Metric status classification and color coding."""

from __future__ import annotations

from typing import Any

# Status colors — traffic-light palette tuned for dark dashboards
STATUS_COLORS = {
    "normal": "#22c55e",    # green
    "warning": "#f59e0b",   # amber
    "danger": "#ef4444",    # red
    "unknown": "#94a3b8",   # slate
    "error": "#64748b",
}

STATUS_LABELS = {
    "normal": "正常",
    "warning": "预警",
    "danger": "危险",
    "unknown": "无数据",
    "error": "错误",
}


def classify_metric_status(
    value: float, config: dict[str, Any]
) -> tuple[str, str, str]:
    """
    Classify a metric value against configured thresholds.

    Returns (status_key, status_label, hex_color).
    Threshold priority: danger > warning > normal.
    """
    warn_low = config.get("warn_low")
    warn_high = config.get("warn_high")
    danger_low = config.get("danger_low")
    danger_high = config.get("danger_high")
    direction = (config.get("direction") or "neutral").lower()

    # Danger zone
    if danger_low is not None and value < danger_low:
        return "danger", STATUS_LABELS["danger"], STATUS_COLORS["danger"]
    if danger_high is not None and value > danger_high:
        return "danger", STATUS_LABELS["danger"], STATUS_COLORS["danger"]

    # Warning zone
    if warn_low is not None and value < warn_low:
        return "warning", STATUS_LABELS["warning"], STATUS_COLORS["warning"]
    if warn_high is not None and value > warn_high:
        return "warning", STATUS_LABELS["warning"], STATUS_COLORS["warning"]

    # Direction-based heuristics when no explicit thresholds
    if direction == "lower_is_better" and warn_high is None:
        if value > 5:
            return "warning", STATUS_LABELS["warning"], STATUS_COLORS["warning"]
    if direction == "higher_is_better" and warn_low is None:
        if value < 0:
            return "warning", STATUS_LABELS["warning"], STATUS_COLORS["warning"]

    return "normal", STATUS_LABELS["normal"], STATUS_COLORS["normal"]


def get_gauge_range(value: float | None, config: dict[str, Any]) -> tuple[float, float]:
    """Determine gauge min/max for plotly indicator."""
    min_val = config.get("min_val")
    max_val = config.get("max_val")

    if min_val is not None and max_val is not None:
        return float(min_val), float(max_val)

    if value is None:
        return 0.0, 100.0

    # Auto range: ±30% around value, respecting thresholds
    bounds = [value * 0.7, value * 1.3]
    for key in ("danger_low", "warn_low", "warn_high", "danger_high"):
        v = config.get(key)
        if v is not None:
            bounds.extend([v * 0.9, v * 1.1])

    lo = min(bounds)
    hi = max(bounds)
    if lo == hi:
        hi = lo + 1
    return lo, hi
