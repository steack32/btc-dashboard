"""Sections détaillées du dashboard, organisées par catégorie."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from analysis.scoring import IndicatorScore
from ui.charts import line_chart


# ---------------------------------------------------------------------------
# Petits helpers d'affichage
# ---------------------------------------------------------------------------

def _color_for_score(s: float) -> str:
    if s < 20:
        return "#1565C0"
    if s < 40:
        return "#90A4AE"
    if s < 60:
        return "#9E9E9E"
    if s < 80:
        return "#43A047"
    return "#E53935"


def _badge(score: IndicatorScore) -> None:
    color = _color_for_score(score.sub_score)
    raw = f"{score.raw:.2f}" if isinstance(score.raw, (int, float)) and score.raw == score.raw else "—"
    st.markdown(
        f"<div style='display:flex; gap:1rem; align-items:baseline;'>"
        f"<div style='font-size:1.5rem; font-weight:600; color:{color};'>{score.sub_score:.0f}/100</div>"
        f"<div style='color:#BBB;'>· {score.interpretation}</div>"
        f"<div style='color:#888; margin-left:auto;'>valeur : <b>{raw}</b></div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    if score.note:
        st.caption(score.note)


# ---------------------------------------------------------------------------
# Section Technique
# ---------------------------------------------------------------------------

def render_technique(scores: dict[str, IndicatorScore], data: dict) -> None:
    st.subheader("Technique")

    btc = data["btc"]["value"]
    ma50 = btc.rolling(50).mean()
    ma200 = btc.rolling(200).mean()

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**Prix BTC + moyennes mobiles (échelle log)**")
        fig = line_chart(
            "BTC vs MA50, MA200",
            traces=[
                {"name": "BTC", "series": btc, "color": "#FFB300", "width": 1.8},
                {"name": "MA50", "series": ma50, "color": "#4FC3F7", "dash": "dot"},
                {"name": "MA200", "series": ma200, "color": "#EF5350", "dash": "dot"},
            ],
            y_log=True,
            height=340,
        )
        st.plotly_chart(fig, use_container_width=True)

        if "mayer" in scores:
            st.markdown("**Mayer Multiple** (prix / MA200)")
            _badge(scores["mayer"])
            mayer_series = (btc / btc.rolling(200).mean()).dropna()
            st.plotly_chart(line_chart(
                "Mayer Multiple",
                traces=[{"name": "Mayer", "series": mayer_series, "color": "#FFB300"}],
                h_lines=[
                    {"y": 1.0, "label": "Neutre", "color": "#888"},
                    {"y": 2.4, "label": "Surchauffe", "color": "#E53935"},
                ],
                height=240,
            ), use_container_width=True)

    with col_b:
        if "rsi_weekly" in scores:
            st.markdown("**RSI hebdomadaire (14)**")
            _badge(scores["rsi_weekly"])
            from analysis.indicators import rsi_weekly
            rsi_w = rsi_weekly(btc)
            st.plotly_chart(line_chart(
                "RSI weekly",
                traces=[{"name": "RSI W", "series": rsi_w, "color": "#FFB300"}],
                h_lines=[
                    {"y": 30, "label": "Sous-acheté", "color": "#43A047"},
                    {"y": 70, "label": "Sur-acheté", "color": "#E53935"},
                ],
                height=240,
            ), use_container_width=True)

        if "pi_cycle" in scores:
            st.markdown("**Pi Cycle Top**")
            _badge(scores["pi_cycle"])
            ma111 = btc.rolling(111).mean()
            ma350x2 = btc.rolling(350).mean() * 2
            st.plotly_chart(line_chart(
                "MA111 vs 2×MA350",
                traces=[
                    {"name": "BTC", "series": btc, "color": "#FFB300", "width": 1.2},
                    {"name": "MA111", "series": ma111, "color": "#4FC3F7"},
                    {"name": "2×MA350", "series": ma350x2, "color": "#EF5350"},
                ],
                y_log=True,
                height=240,
            ), use_container_width=True)
            st.caption("Indicateur historique des sommets de cycle 2013/2017/2021. "
                       "Pertinence post-ETF non garantie — à prendre avec recul.")

    if "ma200w" in scores:
        st.markdown("**Prix vs MA 200 semaines** — support structurel historique")
        _badge(scores["ma200w"])
        weekly = btc.resample("W-SUN").last()
        ma_200w = weekly.rolling(200).mean()
        st.plotly_chart(line_chart(
            "BTC weekly vs MA200W",
            traces=[
                {"name": "BTC (W)", "series": weekly, "color": "#FFB300"},
                {"name": "MA200W", "series": ma_200w, "color": "#EF5350"},
            ],
            y_log=True,
            height=280,
        ), use_container_width=True)


# ---------------------------------------------------------------------------
# Section On-chain
# ---------------------------------------------------------------------------

def render_onchain(scores: dict[str, IndicatorScore], data: dict) -> None:
    st.subheader("On-chain")
    col_a, col_b = st.columns(2)

    with col_a:
        if "mvrv_z" in scores:
            st.markdown("**MVRV Z-Score** — sur/sous-évaluation structurelle")
            _badge(scores["mvrv_z"])
            mvrv = data.get("mvrv_z")
            if mvrv is not None and not mvrv.empty:
                st.plotly_chart(line_chart(
                    "MVRV Z-Score",
                    traces=[{"name": "Z-Score", "series": mvrv["value"], "color": "#FFB300"}],
                    h_lines=[
                        {"y": 0, "label": "Capitulation", "color": "#1565C0"},
                        {"y": 7, "label": "Top historique", "color": "#E53935"},
                    ],
                    height=260,
                ), use_container_width=True)

        if "puell" in scores:
            st.markdown("**Puell Multiple** — santé des mineurs")
            _badge(scores["puell"])
            from analysis.indicators import puell_multiple
            mr = data.get("miner_revenue")
            if mr is not None and not mr.empty:
                puell = puell_multiple(mr["value"]).dropna()
                st.plotly_chart(line_chart(
                    "Puell Multiple",
                    traces=[{"name": "Puell", "series": puell, "color": "#FFB300"}],
                    h_lines=[
                        {"y": 0.5, "label": "Capitulation", "color": "#1565C0"},
                        {"y": 4, "label": "Surchauffe", "color": "#E53935"},
                    ],
                    height=260,
                ), use_container_width=True)

    with col_b:
        if "nupl" in scores:
            st.markdown("**NUPL** — profits/pertes latentes du marché")
            _badge(scores["nupl"])
            mc = data.get("market_cap")
            rc = data.get("realized_cap")
            if mc is not None and rc is not None and not mc.empty and not rc.empty:
                from analysis.indicators import nupl
                n = nupl(mc["value"], rc["value"]).dropna()
                st.plotly_chart(line_chart(
                    "NUPL",
                    traces=[{"name": "NUPL", "series": n, "color": "#FFB300"}],
                    h_lines=[
                        {"y": 0, "label": "Pertes / profits", "color": "#888"},
                        {"y": 0.75, "label": "Euphorie", "color": "#E53935"},
                    ],
                    height=260,
                ), use_container_width=True)

        if "hash_ribbons" in scores:
            st.markdown("**Hash Ribbons** — capitulation ou expansion mineurs")
            _badge(scores["hash_ribbons"])
            hr = data.get("hash_rate")
            if hr is not None and not hr.empty:
                ma30 = hr["value"].rolling(30).mean()
                ma60 = hr["value"].rolling(60).mean()
                st.plotly_chart(line_chart(
                    "Hash rate MA30 vs MA60",
                    traces=[
                        {"name": "Hash MA30", "series": ma30, "color": "#4FC3F7"},
                        {"name": "Hash MA60", "series": ma60, "color": "#EF5350"},
                    ],
                    height=260,
                ), use_container_width=True)

    if "realized_price" in scores:
        st.markdown("**Realized Price** — prix d'achat moyen du marché")
        _badge(scores["realized_price"])
        rp = data.get("realized_price")
        btc = data["btc"]["value"]
        if rp is not None and not rp.empty:
            st.plotly_chart(line_chart(
                "Prix vs Realized Price",
                traces=[
                    {"name": "Prix BTC", "series": btc, "color": "#FFB300"},
                    {"name": "Realized Price", "series": rp["value"], "color": "#4FC3F7"},
                ],
                y_log=True,
                height=300,
            ), use_container_width=True)


# ---------------------------------------------------------------------------
# Section Macro
# ---------------------------------------------------------------------------

def render_macro(scores: dict[str, IndicatorScore], data: dict) -> None:
    st.subheader("Macro")
    col_a, col_b = st.columns(2)

    with col_a:
        if "btc_gold" in scores:
            st.markdown("**Ratio BTC / Or** — onces d'or par bitcoin")
            _badge(scores["btc_gold"])
            btc = data["btc"]["value"]
            gold = data.get("gold")
            if gold is not None and not gold.empty:
                from analysis.indicators import btc_gold_ratio
                bg = btc_gold_ratio(btc, gold["value"])
                st.plotly_chart(line_chart(
                    "BTC/Or",
                    traces=[
                        {"name": "Ratio", "series": bg["ratio"], "color": "#FFB300"},
                        {"name": "MA200", "series": bg["ratio_ma200"], "color": "#EF5350", "dash": "dot"},
                    ],
                    height=280,
                ), use_container_width=True)

    with col_b:
        if "dxy" in scores:
            st.markdown("**DXY** — indice dollar (corrélation inverse à BTC)")
            _badge(scores["dxy"])
            dxy = data.get("dxy")
            if dxy is not None and not dxy.empty:
                st.plotly_chart(line_chart(
                    "DXY",
                    traces=[{"name": "DXY", "series": dxy["value"], "color": "#FFB300"}],
                    height=280,
                ), use_container_width=True)


# ---------------------------------------------------------------------------
# Section Sentiment
# ---------------------------------------------------------------------------

def render_sentiment(scores: dict[str, IndicatorScore], data: dict) -> None:
    st.subheader("Sentiment")
    if "fear_greed" in scores:
        _badge(scores["fear_greed"])
        fng = data.get("fear_greed")
        if fng is not None and not fng.empty:
            st.plotly_chart(line_chart(
                "Fear & Greed Index",
                traces=[{"name": "F&G", "series": fng["value"], "color": "#FFB300"}],
                h_lines=[
                    {"y": 25, "label": "Peur extrême", "color": "#1565C0"},
                    {"y": 75, "label": "Avidité extrême", "color": "#E53935"},
                ],
                height=280,
            ), use_container_width=True)


# ---------------------------------------------------------------------------
# Tableau récapitulatif
# ---------------------------------------------------------------------------

def render_summary_table(scores_list: list[IndicatorScore]) -> None:
    st.subheader("Tableau récapitulatif")
    rows = []
    for s in scores_list:
        rows.append({
            "Indicateur": s.label,
            "Valeur": f"{s.raw:.3f}" if isinstance(s.raw, (int, float)) and s.raw == s.raw else "—",
            "Score (0-100)": f"{s.sub_score:.0f}",
            "Lecture": s.interpretation,
            "Poids": f"{s.weight*100:.0f}%",
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
