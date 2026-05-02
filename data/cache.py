"""Cache local en Parquet pour éviter de tabasser les API.

Stratégie : on lit le fichier cache, si la dernière donnée date de moins
de TTL heures on renvoie tel quel ; sinon on appelle le fetcher et on
remplace le fichier. Pas d'incrémental sophistiqué — la simplicité
prime ici, les API renvoient l'historique complet en une requête.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

import pandas as pd

from config import CACHE_DIR


def _path(name: str) -> Path:
    return CACHE_DIR / f"{name}.parquet"


def load_cached(name: str) -> pd.DataFrame | None:
    p = _path(name)
    if not p.exists():
        return None
    try:
        return pd.read_parquet(p)
    except Exception:
        return None


def save_cached(name: str, df: pd.DataFrame) -> None:
    if df is None or df.empty:
        return
    p = _path(name)
    try:
        df.to_parquet(p)
    except Exception:
        pass


def is_fresh(name: str, ttl_hours: int) -> bool:
    p = _path(name)
    if not p.exists():
        return False
    age_h = (time.time() - p.stat().st_mtime) / 3600
    return age_h < ttl_hours


def fetch_with_cache(
    name: str,
    fetcher: Callable[[], pd.DataFrame],
    ttl_hours: int,
) -> pd.DataFrame:
    """Renvoie la donnée depuis le cache si fraîche, sinon ré-appelle le fetcher.

    Si le fetcher échoue mais qu'un cache existe, on renvoie le cache (mode
    dégradé) : mieux vaut une donnée d'hier qu'une page cassée.
    """
    if is_fresh(name, ttl_hours):
        cached = load_cached(name)
        if cached is not None and not cached.empty:
            return cached

    try:
        df = fetcher()
        if df is not None and not df.empty:
            save_cached(name, df)
            return df
    except Exception:
        pass

    fallback = load_cached(name)
    if fallback is not None and not fallback.empty:
        return fallback

    return pd.DataFrame()
