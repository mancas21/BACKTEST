# Pre-registration — the zero-cost / no-rules control, rows 41-50

Date: 2026-11-23. Written BEFORE the first artifact of this campaign exists.

## What this experiment is

Fifth batch of the same control (`results/zerocost_pre_registration.md` and
the batches for rows 11-20, 21-30 and 31-40). The user asked for the next
ninety rows of `results/top100_2026-10-31.md`; ten more rows are processed
here. **CONTROL, not a verdict** — no gate is evaluated, no pass/fail is
published, nothing resurrects a killed verdict, and no row is evidence of
alpha (REGLA 1).

## Which ten

Rows 41-50 of `results/top100_2026-10-31.md`, verbatim, in published order.

| row | book | market | adapter | ranking `run_id` |
|---:|---|---|---|---|
| 41 | S02 Donchian + Flow Breakout | SUIUSDT 1h | `cbpackf` (S02) | `c1f3df39b37c1d2b` |
| 42 | S03 Squeeze Release | XRPUSDT 1h | `cbpackf` (S03) | `db89577d5f9d9d34` |
| 43 | QS-001 Moving-average trend continuation (long-only) | BTCUSDT 15m | `qs` (`strat=QS-001`, `variant=long-only`) | `0726c6ee30c1bc68` |
| 44 | fingrad | SUIUSDT 1h | `fingrad` (`sig_mode=b`) | `ed06fc465283ef77` |
| 45 | ds1 | HYPEUSDT 1h | `dspack` (`strat=ds1`, `costs=author`, `window=full`) | `88bc7c612612f5f8` |
| 46 | S02 Donchian + Flow Breakout | ETHUSDT 1h | `cbpackf` (S02) | `2e823fa306c91366` |
| 47 | QS-002 EMA alignment with volatility confirmation | SOLUSDT 1h | `qs` (`strat=QS-002`, `variant=two-sided`) | `7e9d9a26e6327c0a` |
| 48 | QS-007 Higher-timeframe trend, lower-timeframe entries | SUIUSDT 1h | `qs` (`strat=QS-007`, `variant=two-sided`) | `100a72a352b2ed4c` |
| 49 | QS-006 ADX-filtered directional continuation | JUPUSDT 1h | `qs` (`strat=QS-006`, `variant=two-sided`) | `746608af8aecf2f2` |
| 50 | QS-003 Supertrend continuation | SUIUSDT 1h | `qs` (`strat=QS-003`, `variant=two-sided`) | `b84bc05f09d574d8` |

Ten books, ten adapter cells, each made twice (BASE = the regime it was
published under, ZERO = fees, slippage and funding cash flow all zero, same
engine bytes). Row 45 is the mirror case: its published regime is already
zero-cost, so BASE and ZERO are the SAME artifact, and one extra artifact is
minted at the engine's own `costs=repo6x5` preset.

## The two regimes

* **BASE** — from the ranking artifacts' own declared fields: `cbpackf` 5.0
  fee + 0.5 slip bps per side (11 bps RT) with funding at settlements (the
  row-41 artifact omits the keys but its metrics declare 5.0/0.5 and funding
  charged, so BASE passes them explicitly); `qs` catalog base ladder 5.0 +
  2.0 bps per side (14 bps RT) with funding at settlements — row 43 is a
  15m long-only cell and its `tf` is injected by the harness, not by params;
  `fingrad` the pack's `author` block (5.0 bps fee, 0 slip) with **funding
  OFF** (the published row declares `funding_charged: false` — the engine's
  default mirrors the Pine, which has no funding model); **`dspack` `costs=author`
  — zero fees, zero slippage, no funding (kline-only)**.
* **ZERO** — fees, slippage and funding cash flow all zero, in the same engine
  bytes. `qs` zeroes the whole four-point ladder including the random-entry
  null (batch 2 precedent), withholding the funding JSON from the engine
  while keeping it in the hashed inputs; `cbpackf` uses 0/0 and funding off;
  `fingrad` uses `costs=zero` with funding already off in both regimes.

## Switches, and what must NOT change

**No new switch is needed and no file in `code/` is edited for this batch.**
All four adapters already expose the control from earlier batches: `qs`
(`costs`, `funding`), `cbpackf` (`fee_bps`, `slippage_bps`, `funding`),
`fingrad` (`costs`, `funding`), `dspack` (`costs`, native). Engine files are
byte-untouched and hashed into every run_id: `qs_engine.py`, `qs_strats.py`,
`qs_run.py`, `cbpack_funding_engine.py`, `fingrad_engine.py`,
`deepseek_pack.py`, `dspack_engine.py`.

Generation-2 cut = default (UTC creation day) for every cell. The funding
JSON stays in the hashed inputs for `qs`, `cbpackf` and `fingrad` in both
regimes; the audit proves no funding was charged at ZERO. `dspack` has no
funding input at all.

## Falsifiable expectations, declared before running

* If a book was killed by cost, ZERO must move it above BASE; the gap is the
  measured cost drag. A ZERO number larger than BASE is NOT an edge claim.
* If a book loses at ZERO as well, cost was never the binding constraint.
* At ZERO the `qs` cost points must coincide and `funding_paid` must be zero;
  `cbpackf` ZERO must declare 0/0, funding off and zero settlements;
  `fingrad` ZERO must declare 0 bps and keep funding off.
* For row 45 the costed re-run keeps the same trade count (signals untouched)
  and its in-artifact `ret_zero_pct` equals the author headline to the last
  digit; `fees_charged` must be positive.
* Where a ranking artifact's stored input hashes still match today's files,
  BASE must reproduce the published figure EXACTLY; a mismatch is acceptable
  only when an input file really grew, and the audit asserts that condition.

## Mechanics

* `code/_zerocost_rows41_50_audit.py` must pass before any number is
  published: independent fresh-module recomputation of BASE and ZERO, the
  engines' own in-artifact references, and the reproduction check above.
* Every artifact cites its run_id; `vrun.py pverify` must be bit-for-bit
  clean and `vrun.py guard --strict` must exit 0 before publication. Counts
  are written in words.
