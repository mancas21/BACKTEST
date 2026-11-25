"""
tm_core.py - Trend Magic Enhanced (AlgoAlpha, Pine v5) -> Python.

Two engines, same I/O:

  mode="fixed"  : audited engine. Logic is line-for-line the same as trend_magic.pine (v6).
  mode="legacy" : emulates the ORIGINAL v5 script, quirks included (nz()-seeded ratchet,
                  na-CCI falls into the bearish branch, direction starts at 0). Use it only to
                  diff against a TradingView export of the original. smooth=True is NOT emulated
                  (see AUDIT.md section 3).

Causality: every value at bar t depends on bars <= t only. A flip is KNOWN AT THE CLOSE of bar t
(it uses that bar's low/high/close), so the backtester fills it at the open of bar t+1.

Dependencies: numpy, pandas.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

NAN = float("nan")
MA_TYPES = ("SMA", "EMA", "SMMA (RMA)", "WMA", "VWMA")
SRC_TYPES = ("close", "hl2", "hlc3", "ohlc4")


@dataclass(frozen=True)
class TMParams:
    cci_len: int = 20
    atr_len: int = 5
    atr_mult: float = 2.0
    src: str = "close"          # CCI source
    atr_type: str = "SMA(TR)"   # "SMA(TR)" (original) | "RMA(TR)" (Wilder)   [fixed only]
    flip_on: str = "wick"       # "wick" (original) | "close"                  [fixed only]
    smooth: bool = False        # smooth the TRIGGER line (ratchet state stays raw) [fixed only]
    ma_len: int = 14
    ma_type: str = "SMA"

    def validate(self, mode: str) -> None:
        if mode not in ("fixed", "legacy"):
            raise ValueError(f"mode must be 'fixed' or 'legacy', got {mode!r}")
        if self.cci_len < 2 or self.atr_len < 1 or self.ma_len < 1:
            raise ValueError("cci_len>=2, atr_len>=1, ma_len>=1 required")
        if not self.atr_mult > 0:
            raise ValueError("atr_mult must be > 0")
        if self.src not in SRC_TYPES:
            raise ValueError(f"src must be one of {SRC_TYPES}")
        if self.atr_type not in ("SMA(TR)", "RMA(TR)"):
            raise ValueError("atr_type must be 'SMA(TR)' or 'RMA(TR)'")
        if self.flip_on not in ("wick", "close"):
            raise ValueError("flip_on must be 'wick' or 'close'")
        if self.ma_type not in MA_TYPES:
            raise ValueError(f"ma_type must be one of {MA_TYPES}")
        if mode == "legacy":
            if self.smooth:
                raise NotImplementedError(
                    "legacy+smooth is not emulated: the original feeds the smoothed value back into "
                    "the ratchet and the window semantics of ta.* on a re-assigned variable cannot be "
                    "verified offline. Use mode='fixed'."
                )
            if self.atr_type != "SMA(TR)" or self.flip_on != "wick":
                raise ValueError("legacy mode is SMA(TR) + wick only")


# --------------------------------------------------------------------------------------
# Pine-exact primitives (NaN semantics follow Pine: a window containing na gives na)
# --------------------------------------------------------------------------------------
def _f64(x) -> np.ndarray:
    return np.asarray(x, dtype=np.float64)


def sma(x, n: int) -> np.ndarray:
    return pd.Series(_f64(x)).rolling(n, min_periods=n).mean().to_numpy()


def ema(x, n: int) -> np.ndarray:
    """ta.ema: seeded with the first non-na source value."""
    a = 2.0 / (n + 1.0)
    xs = _f64(x).tolist()
    out = [NAN] * len(xs)
    s = NAN
    for i, v in enumerate(xs):
        s = v if s != s else a * v + (1.0 - a) * s
        out[i] = s
    return np.array(out)


def rma(x, n: int) -> np.ndarray:
    """ta.rma: seeded with sma(x, n), then alpha = 1/n."""
    a = 1.0 / n
    xs = _f64(x).tolist()
    seed = sma(x, n).tolist()
    out = [NAN] * len(xs)
    s = NAN
    for i, v in enumerate(xs):
        s = seed[i] if s != s else a * v + (1.0 - a) * s
        out[i] = s
    return np.array(out)


def wma(x, n: int) -> np.ndarray:
    x = _f64(x)
    out = np.full(x.shape, np.nan)
    if len(x) >= n:
        w = np.arange(1, n + 1, dtype=np.float64)
        out[n - 1:] = sliding_window_view(x, n) @ w / w.sum()
    return out


def vwma(x, vol, n: int) -> np.ndarray:
    x, vol = _f64(x), _f64(vol)
    with np.errstate(divide="ignore", invalid="ignore"):
        return sma(x * vol, n) / sma(vol, n)


def true_range(h, l, c) -> np.ndarray:
    """ta.tr(true): first bar = high - low."""
    h, l, c = _f64(h), _f64(l), _f64(c)
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum.reduce([h - l, np.abs(h - pc), np.abs(l - pc)])
    tr[0] = h[0] - l[0]
    return tr


def cci(src, n: int) -> np.ndarray:
    """ta.cci = (src - sma) / (0.015 * mean_abs_dev). na when the window is flat (dev == 0)."""
    x = _f64(src)
    out = np.full(x.shape, np.nan)
    m = len(x) - n + 1
    if m <= 0:
        return out
    win = sliding_window_view(x, n)
    step = 50_000  # chunk to keep memory flat on long histories
    for a in range(0, m, step):
        w = win[a:a + step]
        mean = w.mean(axis=1)
        dev = np.abs(w - mean[:, None]).mean(axis=1)
        num = w[:, -1] - mean
        with np.errstate(divide="ignore", invalid="ignore"):
            v = num / (0.015 * dev)
        v[~(dev > 0.0)] = np.nan
        out[n - 1 + a: n - 1 + a + len(w)] = v
    return out


def moving_average(x, vol, n: int, kind: str) -> np.ndarray:
    if kind == "SMA":
        return sma(x, n)
    if kind == "EMA":
        return ema(x, n)
    if kind == "SMMA (RMA)":
        return rma(x, n)
    if kind == "WMA":
        return wma(x, n)
    if kind == "VWMA":
        return vwma(x, vol, n)
    raise ValueError(kind)


def _source(df: pd.DataFrame, name: str) -> np.ndarray:
    o, h, l, c = (df[k].to_numpy(np.float64) for k in ("open", "high", "low", "close"))
    return {"close": c, "hl2": (h + l) / 2, "hlc3": (h + l + c) / 3, "ohlc4": (o + h + l + c) / 4}[name]


def _cached(cache, key, fn):
    if cache is None:
        return fn()
    if key not in cache:
        cache[key] = fn()
    return cache[key]


# --------------------------------------------------------------------------------------
# Engines
# --------------------------------------------------------------------------------------
def _fixed(h, l, c, v, atr, cci_, p: TMParams):
    n = len(c)
    tu = (l - atr * p.atr_mult).tolist()
    td = (h + atr * p.atr_mult).tolist()
    atr_l, cc = atr.tolist(), cci_.tolist()

    # 1) ratchet state (raw). Regime holds when CCI is na. Seeded on the first valid bar.
    raw = [NAN] * n
    up_arr = np.zeros(n, dtype=bool)
    up, cur = True, NAN
    for t in range(n):
        cv = cc[t]
        if cv == cv:
            up = cv >= 0.0
        a = atr_l[t]
        if cur == cur:
            if a == a:
                cur = max(cur, tu[t]) if up else min(cur, td[t])
        elif a == a and cv == cv:
            cur = tu[t] if up else td[t]
        raw[t] = cur
        up_arr[t] = up
    raw = np.array(raw)

    # 2) trigger line (smoothing never touches the ratchet state)
    line = moving_average(raw, v, p.ma_len, p.ma_type) if p.smooth else raw

    # 3) direction state machine
    lo = (l if p.flip_on == "wick" else c).tolist()
    hi = (h if p.flip_on == "wick" else c).tolist()
    cl, ln = c.tolist(), line.tolist()
    dirs = np.zeros(n, dtype=np.int8)
    d = 0
    for t in range(n):
        L = ln[t]
        if L == L:
            pL = ln[t - 1] if t > 0 else NAN
            if pL != pL:  # first valid bar: initialise from price vs line
                d = 1 if cl[t] > L else (-1 if cl[t] < L else 0)
            elif lo[t] > L and lo[t - 1] <= pL:
                d = 1
            elif hi[t] < L and hi[t - 1] >= pL:
                d = -1
        dirs[t] = d

    prev = np.r_[np.int8(0), dirs[:-1]]
    sig = np.where(dirs * prev == -1, dirs, 0).astype(np.int8)  # genuine flips only (no init signal)
    return raw, line, up_arr, dirs, sig


def _legacy(h, l, c, atr, cci_, mult):
    n = len(c)
    tu = (l - atr * mult).tolist()
    td = (h + atr * mult).tolist()
    cc = cci_.tolist()
    raw = [NAN] * n
    prev = NAN
    for t in range(n):
        pv = 0.0 if prev != prev else prev              # nz(magicTrend[1])
        if cc[t] >= 0.0:                                 # na >= 0 is False -> bearish branch
            r = pv if tu[t] < pv else tu[t]
        else:
            r = pv if td[t] > pv else td[t]
        raw[t] = r
        prev = r
    raw = np.array(raw)

    lo, hi, ln = l.tolist(), h.tolist(), raw.tolist()
    dirs = np.zeros(n, dtype=np.int8)
    d = 0
    for t in range(1, n):
        L, pL = ln[t], ln[t - 1]
        if lo[t] > L and lo[t - 1] <= pL:               # ta.crossover(low, magicTrend)
            d = 1
        elif hi[t] < L and hi[t - 1] >= pL:             # ta.crossunder(high, magicTrend)
            d = -1
        dirs[t] = d

    prev_d = np.r_[np.int8(0), dirs[:-1]]
    sig = np.where((dirs > 0) & (prev_d <= 0), 1, np.where((dirs < 0) & (prev_d >= 0), -1, 0)).astype(np.int8)
    sig[0] = 0
    with np.errstate(invalid="ignore"):
        up_arr = np.where(np.isnan(cci_), False, cci_ >= 0)
    return raw, raw.copy(), up_arr, dirs, sig


def trend_magic(df: pd.DataFrame, p: TMParams | None = None, mode: str = "fixed", cache: dict | None = None) -> pd.DataFrame:
    """
    df needs open/high/low/close (+ volume for VWMA). Returns a frame aligned to df.index with:
      atr, cci, raw (ratchet state), line (trigger line), up (CCI regime), dir (+1/-1/0),
      sig (+1/-1 on the bar whose CLOSE confirms a flip), dist_atr ((close-line)/atr).
    `cache` (optional dict) memoises atr/cci across a parameter sweep on ONE dataframe - never share it
    between different dataframes.
    """
    p = p or TMParams()
    p.validate(mode)
    h, l, c = (df[k].to_numpy(np.float64) for k in ("high", "low", "close"))
    v = df["volume"].to_numpy(np.float64) if "volume" in df else np.ones(len(df))

    def _atr():
        tr = true_range(h, l, c)
        return sma(tr, p.atr_len) if p.atr_type == "SMA(TR)" else rma(tr, p.atr_len)

    atr = _cached(cache, ("atr", p.atr_type, p.atr_len), _atr)
    cci_ = _cached(cache, ("cci", p.src, p.cci_len), lambda: cci(_source(df, p.src), p.cci_len))

    if mode == "legacy":
        raw, line, up, dirs, sig = _legacy(h, l, c, atr, cci_, p.atr_mult)
    else:
        raw, line, up, dirs, sig = _fixed(h, l, c, v, atr, cci_, p)

    with np.errstate(divide="ignore", invalid="ignore"):
        dist = (c - line) / atr
    return pd.DataFrame(
        {"atr": atr, "cci": cci_, "raw": raw, "line": line, "up": up, "dir": dirs, "sig": sig, "dist_atr": dist},
        index=df.index,
    )
