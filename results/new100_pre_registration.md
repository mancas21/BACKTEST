# Pre-registration — the NEW-100 screening campaign

Date: 2026-11-20. Written BEFORE the first artifact of the campaign exists.
The pack: `results/new100_pack.md` (N-001..N-100), generated under
`STRATEGY_GENERATOR_PROMPT.md` v1.0 and frozen as of this file. Any spec
edit after the first artifact invalidates the affected artifacts.

## What this campaign is

One hundred NEW candidate books, generated from this repository's own
evidence base (survivor DNA, the ~20-30 bps/trade detection floor, the
killed-families list, the top-100 ranking's measured near-misses), run
through the repo's standard battery. This is a SCREEN, not a verdict
campaign: the battery decides, per REGLA 1 each book is judged only on its
own artifacts, and the kill list is design guidance, never a pre-gate.

## What "works" can honestly mean here

The measured record: ~1500 predecessor books, zero full passes alive, a
null book passes the calibrated gates 0-0.25% of the time, and the gates
detect a net per-trade edge of roughly 20-30 bps. The pack's designs aim at
that floor; nobody — including this pack's author — can promise survivors.
The deliverable is the artifacts and the verdicts, whatever they are.

## Engine and execution (declared)

* Phase 1 — the ~62 single-symbol directional books (F1, F3 directional
  subsets, F5 directional subsets, F6): engine `code/np100_engine.py` over
  the audited `p100_screen_engine` `Book` (signal on the closed bar, fill
  at the next open, stop-first on ties, gap-through at the open, 1% risk
  per trade, the pack's day counters where a spec declares one). Repo cost
  regime: 5.0 fee + 0.5 slip bps per side (11 bps RT). Funding at the real
  settlement instants for funding-covered symbols; the funding file is
  bound into every run_id.
* Phase 2 — the 12 F2 grid books: fills resolved on the 1m tape
  (trade-through, not touch) via the `xrp_neutral_engine_paper_1m`
  machinery pattern; declared fill_model = 1m_resolved. Maker fee 2 bps,
  taker 5 bps, funding at real settlements.
* Phase 3 — the 20 F4/F5 bundle books: the xs-engine pattern (next-open,
  resize-to-target every rebalance with average-cost basis — the fix the
  xsf campaign measured, hysteresis bands, dollar/vol-scaled sizing, 11 bps
  RT per leg, funding both legs).
* Phase 4 — the 10 F7 equities books: `data_dir` override onto the Alpaca
  1d SPY/QQQ CSVs, cost regime 1.2 bps RT (the measured eqpack block),
  no funding (declared).
* Pre-flight validator first (`code/_np100_preflight.py`): every cell on a
  60-day slice, in minutes, BEFORE any long run — the s101 lesson, which
  would have caught that pack's three failed 86-minute passes.

## Gates (the standard battery, unchanged)

The v2 battery (G1-G11 in `GATES_AND_RULES.md`): PF ex-cost > 1.2, n >= 100
full / >= 30 OOS, expectancy Ljung-Box, cost < 30% of gross, walk-forward
folds, concentration (top-5 trades < 100% of PnL), period split, bootstrap
CI above zero, neighborhood stability (one step each side), buy & hold
comparison, null calibration at the book's own n. Phase-2 grid books carry
the additional fill-model certification requirement (1m resolution now,
aggTrade replay before any PASS claim).

## Kill rules (unchanged)

OOS PF < 1 = KILL. No rescue loops, no window picking, no parameter
fishing. Neighborhood failures are kills, not tuning invitations. Every
verdict cites its run_id and its artifact path.

## Honesty rules

* The pack's per-trade edge and trade-count numbers are PRIORS declared by
  the generator contract; they are never quoted as results.
* Phase 1 runs all cells before any survivor is named; no sequential
  peeking that would let later specs copy earlier survivors.
* Multiple-testing haircut applies in full: one hundred candidates on the
  same data means the weakest survivor is noise until it survives a forward
  paper record.

## Deliverables

1. Artifacts per cell in `results/runs/` with run_ids.
2. `results/new100_report.md` (guard --strict) with the full verdict table.
3. Registry regenerated; STATUS.md verdict entry if the state of the world
   changes (i.e., if anything survives; the zero-survivor case is logged as
   a screened pack like its predecessors).
