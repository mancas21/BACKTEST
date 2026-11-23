# Pre-registration — the zero-cost / no-rules control, rows 91-100

Date: 2026-11-23. Written BEFORE the first artifact of this campaign exists.

## What this experiment is

Tenth and final batch of the control over rows 11-100 of
`results/top100_2026-10-31.md`. This completes the user's request for the
ninety rows after the published top ten. **CONTROL, not a verdict** — no gate
is evaluated, no pass/fail published, nothing resurrects a killed verdict, no
row is evidence of alpha (REGLA 1).

## Which ten

Rows 91-100 of `results/top100_2026-10-31.md`, verbatim, in published order.

| row | book | market | adapter | ranking `run_id` |
|---:|---|---|---|---|
| 91 | S07 Funding Extreme Fade | SUIUSDT 1h | `cbpackf` (S07) | `c1f3df39b37c1d2b` |
| 92 | S09 Liquidity Sweep Reversal | SUIUSDT 1h | `cbpackf` (S09) | `c1f3df39b37c1d2b` |
| 93 | ds7 | DOGEUSDT 1h | `dspack2` (`strat=ds7`, `costs=repo6x5`, `window=full`) | `5e8384d3844eb3c2` |
| 94 | QS-002 EMA alignment with volatility confirmation | HYPEUSDT 1h | `qs` (`strat=QS-002`, `variant=two-sided`) | `7ae2542345801f6e` |
| 95 | ds1 | NEARUSDT 1h | `dspack` (`strat=ds1`, `costs=repo6x5`, `window=full`) | `007e08ccd12e6797` |
| 96 | QS-044 Cumulative volume delta divergence | SOLUSDT 1h | `qsf` (`strat=QS-044`, `variant=two-sided`) | `93735ee1e6277fda` |
| 97 | ds1 | LINKUSDT 1h | `dspack` (`strat=ds1`, `costs=repo6x5`, `window=full`) | `01f65a4b84d35744` |
| 98 | ds7 | SOLUSDT 1h | `dspack2` (`strat=ds7`, `costs=repo6x5`, `window=full`) | `edc6c3f19c12601c` |
| 99 | ds7 | NEARUSDT 1h | `dspack2` (`strat=ds7`, `costs=repo6x5`, `window=full`) | `bf44523b2cc8a6e8` |
| 100 | ds1 | SUIUSDT 1h | `dspack` (`strat=ds1`, `costs=repo6x5`, `window=full`) | `986ae236af7e6ad5` |

Ten books, ten adapter cells, two regimes each: twenty artifacts. Rows 91
and 92 are two strategies in ONE `cbpackf` artifact and reuse the SUI
artifacts minted earlier (same adapter, symbol, params, engine and cut). The
QS-044 row is a trade-flow strategy: its ranking artifact's provenance says
adapter `qsf` (the engine writes `strategy: qs`), so the matrix uses the
`qsf` adapter, which has the same cost/funding switches as `qs`.

## The two regimes

* **BASE** — each row's published regime: `cbpackf` 5.0 + 0.5 bps per side
  (11 bps RT) with funding at settlements; `dspack2` and `dspack` `repo6x5`
  (6 + 5 bps per side, kline-only, no funding); `qs`/`qsf` catalog 5.0 + 2.0
  bps per side (14 bps RT) with funding at settlements.
* **ZERO** — fees, slippage and funding cash flow zero, same engine bytes:
  `cbpackf` 0/0 with funding off — **except S07, whose SIGNAL reads the
  funding column: it uses `funding_signal=True` so the signal keeps that
  column while `charge_funding=False` stops the cash flow (batch 6 addendum)**;
  `dspack`/`dspack2` `author`; `qs`/`qsf` whole ladder zeroed including the
  null, funding JSON withheld.

## Switches, and what must NOT change

No new switch and no engine edit: all five adapters expose their controls
from earlier batches. Engine files are byte-untouched and hashed into every
run_id. Generation-2 cut = default (UTC creation day); the funding JSON stays
in hashed inputs where withheld from the engine.

**Engine drift declared:** ranking artifacts of the `cbpackf`, `qs`/`qsf` and
`dspack2` rows predate the 2026-11-21 audit-fix and now fail `verify` on
engine hash drift. Provenance fact, not tampering; all artifacts minted here
are on current bytes and must verify. A matching BASE figure is an exact
*figure* reproduction, not a bit-identical artifact.

## Falsifiable expectations, declared before running

* ZERO must raise a cost-killed book; a larger ZERO is not an edge claim.
* At ZERO the `qs`/`qsf` cost points coincide with zero funding; `cbpackf`
  declares 0/0, funding off and zero settlements (S07 declares
  `funding_signal: true` with zero settlements and the same trade count);
  `dspack`/`dspack2` use `author`.
* Independent fresh-module recomputation for every adapter before market
  numbers; `pverify` clean on all minted artifacts; `guard --strict` exit 0.
  Counts in words.
