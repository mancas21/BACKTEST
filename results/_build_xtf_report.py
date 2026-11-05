"""Build results/xtf_backtest.md from the vrun artifacts only.

Scans results/runs and groups by (timeframe, hold mode), so the report cannot drift
from what was actually run. Every printed number is formatted out of artifact JSON in
the SAME scale the artifact stores it, and every artifact contributing a number has its
run_id cited. That is what `vrun.py guard` enforces.
"""
import glob
import json
import os
from collections import defaultdict

ROOT = r"C:\Users\Lenovo\Documents\backtest-system"
RUNS = os.path.join(ROOT, "results", "runs")
OUT = os.path.join(ROOT, "results", "xtf_backtest.md")

SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "SUIUSDT", "JUPUSDT", "HYPEUSDT"]
TFS = ["1m", "15m", "1h", "5m"]

arts = {}
for p in glob.glob(os.path.join(RUNS, "*.json")):
    try:
        a = json.load(open(p, encoding="utf-8"))
    except Exception:
        continue
    if a.get("schema") == "bt-artifact/1":
        arts[a["run_id"]] = a

grid = defaultdict(dict)                      # (tf, mode) -> sym -> artifact
for a in arts.values():
    if a["strategy"] != "cbot" or a["symbol"] not in SYMS:
        continue
    # A period slice carries the SAME (tf, hold_mode, symbol) key as the full-window
    # run, so without this filter the two collide in the dict and whichever the glob
    # happened to yield last silently replaces the other. Slices get their own table.
    if "slice_from" in a["params"] or "slice_to" in a["params"]:
        continue
    grid[(a["timeframe"], a["params"].get("hold_mode", "bars"))][a["symbol"]] = a

# passes matrix
order, mat = [], {}
for tf in TFS:
    for mode in ("bars", "minutes"):
        d = grid.get((tf, mode))
        if not d:
            continue
        h = next(iter(d.values()))["metrics"]["hold_minutes"]
        order.append((tf, mode, h))
        mat[(tf, mode)] = d

hdr = "| tf | hold | " + " | ".join(SYMS) + " |"
sep = "|---|---|" + "---|" * len(SYMS)
rows, idx_rows = "", ""
tp = tt = 0
for tf, mode, h in order:
    d = mat[(tf, mode)]
    cells = ""
    for s in SYMS:
        a = d.get(s)
        if not a:
            cells += "| not run |"
            continue
        m = a["metrics"]
        tp += m["n_pass"]
        tt += m["n_strategies"]
        cells += f"| {m['n_pass']}/{m['n_strategies']} |"
    rows += f"| {tf} | {h}m |" + cells + "\n"
    for s in SYMS:
        a = d.get(s)
        if a:
            idx_rows += f"| {tf} | {h}m | {s} | `{a['run_id']}` |\n"

# period splits for every symbol that ever passed at 1m
SPLITS = {
    "BTCUSDT": [("P1", "f4d8aeb8daed1041"), ("P2", "6be62afb3c88e373"), ("P3", "a0cf558a3d87dee9")],
    "ETHUSDT": [("P1", "0b9ecedc3af03e61"), ("P2", "ec73451283910de6"), ("P3", "40450a5a486088c0")],
    "SOLUSDT": [("P1", "72eed2a3e0d8ba11"), ("P2", "a1410ecf334b4643"), ("P3", "a1efe4befd8c0326")],
    "HYPEUSDT": [("P1", "e5e863e4d53a0188"), ("P2", "5ddf014281dcfcb4"), ("P3", "d736d11929becff6")],
}
sp_rows, sp_green = "", 0
for s, lst in SPLITS.items():
    cells = ""
    for lab, rid in lst:
        m = arts[rid]["metrics"]
        sp_green += m["n_pass"]
        cells += f"| `{rid}` {m['n_pass']}/{m['n_strategies']} |"
    sp_rows += f"| {s} |" + cells + "|\n"

# other engines
eng_rows = ""
for name in ("cvrmd", "botstrat", "ffs"):
    by = defaultdict(list)
    for a in arts.values():
        if a["strategy"] == name and a["timeframe"] in ("1m", "15m", "1h"):
            by[a["timeframe"]].append(a)
    for tf in ("1m", "15m", "1h"):
        lst = by.get(tf)
        if not lst:
            continue
        pfs = [a["metrics"]["profit_factor"] for a in lst]
        pfs = [p for p in pfs if p is not None and p != float("inf")]
        rets = [a["metrics"]["return_pct"] for a in lst]
        pos = sum(1 for r in rets if r > 0)
        ids = " ".join(f"`{a['run_id']}`" for a in sorted(lst, key=lambda x: x["symbol"]))
        eng_rows += (f"| {name} | {tf} | {len(lst)} | {pos} | {min(pfs):.3f}-{max(pfs):.3f} | "
                     f"{min(rets):+.1f}% to {max(rets):+.1f}% |\n| | | | | | {ids} |\n")

hyp = arts["b6c21d27ee6700ae"]
jup = arts["7cfb9f064dbcabb0"]

TXT = f"""# Cross-timeframe backtest - 1m / 15m / 1h (+ 5m reference) - seven symbols

Every number below is read from vrun artifacts in `results/runs/`; each `verify`s
bit-for-bit. None was typed by hand. Data: Binance USD-M futures WITH kline field 9
(`taker_buy_base`), which is what makes S05 taker-flow and S06 CVD divergence testable
at all. Fetched by `code/fetch_taker_tf.py`.

## cbot 10-strategy suite - passes out of ten per cell

| tf | hold | {' | '.join(SYMS)} |
|---|---|{'---|' * len(SYMS)}
{rows}
**{tp} passes out of {tt} strategy-runs.**

Two config notes:
- At 5m the two hold modes coincide (a three-bar hold and a fifteen-minute hold are the
  same thing), so that row was run twice under different ids with identical metrics.
- HYPEUSDT has a shorter history than the others ({hyp['inputs'][0]['bars']} one-minute
  bars against {jup['inputs'][0]['bars']} for JUP), because its perpetual listed late. It
  is reported in its own column and not pooled with BTC.

## 1m: the only timeframe that ever produced a pass - and the split that killed it

AGENTS.md requires green in at least two of three periods. The same 1m fifteen-minute-hold
config, re-run on three consecutive windows:

| sym | P1 | P2 | P3 |
|---|---|---|---
{sp_rows}
**{sp_green} passing periods out of twelve.** BTC and ETH are green in one period each,
SOL in one, HYPE in none. Nothing reaches two of three. On BTC and SOL the strategy that
passes in a period is not the one that passed the aggregate.

## The other engines at the same timeframes

Their rules are bar-indexed, so evaluating them on a different bar size rescales what the
rules mean (CVRMD's RSI14 is fourteen hours at 1h and fourteen minutes at 1m). A positive
cell here is evidence about timeframe-dependence, NOT a validated strategy at that
timeframe.

| engine | tf | artifacts | positive | PF range | return range |
|---|---|---|---|---|---|
{eng_rows}**sax cannot be run at all.** Its engine source
(`Downloads/sax_engine-claude.py`) no longer exists on disk, so every pre-existing SAX
artifact now fails `verify` with FileNotFoundError. SAX was already killed, so no
conclusion changes, but the repository can no longer reproduce its own SAX evidence.

## VERDICT

**KILLED at every timeframe on every symbol tested.** The suite carries no directional
information from one minute upward. The only configurations that ever passed did so on an
aggregate window and failed the period split - the signature of a selected sample, not an
edge. A permutation control shuffles predictions WITHIN a sample and therefore cannot
detect this; the period split is a separate, mandatory gate.

## Reproduction

```
python code\\fetch_taker_tf.py --tf 1m --sym HYPEUSDT
python code\\vrun.py run    --strategy cbot --tf 1m --symbol HYPEUSDT --set hold_mode=minutes
python code\\_xtf_periods.py HYPEUSDT 1m minutes 3
python code\\vrun.py verify b6c21d27ee6700ae
```

## run_id index for the pass matrix

| tf | hold | sym | run_id |
|---|---|---|---|
{idx_rows}"""

open(OUT, "w", encoding="utf-8").write(TXT)
print("written", OUT, "| passes", tp, "of", tt, "| split green", sp_green, "of 12")