"""Calculs purs des indicateurs.

Toutes les fonctions prennent et renvoient des pd.Series indexées par
date (UTC sans tz). Aucun appel réseau ici — c'est délibérément testable
en isolation.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from config import HALVING_DATES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _as_series(df_or_series) -> pd.Series:
    if isinstance(df_or_series, pd.DataFrame):
        return df_or_series["value"]
    return df_or_series


# ---------------------------------------------------------------------------
# Technique
# ---------------------------------------------------------------------------

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """RSI de Wilder (lissage EMA)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    # Lissage de Wilder : alpha = 1/period
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def rsi_weekly(price_daily: pd.Series, period: int = 14) -> pd.Series:
    weekly = price_daily.resample("W-SUN").last().dropna()
    return rsi(weekly, period)


def ma200w(price_daily: pd.Series) -> pd.Series:
    """Moyenne 200 semaines : on resample en weekly puis MA(200)."""
    weekly = price_daily.resample("W-SUN").last().dropna()
    return weekly.rolling(200).mean()


def mayer_multiple(price_daily: pd.Series) -> pd.Series:
    """Prix / MA200 daily — la Mayer classique."""
    return price_daily / price_daily.rolling(200).mean()


def pi_cycle(price_daily: pd.Series) -> pd.DataFrame:
    """MA111 vs 2×MA350. Signal de top quand MA111 dépasse 2×MA350."""
    ma111 = price_daily.rolling(111).mean()
    ma350x2 = price_daily.rolling(350).mean() * 2
    df = pd.DataFrame({"ma111": ma111, "ma350x2": ma350x2})
    df["signal"] = (df["ma111"] > df["ma350x2"]).astype(int)
    return df


# ---------------------------------------------------------------------------
# On-chain
# ---------------------------------------------------------------------------

def puell_multiple(miner_revenue_usd: pd.Series) -> pd.Series:
    """Revenus mineurs USD / moyenne 365 jours. Calcul local fiable."""
    return miner_revenue_usd / miner_revenue_usd.rolling(365).mean()


def hash_ribbons(hash_rate: pd.Series) -> pd.DataFrame:
    """MA30 vs MA60 du hash rate. Capitulation quand MA30 < MA60."""
    ma30 = hash_rate.rolling(30).mean()
    ma60 = hash_rate.rolling(60).mean()
    df = pd.DataFrame({"ma30": ma30, "ma60": ma60})
    # Signal : positif si MA30 > MA60 (récupération), négatif sinon (capitulation)
    df["spread_pct"] = (ma30 - ma60) / ma60 * 100
    df["state"] = np.where(ma30 >= ma60, "Récupération", "Capitulation")
    return df


def nupl(market_cap: pd.Series, realized_cap: pd.Series) -> pd.Series:
    """Net Unrealized Profit/Loss = (MarketCap - RealizedCap) / MarketCap.

    Interprétation classique :
      < 0       : capitulation
      0 - 0.25  : espoir/peur
      0.25-0.5  : optimisme
      0.5-0.75  : croyance
      > 0.75    : euphorie
    """
    aligned = pd.concat([market_cap.rename("mc"), realized_cap.rename("rc")], axis=1).dropna()
    return ((aligned["mc"] - aligned["rc"]) / aligned["mc"]).rename("nupl")


def mvrv_zscore_local(market_cap: pd.Series, realized_cap: pd.Series) -> pd.Series:
    """Calcul local du Z-Score (fallback si bitcoin-data.com indisponible).

    Note : la formule canonique utilise σ cumulatif sur l'historique
    complet du market cap. On l'approche avec un expanding std, ce qui
    est cohérent avec Glassnode pour les dates récentes.
    """
    aligned = pd.concat([market_cap.rename("mc"), realized_cap.rename("rc")], axis=1).dropna()
    diff = aligned["mc"] - aligned["rc"]
    std = aligned["mc"].expanding().std()
    return (diff / std).rename("mvrv_z")


# ---------------------------------------------------------------------------
# Macro
# ---------------------------------------------------------------------------

def btc_gold_ratio(btc: pd.Series, gold: pd.Series) -> pd.DataFrame:
    """Onces d'or par BTC, plus une MA200 du ratio pour la tendance."""
    df = pd.concat([btc.rename("btc"), gold.rename("gold")], axis=1).dropna()
    df["ratio"] = df["btc"] / df["gold"]
    df["ratio_ma200"] = df["ratio"].rolling(200).mean()
    return df


def dxy_trend(dxy: pd.Series, window: int = 50) -> pd.Series:
    """Variation % du DXY sur la fenêtre — sert au scoring (corrélation inverse BTC)."""
    return (dxy / dxy.shift(window) - 1) * 100


# ---------------------------------------------------------------------------
# Cycle
# ---------------------------------------------------------------------------

def days_since_last_halving(today: date | None = None) -> int:
    if today is None:
        today = date.today()
    past = [h for h in HALVING_DATES if h <= today]
    if not past:
        return 0
    return (today - max(past)).days


def days_until_next_halving(today: date | None = None) -> int | None:
    """Renvoie None si aucun halving futur n'est connu."""
    if today is None:
        today = date.today()
    upcoming = [h for h in HALVING_DATES if h > today]
    if not upcoming:
        # Estimation grossière : ~1458 jours après le dernier (4 ans)
        last = max(HALVING_DATES)
        return max(0, (last.toordinal() + 1458 - today.toordinal()))
    return (min(upcoming) - today).days
