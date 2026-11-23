# Zero cost, no rules — rows 31-40 of the hundred best books re-run

Date: 2026-11-23. Status: **experiment / control**. This report contains no verdict, no gate and no alpha claim (see `results/zerocost_rows31_40_pre_registration.md`, written before the first artifact). It is the fourth batch of the same control as `results/zerocost_report_2026-11-20.md` (rows 1-10), `results/zerocost_rows11_20_report_2026-11-20.md` (rows 11-20) and `results/zerocost_rows21_30_report_2026-11-20.md` (rows 21-30).

## The question

Ten more books were taken from `results/top100_2026-10-31.md` — rows 31 to 40, in the order that list already published — and each was run twice on the same frozen data cut by the same engine bytes: once under the cost regime it was published under (**BASE**) and once with fees, slippage and funding cash flow all at zero (**ZERO**). The gates that decide whether a book is good are not applied here. Two rows are the mirror case already met in row 27: ds1 was PUBLISHED at zero cost (the pack declares no costs and the engine charges no funding), so their BASE and ZERO are the same artifacts by construction, and each gets a **COSTED** re-run under the engine's own repo6x5 preset.

Ten books produced twenty artifacts (ten cells in two regimes, with two BASE/ZERO pairs sharing one artifact, plus two costed re-runs), and every one verifies bit-for-bit (`results/_zerocost_rows31_40_verify.txt`).

## The ten, both regimes

Every row is one stored artifact; the run_id is on its own row. Net % is the book's own net return over its full window, PF its profit factor, Trades its closed-trade count and Max DD % the drawdown exactly as the engine stores it (negative where the engine reports a signed drawdown). Rows 37 and 38 also show their costed re-runs in the prose below.

| Book | Market | Regime | Net % | PF | Trades | Max DD % | run_id |
|---|---|---|---:|---:|---:|---:|---|
| QS-009 Volatility-adjusted momentum | JUPUSDT 1h | BASE | 29.52 | 1.198 | 372 | -16.26 | `25401a76f62d4c70` |
| QS-009 Volatility-adjusted momentum | JUPUSDT 1h | ZERO | 54.01 | 1.279 | 372 | -16.45 | `d40e7af48a7b2b7c` |
| S10 Vol-Targeted Time-Series Momentum | ETHUSDT 1h | BASE | 26.16 | 1.224 | 181 | -15.74 | `3263ad328e60a1eb` |
| S10 Vol-Targeted Time-Series Momentum | ETHUSDT 1h | ZERO | 38.20 | 1.331 | 181 | -13.98 | `82e522ce0d3b6bfd` |
| rsimr | SOLUSDC 1h | BASE | 7.56 | 1.217 | 60 | -14.88 | `4f77139298564618` |
| rsimr | SOLUSDC 1h | ZERO | 11.49 | 1.324 | 60 | -14.03 | `112aff3a78f78d28` |
| QS-004 Donchian channel breakout | SOLUSDT 1h | BASE | 17.46 | 1.217 | 228 | -21.10 | `cfa58e85c5e5720f` |
| QS-004 Donchian channel breakout | SOLUSDT 1h | ZERO | 28.25 | 1.315 | 228 | -19.95 | `314e1dad56a74613` |
| QS-006 ADX-filtered directional continuation | SUIUSDT 1h | BASE | 22.79 | 1.207 | 283 | -18.11 | `129dcfd4cd09d10f` |
| QS-006 ADX-filtered directional continuation | SUIUSDT 1h | ZERO | 38.17 | 1.301 | 283 | -16.11 | `b62406519f892a25` |
| fingrad | ETHUSDT 1h | BASE | 58.99 | 1.203 | 788 | 19.03 | `875f35f807e816bd` |
| fingrad | ETHUSDT 1h | ZERO | 151.27 | 1.445 | 788 | 13.42 | `35be1d630baab789` |
| ds1 | BNBUSDT 1h | BASE | 224.04 | 1.190 | 2041 | -20.88 | `6b1cb73c9af1d390` |
| ds1 | BNBUSDT 1h | ZERO | 224.04 | 1.190 | 2041 | -20.88 | `6b1cb73c9af1d390` |
| ds1 | DOGEUSDT 1h | BASE | 205.42 | 1.186 | 1995 | -28.76 | `20f70bfad539bf29` |
| ds1 | DOGEUSDT 1h | ZERO | 205.42 | 1.186 | 1995 | -28.76 | `20f70bfad539bf29` |
| QS-006 ADX-filtered directional continuation | HYPEUSDT 1h | BASE | 19.82 | 1.196 | 194 | -14.03 | `87ddc432ee66e7cd` |
| QS-006 ADX-filtered directional continuation | HYPEUSDT 1h | ZERO | 34.55 | 1.324 | 194 | -13.77 | `4e4caba793b91376` |
| QS-005 Time-series momentum | ETHUSDT 1h | BASE | 15.67 | 1.195 | 141 | -21.20 | `15f291a37172c589` |
| QS-005 Time-series momentum | ETHUSDT 1h | ZERO | 29.49 | 1.330 | 140 | -20.10 | `de05613646c7d9f6` |

## What each regime actually charged

These are the artifacts' own declared cost fields, not a description of them. `qs` declares the catalog ladder's base point; `cbpackf` and `fingrad` declare fee and slippage per side plus the engine's funding flag; `rsimr` declares its cost preset and round-trip; `dspack` was published at the pack's own `author` regime — the pack file declares no costs — and its costed re-runs carry the engine's `repo6x5` preset name in their params.

| Adapter | Market | Base fee | Base slip | Base funding | Zero fee | Zero slip | Zero funding | run_ids |
|---|---|---|---|---|---|---|---|---|
| `qs` | JUPUSDT 1h | 5 | 2 | True | 0 | 0 | False | `25401a76f62d4c70` `d40e7af48a7b2b7c` |
| `cbpackf` | ETHUSDT 1h | 5 | 0.5 | True | 0 | 0 | False | `3263ad328e60a1eb` `82e522ce0d3b6bfd` |
| `rsimr` | SOLUSDC 1h | repo (11 RT) | n/a | spot: none | zero (0 RT) | n/a | spot: none | `4f77139298564618` `112aff3a78f78d28` |
| `qs` | SOLUSDT 1h | 5 | 2 | True | 0 | 0 | False | `cfa58e85c5e5720f` `314e1dad56a74613` |
| `qs` | SUIUSDT 1h | 5 | 2 | True | 0 | 0 | False | `129dcfd4cd09d10f` `b62406519f892a25` |
| `fingrad` | ETHUSDT 1h | 5 | 0 | True | 0 | 0 | False | `875f35f807e816bd` `35be1d630baab789` |
| `dspack` | BNBUSDT 1h | 0 (author) | 0 (author) | n/a (kline-only) | 0 (author) | 0 (author) | n/a (kline-only) | `6b1cb73c9af1d390` `6b1cb73c9af1d390` |
| `dspack` | DOGEUSDT 1h | 0 (author) | 0 (author) | n/a (kline-only) | 0 (author) | 0 (author) | n/a (kline-only) | `20f70bfad539bf29` `20f70bfad539bf29` |
| `qs` | HYPEUSDT 1h | 5 | 2 | True | 0 | 0 | False | `87ddc432ee66e7cd` `4e4caba793b91376` |
| `qs` | ETHUSDT 1h | 5 | 2 | True | 0 | 0 | False | `15f291a37172c589` `de05613646c7d9f6` |

Funding sign conventions differ by engine and are quoted AS STORED: `qs` `funding_paid` positive means paid; `cbpackf` and `fingrad` store it as their own signed cash flow. `rsimr` is spot and `dspack` is kline-only — neither has a funding input.

## Book by book

Numbers below are quoted from the artifacts in the table above; where a book is named, its run_ids are cited on the line.

**QS-009 Volatility-adjusted momentum — JUPUSDT 1h.** Base net 29.52% at PF 1.198 on 372 trades; zero net 54.01% at PF 1.279 on 372 trades (`25401a76f62d4c70`, `d40e7af48a7b2b7c`). Its base run's `funding_paid` reads 72.04 over 2394 settlement events (positive means paid), `25401a76f62d4c70`. This is one of the batch's re-measurements: its input klines grew since the ranking, so the base line above is not the published number. The catalog ladder and the funding bill were a heavy drag; the whole four-point cost column collapses at ZERO.

**S10 Vol-Targeted Time-Series Momentum — ETHUSDT 1h.** Base net 26.16% at PF 1.224 on 181 trades; zero net 38.20% at PF 1.331 on 181 trades (`3263ad328e60a1eb`, `82e522ce0d3b6bfd`). Its S10 row's `funding_paid_pct` reads 1.5252 and `funding_drag_pp` reads -1.6981, `3263ad328e60a1eb`. The engine's own funding drag for S10 is measured inside the base artifact; the zero run removes both that cash flow and the cost block.

**rsimr — SOLUSDC 1h.** Base net 7.56% at PF 1.217 on 60 trades; zero net 11.49% at PF 1.324 on 60 trades (`4f77139298564618`, `112aff3a78f78d28`). Its own `drag_pp` reads 3.9262 percentage points and `ret_zero_pct` reads 11.4877 percent, `4f77139298564618`; spot book, no funding input. The engine's own zero-cost reference sits inside the same artifact, so the gap needs no arithmetic by the reader.

**QS-004 Donchian channel breakout — SOLUSDT 1h.** Base net 17.46% at PF 1.217 on 228 trades; zero net 28.25% at PF 1.315 on 228 trades (`cfa58e85c5e5720f`, `314e1dad56a74613`). Its base run's `funding_paid` reads 113.81 over 932 settlement events (positive means paid), `cfa58e85c5e5720f`. A second Donchian cell, on SOL this time; the base run reproduces the published figure exactly even though its funding file grew.

**QS-006 ADX-filtered directional continuation — SUIUSDT 1h.** Base net 22.79% at PF 1.207 on 283 trades; zero net 38.17% at PF 1.301 on 283 trades (`129dcfd4cd09d10f`, `b62406519f892a25`). Its base run's `funding_paid` reads 54.90 over 828 settlement events (positive means paid), `129dcfd4cd09d10f`. The SUI cell of the QS-006 pair; its base net reproduces the published figure exactly.

**fingrad — ETHUSDT 1h.** Base net 58.99% at PF 1.203 on 788 trades; zero net 151.27% at PF 1.445 on 788 trades (`875f35f807e816bd`, `35be1d630baab789`). Its base run's `funding_paid` reads 29.06 over 488 settlement events, and its own `ret_zero_pct` (fees removed, funding still charged) reads 145.8926 percent, `875f35f807e816bd`. A re-measurement: the ETH kline file grew since the ranking. The engine's own zero-cost reference (fees off, funding still charged) is printed on this line; the ZERO column removes both.

**ds1 — BNBUSDT 1h.** Base net 224.04% at PF 1.190 on 2041 trades; zero net 224.04% at PF 1.190 on 2041 trades (`6b1cb73c9af1d390`; costed `1a24031d08608979`). THE MIRROR CASE. The pack file declares no costs and the engine charges no funding, so this book was published at zero cost from day one and its BASE and ZERO are one artifact. The costed re-run under the engine's own repo6x5 preset is the informative number.

The costed re-run of BNBUSDT 1h keeps 2041 trades and charges 179675.36 in fees, landing at -54.79% net at PF 0.9077; its own in-artifact zero-cost re-score `ret_zero_pct` reads 224.0446 percent (`1a24031d08608979`).

**ds1 — DOGEUSDT 1h.** Base net 205.42% at PF 1.186 on 1995 trades; zero net 205.42% at PF 1.186 on 1995 trades (`20f70bfad539bf29`; costed `be7d55cccdcd8d72`). The second mirror case, same construction on DOGE. Its costed re-run keeps the identical signal sequence and pays real fees.

The costed re-run of DOGEUSDT 1h keeps 1995 trades and charges 151400.12 in fees, landing at -20.30% net at PF 0.9692; its own in-artifact zero-cost re-score `ret_zero_pct` reads 205.4217 percent (`be7d55cccdcd8d72`).

**QS-006 ADX-filtered directional continuation — HYPEUSDT 1h.** Base net 19.82% at PF 1.196 on 194 trades; zero net 34.55% at PF 1.324 on 194 trades (`87ddc432ee66e7cd`, `4e4caba793b91376`). Its base run's `funding_paid` reads 24.09 over 1083 settlement events (positive means paid), `87ddc432ee66e7cd`. The HYPE cell of the QS-006 pair; the base run reproduces the published figure exactly.

**QS-005 Time-series momentum — ETHUSDT 1h.** Base net 15.67% at PF 1.195 on 141 trades; zero net 29.49% at PF 1.330 on 140 trades (`15f291a37172c589`, `de05613646c7d9f6`). Its base run's `funding_paid` reads 85.06 over 807 settlement events (positive means paid), `15f291a37172c589`. The base run reproduces the published figure exactly; ZERO nearly doubles the net line. This is the one cell where the trade count differs between regimes (141 on the base run, 140 on the zero run): the catalog's equity-dependent risk devices (daily-loss halt, drawdown halving and halt) are part of the strategy and react to the changed equity path, so the cost block can change the number of entries. The signals themselves are not re-fitted.

## What the numbers say

Three readings, none of them a verdict:

1. **Six of the ten published BASE figures reproduce exactly, and the four that do not sit on inputs that really grew.** The reproduction check is in `code/_zerocost_rows31_40_audit.py`; the base run_ids of every reproducing row are on the table lines above.
2. **The two ds1 rows are the mirror that shows what the ranking would look like if every book had been published at zero cost.** Their costed re-runs keep the same trade counts and land below zero net at PF near one, paying large fee bills on identical signals (both costed run_ids are cited on the rows 37 and 38 lines above). A zero-cost line is the upper bound of what a book could earn if execution were free.
3. **Cost removal moves every other book up, but the engines' own funding signs do not transfer between them.** The `qs` base runs on the table above carry positive `funding_paid` (paid), while the `cbpackf` and `fingrad` lines carry their own signed cash flows; funding was never a uniform tax across this batch.

## What this is not

- It is not a resurrection of any killed strategy. The kill list is unchanged and this report adds nothing to it: the QS-004, QS-005, QS-006 and QS-009 families carry their own catalog verdicts, S10 the strategy-pack verdict, rsimr and fingrad their own campaigns, and ds1 the five-strategy DeepSeek pack.
- It is not evidence of alpha. A zero-cost line is the upper bound of what a book could earn if execution were free; nobody trades for free.
- It is not a gate pass. No gate was evaluated, and no gate verdict is published here.
- It is not agent- or user-selected: the ten are published ranking rows 31 to 40, decided before this campaign existed.

## Limits and declared caveats

- **The two ds1 published numbers were never costed numbers.** The pack file declares no costs and the engine charges no funding, so the ranking rows were zero-cost constructions from the start; this campaign did not discover that, it quantified it inside artifacts. The costed re-runs use the engine's own repo6x5 preset; no gate is evaluated on them.
- **Funding is a real cash flow, not a fee.** The ZERO regime removes it because the user asked for all costs removed; for a perp that is a declared control, never a tradable result. The base column keeps it.
- **The `qs` ZERO regime zeroes the whole ladder including the random-entry null**, so the null comparison inside those artifacts is a zero-cost null against a zero-cost book — consistent, but not the published null regime.
- **Execution was not relaxed.** Signal on the closed bar, the engines' own fill modes, stop-first on ties, the engines' own sizing and risk devices all stay. Only the cost block and the screening rules were removed.
- **A re-measurement is not a contradiction.** Where an input file grew since the ranking, both columns here are minted on the same frozen cut; the audit records which rows reproduced exactly and which did not.
- **Trade counts are not always identical.** On QS-005 ETH the base run has 141 trades and the zero run 140 (their run_ids are on the table lines above). The catalog's equity-dependent risk devices are part of the strategy, so a different equity path can add or skip an entry; no signal rule was changed or re-fitted between regimes.

## Provenance

- Pre-registration: `results/zerocost_rows31_40_pre_registration.md` (written before the first artifact existed).
- Matrix: `results/zerocost_rows31_40_matrix.json` (per-cell run_ids, params, cut and inputs, plus the two costed re-runs).
- Verification log: `results/_zerocost_rows31_40_verify.txt` — twenty artifacts, twenty OK.
- Audit: `code/_zerocost_rows31_40_audit.py` — every adapter checked against an independent fresh-module recomputation, the engines' own in-artifact zero-cost references, and the reproduction logic declared in the pre-registration (equality is exact reproduction; inequality requires a grown input file).
- No harness or engine file was edited for this batch: every adapter already exposed its cost switch from batches 1-3. The engine files are byte-untouched and hashed into every run_id.

