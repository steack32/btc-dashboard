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
class Verdict:
    """Avis tranché en trois morceaux affichables séparément."""
    intro: str           # "BTC est dans une zone d'accumulation"
    conclu: str          # "Historiquement, ce type..."
    drivers: str = ""    # "Tiré vers le bas par : ..."


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


def generate_verdict(scores: list[IndicatorScore], aggregate_score: float, palier: str) -> Verdict:
    """Avis tranché en trois morceaux : intro courte, conclusion, drivers.

    On retourne un dataclass plutôt qu'une string formattée — comme ça
    l'UI peut afficher chaque partie indépendamment, sans parsing fragile.
    """
    valid = [s for s in scores if not np.isnan(s.sub_score)]
    if not valid:
        return Verdict(intro="Données insuffisantes pour trancher", conclu="")

    extrêmes_haut = sorted([s for s in valid if s.sub_score >= 75], key=lambda s: -s.sub_score)[:3]
    extrêmes_bas = sorted([s for s in valid if s.sub_score <= 25], key=lambda s: s.sub_score)[:3]

    intro = {
        "Accumuler": "BTC est dans une zone d'accumulation",
        "Ne rien faire": "BTC est en territoire neutre à modérément haussier",
        "Vendre": "BTC est en zone de surchauffe",
    }.get(palier, "Lecture mixte")

    conclu = {
        "Accumuler": "Historiquement, ce type de configuration a marqué les meilleurs points d'entrée. Achat échelonné par tranches plutôt que tout charger d'un coup.",
        "Ne rien faire": "Pas de signal fort dans un sens ou dans l'autre. Tu restes sur tes positions, ne touche à rien — sur du long terme, agir trop souvent coûte plus que ça ne rapporte.",
        "Vendre": "Prudence. Historiquement, ce type de lecture a précédé les sommets de cycle de quelques semaines à quelques mois. C'est le moment d'envisager des prises de bénéfices partielles, pas de tout vendre d'un coup.",
    }.get(palier, "")

    parts: list[str] = []
    if extrêmes_haut:
        noms = ", ".join(s.label for s in extrêmes_haut[:2])
        parts.append(f"Tiré vers le haut par : {noms}")
    if extrêmes_bas:
        noms = ", ".join(s.label for s in extrêmes_bas[:2])
        parts.append(f"Tiré vers le bas par : {noms}")
    drivers = " · ".join(parts)

    return Verdict(intro=intro, conclu=conclu, drivers=drivers)
