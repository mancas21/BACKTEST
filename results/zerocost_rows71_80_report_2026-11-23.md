# Zero cost, no rules — this batch of the hundred best books re-run

Date: 2026-11-23. Status: **experiment / control**. No verdict, no gate and no alpha claim (see `results/zerocost_rows71_80_pre_registration.md`, written before the first artifact). Eighth batch of the control begun in `results/zerocost_report_2026-11-20.md` and continued in the six reports that followed it.

## The question

Ten books were taken from `results/top100_2026-10-31.md` — the next ten rows, in the order that list already published — and each was run twice on the same frozen cut by the same engine bytes: once under its published cost regime (**BASE**) and once with fees, slippage and funding cash flow at zero (**ZERO**). No screening gate is applied. ds3 was published at zero cost (`author`, no funding), so its BASE and ZERO are one artifact and its informative run is the **COSTED** re-run.

Ten books produced twenty artifacts — one BASE/ZERO pair is shared by construction — every one verifying bit-for-bit (`results/_zerocost_rows71_80_verify.txt`).

## The ten, both regimes

Every row is one stored artifact; the run_id is on its own row. Net % is the book's own full-window return, PF its profit factor, Trades its closed-trade count and Max DD % the drawdown exactly as the engine stores it (negative where the engine reports a signed drawdown).

| Book | Market | Regime | Net % | PF | Trades | Max DD % | run_id |
|---|---|---|---:|---:|---:|---:|---|
| A01-15m RSI14 L/S mean-reversion | SPXUSDT 15m | BASE | 13.83 | 1.083 | 237 | 27.40 | `3647fed275a7b77c` |
| A01-15m RSI14 L/S mean-reversion | SPXUSDT 15m | ZERO | 47.66 | 1.213 | 237 | 21.41 | `eb017a535c69cc11` |
| QS-002 EMA alignment with volatility confirmation (long-only) | HYPEUSDT 15m | BASE | 9.08 | 1.082 | 360 | -24.02 | `c29fbb77372b8579` |
| QS-002 EMA alignment with volatility confirmation (long-only) | HYPEUSDT 15m | ZERO | 39.34 | 1.264 | 356 | -19.35 | `bc53ded2edf08db5` |
| QS-009 Volatility-adjusted momentum | BTCUSDT 1h | BASE | 11.11 | 1.081 | 381 | -20.29 | `a9568897d5c08a80` |
| QS-009 Volatility-adjusted momentum | BTCUSDT 1h | ZERO | 59.84 | 1.373 | 379 | -17.24 | `46611f80126dd193` |
| S5 Heikin-Ashi trend | SUIUSDT 4h | BASE | 16.09 | 1.077 | 110 | 52.53 | `e8d437bacc785b9e` |
| S5 Heikin-Ashi trend | SUIUSDT 4h | ZERO | 46.71 | 1.218 | 110 | 46.49 | `02795d4eab8bb655` |
| QS-005 Time-series momentum | HYPEUSDT 1h | BASE | 3.76 | 1.074 | 100 | -16.53 | `b6dc98890bc4c662` |
| QS-005 Time-series momentum | HYPEUSDT 1h | ZERO | 8.38 | 1.157 | 100 | -16.20 | `643b25231b3f0256` |
| QS-007 Higher-timeframe trend, lower-timeframe entries | ETHUSDT 1h | BASE | 3.64 | 1.073 | 114 | -15.46 | `21f34554458d08d5` |
| QS-007 Higher-timeframe trend, lower-timeframe entries | ETHUSDT 1h | ZERO | 13.57 | 1.239 | 114 | -15.16 | `2332b967e16116c5` |
| ds1 | SOLUSDT 1h | BASE | 54.51 | 1.067 | 1765 | -31.58 | `724fb33d063acf1e` |
| ds1 | SOLUSDT 1h | ZERO | 333.70 | 1.300 | 1765 | -19.14 | `afeca0c9288350ff` |
| ds3 | ETHUSDT 1h | BASE | 225.45 | 1.067 | 320 | -78.82 | `581a12987a05a8a0` |
| ds3 | ETHUSDT 1h | ZERO | 225.45 | 1.067 | 320 | -78.82 | `581a12987a05a8a0` |
| QS-001 Moving-average trend continuation | HYPEUSDT 15m | BASE | 7.86 | 1.063 | 314 | -24.15 | `035d83e64f5a3a88` |
| QS-001 Moving-average trend continuation | HYPEUSDT 15m | ZERO | 35.47 | 1.252 | 313 | -21.88 | `5fcd43b88a1d6abf` |
| B25-1h Keltner breakout (long) | SOLUSDT 1h | BASE | 1.93 | 1.060 | 183 | 31.36 | `6190ac3ea54ffb86` |
| B25-1h Keltner breakout (long) | SOLUSDT 1h | ZERO | 27.86 | 1.182 | 183 | 26.80 | `244be1e23b4045a1` |

## What each regime actually charged

Fields below are the artifacts' own declarations: the catalog base point, the `cbpackf` and `pack100` per-side/combined cost blocks with their funding flags, and the `dspack`/`dspack2` preset names.

| Adapter | Market | Base fee | Base slip | Base funding | Zero fee | Zero slip | Zero funding | run_ids |
|---|---|---|---|---|---|---|---|---|
| `pack100` | SPXUSDT 15m | 5.5 combined | n/a | True | 0 combined | n/a | False | `3647fed275a7b77c` `eb017a535c69cc11` |
| `qs` | HYPEUSDT 15m | 5 | 2 | True | 0 | 0 | False | `c29fbb77372b8579` `bc53ded2edf08db5` |
| `qs` | BTCUSDT 1h | 5 | 2 | True | 0 | 0 | False | `a9568897d5c08a80` `46611f80126dd193` |
| `pack50` | SUIUSDT 4h | 5 | 5 | True | 0 | 0 | False | `e8d437bacc785b9e` `02795d4eab8bb655` |
| `qs` | HYPEUSDT 1h | 5 | 2 | True | 0 | 0 | False | `b6dc98890bc4c662` `643b25231b3f0256` |
| `qs` | ETHUSDT 1h | 5 | 2 | True | 0 | 0 | False | `21f34554458d08d5` `2332b967e16116c5` |
| `dspack` | SOLUSDT 1h | repo6x5 | in preset | n/a (kline-only) | author | in preset | n/a (kline-only) | `724fb33d063acf1e` `afeca0c9288350ff` |
| `dspack` | ETHUSDT 1h | author | in preset | n/a (kline-only) | author | in preset | n/a (kline-only) | `581a12987a05a8a0` `581a12987a05a8a0` |
| `qs` | HYPEUSDT 15m | 5 | 2 | True | 0 | 0 | False | `035d83e64f5a3a88` `5fcd43b88a1d6abf` |
| `pack100` | SOLUSDT 1h | 5.5 combined | n/a | True | 0 combined | n/a | False | `6190ac3ea54ffb86` `244be1e23b4045a1` |

## Book by book

Each line quotes its own artifacts, with run_ids on the line.

**A01-15m RSI14 L/S mean-reversion — SPXUSDT 15m.** Base net 13.83% at PF 1.083 on 237 trades; zero net 47.66% at PF 1.213 on 237 trades (`3647fed275a7b77c`, `eb017a535c69cc11`). Its own `zero_cost_pf` reads 1.2130 (fees removed with funding still charged), `3647fed275a7b77c`. The base figure reproduces the published one exactly under current engine bytes despite the old ranking artifact's engine drift.

**QS-002 EMA alignment with volatility confirmation (long-only) — HYPEUSDT 15m.** Base net 9.08% at PF 1.082 on 360 trades; zero net 39.34% at PF 1.264 on 356 trades (`c29fbb77372b8579`, `bc53ded2edf08db5`). Its base run's `funding_paid` reads 133.86 over 645 settlement events (positive means paid), `c29fbb77372b8579`. A fifteen-minute long-only cell; the base figure reproduces the published one exactly. Its trade count changes with the regime (below).

On this cell the trade count changes with the cost regime — 360 on the base run `c29fbb77372b8579` versus 356 on the zero run `bc53ded2edf08db5` — because the catalog's equity-dependent risk devices (daily-loss halt, drawdown halving and halt) are part of the strategy and react to the changed equity path. No signal rule was changed.

**QS-009 Volatility-adjusted momentum — BTCUSDT 1h.** Base net 11.11% at PF 1.081 on 381 trades; zero net 59.84% at PF 1.373 on 379 trades (`a9568897d5c08a80`, `46611f80126dd193`). Its base run's `funding_paid` reads 11.56 over 1211 settlement events (positive means paid), `a9568897d5c08a80`. The base figure reproduces the published one exactly under current engine bytes; its trade count changes with the regime (below).

On this cell the trade count changes with the cost regime — 381 on the base run `a9568897d5c08a80` versus 379 on the zero run `46611f80126dd193` — because the catalog's equity-dependent risk devices (daily-loss halt, drawdown halving and halt) are part of the strategy and react to the changed equity path. No signal rule was changed.

**S5 Heikin-Ashi trend — SUIUSDT 4h.** Base net 16.09% at PF 1.077 on 110 trades; zero net 46.71% at PF 1.218 on 110 trades (`e8d437bacc785b9e`, `02795d4eab8bb655`). A four-hour `pack50` cell: the pack's own per-symbol cost table is the published regime, and the engine's own funding flag is declared in both columns.

**QS-005 Time-series momentum — HYPEUSDT 1h.** Base net 3.76% at PF 1.074 on 100 trades; zero net 8.38% at PF 1.157 on 100 trades (`b6dc98890bc4c662`, `643b25231b3f0256`). Its base run's `funding_paid` reads 8.19 over 1219 settlement events (positive means paid), `b6dc98890bc4c662`. The base figure reproduces the published one exactly under current engine bytes.

**QS-007 Higher-timeframe trend, lower-timeframe entries — ETHUSDT 1h.** Base net 3.64% at PF 1.073 on 114 trades; zero net 13.57% at PF 1.239 on 114 trades (`21f34554458d08d5`, `2332b967e16116c5`). Its base run's `funding_paid` reads 39.35 over 579 settlement events (positive means paid), `21f34554458d08d5`. The base figure reproduces the published one exactly under current engine bytes.

**ds1 — SOLUSDT 1h.** Base net 54.51% at PF 1.067 on 1765 trades; zero net 333.70% at PF 1.300 on 1765 trades (`724fb33d063acf1e`, `afeca0c9288350ff`). ds1 was published with a real cost block (`repo6x5`); ZERO is the same engine's `author` preset. The in-artifact zero re-score and the author headline coincide.

**ds3 — ETHUSDT 1h.** Base net 225.45% at PF 1.067 on 320 trades; zero net 225.45% at PF 1.067 on 320 trades (`581a12987a05a8a0`; costed `ac7c189d26e96774`). THE MIRROR CASE. ds3 was published at `costs=author` — no costs, no funding — so BASE and ZERO are one artifact. The costed re-run keeps the same signal sequence and pays real fees.

The costed re-run keeps 320 trades and charges 155404.35 in fees, landing at 60.67% net at PF 1.0221; its in-artifact zero-cost re-score `ret_zero_pct` reads 225.4495 percent (`ac7c189d26e96774`).

**QS-001 Moving-average trend continuation — HYPEUSDT 15m.** Base net 7.86% at PF 1.063 on 314 trades; zero net 35.47% at PF 1.252 on 313 trades (`035d83e64f5a3a88`, `5fcd43b88a1d6abf`). Its base run's `funding_paid` reads 29.71 over 901 settlement events (positive means paid), `035d83e64f5a3a88`. The base figure reproduces the published one exactly under current engine bytes; its trade count changes with the regime (below).

On this cell the trade count changes with the cost regime — 314 on the base run `035d83e64f5a3a88` versus 313 on the zero run `5fcd43b88a1d6abf` — because the catalog's equity-dependent risk devices (daily-loss halt, drawdown halving and halt) are part of the strategy and react to the changed equity path. No signal rule was changed.

**B25-1h Keltner breakout (long) — SOLUSDT 1h.** Base net 1.93% at PF 1.060 on 183 trades; zero net 27.86% at PF 1.182 on 183 trades (`6190ac3ea54ffb86`, `244be1e23b4045a1`). Its own `zero_cost_pf` reads 1.1676 (fees removed with funding still charged), `6190ac3ea54ffb86`. The base figure reproduces the published one exactly under current engine bytes.

## What the numbers say

Three readings, none of them a verdict:

1. **Old `qs` and `pack100` ranking artifacts no longer verify after the 2026-11-21 audit-fix changed their engine bytes.** That is a provenance fact, not tampering; all artifacts here are on current bytes and verify. Matching BASE figures are exact figure reproductions, not bit-identical artifacts.
2. **ds1 and ds3 are the two mirror images of the cost question.** ds1 was published costed and multiplies at zero; ds3 was published at zero and pays dearly when charged (both pairs of run_ids are cited on their lines above). Neither line is an alpha claim.
3. **All ten books rise at ZERO, and three `qs` cells also change their trade count** through the catalog's own risk devices (declared above), so cost removal here can change which trades exist, not just their size.

## What this is not

- It is not a resurrection of any killed strategy; the kill list is unchanged and these rows carry the verdicts of their own campaigns.
- It is not evidence of alpha. A zero-cost line is the upper bound of what a book could earn if execution were free; nobody trades for free.
- It is not a gate pass. No gate was evaluated here.
- It is not agent- or user-selected: the ten are published ranking rows the published ranking, decided before this campaign existed.

## Limits and declared caveats

- **Funding is a real cash flow, not a fee.** ZERO removes it because the user asked for all costs removed; for a perp that is a declared control, never a tradable result.
- **The `qs` ZERO regime zeroes the whole ladder including the random entry null**, so its internal null comparison is zero-cost against zero-cost — consistent, but not the published null regime.
- **Execution was not relaxed.** Signal on the closed bar, fill modes, stop-first ties, sizing and risk devices all stay. Only the cost block and the screening rules were removed.
- **A re-measurement is not a contradiction.** Where an input file grew or an engine changed, both columns were minted on the same frozen cut and current engine bytes; the audit records which figures reproduced.

## Provenance

- Pre-registration: `results/zerocost_rows71_80_pre_registration.md` (written before the first artifact existed).
- Matrix: `results/zerocost_rows71_80_matrix.json` (per-cell run_ids, params, cut and inputs, plus the costed re-run).
- Verification log: `results/_zerocost_rows71_80_verify.txt` — twenty artifacts, twenty OK.
- Audit: `code/_zerocost_rows71_80_audit.py` — independent fresh-module recomputation for every adapter, the engines' own in-artifact references and the pre-registered reproduction semantics with engine drift stated.
- No harness or engine file was edited for this batch; the engine files are byte-untouched and hashed into every run_id.

