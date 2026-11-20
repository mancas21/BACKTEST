# Zero cost, no rules — the ten best books re-run

Date: 2026-11-20. Status: **experiment / control**. This report contains no verdict, no gate and no alpha claim (see `results/zerocost_pre_registration.md`).

## The question

Ten books were taken from `results/top100_2026-10-31.md` — the first ten rows, in the order that list already published — and each was run twice on the same frozen data cut by the same engine bytes: once under the cost regime it was published under (**BASE**) and once with fees, slippage and funding all at zero (**ZERO**). The gates that decide whether a book is good are not applied here. The point is to see, book by book, how much of the published result was cost and what is left when nothing is charged.

Ten books produced nine adapter runs, because two of the ten rows are two different strategies inside the same `cbpackf` XRPUSDT artifact. Eighteen artifacts were minted, and every one of them verifies bit-for-bit (`results/_zerocost_verify.txt`).

## The ten, both regimes

Every row is one stored artifact; the run_id is on its own row. Net % is the book's own net return over its full window, PF its profit factor, Trades its closed-trade count and Max DD % the drawdown exactly as the engine stores it (negative where the engine reports a signed drawdown).

| Book | Market | Regime | Net % | PF | Trades | Max DD % | run_id |
|---|---|---|---:|---:|---:|---:|---|
| XRP delta-neutral grid v1 | XRPUSDT 15m | BASE | 1704.40 | 1.505 | 5929 | 10.01 | `e1b961d1a26c353d` |
| XRP delta-neutral grid v1 | XRPUSDT 15m | ZERO | 3544.64 | 1.663 | 5930 | 8.94 | `69099eb77c4d288c` |
| F74-15m market-structure HH/HL trend | HYPEUSDT 15m | BASE | 57.39 | 3.206 | 38 | 70.84 | `71e9bf25dc5581e3` |
| F74-15m market-structure HH/HL trend | HYPEUSDT 15m | ZERO | 87.23 | 4.022 | 38 | 66.90 | `6d0076ef99310982` |
| botstrat | SPXUSDT 1h | BASE | 38.72 | 3.079 | 31 | -4.17 | `632e2d2260ca2836` |
| botstrat | SPXUSDT 1h | ZERO | 39.05 | 3.110 | 31 | -4.13 | `69c9ed8891988006` |
| S02 Donchian + Flow Breakout | QQQ 1d | BASE | 25.24 | 2.192 | 39 | -9.77 | `e83fd53a66b52fd2` |
| S02 Donchian + Flow Breakout | QQQ 1d | ZERO | 25.40 | 2.203 | 39 | -9.76 | `ac49d9c266a49e83` |
| F74-1h market-structure HH/HL trend | HYPEUSDT 1h | BASE | 1.01 | 2.029 | 37 | 75.60 | `9b3267194422d882` |
| F74-1h market-structure HH/HL trend | HYPEUSDT 1h | ZERO | 18.15 | 2.356 | 37 | 72.39 | `711122410123d4f9` |
| botstrat | BNBUSDT 1h | BASE | 50.05 | 1.823 | 150 | -16.93 | `62d010ae1d316673` |
| botstrat | BNBUSDT 1h | ZERO | 52.01 | 1.859 | 150 | -16.40 | `d4811a881d4f0aae` |
| cvrmd | SUIUSDT 1h | BASE | 16.09 | 1.740 | 50 | -5.07 | `75bfb5c62d246861` |
| cvrmd | SUIUSDT 1h | ZERO | 18.59 | 1.887 | 50 | -4.88 | `abb85af41ab820b5` |
| S10 Vol-Targeted Time-Series Momentum | XRPUSDT 1h | BASE | 174.39 | 1.755 | 173 | -20.71 | `e3c4ce7d5ce1d2ce` |
| S10 Vol-Targeted Time-Series Momentum | XRPUSDT 1h | ZERO | 201.23 | 1.875 | 173 | -18.68 | `cc201b88f8e83306` |
| S10 Vol-Targeted Time-Series Momentum | SOLUSDT 1h | BASE | 70.79 | 1.590 | 176 | -21.44 | `f7c6306c2a52cca6` |
| S10 Vol-Targeted Time-Series Momentum | SOLUSDT 1h | ZERO | 86.25 | 1.725 | 176 | -20.43 | `323d4f818d073a61` |
| S02 Donchian + Flow Breakout | XRPUSDT 1h | BASE | 180.87 | 1.584 | 227 | -26.71 | `e3c4ce7d5ce1d2ce` |
| S02 Donchian + Flow Breakout | XRPUSDT 1h | ZERO | 245.11 | 1.783 | 225 | -20.99 | `cc201b88f8e83306` |

## What each regime actually charged

These are the artifacts' own declared cost fields, not a description of them: `fee_bps_per_side`, `slippage_bps_per_side` (or the engine's own name for it), and `funding_charged`.

| Adapter | Market | Base fee bps | Base slip bps | Base funding | Zero fee bps | Zero slip bps | Zero funding | run_ids |
|---|---|---:|---:|---|---:|---:|---|---|
| `xrpneutral` | XRPUSDT 15m | 2 | 2 | True | 0 | 0 | False | `e1b961d1a26c353d` `69099eb77c4d288c` |
| `pack100` | HYPEUSDT 15m | 5.5 combined | n/a | True | 0 | n/a | False | `71e9bf25dc5581e3` `6d0076ef99310982` |
| `botstrat` | SPXUSDT 1h | 6 | 5 | False | 0 | 0 | False | `632e2d2260ca2836` `69c9ed8891988006` |
| `eqpack` | QQQ 1d | 0.1 | 0.5 | n/a | 0 | 0 | n/a | `e83fd53a66b52fd2` `ac49d9c266a49e83` |
| `pack100` | HYPEUSDT 1h | 5.5 combined | n/a | True | 0 | n/a | False | `9b3267194422d882` `711122410123d4f9` |
| `botstrat` | BNBUSDT 1h | 6 | 5 | False | 0 | 0 | False | `62d010ae1d316673` `d4811a881d4f0aae` |
| `cvrmd` | SUIUSDT 1h | 6 | 5 | False | 0 | 0 | False | `75bfb5c62d246861` `abb85af41ab820b5` |
| `cbpackf` | XRPUSDT 1h | 5 | 0.5 | True | 0 | 0 | False | `e3c4ce7d5ce1d2ce` `cc201b88f8e83306` |
| `cbpackf` | SOLUSDT 1h | 5 | 0.5 | True | 0 | 0 | False | `f7c6306c2a52cca6` `323d4f818d073a61` |

Two shapes need a word of explanation. `pack100` declares a single combined cost of 5.5 bps per side (`cost_bps_per_side`), so it is not split into a fee and a slip. `xrpneutral` additionally declares a 5.0 bps flat/taker fee in `flat_fee_bps_per_side`, which the grid pays on the fills that are not maker fills; the column above shows its 2.0 bps maker fee.

`botstrat` and `cvrmd` are kline-only engines that have never carried a funding input, so their funding column reads false in both regimes; that is a property of the engine, not something this experiment switched off. Both still charge the pack's original 6 bps commission plus 5 bps slippage per side — the old 22 bps round-trip preset, twice the repo's current 11 bps — and because those engines size each position to a small fraction of equity, the fee block moves their equity only marginally. `eqpack` runs on Alpaca daily equity bars, where no perp funding exists.

## Book by book

Numbers below are quoted from the artifacts in the table above; where a book is named, both of its run_ids are cited on the line.

**XRP delta-neutral grid v1 — XRPUSDT 15m.** Base net 1704.40% at PF 1.505 on 5929 trades; zero net 3544.64% at PF 1.663 on 5930 trades (`e1b961d1a26c353d`, `69099eb77c4d288c`). Its base run's `fees` reads 50999.89 and its `funding_paid` reads 208.21. This is the row that passed every gate in the ranking and the one that pays the heaviest fee bill; its zero line is more than double its base line, which is what a book filled thousands of times should look like. It is also the row the 1m fill audit later killed: this is the 15m OHLC book, unchanged, and a zero-cost number does not cancel that.

**F74-15m market-structure HH/HL trend — HYPEUSDT 15m.** Base net 57.39% at PF 3.206 on 38 trades; zero net 87.23% at PF 4.022 on 38 trades (`71e9bf25dc5581e3`, `6d0076ef99310982`). Its base run's `funding_paid` reads -1214.68 — this engine stores the net funding cash flow, so a negative figure is a cost — and the engine's own `zero_cost_pf` reads 3.3780 (costs removed, funding still charged), against the ZERO artifact's PF on the same line. A large funding bill on a small trade count. Removing it and the fee block moves the result a long way, but the drawdown is the number that decides whether this book is holdable.

**botstrat — SPXUSDT 1h.** Base net 38.72% at PF 3.079 on 31 trades; zero net 39.05% at PF 3.110 on 31 trades (`632e2d2260ca2836`, `69c9ed8891988006`). The identity check of the whole campaign: this book's input bytes never changed since the ranking, and its BASE artifact reproduces the published number exactly. It trades rarely, so the cost block is a small part of its result.

**S02 Donchian + Flow Breakout — QQQ 1d.** Base net 25.24% at PF 2.192 on 39 trades; zero net 25.40% at PF 2.203 on 39 trades (`e83fd53a66b52fd2`, `ac49d9c266a49e83`). Alpaca equities at 1.2 bps round trip: there was almost nothing to remove, and almost nothing moves. This is what the control should look like where costs were never punitive.

**F74-1h market-structure HH/HL trend — HYPEUSDT 1h.** Base net 1.01% at PF 2.029 on 37 trades; zero net 18.15% at PF 2.356 on 37 trades (`9b3267194422d882`, `711122410123d4f9`). Its base run's `funding_paid` reads -884.15 — this engine stores the net funding cash flow, so a negative figure is a cost — and the engine's own `zero_cost_pf` reads 2.1003 (costs removed, funding still charged), against the ZERO artifact's PF on the same line. A flat full-window result at base cost becomes a clearly positive one; the funding line was the binding cost here, not the fees.

**botstrat — BNBUSDT 1h.** Base net 50.05% at PF 1.823 on 150 trades; zero net 52.01% at PF 1.859 on 150 trades (`62d010ae1d316673`, `d4811a881d4f0aae`). Trades often enough for the fee block to matter a little, not often enough for it to be the whole story.

**cvrmd — SUIUSDT 1h.** Base net 16.09% at PF 1.740 on 50 trades; zero net 18.59% at PF 1.887 on 50 trades (`75bfb5c62d246861`, `abb85af41ab820b5`). Same trade count in both regimes: the cost moves the equity, not the signals, which is what a price-level stop and target should do.

**S10 Vol-Targeted Time-Series Momentum — XRPUSDT 1h.** Base net 174.39% at PF 1.755 on 173 trades; zero net 201.23% at PF 1.875 on 173 trades (`e3c4ce7d5ce1d2ce`, `cc201b88f8e83306`). Its base row's `funding_paid_pct` reads 4.77. Both costs are present here — fees and funding — and the zero line sits well above the base line without changing the shape of the book.

**S10 Vol-Targeted Time-Series Momentum — SOLUSDT 1h.** Base net 70.79% at PF 1.590 on 176 trades; zero net 86.25% at PF 1.725 on 176 trades (`f7c6306c2a52cca6`, `323d4f818d073a61`). Its base row's `funding_paid_pct` reads 2.43. The same shape as its XRP sibling at a smaller scale.

**S02 Donchian + Flow Breakout — XRPUSDT 1h.** Base net 180.87% at PF 1.584 on 227 trades; zero net 245.11% at PF 1.783 on 225 trades (`e3c4ce7d5ce1d2ce`, `cc201b88f8e83306`). Its base row's `funding_paid_pct` reads 4.46. The best net return at base cost also gains the most in absolute points. That is a statement about cost, not about edge.

## What the numbers say

Three readings, none of them a verdict:

1. **Cost was real, and its size is not uniform.** The equity book moves from 25.24 at base to 25.40 at zero; the XRP grid moves from 1704.40 to 3544.64 (`e83fd53a66b52fd2`, `ac49d9c266a49e83`, `e1b961d1a26c353d`, `69099eb77c4d288c`). A blanket "costs killed everything" would be false for most of these books.
2. **Zero cost does not rescue a book that was not cost-bound.** Where the base result was small and the trade count low, the zero line is still small: removing a cost that was never the binding constraint changes nothing that matters.
3. **The published ranking is partly a cost ranking.** The 1h market-structure book sits high in the list at 1.01 net and becomes 18.15 at zero cost, while the equity book beside it moves from 25.24 to 25.40 (`9b3267194422d882`, `711122410123d4f9`, `e83fd53a66b52fd2`, `ac49d9c266a49e83`). Position in that list therefore reflects how expensive a book was to run as well as what it predicted.

## What this is not

- It is not a resurrection of any killed strategy. The kill list is unchanged and this report adds nothing to it.
- It is not evidence of alpha. A zero-cost line is the upper bound of what a book could earn if execution were free; nobody trades for free.
- It is not a gate pass. No gate was evaluated, and the words PASS and FAIL do not appear in this report's tables.
- It is not agent- or user-selected: the ten were the published top ten, decided before this campaign existed.

## Limits and declared caveats

- **The ranking artifacts are four weeks old.** Five of the nine input files grew since the ranking was published (the two XRP inputs, the BNB klines, the SUI klines and the HYPE/XRP/SOL funding files share that fate), so BASE here is not a copy of the published number: it is the same book re-measured on today's bytes. Only the SPXUSDT and QQQ rows have unchanged inputs, and only those two reproduce their published figures exactly.
- **Funding is a real cash flow, not a fee.** The ZERO regime removes it because the user asked for all costs removed; for a perp that is a declared control, never a tradable result. The base column keeps it.
- **Execution was not relaxed.** Signal on the closed bar, fill at the next open, stop-first on ties, gap-through at the open, the engine's own sizing and leverage cap all stay. Only the cost block and the screening rules were removed.
- **`xrpneutral` is the 15m OHLC book.** The 1m fill-resolution audit killed it after the ranking was published; this experiment does not re-open that question and its numbers carry the same warning.

## Provenance

- Pre-registration: `results/zerocost_pre_registration.md` (written before the first artifact existed).
- Matrix: `results/zerocost_matrix_2026-11-20.json` (per-cell run_ids, params, cut and inputs).
- Verification log: `results/_zerocost_verify.txt` — eighteen artifacts, eighteen OK.
- Audit: `code/_zerocost_audit.py` — twenty-three checks, all passing, including an independent recomputation of every patched engine at zero cost and the engines' own published zero-cost controls (`zero_cost_pf` for `pack100`, `drag_pp` for `eqpack`).
- Harness switches added for this campaign: an explicit `costs` key on `botstrat`, `cvrmd` and `pack100`; `cbpackf`, `xrpneutral` and `eqpack` already exposed theirs. Absent the key every runner behaves exactly as before, which is why no stored artifact changed status.
