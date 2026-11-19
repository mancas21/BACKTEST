#!/usr/bin/env python
"""_scalpma20_parity.py -- prove the repo `scalpma20` engine implements the SAME
20 strategies as the attached source `scalp_ma_suite-20 STATEGIES-CLAUDE.py`
(preserved byte-identical as code/scalp_ma_source.py, sha a1a72fa2...).

AGENTS.md: when the source is already Python, parity applies to the SIGNAL.
This compares the long/short/exit_long/exit_short boolean arrays (and the
per-strategy sl_atr/tp_atr overrides) of all 20 ids on REAL Binance bars,
attached-source Data vs repo-engine Data. Execution-regime differences
(costs, funding, sizing, cost gate, cooldown, TP slip) are DECLARED separately
-- they are the house regime layered on the identical signal, not a port bug.

Run: python code/_scalpma20_parity.py
"""
from __future__ import annotations
import importlib.util, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")


def _import(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


SRC = _import("scalp_ma_source", os.path.join(HERE, "scalp_ma_source.py"))
REP = _import("scalpma20_engine", os.path.join(HERE, "scalpma20_engine.py"))


def load_real(path, slice_from=None, max_bars=None):
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    ts = pd.to_datetime(df["open_ts"].astype(np.int64), unit="ms", utc=True)
    df["timestamp"] = ts
    df = df.set_index("timestamp").sort_index()
    df = df[~df.index.duplicated()]
    if slice_from:
        df = df[df.index >= pd.Timestamp(slice_from, tz="UTC")]
    if max_bars:
        df = df.iloc[-max_bars:]
    df = df.reset_index()  # timestamp back as a column; index RangeIndex
    # attached Data uses df.index -> give it a DatetimeIndex too via a copy
    return df


def cells():
    out = []
    for sym in ("SUIUSDT", "SOLUSDT", "HYPEUSDT"):
        p = os.path.join(DATA, "binance_klines_5m", f"{sym}_5m.csv")
        if os.path.exists(p):
            out.append((sym, "5m", p, None, None))
    # 1m slices (recent) to exercise the same signals on the finer tape
    for sym in ("SUIUSDT", "BTCUSDT"):
        p = os.path.join(DATA, "binance_klines_1m", f"{sym}_1m.csv")
        if os.path.exists(p):
            out.append((sym, "1m", p, None, 120_000))
    return out


def sig_arrays(sig):
    return (np.asarray(sig.long, bool), np.asarray(sig.short, bool),
            None if sig.exit_long is None else np.asarray(sig.exit_long, bool),
            None if sig.exit_short is None else np.asarray(sig.exit_short, bool))


def main():
    # map attached sid "01_..." -> int
    src_map = {int(sid[:2]): (sid, nv, fn) for sid, desc, nv, fn in SRC.STRATS}
    total = fails = 0
    for sym, tf, path, sf, mb in cells():
        df = load_real(path, sf, mb)
        # attached Data wants a DatetimeIndex; repo Data wants a timestamp column
        df_src = df.set_index("timestamp")
        df_rep = df.copy()  # has 'timestamp' column
        d_src = SRC.Data(df_src)
        d_rep = REP.Data(df_rep, atr_len=14)
        n = len(df)
        print(f"\n=== {sym} {tf}  {n} bars  {df['timestamp'].iloc[0]} -> {df['timestamp'].iloc[-1]} ===")
        for sid in range(1, 21):
            name_s, nv_s, fn_s = src_map[sid]
            name_r, desc_r, nv_r, fn_r = REP.STRATS[sid]
            a = sig_arrays(fn_s(d_src))
            b = sig_arrays(fn_r(d_rep))
            ok = True
            for x, y in zip(a, b):
                if x is None or y is None:
                    ok &= (x is None and y is None)
                else:
                    ok &= bool(np.array_equal(x, y))
            # per-strategy geometry overrides must match too
            sa, sb = fn_s(d_src), fn_r(d_rep)
            ok &= (sa.sl_atr == sb.sl_atr) and (sa.tp_atr == sb.tp_atr) and (sa.flip == sb.flip)
            nl = int(a[0].sum()); ns = int(a[1].sum())
            total += 1; fails += (not ok)
            print(f"  {'PASS' if ok else 'FAIL'} id{sid:02d} {name_r:<26} long={nl:>6} short={ns:>6}")
    print(f"\n{total} signal-parity cells, {fails} FAIL")
    print("DECLARED execution differences (house regime, NOT signal):")
    print("  costs 11 bps RT (5 fee+0.5 slip/side) vs source 10 bps (4+1);")
    print("  funding charged at real settlements vs source none;")
    print("  sizing 1% risk / 20x cap vs source 0.5% / 5x;")
    print("  cost gate TP>=3xRT vs source min_sl_pct 0.08 on SL;")
    print("  no cooldown vs source cooldown=2; TP charged repo slip vs source limit no-slip.")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
