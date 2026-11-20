# Zero cost, no rules — rows 21-30 of the hundred best books re-run

Date: 2026-11-20. Status: **experiment / control**. This report contains no verdict, no gate and no alpha claim (see `results/zerocost_rows21_30_pre_registration.md`, with its dated addendum). It is the third batch of the same control as `results/zerocost_report_2026-11-20.md` (rows 1-10) and `results/zerocost_rows11_20_report_2026-11-20.md` (rows 11-20).

## The question

Ten more books were taken from `results/top100_2026-10-31.md` — rows 21 to 30, in the order that list already published — and each was run twice on the same frozen data cut by the same engine bytes: once under the cost regime it was published under (**BASE**) and once with fees, slippage and funding cash flow all at zero (**ZERO**). The gates that decide whether a book is good are not applied here. One row is the mirror case and gets a third artifact: ds1 was PUBLISHED at zero cost (the pack declares no costs and the engine charges no funding), so its BASE and ZERO are the same artifact by construction, and the informative run for it is the **COSTED** re-run under the engine's own repo6x5 preset.

Ten books produced twenty artifacts (ten cells in two regimes, with row 27's BASE and ZERO sharing one artifact, plus its costed re-run), and every one of them verifies bit-for-bit (`results/_zerocost_rows21_30_verify.txt`).

## The ten, both regimes

Every row is one stored artifact; the run_id is on its own row. Net % is the book's own net return over its full window, PF its profit factor, Trades its closed-trade count and Max DD % the drawdown exactly as the engine stores it (negative where the engine reports a signed drawdown). Row 27 also shows its costed re-run in the prose below.

| Book | Market | Regime | Net % | PF | Trades | Max DD % | run_id |
|---|---|---|---:|---:|---:|---:|---|
| B17-1h EMA 20/50 trend + EMA200 filter (long) | HYPEUSDT 1h | BASE | 53.73 | 1.381 | 77 | 37.46 | `63fbbc00ea9d7166` |
| B17-1h EMA 20/50 trend + EMA200 filter (long) | HYPEUSDT 1h | ZERO | 74.15 | 1.473 | 77 | 36.74 | `aad389671aaf3115` |
| F75-1h equal-highs liquidity grab (short) | SUIUSDT 1h | BASE | 11.66 | 1.352 | 50 | 8.25 | `4797da9e4c7a5b96` |
| F75-1h equal-highs liquidity grab (short) | SUIUSDT 1h | ZERO | 17.85 | 1.558 | 50 | 7.93 | `d6c388d65446d6f2` |
| QS-004 Donchian channel breakout | SUIUSDT 1h | BASE | 23.08 | 1.335 | 197 | -16.20 | `5096daf5413eaf84` |
| QS-004 Donchian channel breakout | SUIUSDT 1h | ZERO | 32.79 | 1.452 | 197 | -15.96 | `f6605276d0aa686f` |
| S46 weekend-gap fade | BTCUSDT 1h | BASE | 26.68 | 1.303 | 60 | 30.16 | `557abfbc4c160f45` |
| S46 weekend-gap fade | BTCUSDT 1h | ZERO | 36.13 | 1.411 | 60 | 28.33 | `34903e14ed65eec3` |
| QS-007 Higher-timeframe trend, lower-timeframe entries | HYPEUSDT 1h | BASE | 14.02 | 1.292 | 74 | -11.14 | `5b700837602aca31` |
| QS-007 Higher-timeframe trend, lower-timeframe entries | HYPEUSDT 1h | ZERO | 20.09 | 1.388 | 75 | -10.67 | `1eef58cfca0b933f` |
| QS-005 Time-series momentum | SUIUSDT 1h | BASE | 15.77 | 1.274 | 143 | -18.74 | `1cf1fe02511ea3cb` |
| QS-005 Time-series momentum | SUIUSDT 1h | ZERO | 22.29 | 1.367 | 143 | -18.86 | `014002cdf20e2aa1` |
| ds1 | XRPUSDT 1h | BASE | 401.67 | 1.267 | 2046 | -29.83 | `53e8e605331e875e` |
| ds1 | XRPUSDT 1h | ZERO | 401.67 | 1.267 | 2046 | -29.83 | `53e8e605331e875e` |
| QS-004 Donchian channel breakout | ETHUSDT 1h | BASE | 34.65 | 1.262 | 199 | -18.31 | `8654067601659418` |
| QS-004 Donchian channel breakout | ETHUSDT 1h | ZERO | 56.31 | 1.373 | 199 | -17.16 | `d504de1ef687ba01` |
| QS-006 ADX-filtered directional continuation | SOLUSDT 1h | BASE | 30.70 | 1.248 | 279 | -16.48 | `7b036f61b1193cb5` |
| QS-006 ADX-filtered directional continuation | SOLUSDT 1h | ZERO | 60.21 | 1.379 | 279 | -16.11 | `88b366e2e7b1add9` |
| QS-093 VWAP plus trade-flow confluence | JUPUSDT 1h | BASE | 5.82 | 1.252 | 95 | -6.30 | `d571f378484bb7d2` |
| QS-093 VWAP plus trade-flow confluence | JUPUSDT 1h | ZERO | 12.64 | 1.591 | 95 | -5.39 | `3329b4466ab7b15b` |

## What each regime actually charged

These are the artifacts' own declared cost fields, not a description of them: the adapter's fee and slippage fields, and `funding_charged`. The `qs` and `qsf` adapters declare the catalog ladder's base point (fee plus slippage per side); `pack100` declares one combined per-side figure; `pack50` declares the pack's per-symbol block from the engine's own cost table; `dspack` was published at the pack's own `author` regime — the pack file declares no costs — and its costed re-run carries the engine's `repo6x5` preset name in its params.

| Adapter | Market | Base fee bps | Base slip bps | Base funding | Zero fee bps | Zero slip bps | Zero funding | run_ids |
|---|---|---:|---:|---|---:|---:|---|---|
| `pack100` | HYPEUSDT 1h | 5.5 combined | n/a | True | 0 combined | n/a | False | `63fbbc00ea9d7166` `aad389671aaf3115` |
| `pack100` | SUIUSDT 1h | 5.5 combined | n/a | True | 0 combined | n/a | False | `4797da9e4c7a5b96` `d6c388d65446d6f2` |
| `qs` | SUIUSDT 1h | 5 | 2 | True | 0 | 0 | False | `5096daf5413eaf84` `f6605276d0aa686f` |
| `pack50` | BTCUSDT 1h | 4 | 2 | True | 0 | 0 | False | `557abfbc4c160f45` `34903e14ed65eec3` |
| `qs` | HYPEUSDT 1h | 5 | 2 | True | 0 | 0 | False | `5b700837602aca31` `1eef58cfca0b933f` |
| `qs` | SUIUSDT 1h | 5 | 2 | True | 0 | 0 | False | `1cf1fe02511ea3cb` `014002cdf20e2aa1` |
| `dspack` | XRPUSDT 1h | 0 (author) | 0 (author) | None | 0 (author) | 0 (author) | None | `53e8e605331e875e` `53e8e605331e875e` |
| `qs` | ETHUSDT 1h | 5 | 2 | True | 0 | 0 | False | `8654067601659418` `d504de1ef687ba01` |
| `qs` | SOLUSDT 1h | 5 | 2 | True | 0 | 0 | False | `7b036f61b1193cb5` `88b366e2e7b1add9` |
| `qsf` | JUPUSDT 1h | 5 | 2 | True | 0 | 0 | False | `d571f378484bb7d2` `3329b4466ab7b15b` |

The `dspack` engine charges no funding (kline-only, the pack declares none), and `pack50`'s `funding_charged` field is the ENGINE'S OWN flag on whether a funding file was handed to it. Funding sign conventions differ by engine and are quoted AS STORED in the book-by-book section: `qs`/`qsf` and `pack50` `funding_paid` positive means paid, `pack100` `funding_paid` negative means paid.

## Book by book

Numbers below are quoted from the artifacts in the table above; where a book is named, its run_ids are cited on the line.

**B17-1h EMA 20/50 trend + EMA200 filter (long) — HYPEUSDT 1h.** Base net 53.73% at PF 1.381 on 77 trades; zero net 74.15% at PF 1.473 on 77 trades (`63fbbc00ea9d7166`, `aad389671aaf3115`). Its base run's `funding_paid` reads -515.96 (negative means paid) and the engine's own zero-fee reference `zero_cost_pf` reads 1.4441. Long-only EMA trend on the most crowded perp in the list: its base run PAID a large funding bill (negative means paid under the pack100 convention) on top of the combined per-side cost, and the engine's own zero-fee reference (`zero_cost_pf`, fees removed with funding still charged) already sits between the base and zero profit factors. The base run reproduces the published figure to full float precision.

**F75-1h equal-highs liquidity grab (short) — SUIUSDT 1h.** Base net 11.66% at PF 1.352 on 50 trades; zero net 17.85% at PF 1.558 on 50 trades (`4797da9e4c7a5b96`, `d6c388d65446d6f2`). Its base run's `funding_paid` reads 9.00 (negative means paid) and the engine's own zero-fee reference `zero_cost_pf` reads 1.5607. The short liquidity-grab book was on the RECEIVING side of funding (positive funding_paid here means the book received), so removing funding moves it the other way from its long-only sibling in row 21 — but removing it still nets higher at zero because the fee block dominates. The base run reproduces the published figure exactly.

**QS-004 Donchian channel breakout — SUIUSDT 1h.** Base net 23.08% at PF 1.335 on 197 trades; zero net 32.79% at PF 1.452 on 197 trades (`5096daf5413eaf84`, `f6605276d0aa686f`). Its base run's `funding_paid` reads 45.52 over 860 settlement events (positive means paid). The catalog battery collapses to a single point at zero (base, adverse and gate cost views all return the same number), the batch 2 consistency check. The base run reproduces the published figure exactly.

**S46 weekend-gap fade — BTCUSDT 1h.** Base net 26.68% at PF 1.303 on 60 trades; zero net 36.13% at PF 1.411 on 60 trades (`557abfbc4c160f45`, `34903e14ed65eec3`). Its base run's `funding_paid` reads -0.3682 (positive means paid) and its own `zero_cost_pf` reads 1.4110. The engine's own zero-fee control (`zero_cost_pf`, fees removed with funding still charged) sits at the ZERO profit factor almost exactly, because the book's net funding bill over the window was a few tenths of a USDT. The base run reproduces the published figure exactly.

**QS-007 Higher-timeframe trend, lower-timeframe entries — HYPEUSDT 1h.** Base net 14.02% at PF 1.292 on 74 trades; zero net 20.09% at PF 1.388 on 75 trades (`5b700837602aca31`, `1eef58cfca0b933f`). Its base run's `funding_paid` reads 67.39 over 744 settlement events (positive means paid). The base run reproduces the published figure exactly.

**QS-005 Time-series momentum — SUIUSDT 1h.** Base net 15.77% at PF 1.274 on 143 trades; zero net 22.29% at PF 1.367 on 143 trades (`1cf1fe02511ea3cb`, `014002cdf20e2aa1`). Its base run's `funding_paid` reads 33.37 over 810 settlement events (positive means paid). The base run reproduces the published figure exactly.

**ds1 — XRPUSDT 1h.** Base net 401.67% at PF 1.267 on 2046 trades; zero net 401.67% at PF 1.267 on 2046 trades (`53e8e605331e875e`; costed `02c320f022499a4a`). THE MIRROR CASE OF THE WHOLE CAMPAIGN. The pack file declares no costs and the engine charges no funding, so the published number was measured at zero cost from day one — its BASE and ZERO are the same artifact. The COSTED re-run under the engine's own repo6x5 preset keeps the identical signal sequence (same trade count) and lands at 8.04 percent net at PF 1.006, paying 198500.76 USDT of fees on the same 2046 trades; the engine's own measured drag is 393.6255 points and its in-artifact zero-cost re-score (`ret_zero_pct`) equals the author headline to the last digit. The published figure was a cost-zero construction; this row is the quantified version of that fact. Its input klines grew since the ranking, so both lines here are re-measurements (401.67 vs the published 390.62, `437c47539b4dc9ae`).

**QS-004 Donchian channel breakout — ETHUSDT 1h.** Base net 34.65% at PF 1.262 on 199 trades; zero net 56.31% at PF 1.373 on 199 trades (`8654067601659418`, `d504de1ef687ba01`). Its base run's `funding_paid` reads 113.83 over 811 settlement events (positive means paid). The base run reproduces the published figure exactly; the zero line sits well above it, the ladder and funding were a heavy drag on this Donchian book.

**QS-006 ADX-filtered directional continuation — SOLUSDT 1h.** Base net 30.70% at PF 1.248 on 279 trades; zero net 60.21% at PF 1.379 on 279 trades (`7b036f61b1193cb5`, `88b366e2e7b1add9`). Its base run's `funding_paid` reads 176.18 over 841 settlement events (positive means paid). The biggest relative mover of the batch: the zero line is roughly double the base line. The base run reproduces the published figure exactly.

**QS-093 VWAP plus trade-flow confluence — JUPUSDT 1h.** Base net 5.82% at PF 1.252 on 95 trades; zero net 12.64% at PF 1.591 on 95 trades (`d571f378484bb7d2`, `3329b4466ab7b15b`). Its base run's `funding_paid` reads 8.30 over 136 settlement events (positive means paid). The trade-flow confluence book is one of the two true re-measurements (JUP klines and funding grew since the ranking, and the trade count differs from the published row). Its base run PAID net funding (positive means paid).

## What the numbers say

Three readings, none of them a verdict:

1. **Eight of the ten published BASE figures reproduce exactly, and the two that do not sit on inputs that really grew.** The grown inputs on the reproducing rows are funding tail records only, and the bit-exact equity paths prove those records never touch an open position. The reproducing rows cite their base run_ids in the table above. The ranking's top-30 is solid ground, not a moving target.
2. **ds1 is the mirror that shows what the ranking would look like if every book had been published at zero cost.** Its costed re-run keeps the same trade count and lands at 8.04 percent at PF 1.006 with 198500.76 USDT of fees (run_id cited on the row 27 line above) — the sort of gap the repo's cost regime produced across the whole historical corpus. A zero-cost line is the upper bound of what a book could earn if execution were free; ds1 is the only row in the three batches that was PUBLISHED on that bound.
3. **The catalog ladder was the heaviest drag in this batch, and the funding sign does not transfer between books.** QS-006 SOL rises from 30.70 to 60.21 and QS-004 ETH from 34.65 to 56.31 at zero (their four run_ids are on the table lines above); meanwhile row 21's long-only book PAID a large funding bill and row 22's short book RECEIVED net funding. Same list, opposite funding signs, book by book.

## What this is not

- It is not a resurrection of any killed strategy. The kill list is unchanged and this report adds nothing to it. QS-004, QS-005, QS-006, QS-007 and QS-093 carry killed verdicts from their own campaigns (zero of ten families, one PARTIAL TK), S46 from the fifty-prompt pack (zero of forty-eight), B17-1h and F75-1h from the prompts-100 screen (zero pass as risk-specified), and ds1 from the five-strategy DeepSeek pack.
- It is not evidence of alpha. A zero-cost line is the upper bound of what a book could earn if execution were free; nobody trades for free.
- It is not a gate pass. No gate was evaluated, and the words PASS and FAIL do not appear in this report's tables.
- It is not agent- or user-selected: the ten are published ranking rows 21 to 30, decided before this campaign existed.

## Limits and declared caveats

- **ds1's published number was never a costed number.** The pack file declares no costs and the engine charges no funding, so the ranking row was a zero-cost construction from the start; this campaign did not discover that, it quantified it inside an artifact. The costed re-run uses the engine's own repo6x5 preset; no gate is evaluated on it.
- **Funding is a real cash flow, not a fee.** The ZERO regime removes it because the user asked for all costs removed; for a perp that is a declared control, never a tradable result. The base column keeps it.
- **The qs and qsf ZERO regime zeroes the whole ladder including the random-entry null**, so the null comparison inside those artifacts is a zero-cost null against a zero-cost book — consistent, but not the published null regime.
- **Execution was not relaxed.** Signal on the closed bar, the engines' own fill modes, stop-first on ties, the engines' own sizing and risk devices all stay. Only the cost block and the screening rules were removed.

## Provenance

- Pre-registration: `results/zerocost_rows21_30_pre_registration.md` (written before the first artifact existed, with a dated addendum on the reproduction-check semantics).
- Matrix: `results/zerocost_rows21_30_matrix.json` (per-cell run_ids, params, cut and inputs, plus row 27's costed run).
- Verification log: `results/_zerocost_rows21_30_verify.txt` — twenty artifacts, twenty OK.
- Audit: `code/_zerocost_rows21_30_audit.py` — every adapter checked against an independent fresh-module recomputation, the engines' own published zero-cost references (`zero_cost_pf` for pack100 and pack50, `ret_zero_pct` for dspack), and the reproduction logic declared in the addendum (equality is exact reproduction; inequality requires a grown input file).
- Harness switches added for this batch: the batch 2 qs switch replicated on `qsf`, and a new costs and funding switch on `pack50`; `pack100` kept its batch 1 switches and `dspack` already exposed its costs key natively. The engine files are byte-untouched (they are hashed into every run_id); absent the keys every runner behaves exactly as before, and the batch 1 SPX artifact was re-verified after the edits to prove it.

