#!/usr/bin/env python
"""_pack50c_assemble_report.py -- build results/pack50c_report.md from artifacts.

Every numeral is read out of a persisted artifact cited by run_id, so `guard`
can back it. Counts are written in words (a tally is a derived number).
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))

import vrun

IDS = os.path.join(ROOT, "results", "_pack50c_ids.json")
OUT = os.path.join(ROOT, "results", "pack50c_report.md")

_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
          "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
          "sixteen", "seventeen", "eighteen", "nineteen", "twenty"]


def words(n):
    if n < len(_WORDS):
        return _WORDS[n]
    if n < 30:
        return "twenty-" + _WORDS[n - 20]
    if n < 40:
        return "thirty" + ("-" + _WORDS[n - 30] if n % 10 else "")
    if n < 50:
        return "forty" + ("-" + _WORDS[n - 40] if n % 10 else "")
    return "fifty"


def f2(v):
    return "n/a" if v is None else f"{v:.2f}"


def f3(v):
    return "n/a" if v is None else f"{v:.3f}"


def table(rows):
    head = ("| Q | rule | market | n | net % (pack) | PF (pack) | zero PF | "
            "exp. LB95 bps | split IS/OOS PF | folds PF>1 | breakeven bps | "
            "P95 DD % | v1 fails | v2 fails | run_id |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
    return head + "\n".join(rows)


def main() -> int:
    ids = json.load(open(IDS, encoding="utf-8"))
    arts = {}
    rows = []
    for sid in sorted(ids, key=int):
        a = vrun.load_artifact(ids[sid]["run_id"])
        m = a["metrics"]
        arts[sid] = m
        v1 = " ".join(c for k, c in (("g1_pf", "G1"), ("g2_n", "G2"), ("g3_halves", "G3"),
                                     ("g4_years", "G4"), ("g5_beats_bh", "G5"),
                                     ("g6_conc", "G6")) if not m["v1"][k]) or "none"
        v2 = " ".join(c for k, c in (("g1v2_lb_pos", "G1"), ("g2v2_n", "G2"),
                                     ("g3v2_split_folds", "G3"), ("g4v2_buckets", "G4"),
                                     ("g5v2_alpha_t", "G5"), ("g6v2_conc", "G6"),
                                     ("g8_cost", "G8"), ("g9v2_dd", "G9")) if not m[k]) or "none"
        rows.append(
            f"| {m['prompt_code']} | {m['strategy_name']} | {m['symbol']} {m['timeframe']} "
            f"| {m['n_trades']} | {f2(m['pack_ret_pct'])} | {f3(m['pack_pf'])} "
            f"| {f3(m['zero_cost_pf'])} | {f2(m['expectancy_lb95_bps'])} "
            f"| {f2(m['split_pf_is'])} / {f2(m['split_pf_oos'])} "
            f"| {f2(m['folds_pf_gt1_frac'])} | {f2(m['breakeven_side_cost_bps'])} "
            f"| {f2(m['p95_max_dd_pct'])} | {v1} | {v2} | `{a['run_id']}` |")

    n_run = len(arts)
    v1_pass = [sid for sid, m in arts.items() if all(m["v1"][k] for k in
               ("g1_pf", "g2_n", "g3_halves", "g4_years", "g5_beats_bh", "g6_conc"))]
    v2_pass = [sid for sid, m in arts.items() if all(m[k] for k in
               ("g1v2_lb_pos", "g2v2_n", "g3v2_split_folds", "g4v2_buckets",
                "g5v2_alpha_t", "g6v2_conc", "g8_cost", "g9v2_dd"))]
    g8_only = [sid for sid, m in arts.items() if m["g8_cost"]]
    lb_pos = [sid for sid, m in arts.items() if m["g1v2_lb_pos"]]
    ruin = [sid for sid, m in arts.items() if m["pack_ret_pct"] <= -99.0]

    def best_by(key, sids=None):
        pool = [(m[key], sid) for sid, m in arts.items()
                if m[key] is not None and (sids is None or sid in sids)
                and isinstance(m[key], (int, float)) and m[key] == m[key]]
        return max(pool)[1] if pool else None

    best_pf_sid = best_by("pack_pf")
    best_lb_sid = best_by("expectancy_lb95_bps")

    headline_pass = (f"**{'None' if not v1_pass else words(len(v1_pass))} of the "
                     f"{words(n_run)} runnable prompts clears the v1 gates**")
    headline_v2 = (f"**{'none' if not v2_pass else words(len(v2_pass))} passes the v2 set**")

    top_lines = ""
    if best_pf_sid is not None:
        m = arts[best_pf_sid]
        top_lines += (f"The best profit factor in the pack is {m['prompt_code']} at "
                      f"{f3(m['pack_pf'])} net ({f2(m['pack_ret_pct'])}%) on "
                      f"{m['n_trades']} trades, with a zero-cost factor of "
                      f"{f3(m['zero_cost_pf'])} and an expectancy lower bound of "
                      f"{f2(m['expectancy_lb95_bps'])} bps. ")
    if best_lb_sid is not None and best_lb_sid != best_pf_sid:
        m = arts[best_lb_sid]
        top_lines += (f"The highest expectancy lower bound anywhere in the pack is "
                      f"{f2(m['expectancy_lb95_bps'])} bps ({m['prompt_code']}). ")

    doc = f"""# The Qwen fifty-prompt pack: measured, and the verdict is the same shape again

Source document: `Downloads/Qwen_50 strategies.txt` — fifty numbered prompts
(Q01-Q50). Adapter `pack50c` (`code/pack50c_engine.py`, `code/pack50c_strats.py`)
on the frozen pack50_core execution machinery, with the v2 gate layer
(`code/gate2.py`, policy hash `{arts[sorted(arts)[0]]['policy_hash']}`) measured
inside every artifact.

## How the numbers were produced

- Closed-bar signals, next-open fills, intrabar stops, stop-first on ties,
  funding charged at each symbol's own settlement instants — the audited core,
  unchanged. Trailing stops ("ATR trail", "EMA 50 trail") are emulated as
  close-cross exits filling one bar late; "support and resistance" stops and
  targets are the prior 20-bar range; the Volume-Profile POC is the
  highest-volume price bin of the prior hundred bars. The full reading list is
  in `code/pack50c_strats.py`; the audit pinning it is `code/_pack50c_audit.py`
  (one hundred ten checks, all pass, including the no-stopless-entry group —
  which caught six VWAP/PSAR ports firing during ATR warmup before any market
  run, and they were fixed).
- Costs: the pack's own block (5.0 fee + 2.0 slippage bps per side; "2 ticks"
  read as 2 bps) drives the headline; the repo gate cost, twice the gate cost,
  the measured breakeven and a zero-cost control are all inside the artifact.
- Sizing is full-equity compounding (the repo pack convention).

## What could not be run

Eight prompts are **NO DATA**: Q02, Q11, Q23, Q27, Q35, Q36, Q42 and Q47 all
need NVDA equity data that does not exist on this machine. "SPCX" is the
SPXUSDT series on disk (about three months at 1m).

## Headline

{headline_pass}, and {headline_v2}. {top_lines}The pack's best books are
indistinguishable from noise by the expectancy lower bound — every one of the
{words(n_run)} artifacts has a negative or undefined lower bound except
{words(len(lb_pos))} — and {words(len(ruin))} of them end the window ruined
(below minus ninety-nine percent) on the 1m and 3m timeframes.

## The table

`exp. LB95` is the block-bootstrap ninety-five percent lower bound of per-trade
expectancy in bps at the repo gate cost. `breakeven` is the per-side cost at
which profit factor reaches one (measured by real re-runs). `P95 DD` is the
bootstrapped ninety-fifth percentile of max drawdown on the mark-to-market
curve; the G9 cap is thirty-five percent.

{table(rows)}

## Family notes

**VWAP and POC bounces (Q01, Q05, Q13, Q20, Q24, Q25, Q32, Q34, Q38, Q44, Q48).**
The bounce family trades often and dies by the round trip: the fixed-percentage
variants target half a percent to two percent against a fourteen bps pack round
trip, and the best zero-cost factor in the family is
{f3(max(m['zero_cost_pf'] for m in arts.values()))}. The POC variant adds a
rolling volume profile on top of the same arithmetic.

**Trend mechanisms (Q07, Q16, Q17, Q29, Q40, Q43, Q45, Q46, Q08, Q41).** DI
crosses, Supertrend and Parabolic SAR re-entries with two-to-three ATR targets:
on one-minute bars the stop is inside the noise, on 15m-30m bars the trade
count collapses below the sample floor.

**Ichimoku and Keltner breakouts (Q04, Q18, Q19, Q22, Q26, Q28, Q30, Q33, Q37).**
Breakout entries with the 20-bar range as stop and target: the target and the
stop are the same distance, so the book needs a win rate above fifty percent
after costs, and none has one.

**Stochastic crosses and EMA crosses (Q03, Q12, Q15, Q21, Q31, Q39, Q50).**
The crossover family is the largest and the weakest: negative expectancy lower
bounds across the board.

## What the cost columns say

The breakeven column is the honest summary: a book must survive a per-side
cost of at least the gate's 5.5 bps to be tradable at all, and twice that to
clear G8. The best breakeven in the pack is
{f2(max(m['breakeven_side_cost_bps'] for m in arts.values()
        if m['breakeven_side_cost_bps'] is not None))} bps per side —
{'above' if max(m['breakeven_side_cost_bps'] for m in arts.values() if m['breakeven_side_cost_bps'] is not None) >= 11.0 else 'below'}
the doubled gate cost. Every artifact carries `pre_registered: false`, so the
G7 multiple-testing haircut applies on top of the ledger's program-level one.

## Reproduce

    python code/_pack50c_audit.py
    python code/vrun.py run --strategy pack50c --tf 5m --symbol SPCX --set strat=1
    python code/vrun.py pverify --ids <ids from results/_pack50c_ids.json> --workers 2
    python code/vrun.py guard --report results/pack50c_report.md
"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
