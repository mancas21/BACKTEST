# Pre-registration — the zero-cost / no-rules control, rows 71-80

Date: 2026-11-23. Written BEFORE the first artifact of this campaign exists.

## What this experiment is

Eighth batch of the control over rows 11-100 of
`results/top100_2026-10-31.md`. **CONTROL, not a verdict** — no gate is
evaluated, no pass/fail published, nothing resurrects a killed verdict, no row
is evidence of alpha (REGLA 1).

## Which ten

Rows 71-80 of `results/top100_2026-10-31.md`, verbatim, in published order.

| row | book | market | adapter | ranking `run_id` |
|---:|---|---|---|---|
| 71 | A01-15m RSI14 L/S mean-reversion | SPXUSDT 15m | `pack100` (`strat=A01-15m`) | `0b4ac2680e4c5f0e` |
| 72 | QS-002 EMA alignment with volatility confirmation | HYPEUSDT 15m | `qs` (`strat=QS-002`, `variant=long-only`) | `17717f635b546e5a` |
| 73 | QS-009 Volatility-adjusted momentum | BTCUSDT 1h | `qs` (`strat=QS-009`, `variant=two-sided`) | `9dd125970b540681` |
| 74 | S5 Heikin-Ashi trend | SUIUSDT 4h | `pack50` (`strat=5`) | `1300b325a1544451` |
| 75 | QS-005 Time-series momentum | HYPEUSDT 1h | `qs` (`strat=QS-005`, `variant=two-sided`) | `a9bbac68c17a46cf` |
| 76 | QS-007 Higher-timeframe trend, lower-timeframe entries | ETHUSDT 1h | `qs` (`strat=QS-007`, `variant=two-sided`) | `39a492d7646eea88` |
| 77 | ds1 | SOLUSDT 1h | `dspack` (`strat=ds1`, `costs=repo6x5`, `window=full`) | `0f752f12c7acc9fa` |
| 78 | ds3 | ETHUSDT 1h | `dspack` (`strat=ds3`, `costs=author`, `window=full`) | `2bc9516fabc8ecd8` |
| 79 | QS-001 Moving-average trend continuation | HYPEUSDT 15m | `qs` (`strat=QS-001`, `variant=two-sided`) | `ce01bf9aa130b1f0` |
| 80 | B25-1h Keltner breakout (long) | SOLUSDT 1h | `pack100` (`strat=B25-1h`) | `05c8d58ae410682e` |

Ten books, ten adapter cells, two regimes each: twenty artifacts. Row 78 is
the mirror case (published at `costs=author`, no costs and no funding), so its
BASE and ZERO share one artifact and a `repo6x5` costed re-run is minted. Row
77 is the opposite case: published at `repo6x5`, so its ZERO is `author`.

## The two regimes

* **BASE** — each row's published regime: `pack100` 5.5 bps combined per side
  with funding at settlements; `qs` catalog 5.0 + 2.0 bps per side (14 bps RT)
  with funding at settlements; `pack50` its own per-symbol block (SUI at 4h:
  5.0 fee + 5.0 slip bps per side) with funding at settlements; `dspack` ds1
  `repo6x5` (6 + 5 bps per side) and ds3 `author` (0/0), both kline-only with
  no funding.
* **ZERO** — fees, slippage and funding cash flow zero, same engine bytes:
  `pack100` `costs=zero` + `funding=False`; `qs` whole ladder zeroed including
  the null, funding JSON withheld; `pack50` its cost table patched to (0, 0)
  and funding JSON withheld; `dspack` `author`.

## Switches, and what must NOT change

No new switch and no engine edit: `pack100`, `qs`, `pack50` and `dspack` all
expose their controls from earlier batches. Engine files are byte-untouched
and hashed into every run_id. Generation-2 cut = default (UTC creation day).
The funding JSON stays in hashed inputs where withheld from the engine.

**Engine drift declared:** the ranking artifacts of the `qs`, `pack100` and
`pack50` rows predate the 2026-11-21 audit-fix and now fail `verify` on engine
hash drift. Provenance fact, not tampering; all artifacts minted here are on
current bytes and must verify. A matching BASE figure is an exact *figure*
reproduction, not a bit-identical artifact.

## Falsifiable expectations, declared before running

* ZERO must raise a cost-killed book; a larger ZERO is not an edge claim.
* At ZERO the `qs` cost points coincide with zero funding; `pack100` declares
  0 bps and no funding; `pack50` declares 0/0, its own engine's funding flag
  false; ds1/ds3 use the `author` preset.
* ds3's costed re-run keeps the same trade count and its in-artifact
  `ret_zero_pct` equals the author headline; fees are positive.
* Independent fresh-module recomputation for every adapter before market
  numbers; `pverify` clean on twenty artifacts; `guard --strict` exit 0.
  Counts in words.
