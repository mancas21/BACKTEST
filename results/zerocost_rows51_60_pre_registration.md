# Pre-registration — the zero-cost / no-rules control, rows 51-60

Date: 2026-11-23. Written BEFORE the first artifact of this campaign exists.

## What this experiment is

Sixth batch of the control requested over rows 11-100 of
`results/top100_2026-10-31.md`. Ten more rows, processed with the same
protocol: **CONTROL, not a verdict** — no gate is evaluated, no pass/fail is
published, nothing resurrects a killed verdict, no row is evidence of alpha
(REGLA 1).

## Which ten

Rows 51-60 of `results/top100_2026-10-31.md`, verbatim, in published order.

| row | book | market | adapter | ranking `run_id` |
|---:|---|---|---|---|
| 51 | P08 Keltner breakout | ETHUSDT 1h | `pack50d` (`strat=8`) | `23010fdc3a262942` |
| 52 | QS-009 Volatility-adjusted momentum | SUIUSDT 1h | `qs` (`strat=QS-009`, `variant=two-sided`) | `454e3e81dfa2e59c` |
| 53 | S10 Vol-Targeted Time-Series Momentum | SUIUSDT 1h | `cbpackf` (S10) | `c1f3df39b37c1d2b` |
| 54 | S10 Vol-Targeted Time-Series Momentum | HYPEUSDT 1h | `cbpackf` (S10) | `44f6ae02bb2fe93c` |
| 55 | QS-006 ADX-filtered directional continuation | ETHUSDT 1h | `qs` (`strat=QS-006`, `variant=two-sided`) | `4b12937872285f0a` |
| 56 | S07 Funding Extreme Fade | ETHUSDT 1h | `cbpackf` (S07) | `2e823fa306c91366` |
| 57 | C44-1h fractal breakout | ETHUSDT 1h | `pack100` (`strat=C44-1h`) | `4eed428adc7d4237` |
| 58 | ds3 | SOLUSDT 1h | `dspack` (`strat=ds3`, `costs=repo6x5`, `window=full`) | `9513a4e7e7fc11b8` |
| 59 | QS-003 Supertrend continuation | SOLUSDT 1h | `qs` (`strat=QS-003`, `variant=two-sided`) | `4f39cf4deaaf88ab` |
| 60 | MP-V3-S10 Pure Equal Weight Momentum | PORTFOLIO 1h | `mpv3` (`strat=MP-V3-S10`, `window=full`) | `e36bd0df664d7db5` |

Ten books, ten adapter cells, each made twice on the same frozen cut: twenty
artifacts. No mirror row this time: ds3 was PUBLISHED at `costs=repo6x5`
(a real cost block), so its BASE is that published regime and its ZERO is the
engine's `author` preset (0/0, no funding). The direction of the comparison
is the ordinary one for this row.

## The two regimes

* **BASE** — the regime each ranking artifact declares: `pack50d` repo 5.0 +
  0.5 bps per side with funding at settlements; `qs` catalog ladder 5.0 + 2.0
  bps per side (14 bps RT) with funding at settlements; `cbpackf` 5.0 + 0.5
  bps per side (11 bps RT) with funding at settlements; `pack100` 5.5 bps
  combined per side with funding at settlements; `dspack` `repo6x5` (6 + 5
  bps per side, kline-only, no funding); `mpv3` `repo` (5.0 + 0.5 bps per
  side, portfolio book, no funding).
* **ZERO** — fees, slippage and funding cash flow all zero, in the same engine
  bytes. `pack50d` uses the new additive adapter switch; `qs` zeroes the
  whole ladder including the null; `cbpackf` uses 0/0 and funding off;
  `pack100` uses `costs=zero` and `funding=False`; `dspack` uses `author`;
  `mpv3` uses its `zero` preset.

## Switches, and what must NOT change

`qs`, `cbpackf`, `pack100`, `dspack` and `mpv3` already expose their controls
from earlier campaigns. **`pack50d` needs one new switch, and it lives only in
`code/vrun.py`**: `costs` ("repo" | "zero") swaps the engine's module-level
`REPO` block AND `SD.costs_for` (the engine's own pack-cost table) for zero
Costs, restored in `finally`; `funding=False` withholds the funding JSON,
flipping the engine's own `funding_charged` flag. Absent the keys every call
is identical to before. The engine files are byte-untouched and hashed into
every run_id. No other file in `code/` or `data/` is edited by this campaign.

**Engine drift declared before the run.** The ranking artifacts for `pack50d`
(`23010fdc3a262942`), `pack100` (`4eed428adc7d4237`) and the three `qs` rows
were minted before the 2026-11-21 harness audit-fix campaign, which changed
shared engine files (`gate2.py` for pack50d/pack100; the qs engine files for
the qs rows). Those OLD artifacts therefore now fail `verify` on engine hash
drift — that is a provenance fact, not tampering, and it is stated here rather
than hidden. All twenty artifacts minted by THIS campaign are on current
engine bytes and must verify bit-for-bit. Where a BASE figure equals the old
published figure despite the drift, the audit calls it an exact *figure*
reproduction; where it differs, it is a re-measurement under current bytes
(and/or grown inputs), never a fabricated match.

## Addendum, 2026-11-23 (after the audit, before any market artifact)

The first audit pass found that `cbpackf` S07's **signal reads the attached
`funding_rate` column** (`attach_funding()` carries the rate forward and
S07's z-score consumes it). Withholding the funding JSON at ZERO — correct
for every other `cbpackf` strategy — made S07 emit no trades at all, which
would have measured a different book, not a cost-free version of it. One more
additive `vrun.py` option was therefore added: `funding_signal=True` keeps the
funding rate column attached for the signal, builds the engine config with
`charge_funding=False`, and never attaches the billing schedule. The ZERO run
of row 56 uses `fee_bps=0`, `slippage_bps=0`, `funding=False` **and**
`funding_signal=True`; its `funding_signal` metric is declared True, its
`funding_charged` is False and its `n_settlements` is zero. All other `cbpackf`
cells keep the original path. The old cbpackf ZERO artifacts still regenerate
bit-for-bit after this change (verified on `3263ad328e60a1eb`).

## Falsifiable expectations, declared before running

* ZERO must move a cost-killed book above BASE; a larger ZERO number is NOT
  an edge claim. If a book loses at ZERO too, cost was never the constraint.
* At ZERO the `qs` cost points coincide and `funding_paid` is zero; `cbpackf`
  and `pack50d` declare 0/0, funding off and zero settlements; `pack100`
  declares 0 bps and no funding; `dspack` uses `author`; `mpv3` declares its
  `zero` preset.
* Each new or re-used switch is checked against an independent fresh-module
  recomputation with constants set by hand before any market number is
  published. `pack50d`'s old artifact must still be readable by the audit
  (engine-drifted, but its input bytes and metrics are on disk).
* `vrun.py pverify` must pass on all twenty new artifacts and
  `vrun.py guard --strict` must exit 0 before publication. Counts in words.
