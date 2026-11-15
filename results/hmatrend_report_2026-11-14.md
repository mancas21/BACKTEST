# hmatrend - the external hermes HMA(34) Trend pack, audited and re-run (2026-11-14)

Question: what is the external file `hma_backtest_oos_consolidado.json` (an "hermes" CLI session's HMA(34) Trend backtest, 12 pairs, 1h, 70/30 IS/OOS on about 125 days of 2026) worth under this repo's rules? Protocol: sources of record copied byte-identical to `code/hma_trend_sources/` (sha256 manifest, all bound into every run_id), conventions measured from the pack's own outputs, a declared spec frozen before any repo-market run, dual-mode engine `code/hma_trend_engine.py` (adapter `hmatrend`), claim-check on the pack's own windows, then the repo battery on full repo history.

Declared costs for every repo-mode cell: 5.0 bps fee + 0.5 bps slip per side (11.0 bps round trip), funding charged at real settlements on the open notional, fill model next_open_stop_first_gap_through, sizing 100% of equity per trade (the pack's own convention), long-only, no take-profit. The zero-cost control is measured inside every artifact.

## 1. What the pack's outputs pin down (measured)

The pack's own engine code did NOT survive; only its output JSONs did. From the JUPUSDT full-2026 run (247 trades on 7618 one-hour bars; claim and parity numbers carried in artifact 2411025b023d0bbf) the outputs pin, exactly:

- Every entry fills at the OPEN of the bar after the signal close (247 of 247 trades), every HMA_DOWN exit fills at the open of the bar after its signal close (229 of 229) - the same next-open convention this repo uses.
- Every STOP exit (18 of 18) fills intrabar at exactly entry - 3.0 x ATR(14, Wilder at the signal bar); the fitted multiple is 3.0 with zero spread.
- Every trade PnL equals the raw price delta - zero fees, and a long-only book (the pack charged its perps neither fees nor funding).
- Sizing compounds the full equity every trade.
- Four trades have entry_bar equal to exit_bar and PnL exactly zero - a flag-ordering quirk of the pack's engine (entry and exit scheduled on the same close, applied enter-then-exit at one open). Not reproduced here (declared).
- The pack's own profit factor is pct-weighted (sum of trade percent gains over percent losses), not money-weighted: the same trade list gives 2.1709 money-weighted against the published 2.2533 pct-weighted (both recomputed from the pack's own trades, carried in artifact 2411025b023d0bbf).

## 2. What the outputs cannot pin down (declared)

The exact exit predicate is not recoverable from the 247-trade sample: no candidate family separates every one of the 229 exit-signal bars from the 2970 position-held bars whose close signal did not fire (HMA slope on 1h and 4h aggregations and seven price sources, periods 10 to 50, lags 1 to 3, close versus HMA, entry-relative levels, HMA trailing, unrealized-PnL thresholds, price-action booleans; re-measured inside artifact 2411025b023d0bbf and by code/_hma_trend_parity.py). The frozen declared spec therefore reads the pack's own label literally: entry = HMA(34) rising at the close, exit = HMA(34) falling at the close, stop = entry - 3.0 x ATR14 (measured exactly). On the pack's OWN bytes the declared book produces 292 trades with average hold 12.7 bars against the claim's 247 trades and 12.9 bars average hold - and 0 shared (entry, exit) bar pairs: the claim's edge lives in exit timing that no defensible reading of "HMA(34) Trend" reproduces. No parameter was fitted to the claim's trades.

Engine audit: code/_hma_trend_audit.py, sixteen known-answer checks, all PASS (it caught two real engine defects before any market run: an ATR-warmup entry that set the stop equal to the entry price, and a PnL basis that omitted the entry fee from the position cost). Parity tool: code/_hma_trend_parity.py, twelve checks, all PASS.

## 3. The claim's measured defects

Measured on the pack's own outputs and re-stated inside every hermes artifact as claim_* metrics (source JSON sha-bound as an adapter source):

- Zero fees: the pack's per-trade PnL is the raw price delta on every source trade; the repo regime charges 11.0 bps round trip.
- Zero funding on perps: eleven of the twelve pack pairs are Binance perpetuals with funding files in this repo; the pack charged none.
- Same-bar close signals filled at next open - the pack is fair on fill timing (measured, not assumed).
- One short window: each pair's IS/OOS covers about 125 days of 2026; the OOS segment is a single 38-day slice. NVDAUSDT and SPCXUSDT use DIFFERENT windows (their data starts later), so the twelve OOS cells are not the same market period.
- Five of the twelve pairs LOSE to buy & hold over their own OOS slice even at zero cost (their excess_return column is negative in the claim table below) - the consolidated averages sit on a window where half the book already loses to holding.

## 4. Claim-check - the declared book on the pack's own windows (zero cost)

mode=hermes: the repo data sliced to the pack's own per-pair windows, zero fees, no funding, the pack's conventions. XAUUSDT has no data on disk (NO DATA declared). The claim columns are the pack's own published numbers, carried inside the artifact.

| symbol | window | bars | declared ret % | declared PF | declared n | claim IS ret % | claim OOS ret % | claim OOS PF | claim OOS n | claim OOS excess % | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 2026-01-01 to 2026-05-05 | 3000 | 5.10 | 1.0831 | 112 | 7.34 | 13.63 | 2.8518 | 28 | -8.78 | a65edc089583d7ba |
| ETHUSDT | 2026-01-01 to 2026-05-05 | 3000 | 0.97 | 1.0123 | 116 | 12.10 | 21.87 | 3.7718 | 28 | 3.47 | 62b36d415be65a19 |
| HYPEUSDT | 2026-01-01 to 2026-05-05 | 3000 | 58.64 | 1.3784 | 113 | 82.79 | 35.07 | 3.9730 | 23 | 21.40 | a18803e0648e5b76 |
| JUPUSDT | 2026-01-01 to 2026-05-05 | 3000 | 28.86 | 1.2110 | 111 | 38.36 | 40.22 | 3.0144 | 29 | 4.02 | 2411025b023d0bbf |
| SOLUSDT | 2026-01-01 to 2026-05-05 | 3000 | -5.31 | 0.9418 | 113 | 8.91 | 9.45 | 1.9213 | 31 | 2.59 | 0fd70280f7eb7d25 |
| SUIUSDT | 2026-01-01 to 2026-05-05 | 3000 | -4.07 | 0.9622 | 113 | 12.11 | 13.26 | 1.8145 | 29 | -3.62 | 5dee529d084895d9 |
| XRPUSDT | 2026-01-01 to 2026-05-05 | 3000 | 19.63 | 1.2265 | 104 | 27.89 | 3.46 | 1.4205 | 30 | -4.02 | 408ac5485eccaf6c |
| 1000PEPEUSDT | 2026-01-01 to 2026-05-05 | 3000 | -12.14 | 0.9067 | 123 | 46.14 | 12.32 | 1.5514 | 29 | -17.66 | 78a537a28461a8b1 |
| ARBUSDT | 2026-01-01 to 2026-05-05 | 3000 | -28.53 | 0.7271 | 114 | -19.59 | 29.31 | 2.2843 | 28 | -6.91 | ad4b85891b38412e |
| NVDAUSDT | 2026-03-26 to 2026-07-28 | 2986 | -2.62 | 0.9598 | 125 | 11.51 | -1.70 | 1.0150 | 30 | 5.99 | eaff1ab244fa05a8 |
| SPCXUSDT | 2026-05-21 to 2026-09-21 | 2972 | -25.55 | 0.7645 | 120 | 24.76 | -0.50 | 1.1004 | 29 | -10.93 | 671cf42e5afe8d9a |

The pack's headline full-2026 JUPUSDT claim (return 890.48 percent, PF 2.2533, 247 trades, max DD 16.90 percent against buy & hold 37.13 percent) is carried in artifact 2411025b023d0bbf; the declared book on the same bytes and window delivers 28.86 percent at PF 1.2110 over 111 trades. The claim is unreproducible from its own published outputs even in the most favorable setting (its own data, its own fills and stop rule, zero cost).

## 5. Repo battery - full repo history, 11 bps RT, funding charged

mode=repo on the full 1h history on disk (per-pair window dates in the table; NVDAUSDT and SPCXUSDT only exist from 2026). Gate battery as in code/bt.py (PF ex-cost above 1.2, n at least 30, net above 0, at least 2 of 3 green thirds, OOS PF above 1.2, OOS net above 0, top-5 concentration at or below 100 percent of PnL, bootstrap CI of the mean trade above 0).

| symbol | window | bars | n | net % | PF ex-cost | max DD % | thirds green | OOS PF | OOS net % | boot CI lo | zero-cost ret % | funding paid | top5 % of PnL | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 2019-09-08 to 2026-11-02 | 62687 | 2406 | -45.31 | 0.9792 | 81.04 | 1 | 0.8921 | -42.31 | -14.38 | 1084.64 | 6546.38 | -289.71 | 93f107d4bc20d3e7 |
| ETHUSDT | 2019-11-27 to 2026-11-02 | 60777 | 2298 | 48.33 | 1.0103 | 69.28 | 2 | 0.9829 | -20.57 | -23.98 | 3173.56 | 12644.22 | 519.06 | 13330a919c10aa61 |
| SOLUSDT | 2020-09-14 to 2026-11-02 | 53769 | 2011 | 119.15 | 1.0128 | 78.93 | 2 | 0.9243 | -164.47 | -59.92 | 2029.16 | 5809.29 | 451.80 | ef1815baa5d5f6ca |
| SUIUSDT | 2023-05-03 to 2026-11-02 | 30696 | 1203 | -91.29 | 0.8118 | 93.27 | 1 | 0.7470 | -14.52 | -14.60 | -63.71 | 248.34 | -43.25 | 688b6aab9d336f44 |
| XRPUSDT | 2020-01-06 to 2026-11-02 | 59816 | 2293 | -40.03 | 0.9761 | 87.78 | 1 | 1.0931 | 35.24 | -13.17 | 1283.85 | 4570.99 | -372.60 | 0a481d64b12dfb13 |
| ARBUSDT | 2024-11-02 to 2026-11-02 | 17520 | 666 | -60.85 | 0.9184 | 87.60 | 1 | 0.9410 | -6.71 | -33.49 | -13.23 | 626.16 | -141.83 | 7aac8b0a72a2eb2a |
| HYPEUSDT | 2025-05-30 to 2026-11-06 | 12614 | 474 | -54.33 | 0.8285 | 86.49 | 1 | 0.9787 | -1.34 | -28.69 | -17.89 | 379.82 | -86.64 | 7fd51aaaad1ff178 |
| 1000PEPEUSDT | 2025-09-01 to 2026-10-09 | 9696 | 383 | -52.51 | 0.8303 | 73.73 | 0 | 1.0735 | 3.84 | -40.37 | -26.78 | 48.64 | -158.82 | a80b4f00cb4c6024 |
| NVDAUSDT | 2026-03-26 to 2026-11-02 | 5304 | 205 | -13.81 | 0.8577 | 28.39 | 1 | 0.9739 | -0.41 | -23.86 | 9.57 | 129.01 | -169.21 | e9bf4de86c939484 |
| SPCXUSDT | 2026-05-21 to 2026-11-02 | 3970 | 165 | -40.56 | 0.6883 | 48.13 | 0 | 0.7623 | -5.66 | -57.71 | -28.39 | 33.16 | -117.39 | 006df3b25dbaf74c |
| JUPUSDT | 2024-01-31 to 2026-10-29 | 24053 | 912 | -69.26 | 0.9057 | 88.42 | 1 | 1.1074 | 9.42 | -24.67 | -20.09 | -206.76 | -136.48 | 30ef63651b4760db |

XAUUSDT: NO DATA - no kline file for the symbol exists anywhere under data/ (the adapter's inputs fail loudly; the pack's XAU cell is declared unmeasurable in this repo).

Reading the table: the top-5 concentration column is negative on the losing cells because the share divides by a negative total PnL - it is measured as stored, and the gate it feeds (at or below 100 percent) passes trivially there; the concentration gate binds only on winning books (ETHUSDT 519.06 percent of PnL).

## 6. Verdict

Per REGLA 1 this verdict uses ONLY this strategy's own artifacts (the 22 run_ids cited above; all verify bit-for-bit). The fingrad and hmaaoadx HMA relatives are context, not evidence.

**KILLED - zero of eleven measurable cells pass the screen battery, at every gate that binds.** The full-history book with repo costs and real funding: profit factor 0.6883 to 1.0128 (nothing reaches the 1.2 gate), OOS profit factor 0.7470 to 1.1074 (nothing reaches 1.2), bootstrap CI of the mean per-trade PnL below zero on all eleven cells, thirds green on at most 2 of 3. The zero-cost control inside the artifacts shows the cost regime is not the whole story: JUPUSDT at zero cost returns -20.09 percent against -69.26 percent at repo costs - the signal has no gross edge to protect.

**The external claim is UNREPRODUCIBLE FROM ITS OWN OUTPUTS.** With the pack's own data, its own measured fill and stop conventions, and zero cost, no defensible reading of "HMA(34) Trend" approaches the published returns; the published profit factor is pct-weighted; the OOS cells are a single 38-day slice with five of twelve pairs already losing to buy & hold; and the pack charged its perps neither fees nor funding. Its numbers must not be cited anywhere as results.

Next step per doctrine: none - no forward paper record for a book with no gross edge; the line closes here unless a NEW, SOURCE-COMPLETE pack arrives (REGLA 1: this verdict never pre-condemns a new port).

Artifacts: results/runs/<run_id>.json for the 22 run_ids in the tables above; bt.py one reports per cell in results/bt_one/hmatrend_<SYMBOL>_1h.md; parity tool code/_hma_trend_parity.py; engine audit code/_hma_trend_audit.py; sources of record code/hma_trend_sources/ with MANIFEST.json.
