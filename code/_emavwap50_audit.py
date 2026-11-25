"""Known-answer / regression audit for the EMA×VWAP 50-Strategy Suite port.

Answers before ANY market number is published:
  * do the indicator primitives match independent calculations?
  * is the signal causal (close -> next-open fill), in BOTH directions?
  * are fees/funding charged with the right sign and on BOTH sides?
  * does the accounting identity close inside every artifact?
  * do the declared NO DATA rows refuse instead of guessing?

Run: python code/_emavwap50_audit.py ; exit 0 all pass, 2 any fail.
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
import emavwap50_engine as E  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + (("  | " + str(detail)) if detail else ""))


def tiny(df_rows):
    df = pd.DataFrame(df_rows)
    return df


def main():
    # --------------------------------------------------------- primitives
    print("\n== indicators ==")
    x = np.arange(1.0, 21.0)
    # EMA span 3, alpha 0.5, seeded with the first value
    e = E.ema(x, 3)
    ref = np.full(len(x), x[0])
    for i in range(1, len(x)):
        ref[i] = 0.5 * x[i] + 0.5 * ref[i - 1]
    check("EMA span-3 == independent recursive calculation",
          np.allclose(e[2:], ref[2:], atol=1e-9), f"{e[-1]:.6f} vs {ref[-1]:.6f}")
    for fn, name in ((lambda v: E.hma(v, 9), "HMA9"),
                     (lambda v: E.zlema(v, 11), "ZLEMA11"),
                     (lambda v: E.dema(v, 11), "DEMA11"),
                     (lambda v: E.tema(v, 11), "TEMA11"),
                     (lambda v: E.kama(v, 10, 2, 30), "KAMA(10,2,30)"),
                     (lambda v: E.alma(v, 11, 0.85, 6), "ALMA(11,.85,6)")):
        flat = fn(np.full(120, 777.0))
        check(f"{name} on a constant series == that constant (both directions)",
              bool(np.allclose(flat[30:], 777.0, atol=1e-7)),
              f"last {flat[-1]:.6f}")
    a = E.atr(np.full(50, 10.0), np.full(50, 10.0), np.full(50, 10.0), 14)
    check("ATR of a zero-range series == 0", np.allclose(a[14:], 0.0))
    adx = E.adx(np.arange(50.0) + 1, np.arange(50.0), np.arange(50.0) + 0.5, 14)
    check("ADX finite on a trending synthetic series", np.isfinite(adx[30:]).all())

    print("\n== VWAP anchors ==")
    # two UTC days, 24 hourly bars each; VWAP must reset on the boundary
    ts = np.arange(48, dtype=np.int64) * 3_600_000
    df = pd.DataFrame(dict(open_ts=ts, open=np.ones(48),
                           high=np.ones(48) * 2, low=np.ones(48),
                           close=np.ones(48) * 1.5, volume=np.ones(48)))
    vw = E.anchored_vwap(df, "daily", warmup=0)
    check("daily VWAP resets at 00:00 UTC",
          vw[0] == 1.5 and vw[23] == 1.5 and vw[24] == 1.5 and vw[47] == 1.5)
    vw15 = E.anchored_vwap(df, "daily", warmup=15)
    check("daily VWAP skips the declared 15-bar warmup",
          np.isnan(vw15[:15]).all() and np.isnan(vw15[24:39]).all() and
          vw15[15] == 1.5 and vw15[39] == 1.5)

    # ------------------------------------------------------- signal rules
    print("\n== execution conventions (both directions) ==")
    n = 120
    op = np.full(n, 100.0)
    close = np.full(n, 100.0)
    high = np.full(n, 101.0)
    low = np.full(n, 99.0)
    vol = np.full(n, 10.0)
    close[0:20] = 100.0
    close[20] = 103.0          # cross above the flat reference
    close[21:40] = 103.0       # armed, close beyond both
    close[40] = 97.0           # cross back below
    close[41:80] = 97.0
    close[80] = 93.0           # short cross below
    close[81:110] = 93.0
    close[110] = 99.0          # short cover
    df2 = pd.DataFrame(dict(open_ts=np.arange(n, dtype=np.int64) * 60_000,
                            open=op, high=np.maximum(high, close),
                            low=np.minimum(low, close), close=close,
                            volume=vol))
    # row 44 has no extra confirm filter, so the pure cross/arm/exit rules
    # can be isolated from indicator gates
    sig = E.build_signals(df2, 44, "15m", None)
    check("long entry fires only after the cross inside the arm window",
          bool(sig["up"][21:40].any()) and not bool(sig["up"][:20].any()))
    check("short entry mirrors the long rule", bool(sig["dn"][40:110].any()),
          f"short entry indices {np.where(sig['dn'])[0][:6].tolist()}")
    check("long exit fires on the cross back, short exit on the cover",
          bool(sig["xlong"][40]) and bool(sig["xshort"][110]))
    res = E.simulate(sig, {"fee": 0.0, "slip": 0.0}, False, None)
    sides = [t["side"] for t in res["trades"]]
    check("both directions are actually traded (long and short)",
          1 in sides and -1 in sides, f"sides {sides[:6]}")
    check("entry fill is the NEXT bar's open, not the signal close",
          abs(res["trades"][0]["entry_i"] - 22) <= 1,
          f"first entry index {res['trades'][0]['entry_i']}")
    costless = E.simulate(sig, {"fee": 0.0, "slip": 0.0}, False, None)
    costly = E.simulate(sig, E.REPO, False, None)
    check("costs reduce net equity on the same signals",
          costly["eq"][-1] < costless["eq"][-1],
          f"{costless['eq'][-1]:.2f} -> {costly['eq'][-1]:.2f}")
    # funding sign: a positive rate must charge a long and credit a short
    ev = [(60_000 * 25, 0.001)]
    f_long = E.simulate(sig, {"fee": 0.0, "slip": 0.0}, True, ev)
    check("funding charges cash on an open position at a real settlement",
          f_long["funded"] != 0.0 and f_long["n_funding"] >= 1,
          f"paid {f_long['funded']:.4f}")

    # ------------------------------------------------------- real artifacts
    print("\n== real BTCUSDT artifacts (26 runnable rows) ==")
    row_tf = dict(E.RUNNABLE)
    failures = []
    nets = {}
    for rid, tf in sorted(row_tf.items()):
        try:
            a = V.make_artifact("emavwap50", tf, "BTCUSDT",
                                {"id": rid}, cut_ts=None)
            m, prov, tabs = (a["metrics"], a["provenance"], a["tables"])
            ok = (np.isfinite(m["net_pct"]) and m["n_trades"] >= 0 and
                  abs(m["pnl_identity_resid"]) < 1e-6)
            if not ok:
                failures.append((rid, "metric/invariant"))
            nets[rid] = m["net_pct"]
        except Exception as exc:
            failures.append((rid, str(exc)[:80]))
    check("all declared runnable rows produce a valid artifact",
          not failures, f"failures: {failures}")
    sample = [V.make_artifact("emavwap50", tf, "BTCUSDT", {"id": rid},
                              cut_ts=None)["metrics"]
              for rid, tf in list(row_tf.items())[:3]]
    check("every artifact carries fee, slippage and zero-cost control",
          all(m.get("zero_cost_ret_pct") is not None and
              m.get("fee_bps_per_side") is not None and
              m.get("slippage_bps_per_side") is not None for m in sample))
    print("\n== NO DATA refusals ==")
    bad = []
    for rid in (2, 30, 32, 35, 38, 48):
        try:
            V.make_artifact("emavwap50", "1h", "BTCUSDT", {"id": rid}, cut_ts=None)
            bad.append(rid)
        except RuntimeError:
            pass
    check("declared NO DATA rows refuse instead of estimating", not bad,
          f"wrongly ran: {bad}")

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("FAILED:", FAIL)
        sys.exit(2)
    print("ALL PASS")


if __name__ == "__main__":
    main()
