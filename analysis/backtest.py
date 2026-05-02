"""Backtest historique du score : on rejoue le calcul jour par jour
pour visualiser comment le système se serait comporté aux moments clés.

Démarre en mai 2018 (Fear & Greed Index publié à partir de février 2018).
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from analysis import indicators as ind
from analysis import scoring as sc
from config import WEIGHTS


# Date de démarrage du backtest
BACKTEST_START = pd.Timestamp("2018-05-01")


# Dates clés du marché BTC depuis 2018 — tops et bottoms majeurs.
# On les utilise pour le tableau récapitulatif : à chaque date, quel
# score le système aurait-il donné, et était-ce la bonne lecture ?
KEY_DATES: list[dict] = [
    {"date": pd.Timestamp("2018-12-15"), "label": "Bottom du bear 2018", "kind": "bottom"},
    {"date": pd.Timestamp("2019-06-26"), "label": "Top intermédiaire 2019", "kind": "top"},
    {"date": pd.Timestamp("2020-03-13"), "label": "Crash Covid", "kind": "bottom"},
    {"date": pd.Timestamp("2021-04-14"), "label": "Top intermédiaire avr. 2021", "kind": "top"},
    {"date": pd.Timestamp("2021-07-20"), "label": "Bottom intermédiaire été 2021", "kind": "bottom"},
    {"date": pd.Timestamp("2021-11-09"), "label": "ATH cycle 2021", "kind": "top"},
    {"date": pd.Timestamp("2022-11-09"), "label": "Bottom du bear 2022 (FTX)", "kind": "bottom"},
    {"date": pd.Timestamp("2024-03-13"), "label": "ATH pré-halving 2024", "kind": "top"},
]


def _align_daily(series: pd.Series, ref_index: pd.DatetimeIndex) -> pd.Series:
    """Aligne une série sur l'index de référence (forward-fill).

    Sert quand une donnée n'est pas mise à jour tous les jours (week-ends pour DXY/Gold).
    """
    return series.reindex(ref_index, method="ffill")


def compute_historical_scores(data: dict, start: pd.Timestamp = BACKTEST_START) -> pd.DataFrame:
    """Recalcule le score agrégé pour chaque jour de l'historique.

    Retourne un DataFrame indexé par date avec :
      - btc_price : prix BTC USD
      - score : score agrégé 0-100
      - palier : "Accumuler" / "Ne rien faire" / "Vendre"
      - sub_<indicateur> : sous-scores 0-100 individuels (transparence)
    """
    btc = data["btc"]["value"] if not data["btc"].empty else pd.Series(dtype=float)
    if btc.empty:
        return pd.DataFrame()

    # On indexe tout sur l'historique BTC quotidien (filtré >= start)
    idx = btc.index[btc.index >= start]
    if len(idx) == 0:
        return pd.DataFrame()

    # --- Calcul des indicateurs sur tout l'historique --------------------
    rsi_w_full = ind.rsi_weekly(btc)
    mayer_full = ind.mayer_multiple(btc)
    ath_dist_full = ind.ath_distance(btc)

    miner_rev = data.get("miner_revenue")
    puell_full = (
        ind.puell_multiple(miner_rev["value"]) if miner_rev is not None and not miner_rev.empty
        else pd.Series(dtype=float)
    )

    # MVRV Z-Score : recalcul local depuis market cap + realized cap (couvre 2014+)
    mc = data.get("market_cap")
    rc = data.get("realized_cap")
    if mc is not None and rc is not None and not mc.empty and not rc.empty:
        mvrv_z_full = ind.mvrv_zscore_local(mc["value"], rc["value"])
    else:
        mvrv_z_full = pd.Series(dtype=float)

    # Ratio BTC/Or
    gold = data.get("gold")
    if gold is not None and not gold.empty:
        bg = ind.btc_gold_ratio(btc, gold["value"])
        bg_ratio_full = bg["ratio"]
        bg_ma200_full = bg["ratio_ma200"]
    else:
        bg_ratio_full = pd.Series(dtype=float)
        bg_ma200_full = pd.Series(dtype=float)

    # Tendance DXY (% sur 50j)
    dxy = data.get("dxy")
    dxy_trend_full = (
        ind.dxy_trend(dxy["value"]) if dxy is not None and not dxy.empty
        else pd.Series(dtype=float)
    )

    # Fear & Greed
    fng = data.get("fear_greed")
    fng_full = fng["value"] if fng is not None and not fng.empty else pd.Series(dtype=float)

    # --- Alignement quotidien ---------------------------------------------
    rsi_w_d = _align_daily(rsi_w_full, idx)
    mayer_d = _align_daily(mayer_full, idx)
    ath_dist_d = _align_daily(ath_dist_full, idx)
    puell_d = _align_daily(puell_full, idx)
    mvrv_z_d = _align_daily(mvrv_z_full, idx)
    bg_ratio_d = _align_daily(bg_ratio_full, idx)
    bg_ma200_d = _align_daily(bg_ma200_full, idx)
    dxy_trend_d = _align_daily(dxy_trend_full, idx)
    fng_d = _align_daily(fng_full, idx)
    btc_d = btc.reindex(idx)

    # --- Sous-scores vectorisés ------------------------------------------
    sub_mvrv_z = sc._piecewise_vec(mvrv_z_d.values, sc.BP_MVRV_Z)
    sub_mayer = sc._piecewise_vec(mayer_d.values, sc.BP_MAYER)
    sub_ath_dist = sc._piecewise_vec(ath_dist_d.values, sc.BP_ATH_DISTANCE)
    sub_rsi = sc._piecewise_vec(rsi_w_d.values, sc.BP_RSI_WEEKLY)
    sub_puell = sc._piecewise_vec(puell_d.values, sc.BP_PUELL)

    # BTC/Or : sous-score basé sur ratio / ratio_ma200
    bg_rel = (bg_ratio_d / bg_ma200_d).replace([np.inf, -np.inf], np.nan)
    sub_btc_gold = sc._piecewise_vec(bg_rel.values, sc.BP_BTC_GOLD)

    # DXY inversé (corrélation inverse à BTC)
    sub_dxy = sc._piecewise_vec((-dxy_trend_d).values, sc.BP_DXY_INV)

    # Fear & Greed est déjà sur 0-100, c'est directement le sous-score
    sub_fng = fng_d.fillna(50.0).values

    # --- Agrégation pondérée (avec redistribution des poids manquants) ---
    weights_keys = [
        "mvrv_z", "mayer", "ath_distance", "rsi_weekly", "puell",
        "btc_gold", "dxy", "fear_greed",
    ]
    sub_arr = np.column_stack([
        sub_mvrv_z, sub_mayer, sub_ath_dist, sub_rsi, sub_puell,
        sub_btc_gold, sub_dxy, sub_fng,
    ])
    w = np.array([WEIGHTS[k] for k in weights_keys])

    # Mask des sous-scores valides (où la donnée brute existait vraiment)
    raw_arr = np.column_stack([
        mvrv_z_d.values,
        mayer_d.values,
        ath_dist_d.values,
        rsi_w_d.values,
        puell_d.values,
        bg_rel.values,
        dxy_trend_d.values,
        fng_d.values,
    ])
    valid = ~np.isnan(raw_arr)

    # Poids effectifs (zéro pour les sous-scores invalides)
    w_eff = valid.astype(float) * w
    w_sum = w_eff.sum(axis=1, keepdims=True)
    # Eviter division par zéro
    w_sum_safe = np.where(w_sum == 0, 1.0, w_sum)

    score_agg = (sub_arr * w_eff).sum(axis=1, keepdims=True) / w_sum_safe
    score_agg = score_agg.flatten()
    score_agg = np.where(w_sum.flatten() == 0, np.nan, score_agg)

    # Palier
    def _palier(s: float) -> str:
        if np.isnan(s):
            return "—"
        if s <= 40:
            return "Accumuler"
        if s <= 70:
            return "Ne rien faire"
        return "Vendre"

    paliers = [_palier(s) for s in score_agg]

    df = pd.DataFrame({
        "btc_price": btc_d.values,
        "score": score_agg,
        "palier": paliers,
        "sub_mvrv_z": sub_mvrv_z,
        "sub_mayer": sub_mayer,
        "sub_ath_distance": sub_ath_dist,
        "sub_rsi_weekly": sub_rsi,
        "sub_puell": sub_puell,
        "sub_btc_gold": sub_btc_gold,
        "sub_dxy": sub_dxy,
        "sub_fear_greed": sub_fng,
    }, index=idx)

    return df


def extract_key_dates(history: pd.DataFrame) -> pd.DataFrame:
    """Pour chaque date clé, récupère le score et le prix BTC à ±3 jours près.

    Retourne un DataFrame prêt à afficher dans st.dataframe.
    """
    rows = []
    for kd in KEY_DATES:
        d = kd["date"]
        if d not in history.index:
            # On prend la date la plus proche (avant ou après, ±3j)
            window = history.loc[
                (history.index >= d - pd.Timedelta(days=3))
                & (history.index <= d + pd.Timedelta(days=3))
            ]
            if window.empty:
                continue
            row = window.iloc[len(window) // 2]
        else:
            row = history.loc[d]

        score = row["score"]
        palier = row["palier"]
        price = row["btc_price"]

        # Lecture juste / fausse / nuancée
        verdict = ""
        if kd["kind"] == "top":
            # On voulait être en "Vendre" (>70), au moins en haut de "Ne rien faire" (>55)
            if score >= 70:
                verdict = "✓ Bon signal de vente"
            elif score >= 55:
                verdict = "~ Signal modéré"
            else:
                verdict = "✗ Signal raté"
        else:  # bottom
            if score <= 40:
                verdict = "✓ Bon signal d'achat"
            elif score <= 50:
                verdict = "~ Signal modéré"
            else:
                verdict = "✗ Signal raté"

        rows.append({
            "Date": d.strftime("%Y-%m-%d"),
            "Évènement": kd["label"],
            "Type": "Top" if kd["kind"] == "top" else "Bottom",
            "Prix BTC": f"${price:,.0f}".replace(",", " ") if not pd.isna(price) else "—",
            "Score": f"{score:.0f}/100" if not pd.isna(score) else "—",
            "Palier du système": palier,
            "Verdict rétrospectif": verdict,
        })

    return pd.DataFrame(rows)
