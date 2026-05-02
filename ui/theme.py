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

        /* Fond profond avec radial gradients diffus + pattern de grille subtil.
           Donne de la profondeur sans tomber dans le kitsch. */
        .stApp {{
            background:
                radial-gradient(ellipse 75% 38% at 0% 0%,
                    rgba(247, 147, 26, 0.07) 0%, transparent 65%),
                radial-gradient(ellipse 65% 45% at 100% 100%,
                    rgba(91, 156, 250, 0.05) 0%, transparent 65%),
                radial-gradient(ellipse 90% 60% at 50% 30%,
                    rgba(247, 147, 26, 0.025) 0%, transparent 70%),
                linear-gradient(180deg, #0E0F11 0%, #0B0C0E 100%);
            background-attachment: fixed;
        }}

        /* Pattern de grille subtil par-dessus */
        .stApp::after {{
            content: '';
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background-image:
                linear-gradient(rgba(255, 255, 255, 0.028) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255, 255, 255, 0.028) 1px, transparent 1px);
            background-size: 48px 48px;
            pointer-events: none;
            z-index: 0;
        }}

        /* Le contenu doit passer au-dessus du pattern */
        [data-testid="stAppViewContainer"] {{
            position: relative;
            z-index: 1;
        }}

        /* Hero card : on style le premier stHorizontalBlock du main container,
           qui contient la jauge à gauche et le verdict à droite. */
        [data-testid="stMainBlockContainer"]
            > div:first-child
            > [data-testid="stVerticalBlock"]
            > [data-testid="stHorizontalBlock"]:first-of-type {{
            background:
                radial-gradient(ellipse 90% 110% at 0% 50%,
                    rgba(247, 147, 26, 0.13) 0%, transparent 65%),
                linear-gradient(135deg,
                    {PALETTE['surface']} 0%,
                    {PALETTE['surface_alt']} 100%);
            border: 1px solid {PALETTE['border_strong']};
            border-radius: 16px;
            padding: 1.6rem 2rem;
            margin-bottom: 1rem;
            box-shadow:
                0 4px 16px rgba(0, 0, 0, 0.4),
                0 0 24px rgba(247, 147, 26, 0.06),
                inset 0 1px 0 rgba(247, 147, 26, 0.12);
            position: relative;
            overflow: hidden;
        }}

        /* Trait lumineux en haut de la hero card */
        [data-testid="stMainBlockContainer"]
            > div:first-child
            > [data-testid="stVerticalBlock"]
            > [data-testid="stHorizontalBlock"]:first-of-type::before {{
            content: '';
            position: absolute;
            top: 0; left: 0;
            width: 40%;
            height: 2px;
            background: linear-gradient(90deg,
                {PALETTE['accent']} 0%,
                transparent 100%);
        }}

        /* Bandeau meta : timestamp + sources (en tooltip), juste sous le hero */
        .dashboard-meta {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            padding: 0.5rem 1rem;
            background: rgba(22, 24, 28, 0.4);
            border: 1px solid {PALETTE['border']};
            border-radius: 10px;
            font-size: 0.82rem;
            color: {PALETTE['text_muted']};
            margin-bottom: 0.5rem;
            flex-wrap: wrap;
        }}
        .dashboard-meta .live-dot {{
            display: inline-block;
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: {PALETTE['accent']};
            margin-right: 0.45rem;
            box-shadow: 0 0 0 0 rgba(247, 147, 26, 0.6);
            animation: live-pulse 2.4s infinite;
            vertical-align: middle;
        }}
        @keyframes live-pulse {{
            0% {{ box-shadow: 0 0 0 0 rgba(247, 147, 26, 0.55); }}
            70% {{ box-shadow: 0 0 0 7px rgba(247, 147, 26, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(247, 147, 26, 0); }}
        }}
        .dashboard-meta b {{
            color: {PALETTE['text']};
            font-weight: 600;
        }}
        .dashboard-meta .sources-info {{
            cursor: help;
            border-bottom: 1px dotted {PALETTE['text_dim']};
            color: {PALETTE['text_muted']};
        }}
        .dashboard-meta .sources-info:hover {{
            color: {PALETTE['accent']};
            border-bottom-color: {PALETTE['accent']};
        }}

        /* Cycle progress bar : barre horizontale entre deux halvings */
        .cycle-progress {{
            background: {PALETTE['surface']};
            border: 1px solid {PALETTE['border']};
            border-left: 2px solid {PALETTE['accent']};
            border-radius: 10px;
            padding: 0.7rem 1rem;
            margin: 0.6rem 0;
        }}
        .cycle-progress-header {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            font-size: 0.82rem;
            color: {PALETTE['text_muted']};
            margin-bottom: 0.5rem;
        }}
        .cycle-progress-header b {{
            color: {PALETTE['text']};
            font-weight: 600;
        }}
        .cycle-progress-track {{
            position: relative;
            height: 6px;
            background: {PALETTE['bg']};
            border-radius: 100px;
            overflow: hidden;
        }}
        .cycle-progress-fill {{
            position: absolute;
            top: 0; left: 0; bottom: 0;
            background: linear-gradient(90deg,
                {PALETTE['accent']} 0%,
                {PALETTE['accent_soft']} 100%);
            border-radius: 100px;
            box-shadow: 0 0 8px rgba(247, 147, 26, 0.4);
        }}
        .cycle-progress-labels {{
            display: flex;
            justify-content: space-between;
            font-size: 0.72rem;
            color: {PALETTE['text_dim']};
            margin-top: 0.4rem;
        }}

        /* Navigation flottante par sections.
           position:sticky cassé par les overflow des wrappers Streamlit -> fixed. */
        .dashboard-nav {{
            position: fixed;
            top: 14px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 1000;
            display: flex;
            justify-content: center;
            gap: 0.3rem;
            padding: 0.4rem 0.5rem;
            background: rgba(14, 15, 17, 0.88);
            backdrop-filter: blur(16px) saturate(150%);
            -webkit-backdrop-filter: blur(16px) saturate(150%);
            border: 1px solid {PALETTE['border_strong']};
            border-radius: 100px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4),
                        0 0 0 1px rgba(247, 147, 26, 0.05);
            flex-wrap: wrap;
            max-width: calc(100% - 24px);
        }}
        .dashboard-nav a {{
            color: {PALETTE['text_muted']};
            text-decoration: none;
            font-size: 0.82rem;
            font-weight: 500;
            padding: 0.3rem 0.85rem;
            border-radius: 100px;
            transition: color 0.2s, background 0.2s;
        }}
        .dashboard-nav a:hover {{
            color: {PALETTE['accent']};
            background: rgba(247, 147, 26, 0.1);
        }}

        /* Compense la nav fixed : on pousse le contenu vers le bas
           pour qu'elle ne masque pas le titre. */
        [data-testid="stMainBlockContainer"] {{
            padding-top: 4rem !important;
        }}

        /* Ancres de sections : scroll-margin pour compenser la nav fixed */
        .section-anchor {{
            display: block;
            height: 0;
            scroll-margin-top: 80px;
        }}

        /* Cards subtiles autour des sections (st.container(border=True)) */
        [data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stHeading"]) {{
            background: rgba(22, 24, 28, 0.4) !important;
            border: 1px solid {PALETTE['border']} !important;
            border-radius: 14px !important;
            padding: 1.2rem 1.5rem !important;
            margin-bottom: 1rem !important;
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
            padding-top: 0.5rem;
            padding-bottom: 4rem;
            max-width: 1400px;
        }}

        /* Block container Streamlit : on rapproche le contenu du haut */
        [data-testid="stMainBlockContainer"] {{
            padding-top: 1.5rem !important;
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

        /* Scrollbar orange Bitcoin — visible en permanence */
        html {{
            overflow-y: scroll !important;  /* force la scrollbar même si le contenu tient */
        }}
        ::-webkit-scrollbar {{
            width: 10px !important;
            height: 10px !important;
        }}
        ::-webkit-scrollbar-track {{
            background: {PALETTE['bg']} !important;
        }}
        ::-webkit-scrollbar-thumb {{
            background: {PALETTE['accent']} !important;
            border-radius: 6px !important;
            border: 2px solid {PALETTE['bg']} !important;
        }}
        ::-webkit-scrollbar-thumb:hover,
        ::-webkit-scrollbar-thumb:active {{
            background: {PALETTE['accent_soft']} !important;
        }}
        ::-webkit-scrollbar-corner {{
            background: {PALETTE['bg']} !important;
        }}

        /* Firefox — orange permanent */
        html,
        body,
        * {{
            scrollbar-width: thin !important;
            scrollbar-color: {PALETTE['accent']} {PALETTE['bg']} !important;
        }}
    </style>
    <div id="btc-top-bar"></div>
    """
    st.markdown(css, unsafe_allow_html=True)
