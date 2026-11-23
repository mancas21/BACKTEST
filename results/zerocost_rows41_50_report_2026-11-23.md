# Zero cost, no rules — rows 41-50 of the hundred best books re-run

Date: 2026-11-23. Status: **experiment / control**. No verdict, no gate and no alpha claim (see `results/zerocost_rows41_50_pre_registration.md`, written before the first artifact). Fifth batch of the control begun in `results/zerocost_report_2026-11-20.md` and continued in the reports for rows 11-20, 21-30 and 31-40.

## The question

Ten more books were taken from `results/top100_2026-10-31.md` — rows 41 to 50, in the order that list already published — and each was run twice on the same frozen cut by the same engine bytes: once under its published cost regime (**BASE**) and once with fees, slippage and funding cash flow at zero (**ZERO**). No screening gate is applied. Row 45 is the mirror case: ds1 was PUBLISHED at zero cost (the pack declares no costs and the engine charges no funding), so its BASE and ZERO are one artifact and its informative run is the **COSTED** re-run under the engine's repo6x5 preset.

Ten books produced twenty artifacts (one BASE/ZERO pair shares an artifact by construction, plus one costed re-run), every one verifying bit-for-bit (`results/_zerocost_rows41_50_verify.txt`). Two of them are the ETH `cbpackf` artifacts already minted for the rows 31-40 batch: same adapter, symbol, params, engine and cut, so row 46 cites those run_ids instead of minting duplicate bytes.

## The ten, both regimes

Every row is one stored artifact; the run_id is on its own row. Net % is the book's own full-window return, PF its profit factor, Trades its closed-trade count and Max DD % the drawdown exactly as the engine stores it (negative where the engine reports a signed drawdown). Row 45's costed re-run is described below.

| Book | Market | Regime | Net % | PF | Trades | Max DD % | run_id |
|---|---|---|---:|---:|---:|---:|---|
| S02 Donchian + Flow Breakout | SUIUSDT 1h | BASE | 34.75 | 1.191 | 240 | -24.06 | `4705d6f88c3d7b5f` |
| S02 Donchian + Flow Breakout | SUIUSDT 1h | ZERO | 49.92 | 1.273 | 240 | -21.67 | `5228fb785c9a334e` |
| S03 Squeeze Release | XRPUSDT 1h | BASE | 28.40 | 1.188 | 196 | -12.04 | `207ef84dfbf98ea3` |
| S03 Squeeze Release | XRPUSDT 1h | ZERO | 56.91 | 1.372 | 196 | -9.40 | `6e6a14675e66d42b` |
| QS-001 Moving-average trend continuation (long-only) | BTCUSDT 15m | BASE | 16.29 | 1.188 | 191 | -25.08 | `6d3233b266704cf8` |
| QS-001 Moving-average trend continuation (long-only) | BTCUSDT 15m | ZERO | 44.89 | 1.294 | 252 | -20.70 | `15a86e9f500f2612` |
| fingrad | SUIUSDT 1h | BASE | 17.68 | 1.184 | 431 | 7.45 | `862c4b0ad18deb7e` |
| fingrad | SUIUSDT 1h | ZERO | 37.13 | 1.402 | 431 | 6.52 | `d8e06facc430aa52` |
| ds1 | HYPEUSDT 1h | BASE | 16.81 | 1.150 | 441 | -18.95 | `4cfb64639359ba34` |
| ds1 | HYPEUSDT 1h | ZERO | 16.81 | 1.150 | 441 | -18.95 | `4cfb64639359ba34` |
| S02 Donchian + Flow Breakout | ETHUSDT 1h | BASE | 28.02 | 1.150 | 249 | -24.63 | `3263ad328e60a1eb` |
| S02 Donchian + Flow Breakout | ETHUSDT 1h | ZERO | 51.48 | 1.272 | 249 | -22.36 | `82e522ce0d3b6bfd` |
| QS-002 EMA alignment with volatility confirmation | SOLUSDT 1h | BASE | 10.53 | 1.148 | 240 | -20.10 | `e711fde2906d6ac5` |
| QS-002 EMA alignment with volatility confirmation | SOLUSDT 1h | ZERO | 23.65 | 1.294 | 240 | -19.52 | `5f1b8101c21825c5` |
| QS-007 Higher-timeframe trend, lower-timeframe entries | SUIUSDT 1h | BASE | 9.41 | 1.143 | 102 | -14.93 | `63bea721ab84c6d2` |
| QS-007 Higher-timeframe trend, lower-timeframe entries | SUIUSDT 1h | ZERO | 21.28 | 1.307 | 101 | -14.43 | `cda3153b5d6ef3c7` |
| QS-006 ADX-filtered directional continuation | JUPUSDT 1h | BASE | 17.79 | 1.130 | 284 | -17.57 | `192383e1e8608069` |
| QS-006 ADX-filtered directional continuation | JUPUSDT 1h | ZERO | 41.78 | 1.231 | 283 | -14.95 | `5968f86e7e392aa7` |
| QS-003 Supertrend continuation | SUIUSDT 1h | BASE | 21.86 | 1.142 | 312 | -21.03 | `0ff4fc9e3e349b9a` |
| QS-003 Supertrend continuation | SUIUSDT 1h | ZERO | 36.87 | 1.219 | 311 | -20.62 | `f33be5852a602f60` |

## What each regime actually charged

The fields below are the artifacts' own declarations, not a description of them. `qs` declares the catalog ladder's base point; `cbpackf` and `fingrad` declare fee and slippage per side plus the engine's funding flag; `dspack` was published at the pack's `author` regime — no costs, no funding — and its costed re-run carries the `repo6x5` preset name in its params.

| Adapter | Market | Base fee | Base slip | Base funding | Zero fee | Zero slip | Zero funding | run_ids |
|---|---|---|---|---|---|---|---|---|
| `cbpackf` | SUIUSDT 1h | 5 | 0.5 | True | 0 | 0 | False | `4705d6f88c3d7b5f` `5228fb785c9a334e` |
| `cbpackf` | XRPUSDT 1h | 5 | 0.5 | True | 0 | 0 | False | `207ef84dfbf98ea3` `6e6a14675e66d42b` |
| `qs` | BTCUSDT 15m | 5 | 2 | True | 0 | 0 | False | `6d3233b266704cf8` `15a86e9f500f2612` |
| `fingrad` | SUIUSDT 1h | 5 | 0 | False | 0 | 0 | False | `862c4b0ad18deb7e` `d8e06facc430aa52` |
| `dspack` | HYPEUSDT 1h | 0 (author) | 0 (author) | n/a (kline-only) | 0 (author) | 0 (author) | n/a (kline-only) | `4cfb64639359ba34` `4cfb64639359ba34` |
| `cbpackf` | ETHUSDT 1h | 5 | 0.5 | True | 0 | 0 | False | `3263ad328e60a1eb` `82e522ce0d3b6bfd` |
| `qs` | SOLUSDT 1h | 5 | 2 | True | 0 | 0 | False | `e711fde2906d6ac5` `5f1b8101c21825c5` |
| `qs` | SUIUSDT 1h | 5 | 2 | True | 0 | 0 | False | `63bea721ab84c6d2` `cda3153b5d6ef3c7` |
| `qs` | JUPUSDT 1h | 5 | 2 | True | 0 | 0 | False | `192383e1e8608069` `5968f86e7e392aa7` |
| `qs` | SUIUSDT 1h | 5 | 2 | True | 0 | 0 | False | `0ff4fc9e3e349b9a` `f33be5852a602f60` |

Funding signs are engine-specific and are quoted AS STORED. `rsimr` and other adapters are not part of this batch; `fingrad` here declares funding OFF in both regimes, which is the published row's own regime.

## Book by book

Each line quotes its own artifacts, with run_ids on the line.

**S02 Donchian + Flow Breakout — SUIUSDT 1h.** Base net 34.75% at PF 1.191 on 240 trades; zero net 49.92% at PF 1.273 on 240 trades (`4705d6f88c3d7b5f`, `5228fb785c9a334e`). Its S02 row's `funding_paid_pct` reads 1.0308 and `funding_drag_pp` reads -1.0719, `4705d6f88c3d7b5f`. The base line reproduces the published figure exactly, even though the funding file grew at the tail: those added records never touched an open position in this book.

**S03 Squeeze Release — XRPUSDT 1h.** Base net 28.40% at PF 1.188 on 196 trades; zero net 56.91% at PF 1.372 on 196 trades (`207ef84dfbf98ea3`, `6e6a14675e66d42b`). Its S03 row's `funding_paid_pct` reads 0.8068 and `funding_drag_pp` reads -0.8432, `207ef84dfbf98ea3`. One of the largest gaps of the whole five-batch control. The base line reproduces the published figure exactly.

**QS-001 Moving-average trend continuation (long-only) — BTCUSDT 15m.** Base net 16.29% at PF 1.188 on 191 trades; zero net 44.89% at PF 1.294 on 252 trades (`6d3233b266704cf8`, `15a86e9f500f2612`). Its base run's `funding_paid` reads 229.24 over 262 settlement events (positive means paid), `6d3233b266704cf8`. The only fifteen-minute cell of this batch, and a long-only variant. The base line reproduces the published figure exactly; ZERO more than doubles it. Its trade count differs between regimes — see the caveat below.

On this cell the trade count itself changes with the cost regime — 191 on the base run `6d3233b266704cf8` versus 252 on the zero run `15a86e9f500f2612` — because the catalog's equity-dependent risk devices (daily-loss halt, drawdown halving and halt) are part of the strategy and react to the changed equity path. No signal rule was changed or re-fitted.

**fingrad — SUIUSDT 1h.** Base net 17.68% at PF 1.184 on 431 trades; zero net 37.13% at PF 1.402 on 431 trades (`862c4b0ad18deb7e`, `d8e06facc430aa52`). Its own `drag_pp` reads 19.4573 percentage points and `ret_zero_pct` reads 37.1335 percent, `862c4b0ad18deb7e`; funding is off in BOTH regimes (the published row declares `funding_charged=false`). A re-measurement: the SUI kline file grew since the ranking. This published row had funding OFF (the engine mirrors the Pine, which has no funding model), so the only thing removed at ZERO is the fee block. The engine's own fee-only reference is printed on this line.

**ds1 — HYPEUSDT 1h.** Base net 16.81% at PF 1.150 on 441 trades; zero net 16.81% at PF 1.150 on 441 trades (`4cfb64639359ba34`; costed `1f9a327631ff125f`). THE MIRROR CASE. The pack file declares no costs and the engine charges no funding, so this book was published at zero cost from day one and its BASE and ZERO are one artifact. The costed re-run under the engine's own repo6x5 preset is the informative number.

The costed re-run of HYPEUSDT 1h keeps 441 trades and charges 24027.45 in fees, landing at -10.15% net at PF 0.8994; its own in-artifact zero-cost re-score `ret_zero_pct` reads 16.8115 percent (`1f9a327631ff125f`).

**S02 Donchian + Flow Breakout — ETHUSDT 1h.** Base net 28.02% at PF 1.150 on 249 trades; zero net 51.48% at PF 1.272 on 249 trades (`3263ad328e60a1eb`, `82e522ce0d3b6bfd`). Its S02 row's `funding_paid_pct` reads 1.7982 and `funding_drag_pp` reads -2.1054, `3263ad328e60a1eb`. This cell reuses the ETH `cbpackf` artifacts minted for rows 31-40: same adapter, symbol, params, engine bytes and frozen cut, so the run_ids are identical by construction. It is a different strategy row (S02, not S10) read out of those same artifacts. The base line reproduces the published figure exactly.

**QS-002 EMA alignment with volatility confirmation — SOLUSDT 1h.** Base net 10.53% at PF 1.148 on 240 trades; zero net 23.65% at PF 1.294 on 240 trades (`e711fde2906d6ac5`, `5f1b8101c21825c5`). Its base run's `funding_paid` reads 98.55 over 910 settlement events (positive means paid), `e711fde2906d6ac5`. The base line reproduces the published figure exactly.

**QS-007 Higher-timeframe trend, lower-timeframe entries — SUIUSDT 1h.** Base net 9.41% at PF 1.143 on 102 trades; zero net 21.28% at PF 1.307 on 101 trades (`63bea721ab84c6d2`, `cda3153b5d6ef3c7`). Its base run's `funding_paid` reads 33.02 over 616 settlement events (positive means paid), `63bea721ab84c6d2`. The base line reproduces the published figure exactly; the trade count differs by one between regimes (see the caveat below).

On this cell the trade count itself changes with the cost regime — 102 on the base run `63bea721ab84c6d2` versus 101 on the zero run `cda3153b5d6ef3c7` — because the catalog's equity-dependent risk devices (daily-loss halt, drawdown halving and halt) are part of the strategy and react to the changed equity path. No signal rule was changed or re-fitted.

**QS-006 ADX-filtered directional continuation — JUPUSDT 1h.** Base net 17.79% at PF 1.130 on 284 trades; zero net 41.78% at PF 1.231 on 283 trades (`192383e1e8608069`, `5968f86e7e392aa7`). Its base run's `funding_paid` reads 36.21 over 1642 settlement events (positive means paid), `192383e1e8608069`. A re-measurement: the JUP kline file grew since the ranking. The trade count differs by one between regimes (see the caveat below).

On this cell the trade count itself changes with the cost regime — 284 on the base run `192383e1e8608069` versus 283 on the zero run `5968f86e7e392aa7` — because the catalog's equity-dependent risk devices (daily-loss halt, drawdown halving and halt) are part of the strategy and react to the changed equity path. No signal rule was changed or re-fitted.

**QS-003 Supertrend continuation — SUIUSDT 1h.** Base net 21.86% at PF 1.142 on 312 trades; zero net 36.87% at PF 1.219 on 311 trades (`0ff4fc9e3e349b9a`, `f33be5852a602f60`). Its base run's `funding_paid` reads 73.38 over 1650 settlement events (positive means paid), `0ff4fc9e3e349b9a`. The base line reproduces the published figure exactly; the trade count differs by one between regimes (see the caveat below).

On this cell the trade count itself changes with the cost regime — 312 on the base run `0ff4fc9e3e349b9a` versus 311 on the zero run `f33be5852a602f60` — because the catalog's equity-dependent risk devices (daily-loss halt, drawdown halving and halt) are part of the strategy and react to the changed equity path. No signal rule was changed or re-fitted.

## What the numbers say

Three readings, none of them a verdict:

1. **Seven of the ten published BASE figures reproduce exactly, and the three that do not sit on inputs that really grew.** The audit `code/_zerocost_rows41_50_audit.py` records which rows reproduced and which files grew; the reproducing rows' run_ids are on the table above.
2. **ds1 is again the mirror that shows what the ranking would look like if every book had been published at zero cost.** Its costed re-run keeps the same signal sequence and pays a real fee bill for a negative net line (both run_ids are cited on the row 45 lines above). A zero-cost line is an upper bound, not a tradable result.
3. **All nine non-mirror books rise at ZERO, but four of the five `qs` cells also change their trade count.** The cost block changes the equity path, and the catalog's own risk devices then change which entries are taken; this is declared per row above rather than buried.

## What this is not

- It is not a resurrection of any killed strategy. The kill list is unchanged: these ten rows carry the verdicts of their own campaigns (the strategy packs, the QS catalog, fingrad and the DeepSeek pack).
- It is not evidence of alpha. A zero-cost line is the upper bound of what a book could earn if execution were free; nobody trades for free.
- It is not a gate pass. No gate was evaluated here.
- It is not agent- or user-selected: the ten are published ranking rows 41 to 50, decided before this campaign existed.

## Limits and declared caveats

- **The ds1 published number was never a costed number.** The pack declares no costs and the engine charges no funding, so the ranking row was a zero-cost construction from the start; this campaign quantified that inside an artifact. The costed re-run uses the engine's own repo6x5 preset; no gate is evaluated on it.
- **Funding is a real cash flow, not a fee.** ZERO removes it because the user asked for all costs removed; for a perp that is a declared control, never a tradable result. `fingrad` here had funding off in both regimes, exactly as published.
- **The `qs` ZERO regime zeroes the whole ladder including the random-entry null**, so the null comparison inside those artifacts is a zero-cost null against a zero-cost book — consistent, but not the published null regime.
- **Execution was not relaxed.** Signal on the closed bar, the engines' own fill modes, stop-first on ties, sizing and risk devices all stay. Only the cost block and the screening rules were removed.
- **A re-measurement is not a contradiction.** Where an input file grew since the ranking, both columns were minted on the same frozen cut; the audit records which rows reproduced exactly and which did not.

## Provenance

- Pre-registration: `results/zerocost_rows41_50_pre_registration.md` (written before the first artifact existed).
- Matrix: `results/zerocost_rows41_50_matrix.json` (per-cell run_ids, params, cut and inputs, plus the costed re-run).
- Verification log: `results/_zerocost_rows41_50_verify.txt` — twenty artifacts, twenty OK.
- Audit: `code/_zerocost_rows41_50_audit.py` — independent fresh-module recomputation for `qs`, `fingrad` and `dspack`, the engines' own in-artifact references, declared cost fields and determinism for `cbpackf`, and the pre-registered reproduction semantics.
- No harness or engine file was edited for this batch: every adapter already exposed its cost switch. The engine files are byte-untouched and hashed into every run_id.

