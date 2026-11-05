# SMQE v2 (Smart Money Quant Engine) — audit and backtest report

Date of record: 2026-10-24 (the last bar in every cited input); engine revision 2026-10-25 (methodology-audit corrections: flip sizing now uses the declared pre-flip equity — the original computed it and never used it — plus the fee-metric fixes and the next-open / exposure / in-market methodology views measured inside every artifact). Source of record: `code/smqe_v2_strategy.pine` — the attached `Downloads/fingrad-entry scanner/smqe_v2_strategy.pine` copied byte-identical (sha256 `031730fabb9cc289...`). Engine: `code/smqe_engine.py` (adapter `smqe`, engine version `smqe-1`). Every number below is read from a persisted artifact in `results/runs/` cited by its `run_id`. The known-answer audit is `code/_smqe_audit.py` -> `results/smqe_audit_known_answers.txt`: forty-four checks, ALL PASS, run on the exact engine bytes before any campaign artifact was produced. Across its life the audit has caught one real executor bug (the TP1 partial never reduced the position), one cost-constant bug, and one convention bug (flip sizing) that a zero-fee test case could not see.

## VERDICT: KILLED — no swept configuration passes the repo gates. One cell (SUI 1h) clears every measurable gate and is recorded as SUSPENDED, not validated.

## What the Pine actually is (static audit)

The strategy ships three engines — Smart Money Concepts structure, MA Order Blocks, and the CVRMD signal core — but EVERY confluence gate that would connect the first two to trading is an opt-in input that defaults to false, and the Pine's own tooltips say the gates are not part of the validated CVRMD backtest. The shipped trading logic is the CVRMD core alone:

- MACD divergence: histogram divergence on pivots of three bars each side (strict on both sides — ties produce no pivot), pivot separation between five and sixty bars, price making a lower low while the histogram makes a higher low for longs, mirrored for shorts, evaluated on the bar the pivot is CONFIRMED, which is three bars after the pivot itself.

- VWAP band: session VWAP (UTC-day anchor, hlc3, volume-weighted, Welford recursion as written) minus one volume-weighted standard deviation; the bar's low must trade at or below the band and close back above it (mirrored above for shorts), after at least five bars in the anchor and a nonzero dispersion.

- CVD slope: cumulative close-location-value times volume, smoothed by an EMA of three, compared with its value five bars ago; strictly positive for longs, strictly negative for shorts.

- RSI arms: RSI over fourteen bars at or below thirty-five (or below the fifty line and rising) for longs; at or above sixty-five (or above the fifty line and falling) for shorts.

Execution: entries and reversals FILL AT THE SIGNAL BAR'S CLOSE (process_orders_on_close=true). Stop distance is the greater of one-and-a-half times ATR over fourteen bars and zero point two percent of price (the Min Stop floor; the repo's earlier CVRMD port had no floor). TP1 exits half the position at a limit set at the VWAP when it sits beyond the close, else at one-and-a-half R; TP2 exits the remainder at two R; both carry the same frozen stop. An opposite signal while positioned closes what remains and reopens the other side at the same close. Sizing is one percent of equity per stop distance, capped at three times notional, compounding. Risk devices: a constant perp funding ledger at one hundredth of a percent per eight hours (longs pay, shorts receive; the Pine books it OUTSIDE strategy equity — it feeds the daily breaker and the reported net return, not sizing or the killswitch), a three percent daily-loss breaker that halts entries for the rest of the UTC day, and a thirty percent equity-DD killswitch that halts entries permanently.

Costs: the repo gate is a fee of five basis points plus half a basis point of slippage per side — an eleven basis point roundtrip. The Pine header itself declares six hundredths of a percent commission per side with zero slippage. Every artifact measures all three views on the same signals (repo as primary, pine and zero as in-artifact controls; the drag column is the zero-cost net return minus the primary net return, with funding charged identically in all three). Initial capital ten thousand USDT, compounding. Not modelled, by declared convention: TV margin and the Premium bar magnifier (intra-bar sequencing is resolved stop-first on ties, the repo convention).

## Full history (data start through the last bar), repo costs

### 1h

| symbol | run_id | n | net % | PF | maxDD % | best5 % PnL | periods green | B&H % | beats B&H | killswitch |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| BTC | `0abbe9f0ab7cd72d` | 95 | -17.30 | 0.666 | 19.78 | — | 1/3 | +706.3 | no | — |
| ETH | `e2f94738b8156bd7` | 94 | -1.63 | 0.968 | 15.13 | — | 1/3 | +1522.6 | no | — |
| SOL | `70cb5ae94c926993` | 83 | +14.25 | 1.404 | 7.48 | 63.6 | 2/3 | +2920.3 | no | — |
| XRP | `12cac307d46702ba` | 100 | +1.50 | 1.036 | 12.19 | 533.9 | 2/3 | +527.8 | no | — |
| BNB | `70ff57384af3d7fe` | 86 | +6.12 | 1.141 | 7.29 | 148.2 | 3/3 | +2825.1 | no | — |
| LINK | `6f43a905a5d8fd41` | 97 | -14.33 | 0.703 | 18.65 | — | 0/3 | +314.3 | no | — |
| ADA | `68e939b9d65afddf` | 89 | -7.50 | 0.834 | 14.68 | — | 1/3 | +282.0 | no | — |
| DOGE | `7695b6918a88a8ed` | 73 | -14.68 | 0.590 | 18.28 | — | 0/3 | +1976.3 | no | — |
| AVAX | `d4e020ead976a627` | 91 | -1.33 | 0.970 | 12.58 | — | 2/3 | +118.1 | no | — |
| NEAR | `00b0cf22b3486805` | 83 | -8.83 | 0.789 | 9.49 | — | 1/3 | +304.8 | no | — |
| HYPE | `eb1ce2c17405e151` | 15 | +4.16 | 1.688 | 3.13 | 192.5 | 2/3 | +176.4 | no | — |
| SPX | `6f091294ee831016` | 21 | -4.23 | 0.624 | 4.66 | — | 0/3 | -29.1 | yes | — |
| SUI | `9d7ad0db1d295b42` | 49 | +16.06 | 1.828 | 5.08 | 59.0 | 3/3 | -31.0 | yes | — |
| JUP | `d0e871302d647849` | 24 | +2.20 | 1.204 | 4.96 | 359.9 | 1/3 | -68.0 | yes | — |

### 15m

| symbol | run_id | n | net % | PF | maxDD % | zero-cost % | PF zero | drag pp | killswitch |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| BTC | `81ef917aed4e3eb2` | 124 | -29.35 | 0.530 | 30.03 | -27.34 | 0.829 | +2.0 | KILLED |
| ETH | `5b3074a01d05da16` | 212 | -28.95 | 0.745 | 30.12 | -13.52 | 0.929 | +15.4 | KILLED |
| SOL | `28eb57a6b5b54e2a` | 247 | -27.98 | 0.764 | 30.04 | -18.29 | 0.885 | +9.7 | KILLED |
| XRP | `b1f1fb16c7ae2c50` | 317 | -27.27 | 0.821 | 30.36 | +13.64 | 1.077 | +40.9 | KILLED |
| HYPE | `36862310e24b319c` | 76 | -3.26 | 0.922 | 11.34 | +5.47 | 1.149 | +8.7 | — |
| SUI | `76853eeb7af4b544` | 222 | -8.13 | 0.932 | 21.14 | +18.25 | 1.157 | +26.4 | — |
| JUP | `2d49a851a590446d` | 102 | -16.82 | 0.689 | 23.73 | -7.41 | 0.853 | +9.4 | — |

### 5m (taker data directory, 2024-10 onward)

| symbol | run_id | n | net % | PF | maxDD % | zero-cost % | PF zero | drag pp | killswitch |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| BTC | `0e9a3f7f70efb2f0` | 91 | -27.47 | 0.420 | 30.47 | -0.30 | 0.996 | +27.2 | KILLED |
| ETH | `a52735f88dd0dbbf` | 155 | -29.02 | 0.655 | 30.16 | +5.55 | 1.067 | +34.6 | KILLED |
| SOL | `89f0bbaef14cbf2a` | 103 | -30.35 | 0.508 | 30.34 | -8.04 | 0.884 | +22.3 | KILLED |
| XRP | `eaa5b8be2df1ca88` | 159 | -25.38 | 0.706 | 26.79 | +11.23 | 1.143 | +36.6 | — |
| SUI | `d0f0aea1ecbd94e0` | 156 | -22.55 | 0.729 | 28.69 | +6.27 | 1.083 | +28.8 | — |
| HYPE | `ae7b79caeda1606b` | 112 | -20.36 | 0.711 | 23.30 | -0.35 | 0.994 | +20.0 | — |
| JUP | `d5e4420c0f2fb12e` | 130 | +1.54 | 1.019 | 14.42 | +29.02 | 1.379 | +27.5 | — |

JUPUSDT exists only in the taker data directories (its 1h and 15m runs there start 2024-10, so they are their own window, not the multi-year history the majors carry); the 5m sweep runs on the taker directory for every symbol because the harness-native 5m files hold only about two months.

## The Pine's own default window (sim start 2024-01-01), repo costs

| symbol | run_id | n | net % | PF | maxDD % | best5 % PnL | periods green | B&H % | beats B&H | killswitch |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| BTC | `4f0b8f193070ec05` | 38 | -8.53 | 0.611 | 11.93 | — | 0/3 | +89.7 | no | — |
| ETH | `97a5b202c9083168` | 40 | +5.97 | 1.369 | 4.67 | 138.1 | 2/3 | +3.1 | yes | — |
| SOL | `01423a6bddefad0e` | 36 | +11.61 | 1.815 | 5.82 | 76.7 | 2/3 | -0.4 | yes | — |
| XRP | `816c57d6b1773bdc` | 45 | +1.02 | 1.050 | 8.15 | 784.2 | 2/3 | +107.8 | no | — |
| BNB | `851e32bc29ce2789` | 36 | -2.63 | 0.858 | 6.66 | — | 1/3 | +133.7 | no | — |
| LINK | `8110fc841638b620` | 41 | -12.30 | 0.456 | 13.72 | — | 1/3 | -23.3 | yes | — |
| ADA | `4085c06e69fe8351` | 42 | -2.63 | 0.882 | 7.16 | — | 1/3 | -65.2 | yes | — |
| DOGE | `e086b95d285b32fe` | 37 | -6.77 | 0.639 | 9.57 | — | 1/3 | -13.7 | yes | — |
| AVAX | `4bca4879987e8479` | 41 | -8.79 | 0.629 | 12.42 | — | 1/3 | -77.1 | yes | — |
| NEAR | `8e3535be0e16fc7e` | 45 | -7.79 | 0.687 | 8.24 | — | 1/3 | +19.8 | no | — |
| HYPE | `409f70ef1c686662` | 15 | +4.16 | 1.688 | 3.13 | 192.5 | 2/3 | +176.4 | no | — |
| SPX | `50e947ec96e952f7` | 21 | -4.23 | 0.624 | 4.66 | — | 0/3 | -29.1 | yes | — |
| SUI | `f87748827795779a` | 39 | +14.29 | 1.960 | 5.08 | 65.3 | 3/3 | +21.0 | no | — |

At 15m in the same window every symbol is also net-negative (PF under one on all six).

## Why each apparent survivor dies

- **SOL 1h, full history** (`70cb5ae94c926993`) clears the trade gates — PF 1.404, n 83, best five trades 63.6% of PnL (net without them +36.37%), two of three period-thirds green, frozen 2023 split train +3.85% / test +10.00% (PF 1.390, n 61) — and loses the buy-and-hold comparison by two orders of magnitude: B&H over the same bars is +2920.3%. The repo rule is explicit: that is not alpha. The Pine-window SOL cell (`01423a6bddefad0e`, PF 1.815, n 36) does beat its window's B&H, but on thirty-six trades with the best five carrying 76.7% of PnL — the same handful-of-trades shape that killed the cbpack 1h survivors.

- **BNB 1h** (`70ff57384af3d7fe`) fails profit factor (1.141) and concentration together: best five trades 148.2% of PnL, net without them -48.21%.

- **XRP 1h** (`12cac307d46702ba`) fails profit factor (1.036) and is the worst concentration in the whole sweep: best five trades 533.9% of PnL, net without them -433.89%.

- **ETH 1h in the Pine window** (`97a5b202c9083168`) shows PF 1.369 with its best five trades carrying 138.1% of PnL; remove them and the book is -38.07%.

- **15m has no gross edge to rescue.** At zero cost the PF is 0.829 on BTC (`81ef917aed4e3eb2`), 0.929 on ETH and 0.885 on SOL — the signals themselves are gross-negative on the majors, unlike the cbpack pattern where a gross edge existed and costs destroyed it. Four of the six 15m cells (BTC, ETH, SOL, XRP) tripped the thirty percent equity-DD killswitch.

- **JUP 1h** (`d0e871302d647849`, taker data from 2024-10) is the closest miss after SUI: PF 1.204 with net +2.20% against a buy-and-hold of -68.0% — but it fails the trade floor (n 24, flagged INSUFFICIENT_SAMPLE) and the concentration gate (best five trades 359.9% of PnL; without them -259.87%). It is a handful of trades on a falling coin, not an edge.

- **5m (all seven taker symbols): every cell fails.** The best PF is JUP at 1.019 (`d5e4420c0f2fb12e`) — under every gate, and its best five trades carry 673.0% of PnL. BTC, ETH and SOL tripped the thirty percent killswitch; zero-cost PF spans 0.996 to 1.379, and only JUP/XRP/SUI carry a positive gross book at this timeframe.

## The one cell that is not falsified: SUI 1h — SUSPENDED

Full history `9d7ad0db1d295b42`; Pine window `f87748827795779a`.

- Full history: net +16.06%, PF 1.828, n 49 (win rate 46.9%), maxDD 5.08%, funding paid +6.33 USD, cost drag +2.93pp.

- Period thirds +4.05% / +5.14% / +6.14% — three of three green — and every calendar year in its history is green. Both sides contribute (the artifact's side table shows positive PnL on longs and shorts alike). Best five trades 59.0% of PnL.

- It beats buy-and-hold over the same bars (-31.0%) — **but the exposure-matched comparator inverts that claim**: the strategy is in position only 2.37% of bars, and passively holding the asset over EXACTLY those bars returns +37.69% — the strategy UNDERPERFORMS its own in-market passive by -21.63pp. Its win over raw buy-and-hold is cash drag on a falling coin, not entry timing. (The comparator is long-only; short-side alpha is not credited by it.)

- Execution-timing sensitivity: with identical signals filled at the NEXT bar's open instead of the signal close, the PF moves 1.825 vs 1.828 and the net return by +0.03pp — the result does not depend on the same-close convention.

- The Pine window confirms the direction (+14.29%, PF 1.960, n 39) but does NOT beat buy-and-hold there (+21.0%).

Why SUSPENDED rather than a pass:

1. **No out-of-sample is possible on this data.** SUI's kline history on disk starts 2023-05-03, so the frozen 2023 split is vacuous (the artifact records zero for both legs) and the whole sample is one regime. This repo already killed the CVRMD SUI edge once for being recent and n-sensitive — this is the same signal core.

2. **It is the maximum over the swept grid.** The full campaign measures forty-seven cells (three timeframes, two windows, up to fourteen symbols) and this cell is the best of them; the multiple-testing haircut applies.

3. **Small sample.** Forty-nine closed trades over three and a half years.

The forward path, if anyone wants it, is the one the neutral XRP bot took: a paper bot measuring the forward window before any capital claim. Nothing in this record authorises a deployment.

## Provenance

- Adapter registered in `code/vrun.py` (`smqe`); the engine `code/smqe_engine.py` and the Pine source of record are hashed into every run_id. The sweep is 1h (harness data, fourteen symbols), 15m (harness data six symbols plus JUP from the taker directory), and 5m (taker directory, seven symbols — the harness-native 5m files are two-month stubs). One-minute bars stay out by design: the session-VWAP divergence core is out of its design range there and every 1m campaign in this repo has been ruin once costs are charged.

- All CURRENT campaign artifacts verify bit-for-bit: forty-seven of forty-seven under `pverify --strategy smqe`, zero stale. The engine revision of 2026-10-25 superseded an earlier generation of the same forty-seven cells plus one smoke artifact (`f3261c37e880f844`, a pre-correction cost constant); the superseded files verify REFUSED (engine drift) by design, are cited nowhere, and are kept under the append-only rule with the supersession recorded in `code/_engine_lock.json` (known_superseded).

- `results/runs/_matrix_smqe.csv` holds the second pass (the Pine window); the full-history run_ids are in the tables above, which are rendered from the artifacts themselves by `code/_smqe_build_report.py`.

- No TradingView numbers were used anywhere: the Pine's own tester output was never quoted, the port is the evidence.

