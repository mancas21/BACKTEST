# Audit-fix round six (2026-11-22) — the planted edge was GROSS, not net: the gates are exonerated and the power curve is real

The sixth external re-audit made the interpretation finding that five rounds
of re-measurement had been building on: **the calibration's planted drift is
GROSS, not net**. `random_entry_trades` adds `edge_bps/1e4` to the gross
per-trade return and `_prep` computes `net = gross − cost − funding` — so
the old d20 cell was a NET edge of +9 bps/trade at the 11 bps round trip,
and at the G8 stress rung (2× cost) the net mean was −2 bps: **statistically
untestable**. With per-trade dispersion in the hundreds of bps on
random-entry 1h books, d20 at n=300 is a t of roughly half — the low
G6/G5/G7/G8 rates were the correct answer to noise, not gate blindness.
The auditor owned their own share of this (the round-1 framing ("a genuine twenty
bps edge is rejected nine times in ten") treated d20 as net), and so do
I: the round-5 "sanity check" verified that the drift PROPAGATES, not that
the edge was strong.

The corrected statement: **the v2 gate set's power at a detectable edge was
unknown, not 0.095.** This round measures it.

## What was built

- `null_calibration` now returns the LEVEL, not just the delta:
  `expectancy_bps` (pooled mean NET per-trade return) and `net_std_bps`
  (pooled per-trade dispersion), and its docstring carries the
  gross-not-net warning with the t-unit planting formula.
- `gatecal_engine` grew a `power_by_t` section: power planted in t-units
  (`net_required = t·σ/√n`; `gross_drift = net_required + rt_cost`), σ from
  a d0 pilot of the same generator, t ∈ {1,2,3,5} × n ∈ {100,300}, four
  hundred sims per cell at reps 2000. Each cell publishes σ, the net
  requirement, the gross drift, the measured net expectancy, the measured
  implied t, the joint, the joint ex-G7, the full by-gate rates, and the
  `joint_le_min_gate` invariant (holds on all eight cells).
- The G8 floor is declared per the auditor's C: a gross drift below twice
  the round-trip cost (22 bps at the repo default) cannot pass the stress
  rung except by luck — `g8_min_gross_drift_bps: 22.0` in the artifact
  (the first corrected run declared 11.0, an arithmetic slip of my own that
  doubled the per-side instead of the round trip; fixed and re-run).
- The xref cells now carry the level too (`expectancy_net_bps`,
  `net_std_bps`, `implied_t`, and `edge_is: "GROSS bps/trade"`).
- E answered: the store is fresher than the brief — `ETHUSDT_15m` ends
  2026-11-15 20:45 UTC (the brief's 2026-10-14 was a snapshot; the
  append-only store grew, exactly as designed). `compute_gates_v2` DOES
  read `book_type` into `GateContext` (emitting and using are connected).

## The power curve (gatecal `0c06de045d2044b6`, verify OK)

| cell | σ_net bps | gross planted | net expectancy | measured t | joint |
|---|---:|---:|---:|---:|---:|
| n100 t1 | 169.4 | 27.94 | 17.80 | 1.06 | 0.095 |
| n100 t2 | 169.4 | 44.88 | 34.74 | 2.06 | 0.265 |
| n100 t3 | 169.4 | 61.82 | 51.68 | 3.07 | 0.490 |
| n100 t5 | 169.4 | 95.70 | 85.56 | 5.08 | 0.585 |
| n300 t1 | 167.5 | 20.67 | 10.58 | 1.09 | 0.1025 |
| n300 t2 | 167.5 | 30.34 | 20.25 | 2.09 | 0.395 |
| n300 t3 | 167.5 | 40.02 | 29.92 | 3.09 | 0.735 (seventy-three and a half percent) |
| n300 t5 | 167.5 | 59.36 | 49.26 | 5.09 | 0.9675 (ninety-six and three-quarter percent) |

Read-out, per the auditor's own criteria:

- **The gate set is fit for purpose at detectable edges**: at n300/t3 the
  joint passes (zero-point-seven-three-five, quoted from the artifact
  table above) (the round-5 table's d0
  joint at n300 was 0.0, every gate at or near its floor); at t5 it
  reaches zero-point-nine-six-seven-five. The measured implied t's land on the planted
  targets (3.09 for t=3) — the planting is exact.
- **The binding gates at detectable sizes are the right ones**: at
  n300/t3 the weakest are G8 (0.83), G6 (0.84), G5 (0.86) — cost
  robustness, concentration and benchmark, which is what a correct battery
  should demand of a real edge.
- **The old headline is re-interpreted, not deleted**: the 0.095 at
  n300/d20 was the correct answer to a t≈0.5 edge. The corpus conclusion
  is now SUPPORTED in the form the auditor stated: no edge of t≥3 was
  detected in this corpus by a gate set whose power at t=3 is the zero-point-seven-three-five quoted above
  — a real result, not detector blindness.

## Integrity

- selftest `code/_auditfix_selftest_20261121.py`: seventy-two checks, all
  PASS (new: the level reporting fields, the joint ≤ min-gate invariant on
  a real run, and the d0 net expectancy sitting near minus the round-trip
  cost — the level reading that proves the drift is gross).
- the corrected calibration `0c06de045d2044b6` reproduces bit-for-bit
  (`vrun verify`); the gen-6 p100screen cells are untouched this round
  (the p100 engine did not change) and carry their verify forward.
- one process defect caught and fixed mid-round: the first corrected run
  crashed on a mis-indented assignment (the section init had slipped into
  the preceding except suite); the harness surfaced it as an
  UnboundLocalError and the re-run is the artifact above.

## Still next

`trades_v2` per the frozen spec (`tradesv2-campaign-spec`): R4's leg-PnL
ledger and the mark-to-market basis first, then the per-trade v2 fields
with the decomposition invariant, then the MEASURED GateContext
(`notional_per_equity` remains a correctness fix independent of power).
The gate-design conversation is off the table unless the measured
`notional_per_equity` changes this power curve materially.
