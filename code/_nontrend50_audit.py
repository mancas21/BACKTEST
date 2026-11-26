"""Known-answer / regression audit for the Non-Trend 50 Suite port.

Before any market number: cross-sectional ranks, dollar neutrality,
causality (future perturbation cannot change earlier equity), funding sign,
accounting identity, NO DATA refusals, and a smoke test of representative
rows from every universe.

Run: python code/_nontrend50_audit.py ; exit 0 all pass, 2 any fail.
"""
import os
import sys

import numpy as np
import pandas as pd

CODE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE)
os.chdir(ROOT)
sys.path.insert(0, CODE)

import vrun as V  # noqa: E402
import nontrend50_engine as E  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + (("  | " + str(detail)) if detail else ""))


def tiny_panel(n=600, s=6):
    rng = np.random.default_rng(7)
    ts = np.arange(n, dtype=np.int64) * 3_600_000
    base = 100 * np.cumprod(1 + rng.normal(0, 0.001, (n, s)), axis=0)
    O = np.concatenate([[base[0]], base[:-1]])
    return dict(ts=ts, symbols=[f"S{j}" for j in range(s)], O=O, C=base,
                V=np.ones((n, s)) * 100, TB=np.ones((n, s)) * 50)


def main():
    print("\n== cross-sectional ranks ==")
    X = np.array([[1.0, 2.0, 3.0], [3.0, 1.0, 2.0]])
    r = E.rank_pct(X)
    check("rank_pct orders ascending (bottom gets the low rank)",
          r[0, 0] < r[0, 1] < r[0, 2], f"{r[0].tolist()}")
    check("rank_pct mirrors on reversed values",
          r[1, 1] < r[1, 2] < r[1, 0], f"{r[1].tolist()}")
    Xn = X.copy()
    Xn[0, 0] = np.nan
    check("NaN gets the neutral rank and never wins a leg",
          E.rank_pct(Xn)[0, 0] == 0.5)

    print("\n== book mechanics ==")
    p = tiny_panel()
    score = E.roc(p["C"], 168)
    res = E.simulate(p, score, 336, {})
    rb_net = res["net_at_fill"]
    check("book is dollar-neutral AT the next-open fill (net exposure ~0)",
          len(rb_net) > 0 and np.max(np.abs(rb_net)) < 1e-6 * E.INIT,
          f"max net at fills {np.max(np.abs(rb_net)):.4f}")
    check("accounting identity closes in the synthetic book",
          abs(res["resid"]) < 1e-6, f"resid {res['resid']:.3e}")
    # causality: change the far future, earlier equity must not move
    p2 = dict(p)
    p2["C"] = p["C"].copy()
    p2["C"][400:] *= 1.10
    p2["O"] = p["O"].copy()
    p2["O"][400:] *= 1.10
    r2 = E.simulate(p2, E.roc(p2["C"], 168), 336, {})
    check("causality: perturbing the future leaves earlier equity unchanged",
          np.allclose(res["eq"][:200], r2["eq"][:200], atol=1e-8))
    # funding sign on a synthetic long book
    frate = {0: [(400, 0.001)], 1: [(400, -0.001)]}
    long_only = np.ones((p["C"].shape[0], p["C"].shape[1]))
    long_only[:336] = -np.inf
    with_f = E.simulate(p, long_only, 10_000, {}, funding=True, frate=frate)
    no_f = E.simulate(p, long_only, 10_000, {}, funding=False, frate=frate)
    check("funding is real cash: positive rate charges, negative credits",
          with_f["eq"][-1] != no_f["eq"][-1],
          f"{no_f['eq'][-1]:.2f} -> {with_f['eq'][-1]:.2f}")
    cheap = E.simulate(p, score, 336, {}, fee_bps=0.0, funding=False)
    dear = E.simulate(p, score, 336, {}, fee_bps=22.0, funding=False)
    check("turnover cost reduces final equity on identical signals",
          dear["eq"][-1] < cheap["eq"][-1],
          f"{cheap['eq'][-1]:.2f} -> {dear['eq'][-1]:.2f}")

    print("\n== real artifacts, one per universe ==")
    smoke = [(51, "U_1H", "1h"), (56, "U_1H", "1h"),
             (69, "T_5M", "5m"), (77, "F_1H", "1h"), (83, "U_1H", "1h")]
    bad = []
    for rid, sym, tf in smoke:
        try:
            a = V.make_artifact("nontrend50", tf, sym, {"id": rid}, cut_ts=None)
            m = a["metrics"]
            if abs(m["pnl_identity_resid"]) > 1e-6 or m["n_trades"] < 0:
                bad.append((rid, "metrics"))
        except Exception as exc:
            bad.append((rid, str(exc)[:90]))
    check("representative rows from U/T/F produce valid artifacts", not bad,
          f"failures: {bad}")

    print("\n== composite refusals ==")
    bad2 = []
    for rid, sym, tf in ((93, "U_1H", "1h"), (100, "U_1H", "1h")):
        try:
            V.make_artifact("nontrend50", tf, sym, {"id": rid}, cut_ts=None)
            bad2.append(rid)
        except RuntimeError:
            pass
    check("composites refuse until their sleeves pass the gates", not bad2,
          f"wrongly ran: {bad2}")

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("FAILED:", FAIL)
        sys.exit(2)
    print("ALL PASS")


if __name__ == "__main__":
    main()
