"""Thème global du dashboard.

Injecte le CSS custom (typographie, couleurs, cartes) et masque les
éléments Streamlit superflus (menu, footer, deploy badge).
"""
from __future__ import annotations

import streamlit as st

from config import PALETTE


def apply_theme() -> None:
    """À appeler tout en haut de app.py, juste après st.set_page_config."""
    css = f"""
    <style>
        /* Police globale */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"], .stApp {{
            font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
            color: {PALETTE['text']};
        }}

        .stApp {{
            background: {PALETTE['bg']};
        }}

        /* Bandeau orange Bitcoin en haut (div injectée séparément, pas un pseudo-élément) */
        #btc-top-bar {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(
                90deg,
                {PALETTE['accent']} 0%,
                {PALETTE['accent']} 35%,
                transparent 100%
            );
            z-index: 9999;
            pointer-events: none;
        }}

        /* On masque le chrome Streamlit (menu, footer, deploy badge).
           Sélecteurs ciblés pour éviter de cacher des <header> du contenu. */
        #MainMenu,
        footer,
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDeployButton"],
        [data-testid="stStatusWidget"] {{
            visibility: hidden !important;
            height: 0 !important;
        }}

        /* Padding du conteneur principal */
        [data-testid="stAppViewContainer"] > .main > div {{
            padding-top: 1.5rem;
            padding-bottom: 4rem;
            max-width: 1400px;
        }}

        /* Titres */
        h1 {{
            font-weight: 700 !important;
            letter-spacing: -0.025em !important;
            font-size: 1.85rem !important;
            color: {PALETTE['text']} !important;
            margin-bottom: 0.25rem !important;
        }}

        h2 {{
            font-weight: 600 !important;
            font-size: 1.25rem !important;
            color: {PALETTE['text']} !important;
            margin-top: 2.5rem !important;
            margin-bottom: 1rem !important;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid {PALETTE['border']};
            letter-spacing: -0.01em;
        }}

        h3 {{
            font-weight: 600 !important;
            font-size: 1rem !important;
            color: {PALETTE['text']} !important;
        }}

        /* Texte normal */
        p, .stMarkdown {{
            color: {PALETTE['text']};
            line-height: 1.55;
        }}

        /* Caption */
        .stCaption, [data-testid="stCaptionContainer"] {{
            color: {PALETTE['text_muted']} !important;
            font-size: 0.85rem !important;
        }}

        /* Diviseurs : on les masque, h2 a déjà sa border */
        hr, [data-testid="stDivider"] {{
            display: none;
        }}

        /* Metrics */
        [data-testid="stMetric"] {{
            background: {PALETTE['surface']};
            border: 1px solid {PALETTE['border']};
            border-radius: 10px;
            padding: 1rem 1.1rem;
        }}

        [data-testid="stMetricLabel"] {{
            color: {PALETTE['text_muted']} !important;
            font-size: 0.75rem !important;
            font-weight: 500 !important;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }}

        [data-testid="stMetricValue"] {{
            font-size: 1.6rem !important;
            font-weight: 600 !important;
            color: {PALETTE['text']} !important;
            letter-spacing: -0.02em;
        }}

        [data-testid="stMetricDelta"] {{
            font-size: 0.85rem !important;
        }}

        /* Cards custom (div.card) */
        .card {{
            background: {PALETTE['surface']};
            border: 1px solid {PALETTE['border']};
            border-radius: 12px;
            padding: 1.5rem;
            margin: 0.5rem 0 1.5rem 0;
        }}

        .card-accent {{
            border-left: 3px solid var(--accent-color, {PALETTE['accent']});
        }}

        /* Badge palier */
        .verdict-badge {{
            display: inline-block;
            padding: 0.35rem 0.9rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            border: 1px solid currentColor;
        }}

        /* Verdict hero */
        .verdict-title {{
            font-size: 2.5rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            line-height: 1.1;
            margin: 0.4rem 0 1rem 0;
        }}

        /* Logo Bitcoin dans le titre */
        .btc-logo {{
            color: {PALETTE['accent']};
            font-weight: 700;
            font-size: 1.05em;
            display: inline-block;
            transform: translateY(-0.02em);
            margin-right: 0.15em;
        }}

        /* Bordure haute orange sur le bandeau cycle */
        .cycle-bar {{
            border-left: 2px solid {PALETTE['accent']} !important;
        }}

        .verdict-text {{
            font-size: 1.02rem;
            line-height: 1.6;
            color: {PALETTE['text']};
        }}

        .verdict-drivers {{
            font-size: 0.9rem;
            color: {PALETTE['text_muted']};
            margin-top: 0.6rem;
            border-top: 1px solid {PALETTE['border']};
            padding-top: 0.7rem;
        }}

        /* Bandeau cycle */
        .cycle-bar {{
            background: {PALETTE['surface']};
            border: 1px solid {PALETTE['border']};
            border-radius: 8px;
            padding: 0.6rem 1rem;
            font-size: 0.88rem;
            color: {PALETTE['text_muted']};
            margin: 1rem 0 0.5rem 0;
        }}

        .cycle-bar strong {{
            color: {PALETTE['text']};
            font-weight: 600;
        }}

        /* Indicateur de score (badge) */
        .indicator-row {{
            display: flex;
            align-items: baseline;
            gap: 0.9rem;
            padding: 0.4rem 0 0.7rem 0;
        }}

        .indicator-score {{
            font-size: 1.6rem;
            font-weight: 600;
            letter-spacing: -0.02em;
        }}

        .indicator-label {{
            color: {PALETTE['text_muted']};
            font-size: 0.92rem;
        }}

        .indicator-raw {{
            margin-left: auto;
            color: {PALETTE['text_dim']};
            font-size: 0.85rem;
        }}

        .indicator-raw b {{
            color: {PALETTE['text']};
            font-weight: 600;
        }}

        /* Sous-titres de section */
        .section-subtitle {{
            color: {PALETTE['text_muted']};
            font-size: 0.92rem;
            margin-bottom: 0.5rem;
            line-height: 1.5;
        }}

        /* Tableau dataframe */
        [data-testid="stDataFrame"] {{
            border: 1px solid {PALETTE['border']};
            border-radius: 10px;
            overflow: hidden;
        }}

        /* Plotly mode bar : couleur de fond transparente */
        .modebar {{
            background: rgba(0,0,0,0) !important;
        }}

        /* Footer custom du dashboard */
        .dashboard-footer {{
            color: {PALETTE['text_dim']};
            font-size: 0.8rem;
            text-align: center;
            margin-top: 3rem;
            padding-top: 1.5rem;
            border-top: 1px solid {PALETTE['border']};
        }}
    </style>
    <div id="btc-top-bar"></div>
    """
    st.markdown(css, unsafe_allow_html=True)
