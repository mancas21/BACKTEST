#!/usr/bin/env python
"""gate2.py -- the v2 statistical gate layer.

WHY THIS EXISTS
    The 2026-10-27 external audit of GATES_AND_RULES.md found the v1 gate set
    (G1-G6) individually lenient, uncalibrated as a set, and blind to trial
    counts. This module implements the v2 machinery as MEASUREMENTS, per
    REGLA 0: every quantity a v2 verdict needs is computed here from raw
    trades and equity curves, with known-answer tests in `_gate2_audit.py`.

WHAT IS HERE (each maps to an audit finding)

    block_bootstrap_mean        moving-block bootstrap of a mean (M2: block,
                                not iid, bootstrap under autocorrelation)
    expectancy_lb_bps           G1v2: 95% lower bound of per-trade expectancy
                                in bps > 0 (C2), with the PF>1.2 condition
                                kept secondary
    effective_n                 G2v2 reporting: autocorrelation-adjusted N
    purged_folds                G3v2: contiguous folds split on entry time,
                                boundary-crossing trades purged from BOTH
                                adjacent folds (C3); a fold PF needs a
                                minimum trade count to count as a fold
    period_buckets              G4v2: monthly or quarterly buckets with a
                                minimum trade count per bucket and a worst-
                                bucket cap (H6)
    beta_alpha_t                G5v2: alpha of strategy bar returns vs the
                                market, OLS beta, t-stat by block bootstrap
                                (H4)
    top_frac_concentration      G6v2: remove the top 5% OF TRADES (scale-
                                free) instead of the top 5 (H5), plus
                                best-calendar-month removal
    breakeven_side_cost         G8v2: the per-side cost (bps) at which PF
                                falls to 1, by bisection with real engine
                                re-runs (H3); plus PF > 1 at 2x gate cost
    p95_max_dd                  G9v2: P95 of the bootstrapped max drawdown of
                                the mark-to-market bar-return series (H1)
    deflated_sharpe             G7: Bailey/Lopez de Prado DSR under a trial
                                count (C1)
    pbo_cscv                    G7 alternative: probability of backtest
                                overfitting via CSCV on a returns matrix

    gate2_verdict               assembles the measured booleans

CONVENTIONS
    * Per-trade quantities use ret_pct (the per-trade percentage return at the
      size actually taken), so profit factor and expectancy are defined at
      FIXED size; currency-PF under compounding is reported separately
      (audit H2: risk-based sizing reweights trades by stop distance and
      changes PF, so the PF definition must be stated).
    * Bootstrap seeds are explicit and recorded in the artifact.
    * Nothing here reads or writes artifacts; engines do that.
"""
from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np
import pandas as pd

_ND = NormalDist()

# ══════════════════════════════════════════════════ policy
# The repo's v2 gate policy. Values are ALIGNED with the reference layer
# `_gates_v2.py` POLICY (adopted 2026-10-27 from the second audit-fix
# implementation); the hash of this dict is written into every artifact so a
# threshold change is visible, never silent.
POLICY = {
    "g1_pf_min": 1.2, "g1_boot_alpha": 0.05,
    "boot_reps": 1000, "boot_seed": 20261027,
    "g2_min_trades": 100, "g2_min_per_symbol": 30, "g2_min_eff_n": 50,
    "g3_split": 0.70, "g3_min_oos_trades": 30,
    "g3_folds": 5, "g3_fold_min_trades": 10, "g3_fold_pass_frac": 0.70,
    "g4_min_bucket_trades": 5, "g4_min_scored_buckets": 6,
    "g4_pos_frac_min": 0.60, "g4_worst_bucket_min_pct": -15.0,
    "g5_alpha_t_min": 2.0,
    "g6_trim_frac": 0.05, "g6_min_k": 5,
    "g8_cost_mult": 2.0, "g8_cost_share_max": 0.35,
    "g9_dd_p95_max_pct": 35.0, "g9_mmr": 0.005,
}


def policy_hash(policy=None):
    import hashlib, json
    p = POLICY if policy is None else policy
    blob = json.dumps(p, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


# ══════════════════════════════════════════════════ bootstrap core
def block_bootstrap_mean(x, n_boot=1000, block=None, seed=0):
    """Moving-block bootstrap of the mean. Returns (means, observed, block)."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n == 0:
        return np.array([]), float("nan"), 0
    if block is None:
        block = max(1, int(round(n ** (1.0 / 3.0))))
    block = min(block, n)
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(n_boot, nb))
    offsets = np.arange(block)[None, None, :]
    # Chunked on purpose (2026-10-27): the full (n_boot, nb, block) index cube
    # plus x[idx] costs about 2 * n_boot * n * 8 bytes, i.e. 5-8 GiB per worker
    # on 1m bars. Three parallel pmatrix workers exhausted the page file
    # (System Event 2004, 17.5 GiB each). Same draws, same means (verified
    # bit-identical); peak memory is now chunk/n_boot of the old peak.
    means = np.empty(n_boot, dtype=float)
    for i in range(0, n_boot, 16):
        s = starts[i:i + 16]
        idx = (s[:, :, None] + offsets).reshape(s.shape[0], -1)[:, :n]
        means[i:i + 16] = x[idx].mean(axis=1)
    return means, float(x.mean()), int(block)


def _ci_lb(means, alpha=0.05):
    if len(means) == 0:
        return float("nan")
    return float(np.percentile(means, 100.0 * alpha / 2.0))


# ══════════════════════════════════════════════════ G1v2 / C2
def expectancy_lb_bps(ret_pct, n_boot=1000, seed=0, block=None):
    """95% lower bound of the per-trade expectancy, in bps, block-bootstrapped.

    `ret_pct` is the per-trade percentage return at the size taken; bps =
    ret_pct * 100. The gate is LB > 0."""
    means, obs, blk = block_bootstrap_mean(np.asarray(ret_pct, float) * 100.0,
                                           n_boot=n_boot, block=block, seed=seed)
    return _ci_lb(means), float(obs), blk


def profit_factor_pct(ret_pct):
    """PF on per-trade percentage returns at fixed size (audit H2)."""
    r = np.asarray(ret_pct, float)
    r = r[~np.isnan(r)]
    g = float(r[r > 0].sum())
    l = float(-r[r < 0].sum())
    if l <= 0:
        return float("inf") if g > 0 else 0.0
    return g / l


# ══════════════════════════════════════════════════ G2v2 / M2
def effective_n(x, max_lag=10):
    """Autocorrelation-adjusted sample size: n / (1 + 2*sum rho_k), floored at 1."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 3:
        return float(n)
    d = x - x.mean()
    var = float((d * d).sum())
    denom = 1.0
    for k in range(1, min(max_lag, n - 1) + 1):
        if var <= 0:
            break
        rho = float((d[k:] * d[:-k]).sum() / var)
        denom += 2.0 * rho
    return float(n / max(denom, 1.0))


# ══════════════════════════════════════════════════ G3v2 / C3
def purged_split(entry_ts, exit_ts, pnl_pct, frac=0.70, min_oos=30):
    """The purged 70/30 split: a trade whose holding period crosses the split
    is removed from BOTH sides (purged from the in-sample half, and it cannot
    enter the out-of-sample half because its entry precedes the split)."""
    e = np.asarray(entry_ts, np.int64)
    x = np.asarray(exit_ts, np.int64)
    p = np.asarray(pnl_pct, float)
    if len(e) == 0:
        return {"pf_is": None, "pf_oos": None, "n_is": 0, "n_oos": 0,
                "purged": 0, "pass": False}
    lo, hi = int(e.min()), int(e.max())
    split = lo + int((hi - lo) * frac)
    in_is = e < split
    crossing = in_is & (x >= split)
    is_m = in_is & (~crossing)
    oos_m = ~in_is
    pf_is = profit_factor_pct(p[is_m]) if is_m.any() else None
    pf_oos = profit_factor_pct(p[oos_m]) if oos_m.any() else None

    def _fin(v):
        return v is not None and np.isfinite(v) and v > 1.0

    ok = bool(_fin(pf_is) and _fin(pf_oos) and int(oos_m.sum()) >= min_oos)
    return {"pf_is": None if pf_is is None or not np.isfinite(pf_is) else round(pf_is, 4),
            "pf_oos": None if pf_oos is None or not np.isfinite(pf_oos) else round(pf_oos, 4),
            "n_is": int(is_m.sum()), "n_oos": int(oos_m.sum()),
            "purged": int(crossing.sum()), "pass": ok}


def purged_folds(entry_ts, exit_ts, pnl_pct, n_folds=5, min_fold_trades=10):
    """Contiguous folds split on entry time; a trade whose holding period
    crosses a fold boundary is purged from BOTH adjacent folds (C3).

    Returns (fold list with pf, n, purged flag, fraction of non-empty folds
    with PF > 1, purged count)."""
    e = np.asarray(entry_ts, np.int64)
    x = np.asarray(exit_ts, np.int64)
    p = np.asarray(pnl_pct, float)
    if len(e) == 0:
        return [], 0.0, 0
    lo, hi = int(e.min()), int(e.max())
    if hi <= lo:
        return [], 0.0, 0
    edges = lo + (hi - lo) * np.arange(n_folds + 1, dtype=np.int64) // n_folds
    fold_of = np.clip(np.searchsorted(edges, e, side="right") - 1, 0, n_folds - 1)
    crossing = np.zeros(len(e), dtype=bool)
    for j in range(n_folds - 1):
        crossing |= (fold_of == j) & (x >= edges[j + 1])
    folds = []
    for j in range(n_folds):
        m = (fold_of == j) & (~crossing)
        pn = p[m]
        pf = profit_factor_pct(pn) if len(pn) else None
        folds.append({"fold": j, "n": int(m.sum()), "purged": False,
                      "pf": None if pf is None else (None if not np.isfinite(pf) else round(pf, 4)),
                      "no_losses": bool(len(pn) and (pn >= 0).all())})
    # a fold whose trades were all purged is reported purged
    for j in range(n_folds):
        raw = int((fold_of == j).sum())
        if folds[j]["n"] < min_fold_trades:
            folds[j]["purged"] = bool(raw > 0 and folds[j]["n"] < raw) or folds[j]["n"] == 0
    ok = [f for f in folds if not f["purged"] and f["n"] >= min_fold_trades]
    good = [f for f in ok if (f["pf"] is not None and f["pf"] > 1.0) or f["no_losses"]]
    frac = float(len(good) / len(ok)) if ok else 0.0
    return folds, frac, int(crossing.sum())


# ══════════════════════════════════════════════════ G4v2 / H6
def period_buckets(exit_ts, pnl_pct, freq="M", min_bucket_trades=5,
                   worst_bucket_cap_pct=-15.0, init=10000.0,
                   min_scored_buckets=6):
    """Calendar buckets (M or Q) of PnL by EXIT time, with a minimum trade
    count per bucket and a floor on the number of scored buckets.

    A bucket with fewer than `min_bucket_trades` trades is not counted as a
    verdict bucket (reported as thin). Fewer than `min_scored_buckets` scored
    buckets is a FAIL (insufficient sample, not a pass). Gate: >= 60% of
    verdict buckets green AND the worst bucket loses no more than
    `worst_bucket_cap_pct` % of starting capital."""
    e = pd.to_datetime(np.asarray(exit_ts, np.int64), unit="ms", utc=True)
    if freq == "M":
        key = e.to_period("M")
    else:
        key = e.to_period("Q")
    s = pd.Series(np.asarray(pnl_pct, float) / 100.0 * init, index=key)
    g = s.groupby(level=0).agg(["sum", "count"])
    full = g[g["count"] >= min_bucket_trades]
    thin = int(len(g) - len(full))
    if len(full) < min_scored_buckets:
        return {"buckets": [], "green_frac": 0.0, "worst_pct": float("nan"),
                "thin_buckets": thin, "n_buckets": int(len(full)),
                "pass_floor": False}
    green = float((full["sum"] > 0).mean())
    worst = float(full["sum"].min() / init * 100.0)
    return {"buckets": [{"period": str(k), "pnl": round(float(v["sum"]), 2),
                         "n": int(v["count"])} for k, v in full.iterrows()],
            "green_frac": green, "worst_pct": worst, "thin_buckets": thin,
            "n_buckets": int(len(full)), "pass_floor": True}


# ══════════════════════════════════════════════════ G5v2 / H4
def beta_alpha_t(strat_bar_ret, mkt_bar_ret, n_boot=1000, seed=0, block=None):
    """Alpha of strategy bar returns vs market bar returns: OLS beta, then the
    t-stat of the mean alpha series by moving-block bootstrap (H4)."""
    r = np.asarray(strat_bar_ret, float)
    m = np.asarray(mkt_bar_ret, float)
    n = min(len(r), len(m))
    r, m = r[:n], m[:n]
    ok = np.isfinite(r) & np.isfinite(m)
    r, m = r[ok], m[ok]
    if len(r) < 10 or float(m.var()) <= 0:
        return {"beta": float("nan"), "alpha_bps_per_bar": float("nan"),
                "t": float("nan")}
    beta = float(np.cov(r, m, ddof=0)[0, 1] / m.var())
    a = r - beta * m
    means, obs, blk = block_bootstrap_mean(a, n_boot=n_boot, block=block, seed=seed)
    se = float(np.std(means, ddof=1)) if len(means) > 1 else float("nan")
    t = float(obs / se) if se and se > 0 and np.isfinite(se) else float("nan")
    return {"beta": beta, "alpha_bps_per_bar": float(obs * 1e4), "t": t,
            "alpha_boot_seed": seed, "alpha_block": blk}


# ══════════════════════════════════════════════════ G6v2 / H5
def top_frac_concentration(pnl_pct, frac=0.05, init=10000.0):
    """Remove the top `frac` FRACTION of trades (>= 1), scale-free (H5)."""
    p = np.asarray(pnl_pct, float)
    p = p[~np.isnan(p)]
    n = len(p)
    if n == 0:
        return {"k": 0, "share_pct": 0.0, "net_without_pct": 0.0}
    k = max(1, int(math.ceil(frac * n)))
    s = np.sort(p)[::-1]
    tot = float(p.sum())
    share = float(100.0 * s[:k].sum() / tot) if tot != 0 else 0.0
    net_without = float(100.0 * (tot - s[:k].sum()) / init)
    return {"k": int(k), "share_pct": share, "net_without_pct": net_without}


def best_month_removal(entry_ts, pnl_pct, init=10000.0):
    """Net after removing the single best calendar month of PnL (H5)."""
    e = pd.to_datetime(np.asarray(entry_ts, np.int64), unit="ms", utc=True)
    s = pd.Series(np.asarray(pnl_pct, float) / 100.0 * init, index=e.to_period("M"))
    gm = s.groupby(level=0).sum()
    if len(gm) == 0:
        return {"best_month": None, "best_month_pnl": 0.0, "net_without_pct": 0.0}
    best = gm.max()
    tot = float(gm.sum())
    return {"best_month": str(gm.idxmax()), "best_month_pnl": round(float(best), 2),
            "net_without_pct": float(100.0 * (tot - best) / init)}


def best_week_removal(exit_ts, pnl_pct, init=10000.0):
    """Net after removing the single best ISO week of PnL (H5: clustered wins
    from one event are concentration too)."""
    e = pd.to_datetime(np.asarray(exit_ts, np.int64), unit="ms", utc=True)
    key = e.strftime("%G-%V")
    s = pd.Series(np.asarray(pnl_pct, float) / 100.0 * init, index=key)
    gw = s.groupby(level=0).sum()
    if len(gw) == 0:
        return {"best_week": None, "best_week_pnl": 0.0, "net_without_pct": 0.0}
    best = gw.max()
    tot = float(gw.sum())
    return {"best_week": str(gw.idxmax()), "best_week_pnl": round(float(best), 2),
            "net_without_pct": float(100.0 * (tot - best) / init)}


# ══════════════════════════════════════════════════ G8v2 / H3
def breakeven_side_cost(run_at_cost, lo=0.0, hi=200.0, iters=9):
    """Per-side total cost in bps at which PF falls to 1, by bisection.

    `run_at_cost(t)` must re-run the engine at `t` bps per side and return a
    trades frame with a `ret_pct` column (real re-runs, not algebra: slippage
    moves fill prices, so the response is not linear)."""
    def pf_of(t):
        tr = run_at_cost(t)
        r = tr["ret_pct"].to_numpy(float) if len(tr) else np.array([])
        return profit_factor_pct(r)

    pf_hi = pf_of(hi)
    if pf_hi >= 1.0:
        return float("inf"), pf_hi      # profitable even at the top of the range
    pf_lo = pf_of(lo)
    if pf_lo <= 1.0:
        return 0.0, pf_lo               # dead at zero cost
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if pf_of(mid) > 1.0:
            lo = mid
        else:
            hi = mid
    return float(0.5 * (lo + hi)), None


# ══════════════════════════════════════════════════ G9v2 / H1
def p95_max_dd(bar_returns, n_boot=1000, seed=0, block=None):
    """P95 of the max drawdown distribution under a moving-block bootstrap of
    the mark-to-market bar returns (H1)."""
    r = np.asarray(bar_returns, float)
    r = r[np.isfinite(r)]
    if len(r) < 10:
        return float("nan")
    rng = np.random.default_rng(seed)
    n = len(r)
    blk_n = max(1, int(round(n ** (1.0 / 3.0)))) if block is None else block
    nb = int(np.ceil(n / blk_n))
    dds = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, n - blk_n + 1, size=nb)
        idx = (starts[:, None] + np.arange(blk_n)[None, :]).reshape(-1)[:n]
        eq = np.cumprod(1.0 + r[idx])
        peak = np.maximum.accumulate(eq)
        dds[b] = -100.0 * ((eq - peak) / peak).min()
    return float(np.percentile(dds, 95))


def drawdown_stats(curve):
    """Max drawdown % and the longest underwater span, in bars (H1)."""
    c = np.asarray(curve, float)
    peak = np.maximum.accumulate(c)
    dd = (c - peak) / np.where(peak > 0, peak, 1.0)
    underwater = dd < 0
    longest = 0
    cur = 0
    for u in underwater:
        cur = cur + 1 if u else 0
        longest = max(longest, cur)
    return {"max_dd_pct": float(-100.0 * dd.min()), "longest_underwater_bars": int(longest)}


# ══════════════════════════════════════════════════ G7 / C1
def deflated_sharpe(sr, sr_trials_var, n_trials, n_obs, skew=0.0, kurt=3.0):
    """Bailey / Lopez de Prado Deflated Sharpe Ratio.

    `sr` is the candidate's Sharpe (per-bar, not annualized), `sr_trials_var`
    the across-trial variance of the trials' Sharpes, `n_obs` the number of
    return observations behind `sr`. Returns the probability that the true SR
    exceeds the expected maximum SR of `n_trials` zero-edge trials."""
    if n_trials < 2 or n_obs < 2 or sr_trials_var <= 0:
        return float("nan")
    g = 0.5772156649015329
    z = _ND.inv_cdf(1.0 - 1.0 / n_trials)
    z2 = _ND.inv_cdf(1.0 - 1.0 / (n_trials * math.e))
    sr0 = math.sqrt(sr_trials_var) * ((1.0 - g) * z + g * z2)
    denom = math.sqrt(max(1e-12, 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr))
    return float(_ND.cdf((sr - sr0) * math.sqrt(n_obs - 1) / denom))


def pbo_cscv(returns_matrix, n_partitions=16):
    """Probability of backtest overfitting via CSCV (Bailey et al.).

    `returns_matrix` is (T x N_candidates) of per-bar returns. Returns the
    distribution-free lambda estimate: the relative rank of the selected
    candidate out-of-sample, averaged over all symmetric combinations."""
    R = np.asarray(returns_matrix, float)
    T, N = R.shape
    if T < n_partitions * 2 or N < 2:
        return float("nan")
    base = T % n_partitions
    if base:
        R = R[base:]
        T = R.shape[0]
    sub = np.array_split(np.arange(T), n_partitions)
    lambdas = []
    combos = _cscv_combos(n_partitions)
    for train_mask in combos:
        is_set = np.concatenate([sub[i] for i in range(n_partitions) if train_mask[i]])
        oos_set = np.concatenate([sub[i] for i in range(n_partitions) if not train_mask[i]])
        mu_is = R[is_set].mean(axis=0)
        best_is = int(np.argmax(mu_is))
        mu_oos = R[oos_set].mean(axis=0)
        order = pd.Series(mu_oos).rank(ascending=False).to_numpy()
        n_oos = len(oos_set)
        omega = (order[best_is] - 0.5) / n_oos
        lambdas.append(omega)
    lambdas = np.asarray(lambdas)
    return float(lambdas.mean())


def _cscv_combos(s):
    from itertools import combinations
    out = []
    choose = s // 2
    for idx in combinations(range(s), choose):
        mask = [False] * s
        for i in idx:
            mask[i] = True
        out.append(mask)
    return out


# ══════════════════════════════════════════════════ v1 gates (shared semantics)
def v1_gates(trades_df, m, years):
    """The G1-G6 semantics of the pack50/pack50b engines, on measured inputs."""
    good_years = sum(1 for v in years.values() if v > 0)
    tot_years = len(years)
    pf = m["pf_pct"]
    g1 = bool((pf is not None and np.isfinite(pf) and pf > 1.2) or
              (m.get("no_losses") and m["return_pct"] > 0))
    halves = [m["is_pf"], m["os_pf"]]
    g3 = bool(all((h is not None and h > 1.0) or
                  (h is None and m.get("no_losses")) for h in halves))
    return {
        "g1_pf": g1,
        "g2_n": bool(m["n_trades"] >= 30),
        "g3_halves": g3,
        "g4_years": bool(tot_years > 0 and good_years >= (2.0 / 3.0) * tot_years),
        "g5_beats_bh": bool(m["return_pct"] > m["bh_return_pct"]),
        "g6_conc": bool(m["conc_net_without_top5_pct"] > 0),
    }
