"""
tm_data.py - OHLCV loading/validation, a synthetic generator (for tests/null experiments), and a
Binance USDT-M kline fetcher.

Synthetic data is for MECHANICS TESTING and null/power experiments only. Never read performance off it.
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd
from scipy.signal import lfilter

_TIME_COLS = ("timestamp", "open_time", "time", "date", "datetime")


def validate_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    need = {"open", "high", "low", "close"}
    if not need <= set(df.columns):
        raise ValueError(f"missing columns: {sorted(need - set(df.columns))}")
    if not df.index.is_monotonic_increasing or df.index.has_duplicates:
        raise ValueError("index must be strictly increasing (sort / drop duplicates first)")
    if df[["open", "high", "low", "close"]].isna().any().any():
        raise ValueError("NaN in OHLC")
    bad = (df["high"] < df[["open", "close"]].max(axis=1) - 1e-12) | (df["low"] > df[["open", "close"]].min(axis=1) + 1e-12)
    if bad.any():
        raise ValueError(f"{int(bad.sum())} bars violate low <= min(o,c) <= max(o,c) <= high")
    dt = df.index.to_series().diff().dropna()
    if len(dt) and dt.max() > dt.median() * 1.5:
        print(f"[warn] {int((dt > dt.median() * 1.5).sum())} gaps in the index (max {dt.max()}); "
              "indicator assumes contiguous bars")
    return df


def load_ohlcv(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path) if path.endswith((".parquet", ".pq")) else pd.read_csv(path)
    df.columns = [str(c).lower() for c in df.columns]
    tcol = next((c for c in _TIME_COLS if c in df.columns), None)
    if tcol is None:
        raise ValueError(f"no time column among {_TIME_COLS}")
    t = df[tcol]
    if np.issubdtype(t.dtype, np.number):
        t = pd.to_datetime(t, unit="ms" if float(t.iloc[0]) > 1e11 else "s", utc=True)
    else:
        t = pd.to_datetime(t, utc=True)
    df = df.set_index(pd.DatetimeIndex(t, name="time")).drop(columns=[tcol]).sort_index()
    df = df[~df.index.duplicated(keep="last")]
    if "volume" not in df:
        df["volume"] = 1.0
    return validate_ohlcv(df[["open", "high", "low", "close", "volume"]].astype(float))


def synth_ohlcv(n: int = 30_000, tf_minutes: int = 60, seed: int = 7, trend_strength: float = 0.0,
                vol: float = 0.004, p0: float = 100.0) -> pd.DataFrame:
    """
    Two-state volatility regimes + optional latent AR(1) trend.
    trend_strength = 0 -> driftless (NULL: no edge exists). >0 -> planted, persistent drift of
    `trend_strength` sigma per bar (a trend-follower SHOULD find it).
    """
    rng = np.random.default_rng(seed)
    state = np.zeros(n, dtype=int)
    u = rng.random(n)
    for t in range(1, n):
        state[t] = state[t - 1] if u[t] < 0.995 else 1 - state[t - 1]
    sigma = vol * np.where(state == 1, 2.0, 0.7)
    phi = 0.97
    z = lfilter([np.sqrt(1 - phi ** 2)], [1.0, -phi], rng.standard_normal(n))
    # -sigma^2/2 makes the PRICE a martingale in simple returns (E[c_t/c_{t-1}] = 1), so a causal strategy
    # has exactly zero expected PnL under the null. Without it, longs earn a convexity drift and a
    # "null" study quietly carries a positive bias.
    r = trend_strength * sigma * z + sigma * rng.standard_normal(n) - 0.5 * sigma ** 2
    c = p0 * np.exp(np.cumsum(r))
    o = np.r_[p0, c[:-1]]
    h = np.maximum(o, c) * np.exp(np.abs(rng.normal(0, 0.5 * sigma)))
    l = np.minimum(o, c) * np.exp(-np.abs(rng.normal(0, 0.5 * sigma)))
    v = rng.lognormal(10, 0.5, n) * (1 + 5 * np.abs(r) / sigma)
    idx = pd.date_range("2022-01-01", periods=n, freq=f"{tf_minutes}min", tz="UTC", name="time")
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": v}, index=idx)


def fetch_binance_klines(symbol: str = "SOLUSDT", interval: str = "1h", start: str | None = None,
                         end: str | None = None) -> pd.DataFrame:
    """Binance USDT-M futures klines (public endpoint). Drops the still-forming last bar."""
    import json
    import urllib.parse
    import urllib.request

    base = "https://fapi.binance.com/fapi/v1/klines"
    t0 = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000) if start else None
    t1 = int(pd.Timestamp(end, tz="UTC").timestamp() * 1000) if end else None
    now_ms = int(time.time() * 1000)
    rows: list = []
    cursor = t0
    while True:
        q = {"symbol": symbol, "interval": interval, "limit": 1500}
        if cursor is not None:
            q["startTime"] = cursor
        if t1 is not None:
            q["endTime"] = t1
        with urllib.request.urlopen(f"{base}?{urllib.parse.urlencode(q)}", timeout=30) as r:
            batch = json.loads(r.read())
        if not batch:
            break
        rows += batch
        cursor = batch[-1][0] + 1
        if len(batch) < 1500:
            break
        time.sleep(0.15)
    df = pd.DataFrame(rows, columns=["open_time", "open", "high", "low", "close", "volume", "close_time",
                                     "qv", "n", "tbv", "tqv", "ig"])
    df = df[df["close_time"].astype("int64") <= now_ms]          # drop unclosed bar
    df.index = pd.to_datetime(df["open_time"].astype("int64"), unit="ms", utc=True)
    df.index.name = "time"
    df = df[["open", "high", "low", "close", "volume"]].astype(float)
    return validate_ohlcv(df[~df.index.duplicated(keep="last")])
