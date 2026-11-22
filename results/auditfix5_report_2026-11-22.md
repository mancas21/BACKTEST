# Audit-fix round five (2026-11-22) — E1's window mismatch, the reps-floor trap, and the v2 per-gate power table

The fifth external re-audit confirmed all eight round-four fixes and made two
pre-flight demands before the trades_v2 campaign: E1's window mismatch and
the calibration-reps check. Both were executed first, exactly as prescribed
— and the reps check found the auditor's suspicion **confirmed in the
artifact**.

- known-answer selftest `code/_auditfix_selftest_20261121.py`: sixty-nine checks (the count in words), all PASS (new: the traded-window range invariant, a zero-range
  traded window refusing even when the full series has range elsewhere, the
  reps-floor raise, and the expectancy field).

## E1 — the two envelope counts were measured over different windows (HIGH, confirmed)

`env_range_bars` was computed over the FULL series (run_pair) while
`env_finite_bars` covered the traded window — the round-four numbers proved it:
max finite two hundred four thousand nine hundred twenty-nine (89 DEV)
against max range two hundred forty-four thousand three hundred sixty-seven
(89's full series). The OOS spread cells carried a range count ~7 times
their window length, and worse: **a traded window of all zero-range bars
passed the guard because the full series had range elsewhere** — the
envelope degenerated to gap-only and the open-only model re-entered through
the window mismatch, the same class as D5 one layer down.

Fix: the range is now measured over the SAME traded window as the
finiteness assertion, zero refuses, and the invariant `range <= finite` is
asserted. The gen-six artifacts show it: pair eighty-one OOS `a5d8ada20f7595ba` finite = range (eight thousand
eight hundred bars, quoted in words); pair eighty-nine OOS
`a427e48da9d9cdaa` finite = range (thirty-six thousand four hundred
sixty-eight bars); pair eighty-nine DEV `e08d9a41af3f4240` finite
204929 / range 204923. (The gen-five numbers quoted above came from the
superseded generation; the current ones are these.) The intrabar spread
stop is measured over the window the book actually trades.

## The reps check — the reference-layer cross-check WAS floor-suppressed (confirmed)

`_gates_v2.null_calibration` defaulted to `reps=400` — below the
`boot_reps_floor` (the POLICY constant of five hundred). The gatecal artifact's reference-layer cross-check
carried the proof: **G1 0.0 and G9 0.0 in every trial, including edge twenty
where G4 showed roughly half power (zero-point-four-nine-five, a value the
floor-suppressed artifact itself carries)** — the by-gate table was floor-suppressed, not
measured.

Two consequences, separated honestly:

- **The headline v2 joint (the zero-point-nine-five at n300/d20 published in the round-two calibration) is GENUINE** — gatecal's v2
  booleans call the gate2 functions directly, which never had the floor;
  that is why the v2 column stayed bit-identical across the floor's
  introduction. Confirmed, not assumed.
- The reference-layer cross-check was garbage and has been re-provisioned:
  `null_calibration`'s default is now 2000 and **a call below the floor
  RAISES** ("raise the reps, do not lower the floor"), and the gatecal xref
  runs at reps 2000 / n_sims 400.

## The v2 per-gate power table — published, with the sanity check passing

The new calibration `9183c116b24003c3` publishes `pass_rate_by_gate` for
G1..G9+G11 over n {30,100,300} × edges {0,20} (twelve cells, four hundred
sims each, reps 2000). At n300:

| gate | d0 | d20 |
|---|---|---|
| G1 | 0.0 | 0.2725 |
| G3 | 0.0175 | 0.39 |
| G4 | 0.0175 | 0.425 |
| G5 | 0.0 | 0.1525 |
| G6 | 0.0 | 0.0925 |
| G7 | 0.0 | 0.2575 |
| G8 | 0.0 | 0.115 |
| G9 | 0.025 | 0.43 |
| G11 | 1.0 | 1.0 |
| joint | 0.0 | 0.0825 |

- **The sanity check passes exactly**: expectancy d20 minus d0 =
  20.0 bps (`expectancy_sanity` in the artifact) — the v2 path scores the
  right trades; there is no repeat of A2 inside it.
- **The joint destroyers are now named**: at n300/d20 the binders are G6
  0.0925 (concentration), G8 0.115 (cost robustness), G5 0.1525
  (benchmark), G7 0.2575 (DSR) — while G4/G9 run at 0.39-0.43 and G2/G11
  do not bind at n300. This is the answer the last two audits asked for.
- The null at n300/d0 is clean (joint 0.0, every gate at or near its
  floor) — the power table is not riding on false positives.
- The properly-provisioned reference-layer joint at n300/d20 (0.0825) is
  consistent with the headline joint published by the engine's own v2
  booleans (the round-two report's zero-point-nine-five).

## E3 — book_type declared

Every spread and basket artifact now carries `book_type: "neutral"` (family
A: `"directional"`) — the field GateContext branches G5 on, declared at the
source rather than defaulted later.

## E2 — declared, not changed

The basket's book genuinely trades `[max(1, start), end]` (it has no
purge-skip in its loop, unlike family A's trade_from/trade_to), so its
benchmark stays on the book's actual window; the single-leg books benchmark
on trade_from/trade_to. The convention difference is one bar in principle
and is now stated here rather than silently unified.

## The re-run (generation six) and integrity

- one hundred seventy-eight p100screen cells re-run on the fixed engine;
  pair eighty-eight remains refused and declared; the regenerated
  `results/prompts100_rescreen_report.md` is `guard --strict` OK with the
  same verdict shape (four DEV screen passes, zero OOS verdict passes).
- the gatecal re-run produced `9183c116b24003c3` (the per-gate table above).
- integrity sweep `code/_auditfix_verify_sweep_20261121.py`: see the tally
  below (counts in words).

- one hundred seventy-eight p100screen cell artifacts verify OK, zero
  REFUSED, zero STALE, plus the new gatecal calibration
  `9183c116b24003c3` reproducing bit-for-bit: generation-six integrity is
  one hundred seventy-nine OK, zero REFUSED (sweep
  `code/_auditfix_verify_sweep_20261121.py`; the single REFUSED in the
  first pass was the superseded gen-five calibration hardcoded in the sweep's
  extra list, since repointed).

## Next — the trades_v2 campaign, spec frozen in memory

The staged spec (R4's leg-PnL ledger first — with the mark-to-market fixed
to the same held-beta basis, resolving D7; then the per-trade v2 fields
with the mandatory per-trade decomposition invariant
gross_ret − cost_ret − funding_ret == pnl/(qty·raw_entry) to one part in a trillion; then a
MEASURED GateContext — `notional_per_equity` is the one change that could
un-suppress much of the joint, since the 1.0 default makes G9 compound full
equity over a 1%-risk book; then G7's PBO wiring) is recorded in
`tradesv2-campaign-spec.md` and begins next. The auditor's own framing
stands: if after all stages the v2 power at n300/d20 is still ~0.10 with a
correct notional and reps at 2000, the next conversation is gate design —
not strategies.
