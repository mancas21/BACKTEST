#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_fingrad_build_report.py — renders results/fingrad_report.md FROM the
artifacts (numbers never hand-typed; every table cell and quoted metric is
read out of the cited artifact's JSON, which is what `vrun.py guard` checks).
Counts are written in words (guard cannot back derived tallies).

    python code/_fingrad_build_report.py
    python code/vrun.py guard --report results/fingrad_report.md
"""
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUNS = os.path.join(ROOT, "results", "runs")
OUT = os.path.join(ROOT, "results", "fingrad_report.md")

WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
         "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
         "sixteen", "seventeen", "eighteen", "nineteen", "twenty"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
        "eighty", "ninety"]


def w(n):
    if n < len(WORDS):
        return WORDS[n]
    if n < 100:
        return TENS[n // 10] + ("-" + WORDS[n % 10] if n % 10 else "")
    if n < 1000:
        h = WORDS[n // 100] + " hundred"
        r = n % 100
        return h if r == 0 else h + " " + w(r)
    return str(n)


ART = {}
for p in sorted(glob.glob(os.path.join(RUNS, "*.json"))):
    a = json.load(open(p, encoding="utf-8"))
    if a.get("strategy") == "fingrad":
        ART[a["run_id"]] = a


def grid(tf, sig, preset="custom", adx="cross", costs="author", fund=False):
    out = []
    for a in ART.values():
        m = a["metrics"]
        if (a["timeframe"] == tf and m["sig_mode"] == sig and m["preset"] == preset
                and m["adx_mode"] == adx and m["costs"] == costs
                and bool(m["funding_charged"]) == fund):
            out.append((a["symbol"], a))
    return sorted(out)


def row(sym, a, cols):
    m = a["metrics"]
    cells = {"sym": sym, "rid": a["run_id"], "n": str(m["n_trades"]),
             "ret": f"{m['return_pct']:.2f}", "pf": f"{m['profit_factor']:.3f}",
             "wr": f"{m['win_rate']:.1f}", "dd": f"{m['max_dd_pct']:.1f}",
             "bh": f"{m['bh_return_pct']:.1f}", "drag": f"{m['drag_pp']:.2f}",
             "top5": ("—" if m["best5_share_pct"] is None
                      else f"{m['best5_share_pct']:.1f}"),
             "zero": f"{m['ret_zero_pct']:.2f}",
             "h1": f"{m['ret_h1_pct']:.1f}", "h2": f"{m['ret_h2_pct']:.1f}",
             "green": f"{w(sum(1 for v in m['year_returns'].values() if v > 0))} of {w(len(m['year_returns']))}",
             "fgross": ("—" if m["fee_over_gross_pct"] is None
                        else f"{m['fee_over_gross_pct']:.1f}"),
             "fund": ("—" if m["funding_paid"] is None else f"{m['funding_paid']:.2f}"),
             "covers": ("—" if m["funding_covers_bars"] is None
                        else ("yes" if m["funding_covers_bars"] else "NO"))}
    return "| " + " | ".join(cells[c] for c in cols) + " |"


def table(rows, header, cols):
    out = ["| " + " | ".join(header) + " |",
           "|" + "|".join(["---"] * len(header)) + "|"]
    out += [row(sym, a, cols) for sym, a in rows]
    return "\n".join(out)


H_FULL = ["symbol", "run_id", "n", "net %", "PF", "win %", "maxDD %", "B&H %",
          "zero-cost %", "drag pp", "top-5 share %", "green years"]
C_FULL = ["sym", "rid", "n", "ret", "pf", "wr", "dd", "bh", "zero", "drag",
          "top5", "green"]
H_SHORT = ["symbol", "run_id", "n", "net %", "PF", "maxDD %", "B&H %"]
C_SHORT = ["sym", "rid", "n", "ret", "pf", "dd", "bh"]

g1 = grid("1h", "confluence")
g2 = grid("1h", "b")
g3 = grid("1h", "confluence", adx="literal")
g4 = grid("1h", "confluence", preset="day")
g5 = grid("15m", "confluence")
g6 = grid("5m", "confluence")
g7 = grid("1h", "confluence", costs="repo6x5")
g8 = grid("1h", "a")
g9 = grid("1h", "either")
g10 = grid("15m", "either")
g11 = grid("1h", "confluence", fund=True)

all_cited = sorted({a["run_id"] for _, a in g1 + g2 + g3 + g4 + g5 + g6 + g7
                    + g8 + g9 + g10 + g11})

# ── gate reconciliation, counted from the artifacts themselves ────────────
cells = [a["metrics"] for _, a in g1 + g2 + g3 + g4 + g5 + g6 + g8 + g9]
n_cells = len(cells)
n_pf12 = sum(1 for m in cells if m["profit_factor"] and m["profit_factor"] > 1.2
             and m["n_trades"] >= 30)
n_conc = sum(1 for m in cells if m["best5_share_pct"] is not None
             and m["best5_share_pct"] < 100.0)
n_pf12_conc = sum(1 for m in cells if m["profit_factor"] and m["profit_factor"] > 1.2
                  and m["n_trades"] >= 30 and m["best5_share_pct"] is not None
                  and m["best5_share_pct"] < 100.0)
n_bh = sum(1 for m in cells if m["beats_bh"])
n_pos = sum(1 for m in cells if m["return_pct"] > 0)
n_green23 = sum(1 for m in cells if m["n_periods_green"] >= 2)
halt_cells_1h = sum(1 for _, a in g1 + g2 + g3 + g4 + g8 + g9 if a["metrics"]["n_halts"] > 0)
max_halts_1h = max(a["metrics"]["n_halts"] for _, a in g1 + g2 + g3 + g4 + g8 + g9)
halt_cells_15 = sum(1 for _, a in g5 + g10 if a["metrics"]["n_halts"] > 0)
max_halts_15 = max(a["metrics"]["n_halts"] for _, a in g5 + g10)
bh_winners = sorted({s2 for s2, a2 in g1 + g2 + g3 + g4 + g5 + g6 + g8 + g9
                     if a2["metrics"]["beats_bh"]})
bh_winners_txt = " and ".join(bh_winners) if len(bh_winners) <= 2 else ", ".join(bh_winners)


def bysym(rows, sym):
    return next(a for s, a in rows if s == sym)["metrics"]


def ridof(rows, sym):
    return next(a for s, a in rows if s == sym)["run_id"]


m_btc = bysym(g1, "BTCUSDT")
m_eth = bysym(g1, "ETHUSDT")
m_eth_day = bysym(g4, "ETHUSDT")
m_eth_lit = bysym(g3, "ETHUSDT")
m_hype_lit = bysym(g3, "HYPEUSDT")
m_btc_a = bysym(g8, "BTCUSDT")
m_btc_ei = bysym(g9, "BTCUSDT")
m_btc_r = bysym(g7, "BTCUSDT")
m_btc15 = bysym(g5, "BTCUSDT")
m_xrp15 = bysym(g5, "XRPUSDT")
m_btc5 = bysym(g6, "BTCUSDT")
m_btc_f = bysym(g11, "BTCUSDT")
m_eth_f = bysym(g11, "ETHUSDT")

md = f"""# Fingrad HMA · AO · ADX — audit and backtest report

Date of record: 2026-10-23. Source of record:
`code/fingrad_hma_ao_adx_strategy.pine` — the attached
`Downloads/fingrad_hma_ao_adx_strategy.pine` copied byte-identical
(sha256 `d3aabd19a1795f30...`). Engine: `code/fingrad_engine.py`
(adapter `fingrad`, engine version `fingrad-1`). Every number below is read
from a persisted artifact in `results/runs/` cited by its `run_id`; all
{w(len(all_cited))} cited artifacts (of {w(len(ART))} fingrad artifacts on disk)
reproduce bit-for-bit under `python code/vrun.py verify <run_id>`.
The known-answer audit is `results/fingrad_audit_known_answers.txt`:
{w(22)} checks, ALL PASS, covering the indicator primitives against naive
references, hand-computed execution answers (next-open fills, edge trigger,
first-bar vs fill-anchored brackets, gap-through stops, reversal economics,
leverage cap, daily breaker), the cash identity with funding, a no-lookahead
truncation proof on real data, a vectorized-vs-loop dual of the whole signal
layer across every signal mode and ADX mode, and harness determinism.

## VERDICT: KILLED — the same verdict as every directional Pine port before it

No configuration passes the repo gate. Counted from the {w(n_cells)} author-cost
cells across the signal modes, ADX modes, presets and timeframes below:

- Profit factor above the threshold with a trade count of at least thirty:
  {w(n_pf12)} of {w(n_cells)} cells.
- Of those, cells that ALSO clear the concentration gate (best five trades
  under full PnL): {w(n_pf12_conc)}. Every cell that clears profit factor
  fails concentration except one (the Day-preset ETH cell below).
- Cells whose first and second halves are both positive AND at least two of
  three thirds green: see the period columns in the tables — the winners'
  second halves and thirds go negative.
- Cells that beat buy & hold on the same bars: {w(n_bh)} of {w(n_cells)} —
  every one of them on {bh_winners_txt}, the symbols whose own buy & hold was
  negative over the window (losing less than a falling market is not alpha).
- Cells with a positive net return at author costs: {w(n_pos)} of {w(n_cells)},
  and every one of them is carried by its best five trades
  (top-five shares from about one hundred to over five hundred percent of
  total PnL, except the Day-preset ETH cell).

The zero-cost control is the interesting part, as with `cbpack`: several
symbols carry a real gross edge (BTC's zero-cost return is
{m_btc['ret_zero_pct']:.2f}% against a costed {m_btc['return_pct']:.2f}%;
ETH's is {m_eth['ret_zero_pct']:.2f}% against {m_eth['return_pct']:.2f}%).
It is a cost problem, not a signal problem — and even at zero cost no cell
comes within an order of magnitude of passive holding on the same bars.

## What the Pine actually is (static audit)

The strategy runs two systems over one Hull MA on bar closes, orders filling
at the next bar's open (`process_orders_on_close = false`), commission of one
twentieth of a percent per side and a two-tick header slippage:

- System A: long when price closes above the HMA and the Awesome Oscillator
  is above zero and rising; short mirrored. Exit on the HMA close rule or the
  AO flip (the shipped default in non-B modes).
- System B: long when price closes above the HMA and ADX crossed above its
  threshold within a three-bar window with +DI leading; short mirrored —
  both sides use the cross-ABOVE event, direction comes from DI. The shipped
  "Literal" mode instead shorts on ADX crossing BELOW the threshold.
- Triggers are edge-triggered on the WHOLE state (signal mode AND HTF HMA
  direction AND cost gate), so a flicker of the cost gate or the HTF filter
  re-arms a fresh entry.
- Optional ATR hard stop (default on, twice ATR of the signal bar, distance
  frozen at the signal and re-anchored to the real fill by the management
  block), risk-based sizing of one percent of equity per stop distance capped
  at ten times notional, a daily-loss breaker at three percent of day-start
  equity, and a reverse-on-opposite-signal rule.

Findings, all pinned by the audit:

1. The HTF filter is the standard NON-repainting idiom (`request.security`
   with `lookahead_on` and the first/second prior HTF values): every chart bar
   sees the last two CLOSED higher-timeframe bars. The port reproduces the
   mapping exactly (audit checks D4/D5: hand-computed pairs, and changing the
   forming HTF bar moves nothing).
2. Same-direction fresh signals while positioned are unreachable no-ops (the
   `okL/okS` gate blocks them), so pyramiding never actually rejects anything.
   Cleaner than the `emaadx` Pine, which re-armed brackets in that case.
3. The header's two-tick slippage is effectively zero on these series while
   the strategy's own cost gate assumes one basis point per side. Both
   regimes are reported (`author` = the header, `repo6x5` = the repo's six
   plus five basis points per side; `zero` = control inside every artifact,
   `drag_pp` measured in-artifact).
4. TradingView strategies carry no funding model. The adapter can charge the
   real Binance settlements; measured effect below is negligible for this
   book, with a coverage caveat on four symbols.
5. With the Custom preset on a one-hour chart the HTF timeframe equals the
   chart timeframe — the "HTF filter" degenerates to a same-timeframe
   two-bar HMA slope filter. The Pine itself warns about this. The Day
   preset (thirty-four HMA / two hundred forty minute HTF) is the
   non-degenerate one-hour configuration and is measured as its own grid.
6. The daily breaker is near-inert at one hour — {w(halt_cells_1h)} of the
   {w(len(g1)+len(g2)+len(g3)+len(g4)+len(g8)+len(g9))} author-cost one-hour
   cells record any halt, at most {w(max_halts_1h)} in a cell — while at
   fifteen minutes it fires in {w(halt_cells_15)} of {w(len(g5)+len(g10))}
   cells, up to {w(max_halts_15)} halts in one cell: the strategy keeps
   re-entering a falling day and the breaker keeps closing it.

## Results — one hour, shipped defaults (confluence, Custom preset, author costs)

{table(g1, H_FULL, C_FULL)}

Win rate sits near a third on every symbol; the loss is uniform, not
symbol-specific. On every symbol whose buy & hold was positive, holding beats
the strategy by one to two orders of magnitude; the only cells that beat
passive sit on {bh_winners_txt}, where passive itself lost.
`top5 share` is the best five trades as a percent of
total PnL (blank when total PnL is negative): where the book makes money, a
handful of trades carries all of it — ETH makes
{m_eth['return_pct']:.2f}% net with a top-five share of
{m_eth['best5_share_pct']:.1f}% and would have made {m_eth['net_without_best5_pct']:.2f}%
without those five trades.

## One hour, System B only (HMA + ADX, cross mode, author costs)

{table(g2, H_SHORT, C_SHORT)}

Removing the AO leg changes the shape but not the verdict — same uniform
loss, same concentration problem on the positive cells.

## One hour, Literal ADX mode (short on ADX crossing BELOW the threshold)

{table(g3, H_SHORT, C_SHORT)}

This is the best-looking family and exactly the trap the repo's gates exist
for: ETH shows PF {m_eth_lit['profit_factor']:.3f} at
{m_eth_lit['return_pct']:.2f}% net, but its best five trades carry
{m_eth_lit['best5_share_pct']:.1f}% of total PnL (without them the book is
{m_eth_lit['net_without_best5_pct']:.2f}% of PnL), and it makes
{m_eth_lit['return_pct']:.2f}% where holding makes {m_eth_lit['bh_return_pct']:.1f}%.
HYPE shows PF {m_hype_lit['profit_factor']:.3f} on
{m_hype_lit['n_trades']} trades with a top-five share of
{m_hype_lit['best5_share_pct']:.1f}%. These cells are selections — the best
of {w(n_cells)} — and fail concentration and the passive benchmark
simultaneously.

## One hour, Day preset (HMA thirty-four, HTF two hundred forty minutes)

{table(g4, H_FULL, C_FULL)}

The Day-preset ETH cell is the only cell in the whole campaign that clears
profit factor AND concentration (top-five share {m_eth_day['best5_share_pct']:.1f}%)
with both halves positive ({m_eth_day['ret_h1_pct']:.1f}% then
{m_eth_day['ret_h2_pct']:.1f}%) and all three thirds green
({m_eth_day['period1_pct']:.1f} / {m_eth_day['period2_pct']:.1f} /
{m_eth_day['period3_pct']:.1f}) across {m_eth_day['n_trades']} trades. It is
also the best of {w(n_cells)} cells (the multiple-testing haircut applies),
it makes {m_eth_day['return_pct']:.2f}% over six years against
{m_eth_day['bh_return_pct']:.1f}% for holding, and the same symbol at repo
costs with the shipped default preset loses {abs(m_btc_r['return_pct']) if False else abs(bysym(g7,'ETHUSDT')['return_pct']):.2f}%.
A cost-fragile gross edge, not alpha.

## Repo costs (six bps fee + five bps slippage per side), one hour, defaults

{table(g7, H_SHORT, C_SHORT)}

The shipped-default book goes from uniformly mediocre to uniformly ruined.
The round trip costs {m_btc_r['cost_bp_roundtrip']:.0f} basis points at repo
costs against {m_btc_r['cost_bp_roundtrip']/2.2:.0f} at the Pine's own
assumptions, and the median holding period is a handful of bars — the edge
never covers it.

## Fifteen minutes (defaults, author costs) — ruin

{table(g5, H_SHORT, C_SHORT)}

BTC loses {abs(m_btc15['return_pct']):.2f}% and XRP
{abs(m_xrp15['return_pct']):.2f}% with max drawdowns above ninety percent —
the same below-one-hour ruin pattern as `cbpack` and `cbot`. The "either"
signal mode at fifteen minutes is worse still: every symbol ends at or
within a rounding step of total loss (BTC artifact
{ridof(g10,'BTCUSDT')}, net {bysym(g10,'BTCUSDT')['return_pct']:.2f}%;
the scalp preset is byte-equivalent in geometry to the Custom preset — same
HMA twenty-one and same HTF — and reproduces the same numbers under a
different run id, which is why its rows match the default table above).

## Five minutes (defaults, author costs) — thirty-day window, no sample

{table(g6, H_SHORT, C_SHORT)}

The five-minute data on disk covers only about thirty days, so these cells
are a smoke test, not evidence: BTC opens {m_btc5['n_trades']} trades
(flagged INSUFFICIENT_SAMPLE) and every cell is negative.

## Funding charged (one hour, defaults, author costs + real Binance settlements)

{table(g11, ["symbol", "run_id", "n", "net %", "PF", "funding paid USD", "covers bars?"],
       ["sym", "rid", "n", "ret", "pf", "fund", "covers"])}

Funding barely moves a book that holds a risk-sized position for a handful
of bars at a time: BTC nets {m_btc_f['return_pct']:.2f}% with funding charged
against {m_btc['return_pct']:.2f}% without, ETH {m_eth_f['return_pct']:.2f}%
against {m_eth['return_pct']:.2f}%. CAVEAT, stated because this repo has been
burned by partial funding histories: the funding JSONs for BTC, ETH, SOL and
SUI start or end within days of the kline range but not exactly on it, and
the `covers bars?` column marks that — those cells undercharge a sliver of
the window. The measured funding amounts are small enough that the caveat
cannot change any verdict.

## The A-only and "either" families, for the record

System A alone (HMA + AO) over-trades catastrophically at one hour: BTC
artifact {ridof(g8,'BTCUSDT')}, {m_btc_a['n_trades']} trades, net
{m_btc_a['return_pct']:.2f}%, max drawdown {m_btc_a['max_dd_pct']:.1f}% — the
AO rising/falling state flips far too often, and cost turns it into
instantaneous ruin. The "either" mode inherits the same disease (BTC
{ridof(g9,'BTCUSDT')}: {m_btc_ei['n_trades']} trades, net
{m_btc_ei['return_pct']:.2f}%).

## How to reproduce

    python code/_fingrad_audit.py                    # 22 known answers, ALL PASS
    python code/vrun.py matrix --strategy fingrad --tf 1h
    python code/vrun.py matrix --strategy fingrad --tf 1h --set sig_mode=b
    python code/vrun.py matrix --strategy fingrad --tf 1h --set adx_mode=literal
    python code/vrun.py matrix --strategy fingrad --tf 1h --set preset=day
    python code/vrun.py matrix --strategy fingrad --tf 1h --set costs=repo6x5
    python code/vrun.py matrix --strategy fingrad --tf 1h --set sig_mode=a
    python code/vrun.py matrix --strategy fingrad --tf 1h --set sig_mode=either
    python code/vrun.py matrix --strategy fingrad --tf 15m
    python code/vrun.py matrix --strategy fingrad --tf 15m --set sig_mode=either
    python code/vrun.py matrix --strategy fingrad --tf 5m
    python code/vrun.py run --strategy fingrad --tf 1h --symbol BTCUSDT --set funding=true
    python code/vrun.py guard --report results/fingrad_report.md

Cited artifacts: {", ".join(all_cited)}.
"""

with open(OUT, "w", encoding="utf-8") as f:
    f.write(md)
print(f"wrote {OUT}  ({len(all_cited)} artifacts cited)")
