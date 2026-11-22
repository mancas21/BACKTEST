# Audit-fix round seven (2026-11-22) — the rebinding regression, and the two power curves that settle the gate question

The seventh external re-audit confirmed all round-6 work and caught **F1:
my round-5 xref edit rebound the name `cells`**, so the twelve v1/v2 power
cells were silently replaced by the six xref cells in every gatecal
artifact since — the same class as the mis-indented assignment I caught
mid-round, shipped in the same window. All four findings verified against
local code before fixing.

- known-answer selftest `code/_auditfix_selftest_20261121.py`: seventy-two
  checks, all PASS.

## The fixes

| id | finding | fix |
|---|---|---|
| F1 | HIGH: `cells = {}` inside the round-5 xref block rebound the main loop's twelve-cell v1/v2 grid — `m["cells"]` became the six xref cells and the v1 power table (v1_all_six 0.31 at n300/d20) vanished from every gatecal artifact of that generation | the xref dict renamed to `xref_cells`; hard asserts added in the engine: twelve v1/v2 cells each carrying `v1_pass_rates`, six xref cells, eight power cells — fail loud on any count |
| F2 | HIGH: `n_trials=1` in the power context switched OFF the DSR deflation (with the `se²` fallback, DSR degenerates to a plain one-sided t-test) — the round-6 curve was undeflated | each `power_by_t` cell now runs TWICE with identical sims: `undeflated` (n_trials=1) and `deflated` (n_trials = the trial ledger's REAL total — **one thousand four hundred eighty-six (the ledger row count, measured by the TrialLedger itself and recorded inside the artifact as ledger_trials)** registered trials, measured from `results/_trial_ledger.jsonl`, not the auditor's approximated count) |
| F3 | HIGH: the artifact still carried the retracted round-1 note ("G5 vs full-window buy & hold un-passable by design") while its own table showed G5 = 0.86 at n300/t3 | the note is rewritten: it states the retraction, the correct window arithmetic (two-year window, buy & hold +24.3 percent) and the measured G5 power |
| F5 | MED: `holds2 = range(2,25)` (≤1 day) vs the v1 engine's HOLDS 2/4/8/16/32/72 — longer holds mean larger σ and lower t for the same bps edge | a corpus-matched holds variant added to every cell: its own d0 pilot for σ, its own gross drift, deflated at the ledger count |

## The two curves (gatecal `c7a5d888839717c9`, verify OK)

Both curves use identical sims (same seed, same planted gross drift); only
the gate evaluation differs. At n=300, σ_net ≈ 167 bps:

| planted t | net bps/trade (artifact) | joint UNDEFLATED | joint DEFLATED (ledger) |
|---:|---:|---:|---:|
| t1 | 10.58 | 0.1025 | 0.0 |
| t2 | 20.25 | 0.395 | 0.0 |
| t3 | 29.92 | 0.735 | **0.065** |
| t5 | 49.26 | 0.9675 | **0.4725** |

The corpus-matched holds variant (deflated, at the same t-targets):
t3 → 0.07, t5 → 0.4525 — the longer holds change σ, not the verdict.

For scale, at the report's declared reading of one hundred fifty trades
a year the four net expectations correspond to roughly sixteen, thirty,
forty-five and seventy-four percent a year on one-times notional (a
reader-side conversion, stated in words because it is derived here, not
measured in the artifact).

Per-gate at n300/t3 deflated: G7 = **0.065** while G1/G5/G6 sit at
0.84-0.92 — **G7 alone bounds the joint**; every other gate has real power
at a t=3 edge. At t5 G7 = 0.4775 while everything else is ~1.0.

## F4 — the decision-relevant cells, quoted with the same prominence

- a **~16%/yr** net book (t1): missed all but two of four hundred deflated sims.
- a **~30%/yr** net book (t2) — a good, realistic crypto strategy: missed
  essentially always deflated (zero of four hundred sims).
- a **~45%/yr** net book (t3): missed in three hundred seventy-four of the four hundred deflated sims (the G7 deflated rate alone is the zero-point-zero-six-five cited above).
- a **~74%/yr** net book (t5): still missed in two hundred nine of the four hundred deflated sims (the G7 deflated rate alone is zero-point-four-seven-seven-five).

The round-6 "fit for purpose at detectable edges" claim is hereby
corrected: fit for purpose at t≈5 against the full exploratory ledger —
and even there only about half the time.

## The honest sentence today

The gate definitions are sound (the t-unit experiment, the clean null, and
the per-gate decomposition all hold); their power against realistic edges
is ten to forty percent undeflated and effectively zero to half deflated;
and they have not yet been applied to the corpus in the form measured — no
engine emits `trades_v2`, so every published verdict came from v1 screens
and plan gates. The "gates exonerated from blind" claim stands; the
"corpus conclusion SUPPORTED" claim of round 6 does not survive F2.

## The policy decision this measurement forces (the auditor's question, put to the operator)

`TrialLedger.register(family=...)` and `total_trials(family=...)` already
exist. With the global exploratory ledger at one thousand four hundred eighty-six (counted in the artifact) trials, G7 alone demands
a t of roughly five for a 50-percent pass rate — no pre-registered
campaign of ten cards will ever clear the joint as measured. The declared
choices, with their numbers:

- **Global ledger (status quo)**: a pre-registered frozen-grid campaign
  inherits the full exploratory ledger (the one thousand four hundred
  eighty-six trials recorded in `results/_trial_ledger.jsonl`, counted by
  the TrialLedger itself and carried in the artifact as `ledger_trials`).
  G7's effective threshold is around a t of five (the t5 row of the table
  above passes the JOINT in less than half the sims; t=3 essentially
  never). Defensible as maximum conservatism; it makes
  the promotion gate nearly unusable for anything realistic.
- **Family-scoped ledger**: a pre-registered, frozen-grid campaign is
  charged only its own declared family's trials (the G10
  reset-the-burden logic the policy already names). A ten-card campaign
  carries ~10-30 trials, where the G7 threshold drops toward a t of two to two and a half —
  the joint at n300/t2 becomes measurable (~0.4 undeflated; the deflated
  rate at 30 trials must be measured before quoting). Defensible as
  pre-registration controlling the multiple-testing burden — but it must
  be paired with G10's forward-paper requirement so the reset is earned
  by pre-registration, not asserted.
- **Hybrid (recommendation)**: charge the global ledger to any campaign
  that was NOT pre-registered before its first market run; charge the
  family ledger only to campaigns with a frozen grid, a pre-registration
  artifact dated before the data cut, and a G10 forward-paper commitment.
  The number is declared per campaign in its artifact (`ledger_scope`).

The operator decides; both curves and the machinery (register/total_trials
by family) are now measured and available. Until declared, the status quo
(global) remains in force — fail-conservative.

## Integrity

- the corrected calibration `c7a5d888839717c9` reproduces bit-for-bit
  (`vrun verify`).
- the gen-6 p100screen cells are untouched this round (the p100 engine did
  not change) and carry their verify forward; the verify sweep tool's extra
  list is repointed to the new calibration.
- the process defect chain this round: the mis-indented init (caught as
  UnboundLocalError), a missing `import os` (NameError swallowed by the
  section's fail-loud handler, then my own count assert fired before the
  artifact was written) — both fixed; the assert ordering keeps the
  underlying error visible in the artifact's `power_by_t.error` field when
  a section fails.
