"""Affichage de la section Backtest."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from analysis import backtest as bt
from analysis.backtest import KEY_DATES, extract_key_dates
from config import PALETTE
from ui.charts import CHART_CONFIG


def _backtest_chart(history: pd.DataFrame) -> go.Figure:
    """Prix BTC (échelle log, gauche) + score 0-100 (droite) sur le même graph.

    Bandes de fond colorées pour les zones Accumuler / Ne rien faire / Vendre.
    Marqueurs aux dates clés (tops/bottoms historiques).
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Bandes des paliers en arrière-plan (sur l'axe score)
    fig.add_hrect(
        y0=0, y1=40,
        fillcolor="rgba(47,191,113,0.07)", line_width=0, layer="below",
        secondary_y=True,
    )
    fig.add_hrect(
        y0=40, y1=75,
        fillcolor="rgba(212,160,68,0.05)", line_width=0, layer="below",
        secondary_y=True,
    )
    fig.add_hrect(
        y0=75, y1=100,
        fillcolor="rgba(209,69,69,0.07)", line_width=0, layer="below",
        secondary_y=True,
    )

    # Prix BTC (axe gauche, log)
    fig.add_trace(
        go.Scatter(
            x=history.index,
            y=history["btc_price"],
            name="Prix BTC",
            mode="lines",
            line=dict(color=PALETTE["accent"], width=1.6),
            hovertemplate="<b>BTC</b> $%{y:,.0f}<extra></extra>",
        ),
        secondary_y=False,
    )

    # Score (axe droit, 0-100)
    fig.add_trace(
        go.Scatter(
            x=history.index,
            y=history["score"],
            name="Score système",
            mode="lines",
            line=dict(color=PALETTE["info"], width=1.4),
            hovertemplate="<b>Score</b> %{y:.0f}/100<extra></extra>",
        ),
        secondary_y=True,
    )

    # Lignes horizontales aux seuils 40 et 75 sur l'axe score
    fig.add_hline(
        y=40, line=dict(color=PALETTE["success"], dash="dash", width=1),
        annotation_text="Seuil Accumuler", annotation_position="bottom right",
        annotation_font=dict(size=10, color=PALETTE["success"]),
        secondary_y=True,
    )
    fig.add_hline(
        y=75, line=dict(color=PALETTE["danger"], dash="dash", width=1),
        annotation_text="Seuil Vendre", annotation_position="top right",
        annotation_font=dict(size=10, color=PALETTE["danger"]),
        secondary_y=True,
    )

    # Marqueurs aux dates clés sur la courbe du prix
    for kd in KEY_DATES:
        d = kd["date"]
        if d < history.index.min() or d > history.index.max():
            continue
        # On va chercher le prix à cette date (ou la plus proche dans la fenêtre)
        nearest_idx = history.index.get_indexer([d], method="nearest")[0]
        price_at = history["btc_price"].iloc[nearest_idx]
        marker_color = PALETTE["danger"] if kd["kind"] == "top" else PALETTE["success"]
        fig.add_trace(
            go.Scatter(
                x=[history.index[nearest_idx]],
                y=[price_at],
                mode="markers",
                marker=dict(symbol="circle", size=9, color=marker_color,
                            line=dict(color="#FFFFFF", width=1)),
                name=kd["label"],
                showlegend=False,
                hovertemplate=f"<b>{kd['label']}</b><br>Prix : $%{{y:,.0f}}<extra></extra>",
            ),
            secondary_y=False,
        )

    # Layout
    fig.update_layout(
        height=520,
        margin=dict(l=10, r=10, t=40, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=PALETTE["text"], family="Inter, system-ui, sans-serif"),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, x=0.5, xanchor="center",
            bgcolor="rgba(0,0,0,0)", font=dict(size=11),
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor=PALETTE["surface"], bordercolor=PALETTE["border_strong"],
            font=dict(color=PALETTE["text"], size=12),
        ),
        dragmode="pan",
        uirevision="backtest",
    )

    fig.update_xaxes(
        gridcolor=PALETTE["border"], zeroline=False,
        showspikes=True, spikemode="across", spikethickness=1,
        spikecolor=PALETTE["accent"], spikedash="solid", spikesnap="cursor",
        showline=True, linecolor=PALETTE["border_strong"],
        rangeslider=dict(visible=True, thickness=0.04, bgcolor=PALETTE["bg"]),
        rangeselector=dict(
            buttons=[
                dict(count=1, label="1A", step="year", stepmode="backward"),
                dict(count=3, label="3A", step="year", stepmode="backward"),
                dict(count=5, label="5A", step="year", stepmode="backward"),
                dict(step="all", label="Tout"),
            ],
            bgcolor=PALETTE["surface"], activecolor=PALETTE["accent"],
            font=dict(color=PALETTE["text"], size=11),
            x=0, y=1.10,
        ),
    )

    # Range explicite pour éviter l'autorange foireux en mode log + secondary_y.
    # On calcule les bornes à partir des données réelles, avec une marge.
    if not history["btc_price"].dropna().empty:
        prices = history["btc_price"].dropna()
        log_min = max(1, np.floor(np.log10(prices.min()) * 10) / 10 - 0.1)
        log_max = np.ceil(np.log10(prices.max()) * 10) / 10 + 0.1
    else:
        log_min, log_max = 3, 5.5

    fig.update_yaxes(
        title_text="Prix BTC (USD, log)",
        type="log",
        range=[log_min, log_max],
        gridcolor=PALETTE["border"], zeroline=False,
        title_font=dict(size=11, color=PALETTE["text_muted"]),
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text="Score (0-100)",
        range=[0, 100],
        gridcolor="rgba(0,0,0,0)", zeroline=False,
        title_font=dict(size=11, color=PALETTE["text_muted"]),
        secondary_y=True,
    )

    return fig


def render_backtest(history: pd.DataFrame) -> None:
    if history.empty:
        st.info("Pas assez de données pour afficher le backtest.")
        return

    st.subheader("Backtest historique")
    st.caption(
        "Simulation du score sur l'historique réel depuis mai 2018. "
        "Le système est-il bien calibré ? Passe en revue les tops et bottoms majeurs."
    )

    st.plotly_chart(_backtest_chart(history), use_container_width=True, config=CHART_CONFIG)

    # Stats globales
    valid = history.dropna(subset=["score"])
    if not valid.empty:
        pct_accumuler = (valid["palier"] == "Accumuler").mean() * 100
        pct_neutre = (valid["palier"] == "Ne rien faire").mean() * 100
        pct_vendre = (valid["palier"] == "Vendre").mean() * 100

        c1, c2, c3 = st.columns(3)
        c1.metric("Temps en Accumuler", f"{pct_accumuler:.1f}%")
        c2.metric("Temps en Ne rien faire", f"{pct_neutre:.1f}%")
        c3.metric("Temps en Vendre", f"{pct_vendre:.1f}%")

    # Tableau dates clés
    st.markdown("**Lecture du système aux retournements majeurs**")
    st.caption(
        "Pour chaque sommet ou creux historique, on regarde ce que le système aurait dit ce jour-là. "
        "Un signal réussi : score en zone d'accumulation (≤ 40) au creux, en zone de vente (≥ 70) au sommet."
    )
    table = extract_key_dates(history)
    if not table.empty:
        st.dataframe(table, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Simulation de stratégie
# ---------------------------------------------------------------------------

def _strategy_chart(sim: pd.DataFrame, dca: pd.DataFrame, bh: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=sim.index, y=sim["portfolio_value"],
        name="Stratégie (achat/vente)", mode="lines",
        line=dict(color=PALETTE["accent"], width=2.2),
        hovertemplate="<b>Stratégie</b> %{y:,.0f} €<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=dca.index, y=dca["portfolio_value"],
        name="DCA simple", mode="lines",
        line=dict(color=PALETTE["info"], width=1.6, dash="dot"),
        hovertemplate="<b>DCA simple</b> %{y:,.0f} €<extra></extra>",
    ))
    if bh is not None and not bh.empty:
        fig.add_trace(go.Scatter(
            x=bh.index, y=bh["portfolio_value"],
            name="Buy & Hold (capital équivalent)", mode="lines",
            line=dict(color=PALETTE["text_muted"], width=1.4, dash="dash"),
            hovertemplate="<b>Buy & Hold</b> %{y:,.0f} €<extra></extra>",
        ))

    # Capital investi de la stratégie en référence
    fig.add_trace(go.Scatter(
        x=sim.index, y=sim["total_invested"],
        name="Capital investi (cumul)", mode="lines",
        line=dict(color=PALETTE["text_dim"], width=1.2),
        hovertemplate="<b>Investi</b> %{y:,.0f} €<extra></extra>",
    ))

    fig.update_layout(
        height=440,
        margin=dict(l=10, r=10, t=40, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=PALETTE["text"], family="Inter, system-ui, sans-serif"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.5, xanchor="center",
                    bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=PALETTE["surface"], bordercolor=PALETTE["border_strong"],
                        font=dict(color=PALETTE["text"], size=12)),
        dragmode="pan",
        uirevision="strategy_sim",
    )
    fig.update_xaxes(
        gridcolor=PALETTE["border"], zeroline=False, showline=True,
        linecolor=PALETTE["border_strong"],
        rangeselector=dict(
            buttons=[
                dict(count=1, label="1A", step="year", stepmode="backward"),
                dict(count=3, label="3A", step="year", stepmode="backward"),
                dict(step="all", label="Tout"),
            ],
            bgcolor=PALETTE["surface"], activecolor=PALETTE["accent"],
            font=dict(color=PALETTE["text"], size=11), x=0, y=1.10,
        ),
    )
    fig.update_yaxes(
        title_text="Valeur du portefeuille (€)",
        gridcolor=PALETTE["border"], zeroline=False,
        title_font=dict(size=11, color=PALETTE["text_muted"]),
    )
    return fig


def _kpi_card(col, label: str, value: str, delta: str = "", color: str | None = None) -> None:
    delta_html = ""
    if delta:
        c = color or PALETTE["text_muted"]
        delta_html = (
            f"<div style='color:{c}; font-size:0.85rem; font-weight:500; margin-top:0.2rem;'>"
            f"{delta}</div>"
        )
    col.markdown(
        f"<div style='background:{PALETTE['surface']}; border:1px solid {PALETTE['border']};"
        f" border-radius:10px; padding:0.85rem 1rem;'>"
        f"<div style='color:{PALETTE['text_muted']}; font-size:0.72rem; font-weight:500;"
        f" text-transform:uppercase; letter-spacing:0.07em; margin-bottom:0.35rem;'>{label}</div>"
        f"<div style='font-size:1.45rem; font-weight:600; color:{PALETTE['text']};"
        f" letter-spacing:-0.02em; line-height:1.1;'>{value}</div>"
        f"{delta_html}"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_strategy_simulation(
    history: pd.DataFrame,
    buy_low: float = 10.0,
    buy_mid: float = 5.0,
    sell_high: float = 20.0,
) -> None:
    if history.empty:
        return

    st.subheader("Simulation de stratégie")
    st.caption(
        f"Règle simulée : **+{buy_low:.0f}€/jour** en zone Accumuler · "
        f"**+{buy_mid:.0f}€/jour** en zone Ne rien faire · "
        f"**−{sell_high:.0f}€/jour** en zone Vendre. "
        "Comparaison avec un DCA classique de même intensité moyenne et un Buy & Hold de capital équivalent."
    )

    sim = bt.simulate_strategy(history, buy_low=buy_low, buy_mid=buy_mid, sell_high=sell_high)
    # Pour la baseline DCA, on prend la moyenne pondérée des deux montants d'achat
    # comme "intensité moyenne" — c'est plus représentatif que le seul buy_low.
    avg_buy = (buy_low + buy_mid) / 2
    dca = bt.simulate_dca(history, avg_buy)
    bh = bt.simulate_buy_and_hold(history, dca["total_invested"].iloc[-1])

    last = sim.iloc[-1]
    last_dca = dca.iloc[-1]
    last_bh = bh.iloc[-1] if not bh.empty else None

    n_buys = (sim["buy_event"] > 0).sum()
    n_sells = (sim["sell_event"] > 0).sum()
    total_bought = sim["buy_event"].sum()
    total_sold = sim["cash_realized"].iloc[-1]

    # Première ligne : la stratégie elle-même
    c1, c2, c3, c4 = st.columns(4)
    _kpi_card(c1, "Capital investi", f"{last['total_invested']:,.0f} €".replace(",", " "))
    _kpi_card(c2, "Cash sécurisé (ventes)",
              f"{last['cash_realized']:,.0f} €".replace(",", " "),
              f"{n_sells} jours de vente")
    _kpi_card(c3, "BTC en portefeuille",
              f"{last['btc_position']:.6f} BTC",
              f"≈ {last['btc_position'] * (last['btc_price'] or 0):,.0f} €".replace(",", " "))
    _kpi_card(c4, "Valeur totale (BTC + cash)",
              f"{last['portfolio_value']:,.0f} €".replace(",", " "),
              f"{last['pnl']:+,.0f} € de PnL".replace(",", " "),
              PALETTE["success"] if last['pnl'] >= 0 else PALETTE["danger"])

    # Deuxième ligne : comparaisons
    st.markdown("<div style='height:0.4rem;'></div>", unsafe_allow_html=True)
    d1, d2, d3 = st.columns(3)

    strat_roi = last['roi_pct']
    dca_roi = last_dca['roi_pct']
    bh_roi = last_bh['roi_pct'] if last_bh is not None else float('nan')

    _kpi_card(
        d1, "ROI Stratégie",
        f"{strat_roi:+.1f}%",
        f"vs capital investi {last['total_invested']:,.0f} €".replace(",", " "),
        PALETTE["success"] if strat_roi >= 0 else PALETTE["danger"],
    )
    _kpi_card(
        d2, "ROI DCA simple",
        f"{dca_roi:+.1f}%",
        f"écart : {strat_roi - dca_roi:+.1f} pts",
        PALETTE["success"] if strat_roi >= dca_roi else PALETTE["danger"],
    )
    _kpi_card(
        d3, "ROI Buy & Hold",
        f"{bh_roi:+.1f}%" if not pd.isna(bh_roi) else "—",
        f"écart : {strat_roi - bh_roi:+.1f} pts" if not pd.isna(bh_roi) else "",
        PALETTE["success"] if strat_roi >= bh_roi else PALETTE["danger"],
    )

    st.plotly_chart(_strategy_chart(sim, dca, bh), use_container_width=True, config=CHART_CONFIG)

    caption = (
        f"Sur la période : **{n_buys} jours d'achat** ({total_bought:,.0f} € investis cumulés) · "
        f"**{n_sells} jours de vente** ({total_sold:,.0f} € sécurisés cumulés). "
        "Note : la simulation traite € ≈ $ pour simplifier (BTC est libellé en USD dans la source)."
    ).replace(",", " ")
    st.caption(caption)
