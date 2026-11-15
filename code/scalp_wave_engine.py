#!/usr/bin/env python
"""
scalp_wave_engine.py — backtest engine for the WAVE_1 scalp pack
(Downloads/scalp_wave1_v1.1.0/wave1), ported to the repo's harness contract.

SOURCE: `Downloads/scalp_wave1_v1.1.0/wave1` (Python-only, pack 1.1.0,
MASTER PROMPT v5.1). The signal logic is copied into this file because
Downloads/ is not durable; `code/` is the durable location.

WHAT THIS IS
------------
Four kline-only indicators on Binance USD-M perpetuals (1m–15m):
  * IND-04  Session VWAP ± σ bands (k1=1, k2=2), reversion side:
            VWAP_EXT_UP -> SHORT, VWAP_EXT_DN -> LONG.
  * IND-06  Liquidity sweep (breaks the prior N-bar extreme, closes back in,
            volume burst z >= theta): SWEEP_BEAR -> SHORT, SWEEP_BULL -> LONG.
  * IND-07a Squeeze release (BB inside KC, run >= m_min, then release) and
            volume burst (rob_z(log1p(vol)) >= burst_theta):
            SQZ_REL_LONG/SHORT, BURST_UP/DN.
  * IND-05  Regime gate (CHOP, ATR percentile, vol z): emits NO events. It is
            NOT applied as a filter by default (that would be an invention:
            the pack never wires it into the other indicators). The
            `regime_filter` param turns it on as a measured variant.

Every signal is emitted once on a CLOSED bar (confirmed-bar semantics,
CONFIRMED repaint class, lag_bars = 0) and carries target_bps / stop_bps
frozen at the signal bar, plus the cost-gate fields.

EXECUTION CONVENTIONS (declared, not tuned)
-------------------------------------------
* Signal on bar i (its close) -> entry fill at bar i+1 OPEN (next-open).
* The entry bar's own range IS after the fill (the fill is at its open), so
  target/stop are evaluated on it too.
* Stop-first on ties: if target and stop are both touched inside one bar,
  the stop wins.
* Gap-through: if a LATER bar's open gaps beyond the stop, the fill is AT
  THE OPEN (not at the stop).
* One position at a time (no pyramiding, no flip). A new entry signal while
  flat opens; a signal while in a position is ignored. An exit inside a bar
  forbids an entry in that same bar (the open is already in the past).
* Same-bar multi-signal priority: the first event in the pack's own
  canonical order (bar_time, ind, sig) wins — a declared rule, not a tuned
  one.
* End of data: force close at the last close.
* Sizing: 1% of cash risked to the frozen stop distance (measured from the
  FILL price, the same distance the stop is placed at), no leverage:
  qty = min(cash*risk/stop_dist/fill_px, cash*(1-fee)/fill_px).
* Costs: repo standard 5 bps fee + 0.5 bps slip per side (11 bps round
  trip), charged on entry AND on exit. Zero-cost control measured inside
  the artifact (same trades, fee=slip=0 -> drag_pp).
* The cost GATE runs with the SAME cost regime as the execution by default
  (repo: fee_taker 5.0, half_spread 0.0, slip 0.5 -> 11 bps RT), so the
  gate and the P&L cannot disagree. `gate_cost="pack"` switches the gate to
  the pack's own DECLARED per-symbol placeholders (13–17 bps RT) as a
  measured sensitivity.
* Funding is NOT modelled: the pack is kline-only NATIVE with no funding
  input. This is a declared limit of the port, not a silent omission.

KNOWN-ANSWER AUDIT (run: python code/scalp_wave_engine.py)
---------------------------------------------------------
Hand-computed cases on synthetic bars: no-signal flat, target hit on the
entry bar, gap-through stop on a later bar, stop-first tie, end-of-data
force close. ALL PASS required before any real-data run.

REGISTER: add to ADAPTERS in code/vrun.py (snippet at the bottom), then:
    python code/vrun.py run --strategy scalpwave --tf 5m --symbol SOLUSDT
    python code/vrun.py verify <run_id>
"""

from __future__ import annotations

import math
import os
from typing import Any

import numpy as np
import pandas as pd

ENGINE_VERSION = "scalpwave-1"
INIT = 10_000.0
RISK = 0.01  # fraction of cash risked per trade

# Repo standard costs: 5 bps fee + 0.5 bps slip per side = 11 bps round trip.
COSTS = {
    "repo": dict(fee=0.0005, slip=0.00005),
    "zero": dict(fee=0.0, slip=0.0),
}

# Cost regime used by the VIABILITY GATE. `repo` mirrors the execution cost
# exactly (2*(5.0 + 0.0 + 0.5) = 11 bps RT); `pack` uses the source pack's
# DECLARED per-symbol placeholders.
GATE_COST_REPO = dict(fee_taker_bps=5.0, fee_maker_bps=2.0,
                      half_spread_bps=0.0, slip_bps=0.5,
                      k_cost=3.0, crr_min=1.0)

# ── Declared parameters (single source of truth, copied from
#    Downloads/scalp_wave1_v1.1.0/wave1/specs/params.yaml, v1.1.0) ──
PARAMS_DECLARED = {
    "version": "1.1.0",
    "tf_classes": {"c0": {"max_seconds": 180}, "c1": {"max_seconds": 300},
                   "c2": {"max_seconds": 1800}},
    "common": {
        "atr_n": 14,
        "rob_baseline_n": 101,
        "rob_eps_rel": 0.05,
        "rob_eps_abs": 1e-9,
        "sigma_min_rel": 1e-8,
        "funding_interval_hours": 8,
        "funding_window_min": 5,
        "cost": {
            "mode": "TAKER_TAKER",
            "fee_taker_bps": 5.0,
            "fee_maker_bps": 2.0,
            "half_spread_bps": 0.5,
            "slip_bps": 1.0,
            "k_cost": 3.0,
            "crr_min": 1.0,
        },
        "cost_per_symbol": {
            "SOLUSDT": {"half_spread_bps": 0.5, "slip_bps": 1.0},
            "SUIUSDT": {"half_spread_bps": 1.0, "slip_bps": 1.5},
            "LINKUSDT": {"half_spread_bps": 1.0, "slip_bps": 1.5},
            "HYPEUSDT": {"half_spread_bps": 1.5, "slip_bps": 2.0},
        },
    },
    "IND-04": {"k1": 1.0, "k2": 2.0,
               "min_minutes_since_anchor": 60, "stop_sigma_mult": 1.0},
    "IND-05": {
        "chop_n": 14, "n_pct": {"c0": 300, "c1": 200, "c2": 150},
        "atr_pct_min": 20.0, "vol_z_min": -1.0,
        "chop_trend_max": 38.2, "chop_range_min": 61.8,
        "require_trend": False,
        "vol_state_low": 25.0, "vol_state_high": 85.0,
    },
    "IND-06": {"lookback_n": {"c0": 30, "c1": 20, "c2": 12},
               "theta": 2.0, "target_atr_mult": 1.5},
    "IND-07a": {"bb_n": 20, "bb_mult": 2.0, "kc_mult": 1.5,
                "m_min": {"c0": 10, "c1": 6, "c2": 4},
                "burst_theta": 3.0, "target_atr_mult": 2.0,
                "stop_atr_mult": 1.0},
}
MIN_TF_SECONDS = 60
MAX_TF_SECONDS = 1800
TF_SECONDS = {"1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800}


# ══════════════════════════════════════ parameters ═════════════════════════

def tf_class(tf_seconds: int) -> int:
    if not (MIN_TF_SECONDS <= tf_seconds <= MAX_TF_SECONDS):
        raise ValueError(
            f"unsupported timeframe: {tf_seconds}s "
            f"(supported {MIN_TF_SECONDS}-{MAX_TF_SECONDS}s)")
    if tf_seconds <= 180:
        return 0
    if tf_seconds <= 300:
        return 1
    return 2


def resolve(params: dict, tf_seconds: int) -> dict:
    c = f"c{tf_class(tf_seconds)}"
    com, i4, i5, i6, i7 = (params["common"], params["IND-04"], params["IND-05"],
                           params["IND-06"], params["IND-07a"])
    return {
        "tf_seconds": tf_seconds,
        "tf_ms": tf_seconds * 1000,
        "atr_n": com["atr_n"],
        "rob_n": com["rob_baseline_n"],
        "rob_eps_rel": com["rob_eps_rel"],
        "rob_eps_abs": com["rob_eps_abs"],
        "sigma_min_rel": com["sigma_min_rel"],
        "funding_interval_hours": com["funding_interval_hours"],
        "funding_window_min": com["funding_window_min"],
        "cost": dict(com["cost"]),
        "k1": i4["k1"], "k2": i4["k2"],
        "b_min": int(math.ceil(i4["min_minutes_since_anchor"] * 60
                               / tf_seconds)),
        "stop_sigma_mult": i4["stop_sigma_mult"],
        "chop_n": i5["chop_n"],
        "n_pct": i5["n_pct"][c],
        "atr_pct_min": i5["atr_pct_min"],
        "vol_z_min": i5["vol_z_min"],
        "chop_trend_max": i5["chop_trend_max"],
        "chop_range_min": i5["chop_range_min"],
        "require_trend": bool(i5["require_trend"]),
        "vol_state_low": i5["vol_state_low"],
        "vol_state_high": i5["vol_state_high"],
        "sweep_n": i6["lookback_n"][c],
        "sweep_theta": i6["theta"],
        "sweep_target_atr": i6["target_atr_mult"],
        "bb_n": i7["bb_n"], "bb_mult": i7["bb_mult"],
        "kc_mult": i7["kc_mult"],
        "m_min": i7["m_min"][c],
        "burst_theta": i7["burst_theta"],
        "sqz_target_atr": i7["target_atr_mult"],
        "sqz_stop_atr": i7["stop_atr_mult"],
    }


def cost_for_symbol(params: dict, sym: str) -> dict:
    cost = dict(params["common"]["cost"])
    cost.update(params["common"].get("cost_per_symbol", {}).get(sym, {}))
    return cost


# ═══════════════════════════════════ primitives ═══════════════════════════

def _f(x) -> np.ndarray:
    return np.asarray(x, dtype=float)


def shift(x, k: int = 1) -> np.ndarray:
    x = _f(x)
    out = np.full(len(x), np.nan)
    if k < len(x):
        out[k:] = x[: len(x) - k]
    return out


def sma(x, n: int) -> np.ndarray:
    x = _f(x)
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        out[n - 1:] = np.lib.stride_tricks.sliding_window_view(x, n).mean(axis=1)
    return out


def stdev_pop(x, n: int) -> np.ndarray:
    x = _f(x)
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        out[n - 1:] = np.lib.stride_tricks.sliding_window_view(x, n).std(
            axis=1, ddof=0)
    return out


def rolling_sum(x, n: int) -> np.ndarray:
    x = _f(x)
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        out[n - 1:] = np.lib.stride_tricks.sliding_window_view(x, n).sum(axis=1)
    return out


def highest(x, n: int) -> np.ndarray:
    x = _f(x)
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        out[n - 1:] = np.lib.stride_tricks.sliding_window_view(x, n).max(axis=1)
    return out


def lowest(x, n: int) -> np.ndarray:
    x = _f(x)
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        out[n - 1:] = np.lib.stride_tricks.sliding_window_view(x, n).min(axis=1)
    return out


def true_range(high, low, close) -> np.ndarray:
    h, l, c = _f(high), _f(low), _f(close)
    tr = h - l
    if len(h) > 1:
        pc = c[:-1]
        tr[1:] = np.maximum(h[1:] - l[1:],
                            np.maximum(np.abs(h[1:] - pc), np.abs(l[1:] - pc)))
    return tr


def rma(x, n: int) -> np.ndarray:
    """Wilder RMA, alpha = 1/n, seeded with the SMA of the first n values."""
    x = _f(x)
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    a = 1.0 / n
    val = float(x[:n].mean())
    out[n - 1] = val
    for i in range(n, len(x)):
        val = a * float(x[i]) + (1.0 - a) * val
        out[i] = val
    return out


def atr(high, low, close, n: int) -> np.ndarray:
    return rma(true_range(high, low, close), n)


def rob_z(x, n: int, eps_rel: float, eps_abs: float) -> np.ndarray:
    """Robust z-score. Baseline window [t-n, t-1] excludes the current bar."""
    x = _f(x)
    out = np.full(len(x), np.nan)
    if len(x) <= n:
        return out
    base = np.lib.stride_tricks.sliding_window_view(x, n)[: len(x) - n]
    med = np.median(base, axis=1)
    mad = np.median(np.abs(base - med[:, None]), axis=1)
    scale = np.maximum(1.4826 * mad,
                       np.maximum(eps_rel * np.abs(med), eps_abs))
    out[n:] = (x[n:] - med) / scale
    return out


def percent_rank_prev(x, n: int) -> np.ndarray:
    x = _f(x)
    out = np.full(len(x), np.nan)
    if len(x) <= n:
        return out
    base = np.lib.stride_tricks.sliding_window_view(x, n)[: len(x) - n]
    cur = x[n:]
    ok = np.isfinite(base).all(axis=1) & np.isfinite(cur)
    cnt = (base <= cur[:, None]).sum(axis=1)
    out[n:] = np.where(ok, 100.0 * cnt / n, np.nan)
    return out


def chop(high, low, close, n: int) -> np.ndarray:
    h, l, c = _f(high), _f(low), _f(close)
    tr = true_range(h, l, c)
    s = rolling_sum(tr, n)
    rng = highest(h, n) - lowest(l, n)
    out = np.full(len(h), np.nan)
    ok = np.isfinite(s) & np.isfinite(rng) & (rng > 0.0)
    out[ok] = 100.0 * np.log10(s[ok] / rng[ok]) / math.log10(n)
    return out


# ═════════════════════════════════ indicators ══════════════════════════════

DAY_MS = 86_400_000


def session_vwap(open_ms, high, low, close, volume, k1: float, k2: float):
    """UTC-anchored VWAP with volume-weighted sigma (stable running form)."""
    n = len(close)
    day = np.asarray(open_ms, dtype=np.int64) // DAY_MS
    p = (np.asarray(high, float) + np.asarray(low, float)
         + np.asarray(close, float)) / 3.0
    vol = np.asarray(volume, float)
    vwap = np.full(n, np.nan)
    sigma = np.full(n, np.nan)
    bars = np.zeros(n, dtype=np.int64)
    W = mu = S = 0.0
    b = 0
    for i in range(n):
        if i == 0 or day[i] != day[i - 1]:
            W = mu = S = 0.0
            b = 0
        b += 1
        v = float(vol[i])
        W += v
        if W > 0.0:
            d = float(p[i]) - mu
            mu += (v / W) * d
            S += v * d * (float(p[i]) - mu)
            vwap[i] = mu
            sigma[i] = math.sqrt(max(S / W, 0.0))
        bars[i] = b
    return {
        "vwap": vwap, "sigma": sigma, "bars": bars,
        "up1": vwap + k1 * sigma, "lo1": vwap - k1 * sigma,
        "up2": vwap + k2 * sigma, "lo2": vwap - k2 * sigma,
    }


def funding_proximity(open_ms, interval_h: float, window_min: float,
                      tf_ms: int) -> np.ndarray:
    t = np.asarray(open_ms, dtype=np.int64)
    iv = int(round(interval_h * 3_600_000))
    w = int(round(window_min * 60_000))
    since = t % iv
    to_next = iv - since
    return (to_next <= w + tf_ms) | (since < w)


def _sq_run(sq_on: np.ndarray) -> np.ndarray:
    run = np.zeros(len(sq_on), dtype=np.int64)
    r = 0
    for i, on in enumerate(sq_on):
        r = r + 1 if on else 0
        run[i] = r
    return run


def compute_all(df: pd.DataFrame, tf_seconds: int,
                params: dict | None = None) -> pd.DataFrame:
    """df columns: open_time (ms), open, high, low, close, volume."""
    P = resolve(params or PARAMS_DECLARED, tf_seconds)
    t = df["open_time"].to_numpy(np.int64)
    o, h, l, c, v = (df[k].to_numpy(float) for k in
                     ("open", "high", "low", "close", "volume"))
    n = len(c)
    out: dict[str, Any] = {"open_time": t}

    tr = true_range(h, l, c)
    atr14 = rma(tr, P["atr_n"])
    with np.errstate(invalid="ignore", divide="ignore"):
        atr_bps = atr14 / c * 1e4
    lv = np.log1p(v)
    z = rob_z(lv, P["rob_n"], P["rob_eps_rel"], P["rob_eps_abs"])

    # IND-04
    sv = session_vwap(t, h, l, c, v, P["k1"], P["k2"])
    vwap, sigma = sv["vwap"], sv["sigma"]
    with np.errstate(invalid="ignore"):
        sig_ok = np.isfinite(sigma) & (sigma > P["sigma_min_rel"]
                                       * np.abs(vwap))
        elig04 = (sv["bars"] >= P["b_min"]) & sig_ok
        dist_z = np.where(sig_ok, (c - vwap) / np.where(
            sig_ok, sigma, 1.0), np.nan)
        up2p, lo2p, cp = shift(sv["up2"]), shift(sv["lo2"]), shift(c)
        ext_up = (elig04 & np.isfinite(up2p) & (c > sv["up2"])
                  & (cp <= up2p))
        ext_dn = (elig04 & np.isfinite(lo2p) & (c < sv["lo2"])
                  & (cp >= lo2p))
    out.update(vwap=vwap, sigma=sigma, up1=sv["up1"], lo1=sv["lo1"],
               up2=sv["up2"], lo2=sv["lo2"], bars_since_anchor=sv["bars"],
               dist_z=dist_z, elig04=elig04, ext_up=ext_up, ext_dn=ext_dn)

    # IND-05
    atr_pct = percent_rank_prev(atr_bps, P["n_pct"])
    chop_v = chop(h, l, c, P["chop_n"])
    with np.errstate(invalid="ignore"):
        eligible05 = (np.isfinite(chop_v) & np.isfinite(atr_pct)
                      & np.isfinite(z) & (atr_pct >= P["atr_pct_min"])
                      & (z >= P["vol_z_min"]))
        if P["require_trend"]:
            eligible05 = eligible05 & (chop_v <= P["chop_trend_max"])
        chop_state = np.select(
            [~np.isfinite(chop_v), chop_v < P["chop_trend_max"],
             chop_v > P["chop_range_min"]], [0, 1, 2], default=3).astype(np.int64)
        vol_state = np.select(
            [~np.isfinite(atr_pct), atr_pct < P["vol_state_low"],
             atr_pct > P["vol_state_high"]], [0, 1, 3], default=2).astype(np.int64)
    out.update(atr14=atr14, atr_bps=atr_bps, atr_pct=atr_pct, chop=chop_v,
               vol_z=z, eligible05=eligible05, chop_state=chop_state,
               vol_state=vol_state)

    # IND-06
    hh_prev = shift(highest(h, P["sweep_n"]))
    ll_prev = shift(lowest(l, P["sweep_n"]))
    with np.errstate(invalid="ignore"):
        bear_raw = ((h > hh_prev) & (c < hh_prev) & (z >= P["sweep_theta"]))
        bull_raw = ((l < ll_prev) & (c > ll_prev) & (z >= P["sweep_theta"]))
        elig06 = np.isfinite(z) & np.isfinite(hh_prev) & np.isfinite(ll_prev)
    out.update(hh_prev=hh_prev, ll_prev=ll_prev,
               sweep_bear=bear_raw & ~bull_raw,
               sweep_bull=bull_raw & ~bear_raw,
               sweep_ambig=bear_raw & bull_raw, elig06=elig06)

    # IND-07a
    basis = sma(c, P["bb_n"])
    sd = stdev_pop(c, P["bb_n"])
    bb_up, bb_lo = basis + P["bb_mult"] * sd, basis - P["bb_mult"] * sd
    atr_kc = rma(tr, P["bb_n"])
    kc_up, kc_lo = basis + P["kc_mult"] * atr_kc, basis - P["kc_mult"] * atr_kc
    with np.errstate(invalid="ignore"):
        sq_valid = (np.isfinite(bb_up) & np.isfinite(bb_lo)
                    & np.isfinite(kc_up) & np.isfinite(kc_lo))
        sq_on = sq_valid & (bb_up < kc_up) & (bb_lo > kc_lo)
        run = _sq_run(sq_on)
        run_prev = np.concatenate([[0], run[:-1]]) if n else run
        release = sq_valid & (run_prev >= P["m_min"]) & ~sq_on
        sqz_long = release & (c > basis)
        sqz_short = release & (c < basis)
        burst = np.isfinite(z) & (z >= P["burst_theta"])
        burst_up = burst & (c > o)
        burst_dn = burst & (c < o)
        elig07a = sq_valid & np.isfinite(z)
    out.update(bb_basis=basis, bb_up=bb_up, bb_lo=bb_lo, kc_up=kc_up,
               kc_lo=kc_lo, sq_on=sq_on, sq_run=run, sqz_long=sqz_long,
               sqz_short=sqz_short, burst_up=burst_up, burst_dn=burst_dn,
               elig07a=elig07a)

    out["funding_prox"] = funding_proximity(
        t, P["funding_interval_hours"], P["funding_window_min"], P["tf_ms"])
    return pd.DataFrame(out)


# ════════════════════════════════ signal generation ══════════════════════

EVENT_COLUMNS = ["bar_time", "ind", "sig", "side", "px", "target_bps",
                 "stop_bps", "cost_bps", "k", "crr", "gate_pass", "feas",
                 "components", "lag_bars", "tier"]


def _gate(target_bps: np.ndarray, stop_bps: np.ndarray, rt_cost: float,
          k: float, crr_min: float):
    t = np.asarray(target_bps, dtype=float)
    s = np.asarray(stop_bps, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        ok = np.isfinite(t) & (t >= k * rt_cost)
        crr = np.where(np.isfinite(s) & (s >= 0.0) & (s + rt_cost > 0.0),
                       (t - rt_cost) / (s + rt_cost), np.nan)
        ok = ok & np.isfinite(crr) & (crr >= crr_min)
    return ok, crr


def _rows(mask, ind, sig, side, px, target, stop, comps, cost_bps, k,
          gate_pass, crr, t):
    idx = np.flatnonzero(mask)
    rows = []
    for i in idx:
        rows.append({
            "bar_time": int(t[i]), "ind": ind, "sig": sig, "side": side,
            "px": float(px[i]), "target_bps": float(target[i]),
            "stop_bps": float(stop[i]), "cost_bps": cost_bps, "k": k,
            "crr": float(crr[i]) if np.isfinite(crr[i]) else None,
            "gate_pass": bool(gate_pass[i]), "feas": "NATIVE",
            "components": {n: float(a[i]) for n, a in comps.items()},
            "lag_bars": 0, "tier": "CONFIRMED"})
    return rows


def generate_signals(df: pd.DataFrame, tf_seconds: int,
                     cost: dict | None = None,
                     params: dict | None = None,
                     mode: str = "TAKER_TAKER",
                     indicators: pd.DataFrame | None = None,
                     use_regime_filter: bool = False) -> pd.DataFrame:
    """Confirmed-tier signal events with the cost-viability gate.

    One row per signal, with target_bps / stop_bps frozen at the signal bar.
    `gate_pass` is computed with the requested cost mode.
    """
    params = params or PARAMS_DECLARED
    P = resolve(params, tf_seconds)
    cc = {**P["cost"], **(cost or {})}
    if mode == "TAKER_TAKER":
        rt = 2.0 * (cc["fee_taker_bps"] + cc["half_spread_bps"]
                    + cc["slip_bps"])
    elif mode == "MAKER_TAKER":
        rt = (cc["fee_maker_bps"]
              + (cc["fee_taker_bps"] + cc["half_spread_bps"] + cc["slip_bps"]))
    else:
        raise ValueError(f"cost mode not permitted: {mode!r}")
    k, crr_min = cc["k_cost"], cc["crr_min"]
    X = indicators if indicators is not None else compute_all(df, tf_seconds,
                                                              params)
    t = X["open_time"].to_numpy()
    c = df["close"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    o = df["open"].to_numpy(float)
    atr = X["atr14"].to_numpy(float)
    z = X["vol_z"].to_numpy(float)
    sigma = X["sigma"].to_numpy(float)
    vwap = X["vwap"].to_numpy(float)
    ev: list[dict] = []

    def gate(target, stop):
        return _gate(target, stop, rt, k, crr_min)

    with np.errstate(invalid="ignore", divide="ignore"):
        # IND-04 (reversion side)
        tgt04 = np.abs(c - vwap) / c * 1e4
        stp04 = P["stop_sigma_mult"] * sigma / c * 1e4
        g04, crr04 = gate(tgt04, stp04)
        comps04 = {"dist_z": X["dist_z"].to_numpy(float),
                   "sigma_bps": sigma / c * 1e4}
        ev += _rows(X["ext_up"].to_numpy(), "IND-04", "VWAP_EXT_UP",
                    "SHORT", c, tgt04, stp04, comps04, rt, k, g04, crr04, t)
        ev += _rows(X["ext_dn"].to_numpy(), "IND-04", "VWAP_EXT_DN",
                    "LONG", c, tgt04, stp04, comps04, rt, k, g04, crr04, t)

        # IND-06
        tgt06 = P["sweep_target_atr"] * atr / c * 1e4
        hh, ll = X["hh_prev"].to_numpy(float), X["ll_prev"].to_numpy(float)
        stp_bear = (h - c) / c * 1e4
        stp_bull = (c - l) / c * 1e4
        gbe, crr_be = gate(tgt06, stp_bear)
        gbu, crr_bu = gate(tgt06, stp_bull)
        comps_be = {"vol_z": z, "wick_atr": (h - hh) / atr}
        comps_bu = {"vol_z": z, "wick_atr": (ll - l) / atr}
        ev += _rows(X["sweep_bear"].to_numpy(), "IND-06", "SWEEP_BEAR",
                    "SHORT", c, tgt06, stp_bear, comps_be, rt, k, gbe, crr_be,
                    t)
        ev += _rows(X["sweep_bull"].to_numpy(), "IND-06", "SWEEP_BULL",
                    "LONG", c, tgt06, stp_bull, comps_bu, rt, k, gbu, crr_bu,
                    t)

        # IND-07a
        tgt07 = P["sqz_target_atr"] * atr / c * 1e4
        stp07 = P["sqz_stop_atr"] * atr / c * 1e4
        g07, crr07 = gate(tgt07, stp07)
        run_prev = (np.concatenate([[0], X["sq_run"].to_numpy()[:-1]])
                    .astype(float) if len(X) else np.array([]))
        basis_dist = (np.abs(c - X["bb_basis"].to_numpy(float)) / atr)
        comps_sq = {"run_len": run_prev, "vol_z": z,
                    "basis_dist_atr": basis_dist}
        ev += _rows(X["sqz_long"].to_numpy(), "IND-07a", "SQZ_REL_LONG",
                    "LONG", c, tgt07, stp07, comps_sq, rt, k, g07, crr07, t)
        ev += _rows(X["sqz_short"].to_numpy(), "IND-07a", "SQZ_REL_SHORT",
                    "SHORT", c, tgt07, stp07, comps_sq, rt, k, g07, crr07, t)
        comps_bu2 = {"vol_z": z, "basis_dist_atr": basis_dist}
        ev += _rows(X["burst_up"].to_numpy(), "IND-07a", "BURST_UP",
                    "LONG", c, tgt07, stp07, comps_bu2, rt, k, g07, crr07, t)
        ev += _rows(X["burst_dn"].to_numpy(), "IND-07a", "BURST_DN",
                    "SHORT", c, tgt07, stp07, comps_bu2, rt, k, g07, crr07, t)

    out = pd.DataFrame(ev, columns=EVENT_COLUMNS)
    if use_regime_filter and not out.empty and "eligible05" in X.columns:
        elig = X["eligible05"].to_numpy(bool)
        tset = {int(x): i for i, x in enumerate(X["open_time"].to_numpy())}
        keep = []
        for bt in out["bar_time"].to_numpy():
            i = tset.get(int(bt), -1)
            keep.append(bool(elig[i]) if i >= 0 else False)
        out = out[np.asarray(keep, bool)].reset_index(drop=True)
    return out.sort_values(["bar_time", "ind", "sig"], kind="stable"
                           ).reset_index(drop=True)


# ════════════════════════════════ executor ═════════════════════════════════

def execute(events: pd.DataFrame, df: pd.DataFrame,
            fee: float, slip: float) -> dict:
    """Next-open fills, stop-first on ties, gap-through at the open.

    One position at a time. Returns the equity curve (per bar) and trades.
    """
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    t = df["open_time"].to_numpy()
    n = len(df)

    idx_of = {int(x): i for i, x in enumerate(t)}
    # signal bar -> entry fill bar (next bar). First signal in the pack's
    # canonical order wins a same-bar tie.
    entry_at: dict[int, dict] = {}
    if not events.empty:
        ev_sorted = events.sort_values(["bar_time", "ind", "sig"], kind="stable")
        for _, ev in ev_sorted.iterrows():
            i = idx_of.get(int(ev["bar_time"]), -1)
            if i < 0 or i + 1 >= n:
                continue
            entry_at.setdefault(i + 1, {
                "side": ev["side"], "target_bps": float(ev["target_bps"]),
                "stop_bps": float(ev["stop_bps"])})

    # The curve starts at INIT (flat, no position). It is inert for the
    # metrics (the peak and the drawdown are unaffected), but a curve that
    # starts at 1.0 instead of the account is a trap for whoever reads it.
    eq = np.full(n, INIT)
    cash, qty, entry = INIT, 0.0, 0.0
    entry_i, entry_side = -1, 0
    target_px = stop_px = 0.0
    trades = []

    def close_trade(i: int, px: float, why: str):
        nonlocal cash, qty, entry, entry_i, entry_side
        fill = px * (1 - slip) if entry_side == 1 else px * (1 + slip)
        # A LONG sells here (receives fill*(1-fee)); a SHORT BUYS BACK here and
        # therefore PAYS fill*(1+fee). Using (1-fee) on the short's buy-back
        # would under-charge that side's fee by 2*fee*notional and flatter
        # every short book.
        if entry_side == 1:
            cash += qty * fill * (1 - fee)
        else:
            cash -= qty * fill * (1 + fee)
        pnl_gross = ((fill - entry) * qty if entry_side == 1
                     else (entry - fill) * qty)
        # The fee is charged on BOTH fills; the notional is both fills' value.
        # `pnl` is NET of it: the repo's gate is "PF EX-COST", so a PF built
        # on a pre-fee PnL would overstate every cell (a family can show
        # PF > 1 and still lose money once the fees are paid).
        fees = qty * (entry + fill) * fee
        trades.append(dict(entry_i=entry_i, exit_i=i, why=why,
                           side=entry_side,
                           pnl=pnl_gross - fees,
                           pnl_gross=pnl_gross,
                           fees=fees,
                           entry_px=entry,
                           exit_px=fill,
                           notional=qty * (entry + fill)))
        qty = 0.0

    for i in range(1, n):
        px = o[i]
        exited_this_bar = False
        # ── 1. exit check for a position opened on an EARLIER bar ──
        # STOP FIRST on ties: if both levels are touched inside one bar, the
        # stop wins (declared convention; the repo's stop-first rule).
        if qty > 0 and entry_i < i:
            if entry_side == 1:
                if l[i] <= stop_px:
                    close_trade(i, min(px, stop_px), "stop")  # gap -> open
                    exited_this_bar = True
                elif h[i] >= target_px:
                    close_trade(i, target_px, "target")
                    exited_this_bar = True
            else:
                if h[i] >= stop_px:
                    close_trade(i, max(px, stop_px), "stop")
                    exited_this_bar = True
                elif l[i] <= target_px:
                    close_trade(i, target_px, "target")
                    exited_this_bar = True
        # ── 2. entry at bar i open (the signal fired on bar i-1) ──
        if qty == 0 and not exited_this_bar and i in entry_at:
            ev = entry_at[i]
            side = 1 if ev["side"] == "LONG" else -1
            stop_bps = ev["stop_bps"]
            if not (np.isfinite(stop_bps) and stop_bps > 0):
                pass
            else:
                fill = px * (1 + slip * side)
                # stop distance measured FROM THE FILL, and the same distance
                # the stop is placed at (one definition, used twice)
                stop_dist = fill * stop_bps / 1e4
                if stop_dist > 0:
                    # SIZE: the risk per UNIT is stop_dist (a price distance),
                    # so the units that risk RISK of cash are
                    # cash*RISK/stop_dist. Dividing by the fill again would
                    # shrink the position by a factor of the PRICE (a 140 USDT
                    # asset would get 140x less risk than a 1 USDT one), which
                    # is not a risk budget, it is a bug. The cap keeps the
                    # book unlevered.
                    q = cash * RISK / stop_dist
                    # The cap must leave the cash able to PAY the entry fee:
                    # notional*(1+fee) <= cash  ->  qty <= cash/((1+fee)*fill).
                    q = min(q, cash / ((1 + fee) * fill))
                    if q > 0:
                        qty = q
                        entry = fill
                        entry_i = i
                        entry_side = side
                        target_px = (fill * (1 + ev["target_bps"] / 1e4)
                                     if side == 1
                                     else fill * (1 - ev["target_bps"] / 1e4))
                        stop_px = (fill - stop_dist if side == 1
                                   else fill + stop_dist)
                        cash -= qty * fill * (1 + fee) if side == 1 else \
                            -qty * fill * (1 - fee)
        # ── 3. the ENTRY bar's range is after our fill -> check it too ──
        # (stop first, same rule as above)
        if qty > 0 and entry_i == i:
            if entry_side == 1:
                if l[i] <= stop_px:
                    close_trade(i, stop_px, "stop")
                elif h[i] >= target_px:
                    close_trade(i, target_px, "target")
            else:
                if h[i] >= stop_px:
                    close_trade(i, stop_px, "stop")
                elif l[i] <= target_px:
                    close_trade(i, target_px, "target")
        eq[i] = cash + qty * c[i]
    if qty > 0:  # end of data: force close
        close_trade(n - 1, c[-1], "end_of_data")
        eq[-1] = cash
    return dict(eq=eq, trades=trades)


# ══════════════════════════════ adapter entry point ══════════════════════

def run_symbol(paths: list, params: dict) -> tuple:
    """Harness contract: (metrics, prov, tables)."""
    p = dict(params)
    # The symbol comes from the SERVED FILE's basename (the harness serves the
    # cut slice under the original name), not from params: the per-symbol cost
    # block is symbol-specific, so a wrong symbol would silently use the
    # generic cost.
    sym = p.get("symbol")
    if not sym and paths:
        sym = os.path.basename(str(paths[0])).split("_")[0]
    sym = (sym or "UNKNOWN").upper()
    frames = [pd.read_csv(x) for x in paths]
    df = pd.concat(frames, ignore_index=True)
    df.columns = [str(x).strip().lower() for x in df.columns]
    if "open_ts" in df.columns:
        df = df.rename(columns={"open_ts": "open_time"})
    # open_time stays in int64 MILLISECONDS: the indicators anchor the session
    # on `open_ms // DAY_MS`, so a datetime column would break the arithmetic.
    df["open_time"] = pd.to_numeric(df["open_time"], errors="coerce")
    df = df.dropna(subset=["open_time"])
    df["open_time"] = df["open_time"].astype(np.int64)
    df = df.drop_duplicates("open_time").sort_values(
        "open_time").reset_index(drop=True)
    # Optional window, declared in the artifact's params (and therefore in its
    # run_id). The pack's own config declares a 12-month 1m window; the 1m
    # files here hold ~2M rows, and the robust-z baseline materialises a
    # 101-wide window per bar, so a bounded window is a memory decision, not
    # a cherry-pick: the artifact records the window it ran on.
    slice_from = p.get("slice_from")
    slice_to = p.get("slice_to")
    if slice_from:
        df = df[df["open_time"] >= int(pd.Timestamp(slice_from, tz="UTC")
                                       .value // 1_000_000)]
    if slice_to:
        df = df[df["open_time"] < int(pd.Timestamp(slice_to, tz="UTC")
                                      .value // 1_000_000)]
    df = df.reset_index(drop=True)
    tf_s = p.get("tf_seconds")
    if tf_s is None:
        tf_s = TF_SECONDS.get(p.get("tf", "5m"), 300)

    gate_cost_mode = p.get("gate_cost", "repo")
    if gate_cost_mode == "pack":
        gate_cost = cost_for_symbol(PARAMS_DECLARED, sym)
    else:
        gate_cost = dict(GATE_COST_REPO)
    regime_filter = bool(p.get("regime_filter", False))

    # The indicators are computed ONCE and reused by every execution below:
    # the signal set does not depend on the execution costs, only the gate
    # does, and the gate is a declared pre-filter.
    X = compute_all(df, tf_s, PARAMS_DECLARED)
    ev_all = generate_signals(df, tf_s, cost=gate_cost, params=PARAMS_DECLARED,
                              mode="TAKER_TAKER", indicators=X,
                              use_regime_filter=regime_filter)
    ev = ev_all[ev_all["gate_pass"]].reset_index(drop=True)

    def measure(events: pd.DataFrame, cc: dict) -> dict:
        out = execute(events, df, cc["fee"], cc["slip"])
        eq, trades = out["eq"], out["trades"]
        pnls = np.array([t["pnl"] for t in trades], float)
        gp = float(pnls[pnls > 0].sum())
        gl = float(-pnls[pnls < 0].sum())
        ret = float(eq[-1] / INIT - 1)
        # ACCOUNTING INVARIANT: the equity change must equal the sum of the
        # net trade PnL (the book ends flat, so the mark-to-market curve ends
        # on cash). This is the check that caught the short-side fee bug; it
        # runs inside every artifact, so a divergence fails loudly instead of
        # producing a plausible-looking PF.
        pnl_sum = float(pnls.sum())
        gap = (eq[-1] - INIT) - pnl_sum
        if abs(gap) > max(1e-6, abs(pnl_sum) * 1e-9):
            raise AssertionError(
                f"accounting invariant broken: eq[-1]-INIT={eq[-1] - INIT:.8f} "
                f"vs sum(pnl)={pnl_sum:.8f} (gap {gap:.8f})")
        peak = np.maximum.accumulate(eq)
        mdd = float((eq / peak - 1).min())
        n_trades = len(trades)
        pf = (gp / gl) if gl > 0 else (float("inf") if gp > 0 else 0.0)
        win = float((pnls > 0).sum() / n_trades) if n_trades else 0.0
        fees = float(sum(t.get("fees", 0.0) for t in trades))
        return dict(eq=eq, trades=trades, net_pct=100 * ret, pf=pf, n=n_trades,
                    win_rate_pct=100 * win, maxDD_pct=100 * mdd,
                    gross_profit=gp, gross_loss=gl, fees=fees,
                    commission_gross_pct=(100.0 * fees / gp) if gp > 0 else 0.0)

    rows = []
    rep = measure(ev, COSTS["repo"])
    zero = measure(ev, COSTS["zero"])
    rows.append(dict(id="repo", kind="cost", cost="repo",
                     net_pct=rep["net_pct"], pf=rep["pf"], n=rep["n"],
                     win_rate_pct=rep["win_rate_pct"],
                     maxDD_pct=rep["maxDD_pct"],
                     commission_gross_pct=rep["commission_gross_pct"]))
    rows.append(dict(id="zero", kind="cost", cost="zero",
                     net_pct=zero["net_pct"], pf=zero["pf"], n=zero["n"],
                     win_rate_pct=zero["win_rate_pct"],
                     maxDD_pct=zero["maxDD_pct"],
                     commission_gross_pct=zero["commission_gross_pct"]))

    # Per signal family. The pack's own study design analyses each family
    # SEPARATELY ("events per signal family analysed separately"), so the
    # aggregate alone would hide which family carries the loss. Measured
    # inside the artifact, at repo costs, one position at a time.
    for (ind, sig), grp in ev.groupby(["ind", "sig"], sort=True):
        r = measure(grp.reset_index(drop=True), COSTS["repo"])
        rows.append(dict(id=f"{ind}:{sig}", kind="family", family=ind,
                         signal=sig, net_pct=r["net_pct"], pf=r["pf"],
                         n=r["n"], win_rate_pct=r["win_rate_pct"],
                         maxDD_pct=r["maxDD_pct"],
                         commission_gross_pct=r["commission_gross_pct"]))

    m = dict(return_pct=rep["net_pct"], profit_factor=rep["pf"],
             n_trades=rep["n"], win_rate=rep["win_rate_pct"],
             max_dd_pct=rep["maxDD_pct"],
             commission_gross_pct=rep["commission_gross_pct"],
             cost_bp_roundtrip=11.0,
             signal_rows=int(len(ev_all)),
             signal_gate_pass=int(len(ev)),
             ret_zero_pct=zero["net_pct"],
             drag_pp=(zero["net_pct"] - rep["net_pct"]),
             fees_paid_usdt=rep["fees"],
             gross_profit_usdt=rep["gross_profit"],
             gross_loss_usdt=rep["gross_loss"])
    prov = {"adapter": "scalpwave", "engine_version": ENGINE_VERSION,
            "fill_model": "taker_next_open",
            "signal_source": "scalp_wave1 v1.1.0 WAVE_1 (IND-04/06/07a)",
            "gate_cost_mode": gate_cost_mode,
            "gate_rt_cost_bps": 2.0 * (gate_cost["fee_taker_bps"]
                                       + gate_cost["half_spread_bps"]
                                       + gate_cost["slip_bps"]),
            "regime_filter": regime_filter,
            "funding_charged": False,
            "note": "kline-only NATIVE signals; the pack carries no funding "
                    "input, so funding is not charged (declared limit)"}
    tables = [dict(r) for r in rows]
    return m, prov, tables


# ══════════════════════════════ known answers ═══════════════════════════

def _bars(*rows):
    return pd.DataFrame(rows, columns=["open_time", "open", "high", "low",
                                       "close", "volume"])


def _long_case(o_entry: float, high: float, low: float, target_bps: float,
               stop_bps: float, exit_kind: str, fee=0.0005, slip=0.00005,
               exit_px_override=None):
    """Hand computation of one long trade, spelled out step by step.

    entry fill = open*(1+slip); the risk per UNIT is the stop distance
    fill*stop_bps/1e4, so the units that risk RISK of cash are
    cash*RISK/stop_dist (NOT divided by the fill again); qty is capped at
    cash*(1-fee)/fill (no leverage). Exit fill = exit_px*(1-slip); equity =
    cash after entry and exit.
    """
    cash = INIT
    fill_in = o_entry * (1 + slip)
    stop_dist = fill_in * stop_bps / 1e4
    qty = cash * RISK / stop_dist
    qty = min(qty, cash / ((1 + fee) * fill_in))
    cash -= qty * fill_in * (1 + fee)
    if exit_kind == "target":
        exit_px = fill_in * (1 + target_bps / 1e4)
    elif exit_kind == "stop":
        exit_px = fill_in - stop_dist
    elif exit_kind == "gap_stop":
        # the bar opened beyond the stop -> the fill is AT THE OPEN
        exit_px = exit_px_override
    else:  # end_of_data -> the last close
        exit_px = exit_px_override
    fill_out = exit_px * (1 - slip)
    cash += qty * fill_out * (1 - fee)
    return cash, qty, fill_in, exit_px


def _short_case(o_entry: float, high: float, low: float, target_bps: float,
                stop_bps: float, exit_kind: str, fee=0.0005, slip=0.00005,
                exit_px_override=None):
    """Hand computation of one SHORT trade, spelled out step by step.

    A short SELLS at the open: fill = open*(1-slip); cash receives
    fill*(1-fee). The stop distance is fill*stop_bps/1e4 above the fill;
    qty = cash*risk/stop_dist/fill, capped by cash*(1-fee)/fill. The exit
    BUYS BACK: fill_out = exit_px*(1+slip); cash pays fill_out*(1+fee).
    """
    cash = INIT
    fill_in = o_entry * (1 - slip)
    stop_dist = fill_in * stop_bps / 1e4
    qty = cash * RISK / stop_dist
    qty = min(qty, cash / ((1 + fee) * fill_in))
    cash += qty * fill_in * (1 - fee)
    if exit_kind == "target":
        exit_px = fill_in * (1 - target_bps / 1e4)
    elif exit_kind == "stop":
        exit_px = fill_in + stop_dist
    elif exit_kind == "gap_stop":
        exit_px = exit_px_override      # the open is beyond the stop
    else:                              # end_of_data -> the last close
        exit_px = exit_px_override
    fill_out = exit_px * (1 + slip)
    cash -= qty * fill_out * (1 + fee)
    return cash, qty, fill_in, exit_px


def _known_answers() -> list:
    t0 = 1_600_000_000_000
    cases = []

    # Case 1: flat market, no signals -> flat equity, 0 trades.
    df = _bars(*[(t0 + i * 300_000, 100.0, 101.0, 99.0, 100.0, 1.0)
                 for i in range(300)])
    out = execute(pd.DataFrame(columns=EVENT_COLUMNS), df, 0.0005, 0.00005)
    cases.append(("no signal -> flat", out, dict(n_trades=0, final_eq=INIT)))

    # Case 2: long signal on bar 4 -> entry at bar 5 open; the ENTRY bar's
    # high (102) already reaches the target (100 bps) -> exit on bar 5.
    rows = [(t0 + i * 300_000, 100.0, 100.0, 99.0, 100.0, 1.0)
            for i in range(5)]
    rows += [(t0 + i * 300_000, 100.5, 102.0, 99.5, 100.5, 1.0)
             for i in range(5, 11)]
    df = _bars(*rows)
    sig = pd.DataFrame([{
        "bar_time": int(rows[4][0]), "ind": "TEST", "sig": "LONG_TEST",
        "side": "LONG", "px": 100.0, "target_bps": 100.0, "stop_bps": 500.0,
        "cost_bps": 11.0, "k": 3.0, "crr": 2.0, "gate_pass": True,
        "feas": "NATIVE", "components": {}, "lag_bars": 0,
        "tier": "CONFIRMED"}])
    out = execute(sig, df, 0.0005, 0.00005)
    exp_eq, _, _, _ = _long_case(100.5, 102.0, 99.5, 100.0, 500.0, "target")
    cases.append(("long target hit on the entry bar", out,
                  dict(n_trades=1, final_eq=exp_eq)))

    # Case 3: long signal, entry bar 5 is benign (low 99.5 is above the
    # stop), and bar 6 GAPS to 95.0, below the stop -> gap-through fill AT
    # THE OPEN, not at the stop.
    rows = [(t0 + i * 300_000, 100.0, 100.0, 99.0, 100.0, 1.0)
            for i in range(5)]
    rows.append((t0 + 5 * 300_000, 100.0, 100.5, 99.5, 100.0, 1.0))
    rows.append((t0 + 6 * 300_000, 95.0, 95.5, 94.0, 95.0, 1.0))
    df = _bars(*rows)
    sig = pd.DataFrame([{
        "bar_time": int(rows[4][0]), "ind": "TEST", "sig": "LONG_TEST",
        "side": "LONG", "px": 100.0, "target_bps": 2000.0, "stop_bps": 100.0,
        "cost_bps": 11.0, "k": 3.0, "crr": 2.0, "gate_pass": True,
        "feas": "NATIVE", "components": {}, "lag_bars": 0,
        "tier": "CONFIRMED"}])
    out = execute(sig, df, 0.0005, 0.00005)
    exp_eq, _, _, _ = _long_case(100.0, 100.5, 99.5, 2000.0, 100.0,
                                 "gap_stop", exit_px_override=95.0)
    cases.append(("long gap-through stop fills at the open", out,
                  dict(n_trades=1, final_eq=exp_eq)))

    # Case 4: stop-first tie: on the entry bar both target (102 >= +100 bps)
    # and stop (98 <= -200 bps) are touched -> the stop wins.
    rows = [(t0 + i * 300_000, 100.0, 100.0, 99.0, 100.0, 1.0)
            for i in range(5)]
    rows.append((t0 + 5 * 300_000, 100.5, 102.0, 98.0, 100.5, 1.0))
    df = _bars(*rows)
    sig = pd.DataFrame([{
        "bar_time": int(rows[4][0]), "ind": "TEST", "sig": "LONG_TEST",
        "side": "LONG", "px": 100.0, "target_bps": 100.0, "stop_bps": 200.0,
        "cost_bps": 11.0, "k": 3.0, "crr": 2.0, "gate_pass": True,
        "feas": "NATIVE", "components": {}, "lag_bars": 0,
        "tier": "CONFIRMED"}])
    out = execute(sig, df, 0.0005, 0.00005)
    exp_eq, _, _, _ = _long_case(100.5, 102.0, 98.0, 100.0, 200.0, "stop")
    cases.append(("stop-first tie -> stop wins", out,
                  dict(n_trades=1, final_eq=exp_eq)))

    # Case 5: end of data -> force close at the last close.
    rows = [(t0 + i * 300_000, 100.0, 100.0, 99.0, 100.0, 1.0)
            for i in range(5)]
    rows.append((t0 + 5 * 300_000, 100.0, 100.5, 99.5, 100.2, 1.0))
    df = _bars(*rows)
    sig = pd.DataFrame([{
        "bar_time": int(rows[4][0]), "ind": "TEST", "sig": "LONG_TEST",
        "side": "LONG", "px": 100.0, "target_bps": 1000.0, "stop_bps": 5000.0,
        "cost_bps": 11.0, "k": 3.0, "crr": 2.0, "gate_pass": True,
        "feas": "NATIVE", "components": {}, "lag_bars": 0,
        "tier": "CONFIRMED"}])
    out = execute(sig, df, 0.0005, 0.00005)
    # force close at the LAST CLOSE (100.2), not at the entry open
    exp_eq, _, _, _ = _long_case(100.0, 100.5, 99.5, 1000.0, 5000.0,
                                 "end_of_data", exit_px_override=100.2)
    cases.append(("end of data -> force close at the last close", out,
                  dict(n_trades=1, final_eq=exp_eq)))

    # Case 6: SHORT, target hit. The exit BUYS BACK, so it pays fill*(1+fee)
    # — the side that the long cases cannot catch.
    rows = [(t0 + i * 300_000, 100.0, 100.0, 99.0, 100.0, 1.0)
            for i in range(5)]
    rows += [(t0 + i * 300_000, 99.5, 100.0, 98.0, 99.5, 1.0)
             for i in range(5, 11)]   # low 98.0 <= target (99.5 - 100bps)
    df = _bars(*rows)
    sig = pd.DataFrame([{
        "bar_time": int(rows[4][0]), "ind": "TEST", "sig": "SHORT_TEST",
        "side": "SHORT", "px": 100.0, "target_bps": 100.0, "stop_bps": 500.0,
        "cost_bps": 11.0, "k": 3.0, "crr": 2.0, "gate_pass": True,
        "feas": "NATIVE", "components": {}, "lag_bars": 0,
        "tier": "CONFIRMED"}])
    out = execute(sig, df, 0.0005, 0.00005)
    exp_eq, _, _, _ = _short_case(99.5, 100.0, 98.0, 100.0, 500.0, "target")
    cases.append(("short target hit (exit buys back and pays fee)",
                  out, dict(n_trades=1, final_eq=exp_eq)))

    # Case 7: SHORT, stop hit on a later bar (gap through the stop -> the
    # buy-back happens at the open).
    rows = [(t0 + i * 300_000, 100.0, 100.0, 99.0, 100.0, 1.0)
            for i in range(5)]
    rows.append((t0 + 5 * 300_000, 100.0, 100.5, 99.5, 100.0, 1.0))
    rows.append((t0 + 6 * 300_000, 105.0, 106.0, 104.5, 105.0, 1.0))
    df = _bars(*rows)
    sig = pd.DataFrame([{
        "bar_time": int(rows[4][0]), "ind": "TEST", "sig": "SHORT_TEST",
        "side": "SHORT", "px": 100.0, "target_bps": 2000.0, "stop_bps": 100.0,
        "cost_bps": 11.0, "k": 3.0, "crr": 2.0, "gate_pass": True,
        "feas": "NATIVE", "components": {}, "lag_bars": 0,
        "tier": "CONFIRMED"}])
    out = execute(sig, df, 0.0005, 0.00005)
    exp_eq, _, _, _ = _short_case(100.0, 100.5, 99.5, 2000.0, 100.0,
                                  "gap_stop", exit_px_override=105.0)
    cases.append(("short gap-through stop buys back at the open", out,
                  dict(n_trades=1, final_eq=exp_eq)))

    # Case 8: SIZING on an EXPENSIVE asset. The risk budget is RISK of cash
    # (1%), so a stop-out must cost about 1% of the account whatever the
    # PRICE of the asset is. A position sized as cash*risk/stop/fill (the
    # formula that divides by the price twice) would risk 1% of cash only
    # for a 1 USDT asset and 1/100000 of it for a 100,000 USDT one. This case
    # is the one that pins the size.
    P = 100_000.0
    rows = [(t0 + i * 300_000, P, P, P, P, 1.0) for i in range(5)]
    rows.append((t0 + 5 * 300_000, P, P * 1.0005, P * 0.99, P, 1.0))
    df = _bars(*rows)
    sig = pd.DataFrame([{
        "bar_time": int(rows[4][0]), "ind": "TEST", "sig": "LONG_TEST",
        "side": "LONG", "px": P, "target_bps": 5000.0, "stop_bps": 100.0,
        "cost_bps": 11.0, "k": 3.0, "crr": 2.0, "gate_pass": True,
        "feas": "NATIVE", "components": {}, "lag_bars": 0,
        "tier": "CONFIRMED"}])
    out = execute(sig, df, 0.0005, 0.00005)
    exp_eq, exp_qty, _, _ = _long_case(P, P * 1.0005, P * 0.99, 5000.0,
                                       100.0, "stop")
    # the stop-out must cost ~1% of the account (plus fees), not ~1% of 1/P
    loss_pct = 100.0 * (INIT - exp_eq) / INIT
    cases.append((f"expensive asset: a stop-out risks ~1% of cash "
                  f"(measured {loss_pct:.3f}%)", out,
                  dict(n_trades=1, final_eq=exp_eq)))

    return cases


def _selftest() -> int:
    fails = 0
    for name, out, expect in _known_answers():
        got_n = len(out["trades"])
        got_eq = float(out["eq"][-1])
        ok = (got_n == expect["n_trades"]
              and abs(got_eq - expect["final_eq"]) < 1e-6)
        print(f"{'PASS' if ok else 'FAIL'} {name}: "
              f"n={got_n} (expect {expect['n_trades']}) "
              f"eq={got_eq:.4f} (expect {expect['final_eq']:.4f})")
        if not ok:
            for tr in out["trades"]:
                print("   trade:", tr)
        fails += not ok
    print(f"\n{len(_known_answers())} known answers, {fails} FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())


# ══════════════════════════════ registration snippet ══════════════════════
# Paste into ADAPTERS in code/vrun.py:
#
#     "scalpwave": {
#         "sources": [os.path.join(CODE, "scalp_wave_engine.py")],
#         "version": "scalpwave-1",
#         "inputs": lambda tf, sym: [
#             os.path.join(TF_DIR[tf][0], f"{sym}_{TF_DIR[tf][1]}.csv")],
#         "run": run_scalpwave, "matrix": True, "needs_tf": True,
#     },
#
# with in vrun.py:
#
#     def run_scalpwave(paths, params):
#         m = _load_module(os.path.join(CODE, "scalp_wave_engine.py"),
#                          "scalp_wave_engine")
#         return m.run_symbol(paths, params)
