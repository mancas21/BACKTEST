# Zero cost, no rules — this batch of the hundred best books re-run

Date: 2026-11-23. Status: **experiment / control**. No verdict, no gate and no alpha claim (see `results/zerocost_rows61_70_pre_registration.md`, written before the first artifact). Seventh batch of the control begun in `results/zerocost_report_2026-11-20.md` and continued in the six reports that followed it.

## The question

Ten books were taken from `results/top100_2026-10-31.md` — the next ten rows, in the order that list already published — and each was run twice on the same frozen cut by the same engine bytes: once under its published cost regime (**BASE**) and once with fees, slippage and funding cash flow at zero (**ZERO**). No screening gate is applied. ds5 was published at zero cost (`author`, no funding), so its BASE and ZERO are one artifact and its informative run is the **COSTED** re-run.

Ten books produced eighteen artifacts — two BASE/ZERO pairs are shared by construction and reused from the previous batch — every one verifying bit-for-bit (`results/_zerocost_rows61_70_verify.txt`).

## The ten, both regimes

Every row is one stored artifact; the run_id is on its own row. Net % is the book's own full-window return, PF its profit factor, Trades its closed-trade count and Max DD % the drawdown exactly as the engine stores it (negative where the engine reports a signed drawdown).

| Book | Market | Regime | Net % | PF | Trades | Max DD % | run_id |
|---|---|---|---:|---:|---:|---:|---|
| QS-003 Supertrend continuation | JUPUSDT 1h | BASE | 20.21 | 1.122 | 324 | -16.11 | `36e2436ee0219dfe` |
| QS-003 Supertrend continuation | JUPUSDT 1h | ZERO | 35.03 | 1.199 | 324 | -15.52 | `4d53d6a930b924f4` |
| S02 Donchian + Flow Breakout | HYPEUSDT 1h | BASE | 11.96 | 1.109 | 177 | -16.58 | `c7b3795cd19f22b2` |
| S02 Donchian + Flow Breakout | HYPEUSDT 1h | ZERO | 21.11 | 1.195 | 177 | -15.75 | `5d377f62df2be150` |
| ds7 | SPXUSDT 1h | BASE | 44.97 | 1.108 | 296 | -45.98 | `9797f6da79168cbb` |
| ds7 | SPXUSDT 1h | ZERO | 178.13 | 1.316 | 296 | -36.45 | `4033d47849c78897` |
| QS-002 EMA alignment with volatility confirmation | JUPUSDT 1h | BASE | 10.19 | 1.102 | 242 | -20.06 | `d33662311f508bdc` |
| QS-002 EMA alignment with volatility confirmation | JUPUSDT 1h | ZERO | 19.91 | 1.184 | 241 | -18.69 | `5740a5c4b14e7bd9` |
| QS-001 Moving-average trend continuation (long-only) | SOLUSDT 15m | BASE | 9.51 | 1.103 | 206 | -25.04 | `4f0c5814f5c1d018` |
| QS-001 Moving-average trend continuation (long-only) | SOLUSDT 15m | ZERO | 43.65 | 1.286 | 203 | -25.05 | `6cef67892f5c1402` |
| ds5 | LINKUSDT 1h | BASE | 52.62 | 1.104 | 1250 | -62.82 | `c1ec7a0f073f25f8` |
| ds5 | LINKUSDT 1h | ZERO | 52.62 | 1.104 | 1250 | -62.82 | `c1ec7a0f073f25f8` |
| QS-001 Moving-average trend continuation | JUPUSDT 1h | BASE | 5.28 | 1.090 | 117 | -17.74 | `7a23c8a869c3c794` |
| QS-001 Moving-average trend continuation | JUPUSDT 1h | ZERO | 9.89 | 1.154 | 117 | -17.08 | `ab0fe922464903c6` |
| F75-15m equal-highs liquidity grab (short) | SUIUSDT 15m | BASE | 11.90 | 1.094 | 388 | 16.59 | `e4a46c300ee2e982` |
| F75-15m equal-highs liquidity grab (short) | SUIUSDT 15m | ZERO | 70.92 | 1.482 | 388 | 8.41 | `4951f4ee7bee5e40` |
| S03 Squeeze Release | HYPEUSDT 1h | BASE | 7.14 | 1.092 | 111 | -18.52 | `c7b3795cd19f22b2` |
| S03 Squeeze Release | HYPEUSDT 1h | ZERO | 13.89 | 1.183 | 111 | -15.46 | `5d377f62df2be150` |
| QS-004 Donchian channel breakout | JUPUSDT 1h | BASE | 8.83 | 1.100 | 216 | -18.51 | `4987260da0fe865f` |
| QS-004 Donchian channel breakout | JUPUSDT 1h | ZERO | 16.85 | 1.170 | 215 | -16.75 | `b29726f28a5c0b9e` |

## What each regime actually charged

Fields below are the artifacts' own declarations: the catalog base point, the `cbpackf` and `pack100` per-side/combined cost blocks with their funding flags, and the `dspack`/`dspack2` preset names.

| Adapter | Market | Base fee | Base slip | Base funding | Zero fee | Zero slip | Zero funding | run_ids |
|---|---|---|---|---|---|---|---|---|
| `qs` | JUPUSDT 1h | 5 | 2 | True | 0 | 0 | False | `36e2436ee0219dfe` `4d53d6a930b924f4` |
| `cbpackf` | HYPEUSDT 1h | 5 | 0.5 | True | 0 | 0 | False | `c7b3795cd19f22b2` `5d377f62df2be150` |
| `dspack2` | SPXUSDT 1h | repo6x5 | in preset | n/a (kline-only) | author | in preset | n/a (kline-only) | `9797f6da79168cbb` `4033d47849c78897` |
| `qs` | JUPUSDT 1h | 5 | 2 | True | 0 | 0 | False | `d33662311f508bdc` `5740a5c4b14e7bd9` |
| `qs` | SOLUSDT 15m | 5 | 2 | True | 0 | 0 | False | `4f0c5814f5c1d018` `6cef67892f5c1402` |
| `dspack` | LINKUSDT 1h | author | in preset | n/a (kline-only) | author | in preset | n/a (kline-only) | `c1ec7a0f073f25f8` `c1ec7a0f073f25f8` |
| `qs` | JUPUSDT 1h | 5 | 2 | True | 0 | 0 | False | `7a23c8a869c3c794` `ab0fe922464903c6` |
| `pack100` | SUIUSDT 15m | 5.5 combined | n/a | True | 0 combined | n/a | False | `e4a46c300ee2e982` `4951f4ee7bee5e40` |
| `cbpackf` | HYPEUSDT 1h | 5 | 0.5 | True | 0 | 0 | False | `c7b3795cd19f22b2` `5d377f62df2be150` |
| `qs` | JUPUSDT 1h | 5 | 2 | True | 0 | 0 | False | `4987260da0fe865f` `b29726f28a5c0b9e` |

## Book by book

Each line quotes its own artifacts, with run_ids on the line.

**QS-003 Supertrend continuation — JUPUSDT 1h.** Base net 20.21% at PF 1.122 on 324 trades; zero net 35.03% at PF 1.199 on 324 trades (`36e2436ee0219dfe`, `4d53d6a930b924f4`). Its base run's `funding_paid` reads 36.41 over 3484 settlement events (positive means paid), `36e2436ee0219dfe`. The base figure reproduces the published one exactly under current engine bytes despite the old ranking artifact's engine drift.

**S02 Donchian + Flow Breakout — HYPEUSDT 1h.** Base net 11.96% at PF 1.109 on 177 trades; zero net 21.11% at PF 1.195 on 177 trades (`c7b3795cd19f22b2`, `5d377f62df2be150`). Its S02 row's `funding_paid_pct` reads 0.4903 and `funding_drag_pp` reads -0.5490, `c7b3795cd19f22b2`. This row and the S03 row below read two different strategies out of the SAME `cbpackf` artifacts, reused from the previous batch (identical adapter, symbol, params, engine and cut).

**ds7 — SPXUSDT 1h.** Base net 44.97% at PF 1.108 on 296 trades; zero net 178.13% at PF 1.316 on 296 trades (`9797f6da79168cbb`, `4033d47849c78897`). The second pack's ds7 was published with a real cost block (`repo6x5`); ZERO is the same engine's `author` preset. The in-artifact zero re-score and the author headline coincide.

**QS-002 EMA alignment with volatility confirmation — JUPUSDT 1h.** Base net 10.19% at PF 1.102 on 242 trades; zero net 19.91% at PF 1.184 on 241 trades (`d33662311f508bdc`, `5740a5c4b14e7bd9`). Its base run's `funding_paid` reads 45.77 over 1720 settlement events (positive means paid), `d33662311f508bdc`. The base figure reproduces the published one exactly under current engine bytes; its trade count changes by one (below).

On this cell the trade count changes with the cost regime — 242 on the base run `d33662311f508bdc` versus 241 on the zero run `5740a5c4b14e7bd9` — because the catalog's equity-dependent risk devices (daily-loss halt, drawdown halving and halt) are part of the strategy and react to the changed equity path. No signal rule was changed.

**QS-001 Moving-average trend continuation (long-only) — SOLUSDT 15m.** Base net 9.51% at PF 1.103 on 206 trades; zero net 43.65% at PF 1.286 on 203 trades (`4f0c5814f5c1d018`, `6cef67892f5c1402`). Its base run's `funding_paid` reads 106.70 over 266 settlement events (positive means paid), `4f0c5814f5c1d018`. A fifteen-minute long-only cell. Both lines are re-measurements on grown inputs; its trade count changes with the regime (below).

On this cell the trade count changes with the cost regime — 206 on the base run `4f0c5814f5c1d018` versus 203 on the zero run `6cef67892f5c1402` — because the catalog's equity-dependent risk devices (daily-loss halt, drawdown halving and halt) are part of the strategy and react to the changed equity path. No signal rule was changed.

**ds5 — LINKUSDT 1h.** Base net 52.62% at PF 1.104 on 1250 trades; zero net 52.62% at PF 1.104 on 1250 trades (`c1ec7a0f073f25f8`; costed `3a681e6fa3e46f86`). THE MIRROR CASE. ds5 was published at `costs=author` — no costs, no funding — so BASE and ZERO are one artifact. The costed re-run keeps the same signals and pays real fees.

The costed re-run keeps 1250 trades and charges 63704.09 in fees, landing at -90.26% net at PF 0.5802; its in-artifact zero-cost re-score `ret_zero_pct` reads 52.6182 percent (`3a681e6fa3e46f86`).

**QS-001 Moving-average trend continuation — JUPUSDT 1h.** Base net 5.28% at PF 1.090 on 117 trades; zero net 9.89% at PF 1.154 on 117 trades (`7a23c8a869c3c794`, `ab0fe922464903c6`). Its base run's `funding_paid` reads 35.63 over 1345 settlement events (positive means paid), `7a23c8a869c3c794`. The base figure reproduces the published one exactly under current engine bytes.

**F75-15m equal-highs liquidity grab (short) — SUIUSDT 15m.** Base net 11.90% at PF 1.094 on 388 trades; zero net 70.92% at PF 1.482 on 388 trades (`e4a46c300ee2e982`, `4951f4ee7bee5e40`). Its own `zero_cost_pf` reads 1.4846 (fees removed with funding still charged), `e4a46c300ee2e982`. A 15m `pack100` cell; the old ranking artifact predates the audit-fix and now fails `verify` on engine drift, so both columns here are on current bytes.

**S03 Squeeze Release — HYPEUSDT 1h.** Base net 7.14% at PF 1.092 on 111 trades; zero net 13.89% at PF 1.183 on 111 trades (`c7b3795cd19f22b2`, `5d377f62df2be150`). Its S03 row's `funding_paid_pct` reads -0.0093 and `funding_drag_pp` reads -0.0011, `c7b3795cd19f22b2`. The S03 row of the shared HYPE `cbpackf` artifacts; the base figure reproduces the published one exactly.

**QS-004 Donchian channel breakout — JUPUSDT 1h.** Base net 8.83% at PF 1.100 on 216 trades; zero net 16.85% at PF 1.170 on 215 trades (`4987260da0fe865f`, `b29726f28a5c0b9e`). Its base run's `funding_paid` reads 62.61 over 1855 settlement events (positive means paid), `4987260da0fe865f`. The base figure reproduces the published one exactly under current engine bytes; its trade count changes by one (below).

On this cell the trade count changes with the cost regime — 216 on the base run `4987260da0fe865f` versus 215 on the zero run `b29726f28a5c0b9e` — because the catalog's equity-dependent risk devices (daily-loss halt, drawdown halving and halt) are part of the strategy and react to the changed equity path. No signal rule was changed.

## What the numbers say

Three readings, none of them a verdict:

1. **Old `qs` and `pack100` ranking artifacts no longer verify after the 2026-11-21 audit-fix changed their engine bytes.** That is a provenance fact, not tampering; all artifacts here are on current bytes and verify. Matching BASE figures are exact figure reproductions, not bit-identical artifacts.
2. **ds5 and ds7 are the two mirror images of the cost question.** ds5 was published at zero and pays dearly when charged; ds7 was published costed and nearly quadruples at zero (both pairs of run_ids are cited on their lines above). Neither line is an alpha claim.
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

- Pre-registration: `results/zerocost_rows61_70_pre_registration.md` (written before the first artifact existed).
- Matrix: `results/zerocost_rows61_70_matrix.json` (per-cell run_ids, params, cut and inputs, plus the costed re-run).
- Verification log: `results/_zerocost_rows61_70_verify.txt` — eighteen artifacts, eighteen OK.
- Audit: `code/_zerocost_rows61_70_audit.py` — independent fresh-module recomputation for every adapter, the engines' own in-artifact references and the pre-registered reproduction semantics with engine drift stated.
- No harness or engine file was edited for this batch; the engine files are byte-untouched and hashed into every run_id.

