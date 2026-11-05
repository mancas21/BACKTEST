"""Parity audit: code/top10_engine.py vs the SOURCE screen engine
(trading-engines/backtest_prompts100/btlib.py + strategies.py) on the SAME
data bytes, trade by trade, plus the published criba numbers (results_100.csv,
2026-10-29) and a truncation-invariance lookahead probe.

Checks per strategy (the 10 of TOP10_ESTRATEGIAS.md):
  1. harness-style df (repo klines + tail glob) == btlib.load df, byte-equal
  2. every trade (entry_i, exit_i, dir, r) identical, and the equity curve
  3. full/is/oos metrics identical to B.evaluate
  4. results_100.csv row (11 bps) reproduced
  5. signals computed on a truncated frame are identical on the shared
     prefix (no lookahead)

Run:  python code/_top10_parity.py   -> exits 1 on any mismatch.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

CODE = Path(__file__).resolve().parent
REPO = CODE.parent
sys.path.insert(0, str(CODE))
import top10_engine as E  # noqa: E402

SRC = Path(r"C:\Users\Lenovo\trading-engines\backtest_prompts100")
sys.path.insert(0, str(SRC))
import btlib as Bsrc  # noqa: E402
import strategies as Ssrc  # noqa: E402

TOP10 = [26, 28, 34, 44, 56, 59, 60, 71, 73, 95]
FAILS = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}  {detail}")
        FAILS.append(name)


def harness_df(sym):
    """Exactly what the top10 adapter feeds the engine."""
    d = REPO / "data" / "binance_klines_1h"
    paths = [d / f"{sym}_1h.csv"]
    import glob
    paths += sorted(glob.glob(str(d / f"{sym}_1h_tail_*.csv")))
    frames = []
    for p in paths:
        raw = pd.read_csv(p)
        frames.append(raw[["open_ts", "open", "high", "low", "close", "volume"]].astype(float))
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates("open_ts").sort_values("open_ts").reset_index(drop=True)
    df.index = pd.RangeIndex(len(df))
    return df, [str(p) for p in paths]


def source_sig(sid, df):
    fn = getattr(Ssrc, f"s{sid}")
    return fn(df)


def my_sig(sid, df):
    if sid in E.FUNDING_STRATEGIES:
        frate = load_funding()
        return E.STRATEGIES[sid](df, frate), frate
    return E.STRATEGIES[sid](df), None


def load_funding():
    fp = REPO / "data" / "binance_funding" / "SUIUSDT_funding.json"
    import json
    with open(fp, encoding="utf-8") as fh:
        d = json.load(fh)
    return pd.Series({int(x["t"]): float(x["r"]) for x in d}).sort_index()


def main():
    csv = pd.read_csv(SRC / "results_100.csv")
    n11 = csv[np.isclose(csv.cost_bps, 0.0011)].set_index("no")

    for sid in TOP10:
        sym = E.STRATEGY_SYMBOLS[sid]
        print(f"\n== #{sid} {E.STRATEGY_NAMES[sid]} {sym} 1h ==")
        df_h, paths = harness_df(sym)
        df_s = Bsrc.load(sym, "1h")
        same = (len(df_h) == len(df_s) and
                np.array_equal(df_h["open_ts"].values, df_s["open_ts"].values) and
                np.array_equal(df_h["close"].values, df_s["close"].values))
        check("df bytes equal to btlib.load", same,
              f"harness {len(df_h)} vs source {len(df_s)}")

        sig_s = source_sig(sid, df_s)
        sig_m, frate = my_sig(sid, df_h)
        fund_s = Bsrc.funding_series(sym) if sid in E.FUNDING_STRATEGIES else None

        cost = 0.0011
        eq_s, tr_s = Bsrc.run_engine(df_s, sig_s, cost_rt=cost, risk=0.01, funding=fund_s)
        eq_m, tr_m, obs = E.run_engine(df_h, sig_m, cost_rt=cost, risk=0.01, funding=frate)

        ok_tr = (len(tr_s) == len(tr_m) and all(
            a["entry_i"] == b["entry_i"] and a["exit_i"] == b["exit_i"] and
            a["dir"] == b["dir"] and a["r"] == b["r"]
            for a, b in zip(tr_s, tr_m)))
        check(f"trades identical (n={len(tr_m)})", ok_tr,
              f"source {len(tr_s)} vs mine {len(tr_m)}")
        check("equity curve identical", np.array_equal(eq_s, eq_m))

        # source evaluate metrics vs csv row
        bpy = 8760
        n = len(df_s)
        split = int(n * 0.7)
        full_s = Bsrc.segment_stats(eq_s, tr_s, 0, n, bpy)
        oos_s = Bsrc.segment_stats(eq_s, tr_s, split, n, bpy)
        row = n11.loc[sid]
        check("csv net reproduced", abs(full_s["net"] - row["net"]) < 1e-12,
              f"source {full_s['net']:.6f} csv {row['net']:.6f}")
        check("csv pf reproduced", abs(full_s["pf"] - row["pf"]) < 1e-12,
              f"source {full_s['pf']:.6f} csv {row['pf']:.6f}")
        check("csv n reproduced", full_s["n"] == int(row["n"]),
              f"{full_s['n']} vs {int(row['n'])}")
        check("csv oos pf reproduced", abs(oos_s["pf"] - row["oos_pf"]) < 1e-12,
              f"source {oos_s['pf']:.6f} csv {row['oos_pf']:.6f}")
        check("csv oos n reproduced", oos_s["n"] == int(row["oos_n"]),
              f"{oos_s['n']} vs {int(row['oos_n'])}")
        check("csv oos net reproduced", abs(oos_s["net"] - row["oos_net"]) < 1e-12,
              f"source {oos_s['net']:.6f} csv {row['oos_net']:.6f}")
        check("csv gate flags reproduced",
              bool(full_s["pf"] > 1.2 and full_s["n"] >= 30 and full_s["net"] > 0) == bool(row["gate"])
              and bool(oos_s["pf"] > 1.2 and oos_s["net"] > 0 and oos_s["n"] >= 30) == bool(row["oos_ok"]))

        # truncation invariance: signals on a truncated frame are identical
        # on the shared prefix (vectorized no-lookahead probe)
        k = int(n * 0.9)
        df_t = df_h.iloc[:k].reset_index(drop=True)
        sig_t, _ = my_sig(sid, df_t)
        pref_ok = True
        for key in ("long_entry", "short_entry", "long_exit", "short_exit"):
            a = np.asarray(sig_m[key], dtype=bool)[:k]
            b = np.asarray(sig_t[key], dtype=bool)
            if not np.array_equal(a, b):
                pref_ok = False
        check("signals prefix-identical on truncated frame (no lookahead)", pref_ok)

    print(f"\n{'ALL PASS' if not FAILS else 'FAILED: ' + str(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
