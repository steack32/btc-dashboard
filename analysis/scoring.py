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
    """Interpolation linéaire entre paliers (value_seuil, score). Scalaire."""
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


def _piecewise_vec(values, breakpoints: list[tuple[float, float]]):
    """Version vectorisée du piecewise — applique sur une série numpy/pandas.

    Utilisée par le backtest pour calculer un sous-score sur tout l'historique
    en une passe. np.interp fait l'interpolation linéaire et clamp aux bornes.
    """
    bps = sorted(breakpoints)
    xs = np.array([b[0] for b in bps])
    ys = np.array([b[1] for b in bps])
    arr = np.asarray(values, dtype=float)
    result = np.interp(arr, xs, ys)
    result = np.where(np.isnan(arr), 50.0, result)
    return result


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
# Breakpoints (valeur_indicateur, sous_score 0-100) — partagés entre score
# scalaire (live) et score vectorisé (backtest) pour rester cohérents.
# ---------------------------------------------------------------------------

# Note : MVRV Z et Mayer recalibrés pour le régime ETF post-2024,
# où les indicateurs restent moins extrêmes même aux sommets de cycle.
BP_MVRV_Z = [(-1, 5), (0, 18), (1, 35), (1.8, 55), (2.5, 75), (3.5, 90), (5, 100)]
BP_PUELL = [(0.3, 5), (0.5, 18), (0.8, 38), (1.2, 55), (2.0, 72), (3.0, 88), (4.5, 100)]
BP_MAYER = [(0.6, 5), (0.85, 22), (1.0, 40), (1.10, 60), (1.20, 78), (1.35, 92), (1.6, 100)]
BP_RSI_WEEKLY = [(20, 5), (30, 18), (40, 35), (50, 50), (60, 65), (70, 82), (80, 95), (90, 100)]
BP_BTC_GOLD = [(0.6, 15), (0.8, 32), (0.95, 45), (1.05, 55), (1.3, 72), (1.7, 88), (2.5, 100)]
BP_DXY_INV = [(-8, 10), (-4, 30), (-1, 45), (1, 55), (4, 70), (8, 90)]
# ATH-distance : ratio prix / plus haut historique. À 1.0 = au sommet absolu.
BP_ATH_DISTANCE = [(0.4, 5), (0.6, 18), (0.75, 35), (0.85, 55), (0.92, 75), (0.97, 90), (1.0, 100)]


# ---------------------------------------------------------------------------
# Sous-scores par indicateur (live, scalaire)
# ---------------------------------------------------------------------------

def score_mvrv_z(z: float) -> IndicatorScore:
    s = _piecewise(z, BP_MVRV_Z)
    return IndicatorScore("mvrv_z", "MVRV Z-Score", z, s, WEIGHTS["mvrv_z"], _interp_band(s))


def score_puell(p: float) -> IndicatorScore:
    s = _piecewise(p, BP_PUELL)
    return IndicatorScore("puell", "Puell Multiple", p, s, WEIGHTS["puell"], _interp_band(s))


def score_mayer(m: float) -> IndicatorScore:
    s = _piecewise(m, BP_MAYER)
    return IndicatorScore("mayer", "Mayer Multiple", m, s, WEIGHTS["mayer"], _interp_band(s))


def score_rsi_weekly(r: float) -> IndicatorScore:
    s = _piecewise(r, BP_RSI_WEEKLY)
    return IndicatorScore("rsi_weekly", "RSI hebdomadaire", r, s, WEIGHTS["rsi_weekly"], _interp_band(s))


def score_ath_distance(ratio: float) -> IndicatorScore:
    """Distance à l'ATH historique. À 1.0 = nouvel ATH."""
    s = _piecewise(ratio, BP_ATH_DISTANCE)
    pct = ratio * 100 if not np.isnan(ratio) else float("nan")
    note = (
        f"Prix à {pct:.1f}% de l'ATH historique" if not np.isnan(pct)
        else "—"
    )
    return IndicatorScore(
        "ath_distance", "Distance à l'ATH", ratio, s, WEIGHTS["ath_distance"],
        _interp_band(s), note=note,
    )


def score_btc_gold(ratio: float, ratio_ma200: float) -> IndicatorScore:
    if ratio_ma200 is None or np.isnan(ratio_ma200) or ratio_ma200 == 0:
        return IndicatorScore("btc_gold", "Ratio BTC/Or", ratio, 50, WEIGHTS["btc_gold"], "Neutre")
    rel = ratio / ratio_ma200
    s = _piecewise(rel, BP_BTC_GOLD)
    return IndicatorScore("btc_gold", "Ratio BTC/Or", ratio, s, WEIGHTS["btc_gold"], _interp_band(s),
                          note=f"BTC vaut {ratio:.0f} onces d'or")


def score_dxy(trend_pct: float) -> IndicatorScore:
    """DXY corrélé inversement à BTC : DXY qui baisse = score haussier."""
    inv = -trend_pct
    s = _piecewise(inv, BP_DXY_INV)
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
