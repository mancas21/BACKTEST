# Zero cost, no rules — rows 11-20 of the hundred best books re-run

Date: 2026-11-20. Status: **experiment / control**. This report contains no verdict, no gate and no alpha claim (see `results/zerocost_rows11_20_pre_registration.md`). It is the second batch of the same control as `results/zerocost_report_2026-11-20.md`, which covered rows 1-10.

## The question

Ten more books were taken from `results/top100_2026-10-31.md` — rows 11 to 20, in the order that list already published — and each was run twice on the same frozen data cut by the same engine bytes: once under the cost regime it was published under (**BASE**) and once with fees, slippage and funding cash flow all at zero (**ZERO**). The gates that decide whether a book is good are not applied here. The point is the same as for rows 1-10: see, book by book, how much of the published result was cost and what is left when nothing is charged.

Ten books produced nine adapter runs, because rows 16 and 17 are two strategies inside the same `eqpack` QQQ artifact. Eighteen artifacts back this report, and every one of them verifies bit-for-bit (`results/_zerocost_rows11_20_verify.txt`). Two of the eighteen are the same QQQ artifacts the rows 1-10 campaign already minted — identical params on identical bytes produce identical run_ids, so this batch cites them instead of minting duplicates.

## The ten, both regimes

Every row is one stored artifact; the run_id is on its own row. Net % is the book's own net return over its full window, PF its profit factor, Trades its closed-trade count and Max DD % the drawdown exactly as the engine stores it (negative where the engine reports a signed drawdown).

| Book | Market | Regime | Net % | PF | Trades | Max DD % | run_id |
|---|---|---|---:|---:|---:|---:|---|
| QS-001 Moving-average trend continuation | HYPEUSDT 1h | BASE | 20.17 | 1.521 | 72 | -9.64 | `c38d452ed032ae45` |
| QS-001 Moving-average trend continuation | HYPEUSDT 1h | ZERO | 27.79 | 1.736 | 72 | -7.58 | `1b8a119240535015` |
| botstrat | AVAXUSDT 1h | BASE | 50.20 | 1.512 | 147 | -21.47 | `1eaf1e4e01bb54ce` |
| botstrat | AVAXUSDT 1h | ZERO | 52.14 | 1.531 | 147 | -20.73 | `d669e0c0ba73f283` |
| C7 | SOLUSDT 1h | BASE | 2.48 | 1.477 | 33 | 1.80 | `2d4793e174cfaf5b` |
| C7 | SOLUSDT 1h | ZERO | 2.92 | 1.583 | 33 | 1.75 | `d58e61d3ec1d702c` |
| botstrat | ETHUSDT 1h | BASE | 27.06 | 1.448 | 140 | -8.53 | `80259a12249596a9` |
| botstrat | ETHUSDT 1h | ZERO | 28.52 | 1.475 | 140 | -8.49 | `97077f5edabb98b6` |
| botstrat | SOLUSDT 1h | BASE | 37.39 | 1.442 | 134 | -9.86 | `dd585aa5134c7de4` |
| botstrat | SOLUSDT 1h | ZERO | 38.98 | 1.461 | 134 | -9.78 | `7a080ed866c97b16` |
| S01 Taker-Flow Drift Bands | QQQ 1d | BASE | 24.18 | 1.427 | 81 | -6.15 | `e83fd53a66b52fd2` |
| S01 Taker-Flow Drift Bands | QQQ 1d | ZERO | 24.44 | 1.433 | 81 | -6.13 | `ac49d9c266a49e83` |
| S05 HTF Trend Pullback (RSI-2) | QQQ 1d | BASE | 11.43 | 1.411 | 99 | -3.72 | `e83fd53a66b52fd2` |
| S05 HTF Trend Pullback (RSI-2) | QQQ 1d | ZERO | 11.86 | 1.427 | 99 | -3.68 | `ac49d9c266a49e83` |
| smqe | SOLUSDT 1h | BASE | 15.53 | 1.440 | 84 | 7.48 | `2df3b1e3ea29f99d` |
| smqe | SOLUSDT 1h | ZERO | 21.40 | 1.649 | 84 | 6.02 | `0d1c4cf446c06ae7` |
| cvrmd | SOLUSDT 1h | BASE | 17.12 | 1.430 | 84 | -6.66 | `dc4bd31dc75d6a56` |
| cvrmd | SOLUSDT 1h | ZERO | 22.16 | 1.575 | 84 | -5.55 | `73010b20871fce71` |
| botstrat | BTCUSDT 1h | BASE | 19.82 | 1.397 | 156 | -4.96 | `b00902544413ce0c` |
| botstrat | BTCUSDT 1h | ZERO | 21.44 | 1.435 | 156 | -4.65 | `ced9488099cac1ed` |

## What each regime actually charged

These are the artifacts' own declared cost fields, not a description of them: `fee_bps_per_side`, the adapter's slippage field, and `funding_charged`.

| Adapter | Market | Base fee bps | Base slip bps | Base funding | Zero fee bps | Zero slip bps | Zero funding | run_ids |
|---|---|---:|---:|---|---:|---:|---|---|
| `qs` | HYPEUSDT 1h | 5 | 2 | True | 0 | 0 | False | `c38d452ed032ae45` `1b8a119240535015` |
| `botstrat` | AVAXUSDT 1h | 6 | 5 | False | 0 | 0 | False | `1eaf1e4e01bb54ce` `d669e0c0ba73f283` |
| `cand7` | SOLUSDT 1h | 5 | 2 | True | 0 | 0 | False | `2d4793e174cfaf5b` `d58e61d3ec1d702c` |
| `botstrat` | ETHUSDT 1h | 6 | 5 | False | 0 | 0 | False | `80259a12249596a9` `97077f5edabb98b6` |
| `botstrat` | SOLUSDT 1h | 6 | 5 | False | 0 | 0 | False | `dd585aa5134c7de4` `7a080ed866c97b16` |
| `eqpack` | QQQ 1d | 0.1 | 0.5 | n/a | 0 | 0 | n/a | `e83fd53a66b52fd2` `ac49d9c266a49e83` |
| `smqe` | SOLUSDT 1h | 5 | 0.5 | True | 0 | 0 | False | `2df3b1e3ea29f99d` `0d1c4cf446c06ae7` |
| `cvrmd` | SOLUSDT 1h | 6 | 5 | False | 0 | 0 | False | `dc4bd31dc75d6a56` `73010b20871fce71` |
| `botstrat` | BTCUSDT 1h | 6 | 5 | False | 0 | 0 | False | `b00902544413ce0c` `ced9488099cac1ed` |

Adapter shapes this batch adds to the rows 1-10 note: `botstrat` and `cvrmd` charge the pack's original preset, 6 bps commission plus 5 bps slippage per side, and are kline-only engines that have never carried a funding input, so their funding column reads false in both regimes. `qs` runs the strategy catalog's four-point cost ladder (base 14 bps RT primary, adverse, stress, plus the 11 bps repo gate point) with funding at the real settlement instants; its ZERO run zeroes all four points at once, and the random-entry null runs in the same regime. `cand7` charges the candidate document's own block, 5.0 fee plus 2.0 slip bps per side, with funding at the real settlements. `smqe` charges the repo 11 bps round trip plus a constant-rate funding ledger of 0.01 percent per 8 hours. `eqpack` runs on Alpaca daily equity bars at 1.2 bps round trip, where no perp funding exists.

## Book by book

Numbers below are quoted from the artifacts in the table above; where a book is named, both of its run_ids are cited on the line. The funding sign conventions differ by engine and are quoted AS STORED: `qs` `funding_paid` positive means paid, `cand7` `funding_net_usdt` positive means RECEIVED, `smqe` `funding_paid_usd` positive means paid.

**QS-001 Moving-average trend continuation — HYPEUSDT 1h.** Base net 20.17% at PF 1.521 on 72 trades; zero net 27.79% at PF 1.736 on 72 trades (`c38d452ed032ae45`, `1b8a119240535015`). Its base run's `funding_paid` reads -11.55 over 861 settlement events (positive means paid, so this book RECEIVED net funding). The catalog battery collapses to a single point at zero: with the ladder zeroed, the base, adverse and gate cost views all return the same number, which is the internal consistency check the pre-registration declared. The base run reproduces the published figure exactly. The funding net over the window was small and the book was on the receiving side of it; the fee block was the real drag. This family passed zero of ten cells in its own campaign, and a control does not change that.

**botstrat — AVAXUSDT 1h.** Base net 50.20% at PF 1.512 on 147 trades; zero net 52.14% at PF 1.531 on 147 trades (`1eaf1e4e01bb54ce`, `d669e0c0ba73f283`). The base run reproduces the published figure exactly, so this is the cleanest botstrat read of the batch: the old preset costs about two points of net on a hundred and forty-seven trades, and everything else about the book is unchanged.

**C7 — SOLUSDT 1h.** Base net 2.48% at PF 1.477 on 33 trades; zero net 2.92% at PF 1.583 on 33 trades (`2d4793e174cfaf5b`, `d58e61d3ec1d702c`). Its base run's `fees_paid` read 40.51 and its `funding_net_usdt` read 10.91 (positive means RECEIVED; this short book was paid to hold). The closest of the seven prespecified candidates. Its signal reads the funding file — entries fire at settlement bars on funding-rate quantiles — so the ZERO regime zeroes the fees and the funding CASH while the signal keeps consuming the real funding series, declared before the run. The artifact's own internal zero-fee control matches the headline exactly at ZERO, which is the switch's known-answer.

**botstrat — ETHUSDT 1h.** Base net 27.06% at PF 1.448 on 140 trades; zero net 28.52% at PF 1.475 on 140 trades (`80259a12249596a9`, `97077f5edabb98b6`). The ETH 1h input grew since the ranking (the published row counts a hundred and thirty-eight trades, this base run counts a hundred and forty), so the base number here is a re-measurement on newer bytes, not a reproduction.

**botstrat — SOLUSDT 1h.** Base net 37.39% at PF 1.442 on 134 trades; zero net 38.98% at PF 1.461 on 134 trades (`dd585aa5134c7de4`, `7a080ed866c97b16`). The base run reproduces the published figure exactly. Same shape as its AVAX sibling: the old preset costs a point and a half of net on a hundred and thirty-four trades.

**S01 Taker-Flow Drift Bands — QQQ 1d.** Base net 24.18% at PF 1.427 on 81 trades; zero net 24.44% at PF 1.433 on 81 trades (`e83fd53a66b52fd2`, `ac49d9c266a49e83`). Its base row's `drag_pp` reads 0.2609. Alpaca equities at 1.2 bps round trip: the engine's own measured drag_pp field equals the zero-minus-base gap on this row to the last digit, which is the eqpack known-answer. There was almost nothing to remove, and almost nothing moves.

**S05 HTF Trend Pullback (RSI-2) — QQQ 1d.** Base net 11.43% at PF 1.411 on 99 trades; zero net 11.86% at PF 1.427 on 99 trades (`e83fd53a66b52fd2`, `ac49d9c266a49e83`). Its base row's `drag_pp` reads 0.4252. Same eqpack artifact as row 16 — the pack runs all strategies in one artifact — and the same conclusion: costs were never punitive here.

**smqe — SOLUSDT 1h.** Base net 15.53% at PF 1.440 on 84 trades; zero net 21.40% at PF 1.649 on 84 trades (`2df3b1e3ea29f99d`, `0d1c4cf446c06ae7`). Its base run's `fees` read 476.72 and its `funding_paid_usd` read -2.20 (positive means paid, so this book RECEIVED net funding); the engine's own zero-fee reference `pf_zero` reads 1.6495 at the primary fill mode. The funding ledger was small (the book was on the receiving side of it) and the fee block was the larger drag; removing both lifts the net by about six points. The base number differs from the published one because the SOL 1h input grew since the ranking (the published row counts eighty-three trades, this base run counts eighty-four).

**cvrmd — SOLUSDT 1h.** Base net 17.12% at PF 1.430 on 84 trades; zero net 22.16% at PF 1.575 on 84 trades (`dc4bd31dc75d6a56`, `73010b20871fce71`). The SOL 1h input grew since the ranking (the published row counts eighty-three trades; this base run measures eighty-four trades on newer bytes), so this is a re-measurement. The zero line sits about five points above the base line with an identical trade count in both regimes: the cost moves the equity, not the signals.

**botstrat — BTCUSDT 1h.** Base net 19.82% at PF 1.397 on 156 trades; zero net 21.44% at PF 1.435 on 156 trades (`b00902544413ce0c`, `ced9488099cac1ed`). The BTC 1h input grew since the ranking (published row: a hundred and fifty-five trades; this base run: a hundred and fifty-six), so the base number is a re-measurement. The zero line sits under two points above it.

## What the numbers say

Three readings, none of them a verdict:

1. **Every book in this batch moves up at zero, and most of the batch was not cost-bound.** The equity rows move from 24.18 to 24.44 and from 11.43 to 11.86; the biggest mover in points is the smqe book at 15.53 to 21.40 (`e83fd53a66b52fd2`, `ac49d9c266a49e83`, `2df3b1e3ea29f99d`, `0d1c4cf446c06ae7`). A blanket "costs killed these books" would be false for eight of the ten; the two biggest relative movers (the smqe book and the cvrmd SOL book at 17.12 to 22.16, `dc4bd31dc75d6a56`, `73010b20871fce71`) are also the two whose BASE costs sit above the repo's current 11 bps regime.
2. **The QS-001 funding answer is the opposite of the F74-1h answer the first batch found.** The 1h market-structure book paid a large funding bill and funding was its binding cost; this catalog book RECEIVED a small net funding amount over the same kind of window (`c38d452ed032ae45`), and its drag was the fee block. Cost conclusions do not transfer between books — which is the point of measuring each.
3. **The ranking order barely moves.** The zero-regime profit factors of the batch span the same narrow band the table above shows, in roughly the same order the books sat at base; nothing here becomes a candidate and nothing was one before (`41ae8c79fe005541` is the ranking's own record of that order).

## What this is not

- It is not a resurrection of any killed strategy. The kill list is unchanged and this report adds nothing to it. QS-001, C7, S01, S05 and smqe all carry their killed verdicts from their own campaigns; botstrat and cvrmd remain early ports and fragile/suspended respectively.
- It is not evidence of alpha. A zero-cost line is the upper bound of what a book could earn if execution were free; nobody trades for free.
- It is not a gate pass. No gate was evaluated, and the words PASS and FAIL do not appear in this report's tables.
- It is not agent- or user-selected: the ten are published ranking rows 11 to 20, decided before this campaign existed.

## Limits and declared caveats

- **Six of the ten books reproduce their published figures exactly** (QS-001, C7, botstrat AVAX, botstrat SOL, and both QQQ rows have byte-unchanged inputs); the other four (botstrat ETH, botstrat BTC, smqe, cvrmd SOL) sit on inputs that grew since 2026-10-31, so their BASE lines are re-measurements on newer bytes, not reproductions.
- **Funding is a real cash flow, not a fee.** The ZERO regime removes it because the user asked for all costs removed; for a perp that is a declared control, never a tradable result. The base column keeps it.
- **C7's signal consumes funding.** Its ZERO run zeroes the fees and the funding cash while the signal keeps reading the real funding file; that is a declared property of this book, not an oversight. Its two artifacts also run on the legacy full-file cut (`cut_ts=full`), because the cand7 engine reads its data by repo-root path rather than from the served files; future data appends will mark them STALE, which is the honest label for that engine.
- **The qs ZERO regime zeroes the whole ladder including the random-entry null**, so the null comparison inside that artifact is a zero-cost null against a zero-cost book — consistent, but not the published null regime.
- **Execution was not relaxed.** Signal on the closed bar, fill at the next open (or the engine's own fill mode), stop-first on ties, gap-through at the open, the engines' own sizing and risk devices all stay. Only the cost block and the screening rules were removed.

## Provenance

- Pre-registration: `results/zerocost_rows11_20_pre_registration.md` (written before the first artifact existed, with a dated addendum correcting which cand7 fields must be equal).
- Matrix: `results/zerocost_rows11_20_matrix.json` (per-cell run_ids, params, cut and inputs).
- Verification log: `results/_zerocost_rows11_20_verify.txt` — eighteen artifacts, eighteen OK.
- Audit: `code/_zerocost_rows11_20_audit.py` — every adapter checked against an independent fresh-module recomputation, the engines' own published zero-cost references (`pf_zero` for smqe, `profit_factor_zero` for cand7, `drag_pp` for eqpack), and exact reproduction asserted only where the ranking's input bytes did not change.
- Harness switches added for this batch: an explicit `costs`/`funding` key on `qs` and `cand7` and a `funding` key on `smqe`; `botstrat`, `cvrmd` and `eqpack` already exposed theirs from the rows 1-10 batch. The engine files are byte-untouched (they are hashed into every run_id); absent the keys every runner behaves exactly as before, and the rows 1-10 SPX artifact was re-verified after the edits to prove it.
