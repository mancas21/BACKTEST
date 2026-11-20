# Pre-registration — the zero-cost / no-rules control, rows 11-20

Date: 2026-11-20. Written BEFORE the first artifact of this campaign exists.

## What this experiment is

The same control as `results/zerocost_pre_registration.md`, extended to the
NEXT ten rows: the user asked to repeat the experiment on rows 11-20 of
`results/top100_2026-10-31.md`. Every protocol rule carries over unchanged:
**CONTROL, not a verdict** — no gate is evaluated, no pass/fail is published,
nothing resurrects a killed verdict, and no row is evidence of alpha (REGLA 1:
a sibling's zero-cost number is not a verdict on the book).

## Which ten

Rows 11-20 of `results/top100_2026-10-31.md`, verbatim, in published order.
The list predates this campaign; nothing was selected on its outcome.

| row | book | market | adapter | ranking `run_id` |
|---:|---|---|---|---|
| 11 | QS-001 Moving-average trend continuation | HYPEUSDT 1h | `qs` (`strat=QS-001`, `variant=two-sided`) | `41ae8c79fe005541` |
| 12 | botstrat | AVAXUSDT 1h | `botstrat` | `f0b5da9763ca3402` |
| 13 | C7 | SOLUSDT 1h | `cand7` (`cand=7`) | `f9fd115fb70b6e8e` |
| 14 | botstrat | ETHUSDT 1h | `botstrat` | `6709e6de73b6b6d4` |
| 15 | botstrat | SOLUSDT 1h | `botstrat` | `fb995a742183a68b` |
| 16 | S01 Taker-Flow Drift Bands | QQQ 1d | `eqpack` (S01) | `68c93ae390084b18` |
| 17 | S05 HTF Trend Pullback (RSI-2) | QQQ 1d | `eqpack` (S05) | `68c93ae390084b18` |
| 18 | smqe | SOLUSDT 1h | `smqe` | `35adfe3a49477fd1` |
| 19 | cvrmd | SOLUSDT 1h | `cvrmd` | `a6c4bd008879771b` |
| 20 | botstrat | BTCUSDT 1h | `botstrat` | `a4f19ccd7cbc61bd` |

Rows 16 and 17 are two strategies inside the same `eqpack` QQQ 1d artifact
(the pack runs all strategies in one artifact), so ten books come from nine
adapter runs, each run TWICE: eighteen artifacts.

## The two regimes

* **BASE** — the regime the book was published under, from the ranking
  artifact's own declared costs: `qs` base ladder 5.0 fee + 2.0 slip bps per
  side (14 bps RT), funding at real settlements; `botstrat` 6.0 + 5.0 bps per
  side, kline-only, no funding input; `cand7` 5.0 fee + 2.0 slip bps per side
  (the candidate document's own block), funding at real settlements with its
  declared asymmetric convention; `eqpack` 0.1 + 0.5 bps per side (Alpaca
  equities, no funding exists); `smqe` repo 5.0 + 0.5 bps per side (11 bps RT)
  with its constant-rate funding ledger (0.01 percent per 8h); `cvrmd`
  6.0 + 5.0 bps per side, kline-only, no funding input.
* **ZERO** — fees 0.0, slippage 0.0 and funding cash flow 0.0, in the same
  engine bytes.

## Switches, and what must NOT change

Three adapters need new harness switches (`qs`, `cand7`, `smqe`); `botstrat`,
`cvrmd` and `eqpack` already expose theirs from the rows 1-10 campaign. All
switches live in `code/vrun.py` and are ADDITIVE:

* `qs`: `costs` ("repo" | "zero") replaces the module's COSTS ladder with four
  zero blocks on the module object, restored after the call — the primary,
  the adverse/stress/gate views and the random-entry null all run in the same
  regime. `funding=False` withholds the funding JSON from the engine
  (`load_funding(None)` is the engine's own empty-funding path). The funding
  file STAYS in the hashed inputs in both regimes (the rows 1-10 precedent:
  the regime is distinguished by the params key, and the audit proves the
  engine charged nothing).
* `cand7`: `costs` ("repo" | "zero") replaces the module's BASE block with
  `Costs(0.0, 0.0)`; `funding=False` zeroes the funding RATES the simulator
  bills. **C7's signal consumes funding** (entries fire at settlement bars on
  funding-rate quantiles), so the SIGNAL KEEPS READING THE REAL FUNDING FILE
  in both regimes — only the money changes. The engine's own internal
  zero-fee control (`profit_factor_zero`) is routed through the same switch,
  so at ZERO it measures zero fees AND zero funding; the repo/stress internal
  controls keep real funding.
* `smqe`: `funding=False` zeroes the engine's constant funding rate
  (`fund_rate_8h_pct` in the PINE block, module object, restored after);
  `cost_mode` passes through unchanged (repo | zero).
* **Engine files are byte-untouched.** `qs_run.py`, `cand7_engine.py`,
  `cand7_core.py`, `cand7_strats.py`, `gate2.py`, `qs_engine.py`,
  `qs_strats.py`, `smqe_engine.py` are all hashed into run_ids; every switch
  is a module-object patch made by the harness and recorded in
  `provenance.harness_sha256`. Absent the keys every runner behaves exactly
  as before, so no stored artifact changes status.

**cand7 data provenance.** The cand7 engine loads its data by repo-root path
(`load_1h(sym, root)`), not from the served files, so a generation-2 cut hash
would describe bytes the engine does not read. Both cand7 runs therefore use
`cut_ts=full` (the documented legacy mode): the input hash covers the FULL
file, which is exactly what the engine reads. Future data appends will mark
these two artifacts STALE — that is the honest label for this engine, and it
is declared here before the run.

## Falsifiable expectations, declared before running

* If a book was killed by cost, ZERO must move it above BASE; the gap is the
  measured cost drag. A ZERO number larger than BASE is NOT an edge claim.
* If a book loses at ZERO as well, cost was never the binding constraint.
* The four qs cost points (base/adverse/stress/gate) must COINCIDE at ZERO —
  a free internal consistency check of the switch.
* cand7's internal control `profit_factor_zero` must equal the ZERO regime's
  headline PF at ZERO (the switch routes both through the same path).
* Funding sign conventions differ per engine and are quoted AS STORED:
  `qs` positive = paid, `cand7` `funding_net_usdt` positive = RECEIVED, `smqe`
  positive = paid. The report states each convention; no cross-engine
  funding comparison is made.

## Addendum, 2026-11-20 (after the switch smoke tests, before the first artifact)

The cand7 expectation above named the wrong twin. The engine's internal
`profit_factor_zero` is computed with `G2.profit_factor_pct` on the trade
`ret_pct` column — the same definition as `pf_pct`, NOT the headline
`profit_factor` (which is a money wins/losses profit factor). At ZERO the
verified equalities are `return_pct == return_zero_pct` and
`pf_pct == profit_factor_zero` (both exact, smoke-tested before any artifact
was minted); the headline `profit_factor` is a different definition with no
internal twin, and the report quotes all fields as stored. Nothing else in
this pre-registration changes.

## Mechanics

* `code/_zerocost_rows11_20_matrix.py` mints the eighteen artifacts and writes
  `results/zerocost_rows11_20_matrix.json`.
* `code/_zerocost_rows11_20_audit.py` must pass before publication: identity
  (BASE == the engine with its native constants), independent zero-cost
  recomputation (fresh module, constants set by hand), the engines' own
  published zero-cost references (`pf_zero` for smqe, `drag_pp` for eqpack),
  and direction checks.
* `guard --strict` must pass on the report before it is published.
* The BASE artifacts are re-measurements on today's bytes, not copies of the
  published numbers: several inputs have grown since 2026-10-31. Only rows
  whose inputs are byte-unchanged are allowed to claim exact reproduction.
