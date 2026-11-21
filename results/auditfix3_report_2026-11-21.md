# Audit-fix round 3 (2026-11-21) — R1/R2/R3/R7 from the re-audit at fad193a, plus one bonus defect found during verification

The third external re-audit (pinned to commit `fad193a`) confirmed all six
round-2 fixes in committed bytes and reported R1–R7. All findings were
verified against local code first; R5 was CLEARED by grep (no other callers
of the changed arity), R6 is acknowledged (the round-2 commit message
overclaimed "bit-identical" to all one hundred eighty cells — only gatecal
was bit-identical; the reports themselves scoped the claim correctly, and
the correction is recorded here rather than by rewriting pushed history).

- known-answer selftest `code/_auditfix_selftest_20261121.py`: sixty
  checks, all PASS (reworked spread scenarios are log-space and carry the
  leg high/low arrays the repo-mode book now requires).
- `code/_gates_v2_selftest.py`: all self-tests passed (unchanged this
  round; `_gates_v2.py` was not touched).

## The fixes

| id | finding | fix |
|---|---|---|
| R1 | HIGH: the N5 envelope builder swallowed every exception and degraded to an OPEN-only stop model — weaker than the pack-parity close mode the comment claimed to equal, unrecorded, and pair eighty-eight hit it BY CONSTRUCTION (its synthetic ALT-BASKET leg has no kline file) | the builder now FAILS LOUD: a spread whose leg has no kline file raises and the cell is refused, never degraded; `SpreadBook` repo mode REQUIRES the leg arrays; the artifact carries `spread_envelope_built`, `spread_stop_model` and `spread_env_range_bars`; pair eighty-eight is declared refused in the regenerated report's not-measured table |
| R2 | HIGH: the served-path fix PREFERRED served bytes but fell back to LIVE files — an undeclared read (a second leg, a label file) sat outside the cut and outside the run_id | strict served mode: after `_register_served`, an undeclared read raises "undeclared input" instead of silently reading the live file. Verified live in the selftest |
| R3 | MED-HIGH: the envelope used the PER-BAR beta while the position holds the ENTRY beta — the stop tested a re-hedged portfolio the book is not carrying (live for pair eighty-five's Kalman beta; pair eighty-one's constant beta was unaffected) | the envelope is computed per bar AT THE HELD ENTRY BETA inside the book's stop check (four corners of log(A) − beta_entry·log(B), conservative for any beta sign). Selftest: a pierce that exists only under the per-bar beta does NOT stop the book |
| R4 | MED: the spread LEDGER is a re-hedged linearisation (PnL = N·side·(s_exit − s_entry) with per-bar beta) — first-order wrong for a fixed-weight position under a drifting hedge ratio | DEFERRED, declared open: per the auditor's own sequencing this belongs to the trades_v2 campaign (the ledger rewrite and the v2 schema land together; the four constant-beta pairs are exact, only eighty-five/eighty-six carry the linearisation error) |
| R5 | MED: the bootstrap_mean_lb arity change could break unknown callers | CLEARED: the repo-wide grep finds no caller outside `_gates_v2.py` and the two updated selftests; the module-docstring `_gates` hook in `pack50_engine.py` does not call this function |
| R6 | LOW: the round-2 commit message overclaimed the bit-identical scope | acknowledged, corrected here; the reports were already correctly scoped |
| R7 | LOW: the NEW-5 sort key could raise TypeError on two unparsable labels | sentinel instead of None in the sort key |

## Bonus defect found while verifying R2

The basket cells' `symbol` param is None, so `run_symbol` inferred the
symbol from the FIRST served input — BTCUSDT — and benchmarked every basket
against **BTC's buy & hold** (the four-digit number quoted in the gen-3
cells, also visible as the BTC rows' benchmark in the regenerated report)
instead of the basket's own passive alternative. Fixed: the basket benchmark
is the EQUAL-WEIGHT buy & hold of the basket's own legs, computed from
declared inputs and carried in the artifact (`bh_equal_weight`,
`bh_benchmark`); the basket artifacts are now labeled BASKET6 (the runner's
declared binding). Measured in the new generation: basket ninety OOS buy &
hold is -24.3830 (`08b80be3a6385175`), not BTC's number.

## The re-run (generation four)

Engine bytes changed again; the gen-3 artifacts verify REFUSED by design
(append-only). The full re-screen re-ran on the fixed engine:

- one hundred seventy-eight cells: the two pair-eighty-eight cells are
  REFUSED by the R1 fix (synthetic leg, no envelope possible) and declared
  in the report's not-measured table — the honest cost of refusing to
  degrade silently.
- the surviving spreads carry the envelope metadata (pair eighty-five DEV
  `c3a368b728987ca3`: `spread_envelope_built` true, stop model
  "intrabar_leg_envelope_at_entry_beta", twelve thousand five hundred ten
  bars with a real leg range).
- pair eighty-nine's numbers are BIT-IDENTICAL to gen-3 (its beta is
  constant, so the entry-beta envelope equals the old one) — its explosive
  headline is the pre-existing linearised-ledger pathology, failed by the
  screen long ago, and is exactly what the deferred R4 ledger rewrite
  addresses.
- the regenerated `results/prompts100_rescreen_report.md` is
  `guard --strict` OK: the same verdict shape (four DEV screen passes, zero
  OOS verdict passes).
- integrity sweep `code/_auditfix_verify_sweep_20261121.py` + the
  calibration (unchanged this round, `_gates_v2.py` untouched):
  see the tally below (counts in words).

- one hundred seventy-eight p100screen cell artifacts verify OK, zero
  REFUSED, zero STALE (sweep `code/_auditfix_verify_sweep_20261121.py`),
  plus the gatecal calibration `d590af40751a6002` — whose sources are
  untouched this round — carrying its earlier bit-for-bit verify forward:
  generation-four integrity is one hundred seventy-nine OK, zero REFUSED.

## Still open

- R4 (above), and everything the auditor lists as the binding constraint:
  v2 joint power 0.095 at n300/d20; no engine emits `trades_v2` (the next
  campaign: the v2 ledger from the p100 Book — with R4 resolved first for
  spread books — plus the v2 PER-GATE power table so the joint's killers
  are named); `gate_g7` PBO trivially passes when `ctx.pbo` is None;
  POLICY-vs-doc mismatches; `slip_stop_mult` placeholder;
  `notional_per_equity` default; exit-day `_daily_returns`; purge without
  embargo.
