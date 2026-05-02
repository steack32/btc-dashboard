"""Helpers Plotly factorisés pour le dashboard.

Toutes les courbes ont par défaut :
  - boutons de période (1M, 6M, 1A, 3A, Max) en haut à gauche
  - tooltip unifié au survol (toutes les valeurs à la même date)
  - zoom à la souris (drag pour sélectionner une zone, double-clic pour reset)
  - molette pour zoomer (scroll zoom)
  - barre d'outils visible (export PNG, reset, pan, zoom)
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


# Configuration passée à st.plotly_chart pour activer zoom molette + barre d'outils
CHART_CONFIG = {
    "displaylogo": False,
    "displayModeBar": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
    "toImageButtonOptions": {"format": "png", "filename": "btc-dashboard", "scale": 2},
    "scrollZoom": True,
    "doubleClick": "reset",
    "locale": "fr",
}

GAUGE_CONFIG = {"displayModeBar": False, "staticPlot": True}


def _base_layout(title: str, height: int = 320, with_rangeselector: bool = True) -> dict:
    xaxis: dict = dict(
        gridcolor="#2A2A2A",
        showgrid=True,
        zeroline=False,
        showspikes=True,
        spikemode="across",
        spikethickness=1,
        spikecolor="#777",
        spikedash="dot",
        rangeslider=dict(visible=False),
    )
    if with_rangeselector:
        xaxis["rangeselector"] = dict(
            buttons=[
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(count=1, label="1A", step="year", stepmode="backward"),
                dict(count=3, label="3A", step="year", stepmode="backward"),
                dict(step="all", label="Tout"),
            ],
            bgcolor="#1E1E1E",
            activecolor="#FFB300",
            font=dict(color="#E0E0E0", size=11),
            x=0,
            y=1.10,
            xanchor="left",
            yanchor="top",
        )
    return dict(
        title=dict(text=title, font=dict(size=14, color="#E0E0E0"), x=0.0),
        height=height,
        margin=dict(l=10, r=10, t=70 if with_rangeselector else 40, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E0E0E0"),
        xaxis=xaxis,
        yaxis=dict(gridcolor="#2A2A2A", showgrid=True, zeroline=False, fixedrange=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.5, xanchor="center",
                    bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#1A1A1A", bordercolor="#444",
                        font=dict(color="#E0E0E0", size=12)),
        dragmode="zoom",
    )


def line_chart(
    title: str,
    traces: list[dict],
    y_log: bool = False,
    h_lines: list[dict] | None = None,
    h_zones: list[dict] | None = None,
    height: int = 320,
    rangeselector: bool = True,
    y_format: str = ",.2f",
    y_title: str | None = None,
) -> go.Figure:
    """Graphique linéaire enrichi.

    traces  : [{"name": str, "series": pd.Series, "color": str?, "dash": str?, "width": float?}]
    h_lines : [{"y": float, "label": str, "color": str?, "dash": str?}]
    h_zones : [{"y0": float, "y1": float, "color": str?}] — bandes colorées en arrière-plan
    """
    fig = go.Figure()
    for t in traces:
        s = t["series"].dropna()
        if s.empty:
            continue
        fig.add_trace(go.Scatter(
            x=s.index,
            y=s.values,
            name=t["name"],
            mode="lines",
            line=dict(
                color=t.get("color", "#FFB300"),
                width=t.get("width", 1.8),
                dash=t.get("dash", "solid"),
            ),
            hovertemplate=f"<b>{t['name']}</b> : %{{y:{y_format}}}<extra></extra>",
        ))

    layout = _base_layout(title, height=height, with_rangeselector=rangeselector)
    if y_log:
        layout["yaxis"]["type"] = "log"
    if y_title:
        layout["yaxis"]["title"] = dict(text=y_title, font=dict(size=11, color="#999"))
    fig.update_layout(**layout)

    # Zones colorées en arrière-plan (zones critiques)
    for z in h_zones or []:
        fig.add_hrect(
            y0=z["y0"],
            y1=z["y1"],
            fillcolor=z.get("color", "rgba(229,57,53,0.07)"),
            line_width=0,
            layer="below",
        )

    # Lignes horizontales de seuil
    for h in h_lines or []:
        color = h.get("color", "#888")
        fig.add_hline(
            y=h["y"],
            line=dict(color=color, dash=h.get("dash", "dash"), width=1),
            annotation_text=h.get("label", ""),
            annotation_position=h.get("position", "top right"),
            annotation_font=dict(size=10, color=color),
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
