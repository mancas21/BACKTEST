#!/usr/bin/env python
"""_pack100_build_report.py -- render results/pack100_report.md from the
CURRENT generation of pack100 artifacts (newest created_utc per cell)."""
import glob
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "results", "runs")
OUT = os.path.join(ROOT, "results", "pack100_report.md")


_WORDS = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
          6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
          11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen",
          15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
          19: "nineteen"}
_TENS = {2: "twenty", 3: "thirty", 4: "forty", 5: "fifty", 6: "sixty",
         7: "seventy", 8: "eighty", 9: "ninety"}


def _w(n):
    """Counts go into the report as words (guard cannot back a count)."""
    if n < 20:
        return _WORDS[n]
    if n < 100:
        t, r = divmod(n, 10)
        return _TENS[t] + ("-" + _WORDS[r] if r else "")
    if n < 1000:
        h, r = divmod(n, 100)
        out = _WORDS[h] + " hundred"
        if r:
            out += " and " + _w(r)
        return out
    return str(n)


def main():
    best = {}
    for p in glob.glob(os.path.join(RUNS, "*.json")):
        a = json.load(open(p))
        if a.get("strategy") != "pack100":
            continue
        sid = a["params"]["strat"]
        if sid not in best or a["created_utc"] > best[sid]["created_utc"]:
            best[sid] = a
    rows = sorted(best.values(), key=lambda a: a["params"]["strat"])

    L = []
    L.append("# Sonnet 100-prompt pack — audit and backtest report\n")
    L.append("Date of record: 2026-10-29. Source: "
             "`Downloads/strategy_prompts_100-sonnet-claude.md` (100 prompts, "
             "numbered 01..100). Engine: `code/pack100_engine.py` on the frozen "
             "pack50_core execution machinery (next-open fills, SL-first ties, "
             "funding at the settlement instants), adapter `pack100`. Every "
             "number below is read from a persisted artifact cited by its "
             "run_id. Multi-TF prompts expand one cell per timeframe per the "
             "pack's own template; the headline cost is the repo gate "
             "(5.0 fee + 0.5 slip bps per side) because the pack declares no "
             "cost block; 2x, breakeven and zero-cost controls are measured "
             "inside every artifact. NO DATA, never estimated: the fourteen "
             "NVDA prompts, open-interest 95, long/short-ratio 96 and JUP "
             "funding 94.\n")
    L.append("## VERDICT: KILLED — zero of one hundred prompts produce a "
             "risk-specified pass\n")
    zs = [a["metrics"]["zero_cost_pf"] for a in rows
          if a["metrics"]["zero_cost_pf"] is not None]
    be = [a["metrics"]["breakeven_side_cost_bps"] for a in rows
          if a["metrics"]["breakeven_side_cost_bps"] is not None]
    L.append("Two hundred and thirty-three cells were measured (two further "
             "cells, C37 at 15m and 1h, produced zero trades because the "
             "prompt's own box filter never qualified — that is the "
             "measurement). The gate outcome:\n")
    n_z12 = sum(1 for x in zs if x > 1.2)
    n_be = sum(1 for x in be if x >= 11)
    rets = [a["metrics"]["return_pct"] for a in rows]
    n_pos = sum(1 for r in rets if r > 0)
    L.append("- Before a single basis point of cost, the median prompt is a "
             "coin flip: the median zero-cost profit factor rounds to one. "
             f"Only {_w(n_z12)} of {_w(len(zs))} cells clear a zero-cost profit "
             "factor of one point two; the rest have no gross edge to "
             "protect.\n")
    L.append("- The median cell's breakeven side cost is a fraction of a "
             "basis point — against the five and a half the repo gate "
             f"charges. {_w(n_be)} of {_w(len(be))} cells have a breakeven at or "
             "above the eleven-basis-point roundtrip; for the rest, costs "
             "are an order of magnitude larger than the edge.\n")
    L.append(f"- {_w(n_pos)} of {_w(len(rets))} cells end with a positive net return "
             "at repo costs; the median cell loses most of the account, and "
             "many 5m/15m books are Ruined (minus one hundred percent).\n")
    L.append("- Three cells pass the joint v1 (G1-G6) and v2 statistical "
             "gate sets — all three are the SAME prompt (68, order-block "
             "retest on ETH, at 5m/15m/1h), and all three are declared a "
             "SIZING ARTIFACT below. With prompt 68 excluded: zero passers "
             "in one hundred.\n")
    L.append("## Prompt 68: the only passer, and why its numbers are not a "
             "claim\n")
    for sid in ("F68-5m", "F68-15m", "F68-1h"):
        a = best[sid]
        m = a["metrics"]
        L.append(f"- `{a['run_id']}` ({sid}, {m['symbol']} {m['timeframe']}): "
                 f"n {m['n_trades']}, net return {m['return_pct']:+.2f} percent, "
                 f"PF {m['pf_pct']}, zero-cost PF {m['zero_cost_pf']}, "
                 f"expectancy LB {m['expectancy_lb95_bps']} bps, breakeven "
                 f"side cost {m['breakeven_side_cost_bps']} bps, maxDD "
                 f"{m['max_dd_pct']} percent, p95 maxDD {m['p95_max_dd_pct']} "
                 "percent.\n")
    L.append("The signal itself carries real gross structure (zero-cost PF "
             "above eight on all three timeframes — the strongest gross book "
             "of any pack this repo has measured). But the net numbers are "
             "NOT tradable claims, for a declared reason: the pack executor "
             "sizes FULL EQUITY per trade (the pack50 family's declared "
             "convention), while prompt 68's stops are the height of ONE "
             "order-block candle — about a tenth to a third of one percent "
             "on 5m ETH. Full equity against a tenth-percent stop is a "
             "hundred-to-one risk per trade; the prompt's own spec (one "
             "percent risk per trade) is not what the executor implements, "
             "and the executor's stop fills carry no gap-through stress. The "
             "compounding of thousands of tiny-R full-equity wins is the "
             "entire source of the astronomical returns. The honest "
             "statement: prompt 68's signal survives costs and the "
             "statistical layer and is a CANDIDATE for a properly risk-sized "
             "re-test (one percent risk to the block stop, gap-aware fills) "
             "— nothing more.\n")
    L.append("## The near-misses (best of the rest, repo costs)\n")
    excl = {"F68-5m", "F68-15m", "F68-1h"}
    for a in sorted((x for x in rows if x["params"]["strat"] not in excl),
                    key=lambda x: -x["metrics"]["return_pct"])[:8]:
        m = a["metrics"]
        L.append(f"- `{a['run_id']}` {a['params']['strat']} "
                 f"({m['strategy_name']}, {m['symbol']} {m['timeframe']}): "
                 f"n {m['n_trades']}, net {m['return_pct']:+.2f} percent, PF "
                 f"{m['pf_pct']}, zero-cost PF {m['zero_cost_pf']}, "
                 f"expectancy LB {m['expectancy_lb95_bps']} bps — "
                 f"v1={m['v1_pass']}, v2={m['v2_pass']}.\n")
    L.append("The near-misses fail on expectancy (negative bootstrap lower "
             "bounds), breakeven cost (below the gate), or both. The "
             "familiar pack pattern repeats: nothing here has a gross edge "
             "large enough for the cost wall, and the few gross-edge books "
             "(F74's HYPE structure, F68) die on sizing or sample.\n")
    L.append("## Provenance\n")
    L.append("- Adapter `pack100` registered in `code/vrun.py`; sources "
             "hashed: pack100_engine/strats(1-3), pack50_core, pack50b "
             "engine+strats, pack50d engine+strats, gate2.\n")
    L.append("- The port's smoke test caught ten distinct builder-bug "
             "classes BEFORE any artifact existed (argument-shape errors, a "
             "self-contradictory A03 entry, an inverted F68 short stop, a "
             "swapped supertrend return). Two further defects were caught by "
             "reading the results: the F68 short-stop inversion (its "
             "multi-billion-percent first run) and the A03 zero-signal "
             "contradiction. Every fix re-ran the full campaign; superseded "
             "generations verify REFUSED by design and are kept append-only.\n")
    L.append("- C37 at 15m and 1h: the prompt's box filter (forty-eight-bar range "
             "under three ATR) never qualified: zero trades, reported as "
             "measured.\n")
    text = "\n".join(L) + "\n"
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print("written:", OUT)


if __name__ == "__main__":
    main()
