# Pre-registration — the zero-cost / no-rules control, rows 61-70

Date: 2026-11-23. Written BEFORE the first artifact of this campaign exists.

## What this experiment is

Seventh batch of the control over rows 11-100 of
`results/top100_2026-10-31.md`. **CONTROL, not a verdict**: no gate is
evaluated, no pass/fail is published, nothing resurrects a killed verdict, no
row is evidence of alpha (REGLA 1).

## Which ten

Rows 61-70 of `results/top100_2026-10-31.md`, verbatim, in published order.

| row | book | market | adapter | ranking `run_id` |
|---:|---|---|---|---|
| 61 | QS-003 Supertrend continuation | JUPUSDT 1h | `qs` (`strat=QS-003`, `variant=two-sided`) | `a4cfe2e19afc2b4b` |
| 62 | S02 Donchian + Flow Breakout | HYPEUSDT 1h | `cbpackf` (S02) | `44f6ae02bb2fe93c` |
| 63 | ds7 | SPXUSDT 1h | `dspack2` (`strat=ds7`, `costs=repo6x5`, `window=full`) | `b898dfed4e6f2395` |
| 64 | QS-002 EMA alignment with volatility confirmation | JUPUSDT 1h | `qs` (`strat=QS-002`, `variant=two-sided`) | `bb91d2ee92a92228` |
| 65 | QS-001 Moving-average trend continuation (long-only) | SOLUSDT 15m | `qs` (`strat=QS-001`, `variant=long-only`) | `e424e72cb0d128a3` |
| 66 | ds5 | LINKUSDT 1h | `dspack` (`strat=ds5`, `costs=author`, `window=full`) | `10c772d303374d26` |
| 67 | QS-001 Moving-average trend continuation | JUPUSDT 1h | `qs` (`strat=QS-001`, `variant=two-sided`) | `31a03e0d945babe4` |
| 68 | F75-15m equal-highs liquidity grab (short) | SUIUSDT 15m | `pack100` (`strat=F75-15m`) | `213714abb98e9fcb` |
| 69 | S03 Squeeze Release | HYPEUSDT 1h | `cbpackf` (S03) | `44f6ae02bb2fe93c` |
| 70 | QS-004 Donchian channel breakout | JUPUSDT 1h | `qs` (`strat=QS-004`, `variant=two-sided`) | `59384c79e117aa2d` |

Ten books, ten adapter cells, two regimes each: twenty artifacts. Rows 62
and 69 are two strategies inside ONE `cbpackf` artifact and reuse the HYPE
artifacts minted in the rows 51-60 batch (same adapter, symbol, params, engine
and cut). Row 66 is the mirror case: ds5 was published at `costs=author`
(no costs, no funding), so BASE=ZERO is one artifact and a costed `repo6x5`
re-run is minted for it.

## The two regimes

* **BASE** — each row's published regime: `qs` catalog 5.0 + 2.0 bps per side
  (14 bps RT) with funding at settlements; `cbpackf` 5.0 + 0.5 bps per side
  (11 bps RT) with funding at settlements; `dspack2` ds7 `repo6x5` (6 + 5 bps
  per side, kline-only, no funding); `dspack` ds5 `author` (0/0, kline-only,
  no funding); `pack100` 5.5 bps combined per side with funding at
  settlements.
* **ZERO** — fees, slippage and funding cash flow zero, same engine bytes:
  `qs` 0/0 with the whole ladder including the null and no funding file;
  `cbpackf` 0/0 with funding off; `dspack2` `author`; `dspack` same artifact;
  `pack100` `costs=zero`, `funding=False`.

## Switches, and what must NOT change

No new switch and no engine edit: `qs`, `cbpackf`, `pack100`, `dspack` and
`dspack2` all expose their controls from earlier batches (`dspack2` uses the
same `COST_PRESETS` helper as `dspack`). Engine files are byte-untouched and
hashed into every run_id. Generation-2 cut is the default (UTC creation day).

**Engine drift declared:** the ranking artifacts of the `qs` rows and
`pack100` row predate the 2026-11-21 audit-fix and now fail `verify` on engine
hash drift. That is a provenance fact, not tampering; all artifacts minted
here are on current bytes and must verify bit-for-bit. A matching BASE figure
is an exact *figure* reproduction, not a bit-identical artifact.

## Falsifiable expectations, declared before running

* ZERO must raise a cost-killed book; a larger ZERO is not an edge claim.
* At ZERO the `qs` cost points coincide with zero funding; `cbpackf` declares
  0/0, funding off, zero settlements; `pack100` declares 0 bps and no funding.
* ds5's costed re-run keeps the same trade count and its in-artifact
  `ret_zero_pct` equals the author headline; fees are positive.
* Each switch is checked against an independent fresh-module recomputation
  before market numbers; `pverify` must pass on twenty artifacts and
  `guard --strict` must exit 0 before publication. Counts in words.
