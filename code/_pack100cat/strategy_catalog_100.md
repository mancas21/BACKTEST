# Catalogo de 100 hipotesis de estrategia (Fase 3 del master prompt v1.0)

**Estado:** especificadas, NO implementadas, NO ejecutadas. Este archivo no contiene resultados de backtest ni afirma rentabilidad. Los estados de datos son SUPUESTOS que la Fase 2 debe verificar.

**Contrato de datos supuesto:** OHLCV de perps USDT-M de Binance (incluye campos taker-buy de las klines, por verificar) y funding realizado. Sin L2, trades tick a tick, liquidaciones ni on-chain. SPCX y NVDA quedan UNVERIFIED y excluidos hasta verificar instrumento, fuente y mercado; no se sustituye ningun activo.

**Universo por defecto:** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified). **Timeframes:** 5m, 15m, 1h (each timeframe is a separate hypothesis). **Ventana:** 6 meses completos como minimo, ampliable si hay mas historia fiable.

**Convenciones:** R = distancia inicial al stop; ATR(14) de Wilder; indicadores sobre barras cerradas; `mirror` = reglas espejo, probadas como hipotesis aparte; holding en barras del timeframe evaluado; pivotes con k = 3 solo disponibles 3 barras despues.

## Resumen de estados de datos

| Estado | Cantidad |
|---|---|
| READY | 72 |
| PARTIAL | 12 |
| BLOCKED | 13 |
| DEPENDENT | 3 |

## Bloques comunes (campos heredados)

**G1 - Position sizing (field 14).** Planned stop risk = 1% of current strategy equity per position: quantity = (0.01 x equity) / (|entry - stop| + estimated round-trip cost per unit). Provisional caps (need approval): gross leverage at most 3x; per-symbol notional at most 25% of equity; at most 4 concurrent positions per strategy; daily loss limit 3% of equity (flat and halt until the next UTC day); halve risk at -15% from peak, halt for review at -25%. The 1% applies per position, with portfolio-level caps separate. Realized loss can exceed 1% (gaps, slippage, liquidation); enforce margin, minimum-order and lot-size limits.

**G2 - Fees, slippage and execution (field 17).** Signal on a closed bar t; execute at the open of t+1 as a taker order (long at ask-side reference, short at bid-side; with OHLCV only, open plus or minus an estimated half-spread). Fee and slippage figures are ESTIMATES until verified in Phase 2: 5 bps taker fee + 2 bps slippage per side = 14 bps round trip (base). Scenarios with multipliers declared before any test: Base 14 bps RT; Adverse 22 bps RT (about 1.6x); Stress 35 bps RT (2.5x) with doubled stop slippage; extra sensitivity point at 11 bps RT. Stops are stop-market: fill at the stop plus slippage; a gap through the stop fills at the worse of stop and open. If stop and target are both touched inside one candle, assume the stop hit first (conservative) unless higher-resolution data resolve the order. No limit-order fills are assumed; maker variants need their own fill model. Flag a strategy EXECUTION-SENSITIVE if profit disappears under Adverse costs.

**G3 - Funding treatment (field 18).** Perps: apply realized funding at the actual payment timestamps (00:00, 08:00 and 16:00 UTC unless the symbol differs; verify per symbol) to the position held at those times. A funding signal (percentile, premium) is distinct from payments actually paid or received. Use realized history only, never future funding. Strategies that ignore funding as a signal still pay or receive it in P&L. Spot or equity legs: no funding.

**G4 - Validation protocol (field 24).** Sequential gates 1 to 7 (G7 below). Chronological splits only: train, validation, walk-forward (at least 4 folds, expanding or rolling), then one final holdout (last 20% of effective history) opened once after the specification is frozen. Embargo at least the maximum holding period; purge overlapping labels. Six months is the default window, not enough for a holdout plus walk-forward on slow strategies: use all verified history, otherwise mark INCONCLUSIVE. Automated causality tests: truncation (signals at t unchanged when data end at t), shift, HTF-closed-bar and pivot-delay tests. Experiment registry records every variant, parameter set and rejection. Multiple testing: Deflated Sharpe, Benjamini-Hochberg across the strategy family, PBO (CSCV) where applicable. Dependence-aware bootstrap (stationary or block) for Sharpe, expectancy and drawdown. Benchmarks: buy-and-hold and a random-entry null with identical exit, hold and costs. Parameter-plateau analysis, regime breakdown, cross-asset and cross-timeframe robustness.

**G5 - Minimum data (field 25).** At least 6 complete calendar months plus warm-up of 3x the longest lookback. Approximate bars in 6 months: 5m about 52,000; 15m about 17,500; 1h about 4,400. Provisional trade counts: at least 100 in the full sample and 30 out of sample; fewer gives INCONCLUSIVE, not REJECT. Extra data needs are in each sheet's data line.

**G6 - Diagnostic plots (field 27).** Equity curve; benchmark comparison; drawdown curve; monthly returns; rolling Sharpe (when the sample allows); trade-return distribution; long vs short; performance by instrument and timeframe; by market regime; cost sensitivity; parameter sensitivity; walk-forward results. All from computed data, never synthetic. Exports: trade log, equity and drawdown series, metrics table, configuration, data provenance, validation results, reproducibility metadata.

**G7 - Acceptance and rejection (fields 28 and 29).** Gate 1 data validity; 2 causality; 3 implementation; 4 economic viability; 5 statistical reliability; 6 robustness; 7 operational readiness. PROVISIONAL thresholds (need your approval; check against the repo's validation contract): net expectancy at least 20 bps per trade under Base costs (screening policy, not a detectability claim); still net positive under Adverse costs; at least 4 of 5 walk-forward folds profitable; P95 bootstrap max drawdown under 35%; at least 60% positive months; worst month no worse than -15%; Deflated Sharpe probability at least 0.95. REJECT on any failure of Gates 2 or 3, non-positive net expectancy under Base costs, or dependence on one fold or one regime. INCONCLUSIVE when sample or power is inadequate. EXECUTION-SENSITIVE when profit exists only under Base costs. BLOCKED when required data are unavailable.

## Decisiones que necesitan aprobacion

- Costos base 14 bps round trip y escenarios 22 / 35 bps (estimados, no verificados).
- Umbrales provisionales de G7 y topes de riesgo de G1.
- Si se usan los campos taker-buy de las klines como flujo a nivel de barra (estrategias 43, 44, 48, 49, 50, 53, 58, 93).
- Fuente de OI y de spot/futuros fechados para 67, 73, 74, 75; la 78 usa klines de mark/index (por verificar).

## Indice

| ID | Familia | Estrategia | Datos |
|---|---|---|---|
| 001 | A | Moving-average trend continuation | READY |
| 002 | A | EMA alignment with volatility confirmation | READY |
| 003 | A | Supertrend continuation | READY |
| 004 | A | Donchian channel breakout | READY |
| 005 | A | Time-series momentum | READY |
| 006 | A | ADX-filtered directional continuation | READY |
| 007 | A | Higher-timeframe trend with lower-timeframe entries | READY |
| 008 | A | Trend pullback continuation | READY |
| 009 | A | Volatility-adjusted momentum | READY |
| 010 | A | Breakout continuation after consolidation | READY |
| 011 | B | RSI oversold/overbought reversal | READY |
| 012 | B | Bollinger Band reversion | READY |
| 013 | B | Z-score deviation from a rolling mean | READY |
| 014 | B | Anchored VWAP reversion | READY |
| 015 | B | VWAP deviation with volatility normalization | READY |
| 016 | B | Mean reversion following extreme candle displacement | READY |
| 017 | B | Range-bound oscillation strategy | READY |
| 018 | B | Reversion after short-term volatility expansion | READY |
| 019 | B | OU-process-inspired spread reversion, subject to stationarity testing | READY |
| 020 | B | Reversion after liquidity-driven price dislocation | READY |
| 021 | C | ATR compression followed by expansion | READY |
| 022 | C | Bollinger Band squeeze breakout | READY |
| 023 | C | Realized-volatility regime breakout | READY |
| 024 | C | Opening-range breakout, only where session definitions are meaningful | READY |
| 025 | C | Donchian breakout with volume confirmation | READY |
| 026 | C | Range expansion after low-volatility consolidation | READY |
| 027 | C | Volatility-adjusted stop-and-reverse | READY |
| 028 | C | Failed breakout reversal | READY |
| 029 | C | Breakout with retest confirmation | READY |
| 030 | C | Breakout filtered by higher-timeframe regime | READY |
| 031 | D | Confirmed swing-high/swing-low breakout | READY |
| 032 | D | Trend structure continuation | READY |
| 033 | D | Confirmed change-of-character reversal | READY |
| 034 | D | Support/resistance rejection | READY |
| 035 | D | Range sweep and reversal | READY |
| 036 | D | Breakout retest | READY |
| 037 | D | Compression inside a prior range | READY |
| 038 | D | Momentum exhaustion reversal | READY |
| 039 | D | Multi-timeframe structural alignment | READY |
| 040 | D | Price displacement with subsequent continuation | READY |
| 041 | E | Volume-confirmed momentum | READY |
| 042 | E | Relative-volume breakout | READY |
| 043 | E | Aggressive buy/sell trade-flow imbalance | PARTIAL |
| 044 | E | Cumulative volume delta divergence | PARTIAL |
| 045 | E | Order-flow imbalance (OFI) | BLOCKED |
| 046 | E | Bid/ask depth imbalance | BLOCKED |
| 047 | E | Order-book imbalance persistence | BLOCKED |
| 048 | E | Trade-flow exhaustion | PARTIAL |
| 049 | E | Volume absorption with independently defined confirmation | PARTIAL |
| 050 | E | Trade-flow and price-displacement divergence | PARTIAL |
| 051 | F | Liquidity sweep reversal | READY |
| 052 | F | Breakout after a measurable depth imbalance | BLOCKED |
| 053 | F | Price impact versus signed trade volume | PARTIAL |
| 054 | F | Spread-normalized short-horizon momentum | BLOCKED |
| 055 | F | Depth-adjusted breakout confirmation | BLOCKED |
| 056 | F | Order-book imbalance with persistence filtering | BLOCKED |
| 057 | F | Replenishment or depletion signals | BLOCKED |
| 058 | F | Trade-flow reversal after aggressive execution | PARTIAL |
| 059 | F | Liquidity vacuum continuation | BLOCKED |
| 060 | F | Microprice deviation from midprice, if valid L2 data support it | BLOCKED |
| 061 | G | Cointegration-based pairs trading | READY |
| 062 | G | Rolling hedge-ratio spread reversion | READY |
| 063 | G | Cross-asset relative momentum | READY |
| 064 | G | Cross-asset residual mean reversion | READY |
| 065 | G | Beta-neutral relative-value trading | READY |
| 066 | G | Market-neutral portfolio signals | READY |
| 067 | G | Basis dislocation reversion | PARTIAL |
| 068 | G | Funding-aware relative-value strategy | READY |
| 069 | G | Lead-lag relationships between verified instruments | READY |
| 070 | G | Residual momentum after controlling for common market exposure | READY |
| 071 | H | Funding-rate regime strategy | READY |
| 072 | H | Funding-adjusted trend following | READY |
| 073 | H | Basis convergence, where suitable instruments exist | PARTIAL |
| 074 | H | Open-interest expansion with price confirmation | PARTIAL |
| 075 | H | Open-interest and price divergence | PARTIAL |
| 076 | H | Liquidation-cascade continuation | BLOCKED |
| 077 | H | Liquidation exhaustion reversal | BLOCKED |
| 078 | H | Perpetual-versus-spot basis signals | READY |
| 079 | H | Funding and momentum interaction | READY |
| 080 | H | Volatility-scaled derivatives exposure | READY |
| 081 | I | Hidden Markov Model regime filter | READY |
| 082 | I | Change-point-based strategy switching | READY |
| 083 | I | Hurst-informed regime selection, with appropriate estimator limitations | READY |
| 084 | I | Realized-volatility regime allocation | READY |
| 085 | I | Trend-versus-reversion regime classifier | READY |
| 086 | I | Bayesian signal weighting | READY |
| 087 | I | Walk-forward calibrated probability model | READY |
| 088 | I | Dynamic volatility-targeted exposure | READY |
| 089 | I | Regime-conditioned breakout | READY |
| 090 | I | Regime-conditioned mean reversion | READY |
| 091 | J | Trend plus volume confirmation | READY |
| 092 | J | Mean reversion plus higher-timeframe regime filter | READY |
| 093 | J | VWAP plus trade-flow confluence | PARTIAL |
| 094 | J | Breakout plus order-book imbalance | BLOCKED |
| 095 | J | Funding plus relative momentum | READY |
| 096 | J | Market-structure reversal plus volatility filter | READY |
| 097 | J | Cross-asset confirmation strategy | READY |
| 098 | J | Risk-budgeted multi-strategy portfolio | DEPENDENT |
| 099 | J | Correlation-aware strategy allocation | DEPENDENT |
| 100 | J | Meta-strategy that selects among independently validated strategy families using causal regime information | DEPENDENT |


---

## Familia A: Trend following

### QS-001 - Moving-average trend continuation

- **ID, familia, estado (1, 3, 30):** QS-001 | A | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Slow information diffusion and herding create serial correlation that slow moving averages capture.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** EMA(20) crosses above EMA(100) at bar close while close > EMA(200); enter next bar open.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Opposite EMA(20)/EMA(100) cross, or 2 consecutive closes beyond EMA(100) against the position.
- **Stop (12):** 2*ATR(14) from entry, fixed at entry (ATR taken from the signal bar); trailing 3*ATR variant declared as a separate test.
- **Toma de ganancias (13):** None (trend exit); optional 4R variant.
- **Holding maximo (15):** 300 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Trending, ADX(14) > 20.
- **No operar (20):** ADX(14) < 15; ATR(14) below its 10th percentile of 200 bars; data gap in the last 5 bars.
- **Hipotesis (21):** EMA(20/100) crosses with the EMA(200) filter earn positive net expectancy after Base costs and beat buy-and-hold on risk-adjusted terms inside trending sub-periods.
- **Modos de fallo (22):** Whipsaw in ranges; cost drag on 5m; late entries; regime dependence.
- **Fijo (23):** Cross rule, EMA(200) filter, next-bar execution, ATR stop at entry. **A calibrar (23):** Fast in {10,20,30}, slow in {50,100,150} (small grid, training and validation only).
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-002 - EMA alignment with volatility confirmation

- **ID, familia, estado (1, 3, 30):** QS-002 | A | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** A stacked EMA order shows persistent direction; expanding volatility shows participation rather than drift.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** EMA(10) > EMA(30) > EMA(100) and close > EMA(10), with ATR(14) above its 50-bar median; enter on the first bar the full condition turns true.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** EMA(10) crosses EMA(30) against the position.
- **Stop (12):** 2*ATR(14), fixed at entry.
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 250 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Directional with expanding volatility.
- **No operar (20):** ATR(14) below its 30th percentile of 200 bars; EMA(10)/EMA(100) spread under 0.2*ATR (flat stack).
- **Hipotesis (21):** Requiring ATR expansion removes low-participation whipsaws and raises expectancy against the same alignment without the filter.
- **Modos de fallo (22):** Late entry in exhausted trends; filter lag.
- **Fijo (23):** Alignment rule and ATR-above-median form. **A calibrar (23):** EMA triple (10/30/100 vs 8/21/55); volatility percentile threshold.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-003 - Supertrend continuation

- **ID, familia, estado (1, 3, 30):** QS-003 | A | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** An ATR-banded trailing line formalizes trend persistence with volatility-scaled hysteresis.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Supertrend(10,3) flips bullish on a closed bar.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Opposite Supertrend flip.
- **Stop (12):** Supertrend line at entry, capped at 3*ATR(14) distance.
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 300 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Trending.
- **No operar (20):** More than 3 flips in the last 20 bars (chop).
- **Hipotesis (21):** Supertrend flips gated by the chop filter earn positive net expectancy; unfiltered flips are the baseline.
- **Modos de fallo (22):** Whipsaw; repainting if open bars are used (closed bars only).
- **Fijo (23):** Closed-bar flips only. **A calibrar (23):** ATR period {7,10,14}, multiplier {2,3,4}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-004 - Donchian channel breakout

- **ID, familia, estado (1, 3, 30):** QS-004 | A | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Breaks of N-bar extremes mark liquidity-seeking moves and trend initiation.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Close above the highest high of the prior 55 bars (current bar excluded).
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Close below the lowest low of the prior 20 bars (long); symmetric for shorts.
- **Stop (12):** 2*ATR(14) fixed at entry, or the 20-bar opposite extreme if closer.
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 400 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Breakout/trend.
- **No operar (20):** ATR(14) below its 20th percentile of 200 bars (false-breakout zone).
- **Hipotesis (21):** A 55/20 Donchian system has positive net expectancy; asymmetric payoff offsets a win rate under 45%.
- **Modos de fallo (22):** False breakouts; cost drag; regime dependence.
- **Fijo (23):** Prior-bar channel (no current bar), next-bar execution. **A calibrar (23):** Entry lookback {20,55,100}, exit lookback {10,20,50}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-005 - Time-series momentum

- **ID, familia, estado (1, 3, 30):** QS-005 | A | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** The sign of an asset's own past return predicts near-term continuation (documented across assets; time-varying in crypto).
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** z = R(L) / (sigma * sqrt(L)) with L = 96 bars is above +1 and the 20-bar return is positive.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** z crosses back through 0, or max hold reached.
- **Stop (12):** 2*ATR(14), fixed.
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 192 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Trending.
- **No operar (20):** |z| < 1; volatility above its 95th percentile of 500 bars.
- **Hipotesis (21):** The sign of the volatility-normalized lookback return predicts the next L/4 bars net of costs.
- **Modos de fallo (22):** Short-horizon reversals; sign of autocorrelation flips.
- **Fijo (23):** Volatility normalization, trade only on signal change. **A calibrar (23):** L in {48,96,288}, threshold in {0.5,1,1.5}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-006 - ADX-filtered directional continuation

- **ID, familia, estado (1, 3, 30):** QS-006 | A | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** ADX separates trending from ranging states, so directional signals act only when trend strength is present.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** +DI > -DI, ADX(14) > 25 and rising over 3 bars, close > EMA(50).
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** ADX(14) < 20 or DI cross against the position.
- **Stop (12):** 2*ATR(14), fixed.
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 250 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Trending.
- **No operar (20):** ADX(14) < 20.
- **Hipotesis (21):** Gating DI signals by ADX > 25 improves expectancy over the ungated DI cross.
- **Modos de fallo (22):** ADX lag (late entries); whipsaw near the threshold.
- **Fijo (23):** Wilder DI/ADX definitions. **A calibrar (23):** ADX threshold {20,25,30}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-007 - Higher-timeframe trend with lower-timeframe entries

- **ID, familia, estado (1, 3, 30):** QS-007 | A | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** The higher timeframe sets the dominant drift; lower-timeframe timing shortens stops and entry cost.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** Entries 5m and 15m (HTF 1h); entries 1h (HTF 4h)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** HTF EMA(50) > EMA(200) on closed HTF bars only, and LTF EMA(20) crosses above EMA(50).
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** LTF cross back, or HTF trend flips.
- **Stop (12):** 2*ATR(14) on the LTF.
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 300 LTF bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** HTF trend with LTF pullback/resumption.
- **No operar (20):** HTF EMA(50)/EMA(200) spread under 0.3*HTF ATR.
- **Hipotesis (21):** LTF entries aligned with the HTF trend earn higher net expectancy than LTF-only crosses with identical exits.
- **Modos de fallo (22):** HTF lag; leakage if an unclosed HTF bar is used (covered by an automated test).
- **Fijo (23):** HTF values available only after the HTF bar closes. **A calibrar (23):** EMA lengths on each timeframe.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-008 - Trend pullback continuation

- **ID, familia, estado (1, 3, 30):** QS-008 | A | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Pullbacks to dynamic support inside a trend offer better reward-to-risk than breakout entries.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** EMA(50) > EMA(200); price retraces to within 0.5*ATR of EMA(20), then a bar closes above the prior bar's high.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Close below EMA(50), or target hit.
- **Stop (12):** Below the pullback swing low, between 1*ATR and 3*ATR.
- **Toma de ganancias (13):** 2.5R (declared variant) or trailing exit.
- **Holding maximo (15):** 150 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Established trend.
- **No operar (20):** ADX(14) < 18; pullback closes beyond EMA(50) by more than 2*ATR (trend break).
- **Hipotesis (21):** Entering on a confirmed resumption bar beats entering on breakouts within the same trend.
- **Modos de fallo (22):** Pullback turns into a reversal; frequent small stops.
- **Fijo (23):** Resumption trigger. **A calibrar (23):** EMA lengths, pullback tolerance in {0.25,0.5,0.75}*ATR.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-009 - Volatility-adjusted momentum

- **ID, familia, estado (1, 3, 30):** QS-009 | A | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Scaling momentum by realized volatility equalizes risk across regimes and improves risk-adjusted returns versus raw momentum.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Score = ROC(48)/sigma(48) is in the top tercile of its trailing 500-bar distribution (past data only) and above 0.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Score falls below its trailing median.
- **Stop (12):** 2*ATR(14), fixed.
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 144 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Moderate-volatility trend.
- **No operar (20):** Volatility above its 97th percentile of 500 bars.
- **Hipotesis (21):** Volatility-normalized momentum with causal percentile thresholds beats raw ROC momentum on a risk-adjusted net basis.
- **Modos de fallo (22):** Threshold instability; fat tails.
- **Fijo (23):** Causal rolling percentile. **A calibrar (23):** Lookback {24,48,96}; tercile vs quartile cut.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-010 - Breakout continuation after consolidation

- **ID, familia, estado (1, 3, 30):** QS-010 | A | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Consolidation compresses inventory; a decisive break often continues.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Box = last 30 bars with high-low range under 3*ATR(14); close breaks above the box high by at least 0.1*ATR on volume above 1.2*SMA(volume,20).
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Close back inside the box, or trailing 3*ATR from the best close.
- **Stop (12):** Box low, capped at 3*ATR(14).
- **Toma de ganancias (13):** 3R (declared variant).
- **Holding maximo (15):** 200 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Post-compression expansion.
- **No operar (20):** Box younger than 15 bars.
- **Hipotesis (21):** Volume-confirmed breaks from qualified boxes continue enough to earn positive net expectancy.
- **Modos de fallo (22):** False breakouts (see #28); volume spikes from one-off events.
- **Fijo (23):** Box definition and volume filter. **A calibrar (23):** Box length {20,30,50}, range threshold {2,3,4}*ATR.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7


---

## Familia B: Mean reversion

### QS-011 - RSI oversold/overbought reversal

- **ID, familia, estado (1, 3, 30):** QS-011 | B | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Short-horizon overreaction and liquidity pressure partially mean-revert.
- **Instrumentos (5):** SOL (reference), then all six
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** V1 (event): RSI(14) crosses below 30 at bar close. V2 (persistent): first bar with RSI(14) < 30, no re-entry until RSI > 30. V1 and V2 are separate hypotheses. Enter next bar open.
- **Entrada corta (10):** Two-sided variant only: RSI(14) crosses above 70; tested separately from long-only.
- **Salida (11):** RSI(14) crosses above 70 (long); short exit symmetric (crosses below 30).
- **Stop (12):** 2*ATR(14); ATR read on the signal bar; fixed at entry, not trailing.
- **Toma de ganancias (13):** None (RSI exit).
- **Holding maximo (15):** 96 bars (required max-hold rule)
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Oscillating/ranging.
- **No operar (20):** ADX(14) > 30 (strong trend).
- **Hipotesis (21):** RSI(14) < 30 entries show positive net expectancy after Base costs on 5m, 15m and 1h; V1 and V2 evaluated separately.
- **Modos de fallo (22):** Catching falling knives in trends; exit at 70 rarely reached so the time stop dominates; cost drag on 5m.
- **Fijo (23):** RSI(14), 1% risk, 2*ATR stop, no pyramiding. **A calibrar (23):** Small predeclared set only: entry {25,30,35}, exit {50,60,70}, stop {1.5,2,3}*ATR, chosen on training/validation, never on the holdout.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7
- **Nota:** Reference strategy from section 6 of the master prompt; not presumed profitable.

### QS-012 - Bollinger Band reversion

- **ID, familia, estado (1, 3, 30):** QS-012 | B | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Prices beyond 2 sigma of a rolling mean tend to revert while volatility is stable.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Close crosses back above the lower Bollinger Band(20,2) after closing below it.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Close reaches the middle band (SMA 20).
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** Middle band.
- **Holding maximo (15):** 48 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Range / low trend.
- **No operar (20):** Band width above 1.5x its 50-bar median (expansion); ADX(14) > 30.
- **Hipotesis (21):** Re-entry confirmation beats touch-entry on net expectancy.
- **Modos de fallo (22):** Band walking; volatility expansion.
- **Fijo (23):** Band re-entry confirmation. **A calibrar (23):** Length {20,30}, k {2,2.5}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-013 - Z-score deviation from a rolling mean

- **ID, familia, estado (1, 3, 30):** QS-013 | B | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Deviations from a rolling fair value, scaled by dispersion, tend to revert.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** z = (close - SMA(L)) / stdev(L) crosses below -2 (first bar only).
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** z crosses 0.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 72 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Stationary range.
- **No operar (20):** |z| > 4 (regime break); volatility above its 95th percentile of 500 bars.
- **Hipotesis (21):** Fixed z-thresholds on a causal rolling mean earn positive net expectancy in range regimes.
- **Modos de fallo (22):** Mean shifts (non-stationarity) turn reversion into trend.
- **Fijo (23):** Causal rolling mean and stdev. **A calibrar (23):** L {50,100,200}, entry z {1.5,2,2.5}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-014 - Anchored VWAP reversion

- **ID, familia, estado (1, 3, 30):** QS-014 | B | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Anchored VWAP approximates the volume-weighted cost basis from a meaningful anchor; stretched prices revert to it.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m (1h only for the weekly anchor)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Close below AVWAP minus 2*sigma(deviation), first bar only. AVWAP is candle-based (typical price x volume), not tick VWAP.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Close reaches AVWAP.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** AVWAP.
- **Holding maximo (15):** Until session end 23:55 UTC
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Rotational sessions.
- **No operar (20):** First 60 minutes after the anchor; |close - AVWAP| > 4 sigma.
- **Hipotesis (21):** Reversion to anchored VWAP earns positive net expectancy for pre-declared anchors.
- **Modos de fallo (22):** Trend days; anchor choice is a selection-bias risk, so anchors are fixed before testing.
- **Fijo (23):** Anchors declared in advance: UTC day open and weekly open (separate hypotheses). **A calibrar (23):** Sigma multiple {1.5,2,2.5}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7
- **Nota:** Differs from #15: arbitrary-anchor sigma bands, versus session VWAP normalized by ATR.

### QS-015 - VWAP deviation with volatility normalization

- **ID, familia, estado (1, 3, 30):** QS-015 | B | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Normalizing the deviation by ATR makes thresholds comparable across assets and volatility regimes.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** (close - session VWAP) / ATR(14) < -2.0, session VWAP reset at 00:00 UTC.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Deviation returns to 0 (close at or above VWAP).
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** VWAP.
- **Holding maximo (15):** 48 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Low-trend sessions.
- **No operar (20):** First 60 minutes of the session; ATR above its 95th percentile of 500 bars.
- **Hipotesis (21):** ATR-normalized thresholds give more stable expectancy across volatility terciles than raw percentage thresholds.
- **Modos de fallo (22):** Scale shifts; trend days.
- **Fijo (23):** Session reset and ATR normalization. **A calibrar (23):** Threshold {1.5,2,2.5}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-016 - Mean reversion following extreme candle displacement

- **ID, familia, estado (1, 3, 30):** QS-016 | B | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Extreme single-bar displacement often reflects forced or aggressive flow that partly retraces.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Down-bar with return below -3 sigma (100-bar return stdev) and volume above 2*SMA(volume,20); enter next open.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Retracement of 50% of the displacement bar, or 8 bars.
- **Stop (12):** Below the displacement low minus 0.5*ATR, capped at 3*ATR.
- **Toma de ganancias (13):** 50% retracement.
- **Holding maximo (15):** 8 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Liquid, no regime shift.
- **No operar (20):** Displacement above 6 sigma (possible regime shift).
- **Hipotesis (21):** Fading extreme body displacement earns positive net expectancy; true news moves are the failure case.
- **Modos de fallo (22):** Continuation after genuine information; stop clustering.
- **Fijo (23):** Displacement definition. **A calibrar (23):** Sigma multiple {2.5,3,4}, retracement {38,50,62}%.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7
- **Nota:** Differs from #20 (wick rejection) and #40 (continuation conditional on a shallow retrace).

### QS-017 - Range-bound oscillation strategy

- **ID, familia, estado (1, 3, 30):** QS-017 | B | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Inside bounded ranges price oscillates between supply and demand edges.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Range = 60 bars with high-low under 4*ATR(14) and at least 2 confirmed touches per edge; long when price is within the lower 25% of the range and the bar closes up.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Mid-range, or opposite edge minus 10%.
- **Stop (12):** 0.5*ATR beyond the edge (range failure).
- **Toma de ganancias (13):** Mid-range (primary) / opposite edge (variant).
- **Holding maximo (15):** 40 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Range.
- **No operar (20):** Range younger than 20 bars; ADX(14) > 25; close outside the range.
- **Hipotesis (21):** Qualified ranges (two touches per edge) keep oscillating long enough to earn net expectancy.
- **Modos de fallo (22):** Range break; edge definition is subjective.
- **Fijo (23):** Range qualification rule. **A calibrar (23):** Lookback {40,60,80}, touch tolerance.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-018 - Reversion after short-term volatility expansion

- **ID, familia, estado (1, 3, 30):** QS-018 | B | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Volatility spikes mean-revert in volatility and often in price once inventory is cleared.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** ATR(5)/ATR(50) > 2 and the last 3-bar return < -1.5*ATR(14); enter on the first bar closing above its open.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** ATR(5)/ATR(50) < 1.2, or 12 bars.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 12 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Post-spike normalization.
- **No operar (20):** ATR(5)/ATR(50) > 4 (crisis).
- **Hipotesis (21):** Fading price after a volatility spike earns positive net expectancy once the spike starts normalizing.
- **Modos de fallo (22):** Volatility clustering continues.
- **Fijo (23):** Spike ratio and confirmation bar. **A calibrar (23):** Ratio {1.8,2,2.5}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-019 - OU-process-inspired spread reversion, subject to stationarity testing

- **ID, familia, estado (1, 3, 30):** QS-019 | B | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** A stationary spread follows Ornstein-Uhlenbeck dynamics; deviations scaled by the estimated half-life revert.
- **Instrumentos (5):** Pre-specified pairs among BTC, ETH, SOL; others only after history is verified
- **Timeframes (6):** 15m, 1h
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Spread s = ln(A) - beta*ln(B) with beta from rolling OLS on the past 500 bars. Trade only if the training-window stationarity test passes (ADF p < 0.05, half-life 5 to 100 bars). Long spread (long A, short beta*B) when the OU z-score is below -2.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** z crosses 0, or 3x half-life.
- **Stop (12):** |z| > 3.5 or 2*ATR of the spread.
- **Toma de ganancias (13):** z = 0.
- **Holding maximo (15):** 3x half-life
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Stationary spread.
- **No operar (20):** Rolling stationarity retest fails; half-life above 100 bars.
- **Hipotesis (21):** Spreads that pass in-sample stationarity tests stay mean-reverting out of sample (tests pass-then-persist).
- **Modos de fallo (22):** Cointegration breakdown; multiplicity across candidate pairs.
- **Fijo (23):** Beta and OU parameters from past data only. **A calibrar (23):** Estimation window, z entry, p-value cutoff.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7. **Override de sizing:** Dollar-neutral legs; 1% risk measured at the spread stop.
- **Nota:** Differs from #61 (cointegration screen over the pair universe) and #62 (adaptive hedge ratio).

### QS-020 - Reversion after liquidity-driven price dislocation

- **ID, familia, estado (1, 3, 30):** QS-020 | B | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Dislocations from thin liquidity (long wicks on high volume) revert as liquidity returns.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Lower wick at least 60% of the bar range, range above 2.5*ATR(14), volume above 2*SMA(volume,20); enter next open.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** 50% retracement of the wick, or 10 bars.
- **Stop (12):** Beyond the wick extreme plus 0.25*ATR, capped at 3*ATR.
- **Toma de ganancias (13):** 50% of the wick.
- **Holding maximo (15):** 10 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Liquid markets.
- **No operar (20):** Wick and range both above 6 sigma.
- **Hipotesis (21):** Wick-dominated, high-volume dislocations revert enough to earn positive net expectancy.
- **Modos de fallo (22):** Genuine breakdown; stop-hunt continuation.
- **Fijo (23):** Wick/range/volume trigger. **A calibrar (23):** Wick fraction {0.5,0.6,0.7}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7
- **Nota:** Differs from #16 (body displacement) and #51 (sweep of prior swing points).


---

## Familia C: Volatility and breakout

### QS-021 - ATR compression followed by expansion

- **ID, familia, estado (1, 3, 30):** QS-021 | C | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Volatility clusters and compresses before expanding; the break chooses direction.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** ATR(14)/ATR(100) < 0.7 for at least 10 bars, then a bar with range above 1.5*ATR(14) closing in the top 30% of its range.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Trailing 2.5*ATR from the best close, or close back inside the compression range.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 150 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Post-compression.
- **No operar (20):** Compression shorter than 10 bars.
- **Hipotesis (21):** Expansion bars after sustained compression continue enough to earn net expectancy.
- **Modos de fallo (22):** Expansion followed by immediate reversal.
- **Fijo (23):** Ratio-based compression. **A calibrar (23):** Ratio {0.6,0.7,0.8}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-022 - Bollinger Band squeeze breakout

- **ID, familia, estado (1, 3, 30):** QS-022 | C | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Bandwidth percentile lows precede volatility expansion.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Bandwidth(20,2) in its lowest 10% of 200 bars within the last 5 bars, then close above the upper band.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Close below SMA(20).
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 120 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Post-squeeze.
- **No operar (20):** Bandwidth percentile above 30 at the signal bar.
- **Hipotesis (21):** Band-break entries after a qualified squeeze earn positive net expectancy.
- **Modos de fallo (22):** Squeeze resolves in the wrong direction; false break.
- **Fijo (23):** Percentile squeeze. **A calibrar (23):** Percentile {5,10,20}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7
- **Nota:** Differs from #21: bandwidth percentile with a band break, versus an ATR ratio with a range bar.

### QS-023 - Realized-volatility regime breakout

- **ID, familia, estado (1, 3, 30):** QS-023 | C | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Breakouts work mainly when realized volatility is rising.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Realized vol (48 bars) percentile crosses above 60 from below 40 within 10 bars, and close exceeds the 30-bar high.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Close below EMA(20), or RV percentile below 40.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 150 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Rising volatility.
- **No operar (20):** RV percentile above 97.
- **Hipotesis (21):** A rising-RV filter increases breakout expectancy versus the same breakout unfiltered.
- **Modos de fallo (22):** Late entry; whipsaw after the volatility peak.
- **Fijo (23):** Causal RV percentile. **A calibrar (23):** Thresholds {50,60,70}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-024 - Opening-range breakout, only where session definitions are meaningful

- **ID, familia, estado (1, 3, 30):** QS-024 | C | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** The initial range sets the auction extremes of the session; a break signals the day's direction.
- **Instrumentos (5):** BTC, ETH, SOL with declared anchors. NVDA excluded until verified (its session would be meaningful).
- **Timeframes (6):** 5m, 15m
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Opening range = first 30 minutes after a pre-declared anchor (UTC 00:00, 08:00 or 13:30); close above the OR high.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Anchor + 8h, or close back inside the OR midpoint.
- **Stop (12):** Opposite OR side, capped at 3*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 8 hours
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Session-driven.
- **No operar (20):** OR width under 0.5*ATR or above 3*ATR.
- **Hipotesis (21):** Pre-declared anchors show a repeatable OR-break edge; each anchor is a separate hypothesis.
- **Modos de fallo (22):** Crypto trades 24/7 so anchors are arbitrary; anchor mining inflates results.
- **Fijo (23):** Anchors fixed in advance. **A calibrar (23):** OR length {30,60} min.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-025 - Donchian breakout with volume confirmation

- **ID, familia, estado (1, 3, 30):** QS-025 | C | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Volume confirms participation behind a break of range extremes.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Close above the prior 20-bar high with volume above 2*SMA(volume,20).
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Close below the prior 10-bar low.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 120 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Breakout.
- **No operar (20):** Volume spike without range expansion.
- **Hipotesis (21):** The volume filter raises net expectancy versus the unfiltered 20-bar break.
- **Modos de fallo (22):** Volume spikes from liquidations or news; fewer trades.
- **Fijo (23):** Volume filter. **A calibrar (23):** Volume multiple {1.5,2,3}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7
- **Nota:** Shorter channel than #4; the filter is volume.

### QS-026 - Range expansion after low-volatility consolidation

- **ID, familia, estado (1, 3, 30):** QS-026 | C | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Narrow-range bars precede range expansion.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** After an NR7 bar (narrowest range of 7 bars), the first close within 3 bars above the NR7 high.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Close back inside the NR7 range, or 8 bars.
- **Stop (12):** Opposite NR7 extreme, capped at 2.5*ATR.
- **Toma de ganancias (13):** 2R.
- **Holding maximo (15):** 8 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Post-NR7.
- **No operar (20):** NR7 range under 0.2*ATR (data artifact).
- **Hipotesis (21):** NR7 breaks earn positive net expectancy at the 5m to 1h scale.
- **Modos de fallo (22):** Small NR7 ranges mean tiny stops, so costs dominate.
- **Fijo (23):** NR7 definition. **A calibrar (23):** NR window {4,7,10}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7
- **Nota:** Differs from #21: single-bar contraction, not a multi-bar ATR ratio.

### QS-027 - Volatility-adjusted stop-and-reverse

- **ID, familia, estado (1, 3, 30):** QS-027 | C | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** An always-in system that reverses on ATR-scaled adverse moves captures trends with defined risk.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Chandelier flip: close above lowest low(22) + 3*ATR(14) while short reverses to long.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Reversal itself (stop-and-reverse).
- **Stop (12):** The trailing chandelier line.
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** Always in (flat only on invalid data)
- **Frecuencia (16):** At most 1 reversal per 5 bars
- **Regimen esperado (19):** Trending.
- **No operar (20):** Data invalid or stale.
- **Hipotesis (21):** ATR-scaled reversals produce positive net convexity versus fixed-percentage reversals.
- **Modos de fallo (22):** Whipsaw in ranges; high turnover cost.
- **Fijo (23):** Chandelier reversal rule. **A calibrar (23):** ATR multiple {2.5,3,4}, lookback {14,22}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-028 - Failed breakout reversal

- **ID, familia, estado (1, 3, 30):** QS-028 | C | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Failed breakouts trap breakout traders; their stops fuel the reversal.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Close below the 20-bar low, then within 3 bars a close back above that low; enter next open.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Range midpoint, or 12 bars.
- **Stop (12):** Beyond the failed-breakout extreme, capped at 3*ATR.
- **Toma de ganancias (13):** Range midpoint.
- **Holding maximo (15):** 12 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Range / exhaustion.
- **No operar (20):** ADX(14) > 35; breakdown volume above 3x average (genuine break).
- **Hipotesis (21):** Close-based failed breaks revert to the range midpoint often enough to earn net expectancy.
- **Modos de fallo (22):** Genuine breakouts that recycle.
- **Fijo (23):** Close-based breach and re-entry. **A calibrar (23):** Lookback {20,30}, re-entry window {2,3,5}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7
- **Nota:** Differs from #35 (wick sweeps of qualified ranges) and #51 (swing-point liquidity pools).

### QS-029 - Breakout with retest confirmation

- **ID, familia, estado (1, 3, 30):** QS-029 | C | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** A retest of the broken level confirms the flip and reduces false-breakout exposure.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Close above the 20-bar high L; within 10 bars price returns to within 0.25*ATR of L and a bar closes above L and above its open.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Close below L minus 0.5*ATR (failed), or trailing 3*ATR.
- **Stop (12):** L minus 0.75*ATR, capped at 3*ATR.
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 120 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Trending after breakout.
- **No operar (20):** No retest within 10 bars: skip the trade.
- **Hipotesis (21):** Retest-confirmed entries earn higher expectancy per trade than immediate breakout entries (with fewer trades: sample adequacy is tested).
- **Modos de fallo (22):** Retests that never come (missed trends).
- **Fijo (23):** Retest rule. **A calibrar (23):** Retest window {5,10,20}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7
- **Nota:** Differs from #36: channel-defined level, no higher-low requirement.

### QS-030 - Breakout filtered by higher-timeframe regime

- **ID, familia, estado (1, 3, 30):** QS-030 | C | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** A higher-timeframe regime filter removes breakouts against the dominant structure.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** Entries 5m and 15m (HTF 1h); entries 1h (HTF 4h)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** LTF close above the 20-bar high while HTF regime is up (HTF close > EMA(100) and ADX(14) > 20).
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** LTF close below the 10-bar low.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 150 LTF bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** HTF trend.
- **No operar (20):** HTF ADX(14) < 20.
- **Hipotesis (21):** The HTF filter improves risk-adjusted expectancy over unfiltered LTF breakouts.
- **Modos de fallo (22):** HTF lag; leakage if the HTF bar is unclosed (automated test).
- **Fijo (23):** Closed-HTF-bar regime. **A calibrar (23):** HTF EMA length, ADX threshold.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7


---

## Familia D: Market structure and price action

### QS-031 - Confirmed swing-high/swing-low breakout

- **ID, familia, estado (1, 3, 30):** QS-031 | D | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** A close beyond the last confirmed swing point shows a shift in the order of supply and demand.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Close above the last confirmed swing high. Pivots use k = 3 bars to the right, so a pivot is known only at pivot + 3 bars after that bar closes.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Close below the last confirmed swing low.
- **Stop (12):** Last confirmed swing low, between 1*ATR and 3*ATR.
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 150 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Trending/expanding.
- **No operar (20):** Pivot distance under 0.5*ATR (noise pivots).
- **Hipotesis (21):** Breaks of confirmed swing highs earn positive net expectancy; unconfirmed pivots are never used.
- **Modos de fallo (22):** Pivot confirmation delay costs entry price; false breaks.
- **Fijo (23):** Pivot confirmation delay k = 3. **A calibrar (23):** k {2,3,5}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-032 - Trend structure continuation

- **ID, familia, estado (1, 3, 30):** QS-032 | D | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** A sequence of higher highs and higher lows reflects persistent demand; pullbacks into it are opportunities.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Last 2 confirmed swing highs and lows are ascending; price retraces 38% to 62% of the last impulse leg, then closes above the prior bar's high. Pivots use k = 3 bars to the right, so a pivot is known only at pivot + 3 bars after that bar closes.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** A confirmed lower low (close below the last swing low).
- **Stop (12):** Below the last confirmed swing low.
- **Toma de ganancias (13):** Retest of the prior swing high, then trailing.
- **Holding maximo (15):** 150 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Trending.
- **No operar (20):** Fewer than 2 confirmed pivots on each side; retracement above 78%.
- **Hipotesis (21):** Retracement entries inside confirmed structure earn higher expectancy than breakout entries.
- **Modos de fallo (22):** Structure breaks mid-trade; subjective leg definition.
- **Fijo (23):** Leg and retracement rule. **A calibrar (23):** Retracement band {38-62, 50-62}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-033 - Confirmed change-of-character reversal

- **ID, familia, estado (1, 3, 30):** QS-033 | D | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** The first break of the opposing structure point after a sequence of lower highs signals a possible transition.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** In a downtrend (lower highs and lower lows), a close above the last confirmed lower high, then a retest within 8 bars that closes above that level. Pivots use k = 3 bars to the right, so a pivot is known only at pivot + 3 bars after that bar closes.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Close below the CHoCH level minus 0.5*ATR, or target.
- **Stop (12):** Below the last confirmed swing low before the break.
- **Toma de ganancias (13):** 2R or the prior swing high.
- **Holding maximo (15):** 100 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Trend transition.
- **No operar (20):** Break on volume below 0.7*SMA(volume,20); ADX(14) > 35 on the prior trend.
- **Hipotesis (21):** Retested CHoCH entries have positive net expectancy; immediate-entry CHoCH is the baseline.
- **Modos de fallo (22):** Failed reversals; wide stops.
- **Fijo (23):** Retest requirement. **A calibrar (23):** Retest window {5,8,12}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-034 - Support/resistance rejection

- **ID, familia, estado (1, 3, 30):** QS-034 | D | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Clusters of confirmed pivots mark prices where orders concentrate; rejections show defense of the zone.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Zone = at least 2 confirmed pivots within 0.5*ATR. Long when a bar wicks into the support zone and closes above the zone midpoint with lower wick at least 1.5x the body. Pivots use k = 3 bars to the right, so a pivot is known only at pivot + 3 bars after that bar closes.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Opposite zone, or 2R.
- **Stop (12):** Zone edge minus 0.25*ATR.
- **Toma de ganancias (13):** 2R / opposite zone.
- **Holding maximo (15):** 60 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Range / retracement.
- **No operar (20):** Zone touched more than 4 times in 50 bars (exhausted).
- **Hipotesis (21):** Pivot-cluster rejections earn positive net expectancy.
- **Modos de fallo (22):** Zone breaks; subjective zone width.
- **Fijo (23):** Zone clustering rule. **A calibrar (23):** Zone width {0.3,0.5,0.8}*ATR.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-035 - Range sweep and reversal

- **ID, familia, estado (1, 3, 30):** QS-035 | D | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** A sweep beyond range edges collects stops; a close back inside signals that the move lacked acceptance.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Qualified range (at least 2 confirmed touches per edge, age at least 20 bars); wick beyond the low by at least 0.1*ATR but close back inside; enter next open.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Range midpoint.
- **Stop (12):** Beyond the sweep extreme.
- **Toma de ganancias (13):** Range midpoint (primary) / opposite edge (variant).
- **Holding maximo (15):** 30 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Range.
- **No operar (20):** Range height under 1.5*ATR; close outside range for 2 bars.
- **Hipotesis (21):** Sweeps of qualified ranges revert to the midpoint often enough to earn net expectancy.
- **Modos de fallo (22):** Real breakouts mimic sweeps.
- **Fijo (23):** Range qualification. **A calibrar (23):** Sweep depth {0.1,0.2,0.3}*ATR.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7
- **Nota:** Differs from #51: trades only inside qualified ranges; #51 trades swing-point liquidity pools anywhere.

### QS-036 - Breakout retest

- **ID, familia, estado (1, 3, 30):** QS-036 | D | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** After a confirmed structure break, retests of the broken pivot show whether the level has flipped.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Close above confirmed swing high H; within 10 bars price retests to within 0.25*ATR of H, then a close above H forms a higher low versus the retest low. Pivots use k = 3 bars to the right, so a pivot is known only at pivot + 3 bars after that bar closes.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Close below H minus 0.5*ATR.
- **Stop (12):** Below the retest low.
- **Toma de ganancias (13):** Trailing 3*ATR.
- **Holding maximo (15):** 120 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Post-break trend.
- **No operar (20):** Retest low below H by more than 1*ATR.
- **Hipotesis (21):** Higher-low confirmation at the retest improves expectancy over immediate entry.
- **Modos de fallo (22):** Missed trends without retests.
- **Fijo (23):** Pivot level and higher-low rule. **A calibrar (23):** Retest window {5,10,20}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7
- **Nota:** Differs from #29: pivot-defined level plus a higher-low requirement.

### QS-037 - Compression inside a prior range

- **ID, familia, estado (1, 3, 30):** QS-037 | D | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Tight consolidation in one third of a larger range hints at the next auction target.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Last 8 bars have range under 40% of the prior 60-bar range and sit in its upper third; close above the consolidation high.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Close below the consolidation low, or target.
- **Stop (12):** Consolidation low, capped at 3*ATR.
- **Toma de ganancias (13):** Prior range high.
- **Holding maximo (15):** 60 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Range with directional bias.
- **No operar (20):** Prior range under 2*ATR.
- **Hipotesis (21):** Compression near the range extreme resolves toward it more often than chance, enough for positive net expectancy.
- **Modos de fallo (22):** Resolves against the bias.
- **Fijo (23):** Thirds rule. **A calibrar (23):** Compression ratio {0.3,0.4,0.5}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-038 - Momentum exhaustion reversal

- **ID, familia, estado (1, 3, 30):** QS-038 | D | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Runs where price progress per bar shrinks while volume fades show waning aggression.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Short fade: 5 or more consecutive up closes with total move above 4*ATR, last bar range under 0.6x the prior bar, and volume falling; enter after a bar closing down. Long fade is the mirror.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** 50% retracement of the run, or 20 bars.
- **Stop (12):** Beyond the run extreme, capped at 3*ATR.
- **Toma de ganancias (13):** 50% of the run.
- **Holding maximo (15):** 20 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Late-stage runs.
- **No operar (20):** Run driven by a single bar above 3*ATR.
- **Hipotesis (21):** Fading decelerating runs earns positive net expectancy.
- **Modos de fallo (22):** Strong trends keep going; picking tops.
- **Fijo (23):** Run and deceleration rule. **A calibrar (23):** Run length {4,5,6}, move threshold {3,4,5}*ATR.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-039 - Multi-timeframe structural alignment

- **ID, familia, estado (1, 3, 30):** QS-039 | D | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Entries on the lower timeframe aligned with higher-timeframe structure share a common order-flow regime.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** Entries 5m and 15m (HTF 1h); entries 1h (HTF 4h)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** HTF structure up (higher highs and higher lows on confirmed HTF pivots, closed HTF bars only) and a LTF break of structure (close above the last LTF confirmed swing high). Pivots use k = 3 bars to the right, so a pivot is known only at pivot + 3 bars after that bar closes.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** LTF lower low, or HTF structure flips.
- **Stop (12):** Last LTF confirmed swing low.
- **Toma de ganancias (13):** Trailing 3*ATR.
- **Holding maximo (15):** 200 LTF bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** HTF trend.
- **No operar (20):** HTF has fewer than 2 confirmed pivots per side.
- **Hipotesis (21):** LTF breaks aligned with HTF structure beat LTF-only breaks on net expectancy.
- **Modos de fallo (22):** HTF lag; pivot delay stacking.
- **Fijo (23):** HTF availability after close. **A calibrar (23):** Pivot k on each timeframe.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-040 - Price displacement with subsequent continuation

- **ID, familia, estado (1, 3, 30):** QS-040 | D | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** A strong displacement bar followed by shallow consolidation signals acceptance of the new price area.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Displacement = bar range above 2*ATR(14) and body above 70% of range, upward. Next 1 to 3 bars hold above its 50% level; long on the close above the consolidation high.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Trailing 2*ATR, or close below the displacement 50% level.
- **Stop (12):** Displacement 50% level, capped at 3*ATR.
- **Toma de ganancias (13):** 2.5R (variant).
- **Holding maximo (15):** 60 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Impulsive expansion.
- **No operar (20):** Retrace beyond 50% of the displacement bar.
- **Hipotesis (21):** Shallow-retrace consolidation after displacement continues enough to earn net expectancy.
- **Modos de fallo (22):** Exhaustion reversals; stop placement inside noise.
- **Fijo (23):** Displacement and retrace rule. **A calibrar (23):** Body fraction {0.6,0.7,0.8}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7
- **Nota:** Differs from #16: continuation conditional on a shallow retrace, versus fading the displacement.


---

## Familia E: Volume and order flow

### QS-041 - Volume-confirmed momentum

- **ID, familia, estado (1, 3, 30):** QS-041 | E | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Momentum accompanied by above-normal volume reflects broader participation.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** ROC(24) in the top quartile of its trailing 500 bars, volume above 1.5*SMA(volume,50), close above EMA(50).
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Close below EMA(20).
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 150 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Trending with participation.
- **No operar (20):** Volume spike without price progress.
- **Hipotesis (21):** Volume confirmation raises momentum expectancy versus unconfirmed ROC signals.
- **Modos de fallo (22):** Volume driven by liquidations or news.
- **Fijo (23):** Volume filter. **A calibrar (23):** Quartile cut, volume multiple.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-042 - Relative-volume breakout

- **ID, familia, estado (1, 3, 30):** QS-042 | E | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Volume relative to its time-of-day norm isolates unusual participation from intraday seasonality.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** RVOL = volume / median volume of the same time of day over the prior 20 days (causal) above 2, with close above the 20-bar high.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Close below EMA(20).
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 120 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Unusual activity.
- **No operar (20):** Fewer than 20 prior days of history.
- **Hipotesis (21):** Time-of-day-adjusted volume improves breakout expectancy versus raw volume filters.
- **Modos de fallo (22):** Event-driven volume that mean-reverts.
- **Fijo (23):** Causal time-of-day median. **A calibrar (23):** RVOL threshold {1.5,2,3}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-043 - Aggressive buy/sell trade-flow imbalance

- **ID, familia, estado (1, 3, 30):** QS-043 | E | DATA-PARTIAL (needs extra verified data: OI, spot/futures history, or bar-level taker fields) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Persistent aggressor imbalance shows one side paying the spread to trade.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** bar-level taker-buy/taker-sell volume (kline taker-buy fields)
- **Dependencias y limites (8):** aggregated per bar only, no tick sequencing; verify the fields exist in the stored dataset
- **Entrada larga (9):** Imbalance = (taker buy volume - taker sell volume) / volume above +0.2 for 3 bars and close above the prior high (bar-level).
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Imbalance below 0, or 12 bars.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 12 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Directional flow.
- **No operar (20):** Volume below 0.5*SMA(volume,50).
- **Hipotesis (21):** Bar-level taker imbalance predicts the next bars' return net of costs; this is not tick-level order flow.
- **Modos de fallo (22):** Imbalance lags price; aggregation hides sequencing.
- **Fijo (23):** Bar-level definition, labeled as such. **A calibrar (23):** Threshold {0.1,0.2,0.3}, persistence {2,3,4}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7
- **Nota:** The tick-level version (T data) is a separate blocked variant.

### QS-044 - Cumulative volume delta divergence

- **ID, familia, estado (1, 3, 30):** QS-044 | E | DATA-PARTIAL (needs extra verified data: OI, spot/futures history, or bar-level taker fields) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Price making new extremes without matching net aggressor volume signals weak participation.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** bar-level taker-buy/taker-sell volume (kline taker-buy fields)
- **Dependencias y limites (8):** aggregated per bar only, no tick sequencing; verify the fields exist in the stored dataset
- **Entrada larga (9):** Bullish divergence: lower price low on confirmed pivots while CVD (bar-level taker delta) makes a higher low; enter after the second pivot confirms. Pivots use k = 3 bars to the right, so a pivot is known only at pivot + 3 bars after that bar closes.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** 2R, or CVD breaks its last pivot.
- **Stop (12):** Below the second pivot low.
- **Toma de ganancias (13):** 2R.
- **Holding maximo (15):** 80 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Late-stage moves.
- **No operar (20):** Pivots under 0.5*ATR apart.
- **Hipotesis (21):** Bar-level CVD divergences at confirmed pivots predict reversals at net-positive expectancy.
- **Modos de fallo (22):** Divergences persist in trends; pivot delay.
- **Fijo (23):** Bar-level CVD, confirmed pivots only. **A calibrar (23):** Pivot k, min separation.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-045 - Order-flow imbalance (OFI)

- **ID, familia, estado (1, 3, 30):** QS-045 | E | DATA-BLOCKED (needs L2, tick trades or liquidations not in the assumed data contract) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Net changes at the best bid and ask predict short-horizon price pressure.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** historical L1/L2 order-book data with exchange timestamps
- **Dependencias y limites (8):** not in the assumed data contract; replay does not prove fills (queue, latency, cancellations)
- **Entrada larga (9):** OFI (best-level size and price changes) over each 5-minute window has a rolling z-score above +2; enter next window.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** z-score below 0, or 3 windows.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 3 windows
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Liquid books.
- **No operar (20):** Spread above its 90th percentile; stale book.
- **Hipotesis (21):** Aggregated OFI predicts the next 5-minute return after costs.
- **Modos de fallo (22):** Alpha decays faster than the evaluation window; queue and latency unmodeled.
- **Fijo (23):** OFI definition (Cont-Kukanov-Stoikov style). **A calibrar (23):** z threshold, window.
- **Retos de ejecucion (26):** Requires verified L1/L2 event data and a latency/fill model; historical replay does not prove fills.
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-046 - Bid/ask depth imbalance

- **ID, familia, estado (1, 3, 30):** QS-046 | E | DATA-BLOCKED (needs L2, tick trades or liquidations not in the assumed data contract) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Resting depth skewed toward one side suggests where liquidity will support or resist price.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** historical L1/L2 order-book data with exchange timestamps
- **Dependencias y limites (8):** not in the assumed data contract; replay does not prove fills (queue, latency, cancellations)
- **Entrada larga (9):** Depth imbalance = (bid depth - ask depth) / (sum) over the top 10 levels above +0.3 at the bar-close snapshot.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Imbalance below 0, or 6 bars.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 6 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Liquid books.
- **No operar (20):** Spoof-prone thin books; spread above its 90th percentile.
- **Hipotesis (21):** Snapshot depth imbalance predicts short-horizon return net of costs.
- **Modos de fallo (22):** Spoofing and layering; cancellations.
- **Fijo (23):** Top-10-level definition. **A calibrar (23):** Levels {5,10,20}, threshold.
- **Retos de ejecucion (26):** Requires verified depth history; cannot be inferred from candles.
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7
- **Nota:** Differs from #47: a single snapshot, no persistence requirement.

### QS-047 - Order-book imbalance persistence

- **ID, familia, estado (1, 3, 30):** QS-047 | E | DATA-BLOCKED (needs L2, tick trades or liquidations not in the assumed data contract) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Imbalance that persists is harder to fake than a single snapshot.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** historical L1/L2 order-book data with exchange timestamps
- **Dependencias y limites (8):** not in the assumed data contract; replay does not prove fills (queue, latency, cancellations)
- **Entrada larga (9):** Depth imbalance above +0.25 in at least 60% of the last 12 snapshots (5-second snapshots), evaluated at bar close.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Persistence falls below 40%, or 6 bars.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 6 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Liquid books.
- **No operar (20):** Snapshot gaps above 10 seconds.
- **Hipotesis (21):** Persistent imbalance predicts return better than snapshot imbalance (#46).
- **Modos de fallo (22):** Cancellation churn; snapshot gaps.
- **Fijo (23):** Persistence rule. **A calibrar (23):** Window, share threshold.
- **Retos de ejecucion (26):** Requires dense snapshot history.
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-048 - Trade-flow exhaustion

- **ID, familia, estado (1, 3, 30):** QS-048 | E | DATA-PARTIAL (needs extra verified data: OI, spot/futures history, or bar-level taker fields) | SPECIFIED, not implemented, not backtested
- **Racional (4):** When persistent aggressive flow stops moving price, the move is running out of fuel.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** bar-level taker-buy/taker-sell volume (kline taker-buy fields)
- **Dependencias y limites (8):** aggregated per bar only, no tick sequencing; verify the fields exist in the stored dataset
- **Entrada larga (9):** Short fade: 4 or more bars of buy imbalance above +0.2 while price progress per unit of imbalance (|return|/ATR divided by imbalance) falls below half its 50-bar median; enter after a down-closing bar. Long fade is the mirror.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** 50% retracement, or 10 bars.
- **Stop (12):** Beyond the run extreme, capped at 3*ATR.
- **Toma de ganancias (13):** 50% of the run.
- **Holding maximo (15):** 10 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Late-stage runs.
- **No operar (20):** Volume below its 20th percentile.
- **Hipotesis (21):** Declining price progress per unit of taker flow predicts reversals at net-positive expectancy.
- **Modos de fallo (22):** Absorption can precede continuation; bar-level aggregation.
- **Fijo (23):** Efficiency ratio. **A calibrar (23):** Run length, ratio threshold.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-049 - Volume absorption with independently defined confirmation

- **ID, familia, estado (1, 3, 30):** QS-049 | E | DATA-PARTIAL (needs extra verified data: OI, spot/futures history, or bar-level taker fields) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Heavy aggressive selling that fails to push price lower implies passive buyers absorbing flow.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** bar-level taker-buy/taker-sell volume (kline taker-buy fields)
- **Dependencias y limites (8):** aggregated per bar only, no tick sequencing; verify the fields exist in the stored dataset
- **Entrada larga (9):** Bar with taker sell share above 65%, volume above 2*SMA(volume,20), range under 0.8*ATR and close in the upper half; confirmation is price-only: the next bar closes above the absorption bar's high.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** 2R, or close below the absorption low.
- **Stop (12):** Below the absorption low.
- **Toma de ganancias (13):** 2R.
- **Holding maximo (15):** 30 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Support/resistance zones.
- **No operar (20):** Absorption bar on news-driven volume above 5x average.
- **Hipotesis (21):** Price-only confirmation of an absorption bar predicts reversals better than absorption alone.
- **Modos de fallo (22):** Absorption may be distribution; bar-level aggregation.
- **Fijo (23):** Independent price-only confirmation. **A calibrar (23):** Taker share {60,65,70}%.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-050 - Trade-flow and price-displacement divergence

- **ID, familia, estado (1, 3, 30):** QS-050 | E | DATA-PARTIAL (needs extra verified data: OI, spot/futures history, or bar-level taker fields) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Price rising on net selling (or the reverse) suggests a move not backed by aggressor flow.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** bar-level taker-buy/taker-sell volume (kline taker-buy fields)
- **Dependencias y limites (8):** aggregated per bar only, no tick sequencing; verify the fields exist in the stored dataset
- **Entrada larga (9):** Long: price down by more than 1.5*ATR over 6 bars while cumulative taker delta over the same bars is positive; enter on the next up-closing bar. Short is the mirror.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Delta turns negative, or 12 bars.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 12 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Divergent flow.
- **No operar (20):** Cumulative delta near zero (|delta| < 5% of volume).
- **Hipotesis (21):** Divergence between price and cumulative taker delta predicts reversals at positive net expectancy.
- **Modos de fallo (22):** Taker flow is not the only flow; bar-level limits.
- **Fijo (23):** Window of 6 bars, delta sign rule. **A calibrar (23):** Window {4,6,10}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7
- **Nota:** Differs from #44: rolling-window divergence, with no pivot requirement.


---

## Familia F: Liquidity and execution-aware

### QS-051 - Liquidity sweep reversal

- **ID, familia, estado (1, 3, 30):** QS-051 | F | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Stops cluster beyond obvious swing points; sweeping them provides liquidity for reversing flow.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Price wicks beyond a prior confirmed swing low (or equal lows within 0.1%) by at least 0.1*ATR and closes back above it; enter next open. Pivots use k = 3 bars to the right, so a pivot is known only at pivot + 3 bars after that bar closes.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** 2R, or close beyond the sweep extreme.
- **Stop (12):** Beyond the sweep wick.
- **Toma de ganancias (13):** 2R.
- **Holding maximo (15):** 40 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Rotational / reversal.
- **No operar (20):** Sweep bar volume above 4x average with a follow-through close.
- **Hipotesis (21):** Sweeps of pivot liquidity pools reverse often enough to earn net expectancy.
- **Modos de fallo (22):** True breakdowns look like sweeps.
- **Fijo (23):** Pool definition, closed-bar confirmation. **A calibrar (23):** Pool tolerance, sweep depth.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7
- **Nota:** Differs from #35 (qualified ranges) and #28 (close-based breach).

### QS-052 - Breakout after a measurable depth imbalance

- **ID, familia, estado (1, 3, 30):** QS-052 | F | DATA-BLOCKED (needs L2, tick trades or liquidations not in the assumed data contract) | SPECIFIED, not implemented, not backtested
- **Racional (4):** A break accompanied by thin resting liquidity ahead of price travels further.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** historical L1/L2 order-book data with exchange timestamps
- **Dependencias y limites (8):** not in the assumed data contract; replay does not prove fills (queue, latency, cancellations)
- **Entrada larga (9):** Close above the 20-bar high with depth imbalance above +0.3 for 3 consecutive snapshots.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Close below EMA(20).
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 60 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Breakout with thin overhead depth.
- **No operar (20):** Spread above its 90th percentile.
- **Hipotesis (21):** Depth confirmation raises breakout expectancy versus price-only breaks.
- **Modos de fallo (22):** Spoofed depth.
- **Fijo (23):** Depth snapshots. **A calibrar (23):** Imbalance threshold.
- **Retos de ejecucion (26):** Requires verified L2 history.
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-053 - Price impact versus signed trade volume

- **ID, familia, estado (1, 3, 30):** QS-053 | F | DATA-PARTIAL (needs extra verified data: OI, spot/futures history, or bar-level taker fields) | SPECIFIED, not implemented, not backtested
- **Racional (4):** The price change per unit of signed volume measures liquidity: low impact signals absorption, high impact thin books.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** bar-level taker-buy/taker-sell volume (kline taker-buy fields)
- **Dependencias y limites (8):** aggregated per bar only, no tick sequencing; verify the fields exist in the stored dataset
- **Entrada larga (9):** Rolling impact coefficient (regress bar return on signed taker volume over 100 bars) above its 80th percentile with signed flow positive: expect continuation, enter long.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Impact coefficient below median, or 8 bars.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 8 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Thin liquidity.
- **No operar (20):** Fewer than 100 bars of stable estimate.
- **Hipotesis (21):** High measured impact plus aligned flow predicts continuation net of costs (bar-level proxy).
- **Modos de fallo (22):** Noisy estimates; bar-level limits.
- **Fijo (23):** Bar-level impact estimate. **A calibrar (23):** Window {50,100,200}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7
- **Nota:** The tick-level version (T data) would be a separate blocked variant.

### QS-054 - Spread-normalized short-horizon momentum

- **ID, familia, estado (1, 3, 30):** QS-054 | F | DATA-BLOCKED (needs L2, tick trades or liquidations not in the assumed data contract) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Momentum that exceeds the cost of crossing the spread is tradable; smaller moves are not.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** historical L1/L2 order-book data with exchange timestamps
- **Dependencias y limites (8):** not in the assumed data contract; replay does not prove fills (queue, latency, cancellations)
- **Entrada larga (9):** Return over 6 bars divided by the median quoted spread above a threshold, and positive.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Ratio below the threshold, or 6 bars.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 6 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Tight spreads.
- **No operar (20):** Spread above its 90th percentile.
- **Hipotesis (21):** Spread-normalized momentum filters out moves smaller than trading cost.
- **Modos de fallo (22):** Spread data errors.
- **Fijo (23):** Spread normalization. **A calibrar (23):** Threshold.
- **Retos de ejecucion (26):** Requires historical bid/ask quotes; none in candles.
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-055 - Depth-adjusted breakout confirmation

- **ID, familia, estado (1, 3, 30):** QS-055 | F | DATA-BLOCKED (needs L2, tick trades or liquidations not in the assumed data contract) | SPECIFIED, not implemented, not backtested
- **Racional (4):** A breakout through thin depth faces little resistance; through thick depth it stalls.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** historical L1/L2 order-book data with exchange timestamps
- **Dependencias y limites (8):** not in the assumed data contract; replay does not prove fills (queue, latency, cancellations)
- **Entrada larga (9):** Close above the 20-bar high and ask depth within 10 bps of price below its 20th percentile.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Close below EMA(20).
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 60 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Breakout.
- **No operar (20):** Stale book.
- **Hipotesis (21):** Depth-adjusted confirmation beats price-only breakouts.
- **Modos de fallo (22):** Depth withdrawal is anticipation, not weakness.
- **Fijo (23):** 10 bps depth band. **A calibrar (23):** Band, percentile.
- **Retos de ejecucion (26):** Requires verified depth history.
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-056 - Order-book imbalance with persistence filtering

- **ID, familia, estado (1, 3, 30):** QS-056 | F | DATA-BLOCKED (needs L2, tick trades or liquidations not in the assumed data contract) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Persistence filtering removes transient spoofed imbalances.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** historical L1/L2 order-book data with exchange timestamps
- **Dependencias y limites (8):** not in the assumed data contract; replay does not prove fills (queue, latency, cancellations)
- **Entrada larga (9):** Imbalance above +0.25 for at least 10 consecutive 5-second snapshots, plus close above the prior bar's high.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Imbalance below 0, or 6 bars.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 6 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Liquid books.
- **No operar (20):** Snapshot gaps.
- **Hipotesis (21):** Persistent imbalance plus price confirmation beats imbalance alone (#46, #47).
- **Modos de fallo (22):** Cancellation churn.
- **Fijo (23):** Persistence and price confirmation. **A calibrar (23):** Persistence length.
- **Retos de ejecucion (26):** Requires dense snapshot history.
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7
- **Nota:** Differs from #47 by the added price-confirmation requirement.

### QS-057 - Replenishment or depletion signals

- **ID, familia, estado (1, 3, 30):** QS-057 | F | DATA-BLOCKED (needs L2, tick trades or liquidations not in the assumed data contract) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Repeated refills at a price (icebergs) or rapid depletion reveal hidden size or imminent breaks.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** historical L1/L2 order-book data with exchange timestamps; tick-level trades with aggressor flag
- **Dependencias y limites (8):** not in the assumed data contract; replay does not prove fills (queue, latency, cancellations); not in the assumed data contract; dedupe by trade id and audit the aggressor flag
- **Entrada larga (9):** Support refilled at least 3 times after trades at the best bid with price holding: long. Rapid depletion of the best ask plus an aggressive buy: breakout long.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Level breaks, or 10 bars.
- **Stop (12):** Beyond the defended level.
- **Toma de ganancias (13):** 2R.
- **Holding maximo (15):** 10 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Event-level liquidity.
- **No operar (20):** Missing event sequence numbers.
- **Hipotesis (21):** Refill and depletion events carry short-term information net of costs.
- **Modos de fallo (22):** Spoofing; event-reconstruction error.
- **Fijo (23):** Event definitions. **A calibrar (23):** Refill count, depletion threshold.
- **Retos de ejecucion (26):** Needs event-level L2 with sequence numbers and trades; gaps invalidate the signal.
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-058 - Trade-flow reversal after aggressive execution

- **ID, familia, estado (1, 3, 30):** QS-058 | F | DATA-PARTIAL (needs extra verified data: OI, spot/futures history, or bar-level taker fields) | SPECIFIED, not implemented, not backtested
- **Racional (4):** After a burst of one-sided aggression exhausts, price often retraces.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** bar-level taker-buy/taker-sell volume (kline taker-buy fields)
- **Dependencias y limites (8):** aggregated per bar only, no tick sequencing; verify the fields exist in the stored dataset
- **Entrada larga (9):** Short fade: 3 consecutive bars of imbalance above +0.3 with price up more than 2.5*ATR, then the first bar whose imbalance turns negative and closes below the prior close.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** 50% retracement, or 8 bars.
- **Stop (12):** Beyond the burst extreme, capped at 3*ATR.
- **Toma de ganancias (13):** 50% of the burst.
- **Holding maximo (15):** 8 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Post-burst.
- **No operar (20):** Imbalance flip on low volume.
- **Hipotesis (21):** Flow-sign reversal after aggressive bursts predicts retracement at net-positive expectancy.
- **Modos de fallo (22):** Bursts continue (momentum ignition).
- **Fijo (23):** Burst and flip rules. **A calibrar (23):** Imbalance threshold, move threshold.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7
- **Nota:** Differs from #48: reacts to the flip after a burst, not to declining efficiency.

### QS-059 - Liquidity vacuum continuation

- **ID, familia, estado (1, 3, 30):** QS-059 | F | DATA-BLOCKED (needs L2, tick trades or liquidations not in the assumed data contract) | SPECIFIED, not implemented, not backtested
- **Racional (4):** When resting liquidity disappears in the direction of travel, price moves further per unit of flow.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** historical L1/L2 order-book data with exchange timestamps
- **Dependencias y limites (8):** not in the assumed data contract; replay does not prove fills (queue, latency, cancellations)
- **Entrada larga (9):** Close above the 20-bar high while total ask depth within 20 bps collapses below its 10th percentile versus the prior 60 minutes.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Depth recovers above median, or 8 bars.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 8 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Thinning books.
- **No operar (20):** Stale or gapped book.
- **Hipotesis (21):** Depth collapses ahead of price predict continuation net of costs.
- **Modos de fallo (22):** Depth withdrawal ahead of news; spoofing.
- **Fijo (23):** Depth collapse rule. **A calibrar (23):** Band, percentile.
- **Retos de ejecucion (26):** Requires verified depth history.
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-060 - Microprice deviation from midprice, if valid L2 data support it

- **ID, familia, estado (1, 3, 30):** QS-060 | F | DATA-BLOCKED (needs L2, tick trades or liquidations not in the assumed data contract) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Microprice weights the quote by opposite-side size, signaling the likely next trade price.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** Evaluate on 5m aggregation only after verifying the signal horizon
- **Datos requeridos (7):** historical L1/L2 order-book data with exchange timestamps
- **Dependencias y limites (8):** not in the assumed data contract; replay does not prove fills (queue, latency, cancellations)
- **Entrada larga (9):** Microprice = (ask*bidSize + bid*askSize)/(bidSize + askSize); long when its deviation from mid has a rolling z-score above +2 at bar close.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** z-score below 0, or 2 bars.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 2 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Liquid books.
- **No operar (20):** Spread above its 80th percentile.
- **Hipotesis (21):** Microprice deviation predicts the next-bar return net of costs.
- **Modos de fallo (22):** Edge decays in seconds and may vanish at 5-minute resolution.
- **Fijo (23):** Microprice definition. **A calibrar (23):** z threshold.
- **Retos de ejecucion (26):** Requires verified L1 history; likely needs sub-minute execution that this harness does not model.
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7


---

## Familia G: Statistical and relative value

### QS-061 - Cointegration-based pairs trading

- **ID, familia, estado (1, 3, 30):** QS-061 | G | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** If two prices share a stochastic trend, their spread is stationary and deviations revert.
- **Instrumentos (5):** Candidate pairs among BTC, ETH, SOL (others only after history is verified); relationships estimated on past data only
- **Timeframes (6):** 15m, 1h
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Engle-Granger and Johansen tests on a 500-bar training window over every candidate pair, with Benjamini-Hochberg control across the pair tests; long the spread when z < -2.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** z crosses 0, or 3x half-life.
- **Stop (12):** |z| > 3.5, or failed rolling retest.
- **Toma de ganancias (13):** z = 0.
- **Holding maximo (15):** 3x half-life
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Stable cointegrating relation.
- **No operar (20):** Rolling cointegration retest fails; half-life above 100 bars.
- **Hipotesis (21):** Pairs that pass the screen stay cointegrated out of sample long enough to earn net expectancy.
- **Modos de fallo (22):** Relation breaks; test multiplicity; correlated is not cointegrated.
- **Fijo (23):** Training-only estimation; retest every 100 bars. **A calibrar (23):** Window {300,500,1000}, entry z, retest cadence.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7. **Override de sizing:** Dollar-neutral legs; 1% risk measured at the spread/portfolio stop.
- **Nota:** Differs from #19 (single pre-specified OU spread) and #62 (adaptive hedge ratio without a cointegration gate).

### QS-062 - Rolling hedge-ratio spread reversion

- **ID, familia, estado (1, 3, 30):** QS-062 | G | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** A time-varying hedge ratio tracks a drifting relation that a fixed beta would miss.
- **Instrumentos (5):** Candidate pairs among BTC, ETH, SOL (others only after history is verified); relationships estimated on past data only
- **Timeframes (6):** 15m, 1h
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Hedge ratio from a Kalman filter (or rolling OLS on 200 bars); spread z below -2 goes long A and short beta*B.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** z crosses 0, or 100 bars.
- **Stop (12):** |z| > 3.5.
- **Toma de ganancias (13):** z = 0.
- **Holding maximo (15):** 100 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Slowly drifting relation.
- **No operar (20):** Hedge-ratio change above 30% in 20 bars (unstable).
- **Hipotesis (21):** An adaptive hedge ratio improves spread-reversion expectancy versus a fixed beta, after rebalancing costs.
- **Modos de fallo (22):** Overfit adaptation speed; hedge rebalancing costs.
- **Fijo (23):** Causal filter. **A calibrar (23):** Process-noise ratio, window.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7. **Override de sizing:** Dollar-neutral legs; 1% risk measured at the spread/portfolio stop.

### QS-063 - Cross-asset relative momentum

- **ID, familia, estado (1, 3, 30):** QS-063 | G | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Cross-sectional winners keep outperforming losers over short-to-medium horizons.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 15m, 1h
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Rank the 6 perps by volatility-adjusted 72-bar return (causal); long the top 2, short the bottom 2; rebalance every 12 bars.
- **Entrada corta (10):** Included: the bottom 2 are shorted (dollar-neutral).
- **Salida (11):** Rank drops out of the top/bottom 2 at rebalance.
- **Stop (12):** Portfolio stop: -3% of strategy equity from the last rebalance; per-leg 3*ATR.
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 48 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Dispersion regimes.
- **No operar (20):** Cross-sectional dispersion below its 20th percentile.
- **Hipotesis (21):** Cross-sectional momentum earns positive net returns after turnover costs.
- **Modos de fallo (22):** Few assets (6) so rank noise is high; momentum crashes.
- **Fijo (23):** Causal ranking, dollar-neutral. **A calibrar (23):** Lookback {24,72,168}, rebalance {6,12,24}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7. **Override de sizing:** Portfolio sizing: gross 100% of equity, net zero; 1% risk concept applied via the portfolio stop.

### QS-064 - Cross-asset residual mean reversion

- **ID, familia, estado (1, 3, 30):** QS-064 | G | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** An asset's return unexplained by the market tends to revert.
- **Instrumentos (5):** ETH, SOL, HYPE, SUI, JUP against BTC
- **Timeframes (6):** 15m, 1h
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Residual = asset return - beta*BTC return (rolling 200-bar beta). Cumulative residual z over 24 bars below -2: long the asset, short beta*BTC.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** z crosses 0, or 24 bars.
- **Stop (12):** z below -3.5, or 3*ATR of the residual.
- **Toma de ganancias (13):** z = 0.
- **Holding maximo (15):** 24 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Stable beta.
- **No operar (20):** Beta change above 0.3 within 50 bars.
- **Hipotesis (21):** Residual reversion after beta-neutral hedging earns positive net expectancy.
- **Modos de fallo (22):** Residual is information (idiosyncratic news); beta instability.
- **Fijo (23):** Past-only beta. **A calibrar (23):** Beta window, z threshold.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7. **Override de sizing:** Dollar-neutral legs; 1% risk measured at the spread/portfolio stop.

### QS-065 - Beta-neutral relative-value trading

- **ID, familia, estado (1, 3, 30):** QS-065 | G | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Two peers with different betas can be traded for relative mispricing with market exposure removed.
- **Instrumentos (5):** Peer pairs among SOL, SUI, JUP, HYPE, ETH with BTC beta hedge
- **Timeframes (6):** 15m, 1h
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Long A / short B scaled to zero BTC beta when relative residual z (A vs B after removing BTC) is below -2.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** z crosses 0, or 48 bars.
- **Stop (12):** z below -3.5.
- **Toma de ganancias (13):** z = 0.
- **Holding maximo (15):** 48 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Correlated peers.
- **No operar (20):** Pair correlation below 0.5 on the last 200 bars.
- **Hipotesis (21):** Beta-neutral peer spreads earn positive net expectancy beyond the single-asset hedge in #64.
- **Modos de fallo (22):** Leg-specific news; beta estimation error.
- **Fijo (23):** Zero-beta construction. **A calibrar (23):** Window, threshold.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7. **Override de sizing:** Dollar-neutral legs; 1% risk measured at the spread/portfolio stop.
- **Nota:** Differs from #64: two risky legs hedged against BTC, rather than one asset against BTC.

### QS-066 - Market-neutral portfolio signals

- **ID, familia, estado (1, 3, 30):** QS-066 | G | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** A composite of momentum and short-term reversal across assets can earn a premium with net zero exposure.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 15m, 1h
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Score = 0.5*z(vol-adjusted 72-bar momentum) - 0.5*z(6-bar return); weights proportional to the demeaned score, gross 100%, net 0; rebalance every 12 bars.
- **Entrada corta (10):** Portfolio is long and short by construction.
- **Salida (11):** Rebalance weights.
- **Stop (12):** Portfolio drawdown stop -3% from the last rebalance.
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 12 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Cross-sectional dispersion.
- **No operar (20):** Dispersion below its 20th percentile.
- **Hipotesis (21):** The blended score earns positive net returns after turnover and funding costs.
- **Modos de fallo (22):** Signal components offset; turnover costs.
- **Fijo (23):** Composite definition. **A calibrar (23):** Blend weights {0.3,0.5,0.7}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7. **Override de sizing:** Portfolio vol targeting instead of per-trade stop sizing.

### QS-067 - Basis dislocation reversion

- **ID, familia, estado (1, 3, 30):** QS-067 | G | DATA-PARTIAL (needs extra verified data: OI, spot/futures history, or bar-level taker fields) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Perp-versus-spot or dated-futures basis dislocations converge through arbitrage.
- **Instrumentos (5):** BTC, ETH (spot history verified)
- **Timeframes (6):** 15m, 1h
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines); spot or dated-futures OHLCV for the same underlying
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first; symbol and timestamp alignment; a spot leg needs spot execution and borrow assumptions
- **Entrada larga (9):** Basis z-score (vs trailing 500 bars) above +2: short the perp, long spot (or the reverse below -2).
- **Entrada corta (10):** Included by construction (two legs).
- **Salida (11):** z crosses 0, or 48 bars.
- **Stop (12):** |z| > 4, or 1% basis loss.
- **Toma de ganancias (13):** z = 0.
- **Holding maximo (15):** 48 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Stable basis dynamics.
- **No operar (20):** Funding timestamp within 15 minutes; spot/perp timestamps misaligned.
- **Hipotesis (21):** Large basis z-scores converge enough to cover costs, spot execution and funding.
- **Modos de fallo (22):** Basis can widen further; capital and borrow constraints.
- **Fijo (23):** Basis definition. **A calibrar (23):** z threshold, window.
- **Retos de ejecucion (26):** Spot leg needs spot fees/borrow assumptions; verify data before use.
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7. **Override de sizing:** Dollar-neutral legs; 1% risk measured at the spread/portfolio stop.

### QS-068 - Funding-aware relative-value strategy

- **ID, familia, estado (1, 3, 30):** QS-068 | G | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Differences in funding across perps pay holders of low-funding assets; pairing legs can harvest the spread.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 1h
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines); realized funding-rate history with payment timestamps
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first; use realized values only; verify the funding interval per symbol
- **Entrada larga (9):** Long the perp with the lowest 8-hour funding and short the highest among the 6, dollar-neutral, when the price relative momentum is not adverse (24-bar relative return above -1*ATR).
- **Entrada corta (10):** Included by construction.
- **Salida (11):** Rebalance every 8 hours.
- **Stop (12):** Pair relative-return stop -2*ATR of the ratio.
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 8 hours
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Funding dispersion.
- **No operar (20):** Funding spread under 2 bps per 8h.
- **Hipotesis (21):** The funding differential plus price carry exceeds costs; P&L is decomposed into price and funding.
- **Modos de fallo (22):** Funding mean-reverts; price moves swamp funding.
- **Fijo (23):** Realized funding only. **A calibrar (23):** Spread threshold, momentum filter.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7. **Override de sizing:** Dollar-neutral legs; 1% risk measured at the spread/portfolio stop.

### QS-069 - Lead-lag relationships between verified instruments

- **ID, familia, estado (1, 3, 30):** QS-069 | G | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Liquid leaders (BTC, ETH) can incorporate information faster than smaller followers.
- **Instrumentos (5):** Leaders BTC and ETH; followers SOL, SUI, JUP, HYPE
- **Timeframes (6):** 5m, 15m
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Leader return over the last bar above +2 sigma while the follower's return is under +0.5 sigma: long the follower next open.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Follower catches up (cumulative return gap under 0.25 sigma), or 3 bars.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 3 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Information shocks.
- **No operar (20):** Timestamp misalignment above 1 second; spread above its 90th percentile.
- **Hipotesis (21):** A lagged cross-asset response exists beyond transaction costs at 5m and 15m.
- **Modos de fallo (22):** Lag shorter than the bar size; edge below costs.
- **Fijo (23):** Lag estimated on past data only. **A calibrar (23):** Lag {1,2}, thresholds.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-070 - Residual momentum after controlling for common market exposure

- **ID, familia, estado (1, 3, 30):** QS-070 | G | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Momentum in the idiosyncratic component is more persistent and less crash-prone than total-return momentum.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 1h
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Residual returns vs BTC (rolling 200-bar beta); rank by 168-bar cumulative residual; long the top 2, short the bottom 2, rebalance every 24 bars.
- **Entrada corta (10):** Included (dollar-neutral).
- **Salida (11):** Rank change at rebalance.
- **Stop (12):** Portfolio stop -3% from the last rebalance.
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 96 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Dispersion regimes.
- **No operar (20):** Dispersion below its 20th percentile.
- **Hipotesis (21):** Residual momentum earns positive net returns and beats raw momentum (#63) on risk-adjusted terms.
- **Modos de fallo (22):** Few assets; beta error.
- **Fijo (23):** Causal residuals. **A calibrar (23):** Lookback {72,168,336}, rebalance {12,24,48}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7. **Override de sizing:** Portfolio sizing as in #63.


---

## Familia H: Derivatives and carry

### QS-071 - Funding-rate regime strategy

- **ID, familia, estado (1, 3, 30):** QS-071 | H | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Extreme positive funding signals crowded longs; extreme negative, crowded shorts; extremes tend to normalize.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 15m, 1h
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines); realized funding-rate history with payment timestamps
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first; use realized values only; verify the funding interval per symbol
- **Entrada larga (9):** Funding below its 10th percentile (30-day rolling, realized values only) and close above EMA(20): long.
- **Entrada corta (10):** Funding above its 90th percentile and close below EMA(20): short.
- **Salida (11):** Funding returns to its median, or 24 hours.
- **Stop (12):** 3*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 24 hours
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Crowded positioning.
- **No operar (20):** Funding history under 30 days.
- **Hipotesis (21):** Fading funding extremes confirmed by price earns positive net returns after funding paid/received.
- **Modos de fallo (22):** Crowding persists in trends; funding is slow.
- **Fijo (23):** Realized funding, percentile rule. **A calibrar (23):** Percentile cutoffs {5/95,10/90,20/80}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-072 - Funding-adjusted trend following

- **ID, familia, estado (1, 3, 30):** QS-072 | H | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Trend positions pay or receive funding; high carry cost reduces net edge.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines); realized funding-rate history with payment timestamps
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first; use realized values only; verify the funding interval per symbol
- **Entrada larga (9):** EMA(20)/EMA(100) long signal allowed only if funding is at most 0.03% per 8h; size scaled down by 50% above that.
- **Entrada corta (10):** Mirror: short allowed only if funding is at least -0.03% per 8h.
- **Salida (11):** Trend exit, or funding drag over 0.1% for the trade.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 300 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Trending.
- **No operar (20):** Funding above 0.1% per 8h against the position.
- **Hipotesis (21):** Funding-aware filtering improves net trend returns versus plain EMA trend (#1).
- **Modos de fallo (22):** Filter removes the best trends (crowded but profitable).
- **Fijo (23):** Funding thresholds. **A calibrar (23):** Funding cap {0.02,0.03,0.05}%.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-073 - Basis convergence, where suitable instruments exist

- **ID, familia, estado (1, 3, 30):** QS-073 | H | DATA-PARTIAL (needs extra verified data: OI, spot/futures history, or bar-level taker fields) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Dated futures converge to spot at expiry; calendar spreads reflect carry.
- **Instrumentos (5):** BTC, ETH quarterlies (availability to be verified)
- **Timeframes (6):** 1h
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines); spot or dated-futures OHLCV for the same underlying
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first; symbol and timestamp alignment; a spot leg needs spot execution and borrow assumptions
- **Entrada larga (9):** Calendar spread (quarterly vs perp) above its rolling mean by 2 sigma: short the quarterly, long the perp.
- **Entrada corta (10):** Reverse when below -2 sigma.
- **Salida (11):** Spread z crosses 0, or 3 days before expiry.
- **Stop (12):** |z| > 4.
- **Toma de ganancias (13):** z = 0.
- **Holding maximo (15):** Until near expiry
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Stable term structure.
- **No operar (20):** Under 5 days to expiry.
- **Hipotesis (21):** Calendar spreads converge enough to earn net returns after fees and funding.
- **Modos de fallo (22):** Capital efficiency; limited instruments.
- **Fijo (23):** Spread definition. **A calibrar (23):** z threshold.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7. **Override de sizing:** Dollar-neutral legs; 1% risk measured at the spread/portfolio stop.

### QS-074 - Open-interest expansion with price confirmation

- **ID, familia, estado (1, 3, 30):** QS-074 | H | DATA-PARTIAL (needs extra verified data: OI, spot/futures history, or bar-level taker fields) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Rising open interest during a breakout indicates new positions entering in the move's direction.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines); open-interest history
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first; public-API depth is short (about 30 days as far as known): needs a bulk source and a gap audit
- **Entrada larga (9):** 12-bar open-interest change above +2 sigma (rolling) and close above the 20-bar high.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** OI change below 0, or close below EMA(20).
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 100 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Positioning-led trends.
- **No operar (20):** OI data gap in the last 12 bars.
- **Hipotesis (21):** OI-confirmed breakouts continue more than OI-flat ones.
- **Modos de fallo (22):** OI includes hedged positions; data gaps.
- **Fijo (23):** OI sigma rule. **A calibrar (23):** Window, sigma threshold.
- **Retos de ejecucion (26):** Needs a verified OI source with at least the same history as the price data.
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-075 - Open-interest and price divergence

- **ID, familia, estado (1, 3, 30):** QS-075 | H | DATA-PARTIAL (needs extra verified data: OI, spot/futures history, or bar-level taker fields) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Price extremes with falling OI suggest short covering or exhaustion rather than new conviction.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines); open-interest history
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first; public-API depth is short (about 30 days as far as known): needs a bulk source and a gap audit
- **Entrada larga (9):** Long: new 48-bar low while open interest falls over the same 48 bars.
- **Entrada corta (10):** Short: new 48-bar high while OI falls.
- **Salida (11):** Close crosses EMA(20), or 12 bars.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 12 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Exhaustion.
- **No operar (20):** OI data gap.
- **Hipotesis (21):** Moves on falling OI revert more than moves on rising OI.
- **Modos de fallo (22):** Falling OI can accompany real trends.
- **Fijo (23):** Divergence rule. **A calibrar (23):** Window {24,48,96}.
- **Retos de ejecucion (26):** Needs a verified OI source.
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-076 - Liquidation-cascade continuation

- **ID, familia, estado (1, 3, 30):** QS-076 | H | DATA-BLOCKED (needs L2, tick trades or liquidations not in the assumed data contract) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Forced liquidations push price through levels, triggering further liquidations.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** historical liquidation events
- **Dependencias y limites (8):** no reliable public history; candle-based proxies must never be labeled liquidations
- **Entrada larga (9):** Long-liquidation notional above its 99th percentile in the last bar and price breaking the 20-bar low: short continuation.
- **Entrada corta (10):** Mirror with short liquidations.
- **Salida (11):** Liquidation rate below 50% of peak, or 6 bars.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 6 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Cascades.
- **No operar (20):** Missing liquidation history.
- **Hipotesis (21):** Large liquidation bursts continue price for a few bars net of costs.
- **Modos de fallo (22):** Exhaustion arrives sooner; latency.
- **Fijo (23):** Real liquidation events only. **A calibrar (23):** Percentile, break lookback.
- **Retos de ejecucion (26):** Blocked unless a reliable liquidation history exists; candle-based proxies must not be called liquidations.
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-077 - Liquidation exhaustion reversal

- **ID, familia, estado (1, 3, 30):** QS-077 | H | DATA-BLOCKED (needs L2, tick trades or liquidations not in the assumed data contract) | SPECIFIED, not implemented, not backtested
- **Racional (4):** After a cascade, forced selling dries up and price tends to rebound.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** historical liquidation events
- **Dependencias y limites (8):** no reliable public history; candle-based proxies must never be labeled liquidations
- **Entrada larga (9):** After a long-liquidation burst, liquidation rate falls below 50% of peak for 3 bars and price stabilizes (3 bars without a new low): long.
- **Entrada corta (10):** Mirror.
- **Salida (11):** 50% retracement, or 12 bars.
- **Stop (12):** Below the cascade low.
- **Toma de ganancias (13):** 50% retracement.
- **Holding maximo (15):** 12 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Post-cascade.
- **No operar (20):** Missing liquidation history.
- **Hipotesis (21):** Reversals after liquidation exhaustion earn positive net returns.
- **Modos de fallo (22):** Cascades restart.
- **Fijo (23):** Real liquidation events only. **A calibrar (23):** Decay ratio, calm window.
- **Retos de ejecucion (26):** Blocked unless a reliable liquidation history exists.
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-078 - Perpetual-versus-spot basis signals

- **ID, familia, estado (1, 3, 30):** QS-078 | H | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** The perp premium to spot is a positioning gauge; extremes mark crowded leverage.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines); mark/index price klines
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first; verify availability and timestamp alignment with trade klines
- **Entrada larga (9):** Premium index z-score (vs trailing 500 bars) below -2 with close above EMA(20): long the perp (directional).
- **Entrada corta (10):** Premium z above +2 with close below EMA(20): short.
- **Salida (11):** z crosses 0, or 48 bars.
- **Stop (12):** 3*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 48 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Leverage extremes.
- **No operar (20):** Mark/index alignment errors.
- **Hipotesis (21):** Directional use of premium extremes earns positive net returns.
- **Modos de fallo (22):** Premium extremes persist in trends.
- **Fijo (23):** Premium z-score. **A calibrar (23):** z threshold, window.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7
- **Nota:** Differs from #67: directional positioning signal, not market-neutral convergence.

### QS-079 - Funding and momentum interaction

- **ID, familia, estado (1, 3, 30):** QS-079 | H | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Momentum with uncrowded funding is more durable than momentum with crowded funding.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines); realized funding-rate history with payment timestamps
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first; use realized values only; verify the funding interval per symbol
- **Entrada larga (9):** Momentum long (ROC(48) above 0, close above EMA(50)) taken only if funding is below its 70th percentile; if above the 90th percentile skip.
- **Entrada corta (10):** Mirror with funding above its 30th percentile.
- **Salida (11):** Momentum turns negative, or funding above its 95th percentile.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 200 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Uncrowded trends.
- **No operar (20):** Funding history under 30 days.
- **Hipotesis (21):** Funding-conditioned momentum earns higher net risk-adjusted returns than plain momentum.
- **Modos de fallo (22):** Crowded trends can still pay.
- **Fijo (23):** Percentile rule. **A calibrar (23):** Percentile cutoffs.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7
- **Nota:** Differs from #72: funding is a percentile filter here, not an absolute cap on carry cost.

### QS-080 - Volatility-scaled derivatives exposure

- **ID, familia, estado (1, 3, 30):** QS-080 | H | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Scaling perp exposure by forecast volatility stabilizes risk and reduces leverage in turbulent periods.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines); realized funding-rate history with payment timestamps
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first; use realized values only; verify the funding interval per symbol
- **Entrada larga (9):** Take #1's trend signals; position = min(cap, target vol / EWMA vol), net of funding.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** As #1.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 300 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Any.
- **No operar (20):** EWMA vol above its 99th percentile (flat).
- **Hipotesis (21):** Volatility-scaled exposure improves risk-adjusted returns versus fixed-risk sizing of the same signals.
- **Modos de fallo (22):** Vol forecast lag; leverage cap binding.
- **Fijo (23):** EWMA vol, cap. **A calibrar (23):** Target vol {15,25,35}%, lambda {0.94,0.97}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7
- **Nota:** Overlay on #1; differs from #88, which is a standalone vol-managed long exposure.


---

## Familia I: Market regimes and adaptive models

### QS-081 - Hidden Markov Model regime filter

- **ID, familia, estado (1, 3, 30):** QS-081 | I | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Latent volatility/return states explain when trend or reversion rules work.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 15m, 1h
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** 3-state Gaussian HMM fit on training data only (features: return, log realized vol); filtered (forward-only) state probabilities; run the base rule (EMA trend or RSI reversion) only in the state with positive training-window conditional expectancy.
- **Entrada corta (10):** Per base rule.
- **Salida (11):** Base rule exit or state change.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** Per base rule.
- **Holding maximo (15):** Per base rule
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** State-dependent.
- **No operar (20):** State probability below 0.6; refit window incomplete.
- **Hipotesis (21):** Regime-gated base rules improve net expectancy versus ungated rules, out of sample.
- **Modos de fallo (22):** State relabeling; unstable fits; smoothing leakage if smoothed states are used.
- **Fijo (23):** Forward-filtered probabilities only. **A calibrar (23):** Number of states {2,3}, refit cadence.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-082 - Change-point-based strategy switching

- **ID, familia, estado (1, 3, 30):** QS-082 | I | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Structural breaks in return or volatility signal that the prior rule may no longer apply.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Bayesian online change-point detection (hazard 1/200) on returns and log volatility; after a detected change point, switch from the trend rule to the reversion rule for 50 bars.
- **Entrada corta (10):** Per base rule.
- **Salida (11):** Per base rule, or switch back after 50 bars.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** Per base rule.
- **Holding maximo (15):** 50 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Transitions.
- **No operar (20):** Fewer than 200 bars since the last change point.
- **Hipotesis (21):** Switching at detected change points improves net expectancy over staying with one rule.
- **Modos de fallo (22):** False change points; detection delay.
- **Fijo (23):** Causal detector. **A calibrar (23):** Hazard {1/100,1/200,1/400}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-083 - Hurst-informed regime selection, with appropriate estimator limitations

- **ID, familia, estado (1, 3, 30):** QS-083 | I | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** The Hurst exponent distinguishes persistence from anti-persistence, but estimates are noisy on short windows.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 15m, 1h
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Rolling Hurst (DFA or variance-ratio-based) on 256 bars; H above 0.55: trend rule; H below 0.45: reversion rule; else flat; trade only if the bootstrap 90% interval excludes 0.5.
- **Entrada corta (10):** Per base rule.
- **Salida (11):** Per base rule, or regime leaves the band.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** Per base rule.
- **Holding maximo (15):** Per base rule
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Persistent vs anti-persistent.
- **No operar (20):** Bootstrap interval includes 0.5.
- **Hipotesis (21):** Intervals excluding 0.5 identify regimes where the matching rule earns net expectancy.
- **Modos de fallo (22):** Estimator bias and wide intervals; regime flicker.
- **Fijo (23):** Bootstrap gate. **A calibrar (23):** Window {256,512}, bands.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-084 - Realized-volatility regime allocation

- **ID, familia, estado (1, 3, 30):** QS-084 | I | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Reversion tends to work in low-volatility states and trend/breakout in high-volatility states.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** RV percentile (trailing 500) below 30: weight 100% on RSI reversion (#11); above 70: Donchian breakout (#4); between: smooth blend.
- **Entrada corta (10):** Per sleeve.
- **Salida (11):** Per sleeve.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** Per sleeve.
- **Holding maximo (15):** Per sleeve
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Volatility cycles.
- **No operar (20):** RV above its 99th percentile.
- **Hipotesis (21):** Volatility-based allocation beats either sleeve alone on a net risk-adjusted basis.
- **Modos de fallo (22):** Regime lag; blend instability.
- **Fijo (23):** Causal percentiles. **A calibrar (23):** Cut percentiles {25/75,30/70}.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-085 - Trend-versus-reversion regime classifier

- **ID, familia, estado (1, 3, 30):** QS-085 | I | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** A model can learn which baseline will perform better next, given causal features.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 15m, 1h
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Regularized logistic regression, trained walk-forward, predicts which of {trend #1, reversion #11} has the better next-24-bar outcome from ADX, RV ratio, autocorrelation and Hurst features; run the favored sleeve.
- **Entrada corta (10):** Per sleeve.
- **Salida (11):** Per sleeve.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** Per sleeve.
- **Holding maximo (15):** Per sleeve
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Classifier-driven.
- **No operar (20):** Predicted probability between 0.45 and 0.55.
- **Hipotesis (21):** Classifier-selected sleeves beat the best fixed sleeve, out of sample, net of costs.
- **Modos de fallo (22):** Label leakage; unstable features.
- **Fijo (23):** Purged labels, embargo, walk-forward. **A calibrar (23):** Regularization strength, feature set.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-086 - Bayesian signal weighting

- **ID, familia, estado (1, 3, 30):** QS-086 | I | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Combining several signals with weights from their recent posterior performance adapts to changing regimes.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 15m, 1h
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Weights over K baseline sleeves from a Bayesian model average with a forgetting factor 0.98; long when the weighted score exceeds +0.3.
- **Entrada corta (10):** Short below -0.3.
- **Salida (11):** Score crosses 0, or max hold.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 150 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Adaptive.
- **No operar (20):** Fewer than 100 observations per sleeve.
- **Hipotesis (21):** Posterior-weighted combination beats equal-weight combination net of costs.
- **Modos de fallo (22):** Weight turnover; overfitting.
- **Fijo (23):** Causal updates. **A calibrar (23):** Forgetting factor {0.95,0.98,0.99}, thresholds.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-087 - Walk-forward calibrated probability model

- **ID, familia, estado (1, 3, 30):** QS-087 | I | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** A calibrated probability of a profitable trade lets sizing and filtering follow evidence rather than raw scores.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Regularized model (logistic or gradient boosting) predicting P(return over H bars exceeds cost); isotonic calibration on the validation fold; trade when calibrated p exceeds 0.55 and expected edge exceeds Base costs.
- **Entrada corta (10):** Mirror for the short model.
- **Salida (11):** H bars, or p falls below 0.5.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** H = 12 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Feature-driven.
- **No operar (20):** Calibration drift flag.
- **Hipotesis (21):** A calibrated model keeps a positive net edge out of sample.
- **Modos de fallo (22):** Label leakage; calibration drift.
- **Fijo (23):** Purge and embargo; walk-forward refit. **A calibrar (23):** Model class, regularization, H.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-088 - Dynamic volatility-targeted exposure

- **ID, familia, estado (1, 3, 30):** QS-088 | I | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** A volatility-managed long exposure earns a better risk-adjusted return than constant exposure.
- **Instrumentos (5):** BTC, ETH, SOL
- **Timeframes (6):** 1h
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Long BTC or ETH perp with exposure = min(2x, target vol / EWMA vol); rebalance when exposure deviates by more than 20%.
- **Entrada corta (10):** None (long exposure).
- **Salida (11):** Exposure rescaling only; no discrete exit.
- **Stop (12):** Portfolio stop -15% from peak (replaces ATR stop).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** Continuous
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Any.
- **No operar (20):** Vol forecast unavailable.
- **Hipotesis (21):** Volatility targeting improves Sharpe and drawdown versus buy-and-hold at similar average exposure.
- **Modos de fallo (22):** Vol-of-vol; funding drag; rebalancing costs.
- **Fijo (23):** EWMA vol, cap 2x. **A calibrar (23):** Target vol {20,30,40}%.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7. **Override de sizing:** Exposure sizing replaces the 1% stop rule.
- **Nota:** Differs from #80 (overlay on trend signals): this is a standalone long exposure.

### QS-089 - Regime-conditioned breakout

- **ID, familia, estado (1, 3, 30):** QS-089 | I | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Breakouts follow through in expansion regimes and fail in compression-less chop.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 15m, 1h
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Donchian(20) breakout taken only when the HMM high-volatility-trend probability (#81, filtered) exceeds 0.6 and RV percentile is rising.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Close below the 10-bar low.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 150 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Expansion.
- **No operar (20):** State probability below 0.6.
- **Hipotesis (21):** Regime-gated breakouts beat ungated breakouts net of costs.
- **Modos de fallo (22):** Late regime detection.
- **Fijo (23):** Forward-filtered probabilities. **A calibrar (23):** Probability threshold.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-090 - Regime-conditioned mean reversion

- **ID, familia, estado (1, 3, 30):** QS-090 | I | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Reversion works in low-trend states and fails when a trend takes hold.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** RSI(14) < 30 long only when the HMM low-volatility-range probability exceeds 0.6 and ADX(14) < 20.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** RSI(14) > 50, or 48 bars.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 48 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Range.
- **No operar (20):** State probability below 0.6; ADX(14) above 25.
- **Hipotesis (21):** Regime-gated reversion beats ungated RSI reversion (#11) net of costs.
- **Modos de fallo (22):** Regime flips mid-trade.
- **Fijo (23):** Forward-filtered probabilities. **A calibrar (23):** Probability threshold, ADX cap.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7


---

## Familia J: Multi-signal and portfolio

### QS-091 - Trend plus volume confirmation

- **ID, familia, estado (1, 3, 30):** QS-091 | J | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Trends backed by rising participation are more durable.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** EMA(20) above EMA(100) with close above EMA(200), volume above 1.2*SMA(volume,50), and OBV above its own EMA(20).
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** EMA(20) crosses below EMA(100).
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 300 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Trending with participation.
- **No operar (20):** Volume below 0.7*SMA(volume,50).
- **Hipotesis (21):** Adding volume confirmation to #1 improves net expectancy.
- **Modos de fallo (22):** Volume filters remove valid trends.
- **Fijo (23):** Confirmation conditions. **A calibrar (23):** Volume multiple, OBV smoothing.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-092 - Mean reversion plus higher-timeframe regime filter

- **ID, familia, estado (1, 3, 30):** QS-092 | J | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Reversion trades aligned with a non-trending HTF regime avoid trending traps.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** Entries 5m and 15m (HTF 1h); entries 1h (HTF 4h)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** RSI(14) < 30, HTF ADX(14) < 25 and HTF close above EMA(200) (HTF bars closed).
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** RSI(14) > 50, or 48 bars.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 48 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** HTF range.
- **No operar (20):** HTF ADX above 25.
- **Hipotesis (21):** The HTF regime filter improves #11 net expectancy.
- **Modos de fallo (22):** HTF lag; fewer trades.
- **Fijo (23):** Closed-HTF-bar regime. **A calibrar (23):** HTF ADX cap, EMA length.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-093 - VWAP plus trade-flow confluence

- **ID, familia, estado (1, 3, 30):** QS-093 | J | DATA-PARTIAL (needs extra verified data: OI, spot/futures history, or bar-level taker fields) | SPECIFIED, not implemented, not backtested
- **Racional (4):** A VWAP reclaim backed by aggressor flow is a stronger signal than either alone.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines); bar-level taker-buy/taker-sell volume (kline taker-buy fields)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first; aggregated per bar only, no tick sequencing; verify the fields exist in the stored dataset
- **Entrada larga (9):** Close crosses above session VWAP and taker imbalance above +0.15 for 2 consecutive bars (bar-level).
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Close below VWAP.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 48 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Intraday trend.
- **No operar (20):** First 60 minutes of the session.
- **Hipotesis (21):** Flow confluence improves VWAP-cross expectancy.
- **Modos de fallo (22):** Bar-level flow lags.
- **Fijo (23):** Confluence rule. **A calibrar (23):** Imbalance threshold.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-094 - Breakout plus order-book imbalance

- **ID, familia, estado (1, 3, 30):** QS-094 | J | DATA-BLOCKED (needs L2, tick trades or liquidations not in the assumed data contract) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Breaks accompanied by supportive resting depth are likelier to continue.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** historical L1/L2 order-book data with exchange timestamps
- **Dependencias y limites (8):** not in the assumed data contract; replay does not prove fills (queue, latency, cancellations)
- **Entrada larga (9):** Close above the 20-bar high and depth imbalance above +0.25 for at least 6 of the last 10 snapshots.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Close below EMA(20).
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 60 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Breakout.
- **No operar (20):** Stale book; spread above its 90th percentile.
- **Hipotesis (21):** Depth confirmation improves breakout expectancy.
- **Modos de fallo (22):** Spoofing.
- **Fijo (23):** Confluence rule. **A calibrar (23):** Imbalance threshold.
- **Retos de ejecucion (26):** Requires verified L2 history.
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-095 - Funding plus relative momentum

- **ID, familia, estado (1, 3, 30):** QS-095 | J | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Cross-sectional momentum is more durable where funding shows no crowding.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 1h
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines); realized funding-rate history with payment timestamps
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first; use realized values only; verify the funding interval per symbol
- **Entrada larga (9):** Rank by volatility-adjusted 72-bar return (as #63); long the top 2 only if funding is below its 80th percentile; short the bottom 2 only if funding is above its 20th percentile.
- **Entrada corta (10):** Included (dollar-neutral when both legs qualify).
- **Salida (11):** Rebalance every 12 bars.
- **Stop (12):** Portfolio stop -3% from the last rebalance.
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 48 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Dispersion with uncrowded funding.
- **No operar (20):** Fewer than 2 qualifying legs per side.
- **Hipotesis (21):** Funding-filtered momentum improves #63 net risk-adjusted returns.
- **Modos de fallo (22):** Few assets; filters reduce breadth.
- **Fijo (23):** Percentile rule. **A calibrar (23):** Percentile cutoffs.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7. **Override de sizing:** Portfolio sizing as in #63.

### QS-096 - Market-structure reversal plus volatility filter

- **ID, familia, estado (1, 3, 30):** QS-096 | J | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Structure-based reversals work best in moderate volatility, not in dead markets or panic.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 5m, 15m, 1h (each timeframe is a separate hypothesis)
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** The #33 CHoCH retest long, taken only when ATR(14) percentile (500 bars) is between 30 and 80.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** As #33.
- **Stop (12):** As #33.
- **Toma de ganancias (13):** As #33.
- **Holding maximo (15):** 100 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Moderate volatility transition.
- **No operar (20):** ATR percentile outside 30-80.
- **Hipotesis (21):** The volatility filter improves #33 expectancy.
- **Modos de fallo (22):** Fewer trades.
- **Fijo (23):** Percentile band. **A calibrar (23):** Band edges.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-097 - Cross-asset confirmation strategy

- **ID, familia, estado (1, 3, 30):** QS-097 | J | DATA-READY (OHLCV/funding; pending Phase 2 verification) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Moves confirmed across several assets reflect market-wide flow rather than idiosyncratic noise.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 15m, 1h
- **Datos requeridos (7):** OHLCV candles (Binance USDT-M perp klines)
- **Dependencias y limites (8):** candle-only: no intrabar sequencing, so same-candle stop/target ties resolve stop-first
- **Entrada larga (9):** Donchian(20) breakout on asset X taken only if BTC and ETH are above their own EMA(50) and at least 2 of the other perps are above theirs.
- **Entrada corta (10):** Mirror image of the long rules (two-sided variant, tested as a separate hypothesis from long-only).
- **Salida (11):** Close below the 10-bar low, or confirmation lost.
- **Stop (12):** 2*ATR(14).
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** 150 bars
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Broad market trend.
- **No operar (20):** Confirmation set contains stale data.
- **Hipotesis (21):** Cross-asset confirmation improves breakout expectancy over single-asset breakouts.
- **Modos de fallo (22):** Confirmation lags; reduces idiosyncratic winners.
- **Fijo (23):** Confirmation set definition. **A calibrar (23):** EMA length, confirmation count.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7

### QS-098 - Risk-budgeted multi-strategy portfolio

- **ID, familia, estado (1, 3, 30):** QS-098 | J | DEPENDENT (needs independently validated component strategies) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Combining uncorrelated validated strategies with risk budgets improves portfolio Sharpe.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 1h
- **Datos requeridos (7):** return streams of independently validated strategies
- **Dependencias y limites (8):** cannot be tested until component strategies pass Gate 6
- **Entrada larga (9):** Allocate across strategies that pass Gate 6, with equal risk contribution from a causal 60-day covariance estimate and caps per strategy.
- **Entrada corta (10):** n/a
- **Salida (11):** Monthly rebalance.
- **Stop (12):** Portfolio drawdown rule from G1.
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** Continuous
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Any.
- **No operar (20):** Fewer than 3 validated components.
- **Hipotesis (21):** The risk-budgeted portfolio beats the best single component on a risk-adjusted net basis.
- **Modos de fallo (22):** Correlation spikes in stress; shared costs.
- **Fijo (23):** Causal covariance. **A calibrar (23):** Covariance window, caps.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7. **Override de sizing:** Portfolio-level risk budget replaces per-trade sizing.

### QS-099 - Correlation-aware strategy allocation

- **ID, familia, estado (1, 3, 30):** QS-099 | J | DEPENDENT (needs independently validated component strategies) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Allocation that accounts for correlated strategies avoids hidden concentration.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 1h
- **Datos requeridos (7):** return streams of independently validated strategies
- **Dependencias y limites (8):** cannot be tested until component strategies pass Gate 6
- **Entrada larga (9):** Hierarchical risk parity or minimum-correlation weights over validated strategies, using Ledoit-Wolf shrinkage on past data.
- **Entrada corta (10):** n/a
- **Salida (11):** Monthly rebalance.
- **Stop (12):** Portfolio drawdown rule from G1.
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** Continuous
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Any.
- **No operar (20):** Fewer than 3 validated components.
- **Hipotesis (21):** Correlation-aware weights reduce drawdown versus equal weights.
- **Modos de fallo (22):** Estimation error; regime shifts.
- **Fijo (23):** Shrinkage estimator. **A calibrar (23):** Window, linkage.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7. **Override de sizing:** Portfolio-level risk budget replaces per-trade sizing.
- **Nota:** Differs from #98: allocation uses clustering/shrinkage rather than equal risk contribution.

### QS-100 - Meta-strategy that selects among independently validated strategy families using causal regime information

- **ID, familia, estado (1, 3, 30):** QS-100 | J | DEPENDENT (needs independently validated component strategies) | SPECIFIED, not implemented, not backtested
- **Racional (4):** Different families win in different regimes; a causal selector can allocate to the right one.
- **Instrumentos (5):** BTC, ETH, SOL, HYPE, SUI, JUP USDT-M perps (per-symbol history to be verified)
- **Timeframes (6):** 1h
- **Datos requeridos (7):** return streams of independently validated strategies
- **Dependencias y limites (8):** cannot be tested until component strategies pass Gate 6
- **Entrada larga (9):** Regime from #81/#84/#85 (causal) selects among family sleeves that have already passed Gate 6; nested walk-forward evaluates the selector.
- **Entrada corta (10):** n/a
- **Salida (11):** Regime change, with a minimum dwell time of 24 bars.
- **Stop (12):** Portfolio drawdown rule from G1.
- **Toma de ganancias (13):** None.
- **Holding maximo (15):** Continuous
- **Frecuencia (16):** One entry per signal episode (no re-entry while the condition persists); cool-down 5 bars after an exit; max 1 open position per symbol
- **Regimen esperado (19):** Regime-dependent.
- **No operar (20):** No validated sleeves for the current regime.
- **Hipotesis (21):** Selection among validated sleeves beats the best fixed sleeve out of sample; selection uncertainty is counted as extra multiple testing.
- **Modos de fallo (22):** Selection overfitting; regime lag.
- **Fijo (23):** Causal regime inputs only. **A calibrar (23):** Dwell time, regime source.
- **Retos de ejecucion (26):** Taker entry at next-bar open; stop-market slippage in fast moves; costs matter most on 5m
- **Heredados:** 14 sizing = G1; 17 costos = G2; 18 funding = G3; 24 validacion = G4; 25 datos minimos = G5; 27 graficos = G6; 28-29 aceptacion/rechazo = G7. **Override de sizing:** Portfolio-level risk budget replaces per-trade sizing.
