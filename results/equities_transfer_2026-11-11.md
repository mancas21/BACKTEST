# S&P index transfer — every strategy in the repo run on the equity series

- generated: `2026-11-11T19:26:13Z`
- equities data: `data/alpaca_1d` — real Alpaca DAILY bars; SPY (the S&P index ETF) and QQQ (Nasdaq 100)
- method: the SAME engine and the SAME declared parameters on another market. The harness's `data_dir` override re-points the input at `<data_dir>/<SYMBOL>_<TF>.csv`; the directory is part of the artifact's core, so the run_id cannot collide with the crypto one
- timeframe: the equity store is daily, so the transfer runs at 1d. The crypto cells run at their own intraday timeframe — market AND timeframe change together, so this is a transfer test, not a like-for-like comparison
- costs: `standard` = the repo's 11 bps round trip where the engine takes a cost parameter, otherwise the engine's own declared costs; `pure` = the same signals with no costs at all

## Verdict

**NO EDGE TRANSFERS TO THE S&P INDEX.** On SPY, 5 of the 10 cells that produced a number LOSE. The exceptions are listed below, and none of them clears the bar either.

| strategy | regime | n | net % | PF | run_id |
|---|---|---:|---:|---:|---|
| ffs | standard | 1 | 0.92 | inf | `bc190acdbc641394` |

The smallest sample among those positives is 1 closed trades, against the repo's floor of 30.

Buy & hold on the same window returned between +350.76% and +351.95% on SPY — each engine reports its own benchmark and they differ by the closing basis — and every cell on SPY is far below it.

On QQQ, 5 cells are positive and every one of them sits below the repo's sample floor, with its result carried by one or two trades (see the table).

The cbpack family on SPY (the repo's declared equities adaptation, seven strategies ran): 0 passed every gate, 0 beat buy & hold, 1 cleared PF above 1.2 with the sample floor, and the best one returned 15.76% net against an index that returned +350.76% on the same window. Artifact `ef76eae918ddf6d5`.

The cbpack family on QQQ (the repo's declared equities adaptation, seven strategies ran): 0 passed every gate, 0 beat buy & hold, 3 cleared PF above 1.2 with the sample floor, and the best one returned 23.63% net against an index that returned +607.07% on the same window. Artifact `f34b6a9d5eace74e`.

The deeper point is about TIMEFRAME, not about the index: most of this repo's books trade intraday structure (intraday sessions, sweeps, squeezes, HTF alignment) that does not exist in a daily bar. A zero-trade cell there is a statement about the timeframe. Reading it as a failed strategy on the index would be wrong, and reading it as a pass would be worse.

## Cells

| strategy | symbol | regime | n | net % | PF | win % | max DD % | buy&hold % | run_id |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| eqpack | SPY | standard | - | - | - | - | - | 350.76 | `ef76eae918ddf6d5` |
| eqpack | SPY | pure | - | - | - | - | - | 350.76 | `7f204f1a85300b6a` |
| eqpack | SPY | extra:eq | - | - | - | - | - | 350.76 | `66e278f18ed51cbc` |
| eqpack | QQQ | standard | - | - | - | - | - | 607.07 | `f34b6a9d5eace74e` |
| eqpack | QQQ | pure | - | - | - | - | - | 607.07 | `ae70a3dabb96d042` |
| eqpack | QQQ | extra:eq | - | - | - | - | - | 607.07 | `fae78a6d68f77157` |
| cvrmd | SPY | standard | 0 | 0 | 0 | 0 | 0 | - | `2eb5fe1e4d2caebe` |
| cvrmd | QQQ | standard | 0 | 0 | 0 | 0 | 0 | - | `b5c4bcb32aa91e9b` |
| ffs | SPY | standard | 1 | 0.92 | inf | 1 | -1.14 | - | `bc190acdbc641394` |
| ffs | QQQ | standard | 0 | 0 | 0 | 0 | 0 | - | `2e95d3304ca9de47` |
| emaadx | SPY | standard | 7 | -7.14 | 0.5383 | 28.6 | 14.94 | 350.76 | `48a916b8b4bf4866` |
| emaadx | QQQ | standard | 8 | 11.97 | 1.4983 | 37.5 | 13.07 | 607.07 | `643e89162b1967cc` |
| scalpwave | SPY | standard | 21 | -2.74 | 0.8069 | 33.3 | -68.12 | - | `37b7af84e45bb772` |
| scalpwave | QQQ | standard | 17 | 8.35 | 1.9314 | 52.9 | -66.61 | - | `032c0fe2d4dfce9e` |
| pack20 | SPY | standard | 3 | -4.85 | 0 | - | -4.85 | 351.95 | `db1fe26a129d3959` |
| pack20 | QQQ | standard | 3 | 11.95 | 15.7472 | - | -0.72 | 607.49 | `bfc192689b9e23bf` |
| qs096 | SPY | standard | 17 | -7.17 | 0.1634 | 5.9 | -8.45 | - | `500afd611f6f7ec1` |
| qs096 | SPY | pure | 17 | -6.92 | 0.1750 | 5.9 | -8.27 | - | `fc95155b303cb1b8` |
| qs096 | QQQ | standard | 10 | 1.49 | 1.4011 | 20 | -2.70 | - | `491666f94498daef` |
| qs096 | QQQ | pure | 10 | 1.72 | 1.4719 | 20 | -2.68 | - | `519f853fc53f4904` |

Artifacts: `results/runs/<run_id>` (the run_id column names the file).

## The cbpack family on equities, strategy by strategy

`eqpack` is the repo's declared equities adaptation of the cbpack pack (same hash-locked engine, daily bars, HTF aligned to the daily chart, candle-proxy flow). Its artifact reports one row per strategy.

| symbol | regime | strategy | n | net % | PF | win % | maxDD % | buy&hold % | excess pp | top-5 share % |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SPY | standard | `S01` | 69 | 4.83 | 1.0968 | 39.1 | -12.49 | 350.76 | -345.93 | 247.23 |
| SPY | standard | `S02` | 47 | 3.87 | 1.1297 | 31.9 | -14.39 | 350.76 | -346.90 | 540.48 |
| SPY | standard | `S03` | 8 | 0.39 | 1.0733 | 37.5 | -4.65 | 350.76 | -350.37 | 1464.85 |
| SPY | standard | `S04` | 50 | -15.18 | 0.5747 | 26 | -17.97 | 350.76 | -365.95 | - |
| SPY | standard | `S05` | 103 | 15.76 | 1.5380 | 68 | -5.41 | 350.76 | -335 | 47.51 |
| SPY | standard | `S09` | 8 | -3.48 | 0.4552 | 25 | -5.33 | 350.76 | -354.24 | - |
| SPY | standard | `S10` | 14 | 15.35 | 2.8323 | 35.7 | -8.85 | 350.76 | -335.41 | 154.57 |
| SPY | pure | `S01` | 70 | 11.58 | 1.2362 | 40 | -11.90 | 350.76 | -339.18 | 110.49 |
| SPY | pure | `S02` | 47 | 6.24 | 1.2181 | 34 | -13.39 | 350.76 | -344.52 | 342.95 |
| SPY | pure | `S03` | 8 | 0.92 | 1.1869 | 37.5 | -4.31 | 350.76 | -349.84 | 634.91 |
| SPY | pure | `S04` | 50 | -13.10 | 0.6191 | 26 | -16.07 | 350.76 | -363.86 | - |
| SPY | pure | `S05` | 103 | 22.18 | 1.7832 | 68.9 | -4.73 | 350.76 | -328.58 | 36.24 |
| SPY | pure | `S09` | 8 | -2.81 | 0.5284 | 25 | -5.05 | 350.76 | -353.58 | - |
| SPY | pure | `S10` | 14 | 15.78 | 2.9352 | 35.7 | -8.76 | 350.76 | -334.98 | 151.68 |
| SPY | extra:eq | `S01` | 69 | 9.13 | 1.1884 | 39.1 | -11.95 | 350.76 | -341.64 | 137.13 |
| SPY | extra:eq | `S02` | 47 | 6.01 | 1.2095 | 34 | -13.48 | 350.76 | -344.75 | 354.95 |
| SPY | extra:eq | `S03` | 8 | 0.89 | 1.1801 | 37.5 | -4.33 | 350.76 | -349.87 | 655.23 |
| SPY | extra:eq | `S04` | 50 | -13.28 | 0.6150 | 26 | -16.23 | 350.76 | -364.04 | - |
| SPY | extra:eq | `S05` | 103 | 21.51 | 1.7582 | 68.9 | -4.75 | 350.76 | -329.25 | 37.08 |
| SPY | extra:eq | `S09` | 8 | -2.86 | 0.5229 | 25 | -5.07 | 350.76 | -353.62 | - |
| SPY | extra:eq | `S10` | 14 | 15.75 | 2.9264 | 35.7 | -8.77 | 350.76 | -335.02 | 151.91 |
| QQQ | standard | `S01` | 81 | 19.84 | 1.3440 | 43.2 | -6.47 | 607.07 | -587.22 | 61.37 |
| QQQ | standard | `S02` | 39 | 23.63 | 2.0835 | 46.2 | -9.97 | 607.07 | -583.44 | 104.38 |
| QQQ | standard | `S03` | 4 | 1.30 | 1.4954 | 50 | -2.67 | 607.07 | -605.76 | 301.86 |
| QQQ | standard | `S04` | 57 | -8.19 | 0.7866 | 29.8 | -15.01 | 607.07 | -615.26 | - |
| QQQ | standard | `S05` | 99 | 7.71 | 1.2711 | 65.7 | -4.08 | 607.07 | -599.35 | 90.62 |
| QQQ | standard | `S09` | 13 | 0.53 | 1.0562 | 38.5 | -5.37 | 607.07 | -606.54 | 1880.33 |
| QQQ | standard | `S10` | 10 | 21.29 | 6.1759 | 60 | -6.67 | 607.07 | -585.78 | 116.29 |
| QQQ | pure | `S01` | 81 | 24.44 | 1.4330 | 43.2 | -6.13 | 607.07 | -582.63 | 52.18 |
| QQQ | pure | `S02` | 39 | 25.40 | 2.2032 | 46.2 | -9.76 | 607.07 | -581.66 | 98.65 |
| QQQ | pure | `S03` | 4 | 1.49 | 1.5899 | 50 | -2.65 | 607.07 | -605.58 | 269.52 |
| QQQ | pure | `S04` | 57 | -6.43 | 0.8283 | 29.8 | -14.04 | 607.07 | -613.50 | - |
| QQQ | pure | `S05` | 99 | 11.86 | 1.4273 | 67.7 | -3.68 | 607.07 | -595.21 | 61.74 |
| QQQ | pure | `S09` | 13 | 1.25 | 1.1400 | 38.5 | -5.20 | 607.07 | -605.81 | 814.34 |
| QQQ | pure | `S10` | 10 | 21.57 | 6.3682 | 60 | -6.67 | 607.07 | -585.50 | 115.52 |
| QQQ | extra:eq | `S01` | 81 | 24.18 | 1.4274 | 43.2 | -6.15 | 607.07 | -582.89 | 52.63 |
| QQQ | extra:eq | `S02` | 39 | 25.24 | 2.1924 | 46.2 | -9.77 | 607.07 | -581.83 | 99.13 |
| QQQ | extra:eq | `S03` | 4 | 1.48 | 1.5821 | 50 | -2.65 | 607.07 | -605.59 | 271.78 |
| QQQ | extra:eq | `S04` | 57 | -6.51 | 0.8263 | 29.8 | -14.05 | 607.07 | -613.58 | - |
| QQQ | extra:eq | `S05` | 99 | 11.43 | 1.4113 | 67.7 | -3.72 | 607.07 | -595.64 | 63.73 |
| QQQ | extra:eq | `S09` | 13 | 1.20 | 1.1334 | 38.5 | -5.21 | 607.07 | -605.87 | 849.40 |
| QQQ | extra:eq | `S10` | 10 | 21.54 | 6.3534 | 60 | -6.67 | 607.07 | -585.52 | 115.58 |

## The crypto counterpart

One crypto cell per adapter — its highest PF over the crypto rows (a selection, shown for scale, not a measurement). The numbers are read from the cited artifact. The equity cells are not a like-for-like comparison (different market, different timeframe); this column only says how much there was to transfer.

| strategy | crypto cell | crypto n | crypto PF | crypto net % | crypto run_id |
|---|---|---:|---:|---:|---|
| eqpack | QQQ 1d | - | - | - | `ae70a3dabb96d042` |
| eqpack | QQQ 1d | - | - | - | `ae70a3dabb96d042` |
| cvrmd | SUIUSDT 1h | 49 | 1.7881 | 16.74 | `00c8c19179ea05ba` |
| cvrmd | SUIUSDT 1h | 49 | 1.7881 | 16.74 | `00c8c19179ea05ba` |
| ffs | HYPEUSDT 15m | 305 | 1.0055 | -11.46 | `7a0dcdd7a146e941` |
| ffs | HYPEUSDT 15m | 305 | 1.0055 | -11.46 | `7a0dcdd7a146e941` |
| emaadx | LINKUSDT 1h | 226 | 1.1426 | 168.68 | `d91d4860ad35c60d` |
| emaadx | LINKUSDT 1h | 226 | 1.1426 | 168.68 | `d91d4860ad35c60d` |
| scalpwave | SUIUSDT 15m | 5627 | 0.8624 | -99.73 | `2d4064eeea7e9785` |
| scalpwave | SUIUSDT 15m | 5627 | 0.8624 | -99.73 | `2d4064eeea7e9785` |
| qs096 | QQQ 1d | 10 | 1.4719 | 1.72 | `519f853fc53f4904` |
| qs096 | QQQ 1d | 10 | 1.4719 | 1.72 | `519f853fc53f4904` |

## Cells that could not run, and why

Every refusal is the engine's own guard: each engine declares the timeframes, symbols or columns it supports, and refuses loudly instead of silently producing a number.

| strategy | regime | reason |
|---|---|---|
| cbpack | standard | REFUSED: htf minutes must be >= chart timeframe |
| cbpackf | standard | REFUSED: htf minutes must be >= chart timeframe |
| prompts100 | standard | KeyError: 'id' |
| top10 | standard | KeyError: 'id' |
| smqe | standard | REFUSED: smqe: unsupported tf '1d' (use 1h/15m/5m/1m) |
| smqe11 | standard | REFUSED: smqe11 supports 1h only (got tf='1d'); the engine's funding factor assumes the 1h chart |
| fingrad | standard | REFUSED: fingrad: unsupported tf '1d' (use 1h/15m/5m/1m) |
| botstrat | standard | REFUSED: botstrat only runs the 1h file; got SPY_1d.csv (the engine hardcodes data/binance_klines_1h) |
| botstrat | standard | REFUSED: botstrat only runs the 1h file; got QQQ_1d.csv (the engine hardcodes data/binance_klines_1h) |
| hmaaoadx | standard | REFUSED: hmaaoadx supports 1h only (got tf='1d') |
| cbot | standard | KeyError: "['taker_buy_base'] not in index" |
| qs097 | standard | REFUSED: qs097 traded symbol must be one of ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'HYPEUSDT', 'SUIUSDT', 'JUPUSDT') (got 'SPY') |
| qs097 | standard | REFUSED: qs097 traded symbol must be one of ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'HYPEUSDT', 'SUIUSDT', 'JUPUSDT') (got 'QQQ') |

## Adapters that cannot be pointed at the equity series at all

| adapter | why |
|---|---|
| qs / qsf / qsb / qsc / qsd | fixed taker-flow leg set per card; the engine needs the taker-buy column, which equity bars do not carry |
| pack50 / pack50b / pack50c / pack50d / pack100 | pair books with a fixed crypto leg list and a per-symbol funding file |
| dspack / dspack2 | fixed five-name crypto universe (BTC/ETH/SOL/SUI/XRP) |
| xsf / xsb / xsc | fixed fourteen-name crypto universe, rank-rotation books |
| cand7 | fixed leg baskets over crypto 1h taker bars |
| q10 | card-based universe of the majors |
| mp20 / mps20 / mpv3 | portfolio books, not a single symbol |
| xrpneutral / xrpneutral1m | 15m books by construction (the deployed neutral book) |
| bookreplay | replay of one book on aggTrades; the tape is XRP-only |
| rsimr / gate2 / gatecal / q10diag | diagnostics and null calibrators, not strategies |
| sax | the engine file no longer exists on disk (unrunnable by design) |

## A clarification about `SPXUSDT`

The repo's store also carries `SPXUSDT` (a Binance perpetual whose base asset is `SPX`) and it is easy to read that as the S&P index. It is not: the daily-return correlation with the real SPY series over the overlap is 0.31, while the correlation of SPY with QQQ is 0.95. `SPXUSDT` is a crypto token that happens to be named SPX, and the repo's `SPXUSDT` rows are not index exposure.

## How to read this

- A zero-trade cell is a timeframe statement, not a verdict on the S&P index. The intraday books (session VWAP, sweeps, squeezes, HTF alignment) have no daily analogue.
- The positive QQQ cells sit below the repo's n >= 30 floor and their best five trades carry more than the whole result: that is a selection, not an edge.
- Buy & hold on the same window is the bar to clear, and no cell is anywhere near it.
- No funding is charged anywhere: equity bars carry no perp funding, and no funding file exists for SPY or QQQ.
- These are paper measurements on real equity bars through the same engines. Nothing here is a live order.

