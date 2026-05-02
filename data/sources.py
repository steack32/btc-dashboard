"""Récupération des données depuis les API publiques.

Chaque fetcher renvoie un DataFrame indexé par date (UTC, sans tz),
avec une colonne 'value' (ou plusieurs colonnes nommées explicitement).
Toutes les fonctions sont enveloppées par fetch_with_cache.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
import requests
import yfinance as yf

from config import HISTORY_YEARS, TTL_HOURS, URLS, YF_TICKERS
from data.cache import fetch_with_cache


# ---------------------------------------------------------------------------
# yfinance — prix BTC, or, DXY
# ---------------------------------------------------------------------------

def _yf_close(ticker: str) -> pd.DataFrame:
    end = dt.date.today() + dt.timedelta(days=1)
    start = end - dt.timedelta(days=365 * HISTORY_YEARS)
    df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    out = pd.DataFrame({"value": df["Close"]})
    out.index = pd.to_datetime(out.index).tz_localize(None).normalize()
    out = out.dropna()
    return out


def fetch_btc() -> pd.DataFrame:
    return fetch_with_cache("btc_price", lambda: _yf_close(YF_TICKERS["btc"]), TTL_HOURS["price"])


def fetch_gold() -> pd.DataFrame:
    return fetch_with_cache("gold_price", lambda: _yf_close(YF_TICKERS["gold"]), TTL_HOURS["macro"])


def fetch_dxy() -> pd.DataFrame:
    return fetch_with_cache("dxy", lambda: _yf_close(YF_TICKERS["dxy"]), TTL_HOURS["macro"])


# ---------------------------------------------------------------------------
# blockchain.com /charts — hash rate, revenus mineurs, market cap, supply
# ---------------------------------------------------------------------------

def _blockchain_chart(chart: str) -> pd.DataFrame:
    url = URLS["blockchain_charts"].format(chart=chart)
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    payload = r.json().get("values", [])
    if not payload:
        return pd.DataFrame()
    df = pd.DataFrame(payload)
    df["t"] = pd.to_datetime(df["x"], unit="s").dt.tz_localize(None).dt.normalize()
    df = df.rename(columns={"y": "value"})[["t", "value"]].set_index("t").sort_index()
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna()
    return df


def fetch_hash_rate() -> pd.DataFrame:
    return fetch_with_cache("hash_rate", lambda: _blockchain_chart("hash-rate"), TTL_HOURS["onchain"])


def fetch_miner_revenue() -> pd.DataFrame:
    return fetch_with_cache(
        "miner_revenue", lambda: _blockchain_chart("miners-revenue"), TTL_HOURS["onchain"]
    )


def fetch_market_cap() -> pd.DataFrame:
    """Market cap via CoinMetrics Community (plus précis que blockchain.com)."""
    return fetch_market_cap_cm()


def fetch_supply() -> pd.DataFrame:
    return fetch_with_cache("supply", lambda: _blockchain_chart("total-bitcoins"), TTL_HOURS["onchain"])


# ---------------------------------------------------------------------------
# bitcoin-data.com — métriques on-chain pré-calculées (rate-limité)
# ---------------------------------------------------------------------------

def _bitcoin_data(endpoint: str, value_field: str) -> pd.DataFrame:
    url = URLS["bitcoin_data"].format(endpoint=endpoint)
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    payload = r.json()
    if not payload:
        return pd.DataFrame()
    df = pd.DataFrame(payload)
    if "d" in df.columns:
        df["t"] = pd.to_datetime(df["d"]).dt.tz_localize(None).dt.normalize()
    elif "unixTs" in df.columns:
        df["t"] = pd.to_datetime(df["unixTs"].astype(int), unit="s").dt.tz_localize(None).dt.normalize()
    else:
        return pd.DataFrame()
    if value_field not in df.columns:
        # Certains endpoints renvoient une seule colonne valeur sous un nom variable
        cols = [c for c in df.columns if c not in ("d", "unixTs", "t")]
        if not cols:
            return pd.DataFrame()
        value_field = cols[0]
    df = df.rename(columns={value_field: "value"})[["t", "value"]].set_index("t").sort_index()
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna()
    return df


def fetch_mvrv_zscore() -> pd.DataFrame:
    return fetch_with_cache(
        "mvrv_zscore", lambda: _bitcoin_data("mvrv-zscore", "mvrvZscore"), TTL_HOURS["onchain"]
    )


def fetch_realized_price() -> pd.DataFrame:
    return fetch_with_cache(
        "realized_price", lambda: _bitcoin_data("realized-price", "realizedPrice"), TTL_HOURS["onchain"]
    )


# ---------------------------------------------------------------------------
# CoinMetrics Community — Realized Cap dérivé (gratuit, sans rate-limit serré)
# ---------------------------------------------------------------------------

def _coinmetrics_metric(metric: str) -> pd.DataFrame:
    """Récupère une métrique BTC daily depuis CoinMetrics Community avec pagination."""
    url = URLS["coinmetrics"]
    params = {
        "assets": "btc",
        "metrics": metric,
        "frequency": "1d",
        "page_size": 10000,
    }
    out = []
    next_url = None
    while True:
        r = requests.get(next_url or url, params=None if next_url else params, timeout=30)
        if r.status_code != 200:
            break
        body = r.json()
        out.extend(body.get("data", []))
        next_url = body.get("next_page_url")
        if not next_url:
            break
    if not out:
        return pd.DataFrame()
    df = pd.DataFrame(out)
    df["t"] = pd.to_datetime(df["time"]).dt.tz_localize(None).dt.normalize()
    df["value"] = pd.to_numeric(df[metric], errors="coerce")
    df = df[["t", "value"]].set_index("t").sort_index().dropna()
    return df


def fetch_market_cap_cm() -> pd.DataFrame:
    return fetch_with_cache(
        "market_cap_cm", lambda: _coinmetrics_metric("CapMrktCurUSD"), TTL_HOURS["onchain"]
    )


def fetch_mvrv_ratio_cm() -> pd.DataFrame:
    return fetch_with_cache(
        "mvrv_ratio_cm", lambda: _coinmetrics_metric("CapMVRVCur"), TTL_HOURS["onchain"]
    )


def fetch_realized_cap() -> pd.DataFrame:
    """Realized Cap dérivé : MarketCap / MVRV ratio (égalité par définition).

    Source primaire : CoinMetrics community (gratuit, fiable). Pas de
    dépendance à bitcoin-data.com pour cette donnée critique.
    """
    def _build() -> pd.DataFrame:
        mc = fetch_market_cap_cm()
        mvrv = fetch_mvrv_ratio_cm()
        if mc.empty or mvrv.empty:
            return pd.DataFrame()
        df = pd.concat([mc["value"].rename("mc"), mvrv["value"].rename("mvrv")], axis=1).dropna()
        df = df[df["mvrv"] > 0]
        rc = (df["mc"] / df["mvrv"]).rename("value").to_frame()
        return rc

    return fetch_with_cache("realized_cap", _build, TTL_HOURS["onchain"])


# ---------------------------------------------------------------------------
# alternative.me — Fear & Greed Index
# ---------------------------------------------------------------------------

def _fear_greed_raw() -> pd.DataFrame:
    r = requests.get(URLS["fear_greed"], timeout=15)
    r.raise_for_status()
    rows = r.json().get("data", [])
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["t"] = pd.to_datetime(df["timestamp"].astype(int), unit="s").dt.tz_localize(None).dt.normalize()
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["classification"] = df["value_classification"]
    df = df[["t", "value", "classification"]].set_index("t").sort_index()
    df = df.dropna(subset=["value"])
    return df


def fetch_fear_greed() -> pd.DataFrame:
    return fetch_with_cache("fear_greed", _fear_greed_raw, TTL_HOURS["fng"])
