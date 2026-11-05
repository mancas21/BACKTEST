# SPECS — @nftepml backtest lab

Every posted strategy's recipe, condensed from the source that defines it.
`SOURCE` is a repo-relative path with the line(s) the spec was distilled from.
`code/x_spec_check.py` verifies that every numeric token in an entry appears
literally in the cited file — parameters may not be invented.

Common conventions (all engines): signal on closed bar, fill next open unless
noted, fees on every fill, 1% of equity risked per trade unless noted,
repo costs 11 bps round trip unless noted.

The lab keeps three files in sync. `registry` rows cite their artifact; `SPECS.md`
sections cite their source file; every numeric token here is checked against the
cited file by `code/x_spec_check.py`.

### Post-to-spec map

| Post family / adapter | Spec sections |
|---|---|
| top10 | top10-* (ten sections) |
| xrpneutral | xrpneutral-v1, xrpneutral-v2 |
| xrpneutral1m | xrpneutral-1m |
| cbpackf | cbpackf-s02, s04, s06, s07, s10 |
| qs | qs-001 .. qs-010 |
| pack100 | pack100-13, 21, 29, 45, 53, 61, 69, 77, 82, 93 |
| smqe | smqe-v2-core |
| emaadx | emaadx-ema-adx |
| fingrad | fingrad-hma-ao-adx |
| rsimr | rsimr-sol-usdc |
| mpv3 | mpv3-s10-pure-ew-momentum |

---

## top10-168-bar-breakout
SOURCE: code/top10_engine.py:176-181
MECHANISM: Long breakout above the rolling 168-bar high; exit on breakdown below the rolling 72-bar low.
RULES: entry = close > prior rolling highest high (168); exit = close < prior rolling lowest low (72); stop = 2.5 x ATR(14); fills at next open; risk 1% of equity from stop distance; long only; BTCUSDT hourly.
COSTS: 11 bps round trip.

## top10-donchian-breakout
SOURCE: code/top10_engine.py:153-160
MECHANISM: Donchian-55 breakout, long only, BTCUSDT hourly.
RULES: entry = close > Donchian(55) prior upper channel; exit = close < Donchian(20) prior lower channel; stop = 3 x ATR(14); fills at next open; risk 1% of equity from stop distance.
COSTS: 11 bps round trip.

## top10-donchian-chandelier
SOURCE: code/top10_engine.py:183-188
MECHANISM: Donchian breakout with a Chandelier-style trailing stop, JUPUSDT hourly.
RULES: entry = close > 30-bar prior high; exit = trailing stop at 3 x ATR(14) from the highest high since entry; stop = 3 x ATR(14); fills at next open; risk 1% of equity from stop distance.
COSTS: 11 bps round trip.

## top10-ema-cross
SOURCE: code/top10_engine.py:145-152
MECHANISM: EMA cross, long and short, ETHUSDT hourly.
RULES: entry = cross of EMA(20) over EMA(50) in direction of ATR(14) stop; exit = reverse cross; stop = 2 x ATR(14); fills at next open; risk 1% of equity from stop distance.
COSTS: 11 bps round trip.

## top10-hour-of-day-filter
SOURCE: code/top10_engine.py:207-215
MECHANISM: EMA cross filtered to specific UTC hours, JUPUSDT hourly, long and short.
RULES: entry = cross of EMA(20) and EMA(50) during UTC hours 14-17; exit = reverse EMA(20)/EMA(50) cross; stop = 2 x ATR(14); fills at next open; risk 1% of equity from stop distance.
COSTS: 11 bps round trip.

## top10-keltner-con-rsi
SOURCE: code/top10_engine.py:199-206
MECHANISM: Keltner channel breakout with RSI confirmation, HYPEUSDT hourly.
RULES: entry = close > Keltner(20, 2) upper band and RSI(14) > 60; exit = close < EMA(20); stop = 2 x ATR(14); fills at next open; risk 1% of equity from stop distance.
COSTS: 11 bps round trip.

## top10-price-funding-divergence
SOURCE: code/top10_engine.py:230-238
MECHANISM: Price-funding divergence as a short signal, SUIUSDT hourly, funding accrued per real settlement.
RULES: entry (short) = close at/below prior 48-bar low and funding at its 30-bar extreme; exit = after 24 bars; stop = 2 x ATR(14); fills at next open; risk 1% of equity from stop distance.
COSTS: 11 bps round trip; funding accrued at real settlement timestamps.

## top10-range-expansion
SOURCE: code/top10_engine.py:189-198
MECHANISM: Range-expansion bar with strong close, SOLUSDT hourly.
RULES: entry (long) = bar range > 2 x ATR(14) and close in the upper part of the range; exit = close < prior bar low; stop = ATR(14)-based; fills at next open; risk 1% of equity from stop distance.
COSTS: 11 bps round trip.

## top10-regression-slope
SOURCE: code/top10_engine.py:161-175
MECHANISM: Linear-regression slope trend follower, SOLUSDT hourly.
RULES: entry = regression slope of close positive with channel confirmation, mirrored for shorts; exit = slope sign flips; stop = ATR(14)-based; fills at next open; risk 1% of equity from stop distance.
COSTS: 11 bps round trip.

## top10-sunday-to-monday-reversion
SOURCE: code/top10_engine.py:216-229
MECHANISM: Sunday reversion to Monday, ETHUSDT hourly, long only.
RULES: entry = Sunday (UTC day 6) after 23:00 with a deep drop vs the Sunday open; exit = Monday 23:00 UTC or Tuesday 00:00 UTC; stop = 2 x ATR(14); fills at next open; risk 1% of equity from stop distance.
COSTS: 11 bps round trip.

## xrpneutral-v1
SOURCE: AGENTS.md
MECHANISM: Delta-neutral two-sided grid on XRPUSDT perps, funding paid by the long book.
RULES: entry = grid levels every 0.25 x equity per level, 10,000 USDT start; delta cap 50% of equity; funding accrued at real settlements; fills resolved minute by minute for the 1m record.
COSTS: maker 0.02% / taker 0.05% per side; funding charged.

## xrpneutral-v2
SOURCE: AGENTS.md
MECHANISM: Delta-neutral two-sided grid on XRPUSDT perps, 5 levels per side.
RULES: entry = 25 USDT per level, 5 levels per side, leverage 10x; net delta capped at 200% of equity (the v1 50% cap could not fund a 25 USDT lot); funding accrued at real settlements.
COSTS: maker 0.02% / taker 0.05% per side; funding charged.

## xrpneutral-1m
SOURCE: AGENTS.md
MECHANISM: The v2 neutral book with fills resolved minute by minute on a 1m tape.
RULES: entry = 25 USDT per level, 5 levels per side, leverage 10x; a bar resolves minute by minute only when its 1m tape is complete, otherwise the bar keeps the original 15m resolution; same-minute touches are counted and banned, never assumed; funding accrued at real settlements.
COSTS: maker 0.02% / taker 0.05% per side; funding charged.

## cbpackf-s02
SOURCE: code/cbpack_funding_engine.py:73-74
MECHANISM: Donchian channel breakout filtered by taker-flow z-score and higher-timeframe trend, funding charged.
RULES: entry = N-bar channel breakout with taker-flow z confirmation and HTF trend alignment; exit = channel exit + ATR stop; funding accrued at real settlements.
COSTS: repo costs; funding charged.

## cbpackf-s04
SOURCE: code/cbpack_funding_engine.py:75-76
MECHANISM: VWAP fade in range regimes only, funding charged.
RULES: entry = price at rolling-VWAP sigma extreme with efficiency ratio below max and flow turning; exit = at VWAP + ATR stop + time stop; funding accrued at real settlements.
COSTS: repo costs; funding charged.

## cbpackf-s06
SOURCE: code/cbpack_funding_engine.py:77-78
MECHANISM: Asia session range breakout (UTC), funding charged.
RULES: entry = break of the Asia UTC range with volume spike, flow z-score, max 1 entry per day; exit = session end + ATR stop/target; funding accrued at real settlements.
COSTS: repo costs; funding charged.

## cbpackf-s07
SOURCE: code/cbpack_funding_engine.py:78-79
MECHANISM: Funding extreme fade, funding charged both ways.
RULES: entry = funding z-score at an extreme and price rolling over EMA; exit = ATR stop/target + time stop; funding accrued at real settlements.
COSTS: repo costs; funding charged.

## cbpackf-s10
SOURCE: code/cbpack_funding_engine.py:81-82
MECHANISM: Vol-targeted time-series momentum, funding charged.
RULES: entry = N-bar return / realised vol above threshold with hysteresis (exit below zero); exit = sign flip + wide ATR stop; funding accrued at real settlements.
COSTS: repo costs; funding charged.

## qs-001
SOURCE: code/qs_strats.py:84-112
MECHANISM: Moving-average trend continuation.
RULES: entry = edge on EMA(20)/EMA(100) cross with close beyond EMA(200), ADX >= 15, ATR >= its 10th percentile, no data gaps; exit = reverse cross or two closes beyond EMA(100); stop = 2 x ATR(14) from signal close.
COSTS: repo costs.

## qs-002
SOURCE: code/qs_strats.py:113-136
MECHANISM: EMA alignment with volatility confirmation.
RULES: entry = edge on stacked EMA(10) > EMA(30) > EMA(100) with close > EMA(10) and ATR above its 50-bar median; mirror for shorts; exit = EMA(10)/EMA(30) cross back; stop = 2 x ATR(14).
COSTS: repo costs.

## qs-003
SOURCE: code/qs_strats.py:137-165
MECHANISM: Supertrend continuation.
RULES: entry = edge on Supertrend(10, 3) flip, at most a few flips in the last 20 bars (no chop); exit = opposite flip; stop = Supertrend line at entry, capped at 3 x ATR.
COSTS: repo costs.

## qs-004
SOURCE: code/qs_strats.py:166-192
MECHANISM: Donchian channel breakout.
RULES: entry = close above prior 55-bar high (mirror short); stop = closer of 2 x ATR(14) and the 20-bar opposite extreme; exit = breakdown/back inside channel; ATR floor filter.
COSTS: repo costs.

## qs-005
SOURCE: code/qs_strats.py:193-220
MECHANISM: Time-series momentum, z-scored.
RULES: entry = 96-bar return z-score above 1 and positive 20-bar return (mirror short); exit = return sign flips / z normalises; stop = 2 x ATR(14).
COSTS: repo costs.

## qs-006
SOURCE: code/qs_strats.py:221-244
MECHANISM: ADX-filtered directional continuation.
RULES: entry = +DI over -DI with ADX > 25 rising over 3 bars and close > EMA(50) (mirror short); exit = ADX < 20 or DI cross; stop = 2 x ATR(14).
COSTS: repo costs.

## qs-007
SOURCE: code/qs_strats.py:245-292
MECHANISM: Higher-timeframe trend with lower-timeframe entries.
RULES: entry = HTF (6x bars) EMA(50) > EMA(200) with adequate spread, LTF EMA(20) crosses EMA(50) on the HTF side; exit = LTF reverse cross; stop = 2 x ATR(14).
COSTS: repo costs.

## qs-008
SOURCE: code/qs_strats.py:293-324
MECHANISM: Trend pullback continuation.
RULES: entry = pullback to EMA(20) within EMA(50)/EMA(200) uptrend with ADX >= 18, buy on reclaim of prior bar high; stop at pullback swing low bounded to [1, 3] x ATR; target per sheet.
COSTS: repo costs.

## qs-009
SOURCE: code/qs_strats.py:325-348
MECHANISM: Volatility-adjusted momentum.
RULES: entry = 48-bar return / return-sigma in the top tercile and positive (mirror short), gated below the 97th percentile vol; exit = rank falls / score flips; stop = 2 x ATR(14).
COSTS: repo costs.

## qs-010
SOURCE: code/qs_strats.py:349-378
MECHANISM: Breakout continuation after consolidation.
RULES: entry = close above 30-bar box high + 0.1 x ATR with box range < 3 x ATR and volume > 1.2 x its 20-bar mean; mirror short; stop = box low capped at 3 x ATR; exit on opposite break or trail.
COSTS: repo costs.

## smqe-v2-core
SOURCE: code/smqe_engine.py:8-40
MECHANISM: CVRMD v1.1 core — MACD histogram divergence, VWAP band tag, CVD confirmation, RSI filter.
RULES: long = bullish MACD(12,26,9) histogram divergence on 3/3 pivots (separation 5 to 60 bars) with price at/below the session VWAP lower band closing back above it, EMA(3) of CLV x volume above zero, RSI(14) <= 30+5 or below 50 and rising; mirror short; fills at signal-bar close; stop = max(1.5 x ATR(14), 0.2% of close).
COSTS: 0.06% per side; slippage 0 ticks.

## emaadx-ema-adx
SOURCE: code/emaadx_engine.py:6-30
MECHANISM: EMA cross with ADX filter, bracket exits.
RULES: long = EMA(20) crosses EMA(50) with ADX >= 25 and +DI > -DI; mirror short; SL = close minus 2 x ATR(14) at the signal bar; TP = close plus 4 x ATR(14) equivalent (rr 2); fills at signal-bar close (process_orders_on_close); 100% equity; commission 0.05% per fill.
COSTS: 0.05% per fill (author); repo 6 bps + 5 bps per fill.

## fingrad-hma-ao-adx
SOURCE: code/fingrad_engine.py:7-45
MECHANISM: HMA(21) with AO and ADX confluence, HTF filter, daily-loss breaker.
RULES: long = close > HMA with AO > 0 and AO rising (mode A), or ADX crossed above 25 within 3 bars with DI in the trade direction (mode B); short mirrored; exit = HMA loss or AO flip; hard stop = 2 x ATR(14) of the signal bar; risk 1% of equity per stop distance, max 10x notional; daily loss breaker 3% of day-start equity.
COSTS: 0.05% fee + 0.01% slip per side; repo 6 bps + 5 bps.

## rsimr-sol-usdc
SOURCE: code/rsi_mr_engine.py:6-40
MECHANISM: RSI mean reversion, SOL/USDC spot only, long only.
RULES: entry = flat and RSI(14) < 30 at close, market buy next open; exit = RSI(14) > 70 at close, market sell next open; stop = 2 x ATR(14) below fill, frozen at signal; stop checked intrabar first, gaps fill at open; risk 1% of equity to stop distance, max full-equity notional, no leverage.
COSTS: repo 11 bps round trip.

## mpv3-s10-pure-ew-momentum
SOURCE: code/mpv3_engine.py:1-40
MECHANISM: Pure equal-weight momentum portfolio, weekly rebalance, 20-day momentum filter.
RULES: portfolio = AVAX, BTC, ETH, LINK, SOL; signal at bar close, rebalance at next open; momentum-rank picks long constituents, equal weight; fees on every dollar of turnover; 100,000 start.
COSTS: repo 11 bps round trip (5 bps fee + 0.5 bps slip per side).

## pack100-13
SOURCE: content/spec_sources/strategy_prompts_100-sonnet-claude.md:105-111
MECHANISM: Consecutive down bars bounce, BTCUSDT.
RULES: long = after 4 consecutive red closes with close > EMA(200); exit = close > previous bar high; stop = ATR(14) * 2; long only; fills at next open; risk 1% of equity per trade.
COSTS: prompt declares none; repo 11 bps round trip applied for the measured runs.

## pack100-21
SOURCE: content/spec_sources/strategy_prompts_100-sonnet-claude.md:158-164
MECHANISM: MACD(12,26,9) trend, BTCUSDT.
RULES: long = MACD crosses above signal while MACD > 0; exit = MACD crosses below signal; stop = ATR(14) * 2; long only; fills at next open; risk 1% of equity per trade.
COSTS: prompt declares none; repo 11 bps round trip applied for the measured runs.

## pack100-29
SOURCE: content/spec_sources/strategy_prompts_100-sonnet-claude.md:206-212
MECHANISM: KAMA(10,2,30) trend, BTCUSDT.
RULES: entry = close crosses above KAMA with KAMA rising; exit = close crosses below KAMA; short mirror; stop = ATR(14) * 2; fills at next open; risk 1% of equity per trade.
COSTS: prompt declares none; repo 11 bps round trip applied for the measured runs.

## pack100-45
SOURCE: content/spec_sources/strategy_prompts_100-sonnet-claude.md:307-313
MECHANISM: Impulse-bar continuation, BTCUSDT.
RULES: impulse = bar return more than 3 standard deviations of the last 100 bar returns; entry = next open in impulse direction (long and short); exit = after 6 bars; stop = ATR(14) * 2; risk 1% of equity per trade.
COSTS: prompt declares none; repo 11 bps round trip applied for the measured runs.

## pack100-53
SOURCE: content/spec_sources/strategy_prompts_100-sonnet-claude.md:360-366
MECHANISM: True Strength Index (25,13), BTCUSDT.
RULES: long = TSI crosses above its 13-bar signal while TSI > 0; exit = TSI crosses below signal; stop = ATR(14) * 2; long only; fills at next open; risk 1% of equity per trade.
COSTS: prompt declares none; repo 11 bps round trip applied for the measured runs.

## pack100-61
SOURCE: content/spec_sources/strategy_prompts_100-sonnet-claude.md:413-419
MECHANISM: Delta-proxy momentum, BTCUSDT.
RULES: long = 10-bar sum of delta proxy (close-open)/(high-low) x volume above 2 times its own 100-bar standard deviation and close > EMA(20); exit = the 10-bar sum below zero; stop = ATR(14) * 2; long only; fills at next open; risk 1% of equity per trade.
COSTS: prompt declares none; repo 11 bps round trip applied for the measured runs.

## pack100-69
SOURCE: content/spec_sources/strategy_prompts_100-sonnet-claude.md:466-472
MECHANISM: Break-of-structure pullback, BTCUSDT.
RULES: long = after close above last swing high (5-bar pivots), enter at 50% retracement of the impulse; exit at 2R; short mirror; stop beyond the pivot that started the impulse; fills at next open; risk 1% of equity per trade.
COSTS: prompt declares none; repo 11 bps round trip applied for the measured runs.

## pack100-77
SOURCE: content/spec_sources/strategy_prompts_100-sonnet-claude.md:514-520
MECHANISM: Previous-day low sweep, BTCUSDT.
RULES: long = price sweeps below the previous UTC day's low and closes back above it; exit = at the previous day's midpoint; short mirror with the previous day's high; stop beyond the sweep extreme; fills at next open; risk 1% of equity per trade.
COSTS: prompt declares none; repo 11 bps round trip applied for the measured runs.

## pack100-82
SOURCE: content/spec_sources/strategy_prompts_100-sonnet-claude.md:549-555
MECHANISM: Weekend effect, BTCUSDT.
RULES: long at Friday 21:00 UTC; exit at Monday 00:00 UTC; stop = ATR(14) * 3; fills at next open; risk 1% of equity per trade; 1h only.
COSTS: prompt declares none; repo 11 bps round trip applied for the measured runs.

## pack100-93
SOURCE: content/spec_sources/strategy_prompts_100-sonnet-claude.md:620-626
MECHANISM: Bollinger + RSI + volume confluence, BTCUSDT.
RULES: long = close < lower Bollinger Band (20, 2) with RSI(14) < 30 and volume > 1.5 x SMA(volume, 20); exit = at the middle band; stop = ATR(14) * 2; long only; fills at next open; risk 1% of equity per trade.
COSTS: prompt declares none; repo 11 bps round trip applied for the measured runs.
