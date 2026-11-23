# Zero cost, no rules — rows 51-60 of the hundred best books re-run

Date: 2026-11-23. Status: **experiment / control**. No verdict, no gate and no alpha claim (see `results/zerocost_rows51_60_pre_registration.md` and its dated addendum, both written before the market artifacts). Sixth batch of the control begun in `results/zerocost_report_2026-11-20.md` and continued in the four reports that followed it.

## The question

Ten more books were taken from `results/top100_2026-10-31.md` — rows 51 to 60, in the order that list already published — and each was run twice on the same frozen cut by the same engine bytes: once under its published cost regime (**BASE**) and once with fees, slippage and funding cash flow at zero (**ZERO**). No screening gate is applied. ds3 is the one book here that was published WITH a real cost block (`repo6x5`), so its ZERO uses the same engine's `author` preset.

Ten books produced twenty artifacts (two `cbpackf` SUI artifacts reused from the rows 41-50 batch: same adapter, symbol, params, engine and cut), every one verifying bit-for-bit (`results/_zerocost_rows51_60_verify.txt`).

## The ten, both regimes

Every row is one stored artifact; the run_id is on its own row. Net % is the book's own full-window return, PF its profit factor, Trades its closed-trade count and Max DD % the drawdown exactly as the engine stores it (negative where the engine reports a signed drawdown).

| Book | Market | Regime | Net % | PF | Trades | Max DD % | run_id |
|---|---|---|---:|---:|---:|---:|---|
| P08 Keltner breakout | ETHUSDT 1h | BASE | 114.98 | 1.169 | 522 | 31.80 | `9258472c05579db5` |
| P08 Keltner breakout | ETHUSDT 1h | ZERO | 287.92 | 1.295 | 522 | 26.15 | `50268b8b42f8b857` |
| QS-009 Volatility-adjusted momentum | SUIUSDT 1h | BASE | 26.63 | 1.137 | 363 | -22.76 | `9f34c460644e7fc1` |
| QS-009 Volatility-adjusted momentum | SUIUSDT 1h | ZERO | 54.15 | 1.232 | 364 | -19.23 | `c0760989624cde8d` |
| S10 Vol-Targeted Time-Series Momentum | SUIUSDT 1h | BASE | 12.99 | 1.133 | 167 | -20.81 | `4705d6f88c3d7b5f` |
| S10 Vol-Targeted Time-Series Momentum | SUIUSDT 1h | ZERO | 19.11 | 1.198 | 167 | -20.05 | `5228fb785c9a334e` |
| S10 Vol-Targeted Time-Series Momentum | HYPEUSDT 1h | BASE | 9.30 | 1.130 | 121 | -20.93 | `c7b3795cd19f22b2` |
| S10 Vol-Targeted Time-Series Momentum | HYPEUSDT 1h | ZERO | 13.59 | 1.193 | 121 | -19.92 | `5d377f62df2be150` |
| QS-006 ADX-filtered directional continuation | ETHUSDT 1h | BASE | 11.18 | 1.127 | 293 | -17.11 | `10ab97da5d782c39` |
| QS-006 ADX-filtered directional continuation | ETHUSDT 1h | ZERO | 28.77 | 1.302 | 292 | -16.58 | `ce371a0bc5f65615` |
| S07 Funding Extreme Fade | ETHUSDT 1h | BASE | 2.71 | 1.126 | 34 | -5.30 | `3263ad328e60a1eb` |
| S07 Funding Extreme Fade | ETHUSDT 1h | ZERO | 4.60 | 1.225 | 34 | -4.98 | `b1a2c9c0e325a6c9` |
| C44-1h fractal breakout | ETHUSDT 1h | BASE | 29.25 | 1.126 | 381 | 65.91 | `d2546b98f9d9ce7a` |
| C44-1h fractal breakout | ETHUSDT 1h | ZERO | 103.40 | 1.218 | 381 | 61.52 | `2a5af8f7aed9ac76` |
| ds3 | SOLUSDT 1h | BASE | 4466.84 | 1.125 | 286 | -70.99 | `8a0e44e2ffefff86` |
| ds3 | SOLUSDT 1h | ZERO | 8483.28 | 1.169 | 286 | -67.29 | `85401329ff6193c9` |
| QS-003 Supertrend continuation | SOLUSDT 1h | BASE | 15.62 | 1.124 | 340 | -22.77 | `0d908e3b1a540201` |
| QS-003 Supertrend continuation | SOLUSDT 1h | ZERO | 32.92 | 1.232 | 340 | -22.43 | `3829df669e17a50b` |
| MP-V3-S10 Pure Equal Weight Momentum | PORTFOLIO 1h | BASE | 1098.37 | 1.119 | 317 | -80.21 | `fabe6ed1e63d66cf` |
| MP-V3-S10 Pure Equal Weight Momentum | PORTFOLIO 1h | ZERO | 1230.74 | 1.128 | 317 | -79.79 | `4219f0cd0da94225` |

## What each regime actually charged

The fields below are the artifacts' own declarations. `qs` declares the catalog ladder's base point; `cbpackf`, `pack100` and `pack50d` declare per-side costs plus the engine's funding flag (the latter two as one combined figure); `mpv3` declares fee, slippage and round-trip; `dspack` declares the preset name (`repo6x5` or `author`).

| Adapter | Market | Base fee | Base slip | Base funding | Zero fee | Zero slip | Zero funding | run_ids |
|---|---|---|---|---|---|---|---|---|
| `pack50d` | ETHUSDT 1h | 5.5 combined | n/a | True | 5.5 combined | n/a | False | `9258472c05579db5` `50268b8b42f8b857` |
| `qs` | SUIUSDT 1h | 5 | 2 | True | 0 | 0 | False | `9f34c460644e7fc1` `c0760989624cde8d` |
| `cbpackf` | SUIUSDT 1h | 5 | 0.5 | True | 0 | 0 | False | `4705d6f88c3d7b5f` `5228fb785c9a334e` |
| `cbpackf` | HYPEUSDT 1h | 5 | 0.5 | True | 0 | 0 | False | `c7b3795cd19f22b2` `5d377f62df2be150` |
| `qs` | ETHUSDT 1h | 5 | 2 | True | 0 | 0 | False | `10ab97da5d782c39` `ce371a0bc5f65615` |
| `cbpackf` | ETHUSDT 1h | 5 | 0.5 | True | 0 | 0 | False | `3263ad328e60a1eb` `b1a2c9c0e325a6c9` |
| `pack100` | ETHUSDT 1h | 5.5 combined | n/a | True | 0 combined | n/a | False | `d2546b98f9d9ce7a` `2a5af8f7aed9ac76` |
| `dspack` | SOLUSDT 1h | repo6x5 | in preset | n/a (kline-only) | author | in preset | n/a (kline-only) | `8a0e44e2ffefff86` `85401329ff6193c9` |
| `qs` | SOLUSDT 1h | 5 | 2 | True | 0 | 0 | False | `0d908e3b1a540201` `3829df669e17a50b` |
| `mpv3` | PORTFOLIO 1h | 5 | 0.5 | n/a (no funding) | 0 | 0 | n/a (no funding) | `fabe6ed1e63d66cf` `4219f0cd0da94225` |

Funding signs are engine-specific and quoted AS STORED. Row 56's ZERO still ATTACHES the funding rate for the signal but declares `funding_signal: true`, `funding_charged: false` and zero settlements.

## Book by book

Each line quotes its own artifacts, with run_ids on the line.

**P08 Keltner breakout — ETHUSDT 1h.** Base net 114.98% at PF 1.169 on 522 trades; zero net 287.92% at PF 1.295 on 522 trades (`9258472c05579db5`, `50268b8b42f8b857`). Its own `zero_cost_pf` reads 1.2911 and `funding_paid` reads -314.4293, `9258472c05579db5`. A new additive `vrun.py` switch was audited for this cell before the run; the old ranking artifact predates the 2026-11-21 audit-fix and now fails `verify` on engine-hash drift, so the matching figure is a reproduction under current bytes.

**QS-009 Volatility-adjusted momentum — SUIUSDT 1h.** Base net 26.63% at PF 1.137 on 363 trades; zero net 54.15% at PF 1.232 on 364 trades (`9f34c460644e7fc1`, `c0760989624cde8d`). Its base run's `funding_paid` reads 92.86 over 1138 settlement events (positive means paid), `9f34c460644e7fc1`. The base figure matches the published one exactly, although the old ranking artifact's engine bytes drifted in the audit-fix campaign. Its trade count differs by one between regimes (below).

On this cell the trade count changes with the cost regime — 363 on the base run `9f34c460644e7fc1` versus 364 on the zero run `c0760989624cde8d` — because the catalog's equity-dependent risk devices (daily-loss halt, drawdown halving and halt) are part of the strategy and react to the changed equity path. No signal rule was changed.

**S10 Vol-Targeted Time-Series Momentum — SUIUSDT 1h.** Base net 12.99% at PF 1.133 on 167 trades; zero net 19.11% at PF 1.198 on 167 trades (`4705d6f88c3d7b5f`, `5228fb785c9a334e`). Its S10 row's `funding_paid_pct` reads 0.6434 and `funding_drag_pp` reads -0.7202, `4705d6f88c3d7b5f`. This row reuses the SUI `cbpackf` artifacts minted for the previous batch: same adapter, symbol, params, engine bytes and cut. The ranking row is a different strategy (S10, not S02) read out of them.

**S10 Vol-Targeted Time-Series Momentum — HYPEUSDT 1h.** Base net 9.30% at PF 1.130 on 121 trades; zero net 13.59% at PF 1.193 on 121 trades (`c7b3795cd19f22b2`, `5d377f62df2be150`). Its S10 row's `funding_paid_pct` reads 0.4222 and `funding_drag_pp` reads -0.4312, `c7b3795cd19f22b2`. The engine's own funding drag for S10 is measured inside the base artifact; the zero run removes both that cash flow and the fee.

**QS-006 ADX-filtered directional continuation — ETHUSDT 1h.** Base net 11.18% at PF 1.127 on 293 trades; zero net 28.77% at PF 1.302 on 292 trades (`10ab97da5d782c39`, `ce371a0bc5f65615`). Its base run's `funding_paid` reads 41.11 over 817 settlement events (positive means paid), `10ab97da5d782c39`. The base figure matches the published one exactly under current engine bytes; its trade count differs by one (below).

On this cell the trade count changes with the cost regime — 293 on the base run `10ab97da5d782c39` versus 292 on the zero run `ce371a0bc5f65615` — because the catalog's equity-dependent risk devices (daily-loss halt, drawdown halving and halt) are part of the strategy and react to the changed equity path. No signal rule was changed.

**S07 Funding Extreme Fade — ETHUSDT 1h.** Base net 2.71% at PF 1.126 on 34 trades; zero net 4.60% at PF 1.225 on 34 trades (`3263ad328e60a1eb`, `b1a2c9c0e325a6c9`). Its S07 row's `funding_paid_pct` reads -0.1224 and `funding_drag_pp` reads 0.1265, `3263ad328e60a1eb`. THE FUNDING-SIGNAL CASE. S07's signal READS the attached funding rate column, so simply withholding the JSON at ZERO made it stop trading altogether. The ZERO run keeps that column for the signal and sets `charge_funding=False`, so 34 trades occur in both regimes and only the money changes. This was found by the audit and declared in a dated addendum to the pre-registration.

**C44-1h fractal breakout — ETHUSDT 1h.** Base net 29.25% at PF 1.126 on 381 trades; zero net 103.40% at PF 1.218 on 381 trades (`d2546b98f9d9ce7a`, `2a5af8f7aed9ac76`). Its own `zero_cost_pf` reads 1.2103 (fees removed with funding still charged), `d2546b98f9d9ce7a`. A breakout book at the repo cost point. The old ranking artifact predates the audit-fix campaign and now fails `verify` on engine hash drift; both columns here are on current bytes.

**ds3 — SOLUSDT 1h.** Base net 4466.84% at PF 1.125 on 286 trades; zero net 8483.28% at PF 1.169 on 286 trades (`8a0e44e2ffefff86`, `85401329ff6193c9`). The one row PUBLISHED with a real cost block (`repo6x5`): BASE is that published regime and ZERO is the engine's `author` preset. The kline file grew since the ranking, so the base figure is a re-measurement. The engine's own zero re-score and the author headline coincide.

**QS-003 Supertrend continuation — SOLUSDT 1h.** Base net 15.62% at PF 1.124 on 340 trades; zero net 32.92% at PF 1.232 on 340 trades (`0d908e3b1a540201`, `3829df669e17a50b`). Its base run's `funding_paid` reads 119.34 over 1667 settlement events (positive means paid), `0d908e3b1a540201`. The base figure matches the published one exactly under current engine bytes.

**MP-V3-S10 Pure Equal Weight Momentum — PORTFOLIO 1h.** Base net 1098.37% at PF 1.119 on 317 trades; zero net 1230.74% at PF 1.128 on 317 trades (`fabe6ed1e63d66cf`, `4219f0cd0da94225`). Its own `cost_drag_pp` reads 132.3742 percentage points and `fees_paid` reads 97131.70, `fabe6ed1e63d66cf`. The only portfolio book of the five-batch control. Its kline inputs grew since the ranking, but the base figure matches the published one exactly; the engine's own cost drag is measured inside the artifact.

## What the numbers say

Three readings, none of them a verdict:

1. **The old ranking artifacts of `pack50d`, `pack100` and the `qs` rows no longer verify: the 2026-11-21 audit-fix changed their engine bytes.** That is a provenance fact, not tampering. Every artifact in this report was minted on current bytes and verifies; where a BASE figure matches the old published one, the audit calls it an exact *figure* reproduction, not a bit-identical artifact.
2. **Removing the funding JSON is not safe for a strategy whose signal reads funding.** S07's first ZERO attempt produced no trades at all; the pre-registered addendum added a signal-only funding path, and the correct ZERO run keeps the same 34 trades at a higher net line (both run_ids are cited on row 56).
3. **All ten books rise at ZERO, but the mechanism differs.** ds3's costed-to-author gap is the largest in the five batches; the portfolio book's own measured drag is cited on row 60; and two `qs` cells change trade count through the catalog's own risk devices (declared above).

## What this is not

- It is not a resurrection of any killed strategy. The kill list is unchanged; these rows carry the verdicts of their own campaigns (the strategy packs, the QS catalog, the DeepSeek pack and MP-V3).
- It is not evidence of alpha. A zero-cost line is the upper bound of what a book could earn if execution were free; nobody trades for free.
- It is not a gate pass. No gate was evaluated here.
- It is not agent- or user-selected: the ten are published ranking rows 51 to 60, decided before this campaign existed.

## Limits and declared caveats

- **Funding is a real cash flow, not a fee.** ZERO removes the cash flow because the user asked for all costs removed; for a perp that is a declared control, never a tradable result. Row 56 keeps the funding column only as a signal input, never as money.
- **The `qs` ZERO regime zeroes the whole ladder including the random-entry null**, so its internal null comparison is zero-cost against zero-cost — consistent, but not the published null regime.
- **Execution was not relaxed.** Signal on the closed bar, fill modes, stop-first ties, sizing and risk devices all stay. Only the cost block and the screening rules were removed.
- **A re-measurement is not a contradiction.** Where an input file grew or an engine changed since the ranking, both columns were minted on the same frozen cut and current engine bytes; the audit records which figures reproduced exactly.

## Provenance

- Pre-registration: `results/zerocost_rows51_60_pre_registration.md` with its dated addendum (both written before the market artifacts).
- Matrix: `results/zerocost_rows51_60_matrix.json` (per-cell run_ids, params, cut and inputs).
- Verification log: `results/_zerocost_rows51_60_verify.txt` — twenty artifacts, twenty OK.
- Audit: `code/_zerocost_rows51_60_audit.py` — independent fresh-module recomputation for `pack50d`, `qs`, `pack100`, `dspack` and `mpv3`, declared fields and determinism for `cbpackf`, and the pre-registered reproduction semantics with engine drift stated explicitly.
- Harness changes: one additive `pack50d` costs/funding switch and one additive `cbpackf` `funding_signal` option, both in `vrun.py`, both restoring module state in `finally`. Engine files are byte-untouched and hashed into every run_id.

