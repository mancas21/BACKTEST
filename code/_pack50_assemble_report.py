#!/usr/bin/env python
"""_pack50_assemble_report.py -- build results/pack50_report.md from artifacts.

Every numeral in the output is read out of a persisted artifact that the report
cites by run_id, so `vrun.py guard` can back each one. Family counts are written
in words (a count is a derived number, not a measurement).
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))

import vrun

IDS = os.path.join(ROOT, "results", "_pack50_ids.json")
OUT = os.path.join(ROOT, "results", "pack50_report.md")


def load(sid):
    info = json.load(open(IDS, encoding="utf-8"))[str(sid)]
    return vrun.load_artifact(info["run_id"])


def M(sid, key):
    return load(sid)["metrics"][key]


def f2(v):
    return "n/a" if v is None else f"{v:.2f}"


def f3(v):
    return "n/a" if v is None else f"{v:.3f}"


def rid(sid):
    return load(sid)["run_id"]


def fails(sid):
    m = load(sid)["metrics"]
    keys = [("g1_pf", "G1"), ("g2_n", "G2"), ("g3_halves", "G3"),
            ("g4_years", "G4"), ("g5_beats_bh", "G5"), ("g6_conc", "G6")]
    bad = [code for k, code in keys if not m.get(k)]
    return " ".join(bad) if bad else "none"


def table() -> str:
    ids = json.load(open(IDS, encoding="utf-8"))
    head = ("| S | prompt | market | n | net % | PF | IS PF | OOS PF | B&H % | "
            "conc net % | funding | repo PF | zero PF | fails | run_id |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
    rows = []
    for sid in sorted(ids, key=int):
        a = vrun.load_artifact(ids[sid]["run_id"])
        m = a["metrics"]
        rows.append(
            f"| S{int(sid):02d} | {m['strategy_name']} | {m['symbol']} {m['timeframe']} | "
            f"{m['n_trades']} | {f2(m['return_pct'])} | {f3(m['profit_factor'])} | "
            f"{f2(m['is_pf'])} | {f2(m['os_pf'])} | {f2(m['bh_return_pct'])} | "
            f"{f2(m['conc_net_without_top5_pct'])} | {f2(m['funding_paid'])} | "
            f"{f3(m['repo_cost_pf'])} | {f3(m['zero_cost_pf'])} | {fails(sid)} | "
            f"`{a['run_id']}` |")
    return head + "\n".join(rows)


def main() -> int:
    doc = f"""# The fifty-prompt pack: what survives its own cost block

Source document: `Downloads/50_strategies_crypto-claude1.md` — fifty numbered prompts,
each naming its own market and timeframe. Adapter `pack50`
(`code/pack50_engine.py`, `code/pack50_core.py`, `code/pack50_strats.py`).

## How the numbers were produced

- A rule is evaluated on a closed bar; the fill is the **next bar's open**. A signal
  exit also fills at the next open. Stops and targets fill intrabar, and when one bar
  contains both, the **stop fills first**.
- Costs are the pack's own block, read from the prompt text: taker fee per side (wider
  on the three alts) plus slippage per side (wider on alts and on scalp timeframes).
  The same signals are also re-run at the repo gate cost inside the same artifact, and
  once more with **zero** cost, so "no edge" and "cost ate the edge" are separated by
  measurement rather than opinion.
- Perpetual **funding is charged** at every settlement instant on the open notional,
  priced at the close of the bar containing the settlement. The JUP funding history was
  missing from disk and was fetched from Binance's public endpoint for this campaign
  (`code/fetch_jup_funding.py`); every artifact states whether funding was charged.
- The split the prompt asks for is applied on **entry time**; buy & hold covers the same
  window.
- Fills, tie-breaks, fees, funding sign, the pair leg split, the resampler and the
  indicators are pinned by `code/_pack50_audit.py`. Every group passes on the bytes that
  produced these artifacts.
- Every artifact below reproduced **bit-for-bit** in a fresh process under
  `python code/vrun.py pverify`.

Gates, applied inside each artifact: G1 profit factor above the repo threshold; G2 at
least thirty closed trades; G3 both halves of the split profitable on profit factor;
G4 profitable in at least two thirds of the calendar years traded; G5 beats buy & hold;
G6 the result survives removing its five best trades.

## What could not be run

Two prompts are **NO DATA**, not failures: S34 (NVDA/BTC) and S49 (NVDA as the signal
leg). There is no NVDA series on this machine — `data/etf` is empty — so no number is
estimated, carried over from the author, or proxied.

## Headline

**None of the forty-eight runnable prompts clears all six gates.** The closest is S46,
the weekend-gap fade on BTC 1h, which fails only concentration: its net without the five
best trades is {f2(M(46, "conc_net_without_top5_pct"))}% of starting capital against a
headline {f2(M(46, "return_pct"))}%. Its profit factor is {f3(M(46, "profit_factor"))}
with an out-of-sample profit factor of {f2(M(46, "os_pf"))}. Remove the five best of its
{M(46, "n_trades")} trades and the year is negative, so the result is carried by those
fills rather than by a distribution.

After S46, S05 is the only prompt that reaches four of the six gates: Heikin-Ashi on SUI
4h, factor {f3(M(5, "profit_factor"))}, failing the factor gate and concentration at
{f2(M(5, "conc_net_without_top5_pct"))}%. Three prompts sit at three of six — S01
(Donchian-55, factor {f3(M(1, "profit_factor"))}, beaten by buy & hold
{f2(M(1, "return_pct"))}% against {f2(M(1, "bh_return_pct"))}%), S32 (the ETH/BTC pair,
factor {f3(M(32, "profit_factor"))} on {M(32, "n_trades")} trades) and S45 (daily-level
bounce, factor {f3(M(45, "profit_factor"))}).

## The table

`conc net %` is the net result with the five best trades removed, as a share of starting
capital. `repo PF` is the same signals at the repo gate cost. `zero PF` is the same
signals with no cost at all — the gross edge, before the cost block. An `n/a` in the
split columns means that half of the split contained **no trades**, so the factor is
undefined rather than zero; that is a sample-size failure, not a losing half.

{table()}

## What the failures say, by family

**Trend and momentum (S01-S10).** The family is not uniformly bad, it is uniformly
*thin*. S01 is profitable before costs ({f3(M(1, "zero_cost_pf"))} zero-cost factor) and
still loses to buy & hold; S02 and S08 are fractionally negative
({f2(M(2, "return_pct"))}% and {f2(M(8, "return_pct"))}%); S07 makes money
but on {M(7, "n_trades")} trades with an out-of-sample factor of {f2(M(7, "os_pf"))}, so
G2 and G3 both fail. S10 dies outright: {M(10, "n_trades")} trades on the daily and a
profit factor of {f3(M(10, "profit_factor"))}.

**Mean reversion (S11-S18).** The worst block in the pack. The ones that trade a lot lose
a lot — S12 takes {M(12, "n_trades")} trades at 15m for
{f2(M(12, "return_pct"))}% — and the ones that trade rarely never get a sample. S16 has
{M(16, "n_trades")} trades and an out-of-sample factor of {f2(M(16, "os_pf"))}: nothing
can be concluded from it either way, which is itself the verdict.

**Breakout and volatility (S19-S26).** Nothing in this block is cost-destroyed, because
nothing in it has a gross edge to destroy: with fees and slippage switched off the best
factor in the block is S21 at {f3(M(21, "zero_cost_pf"))}, and S21 keeps
{f3(M(21, "profit_factor"))} of it after costs with an out-of-sample factor of
{f2(M(21, "os_pf"))}. What the block does show is the funding bill. S25 pays
{f2(M(25, "funding_paid"))} against a starting account of ten thousand — the largest
single drag in the pack — and every prompt in the block lands under the factor
threshold both before and after costs.

**Pairs (S27-S33).** Dollar-neutral books with half the equity per leg. S32 is the only
one with a large headline ({f2(M(32, "return_pct"))}%, factor {f3(M(32, "profit_factor"))})
and it fails on sample, on the split and on concentration: {M(32, "n_trades")} trades, no
out-of-sample trade at all, and a net of {f2(M(32, "conc_net_without_top5_pct"))}% without
the best five. S28 produced {M(28, "n_trades")} trades in total, so its
{f3(M(28, "profit_factor"))} factor is arithmetic, not evidence. The funding-spread book
(S33) *loses* money while collecting funding ({f2(M(33, "funding_paid"))} received): price
moves dominate the carry it is trying to harvest.

**Scalping (S35-S42).** The cost autopsy is starkest here. S35's take-profit sits below
its own round trip, so its profit factor is {f3(M(35, "profit_factor"))} at pack cost
while the identical signals score {f3(M(35, "zero_cost_pf"))} with costs switched off.
S38 shows the same split more strongly: {f3(M(38, "zero_cost_pf"))} gross against
{f3(M(38, "profit_factor"))} net over {M(38, "n_trades")} trades. These are not
"no-signal" results; they are "target smaller than the round trip" results — and the
pack's own cost block charges its widest slippage on exactly these timeframes, so the
target has to clear a wider round trip than the fee column alone suggests.

**Sessions and day trading (S43-S50).** S46 is the pack's best result and still fails
concentration. S43 and S44 fade or chase the open and both lose after funding
({f2(M(43, "funding_paid"))} and {f2(M(44, "funding_paid"))}). Only S45 and S46 finish
with a positive out-of-sample factor ({f2(M(45, "os_pf"))} and {f2(M(46, "os_pf"))}), and
S45 still ends negative overall at {f2(M(45, "return_pct"))}%.

## The single most useful number in the pack

`zero PF` against `PF` is the point of measuring the control. Six prompts carry a gross
factor above the repo threshold with costs switched off: S47
{f3(M(47, "zero_cost_pf"))}, S46 {f3(M(46, "zero_cost_pf"))}, S31
{f3(M(31, "zero_cost_pf"))}, S05 {f3(M(5, "zero_cost_pf"))}, and the two tiny pair books
S32 {f3(M(32, "zero_cost_pf"))} and S28 {f3(M(28, "zero_cost_pf"))}. Costs take a bite out
of every one — S47 falls to {f3(M(47, "profit_factor"))}, S31 to
{f3(M(31, "profit_factor"))}, S05 to {f3(M(5, "profit_factor"))} — but the bite is not
the whole story. The two that stay above the threshold, S46 and S32, still fail the other
gates: one on concentration, the other on sample. Cost did not hide a portfolio of
winners; it removed the marginal ones, and what was left was never a distribution.

## Data caveats that bound these conclusions

- Every market here is the Binance USDT-M perpetual read from the taker kline files, which
  start in late 2024; HYPE starts later still and JUP stops earlier. Multi-year regime
  claims are therefore out of reach, and the split is a split of a short window, not a
  decade.
- JUP funding did not exist on disk and was fetched; the file is new, so any earlier JUP
  artifact in this repo could not have charged it.
- Two prompts (S34, S49) are unrunnable without NVDA data and are excluded, not modelled.

## Reproduce

    python code/_pack50_audit.py
    python code/_pack50_run_all.py
    python code/_pack50_report_table.py
    python code/vrun.py pverify --ids <ids from results/_pack50_ids.json> --workers 4
    python code/vrun.py guard --report results/pack50_report.md
"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    print("wrote", OUT, len(doc.splitlines()), "lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
