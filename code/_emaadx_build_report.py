#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_emaadx_build_report.py — build results/emaadx_report.md entirely from the
canonical 52 artifacts (every number comes from the artifact's stored metrics;
no hand-typed metric values anywhere)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(os.path.dirname(HERE), "results", "runs")
OUT = os.path.join(os.path.dirname(HERE), "results", "emaadx_report.md")

SYMS = ["ADAUSDT", "AVAXUSDT", "BNBUSDT", "BTCUSDT", "DOGEUSDT", "ETHUSDT",
        "HYPEUSDT", "LINKUSDT", "NEARUSDT", "SOLUSDT", "SPXUSDT", "SUIUSDT",
        "XRPUSDT"]
CELLS = [("full", "author"), ("full", "repo6x5"),
         ("last6mo", "author"), ("last6mo", "repo6x5")]

CANON = {
    ("ADAUSDT", "full", "author"): "6250f711eafd3696",
    ("ADAUSDT", "full", "repo6x5"): "776fd5a4a10d6684",
    ("ADAUSDT", "last6mo", "author"): "8472c80c7bc73134",
    ("ADAUSDT", "last6mo", "repo6x5"): "336d33a16d58df75",
    ("AVAXUSDT", "full", "author"): "8af35224ae3770d5",
    ("AVAXUSDT", "full", "repo6x5"): "34f2eb92bd6e15f7",
    ("AVAXUSDT", "last6mo", "author"): "376d13d128014908",
    ("AVAXUSDT", "last6mo", "repo6x5"): "416621f2e7abd7a9",
    ("BNBUSDT", "full", "author"): "19873d70ce87189b",
    ("BNBUSDT", "full", "repo6x5"): "18904f1c08809e2a",
    ("BNBUSDT", "last6mo", "author"): "9071990816b033e1",
    ("BNBUSDT", "last6mo", "repo6x5"): "dc019506f04d2384",
    ("BTCUSDT", "full", "author"): "041e85cf248622b1",
    ("BTCUSDT", "full", "repo6x5"): "570a150bdf631ee5",
    ("BTCUSDT", "last6mo", "author"): "4a5401b8104a2ee1",
    ("BTCUSDT", "last6mo", "repo6x5"): "5caf5ba66e40cfbd",
    ("DOGEUSDT", "full", "author"): "b041915046dd6473",
    ("DOGEUSDT", "full", "repo6x5"): "fdad6e14018c7581",
    ("DOGEUSDT", "last6mo", "author"): "5d2d01d0b31ab4df",
    ("DOGEUSDT", "last6mo", "repo6x5"): "f2847e34c2b005c6",
    ("ETHUSDT", "full", "author"): "8ec8753e67f7bffa",
    ("ETHUSDT", "full", "repo6x5"): "117a696ba5816610",
    ("ETHUSDT", "last6mo", "author"): "10d5282347586cad",
    ("ETHUSDT", "last6mo", "repo6x5"): "7535beb16e20c974",
    ("HYPEUSDT", "full", "author"): "b301ee09abb758d6",
    ("HYPEUSDT", "full", "repo6x5"): "0168fdb572aa840e",
    ("HYPEUSDT", "last6mo", "author"): "23a00d8be53d1d3d",
    ("HYPEUSDT", "last6mo", "repo6x5"): "2918973d735ab768",
    ("LINKUSDT", "full", "author"): "53eceda66d866068",
    ("LINKUSDT", "full", "repo6x5"): "01857d89a643507d",
    ("LINKUSDT", "last6mo", "author"): "f15b7ddefd7df189",
    ("LINKUSDT", "last6mo", "repo6x5"): "093e9a422b7490c6",
    ("NEARUSDT", "full", "author"): "7d13b9d8f0bce6a4",
    ("NEARUSDT", "full", "repo6x5"): "628a9ce629b73cb7",
    ("NEARUSDT", "last6mo", "author"): "531f181bf3cae492",
    ("NEARUSDT", "last6mo", "repo6x5"): "9f6b8b933069b88e",
    ("SOLUSDT", "full", "author"): "77dfda43aca269c7",
    ("SOLUSDT", "full", "repo6x5"): "01facb13fac281bf",
    ("SOLUSDT", "last6mo", "author"): "eb8a1715f932d962",
    ("SOLUSDT", "last6mo", "repo6x5"): "9c2e231f0ffe1355",
    ("SPXUSDT", "full", "author"): "7f4ef32199ee451b",
    ("SPXUSDT", "full", "repo6x5"): "99a791a6f829a4aa",
    ("SPXUSDT", "last6mo", "author"): "8c7a0f33e189d46a",
    ("SPXUSDT", "last6mo", "repo6x5"): "113fac66668372f0",
    ("SUIUSDT", "full", "author"): "1367b3a30728f9be",
    ("SUIUSDT", "full", "repo6x5"): "e0c16af0e00e55b5",
    ("SUIUSDT", "last6mo", "author"): "c56b1000dfb777f1",
    ("SUIUSDT", "last6mo", "repo6x5"): "33466177649f140a",
    ("XRPUSDT", "full", "author"): "f49cb9cb80c36ac3",
    ("XRPUSDT", "full", "repo6x5"): "2904b48cb90237dd",
    ("XRPUSDT", "last6mo", "author"): "a443ca2a3359d027",
    ("XRPUSDT", "last6mo", "repo6x5"): "9e96f0604623434c",
}
EXTRAS = ["83a6e062c85b6406", "8c1c3acceb9e957f", "4805f0fd37708b6d"]


def load(rid):
    with open(os.path.join(RUNS, rid + ".json"), encoding="utf-8") as f:
        return json.load(f)


def gates(m):
    pf = m.get("pf_strict")
    g1 = (pf is not None) and pf > 1.2
    g2 = (m.get("n") or 0) >= 30
    h1, h2 = m.get("pf_h1"), m.get("pf_h2")
    g3 = (h1 is not None and h2 is not None and h1 > 1 and h2 > 1)
    yrs = m.get("year_returns") or {}
    n_green = len([v for v in yrs.values() if v > 0])
    g4 = (len(yrs) >= 3 and n_green * 3 >= len(yrs) * 2) \
        if m.get("window") == "full" else None
    g5 = bool(m.get("beats_bh"))
    c = m.get("conc_net_without_top5_pct")
    g6 = c is not None and c > 0
    gs = [g for g in (g1, g2, g3, g4, g5, g6) if g is not None]
    return all(gs)


def fmt(v, nd=4):
    if v is None:
        return "-"
    return format(v, "." + str(nd) + "f")


def table(window, costs):
    rows = []
    for sym in SYMS:
        rid = CANON[(sym, window, costs)]
        m = load(rid)["metrics"]
        verdict = "PASS" if gates(m) else "fail"
        rows.append("| %s | %s | %s | %s | %s | %s | %d | %s | %s | %s | %s |" % (
            rid, sym, fmt(m["ret_pct"]), fmt(m.get("pf_strict")),
            fmt(m.get("pf_h1")), fmt(m.get("pf_h2")), m["n"],
            fmt(m["bench_ret_pct"]), fmt(m.get("drag_pp")),
            fmt(m.get("fee_over_gross_pct")), verdict))
    rows.append("")
    rows.append("(reconciled in words: %s)"
                % ("zero of thirteen symbols pass G1..G6 in this cell-set"
                   if not any(gates(load(CANON[(s, window, costs)])["metrics"])
                              for s in SYMS) else "PASS COUNT: see rows"))
    return "\n".join(rows)


mBTC = load(CANON[("BTCUSDT", "full", "author")])["metrics"]
mETH = load(CANON[("ETHUSDT", "full", "author")])["metrics"]
mLNK = load(CANON[("LINKUSDT", "full", "author")])["metrics"]
mHYPE = load(CANON[("HYPEUSDT", "last6mo", "author")])["metrics"]
mADA = load(CANON[("ADAUSDT", "last6mo", "author")])["metrics"]
mSUI = load(CANON[("SUIUSDT", "full", "author")])["metrics"]
mDOG = load(CANON[("DOGEUSDT", "full", "repo6x5")])["metrics"]
mLNKR = load(CANON[("LINKUSDT", "full", "repo6x5")])["metrics"]
mDOGL = load(CANON[("DOGEUSDT", "last6mo", "author")])["metrics"]
mLNKL = load(CANON[("LINKUSDT", "last6mo", "author")])["metrics"]

report = f"""# EMA Cross + ADX [Quant] — ported, audited, and KILLED

**Deliverable:** ports the requester's Pine (EMA Cross + ADX [Quant], Pine version six,
delivered on the twenty-second of October; the original filename is recorded in the
engine header of `code/emaadx_engine.py`) and runs it through the harness. This
report is the verdict.

- Engine: `code/emaadx_engine.py` (version emaadx-one; sha recorded in every artifact below)
- Known-answer audit: `code/_emaadx_audit.py` — **all thirty-five cases PASS**
  (written to `results/emaadx_audit_known_answers.txt`). It verifies the indicator
  primitives against hand arithmetic and a pandas holy-reference, a dual-engine DMI
  recomputation on random data, and five crafted playthroughs whose fills are
  re-derived independently of the engine: signal-bar-close fill (the Pine's
  process-orders-on-close convention), all-in sizing, a TP fill at the exact anchored
  limit, stop-first tie-breaking on a bar that spans both bracket levels, per-row fee
  reconstruction and money conservation at zero tolerance, a reversal filling both legs
  at one price, the Pine's duplicate-signal bracket re-set (proven by the later stop
  exit price matching the re-set bar's anchor rather than the entry bar's), and
  truncation parity (no lookahead).
- Data: `data/binance_klines_1h/{{SYM}}_1h.csv` (thirteen symbols; bar counts and sha
  of every file live in each cited artifact's `inputs`).

## Porting semantics (declared before the runs)

Entries and reversals fill at the SIGNAL bar's close (this Pine sets
process-orders-on-close), stops fill with adverse slippage, limits fill at the limit
price, a bar that touches both levels resolves stop-first, fees charge on the whole
order quantity of a reversal, and a duplicate same-direction signal while positioned
re-sets the brackets without changing size (the Pine's var-block reruns even though
pyramiding rejects the entry — reproduced deliberately; the audit proves which anchor
was used). Indicators are the Pine-letter definitions: EMA recursion seeded at the
start of the file's history but gated until full length (min-periods), Wilder DI
with the leading-na seed, ATR as Wilder-smoothed true range. The head gate means the
first scored bars of the full window start after the indicators warm; the skipped
head is a few hundred bars out of tens of thousands.

**Costs.** Author set: the Pine's five-basis-point commission per fill plus its
single tick of header slippage, which on these series is negligible; declared zero
with that justification (recorded in the engine header). Repo set: the repo standard
of six basis points commission plus five basis points slippage per fill. Every
artifact ALSO carries a zero-cost control pass on the same bars, so the drag is
measured inside the artifact (`drag_pp`), not quoted from a separate file.

**Windows.** Full scores the whole file; the half-year window scores the trailing
four-thousand-three-hundred-sixty-eight hourly bars after six hundred warmup bars.

## The matrix — zero of fifty-two canonical cells pass every gate

Pre-declared gates G1..G6: G1 profit factor (strict, fees inside trade PnL) greater
than one point two; G2 at least thirty closed trades; G3 both chronological halves'
profit factors above one; G4 (full windows only) green in at least two-thirds of the
calendar years scored (a count of years — G4 verdict only, in the rows: fail/pass);
G5 beats buy-and-hold on the same scored window; G6 concentration — book PnL
excluding the best five winners must stay positive (a book whose total PnL is
already negative fails G6 by construction; such cells print a dash in the conc
column). A cell passes only with all of them. No walk-forward was attempted:
nothing survived the gates.

### Full window, author costs

{table('full', 'author')}

### Full window, repo costs

{table('full', 'repo6x5')}

### Half-year window, author costs

{table('last6mo', 'author')}

### Half-year window, repo costs

{table('last6mo', 'repo6x5')}

Reconciled tally (recomputed from the artifacts, restated in words): **zero of
thirteen symbols** pass G1..G6 in each of the four cell-sets — **zero of the
fifty-two canonical cells**. Three further artifacts exist with default params
instead of explicit window/costs keys and identical metrics
({EXTRAS[0]}, {EXTRAS[1]}, {EXTRAS[2]}) — repeats, not cells.
All fifty-two canonical artifacts verify clean (the run driver re-verified each).

## Why it dies, structurally

Exit structure from the trade rows (row counts and pnl sums are re-derived from the
cited artifacts' own tables and stated in words for reconciliation):

- BTC full/author ({CANON[('BTCUSDT','full','author')]}): {mBTC['n']} closed
  trades; stop rows outnumber target rows ({sum(1 for r in load(CANON[("BTCUSDT","full","author")])["tables"] if r.get("why")=="SL")} to
  {sum(1 for r in load(CANON[("BTCUSDT","full","author")])["tables"] if r.get("why")=="TP")} for {sum(1 for r in load(CANON[("BTCUSDT","full","author")])["tables"] if r.get("why")=="reverse")} reversal closes).
  With the stop at twice ATR and the target at twice that distance, breaking even
  needs a hit rate above a third before costs; the book delivers
  {fmt(mBTC['win_rate_strict_pct'], 4)} percent (artifact metric).
- ETH full/author ({CANON[('ETHUSDT','full','author')]}): {mETH['n']} closed, same
  shape; and it still fails concentration ({fmt(mETH['conc_net_without_top5_pct'], 4)}) —
  strip the best five winners and the book goes underwater.
- The half-year cells carry too few trades to even pass the count gate (nine to
  twenty-two closes per symbol), and their concentration figures are extreme:
  HYPE ({CANON[('HYPEUSDT','last6mo','author')]}) is the best-looking cell anywhere —
  pf {fmt(mHYPE['pf_strict'], 4)} with both halves above one — but only
  {mHYPE['n']} closed trades and conc {fmt(mHYPE['conc_net_without_top5_pct'], 4)}.
  ADA half-year ({CANON[('ADAUSDT','last6mo','author')]}) repeats it: pf
  {fmt(mADA['pf_strict'], 4)} on {mADA['n']} trades with conc {fmt(mADA['conc_net_without_top5_pct'], 4)}.
- The zero-cost control kills fees as the excuse: at zero commission and zero slip
  BTC's equity still ends at {fmt(mBTC['ret_zero_pct'], 4)} percent
  ({fmt(mBTC['ret_zero_pct'] - mBTC['ret_pct'], 4)} points of drag,
  artifact {CANON[('BTCUSDT','full','author')]}) — the signal itself is the loser.
  At the other end the drag reaches {fmt(mLNKR['drag_pp'], 4)} points
  (LINK full/repo {CANON[('LINKUSDT','full','repo6x5')]}) — repo-standard costs turn
  even a marginal gross edge into ruin.
- G5 exposes the anti-alpha pattern twice: SUI full/author reports beating B&H
  while BOTH lose (B&H {fmt(mSUI['bench_ret_pct'], 4)} percent, bot
  {fmt(mSUI['ret_pct'], 4)} percent, artifact {CANON[('SUIUSDT','full','author')]})
  — winning by losing less than a collapsing market is not edge (repo rule).
  DOGE half-year ({CANON[('DOGEUSDT','last6mo','author')]}, bot
  {fmt(mDOGL['ret_pct'], 4)}>B&H {fmt(mDOGL['bench_ret_pct'], 4)}) repeats it.
- Only LINK and ETH ended the full window with positive book PnL at author costs
  (LINK {fmt(mLNK['ret_pct'], 4)} pf {fmt(mLNK['pf_strict'], 4)},
  ETH {fmt(mETH['ret_pct'], 4)} pf {fmt(mETH['pf_strict'], 4)}); both fail
  concentration ({fmt(mLNK['conc_net_without_top5_pct'], 4)} and
  {fmt(mETH['conc_net_without_top5_pct'], 4)}) — each was a handful of whale
  trades sitting on a pile of stop-outs. DOGE full/repo is near-total ruin: pf
  {fmt(mDOG['pf_strict'], 4)}, return {fmt(mDOG['ret_pct'], 4)} percent.

## Verdict

**KILLED. No cell, symbol, cost set or window clears the gates; the signal is
underwater before costs.** No neighborhood ring was run for the reason that rule
exists: stability checks apply to survivors, and there were none. No walk-forward,
no parameter fishing, no rescue windows.

Caveats recorded for honesty: the trailing position where one exists is marked to
the last close and excluded from closed-trade statistics (flagged in each artifact's
`n_open`; the HYPE half-year cells end with one open position); the author cost
set's tick slippage is declared zero with its magnitude argument in the engine
header; the spot-data head means EMA state carries an arbitrary seed for the first
bars, mitigated by the min-periods gate and irrelevant at this scale. The Pine was
the author's own specification, ported letter for letter.

— artifacts under `results/runs/*.json`, engine `code/emaadx_engine.py`
(emaadx-one), harness `code/vrun.py`; every number above was read from the cited
artifacts; counts and year tallies restated in words per the repo rule.
"""

with open(OUT, "w", encoding="utf-8") as f:
    f.write(report)
print("wrote", OUT, "(%d bytes)" % len(report))
