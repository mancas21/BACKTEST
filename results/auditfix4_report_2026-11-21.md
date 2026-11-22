# Audit-fix round four (2026-11-21) — D2's silent stop-disable, D5's benchmark window, and the retraction

The fourth external re-audit (pinned to the current main commit at the time) confirmed R1/R2/R3 and
the basket-benchmark bonus as genuinely fixed, and caught the regression
the R1 rewrite introduced: **the finiteness guard its predecessor had was
dropped**. All findings verified against local code before fixing.

- known-answer selftest `code/_auditfix_selftest_20261121.py`: sixty-four
  checks, all PASS (new: NaN leg bar refuses, −inf leg bar refuses,
  zero-range envelope refuses, `envelope_built` is False before the run and
  a measured True after).

## The fixes

| id | finding | fix |
|---|---|---|
| D2 | HIGH: a NaN leg bar made both envelope corners NaN (Python's order-dependent max/min), and NaN comparisons are False — **a missing or misaligned bar silently disabled the stop in both directions**; log(0) = −inf fabricated a spurious stop. The R1 rewrite dropped the `np.where(np.isfinite(...))` guard its predecessor had, and the selftest could not see it because it feeds clean synthetic arrays | `SpreadBook.run` now asserts, over the TRADED window, that all four leg arrays are finite — any non-finite bar raises with the count — and refuses a zero-range envelope ("the loaders disagree or the data is degenerate"). Fail loud, never skip |
| D5 | MED-HIGH: the round-3 basket benchmark fixed the assets but not the window — each leg's buy & hold ran over its OWN listing window (BTC listing in twenty-nineteen, SUI in twenty-twenty-three, HYPE in twenty-twenty-five) while the basket trades the aligned intersection; also `buy_and_hold_pct` returns None on a degenerate window and `np.mean` would TypeError | the equal-weight benchmark is computed from the basket's own aligned panel closes over the basket's traded window `[start, end]`; a degenerate window or a missing boundary close yields None (honest N-A), never an exception |
| D6 | MED: `spread_envelope_built` was inferred (`not pack_conventions`) — an artifact could report "built" next to zero range bars and every stop disabled | the flag starts False and becomes True only after the D2 finiteness assertion passes over the traded window; `spread_env_finite_bars` travels with it |
| D7 | MED: R3 made the stop reference the entry-beta portfolio while the mark-to-market still references the per-bar-beta spread — R4 is now an internal inconsistency, not a linearisation nicety | declared, not hidden: spread artifacts carry `spread_pnl_basis: "rehedged_per_bar_beta_linearisation"` (pack parity mode: `"pack_linearised_spread"`). The leg-PnL ledger rewrite (R4) is the first item of the trades_v2 campaign |
| D3 | LOW: `pack_conventions` assigned twice (the cast guard, then the raw overwrite) | the second assignment deleted; `charge_funding` now derives from the cast value |
| D4 | LOW: the dead zero-range DataFrame in `run_pair` documented the removed open-only model | deleted |
| D1 | LOW: the envelope refusal probed the LIVE filesystem inside a cut-enforced run | under strict serving the check consults the served map (declared inputs); the live check remains for standalone mode only |
| D8 | NOTE: strict mode changed missing-funding behaviour (undeclared funding JSON now raises instead of silently returning zeros) | declared: the gen-5 runner log shows the refusals were exactly pair eighty-eight's two cells (envelope refusal); **zero** cells refused for funding reasons |

## The retraction (corpus bookkeeping)

Pair eighty-eight is **not-measurable**, not killed — different verdicts,
recorded differently. More important, per the auditor: the pair-88 numbers
published in every generation of the rescreen report up to gen-3 were
produced under the silently-degraded open-only stop model. **They are
RETRACTED, not merely superseded** — the engine was wrong, not replaced.
The retraction is recorded in `code/_engine_lock.json`'s supersession note
and here; no current report cites them.

## The measurement the auditor asked for

Every surviving spread cell now publishes its envelope metadata (measured
inside the artifact, guard-backable): `spread_envelope_built` (True only
after the finiteness assertion), `spread_env_finite_bars` (finite bars over
the traded window), `spread_env_range_bars` (bars with a real leg range,
over the full frame), `spread_stop_model` and `spread_pnl_basis`. The ten
cells of pairs eighty-one, eighty-two, eighty-five, eighty-six and
eighty-nine: finite bars from two thousand nine hundred sixty-six (pair
eighty-five DEV, its segment) to two hundred four thousand nine hundred
twenty-nine (pair eighty-nine DEV), range bars from twelve thousand five
hundred ten to two hundred forty-four thousand three hundred sixty-seven —
non-zero everywhere, so the intrabar spread stop is a measurement, not a
claim. Pair eighty-five DEV `99dd566e2a4f7372`: finite 2966 / range 12510.

## The re-run (generation five) and integrity

- one hundred seventy-eight cells re-run on the fixed engine; the
  regenerated `results/prompts100_rescreen_report.md` is `guard --strict`
  OK with the same verdict shape (four DEV screen passes, zero OOS verdict
  passes); the gatecal calibration is untouched this round
  (`_gates_v2.py` unchanged) and carries its verify forward.
- integrity sweep `code/_auditfix_verify_sweep_20261121.py`: see the tally
  below (counts in words).

- one hundred seventy-eight p100screen cell artifacts verify OK, zero
  REFUSED, zero STALE, plus the gatecal calibration `d590af40751a6002`
  (sources untouched this round): generation-five integrity is one hundred
  seventy-nine OK, zero REFUSED (sweep
  `code/_auditfix_verify_sweep_20261121.py`).

## Still open

- **R4 first**: the spread ledger is declared as a re-hedged per-bar-beta
  linearisation (`spread_pnl_basis`); the leg-PnL ledger rewrite is the
  first item of the trades_v2 campaign, so the spread books' `gross_ret`
  describes the portfolio the book actually held.
- v2 joint power 0.095 at n300/d20; no engine emits `trades_v2` yet;
  `gate_g7` PBO passes trivially without a caller-supplied matrix;
  POLICY-vs-doc mismatches; `slip_stop_mult` placeholder;
  `notional_per_equity` default; exit-day `_daily_returns`; purge without
  embargo.
