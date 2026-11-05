# The fifty-prompt pack: what survives its own cost block

Source document: `Downloads/50_strategies_crypto-claude1.md` — fifty numbered prompts,
each naming its own market and timeframe. Adapter `pack50`
(`code/pack50_engine.py`, `code/pack50_core.py`, `code/pack50_strats.py`).

## How the numbers were produced

- A rule is evaluated on a closed bar; the fill is the **next bar's open**. A signal
  exit also fills at the next open. Stops and targets fill intrabar, and when one bar
  contains both, the **stop fills first**.
- Costs are the pack's own block, read from the prompt text: taker fee per side (wider
  on the three alts) plus slippage per side (wider on alts and on scalp timeframes).
  The same signals are also re-run at the repo gate cost inside the same artifact, and
  once more with **zero** cost, so "no edge" and "cost ate the edge" are separated by
  measurement rather than opinion.
- Perpetual **funding is charged** at every settlement instant on the open notional,
  priced at the close of the bar containing the settlement. The JUP funding history was
  missing from disk and was fetched from Binance's public endpoint for this campaign
  (`code/fetch_jup_funding.py`); every artifact states whether funding was charged.
- The split the prompt asks for is applied on **entry time**; buy & hold covers the same
  window.
- Fills, tie-breaks, fees, funding sign, the pair leg split, the resampler and the
  indicators are pinned by `code/_pack50_audit.py`. Every group passes on the bytes that
  produced these artifacts.
- Every artifact below reproduced **bit-for-bit** in a fresh process under
  `python code/vrun.py pverify`.

Gates, applied inside each artifact: G1 profit factor above the repo threshold; G2 at
least thirty closed trades; G3 both halves of the split profitable on profit factor;
G4 profitable in at least two thirds of the calendar years traded; G5 beats buy & hold;
G6 the result survives removing its five best trades.

## What could not be run

Two prompts are **NO DATA**, not failures: S34 (NVDA/BTC) and S49 (NVDA as the signal
leg). There is no NVDA series on this machine — `data/etf` is empty — so no number is
estimated, carried over from the author, or proxied.

## Headline

**None of the forty-eight runnable prompts clears all six gates.** The closest is S46,
the weekend-gap fade on BTC 1h, which fails only concentration: its net without the five
best trades is -8.65% of starting capital against a
headline 26.68%. Its profit factor is 1.303
with an out-of-sample profit factor of 2.64. Remove the five best of its
60 trades and the year is negative, so the result is carried by those
fills rather than by a distribution.

After S46, S05 is the only prompt that reaches four of the six gates: Heikin-Ashi on SUI
4h, factor 1.077, failing the factor gate and concentration at
-95.27%. Three prompts sit at three of six — S01
(Donchian-55, factor 1.118, beaten by buy & hold
11.83% against 24.30%), S32 (the ETH/BTC pair,
factor 4.803 on 24 trades) and S45 (daily-level
bounce, factor 0.988).

## The table

`conc net %` is the net result with the five best trades removed, as a share of starting
capital. `repo PF` is the same signals at the repo gate cost. `zero PF` is the same
signals with no cost at all — the gross edge, before the cost block. An `n/a` in the
split columns means that half of the split contained **no trades**, so the factor is
undefined rather than zero; that is a sample-size failure, not a losing half.

| S | prompt | market | n | net % | PF | IS PF | OOS PF | B&H % | conc net % | funding | repo PF | zero PF | fails | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S01 | Donchian-55 breakout | BTCUSDT 4h | 53 | 11.83 | 1.118 | 1.05 | 1.28 | 24.30 | -24.67 | -289.60 | 1.124 | 1.193 | G1 G5 G6 | `1dac06b2e17c8562` |
| S02 | dual EMA 21/55 trend | ETHUSDT 4h | 45 | -2.39 | 0.982 | 1.33 | 0.36 | -7.52 | -57.91 | -37.37 | 0.985 | 1.023 | G1 G3 G4 G6 | `d20abeaaad5c58aa` |
| S03 | MACD histogram momentum | SOLUSDT 4h | 111 | -40.90 | 0.800 | 0.82 | 0.72 | -34.95 | -132.36 | -181.22 | 0.803 | 0.843 | G1 G3 G4 G5 G6 | `d9bd110141f559b4` |
| S04 | ADX-gated DI cross | HYPEUSDT 4h | 29 | -29.88 | 0.403 | 0.19 | 1.04 | 134.90 | -48.79 | 5.64 | 0.430 | 0.465 | G1 G2 G3 G4 G5 G6 | `674834c1010324d2` |
| S05 | Heikin-Ashi trend | SUIUSDT 4h | 110 | 16.11 | 1.077 | 1.09 | 1.03 | -59.08 | -95.27 | -178.69 | 1.134 | 1.209 | G1 G6 | `8321c904af22c0ad` |
| S06 | Keltner breakout + 4h slope | BTCUSDT 1h | 213 | -16.12 | 0.881 | 0.78 | 1.35 | 24.30 | -53.64 | -243.86 | 0.894 | 1.062 | G1 G3 G5 G6 | `28c183720f6041e1` |
| S07 | time-series momentum 90d | ETHUSDT 4h | 21 | 10.56 | 1.147 | 2.85 | 0.21 | -7.52 | -69.65 | -234.50 | 1.150 | 1.188 | G1 G2 G3 G4 G6 | `f80d7c92490b74a4` |
| S08 | Hull MA trend | JUPUSDT 4h | 140 | -0.40 | 0.999 | 1.07 | 0.80 | -65.35 | -175.56 | 385.31 | 1.026 | 1.062 | G1 G3 G4 G6 | `7bc961ced23df363` |
| S09 | Parabolic SAR trend | SOLUSDT 1h | 360 | -12.98 | 0.962 | 0.92 | 1.11 | -34.95 | -63.81 | -304.37 | 0.972 | 1.088 | G1 G3 G4 G6 | `e4a95d4ef56399ae` |
| S10 | Turtle 20-day breakout | BTCUSDT 1d | 17 | -25.02 | 0.120 | 0.08 | 0.24 | 24.30 | -26.51 | -204.47 | 0.117 | 0.129 | G1 G2 G3 G4 G5 G6 | `9f160f2255405dac` |
| S11 | Bollinger 2.2 sigma reversion | ETHUSDT 15m | 873 | -74.79 | 0.716 | 0.72 | 0.71 | -7.52 | -88.72 | -32.39 | 0.730 | 0.918 | G1 G3 G4 G5 G6 | `56da728f7171116c` |
| S12 | VWAP deviation reversion | SOLUSDT 15m | 6200 | -99.98 | 0.597 | 0.60 | 0.46 | -32.75 | -109.41 | -72.00 | 0.620 | 0.929 | G1 G3 G4 G5 G6 | `3d977bd5fdb24204` |
| S13 | z-score reversion | BTCUSDT 1h | 1226 | -72.79 | 0.799 | 0.81 | 0.75 | 24.30 | -97.23 | 65.92 | 0.815 | 1.032 | G1 G3 G4 G5 G6 | `e7b1a54fc073cc35` |
| S14 | RSI-2 snap-back | SUIUSDT 1h | 134 | -7.92 | 0.933 | 1.04 | 0.61 | -59.08 | -34.88 | -44.62 | 1.032 | 1.165 | G1 G3 G4 G6 | `88382b0afae57724` |
| S15 | Stochastic RSI reversion | HYPEUSDT 30m | 1589 | -90.74 | 0.839 | 0.84 | 0.80 | 135.56 | -112.36 | 11.74 | 0.931 | 1.068 | G1 G3 G4 G5 G6 | `52173caff5e3c7dd` |
| S16 | Keltner fade | JUPUSDT 1h | 15 | -23.86 | 0.814 | 0.81 | 0.00 | -65.35 | -82.99 | 715.14 | 0.823 | 0.835 | G1 G2 G3 G4 G6 | `69e2713600ec9602` |
| S17 | Williams %R extreme | BTCUSDT 30m | 287 | -31.79 | 0.568 | 0.54 | 0.72 | 24.30 | -38.84 | -23.11 | 0.593 | 0.945 | G1 G3 G4 G5 G6 | `c786105cca43aba6` |
| S18 | Hurst-gated reversion | ETHUSDT 1h | 137 | -40.93 | 0.822 | 0.81 | 0.88 | -7.52 | -63.11 | 260.04 | 0.827 | 0.876 | G1 G3 G4 G5 G6 | `1018e6dcb339dbbb` |
| S19 | Bollinger-Keltner squeeze | BTCUSDT 1h | 84 | -9.57 | 0.912 | 0.94 | 0.86 | 24.30 | -39.59 | -20.56 | 0.919 | 1.000 | G1 G3 G4 G5 G6 | `cc5c142700cbabdf` |
| S20 | opening-range breakout | ETHUSDT 15m | 706 | -53.71 | 0.805 | 0.81 | 0.79 | -7.52 | -72.19 | -37.33 | 0.821 | 1.023 | G1 G3 G4 G5 G6 | `7af150b557ad20c2` |
| S21 | ATR-expansion breakout | SOLUSDT 4h | 94 | 64.87 | 1.093 | 1.44 | 0.32 | -34.95 | -147.58 | -431.12 | 1.095 | 1.116 | G1 G3 G4 G6 | `056f65013c9bc22f` |
| S22 | inside-bar breakout | SUIUSDT 1h | 576 | -73.31 | 0.627 | 0.61 | 0.74 | -59.08 | -101.31 | -9.63 | 0.745 | 0.937 | G1 G3 G4 G5 G6 | `da0424b7861989a1` |
| S23 | volatility-regime breakout | HYPEUSDT 4h | 26 | -15.68 | 0.810 | 0.77 | 0.91 | 134.90 | -81.27 | -41.83 | 0.835 | 0.865 | G1 G2 G3 G4 G5 G6 | `890345934a953513` |
| S24 | range-break failure fade | BTCUSDT 1h | 852 | -71.37 | 0.701 | 0.70 | 0.69 | 24.30 | -91.25 | 43.40 | 0.716 | 0.931 | G1 G3 G4 G5 G6 | `51a594e473e77acd` |
| S25 | Chandelier breakout | ETHUSDT 4h | 181 | -22.42 | 0.936 | 0.94 | 0.91 | -7.52 | -203.57 | -1042.49 | 0.940 | 0.990 | G1 G3 G4 G5 G6 | `ae860b93c4ad7e60` |
| S26 | daily pivot R1/S1 | JUPUSDT 1h | 641 | -74.94 | 0.846 | 0.86 | 0.73 | -65.35 | -139.08 | -102.38 | 0.904 | 0.987 | G1 G3 G4 G5 G6 | `f8fa2c7d82d7d5bb` |
| S27 | SOL/ETH ratio reversion | SOLUSDT+ETHUSDT 1h | 579 | -48.31 | 0.490 | 0.53 | 0.29 | -20.10 | -55.09 | 50.68 | 0.522 | 1.037 | G1 G3 G4 G5 G6 | `47f3502da45d49ba` |
| S28 | BTC/ETH cointegration | BTCUSDT+ETHUSDT 4h | 4 | 3.46 | 25.620 | 0.00 | 25.62 | 8.39 | 0.00 | 6.86 | 27.874 | 230.934 | G2 G3 G5 G6 | `074e9fb993e0a583` |
| S29 | SUI/SOL momentum spread | SUIUSDT+SOLUSDT 4h | 124 | -25.40 | 0.614 | 0.65 | 0.52 | -47.02 | -35.62 | -6.07 | 0.745 | 0.932 | G1 G3 G4 G6 | `a4c58aead9f190c0` |
| S30 | JUP/SOL rotation | JUPUSDT+SOLUSDT 1d | 64 | -34.02 | 0.621 | 0.52 | 0.99 | -52.42 | -75.16 | -7.36 | 0.660 | 0.713 | G1 G3 G4 G6 | `b9033295be4cc9c2` |
| S31 | HYPE/BTC beta-neutral | HYPEUSDT+BTCUSDT 4h | 28 | 4.54 | 1.151 | 1.23 | 1.01 | 60.04 | -16.81 | 19.17 | 1.247 | 1.378 | G1 G2 G5 G6 | `bec9428f936e2b4f` |
| S32 | ETH/BTC dominance proxy | ETHUSDT+BTCUSDT 1d | 24 | 73.36 | 4.803 | 3.56 | n/a | 8.39 | -3.57 | -87.95 | 4.859 | 5.561 | G2 G3 G6 | `8d5242a3a743b39d` |
| S33 | funding-spread pair | ETHUSDT+SOLUSDT 1h | 525 | -57.05 | 0.647 | 0.64 | 0.67 | -20.10 | -69.53 | 188.34 | 0.664 | 0.893 | G1 G3 G4 G5 G6 | `d1b18abf699949df` |
| S35 | VWAP pullback scalp | BTCUSDT 1m | 10856 | -100.00 | 0.000 | 0.00 | 0.00 | 23.88 | -100.00 | -2.52 | 0.105 | 1.019 | G1 G3 G4 G5 G6 | `508fbe03071ddb4b` |
| S36 | order-imbalance scalp | ETHUSDT 1m | 6454 | -100.00 | 0.000 | 0.00 | 0.00 | -8.42 | -100.00 | -6.70 | 0.034 | 0.954 | G1 G3 G4 G5 G6 | `3fdda9ccfe3eeeb3` |
| S37 | EMA 5/13 volume-hour scalp | SOLUSDT 5m | 6476 | -100.00 | 0.303 | 0.30 | 0.28 | -32.98 | -101.05 | -0.89 | 0.476 | 0.953 | G1 G3 G4 G5 G6 | `3a487848b68b17c2` |
| S38 | liquidity-sweep reversal | SUIUSDT 1m | 37821 | -100.00 | 0.376 | 0.38 | 0.30 | -54.41 | -107.29 | 2.68 | 0.601 | 1.026 | G1 G3 G4 G5 G6 | `744fd24001c5ee45` |
| S39 | Bollinger squeeze scalp | HYPEUSDT 3m | 2343 | -98.54 | 0.590 | 0.60 | 0.47 | 132.52 | -106.43 | 13.21 | 0.767 | 1.066 | G1 G3 G4 G5 G6 | `dbb04ee79de80020` |
| S40 | tick-rule momentum scalp | JUPUSDT 1m | 5037 | -100.00 | 0.007 | 0.01 | 0.01 | -67.34 | -100.09 | -1.06 | 0.215 | 0.925 | G1 G3 G4 G5 G6 | `6c0abd480bab5b7d` |
| S41 | Supertrend scalp | BTCUSDT 5m | 5314 | -99.99 | 0.505 | 0.50 | 0.37 | 24.27 | -115.06 | -124.90 | 0.634 | 0.971 | G1 G3 G4 G5 G6 | `300741d18994eca6` |
| S42 | 1m range-expansion fade | ETHUSDT 1m | 2553 | -99.07 | 0.000 | 0.00 | 0.00 | -8.42 | -99.07 | 1.05 | 0.117 | 0.950 | G1 G3 G4 G5 G6 | `07bf0698d8b278b7` |
| S43 | London-open breakout | BTCUSDT 15m | 165 | -31.20 | 0.905 | 0.97 | 0.71 | 24.30 | -104.84 | -269.92 | 0.909 | 0.954 | G1 G3 G4 G5 G6 | `b71e37d56ccc3f55` |
| S44 | New York-open fade | ETHUSDT 15m | 72 | -22.81 | 0.253 | 0.27 | 0.20 | -7.52 | -29.52 | -0.41 | 0.260 | 0.372 | G1 G3 G4 G5 G6 | `24ab010f67e09e62` |
| S45 | daily-level bounce | SOLUSDT 1h | 114 | -1.51 | 0.988 | 0.93 | 1.19 | -34.95 | -54.01 | 45.51 | 0.997 | 1.107 | G1 G3 G6 | `fdd964c4e8c669e5` |
| S46 | weekend-gap fade | BTCUSDT 1h | 60 | 26.68 | 1.303 | 1.07 | 2.64 | 24.30 | -8.65 | -0.61 | 1.312 | 1.411 | G6 | `be0a85f7ab2b522c` |
| S47 | intraday trend-day pullback | SUIUSDT 15m | 2313 | -56.71 | 0.948 | 0.95 | 0.91 | -54.12 | -176.81 | -112.31 | 1.109 | 1.538 | G1 G3 G4 G5 G6 | `fa0d446d3fe5916c` |
| S48 | funding-reset scalp | HYPEUSDT 30m | 575 | -81.01 | 0.528 | 0.49 | 0.85 | 135.56 | -92.00 | -0.87 | 0.647 | 0.825 | G1 G3 G4 G5 G6 | `f1367cbaf19f7369` |
| S50 | liquidity grab of the 24h low | JUPUSDT 1h | 1272 | -97.66 | 0.788 | 0.79 | 0.70 | -65.35 | -132.80 | 82.54 | 0.840 | 0.916 | G1 G3 G4 G5 G6 | `64a2b41447e941a1` |

## What the failures say, by family

**Trend and momentum (S01-S10).** The family is not uniformly bad, it is uniformly
*thin*. S01 is profitable before costs (1.193 zero-cost factor) and
still loses to buy & hold; S02 and S08 are fractionally negative
(-2.39% and -0.40%); S07 makes money
but on 21 trades with an out-of-sample factor of 0.21, so
G2 and G3 both fail. S10 dies outright: 17 trades on the daily and a
profit factor of 0.120.

**Mean reversion (S11-S18).** The worst block in the pack. The ones that trade a lot lose
a lot — S12 takes 6200 trades at 15m for
-99.98% — and the ones that trade rarely never get a sample. S16 has
15 trades and an out-of-sample factor of 0.00: nothing
can be concluded from it either way, which is itself the verdict.

**Breakout and volatility (S19-S26).** Nothing in this block is cost-destroyed, because
nothing in it has a gross edge to destroy: with fees and slippage switched off the best
factor in the block is S21 at 1.116, and S21 keeps
1.093 of it after costs with an out-of-sample factor of
0.32. What the block does show is the funding bill. S25 pays
-1042.49 against a starting account of ten thousand — the largest
single drag in the pack — and every prompt in the block lands under the factor
threshold both before and after costs.

**Pairs (S27-S33).** Dollar-neutral books with half the equity per leg. S32 is the only
one with a large headline (73.36%, factor 4.803)
and it fails on sample, on the split and on concentration: 24 trades, no
out-of-sample trade at all, and a net of -3.57% without
the best five. S28 produced 4 trades in total, so its
25.620 factor is arithmetic, not evidence. The funding-spread book
(S33) *loses* money while collecting funding (188.34 received): price
moves dominate the carry it is trying to harvest.

**Scalping (S35-S42).** The cost autopsy is starkest here. S35's take-profit sits below
its own round trip, so its profit factor is 0.000 at pack cost
while the identical signals score 1.019 with costs switched off.
S38 shows the same split more strongly: 1.026 gross against
0.376 net over 37821 trades. These are not
"no-signal" results; they are "target smaller than the round trip" results — and the
pack's own cost block charges its widest slippage on exactly these timeframes, so the
target has to clear a wider round trip than the fee column alone suggests.

**Sessions and day trading (S43-S50).** S46 is the pack's best result and still fails
concentration. S43 and S44 fade or chase the open and both lose after funding
(-269.92 and -0.41). Only S45 and S46 finish
with a positive out-of-sample factor (1.19 and 2.64), and
S45 still ends negative overall at -1.51%.

## The single most useful number in the pack

`zero PF` against `PF` is the point of measuring the control. Six prompts carry a gross
factor above the repo threshold with costs switched off: S47
1.538, S46 1.411, S31
1.378, S05 1.209, and the two tiny pair books
S32 5.561 and S28 230.934. Costs take a bite out
of every one — S47 falls to 0.948, S31 to
1.151, S05 to 1.077 — but the bite is not
the whole story. The two that stay above the threshold, S46 and S32, still fail the other
gates: one on concentration, the other on sample. Cost did not hide a portfolio of
winners; it removed the marginal ones, and what was left was never a distribution.

## Data caveats that bound these conclusions

- Every market here is the Binance USDT-M perpetual read from the taker kline files, which
  start in late 2024; HYPE starts later still and JUP stops earlier. Multi-year regime
  claims are therefore out of reach, and the split is a split of a short window, not a
  decade.
- JUP funding did not exist on disk and was fetched; the file is new, so any earlier JUP
  artifact in this repo could not have charged it.
- Two prompts (S34, S49) are unrunnable without NVDA data and are excluded, not modelled.

## Reproduce

    python code/_pack50_audit.py
    python code/_pack50_run_all.py
    python code/_pack50_report_table.py
    python code/vrun.py pverify --ids <ids from results/_pack50_ids.json> --workers 4
    python code/vrun.py guard --report results/pack50_report.md
