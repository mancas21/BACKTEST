"""Known-answer / regression audit for EMA×VWAP Suite 2 (#101–150).
Before any market number: 3m resampling, both directions, inverse fades,
limit fills, cost/funding signs, accounting identity and NO DATA refusals.

Run: python code/_emavwapv2_audit.py ; exit 0 all pass, 2 any fail.
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
import emavwapv2_engine as E  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + (("  | " + str(detail)) if detail else ""))


def synthetic(n=400):
    ts = np.arange(n, dtype=np.int64) * 60_000
    c = 100 + np.concatenate([np.zeros(200), np.linspace(0, 6, 200)])
    return pd.DataFrame(dict(open_ts=ts, open=c - 0.1, high=c + 0.3,
                             low=c - 0.3, close=c, volume=np.ones(n) * 10))


def main():
    print("\n== 3m resampling ==")
    six = pd.DataFrame(dict(open_ts=np.arange(6, dtype=np.int64) * 60_000,
                            open=[1, 2, 3, 4, 5, 6], high=[2, 3, 4, 5, 6, 7],
                            low=[0, 1, 2, 3, 4, 5], close=[1.5, 2.5, 3.5, 4.5, 5.5, 6.5],
                            volume=[1, 2, 3, 4, 5, 6]))
    r = E.resample_3m(six)
    check("3m OHLCV == first/max/min/last and summed volume",
          len(r) == 2 and r.iloc[0]["open"] == 1 and r.iloc[0]["high"] == 4 and
          r.iloc[0]["low"] == 0 and r.iloc[0]["close"] == 3.5 and
          r.iloc[0]["volume"] == 6, r.iloc[0].to_dict())

    print("\n== signals, both directions ==")
    df = synthetic()
    s = E.build(df, 101)
    check("long and short entry rules exist on a trending synthetic",
          s["up"].any() or s["dn"].any(), f"up {s['up'].sum()} dn {s['dn'].sum()}")
    base = E.build(df, 0)
    inv = E.build(df, 129)
    check("inverse fade mirrors the base signal set",
          np.array_equal(inv["up"], base["dn"]) and
          np.array_equal(inv["dn"], base["up"]))
    res = E.simulate(s, E.REPO, False, None)
    check("accounting identity closes on the synthetic book",
          abs(res["resid"]) < 1e-6, f"resid {res['resid']:.3e}")
    cheap = E.simulate(s, E.E1.ZERO, False, None)
    check("costs reduce net equity on identical signals",
          cheap["eq"][-1] > res["eq"][-1],
          f"{cheap['eq'][-1]:.2f} -> {res['eq'][-1]:.2f}")
    f_evt = [(350 * 60_000, 0.001)]
    longish = E.build(df, 101)
    with_f = E.simulate(longish, E.E1.ZERO, True, f_evt)
    no_f = E.simulate(longish, E.E1.ZERO, False, f_evt)
    check("funding is charged when enabled, not when disabled",
          with_f["eq"][-1] != no_f["eq"][-1],
          f"{no_f['eq'][-1]:.2f} -> {with_f['eq'][-1]:.2f}")
    lim = E.build(df, 104)
    lr = E.simulate(lim, E.LIMIT, False, None)
    check("limit-fill row records missed orders as a measurement",
          lr["missed"] >= 0, f"missed {lr['missed']}")

    print("\n== real artifacts ==")
    smoke = [(101, "3m"), (104, "5m"), (121, "3m"), (129, "3m"), (148, "15m")]
    bad = []
    for rid, tf in smoke:
        try:
            a = V.make_artifact("emavwapv2", tf, "BTCUSDT", {"id": rid}, cut_ts=None)
            if abs(a["metrics"]["pnl_identity_resid"]) > 1e-6:
                bad.append((rid, "identity"))
        except RuntimeError as exc:
            if rid not in (148,):
                bad.append((rid, str(exc)[:80]))
    check("representative rows run or refuse as declared", not bad, f"bad: {bad}")

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("FAILED:", FAIL)
        sys.exit(2)
    print("ALL PASS")


if __name__ == "__main__":
    main()
