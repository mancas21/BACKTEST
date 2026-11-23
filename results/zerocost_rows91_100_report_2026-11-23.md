# Zero cost, no rules — this batch of the hundred best books re-run

Date: 2026-11-23. Status: **experiment / control**. No verdict, no gate and no alpha claim (see `results/zerocost_rows91_100_pre_registration.md`, written before the first artifact). Tenth and final batch of the control begun in `results/zerocost_report_2026-11-20.md` and continued in the six reports that followed it.

## The question

Ten books were taken from `results/top100_2026-10-31.md` — rows 91 to 100, in the order that list already published — and each was run twice on the same frozen cut by the same engine bytes: once under its published cost regime (**BASE**) and once with fees, slippage and funding cash flow at zero (**ZERO**). No screening gate is applied. No row in this final batch was published at zero cost: every BASE is a costed regime (`repo6x5` for the DeepSeek books, the catalog ladder or the `cbpackf` block for the rest), and every ZERO removes it.

Ten books produced nineteen unique artifacts — one BASE/ZERO pair shares an artifact by construction — every one verifying bit-for-bit (`results/_zerocost_rows91_100_verify.txt`).

## The ten, both regimes

Every row is one stored artifact; the run_id is on its own row. Net % is the book's own full-window return, PF its profit factor, Trades its closed-trade count and Max DD % the drawdown exactly as the engine stores it (negative where the engine reports a signed drawdown).

| Book | Market | Regime | Net % | PF | Trades | Max DD % | run_id |
|---|---|---|---:|---:|---:|---:|---|
| S07 Funding Extreme Fade | SUIUSDT 1h | BASE | 0.99 | 1.036 | 40 | -9.75 | `4705d6f88c3d7b5f` |
| S07 Funding Extreme Fade | SUIUSDT 1h | ZERO | 2.27 | 1.085 | 40 | -9.07 | `595b81ffc1f6877c` |
| S09 Liquidity Sweep Reversal | SUIUSDT 1h | BASE | 3.70 | 1.028 | 210 | -12.53 | `4705d6f88c3d7b5f` |
| S09 Liquidity Sweep Reversal | SUIUSDT 1h | ZERO | 18.52 | 1.143 | 210 | -9.91 | `5228fb785c9a334e` |
| ds7 | DOGEUSDT 1h | BASE | 36.11 | 1.025 | 892 | -60.62 | `27d84442b993842b` |
| ds7 | DOGEUSDT 1h | ZERO | 869.64 | 1.218 | 892 | -38.87 | `66ce9aeb25348c43` |
| QS-002 EMA alignment with volatility confirmation | HYPEUSDT 1h | BASE | 1.40 | 1.026 | 155 | -15.88 | `c80c391c0cacccb1` |
| QS-002 EMA alignment with volatility confirmation | HYPEUSDT 1h | ZERO | 6.07 | 1.099 | 155 | -16.07 | `155a29cb11bf0336` |
| ds1 | NEARUSDT 1h | BASE | 19.38 | 1.028 | 1864 | -27.02 | `06bd4107e2284798` |
| ds1 | NEARUSDT 1h | ZERO | 210.06 | 1.233 | 1864 | -15.57 | `60563ed6cd83912f` |
| QS-044 Cumulative volume delta divergence | SOLUSDT 1h | BASE | 1.60 | 1.024 | 247 | -18.81 | `ca49b0b4b0012a08` |
| QS-044 Cumulative volume delta divergence | SOLUSDT 1h | ZERO | 21.87 | 1.318 | 247 | -16.60 | `9b05e75173045ed4` |
| ds1 | LINKUSDT 1h | BASE | 17.68 | 1.026 | 2011 | -35.19 | `8bcce39c0bc7913b` |
| ds1 | LINKUSDT 1h | ZERO | 289.50 | 1.282 | 2011 | -18.22 | `435ef5696202c77d` |
| ds7 | SOLUSDT 1h | BASE | 36.02 | 1.020 | 1111 | -68.00 | `f83612b4ce125c43` |
| ds7 | SOLUSDT 1h | ZERO | 1469.22 | 1.232 | 1111 | -33.00 | `1cefcebb085c9ff7` |
| ds7 | NEARUSDT 1h | BASE | 28.41 | 1.019 | 1024 | -62.54 | `ed368f3995c636af` |
| ds7 | NEARUSDT 1h | ZERO | 1123.27 | 1.213 | 1024 | -42.58 | `13d765e0040aac5a` |
| ds1 | SUIUSDT 1h | BASE | 6.02 | 1.010 | 1046 | -24.93 | `0fe18404d88b7fd2` |
| ds1 | SUIUSDT 1h | ZERO | 87.49 | 1.252 | 1046 | -20.39 | `c4102617ba6dd349` |

## What each regime actually charged

Fields below are the artifacts' own declarations: the catalog base point, the `cbpackf` and `pack100` per-side/combined cost blocks with their funding flags, and the `dspack`/`dspack2` preset names.

| Adapter | Market | Base fee | Base slip | Base funding | Zero fee | Zero slip | Zero funding | run_ids |
|---|---|---|---|---|---|---|---|---|
| `cbpackf` | SUIUSDT 1h | 5 | 0.5 | True | 0 | 0 | False | `4705d6f88c3d7b5f` `595b81ffc1f6877c` |
| `cbpackf` | SUIUSDT 1h | 5 | 0.5 | True | 0 | 0 | False | `4705d6f88c3d7b5f` `5228fb785c9a334e` |
| `dspack2` | DOGEUSDT 1h | repo6x5 | in preset | n/a (kline-only) | author | in preset | n/a (kline-only) | `27d84442b993842b` `66ce9aeb25348c43` |
| `qs` | HYPEUSDT 1h | 5 | 2 | True | 0 | 0 | False | `c80c391c0cacccb1` `155a29cb11bf0336` |
| `dspack` | NEARUSDT 1h | repo6x5 | in preset | n/a (kline-only) | author | in preset | n/a (kline-only) | `06bd4107e2284798` `60563ed6cd83912f` |
| `qsf` | SOLUSDT 1h | 5 | 2 | True | 0 | 0 | False | `ca49b0b4b0012a08` `9b05e75173045ed4` |
| `dspack` | LINKUSDT 1h | repo6x5 | in preset | n/a (kline-only) | author | in preset | n/a (kline-only) | `8bcce39c0bc7913b` `435ef5696202c77d` |
| `dspack2` | SOLUSDT 1h | repo6x5 | in preset | n/a (kline-only) | author | in preset | n/a (kline-only) | `f83612b4ce125c43` `1cefcebb085c9ff7` |
| `dspack2` | NEARUSDT 1h | repo6x5 | in preset | n/a (kline-only) | author | in preset | n/a (kline-only) | `ed368f3995c636af` `13d765e0040aac5a` |
| `dspack` | SUIUSDT 1h | repo6x5 | in preset | n/a (kline-only) | author | in preset | n/a (kline-only) | `0fe18404d88b7fd2` `c4102617ba6dd349` |

## Book by book

Each line quotes its own artifacts, with run_ids on the line.

**S07 Funding Extreme Fade — SUIUSDT 1h.** Base net 0.99% at PF 1.036 on 40 trades; zero net 2.27% at PF 1.085 on 40 trades (`4705d6f88c3d7b5f`, `595b81ffc1f6877c`). Its S07 row's `funding_paid_pct` reads -0.0240 and `funding_drag_pp` reads 0.0227, `4705d6f88c3d7b5f`. THE FUNDING-SIGNAL CASE AGAIN. S07 reads the attached funding column in its signal, so ZERO keeps that column for the signal and sets `charge_funding=False`: the trade count is identical in both regimes and only the cash flow changes. This path was audited and declared in an earlier batch's dated addendum.

**S09 Liquidity Sweep Reversal — SUIUSDT 1h.** Base net 3.70% at PF 1.028 on 210 trades; zero net 18.52% at PF 1.143 on 210 trades (`4705d6f88c3d7b5f`, `5228fb785c9a334e`). Its S09 row's `funding_paid_pct` reads -0.1697 and `funding_drag_pp` reads 0.1748, `4705d6f88c3d7b5f`. This row reuses the SUI `cbpackf` artifacts minted in earlier batches (same adapter, symbol, params, engine and cut); the ranking row is S09, read out of those artifacts.

**ds7 — DOGEUSDT 1h.** Base net 36.11% at PF 1.025 on 892 trades; zero net 869.64% at PF 1.218 on 892 trades (`27d84442b993842b`, `66ce9aeb25348c43`). The second pack's ds7 on DOGE was published at `repo6x5` (a real cost block); ZERO is the same engine's `author` preset.

**QS-002 EMA alignment with volatility confirmation — HYPEUSDT 1h.** Base net 1.40% at PF 1.026 on 155 trades; zero net 6.07% at PF 1.099 on 155 trades (`c80c391c0cacccb1`, `155a29cb11bf0336`). Its base run's `funding_paid` reads 15.99 over 1146 settlement events (positive means paid), `c80c391c0cacccb1`. The base figure reproduces the published one exactly under current engine bytes despite the old ranking artifact's engine drift.

**ds1 — NEARUSDT 1h.** Base net 19.38% at PF 1.028 on 1864 trades; zero net 210.06% at PF 1.233 on 1864 trades (`06bd4107e2284798`, `60563ed6cd83912f`). ds1 on NEAR was published at `repo6x5`; ZERO is `author`. The in-artifact zero re-score and the author headline coincide.

**QS-044 Cumulative volume delta divergence — SOLUSDT 1h.** Base net 1.60% at PF 1.024 on 247 trades; zero net 21.87% at PF 1.318 on 247 trades (`ca49b0b4b0012a08`, `9b05e75173045ed4`). A trade-flow strategy: the ranking artifact's provenance names adapter `qsf`, so the matrix uses the `qsf` adapter with the same cost/funding switches as `qs`. The whole ladder is zeroed at ZERO.

**ds1 — LINKUSDT 1h.** Base net 17.68% at PF 1.026 on 2011 trades; zero net 289.50% at PF 1.282 on 2011 trades (`8bcce39c0bc7913b`, `435ef5696202c77d`). ds1 on LINK was published at `repo6x5`; ZERO is `author`.

**ds7 — SOLUSDT 1h.** Base net 36.02% at PF 1.020 on 1111 trades; zero net 1469.22% at PF 1.232 on 1111 trades (`f83612b4ce125c43`, `1cefcebb085c9ff7`). ds7 on SOL was published at `repo6x5`; ZERO is `author`.

**ds7 — NEARUSDT 1h.** Base net 28.41% at PF 1.019 on 1024 trades; zero net 1123.27% at PF 1.213 on 1024 trades (`ed368f3995c636af`, `13d765e0040aac5a`). ds7 on NEAR was published at `repo6x5`; ZERO is `author`.

**ds1 — SUIUSDT 1h.** Base net 6.02% at PF 1.010 on 1046 trades; zero net 87.49% at PF 1.252 on 1046 trades (`0fe18404d88b7fd2`, `c4102617ba6dd349`). ds1 on SUI was published at `repo6x5`; ZERO is `author`. The kline file grew since the ranking, so the base figure is a re-measurement; the engine's own zero re-score still equals the author headline.

## What the numbers say

Three readings, none of them a verdict:

1. **Old `qs` and `pack100` ranking artifacts no longer verify after the 2026-11-21 audit-fix changed their engine bytes.** That is a provenance fact, not tampering; all artifacts here are on current bytes and verify. Matching BASE figures are exact figure reproductions, not bit-identical artifacts.
2. **S07 is the one cell where a naive zero run would have measured a different strategy.** Keeping the funding column as a signal input while stopping its cash flow preserved the trade count (run_ids are cited on their lines above). Neither line is an alpha claim.
3. **All ten books rise at ZERO, and three `qs` cells also change their trade count** through the catalog's own risk devices (declared above), so cost removal here can change which trades exist, not just their size.

## What this is not

- It is not a resurrection of any killed strategy; the kill list is unchanged and these rows carry the verdicts of their own campaigns.
- It is not evidence of alpha. A zero-cost line is the upper bound of what a book could earn if execution were free; nobody trades for free.
- It is not a gate pass. No gate was evaluated here.
- It is not agent- or user-selected: the ten are published ranking rows rows 91 to 100 of the published ranking, decided before this campaign existed.

## Limits and declared caveats

- **Funding is a real cash flow, not a fee.** ZERO removes it because the user asked for all costs removed; for a perp that is a declared control, never a tradable result.
- **The `qs` ZERO regime zeroes the whole ladder including the random entry null**, so its internal null comparison is zero-cost against zero-cost — consistent, but not the published null regime.
- **Execution was not relaxed.** Signal on the closed bar, fill modes, stop-first ties, sizing and risk devices all stay. Only the cost block and the screening rules were removed.
- **A re-measurement is not a contradiction.** Where an input file grew or an engine changed, both columns were minted on the same frozen cut and current engine bytes; the audit records which figures reproduced.

## Provenance

- Pre-registration: `results/zerocost_rows91_100_pre_registration.md` (written before the first artifact existed).
- Matrix: `results/zerocost_rows91_100_matrix.json` (per-cell run_ids, params, cut and inputs).
- Verification log: `results/_zerocost_rows91_100_verify.txt` — nineteen artifacts, nineteen OK.
- Audit: `code/_zerocost_rows91_100_audit.py` — independent fresh-module recomputation for every adapter, the engines' own in-artifact references and the pre-registered reproduction semantics with engine drift stated.
- No harness or engine file was edited for this batch; the engine files are byte-untouched and hashed into every run_id.

