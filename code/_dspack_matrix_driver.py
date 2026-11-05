#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_dspack_matrix_driver.py — run the dspack matrix through the vrun CLI.

4 symbol strategies (ds1, ds2, ds3, ds5) x 13 canonical 1h symbols
x {full author, full repo6x5, last6mo author, last6mo repo6x5},
plus ds4 on symbol PORTFOLIO (the 13-file cross-sectional cell)
under the same 4 (window, costs) combinations.
Every cell: run + verify; prints one line per cell (auto-flushed).
"""
import re
import subprocess
import sys

ROOT = r"C:\Users\Lenovo\Documents\backtest-system"
VRUN = [sys.executable, "code/vrun.py"]

SYMS = ["ADAUSDT", "AVAXUSDT", "BNBUSDT", "BTCUSDT", "DOGEUSDT", "ETHUSDT",
        "HYPEUSDT", "LINKUSDT", "NEARUSDT", "SOLUSDT", "SPXUSDT", "SUIUSDT",
        "XRPUSDT"]
STRATS = ["ds1", "ds2", "ds3", "ds5"]
CELLS = [("full", "author"), ("full", "repo6x5"),
         ("last6mo", "author"), ("last6mo", "repo6x5")]

RUN_RE = re.compile(r"run_id\s*:\s*([0-9a-f]{16})")


def cli(*args):
    p = subprocess.run(VRUN + list(args), cwd=ROOT, capture_output=True,
                       text=True, timeout=3600)
    return (p.returncode, p.stdout + "\n" + p.stderr)


def cell(strat, sym, window, costs):
    rc, out = cli("run", "--strategy", "dspack", "--tf", "1h",
                  "--symbol", sym,
                  "--set", f"strat={strat}",
                  "--set", f"window={window}",
                  "--set", f"costs={costs}")
    m = RUN_RE.search(out)
    if rc != 0 or not m:
        print("RUN-FAIL %-4s %-10s %-8s %-8s rc=%d :: %s"
              % (strat, sym, window, costs, rc,
                 (out.strip().splitlines() or ["?"])[-1]), flush=True)
        return
    rid = m.group(1)
    vrc, vout = cli("verify", rid)
    stamp = "OK" if (vrc == 0) else ("STALE" if vrc == 3 else "REFUSED")
    print("CELL %-4s %-10s %-8s %-8s %s %s (run rc=%d)"
          % (strat, sym, window, costs, rid, stamp, rc), flush=True)
    if vrc != 0:
        print("  verify detail:", vout.strip(), flush=True)


for sym in SYMS:
    for strat in STRATS:
        for window, costs in CELLS:
            cell(strat, sym, window, costs)
for window, costs in CELLS:
    cell("ds4", "PORTFOLIO", window, costs)
print("done", flush=True)
