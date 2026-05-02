"""Sections détaillées du dashboard, organisées par catégorie."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from analysis.scoring import IndicatorScore
from config import PALETTE
from ui.charts import CHART_CONFIG, line_chart


# Couleurs des bandes critiques en arrière-plan (transparentes)
ZONE_HOT = "rgba(209, 69, 69, 0.06)"   # rouge brique transparent
ZONE_COLD = "rgba(91, 127, 184, 0.06)" # bleu acier transparent


# ---------------------------------------------------------------------------
# Petits helpers d'affichage
# ---------------------------------------------------------------------------

def _color_for_score(s: float) -> str:
    if s < 40:
        return PALETTE["success"]
    if s < 75:
        return PALETTE["warning"]
    return PALETTE["danger"]


def _badge(score: IndicatorScore) -> None:
    color = _color_for_score(score.sub_score)
    raw = f"{score.raw:.2f}" if isinstance(score.raw, (int, float)) and score.raw == score.raw else "—"
    st.markdown(
        f"""
        <div class='indicator-row'>
            <div class='indicator-score' style='color:{color};'>{score.sub_score:.0f}/100</div>
            <div class='indicator-label'>· {score.interpretation}</div>
            <div class='indicator-raw'>valeur : <b>{raw}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if score.note:
        st.caption(score.note)


def _show(fig) -> None:
    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)


# ---------------------------------------------------------------------------
# Section Technique
# ---------------------------------------------------------------------------

def render_technique(scores: dict[str, IndicatorScore], data: dict) -> None:
    st.subheader("Technique")
    st.caption(
        "Glisser-déposer pour faire défiler la timeline · molette pour zoomer · "
        "boutons 1M/6M/1A/3A/Tout pour sauter à une période · barre du bas pour scrubber · "
        "outils de dessin dans la barre d'outils pour tracer tes propres lignes de tendance · "
        "double-clic pour réinitialiser."
    )

    btc = data["btc"]["value"]
    ma50 = btc.rolling(50).mean()
    ma200 = btc.rolling(200).mean()

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**Prix BTC + moyennes mobiles** — échelle log")
        _show(line_chart(
            "BTC vs MA50, MA200",
            traces=[
                {"name": "BTC", "series": btc, "color": PALETTE["accent"], "width": 1.8},
                {"name": "MA50", "series": ma50, "color": PALETTE["info"], "dash": "dot"},
                {"name": "MA200", "series": ma200, "color": PALETTE["danger"], "dash": "dot"},
            ],
            y_log=True,
            y_format=",.0f",
            y_title="Prix (USD)",
            height=460,
        ))

        if "mayer" in scores:
            st.markdown("**Mayer Multiple** — prix divisé par sa MA200 quotidienne")
            _badge(scores["mayer"])
            mayer_series = (btc / btc.rolling(200).mean()).dropna()
            _show(line_chart(
                "Mayer Multiple",
                traces=[{"name": "Mayer", "series": mayer_series, "color": PALETTE["accent"]}],
                h_lines=[
                    {"y": 1.0, "label": "Neutre (= MA200)", "color": PALETTE["text_muted"]},
                    {"y": 2.4, "label": "Surchauffe historique", "color": "#E53935"},
                ],
                h_zones=[
                    {"y0": 2.4, "y1": 10, "color": ZONE_HOT},
                    {"y0": 0, "y1": 0.85, "color": ZONE_COLD},
                ],
                y_format=",.2f",
                y_title="Multiple",
                height=340,
            ))

    with col_b:
        if "ath_distance" in scores:
            st.markdown("**Distance à l'ATH** — où est BTC vs son plus haut historique")
            _badge(scores["ath_distance"])
            from analysis.indicators import ath_distance
            ath_d = ath_distance(btc).dropna()
            _show(line_chart(
                "Ratio prix / ATH",
                traces=[{"name": "Distance ATH", "series": ath_d, "color": PALETTE["accent"]}],
                h_lines=[
                    {"y": 1.0, "label": "Sur l'ATH", "color": PALETTE["danger"]},
                    {"y": 0.5, "label": "50% sous l'ATH", "color": PALETTE["text_muted"]},
                ],
                h_zones=[
                    {"y0": 0.92, "y1": 1.05, "color": ZONE_HOT},
                    {"y0": 0, "y1": 0.6, "color": ZONE_COLD},
                ],
                y_format=",.2f",
                y_title="Ratio",
                height=280,
            ))

        if "rsi_weekly" in scores:
            st.markdown("**RSI hebdomadaire (14)** — momentum long terme")
            _badge(scores["rsi_weekly"])
            from analysis.indicators import rsi_weekly
            rsi_w = rsi_weekly(btc)
            _show(line_chart(
                "RSI weekly",
                traces=[{"name": "RSI W", "series": rsi_w, "color": PALETTE["accent"]}],
                h_lines=[
                    {"y": 30, "label": "Sous-acheté", "color": PALETTE["success"]},
                    {"y": 70, "label": "Sur-acheté", "color": "#E53935"},
                ],
                h_zones=[
                    {"y0": 70, "y1": 100, "color": ZONE_HOT},
                    {"y0": 0, "y1": 30, "color": ZONE_COLD},
                ],
                y_format=",.1f",
                y_title="RSI",
                height=340,
            ))



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
                _show(line_chart(
                    "MVRV Z-Score",
                    traces=[{"name": "Z-Score", "series": mvrv["value"], "color": PALETTE["accent"]}],
                    h_lines=[
                        {"y": 0, "label": "Capitulation", "color": PALETTE["cold"]},
                        {"y": 7, "label": "Top historique", "color": "#E53935"},
                    ],
                    h_zones=[
                        {"y0": 7, "y1": 20, "color": ZONE_HOT},
                        {"y0": -5, "y1": 0, "color": ZONE_COLD},
                    ],
                    y_format=",.2f",
                    y_title="Z-Score",
                    height=360,
                ))

        if "puell" in scores:
            st.markdown("**Puell Multiple** — santé des mineurs")
            _badge(scores["puell"])
            from analysis.indicators import puell_multiple
            mr = data.get("miner_revenue")
            if mr is not None and not mr.empty:
                puell = puell_multiple(mr["value"]).dropna()
                _show(line_chart(
                    "Puell Multiple",
                    traces=[{"name": "Puell", "series": puell, "color": PALETTE["accent"]}],
                    h_lines=[
                        {"y": 0.5, "label": "Capitulation mineurs", "color": PALETTE["cold"]},
                        {"y": 4, "label": "Surchauffe", "color": "#E53935"},
                    ],
                    h_zones=[
                        {"y0": 4, "y1": 20, "color": ZONE_HOT},
                        {"y0": 0, "y1": 0.5, "color": ZONE_COLD},
                    ],
                    y_format=",.2f",
                    y_title="Multiple",
                    height=360,
                ))



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
                _show(line_chart(
                    "BTC/Or",
                    traces=[
                        {"name": "Ratio", "series": bg["ratio"], "color": PALETTE["accent"]},
                        {"name": "MA200", "series": bg["ratio_ma200"], "color": PALETTE["danger"], "dash": "dot"},
                    ],
                    y_format=",.0f",
                    y_title="Onces d'or",
                    height=380,
                ))

    with col_b:
        if "dxy" in scores:
            st.markdown("**DXY** — indice dollar (corrélation inverse à BTC)")
            _badge(scores["dxy"])
            dxy = data.get("dxy")
            if dxy is not None and not dxy.empty:
                _show(line_chart(
                    "DXY",
                    traces=[{"name": "DXY", "series": dxy["value"], "color": PALETTE["accent"]}],
                    y_format=",.2f",
                    y_title="Indice DXY",
                    height=380,
                ))


# ---------------------------------------------------------------------------
# Section Sentiment
# ---------------------------------------------------------------------------

def render_sentiment(scores: dict[str, IndicatorScore], data: dict) -> None:
    st.subheader("Sentiment")
    if "fear_greed" in scores:
        _badge(scores["fear_greed"])
        fng = data.get("fear_greed")
        if fng is not None and not fng.empty:
            _show(line_chart(
                "Fear & Greed Index",
                traces=[{"name": "F&G", "series": fng["value"], "color": PALETTE["accent"]}],
                h_lines=[
                    {"y": 25, "label": "Peur extrême", "color": PALETTE["cold"]},
                    {"y": 75, "label": "Avidité extrême", "color": "#E53935"},
                ],
                h_zones=[
                    {"y0": 75, "y1": 100, "color": ZONE_HOT},
                    {"y0": 0, "y1": 25, "color": ZONE_COLD},
                ],
                y_format=",.0f",
                y_title="Indice F&G",
                height=320,
            ))


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
