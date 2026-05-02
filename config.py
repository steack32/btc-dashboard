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
# Distance à l'ATH ajoutée pour mieux capter les sommets en régime ETF
# (où MVRV Z et Mayer restent plus modérés qu'avant).
WEIGHTS: dict[str, float] = {
    "mvrv_z": 0.20,
    "mayer": 0.20,
    "ath_distance": 0.18,
    "rsi_weekly": 0.13,
    "puell": 0.12,
    "btc_gold": 0.07,
    "dxy": 0.05,
    "fear_greed": 0.05,
}

assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "Pondérations non normalisées"

# Paliers du verdict global (borne supérieure incluse).
# Trois catégories actionnables plutôt que cinq descriptives :
#   0-40   : zone d'accumulation (acheter par tranches)
#   40-75  : rester sur ses positions
#   75-100 : prises de bénéfices à envisager
VERDICT_BANDS: list[tuple[float, str]] = [
    (40, "Accumuler"),
    (70, "Ne rien faire"),
    (100, "Vendre"),
]

VERDICT_COLORS: dict[str, str] = {
    "Accumuler": "#2FBF71",     # vert sage
    "Ne rien faire": "#D4A044", # or désaturé
    "Vendre": "#D14545",        # rouge brique
}

# Palette globale du dashboard (sobre, finance pro)
PALETTE: dict[str, str] = {
    # Fonds
    "bg": "#0E0F11",            # fond principal
    "surface": "#16181C",       # cards
    "surface_alt": "#1A1D22",   # cards alternées
    "border": "#2A2D33",        # bordures fines
    "border_strong": "#3A3D43", # bordures appuyées
    # Texte
    "text": "#E8E9ED",          # texte primaire
    "text_muted": "#9499A0",    # texte secondaire
    "text_dim": "#5C6068",      # texte tertiaire
    # Accents
    "accent": "#F7931A",        # orange Bitcoin officiel (le vrai, du logo)
    "accent_soft": "#FFAA3D",   # variante plus claire pour hover/focus
    "info": "#5B9CFA",          # bleu fintech
    "success": "#2FBF71",       # vert sage
    "warning": "#D4A044",       # or désaturé
    "danger": "#D14545",        # rouge brique
    "cold": "#5B7FB8",          # bleu acier (capitulation)
    # Couleurs de courbes
    "series_main": "#F7931A",
    "series_alt": "#5B9CFA",
    "series_neutral": "#8B92A0",
    "series_warm": "#D14545",
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
