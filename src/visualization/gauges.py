"""Plotly gauge / speedometer charts for macro metrics."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from src.visualization.metrics_status import STATUS_COLORS, get_gauge_range


def render_gauge(metric: dict[str, Any]) -> go.Figure:
    """Create a compact car-dashboard style gauge for a single metric."""
    value = metric.get("value")
    name = metric.get("name", "Metric")
    unit = metric.get("unit", "")
    status_color = metric.get("status_color", STATUS_COLORS["unknown"])
    status_label = metric.get("status_label", "")

    h = 118
    title_size = 10
    num_size = 16

    if value is None:
        fig = go.Figure(
            go.Indicator(
                mode="number",
                value=0,
                title={"text": f"{name}<br><span style='font-size:0.65em;color:#94a3b8'>{status_label}</span>"},
                number={"font": {"size": num_size, "color": "#94a3b8"}},
            )
        )
        fig.update_layout(height=h, margin=dict(l=8, r=8, t=42, b=4), paper_bgcolor="rgba(0,0,0,0)")
        return fig

    min_val, max_val = get_gauge_range(value, metric)

    # Build threshold steps for gauge bar coloring
    steps = _build_gauge_steps(metric, min_val, max_val)

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=value,
            number={
                "suffix": f" {unit}" if unit else "",
                "font": {"size": num_size, "color": "#f1f5f9"},
            },
            title={
                "text": (
                    f"<span style='font-size:{title_size}px'>{name}</span><br>"
                    f"<span style='font-size:0.65em;color:{status_color}'>● {status_label}</span>"
                ),
                "font": {"size": title_size, "color": "#e2e8f0"},
            },
            gauge={
                "axis": {
                    "range": [min_val, max_val],
                    "tickwidth": 1,
                    "tickcolor": "#475569",
                    "tickfont": {"color": "#94a3b8", "size": 7},
                },
                "bar": {"color": status_color, "thickness": 0.2},
                "bgcolor": "#1e293b",
                "borderwidth": 2,
                "bordercolor": "#334155",
                "steps": steps,
                "threshold": {
                    "line": {"color": "#f8fafc", "width": 3},
                    "thickness": 0.8,
                    "value": value,
                },
            },
        )
    )

    fig.update_layout(
        height=h,
        margin=dict(l=10, r=10, t=48, b=4),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e2e8f0", "size": 9},
    )
    return fig


def _build_gauge_steps(
    metric: dict[str, Any], min_val: float, max_val: float
) -> list[dict[str, Any]]:
    """Build colored background steps on the gauge."""
    steps: list[dict[str, Any]] = []
    span = max_val - min_val
    if span <= 0:
        return steps

    danger_low = metric.get("danger_low")
    danger_high = metric.get("danger_high")
    warn_low = metric.get("warn_low")
    warn_high = metric.get("warn_high")

    # Green (normal) base
    steps.append({"range": [min_val, max_val], "color": "rgba(34, 197, 94, 0.15)"})

    if danger_low is not None and danger_low > min_val:
        steps.append(
            {"range": [min_val, danger_low], "color": "rgba(239, 68, 68, 0.35)"}
        )
    if warn_low is not None and warn_low > min_val:
        lo = danger_low if danger_low is not None else min_val
        if warn_low > lo:
            steps.append({"range": [lo, warn_low], "color": "rgba(245, 158, 11, 0.3)"})

    if danger_high is not None and danger_high < max_val:
        steps.append(
            {"range": [danger_high, max_val], "color": "rgba(239, 68, 68, 0.35)"}
        )
    if warn_high is not None and warn_high < max_val:
        hi = danger_high if danger_high is not None else max_val
        if warn_high < hi:
            steps.append({"range": [warn_high, hi], "color": "rgba(245, 158, 11, 0.3)"})

    return steps
