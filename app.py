"""Dashboard BTC — orchestration Streamlit.

Lance avec : streamlit run app.py
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from analysis import backtest as bt
from analysis import indicators as ind
from analysis import scoring as sc
from config import PALETTE
from data import sources as ds
from ui.backtest import render_backtest, render_strategy_simulation
from ui.header import render_header
from ui.sections import (
    render_technique,
    render_onchain,
    render_macro,
    render_sentiment,
    render_summary_table,
)
from ui.theme import apply_theme


st.set_page_config(
    page_title="Bitcoin Dashboard",
    page_icon="₿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

apply_theme()


# ---------------------------------------------------------------------------
# Chargement des données (cache Streamlit + cache disque par-dessus)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def load_all_data() -> dict:
    return {
        "btc": ds.fetch_btc(),
        "gold": ds.fetch_gold(),
        "dxy": ds.fetch_dxy(),
        "miner_revenue": ds.fetch_miner_revenue(),
        "market_cap": ds.fetch_market_cap(),
        "mvrv_z": ds.fetch_mvrv_zscore(),
        "realized_cap": ds.fetch_realized_cap(),
        "fear_greed": ds.fetch_fear_greed(),
    }


def _last_value(df: pd.DataFrame | None, col: str = "value") -> float:
    if df is None or df.empty or col not in df.columns:
        return float("nan")
    s = df[col].dropna()
    return float(s.iloc[-1]) if not s.empty else float("nan")


def _last_value_series(s: pd.Series | None) -> float:
    if s is None:
        return float("nan")
    s = s.dropna()
    return float(s.iloc[-1]) if not s.empty else float("nan")


def _pct_change(s: pd.Series, days: int) -> float:
    """Variation en % sur N jours, NaN si pas assez d'historique."""
    if s is None or s.empty or len(s) <= days:
        return float("nan")
    last, ref = s.iloc[-1], s.iloc[-1 - days]
    if ref == 0 or pd.isna(ref) or pd.isna(last):
        return float("nan")
    return (float(last) / float(ref) - 1) * 100


# ---------------------------------------------------------------------------
# Calcul des scores
# ---------------------------------------------------------------------------

def compute_scores(data: dict) -> tuple[list[sc.IndicatorScore], dict[str, sc.IndicatorScore]]:
    scores: list[sc.IndicatorScore] = []

    btc = data["btc"]
    btc_price = btc["value"] if not btc.empty else pd.Series(dtype=float)

    if not btc_price.empty:
        rsi_w = ind.rsi_weekly(btc_price)
        scores.append(sc.score_rsi_weekly(_last_value_series(rsi_w)))

        mayer = ind.mayer_multiple(btc_price)
        scores.append(sc.score_mayer(_last_value_series(mayer)))

        ath_d = ind.ath_distance(btc_price)
        scores.append(sc.score_ath_distance(_last_value_series(ath_d)))

    mvrv = data.get("mvrv_z")
    if mvrv is not None and not mvrv.empty:
        scores.append(sc.score_mvrv_z(_last_value(mvrv)))
    else:
        mc = data.get("market_cap")
        rc = data.get("realized_cap")
        if mc is not None and rc is not None and not mc.empty and not rc.empty:
            z_local = ind.mvrv_zscore_local(mc["value"], rc["value"])
            scores.append(sc.score_mvrv_z(_last_value_series(z_local)))

    mr = data.get("miner_revenue")
    if mr is not None and not mr.empty:
        puell = ind.puell_multiple(mr["value"])
        scores.append(sc.score_puell(_last_value_series(puell)))

    gold = data.get("gold")
    if gold is not None and not gold.empty and not btc_price.empty:
        bg = ind.btc_gold_ratio(btc_price, gold["value"])
        last_bg = bg.dropna().iloc[-1] if not bg.dropna().empty else None
        if last_bg is not None:
            scores.append(sc.score_btc_gold(float(last_bg["ratio"]), float(last_bg["ratio_ma200"])))

    dxy = data.get("dxy")
    if dxy is not None and not dxy.empty:
        trend = ind.dxy_trend(dxy["value"])
        scores.append(sc.score_dxy(_last_value_series(trend)))

    fng = data.get("fear_greed")
    if fng is not None and not fng.empty:
        scores.append(sc.score_fear_greed(_last_value(fng)))

    by_name = {s.name: s for s in scores}
    return scores, by_name


# ---------------------------------------------------------------------------
# KPIs rapides du hero
# ---------------------------------------------------------------------------

def build_kpis(data: dict, scores: dict) -> list[dict]:
    """Construit la grille de KPIs affichée sous le compteur."""
    btc = data["btc"]["value"] if not data["btc"].empty else pd.Series(dtype=float)
    last_price = _last_value_series(btc)
    chg_7 = _pct_change(btc, 7)
    chg_30 = _pct_change(btc, 30)

    def _delta_color(v: float) -> str:
        if pd.isna(v):
            return PALETTE["text_muted"]
        return PALETTE["success"] if v >= 0 else PALETTE["danger"]

    def _delta_str(v: float) -> str:
        if pd.isna(v):
            return ""
        sign = "+" if v >= 0 else ""
        return f"{sign}{v:.2f}% sur la période"

    # Prix BTC formaté
    if not pd.isna(last_price):
        if last_price >= 1000:
            price_str = f"${last_price:,.0f}".replace(",", " ")
        else:
            price_str = f"${last_price:,.2f}"
    else:
        price_str = "—"

    kpis = [
        {
            "label": "Prix BTC",
            "value": price_str,
            "delta": f"+{chg_7:.2f}% (7j)" if not pd.isna(chg_7) and chg_7 >= 0
                     else (f"{chg_7:.2f}% (7j)" if not pd.isna(chg_7) else ""),
            "delta_color": _delta_color(chg_7),
        },
        {
            "label": "Variation 30j",
            "value": (f"+{chg_30:.1f}%" if not pd.isna(chg_30) and chg_30 >= 0
                      else (f"{chg_30:.1f}%" if not pd.isna(chg_30) else "—")),
            "delta": "",
            "delta_color": _delta_color(chg_30),
        },
    ]

    if "mvrv_z" in scores:
        s = scores["mvrv_z"]
        kpis.append({
            "label": "MVRV Z-Score",
            "value": f"{s.raw:.2f}" if not pd.isna(s.raw) else "—",
            "delta": s.interpretation,
            "delta_color": PALETTE["text_muted"],
        })

    if "mayer" in scores:
        s = scores["mayer"]
        kpis.append({
            "label": "Mayer Multiple",
            "value": f"{s.raw:.2f}" if not pd.isna(s.raw) else "—",
            "delta": s.interpretation,
            "delta_color": PALETTE["text_muted"],
        })

    if "rsi_weekly" in scores:
        s = scores["rsi_weekly"]
        kpis.append({
            "label": "RSI hebdo",
            "value": f"{s.raw:.0f}" if not pd.isna(s.raw) else "—",
            "delta": s.interpretation,
            "delta_color": PALETTE["text_muted"],
        })

    if "fear_greed" in scores:
        s = scores["fear_greed"]
        kpis.append({
            "label": "Fear & Greed",
            "value": f"{s.raw:.0f}" if not pd.isna(s.raw) else "—",
            "delta": s.interpretation,
            "delta_color": PALETTE["text_muted"],
        })

    return kpis


# ---------------------------------------------------------------------------
# Layout principal
# ---------------------------------------------------------------------------

def main() -> None:
    with st.spinner("Récupération des données..."):
        data = load_all_data()

    if data["btc"].empty:
        st.error(
            "Impossible de récupérer le prix BTC. Vérifie ta connexion ou réessaie dans quelques minutes."
        )
        st.stop()

    scores_list, scores = compute_scores(data)
    agg, palier = sc.aggregate(scores_list)
    verdict = sc.generate_verdict(scores_list, agg, palier)

    days_post = ind.days_since_last_halving()
    days_next = ind.days_until_next_halving()
    kpis = build_kpis(data, scores)

    render_header(agg, palier, verdict, days_post, days_next, kpis=kpis)

    render_technique(scores, data)
    render_onchain(scores, data)
    render_macro(scores, data)
    render_sentiment(scores, data)
    render_summary_table(scores_list)

    # Backtest historique : calcul vectorisé rapide (<200ms sur 8 ans).
    # Le cache de load_all_data() évite déjà les appels API en double.
    history = bt.compute_historical_scores(data)
    render_backtest(history)
    render_strategy_simulation(history, buy_low=10.0, buy_mid=5.0, sell_high=20.0)

    # Pied de page
    st.markdown(
        f"""
        <div class='dashboard-footer'>
            Dernière mise à jour : {datetime.now().strftime('%d %b %Y, %H:%M')}
            · Sources : yfinance, blockchain.com, CoinMetrics, bitcoin-data.com, alternative.me
            · Ce dashboard est un outil d'aide à la lecture, pas un conseil en investissement.
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
