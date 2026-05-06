"""En-tête du dashboard : compteur central, verdict, KPIs rapides, bandeau cycle."""
from __future__ import annotations

import math
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

from analysis.scoring import Verdict
from config import CACHE_DIR, PALETTE, VERDICT_COLORS
from ui.charts import GAUGE_CONFIG, gauge


SOURCES_TEXT = "yfinance, CoinMetrics, blockchain.com, bitcoin-data.com, alternative.me"


def _format_lag(last_data_date: date) -> str:
    lag = (date.today() - last_data_date).days
    if lag <= 0:
        return "aujourd'hui"
    if lag == 1:
        return "hier"
    return f"il y a {lag} j"


def render_meta_bar(last_data_date: date | None = None) -> None:
    """Bandeau sous le hero : date réelle des données + bouton de rafraîchissement.

    Le bouton vide à la fois le cache disque (.parquet) et le cache Streamlit
    en mémoire, puis relance l'app pour forcer un re-fetch des API.
    """
    col_meta, col_btn = st.columns([6, 1])

    with col_meta:
        if last_data_date is not None:
            date_str = last_data_date.strftime("%d %b %Y").lower()
            age_label = _format_lag(last_data_date)
            html = (
                f"<div class='dashboard-meta'>"
                f"<div><span class='live-dot'></span>"
                f"<b>Dernière donnée</b> · {date_str} ({age_label})</div>"
                f"<div><span class='sources-info' title='{SOURCES_TEXT}'>"
                f"5 sources publiques</span></div>"
                f"</div>"
            )
        else:
            html = (
                "<div class='dashboard-meta'>"
                "<div><span class='live-dot'></span>"
                "<b>Données indisponibles</b></div>"
                "</div>"
            )
        st.markdown(html, unsafe_allow_html=True)

    with col_btn:
        if st.button(
            "🔄 Rafraîchir",
            width="stretch",
            help="Vider le cache et re-télécharger les données depuis les API",
        ):
            for f in Path(CACHE_DIR).glob("*.parquet"):
                try:
                    f.unlink()
                except OSError:
                    pass
            st.cache_data.clear()
            st.rerun()


def _fmt_compact(value: float, prefix: str = "", suffix: str = "", decimals: int = 0) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    if abs(value) >= 1_000_000:
        return f"{prefix}{value/1_000_000:.{decimals}f}M{suffix}"
    if abs(value) >= 1_000:
        return f"{prefix}{value/1_000:,.{decimals}f}{suffix}".replace(",", " ")
    return f"{prefix}{value:.{decimals}f}{suffix}"


def _kpi(col, label: str, value: str, delta: str | None = None, delta_color: str | None = None) -> None:
    delta_html = ""
    if delta:
        c = delta_color or PALETTE["text_muted"]
        delta_html = f"<div style='color:{c}; font-size:0.85rem; font-weight:500; margin-top:0.15rem;'>{delta}</div>"
    col.markdown(
        f"""
        <div style='background:{PALETTE['surface']}; border:1px solid {PALETTE['border']};
                    border-radius:10px; padding:0.85rem 1rem;'>
            <div style='color:{PALETTE['text_muted']}; font-size:0.72rem; font-weight:500;
                        text-transform:uppercase; letter-spacing:0.07em; margin-bottom:0.35rem;'>
                {label}
            </div>
            <div style='font-size:1.45rem; font-weight:600; color:{PALETTE['text']};
                        letter-spacing:-0.02em; line-height:1.1;'>
                {value}
            </div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_header(
    score: float,
    palier: str,
    verdict: Verdict,
    days_since_halving: int,
    days_until_next: int | None,
    kpis: list[dict] | None = None,
) -> None:
    """Hero : titre + compteur angulaire + verdict en grand + KPIs en bas + bandeau cycle.

    kpis : liste de dicts {label, value, delta?, delta_color?}.
    """
    color = VERDICT_COLORS.get(palier, PALETTE["text_muted"])

    # Titre — ₿ en orange Bitcoin officiel comme signature visuelle.
    # HTML compact (sans indentations) pour éviter que Streamlit
    # interprète les indentations comme du code block markdown.
    title_html = (
        f"<div style='margin-bottom:1rem;'>"
        f"<h1 style='margin:0; font-weight:700; letter-spacing:-0.025em;'>"
        f"<span class='btc-logo'>₿</span>Bitcoin"
        f"<span style='color:{PALETTE['text_muted']}; font-weight:500; margin:0 0.4rem;'>·</span>"
        f"<span style='color:{PALETTE['text_muted']}; font-weight:500;'>Lecture moyen-long terme</span>"
        f"</h1>"
        f"<p style='color:{PALETTE['text_muted']}; font-size:0.95rem; margin:0.3rem 0 0 0;'>"
        f"Score multi-indicateurs et verdict actionnable, sans analyse à court terme."
        f"</p>"
        f"</div>"
    )
    st.markdown(title_html, unsafe_allow_html=True)

    # Hero principal : compteur + verdict.
    # Le style "card" est appliqué via CSS sur le premier
    # [data-testid="stHorizontalBlock"] dans le main container (voir theme.py).
    col_gauge, col_verdict = st.columns([1, 1.4], gap="large")

    with col_gauge:
        st.plotly_chart(gauge(score, color), width="stretch", config=GAUGE_CONFIG)

    with col_verdict:
        drivers_html = (
            f"<div class='verdict-drivers'>{verdict.drivers}</div>"
            if verdict.drivers else ""
        )
        verdict_html = (
            f"<div style='padding-top:1rem;'>"
            f"<span class='verdict-badge' style='color:{color};'>{palier}</span>"
            f"<div class='verdict-title' style='color:{color};'>{verdict.intro}</div>"
            f"<div class='verdict-text'>{verdict.conclu}</div>"
            f"{drivers_html}"
            f"</div>"
        )
        st.markdown(verdict_html, unsafe_allow_html=True)

    # KPIs en grille
    if kpis:
        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
        cols = st.columns(len(kpis))
        for c, k in zip(cols, kpis):
            _kpi(c, k["label"], k["value"], k.get("delta"), k.get("delta_color"))

    # Bandeau cycle : progress bar visuelle entre les deux halvings
    if days_until_next is not None and days_until_next > 0:
        total_cycle = days_since_halving + days_until_next
        pct = (days_since_halving / total_cycle * 100) if total_cycle > 0 else 0
        next_date = date.today() + timedelta(days=days_until_next)
        next_label = next_date.strftime("%b %Y").lower()
        st.markdown(
            f"<div class='cycle-progress'>"
            f"<div class='cycle-progress-header'>"
            f"<div>Cycle Bitcoin · <b>jour {days_since_halving}</b> "
            f"sur ~{total_cycle}</div>"
            f"<div><b>{pct:.0f}%</b> du cycle écoulé</div>"
            f"</div>"
            f"<div class='cycle-progress-track'>"
            f"<div class='cycle-progress-fill' style='width:{pct:.1f}%;'></div>"
            f"</div>"
            f"<div class='cycle-progress-labels'>"
            f"<span>Halving avr 2024</span>"
            f"<span>Prochain halving · {next_label}</span>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='cycle-progress'>"
            f"<div class='cycle-progress-header'>"
            f"<div>Cycle Bitcoin · <b>jour {days_since_halving}</b> "
            f"après le dernier halving</div>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
