"""En-tête du dashboard : compteur central, verdict, KPIs rapides, bandeau cycle."""
from __future__ import annotations

import math

import streamlit as st

from config import PALETTE, VERDICT_COLORS
from ui.charts import GAUGE_CONFIG, gauge


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
    verdict: str,
    days_since_halving: int,
    days_until_next: int | None,
    kpis: list[dict] | None = None,
) -> None:
    """Hero : titre + compteur angulaire + verdict en grand + KPIs en bas + bandeau cycle.

    kpis : liste de dicts {label, value, delta?, delta_color?}.
    """
    color = VERDICT_COLORS.get(palier, PALETTE["text_muted"])

    # Titre — ₿ en orange Bitcoin officiel comme signature visuelle
    st.markdown(
        f"""
        <div style='margin-bottom:1.5rem;'>
            <h1 style='margin:0; font-weight:700; letter-spacing:-0.025em;'>
                <span class='btc-logo'>₿</span>Bitcoin
                <span style='color:{PALETTE['text_muted']}; font-weight:500; margin:0 0.4rem;'>·</span>
                <span style='color:{PALETTE['text_muted']}; font-weight:500;'>Lecture moyen-long terme</span>
            </h1>
            <p style='color:{PALETTE['text_muted']}; font-size:0.95rem; margin:0.3rem 0 0 0;'>
                Score multi-indicateurs et verdict actionnable, sans analyse à court terme.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Hero principal : compteur + verdict
    col_gauge, col_verdict = st.columns([1, 1.4], gap="large")

    with col_gauge:
        st.plotly_chart(gauge(score, color), use_container_width=True, config=GAUGE_CONFIG)

    with col_verdict:
        # Avis tranché et drivers
        intro_part, _, rest = verdict.partition(".")
        body = (rest or "").strip()
        if body.startswith("Le score") or body.startswith(" Le score") or body.startswith("Tiré"):
            # On extrait la phrase de drivers pour l'afficher séparément
            drivers_idx = max(body.find("Le score est tiré"), body.find("Tiré vers"))
            if drivers_idx >= 0:
                conclu = body[:drivers_idx].strip()
                drivers = body[drivers_idx:].strip()
            else:
                conclu = body
                drivers = ""
        else:
            conclu = body
            drivers = ""

        st.markdown(
            f"""
            <div style='padding-top:1rem;'>
                <span class='verdict-badge' style='color:{color};'>{palier}</span>
                <div class='verdict-title' style='color:{color};'>
                    {intro_part.strip()}
                </div>
                <div class='verdict-text'>
                    {conclu}
                </div>
                {f"<div class='verdict-drivers'>{drivers}</div>" if drivers else ""}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # KPIs en grille
    if kpis:
        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
        cols = st.columns(len(kpis))
        for c, k in zip(cols, kpis):
            _kpi(c, k["label"], k["value"], k.get("delta"), k.get("delta_color"))

    # Bandeau cycle
    cycle_html = f"<strong>Jour {days_since_halving}</strong> après le dernier halving"
    if days_until_next is not None:
        cycle_html += f"  ·  prochain halving estimé dans <strong>{days_until_next} jours</strong>"
    st.markdown(f"<div class='cycle-bar'>{cycle_html}</div>", unsafe_allow_html=True)
