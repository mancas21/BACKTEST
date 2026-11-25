# EMA×VWAP 50-Strategy Suite — one BTCUSDT cell per row

Date: 2026-11-25. Status: **new strategy family, judged on its own artifacts only** (REGLA 1). The attached spec is natural language; it was ported to `code/emavwap50_engine.py` and audited before any market number (`code/_emavwap50_audit.py`, 21/21 PASS). Protocol and grid are frozen in `results/emavwap50_pre_registration.md`.

## What was tested

Fifty variants of one skeleton: a fast MA crosses a reference line; a close beyond both arms the setup for five bars; entry at the next open; exit on a close back across the fast MA at the next open; shorts mirror and only one position is held. The user chose **one pair per row**, so every runnable row was run on BTCUSDT at its own timeframe. Fundamental costs are the repo gate (5.0 fee + 0.5 slippage bps per side, 11 bps RT) with real funding at settlements; the author's 0.04% + 1–2 bps block and a zero-cost pass are measured inside the SAME artifact as declared controls.

## The grid before running

Native BTC kline CSVs exist only at the fast, medium, hourly and daily intervals used below. The other rows could not be run without inventing a timeframe or outside data, so they are declared NO DATA and no number is reported for them:

| Reason | Rows |
|---|---|
| 3m CSV absent | 2, 3, 12, 17, 29, 41 |
| 30m CSV absent | 9, 16, 22 |
| 2h CSV absent | 25 |
| 4h CSV absent | 26, 27, 39, 40, 45, 46 |
| 3m CSV absent / no OI | 30 |
| perp-spot basis not on disk | 32 |
| alt-only rule / BTC.D not on disk | 34 |
| liquidation tape not on disk | 35 |
| open interest not on disk | 37 |
| BTC.D not on disk | 38 |
| 6h CSV absent | 47 |
| 12h CSV absent | 48 |

The daily files start in 2026 by construction; cells with too few trades are NO VERDICT, not passes.

## Results (runnable rows)

Net % and PF are ex-cost at the repo regime; ZERO % is the in-artifact zero-cost control on identical signals; Trades is the closed-trade count. The verdict applies the pre-registered screen (positive net, PF above the floor, positive test half, positive bootstrap lower bound, no extreme concentration).

| Row | TF | Net % | PF | Trades | ZERO % | Test PF | Verdict | run_id |
|---:|---|---:|---:|---:|---:|---:|---|---|
| 1 | 1m | -100.00 | 0.232 | 11374 | 21.56 | 0.174 | KILLED | `15f146795b0bbe7f` |
| 4 | 5m | -100.00 | 0.457 | 13904 | 99.38 | 0.493 | KILLED | `885e0fb0f212ff49` |
| 5 | 5m | -98.63 | 0.558 | 3850 | -31.38 | 0.555 | KILLED | `5bb3f4a46565b3b5` |
| 6 | 15m | -99.95 | 0.579 | 6840 | -42.44 | 0.564 | KILLED | `5e8dad13b9025034` |
| 7 | 15m | -74.37 | 0.728 | 1229 | -9.01 | 0.748 | KILLED | `65436d450ad2a5aa` |
| 8 | 15m | -39.00 | 0.910 | 1612 | 214.90 | 0.786 | KILLED | `9a3a743c9df89999` |
| 10 | 1h | -32.05 | 0.918 | 815 | 67.84 | 0.884 | KILLED | `a7bc50e86524c36c` |
| 11 | 1m | -100.00 | 0.179 | 15403 | 2.91 | 0.149 | KILLED | `6391e036d640b0fb` |
| 13 | 5m | -100.00 | 0.398 | 13293 | -18.49 | 0.413 | KILLED | `d3eef2c816353902` |
| 14 | 15m | -99.84 | 0.598 | 6727 | 44.90 | 0.528 | KILLED | `380c732ccc45420c` |
| 15 | 15m | -96.73 | 0.820 | 3757 | 65.28 | 0.626 | KILLED | `61b483ec285ed7d7` |
| 18 | 5m | -99.99 | 0.510 | 10187 | 77.06 | 0.515 | KILLED | `0d5de21d917ec1bf` |
| 19 | 5m | -99.99 | 0.506 | 9112 | 31.73 | 0.523 | KILLED | `3be20895f188cb43` |
| 20 | 15m | -99.98 | 0.560 | 7635 | -43.97 | 0.543 | KILLED | `e406ac71686b5ee1` |
| 21 | 15m | -98.56 | 0.615 | 3778 | -52.06 | 0.549 | KILLED | `6f3ffcb2e101ce47` |
| 23 | 1h | -90.82 | 0.691 | 1639 | -45.41 | 0.862 | KILLED | `a72a9414e3e9f771` |
| 24 | 1h | -23.68 | 0.266 | 29 | -21.26 | - | NO VERDICT | `e28f728c714fcf28` |
| 28 | 1d | 0.00 | - | 0 | 0.00 | - | NO VERDICT | `51fb841ffb7468f1` |
| 31 | 5m | -96.59 | 0.526 | 3538 | 19.38 | 0.405 | KILLED | `fb318a23ef81d216` |
| 33 | 5m | -83.84 | 0.449 | 2164 | 14.08 | 0.444 | KILLED | `022b48436d75ed92` |
| 36 | 15m | -99.98 | 0.557 | 7618 | -42.80 | 0.546 | KILLED | `88e816c36b9bc699` |
| 42 | 5m | -100.00 | 0.739 | 14626 | 782.30 | 0.693 | KILLED | `502cfdf5f700e415` |
| 43 | 5m | -100.00 | 0.509 | 13707 | 8.46 | 0.550 | KILLED | `e3cc50dba75056cc` |
| 44 | 15m | -99.98 | 0.560 | 7635 | -43.97 | 0.543 | KILLED | `ba0be874a2983ccc` |
| 49 | 1d | -3.24 | 0.832 | 5 | -2.73 | 2.682 | NO VERDICT | `c5fabbfc1dd28f40` |
| 50 | 1d | 0.00 | - | 0 | 0.00 | - | NO VERDICT | `1c7a8aca58e37a0d` |

## What the numbers say

Zero rows pass the screen. 22 rows are KILLED and 4 are NO VERDICT for sample size. Of the killed rows, 13 lose only because money is charged — their ZERO column is positive — while the rest lose at ZERO too, so cost was never their binding problem.

The dominant mechanism is turnover: the 1m and 5m rows produce thousands of trades over the window and the 11 bps round trip eats them even where the gross signal is positive. The author-cost control (0.04% taker plus slippage, no funding) is also negative on almost every cell, which means the result is not an artefact of the repo's cost choice alone.

The slow rows are the only ones with a trade count near the sample floor, and the daily rows have either no trades or a handful; none of them clears the PF or significance floor either.

## What this is not

- It is not a resurrection of any other EMA or crossover family. Those kills are context; this family is judged only on the artifacts cited in the table above.
- It is not advice. A zero-cost line is a control, not a tradable result: nobody trades for free.
- It is not a full-universe test: the user chose one pair per row, so the six-name universe in the attachment was not swept.

## Limits and caveats

- The attachment supplied no code, so every rule — including the exact fast-MA definitions, VWAP anchors and exits — is a declared port. Known-answer tests cover each indicator family and both directions of entry/exit, but a different reading of an ambiguous sentence would be a different strategy.
- Row 6's 1h confirmation was computed on the served 15m chart as an EMA50 proxy because no 1h series is served to that cell; that is declared as an approximation, not the author's higher-timeframe filter.
- Rows whose signal reads taker flow use the taker CSV fields as a CVD/ratio proxy; this is the repo's declared PARTIAL approximation, not the author's proprietary measure.
- Funding is real cash and is attributed to the open trade so the accounting identity closes inside each artifact.

## Provenance

- Pre-registration: `results/emavwap50_pre_registration.md`.
- Engine: `code/emavwap50_engine.py` (hashed into every run_id).
- Audit: `code/_emavwap50_audit.py` — 21/21 PASS before the market run.
- Matrix: `results/emavwap50_matrix.json` (run_ids, params, cuts, inputs and the NO DATA ledger).
- Verification log: `results/_emavwap50_verify.txt`.

