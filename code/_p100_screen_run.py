"""The re-screen of family A: every prompt, DEV (selection) and OOS (verdict).

One artifact per (prompt, segment): 80 prompts x 2 segments = 160 artifacts,
each with its own run_id, each verifiable bit-for-bit.

Usage:  python code/_p100_screen_run.py [--ids 1,2,3] [--segments DEV,OOS]
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
PACK = os.path.join(ROOT, "code", "prompts100")
OUT = os.path.join(ROOT, "results", "_p100_screen_cells.json")


# the pair and basket prompts are NOT in the pack's runner map (they live in
# its pairs engine); their own bindings come from the pack's own code
PAIR_SYMBOLS = {81: ("SOLUSDT", "1h"), 82: ("BTCUSDT", "1h"),
                85: ("HYPEUSDT", "1h"), 86: ("SUIUSDT", "1h"),
                88: ("BTCUSDT", "1h"), 89: ("ETHUSDT", "15m")}
BASKET_SYMBOLS = {83: ("BASKET6", "1h"), 84: ("BASKET6", "1h"),
                  87: ("BASKET6", "1h"), 90: ("BASKET6", "1h")}


def strategy_map():
    src = open(os.path.join(PACK, "backtest100_runner.py"), encoding="utf-8",
               errors="replace").read()
    i = src.find("STRATEGY_MAP = {")
    j = src.find("\n}", i)
    block = src[i:j + 2]
    out = ast.literal_eval(block[block.index("{"):])
    for k, v in PAIR_SYMBOLS.items():
        out[str(k)] = v
    for k, v in BASKET_SYMBOLS.items():
        out[str(k)] = v
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default=None)
    ap.add_argument("--segments", default="DEV,OOS")
    args = ap.parse_args()

    smap = strategy_map()
    ids = ([int(x) for x in args.ids.split(",")] if args.ids
           else sorted(int(k) for k in smap))
    segments = args.segments.split(",")

    # ONE FILE PER CELL: two runners writing the same aggregate file would
    # clobber each other (the cells of one family would vanish).
    CELL_DIR = os.path.join(ROOT, "results", "_p100_cells")
    os.makedirs(CELL_DIR, exist_ok=True)
    cells = {}
    if os.path.exists(OUT):
        cells = json.load(open(OUT, encoding="utf-8"))
    for fn in os.listdir(CELL_DIR):
        if not fn.endswith(".json"):
            continue
        d = json.load(open(os.path.join(CELL_DIR, fn), encoding="utf-8"))
        cells[d["key"]] = d
    t0 = time.time()
    for sid in ids:
        symbol, tf = smap[str(sid)]
        for seg in segments:
            key = f"{sid}/{seg}"
            if key in cells:
                continue
            cmd = [sys.executable, "-X", "utf8", "code/vrun.py", "run",
                   "--strategy", "p100screen", "--tf", tf, "--symbol", symbol,
                   "--set", f"id={sid}", "--set", f"segment={seg}"]
            p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            txt = (p.stdout or "") + (p.stderr or "")
            rid = re.search(r"run_id\s*:\s*([0-9a-f]{16})", txt)
            if not rid:
                print(f"!! #{sid} {seg}: NO RUN_ID\n{txt[-600:]}", flush=True)
                continue
            rid = rid.group(1)
            a = json.load(open(os.path.join(ROOT, "results", "runs",
                                           rid + ".json"), encoding="utf-8"))
            m = a["metrics"]
            cells[key] = dict(run_id=rid, id=sid, segment=seg, symbol=symbol,
                               tf=tf, metrics=m, key=key)
            print(f"#{sid:<4} {seg:4s} {symbol:9s} {tf:4s} {rid}  "
                  f"n {m['n_trades']:5d}  PF {str(m['profit_factor'])[:6]:>6}  "
                  f"net {m['return_pct']:9.2f}%  dd {m['max_dd_pct']:8.2f}%  "
                  f"bh {str(m.get('bh_return_pct'))[:8]:>8}", flush=True)
            cells[key]["key"] = key
            with open(os.path.join(CELL_DIR, f"{sid}_{seg}.json"), "w",
                      encoding="utf-8") as f:
                json.dump(cells[key], f, indent=1, default=str)
            with open(OUT, "w", encoding="utf-8") as f:
                json.dump(cells, f, indent=1, default=str)
    print(f"\n{len(cells)} celdas en {time.time() - t0:.0f}s -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
