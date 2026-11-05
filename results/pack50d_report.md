# The Qwen fifty-prompt pack: measured, and the verdict is the same shape again

Source document: `Downloads/deepseek_markdown_20261027_68930c.md` — fifty numbered prompts
(P01-P50). Adapter `pack50d` (`code/pack50c_engine.py`, `code/pack50c_strats.py`)
on the frozen pack50_core execution machinery, with the v2 gate layer
(`code/gate2.py`, policy hash `6bc4e74936a26a1e`) measured
inside every artifact.

## How the numbers were produced

- Closed-bar signals, next-open fills, intrabar stops, stop-first on ties,
  funding charged at each symbol's own settlement instants — the audited core,
  unchanged. Trailing stops ("ATR trail", "EMA 50 trail") are emulated as
  close-cross exits filling one bar late; "support and resistance" stops and
  targets are the prior 20-bar range; the Volume-Profile POC is the
  highest-volume price bin of the prior hundred bars. The full reading list is
  in `code/pack50d_strats.py`; the audit pinning it is `code/_pack50d_audit.py`
  (one hundred twenty-one checks, all pass).
- Costs: the pack's own block (5.0 fee + 2.0 slippage bps per side; "2 ticks"
  read as 2 bps) drives the headline; the repo gate cost, twice the gate cost,
  the measured breakeven and a zero-cost control are all inside the artifact.
- Sizing is full-equity compounding (the repo pack convention).

## What could not be run

Two prompts are **NO DATA**: P30 and P46 need NVDA equity data that does not
exist on this machine. "SPCX" (P47) is the SPXUSDT series on disk (about three
months at 1m). P17 is a dollar-neutral ETH/SOL pair book and P23's BTC filter
leg is hashed into its artifact's inputs.

## Headline

**None of the forty-eight runnable prompts clears the v1 gates**, and **none passes the v2 set**. The best profit factor among books with a real sample is P06 at 1.576 net (28.21%) on 15 trades, with a zero-cost factor of 1.626 and an expectancy lower bound of -263.64 bps. P07, the daily EMA 50/200 cross, took exactly one trade in the window and shows an infinite profit factor on it — a sample failure, not a result. The highest expectancy lower bound among books with a real sample is -0.57 bps (P28, 266 trades) — the closest any book measured in this repository has come to the expectancy gate, and still short. The pack's best books are
indistinguishable from noise by the expectancy lower bound — every one of the
forty-eight artifacts has a negative or undefined lower bound except
one — and eleven of them end the window ruined
(below minus ninety-nine percent) on the 1m and 3m timeframes.

## The table

`exp. LB95` is the block-bootstrap ninety-five percent lower bound of per-trade
expectancy in bps at the repo gate cost. `breakeven` is the per-side cost at
which profit factor reaches one (measured by real re-runs). `P95 DD` is the
bootstrapped ninety-fifth percentile of max drawdown on the mark-to-market
curve; the G9 cap is thirty-five percent.

| P | rule | market | n | net % (pack) | PF (pack) | zero PF | exp. LB95 bps | split IS/OOS PF | folds PF>1 | breakeven bps | P95 DD % | v1 fails | v2 fails | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P01 | Supertrend + EMA200 | BTCUSDT 4h | 30 | 5.80 | 1.149 | 1.235 | -112.79 | 1.38 / 0.84 | 0.00 | 20.90 | 35.81 | G1 G3 G4 G5 G6 | G1 G2 G3 G4 G5 G6 G9 | `954e15c8954197ee` |
| P02 | EMA 20/50 cross | ETHUSDT 1h | 233 | -46.75 | 0.771 | 0.890 | -49.91 | 0.77 / 0.90 | 0.20 | 0.00 | 69.96 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `56380e822c93acf6` |
| P03 | Donchian 20 breakout | SOLUSDT 15m | 1240 | -78.65 | 0.885 | 1.042 | -16.40 | 0.93 / 0.89 | 0.40 | 1.76 | 92.11 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `c5aee576266cf327` |
| P04 | MACD histogram + EMA50 | HYPEUSDT 1h | 350 | -52.57 | 0.908 | 0.992 | -46.97 | 1.01 / 0.68 | 0.40 | 0.00 | 87.13 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `31ae6c55172a7646` |
| P05 | Ichimoku Kumo breakout | SUIUSDT 30m | 1971 | 202.61 | 1.111 | 1.282 | -2.72 | 1.17 / 1.09 | 1.00 | 12.30 | 88.95 | G1 G6 | G1 G4 G5 G6 G9 | `24702522793f8fe0` |
| P06 | Supertrend + RSI pullback | JUPUSDT 4h | 15 | 28.21 | 1.576 | 1.626 | -263.64 | 1.64 / 1.49 | 0.00 | n/a | 45.74 | G2 G3 G6 | G1 G2 G3 G4 G5 G8 G9 | `3bb1691c2447fc38` |
| P07 | EMA 50/200 cross | BTCUSDT 1d | 1 | 18.13 | inf | n/a | 1816.54 | n/a / n/a | 0.00 | n/a | 38.83 | G2 G3 G5 G6 | G2 G3 G4 G5 G6 G8 G9 | `e99ba04a2d20f7e3` |
| P08 | Keltner breakout | ETHUSDT 1h | 522 | 83.91 | 1.139 | 1.291 | -5.35 | 1.28 / 0.85 | 1.00 | 14.65 | 59.36 | G1 G3 | G1 G3 G5 G6 G9 | `cdce9bf5c26d097f` |
| P09 | LinReg slope + R2 | SOLUSDT 1h | 872 | -75.90 | 0.908 | 1.014 | -27.32 | 0.94 / 0.91 | 0.20 | 0.98 | 94.07 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `2663e9040e7bec23` |
| P10 | HH/HL structure break | HYPEUSDT 4h | 143 | -87.80 | 0.703 | 0.732 | -219.39 | 0.69 / 0.68 | 0.00 | 0.00 | 97.41 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `6ce7543aaa0c6971` |
| P11 | BB bounce + RSI | BTCUSDT 15m | 883 | -77.78 | 0.624 | 0.922 | -19.22 | 0.69 / 0.65 | 0.00 | 0.00 | 81.73 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `b9c8daa97446c182` |
| P12 | RSI 30/70, Asian only | ETHUSDT 5m | 1513 | -88.43 | 0.504 | 0.994 | -14.04 | 0.62 / 0.48 | 0.00 | 0.00 | 87.34 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `fa86ac6811db358d` |
| P13 | VWAP reversion | SOLUSDT 1h | 1330 | -95.40 | 0.655 | 0.865 | -27.57 | 0.72 / 0.64 | 0.00 | 0.00 | 97.61 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `f9a1959435579979` |
| P14 | Keltner fade | SUIUSDT 15m | 832 | -91.16 | 0.754 | 0.872 | -39.91 | 0.79 / 0.73 | 0.00 | 0.00 | 97.24 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `1a4a96ba3f9c21d3` |
| P15 | z-score reversion | JUPUSDT 5m | 4683 | -99.94 | 0.792 | 0.992 | -16.18 | 0.83 / 0.83 | 0.00 | 0.00 | 99.96 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `4ccc79929bcbe1b8` |
| P16 | RSI(2) Connors | BTCUSDT 1h | 780 | -70.58 | 0.531 | 0.948 | -17.52 | 0.61 / 0.59 | 0.00 | 0.00 | 74.93 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `dd7de2aba22315ac` |
| P17 | ETH/SOL z-score pair | ETHUSDT+SOLUSDT 30m | 904 | -68.70 | 0.275 | 1.118 | -12.11 | 0.45 / 0.21 | 0.00 | 0.59 | 66.28 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `3b84965499084ec8` |
| P18 | Bollinger %B | HYPEUSDT 15m | 2729 | -95.65 | 0.876 | 1.055 | -12.97 | 0.93 / 0.85 | 0.00 | 2.15 | 98.28 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `c16714c5003b704b` |
| P19 | London open fade | SOLUSDT 5m | 315 | -47.43 | 0.300 | 0.711 | -23.14 | 0.42 / 0.23 | 0.00 | 0.00 | 51.39 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `191bde885b79a0be` |
| P20 | MFI divergence | SUIUSDT 30m | 1631 | -98.15 | 0.828 | 0.936 | -31.46 | 0.87 / 0.79 | 0.00 | 0.00 | 99.52 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `44c32189aef31031` |
| P21 | Asian range breakout | BTCUSDT 1h | 258 | -20.85 | 0.933 | 1.079 | -34.43 | 0.98 / 0.92 | 0.40 | 3.71 | 58.11 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `05d888c6df13ffdf` |
| P22 | ORB 13:30 | ETHUSDT 15m | 531 | -60.55 | 0.757 | 0.961 | -25.98 | 0.84 / 0.67 | 0.20 | 0.00 | 75.73 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `076ad8bd474e946e` |
| P23 | volume breakout + BTC filter | SOLUSDT+BTCUSDT 5m | 2877 | -98.30 | 0.563 | 1.000 | -12.97 | 0.66 / 0.57 | 0.00 | 0.20 | 97.51 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `d1fc717704987ce7` |
| P24 | 52-bar high, long-only | HYPEUSDT 1h | 169 | 14.61 | 1.093 | 1.172 | -61.12 | 1.19 / 0.90 | 0.60 | 16.21 | 67.83 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G9 | `2f8c28d0cdc329bf` |
| P25 | NR7 contraction | SUIUSDT 15m | 820 | -72.89 | 0.759 | 0.979 | -18.85 | 0.85 / 0.66 | 0.20 | 0.00 | 81.99 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `6c9b3643ea2469e2` |
| P26 | squeeze release | JUPUSDT 1h | 114 | 3.56 | 1.059 | 1.179 | -45.81 | 1.11 / 1.01 | 0.60 | 10.74 | 45.89 | G1 G3 G4 G6 | G1 G3 G4 G5 G6 G8 G9 | `ce5f19681812b35d` |
| P27 | 20-day high, Chandelier | BTCUSDT 1d | 13 | 11.93 | 1.372 | 1.415 | -535.04 | 1.10 / 2.71 | 0.00 | 77.54 | 54.56 | G2 G3 G5 G6 | G1 G2 G3 G4 G5 G6 G9 | `a9003311251ef79b` |
| P28 | momentum ignition | ETHUSDT 5m | 266 | 41.44 | 1.316 | 1.825 | -0.57 | 1.52 / 1.00 | 1.00 | 14.26 | 26.91 | G3 | G1 G3 G4 G5 G6 | `ff1403fda59140c8` |
| P29 | VWAP breakout | SOLUSDT 30m | 354 | -19.08 | 0.915 | 1.173 | -14.09 | 1.15 / 0.56 | 0.40 | 4.49 | 45.05 | G1 G3 G4 G6 | G1 G3 G4 G5 G6 G8 G9 | `9cbf5900f6574b65` |
| P31 | EMA 9/21 + VWAP | BTCUSDT 1m | 3607 | -99.34 | 0.059 | 1.026 | -11.25 | 0.11 / 0.08 | 0.00 | 0.20 | 98.31 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `842ab7850a311d36` |
| P32 | BB squeeze scalper | ETHUSDT 1m | 1 | -0.25 | 0.000 | 0.000 | -21.97 | n/a / 0.00 | 0.00 | 0.00 | 0.66 | G1 G2 G3 G4 G6 | G1 G2 G3 G4 G5 G6 G8 | `ae1c9db2bd5dc67d` |
| P33 | RSI 50 cross | SOLUSDT 3m | 6492 | -99.99 | 0.368 | 1.021 | -11.43 | 0.50 / 0.33 | 0.00 | 0.20 | 99.94 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `e5046c6b62aa6e54` |
| P34 | micro mean reversion | HYPEUSDT 1m | 45751 | -100.00 | 0.512 | 1.019 | -7.13 | 0.59 / 0.60 | 0.00 | 0.20 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `2de8332d93bb2a6d` |
| P35 | Supertrend 10/2 + 1H filter | SUIUSDT 5m | 4359 | -99.90 | 0.572 | 0.941 | -14.77 | 0.65 / 0.58 | 0.00 | 0.00 | 99.81 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `250e534246ea2940` |
| P36 | micro breakout | JUPUSDT 1m | 45290 | -100.00 | 0.143 | 0.986 | -7.10 | 0.21 / 0.09 | 0.00 | 0.00 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `0b8d1313d1451bff` |
| P37 | VWAP wick bounce | BTCUSDT 3m | 11141 | -100.00 | 0.088 | 0.940 | -11.88 | 0.17 / 0.11 | 0.00 | 0.00 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `8784e02a57225a85` |
| P38 | StochRSI cross | ETHUSDT 5m | 3272 | -98.90 | 0.426 | 1.020 | -11.87 | 0.54 / 0.43 | 0.00 | 0.20 | 98.04 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `7092c0241175396b` |
| P39 | CVD proxy | SOLUSDT 1m | 290139 | -100.00 | 0.075 | 1.001 | -1.16 | 0.14 / 0.08 | 0.00 | 0.20 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `bdcf8f239ac7e8cc` |
| P40 | ATR envelope fade | HYPEUSDT 3m | 7393 | -99.99 | 0.752 | 1.030 | -11.91 | 0.82 / 0.77 | 0.00 | 0.59 | 99.99 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `3cb8abe293396e44` |
| P41 | session open momentum | BTCUSDT 15m | 768 | -56.90 | 0.689 | 1.130 | -12.92 | 0.76 / 0.76 | 0.00 | 1.76 | 60.90 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `d13571c1b348581e` |
| P42 | overnight range breakout | ETHUSDT 30m | 42 | -22.99 | 0.617 | 0.695 | -144.46 | 0.66 / 0.56 | 0.00 | 0.00 | 43.79 | G1 G3 G4 G5 G6 | G1 G2 G3 G4 G5 G6 G8 G9 | `d68eb2aeeadbe6e0` |
| P43 | session extreme fade | SOLUSDT 15m | 177 | -48.44 | 0.588 | 0.715 | -56.07 | 0.62 / 0.60 | 0.20 | 0.00 | 62.13 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `74615a5fcaa988c5` |
| P44 | weekend gap fade | SUIUSDT 1h | 76 | 9.47 | 1.188 | 1.371 | -46.52 | 0.59 / 3.73 | 0.40 | 15.82 | 34.59 | G1 G3 G4 G6 | G1 G2 G3 G4 G5 G6 | `73ec7766d0e92513` |
| P45 | VWAP band mode switch | JUPUSDT 15m | 22939 | -100.00 | 0.026 | 0.039 | -16.75 | 0.03 / 0.03 | 0.00 | 0.00 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `865a7b20d9592b0c` |
| P47 | trend pullback | SPCX 15m | 375 | -60.55 | 0.716 | 0.871 | -35.43 | 0.65 / 0.92 | 0.00 | 0.00 | 74.72 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `adfaeef2d1e745b1` |
| P48 | momentum + OBV | BTCUSDT 30m | 1804 | -88.90 | 0.789 | 1.053 | -13.14 | 0.86 / 0.78 | 0.00 | 1.37 | 91.69 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `87bcb05c8b34d993` |
| P49 | Ichimoku + Kumo twist | ETHUSDT 1h | 188 | -45.77 | 0.805 | 0.896 | -66.42 | 0.95 / 0.53 | 0.20 | 0.00 | 75.21 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `cae858612c52ce1e` |
| P50 | MTF confluence | SOLUSDT 15m | 7033 | -99.98 | 0.757 | 1.052 | -10.95 | 0.85 / 0.69 | 0.00 | 0.98 | 99.96 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `bd911d47bda83360` |

## Family notes

**Trend following (P01-P10).** Supertrend, EMA crosses, Donchian, Keltner,
linear-regression slope and swing structure on 4H/1H/15m/1D: the slowest books
in the pack (P07 trades the daily) fail on sample, the faster ones on cost.

**Mean reversion (P11-P20).** Bollinger, RSI, VWAP and z-score fades with
regime filters, one RSI(2) Connors book and one ETH/SOL pair: the
fixed-percentage targets fight the fourteen bps pack round trip.

**Breakout and momentum (P21-P30).** Session ranges, volume-confirmed
breakouts, squeeze releases, a momentum-ignition candle and the 20-day-high
turtle variant with its Chandelier trail.

**Scalping (P31-P40).** One-minute EMA/VWAP/Bollinger/CVD books: the cost
autopsy block, as in every pack before this one.

**Day trading and sessions (P41-P50).** Session opens, overnight ranges, gap
fades, VWAP band modes and the multi-timeframe confluence book.

## What the cost columns say

The breakeven column is the honest summary: a book must survive a per-side
cost of at least the gate's 5.5 bps to be tradable at all, and twice that to
clear G8. The best breakeven in the pack is
77.54 bps per side —
above
the doubled gate cost. Every artifact carries `pre_registered: false`, so the
G7 multiple-testing haircut applies on top of the ledger's program-level one.

## Reproduce

    python code/_pack50c_audit.py
    python code/vrun.py run --strategy pack50d --tf 1h --symbol ETHUSDT --set strat=2
    python code/vrun.py pverify --ids <ids from results/_pack50d_ids.json> --workers 2
    python code/vrun.py guard --report results/pack50d_report.md
