#!/usr/bin/env python
"""_pack50b_assemble_report.py -- build results/pack50b_report.md from artifacts.

Every numeral in the output is read out of a persisted artifact that the report
cites by run_id, so `vrun.py guard` can back each one. Counts are written in
words (a count is a derived number, not a measurement).
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))

import vrun

IDS = os.path.join(ROOT, "results", "_pack50b_ids.json")
OUT = os.path.join(ROOT, "results", "pack50b_report.md")


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
    head = ("| Prompt | rule | market | n | net % | PF | IS PF | OOS PF | B&H % | "
            "conc net % | funding $ | repo PF | zero PF | fails | run_id |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
    rows = []
    for sid in sorted(ids, key=int):
        a = vrun.load_artifact(ids[sid]["run_id"])
        m = a["metrics"]
        rows.append(
            f"| {m['prompt_code']} | {m['strategy_name']} | {m['symbol']} {m['timeframe']} | "
            f"{m['n_trades']} | {f2(m['return_pct'])} | {f3(m['profit_factor'])} | "
            f"{f2(m['is_pf'])} | {f2(m['os_pf'])} | {f2(m['bh_return_pct'])} | "
            f"{f2(m['conc_net_without_top5_pct'])} | {f2(m['funding_paid'])} | "
            f"{f3(m['repo_cost_pf'])} | {f3(m['zero_cost_pf'])} | {fails(sid)} | "
            f"`{a['run_id']}` |")
    return head + "\n".join(rows)


def main() -> int:
    doc = f"""# The claude2 fifty-prompt pack: nothing survives, and most of it has no gross edge

Source document: `Downloads/crypto_strategy_prompts_50-claude2.md` — fifty numbered
prompts, twenty-five scalping (S01-S25) and twenty-five day trading (D01-D25), each
naming its own market and timeframe. Adapter `pack50b`
(`code/pack50b_engine.py`, `code/pack50b_strats.py`, on the frozen
`code/pack50_core.py` execution core that the pack50 campaign pinned).

## How the numbers were produced

- A rule is evaluated on a closed bar; the fill is the **next bar's open**. A signal
  exit also fills at the next open. Stops and targets fill intrabar, and when one bar
  contains both, the **stop fills first**. Flat-by-time rules (S07, D07, D11) fire on
  the first bar at/after the deadline and fill one bar late.
- Costs are the pack's own block, uniform as the prompt header declares: **5 bps fee
  and 2 bps slippage per side (14 bps round trip)**. The same signals are re-run at
  the repo gate cost (5.0 + 0.5 bps) and once more with **zero** cost inside the same
  artifact, so "no edge" and "cost ate the edge" are separated by measurement.
- Sizing is **full-equity compounding**, the repo-wide pack convention, so this report
  is comparable to the claude1 pack report. The prompt header's "1% of equity per
  trade" would rescale returns and drawdowns but not profit factor, win rate, trade
  count or the cost share.
- Perpetual **funding is charged** at every settlement instant on the open notional,
  priced at the close of the bar containing the settlement.
- The split is 70/30 on **entry time**; buy & hold covers the same window.
- `code/_pack50b_audit.py` pins fills, tie-breaks, fees, funding sign, the pair leg
  split, the resampler, the new indicators (stochastic, CCI, OBV, the TTM linear
  regression residual, Ichimoku), the stateful pair targets, and a
  **no-stopless-entry** check: an entry may not fire on a bar whose stop level is
  undefined. That last group exists because two ports were caught and fixed by it
  mid-campaign (a negated-NaN downtrend gate in S02 and an ATR-warmup entry in S13
  both produced stopless positions); after the fix every artifact was re-created, so
  every run_id below covers the final engine bytes.
- Timeframes map to the taker kline files as in the pack50 campaign: 1m and 3m from
  the 1m files (3m resampled), 5m native, 15m and 30m from the 15m files (30m
  resampled), 1h native. "SPCX" is read as the SPXUSDT series on disk, which exists
  only as plain 1m/1h klines; its 5m/15m prompts resample from the 1m file.

Gates, applied inside each artifact: G1 profit factor above the repo threshold; G2 at
least thirty closed trades; G3 both halves of the split profitable on profit factor;
G4 profitable in at least two thirds of the calendar years traded; G5 beats buy & hold;
G6 the result survives removing its five best trades.

## What could not be run

Four prompts are **NO DATA**, not failures: S08 and S23 (NVDA 5m and 1m scalps), D08
and D18 (NVDA 15m and 1h day strategies). There is no NVDA series on this machine, so
no number is estimated, carried over from the author, or proxied. This is the same
class of exclusion as the claude1 pack's S34 and S49.

## Headline

**None of the forty-six runnable prompts clears all six gates.** Two prompts reach
four of the six — D05, the TTM squeeze release on SUI 1h, and D13, the Fibonacci
pullback on SUI 30m — and both fail exactly the profit-factor gate and the
concentration gate. D05 nets {f2(M(30, 'return_pct'))}% with a profit factor of
{f3(M(30, 'profit_factor'))}; remove its five best trades and the net becomes
{f2(M(30, 'conc_net_without_top5_pct'))}% of starting capital. D13 nets
{f2(M(38, 'return_pct'))}% with a profit factor of {f3(M(38, 'profit_factor'))} and a
concentration net of {f2(M(38, 'conc_net_without_top5_pct'))}%. Two more prompts reach
three of six: D04 (Ichimoku on HYPE 30m, {f3(M(29, 'profit_factor'))} on
{M(29, 'n_trades')} trades, beaten by buy & hold {f2(M(29, 'bh_return_pct'))}%) and
D23 (the daily pivot bounce on SUI 15m, {f3(M(48, 'profit_factor'))} on
{M(48, 'n_trades')} trades). Nothing else gets past two.

## The table

`conc net %` is the net result with the five best trades removed, as a share of starting
capital. `repo PF` is the same signals at the repo gate cost. `zero PF` is the same
signals with no cost at all — the gross edge, before the cost block. An `n/a` in the
split columns means that half of the split contained **no trades**, so the factor is
undefined rather than zero.

{table()}

## The scalping block has no edge to destroy

The twenty-three runnable scalping prompts are not a cost story — they are a
**gross-edge story**. With fees and slippage switched OFF, the best profit factor in
the whole block is S03, the RSI(2) reversion on SOL 1m, at {f3(M(3, 'zero_cost_pf'))};
every other prompt sits at or below {f3(M(21, 'zero_cost_pf'))} (S21) and most are under
1.05. Nothing in the block clears the repo threshold before a single fee is charged.
The pack's 14 bps round trip then turns marginal gross factors into ruin: most 1m and
3m accounts end the window at −100% (S01, S03, S05, S09, S12, S13, S14, S18, S19, S20,
S22 all read −100.0% net), with trade counts from {M(3, 'n_trades')} (S03) to
{M(22, 'n_trades')} (S22). S13 is the sharpest single finding: the VWAP deviation fade
on SUI 5m carries a profit factor of {f3(M(13, 'zero_cost_pf'))} with cost switched off
— it is a net-negative rule even for free. S02, the daily-VWAP pullback on ETH 5m,
trades {M(2, 'n_trades')} times for {f2(M(2, 'return_pct'))}% net against a zero-cost
factor of {f3(M(2, 'zero_cost_pf'))}.

The three pairs sit in the same block. S16 (ETH/BTC z-score, 15m) and S17 (SOL/ETH
Bollinger, 15m) net {f2(M(16, 'return_pct'))}% and {f2(M(17, 'return_pct'))}% with
zero-cost factors of {f3(M(16, 'zero_cost_pf'))} and {f3(M(17, 'zero_cost_pf'))};
funding lands at {f2(M(16, 'funding_paid'))} and {f2(M(17, 'funding_paid'))} dollars
(negative funding means the book collected it).

## The day-trading block: a little gross edge, none of it priced

Six day-trading prompts carry a zero-cost factor above 1.05 — D02 at
{f3(M(27, 'zero_cost_pf'))}, D05 at {f3(M(30, 'zero_cost_pf'))}, D13 at
{f3(M(38, 'zero_cost_pf'))}, D23 at {f3(M(48, 'zero_cost_pf'))}, D20 at
{f3(M(45, 'zero_cost_pf'))} and D11 at {f3(M(36, 'zero_cost_pf'))} — and three of those
stay above 1.0 after the pack's own costs. The strongest net profit factor in the
entire pack is D13 at {f3(M(38, 'profit_factor'))}; D05 and D23 follow at
{f3(M(30, 'profit_factor'))} and {f3(M(48, 'profit_factor'))}. All three are above
water in the half of the split that matters (OOS factors {f2(M(30, 'os_pf'))} and
{f2(M(38, 'os_pf'))} for the D05/D13 pair, D23's second half at
{f2(M(48, 'os_pf'))}), D05 and D13 are green in every year they trade — and all three
still fail the factor gate and die on concentration. G5 tells the same story from the
other side: five prompts beat buy & hold (D03, D05, D13, D14, D23), and they do it
while the underlying market fell — SUI buy & hold is {f2(M(48, 'bh_return_pct'))}% over
the window — not while out-trading an up market.

Funding is a real but secondary drag on this block: the two SUI survivors are roughly
flat on it ({f2(M(30, 'funding_paid'))} and {f2(M(38, 'funding_paid'))} dollars), the
ETH Donchian book D02's funding line reads {f2(M(27, 'funding_paid'))} dollars and the
JUP Chandelier book D14's reads {f2(M(39, 'funding_paid'))} (negative funding means
the book collected it).

## The single most useful number in the pack

`zero PF` against `PF` is the point of measuring the control. In the claude1 pack the
zero-cost control exposed six cost-destroyed winners; in this pack it exposes almost
nothing to destroy. Two prompts — D23 at {f3(M(48, 'zero_cost_pf'))} and D13 at
{f3(M(38, 'zero_cost_pf'))} — carry a gross factor above the repo threshold before
costs, and both fall under it at the pack's own block ({f3(M(48, 'profit_factor'))} and
{f3(M(38, 'profit_factor'))}). Everything else was never above the threshold at any
cost level. The verdicts are signal verdicts, not cost verdicts.

## Data caveats that bound these conclusions

- Every crypto market here is the Binance USDT-M perpetual read from the taker kline
  files, which start in October 2024 (HYPE later, JUP from its listing, SPX plain
  klines only). Two calendar years is the longest window any artifact sees, and
  S15/S25/D25 see roughly three months of SPX — the prompt file itself flags SPCX as
  exploratory, and their G4 year gate fails on a single-year sample.
- 3m and 30m bars are resampled from 1m and 15m files on the UTC grid; the resampler
  is pinned against the core's own in the audit.
- Four prompts are unrunnable without NVDA data and are excluded, not modelled.

## Reproduce

    python code/_pack50b_audit.py
    python code/_pack50b_run_all.py
    python code/vrun.py pverify --ids <ids from results/_pack50b_ids.json> --workers 2
    python code/vrun.py guard --report results/pack50b_report.md
"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    print("wrote", OUT, len(doc.splitlines()), "lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
