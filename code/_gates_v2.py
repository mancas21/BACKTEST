"""
_gates_v2.py -- gates G1-G11 and the supporting measurement layer.

Companion to GATES_AND_RULES.md (v2). Pure functions over a trades DataFrame; no
engine is imported, so any engine that emits the trade schema below can call it
from inside its artifact builder (the `_gates` hook in pack50_engine.py).

POLICY NUMBERS ARE PROPOSED DEFAULTS. They are all in POLICY below, they are
hashed (policy_hash) and the hash should be written into every artifact, so a
threshold change is visible instead of silent.

Trade schema (one row per CLOSED trade, all returns are fractions of trade
notional on a FIXED-SIZE basis, i.e. not compounded):
    entry_time, exit_time   timestamps (UTC)
    symbol                  str (pair id for pair books)
    gross_ret               return before fees/slippage/funding
    cost_ret                fees + slippage, round trip, positive = cost
    funding_ret             funding paid (positive = paid, negative = received)
    mae                     max adverse excursion as a positive fraction of entry
    side                    +1 / -1                         (optional)
    exit_reason             'stop' | 'target' | 'signal'..  (optional)
net_ret = gross_ret - cost_ret - funding_ret.

Nothing here is a result. Every number it produces becomes a result only when
the engine persists it in a run artifact (REGLA 0).

PROVENANCE (2026-10-27): this file arrived as `BACKTEST AUDIT FIXES-CLAUDE.zip`
(a second implementation of the same audit) and is adopted as the repo's
reference gate layer after a cross-check against `code/gate2.py`. Two fixes
were applied during that cross-check, both found on REAL repo data:
    FIX 1: random_entry_trades silently produced garbage timestamps on a
    RangeIndex frame -- integer bar positions were fed to pd.to_datetime as
    nanoseconds, every trade landed on 1970-01-01, and the gate dict still
    looked plausible (G2=1.0, G9=0.875). It now fails loudly on a
    non-DatetimeIndex.
    FIX 2: load_cost_model now also reads this repo's actual cost-file schema
    (`per_symbol_binance_usdtm.{SYM}.rt_10k_bp`), not only the guessed shapes.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import NormalDist
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

_ND = NormalDist()
EULER_GAMMA = 0.5772156649015329

REPO_FEE_BPS = 5.0
REPO_SLIP_BPS = 0.5
REPO_RT_BPS = 2.0 * (REPO_FEE_BPS + REPO_SLIP_BPS)  # 11.0

# --------------------------------------------------------------------------- #
# Policy (proposed defaults -- edit here, nowhere else)
# --------------------------------------------------------------------------- #
POLICY: Dict[str, Any] = {
    "version": "2.1",
    # G1 profit factor + expectancy confidence bound
    "g1_pf_min": 1.2,
    "g1_boot_alpha": 0.05,          # one-sided: 5th pct of bootstrap mean must be > 0
    # G2 sample
    "g2_min_trades": 100,
    "g2_min_per_symbol": 30,
    "g2_min_eff_n": 50,
    # G3 split + folds (frozen-parameter chronological stability)
    "g3_split": 0.70,
    "g3_min_oos_trades": 30,
    "g3_folds": 5,
    "g3_fold_min_trades": 10,
    "g3_fold_pass_frac": 0.70,
    # G4 calendar buckets
    "g4_min_bucket_trades": 5,
    "g4_min_scored_buckets": 6,
    "g4_pos_frac_min": 0.60,
    "g4_worst_bucket_min": -0.15,   # fixed-size basis, fraction of one unit of capital
    # G5 benchmark
    "g5_alpha_t_min": 2.0,
    # G6 concentration
    "g6_trim_frac": 0.05,
    "g6_min_k": 5,
    "g6_check_week": True,
    # G7 multiple testing
    "g7_dsr_min": 0.95,
    "g7_pbo_max": 0.50,
    "g7_min_days": 60,
    # G8 cost stress
    "g8_cost_mult": 2.0,
    "g8_cost_share_max": 0.35,      # single number; the old text said "30-40%"
    # G9 risk
    "g9_dd_max": 0.35,
    "g9_require_mae": True,
    # G10 forward
    "g10_min_trades": 30,
    "g10_min_days": 60,
    # G11 win-rate margin (added 2026-11-01, adopted from the external qbt gate
    # audit): a high-win-rate book must sit comfortably above breakeven
    "g11_wr_min": 0.75,
    "g11_margin_min_pp": 5.0,
    # neighborhood stability
    "nb_pass_frac": 0.70,
    "nb_pf_ratio_min": 0.75,
    # data integrity
    "data_gap_frac_max": 0.002,
    "data_wick_z": 25.0,
    # bootstrap
    "boot_reps": 2000,
    "boot_seed": 20261027,
    # costs
    "slip_stop_mult": 3.0,          # PLACEHOLDER: calibrate on stress windows
    "slip_ref_notional_usd": 10_000.0,
}


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def policy_hash(policy: Dict[str, Any] = POLICY) -> str:
    return hashlib.sha256(_canon(policy).encode()).hexdigest()[:16]


# --------------------------------------------------------------------------- #
# Context
# --------------------------------------------------------------------------- #
@dataclass
class GateContext:
    benchmark_close: Optional[pd.Series] = None   # UTC-indexed close of the traded asset
    bh_total_return: Optional[float] = None       # engine's B&H (first open -> last close)
    book_type: str = "directional"                # "directional" | "neutral"
    inventory_book: bool = False                  # grid / martingale / anything with open inventory
    equity_mtm: Optional[pd.Series] = None        # mark-to-market equity incl. unrealised PnL
    notional_per_equity: float = 1.0              # sizing multiple (full-equity = 1.0)
    max_leverage: Optional[float] = None          # exchange leverage setting (isolated margin)
    mmr: float = 0.005                            # maintenance margin rate (tier dependent)
    n_trials: Optional[int] = None                # from TrialLedger.total_trials()
    trial_sr_var: Optional[float] = None          # TrialLedger.sr_variance()
    trial_corr_mean: float = 0.0
    pbo: Optional[float] = None                   # from pbo_cscv() when a grid exists
    start_equity_usd: Optional[float] = None      # enables size-aware cost pass in G8
    fee_bps: float = REPO_FEE_BPS
    slip_bps: float = REPO_SLIP_BPS


# --------------------------------------------------------------------------- #
# Basic statistics
# --------------------------------------------------------------------------- #
def profit_factor(r) -> float:
    r = np.asarray(r, float)
    g = r[r > 0].sum()
    l = -r[r < 0].sum()
    if l == 0:
        return math.inf if g > 0 else 0.0
    return float(g / l)


def stationary_bootstrap_indices(n: int, reps: int, mean_block: float,
                                 rng: np.random.Generator) -> np.ndarray:
    """Politis-Romano stationary bootstrap index matrix (reps x n)."""
    p = 1.0 / max(float(mean_block), 1.0)
    idx = np.empty((reps, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, reps)
    jump = rng.random((reps, n)) < p
    starts = rng.integers(0, n, (reps, n))
    for t in range(1, n):
        idx[:, t] = np.where(jump[:, t], starts[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def _safe_reps(n: int, reps: int) -> int:
    return int(max(200, min(reps, 6_000_000 // max(n, 1))))


def _block_len(n: int) -> float:
    return max(1.0, round(n ** (1.0 / 3.0)))


def bootstrap_mean_lb(r: np.ndarray, alpha: float, reps: int,
                      rng: np.random.Generator) -> Tuple[float, float]:
    n = len(r)
    reps = _safe_reps(n, reps)
    idx = stationary_bootstrap_indices(n, reps, _block_len(n), rng)
    means = r[idx].mean(axis=1)
    return float(np.quantile(means, alpha)), float(means.mean())


def bootstrap_max_dd(r: np.ndarray, size: float, reps: int,
                     rng: np.random.Generator) -> Dict[str, float]:
    """Max drawdown distribution of the trade sequence under full-equity compounding."""
    n = len(r)
    reps = _safe_reps(n, reps)
    idx = stationary_bootstrap_indices(n, reps, _block_len(n), rng)
    rets = np.maximum(1.0 + size * r[idx], 0.0)
    eq = np.cumprod(rets, axis=1)
    eq = np.concatenate([np.ones((reps, 1)), eq], axis=1)
    peak = np.maximum.accumulate(eq, axis=1)
    dd = 1.0 - eq / peak
    mdd = dd.max(axis=1)
    return {"p50": float(np.quantile(mdd, 0.5)), "p95": float(np.quantile(mdd, 0.95)),
            "ruin_frac": float((eq[:, -1] <= 0).mean())}


def alpha_beta_hac(y: np.ndarray, x: np.ndarray) -> Tuple[float, float, float]:
    """OLS y = a + b x with Newey-West (Bartlett) t-stat on a."""
    y = np.asarray(y, float)
    x = np.asarray(x, float)
    T = len(y)
    X = np.column_stack([np.ones(T), x])
    try:
        XtX_inv = np.linalg.inv(X.T @ X)
    except np.linalg.LinAlgError:
        return 0.0, 0.0, 0.0
    b = XtX_inv @ (X.T @ y)
    e = y - X @ b
    L = int(np.floor(4 * (T / 100.0) ** (2.0 / 9.0)))
    u = X * e[:, None]
    S = u.T @ u
    for l in range(1, L + 1):
        w = 1.0 - l / (L + 1.0)
        G = u[l:].T @ u[:-l]
        S += w * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    t = b[0] / math.sqrt(V[0, 0]) if V[0, 0] > 0 else 0.0
    return float(b[0]), float(b[1]), float(t)


def _moments(r: np.ndarray) -> Tuple[float, float, float, float]:
    m = r.mean()
    d = r - m
    m2 = (d ** 2).mean()
    if m2 <= 0:
        return m, 0.0, 0.0, 3.0
    return m, math.sqrt(m2), (d ** 3).mean() / m2 ** 1.5, (d ** 4).mean() / m2 ** 2


def deflated_sharpe(returns, n_trials: int, sr_var: Optional[float] = None,
                    trial_corr: float = 0.0) -> Dict[str, float]:
    """Bailey & Lopez de Prado (2014). Per-period (non-annualised) Sharpe."""
    r = np.asarray(returns, float)
    T = len(r)
    sd = r.std(ddof=1) if T > 2 else 0.0
    if T < 3 or sd == 0:
        return {"dsr": float("nan"), "sr": float("nan"), "sr0": float("nan"), "T": T}
    sr = r.mean() / sd
    _, _, g3, g4 = _moments(r)
    var_mult = max(1.0 - g3 * sr + (g4 - 1.0) / 4.0 * sr ** 2, 1e-12)
    se = math.sqrt(var_mult / (T - 1))
    n_eff = trial_corr + (1.0 - trial_corr) * max(n_trials, 1)
    if n_eff <= 1.0:
        sr0 = 0.0
    else:
        v = sr_var if (sr_var is not None and sr_var > 0) else se ** 2
        sr0 = math.sqrt(v) * ((1 - EULER_GAMMA) * _ND.inv_cdf(1 - 1.0 / n_eff)
                              + EULER_GAMMA * _ND.inv_cdf(1 - 1.0 / (n_eff * math.e)))
    return {"dsr": float(_ND.cdf((sr - sr0) / se)), "sr": float(sr), "sr0": float(sr0),
            "T": T, "n_eff_trials": float(n_eff)}


def pbo_cscv(M: np.ndarray, S: int = 16) -> Dict[str, float]:
    """Probability of Backtest Overfitting via CSCV. M: T x N matrix of per-period
    returns, one column per candidate (e.g. every combo of the pre-declared grid)."""
    M = np.asarray(M, float)
    T, N = M.shape
    if N < 2:
        return {"pbo": float("nan"), "n_combos": 0}
    S = int(S - (S % 2))
    block = T // S
    if block < 2:
        return {"pbo": float("nan"), "n_combos": 0}
    M = M[T - block * S:]
    B = M.reshape(S, block, N)
    bsum = B.sum(axis=1)
    bsq = (B ** 2).sum(axis=1)
    combos = np.array(list(itertools.combinations(range(S), S // 2)))
    C = len(combos)
    mask = np.zeros((C, S))
    mask[np.arange(C)[:, None], combos] = 1.0
    n_is = block * (S // 2)

    def sharpe(sum_, sq_, n):
        mu = sum_ / n
        var = np.maximum(sq_ / n - mu ** 2, 1e-18)
        return mu / np.sqrt(var)

    sr_is = sharpe(mask @ bsum, mask @ bsq, n_is)
    sr_oos = sharpe((1 - mask) @ bsum, (1 - mask) @ bsq, n_is)
    best = sr_is.argmax(axis=1)
    oos_of_best = sr_oos[np.arange(C), best]
    rank = (sr_oos < oos_of_best[:, None]).sum(axis=1) + 1  # 1..N ascending
    omega = rank / (N + 1.0)
    logit = np.log(omega / (1.0 - omega))
    return {"pbo": float((logit <= 0).mean()), "n_combos": int(C)}


# --------------------------------------------------------------------------- #
# Trades preparation
# --------------------------------------------------------------------------- #
def _prep(trades: pd.DataFrame) -> pd.DataFrame:
    need = ["entry_time", "exit_time", "gross_ret", "cost_ret"]
    miss = [c for c in need if c not in trades.columns]
    if miss:
        raise ValueError(f"trades missing columns: {miss}")
    t = trades.copy()
    t["entry_time"] = pd.to_datetime(t["entry_time"], utc=True)
    t["exit_time"] = pd.to_datetime(t["exit_time"], utc=True)
    if "symbol" not in t.columns:
        t["symbol"] = "ALL"
    if "funding_ret" not in t.columns:
        t["funding_ret"] = 0.0
    t["net"] = t["gross_ret"] - t["cost_ret"] - t["funding_ret"]
    return t.sort_values("exit_time").reset_index(drop=True)


def effective_n(t: pd.DataFrame) -> Dict[str, float]:
    """Heuristic effective sample size: lag-1 autocorrelation and cross-symbol
    design effect. Both clamp at >= 0 so N_eff never exceeds N."""
    r = t["net"].to_numpy()
    n = len(r)
    rho1 = 0.0
    if n > 3 and r.std() > 0:
        rho1 = float(np.corrcoef(r[:-1], r[1:])[0, 1])
        if not np.isfinite(rho1):
            rho1 = 0.0
    rho1 = max(rho1, 0.0)
    n_ac = n * (1 - rho1) / (1 + rho1)
    deff, rho_x = 1.0, 0.0
    k = t["symbol"].nunique()
    if k >= 2:
        day = t["exit_time"].dt.floor("D")
        pv = t.assign(day=day).pivot_table(index="day", columns="symbol", values="net",
                                           aggfunc="sum", fill_value=0.0)
        if len(pv) >= 30:
            c = np.corrcoef(pv.to_numpy().T)
            off = c[~np.eye(k, dtype=bool)]
            off = off[np.isfinite(off)]
            if len(off):
                rho_x = max(float(off.mean()), 0.0)
                deff = 1.0 + (k - 1) * rho_x
    return {"n": n, "rho1": rho1, "rho_cross": rho_x, "design_effect": deff,
            "n_eff": n_ac / max(deff, 1.0)}


def _daily_returns(t: pd.DataFrame, ctx: GateContext,
                   days: Optional[pd.DatetimeIndex]) -> Tuple[pd.Series, bool]:
    if ctx.equity_mtm is not None:
        eq = ctx.equity_mtm.copy()
        eq.index = pd.to_datetime(eq.index, utc=True)
        d = eq.resample("1D").last().ffill().pct_change().dropna()
        return d, True
    d = t.groupby(t["exit_time"].dt.floor("D"))["net"].sum() * ctx.notional_per_equity
    if days is None:
        days = pd.date_range(d.index.min(), d.index.max(), freq="D", tz="UTC")
    return d.reindex(days, fill_value=0.0), False


def _bench_daily(ctx: GateContext) -> Optional[pd.Series]:
    if ctx.benchmark_close is None:
        return None
    b = ctx.benchmark_close.copy()
    b.index = pd.to_datetime(b.index, utc=True)
    return b.resample("1D").last().dropna().pct_change().dropna()


# --------------------------------------------------------------------------- #
# Gates
# --------------------------------------------------------------------------- #
def gate_g1(t, ctx, P, rng):
    r = t["net"].to_numpy()
    pf = profit_factor(r)
    n_loss = int((r < 0).sum())
    lb, bmean = bootstrap_mean_lb(r, P["g1_boot_alpha"], P["boot_reps"], rng)
    pf_gross = profit_factor(t["gross_ret"].to_numpy())
    ok_pf = (pf > P["g1_pf_min"]) if n_loss else (float(r.sum()) > 0)
    return {"pass": bool(ok_pf and lb > 0), "pf_net": pf, "pf_gross": pf_gross,
            "expectancy_bps": float(r.mean() * 1e4), "boot_lb_bps": lb * 1e4,
            "zero_losers": n_loss == 0}


def gate_g2(t, ctx, P, rng):
    n = len(t)
    per = t["symbol"].value_counts()
    en = effective_n(t)
    thin = per[per < P["g2_min_per_symbol"]].to_dict()
    return {"pass": bool(n >= P["g2_min_trades"] and not thin and en["n_eff"] >= P["g2_min_eff_n"]),
            "n": n, "thin_symbols": thin, **{k: en[k] for k in ("n_eff", "rho1", "rho_cross")}}


def _pf_slice(t, lo, hi, purge_hi=True):
    m = (t["entry_time"] >= lo) & (t["entry_time"] < hi)
    s = t[m]
    purged = 0
    if purge_hi:
        crossing = s["exit_time"] > hi
        purged = int(crossing.sum())
        s = s[~crossing]
    return s, purged


def gate_g3(t, ctx, P, rng):
    t0, t1 = t["entry_time"].min(), t["exit_time"].max()
    split = t0 + (t1 - t0) * P["g3_split"]
    is_, p_is = _pf_slice(t, t0, split)
    oos = t[t["entry_time"] >= split]
    pf_is, pf_oos = profit_factor(is_["net"]), profit_factor(oos["net"])
    ok_split = bool(len(oos) >= P["g3_min_oos_trades"] and len(is_) > 0
                    and pf_is > 1.0 and pf_oos > 1.0)
    K = P["g3_folds"]
    edges = pd.to_datetime(np.linspace(t0.value, t1.value, K + 1), utc=True)
    folds = []
    for i in range(K):
        hi = edges[i + 1] if i < K - 1 else t1 + pd.Timedelta(seconds=1)
        s, purged = _pf_slice(t, edges[i], hi, purge_hi=(i < K - 1))
        pf = profit_factor(s["net"]) if len(s) else 0.0
        folds.append({"n": int(len(s)), "purged": purged, "pf": pf,
                      "pass": bool(len(s) >= P["g3_fold_min_trades"] and pf > 1.0)})
    need = math.ceil(P["g3_fold_pass_frac"] * K)
    n_pass = sum(f["pass"] for f in folds)
    return {"pass": bool(ok_split and n_pass >= need), "pf_is": pf_is, "pf_oos": pf_oos,
            "n_is": int(len(is_)), "n_oos": int(len(oos)), "purged_at_split": p_is,
            "folds_pass": n_pass, "folds_needed": need, "folds": folds}


def gate_g4(t, ctx, P, rng):
    b = t.groupby(t["exit_time"].dt.strftime("%Y-%m"))["net"].agg(["sum", "count"])
    scored = b[b["count"] >= P["g4_min_bucket_trades"]]
    if len(scored) < P["g4_min_scored_buckets"]:
        return {"pass": False, "reason": "insufficient scored buckets",
                "scored": int(len(scored)), "buckets": int(len(b))}
    frac = float((scored["sum"] > 0).mean())
    worst = float(scored["sum"].min())
    return {"pass": bool(frac >= P["g4_pos_frac_min"] and worst >= P["g4_worst_bucket_min"]),
            "frac_positive": frac, "worst_bucket": worst, "scored": int(len(scored)),
            "buckets": int(len(b))}


def gate_g5(t, ctx, P, rng):
    bd = _bench_daily(ctx)
    if bd is None:
        return {"pass": False, "reason": "no benchmark supplied (fail closed)"}
    y, mtm = _daily_returns(t, ctx, bd.index)
    j = y.index.intersection(bd.index)
    if len(j) < 60:
        return {"pass": False, "reason": "fewer than 60 overlapping days", "days": int(len(j))}
    a, beta, tstat = alpha_beta_hac(y.loc[j].to_numpy(), bd.loc[j].to_numpy())
    comp = float(np.prod(1.0 + ctx.notional_per_equity * t["net"].to_numpy()) - 1.0)
    bh = ctx.bh_total_return
    if bh is None:
        c = ctx.benchmark_close
        bh = float(c.iloc[-1] / c.iloc[0] - 1.0)
    raw_ok = comp > bh
    ok = bool(a > 0 and tstat >= P["g5_alpha_t_min"]
              and (raw_ok if ctx.book_type == "directional" else True))
    return {"pass": ok, "alpha_ann": a * 365.0, "beta": beta, "alpha_t_hac": tstat,
            "strategy_return": comp, "bh_return": bh, "beats_raw_bh": bool(raw_ok),
            "book_type": ctx.book_type, "mtm_series": mtm, "days": int(len(j))}


def gate_g6(t, ctx, P, rng):
    r = t["net"].to_numpy()
    total = float(r.sum())
    k = max(P["g6_min_k"], math.ceil(P["g6_trim_frac"] * len(r)))
    ex_top = total - float(np.sort(r)[::-1][:k].sum())
    m = t.groupby(t["exit_time"].dt.strftime("%Y-%m"))["net"].sum()
    ex_month = total - float(m.max())
    wk = t.groupby(t["exit_time"].dt.strftime("%G-%V"))["net"].sum()
    ex_week = total - float(wk.max())
    ok = ex_top > 0 and ex_month > 0 and (ex_week > 0 or not P["g6_check_week"])
    return {"pass": bool(ok), "k_removed": k, "net_ex_top": ex_top, "net_ex_best_month": ex_month,
            "net_ex_best_week": ex_week, "net_total": total}


def gate_g7(t, ctx, P, rng, daily=None):
    if ctx.n_trials is None:
        return {"pass": False, "reason": "no trial ledger count (fail closed)"}
    if daily is None:
        bd = _bench_daily(ctx)
        daily, _ = _daily_returns(t, ctx, bd.index if bd is not None else None)
    d = daily.to_numpy()
    if len(d) < P["g7_min_days"]:
        return {"pass": False, "reason": "fewer than g7_min_days daily returns", "days": len(d)}
    res = deflated_sharpe(d, ctx.n_trials, ctx.trial_sr_var, ctx.trial_corr_mean)
    pbo_ok = True if ctx.pbo is None else bool(ctx.pbo <= P["g7_pbo_max"])
    ok = bool(np.isfinite(res["dsr"]) and res["dsr"] >= P["g7_dsr_min"] and pbo_ok)
    return {"pass": ok, "pbo": ctx.pbo, "pbo_evaluated": ctx.pbo is not None, **res}


def size_aware_cost_ret(t: pd.DataFrame, start_equity_usd: float, size: float,
                        fee_bps: float, base_slip_bps: float, P: Dict[str, Any]) -> np.ndarray:
    """Round-trip cost per trade with square-root size impact and a stop-exit
    multiplier. Equity path from the baseline net returns (full-equity compounding)."""
    r = t["net"].to_numpy()
    eq = start_equity_usd * np.concatenate([[1.0], np.cumprod(np.maximum(1 + size * r, 0.0))[:-1]])
    notional = eq * size
    f = np.sqrt(np.maximum(notional / P["slip_ref_notional_usd"], 1.0))
    slip_in = base_slip_bps * f
    is_stop = (t["exit_reason"].to_numpy() == "stop") if "exit_reason" in t.columns \
        else np.zeros(len(t), bool)
    slip_out = base_slip_bps * f * np.where(is_stop, P["slip_stop_mult"], 1.0)
    return (2 * fee_bps + slip_in + slip_out) / 1e4


def gate_g8(t, ctx, P, rng):
    g, c, f = t["gross_ret"].to_numpy(), t["cost_ret"].to_numpy(), t["funding_ret"].to_numpy()
    m = P["g8_cost_mult"]
    r2 = g - m * c - f
    pf2, mean2 = profit_factor(r2), float(r2.mean())
    gross_sum = float(g.sum())
    share = float(c.sum() / gross_sum) if gross_sum > 0 else math.inf
    lo, hi = 0.0, 50.0
    if profit_factor(g - 0.0 * c - f) <= 1.0:
        m_star = 0.0
    elif profit_factor(g - hi * c - f) > 1.0:
        m_star = math.inf
    else:
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if profit_factor(g - mid * c - f) > 1.0 else (lo, mid)
        m_star = 0.5 * (lo + hi)
    mean_c_bps = float(c.mean() * 1e4)
    out = {"pf_at_mult": pf2, "mean_bps_at_mult": mean2 * 1e4, "cost_share": share,
           "breakeven_mult_pf": m_star,
           "breakeven_rt_bps_pf": m_star * mean_c_bps if np.isfinite(m_star) else math.inf,
           "mean_rt_cost_bps": mean_c_bps}
    ok = pf2 > 1.0 and mean2 > 0 and share <= P["g8_cost_share_max"]
    if ctx.start_equity_usd:
        c_sa = size_aware_cost_ret(t, ctx.start_equity_usd, ctx.notional_per_equity,
                                   ctx.fee_bps, ctx.slip_bps, P)
        r_sa = g - c_sa - f
        out["pf_size_aware"] = profit_factor(r_sa)
        ok = ok and out["pf_size_aware"] > 1.0
    out["pass"] = bool(ok)
    return out


def gate_g9(t, ctx, P, rng):
    out: Dict[str, Any] = {}
    ok = True
    r = t["net"].to_numpy()
    bs = bootstrap_max_dd(r, ctx.notional_per_equity, P["boot_reps"], rng)
    out["boot_maxdd_p95"] = bs["p95"]
    out["ruin_frac"] = bs["ruin_frac"]
    ok &= bs["p95"] <= P["g9_dd_max"] and bs["ruin_frac"] == 0.0
    if ctx.equity_mtm is not None:
        e = ctx.equity_mtm.to_numpy(float)
        dd = float((1 - e / np.maximum.accumulate(e)).max())
        out["mtm_maxdd"] = dd
        ok &= dd <= P["g9_dd_max"]
    elif ctx.inventory_book:
        out["reason_mtm"] = "inventory book without mark-to-market equity (fail closed)"
        ok = False
    if ctx.max_leverage is None:
        out["reason_leverage"] = "max_leverage not declared (fail closed)"
        ok = False
    elif "mae" in t.columns:
        thresh = 1.0 / ctx.max_leverage - ctx.mmr
        liq = int((t["mae"].to_numpy() >= thresh).sum())
        out["liquidation_threshold_move"] = thresh
        out["liquidated_trades"] = liq
        ok &= liq == 0
    elif P["g9_require_mae"]:
        out["reason_mae"] = "engine did not emit mae (fail closed)"
        ok = False
    out["pass"] = bool(ok)
    return out


def gate_g11(t, ctx, P, rng):
    """Win-rate margin over breakeven for high-win-rate books (added 2026-11-01,
    adopted from the external qbt gate set, G7 there). A book with win rate
    >= g11_wr_min must sit at least g11_margin_min_pp above the breakeven win
    rate 1/(1+payoff). High-win-rate negative-skew systems die on the left tail
    and on fill-model optimism, not on the right tail; the margin is their
    static fragility signature (the killed XRP grid ran ~87% win at ~3pp).
    Payoff = mean win / mean loss on the NET series; a book with no losers has
    breakeven 0 and passes trivially. Not yet part of the G1-G9 null-calibration
    joint (it only binds above the 75% region); fold it in at the next
    recalibration."""
    r = t["net"].to_numpy()
    n = len(r)
    if n == 0:
        return {"pass": False, "reason": "no trades"}
    wr = float((r > 0).sum()) / n
    wins, losses = r[r > 0], r[r <= 0]
    avg_l = float(-losses.mean()) if len(losses) else 0.0
    if avg_l <= 0:
        payoff, be = math.inf, 0.0
    else:
        payoff = float(wins.mean()) / avg_l
        be = 1.0 / (1.0 + payoff)
    margin_pp = (wr - be) * 100.0
    gated = wr >= P["g11_wr_min"]
    ok = margin_pp >= P["g11_margin_min_pp"] if gated else True
    return {"pass": bool(ok), "gated": bool(gated), "win_rate": wr, "payoff": payoff,
            "breakeven_wr": be, "wr_margin_pp": margin_pp}


def evaluate_forward(fwd: pd.DataFrame, prereg: Dict[str, Any], P: Dict[str, Any] = POLICY) -> Dict[str, Any]:
    """G10. prereg must carry commit_hash, registered_at (ISO) and mean_floor
    (fraction, >= 0), written BEFORE the forward window started."""
    for k in ("commit_hash", "registered_at", "mean_floor"):
        if k not in prereg:
            return {"pass": False, "reason": f"prereg missing {k}"}
    t = _prep(fwd)
    reg = pd.Timestamp(prereg["registered_at"])
    reg = reg.tz_localize("UTC") if reg.tzinfo is None else reg.tz_convert("UTC")
    if t["entry_time"].min() < reg:
        return {"pass": False, "reason": "forward trades start before registration"}
    days = (t["exit_time"].max() - t["entry_time"].min()).days
    r = t["net"].to_numpy()
    pf = profit_factor(r)
    ok = (len(t) >= P["g10_min_trades"] and days >= P["g10_min_days"] and pf > 1.0
          and r.mean() >= max(0.0, prereg["mean_floor"]))
    return {"pass": bool(ok), "n": len(t), "days": int(days), "pf": pf,
            "mean_bps": float(r.mean() * 1e4), "mean_floor_bps": prereg["mean_floor"] * 1e4}


def evaluate_gates_v2(trades: pd.DataFrame, ctx: Optional[GateContext] = None,
                      policy: Dict[str, Any] = POLICY, forward: Optional[pd.DataFrame] = None,
                      prereg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ctx = ctx or GateContext()
    t = _prep(trades)
    rng = np.random.default_rng(policy["boot_seed"])
    gates = {
        "G1": gate_g1(t, ctx, policy, rng), "G2": gate_g2(t, ctx, policy, rng),
        "G3": gate_g3(t, ctx, policy, rng), "G4": gate_g4(t, ctx, policy, rng),
        "G5": gate_g5(t, ctx, policy, rng), "G6": gate_g6(t, ctx, policy, rng),
        "G7": gate_g7(t, ctx, policy, rng), "G8": gate_g8(t, ctx, policy, rng),
        "G9": gate_g9(t, ctx, policy, rng), "G11": gate_g11(t, ctx, policy, rng),
    }
    if forward is not None and prereg is not None:
        gates["G10"] = evaluate_forward(forward, prereg, policy)
    else:
        gates["G10"] = {"pass": None, "status": "PENDING (needs forward run + prereg)"}
    backtest_pass = all(gates[g]["pass"] for g in ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8",
                                                   "G9", "G11"])
    modes: List[str] = []
    if not gates["G2"]["pass"]:
        modes.append("SAMPLE_FAILURE")
    if not gates["G11"]["pass"]:
        modes.append("WR_MARGIN_FAILURE (high win rate too close to breakeven)")
    if not gates["G1"]["pass"] or not gates["G8"]["pass"]:
        modes.append("SIGNAL_FAILURE (gross PF below threshold)" if gates["G1"]["pf_gross"] <= policy["g1_pf_min"]
                     else "COST_FAILURE (gross edge exists, net does not clear)")
    return {"policy_hash": policy_hash(policy), "policy_version": policy["version"],
            "gates": gates, "backtest_pass": bool(backtest_pass),
            "cleared": bool(backtest_pass and gates["G10"]["pass"] is True),
            "failure_modes": modes}


# --------------------------------------------------------------------------- #
# Neighborhood stability
# --------------------------------------------------------------------------- #
def neighborhood_check(results: Dict[tuple, Dict[str, Any]], center: tuple,
                       axes: Sequence[Sequence], P: Dict[str, Any] = POLICY) -> Dict[str, Any]:
    """results[param_tuple] = {'pf': float, 'g1': bool, 'g3': bool}. A neighbor is the
    +/-1 step along one axis with all other axes fixed. Missing neighbors fail closed."""
    neigh = []
    for d, ax in enumerate(axes):
        ax = list(ax)
        i = ax.index(center[d])
        for j in (i - 1, i + 1):
            if 0 <= j < len(ax):
                p = list(center)
                p[d] = ax[j]
                neigh.append(tuple(p))
    missing = [p for p in neigh if p not in results]
    if missing or len(neigh) < 2 or center not in results:
        return {"pass": False, "reason": "incomplete neighborhood", "missing": missing}
    ok = [bool(results[p]["g1"] and results[p]["g3"]) for p in neigh]
    c_pf = results[center]["pf"]
    med = float(np.median([results[p]["pf"] for p in neigh]))
    ratio = med / c_pf if c_pf > 0 else 0.0
    return {"pass": bool(np.mean(ok) >= P["nb_pass_frac"] and ratio >= P["nb_pf_ratio_min"]),
            "frac_neighbors_pass": float(np.mean(ok)), "median_pf_ratio": ratio,
            "n_neighbors": len(neigh)}


# --------------------------------------------------------------------------- #
# Calibration: null strategies (false-positive rate) and planted edge (power)
# --------------------------------------------------------------------------- #
def random_entry_trades(df: pd.DataFrame, n_trades: int, hold_bars: Sequence[int],
                        rng: np.random.Generator, side_mode: str = "both",
                        rt_cost_bps: float = REPO_RT_BPS, symbol: str = "NULL",
                        edge_bps: float = 0.0) -> pd.DataFrame:
    """Non-overlapping random-entry book: signal on a closed bar, fill at the next
    open, exit fill at an open after a hold drawn from the candidate's empirical
    hold-time distribution. edge_bps plants an additive per-trade edge (positive control)."""
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(
            "random_entry_trades needs a DatetimeIndex (entry_time comes from df.index); "
            "a positional index silently becomes 1970 timestamps downstream")
    o, h, l = df["open"].to_numpy(float), df["high"].to_numpy(float), df["low"].to_numpy(float)
    T = len(df)
    holds = rng.choice(np.maximum(np.asarray(hold_bars, int), 1), size=n_trades)
    free = T - 2 - int(holds.sum()) - n_trades
    if free <= 0:
        raise ValueError("series too short for requested trades/holds")
    cuts = np.sort(rng.integers(0, free + 1, n_trades))
    starts = cuts + np.concatenate([[0], np.cumsum(holds[:-1] + 1)])
    exits = starts + holds
    side = (rng.choice([1, -1], n_trades) if side_mode == "both"
            else np.full(n_trades, 1 if side_mode == "long" else -1))
    entry, exitp = o[starts], o[exits]
    gross = side * (exitp / entry - 1.0) + edge_bps / 1e4
    mae = np.empty(n_trades)
    for i in range(n_trades):
        s, e = starts[i], exits[i]
        mae[i] = max((entry[i] - l[s:e].min()) / entry[i], 0.0) if side[i] == 1 \
            else max((h[s:e].max() - entry[i]) / entry[i], 0.0)
    idx = df.index
    return pd.DataFrame({"entry_time": idx[starts], "exit_time": idx[exits], "symbol": symbol,
                         "side": side, "gross_ret": gross, "cost_ret": rt_cost_bps / 1e4,
                         "funding_ret": 0.0, "mae": mae})


def _upper95_rate(k: int, n: int) -> float:
    if n == 0:
        return float("nan")
    if k == 0:
        return 1.0 - 0.05 ** (1.0 / n)
    p = k / n
    z = 1.645
    return float((p + z * z / (2 * n) + z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)))
                 / (1 + z * z / n))


def _calib_policy(P, reps):
    p = dict(P)
    p["boot_reps"] = reps
    return p


def null_calibration(df: pd.DataFrame, n_trades: int, hold_bars: Sequence[int],
                     ctx: GateContext, n_sims: int = 300, seed: int = 7,
                     side_mode: str = "both", rt_cost_bps: float = REPO_RT_BPS,
                     policy: Dict[str, Any] = POLICY, reps: int = 400,
                     edge_bps: float = 0.0, k_candidates: Optional[int] = None) -> Dict[str, Any]:
    """Pass-rate of the whole gate set on random-entry books. With edge_bps=0 this is
    the empirical false-positive rate P0; with edge_bps>0 it is power at that edge."""
    rng = np.random.default_rng(seed)
    pol = _calib_policy(policy, reps)
    names = ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9"]
    per = {g: 0 for g in names}
    joint = joint_no_g7 = 0
    for _ in range(n_sims):
        tr = random_entry_trades(df, n_trades, hold_bars, rng, side_mode, rt_cost_bps, edge_bps=edge_bps)
        res = evaluate_gates_v2(tr, ctx, pol)["gates"]
        for g in names:
            per[g] += int(bool(res[g]["pass"]))
        joint += int(all(res[g]["pass"] for g in names))
        joint_no_g7 += int(all(res[g]["pass"] for g in names if g != "G7"))
    p0 = joint / n_sims
    out = {"n_sims": n_sims, "edge_bps": edge_bps, "pass_rate_joint": p0,
           "pass_rate_joint_ex_G7": joint_no_g7 / n_sims,
           "pass_rate_by_gate": {g: per[g] / n_sims for g in names},
           "upper95_joint": _upper95_rate(joint, n_sims)}
    if k_candidates:
        out["k_candidates"] = k_candidates
        out["p_at_least_one_false_pass_point"] = 1.0 - (1.0 - p0) ** k_candidates
        out["p_at_least_one_false_pass_upper95"] = 1.0 - (1.0 - out["upper95_joint"]) ** k_candidates
    return out


def planted_edge_power(df: pd.DataFrame, n_trades: int, hold_bars: Sequence[int],
                       ctx: GateContext, edges_bps: Sequence[float], **kw) -> List[Dict[str, Any]]:
    return [null_calibration(df, n_trades, hold_bars, ctx, edge_bps=e, **kw) for e in edges_bps]


# --------------------------------------------------------------------------- #
# Trial ledger (hash-chained, append-only) -> N_trials for the DSR
# --------------------------------------------------------------------------- #
class TrialLedger:
    """One JSON line per run_id. A re-run of the same run_id is the same trial and is
    not double counted. n_variants counts every combo/prompt inside a pack run."""

    def __init__(self, path: str):
        self.path = path

    def _read(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as fh:
            return [json.loads(x) for x in fh if x.strip()]

    @staticmethod
    def _hash(prev: str, entry: Dict[str, Any]) -> str:
        body = {k: v for k, v in entry.items() if k != "hash"}
        return hashlib.sha256((prev + _canon(body)).encode()).hexdigest()

    def register(self, family: str, run_id: str, n_variants: int = 1,
                 sr_daily: Optional[float] = None, note: str = "") -> bool:
        rows = self._read()
        if any(r["run_id"] == run_id for r in rows):
            return False
        prev = rows[-1]["hash"] if rows else "GENESIS"
        e = {"ts": datetime.now(timezone.utc).isoformat(), "family": family, "run_id": run_id,
             "n_variants": int(n_variants), "sr_daily": sr_daily, "note": note, "prev": prev}
        e["hash"] = self._hash(prev, e)
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(e) + "\n")
        return True

    def total_trials(self, family: Optional[str] = None) -> int:
        return sum(r["n_variants"] for r in self._read() if family is None or r["family"] == family)

    def sr_variance(self, min_obs: int = 10) -> Optional[float]:
        s = [r["sr_daily"] for r in self._read() if r.get("sr_daily") is not None]
        return float(np.var(s, ddof=1)) if len(s) >= min_obs else None

    def verify(self) -> Tuple[bool, List[str]]:
        prev, bad = "GENESIS", []
        for i, r in enumerate(self._read()):
            if r["prev"] != prev or r["hash"] != self._hash(prev, r):
                bad.append(f"line {i + 1}: chain broken")
            prev = r["hash"]
        return (not bad), bad


# --------------------------------------------------------------------------- #
# Artifact chain (tamper-evidence for results/runs/ without touching run_id v1)
# --------------------------------------------------------------------------- #
def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def chain_append(chain_path: str, artifact_path: str) -> Dict[str, Any]:
    rows = []
    if os.path.exists(chain_path):
        with open(chain_path, "r", encoding="utf-8") as fh:
            rows = [json.loads(x) for x in fh if x.strip()]
    prev = rows[-1]["hash"] if rows else "GENESIS"
    e = {"ts": datetime.now(timezone.utc).isoformat(), "artifact": os.path.basename(artifact_path),
         "file_sha256": _sha256_file(artifact_path), "prev": prev}
    e["hash"] = hashlib.sha256((prev + _canon({k: v for k, v in e.items() if k != "hash"})).encode()).hexdigest()
    with open(chain_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(e) + "\n")
    return e


def chain_verify(chain_path: str, runs_dir: str) -> Tuple[bool, List[str]]:
    prev, bad = "GENESIS", []
    with open(chain_path, "r", encoding="utf-8") as fh:
        rows = [json.loads(x) for x in fh if x.strip()]
    for i, r in enumerate(rows):
        body = {k: v for k, v in r.items() if k != "hash"}
        if r["prev"] != prev or r["hash"] != hashlib.sha256((prev + _canon(body)).encode()).hexdigest():
            bad.append(f"entry {i + 1}: chain broken")
        fp = os.path.join(runs_dir, r["artifact"])
        if not os.path.exists(fp):
            bad.append(f"{r['artifact']}: missing")
        elif _sha256_file(fp) != r["file_sha256"]:
            bad.append(f"{r['artifact']}: bytes changed since it was chained")
        prev = r["hash"]
    return (not bad), bad


def env_fingerprint(seed: Optional[int] = None) -> Dict[str, Any]:
    return {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__,
            "platform": platform.platform(), "seed": seed, "policy_hash": policy_hash()}


# --------------------------------------------------------------------------- #
# Costs
# --------------------------------------------------------------------------- #
def load_cost_model(path: str) -> Dict[str, float]:
    """Reads results/cost_model_*.json into {SYMBOL: round_trip_bps}. The schema was
    not visible to the author, so several shapes are accepted; adjust if yours differs."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict) and isinstance(data.get("symbols"), dict):
        data = data["symbols"]
    # this repo's actual schema: per_symbol_binance_usdtm.{SYM}.{rt_10k_bp|...}
    if isinstance(data, dict) and isinstance(data.get("per_symbol_binance_usdtm"), dict):
        data = data["per_symbol_binance_usdtm"]
    out: Dict[str, float] = {}
    for sym, v in (data.items() if isinstance(data, dict) else []):
        if isinstance(v, (int, float)):
            out[sym.upper()] = float(v)
        elif isinstance(v, dict):
            for key in ("rt_bps", "round_trip_bps", "roundtrip_bps", "rt",
                        "rt_10k_bp"):
                if key in v:
                    out[sym.upper()] = float(v[key])
                    break
    if not out:
        raise ValueError("unrecognised cost model schema; expected {SYMBOL: rt_bps|{rt_bps: ..}}")
    return out


def resolve_gate_cost(symbol: str, model: Dict[str, float]) -> Dict[str, Any]:
    """Gate cost = max(repo default, measured per-symbol). Enforced, not advisory."""
    meas = model.get(symbol.upper())
    rt = max(REPO_RT_BPS, meas) if meas is not None else REPO_RT_BPS
    return {"rt_bps": rt, "fee_bps": REPO_FEE_BPS, "slip_bps": rt / 2.0 - REPO_FEE_BPS,
            "source": "per-symbol measured" if (meas is not None and meas > REPO_RT_BPS)
            else ("repo default" if meas is not None else "repo default (symbol not in cost model)")}


def admit_declared_costs(declared_fee_bps: float, declared_slip_bps: float, symbol: str,
                         model: Dict[str, float]) -> Tuple[bool, Dict[str, Any]]:
    """Scanner admission: replaces 'exactly 5.0 / 0.5 / 11.0' with 'exactly the
    resolved gate cost for this symbol', so thin names are tested at their real cost."""
    exp = resolve_gate_cost(symbol, model)
    ok = (abs(declared_fee_bps - exp["fee_bps"]) < 1e-9
          and abs(declared_slip_bps - exp["slip_bps"]) < 1e-9)
    return ok, exp


def slippage_per_side_bps(notional_usd: float, base_bps: float = REPO_SLIP_BPS,
                          is_stop: bool = False, P: Dict[str, Any] = POLICY) -> float:
    f = math.sqrt(max(notional_usd / P["slip_ref_notional_usd"], 1.0))
    return base_bps * f * (P["slip_stop_mult"] if is_stop else 1.0)


# --------------------------------------------------------------------------- #
# Fidelity helpers (grid / maker / bar-path)
# --------------------------------------------------------------------------- #
def maker_fill_mask(side: np.ndarray, limit_px: np.ndarray, bar_high: np.ndarray,
                    bar_low: np.ndarray, tick: float, ticks_through: int = 1) -> np.ndarray:
    """Conservative maker fill: a buy limit fills only if the bar trades THROUGH it by
    `ticks_through` ticks; a sell limit likewise. Touch is not a fill."""
    buy = (side == 1) & (bar_low <= limit_px - ticks_through * tick)
    sell = (side == -1) & (bar_high >= limit_px + ticks_through * tick)
    return buy | sell


def adverse_first_path(o: float, h: float, l: float, c: float, exposure_side: int) -> List[float]:
    """Intrabar path assumption for ambiguous bars: the adverse extreme is visited
    first. Long exposure -> O, L, H, C. Short exposure -> O, H, L, C."""
    return [o, l, h, c] if exposure_side >= 0 else [o, h, l, c]


def inventory_metrics(equity_mtm: pd.Series) -> Dict[str, float]:
    e = equity_mtm.to_numpy(float)
    peak = np.maximum.accumulate(e)
    under = e < peak
    longest = cur = 0
    for u in under:
        cur = cur + 1 if u else 0
        longest = max(longest, cur)
    return {"max_dd": float((1 - e / peak).max()), "frac_time_underwater": float(under.mean()),
            "longest_underwater_bars": int(longest)}


def mark_open_inventory(entry_px: np.ndarray, qty: np.ndarray, last_px: float,
                        exit_cost_bps: float) -> float:
    """PnL of positions still open at the end of the test, marked at the last close
    with the exit cost charged -- they belong in the result, not outside it."""
    pnl = float(((last_px - entry_px) * qty).sum())
    cost = float((np.abs(qty) * last_px).sum() * exit_cost_bps / 1e4)
    return pnl - cost


# --------------------------------------------------------------------------- #
# Look-ahead audit
# --------------------------------------------------------------------------- #
def truncation_invariance(signal_fn: Callable[[pd.DataFrame], pd.Series], df: pd.DataFrame,
                          cut_fracs: Sequence[float] = (0.5, 0.7, 0.9)) -> Dict[str, Any]:
    """Signals up to bar T computed on data[:T] must equal those computed on the full
    series. Any difference means the signal used information from after T."""
    full = signal_fn(df)
    rows = []
    for f in cut_fracs:
        T = int(len(df) * f)
        part = signal_fn(df.iloc[:T])
        a = np.asarray(full.iloc[:T], float)
        b = np.asarray(part.iloc[:T], float)
        eq = np.isclose(a, b, rtol=1e-9, atol=1e-12, equal_nan=True)
        mism = int((~eq).sum())
        rows.append({"cut": T, "mismatches": mism,
                     "first_mismatch": str(df.index[:T][~eq][0]) if mism else None})
    return {"pass": all(r["mismatches"] == 0 for r in rows), "cuts": rows}


def align_htf_last_closed(ltf: pd.DataFrame, htf: pd.DataFrame, ltf_delta: pd.Timedelta,
                          htf_delta: pd.Timedelta, cols: Sequence[str]) -> pd.DataFrame:
    """Attach the last FULLY CLOSED higher-timeframe bar to each lower-timeframe bar.
    Binance indexes klines by OPEN time, so a naive merge on open time leaks the HTF
    bar's close. Knowledge time: HTF = open + htf_delta, LTF decision = open + ltf_delta."""
    L = ltf[[]].copy()
    L["_known"] = ltf.index + ltf_delta
    R = htf[list(cols)].copy()
    R["_avail"] = htf.index + htf_delta
    m = pd.merge_asof(L.sort_values("_known"), R.sort_values("_avail"),
                      left_on="_known", right_on="_avail", direction="backward")
    m.index = L.sort_values("_known").index
    return m.drop(columns=["_known", "_avail"]).reindex(ltf.index)


# --------------------------------------------------------------------------- #
# Data integrity
# --------------------------------------------------------------------------- #
def data_integrity_report(df: pd.DataFrame, tf_minutes: float,
                          P: Dict[str, Any] = POLICY) -> Dict[str, Any]:
    idx = df.index
    delta = pd.Timedelta(minutes=tf_minutes)
    dup = int(idx.duplicated().sum())
    nonmono = int((idx[1:] <= idx[:-1]).sum())
    diffs = pd.Series(idx[1:] - idx[:-1])
    gaps = diffs[diffs > delta]
    missing = int(((gaps / delta) - 1).round().sum())
    expected = (idx[-1] - idx[0]) / delta + 1
    gap_frac = missing / expected if expected else 0.0
    ohlc = df[["open", "high", "low", "close"]]
    bad_ohlc = int(((df["high"] < ohlc[["open", "close"]].max(axis=1))
                    | (df["low"] > ohlc[["open", "close"]].min(axis=1))
                    | (df["low"] > df["high"])).sum())
    nonpos = int((ohlc <= 0).any(axis=1).sum())
    zero_vol = int((df["volume"] == 0).sum()) if "volume" in df.columns else None
    rng_ = (df["high"] - df["low"]) / df["close"]
    med = rng_.median()
    mad = (rng_ - med).abs().median() * 1.4826
    wick_out = int(((rng_ - med) / mad > P["data_wick_z"]).sum()) if mad > 0 else 0
    hard = dup > 0 or nonmono > 0 or bad_ohlc > 0 or nonpos > 0 or gap_frac > P["data_gap_frac_max"]
    return {"pass": not hard, "bars": len(df), "duplicates": dup, "non_monotonic": nonmono,
            "bad_ohlc": bad_ohlc, "non_positive_prices": nonpos, "missing_bars": missing,
            "gap_frac": gap_frac, "zero_volume_bars": zero_vol,
            "wick_outliers_warn": wick_out}


def infer_funding_intervals(funding_times: pd.Series) -> Dict[str, Any]:
    """Binance funding interval is not constant across symbols or time (1h/4h/8h).
    Charge funding at the actual settlement instants from the funding history; this
    reports the modal interval and every point where it changes."""
    ft = pd.to_datetime(funding_times, utc=True).sort_values().reset_index(drop=True)
    hrs = (ft.diff().dt.total_seconds() / 3600.0).round(2)
    modal = float(hrs.mode().iloc[0]) if hrs.notna().any() else float("nan")
    changes, last = [], None
    for ts, h in zip(ft, hrs):
        if pd.isna(h):
            continue
        if last is not None and abs(h - last) > 0.05:
            changes.append({"at": str(ts), "from_h": last, "to_h": float(h)})
        last = float(h)
    return {"modal_hours": modal, "n_changes": len(changes), "changes": changes[:20]}
