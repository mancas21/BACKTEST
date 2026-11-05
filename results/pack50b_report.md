# The claude2 fifty-prompt pack: nothing survives, and most of it has no gross edge

Source document: `Downloads/crypto_strategy_prompts_50-claude2.md` — fifty numbered
prompts, twenty-five scalping (S01-S25) and twenty-five day trading (D01-D25), each
naming its own market and timeframe. Adapter `pack50b`
(`code/pack50b_engine.py`, `code/pack50b_strats.py`, on the frozen
`code/pack50_core.py` execution core that the pack50 campaign pinned).

## How the numbers were produced

- A rule is evaluated on a closed bar; the fill is the **next bar's open**. A signal
  exit also fills at the next open. Stops and targets fill intrabar, and when one bar
  contains both, the **stop fills first**. Flat-by-time rules (S07, D07, D11) fire on
  the first bar at/after the deadline and fill one bar late.
- Costs are the pack's own block, uniform as the prompt header declares: **5 bps fee
  and 2 bps slippage per side (14 bps round trip)**. The same signals are re-run at
  the repo gate cost (5.0 + 0.5 bps) and once more with **zero** cost inside the same
  artifact, so "no edge" and "cost ate the edge" are separated by measurement.
- Sizing is **full-equity compounding**, the repo-wide pack convention, so this report
  is comparable to the claude1 pack report. The prompt header's "1% of equity per
  trade" would rescale returns and drawdowns but not profit factor, win rate, trade
  count or the cost share.
- Perpetual **funding is charged** at every settlement instant on the open notional,
  priced at the close of the bar containing the settlement.
- The split is 70/30 on **entry time**; buy & hold covers the same window.
- `code/_pack50b_audit.py` pins fills, tie-breaks, fees, funding sign, the pair leg
  split, the resampler, the new indicators (stochastic, CCI, OBV, the TTM linear
  regression residual, Ichimoku), the stateful pair targets, and a
  **no-stopless-entry** check: an entry may not fire on a bar whose stop level is
  undefined. That last group exists because two ports were caught and fixed by it
  mid-campaign (a negated-NaN downtrend gate in S02 and an ATR-warmup entry in S13
  both produced stopless positions); after the fix every artifact was re-created, so
  every run_id below covers the final engine bytes.
- Timeframes map to the taker kline files as in the pack50 campaign: 1m and 3m from
  the 1m files (3m resampled), 5m native, 15m and 30m from the 15m files (30m
  resampled), 1h native. "SPCX" is read as the SPXUSDT series on disk, which exists
  only as plain 1m/1h klines; its 5m/15m prompts resample from the 1m file.

Gates, applied inside each artifact: G1 profit factor above the repo threshold; G2 at
least thirty closed trades; G3 both halves of the split profitable on profit factor;
G4 profitable in at least two thirds of the calendar years traded; G5 beats buy & hold;
G6 the result survives removing its five best trades.

## What could not be run

Four prompts are **NO DATA**, not failures: S08 and S23 (NVDA 5m and 1m scalps), D08
and D18 (NVDA 15m and 1h day strategies). There is no NVDA series on this machine, so
no number is estimated, carried over from the author, or proxied. This is the same
class of exclusion as the claude1 pack's S34 and S49.

## Headline

**None of the forty-six runnable prompts clears all six gates.** Two prompts reach
four of the six — D05, the TTM squeeze release on SUI 1h, and D13, the Fibonacci
pullback on SUI 30m — and both fail exactly the profit-factor gate and the
concentration gate. D05 nets 39.80% with a profit factor of
1.073; remove its five best trades and the net becomes
-3.75% of starting capital. D13 nets
13.11% with a profit factor of 1.099 and a
concentration net of -10.77%. Two more prompts reach
three of six: D04 (Ichimoku on HYPE 30m, 1.038 on
1512 trades, beaten by buy & hold 135.56%) and
D23 (the daily pivot bounce on SUI 15m, 1.065 on
87 trades). Nothing else gets past two.

## The table

`conc net %` is the net result with the five best trades removed, as a share of starting
capital. `repo PF` is the same signals at the repo gate cost. `zero PF` is the same
signals with no cost at all — the gross edge, before the cost block. An `n/a` in the
split columns means that half of the split contained **no trades**, so the factor is
undefined rather than zero.

| Prompt | rule | market | n | net % | PF | IS PF | OOS PF | B&H % | conc net % | funding $ | repo PF | zero PF | fails | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S01 | EMA 9/21 cross, EMA200 filter | BTCUSDT 1m | 26029 | -100.00 | 0.043 | 0.04 | 0.03 | 23.88 | -100.47 | 0.48 | 0.089 | 1.031 | G1 G3 G4 G5 G6 | `c511476869a19407` |
| S02 | daily-VWAP pullback | ETHUSDT 5m | 6147 | -99.98 | 0.512 | 0.51 | 0.48 | -7.47 | -103.88 | -9.89 | 0.593 | 1.029 | G1 G3 G4 G5 G6 | `61dcfd98afb6db8e` |
| S03 | RSI(2) mean reversion | SOLUSDT 1m | 54708 | -100.00 | 0.116 | 0.12 | 0.08 | -33.35 | -101.26 | -0.62 | 0.209 | 1.091 | G1 G3 G4 G5 G6 | `2981e2a8fd579f43` |
| S04 | Bollinger squeeze breakout | HYPEUSDT 5m | 1944 | -97.51 | 0.638 | 0.64 | 0.54 | 134.09 | -107.13 | 6.81 | 0.680 | 0.875 | G1 G3 G4 G5 G6 | `e694afa7a928495d` |
| S05 | Donchian 20 + volume | SUIUSDT 3m | 16459 | -100.00 | 0.580 | 0.58 | 0.42 | -54.41 | -105.34 | 0.36 | 0.646 | 0.964 | G1 G3 G4 G5 G6 | `4149b92e3d838e8a` |
| S06 | StochRSI pullback | JUPUSDT 5m | 7100 | -100.00 | 0.772 | 0.77 | 0.60 | -67.25 | -111.95 | -1.60 | 0.827 | 0.996 | G1 G3 G4 G5 G6 | `8fce3d5fee0bb443` |
| S07 | NY-open range breakout | BTCUSDT 5m | 722 | -69.43 | 0.555 | 0.57 | 0.49 | 24.27 | -79.20 | -10.11 | 0.616 | 0.914 | G1 G3 G4 G5 G6 | `6031daf0766848bb` |
| S09 | MACD zero-cross + ADX | ETHUSDT 1m | 44716 | -100.00 | 0.097 | 0.10 | 0.12 | -8.42 | -100.85 | -0.37 | 0.180 | 1.026 | G1 G3 G4 G5 G6 | `85c005ff28968d7e` |
| S10 | Supertrend + 1h EMA50 slope | SOLUSDT 5m | 4324 | -99.89 | 0.734 | 0.73 | 0.56 | -32.98 | -112.95 | -57.25 | 0.777 | 0.962 | G1 G3 G4 G5 G6 | `d6801d06e5155c64` |
| S11 | Bollinger range fade, ADX<18 | BTCUSDT 1m | 4518 | -99.83 | 0.076 | 0.08 | 0.04 | 23.88 | -100.85 | 1.72 | 0.123 | 0.968 | G1 G3 G4 G5 G6 | `db8ebc131d05f660` |
| S12 | momentum ignition continuation | HYPEUSDT 1m | 7373 | -100.00 | 0.287 | 0.29 | 0.29 | 132.52 | -102.62 | 2.52 | 0.375 | 0.967 | G1 G3 G4 G5 G6 | `21c1e477f9e6c349` |
| S13 | VWAP deviation fade | SUIUSDT 5m | 12684 | -100.00 | 0.145 | 0.15 | 0.06 | -54.50 | -108.90 | 0.91 | 0.160 | 0.235 | G1 G3 G4 G5 G6 | `4d370e11fe7f532d` |
| S14 | EMA ribbon + RSI(7) | JUPUSDT 3m | 13238 | -100.00 | 0.626 | 0.63 | 0.52 | -67.34 | -104.49 | -23.60 | 0.697 | 1.000 | G1 G3 G4 G5 G6 | `074d282d7cadaff6` |
| S15 | EMA 20 pullback | SPXUSDT 5m | 2008 | -95.81 | 0.585 | 0.59 | 0.54 | 18.89 | -101.81 | 6.98 | 0.649 | 0.943 | G1 G3 G4 G5 G6 | `53ce51b561957871` |
| S16 | ETH/BTC z-score pair | ETHUSDT+BTCUSDT 15m | 1137 | -78.11 | 0.554 | 0.56 | 0.48 | 8.39 | -87.57 | 38.95 | 0.628 | 1.032 | G1 G3 G4 G5 G6 | `684df1405e68bfaf` |
| S17 | SOL/ETH Bollinger pair | SOLUSDT+ETHUSDT 15m | 1803 | -92.30 | 0.536 | 0.55 | 0.35 | -20.13 | -99.21 | 52.64 | 0.603 | 0.989 | G1 G3 G4 G5 G6 | `989d38ba2631f78e` |
| S18 | Keltner breakout | BTCUSDT 3m | 8747 | -100.00 | 0.613 | 0.61 | 0.53 | 23.88 | -109.64 | -11.85 | 0.681 | 1.002 | G1 G3 G4 G5 G6 | `98a9b4664a15fef7` |
| S19 | liquidity sweep reversal | ETHUSDT 1m | 18087 | -100.00 | 0.268 | 0.27 | 0.28 | -8.42 | -102.88 | -2.96 | 0.370 | 0.938 | G1 G3 G4 G5 G6 | `f5fe3b4e4d4c4adc` |
| S20 | Heikin-Ashi flip | SOLUSDT 3m | 26328 | -100.00 | 0.526 | 0.53 | 0.42 | -33.35 | -103.99 | -9.80 | 0.612 | 1.002 | G1 G3 G4 G5 G6 | `beb15589cdb2277b` |
| S21 | CCI pullback | HYPEUSDT 15m | 1067 | -69.62 | 0.877 | 0.88 | 0.87 | 135.56 | -88.79 | 8.18 | 0.907 | 1.038 | G1 G3 G4 G5 G6 | `69254b303da0d346` |
| S22 | conviction candle through EMA20 | SUIUSDT 1m | 120659 | -100.00 | 0.296 | 0.30 | 0.17 | -54.41 | -103.67 | 1.10 | 0.383 | 0.985 | G1 G3 G4 G5 G6 | `1c63d931583b8f13` |
| S24 | NR4 inside-bar breakout | BTCUSDT 5m | 6032 | -99.98 | 0.401 | 0.40 | 0.33 | 24.27 | -104.38 | -6.01 | 0.474 | 0.963 | G1 G3 G4 G5 G6 | `763cca187478544f` |
| S25 | Bollinger mean reversion | SPXUSDT 1m | 7193 | -99.99 | 0.560 | 0.56 | 0.44 | 18.89 | -106.71 | 1.38 | 0.635 | 1.017 | G1 G3 G4 G5 G6 | `9ab5abaa4b0c0aa5` |
| D01 | Supertrend(10,3) + EMA200 | BTCUSDT 1h | 215 | -57.56 | 0.562 | 0.50 | 0.91 | 24.30 | -69.24 | -23.68 | 0.585 | 0.681 | G1 G3 G4 G5 G6 | `9d312a35957eeb02` |
| D02 | Donchian 55 breakout | ETHUSDT 30m | 832 | -9.10 | 0.990 | 1.04 | 0.81 | -7.52 | -47.84 | -245.68 | 1.016 | 1.124 | G1 G3 G4 G5 G6 | `579192b36954b8a7` |
| D03 | EMA 21/55 cross + ADX | SOLUSDT 1h | 77 | -26.89 | 0.751 | 0.78 | 0.67 | -34.95 | -47.51 | -31.13 | 0.767 | 0.827 | G1 G3 G4 G6 | `76c9378059a7a72f` |
| D04 | Ichimoku cloud breakout | HYPEUSDT 30m | 1512 | 82.93 | 1.038 | 1.06 | 1.01 | 135.56 | -31.96 | -63.60 | 1.069 | 1.203 | G1 G5 G6 | `e5f90f77104b1424` |
| D05 | TTM squeeze release | SUIUSDT 1h | 328 | 39.80 | 1.073 | 1.06 | 1.11 | -59.08 | -3.75 | -10.84 | 1.095 | 1.184 | G1 G6 | `86f4ca910fe12ca5` |
| D06 | RSI pullback in trend | JUPUSDT 30m | 861 | -82.51 | 0.902 | 0.94 | 0.76 | -66.15 | -113.67 | -87.94 | 0.917 | 0.970 | G1 G3 G4 G5 G6 | `7c5a47a6082ca6a8` |
| D07 | previous-day high/low breakout | SPXUSDT 1h | 477 | -42.85 | 0.957 | 1.09 | 0.57 | -22.98 | -127.34 | -120.43 | 0.968 | 1.009 | G1 G3 G4 G5 G6 | `74525c721c1e5df7` |
| D09 | anchored VWAP reclaim | BTCUSDT 15m | 1271 | -87.72 | 0.601 | 0.60 | 0.62 | 24.30 | -97.23 | -19.28 | 0.654 | 0.918 | G1 G3 G4 G5 G6 | `6e6b695e5a02533c` |
| D10 | MACD cross + EMA200 | ETHUSDT 1h | 456 | -66.28 | 0.857 | 0.88 | 0.75 | -7.52 | -100.70 | -73.75 | 0.872 | 0.936 | G1 G3 G4 G5 G6 | `43ddc403102a57ee` |
| D11 | Asian range breakout | SOLUSDT 15m | 653 | -42.25 | 0.896 | 0.95 | 0.69 | -32.75 | -80.28 | -65.84 | 0.931 | 1.080 | G1 G3 G4 G5 G6 | `e2bc291d5aadd515` |
| D12 | Parabolic SAR + ADX | HYPEUSDT 1h | 408 | -87.68 | 0.768 | 0.77 | 0.79 | 134.90 | -125.75 | -35.29 | 0.778 | 0.817 | G1 G3 G4 G5 G6 | `3d301e9901f798ee` |
| D13 | Fibonacci pullback | SUIUSDT 30m | 113 | 13.11 | 1.099 | 1.05 | 1.27 | -54.12 | -10.77 | -11.32 | 1.129 | 1.245 | G1 G6 | `7bc4da0aec131154` |
| D14 | Chandelier trend follower | JUPUSDT 1h | 384 | -8.99 | 0.990 | 1.14 | 0.73 | -65.35 | -141.61 | -214.62 | 1.002 | 1.046 | G1 G3 G4 G6 | `e100aa2c68ea7f98` |
| D15 | range reversion, ADX<20 | BTCUSDT 30m | 118 | -24.04 | 0.597 | 0.71 | 0.31 | 24.30 | -34.96 | -1.28 | 0.635 | 0.804 | G1 G3 G4 G5 G6 | `57ae06f29347c04d` |
| D16 | ETH/BTC ratio trend pair | ETHUSDT+BTCUSDT 1h | 356 | -35.74 | 0.592 | 0.66 | 0.34 | 8.39 | -41.77 | -15.16 | 0.670 | 1.074 | G1 G3 G4 G5 G6 | `f4b9c3dec4b63f0c` |
| D17 | SOL/BTC z-score pair | SOLUSDT+BTCUSDT 1h | 220 | -43.52 | 0.667 | 0.73 | 0.47 | -8.02 | -60.82 | 129.29 | 0.698 | 0.827 | G1 G3 G4 G5 G6 | `77ea10f315b34a45` |
| D19 | previous-day sweep reversal | BTCUSDT 1h | 459 | -44.90 | 0.743 | 0.80 | 0.55 | 24.30 | -62.51 | 20.60 | 0.794 | 1.025 | G1 G3 G4 G5 G6 | `be9ac050152cedc4` |
| D20 | OBV volume breakout | ETHUSDT 15m | 1809 | -79.55 | 0.881 | 0.90 | 0.77 | -7.52 | -98.31 | -65.22 | 0.920 | 1.082 | G1 G3 G4 G5 G6 | `65ba854ef5ab151c` |
| D21 | fast Supertrend(7,2.5) | SOLUSDT 30m | 596 | -67.79 | 0.811 | 0.84 | 0.68 | -32.75 | -83.41 | -80.82 | 0.838 | 0.945 | G1 G3 G4 G5 G6 | `f2a6b91da259748d` |
| D22 | Keltner squeeze breakout | HYPEUSDT 15m | 418 | -52.52 | 0.776 | 0.76 | 0.83 | 135.56 | -68.52 | 17.23 | 0.808 | 0.945 | G1 G3 G4 G5 G6 | `0152f94b96b229f7` |
| D23 | daily pivot bounce | SUIUSDT 15m | 87 | 4.75 | 1.065 | 1.34 | 0.43 | -54.12 | -22.15 | -2.13 | 1.105 | 1.268 | G1 G3 G6 | `71bf4c777fb2f104` |
| D24 | stochastic cross + EMA200 | JUPUSDT 15m | 1614 | -91.04 | 0.811 | 0.81 | 0.85 | -66.15 | -109.30 | -49.39 | 0.844 | 0.986 | G1 G3 G4 G5 G6 | `dc1de6fce2ba4295` |
| D25 | EMA ribbon trend | SPXUSDT 15m | 286 | -63.78 | 0.677 | 0.65 | 0.77 | 18.89 | -78.45 | 12.01 | 0.699 | 0.787 | G1 G3 G4 G5 G6 | `a5ef053c86b989e7` |

## The scalping block has no edge to destroy

The twenty-three runnable scalping prompts are not a cost story — they are a
**gross-edge story**. With fees and slippage switched OFF, the best profit factor in
the whole block is S03, the RSI(2) reversion on SOL 1m, at 1.091;
every other prompt sits at or below 1.038 (S21) and most are under
1.05. Nothing in the block clears the repo threshold before a single fee is charged.
The pack's 14 bps round trip then turns marginal gross factors into ruin: most 1m and
3m accounts end the window at −100% (S01, S03, S05, S09, S12, S13, S14, S18, S19, S20,
S22 all read −100.0% net), with trade counts from 54708 (S03) to
120659 (S22). S13 is the sharpest single finding: the VWAP deviation fade
on SUI 5m carries a profit factor of 0.235 with cost switched off
— it is a net-negative rule even for free. S02, the daily-VWAP pullback on ETH 5m,
trades 6147 times for -99.98% net against a zero-cost
factor of 1.029.

The three pairs sit in the same block. S16 (ETH/BTC z-score, 15m) and S17 (SOL/ETH
Bollinger, 15m) net -78.11% and -92.30% with
zero-cost factors of 1.032 and 0.989;
funding lands at 38.95 and 52.64 dollars
(negative funding means the book collected it).

## The day-trading block: a little gross edge, none of it priced

Six day-trading prompts carry a zero-cost factor above 1.05 — D02 at
1.124, D05 at 1.184, D13 at
1.245, D23 at 1.268, D20 at
1.082 and D11 at 1.080 — and three of those
stay above 1.0 after the pack's own costs. The strongest net profit factor in the
entire pack is D13 at 1.099; D05 and D23 follow at
1.073 and 1.065. All three are above
water in the half of the split that matters (OOS factors 1.11 and
1.27 for the D05/D13 pair, D23's second half at
0.43), D05 and D13 are green in every year they trade — and all three
still fail the factor gate and die on concentration. G5 tells the same story from the
other side: five prompts beat buy & hold (D03, D05, D13, D14, D23), and they do it
while the underlying market fell — SUI buy & hold is -54.12% over
the window — not while out-trading an up market.

Funding is a real but secondary drag on this block: the two SUI survivors are roughly
flat on it (-10.84 and -11.32 dollars), the
ETH Donchian book D02's funding line reads -245.68 dollars and the
JUP Chandelier book D14's reads -214.62 (negative funding means
the book collected it).

## The single most useful number in the pack

`zero PF` against `PF` is the point of measuring the control. In the claude1 pack the
zero-cost control exposed six cost-destroyed winners; in this pack it exposes almost
nothing to destroy. Two prompts — D23 at 1.268 and D13 at
1.245 — carry a gross factor above the repo threshold before
costs, and both fall under it at the pack's own block (1.065 and
1.099). Everything else was never above the threshold at any
cost level. The verdicts are signal verdicts, not cost verdicts.

## Data caveats that bound these conclusions

- Every crypto market here is the Binance USDT-M perpetual read from the taker kline
  files, which start in October 2024 (HYPE later, JUP from its listing, SPX plain
  klines only). Two calendar years is the longest window any artifact sees, and
  S15/S25/D25 see roughly three months of SPX — the prompt file itself flags SPCX as
  exploratory, and their G4 year gate fails on a single-year sample.
- 3m and 30m bars are resampled from 1m and 15m files on the UTC grid; the resampler
  is pinned against the core's own in the audit.
- Four prompts are unrunnable without NVDA data and are excluded, not modelled.

## Reproduce

    python code/_pack50b_audit.py
    python code/_pack50b_run_all.py
    python code/vrun.py pverify --ids <ids from results/_pack50b_ids.json> --workers 2
    python code/vrun.py guard --report results/pack50b_report.md
