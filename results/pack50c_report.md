# The Qwen fifty-prompt pack: measured, and the verdict is the same shape again

Source document: `Downloads/Qwen_50 strategies.txt` — fifty numbered prompts
(Q01-Q50). Adapter `pack50c` (`code/pack50c_engine.py`, `code/pack50c_strats.py`)
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
  in `code/pack50c_strats.py`; the audit pinning it is `code/_pack50c_audit.py`
  (one hundred ten checks, all pass, including the no-stopless-entry group —
  which caught six VWAP/PSAR ports firing during ATR warmup before any market
  run, and they were fixed).
- Costs: the pack's own block (5.0 fee + 2.0 slippage bps per side; "2 ticks"
  read as 2 bps) drives the headline; the repo gate cost, twice the gate cost,
  the measured breakeven and a zero-cost control are all inside the artifact.
- Sizing is full-equity compounding (the repo pack convention).

## What could not be run

Eight prompts are **NO DATA**: Q02, Q11, Q23, Q27, Q35, Q36, Q42 and Q47 all
need NVDA equity data that does not exist on this machine. "SPCX" is the
SPXUSDT series on disk (about three months at 1m).

## Headline

**None of the forty-two runnable prompts clears the v1 gates**, and **none passes the v2 set**. The best profit factor in the pack is Q29 at 0.886 net (-57.87%) on 377 trades, with a zero-cost factor of 0.974 and an expectancy lower bound of -48.94 bps. The highest expectancy lower bound anywhere in the pack is -0.92 bps (Q30). The pack's best books are
indistinguishable from noise by the expectancy lower bound — every one of the
forty-two artifacts has a negative or undefined lower bound except
zero — and thirty-three of them end the window ruined
(below minus ninety-nine percent) on the 1m and 3m timeframes.

## The table

`exp. LB95` is the block-bootstrap ninety-five percent lower bound of per-trade
expectancy in bps at the repo gate cost. `breakeven` is the per-side cost at
which profit factor reaches one (measured by real re-runs). `P95 DD` is the
bootstrapped ninety-fifth percentile of max drawdown on the mark-to-market
curve; the G9 cap is thirty-five percent.

| Q | rule | market | n | net % (pack) | PF (pack) | zero PF | exp. LB95 bps | split IS/OOS PF | folds PF>1 | breakeven bps | P95 DD % | v1 fails | v2 fails | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Q01 | VWAP bounce | SPCX 5m | 1273 | -90.03 | 0.581 | 0.891 | -19.43 | 0.61 / 0.69 | 0.00 | 0.00 | 91.01 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `37672f4967910d94` |
| Q03 | stochastic reversion | SPCX 1m | 1491 | -76.50 | 0.882 | 1.082 | -12.90 | 0.82 / 1.09 | 0.20 | 2.54 | 87.58 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `e9dcb88a1102a73c` |
| Q04 | Keltner breakout, S/R | HYPEUSDT 1m | 172204 | -100.00 | 0.027 | 0.340 | -1.98 | 0.04 / 0.05 | 0.00 | 0.00 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `819c9580c85842a8` |
| Q05 | VWAP bounce | BTCUSDT 15m | 5776 | -99.98 | 0.455 | 0.970 | -12.59 | 0.55 / 0.47 | 0.00 | 0.00 | 99.94 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `3a50d1b7216e889d` |
| Q06 | RSI extremes | ETHUSDT 1m | 41005 | -100.00 | 0.283 | 1.067 | -7.82 | 0.37 / 0.30 | 0.00 | 0.20 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `c3a87f2efe46ad75` |
| Q07 | DI cross, ADX>25 | SOLUSDT 1m | 10005 | -100.00 | 0.436 | 0.961 | -12.54 | 0.56 / 0.39 | 0.00 | 0.00 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `8c8404e7376fd02b` |
| Q08 | PSAR reversal | SUIUSDT 1m | 85775 | -100.00 | 0.305 | 0.979 | -3.83 | 0.38 / 0.18 | 0.00 | 0.00 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `00e0f70ad390778e` |
| Q09 | Bollinger breakout | HYPEUSDT 1m | 16379 | -100.00 | 0.666 | 0.991 | -12.31 | 0.73 / 0.72 | 0.00 | 0.00 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `30657f6a3476fec1` |
| Q10 | Bollinger breakout | SOLUSDT 3m | 16656 | -100.00 | 0.429 | 0.916 | -13.16 | 0.52 / 0.42 | 0.00 | 0.00 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `5c699085d3306b3e` |
| Q12 | EMA 9/21 cross | SPCX 15m | 487 | -56.79 | 0.695 | 0.942 | -24.04 | 0.78 / 0.68 | 0.20 | 0.00 | 69.02 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `d000c18cb7300359` |
| Q13 | POC bounce | ETHUSDT 30m | 1295 | -76.79 | 0.862 | 1.057 | -15.11 | 0.91 / 0.85 | 0.00 | 1.76 | 86.43 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `f6f079f9962070cb` |
| Q14 | Bollinger breakout | BTCUSDT 3m | 18561 | -100.00 | 0.305 | 0.943 | -12.03 | 0.40 / 0.33 | 0.00 | 0.00 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `4e77a1be6108f0af` |
| Q15 | stochastic cross | JUPUSDT 15m | 8346 | -100.00 | 0.721 | 1.004 | -13.25 | 0.80 / 0.72 | 0.00 | 0.20 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `70f97efc14907117` |
| Q16 | DI cross, ADX>25 | SOLUSDT 1m | 12595 | -100.00 | 0.097 | 0.693 | -13.28 | 0.16 / 0.08 | 0.00 | 0.00 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `7889b45cf034d8de` |
| Q17 | Supertrend | ETHUSDT 30m | 1419 | -87.89 | 0.586 | 0.976 | -15.11 | 0.71 / 0.49 | 0.00 | 0.00 | 88.66 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `59b53b133165e34d` |
| Q18 | Ichimoku breakout | SOLUSDT 1m | 80855 | -100.00 | 0.441 | 0.983 | -4.10 | 0.50 / 0.38 | 0.00 | 0.00 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `2e3a0d4c99c37991` |
| Q19 | Keltner breakout, S/R | HYPEUSDT 30m | 4155 | -100.00 | 0.282 | 0.459 | -39.35 | 0.31 / 0.33 | 0.00 | 0.00 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `adcd4918c94a19f7` |
| Q20 | POC bounce | JUPUSDT 3m | 16868 | -100.00 | 0.584 | 1.009 | -11.86 | 0.66 / 0.62 | 0.00 | 0.20 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `c43c7ed28bbe520e` |
| Q21 | stochastic cross | ETHUSDT 5m | 26831 | -100.00 | 0.413 | 1.021 | -11.21 | 0.51 / 0.35 | 0.00 | 0.20 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `814d633c450ef69f` |
| Q22 | Bollinger breakout, S/R | BTCUSDT 3m | 38724 | -100.00 | 0.006 | 0.148 | -8.45 | 0.01 / 0.02 | 0.00 | 0.00 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `ccc1bfa3d1d0b408` |
| Q24 | POC bounce | SPCX 30m | 330 | -70.41 | 0.542 | 0.683 | -50.54 | 0.62 / 0.42 | 0.00 | 0.00 | 82.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `cf5c192490dd1f7f` |
| Q25 | POC bounce | ETHUSDT 3m | 7431 | -100.00 | 0.669 | 0.996 | -12.84 | 0.75 / 0.65 | 0.00 | 0.00 | 99.99 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `c144dbf478180e38` |
| Q26 | Ichimoku, S/R | JUPUSDT 15m | 18799 | -100.00 | 0.406 | 0.636 | -17.74 | 0.44 / 0.41 | 0.00 | 0.00 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `380d53e834b0ba86` |
| Q28 | Ichimoku breakout | HYPEUSDT 15m | 8942 | -100.00 | 0.636 | 0.937 | -15.15 | 0.68 / 0.72 | 0.00 | 0.00 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `87776e6bf30dc29b` |
| Q29 | DI cross, ADX>25 | JUPUSDT 30m | 377 | -57.87 | 0.886 | 0.974 | -48.94 | 0.90 / 0.90 | 0.20 | 0.00 | 84.97 | G1 G3 G4 G6 | G1 G3 G4 G5 G6 G8 G9 | `2d4891e1ba1f4ba4` |
| Q30 | Ichimoku breakout | BTCUSDT 1m | 365975 | -100.00 | 0.034 | 0.951 | -0.92 | 0.06 / 0.07 | 0.00 | 0.00 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `f5148447ac6bc001` |
| Q31 | MACD histogram, S/R | SOLUSDT 15m | 4652 | -99.98 | 0.407 | 0.821 | -16.53 | 0.50 / 0.40 | 0.00 | 0.00 | 99.96 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `c9b25dac593875b1` |
| Q32 | VWAP bounce | ETHUSDT 1m | 28535 | -100.00 | 0.131 | 0.995 | -10.95 | 0.19 / 0.12 | 0.00 | 0.00 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `4e9e7e4aa9610f0e` |
| Q33 | Bollinger breakout, S/R | SUIUSDT 1m | 119388 | -100.00 | 0.011 | 0.125 | -2.87 | 0.02 / 0.01 | 0.00 | 0.00 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `e8963ebda209bf4d` |
| Q34 | VWAP bounce | JUPUSDT 30m | 7701 | -100.00 | 0.643 | 0.957 | -14.02 | 0.68 / 0.76 | 0.00 | 0.00 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `727e827bfe5588b4` |
| Q37 | Keltner breakout | SOLUSDT 30m | 4222 | -99.93 | 0.612 | 0.910 | -16.34 | 0.66 / 0.69 | 0.00 | 0.00 | 99.89 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `4ce424a180ab9670` |
| Q38 | POC bounce | HYPEUSDT 5m | 12024 | -100.00 | 0.466 | 1.010 | -11.56 | 0.57 / 0.49 | 0.00 | 0.20 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `7ed022216e10db05` |
| Q39 | EMA 9/21 cross | JUPUSDT 1m | 48405 | -100.00 | 0.250 | 1.019 | -6.67 | 0.31 / 0.18 | 0.00 | 0.20 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `301fd77e3e52dff9` |
| Q40 | DI cross, ADX>25 | SUIUSDT 30m | 478 | -54.83 | 0.625 | 0.930 | -18.82 | 0.66 / 0.73 | 0.00 | 0.00 | 61.06 | G1 G3 G4 G6 | G1 G3 G4 G5 G6 G8 G9 | `15f1c7c79b461dbd` |
| Q41 | PSAR reversal | ETHUSDT 3m | 22698 | -100.00 | 0.392 | 1.038 | -10.96 | 0.51 / 0.36 | 0.00 | 0.20 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `5dca2a61088fc8de` |
| Q43 | PSAR reversal | SOLUSDT 15m | 5860 | -99.97 | 0.564 | 1.009 | -12.21 | 0.66 / 0.54 | 0.00 | 0.20 | 99.93 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `14e7e6dd14206d6f` |
| Q44 | VWAP bounce | JUPUSDT 1m | 22995 | -100.00 | 0.324 | 1.014 | -11.28 | 0.43 / 0.33 | 0.00 | 0.20 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `239f08656f6149f4` |
| Q45 | Supertrend | SOLUSDT 3m | 16007 | -100.00 | 0.440 | 0.969 | -12.12 | 0.55 / 0.41 | 0.00 | 0.00 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `ad177f10c49ced4e` |
| Q46 | DI cross, ADX>25 | BTCUSDT 5m | 1930 | -92.61 | 0.576 | 1.029 | -13.06 | 0.68 / 0.58 | 0.00 | 0.20 | 91.33 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `bbc8e2c8e336b609` |
| Q48 | POC bounce | ETHUSDT 15m | 5591 | -99.96 | 0.495 | 1.004 | -12.43 | 0.61 / 0.45 | 0.00 | 0.20 | 99.91 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `1325025ba31b7ce8` |
| Q49 | Bollinger breakout | SUIUSDT 3m | 23730 | -100.00 | 0.434 | 0.977 | -11.94 | 0.53 / 0.44 | 0.00 | 0.00 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `b56d86b8b123fab4` |
| Q50 | stochastic cross, S/R | SOLUSDT 15m | 10928 | -100.00 | 0.499 | 0.969 | -12.83 | 0.59 / 0.51 | 0.00 | 0.00 | 100.00 | G1 G3 G4 G5 G6 | G1 G3 G4 G5 G6 G8 G9 | `2eb5711049ca4fa5` |

## Family notes

**VWAP and POC bounces (Q01, Q05, Q13, Q20, Q24, Q25, Q32, Q34, Q38, Q44, Q48).**
The bounce family trades often and dies by the round trip: the fixed-percentage
variants target half a percent to two percent against a fourteen bps pack round
trip, and the best zero-cost factor in the family is
1.082. The POC variant adds a
rolling volume profile on top of the same arithmetic.

**Trend mechanisms (Q07, Q16, Q17, Q29, Q40, Q43, Q45, Q46, Q08, Q41).** DI
crosses, Supertrend and Parabolic SAR re-entries with two-to-three ATR targets:
on one-minute bars the stop is inside the noise, on 15m-30m bars the trade
count collapses below the sample floor.

**Ichimoku and Keltner breakouts (Q04, Q18, Q19, Q22, Q26, Q28, Q30, Q33, Q37).**
Breakout entries with the 20-bar range as stop and target: the target and the
stop are the same distance, so the book needs a win rate above fifty percent
after costs, and none has one.

**Stochastic crosses and EMA crosses (Q03, Q12, Q15, Q21, Q31, Q39, Q50).**
The crossover family is the largest and the weakest: negative expectancy lower
bounds across the board.

## What the cost columns say

The breakeven column is the honest summary: a book must survive a per-side
cost of at least the gate's 5.5 bps to be tradable at all, and twice that to
clear G8. The best breakeven in the pack is
2.54 bps per side —
below
the doubled gate cost. Every artifact carries `pre_registered: false`, so the
G7 multiple-testing haircut applies on top of the ledger's program-level one.

## Reproduce

    python code/_pack50c_audit.py
    python code/vrun.py run --strategy pack50c --tf 5m --symbol SPCX --set strat=1
    python code/vrun.py pverify --ids <ids from results/_pack50c_ids.json> --workers 2
    python code/vrun.py guard --report results/pack50c_report.md
