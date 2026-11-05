#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_emaadx_matrix_driver.py — run the emaadx matrix through the vrun CLI.

13 symbols x {full author, full repo6x5, last6mo author, last6mo repo6x5}.
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
CELLS = [("full", "author"), ("full", "repo6x5"),
         ("last6mo", "author"), ("last6mo", "repo6x5")]

RUN_RE = re.compile(r"run_id\s*:\s*([0-9a-f]{16})")


def cli(*args):
    p = subprocess.run(VRUN + list(args), cwd=ROOT, capture_output=True,
                       text=True, timeout=1800)
    return (p.returncode, p.stdout + "\n" + p.stderr)


for sym in SYMS:
    for window, costs in CELLS:
        rc, out = cli("run", "--strategy", "emaadx", "--tf", "1h",
                      "--symbol", sym, "--set", "window=" + window,
                      "--set", "costs=" + costs)
        m = RUN_RE.search(out)
        if rc != 0 or not m:
            print("RUN-FAIL %-9s %-8s %-8s rc=%d :: %s"
                  % (sym, window, costs, rc,
                     (out.strip().splitlines() or ["?"])[-1]), flush=True)
            continue
        rid = m.group(1)
        vrc, vout = cli("verify", rid)
        stamp = "OK" if (vrc == 0) else ("STALE" if vrc == 3 else "REFUSED")
        print("CELL %-9s %-8s %-8s %s %s (run rc=%d)"
              % (sym, window, costs, rid, stamp, rc), flush=True)
        if vrc == 3:
            # the CLI already re-ran and found new bytes downstream? no — stale
            # means data drifted AFTER the artifact was written this same call;
            # report it loudly rather than swallowing it.
            print("  verify detail:", vout.strip(), flush=True)
print("done", flush=True)
