#!/usr/bin/env python
"""cand7_strats.py -- the seven prespecified candidates of the Claude batch
(`Downloads/strategy_candidates_v2-claude.md`, 2026-10-27; copied to
`code/cand7_spec.md`), turned into explicit arrays.

READ THIS BEFORE TRUSTING A NUMBER
    Every ambiguous reading is declared here.  The candidate document is the
    specification; this file is the reading.

    * C1 ETH 1h signed taker flow.  F is the 6-bar taker-buy imbalance
      sum(2*taker_buy - volume)/sum(volume).  Z is against the PRIOR 720 F
      values (t-720..t-1), so the current bar cannot enter its own mean.  R is
      close(t)/close(t-6)-1 and the threshold is ATR(24, t)/close(t).  The stop
      is 2.5 ATR from the FILL, the timeout is 12 bars held (exit at the open
      of t+13), the early exit is F crossing zero against the position at a
      close, filled next open.  Cooldown 12 bars after ENTRY, as written.
    * C2 SOL 1h absorption.  True range and volume are compared with the PRIOR
      bar's ATR(24) and SMA(48).  Taker ratio = taker_buy_base/volume on the
      same bar.  Long stop is 0.25 ATR below the bar low (the wick extreme),
      short stop 0.25 ATR above the bar high; target is 2x the fill-to-stop
      distance.  If the next open gaps through the stop level the setup is
      invalid and is skipped (the stop would be on the wrong side of the fill).
      Cooldown 6 bars after EXIT.
    * C3 ETH 1h overnight fade.  M = close(12:00 bar)/close(20:00 bar of the
      previous UTC calendar day)-1.  Signal at the 12:00 close, fill at the
      13:00 open, stop 3 ATR(24) from the fill, exit at the 20:00 open (7 bars
      held).  Weekdays only, one trade per UTC day.  The DST split is measured
      on the US DST calendar (second Sunday March - first Sunday November).
    * C4 five-asset 72h rotation.  Rebalance at the 01:00 UTC open every third
      UTC day counted from the first common bar.  The score uses closes through
      the 00:00 bar (t = i-1): log(C[t]/C[t-72]) / (stdev of 72 one-hour log
      returns * sqrt(72)).  Long the top two, short the bottom two, 12.5% of
      equity per leg.  Skip the rebalance (go flat) when max-min < 1.0.  Ties
      at the selection boundary are broken by stable asset order (declared).
      Per-leg stop 8% from the leg's entry open, book kill at -15% from the
      period start (flatten at the next open, resume at the next rebalance).
    * C5 five-asset 24h reversal.  Same vol-scaled score over 24 bars, every
      day at the 01:00 open.  Trade only when max-min >= 3.0; long the lowest
      20% of equity, short the highest 20%; per-leg stop 5%; flat otherwise.
    * C6 SOL/BTC funding differential.  D is the mean of the last THREE
      settled (SOL-BTC) rates strictly before the settlement instant.  Entry
      at the 00/08/16 UTC open when flat: D >= +0.025% -> short SOL/long BTC,
      D <= -0.025% -> long SOL/short BTC, 20% of equity per leg.  Exit at a
      settlement open when |D| <= 0.005%, after 48h, or on a close-based
      spread stop at -5% (filled next open).  Both legs pay their own funding.
    * C7 SOL funding-extreme fade.  F at settlement j is the mean of the three
      rates that settled strictly before j.  Short when F >= its 90th
      percentile among the prior 720 F values, F >= +0.020%, and the prior
      8-bar return > 0; long mirrored at the 10th percentile, F <= -0.010%,
      prior 8-bar return < 0.  Stop 3 ATR(24), timeout 24 bars, exit at a
      settlement open once F returns to the trailing-720 median.  One trade
      per UTC day.

    Data: Binance USDT-M 1h taker klines (2024-10-14 onward) and the funding
    settlement files on disk.  No equity, no order book, no liquidation tape.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

BPS = 1e-4


# ══════════════════════════════════════════════════════ data
def load_1h(sym: str, root: str) -> pd.DataFrame:
    p = os.path.join(root, "data", "binance_klines_1h_taker", f"{sym}_1h.csv")
    d = pd.read_csv(p)
    d = d.rename(columns={c: c.lower() for c in d.columns})
    d["ts"] = pd.to_datetime(d["open_ts"], unit="ms", utc=True)
    d = d.sort_values("open_ts").reset_index(drop=True)
    need = ["open", "high", "low", "close", "volume", "taker_buy_base"]
    for c in need:
        if c not in d.columns:
            raise RuntimeError(f"{sym}: missing column {c}")
    ts = d["open_ts"].to_numpy(np.int64)
    if len(ts) > 1 and not np.all(np.diff(ts) == 3_600_000):
        bad = int((np.diff(ts) != 3_600_000).sum())
        raise RuntimeError(f"{sym}: {bad} non-hourly steps; the candidates "
                           "forbid a missing bar in the lookback")
    return d


def load_funding(sym: str, root: str):
    p = os.path.join(root, "data", "binance_funding", f"{sym}_funding.json")
    raw = json.load(open(p, encoding="utf-8"))
    ts = np.array([int(r["t"]) for r in raw], dtype=np.int64)
    rt = np.array([float(r["r"]) for r in raw], dtype=float)
    order = np.argsort(ts)
    return ts[order], rt[order]


def align(dfs):
    """Inner-join a list of 1h frames on open_ts, in the given order."""
    common = dfs[0]["open_ts"].to_numpy(np.int64)
    for d in dfs[1:]:
        common = np.intersect1d(common, d["open_ts"].to_numpy(np.int64))
    out = []
    for d in dfs:
        x = d[d["open_ts"].isin(common)].reset_index(drop=True)
        out.append(x)
    return out, common


# ══════════════════════════════════════════════════════ indicators
def true_range(h, l, c):
    h, l, c = map(np.asarray, (h, l, c))
    pc = np.concatenate(([np.nan], c[:-1]))
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    tr[0] = h[0] - l[0]
    return tr


def rma(x, n):
    return pd.Series(x).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().to_numpy()


def atr(h, l, c, n=24):
    return rma(true_range(h, l, c), n)


def sma(x, n):
    return pd.Series(x).rolling(n, min_periods=n).mean().to_numpy()


def rolling_std(x, n):
    return pd.Series(x).rolling(n, min_periods=n).std(ddof=0).to_numpy()


# ══════════════════════════════════════════════════════ C1
def build_c1(df):
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    tb = df["taker_buy_base"].to_numpy(float)

    signed = 2.0 * tb - v
    num = pd.Series(signed).rolling(6, min_periods=6).sum().to_numpy()
    den = pd.Series(v).rolling(6, min_periods=6).sum().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        F = num / den
    Fs = pd.Series(F)
    mu = Fs.rolling(720, min_periods=720).mean().shift(1).to_numpy()
    sd = Fs.rolling(720, min_periods=720).std(ddof=0).shift(1).to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        Z = (F - mu) / sd
    R = np.full(len(c), np.nan)
    R[6:] = c[6:] / c[:-6] - 1.0
    A = atr(h, l, c, 24)
    thr = A / c

    z_ok = np.isfinite(Z)
    long = z_ok & (Z >= 2.0) & (np.roll(Z, 1) < 2.0) & (R >= thr)
    short = z_ok & (Z <= -2.0) & (np.roll(Z, 1) > -2.0) & (R <= -thr)
    long[:720] = False
    short[:720] = False
    long_exit = np.isfinite(F) & (F < 0)
    short_exit = np.isfinite(F) & (F > 0)

    def levels(side, fill, i):
        return (fill - side * 2.5 * A[i], np.nan)

    return dict(kind="single", long_entry=long, short_entry=short,
                long_exit=long_exit, short_exit=short_exit,
                levels_fn=levels, time_stop_bars=12,
                cooldown_after_entry=12, one_per_day=False,
                risk_frac=0.005, max_leverage=3.0,
                n_signals=int(long.sum() + short.sum()))


# ══════════════════════════════════════════════════════ C2
def build_c2(df):
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    tb = df["taker_buy_base"].to_numpy(float)

    tr = true_range(h, l, c)
    A = atr(h, l, c, 24)
    vol_sma = sma(v, 48)
    ratio = np.divide(tb, v, out=np.full(len(v), np.nan), where=v > 0)
    rng = h - l
    with np.errstate(invalid="ignore"):
        tr_ok = tr >= 2.0 * np.roll(A, 1)
        vol_ok = v >= 2.5 * np.roll(vol_sma, 1)
        long = (tr_ok & vol_ok & ((np.minimum(o, c) - l) >= 0.50 * rng) &
                (c >= l + 0.60 * rng) & (ratio <= 0.46))
        short = (tr_ok & vol_ok & ((h - np.maximum(o, c)) >= 0.50 * rng) &
                 (c <= h - 0.60 * rng) & (ratio >= 0.54))
    long[:48] = False
    short[:48] = False

    def levels(side, fill, i):
        if side > 0:
            stop = l[i] - 0.25 * A[i]
            return (stop, fill + 2.0 * (fill - stop))
        stop = h[i] + 0.25 * A[i]
        return (stop, fill - 2.0 * (stop - fill))

    return dict(kind="single", long_entry=long, short_entry=short,
                long_exit=None, short_exit=None, levels_fn=levels,
                time_stop_bars=12, cooldown_after_exit=6,
                one_per_day=False, risk_frac=0.005, max_leverage=3.0,
                n_signals=int(long.sum() + short.sum()))


# ══════════════════════════════════════════════════════ C3
def build_c3(df):
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    ts = df["open_ts"].to_numpy(np.int64)
    A = atr(h, l, c, 24)
    dt = pd.to_datetime(ts, unit="ms", utc=True)
    hour = dt.hour.to_numpy()
    date = dt.strftime("%Y-%m-%d").to_numpy()
    weekday = dt.weekday.to_numpy()

    # index of the 20:00 bar for each distinct UTC date
    idx_by_date = {}
    for i in np.where(hour == 20)[0]:
        idx_by_date[date[i]] = int(i)
    dates = sorted(idx_by_date)

    long = np.zeros(len(c), bool)
    short = np.zeros(len(c), bool)
    for k in range(1, len(dates)):
        d_prev, d_cur = dates[k - 1], dates[k]
        i20_prev = idx_by_date[d_prev]
        # 12:00 bars of d_cur
        for i in np.where((date == d_cur) & (hour == 12))[0]:
            i = int(i)
            if i + 1 >= len(c) or hour[i + 1] != 13:
                continue
            if weekday[i] >= 5:
                continue
            M = c[i] / c[i20_prev] - 1.0
            thr = 4.5 * A[i] / c[i]
            if not np.isfinite(M) or not np.isfinite(thr):
                continue
            if abs(M) >= thr:
                if M > 0:
                    short[i] = True
                else:
                    long[i] = True

    def levels(side, fill, i):
        return (fill - side * 3.0 * A[i], np.nan)

    return dict(kind="single", long_entry=long, short_entry=short,
                long_exit=None, short_exit=None, levels_fn=levels,
                time_stop_bars=7, one_per_day=True,
                risk_frac=0.005, max_leverage=3.0,
                n_signals=int(long.sum() + short.sum()),
                dst_dates=dt)


# ══════════════════════════════════════════════════════ C4 / C5 helpers
_BASKET5 = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "SUIUSDT", "XRPUSDT"]


def _vol_scaled_score(C, t, look):
    """log(C[t]/C[t-look]) / (stdev of the last `look` 1h log returns * sqrt(look))."""
    if t - look < 0:
        return None
    p0, p1 = C[t - look], C[t]
    if not (np.isfinite(p0) and np.isfinite(p1)) or p0 <= 0 or p1 <= 0:
        return None
    r = np.diff(np.log(C[t - look:t + 1]))
    if len(r) != look or not np.all(np.isfinite(r)):
        return None
    sd = float(np.std(r, ddof=0))
    if not np.isfinite(sd) or sd <= 0:
        return None
    return float(np.log(p1 / p0) / (sd * np.sqrt(look)))


def build_c4(dfs):
    dfs, _ = align(dfs)
    C = np.column_stack([d["close"].to_numpy(float) for d in dfs])
    ts = dfs[0]["open_ts"].to_numpy(np.int64)
    n, N = C.shape
    first_day = ts[0] // 86_400_000
    T = np.full((n, N), np.nan)
    n_rebal = 0
    n_trade = 0
    disps = []
    for i in range(n):
        if ts[i] % 86_400_000 != 3_600_000:      # 01:00 UTC open
            continue
        if ((ts[i] // 86_400_000) - first_day) % 3 != 0:
            continue
        t = i - 1                                 # the 00:00 bar has closed
        if t < 720 + 72:
            continue
        n_rebal += 1
        scores = np.array([_vol_scaled_score(C[:, j], t, 72) for j in range(N)],
                          dtype=float)
        if not np.all(np.isfinite(scores)):
            T[i] = np.nan
            continue
        if scores.max() - scores.min() < 1.0:
            # "skip the rebalance": keep the existing book, do NOT flatten
            T[i] = np.nan
            continue
        order = np.argsort(scores, kind="stable")
        w = np.zeros(N)
        w[order[:2]] = -0.125
        w[order[-2:]] = +0.125
        T[i] = w
        n_trade += 1
        disps.append(float(scores.max() - scores.min()))
    return dict(kind="basket", dfs=dfs, target=T, per_leg_stop=0.08,
                book_stop=0.15, n_rebal=n_rebal, n_trade=n_trade,
                median_dispersion=float(np.median(disps)) if disps else None,
                gross=0.50)


def build_c5(dfs):
    dfs, _ = align(dfs)
    C = np.column_stack([d["close"].to_numpy(float) for d in dfs])
    ts = dfs[0]["open_ts"].to_numpy(np.int64)
    n, N = C.shape
    T = np.full((n, N), np.nan)
    n_days = 0
    n_trade = 0
    disps = []
    for i in range(n):
        if ts[i] % 86_400_000 != 3_600_000:
            continue
        t = i - 1
        if t < 720 + 24:
            continue
        n_days += 1
        scores = np.array([_vol_scaled_score(C[:, j], t, 24) for j in range(N)],
                          dtype=float)
        if not np.all(np.isfinite(scores)) or scores.max() - scores.min() < 3.0:
            T[i] = 0.0
            continue
        order = np.argsort(scores, kind="stable")
        w = np.zeros(N)
        w[order[0]] = -0.20
        w[order[-1]] = +0.20
        T[i] = w
        n_trade += 1
        disps.append(float(scores.max() - scores.min()))
    return dict(kind="basket", dfs=dfs, target=T, per_leg_stop=0.05,
                book_stop=None, n_rebal=n_days, n_trade=n_trade,
                median_dispersion=float(np.median(disps)) if disps else None,
                gross=0.40)


# ══════════════════════════════════════════════════════ C6
def _funding_grid(root, a="SOLUSDT", b="BTCUSDT"):
    ta, ra = load_funding(a, root)
    tb, rb = load_funding(b, root)
    grid = np.union1d(ta, tb)
    sa = pd.Series(ra, index=ta).reindex(grid, method="ffill").to_numpy()
    sb = pd.Series(rb, index=tb).reindex(grid, method="ffill").to_numpy()
    diff = sa - sb
    d3 = pd.Series(diff).rolling(3, min_periods=3).mean().to_numpy()
    return grid, d3


def build_c6(df_sol, df_btc, root):
    (a, b), _ = align([df_sol, df_btc])
    ts = a["open_ts"].to_numpy(np.int64)
    grid, d3 = _funding_grid(root)
    entry = np.zeros(len(ts), int)
    exit_at_open = np.zeros(len(ts), bool)
    n_sig = 0
    fin = d3[np.isfinite(d3)]
    frac_ge = float(np.mean(np.abs(fin) >= 0.00025)) if len(fin) else 0.0
    frac_neg = float(np.mean(fin <= -0.00025)) if len(fin) else 0.0
    frac_pos = float(np.mean(fin >= 0.00025)) if len(fin) else 0.0
    for i in range(len(ts)):
        j = int(np.searchsorted(grid, ts[i], side="left")) - 1
        if j < 0 or not np.isfinite(d3[j]):
            continue
        at_instant = (j + 1 < len(grid) and grid[j + 1] == ts[i])
        if at_instant:
            exit_at_open[i] = bool(abs(d3[j]) <= 0.00005)
            if d3[j] >= 0.00025:
                entry[i] = -1
                n_sig += 1
            elif d3[j] <= -0.00025:
                entry[i] = +1
                n_sig += 1
    return dict(kind="pair", df_a=a, df_b=b, entry_at_open=entry,
                exit_at_open=exit_at_open, stop_at_close=np.zeros(len(ts), bool),
                entry_frac=0.20, max_hold_bars=48, spread_stop=0.05,
                n_signals=n_sig, frac_abs_d_ge_25bps=frac_ge,
                frac_d_le_neg25_bps=frac_neg, frac_d_ge_pos25_bps=frac_pos,
                n_entry_long=int((entry == 1).sum()),
                n_entry_short=int((entry == -1).sum()))


# ══════════════════════════════════════════════════════ C7
def build_c7(df, root):
    ts = df["open_ts"].to_numpy(np.int64)
    c = df["close"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    A = atr(h, l, c, 24)
    f_ts, f_r = load_funding("SOLUSDT", root)
    Fnow = pd.Series(f_r).rolling(3, min_periods=3).mean().to_numpy()
    p90 = pd.Series(Fnow).rolling(720, min_periods=720).quantile(0.90).shift(1).to_numpy()
    p10 = pd.Series(Fnow).rolling(720, min_periods=720).quantile(0.10).shift(1).to_numpy()
    med = pd.Series(Fnow).rolling(720, min_periods=720).median().shift(1).to_numpy()

    long = np.zeros(len(ts), bool)
    short = np.zeros(len(ts), bool)
    long_exit = np.zeros(len(ts), bool)
    short_exit = np.zeros(len(ts), bool)
    n_sig = 0
    for i in range(9, len(ts)):
        s = int(np.searchsorted(f_ts, ts[i], side="left"))
        if s >= len(f_ts) or f_ts[s] != ts[i]:
            continue                      # not a settlement-bar open
        idx = s - 1                       # mean(rate[s-3..s-1]) = last 3 before the instant
        if idx < 720:
            continue
        F = Fnow[idx]
        if not (np.isfinite(F) and np.isfinite(p90[idx]) and np.isfinite(p10[idx])):
            continue
        r8 = c[i - 1] / c[i - 9] - 1.0
        if F >= p90[idx] and F >= 0.0002 and r8 > 0:
            short[i] = True
            n_sig += 1
        elif F <= p10[idx] and F <= -0.0001 and r8 < 0:
            long[i] = True
            n_sig += 1
        short_exit[i] = bool(F <= med[idx])
        long_exit[i] = bool(F >= med[idx])

    def levels(side, fill, i):
        return (fill - side * 3.0 * A[i], np.nan)

    return dict(kind="single", long_entry=long, short_entry=short,
                long_exit=long_exit, short_exit=short_exit,
                levels_fn=levels, time_stop_bars=24, one_per_day=True,
                risk_frac=0.005, max_leverage=3.0, n_signals=n_sig)


# ══════════════════════════════════════════════════════ registry
# The numeric readings of each candidate, stored in the artifact so that a
# report quoting a rule is quoting a measured declaration, not prose.
DECLARED = {
    1: {"atr_bars": 24, "z_entry": 2.0, "z_prior_bars": 720, "flow_bars": 6,
        "ret_bars": 6, "stop_atr": 2.5, "hold_bars": 12, "cooldown_bars": 12},
    2: {"atr_bars": 24, "vol_bars": 48, "range_mult": 2.0, "vol_mult": 2.5,
        "wick_frac": 0.50, "close_frac": 0.60, "ratio_long": 0.46,
        "ratio_short": 0.54, "stop_atr": 0.25, "target_r": 2.0,
        "hold_bars": 12, "cooldown_bars": 6},
    3: {"signal_hour": 12, "exit_hour": 20, "threshold_atr": 4.5,
        "atr_bars": 24, "stop_atr": 3.0, "hold_bars": 7},
    4: {"lookback_bars": 72, "rebal_every_days": 3, "dispersion_gate": 1.0,
        "leg_frac": 0.125, "leg_stop": 0.08, "book_kill": 0.15,
        "gross": 0.50, "min_bars": 792},
    5: {"lookback_bars": 24, "rebal_every_days": 1, "dispersion_gate": 3.0,
        "leg_frac": 0.20, "leg_stop": 0.05, "gross": 0.40, "min_bars": 744},
    6: {"diff_bars": 3, "entry_bps": 2.5, "exit_bps": 0.5, "hold_bars": 48,
        "spread_stop": 0.05, "leg_frac": 0.20, "gross": 0.40},
    7: {"f_bars": 3, "pct_hi": 90.0, "pct_lo": 10.0, "window": 720,
        "floor_hi_bps": 2.0, "floor_lo_bps": -1.0, "ret_bars": 8,
        "stop_atr": 3.0, "hold_bars": 24},
}

SPECS = {
    1: dict(code="C1", sym="ETHUSDT", tf="1h", legs=["ETHUSDT"],
            name="signed taker-flow persistence", build=build_c1,
            funding=["ETHUSDT"]),
    2: dict(code="C2", sym="SOLUSDT", tf="1h", legs=["SOLUSDT"],
            name="absorption of forced flow", build=build_c2,
            funding=["SOLUSDT"]),
    3: dict(code="C3", sym="ETHUSDT", tf="1h", legs=["ETHUSDT"],
            name="overnight extension fade", build=build_c3,
            funding=["ETHUSDT"]),
    4: dict(code="C4", sym="BASKET5", tf="1h", legs=_BASKET5,
            name="vol-adjusted 72h rotation", build=build_c4,
            funding=_BASKET5),
    5: dict(code="C5", sym="BASKET5", tf="1h", legs=_BASKET5,
            name="dispersion-gated 24h reversal", build=build_c5,
            funding=_BASKET5),
    6: dict(code="C6", sym="SOLUSDT+BTCUSDT", tf="1h",
            legs=["SOLUSDT", "BTCUSDT"], name="funding differential pair",
            build=build_c6, funding=["SOLUSDT", "BTCUSDT"]),
    7: dict(code="C7", sym="SOLUSDT", tf="1h", legs=["SOLUSDT"],
            name="funding-extreme fade", build=build_c7,
            funding=["SOLUSDT"]),
}
