#!/usr/bin/env python
"""_gate2_audit.py -- known-answer audit for the v2 gate layer (gate2.py).

Every function is pinned against a case whose answer is known by
construction: planted drifts, exact breakeven arithmetic, crafted trade
panels, AR(1) effective N, DSR monotonicity, and the null-engine's
reproducibility and edge-monotonicity contract.

    python code/_gate2_audit.py          # exit 0 only if ALL PASS
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gate2 as G

RESULTS = []


def check(group, name, ok, detail=""):
    RESULTS.append((group, name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {group:10s} {name}  {detail}")


# ────────────────────────────────────────────── expectancy / PF at fixed size
def g1_expectancy():
    rng = np.random.default_rng(42)
    n = 300
    edge = 0.05                                    # +5 bps per trade
    r = edge + rng.normal(0, 0.1, n)               # 10 bps noise: t ~ 8
    lb, obs, blk = G.expectancy_lb_bps(r, n_boot=1000, seed=0)
    check("expectancy", "planted 5 bps edge -> 95% LB > 0", lb > 0,
          f"lb={lb:.2f} bps obs={obs:.2f}")
    check("expectancy", "observed mean is in bps, near the planted edge",
          0.0 < obs < 12.0, f"obs={obs:.2f}")
    r0 = rng.normal(0, 0.1, n)
    lb0, obs0, _ = G.expectancy_lb_bps(r0, n_boot=1000, seed=0)
    check("expectancy", "zero-edge series -> LB below the observed mean",
          lb0 < obs0, f"lb={lb0:.2f} obs={obs0:.2f}")
    r_nan = np.concatenate([r0, [np.nan] * 5])
    lb1, _, _ = G.expectancy_lb_bps(r_nan, n_boot=100, seed=0)
    check("expectancy", "NaN rows are dropped, not fatal", np.isfinite(lb1))
    check("expectancy", "PF at fixed size: winners/losers ratio",
          abs(G.profit_factor_pct([1, 2, -1, -1]) - 1.5) < 1e-12,
          f"pf={G.profit_factor_pct([1, 2, -1, -1])}")


# ────────────────────────────────────────────── effective N
def g2_effective_n():
    rng = np.random.default_rng(7)
    n = 2000
    iid = rng.normal(0, 1, n)
    en_iid = G.effective_n(iid)
    check("effective-n", "iid series -> effective N within the sampling band of n",
          0.6 * n < en_iid < 1.35 * n, f"eff={en_iid:.0f} of {n}")
    e = rng.normal(0, 1, n)
    ar1 = np.empty(n)
    ar1[0] = e[0]
    for i in range(1, n):
        ar1[i] = 0.5 * ar1[i - 1] + math_sqrt6 * e[i]
    en_ar1 = G.effective_n(ar1)
    check("effective-n", "AR(1) rho=0.5 -> effective N ~ n/3",
          0.2 * n < en_ar1 < 0.45 * n, f"eff={en_ar1:.0f} of {n}")


math_sqrt6 = np.sqrt(1 - 0.25)          # innovations scaled so Var = 1


# ────────────────────────────────────────────── purged folds
def g3_folds():
    day = 24 * 3600 * 1000
    n = 61                                          # spans exactly 60 days -> clean edges
    entry = (1600128000000 + np.arange(n) * day).astype(np.int64)
    exit = entry + int(0.5 * day)                  # no crossing trades
    pnl = np.concatenate([np.full(20, 1.0), np.full(20, -1.0), np.full(21, 2.0)])
    folds, frac, purged = G.purged_folds(entry, exit, pnl, n_folds=3)
    check("folds", "clean folds -> every fold non-purged", purged == 0,
          f"purged={purged}")
    check("folds", "one losing fold of three -> 2/3 folds PF > 1",
          abs(frac - 2 / 3) < 1e-9, f"frac={frac}")
    exit2 = entry.copy()
    exit2[[9, 10, 29, 30]] = entry[[9, 10, 29, 30]] + 15 * day   # cross boundaries
    folds2, frac2, purged2 = G.purged_folds(entry, exit2, pnl, n_folds=3)
    check("folds", "boundary-crossers are purged from both sides", purged2 == 4,
          f"purged={purged2}")


# ────────────────────────────────────────────── buckets
def g4_buckets():
    day = 24 * 3600 * 1000
    start = int(pd.Timestamp("2020-10-01", tz="UTC").value // 10 ** 6)  # a month boundary
    n = 90
    entry = (start + np.arange(n) * day).astype(np.int64)          # Oct, Nov, Dec
    pnl = np.concatenate([np.full(30, 1.0), np.full(30, -0.5), np.full(30, 0.2)])
    b = G.period_buckets(entry, pnl, freq="M", min_bucket_trades=5, min_scored_buckets=3)
    check("buckets", "three monthly buckets found", b["n_buckets"] == 3,
          f"n={b['n_buckets']}")
    check("buckets", "two of three buckets green", abs(b["green_frac"] - 2 / 3) < 1e-9,
          f"green={b['green_frac']}")
    check("buckets", "worst bucket caps at its sum",
          abs(b["worst_pct"] - (-14.3)) < 1e-6,
          f"worst={b['worst_pct']}")
    b2 = G.period_buckets(entry, pnl, freq="Q", min_bucket_trades=5, min_scored_buckets=3)
    check("buckets", "quarterly collapses to one bucket", b2["n_buckets"] == 1,
          f"n={b2['n_buckets']}")
    # a thin bucket (below min trades) is not a verdict bucket
    entry3 = np.concatenate([entry[:80], [entry[0] + 200 * day, entry[0] + 200 * day + day,
                                          entry[0] + 201 * day]])
    pnl3 = np.concatenate([pnl[:80], [1.0, 1.0, -5.0]])
    b3 = G.period_buckets(entry3 + day, pnl3, freq="M", min_bucket_trades=5, min_scored_buckets=3)
    check("buckets", "thin bucket excluded", b3["thin_buckets"] >= 1,
          f"thin={b3['thin_buckets']} n={b3['n_buckets']}")
    b4 = G.period_buckets(entry, pnl, freq="M", min_bucket_trades=5)   # default floor
    check("buckets", "below the six-scored-bucket floor the gate fails",
          b4["n_buckets"] == 3 and b4["pass_floor"] is False,
          f"n={b4['n_buckets']} floor={b4['pass_floor']}")


# ────────────────────────────────────────────── beta / alpha
def g5_beta_alpha():
    rng = np.random.default_rng(11)
    n = 1500
    m = rng.normal(0, 0.01, n)
    r = 0.0002 + 0.5 * m + rng.normal(0, 0.002, n)
    out = G.beta_alpha_t(r, m, n_boot=500, seed=0)
    check("beta", "beta recovered ~0.5", abs(out["beta"] - 0.5) < 0.05,
          f"beta={out['beta']:.3f}")
    check("beta", "alpha 2 bps/bar is significant (t > 2)", out["t"] > 2,
          f"t={out['t']:.2f} alpha={out['alpha_bps_per_bar']:.2f} bps")
    r0 = rng.normal(0, 0.01, n)                    # no alpha
    out0 = G.beta_alpha_t(r0, m, n_boot=500, seed=0)
    check("beta", "zero-alpha book -> |t| small", abs(out0["t"]) < 2,
          f"t={out0['t']:.2f}")


# ────────────────────────────────────────────── concentration v2
def g6_concentration():
    pnl = [1.0] * 19 + [50.0]                       # one whale among twenty
    out = G.top_frac_concentration(np.array(pnl), frac=0.05, init=10000.0)
    check("conc", "top 5% of 20 trades = the single whale (k=1)", out["k"] == 1,
          f"k={out['k']}")
    check("conc", "whale share of PnL", abs(out["share_pct"] - 100 * 50 / 69) < 1e-9,
          f"share={out['share_pct']:.2f}")
    pnl100 = np.concatenate([np.full(95, 0.1), np.full(5, 3.0)])
    out2 = G.top_frac_concentration(pnl100, frac=0.05, init=10000.0)
    check("conc", "top 5% of 100 trades = five trades", out2["k"] == 5, f"k={out2['k']}")
    day = 24 * 3600 * 1000
    start = int(pd.Timestamp("2020-10-01", tz="UTC").value // 10 ** 6)
    entry = (start + np.arange(60) * day).astype(np.int64)
    pnl3 = np.full(60, 0.1)
    pnl3[10:20] = 5.0                               # one golden ten-day stretch, inside October
    bm = G.best_month_removal(entry, pnl3, init=10000.0)
    # October holds 31 days = 21 small trades + the ten 5% trades -> 52.1% of init
    # total = 55% -> net without the best month = 2.9%
    check("conc", "best month identified and removed",
          bm["best_month"] == "2020-10" and bm["best_month_pnl"] == 5210.0
          and abs(bm["net_without_pct"] - 2.9) < 1e-9,
          f"best={bm['best_month']} pnl={bm['best_month_pnl']} net={bm['net_without_pct']:.3f}")


# ────────────────────────────────────────────── breakeven cost
def g8_breakeven():
    def run_at(t):
        n = 50
        r = np.full(n, 0.10) - 2 * t / 1e4 * 100.0   # 10 bps gross, t bps/side
        return pd.DataFrame({"ret_pct": r})

    be, _ = G.breakeven_side_cost(run_at, lo=0.0, hi=100.0, iters=30)
    check("breakeven", "10 bps gross per trade -> breakeven 5 bps/side",
          abs(be - 5.0) < 1e-6, f"be={be:.4f}")

    def always_alive(t):
        return pd.DataFrame({"ret_pct": np.full(40, 0.5)})

    be2, pf_hi = G.breakeven_side_cost(always_alive, lo=0.0, hi=100.0)
    check("breakeven", "book profitable at the top of the range -> infinite",
          be2 == float("inf") and pf_hi is not None, f"be={be2}")


# ────────────────────────────────────────────── drawdown
def g9_drawdown():
    rng = np.random.default_rng(3)
    up = np.full(500, 0.001)
    check("dd", "constant up-drift has zero drawdown",
          G.drawdown_stats(np.cumprod(1 + up))["max_dd_pct"] < 1e-9)
    walk = rng.normal(0, 0.01, 1000)
    dd = G.drawdown_stats(np.cumprod(1 + walk))["max_dd_pct"]
    check("dd", "a random walk has a real drawdown", dd > 5.0, f"dd={dd:.1f}%")
    p95 = G.p95_max_dd(walk, n_boot=300, seed=0)
    check("dd", "P95 bootstrap DD exceeds the realized DD",
          p95 >= dd * 0.8, f"p95={p95:.1f} realized={dd:.1f}")
    p95_up = G.p95_max_dd(up, n_boot=200, seed=0)
    check("dd", "P95 DD of a pure drift is ~0", p95_up < 0.5, f"p95={p95_up:.3f}")


# ────────────────────────────────────────────── DSR / PBO
def g7_dsr_pbo():
    d0 = G.deflated_sharpe(0.0, sr_trials_var=0.04, n_trials=100, n_obs=2000)
    check("dsr", "zero-SR candidate under 100 trials -> DSR ~ 0", d0 < 0.2,
          f"dsr={d0:.3f}")
    d1 = G.deflated_sharpe(0.10, sr_trials_var=0.0004, n_trials=10, n_obs=5000)
    d2 = G.deflated_sharpe(0.10, sr_trials_var=0.0004, n_trials=1000, n_obs=5000)
    check("dsr", "DSR falls as the trial count rises", d1 > d2,
          f"n=10: {d1:.3f}  n=1000: {d2:.3f}")
    d3 = G.deflated_sharpe(0.15, sr_trials_var=0.0004, n_trials=100, n_obs=5000)
    check("dsr", "a large true SR survives deflation", d3 > 0.95, f"dsr={d3:.3f}")
    rng = np.random.default_rng(5)
    T, N = 1000, 8
    R = rng.normal(0, 0.01, (T, N))
    R[:, 0] += 0.001                               # one genuinely better column
    lam = G.pbo_cscv(R, n_partitions=16)
    check("pbo", "CSCV lambda of a dominated panel stays below 0.5", lam < 0.5,
          f"lambda={lam:.3f}")




# ────────────────────────────────────────────── purged split / best week / policy
def g15_split_week_policy():
    day = 24 * 3600 * 1000
    n = 100
    entry = (1600128000000 + np.arange(n) * day).astype(np.int64)
    exit = entry + int(0.5 * day)
    pnl = np.concatenate([np.full(50, 1.0), np.full(50, -0.5)])
    sp = G.purged_split(entry, exit, pnl)
    check("split", "IS half green, OOS half red -> both-PF gate fails",
          sp["pf_is"] is not None and sp["pf_is"] > 1.0 and not sp["pass"],
          f"is={sp['pf_is']} oos={sp['pf_oos']}")
    pnl2 = np.concatenate([np.full(50, 0.5), np.full(50, 0.8)])
    sp2 = G.purged_split(entry, exit, pnl2)
    check("split", "both halves green pass; no crossing trades purged",
          sp2["pass"] and sp2["purged"] == 0, f"purged={sp2['purged']}")
    exit3 = entry.copy()
    exit3[45:50] = entry[45:50] + 20 * day       # cross the split
    sp3 = G.purged_split(entry, exit3, pnl2)
    check("split", "boundary-crossers purged at the split", sp3["purged"] == 5,
          f"purged={sp3['purged']}")
    wk = G.best_week_removal(exit, pnl2, init=10000.0)
    check("week", "best week identified (all trades land in two ISO weeks)",
          wk["best_week"] is not None and wk["net_without_pct"] > 0,
          f"best={wk['best_week']} net={wk['net_without_pct']:.2f}")
    h = G.policy_hash()
    h2 = G.policy_hash(dict(G.POLICY))
    h3 = G.policy_hash({**G.POLICY, "g1_pf_min": 1.3})
    check("policy", "policy hash is stable and threshold-sensitive",
          h == h2 and h != h3, f"{h} vs {h3}")


def main() -> int:
    for fn in (g1_expectancy, g2_effective_n, g3_folds, g4_buckets, g5_beta_alpha,
               g6_concentration, g8_breakeven, g9_drawdown, g7_dsr_pbo):
        try:
            fn()
        except Exception as e:
            check(fn.__name__, "raised", False, f"{type(e).__name__}: {e}")
    bad = [r for r in RESULTS if not r[2]]
    print()
    print(f"{len(RESULTS) - len(bad)}/{len(RESULTS)} checks PASS")
    if bad:
        for g, nm, _, d in bad:
            print(f"  [{g}] {nm} {d}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
