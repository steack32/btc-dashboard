"""Helpers Plotly factorisés pour le dashboard."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def _base_layout(title: str, height: int = 320) -> dict:
    return dict(
        title=dict(text=title, font=dict(size=14)),
        height=height,
        margin=dict(l=10, r=10, t=40, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E0E0E0"),
        xaxis=dict(gridcolor="#2A2A2A", showgrid=True, zeroline=False),
        yaxis=dict(gridcolor="#2A2A2A", showgrid=True, zeroline=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )


def line_chart(title: str, traces: list[dict], y_log: bool = False,
               h_lines: list[dict] | None = None, height: int = 320) -> go.Figure:
    """traces : [{'name': str, 'series': pd.Series, 'color': str?, 'dash': str?}]
    h_lines : [{'y': float, 'label': str?, 'color': str?, 'dash': str?}]
    """
    fig = go.Figure()
    for t in traces:
        s = t["series"].dropna()
        if s.empty:
            continue
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name=t["name"], mode="lines",
            line=dict(color=t.get("color", "#FFB300"), width=t.get("width", 1.6),
                      dash=t.get("dash", "solid")),
        ))
    layout = _base_layout(title, height=height)
    if y_log:
        layout["yaxis"]["type"] = "log"
    fig.update_layout(**layout)
    for h in h_lines or []:
        fig.add_hline(
            y=h["y"], line=dict(color=h.get("color", "#888"), dash=h.get("dash", "dash"), width=1),
            annotation_text=h.get("label", ""), annotation_position="right",
            annotation_font=dict(size=10, color=h.get("color", "#888")),
        )
    return fig


def gauge(score: float, color: str) -> go.Figure:
    """Jauge horizontale 0-100 pour le score global."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={"x": [0, 1], "y": [0, 1]},
        number={"font": {"size": 56, "color": color}, "suffix": "/100"},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#888"},
            "bar": {"color": color, "thickness": 0.35},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 20], "color": "#0D2B4A"},
                {"range": [20, 40], "color": "#37474F"},
                {"range": [40, 60], "color": "#424242"},
                {"range": [60, 80], "color": "#1B5E20"},
                {"range": [80, 100], "color": "#7F1D1D"},
            ],
        },
    ))
    fig.update_layout(
        height=240,
        margin=dict(l=20, r=20, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E0E0E0"),
    )
    return fig
