"""Helpers Plotly factorisés pour le dashboard.

UX inspirée de TradingView :
  - Pan à la souris par défaut (drag pour faire défiler la timeline)
  - Scroll molette = zoom centré sur la position du curseur
  - Crosshair (réticule) qui suit la souris avec valeurs sur les axes
  - Range slider compact en bas pour scrubber rapidement dans l'historique
  - Boutons de période (1M, 6M, 1A, 3A, Tout) au-dessus
  - Outils de dessin (lignes de tendance, formes) dans la barre d'outils
  - Zoom préservé entre les rerenders Streamlit grâce à uirevision
  - Format de date qui s'adapte selon le niveau de zoom
  - Bouton plein écran sur chaque graph
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from config import PALETTE


# Configuration passée à st.plotly_chart pour activer molette + barre d'outils complète
CHART_CONFIG = {
    "displaylogo": False,
    "displayModeBar": True,
    "modeBarButtonsToAdd": [
        "drawline",       # tracer des lignes de tendance
        "drawopenpath",   # tracer des courbes libres
        "drawrect",       # encadrer une zone
        "eraseshape",     # effacer les formes dessinées
    ],
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "btc-dashboard",
        "scale": 2,
        "width": 1600,
        "height": 800,
    },
    "scrollZoom": True,
    "doubleClick": "reset",
    "showAxisDragHandles": True,
    "showAxisRangeEntryBoxes": True,
    "responsive": True,
}

GAUGE_CONFIG = {"displayModeBar": False, "staticPlot": True}


# Format de date adaptatif : selon le niveau de zoom, on affiche jour/semaine/mois/année
_TICKFORMAT_STOPS = [
    dict(dtickrange=[None, 86400000], value="%H:%M"),                 # < 1 jour
    dict(dtickrange=[86400000, 604800000], value="%d %b"),            # < 1 semaine
    dict(dtickrange=[604800000, 2592000000], value="%d %b %Y"),       # < 1 mois
    dict(dtickrange=[2592000000, 31536000000], value="%b %Y"),        # < 1 an
    dict(dtickrange=[31536000000, None], value="%Y"),                 # > 1 an
]


def _base_layout(
    title: str,
    height: int = 320,
    with_rangeselector: bool = True,
    with_rangeslider: bool = True,
    uikey: str = "default",
) -> dict:
    xaxis: dict = dict(
        gridcolor=PALETTE["border"],
        showgrid=True,
        zeroline=False,
        showspikes=True,
        spikemode="across",
        spikethickness=1.2,
        spikecolor=PALETTE["accent"],
        spikedash="solid",
        spikesnap="cursor",
        showline=True,
        linecolor=PALETTE["border_strong"],
        tickformatstops=_TICKFORMAT_STOPS,
        rangeslider=dict(
            visible=with_rangeslider,
            thickness=0.05,
            bgcolor=PALETTE["bg"],
            bordercolor=PALETTE["border"],
            borderwidth=1,
        ),
        type="date",
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
            bgcolor=PALETTE["surface"],
            activecolor=PALETTE["accent"],
            font=dict(color=PALETTE["text"], size=11),
            x=0,
            y=1.12,
            xanchor="left",
            yanchor="top",
        )

    yaxis = dict(
        gridcolor=PALETTE["border"],
        showgrid=True,
        zeroline=False,
        showspikes=True,
        spikemode="across",
        spikethickness=1.2,
        spikecolor=PALETTE["accent"],
        spikedash="solid",
        spikesnap="cursor",
        showline=True,
        linecolor=PALETTE["border_strong"],
        side="right",
        autorange=True,
        fixedrange=False,
    )

    return dict(
        title=dict(text=title, font=dict(size=14, color=PALETTE["text"]), x=0.0, y=0.97),
        height=height,
        margin=dict(l=10, r=60, t=70 if with_rangeselector else 40, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=PALETTE["text"], family="Inter, system-ui, sans-serif"),
        xaxis=xaxis,
        yaxis=yaxis,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.04,
            x=1,
            xanchor="right",
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor=PALETTE["surface"],
            bordercolor=PALETTE["border_strong"],
            font=dict(color=PALETTE["text"], size=12, family="Inter, system-ui, sans-serif"),
        ),
        dragmode="pan",
        uirevision=uikey,
        newshape=dict(line=dict(color=PALETTE["accent"], width=2)),
        modebar=dict(
            bgcolor="rgba(0,0,0,0)",
            color=PALETTE["text_muted"],
            activecolor=PALETTE["accent"],
            orientation="v",
        ),
    )


def line_chart(
    title: str,
    traces: list[dict],
    y_log: bool = False,
    h_lines: list[dict] | None = None,
    h_zones: list[dict] | None = None,
    height: int = 360,
    rangeselector: bool = True,
    rangeslider: bool = True,
    y_format: str = ",.2f",
    y_title: str | None = None,
    uikey: str | None = None,
) -> go.Figure:
    """Graphique linéaire avec UX type TradingView.

    traces  : [{"name": str, "series": pd.Series, "color": str?, "dash": str?, "width": float?}]
    h_lines : [{"y": float, "label": str, "color": str?, "dash": str?}]
    h_zones : [{"y0": float, "y1": float, "color": str?}] — bandes de fond
    uikey   : identifiant stable pour préserver le zoom (défaut = title)
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
                color=t.get("color", PALETTE["accent"]),
                width=t.get("width", 1.8),
                dash=t.get("dash", "solid"),
                shape="linear",
            ),
            hovertemplate=f"<b>{t['name']}</b> %{{y:{y_format}}}<extra></extra>",
            connectgaps=False,
        ))

    layout = _base_layout(
        title,
        height=height,
        with_rangeselector=rangeselector,
        with_rangeslider=rangeslider,
        uikey=uikey or title,
    )
    if y_log:
        layout["yaxis"]["type"] = "log"
    if y_title:
        layout["yaxis"]["title"] = dict(text=y_title, font=dict(size=11, color="#888"))
    fig.update_layout(**layout)

    # Bandes critiques en arrière-plan
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
        color = h.get("color", PALETTE["text_muted"])
        fig.add_hline(
            y=h["y"],
            line=dict(color=color, dash=h.get("dash", "dash"), width=1),
            annotation_text=h.get("label", ""),
            annotation_position=h.get("position", "top right"),
            annotation_font=dict(size=10, color=color),
        )
    return fig


def gauge(score: float, color: str) -> go.Figure:
    """Compteur angulaire (style tachymètre) pour le score global.

    L'aiguille (threshold) est colorée selon le palier — vert/or/rouge.
    Les bandes de fond sont les zones d'accumulation / neutre / vente.
    """
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={"x": [0.05, 0.95], "y": [0.0, 1.0]},
        number={
            "font": {
                "size": 52,
                "color": PALETTE["text"],
                "family": "Inter, sans-serif",
            },
            "suffix": " / 100",
            "valueformat": ".0f",
        },
        gauge={
            "shape": "angular",
            "axis": {
                "range": [0, 100],
                "tickwidth": 0,
                "tickcolor": PALETTE["text_dim"],
                "tickfont": {
                    "size": 10,
                    "color": PALETTE["text_dim"],
                    "family": "Inter, sans-serif",
                },
                "tickvals": [0, 50, 100],
                "ticktext": ["0", "50", "100"],
            },
            "bar": {"color": "rgba(0,0,0,0)", "thickness": 0},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 40], "color": "#2A4D38"},   # vert sombre — Accumuler
                {"range": [40, 75], "color": "#4D4128"},  # or sombre — Ne rien faire
                {"range": [75, 100], "color": "#4D2828"}, # rouge sombre — Vendre
            ],
            "threshold": {
                "line": {"color": color, "width": 5},
                "thickness": 0.85,
                "value": score,
            },
        },
    ))
    fig.update_layout(
        height=230,
        margin=dict(l=20, r=20, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=PALETTE["text"], family="Inter, sans-serif"),
    )
    return fig
