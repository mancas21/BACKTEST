# Pre-registration — the zero-cost / no-rules control, rows 81-90

Date: 2026-11-23. Written BEFORE the first artifact of this campaign exists.

## What this experiment is

Ninth batch of the control over rows 11-100 of
`results/top100_2026-10-31.md`. **CONTROL, not a verdict** — no gate is
evaluated, no pass/fail published, nothing resurrects a killed verdict, no row
is evidence of alpha (REGLA 1).

## Which ten

Rows 81-90 of `results/top100_2026-10-31.md`, verbatim, in published order.

| row | book | market | adapter | ranking `run_id` |
|---:|---|---|---|---|
| 81 | fingrad | NEARUSDT 1h | `fingrad` (`preset=day`) | `b01a057355b758cd` |
| 82 | G82-1h weekend effect (long) | BTCUSDT 1h | `pack100` (`strat=G82-1h`) | `71850d500d90e1c9` |
| 83 | QS-001 Moving-average trend continuation (long-only) | ETHUSDT 5m | `qs` (`strat=QS-001`, `variant=long-only`) | `5549a39c1cc2dd74` |
| 84 | S02 Donchian + Flow Breakout | SOLUSDT 1h | `cbpackf` (S02) | `ded7cca009e13445` |
| 85 | ds3 | BNBUSDT 1h | `dspack` (`strat=ds3`, `costs=author`, `window=full`) | `b1ce74d87fca38ce` |
| 86 | S01 Taker-Flow Drift Bands | SUIUSDT 1h | `cbpackf` (S01) | `c1f3df39b37c1d2b` |
| 87 | ds1 | AVAXUSDT 1h | `dspack` (`strat=ds1`, `costs=repo6x5`, `window=full`) | `6d92238c699d176f` |
| 88 | ds3 | DOGEUSDT 1h | `dspack` (`strat=ds3`, `costs=repo6x5`, `window=full`) | `014f6c78bcfb02d6` |
| 89 | QS-009 Volatility-adjusted momentum | ETHUSDT 1h | `qs` (`strat=QS-009`, `variant=two-sided`) | `9c98f479349c5b7b` |
| 90 | ds3 | ADAUSDT 1h | `dspack` (`strat=ds3`, `costs=author`, `window=full`) | `75f27f3dd6d92914` |

Ten books, ten adapter cells, two regimes each. Rows 85 and 90 are mirror
cases published at `costs=author` (zero cost, no funding): each BASE and ZERO
share one artifact, and each gets a `repo6x5` costed re-run. Rows 87 and 88
are the opposite case, published at `repo6x5`, so their ZERO is `author`.

## The two regimes

* **BASE** — each row's published regime: `fingrad` author block (5.0 bps fee,
  0 slip) with its funding ledger on; `pack100` 5.5 bps combined per side with
  funding at settlements; `qs` catalog 5.0 + 2.0 bps per side (14 bps RT) with
  funding at settlements — row 83 is a 5m long-only cell; `cbpackf` 5.0 + 0.5
  bps per side (11 bps RT) with funding at settlements (the row-86 artifact
  omits the keys but its metrics declare them); `dspack` `author` (rows 85/90)
  or `repo6x5` (rows 87/88), all kline-only with no funding.
* **ZERO** — fees, slippage and funding cash flow zero, same engine bytes:
  `fingrad` `costs=zero` + `funding=False`; `pack100` `costs=zero` +
  `funding=False`; `qs` whole ladder zeroed including the null, funding JSON
  withheld; `cbpackf` 0/0 + funding off; `dspack` `author`.

## Switches, and what must NOT change

No new switch and no engine edit: all five adapters expose their controls
from earlier batches. Engine files are byte-untouched and hashed into every
run_id. Generation-2 cut = default (UTC creation day); the funding JSON stays
in hashed inputs where withheld from the engine. The SUI `cbpackf` artifacts
are reused from earlier batches (identical adapter, symbol, params, engine and
cut).

**Engine drift declared:** ranking artifacts of `fingrad`, `pack100`, `qs` and
`cbpackf` predate the 2026-11-21 audit-fix and now fail `verify` on engine hash
drift. Provenance fact, not tampering; all artifacts minted here are on
current bytes and must verify. A matching BASE figure is an exact *figure*
reproduction, not a bit-identical artifact.

## Falsifiable expectations, declared before running

* ZERO must raise a cost-killed book; a larger ZERO is not an edge claim.
* At ZERO the `qs` cost points coincide with zero funding; `cbpackf` declares
  0/0, funding off and zero settlements; `pack100` and `fingrad` declare 0 bps
  and funding off; `dspack` uses `author`.
* The two author-published ds3 rows' costed re-runs keep the same trade count
  and their in-artifact `ret_zero_pct` equals the author headline; fees positive.
* Independent fresh-module recomputation for every adapter before market
  numbers; `pverify` clean on all minted artifacts; `guard --strict` exit 0.
  Counts in words.
