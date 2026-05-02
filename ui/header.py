"""En-tête du dashboard : score global + verdict tranché + bandeau cycle."""
from __future__ import annotations

import streamlit as st

from config import VERDICT_COLORS
from ui.charts import gauge


def render_header(
    score: float,
    palier: str,
    verdict: str,
    days_since_halving: int,
    days_until_next: int | None,
) -> None:
    color = VERDICT_COLORS.get(palier, "#9E9E9E")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.plotly_chart(gauge(score, color), use_container_width=True, config={"displayModeBar": False})
    with col2:
        st.markdown(
            f"<h2 style='color:{color}; margin-bottom:0.2rem;'>Verdict : {palier}</h2>",
            unsafe_allow_html=True,
        )
        st.markdown(f"<p style='font-size:1.05rem; line-height:1.55;'>{verdict}</p>",
                    unsafe_allow_html=True)

    # Bandeau contextuel cycle
    cycle_text = f"**Jour {days_since_halving} après le dernier halving**"
    if days_until_next is not None:
        cycle_text += f"  ·  prochain halving estimé dans {days_until_next} jours"
    st.markdown(cycle_text)
    st.divider()
