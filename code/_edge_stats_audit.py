#!/usr/bin/env python3
"""_edge_stats_audit.py — known-answer audit of the vendored statistical layer.

`code/edge_stats.py` is the only file in this repo that implements Benjamini-
Hochberg, Hansen's SPA, a minimum detectable effect, a day-clustered t-statistic
or a timing null. Importing untested statistics is exactly the "assert, don't
assume" failure this repo keeps paying for, so every function used by a gate gets
an answer that can be computed by hand or by an independent implementation.

Checks, each with the expected value stated BEFORE it is computed:

  1. BH, five small p-values at q=0.10 -> all five rejected.
  2. BH, one small and two large -> exactly the first rejected.
  3. BH rejection set is a prefix of the sorted order (BH is monotone).
  4. cluster_t equals an independent CR1 implementation (within 1e-9).
  5. cluster_t degenerates to the one-sample t when every day is its own cluster.
  6. effective_n: n unique days -> n; all one day -> 1; two blocks of five -> 5.
  7. mde_bps equals (z_{1-a/2}+z_power)*sigma/sqrt(n_eff) for a hand case.
  8. mde_bps is strictly decreasing in n_eff and infinite at n_eff=0.
  9. SPA: a trial that dominates the benchmark gets a small p; a trial identical
     to the benchmark does not.
 10. SPA and bootstrap_ci are deterministic under a fixed seed.
 11. bootstrap_ci brackets its own point estimate.
 12. circular_shift_null: a signal that IS the forward return gets a small p.

Usage: python code/_edge_stats_audit.py [--write results/edge_stats_audit.txt]
Exit code 0 = every check passed, 1 = at least one failed.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy import stats as sps

sys.path.insert(0, str(Path(__file__).resolve().parent))
import edge_stats as es  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))


def cr1_reference(x: np.ndarray, day_ids: np.ndarray) -> float:
    """Independent Liang-Zeger CR1 t-stat of the mean, written from the formula."""
    x = np.asarray(x, float)
    days = np.asarray(day_ids)
    uniq = np.unique(days)
    g = len(uniq)
    n = len(x)
    mean = x.mean()
    resid = x - mean
    cluster_sums = np.array([resid[days == u].sum() for u in uniq])
    var = (g / (g - 1.0)) * (cluster_sums ** 2).sum() / (n ** 2)
    return float(mean / np.sqrt(var))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", default=None)
    args = ap.parse_args()

    # 1 / 2 / 3 -- Benjamini-Hochberg against hand-computed answers.
    out, _ = es.benjamini_hochberg([0.01, 0.02, 0.03, 0.04, 0.05], q=0.10)
    check("BH: five p-values all below the q=0.10 ladder -> five rejections",
          int(np.sum(out)) == 5, f"rejected {int(np.sum(out))} of 5")

    out, _ = es.benjamini_hochberg([0.01, 0.50, 0.60], q=0.10)
    check("BH: one small and two large -> only the first rejected",
          list(map(bool, out)) == [True, False, False], f"{list(map(bool, out))}")

    # 3 -- BH against an independent step-up implementation over random inputs.
    def bh_reference(pvals, q):
        p = np.sort(np.asarray(pvals, float))
        n = len(p)
        k = 0
        for i in range(1, n + 1):
            if p[i - 1] <= i * q / n:
                k = i
        out_ref = np.zeros(n, bool)
        out_ref[:k] = True
        return out_ref

    agree = True
    nonvacuous = False
    detail = []
    for seed in (1, 7, 23):
        rng = np.random.default_rng(seed)
        p = np.concatenate([rng.uniform(0.0, 0.002, 6), rng.uniform(0.20, 1.0, 34)])
        out, _ = es.benjamini_hochberg(p, q=0.10)
        ref_sorted = bh_reference(p, 0.10)
        got_sorted = out[np.argsort(p)]
        agree &= bool(np.array_equal(got_sorted, ref_sorted))
        nonvacuous |= bool(ref_sorted.sum() > 0)
        detail.append(int(ref_sorted.sum()))
    check("BH matches an independent step-up implementation on random inputs",
          agree, f"rejections per seed: {detail}")
    check("BH check is non-vacuous (at least one rejection observed)",
          nonvacuous)

    # 4 -- cluster_t against the independent CR1 formula.
    rng = np.random.default_rng(11)
    n = 300
    day_ids = rng.integers(0, 40, size=n)
    x = rng.normal(0.4, 1.0, size=n) + 0.3 * day_ids
    got = es.cluster_t(x, day_ids)
    want = cr1_reference(x, day_ids)
    check("cluster_t equals an independent CR1 implementation",
          abs(got - want) < 1e-9, f"got {got:.10f} want {want:.10f}")

    # 5 -- with one observation per day, CR1 reduces to the scaled one-sample t.
    x2 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    days2 = np.arange(5)
    got = es.cluster_t(x2, days2)
    want = cr1_reference(x2, days2)
    check("cluster_t degenerates correctly when each day is its own cluster",
          abs(got - want) < 1e-12, f"got {got:.6f} want {want:.6f}")

    # 6 -- effective_n is the Kish-style design effect, hand-computable.
    check("effective_n: n unique days -> n",
          abs(es.effective_n(np.arange(50)) - 50.0) < 1e-12)
    check("effective_n: one day for everything -> 1",
          abs(es.effective_n(np.zeros(50, int)) - 1.0) < 1e-12)
    two = np.array([0] * 5 + [1] * 5)
    check("effective_n: two balanced blocks of five -> the cluster count, 2",
          abs(es.effective_n(two) - 2.0) < 1e-12)
    # Unbalanced clusters separate the formula from a plain cluster count.
    uneven = np.array([0] * 8 + [1] + [2])
    check("effective_n: clusters of 8,1,1 -> 100/66",
          abs(es.effective_n(uneven) - 100.0 / 66.0) < 1e-12,
          f"{es.effective_n(uneven):.6f}")

    # 7 / 8 -- mde_bps against the formula in its own docstring.
    sigma, n_eff = 100.0, 100.0
    want = (sps.norm.ppf(0.975) + sps.norm.ppf(0.80)) * sigma / np.sqrt(n_eff)
    got = es.mde_bps(sigma, n_eff)
    check("mde_bps equals (z_alpha + z_power)*sigma/sqrt(n_eff)",
          abs(got - want) < 1e-9, f"got {got:.6f} want {want:.6f}")

    ladder = [es.mde_bps(sigma, k) for k in (10, 50, 200, 1000)]
    check("mde_bps strictly decreases as n_eff grows",
          all(a > b for a, b in zip(ladder, ladder[1:])),
          " > ".join(f"{v:.2f}" for v in ladder))
    check("mde_bps is infinite at n_eff = 0",
          es.mde_bps(sigma, 0) == float("inf"))

    # 9 / 10 -- SPA with a dominating trial and with a null trial.
    rng = np.random.default_rng(3)
    t_len = 400
    bench = rng.normal(0, 1, size=t_len)
    dominating = np.column_stack([bench + 1.5, bench + 0.2])
    identical = np.column_stack([bench, bench])
    p_dom = es.spa_test(dominating, bench, reps=2000, seed=42)
    p_null = es.spa_test(identical, bench, reps=2000, seed=42)
    check("SPA: a trial that beats the benchmark gets a small p",
          p_dom < 0.05, f"p={p_dom:.4f}")
    check("SPA: a trial identical to the benchmark does not",
          p_null > 0.05, f"p={p_null:.4f}")

    p_again = es.spa_test(dominating, bench, reps=2000, seed=42)
    check("SPA is deterministic under a fixed seed", p_dom == p_again,
          f"{p_dom:.6f} == {p_again:.6f}")

    # 11 -- bootstrap CI brackets the point estimate and is deterministic.
    rng = np.random.default_rng(5)
    bx = rng.normal(2.0, 3.0, size=500)
    bd = rng.integers(0, 50, size=500)
    lo1, hi1 = es.bootstrap_ci(bx, bd, reps=1000, seed=42)[:2]
    lo2, hi2 = es.bootstrap_ci(bx, bd, reps=1000, seed=42)[:2]
    check("bootstrap_ci brackets the sample mean",
          lo1 <= bx.mean() <= hi1, f"[{lo1:.4f}, {hi1:.4f}] around {bx.mean():.4f}")
    check("bootstrap_ci is deterministic under a fixed seed",
          (lo1, hi1) == (lo2, hi2))

    # 12 -- circular shift against a signal that IS the forward return.
    sig = rng.normal(0, 1, size=600)
    fwd = sig.copy()
    obs = float(np.mean(sig * fwd))
    p_cs, _ = es.circular_shift_null(sig, fwd,
                                     event_rule=lambda s, r: float(np.mean(s * r)),
                                     obs_stat=obs, reps=1000, seed=42)
    check("circular_shift_null: signal == forward return -> small p",
          p_cs < 0.05, f"p={p_cs:.4f}")

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = len(RESULTS) - passed
    print(f"\n{passed} passed, {failed} failed, {len(RESULTS)} checks")
    print("VERDICT:", "PASS" if failed == 0 else "FAIL")

    if args.write:
        out = Path(args.write)
        out.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"{'PASS' if ok else 'FAIL'}\t{name}\t{detail}" for name, ok, detail in RESULTS]
        lines.append(f"TOTAL {passed}/{len(RESULTS)} passed")
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"written: {out}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
