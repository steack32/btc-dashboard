"""Conversion de chaque indicateur en sous-score 0-100, agrégation et verdict.

Convention : 0 = très baissier (capitulation), 50 = neutre, 100 = très
haussier (surchauffe / euphorie). Le score n'est PAS un signal d'achat —
au-delà de 80 c'est une zone de prise de bénéfices, pas d'entrée.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import VERDICT_BANDS, WEIGHTS


@dataclass
class IndicatorScore:
    name: str
    label: str           # libellé affiché (français)
    raw: float           # valeur brute de l'indicateur
    sub_score: float     # 0-100
    weight: float
    interpretation: str  # mot-clé : Capitulation / Sous-évalué / Neutre / Haussier / Surchauffe
    note: str = ""       # détail optionnel pour l'avis


def _piecewise(value: float, breakpoints: list[tuple[float, float]]) -> float:
    """Interpolation linéaire entre paliers (value_seuil, score)."""
    if np.isnan(value):
        return 50.0
    bps = sorted(breakpoints)
    if value <= bps[0][0]:
        return bps[0][1]
    if value >= bps[-1][0]:
        return bps[-1][1]
    for (x1, y1), (x2, y2) in zip(bps, bps[1:]):
        if x1 <= value <= x2:
            t = (value - x1) / (x2 - x1) if x2 != x1 else 0
            return y1 + t * (y2 - y1)
    return 50.0


def _interp_band(score: float) -> str:
    if score < 20:
        return "Capitulation"
    if score < 40:
        return "Sous-évalué"
    if score < 60:
        return "Neutre"
    if score < 80:
        return "Haussier"
    return "Surchauffe"


# ---------------------------------------------------------------------------
# Sous-scores par indicateur
# ---------------------------------------------------------------------------

def score_mvrv_z(z: float) -> IndicatorScore:
    # Seuils historiques : <0 capitulation, ~3-4 zone tendue, >7 top
    s = _piecewise(z, [(-1, 5), (0, 20), (1, 40), (2.5, 55), (4, 70), (5.5, 82), (7, 95), (10, 100)])
    return IndicatorScore("mvrv_z", "MVRV Z-Score", z, s, WEIGHTS["mvrv_z"], _interp_band(s))


def score_puell(p: float) -> IndicatorScore:
    s = _piecewise(p, [(0.3, 5), (0.5, 18), (0.8, 38), (1.2, 55), (2.0, 72), (3.0, 88), (4.5, 100)])
    return IndicatorScore("puell", "Puell Multiple", p, s, WEIGHTS["puell"], _interp_band(s))


def score_mayer(m: float) -> IndicatorScore:
    # < 1 sous-évalué, 1-2.4 zone normale, > 2.4 surchauffe historique
    s = _piecewise(m, [(0.6, 5), (0.85, 25), (1.0, 45), (1.4, 60), (1.9, 75), (2.4, 88), (3.0, 100)])
    return IndicatorScore("mayer", "Mayer Multiple", m, s, WEIGHTS["mayer"], _interp_band(s))


def score_rsi_weekly(r: float) -> IndicatorScore:
    s = _piecewise(r, [(20, 5), (30, 18), (40, 35), (50, 50), (60, 65), (70, 82), (80, 95), (90, 100)])
    return IndicatorScore("rsi_weekly", "RSI hebdomadaire", r, s, WEIGHTS["rsi_weekly"], _interp_band(s))


def score_nupl(n: float) -> IndicatorScore:
    s = _piecewise(n, [(-0.25, 5), (0, 22), (0.25, 42), (0.5, 60), (0.65, 78), (0.75, 92), (0.85, 100)])
    return IndicatorScore("nupl", "NUPL", n, s, WEIGHTS["nupl"], _interp_band(s))


def score_ma200w(price: float, ma: float) -> IndicatorScore:
    """Position du prix par rapport à la MA 200 semaines."""
    if ma is None or np.isnan(ma) or ma == 0:
        return IndicatorScore("ma200w", "Prix vs MA 200 sem.", float("nan"), 50, WEIGHTS["ma200w"], "Neutre")
    ratio = price / ma
    s = _piecewise(ratio, [(0.7, 5), (0.9, 22), (1.0, 45), (1.5, 60), (2.5, 78), (4.0, 92), (6.0, 100)])
    return IndicatorScore("ma200w", "Prix vs MA 200 sem.", ratio, s, WEIGHTS["ma200w"], _interp_band(s),
                          note=f"Prix à {ratio:.2f}× la MA200W")


def score_pi_cycle(triggered: bool, ma111: float, ma350x2: float) -> IndicatorScore:
    """Pi Cycle : binaire. Déclenché = sommet probable, sinon neutre-bas."""
    if triggered:
        return IndicatorScore("pi_cycle", "Pi Cycle Top", 1, 95, WEIGHTS["pi_cycle"], "Surchauffe",
                              note="MA111 a dépassé 2×MA350 — historiquement signal de top")
    # Distance relative entre les deux MA — plus on s'en rapproche, plus on monte dans le score
    if ma350x2 and not np.isnan(ma350x2) and ma350x2 != 0:
        gap = ma111 / ma350x2
        s = _piecewise(gap, [(0.4, 15), (0.6, 30), (0.8, 50), (0.95, 70), (1.0, 92)])
    else:
        s = 50
    return IndicatorScore("pi_cycle", "Pi Cycle Top", 0, s, WEIGHTS["pi_cycle"], _interp_band(s))


def score_hash_ribbons(spread_pct: float) -> IndicatorScore:
    """Spread (MA30 - MA60)/MA60 en %. Négatif = capitulation mineurs.

    Capitulation = score bas mais c'est historiquement une opportunité —
    on garde la convention (bas = baissier) pour la cohérence du score
    agrégé, l'interprétation textuelle nuance.
    """
    s = _piecewise(spread_pct, [(-10, 8), (-5, 22), (-1, 40), (1, 55), (5, 70), (15, 88), (30, 100)])
    label = _interp_band(s)
    note = "Capitulation mineurs (historiquement zone d'achat)" if spread_pct < 0 else "Mineurs en expansion"
    return IndicatorScore("hash_ribbons", "Hash Ribbons", spread_pct, s, WEIGHTS["hash_ribbons"], label, note=note)


def score_btc_gold(ratio: float, ratio_ma200: float) -> IndicatorScore:
    if ratio_ma200 is None or np.isnan(ratio_ma200) or ratio_ma200 == 0:
        return IndicatorScore("btc_gold", "Ratio BTC/Or", ratio, 50, WEIGHTS["btc_gold"], "Neutre")
    rel = ratio / ratio_ma200
    s = _piecewise(rel, [(0.6, 15), (0.8, 32), (0.95, 45), (1.05, 55), (1.3, 72), (1.7, 88), (2.5, 100)])
    return IndicatorScore("btc_gold", "Ratio BTC/Or", ratio, s, WEIGHTS["btc_gold"], _interp_band(s),
                          note=f"BTC vaut {ratio:.0f} onces d'or")


def score_dxy(trend_pct: float) -> IndicatorScore:
    """DXY corrélé inversement à BTC : DXY qui baisse = score haussier."""
    inv = -trend_pct  # on inverse le signe
    s = _piecewise(inv, [(-8, 10), (-4, 30), (-1, 45), (1, 55), (4, 70), (8, 90)])
    return IndicatorScore("dxy", "Tendance DXY", trend_pct, s, WEIGHTS["dxy"], _interp_band(s),
                          note=f"DXY {trend_pct:+.1f}% sur 50 jours")


def score_fear_greed(v: float) -> IndicatorScore:
    s = float(v)  # F&G est déjà sur 0-100, parfait
    label = _interp_band(s)
    return IndicatorScore("fear_greed", "Fear & Greed", v, s, WEIGHTS["fear_greed"], label)


def score_realized_price(price: float, realized: float) -> IndicatorScore:
    if realized is None or np.isnan(realized) or realized == 0:
        return IndicatorScore("realized_price", "Prix vs Realized", float("nan"), 50,
                              WEIGHTS["realized_price"], "Neutre")
    rel = price / realized
    s = _piecewise(rel, [(0.7, 5), (1.0, 30), (1.5, 50), (2.5, 70), (4.0, 88), (6.0, 100)])
    return IndicatorScore("realized_price", "Prix vs Realized", rel, s, WEIGHTS["realized_price"],
                          _interp_band(s), note=f"Prix à {rel:.2f}× le Realized Price")


# ---------------------------------------------------------------------------
# Agrégation et verdict
# ---------------------------------------------------------------------------

def aggregate(scores: list[IndicatorScore]) -> tuple[float, str]:
    """Moyenne pondérée. Si un indicateur manque, son poids est redistribué."""
    valid = [s for s in scores if not np.isnan(s.sub_score)]
    if not valid:
        return 50.0, "Neutre"
    total_w = sum(s.weight for s in valid)
    if total_w == 0:
        return 50.0, "Neutre"
    agg = sum(s.sub_score * s.weight for s in valid) / total_w
    palier = _band(agg)
    return agg, palier


def _band(score: float) -> str:
    for upper, name in VERDICT_BANDS:
        if score <= upper:
            return name
    return VERDICT_BANDS[-1][1]


def generate_verdict(scores: list[IndicatorScore], aggregate_score: float, palier: str) -> str:
    """Avis tranché en 1-2 phrases. Règles fondées sur les indicateurs extrêmes.

    On regarde lesquels poussent le plus vers le haut ou le bas pour
    construire une justification, plutôt que d'énoncer un palier abstrait.
    """
    valid = [s for s in scores if not np.isnan(s.sub_score)]
    if not valid:
        return "Données insuffisantes pour trancher."

    extrêmes_haut = sorted([s for s in valid if s.sub_score >= 75], key=lambda s: -s.sub_score)[:3]
    extrêmes_bas = sorted([s for s in valid if s.sub_score <= 25], key=lambda s: s.sub_score)[:3]

    intro = {
        "Capitulation": "BTC est en zone de capitulation",
        "Baissier": "BTC reste sous pression baissière",
        "Neutre": "BTC est en territoire neutre",
        "Haussier": "BTC est clairement haussier",
        "Euphorie": "BTC est en zone d'euphorie",
    }.get(palier, "Lecture mixte")

    conclu = {
        "Capitulation": "Historiquement, ce type de configuration a marqué les plus belles opportunités d'accumulation. Achat échelonné raisonnable.",
        "Baissier": "Pas de précipitation, mieux vaut accumuler par tranches que tout charger d'un coup.",
        "Neutre": "Pas de signal fort — on attend une rupture franche dans un sens ou l'autre avant de bouger.",
        "Haussier": "Le momentum est confirmé. On reste exposé, mais on commence à préparer mentalement les zones de prises de bénéfices partielles.",
        "Euphorie": "Prudence. Historiquement, ce type de lecture a précédé les sommets de cycle de quelques semaines à quelques mois. Prises de bénéfices partielles à envisager sérieusement.",
    }.get(palier, "")

    drivers = ""
    if extrêmes_haut:
        noms = ", ".join(s.label for s in extrêmes_haut[:2])
        drivers += f" Le score est tiré vers le haut par : {noms}."
    if extrêmes_bas:
        noms = ", ".join(s.label for s in extrêmes_bas[:2])
        drivers += f" Tiré vers le bas par : {noms}."

    return f"{intro} (score {aggregate_score:.0f}/100).{drivers} {conclu}"
