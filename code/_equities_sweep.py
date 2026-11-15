#!/usr/bin/env python3
"""
_equities_sweep.py — run the repo's strategies on the S&P 500 series.

The equities store is data/alpaca_1d (real Alpaca daily bars: SPY = the S&P
500 ETF, QQQ = Nasdaq 100, plus AAPL/MSFT/NVDA). The crypto store has no daily
bars, so the transfer runs at tf=1d against those files through the harness's
`data_dir` override (code/vrun.py, make_artifact): the SAME engine reads
another market, the directory lands in the artifact's core, and the run_id
cannot collide with the crypto one.

TWO COST REGIMES per strategy, because the question "does the edge transfer?"
has two possible answers:
  * STANDARD — the repo's standard (5 bps fee + 0.5 bps slip per side, 11 bps
    round trip) for the engines that take a cost parameter; the engine's own
    declared costs for the ones that do not (declared, not assumed).
  * PURE — the same signals with NO costs at all, where the engine takes a
    cost parameter. This separates "costs killed a real edge" from "it was
    negative before costs".

Every cell is an artifact with its own run_id; nothing is quoted from a
console. Adapters that cannot run on the equities series (fixed crypto
universes, portfolio books, intraday-only books) fail loudly and are recorded
as NOT RUNNABLE with the reason.

Usage:  python code/_equities_sweep.py [--dry]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
EQ_DIR = os.path.join("data", "alpaca_1d")
OUT = os.path.join(HERE, "_equities_sweep.json")

# Symbols scored: SPY is the S&P 500, QQQ its Nasdaq sibling (the repo's
# existing equities campaign used QQQ).
SYMBOLS = ["SPY", "QQQ"]

# Candidate adapters: the ones whose inputs are symbol x timeframe. The rest
# (fixed universes, portfolio books, diagnostics) are listed in the report as
# NOT RUNNABLE and why.
#
# The cost sets are each engine's OWN vocabulary (never invented):
#   * cbpack/cbpackf/prompts100/top10 take fee_bps + slippage_bps;
#   * smqe/smqe11/qs096/qs097 take cost_mode (repo|pine|zero);
#   * fingrad takes costs (author|repo6x5|zero);
#   * eqpack takes costs (eq|cons|zero|repo).
# Where the engine has no cost parameter, its costs are baked in and the run
# happens at those declared costs; the report says so per adapter.
CANDIDATES = [
    ("cbpack",      ["fee_bps=5.0", "slippage_bps=0.5"], ["fee_bps=0", "slippage_bps=0"], []),
    ("cbpackf",     ["fee_bps=5.0", "slippage_bps=0.5"], ["fee_bps=0", "slippage_bps=0"], []),
    ("prompts100",  ["fee_bps=5.0", "slippage_bps=0.5"], ["fee_bps=0", "slippage_bps=0"], []),
    ("top10",       ["fee_bps=5.0", "slippage_bps=0.5"], ["fee_bps=0", "slippage_bps=0"], []),
    ("smqe",        ["cost_mode=repo"], ["cost_mode=zero"], []),
    ("smqe11",      ["cost_mode=repo"], ["cost_mode=zero"], []),
    ("qs096",       ["cost=gate"], ["cost=zero"], []),
    ("qs097",       ["cost=gate"], ["cost=zero"], []),
    ("fingrad",     ["costs=author"], ["costs=zero"], ["costs=repo6x5"]),
    ("eqpack",      ["costs=repo"], ["costs=zero"], ["costs=eq"]),
    ("cvrmd",       [], [], []),
    ("botstrat",    [], [], []),
    ("ffs",         [], [], []),
    ("emaadx",      [], [], []),
    ("hmaaoadx",    [], [], []),
    ("scalpwave",   [], [], []),
    ("cbot",        [], [], []),
    ("pack20",      [], [], []),
]

# Adapters that cannot be pointed at the equities series, with the reason.
NOT_RUNNABLE = {
    "qs/qsf/qsb/qsc/qsd": "fixed taker-flow leg set per card; the engine needs the "
                           "taker-buy column, which equity bars do not carry",
    "pack50/pack50b/pack50c/pack50d/pack100": "pair books with a fixed crypto leg "
                                              "list and a per-symbol funding file",
    "dspack/dspack2": "fixed five-name crypto universe (BTC/ETH/SOL/SUI/XRP)",
    "xsf/xsb/xsc": "fixed fourteen-name crypto universe, rank-rotation books",
    "cand7": "fixed leg baskets over crypto 1h taker bars",
    "q10": "card-based universe of the majors",
    "mp20/mps20/mpv3": "portfolio books, not a single symbol",
    "xrpneutral/xrpneutral1m": "15m books by construction (the deployed neutral bot)",
    "bookreplay": "replay of one book on aggTrades; the tape is XRP-only",
    "rsimr/gate2/gatecal/q10diag": "diagnostics and null calibrators, not strategies",
    "sax": "engine file no longer exists on disk (unrunnable by design)",
    "prompts100": "fixed prompt set; only the per-symbol variants are attempted",
}


def run(strategy, symbol, sets):
    cmd = [sys.executable, "-X", "utf8", os.path.join("code", "vrun.py"),
           "run", "--strategy", strategy, "--tf", "1d", "--symbol", symbol,
           "--set", "data_dir=" + EQ_DIR]
    for kv in sets:
        cmd += ["--set", kv]
    t0 = time.time()
    pr = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                        encoding="utf-8", errors="replace")
    out = (pr.stdout or "") + (pr.stderr or "")
    rid = None
    m = re.search(r"run_id\s*:\s*([0-9a-f]{16})", out)
    if m:
        rid = m.group(1)
    err = None
    if pr.returncode != 0:
        lines = [x.strip() for x in out.splitlines()
                 if x.strip() and not x.startswith("  File ")
                 and not x.strip().startswith(("Traceback", "return ", "raise "))]
        err = lines[-1][:160] if lines else f"rc={pr.returncode}"
    return dict(ok=pr.returncode == 0 and rid is not None, run_id=rid,
                rc=pr.returncode, error=err, secs=round(time.time() - t0, 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--only", default=None,
                    help="run just this adapter and merge it into the sweep file")
    args = ap.parse_args()
    results = []
    for strategy, std_sets, pure_sets, extra_sets in CANDIDATES:
        if args.only and strategy != args.only:
            continue
        for sym in SYMBOLS:
            regimes = [("standard", std_sets)]
            if pure_sets:
                regimes.append(("pure", pure_sets))
            for sets in extra_sets:
                regimes.append((f"extra:{sets.split('=')[1]}", [sets]))
            for regime, sets in regimes:
                if args.dry:
                    print(f"DRY {strategy} {sym} {regime} {sets}")
                    continue
                r = run(strategy, sym, sets)
                r.update(strategy=strategy, symbol=sym, regime=regime)
                results.append(r)
                print(f"{'OK  ' if r['ok'] else 'FAIL'} {strategy:12s} {sym:4s} "
                      f"{regime:9s} {r['run_id'] or r['error']} "
                      f"({r['secs']}s)", flush=True)
                if not r["ok"]:
                    print("      ", r["error"], flush=True)
    if not args.dry:
        if args.only and os.path.exists(OUT):
            old = json.load(open(OUT, encoding="utf-8"))
            keep = [r for r in old if r["strategy"] != args.only]
            merged = keep + results
        else:
            merged = results
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=1)
        ok = sum(1 for r in merged if r["ok"])
        print(f"\n{ok}/{len(merged)} cells produced an artifact -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
