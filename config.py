"""Constantes, pondérations et seuils du dashboard BTC."""
from __future__ import annotations

from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
CACHE_DIR = PROJECT_ROOT / ".cache"
CACHE_DIR.mkdir(exist_ok=True)

# Durée de fraîcheur du cache (heures) par catégorie
TTL_HOURS: dict[str, int] = {
    "price": 1,
    "onchain": 6,
    "macro": 6,
    "fng": 24,
}

# Pondérations du score agrégé (somme = 1.0)
WEIGHTS: dict[str, float] = {
    "mvrv_z": 0.20,
    "puell": 0.12,
    "mayer": 0.12,
    "rsi_weekly": 0.10,
    "nupl": 0.10,
    "ma200w": 0.08,
    "pi_cycle": 0.05,
    "hash_ribbons": 0.05,
    "btc_gold": 0.05,
    "dxy": 0.05,
    "fear_greed": 0.05,
    "realized_price": 0.03,
}

assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "Pondérations non normalisées"

# Paliers du verdict global (borne supérieure incluse)
VERDICT_BANDS: list[tuple[float, str]] = [
    (20, "Capitulation"),
    (40, "Baissier"),
    (60, "Neutre"),
    (80, "Haussier"),
    (100, "Euphorie"),
]

# Couleurs associées aux paliers (pour le bandeau d'en-tête)
VERDICT_COLORS: dict[str, str] = {
    "Capitulation": "#1565C0",
    "Baissier": "#90A4AE",
    "Neutre": "#9E9E9E",
    "Haussier": "#43A047",
    "Euphorie": "#E53935",
}

# Halvings Bitcoin (UTC)
HALVING_DATES: list[date] = [
    date(2012, 11, 28),
    date(2016, 7, 9),
    date(2020, 5, 11),
    date(2024, 4, 19),
]

# URLs des sources de données
URLS: dict[str, str] = {
    "blockchain_charts": "https://api.blockchain.info/charts/{chart}?timespan=all&format=json&cors=true",
    "bitcoin_data": "https://bitcoin-data.com/api/v1/{endpoint}",
    "fear_greed": "https://api.alternative.me/fng/?limit=0",
    "coinmetrics": "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics",
}

# Tickers yfinance
YF_TICKERS: dict[str, str] = {
    "btc": "BTC-USD",
    "gold": "GC=F",
    "dxy": "DX-Y.NYB",
}

# Période d'historique souhaitée pour les données prix (années)
HISTORY_YEARS = 11
