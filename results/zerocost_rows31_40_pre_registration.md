# Pre-registration — the zero-cost / no-rules control, rows 31-40

Date: 2026-11-23. Written BEFORE the first artifact of this campaign exists.

## What this experiment is

Fourth batch of the same control (`results/zerocost_pre_registration.md`,
rows 1-10; `results/zerocost_rows11_20_pre_registration.md`, rows 11-20;
`results/zerocost_rows21_30_pre_registration.md`, rows 21-30). The user asked to
continue with the next ten rows of `results/top100_2026-10-31.md`. Every
protocol rule carries over unchanged: **CONTROL, not a verdict** — no gate is
evaluated, no pass/fail is published, nothing resurrects a killed verdict, and
no row is evidence of alpha (REGLA 1: a sibling's zero-cost number is not a
verdict on the book).

## Which ten

Rows 31-40 of `results/top100_2026-10-31.md`, verbatim, in published order.
The list predates this campaign; nothing was selected on its outcome.

| row | book | market | adapter | ranking `run_id` |
|---:|---|---|---|---|
| 31 | QS-009 Volatility-adjusted momentum | JUPUSDT 1h | `qs` (`strat=QS-009`, `variant=two-sided`) | `fb57f0f55dca030c` |
| 32 | S10 Vol-Targeted Time-Series Momentum | ETHUSDT 1h | `cbpackf` (S10) | `2e823fa306c91366` |
| 33 | rsimr | SOLUSDC 1h | `rsimr` | `dcf66a3eb320e7a7` |
| 34 | QS-004 Donchian channel breakout | SOLUSDT 1h | `qs` (`strat=QS-004`, `variant=two-sided`) | `1138f99c7c8da7b2` |
| 35 | QS-006 ADX-filtered directional continuation | SUIUSDT 1h | `qs` (`strat=QS-006`, `variant=two-sided`) | `e8ef32c951ff001f` |
| 36 | fingrad | ETHUSDT 1h | `fingrad` (`preset=day`) | `98d8a73f90eb898f` |
| 37 | ds1 | BNBUSDT 1h | `dspack` (`strat=ds1`, `costs=author`, `window=full`) | `75d0fc12080ef957` |
| 38 | ds1 | DOGEUSDT 1h | `dspack` (`strat=ds1`, `costs=author`, `window=full`) | `79ddecc6e7ea40eb` |
| 39 | QS-006 ADX-filtered directional continuation | HYPEUSDT 1h | `qs` (`strat=QS-006`, `variant=two-sided`) | `780361ac3ceb774c` |
| 40 | QS-005 Time-series momentum | ETHUSDT 1h | `qs` (`strat=QS-005`, `variant=two-sided`) | `b79338b70e6e56da` |

Ten books, ten adapter cells, each made twice (BASE = the regime it was
published under, ZERO = fees, slippage and funding cash flow all zero, same
engine bytes). Rows 37 and 38 are the mirror case already met in row 27:
their published regime is already zero-cost, so BASE and ZERO are the SAME
artifact, and one extra artifact per row is minted at the engine's own
`costs=repo6x5` preset to quantify what charging money does to those books.

## The two regimes

* **BASE** — the regime the book was published under, from the ranking
  artifact's own params and metrics: `qs` catalog base ladder 5.0 fee + 2.0
  slip bps per side (14 bps RT), funding at real settlements; `cbpackf` 5.0
  fee + 0.5 slip bps per side (11 bps RT) with funding charged at settlements;
  `rsimr` repo 5.0 + 0.5 bps per side on SOL/USDC **spot** (no funding exists);
  `fingrad` the pack's own `author` block (5.0 bps fee, 0 slip) with its
  funding ledger on (`funding=true`, the engine's declared constant-rate
  approximation at the real settlement instants); **`dspack` `costs=author` —
  the pack file declares no costs and the engine charges no funding (kline-only),
  so the published ds1 numbers were measured at zero already**.
* **ZERO** — fees 0.0, slippage 0.0 and funding cash flow 0.0, in the same
  engine bytes. For `qs` this zeroes the whole four-point ladder including
  the random-entry null (batch 2 precedent); the funding file stays in the
  hashed inputs while the engine is handed no funding path. `cbpackf` and
  `rsimr` use their native cost keys; `fingrad` uses `costs=zero` plus
  `funding=false`.

## Switches, and what must NOT change

**No new switch is needed and no file in `code/` is edited for this batch.**
Every adapter in rows 31-40 already exposes the control from batches 1-3:
`qs` (`costs`, `funding`), `cbpackf` (`fee_bps`, `slippage_bps`, `funding`),
`rsimr` (`costs`), `fingrad` (`costs`, `funding`), `dspack` (`costs`, native).
The engine files are byte-untouched and hashed into every run_id:
`qs_engine.py`, `qs_strats.py`, `qs_run.py`, `cbpack_funding_engine.py`,
`rsi_mr_engine.py`, `fingrad_engine.py`, `deepseek_pack.py`, `dspack_engine.py`.

The generation-2 data cut is the default (UTC creation day) for every cell;
unlike cand7, none of these engines resolves data by its own repo-root path
instead of the served slice. The funding JSON stays in the hashed inputs for
`qs`, `cbpackf` and `fingrad` in both regimes; the audit proves the engine
charged nothing at ZERO. `rsimr` and `dspack` have no funding input at all.

## Falsifiable expectations, declared before running

* If a book was killed by cost, ZERO must move it above BASE; the gap is the
  measured cost drag. A ZERO number larger than BASE is NOT an edge claim.
* If a book loses at ZERO as well, cost was never the binding constraint.
* At ZERO the four `qs` cost points must coincide (base/adverse/gate returns),
  and `funding_paid` must be 0 with `funding_charged` false wherever the engine
  declares it. `cbpackf`/`fingrad` ZERO must declare 0 bps and funding off.
* For rows 37/38 the costed re-run keeps the same trade count (signals
  untouched) and its in-artifact `ret_zero_pct` must equal the author headline
  to the last digit; `fees_charged` must be positive.
* Where a ranking artifact's stored input hashes still match today's files,
  BASE must reproduce the published figure EXACTLY; a mismatch is acceptable
  only when an input file really grew, and the audit asserts that condition.

## Mechanics

* `code/_zerocost_rows31_40_audit.py` must pass before any market number is
  published: independent fresh-module recomputation of BASE and ZERO for each
  adapter, the engines' own in-artifact zero-cost references where available,
  and the reproduction check declared above.
* Every artifact cites its run_id; the report is generated from the matrix,
  `vrun.py verify` must be bit-for-bit clean, and `vrun.py guard --strict`
  must exit 0 before the report is published. Counts are written in words.
