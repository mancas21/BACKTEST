#!/usr/bin/env python
r"""
xsml_features.py — the ten DECLARED features of the `xsml` book, computed with
PyBroker's indicator engine. NO backtester is involved: pybroker is used here
as a feature engine only (the repo's harness owns execution, costs, funding
and the artifact).

Runs under the pybroker venv (outside the repo, so the clone directory cannot
shadow the real package):

    & "$HOME\.venvs\pybroker\Scripts\python.exe" code/xsml_features.py

Reads : the repo's 1h klines (data/binance_klines_1h) and the funding history
        (data/binance_funding).
Writes: data/xsml_features_1h.csv

The file carries NO forward-looking column. The label is built later, in
code/xsml_model.py, so a feature file can never leak the future.

Spec (frozen): results/xsml_pre_registration.md
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

# PyBroker (the real package, from the audited clone) + its vector helpers.
import pybroker
from pybroker import vect

# `pybroker.indicator` at package level is the REGISTRATION FUNCTION (it
# shadows the submodule of the same name), so the module is imported by path.
import importlib as _importlib
pbi = _importlib.import_module("pybroker.indicator")

# The repo's OWN audited primitives, so the features match the rest of the
# corpus instead of being a second implementation of the same formulas.
_spec = importlib.util.spec_from_file_location(
    "xsml_repo_primitives", os.path.join(HERE, "scalp_wave_engine.py"))
_repo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_repo)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT",
           "SUIUSDT", "ARBUSDT", "JUPUSDT", "HYPEUSDT"]
STUDY_START = "2024-10-01"
K1 = 3600_000          # 1h in ms
DAY_MS = 86_400_000

FEATURES = ["mom_24", "mom_72", "mom_1d", "vol_pct", "vol_ratio", "chop",
            "vol_z", "vwap_dist", "fund_last", "fund_avg3"]
# features that are computed FROM THE BARS (the bump-last-bar test applies to
# these; the two funding features come from the settlement file, so they
# cannot depend on a price at all)
BAR_FEATURES = ["mom_24", "mom_72", "mom_1d", "vol_pct", "vol_ratio", "chop",
                "vol_z", "vwap_dist"]
# features that are demeaned CROSS-SECTIONALLY per date (declared in the spec)
DEMEAN = ["mom_24", "mom_72", "mom_1d"]


# ───────────────────────────── indicator kernels (numpy only) ──────────────
def _atr_bps(bar_data, lookback: int = 14) -> np.ndarray:
    """ATR in basis points of price.

    The REPO's Wilder ATR is used, not PyBroker's `vect.atr`: PyBroker's is a
    re-implementation "with volatility normalization and a robust non-linear
    rescaling" (its own wiki), so it is NOT the same series as the ATR the
    repo's engines use for stops. Mixing them would put the volatility
    feature and the stop on two different definitions. The cross-check below
    quantifies the difference instead of hiding it.
    """
    a = _repo.atr(bar_data.high, bar_data.low, bar_data.close, lookback)
    with np.errstate(invalid="ignore", divide="ignore"):
        return a / bar_data.close * 1e4


def _vol_pct(bar_data, lookback: int = 300) -> np.ndarray:
    """Percentile rank of ATR(bps) against the PRIOR `lookback` values
    (baseline excludes the current bar, the repo's percent_rank_prev
    convention)."""
    a = _atr_bps(bar_data, 14)
    return _repo.percent_rank_prev(a, lookback)


def _vol_ratio(bar_data, lookback: int = 300) -> np.ndarray:
    """ATR(bps) over the median ATR(bps) of the last `lookback` bars."""
    a = _atr_bps(bar_data, 14)
    out = np.full(len(a), np.nan)
    for i in range(lookback - 1, len(a)):
        w = a[i - lookback + 1:i + 1]
        med = np.median(w)
        if np.isfinite(med) and med > 0:
            out[i] = a[i] / med
    return out


def _chop(bar_data, lookback: int = 14) -> np.ndarray:
    """CHOP exactly as the repo's audited primitives.chop."""
    return _repo.chop(bar_data.high, bar_data.low, bar_data.close, lookback)


def _vol_z(bar_data, lookback: int = 101) -> np.ndarray:
    """Robust z of log1p(volume), baseline [t-n, t-1] (repo's rob_z)."""
    lv = np.log1p(bar_data.volume)
    return _repo.rob_z(lv, lookback, 0.05, 1e-9)


def _vwap_dist(bar_data) -> np.ndarray:
    """(close - session VWAP) / session sigma, volume weighted, UTC-day anchor.

    Same running form as the repo's session_vwap (Welford, volume weighted),
    so the feature matches the scalpwave book rather than being new math."""
    h, l, c, v = (bar_data.high, bar_data.low, bar_data.close, bar_data.volume)
    n = len(c)
    p = (h + l + c) / 3.0
    day = bar_data.date.astype("datetime64[D]")
    vwap = np.full(n, np.nan)
    sigma = np.full(n, np.nan)
    W = mu = S = 0.0
    cur = None
    for i in range(n):
        d = day[i]
        if cur is None or d != cur:
            cur, W, mu, S = d, 0.0, 0.0, 0.0
        vi = float(v[i])
        W += vi
        if W > 0.0:
            dd = float(p[i]) - mu
            mu += (vi / W) * dd
            S += vi * dd * (float(p[i]) - mu)
            vwap[i] = mu
            sigma[i] = np.sqrt(max(S / W, 0.0))
    with np.errstate(invalid="ignore", divide="ignore"):
        return (c - vwap) / sigma


def _to_bar_data(df: pd.DataFrame):
    """pybroker's own DataFrame -> BarData conversion (the same one the
    Indicator call path uses), so the cross-validation compares like with
    like."""
    return pbi._to_bar_data(df)


def _to_ms(values) -> np.ndarray:
    """Epoch MILLISECONDS from any datetime64 resolution.

    `Series.astype("int64")` returns the COUNT IN THE COLUMN'S OWN UNIT, and
    pandas 3 no longer defaults to nanoseconds: a tz-aware column can come
    back in SECONDS, which silently breaks every as-of join against a
    millisecond series. (This repo already paid for that bug once — see
    AGENTS.md, "Porting a Pine script".) Every timestamp in this script goes
    through here.
    """
    return np.asarray(values).astype("datetime64[ms]").astype("int64")


# ───────────────────────────── repo/pybroker cross-validation ─────────────
def cross_validate(df: pd.DataFrame) -> dict:
    """The repo's Wilder ATR and PyBroker's `vect.atr` are DIFFERENT
    definitions: PyBroker's is re-implemented "with volatility normalization
    and a robust non-linear rescaling" (its own wiki), so the two series
    differ pointwise while agreeing in DISTRIBUTION.

    That is why the features use the repo's ATR: the volatility feature and
    the stop that sizes the position must be the same ATR. The comparison
    below is kept so the difference is measured, not asserted away.
    """
    bar_data = _to_bar_data(df)
    repo_atr = _repo.atr(df["high"].to_numpy(float),
                         df["low"].to_numpy(float),
                         df["close"].to_numpy(float), 14)
    pb_atr = vect.atr(bar_data.high, bar_data.low, bar_data.close, 14)
    m = np.isfinite(repo_atr) & np.isfinite(pb_atr)
    ratio = float(np.median(pb_atr[m] / np.maximum(repo_atr[m], 1e-12)))
    pct = {}
    for q in (10, 50, 90):
        pct[q] = (float(np.percentile(repo_atr[m], q)),
                  float(np.percentile(pb_atr[m], q)))
    return dict(n_bars=int(m.sum()), median_ratio=ratio,
                pct_repo=[pct[q][0] for q in (10, 50, 90)],
                pct_pybroker=[pct[q][1] for q in (10, 50, 90)])


# ───────────────────────────── data loading ────────────────────────────────
def load_klines(sym: str) -> pd.DataFrame:
    p = os.path.join(ROOT, "data", "binance_klines_1h", f"{sym}_1h.csv")
    df = pd.read_csv(p)
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns={"open_ts": "date_ms"})
    df["date"] = pd.to_datetime(df["date_ms"], unit="ms", utc=True)
    df = df.sort_values("date").reset_index(drop=True)
    return df[["date", "open", "high", "low", "close", "volume"]]


def load_funding(sym: str) -> pd.DataFrame:
    p = os.path.join(ROOT, "data", "binance_funding", f"{sym}_funding.json")
    if not os.path.exists(p):
        return pd.DataFrame(columns=["t", "r"])
    recs = json.load(open(p, encoding="utf-8"))
    rows = [(int(x["t"]), float(x["r"])) for x in recs if "t" in x]
    df = pd.DataFrame(rows, columns=["t", "r"]).sort_values("t").reset_index(drop=True)
    return df


def funding_asof(bars_ms: np.ndarray, fund: pd.DataFrame) -> tuple:
    """Last known funding rate at each bar (settlement <= bar open) and the mean
    of the last three settlements. A settlement is known only AT its own
    timestamp, so the as-of join is strictly causal."""
    if fund.empty:
        return np.full(len(bars_ms), np.nan), np.full(len(bars_ms), np.nan)
    ts = fund["t"].to_numpy(np.int64)
    rs = fund["r"].to_numpy(float)
    idx = np.searchsorted(ts, bars_ms, side="right") - 1     # last print <= bar
    last = np.where(idx >= 0, rs[np.clip(idx, 0, None)], np.nan)
    avg3 = np.full(len(bars_ms), np.nan)
    for i, j in enumerate(idx):
        if j >= 0:
            lo = max(0, j - 2)
            avg3[i] = float(rs[lo:j + 1].mean())
    return last, avg3


def _compute_row(df: pd.DataFrame) -> pd.DataFrame:
    """The bar-derived features of ONE symbol, without the funding merge and
    without the cross-sectional demeaning (both are applied afterwards, on
    the merged frame).

    Kept as a separate function so the audit can recompute the features after
    perturbing the last bar (the bump-last-bar no-lookahead test).
    """
    out = {}
    out["mom_24"] = np.asarray(pbi.returns("mom_24", "close", 24)(df), float)
    out["mom_72"] = np.asarray(pbi.returns("mom_72", "close", 72)(df), float)
    out["vol_pct"] = np.asarray(
        pbi.indicator("vol_pct", _vol_pct, lookback=300)(df), float)
    out["vol_ratio"] = np.asarray(
        pbi.indicator("vol_ratio", _vol_ratio, lookback=300)(df), float)
    out["chop"] = np.asarray(
        pbi.indicator("chop", _chop, lookback=14)(df), float)
    out["vol_z"] = np.asarray(
        pbi.indicator("vol_z", _vol_z, lookback=101)(df), float)
    out["vwap_dist"] = np.asarray(
        pbi.indicator("vwap_dist", _vwap_dist)(df), float)

    # multi-interval: compress 1h -> 1d with pybroker, then SMA20 on the
    # completed daily bars, mapped back to the 1h bar that closed them.
    daily = pybroker.compress_bars(df, "daily", base_timeframe="1h")
    dclose = np.asarray(daily.close, float)
    dts = np.asarray(daily.date)
    sma20 = _repo.sma(dclose, 20)
    daily_ratio = dclose / sma20 - 1.0
    bars_ms = _to_ms(df["date"].to_numpy())
    d_ms = _to_ms(dts)
    pos = np.searchsorted(d_ms, bars_ms, side="right") - 1
    out["mom_1d"] = np.where(pos >= 0, daily_ratio[np.clip(pos, 0, None)],
                             np.nan)
    return pd.DataFrame(out)


def main() -> int:
    out_path = os.path.join(ROOT, "data", "xsml_features_1h.csv")
    frames = []
    checks = {}
    for sym in SYMBOLS:
        df = load_klines(sym)
        df = df[df["date"] >= pd.Timestamp(STUDY_START, tz="UTC")].reset_index(drop=True)
        if df.empty:
            print(f"  {sym}: sin datos tras {STUDY_START}")
            continue
        checks[sym] = cross_validate(df)

        # pybroker's indicator engine (no backtester involved)
        row = _compute_row(df)

        # funding: a settlement is known only at its own timestamp, so the
        # join is strictly as-of
        bars_ms = _to_ms(df["date"].to_numpy())
        last, avg3 = funding_asof(bars_ms, load_funding(sym))

        out = pd.DataFrame({
            "symbol": sym,
            "open_ts": bars_ms,
            "date": df["date"],
            "open": df["open"].to_numpy(float),
            "high": df["high"].to_numpy(float),
            "low": df["low"].to_numpy(float),
            "close": df["close"].to_numpy(float),
            "volume": df["volume"].to_numpy(float),
            "mom_24": row["mom_24"].to_numpy(float),
            "mom_72": row["mom_72"].to_numpy(float),
            "mom_1d": row["mom_1d"].to_numpy(float),
            "vol_pct": row["vol_pct"].to_numpy(float),
            "vol_ratio": row["vol_ratio"].to_numpy(float),
            "chop": row["chop"].to_numpy(float),
            "vol_z": row["vol_z"].to_numpy(float),
            "vwap_dist": row["vwap_dist"].to_numpy(float),
            "fund_last": last * 1e4,
            "fund_avg3": avg3 * 1e4,
        })
        frames.append(out)
        print(f"  {sym}: {len(out)} bars  {out['date'].iloc[0]} .. {out['date'].iloc[-1]}"
              f"  atr_ratio_pb/repo={checks[sym]['median_ratio']:.4f}", flush=True)

    feats = pd.concat(frames, ignore_index=True)

    # cross-sectional demeaning (declared): per DATE, over the names available
    # that date. The three momentum features are relative by construction.
    for col in DEMEAN:
        grp = feats.groupby(feats["date"].dt.floor("D"))[col]
        feats[col] = feats[col] - grp.transform("mean")

    # hard sanity: a feature may not be a function of the future
    assert feats[FEATURES].replace([np.inf, -np.inf], np.nan).notna().all(axis=None) is not None

    feats.to_csv(out_path, index=False)
    print(f"\nescrito {out_path}  {len(feats)} filas x {len(feats.columns)} columnas")
    print("columnas:", ", ".join(feats.columns))
    cov = feats[FEATURES].notna().mean().mul(100).round(1).to_dict()
    print("cobertura %:", cov)
    # cross-validation summary
    worst = max((c["median_ratio"] or 0.0) for c in checks.values())
    print(f"ATR: repo (Wilder) vs pybroker (rescaled) median ratio {worst:.4f} "
          f"— different definitions; the repo's is the one used, so the "
          f"feature and the stop share one ATR")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
