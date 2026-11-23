# Zero cost, no rules — this batch of the hundred best books re-run

Date: 2026-11-23. Status: **experiment / control**. No verdict, no gate and no alpha claim (see `results/zerocost_rows81_90_pre_registration.md`, written before the first artifact). Ninth batch of the control begun in `results/zerocost_report_2026-11-20.md` and continued in the six reports that followed it.

## The question

Ten books were taken from `results/top100_2026-10-31.md` — rows 81 to 90, in the order that list already published — and each was run twice on the same frozen cut by the same engine bytes: once under its published cost regime (**BASE**) and once with fees, slippage and funding cash flow at zero (**ZERO**). No screening gate is applied. ds3 (two rows) was published at zero cost (`author`, no funding), so its BASE and ZERO are one artifact and the informative runs are the **COSTED** re-runs.

Ten books produced twenty artifacts — two BASE/ZERO pairs share one artifact by construction, plus two costed re-runs — every one verifying bit-for-bit (`results/_zerocost_rows81_90_verify.txt`).

## The ten, both regimes

Every row is one stored artifact; the run_id is on its own row. Net % is the book's own full-window return, PF its profit factor, Trades its closed-trade count and Max DD % the drawdown exactly as the engine stores it (negative where the engine reports a signed drawdown).

| Book | Market | Regime | Net % | PF | Trades | Max DD % | run_id |
|---|---|---|---:|---:|---:|---:|---|
| fingrad | NEARUSDT 1h | BASE | 12.45 | 1.056 | 736 | 17.21 | `dae20162749ceb78` |
| fingrad | NEARUSDT 1h | ZERO | 42.57 | 1.198 | 736 | 13.80 | `ce1c43e3325ae204` |
| G82-1h weekend effect (long) | BTCUSDT 1h | BASE | 2.29 | 1.057 | 104 | 17.11 | `d290940df20ffc6d` |
| G82-1h weekend effect (long) | BTCUSDT 1h | ZERO | 18.20 | 1.256 | 104 | 14.89 | `3d1888c2df77572b` |
| QS-001 Moving-average trend continuation (long-only) | ETHUSDT 5m | BASE | 9.03 | 1.056 | 460 | -25.10 | `08b4eb9c82e57dab` |
| QS-001 Moving-average trend continuation (long-only) | ETHUSDT 5m | ZERO | 119.89 | 1.311 | 489 | -25.00 | `35580b18a43c357b` |
| S02 Donchian + Flow Breakout | SOLUSDT 1h | BASE | 9.94 | 1.051 | 269 | -26.73 | `77e526d5910e1be8` |
| S02 Donchian + Flow Breakout | SOLUSDT 1h | ZERO | 29.53 | 1.150 | 269 | -23.90 | `30cf4a07c3814ec6` |
| ds3 | BNBUSDT 1h | BASE | 73.85 | 1.040 | 322 | -72.43 | `6a14a29502e68082` |
| ds3 | BNBUSDT 1h | ZERO | 73.85 | 1.040 | 322 | -72.43 | `6a14a29502e68082` |
| S01 Taker-Flow Drift Bands | SUIUSDT 1h | BASE | 8.76 | 1.045 | 292 | -16.02 | `4705d6f88c3d7b5f` |
| S01 Taker-Flow Drift Bands | SUIUSDT 1h | ZERO | 27.68 | 1.141 | 292 | -13.22 | `5228fb785c9a334e` |
| ds1 | AVAXUSDT 1h | BASE | 34.97 | 1.049 | 1833 | -36.73 | `2c2e43de088921bc` |
| ds1 | AVAXUSDT 1h | ZERO | 291.72 | 1.278 | 1833 | -25.90 | `753e1c61919bcf56` |
| ds3 | DOGEUSDT 1h | BASE | 418.42 | 1.045 | 298 | -79.39 | `2879bf46de7fd3db` |
| ds3 | DOGEUSDT 1h | ZERO | 900.46 | 1.069 | 298 | -76.85 | `f3dc8cbe95c71648` |
| QS-009 Volatility-adjusted momentum | ETHUSDT 1h | BASE | 4.51 | 1.043 | 386 | -17.98 | `1c3373f1bb39b044` |
| QS-009 Volatility-adjusted momentum | ETHUSDT 1h | ZERO | 27.35 | 1.205 | 385 | -16.79 | `5cb4f21b0e672270` |
| ds3 | ADAUSDT 1h | BASE | 375.83 | 1.041 | 314 | -82.43 | `1f809d76773c08ce` |
| ds3 | ADAUSDT 1h | ZERO | 375.83 | 1.041 | 314 | -82.43 | `1f809d76773c08ce` |

## What each regime actually charged

Fields below are the artifacts' own declarations: the catalog base point, the `cbpackf` and `pack100` per-side/combined cost blocks with their funding flags, and the `dspack`/`dspack2` preset names.

| Adapter | Market | Base fee | Base slip | Base funding | Zero fee | Zero slip | Zero funding | run_ids |
|---|---|---|---|---|---|---|---|---|
| `fingrad` | NEARUSDT 1h | 5 | 0 | False | 0 | 0 | False | `dae20162749ceb78` `ce1c43e3325ae204` |
| `pack100` | BTCUSDT 1h | 5.5 combined | n/a | True | 0 combined | n/a | False | `d290940df20ffc6d` `3d1888c2df77572b` |
| `qs` | ETHUSDT 5m | 5 | 2 | True | 0 | 0 | False | `08b4eb9c82e57dab` `35580b18a43c357b` |
| `cbpackf` | SOLUSDT 1h | 5 | 0.5 | True | 0 | 0 | False | `77e526d5910e1be8` `30cf4a07c3814ec6` |
| `dspack` | BNBUSDT 1h | author | in preset | n/a (kline-only) | author | in preset | n/a (kline-only) | `6a14a29502e68082` `6a14a29502e68082` |
| `cbpackf` | SUIUSDT 1h | 5 | 0.5 | True | 0 | 0 | False | `4705d6f88c3d7b5f` `5228fb785c9a334e` |
| `dspack` | AVAXUSDT 1h | repo6x5 | in preset | n/a (kline-only) | author | in preset | n/a (kline-only) | `2c2e43de088921bc` `753e1c61919bcf56` |
| `dspack` | DOGEUSDT 1h | repo6x5 | in preset | n/a (kline-only) | author | in preset | n/a (kline-only) | `2879bf46de7fd3db` `f3dc8cbe95c71648` |
| `qs` | ETHUSDT 1h | 5 | 2 | True | 0 | 0 | False | `1c3373f1bb39b044` `5cb4f21b0e672270` |
| `dspack` | ADAUSDT 1h | author | in preset | n/a (kline-only) | author | in preset | n/a (kline-only) | `1f809d76773c08ce` `1f809d76773c08ce` |

## Book by book

Each line quotes its own artifacts, with run_ids on the line.

**fingrad — NEARUSDT 1h.** Base net 12.45% at PF 1.056 on 736 trades; zero net 42.57% at PF 1.198 on 736 trades (`dae20162749ceb78`, `ce1c43e3325ae204`). This published row had funding OFF, so the only thing removed at ZERO is the fee block. The engine's own fee-only reference is measured inside the base artifact.

**G82-1h weekend effect (long) — BTCUSDT 1h.** Base net 2.29% at PF 1.057 on 104 trades; zero net 18.20% at PF 1.256 on 104 trades (`d290940df20ffc6d`, `3d1888c2df77572b`). Its own `zero_cost_pf` reads 1.2123 (fees removed with funding still charged), `d290940df20ffc6d`. The base figure reproduces the published one exactly under current engine bytes despite the old ranking artifact's engine drift.

**QS-001 Moving-average trend continuation (long-only) — ETHUSDT 5m.** Base net 9.03% at PF 1.056 on 460 trades; zero net 119.89% at PF 1.311 on 489 trades (`08b4eb9c82e57dab`, `35580b18a43c357b`). Its base run's `funding_paid` reads 178.06 over 221 settlement events (positive means paid), `08b4eb9c82e57dab`. A five-minute long-only cell, the fastest timeframe in the whole control. The base figure reproduces the published one exactly; its trade count changes with the regime (below).

On this cell the trade count changes with the cost regime — 460 on the base run `08b4eb9c82e57dab` versus 489 on the zero run `35580b18a43c357b` — because the catalog's equity-dependent risk devices (daily-loss halt, drawdown halving and halt) are part of the strategy and react to the changed equity path. No signal rule was changed.

**S02 Donchian + Flow Breakout — SOLUSDT 1h.** Base net 9.94% at PF 1.051 on 269 trades; zero net 29.53% at PF 1.150 on 269 trades (`77e526d5910e1be8`, `30cf4a07c3814ec6`). Its S02 row's `funding_paid_pct` reads 2.5081 and `funding_drag_pp` reads -2.5271, `77e526d5910e1be8`. The SOL `cbpackf` artifacts were minted for this batch; the ranking row is S02, and the engine's own funding drag is measured inside the base artifact.

**ds3 — BNBUSDT 1h.** Base net 73.85% at PF 1.040 on 322 trades; zero net 73.85% at PF 1.040 on 322 trades (`6a14a29502e68082`; costed `b56e70553e41d823`). THE MIRROR CASE. ds3 was published at `costs=author` — no costs, no funding — so BASE and ZERO are one artifact. The costed re-run keeps the same signals and pays real fees.

The costed re-run keeps 322 trades and charges 106521.21 in fees, landing at -14.55% net at PF 0.9901; its in-artifact zero-cost re-score `ret_zero_pct` reads 73.8490 percent (`b56e70553e41d823`).

**S01 Taker-Flow Drift Bands — SUIUSDT 1h.** Base net 8.76% at PF 1.045 on 292 trades; zero net 27.68% at PF 1.141 on 292 trades (`4705d6f88c3d7b5f`, `5228fb785c9a334e`). Its S01 row's `funding_paid_pct` reads 0.3625 and `funding_drag_pp` reads -0.3996, `4705d6f88c3d7b5f`. This row reuses the SUI `cbpackf` artifacts minted in earlier batches (same adapter, symbol, params, engine and cut); the ranking row is S01, read out of those artifacts.

**ds1 — AVAXUSDT 1h.** Base net 34.97% at PF 1.049 on 1833 trades; zero net 291.72% at PF 1.278 on 1833 trades (`2c2e43de088921bc`, `753e1c61919bcf56`). ds1 was published with a real cost block (`repo6x5`); ZERO is the same engine's `author` preset. The in-artifact zero re-score and the author headline coincide.

**ds3 — DOGEUSDT 1h.** Base net 418.42% at PF 1.045 on 298 trades; zero net 900.46% at PF 1.069 on 298 trades (`2879bf46de7fd3db`, `f3dc8cbe95c71648`). ds3 was published at `repo6x5`; its ZERO is `author`. The kline file grew since the ranking, so the base figure is a re-measurement.

**QS-009 Volatility-adjusted momentum — ETHUSDT 1h.** Base net 4.51% at PF 1.043 on 386 trades; zero net 27.35% at PF 1.205 on 385 trades (`1c3373f1bb39b044`, `5cb4f21b0e672270`). Its base run's `funding_paid` reads 60.64 over 1164 settlement events (positive means paid), `1c3373f1bb39b044`. The base figure reproduces the published one exactly under current engine bytes; its trade count changes by one (below).

On this cell the trade count changes with the cost regime — 386 on the base run `1c3373f1bb39b044` versus 385 on the zero run `5cb4f21b0e672270` — because the catalog's equity-dependent risk devices (daily-loss halt, drawdown halving and halt) are part of the strategy and react to the changed equity path. No signal rule was changed.

**ds3 — ADAUSDT 1h.** Base net 375.83% at PF 1.041 on 314 trades; zero net 375.83% at PF 1.041 on 314 trades (`1f809d76773c08ce`; costed `ee7ad10ea0eab968`). THE MIRROR CASE. ds3 on ADA was published at `author` (zero cost, no funding), so BASE and ZERO are one artifact and its informative run is the COSTED re-run, which pays real fees on identical signals.

The costed re-run keeps 314 trades and charges 295196.02 in fees, landing at 138.03% net at PF 1.0186; its in-artifact zero-cost re-score `ret_zero_pct` reads 375.8307 percent (`ee7ad10ea0eab968`).

## What the numbers say

Three readings, none of them a verdict:

1. **Old `qs` and `pack100` ranking artifacts no longer verify after the 2026-11-21 audit-fix changed their engine bytes.** That is a provenance fact, not tampering; all artifacts here are on current bytes and verify. Matching BASE figures are exact figure reproductions, not bit-identical artifacts.
2. **ds1/ds3-on-DOGE and ds3-on-BNB/ADA are the two mirror images of the cost question.** The costed-published rows multiply at zero while the author-published rows pay dearly when charged (run_ids are cited on their lines above). Neither line is an alpha claim.
3. **All ten books rise at ZERO, and three `qs` cells also change their trade count** through the catalog's own risk devices (declared above), so cost removal here can change which trades exist, not just their size.

## What this is not

- It is not a resurrection of any killed strategy; the kill list is unchanged and these rows carry the verdicts of their own campaigns.
- It is not evidence of alpha. A zero-cost line is the upper bound of what a book could earn if execution were free; nobody trades for free.
- It is not a gate pass. No gate was evaluated here.
- It is not agent- or user-selected: the ten are published ranking rows rows 81 to 90 of the published ranking, decided before this campaign existed.

## Limits and declared caveats

- **Funding is a real cash flow, not a fee.** ZERO removes it because the user asked for all costs removed; for a perp that is a declared control, never a tradable result.
- **The `qs` ZERO regime zeroes the whole ladder including the random entry null**, so its internal null comparison is zero-cost against zero-cost — consistent, but not the published null regime.
- **Execution was not relaxed.** Signal on the closed bar, fill modes, stop-first ties, sizing and risk devices all stay. Only the cost block and the screening rules were removed.
- **A re-measurement is not a contradiction.** Where an input file grew or an engine changed, both columns were minted on the same frozen cut and current engine bytes; the audit records which figures reproduced.

## Provenance

- Pre-registration: `results/zerocost_rows81_90_pre_registration.md` (written before the first artifact existed).
- Matrix: `results/zerocost_rows81_90_matrix.json` (per-cell run_ids, params, cut and inputs, plus the costed re-run).
- Verification log: `results/_zerocost_rows81_90_verify.txt` — twenty artifacts, twenty OK.
- Audit: `code/_zerocost_rows81_90_audit.py` — independent fresh-module recomputation for every adapter, the engines' own in-artifact references and the pre-registered reproduction semantics with engine drift stated.
- No harness or engine file was edited for this batch; the engine files are byte-untouched and hashed into every run_id.

