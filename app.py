"""Dashboard BTC — orchestration Streamlit.

Lance avec : streamlit run app.py
"""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

from analysis import indicators as ind
from analysis import scoring as sc
from data import sources as ds
from ui.header import render_header
from ui.sections import (
    render_technique,
    render_onchain,
    render_macro,
    render_sentiment,
    render_summary_table,
)


st.set_page_config(
    page_title="BTC — Haussier ou pas ?",
    page_icon="₿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Chargement des données (cache Streamlit + cache disque par-dessus)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def load_all_data() -> dict:
    return {
        "btc": ds.fetch_btc(),
        "gold": ds.fetch_gold(),
        "dxy": ds.fetch_dxy(),
        "hash_rate": ds.fetch_hash_rate(),
        "miner_revenue": ds.fetch_miner_revenue(),
        "market_cap": ds.fetch_market_cap(),
        "supply": ds.fetch_supply(),
        "mvrv_z": ds.fetch_mvrv_zscore(),
        "realized_cap": ds.fetch_realized_cap(),
        "realized_price": ds.fetch_realized_price(),
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


# ---------------------------------------------------------------------------
# Calcul des scores
# ---------------------------------------------------------------------------

def compute_scores(data: dict) -> tuple[list[sc.IndicatorScore], dict[str, sc.IndicatorScore]]:
    scores: list[sc.IndicatorScore] = []

    btc = data["btc"]
    btc_price = btc["value"] if not btc.empty else pd.Series(dtype=float)
    last_price = _last_value_series(btc_price)

    # Technique
    if not btc_price.empty:
        rsi_w = ind.rsi_weekly(btc_price)
        scores.append(sc.score_rsi_weekly(_last_value_series(rsi_w)))

        mayer = ind.mayer_multiple(btc_price)
        scores.append(sc.score_mayer(_last_value_series(mayer)))

        pi = ind.pi_cycle(btc_price)
        last_pi = pi.dropna().iloc[-1] if not pi.dropna().empty else None
        if last_pi is not None:
            scores.append(sc.score_pi_cycle(
                bool(last_pi["signal"]), float(last_pi["ma111"]), float(last_pi["ma350x2"])
            ))

        ma200_w = ind.ma200w(btc_price)
        scores.append(sc.score_ma200w(last_price, _last_value_series(ma200_w)))

    # On-chain — MVRV Z (avec fallback local si l'API distante a renvoyé vide)
    mvrv = data.get("mvrv_z")
    if mvrv is not None and not mvrv.empty:
        scores.append(sc.score_mvrv_z(_last_value(mvrv)))
    else:
        mc = data.get("market_cap")
        rc = data.get("realized_cap")
        if mc is not None and rc is not None and not mc.empty and not rc.empty:
            z_local = ind.mvrv_zscore_local(mc["value"], rc["value"])
            scores.append(sc.score_mvrv_z(_last_value_series(z_local)))

    # Puell (calcul local fiable)
    mr = data.get("miner_revenue")
    if mr is not None and not mr.empty:
        puell = ind.puell_multiple(mr["value"])
        scores.append(sc.score_puell(_last_value_series(puell)))

    # NUPL
    mc = data.get("market_cap")
    rc = data.get("realized_cap")
    if mc is not None and rc is not None and not mc.empty and not rc.empty:
        n = ind.nupl(mc["value"], rc["value"])
        scores.append(sc.score_nupl(_last_value_series(n)))

    # Hash Ribbons
    hr = data.get("hash_rate")
    if hr is not None and not hr.empty:
        hb = ind.hash_ribbons(hr["value"])
        last_hb = hb.dropna().iloc[-1] if not hb.dropna().empty else None
        if last_hb is not None:
            scores.append(sc.score_hash_ribbons(float(last_hb["spread_pct"])))

    # Realized Price
    rp = data.get("realized_price")
    if rp is not None and not rp.empty and not np.isnan(last_price):
        scores.append(sc.score_realized_price(last_price, _last_value(rp)))

    # Macro — BTC/Gold
    gold = data.get("gold")
    if gold is not None and not gold.empty and not btc_price.empty:
        bg = ind.btc_gold_ratio(btc_price, gold["value"])
        last_bg = bg.dropna().iloc[-1] if not bg.dropna().empty else None
        if last_bg is not None:
            scores.append(sc.score_btc_gold(float(last_bg["ratio"]), float(last_bg["ratio_ma200"])))

    # DXY
    dxy = data.get("dxy")
    if dxy is not None and not dxy.empty:
        trend = ind.dxy_trend(dxy["value"])
        scores.append(sc.score_dxy(_last_value_series(trend)))

    # Sentiment — Fear & Greed
    fng = data.get("fear_greed")
    if fng is not None and not fng.empty:
        scores.append(sc.score_fear_greed(_last_value(fng)))

    by_name = {s.name: s for s in scores}
    return scores, by_name


# ---------------------------------------------------------------------------
# Layout principal
# ---------------------------------------------------------------------------

def main() -> None:
    st.markdown(
        "<h1 style='margin-bottom:0;'>Bitcoin — Haussier ou pas ?</h1>"
        "<p style='color:#999; margin-top:0;'>"
        "Lecture multi-indicateurs pour positionnement moyen-long terme."
        "</p>",
        unsafe_allow_html=True,
    )

    with st.spinner("Récupération des données..."):
        data = load_all_data()

    if data["btc"].empty:
        st.error(
            "Impossible de récupérer le prix BTC depuis yfinance. "
            "Vérifie ta connexion ou réessaie dans quelques minutes."
        )
        st.stop()

    scores_list, scores = compute_scores(data)
    agg, palier = sc.aggregate(scores_list)
    verdict = sc.generate_verdict(scores_list, agg, palier)

    # En-tête : score + verdict + cycle
    days_post = ind.days_since_last_halving()
    days_next = ind.days_until_next_halving()
    render_header(agg, palier, verdict, days_post, days_next)

    # Sections détaillées
    render_technique(scores, data)
    st.divider()
    render_onchain(scores, data)
    st.divider()
    render_macro(scores, data)
    st.divider()
    render_sentiment(scores, data)
    st.divider()
    render_summary_table(scores_list)

    # Pied de page
    st.caption(
        f"Dernière mise à jour : {datetime.now().strftime('%Y-%m-%d %H:%M')}  ·  "
        "Sources : yfinance, blockchain.com/charts, bitcoin-data.com, alternative.me  ·  "
        "Ce dashboard est un outil d'aide à la lecture, pas un conseil en investissement."
    )


if __name__ == "__main__":
    main()
