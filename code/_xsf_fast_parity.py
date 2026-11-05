"""_xsf_fast_parity.py — validates xs_core_fast.simulate against the PINNED
xs_factor_c_engine._simulate on the FUNDGATE card, and measures the speedup.

Dev audit (like _cbpack_funding_parity.py), not an artifact: it writes no
run artifacts and changes no pinned file. PASS criteria:
  * structural trade equality (sym, dir, entry_ts, exit_ts, count);
  * per-trade net bps and equity curve within 1e-6 relative / 1e-8 absolute;
  * derived metrics (maxDD, turnover, funding paid, exposure) within 1e-6 rel;
  * fast core deterministic across two runs (exact JSON equality).
"""

import json
import sys
import time

import numpy as np

sys.path.insert(0, "code")
import xs_factor_c_engine as xsc
import xs_core_fast as fast


def rel(a, b):
    return abs(a - b) / max(abs(b), 1e-12)


def main():
    UNI = xsc.UNIVERSE
    klines = [f"data/binance_klines_1h/{s}_1h.csv" for s in UNI]
    fund_files = [f"data/binance_funding/{s}_funding.json" for s in UNI]

    t0 = time.perf_counter()
    idx, close_w, open_w = xsc._load_frames_7(klines)
    t_load = time.perf_counter() - t0
    logret = np.log(close_w).diff()
    funding, rate8h = xsc._load_funding(fund_files, idx)
    lb, reb, cost_rate = 336, 336, 5.5e-4
    sig = close_w / close_w.shift(lb) - 1.0
    long_ok = rate8h <= 0.0
    short_ok = rate8h > 0.0
    funded = rate8h.notna()
    sig.attrs["lb"] = lb
    sig.attrs["asc"] = False

    fails = []

    # ---- pinned engine (net regime) ----
    t0 = time.perf_counter()
    eqP, trP, dP = xsc._simulate(close_w, open_w, sig, reb, cost_rate,
                                 long_ok=long_ok, short_ok=short_ok,
                                 funded=funded, funding=funding,
                                 charge_funding=True)
    t_pin = time.perf_counter() - t0

    # ---- fast core (net regime, twice for determinism) ----
    t0 = time.perf_counter()
    eqF, trF, dF = fast.simulate(close_w, open_w, sig, reb, cost_rate,
                                 long_ok=long_ok, short_ok=short_ok,
                                 funded=funded, funding=funding,
                                 charge_funding=True, min_elig=xsc.MIN_ELIG,
                                 k_fixed=2)
    t_fast = time.perf_counter() - t0
    eqF2, trF2, dF2 = fast.simulate(close_w, open_w, sig, reb, cost_rate,
                                    long_ok=long_ok, short_ok=short_ok,
                                    funded=funded, funding=funding,
                                    charge_funding=True, min_elig=xsc.MIN_ELIG,
                                    k_fixed=2)
    t_det = json.dumps(dF, sort_keys=True) == json.dumps(dF2, sort_keys=True) \
        and json.dumps(eqF.tolist()) == json.dumps(eqF2.tolist()) \
        and json.dumps(trF) == json.dumps(trF2)

    print(f"load+signals: {t_load:.2f}s   pinned sim: {t_pin:.2f}s   "
          f"fast sim: {t_fast:.3f}s   speedup: {t_pin / t_fast:.1f}x   "
          f"deterministic: {t_det}")
    if not t_det:
        fails.append("determinism")

    # structural trade equality
    if len(trP) != len(trF):
        fails.append(f"trade count {len(trP)} vs {len(trF)}")
    else:
        for a, b in zip(trP, trF):
            for k in ("sym", "dir", "entry_ts", "exit_ts", "entry_pos", "exit_pos"):
                if a[k] != b[k]:
                    fails.append(f"trade struct {k}: {a[k]} vs {b[k]}")
                    break
            d = rel(a["net_ret_notional_bps"], b["net_ret_notional_bps"])
            if d > 1e-6:
                fails.append(f"trade bps rel {d:.2e}")

    # equity curve
    d_eq = float(np.max(np.abs(eqP - eqF)))
    print(f"equity max abs diff: {d_eq:.3e}")
    if d_eq > 1e-8:
        fails.append(f"equity diff {d_eq:.2e}")

    # diag parity
    for k in ("turnover_notional", "funding_paid_usd", "fund_events_billed",
              "n_decisions", "deferred_fills", "nan_mark_bars",
              "avg_gross_exposure_pct", "first_active_pos"):
        a, b = dP[k], dF[k]
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if a == b:
                continue
            if rel(a, b) > 1e-6:
                fails.append(f"diag {k}: {a} vs {b}")
        elif a != b:
            fails.append(f"diag {k}: {a} vs {b}")

    # derived: maxDD and per-trade pf from both engines
    ddP, ddF = xse_dd(eqP), xse_dd(eqF)
    if rel(abs(ddP), abs(ddF)) > 1e-6:
        fails.append(f"maxDD {ddP:.6f} vs {ddF:.6f}")

    # ---- no-funding regime parity ----
    eqPn, trPn, dPn = xsc._simulate(close_w, open_w, sig, reb, 0.0,
                                    long_ok=long_ok, short_ok=short_ok,
                                    funded=funded, funding=funding,
                                    charge_funding=False)
    eqFn, trFn, dFn = fast.simulate(close_w, open_w, sig, reb, 0.0,
                                    long_ok=long_ok, short_ok=short_ok,
                                    funded=funded, funding=funding,
                                    charge_funding=False, min_elig=xsc.MIN_ELIG,
                                    k_fixed=2)
    d_eqn = float(np.max(np.abs(eqPn - eqFn)))
    print(f"no-funding regime equity max abs diff: {d_eqn:.3e}")
    if d_eqn > 1e-8:
        fails.append(f"no-funding equity diff {d_eqn:.2e}")
    if len(trPn) != len(trFn):
        fails.append("no-funding trade count")

    # cross-check against the PINNED ARTIFACT (FUNDGATE main) for the net regime
    art = json.load(open("results/runs/f8c556f2a7d194c3.json", encoding="utf-8"))
    m = art["metrics"]
    dd_fast = xse_dd(eqF)
    for k, v in (("return_pct", (eqF[-1] - 1.0) * 100.0),
                 ("max_dd_pct", dd_fast),
                 ("n_trades", len(trF))):
        a = m[k]
        if isinstance(a, int) and isinstance(v, int):
            okk = a == v
        else:
            okk = rel(float(a), float(v)) < 1e-6
        print(f"vs artifact {k}: artifact={a} fast={round(float(v), 4)} "
              f"{'OK' if okk else 'MISMATCH'}")
        if not okk:
            fails.append(f"artifact {k}")

    print()
    if fails:
        print("PARITY FAIL:", fails)
        return 1
    print("PARITY OK: fast core reproduces the pinned engine within tolerance")
    return 0


def xse_dd(eq):
    import xs_factor_engine as xse
    return xse._max_dd(eq)


if __name__ == "__main__":
    sys.exit(main())
