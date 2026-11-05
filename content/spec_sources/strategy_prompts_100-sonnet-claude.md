# 100 prompts de backtest · SOL · HYPE · SUI · ETH · BTC · JUP · SPCX · NVDA

Plantilla base (tu ejemplo): *RSI mean-reversion, 5m-15m-1h, 6 meses, 1% de riesgo por trade, stop ATR(14)\*2, equity curve + drawdown chart + Sharpe / max DD / win rate / profit factor.* Cada bloque de abajo es autónomo: se copia y se pega tal cual.

## Convenciones

- **Tamaño de posición** = 1% del equity / distancia al stop. **R** = distancia inicial al stop. *Mirror* = lógica espejo para el lado corto.
- Horarios en **UTC**. "Long only" = solo largos; "Long/Short" = ambos lados.
- Donde el prompt dice `5m-15m-1h`, el agente corre las tres temporalidades por separado y compara.
- Si un par no tiene 6 meses de historial en tu fuente de datos (puede pasar con SPCX o NVDA), el agente debe usar el historial disponible y decir la ventana real.
- **94-96** usan funding, open interest y long/short ratio. Hasta donde sé, la API de Binance solo da ~30 días de historial de OI y long/short; para 6 meses conviene usar los archivos de data.binance.vision u otra fuente, y reportar la ventana real.
- **99-100** son pares ratio dollar-neutral (dos patas), no un solo activo.
- Los prompts no incluyen comisiones ni slippage (igual que tu ejemplo). Sufijo opcional para añadir al final de cualquiera: `Fees and slippage on. Show trade count and compare against buy and hold.`

## Índice

| Familia | IDs | # |
|---|---|---|
| A. Reversion a la media | 01-15 | 15 |
| B. Seguimiento de tendencia | 16-30 | 15 |
| C. Rupturas y volatilidad | 31-45 | 15 |
| D. Momentum | 46-55 | 10 |
| E. Volumen, VWAP y flujo | 56-65 | 10 |
| F. Price action y SMC | 66-77 | 12 |
| G. Sesiones y tiempo (UTC) | 78-85 | 8 |
| H. Regimenes, confluencias y derivados | 86-100 | 15 |


---

## A. Reversion a la media

**01 · RSI(14) long/short mean-reversion · SPCX/USDT**

```text
Use available skills. An RSI(14) long/short mean-reversion strategy on SPCX/USDT 5m-15m-1h candles for the past 6 months. Long: entry when RSI(14) < 30, exit when RSI(14) > 50. Short: entry when RSI(14) > 70, exit when RSI(14) < 50. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**02 · RSI(2) Connors-style pullback · JUP/USDT**

```text
Use available skills. An RSI(2) Connors-style pullback strategy on JUP/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when RSI(2) < 10 and close > SMA(200), exit when close > SMA(5). Use 1% risk per trade with ATR(14)*3 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**03 · Bollinger Bands (20,2) mean-reversion · SPCX/USDT**

```text
Use available skills. A Bollinger Bands (20,2) mean-reversion strategy on SPCX/USDT 5m-15m-1h candles for the past 6 months. Long: entry when close dips below the lower band and the next bar closes back inside the band, exit at the middle band (SMA 20). Short: mirror on the upper band. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**04 · Bollinger %B + RSI mean-reversion · NVDA/USDT**

```text
Use available skills. A Bollinger %B + RSI mean-reversion strategy on NVDA/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when %B(20,2) < 0 and RSI(14) < 35, exit when %B > 0.5. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**05 · price z-score mean-reversion · JUP/USDT**

```text
Use available skills. A price z-score mean-reversion strategy on JUP/USDT 5m-15m-1h candles for the past 6 months. z = (close - SMA(50)) / stdev(close, 50). Long: entry when z < -2, exit when z > 0. Short: entry when z > 2, exit when z < 0. Use 1% risk per trade with ATR(14)*2.5 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**06 · Stochastic (14,3,3) oversold/overbought · SPCX/USDT**

```text
Use available skills. A Stochastic (14,3,3) oversold/overbought strategy on SPCX/USDT 5m-15m-1h candles for the past 6 months. Long: entry when %K crosses above %D while both are below 20, exit when %K > 80. Short: entry when %K crosses below %D while both are above 80, exit when %K < 20. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**07 · CCI(20) extreme-reversion · NVDA/USDT**

```text
Use available skills. A CCI(20) extreme-reversion strategy on NVDA/USDT 5m-15m-1h candles for the past 6 months. Long: entry when CCI(20) < -150, exit when CCI(20) > 0. Short: entry when CCI(20) > 150, exit when CCI(20) < 0. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**08 · Williams %R(14) reversal · HYPE/USDT**

```text
Use available skills. A Williams %R(14) reversal strategy on HYPE/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when %R was below -90 and crosses back above -80, exit when %R > -20. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**09 · MFI(14) + RSI(14) oversold · SUI/USDT**

```text
Use available skills. An MFI(14) + RSI(14) oversold strategy on SUI/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when MFI(14) < 20 and RSI(14) < 35, exit when MFI(14) > 60. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**10 · IBS (internal bar strength) mean-reversion · ETH/USDT**

```text
Use available skills. An IBS (internal bar strength) mean-reversion strategy on ETH/USDT 5m-15m-1h candles for the past 6 months. IBS = (close - low) / (high - low). Long only: entry when IBS < 0.2 and close > SMA(100), exit when IBS > 0.7. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**11 · session VWAP deviation mean-reversion · SUI/USDT**

```text
Use available skills. A session VWAP deviation mean-reversion strategy on SUI/USDT 5m-15m-1h candles for the past 6 months. VWAP resets daily at 00:00 UTC; use the rolling 100-bar stdev of (close - VWAP). Long: entry when close < VWAP - 2*stdev, exit at VWAP. Short: entry when close > VWAP + 2*stdev, exit at VWAP. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**12 · Keltner Channel fade · ETH/USDT**

```text
Use available skills. A Keltner Channel fade strategy on ETH/USDT 5m-15m-1h candles for the past 6 months. Channel = EMA(20) +/- 2*ATR(10). Long: entry when close closes back above the lower band after closing below it, exit at EMA(20). Short: mirror on the upper band. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**13 · consecutive-down-bars bounce · BTC/USDT**

```text
Use available skills. A consecutive-down-bars bounce strategy on BTC/USDT 5m-15m-1h candles for the past 6 months. Long only: entry after 4 consecutive red closes while close > EMA(200), exit when close > the previous bar's high. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**14 · RSI(7) 20-bar-low reversal · JUP/USDT**

```text
Use available skills. An RSI(7) 20-bar-low reversal strategy on JUP/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when RSI(7) < 20 and close is at a 20-bar low, exit when RSI(7) > 60. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**15 · EMA(50) overextension reversion · SPCX/USDT**

```text
Use available skills. An EMA(50) overextension reversion strategy on SPCX/USDT 5m-15m-1h candles for the past 6 months. Long: entry when close < EMA(50) - 3*ATR(14), exit at EMA(50). Short: entry when close > EMA(50) + 3*ATR(14), exit at EMA(50). Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```


---

## B. Seguimiento de tendencia

**16 · EMA 9/21 crossover · NVDA/USDT**

```text
Use available skills. An EMA 9/21 crossover strategy on NVDA/USDT 5m-15m-1h candles for the past 6 months. Long: entry when EMA(9) crosses above EMA(21), exit on the opposite cross. Short: entry when EMA(9) crosses below EMA(21), exit on the opposite cross. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**17 · EMA 20/50 trend strategy with an EMA(200) filter · HYPE/USDT**

```text
Use available skills. An EMA 20/50 trend strategy with an EMA(200) filter on HYPE/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when EMA(20) crosses above EMA(50) and close > EMA(200), exit when EMA(20) crosses below EMA(50). Use 1% risk per trade with ATR(14)*3 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**18 · Supertrend (10,3) · HYPE/USDT**

```text
Use available skills. A Supertrend (10,3) strategy on HYPE/USDT 5m-15m-1h candles for the past 6 months. Long: entry when Supertrend flips bullish, exit when it flips bearish. Short: mirror. Use 1% risk per trade with the Supertrend line as stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**19 · Donchian(20) breakout · SUI/USDT**

```text
Use available skills. A Donchian(20) breakout strategy on SUI/USDT 5m-15m-1h candles for the past 6 months. Long: entry when close breaks above the 20-bar highest high, exit when close breaks below the 10-bar lowest low. Short: mirror. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**20 · ADX + DI crossover · ETH/USDT**

```text
Use available skills. An ADX + DI crossover strategy on ETH/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when +DI crosses above -DI while ADX(14) > 25 and rising, exit when ADX(14) < 20 or -DI crosses above +DI. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**21 · MACD(12,26,9) trend · BTC/USDT**

```text
Use available skills. A MACD(12,26,9) trend strategy on BTC/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when MACD crosses above the signal line while MACD > 0, exit when MACD crosses below the signal line. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**22 · Ichimoku cloud breakout · JUP/USDT**

```text
Use available skills. An Ichimoku cloud breakout strategy on JUP/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when close breaks above the cloud and Tenkan > Kijun, exit when close falls below Kijun. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**23 · Parabolic SAR + EMA(100) · SPCX/USDT**

```text
Use available skills. A Parabolic SAR + EMA(100) strategy on SPCX/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when SAR (0.02, 0.2) flips below price and close > EMA(100), exit when SAR flips above price. Use 1% risk per trade with the Parabolic SAR value as stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**24 · Hull MA(55) slope · NVDA/USDT**

```text
Use available skills. A Hull MA(55) slope strategy on NVDA/USDT 5m-15m-1h candles for the past 6 months. Long: entry when HMA(55) turns up (slope changes from negative to positive), exit when it turns down. Short: mirror. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**25 · Keltner Channel breakout · SOL/USDT**

```text
Use available skills. A Keltner Channel breakout strategy on SOL/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when close > EMA(20) + 2*ATR(10), exit when close < EMA(20). Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**26 · triple EMA (8/21/55) pullback · HYPE/USDT**

```text
Use available skills. A triple EMA (8/21/55) pullback strategy on HYPE/USDT 5m-15m-1h candles for the past 6 months. Long only: while EMA(8) > EMA(21) > EMA(55), entry when close crosses back above EMA(21) after dipping below it, exit when EMA(8) crosses below EMA(21). Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**27 · Aroon(25) trend · SUI/USDT**

```text
Use available skills. An Aroon(25) trend strategy on SUI/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when Aroon Up > 70 and Aroon Down < 30, exit when Aroon Up < 50. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**28 · linear-regression slope trend · ETH/USDT**

```text
Use available skills. A linear-regression slope trend strategy on ETH/USDT 5m-15m-1h candles for the past 6 months. Long: entry when the LinReg(50) slope is positive and R-squared > 0.5, exit when the slope turns negative. Short: mirror with a negative slope. Use 1% risk per trade with ATR(14)*2.5 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**29 · KAMA(10,2,30) trend · BTC/USDT**

```text
Use available skills. A KAMA(10,2,30) trend strategy on BTC/USDT 5m-15m-1h candles for the past 6 months. Long: entry when close crosses above KAMA and KAMA is rising, exit when close crosses below KAMA. Short: mirror. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**30 · Turtle 55/20 breakout · JUP/USDT**

```text
Use available skills. A Turtle 55/20 breakout strategy on JUP/USDT 5m-15m-1h candles for the past 6 months. Long: entry when close breaks above the 55-bar high, exit when close breaks below the 20-bar low. Short: mirror. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```


---

## C. Rupturas y volatilidad

**31 · opening-range breakout · SPCX/USDT**

```text
Use available skills. An opening-range breakout strategy on SPCX/USDT 5m-15m candles for the past 6 months. Opening range = first 60 minutes after 00:00 UTC. Long: entry when close breaks above the range high. Short: entry when close breaks below the range low. Exit at 23:55 UTC at the latest. Use 1% risk per trade with a stop loss at the opposite side of the opening range. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**32 · Bollinger squeeze breakout · NVDA/USDT**

```text
Use available skills. A Bollinger squeeze breakout strategy on NVDA/USDT 5m-15m-1h candles for the past 6 months. Squeeze = Bollinger Band width (20,2) in its lowest 10% of the last 200 bars. Long: entry when close breaks above the upper band during or right after a squeeze, exit when close < SMA(20). Short: mirror. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**33 · TTM-style squeeze momentum · SOL/USDT**

```text
Use available skills. A TTM-style squeeze momentum strategy on SOL/USDT 5m-15m-1h candles for the past 6 months. Squeeze is on when the Bollinger Bands (20,2) sit inside the Keltner Channel (20, 1.5*ATR). Entry on squeeze release in the direction of the momentum histogram (linear regression of close minus the midline), exit when the momentum flips sign. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**34 · NR7 breakout · HYPE/USDT**

```text
Use available skills. An NR7 breakout strategy on HYPE/USDT 5m-15m-1h candles for the past 6 months. NR7 = the bar with the narrowest range of the last 7 bars. Long: entry when a later close breaks above the NR7 high. Short: entry when a later close breaks below the NR7 low. Exit after 10 bars. Use 1% risk per trade with a stop loss at the opposite end of the NR7 bar. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**35 · inside-bar breakout · SUI/USDT**

```text
Use available skills. An inside-bar breakout strategy on SUI/USDT 5m-15m-1h candles for the past 6 months. Long: entry when close breaks above the mother-bar high after an inside bar, exit at 2R or when close falls back below the mother bar's midpoint. Short: mirror. (R = initial stop distance.) Use 1% risk per trade with a stop loss at the opposite end of the mother bar. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**36 · ATR expansion momentum · ETH/USDT**

```text
Use available skills. An ATR expansion momentum strategy on ETH/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when a bar's range > 2*ATR(14) and the close is in the top 25% of that range, exit after 8 bars or when close < EMA(20). Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**37 · range-box breakout strategy with volume confirmation · BTC/USDT**

```text
Use available skills. A range-box breakout strategy with volume confirmation on BTC/USDT 5m-15m-1h candles for the past 6 months. Box = the last 48 bars when their high-low range is < 3*ATR(14). Long: entry when close breaks above the box high with volume > 1.5*SMA(volume,20), exit when close < the box midpoint. Use 1% risk per trade with a stop loss at the box low. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**38 · 20-bar high breakout strategy with volume spike · JUP/USDT**

```text
Use available skills. A 20-bar high breakout strategy with volume spike on JUP/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when close > the 20-bar highest high and volume > 2*SMA(volume,20), exit when close < EMA(20). Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**39 · previous-day high/low breakout · SPCX/USDT**

```text
Use available skills. A previous-day high/low breakout strategy on SPCX/USDT 5m-15m-1h candles for the past 6 months. Long: entry when close breaks above the previous UTC day's high. Short: entry when close breaks below the previous UTC day's low. Exit at 23:55 UTC. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**40 · previous-week high/low breakout · BTC/USDT**

```text
Use available skills. A previous-week high/low breakout strategy on BTC/USDT 1h candles for the past 6 months. Weeks start Monday 00:00 UTC. Long: entry when close breaks above the previous week's high, exit when close falls back below it. Short: mirror with the previous week's low. Use 1% risk per trade with ATR(14)*3 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**41 · Bollinger Band walk · SOL/USDT**

```text
Use available skills. A Bollinger Band walk strategy on SOL/USDT 5m-15m-1h candles for the past 6 months. Long only: entry after 2 consecutive closes above the upper band (20,2) while ADX(14) > 25, exit when close < SMA(20). Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**42 · volatility-contraction breakout · NVDA/USDT**

```text
Use available skills. A volatility-contraction breakout strategy on NVDA/USDT 5m-15m-1h candles for the past 6 months. Contraction = ATR(5)/ATR(50) < 0.6. Long: entry during contraction when close breaks above the 10-bar high, exit when ATR(5)/ATR(50) > 1.2 or close < EMA(10). Short: mirror. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**43 · Donchian(55) breakout strategy with a volatility filter · SUI/USDT**

```text
Use available skills. A Donchian(55) breakout strategy with a volatility filter on SUI/USDT 5m-15m-1h candles for the past 6 months. Only trade when ATR(14) is above its 100-bar median. Long: entry when close > the 55-bar high, exit when close < the 20-bar low. Short: mirror. Use 1% risk per trade with ATR(14)*2.5 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**44 · fractal breakout · ETH/USDT**

```text
Use available skills. A fractal breakout strategy on ETH/USDT 5m-15m-1h candles for the past 6 months. Use 5-bar fractals. Long: entry when close breaks above the last confirmed fractal high, exit when close breaks below the last confirmed fractal low. Short: mirror. Use 1% risk per trade with a stop loss at the last opposite fractal. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**45 · impulse-bar continuation · BTC/USDT**

```text
Use available skills. An impulse-bar continuation strategy on BTC/USDT 5m-15m-1h candles for the past 6 months. Impulse = a bar whose return is more than 3 standard deviations of the last 100 bar returns. Enter at the next open in the impulse direction (long and short), exit after 6 bars. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```


---

## D. Momentum

**46 · ROC(24) momentum · JUP/USDT**

```text
Use available skills. An ROC(24) momentum strategy on JUP/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when ROC(24) > 0 and ROC(24) is above its 10-bar SMA, exit when ROC(24) < 0. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**47 · time-series momentum · SPCX/USDT**

```text
Use available skills. A time-series momentum strategy on SPCX/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when the 100-bar return and the 20-bar return are both positive, exit when the 20-bar return turns negative. Use 1% risk per trade with ATR(14)*3 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**48 · RSI(14) momentum · NVDA/USDT**

```text
Use available skills. An RSI(14) momentum strategy on NVDA/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when RSI(14) crosses above 60 and close > EMA(50), exit when RSI(14) < 45. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**49 · Awesome Oscillator zero-cross · SOL/USDT**

```text
Use available skills. An Awesome Oscillator zero-cross strategy on SOL/USDT 5m-15m-1h candles for the past 6 months. Long: entry when AO(5,34) crosses above zero, exit when it crosses below zero. Short: mirror. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**50 · Elder Impulse System · HYPE/USDT**

```text
Use available skills. An Elder Impulse System strategy on HYPE/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when EMA(13) is rising and the MACD histogram (12,26,9) is rising, exit when either turns down. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**51 · relative-strength-vs-BTC momentum · SUI/USDT**

```text
Use available skills. A relative-strength-vs-BTC momentum strategy on SUI/USDT 5m-15m-1h candles for the past 6 months. Relative return = the pair's 24-bar return minus BTC/USDT's 24-bar return. Long only: entry when relative return > 0, RSI(14) > 55 and BTC close > BTC EMA(50), exit when relative return < 0. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**52 · TRIX(15) zero-cross · ETH/USDT**

```text
Use available skills. A TRIX(15) zero-cross strategy on ETH/USDT 5m-15m-1h candles for the past 6 months. Long: entry when TRIX(15) crosses above zero, exit when it crosses below zero. Short: mirror. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**53 · True Strength Index (25,13) · BTC/USDT**

```text
Use available skills. A True Strength Index (25,13) strategy on BTC/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when TSI crosses above its 13-bar signal line while TSI > 0, exit when TSI crosses below the signal line. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**54 · MACD histogram acceleration · JUP/USDT**

```text
Use available skills. A MACD histogram acceleration strategy on JUP/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when close > EMA(200) and the MACD histogram (12,26,9) has increased for 3 consecutive bars, exit when it has decreased for 2 consecutive bars. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**55 · momentum-acceleration · SPCX/USDT**

```text
Use available skills. A momentum-acceleration strategy on SPCX/USDT 5m-15m-1h candles for the past 6 months. Acceleration = ROC(10) - ROC(10)[5]. Long: entry when ROC(10) > 0 and acceleration > 0, exit when acceleration < 0. Short: mirror. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```


---

## E. Volumen, VWAP y flujo

**56 · VWAP trend · NVDA/USDT**

```text
Use available skills. A VWAP trend strategy on NVDA/USDT 5m-15m-1h candles for the past 6 months. VWAP resets daily at 00:00 UTC. Long only: entry when close crosses above VWAP, VWAP is rising and volume > SMA(volume,20), exit when close < VWAP. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**57 · anchored-VWAP pullback · SOL/USDT**

```text
Use available skills. An anchored-VWAP pullback strategy on SOL/USDT 5m-15m-1h candles for the past 6 months. Anchor VWAP at the lowest low of the last 72 hours. Long only: entry when price pulls back to the anchored VWAP and closes above it with a bullish candle, exit when close < AVWAP - 0.5*ATR(14). Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**58 · OBV breakout · HYPE/USDT**

```text
Use available skills. An OBV breakout strategy on HYPE/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when OBV breaks above its 50-bar high while close > EMA(50), exit when OBV falls below its own EMA(20). Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**59 · Chaikin Money Flow · SUI/USDT**

```text
Use available skills. A Chaikin Money Flow strategy on SUI/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when CMF(20) crosses above 0.1 and close > EMA(50), exit when CMF(20) < 0. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**60 · volume-climax reversal · ETH/USDT**

```text
Use available skills. A volume-climax reversal strategy on ETH/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when a green bar has volume > 3*SMA(volume,20) and RSI(14) was < 25 on the previous bar, exit when RSI(14) > 55 or after 12 bars. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**61 · delta-proxy momentum · BTC/USDT**

```text
Use available skills. A delta-proxy momentum strategy on BTC/USDT 5m-15m-1h candles for the past 6 months. Delta proxy per bar = (close - open) / (high - low) * volume. Long only: entry when the 10-bar sum of the delta proxy exceeds 2 times its own 100-bar standard deviation and close > EMA(20), exit when the 10-bar sum < 0. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**62 · VWMA vs SMA volume-trend · JUP/USDT**

```text
Use available skills. A VWMA vs SMA volume-trend strategy on JUP/USDT 5m-15m-1h candles for the past 6 months. Long: entry when VWMA(20) > SMA(20) and close > VWMA(20), exit when VWMA(20) < SMA(20). Short: mirror. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**63 · Force Index trend · SPCX/USDT**

```text
Use available skills. A Force Index trend strategy on SPCX/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when the 13-bar EMA of Force Index crosses above 0 and close > EMA(50), exit when it crosses below 0. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**64 · low-volume pullback · NVDA/USDT**

```text
Use available skills. A low-volume pullback strategy on NVDA/USDT 5m-15m-1h candles for the past 6 months. Long only: while close > EMA(50), entry when a green bar closes above the previous high after 3 consecutive pullback bars with volume < SMA(volume,20), exit when close < EMA(20). Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**65 · volume-profile POC · SOL/USDT**

```text
Use available skills. A volume-profile POC strategy on SOL/USDT 5m-15m-1h candles for the past 6 months. POC = the price level (50 bins) with the highest traded volume over the last 200 bars. Long: entry when close crosses above the POC with volume > SMA(volume,20), exit when close crosses back below the POC. Short: mirror. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```


---

## F. Price action y SMC

**66 · liquidity sweep reversal · HYPE/USDT**

```text
Use available skills. A liquidity sweep reversal strategy on HYPE/USDT 5m-15m-1h candles for the past 6 months. Long: entry when price wicks below the previous 20-bar low and closes back above it, exit at 2R. Short: mirror with the 20-bar high. (R = initial stop distance.) Use 1% risk per trade with a stop loss beyond the sweep wick. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**67 · Fair Value Gap retest · SUI/USDT**

```text
Use available skills. A Fair Value Gap retest strategy on SUI/USDT 5m-15m-1h candles for the past 6 months. Bullish FVG = low[0] > high[2] on a displacement bar with range > 1.5*ATR(14). Long: entry when price retraces into the gap and closes above the gap midpoint, exit at 2R. Short: mirror with bearish FVGs. Use 1% risk per trade with a stop loss beyond the far edge of the gap. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**68 · order-block retest · ETH/USDT**

```text
Use available skills. An order-block retest strategy on ETH/USDT 5m-15m-1h candles for the past 6 months. Bullish order block = the last bearish candle before a bullish displacement of more than 2*ATR(14). Long: entry on the first retest of the block, exit at 2R. Short: mirror. Use 1% risk per trade with a stop loss beyond the order-block extreme. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**69 · break-of-structure pullback · BTC/USDT**

```text
Use available skills. A break-of-structure pullback strategy on BTC/USDT 5m-15m-1h candles for the past 6 months. Use 5-bar pivots. Long: after a close above the last swing high (BOS), entry at the 50% retracement of the impulse leg, exit at 2R. Short: mirror. Use 1% risk per trade with a stop loss beyond the pivot that started the impulse. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**70 · pin-bar at EMA(50) · JUP/USDT**

```text
Use available skills. A pin-bar at EMA(50) strategy on JUP/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when a bullish pin bar (lower wick > 2x the body, close in the top third of the range) touches EMA(50) while close > EMA(200), exit at 2R or when close < EMA(50). Use 1% risk per trade with a stop loss below the pin-bar low. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**71 · engulfing-at-extreme · SPCX/USDT**

```text
Use available skills. An engulfing-at-extreme strategy on SPCX/USDT 5m-15m-1h candles for the past 6 months. Long: entry when a bullish engulfing candle forms at a 20-bar low, exit at SMA(20). Short: bearish engulfing at a 20-bar high, exit at SMA(20). Use 1% risk per trade with a stop loss beyond the engulfing candle's extreme. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**72 · morning/evening star at Bollinger Bands · NVDA/USDT**

```text
Use available skills. A morning/evening star at Bollinger Bands strategy on NVDA/USDT 5m-15m-1h candles for the past 6 months. Long: entry on a morning star whose low is below the lower Bollinger Band (20,2), exit at SMA(20). Short: evening star above the upper band, exit at SMA(20). Use 1% risk per trade with a stop loss beyond the star's extreme. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**73 · double-bottom breakout · SOL/USDT**

```text
Use available skills. A double-bottom breakout strategy on SOL/USDT 5m-15m-1h candles for the past 6 months. Double bottom = two pivot lows within 1% of each other, 10-40 bars apart. Long: entry when close breaks above the highest high between them (neckline), exit at the measured move (pattern height projected from the neckline). Use 1% risk per trade with a stop loss below the second low. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**74 · market-structure HH/HL trend · HYPE/USDT**

```text
Use available skills. A market-structure HH/HL trend strategy on HYPE/USDT 5m-15m-1h candles for the past 6 months. Use 3-bar pivots. Long: entry after two consecutive higher highs and higher lows, exit when a lower low forms. Short: mirror. Use 1% risk per trade with a stop loss beyond the last higher low (long) / lower high (short). Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**75 · equal-highs liquidity grab · SUI/USDT**

```text
Use available skills. An equal-highs liquidity grab strategy on SUI/USDT 5m-15m-1h candles for the past 6 months. Equal highs = two or more pivot highs within 0.1% of each other. Short: entry when price wicks above them and closes back below, exit at 2R. (R = initial stop distance.) Use 1% risk per trade with a stop loss above the wick high. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**76 · support/resistance flip · ETH/USDT**

```text
Use available skills. A support/resistance flip strategy on ETH/USDT 5m-15m-1h candles for the past 6 months. Long only: after a close above the 50-bar resistance, entry when price retests the level from above and closes bullish, exit at 2R. (R = initial stop distance.) Use 1% risk per trade with a stop loss 0.5*ATR(14) below the flipped level. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**77 · previous-day low sweep · BTC/USDT**

```text
Use available skills. A previous-day low sweep strategy on BTC/USDT 5m-15m-1h candles for the past 6 months. Long: entry when price sweeps below the previous UTC day's low and closes back above it, exit at the previous day's midpoint. Short: mirror with the previous day's high. Use 1% risk per trade with a stop loss beyond the sweep extreme. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```


---

## G. Sesiones y tiempo (UTC)

**78 · Asia-range breakout strategy at the London open · ETH/USDT**

```text
Use available skills. An Asia-range breakout strategy at the London open on ETH/USDT 5m-15m candles for the past 6 months. Asia range = 00:00-07:00 UTC. Long: entry when close breaks above the range high after 07:00 UTC. Short: entry when close breaks below the range low. Exit at 16:00 UTC. Use 1% risk per trade with a stop loss at the opposite end of the Asia range. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**79 · London-open fade · SOL/USDT**

```text
Use available skills. A London-open fade strategy on SOL/USDT 5m-15m candles for the past 6 months. Short: entry at 07:30 UTC if price is more than 1.5*ATR(14) above the Asia session close, exit at the Asia session VWAP or at 12:00 UTC. Long: mirror below. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**80 · New York open momentum · NVDA/USDT**

```text
Use available skills. A New York open momentum strategy on NVDA/USDT 5m-15m candles for the past 6 months. Pre-open range = 12:30-13:30 UTC. Long: entry when the first 15m close after 13:30 UTC is above the pre-open high. Short: entry when it is below the pre-open low. Exit at 20:00 UTC. Use 1% risk per trade with a stop loss at the opposite side of the pre-open range. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**81 · hour-of-day seasonality · BTC/USDT**

```text
Use available skills. An hour-of-day seasonality strategy on BTC/USDT 1h candles for the past 6 months. Use the first 3 months to find the 3 UTC hours with the best average return and the 3 with the worst. In the following 3 months (out of sample) go long in the best hours and short in the worst hours, holding for that single hour. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**82 · weekend effect · BTC/USDT**

```text
Use available skills. A weekend effect strategy on BTC/USDT 1h candles for the past 6 months. Long at Friday 21:00 UTC, exit at Monday 00:00 UTC. Use 1% risk per trade with ATR(14)*3 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**83 · funding-timestamp run-up · SOL/USDT**

```text
Use available skills. A funding-timestamp run-up strategy on SOL/USDT 5m-15m candles for the past 6 months. Long: entry 30 minutes before each 8h funding timestamp (00:00, 08:00, 16:00 UTC), exit 15 minutes after it. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**84 · daily-open reversion · HYPE/USDT**

```text
Use available skills. A daily-open reversion strategy on HYPE/USDT 5m-15m-1h candles for the past 6 months. Short: entry when price is more than 1.5*ATR(14) above the 00:00 UTC daily open, at or after 12:00 UTC, exit at the daily open or at 23:55 UTC. Long: mirror below the daily open. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**85 · mid-day-lull mean-reversion · SUI/USDT**

```text
Use available skills. A mid-day-lull mean-reversion strategy on SUI/USDT 5m-15m candles for the past 6 months. Only trade 17:00-21:00 UTC. Long: entry when RSI(14) < 25, exit at session VWAP. Short: entry when RSI(14) > 75, exit at session VWAP. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```


---

## H. Regimenes, confluencias y derivados

**86 · ADX regime-switching · JUP/USDT**

```text
Use available skills. An ADX regime-switching strategy on JUP/USDT 5m-15m-1h candles for the past 6 months. When ADX(14) < 20 trade Bollinger (20,2) mean reversion (long below the lower band, exit at SMA(20)). When ADX(14) > 25 trade the EMA(20)/EMA(50) crossover trend. Stay flat in between. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**87 · volatility-percentile regime · SPCX/USDT**

```text
Use available skills. A volatility-percentile regime strategy on SPCX/USDT 5m-15m-1h candles for the past 6 months. Rank ATR(14)/close over the last 500 bars. Below the 30th percentile: long when RSI(14) < 30, exit when RSI(14) > 55. Above the 70th percentile: Donchian(20) breakout, exit at the 10-bar opposite extreme. Otherwise flat. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**88 · variance-ratio regime · NVDA/USDT**

```text
Use available skills. A variance-ratio regime strategy on NVDA/USDT 5m-15m-1h candles for the past 6 months. Compute the variance ratio VR(10) over a rolling 200 bars. VR < 0.9: RSI(14) mean reversion (long < 30, exit > 50). VR > 1.1: EMA(20)/EMA(50) trend. Otherwise flat. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**89 · BTC-regime-filtered trend · SOL/USDT**

```text
Use available skills. A BTC-regime-filtered trend strategy on SOL/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when EMA(20) crosses above EMA(50) and BTC/USDT close > BTC EMA(200) on the same timeframe, exit when EMA(20) crosses below EMA(50) or BTC falls below its EMA(200). Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**90 · multi-timeframe trend + pullback · HYPE/USDT**

```text
Use available skills. A multi-timeframe trend + pullback strategy on HYPE/USDT 5m-15m candles for the past 6 months. 1h filter: EMA(50) > EMA(200). On the 5m and 15m, long only: entry when RSI(14) crosses back above 40 after being below 35, exit when RSI(14) > 65. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**91 · multi-timeframe Donchian breakout · SUI/USDT**

```text
Use available skills. A multi-timeframe Donchian breakout strategy on SUI/USDT 15m candles for the past 6 months. Long: entry when a 15m close breaks above the 1h Donchian(20) high, exit when the 15m close < EMA(21). Short: mirror with the 1h Donchian(20) low. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**92 · RSI + MACD + EMA confluence · SOL/USDT**

```text
Use available skills. An RSI + MACD + EMA confluence strategy on SOL/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when RSI(14) > 50, the MACD histogram > 0 and close > EMA(50) have all become true within the last 3 bars, exit when at least two of the three conditions fail. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**93 · Bollinger + RSI + volume confluence · BTC/USDT**

```text
Use available skills. A Bollinger + RSI + volume confluence strategy on BTC/USDT 5m-15m-1h candles for the past 6 months. Long only: entry when close < the lower Bollinger Band (20,2), RSI(14) < 30 and volume > 1.5*SMA(volume,20), exit at the middle band. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**94 · funding-rate extreme fade · JUP/USDT**

```text
Use available skills. A funding-rate extreme fade strategy on JUP/USDT 15m-1h candles for the past 6 months. Using Binance funding-rate history: short when the funding rate is above its rolling 90th percentile (30 days), long when it is below its 10th percentile. Exit when funding returns to its median or after 24 hours. Use 1% risk per trade with ATR(14)*3 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**95 · open-interest divergence · SOL/USDT**

```text
Use available skills. An open-interest divergence strategy on SOL/USDT 15m-1h candles for the past 6 months. Short: entry when price makes a new 48-bar high while open interest falls over the same 48 bars. Long: entry when price makes a new 48-bar low while open interest falls. Exit after 12 bars or when close crosses EMA(20). Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**96 · long/short-ratio contrarian · ETH/USDT**

```text
Use available skills. A long/short-ratio contrarian strategy on ETH/USDT 15m-1h candles for the past 6 months. Using the Binance global long/short account ratio: short when the ratio is above its rolling 90th percentile (30 days), long when it is below its 10th percentile. Exit when it returns to its median. Use 1% risk per trade with ATR(14)*3 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**97 · liquidation-cascade bounce · HYPE/USDT**

```text
Use available skills. A liquidation-cascade bounce strategy on HYPE/USDT 5m-15m-1h candles for the past 6 months. Proxy for a liquidation cascade: a bar drops more than 3*ATR(14) with volume > 3*SMA(volume,20). Long: entry at that bar's close, exit at session VWAP or after 8 bars. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**98 · volatility-filtered Donchian trend · HYPE/USDT**

```text
Use available skills. A volatility-filtered Donchian trend strategy on HYPE/USDT 5m-15m-1h candles for the past 6 months. Long: entry when close > the 20-bar high, exit when close < the 10-bar low. Short: mirror. Skip new entries when the 24-bar realized volatility is above its 90th percentile. Use 1% risk per trade with ATR(14)*2 stop loss. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**99 · ETH/BTC ratio mean-reversion · ETH/BTC**

```text
Use available skills. An ETH/BTC ratio mean-reversion strategy on the ETH/BTC ratio (ETH/USDT divided by BTC/USDT) 5m-15m-1h candles for the past 6 months. Dollar-neutral. z = (ratio - SMA(100)) / stdev(ratio, 100). Long ETH / short BTC when z < -2, exit when z > 0. Short ETH / long BTC when z > 2, exit when z < 0. Use 1% risk per trade with an ATR(14)*2 stop loss measured on the ratio. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

**100 · relative-strength ratio trend · HYPE/BTC**

```text
Use available skills. A relative-strength ratio trend strategy on the HYPE/BTC ratio (HYPE/USDT divided by BTC/USDT) 5m-15m-1h candles for the past 6 months. Dollar-neutral. Long HYPE / short BTC when the HYPE/BTC ratio crosses above its EMA(50) and EMA(50) is rising, exit when the ratio crosses back below EMA(50). Short HYPE / long BTC on the mirror signal. Use 1% risk per trade with an ATR(14)*2 stop loss measured on the ratio. Show me equity curve, drawdown chart, and key metrics (Sharpe, max DD, win rate, profit factor).
```

---

## Cobertura por par

| Par | Prompts |
|---|---|
| SPCX/USDT | 12 |
| JUP/USDT | 12 |
| NVDA/USDT | 12 |
| HYPE/USDT | 13 |
| SUI/USDT | 12 |
| ETH/USDT | 12 |
| BTC/USDT | 13 |
| SOL/USDT | 12 |
| ETH/BTC (ratio) | 1 |
| HYPE/BTC (ratio) | 1 |
