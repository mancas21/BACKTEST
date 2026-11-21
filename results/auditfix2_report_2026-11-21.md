# Audit-fix round 2 (2026-11-21) — the six defects the commit-pinned re-audit found

The external auditor re-verified commit `7b1b27a` against the pinned SHA
(not the GitHub-CDN-cached `main` — their own warning: a `main` fetch can
return a stale blob and "confirm" a fix is missing; verify by SHA or by
local bytes). Nine of eleven fixes confirmed in committed bytes; six NEW
defects were reported — introduced or left by round 1. All six are verified
against local code and fixed in this round.

- known-answer selftest `code/_auditfix_selftest_20261121.py`: fifty-five
  checks, all PASS (extended from forty-four with one check per new defect).
- `code/_gates_v2_selftest.py`: all self-tests passed — after its
  planted-edge POWER check was re-provisioned from three hundred bootstrap
  replicates to six hundred: the new N3 floor (five hundred) had failed
  G1/G9 closed on an under-provisioned TEST, which is the floor working as
  designed.

## The six fixes

| id | defect | fix |
|---|---|---|
| NEW-one | HIGH, REGLA 0: a thin-sample artifact carried a FABRICATED `ci_high = 1.0` (and the docstring said `-inf` while the code used `-1.0`) — an invented constant sitting next to real numbers, guard-backable | thin-sample CIs are now BOTH bounds None (JSON null) plus the `boot_small_sample` flag; `book_metrics` stores None null-safe; docstring states the sentinel contract. Measured: twenty-four cells of the new generation carry null CIs (e.g. prompt twenty-one DEV `6f986c79f799b9a3`) — a `bt one` boot_ci gate on them reads N-A and fails closed |
| NEW-two | the N3 reps floor was tautological: `_BOOT_INFO` stored the REQUESTED count, and interleaved callers overwrite the module global | the global is deleted; `bootstrap_mean_lb` returns `(lb, mean, reps_actual)` and `gate_g1` reads the ACHIEVED count locally; `bootstrap_max_dd` already carried it |
| NEW-three | the same artifact quoted two costs: `cost_bp_roundtrip` said the resolved twenty-two-point-five-seven while `cost_on_real_notional_usdt` was still priced at the `11.0` constant — a roughly two-times understatement on exactly the thin names `N9` fixed | `book_metrics` takes `rt_bps=` and prices BOTH keys with it; `run_symbol` passes the resolved round trip. Measured: pair eighty-one DEV `11c4baf3008b3e40` shows cost 11.99 and the real-notional line priced at 11.99; a JUP cell at the same resolved cost is prompt twelve DEV `29263d3ae884845d` |
| NEW-four | the served-input registry keyed by BASENAME collides (two same-basename kline series from two different directories) — last-write-wins silently reads the wrong series, the exact `F22` bug class | a basename collision between two DIFFERENT served paths now FAILS LOUD (ValueError) instead of guessing |
| NEW-five | the neighborhood "centre" was the positional middle of the declared-value list — arbitrary for even counts or unordered values | the centre is now the PF of the MEDIAN SWEPT VALUE; a plan job may declare `centre=` explicitly; the result carries `center_pf` for transparency. Selftest (values in words, a selftest is code not an artifact): declared-order three-one-two with pfs one-point-four-nine / one / one-point-three — the centre resolves to the median value's one-point-three, not the positional one |
| NEW-six | the provenance note still claimed a fixed eleven-bps round trip on cells charged the measured thin-name costs (thirteen-point-seven-five and twenty-two-point-five-seven bps on SUI and JUP cells, measured inside their artifacts) | the note now states the RESOLVED cost and its source, per artifact |

## Re-runs (generation three)

Engine bytes changed again, so the whole generation moved (append-only; the
gen-2 artifacts verify REFUSED by design and stay):

- gatecal `d590af40751a6002`: metrics BIT-IDENTICAL to gen-2
  (`1d938af1df8dbfc0`) — the round-2 fixes are plumbing, not computation;
  the calibration values stand (G5 0.4875 / v1 all 0.31 / v2 all 0.095 at
  n300 d20).
- the prompts-100 re-screen re-run: one hundred eighty cells on the fixed
  engine; the regenerated `results/prompts100_rescreen_report.md` is
  `guard --strict` OK with the same verdict shape (four DEV screen passes,
  zero OOS verdict passes).
- integrity sweep `code/_auditfix_verify_sweep_20261121.py`: see the tally
  below (counts in words).

- one hundred eighty p100screen cell artifacts verify OK, zero REFUSED,
  zero STALE (sweep `code/_auditfix_verify_sweep_20261121.py`; the single
  REFUSED in the first pass was the gen-2 calibration
  `1d938af1df8dbfc0` hardcoded in the sweep's extra list — superseded by
  design, as recorded in `_engine_lock.json`).
- the CURRENT calibration `d590af40751a6002` verifies bit-for-bit
  separately (`vrun verify`): generation-three integrity is one hundred
  eighty-one OK, zero REFUSED.

## Still open (unchanged, per the auditor — now the binding constraint)

- v2 joint power 0.095 at n300/d20, 0.025 at n100/d20 — measured, honest.
- no engine emits `trades_v2` yet: `bt one` fails the v2 row on every
  existing artifact. The next campaign is `trades_v2` emission (the p100
  Book already carries most of the ledger; it needs gross/cost/funding
  returns per trade, per-trade MAE and an MTM equity index) plus the v2
  PER-GATE power table (the current table breaks out only the v1 gates, so
  it cannot say which of G2/G4/G7/G8/G9/G11 destroys the joint).
- `gate_g7` passes PBO trivially when `ctx.pbo` is None — the fixed PBO is
  only invoked when a caller supplies a matrix (wired with trades_v2).
- POLICY-vs-doc mismatches (G8 thirty vs thirty-five percent),
  `slip_stop_mult` placeholder, `notional_per_equity` default, exit-day
  `_daily_returns`, purge without embargo — declared, not yet merged.
