# TOP 100 ESTRATEGIAS · ranking relativo por profit_factor neto

> **ADVERTENCIA DE HONESTIDAD (leer primero).** El corpus completo (2370 celdas; 295 estrategias distintas con n≥30 y métricas limpias) tiene **CERO supervivientes confirmados**: ninguna estrategia pasó la batería de validación completa (IS/OOS + bootstrap + concentración + costes + B&H). Este documento es un **ranking RELATIVO de las menos malas por PF neto in-sample**, NO una lista de estrategias rentables ni recomendaciones de trading. Un PF alto en IS con muestra pequeña, drawdown profundo u OOS fallido **no es invertible**. La cola del top-100 baja hasta PF≈0.92 (marginal). **Solo 68 de las 100 tienen PF neto >1** en su artefacto verificado; las 32 restantes pierden dinero a costes de la casa y se incluyen solo para completar el top-100 relativo. El ranking usa el **PF NETO del artefacto** (execution repo, 11 bps round-trip + funding real), NO el PF declarado/optimista del registry. Costes de la casa: 11 bps round-trip + funding real.

- **Criterio de ranking:** mejor celda (mayor PF neto) por estrategia distinta `(familia, nombre)`, con `n_trades ≥ 30` y métricas limpias (se excluyen celdas con explosión de compounding, p.ej. return ~1e58).
- **Fuente:** cada número proviene del artefacto verificado citado por `run_id` (RULE 0). PF/return/DD/win-rate del artefacto; OOS del campo `oos_*` o, en p100screen, de la celda OOS separada.
- **Cobertura OOS:** 58/100 tienen PF OOS disponible; de ellos, **26** con OOS PF>1 (el resto falla out-of-sample).
- **PF neto >1 en IS (artefacto verificado):** 68/100; **>1.2:** 29/100. Las 32 restantes tienen PF neto <1 (pierden a costes repo). Familias representadas: {'p100screen': 23, 'llm_pack': 18, 'pack20': 16, 'trend_hma_simple': 8, 'deepseek_ds1-ds5': 5, 'htffvg': 4, 'qs097': 3, 'grid_neutral': 2, 'trend_hma_ao_adx': 2, 'xs_factor': 2, 'deepseek_ds6-ds10': 2, 'pivot_box_breakout': 1, 'qs096': 1, 'smc_composite': 1, 'vwap_cvd_divergence': 1, 'smqe11': 1, 'prespecified_candidates': 1, 'trend_ema_crossover': 1, 'rsi_mean_reversion': 1, 'portfolio_momentum': 1, 'xs_relative_value': 1, 'strategies_101_150': 1, 'ffs': 1, 'sax_scalper': 1, 'scalp_wave': 1, 'scalp_ma_suite': 1}.

## Tabla resumen

| # | Estrategia | Familia | Símbolo | TF | PF neto | Ret % | n | WR % | MaxDD % | OOS PF | Veredicto |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Force Index trend | p100screen | BTCUSDT | 15m | 6.766 | 102.2 | 32 | 3.1 | -67.7 | 0.278 | SIN VEREDICTO |
| 2 | Parabolic SAR + EMA(100) | p100screen | SUIUSDT | 15m | 6.529 | 252.7 | 69 | 1.4 | -83.5 | 0.133 | SIN VEREDICTO |
| 3 | Botstrat: ruptura de caja de pivotes con confi | pivot_box_breakout | SPXUSDT | 1h | 3.079 | 38.7 | 31 | 0.6 | -4.2 | n/a | SIN VEREDICTO (15m = duplica… |
| 4 | Motor qs096: estrategia cuantitativa con filtr | qs096 | HYPEUSDT | 1h | 2.609 | 32.9 | 68 | 33.8 | -11.0 | 6.409 | SIN VEREDICTO |
| 5 | mid-day-lull mean-reversion | p100screen | HYPEUSDT | 1h | 2.607 | 28.1 | 127 | 57.5 | -3.0 | 3.100 | SIN VEREDICTO |
| 6 | fractal breakout | p100screen | BTCUSDT | 1h | 2.293 | 254.0 | 136 | 29.4 | -16.6 | 1.382 | SIN VEREDICTO |
| 7 | low-volume pullback | p100screen | ETHUSDT | 1h | 1.855 | 29.0 | 42 | 11.9 | -24.8 | 0.000 | SIN VEREDICTO |
| 8 | Compuesto SMC (smart money concepts): order bl | smc_composite | SUIUSDT | 1h | 1.828 | 16.1 | 49 | 46.9 | -5.1 | n/a | SUSPENDED (sin OOS posible) |
| 9 | Divergencia VWAP / CVD (cumulative volume delt | vwap_cvd_divergence | SUIUSDT | 1h | 1.788 | 16.7 | 49 | 0.5 | -5.1 | n/a | FRAGILE/SUSPENDED (PF ~1.02 … |
| 10 | weekend-gap fade | llm_pack | 1000PEPEUSDT | 1d | 1.765 | 53.6 | 34 | 64.7 | -29.2 | n/a | KILLED 0/48 |
| 11 | Motor smqe11: variante SMC cuantitativa. (moto | smqe11 | SUIUSDT | 1h | 1.661 | 15.1 | 53 | 43.4 | -5.5 | 1.192 | SIN VEREDICTO |
| 12 | atr vol breakout | pack20 | ETHUSDT | 1h | 1.585 | 882.1 | 388 | n/a | -25.1 | 1.625 | SIN VEREDICTO |
| 13 | XRP delta-neutral grid v1 (10k, 0.25x/lvl) | grid_neutral | XRPUSDT | 15m | 1.500 | 1598.2 | 5888 | 86.8 | -10.2 | n/a | KILLED (resolucion 1m: PF 0.… |
| 14 | Candidatos pre-especificados. (motor/candidato | prespecified_candidates | SOLUSDT | 1h | 1.477 | 2.5 | 33 | 51.5 | -1.8 | n/a | SIN VEREDICTO |
| 15 | double-bottom breakout | p100screen | ETHUSDT | 1h | 1.469 | 36.5 | 106 | 43.4 | -14.8 | 2.057 | SIN VEREDICTO |
| 16 | Tendencia con HMA (Hull MA) simple. | trend_hma_simple | HYPEUSDT | 1h | 1.378 | 58.6 | 113 | n/a | -27.1 | 2.365 | KILLED 0/11 (PF ex-cost 0.69… |
| 17 | linear-regression slope trend | p100screen | BTCUSDT | 1h | 1.336 | 73.5 | 366 | 34.4 | -22.6 | 0.788 | SIN VEREDICTO |
| 18 | order-block retest | p100screen | SOLUSDT | 1h | 1.332 | 56.4 | 263 | 42.2 | -24.7 | 0.790 | SIN VEREDICTO |
| 19 | liq fvg | pack20 | SOLUSDT | 15m | 1.332 | 29.7 | 61 | n/a | -13.8 | n/a | SIN VEREDICTO |
| 20 | Tendencia HMA + Awesome Oscillator + ADX. (mot | trend_hma_ao_adx | HYPEUSDT | 1h | 1.327 | 8.8 | 137 | 38.7 | -4.2 | n/a | KILLED (y sin funding en per… |
| 21 | DeepSeek DS1 (pack LLM DeepSeek) | deepseek_ds1-ds5 | SOLUSDT | 1h | 1.293 | 332.1 | 1753 | 32.2 | -19.1 | n/a | medido a 11 bps RT: +49.8% |
| 22 | impulse-bar continuation | p100screen | ETHUSDT | 1h | 1.275 | 264.6 | 622 | 24.1 | -40.9 | 1.014 | SIN VEREDICTO |
| 23 | Cruce de EMAs 9/21 con filtro de tendencia. (m | trend_ema_crossover | LABUSDT | 1h | 1.270 | 28.4 | 345 | 0.3 | -15.0 | 1.558 | KILLED 0/101 (ninguna celda … |
| 24 | triple EMA (8/21/55) pullback | p100screen | ETHUSDT | 1h | 1.262 | 319.0 | 942 | 27.9 | -29.8 | 1.035 | SIN VEREDICTO |
| 25 | variance-ratio regime | p100screen | BTCUSDT | 1h | 1.244 | -95.9 | 2433 | 44.6 | -96.5 | 1.656 | SIN VEREDICTO |
| 26 | Motor qs097: variante cuantitativa con filtros | qs097 | ETHUSDT | 1h | 1.234 | 26.0 | 306 | 31.4 | -16.0 | 1.234 | SIN VEREDICTO |
| 27 | Tendencia con HMA (Hull MA) simple. | trend_hma_simple | XRPUSDT | 1h | 1.226 | 19.6 | 104 | n/a | -15.9 | 1.280 | KILLED 0/11 (PF ex-cost 0.69… |
| 28 | rsimr | rsi_mean_reversion | SOLUSDC | 1h | 1.217 | 7.6 | 60 | 31.7 | -14.9 | n/a | NO PASA (mitades inestables) |
| 29 | Tendencia con HMA (Hull MA) simple. | trend_hma_simple | JUPUSDT | 1h | 1.211 | 28.9 | 111 | n/a | -25.2 | 1.626 | KILLED 0/11 (PF ex-cost 0.69… |
| 30 | Motor qs097: variante cuantitativa con filtros | qs097 | SUIUSDT | 1h | 1.192 | 26.1 | 295 | 33.9 | -16.2 | 1.134 | SIN VEREDICTO |
| 31 | ADX regime-switching | p100screen | SUIUSDT | 1h | 1.190 | 0.3 | 145 | 44.1 | -0.5 | 0.082 | SIN VEREDICTO |
| 32 | Motor qs097: variante cuantitativa con filtros | qs097 | HYPEUSDT | 1h | 1.181 | 10.6 | 162 | 32.7 | -12.0 | 1.355 | SIN VEREDICTO |
| 33 | DeepSeek DS3 (pack LLM DeepSeek) | deepseek_ds1-ds5 | SOLUSDT | 1h | 1.167 | 8321.2 | 284 | 31.3 | -67.3 | n/a | medido a 11 bps RT: +4150.8% |
| 34 | morning/evening star at Bollinger Bands | p100screen | BTCUSDT | 1h | 1.151 | 33.2 | 317 | 40.1 | -21.1 | 0.626 | SIN VEREDICTO |
| 35 | LOWVOL | xs_factor | LOWVOL | 1h | 1.151 | -45.9 | 65 | 52.3 | -84.4 | n/a | KILLED 0/3 (senal: 2/3 PF br… |
| 36 | Donchian-55 breakout | llm_pack | BTCUSDT | 4h | 1.148 | 12.4 | 53 | 43.4 | -23.7 | n/a | KILLED 0/48 |
| 37 | multi-timeframe trend + pullback | p100screen | BASKET6 | 1h | 1.143 | 39.6 | 124 | 56.5 | -38.9 | 1.336 | SIN VEREDICTO |
| 38 | TRIX(15) zero-cross | p100screen | BTCUSDT | 15m | 1.132 | 393.4 | 877 | 14.5 | -58.6 | 1.071 | SIN VEREDICTO |
| 39 | Pure Equal Weight Momentum | portfolio_momentum | PORTFOLIO | 1h | 1.119 | 1098.4 | 316 | 38.0 | -80.2 | n/a | KILLED (concentracion: top-5… |
| 40 | DeepSeek DS5 (pack LLM DeepSeek) | deepseek_ds1-ds5 | LINKUSDT | 1h | 1.111 | 55.0 | 1241 | 44.4 | -62.8 | n/a | medido a 11 bps RT: -90.4% |
| 41 | funding-timestamp run-up | p100screen | BASKET6 | 1h | 1.108 | 24.2 | 125 | 47.2 | -26.5 | 1.442 | SIN VEREDICTO |
| 42 | DeepSeek DS7 (pack LLM DeepSeek) | deepseek_ds6-ds10 | SPXUSDT | 1h | 1.108 | 45.0 | 296 | 67.2 | -46.0 | n/a | SIN VEREDICTO |
| 43 | D13 Fibonacci pullback | llm_pack | SUIUSDT | 30m | 1.099 | 13.1 | 113 | 50.4 | -19.0 | n/a | KILLED 0/46 |
| 44 | volume-climax reversal | p100screen | HYPEUSDT | 1h | 1.096 | 1.6 | 50 | 22.0 | -8.5 | 1.355 | SIN VEREDICTO |
| 45 | ATR-expansion breakout | llm_pack | SOLUSDT | 4h | 1.093 | 64.9 | 94 | 35.1 | -56.2 | n/a | KILLED 0/48 |
| 46 | NR7 breakout | p100screen | SOLUSDT | 1h | 1.091 | 131.1 | 1561 | 32.2 | -36.3 | 0.960 | SIN VEREDICTO |
| 47 | DeepSeek DS4 (pack LLM DeepSeek) | deepseek_ds1-ds5 | PORTFOLIO | 1h | 1.084 | 5.7 | 202 | 53.5 | -72.6 | n/a | SIN MEDIR A COSTOS REPO (pre… |
| 48 | Tendencia con HMA (Hull MA) simple. | trend_hma_simple | BTCUSDT | 1h | 1.083 | 5.1 | 112 | n/a | -19.2 | 1.769 | KILLED 0/11 (PF ex-cost 0.69… |
| 49 | vwap fade | pack20 | SOLUSDT | 15m | 1.077 | 405901.0 | 17850 | n/a | -76.3 | 1.079 | SIN VEREDICTO |
| 50 | Heikin-Ashi trend | llm_pack | SUIUSDT | 4h | 1.077 | 16.1 | 110 | 32.7 | -52.5 | n/a | KILLED 0/48 |
| 51 | squeeze rank breakout | pack20 | SOLUSDT | 1h | 1.076 | 90.0 | 684 | n/a | -33.7 | 1.065 | SIN VEREDICTO |
| 52 | D05 TTM squeeze release | llm_pack | SUIUSDT | 1h | 1.073 | 39.8 | 328 | 45.7 | -48.7 | n/a | KILLED 0/46 |
| 53 | D23 daily pivot bounce | llm_pack | SUIUSDT | 15m | 1.065 | 4.8 | 87 | 40.2 | -21.2 | n/a | KILLED 0/46 |
| 54 | ttm squeeze | pack20 | XRPUSDT | 1h | 1.048 | 488.3 | 3396 | n/a | -74.3 | 1.116 | SIN VEREDICTO |
| 55 | D04 Ichimoku cloud breakout | llm_pack | HYPEUSDT | 30m | 1.038 | 82.9 | 1512 | 44.6 | -58.7 | n/a | KILLED 0/46 |
| 56 | SKEW | xs_factor | SKEW | 1h | 1.034 | -28.5 | 209 | 54.5 | -100.2 | n/a | KILLED 0/3 (senal: 2/3 PF br… |
| 57 | VOLCOMP | xs_relative_value | VOLCOMP | 1h | 1.034 | -23.4 | 239 | 50.2 | -82.6 | n/a | KILLED 0/2 (ambas pierden en… |
| 58 | Renko trend strategy on SUIUSDT 5 minute sourc | strategies_101_150 | SUIUSDT | renko | 1.025 | 227.4 | 6089 | 45.6 | -75.9 | 0.811 | KILLED 0/37 (ruina por coste… |
| 59 | DeepSeek DS2 (pack LLM DeepSeek) | deepseek_ds1-ds5 | SUIUSDT | 1h | 1.024 | 10.5 | 725 | 41.7 | -37.2 | n/a | SIN MEDIR A COSTOS REPO (pre… |
| 60 | HTF FVG: fair value gaps en temporalidad super | htffvg | ETHUSDT | 15m | 1.022 | 12.3 | 630 | 39.7 | -34.4 | 0.927 | SIN VEREDICTO |
| 61 | HTF FVG: fair value gaps en temporalidad super | htffvg | HYPEUSDT | 15m | 1.014 | 2.1 | 204 | 37.2 | -15.6 | 0.775 | SIN VEREDICTO |
| 62 | rsi2 connors | pack20 | SOLUSDT | 1h | 1.014 | 64.3 | 2374 | n/a | -69.3 | 0.776 | SIN VEREDICTO |
| 63 | Tendencia con HMA (Hull MA) simple. | trend_hma_simple | SOLUSDT | 1h | 1.013 | 119.2 | 2011 | n/a | -78.9 | 0.924 | KILLED 0/11 (PF ex-cost 0.69… |
| 64 | ema pullback | pack20 | BTCUSDT | 1h | 1.012 | 13.5 | 1070 | n/a | -48.2 | 0.952 | SIN VEREDICTO |
| 65 | Tendencia con HMA (Hull MA) simple. | trend_hma_simple | ETHUSDT | 1h | 1.010 | 48.3 | 2298 | n/a | -69.3 | 0.983 | KILLED 0/11 (PF ex-cost 0.69… |
| 66 | order block | pack20 | XRPUSDT | 1h | 1.007 | 27.8 | 1062 | n/a | -81.1 | 0.907 | SIN VEREDICTO |
| 67 | HTF FVG: fair value gaps en temporalidad super | htffvg | JUPUSDT | 15m | 1.006 | 1.0 | 239 | 36.8 | -16.8 | 1.079 | SIN VEREDICTO |
| 68 | ffs | ffs | HYPEUSDT | 15m | 1.006 | -11.5 | 305 | 0.5 | -27.7 | n/a | KILLED (window-pick) |
| 69 | Hull MA trend | llm_pack | JUPUSDT | 4h | 0.999 | -0.4 | 140 | 34.3 | -65.3 | n/a | KILLED 0/48 |
| 70 | macd momentum | pack20 | SOLUSDT | 1h | 0.999 | -6.9 | 2554 | n/a | -85.6 | 0.976 | SIN VEREDICTO |
| 71 | break-of-structure pullback | p100screen | HYPEUSDT | 15m | 0.996 | -0.1 | 61 | 44.3 | -13.0 | 0.767 | SIN VEREDICTO |
| 72 | Bollinger %B + RSI mean-reversion | p100screen | HYPEUSDT | 1h | 0.994 | -0.9 | 127 | 59.1 | -8.8 | 0.777 | SIN VEREDICTO |
| 73 | logreg walkforward | pack20 | SOLUSDT | 1h | 0.993 | -64.9 | 4520 | n/a | -96.8 | 0.973 | SIN VEREDICTO |
| 74 | D14 Chandelier trend follower | llm_pack | JUPUSDT | 1h | 0.990 | -9.0 | 384 | 35.7 | -64.1 | n/a | KILLED 0/46 |
| 75 | D02 Donchian 55 breakout | llm_pack | ETHUSDT | 30m | 0.990 | -9.1 | 832 | 44.2 | -44.1 | n/a | KILLED 0/46 |
| 76 | daily-level bounce | llm_pack | SOLUSDT | 1h | 0.988 | -1.5 | 114 | 22.8 | -33.1 | n/a | KILLED 0/48 |
| 77 | HTF FVG: fair value gaps en temporalidad super | htffvg | SOLUSDT | 15m | 0.987 | -11.4 | 895 | 37.4 | -57.4 | 0.797 | SIN VEREDICTO |
| 78 | sax | sax_scalper | AVAXUSDT | 1h | 0.982 | -32.3 | 3120 | 0.4 | -55.5 | n/a | UNRUNNABLE (engine borrado; … |
| 79 | dual EMA 21/55 trend | llm_pack | ETHUSDT | 4h | 0.982 | -2.4 | 45 | 33.3 | -38.8 | n/a | KILLED 0/48 |
| 80 | donchian turtle | pack20 | ETHUSDT | 1h | 0.982 | -45.3 | 1559 | n/a | -83.4 | 0.906 | SIN VEREDICTO |
| 81 | DeepSeek DS8 (pack LLM DeepSeek) | deepseek_ds6-ds10 | PAIRS_BTC_ETH | 1h | 0.967 | -59.5 | 10590 | 42.8 | -77.4 | n/a | SIN VEREDICTO |
| 82 | pdh sweep | pack20 | ETHUSDT | 15m | 0.966 | -79.4 | 3135 | n/a | -92.0 | 0.849 | SIN VEREDICTO |
| 83 | time-series momentum | p100screen | BTCUSDT | 5m | 0.966 | -100.0 | 7900 | 20.0 | -100.0 | 0.603 | SIN VEREDICTO |
| 84 | gbm walkforward | pack20 | SOLUSDT | 1h | 0.965 | -100.0 | 9699 | n/a | -100.0 | 0.801 | SIN VEREDICTO |
| 85 | Tendencia con HMA (Hull MA) simple. | trend_hma_simple | SUIUSDT | 1h | 0.962 | -4.1 | 113 | n/a | -39.6 | 1.679 | KILLED 0/11 (PF ex-cost 0.69… |
| 86 | Parabolic SAR trend | llm_pack | SOLUSDT | 1h | 0.962 | -13.0 | 360 | 37.2 | -42.9 | n/a | KILLED 0/48 |
| 87 | Tendencia con HMA (Hull MA) simple. | trend_hma_simple | NVDAUSDT | 1h | 0.960 | -2.6 | 125 | n/a | -23.4 | 0.734 | KILLED 0/11 (PF ex-cost 0.69… |
| 88 | D07 previous-day high/low breakout | llm_pack | SPXUSDT | 1h | 0.957 | -42.9 | 477 | 45.9 | -73.3 | n/a | KILLED 0/46 |
| 89 | True Strength Index (25,13) | p100screen | SOLUSDT | 5m | 0.955 | -99.4 | 3322 | 19.1 | -99.8 | 0.560 | SIN VEREDICTO |
| 90 | hmaaoadx | trend_hma_ao_adx | SUIUSDT | 1h | 0.955 | -4.5 | 431 | 33.9 | -11.5 | n/a | SIN VEREDICTO |
| 91 | scalpwave | scalp_wave | SOLUSDT | 5m | 0.950 | -0.3 | 209 | 31.1 | -9.3 | n/a | KILLED (todas las celdas pie… |
| 92 | intraday trend-day pullback | llm_pack | SUIUSDT | 15m | 0.948 | -56.7 | 2313 | 23.1 | -88.2 | n/a | KILLED 0/48 |
| 93 | bb mean revert | pack20 | SOLUSDT | 1h | 0.942 | -98.9 | 2960 | n/a | -99.7 | 0.833 | SIN VEREDICTO |
| 94 | keltner break hma | scalp_ma_suite | SOLUSDT | 5m | 0.937 | -100.0 | 27882 | 40.6 | -100.0 | 0.657 | KILLED 0/120 (PF neto 0.32-0… |
| 95 | Chandelier breakout | llm_pack | ETHUSDT | 4h | 0.936 | -22.4 | 181 | 22.6 | -68.3 | n/a | KILLED 0/48 |
| 96 | xrpneutral1m | grid_neutral | XRPUSDT | 15m | 0.933 | -74.2 | 3018 | 77.5 | -81.5 | n/a | KILLED (el mismo libro resue… |
| 97 | RSI-2 snap-back | llm_pack | SUIUSDT | 1h | 0.933 | -7.9 | 134 | 67.2 | -29.6 | n/a | KILLED 0/48 |
| 98 | daily-open reversion | p100screen | BASKET6 | 1h | 0.932 | -76.9 | 2134 | 46.4 | -89.5 | 0.850 | SIN VEREDICTO |
| 99 | zscore fade | pack20 | SOLUSDT | 15m | 0.926 | -99.9 | 3957 | n/a | -100.0 | 0.803 | SIN VEREDICTO |
| 100 | adx di trend | pack20 | ETHUSDT | 1h | 0.922 | -81.8 | 1517 | n/a | -91.6 | 0.761 | SIN VEREDICTO |

## Fichas detalladas

### 1. Force Index trend

- **Familia:** `p100screen` — Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.
- **Nombre/celda:** `id=63` · **Símbolo:** BTCUSDT · **TF:** 15m
- **Descripción:** Force Index trend
- **PF neto (IS):** 6.7660 · **Return neto:** 102.24% · **n trades:** 32 · **Win rate:** 3.12% · **Max DD:** -67.73%
- **OOS:** PF 0.2782 · ret -25.05% · n 32
- **Buy & Hold (contexto):** 1039.89%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** -1.1767
- **Ventana:** 2019-09-08 → 2026-11-15
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `9d5e52a5ed84972f`

### 2. Parabolic SAR + EMA(100)

- **Familia:** `p100screen` — Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.
- **Nombre/celda:** `id=23` · **Símbolo:** SUIUSDT · **TF:** 15m
- **Descripción:** Parabolic SAR + EMA(100)
- **PF neto (IS):** 6.5289 · **Return neto:** 252.68% · **n trades:** 69 · **Win rate:** 1.45% · **Max DD:** -83.47%
- **OOS:** PF 0.1326 · ret -46.1% · n 68
- **Buy & Hold (contexto):** 144.35%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** -1.1044
- **Ventana:** 2023-05-03 → 2026-11-15
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `c097e05342b5ad9e`

### 3. Botstrat: ruptura de caja de pivotes con confirmación. (motor/candidato botstrat)

- **Familia:** `pivot_box_breakout` — Botstrat: ruptura de caja de pivotes con confirmación.
- **Nombre/celda:** `botstrat` · **Símbolo:** SPXUSDT · **TF:** 1h
- **Descripción:** Botstrat: ruptura de caja de pivotes con confirmación. (motor/candidato botstrat)
- **PF neto (IS):** 3.0793 · **Return neto:** 38.72% · **n trades:** 31 · **Win rate:** 0.55% · **Max DD:** -4.17%
- **OOS:** no disponible
- **Costes:** no registrado (casa: 11 bps RT) · **Funding cobrado:** no registrado
- **Ventana:** 2024-12-10 → 2026-09-26
- **Veredicto:** SIN VEREDICTO (15m = duplicado del 1h: engine hardcodea 1h)
- **Artefacto (run_id):** `f2aa1050b118e54f`

### 4. Motor qs096: estrategia cuantitativa con filtros de régimen y sizing por riesgo. (motor/candidato qs096)

- **Familia:** `qs096` — Motor qs096: estrategia cuantitativa con filtros de régimen y sizing por riesgo.
- **Nombre/celda:** `qs096` · **Símbolo:** HYPEUSDT · **TF:** 1h
- **Descripción:** Motor qs096: estrategia cuantitativa con filtros de régimen y sizing por riesgo. (motor/candidato qs096)
- **PF neto (IS):** 2.6092 · **Return neto:** 32.87% · **n trades:** 68 · **Win rate:** 33.82% · **Max DD:** -10.97%
- **OOS:** PF 6.4087 · ret 28.33% · n 23
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** 1.1066
- **Ventana:** 2025-05-30 → 2026-09-26
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `5cdb10b47424023f`

### 5. mid-day-lull mean-reversion

- **Familia:** `p100screen` — Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.
- **Nombre/celda:** `id=85` · **Símbolo:** HYPEUSDT · **TF:** 1h
- **Descripción:** mid-day-lull mean-reversion
- **PF neto (IS):** 2.6073 · **Return neto:** 28.10% · **n trades:** 127 · **Win rate:** 57.48% · **Max DD:** -3.04%
- **OOS:** PF 3.0997 · ret 428.78% · n 383
- **Buy & Hold (contexto):** 35.3%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** 0.0894
- **Ventana:** 2025-05-30 → 2026-11-06
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `b6ebfc6ec584042f`

### 6. fractal breakout

- **Familia:** `p100screen` — Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.
- **Nombre/celda:** `id=44` · **Símbolo:** BTCUSDT · **TF:** 1h
- **Descripción:** fractal breakout
- **PF neto (IS):** 2.2929 · **Return neto:** 253.96% · **n trades:** 136 · **Win rate:** 29.41% · **Max DD:** -16.55%
- **OOS:** PF 1.3816 · ret 5.94% · n 22
- **Buy & Hold (contexto):** 1039.89%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** 0.4225
- **Ventana:** 2019-09-08 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `ad95c2e4834a2eda`

### 7. low-volume pullback

- **Familia:** `p100screen` — Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.
- **Nombre/celda:** `id=64` · **Símbolo:** ETHUSDT · **TF:** 1h
- **Descripción:** low-volume pullback
- **PF neto (IS):** 1.8551 · **Return neto:** 29.00% · **n trades:** 42 · **Win rate:** 11.90% · **Max DD:** -24.75%
- **OOS:** PF 0.0 · ret -15.79% · n 15
- **Buy & Hold (contexto):** 2737.5%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** -0.0273
- **Ventana:** 2019-11-27 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `446487b2c7163b48`

### 8. Compuesto SMC (smart money concepts): order blocks, FVG, liquidez. (motor/candidato smqe)

- **Familia:** `smc_composite` — Compuesto SMC (smart money concepts): order blocks, FVG, liquidez.
- **Nombre/celda:** `smqe` · **Símbolo:** SUIUSDT · **TF:** 1h
- **Descripción:** Compuesto SMC (smart money concepts): order blocks, FVG, liquidez. (motor/candidato smqe)
- **PF neto (IS):** 1.8278 · **Return neto:** 16.06% · **n trades:** 49 · **Win rate:** 46.94% · **Max DD:** -5.08%
- **OOS:** no disponible
- **Buy & Hold (contexto):** -31.03%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no registrado
- **Ventana:** 2023-05-03 → 2026-10-24
- **Veredicto:** SUSPENDED (sin OOS posible)
- **Artefacto (run_id):** `3a6053c52d7639f5`

### 9. Divergencia VWAP / CVD (cumulative volume delta) con confirmación de flujo. (motor/candidato cvrmd)

- **Familia:** `vwap_cvd_divergence` — Divergencia VWAP / CVD (cumulative volume delta) con confirmación de flujo.
- **Nombre/celda:** `cvrmd` · **Símbolo:** SUIUSDT · **TF:** 1h
- **Descripción:** Divergencia VWAP / CVD (cumulative volume delta) con confirmación de flujo. (motor/candidato cvrmd)
- **PF neto (IS):** 1.7881 · **Return neto:** 16.74% · **n trades:** 49 · **Win rate:** 0.47% · **Max DD:** -5.07%
- **OOS:** no disponible
- **Costes:** no registrado (casa: 11 bps RT) · **Funding cobrado:** no registrado
- **Ventana:** 2023-05-03 → 2026-10-27
- **Veredicto:** FRAGILE/SUSPENDED (PF ~1.02 historia completa)
- **Artefacto (run_id):** `00c8c19179ea05ba`

### 10. weekend-gap fade

- **Familia:** `llm_pack` — Pack generado por LLM: rupturas, momentum, mean-reversion y filtros de volumen/flujo.
- **Nombre/celda:** `weekend-gap fade` · **Símbolo:** 1000PEPEUSDT · **TF:** 1d
- **Descripción:** weekend-gap fade
- **PF neto (IS):** 1.7647 · **Return neto:** 53.63% · **n trades:** 34 · **Win rate:** 64.71% · **Max DD:** -29.17%
- **OOS:** no disponible
- **Buy & Hold (contexto):** 9.28%
- **Costes:** 12.0 bps round-trip · **Funding cobrado:** no
- **Ventana:** 2026-01-01 → 2026-11-13
- **Veredicto:** KILLED 0/48
- **Artefacto (run_id):** `3586a215c95d6d87`

### 11. Motor smqe11: variante SMC cuantitativa. (motor/candidato smqe11)

- **Familia:** `smqe11` — Motor smqe11: variante SMC cuantitativa.
- **Nombre/celda:** `smqe11` · **Símbolo:** SUIUSDT · **TF:** 1h
- **Descripción:** Motor smqe11: variante SMC cuantitativa. (motor/candidato smqe11)
- **PF neto (IS):** 1.6608 · **Return neto:** 15.06% · **n trades:** 53 · **Win rate:** 43.40% · **Max DD:** -5.52%
- **OOS:** PF 1.1915 · ret 1.68% · n 18
- **Buy & Hold (contexto):** -35.56%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Ventana:** 2023-05-03 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `37ea1992569b77bb`

### 12. atr vol breakout

- **Familia:** `pack20` — Pack de 20 estrategias intradía (VWAP fade, ATR/vol breakout, TTM squeeze, etc.).
- **Nombre/celda:** `17_atr_vol_breakout` · **Símbolo:** ETHUSDT · **TF:** 1h
- **Descripción:** atr vol breakout
- **PF neto (IS):** 1.5855 · **Return neto:** 882.14% · **n trades:** 388 · **Win rate:** n/a · **Max DD:** -25.14%
- **OOS:** PF 1.625 · ret 159.11% · n 118
- **Buy & Hold (contexto):** 1456.39%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** 24.6209
- **Ventana:** 2019-11-27 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `3aaf8d34f49f1187`

### 13. XRP delta-neutral grid v1 (10k, 0.25x/lvl)

- **Familia:** `grid_neutral` — Grid delta-neutral.
- **Nombre/celda:** `XRP delta-neutral grid v1 (10k, 0.25x/lvl)` · **Símbolo:** XRPUSDT · **TF:** 15m
- **Descripción:** XRP delta-neutral grid v1 (10k, 0.25x/lvl)
- **PF neto (IS):** 1.4997 · **Return neto:** 1598.19% · **n trades:** 5888 · **Win rate:** 86.82% · **Max DD:** -10.18%
- **OOS:** no disponible
- **Buy & Hold (contexto):** 570.46%
- **Costes:** 14.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** 20.8978
- **Ventana:** 2020-01-06 → 2026-10-27
- **Veredicto:** KILLED (resolucion 1m: PF 0.93 vs 1.30 en el OOS 2023+; sonda _xrp_1m_resolution.py)
- **Artefacto (run_id):** `295c21687960fadd`

### 14. Candidatos pre-especificados. (motor/candidato cand7)

- **Familia:** `prespecified_candidates` — Candidatos pre-especificados.
- **Nombre/celda:** `cand7` · **Símbolo:** SOLUSDT · **TF:** 1h
- **Descripción:** Candidatos pre-especificados. (motor/candidato cand7)
- **PF neto (IS):** 1.4770 · **Return neto:** 2.48% · **n trades:** 33 · **Win rate:** 51.52% · **Max DD:** -1.80%
- **OOS:** no disponible
- **Buy & Hold (contexto):** -34.95%
- **Costes:** no registrado (casa: 11 bps RT) · **Funding cobrado:** no registrado
- **Ventana:** 2024-10-14 → 2026-10-26
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `ad79893b81cd0690`

### 15. double-bottom breakout

- **Familia:** `p100screen` — Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.
- **Nombre/celda:** `id=73` · **Símbolo:** ETHUSDT · **TF:** 1h
- **Descripción:** double-bottom breakout
- **PF neto (IS):** 1.4692 · **Return neto:** 36.46% · **n trades:** 106 · **Win rate:** 43.40% · **Max DD:** -14.81%
- **OOS:** PF 2.0567 · ret 8.6% · n 19
- **Buy & Hold (contexto):** 2737.5%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** -0.091
- **Ventana:** 2019-11-27 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `fe1f0f9405591a09`

### 16. Tendencia con HMA (Hull MA) simple.

- **Familia:** `trend_hma_simple` — Tendencia con HMA (Hull MA) simple.
- **Nombre/celda:** `card=HYPEUSDT` · **Símbolo:** HYPEUSDT · **TF:** 1h
- **Descripción:** Tendencia con HMA (Hull MA) simple.
- **PF neto (IS):** 1.3784 · **Return neto:** 58.64% · **n trades:** 113 · **Win rate:** n/a · **Max DD:** -27.05%
- **OOS:** PF 2.3653 · ret 34.97% · n 30
- **Buy & Hold (contexto):** 70.59%
- **Costes:** no registrado (casa: 11 bps RT) · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -40.7194
- **Ventana:** 2025-05-30 → 2026-11-06
- **Veredicto:** KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs)
- **Artefacto (run_id):** `0c7aebcfe691bdaa`

### 17. linear-regression slope trend

- **Familia:** `p100screen` — Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.
- **Nombre/celda:** `id=28` · **Símbolo:** BTCUSDT · **TF:** 1h
- **Descripción:** linear-regression slope trend
- **PF neto (IS):** 1.3359 · **Return neto:** 73.49% · **n trades:** 366 · **Win rate:** 34.43% · **Max DD:** -22.56%
- **OOS:** PF 0.7882 · ret -8.22% · n 63
- **Buy & Hold (contexto):** 1039.89%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** 0.0167
- **Ventana:** 2019-09-08 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `8483586c072d5cec`

### 18. order-block retest

- **Familia:** `p100screen` — Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.
- **Nombre/celda:** `id=68` · **Símbolo:** SOLUSDT · **TF:** 1h
- **Descripción:** order-block retest
- **PF neto (IS):** 1.3323 · **Return neto:** 56.39% · **n trades:** 263 · **Win rate:** 42.21% · **Max DD:** -24.68%
- **OOS:** PF 0.7898 · ret -6.77% · n 52
- **Buy & Hold (contexto):** 6096.16%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** 0.0069
- **Ventana:** 2020-09-14 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `3ed8943d9f8d69ab`

### 19. liq fvg

- **Familia:** `pack20` — Pack de 20 estrategias intradía (VWAP fade, ATR/vol breakout, TTM squeeze, etc.).
- **Nombre/celda:** `01_liq_fvg` · **Símbolo:** SOLUSDT · **TF:** 15m
- **Descripción:** liq fvg
- **PF neto (IS):** 1.3319 · **Return neto:** 29.67% · **n trades:** 61 · **Win rate:** n/a · **Max DD:** -13.77%
- **OOS:** ret 0.0% · n 0
- **Buy & Hold (contexto):** 2705.14%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -39.4879
- **Ventana:** 2020-09-14 → 2026-11-07
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `280e88028bd44e31`

### 20. Tendencia HMA + Awesome Oscillator + ADX. (motor/candidato fingrad)

- **Familia:** `trend_hma_ao_adx` — Tendencia HMA + Awesome Oscillator + ADX.
- **Nombre/celda:** `fingrad` · **Símbolo:** HYPEUSDT · **TF:** 1h
- **Descripción:** Tendencia HMA + Awesome Oscillator + ADX. (motor/candidato fingrad)
- **PF neto (IS):** 1.3272 · **Return neto:** 8.84% · **n trades:** 137 · **Win rate:** 38.69% · **Max DD:** -4.21%
- **OOS:** no disponible
- **Buy & Hold (contexto):** 176.41%
- **Costes:** 10.0 bps round-trip · **Funding cobrado:** no
- **Ventana:** 2025-05-30 → 2026-09-26
- **Veredicto:** KILLED (y sin funding en perps: SUI 17.3%->1.6% con funding)
- **Artefacto (run_id):** `2288aa01825d36ca`

### 21. DeepSeek DS1 (pack LLM DeepSeek)

- **Familia:** `deepseek_ds1-ds5` — Pack DeepSeek DS1-DS5 generado por LLM.
- **Nombre/celda:** `ds1` · **Símbolo:** SOLUSDT · **TF:** 1h
- **Descripción:** DeepSeek DS1 (pack LLM DeepSeek)
- **PF neto (IS):** 1.2933 · **Return neto:** 332.12% · **n trades:** 1753 · **Win rate:** 32.17% · **Max DD:** -19.14%
- **OOS:** no disponible
- **Costes:** no registrado (casa: 11 bps RT) · **Funding cobrado:** no registrado
- **Ventana:** 2020-09-14 → 2026-10-17
- **Veredicto:** medido a 11 bps RT: +49.8%
- **Artefacto (run_id):** `bfe50d8919258f06`

### 22. impulse-bar continuation

- **Familia:** `p100screen` — Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.
- **Nombre/celda:** `id=45` · **Símbolo:** ETHUSDT · **TF:** 1h
- **Descripción:** impulse-bar continuation
- **PF neto (IS):** 1.2748 · **Return neto:** 264.63% · **n trades:** 622 · **Win rate:** 24.12% · **Max DD:** -40.94%
- **OOS:** PF 1.0137 · ret 0.78% · n 124
- **Buy & Hold (contexto):** 2737.5%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** 0.0127
- **Ventana:** 2019-11-27 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `df3d84f2bad4b17b`

### 23. Cruce de EMAs 9/21 con filtro de tendencia. (motor/candidato ema921)

- **Familia:** `trend_ema_crossover` — Cruce de EMAs 9/21 con filtro de tendencia.
- **Nombre/celda:** `ema921` · **Símbolo:** LABUSDT · **TF:** 1h
- **Descripción:** Cruce de EMAs 9/21 con filtro de tendencia. (motor/candidato ema921)
- **PF neto (IS):** 1.2701 · **Return neto:** 28.44% · **n trades:** 345 · **Win rate:** 0.30% · **Max DD:** -14.99%
- **OOS:** PF 1.5581 · ret 13.21% · n 88
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** -1.9495
- **Ventana:** 2025-10-17 → 2026-10-09
- **Veredicto:** KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra)
- **Artefacto (run_id):** `dfab81a68433a1fd`

### 24. triple EMA (8/21/55) pullback

- **Familia:** `p100screen` — Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.
- **Nombre/celda:** `id=26` · **Símbolo:** ETHUSDT · **TF:** 1h
- **Descripción:** triple EMA (8/21/55) pullback
- **PF neto (IS):** 1.2622 · **Return neto:** 319.04% · **n trades:** 942 · **Win rate:** 27.92% · **Max DD:** -29.79%
- **OOS:** PF 1.0348 · ret 3.15% · n 183
- **Buy & Hold (contexto):** 2737.5%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** 0.0471
- **Ventana:** 2019-11-27 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `2f8f3ce69d850de1`

### 25. variance-ratio regime

- **Familia:** `p100screen` — Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.
- **Nombre/celda:** `id=88` · **Símbolo:** BTCUSDT · **TF:** 1h
- **Descripción:** variance-ratio regime
- **PF neto (IS):** 1.2442 · **Return neto:** -95.90% · **n trades:** 2433 · **Win rate:** 44.64% · **Max DD:** -96.47%
- **OOS:** PF 1.656 · ret -13.13% · n 368
- **Buy & Hold (contexto):** 2737.5%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** -0.0077
- **Ventana:** 2019-11-27 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `5636a3a9936646fc`

### 26. Motor qs097: variante cuantitativa con filtros de régimen.

- **Familia:** `qs097` — Motor qs097: variante cuantitativa con filtros de régimen.
- **Nombre/celda:** `card=ETHUSDT` · **Símbolo:** ETHUSDT · **TF:** 1h
- **Descripción:** Motor qs097: variante cuantitativa con filtros de régimen.
- **PF neto (IS):** 1.2336 · **Return neto:** 25.99% · **n trades:** 306 · **Win rate:** 31.37% · **Max DD:** -16.03%
- **OOS:** PF 1.2336 · ret 25.99% · n 306
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -7.1405
- **Ventana:** 2019-09-08 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `50b60069f86c09ec`

### 27. Tendencia con HMA (Hull MA) simple.

- **Familia:** `trend_hma_simple` — Tendencia con HMA (Hull MA) simple.
- **Nombre/celda:** `card=XRPUSDT` · **Símbolo:** XRPUSDT · **TF:** 1h
- **Descripción:** Tendencia con HMA (Hull MA) simple.
- **PF neto (IS):** 1.2265 · **Return neto:** 19.63% · **n trades:** 104 · **Win rate:** n/a · **Max DD:** -15.87%
- **OOS:** PF 1.2804 · ret 5.02% · n 34
- **Buy & Hold (contexto):** -23.45%
- **Costes:** no registrado (casa: 11 bps RT) · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -33.7528
- **Ventana:** 2020-01-06 → 2026-11-02
- **Veredicto:** KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs)
- **Artefacto (run_id):** `25f2aeb618b8c6ee`

### 28. rsimr

- **Familia:** `rsi_mean_reversion` — Reversión a la media con RSI.
- **Nombre/celda:** `rsimr` · **Símbolo:** SOLUSDC · **TF:** 1h
- **Descripción:** rsimr
- **PF neto (IS):** 1.2172 · **Return neto:** 7.56% · **n trades:** 60 · **Win rate:** 31.67% · **Max DD:** -14.88%
- **OOS:** no disponible
- **Buy & Hold (contexto):** 15.2%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no registrado
- **Ventana:** 2026-04-01 → 2026-10-29
- **Veredicto:** NO PASA (mitades inestables)
- **Artefacto (run_id):** `dcf66a3eb320e7a7`

### 29. Tendencia con HMA (Hull MA) simple.

- **Familia:** `trend_hma_simple` — Tendencia con HMA (Hull MA) simple.
- **Nombre/celda:** `card=JUPUSDT` · **Símbolo:** JUPUSDT · **TF:** 1h
- **Descripción:** Tendencia con HMA (Hull MA) simple.
- **PF neto (IS):** 1.2110 · **Return neto:** 28.86% · **n trades:** 111 · **Win rate:** n/a · **Max DD:** -25.23%
- **OOS:** PF 1.626 · ret 25.65% · n 36
- **Buy & Hold (contexto):** 1.43%
- **Costes:** no registrado (casa: 11 bps RT) · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -40.3737
- **Ventana:** 2024-01-31 → 2026-10-29
- **Veredicto:** KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs)
- **Artefacto (run_id):** `2411025b023d0bbf`

### 30. Motor qs097: variante cuantitativa con filtros de régimen.

- **Familia:** `qs097` — Motor qs097: variante cuantitativa con filtros de régimen.
- **Nombre/celda:** `card=SUIUSDT` · **Símbolo:** SUIUSDT · **TF:** 1h
- **Descripción:** Motor qs097: variante cuantitativa con filtros de régimen.
- **PF neto (IS):** 1.1921 · **Return neto:** 26.08% · **n trades:** 295 · **Win rate:** 33.90% · **Max DD:** -16.23%
- **OOS:** PF 1.1342 · ret 12.06% · n 210
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -12.1402
- **Ventana:** 2019-09-08 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `0be0854a2f52fe2e`

### 31. ADX regime-switching

- **Familia:** `p100screen` — Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.
- **Nombre/celda:** `id=86` · **Símbolo:** SUIUSDT · **TF:** 1h
- **Descripción:** ADX regime-switching
- **PF neto (IS):** 1.1896 · **Return neto:** 0.33% · **n trades:** 145 · **Win rate:** 44.14% · **Max DD:** -0.52%
- **OOS:** PF 0.0818 · ret -4.46% · n 106
- **Buy & Hold (contexto):** 137.32%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** -0.0056
- **Ventana:** 2023-05-03 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `c74cd2f8ba7cbc03`

### 32. Motor qs097: variante cuantitativa con filtros de régimen.

- **Familia:** `qs097` — Motor qs097: variante cuantitativa con filtros de régimen.
- **Nombre/celda:** `card=HYPEUSDT` · **Símbolo:** HYPEUSDT · **TF:** 1h
- **Descripción:** Motor qs097: variante cuantitativa con filtros de régimen.
- **PF neto (IS):** 1.1805 · **Return neto:** 10.55% · **n trades:** 162 · **Win rate:** 32.72% · **Max DD:** -12.03%
- **OOS:** PF 1.3549 · ret 7.43% · n 55
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -16.5086
- **Ventana:** 2019-09-08 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `6f5ec1d20c40a815`

### 33. DeepSeek DS3 (pack LLM DeepSeek)

- **Familia:** `deepseek_ds1-ds5` — Pack DeepSeek DS1-DS5 generado por LLM.
- **Nombre/celda:** `ds3` · **Símbolo:** SOLUSDT · **TF:** 1h
- **Descripción:** DeepSeek DS3 (pack LLM DeepSeek)
- **PF neto (IS):** 1.1665 · **Return neto:** 8321.20% · **n trades:** 284 · **Win rate:** 31.34% · **Max DD:** -67.29%
- **OOS:** no disponible
- **Costes:** no registrado (casa: 11 bps RT) · **Funding cobrado:** no registrado
- **Ventana:** 2020-09-14 → 2026-10-17
- **Veredicto:** medido a 11 bps RT: +4150.8%
- **Artefacto (run_id):** `55cbf103e822ae30`

### 34. morning/evening star at Bollinger Bands

- **Familia:** `p100screen` — Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.
- **Nombre/celda:** `id=72` · **Símbolo:** BTCUSDT · **TF:** 1h
- **Descripción:** morning/evening star at Bollinger Bands
- **PF neto (IS):** 1.1511 · **Return neto:** 33.21% · **n trades:** 317 · **Win rate:** 40.06% · **Max DD:** -21.06%
- **OOS:** PF 0.6265 · ret -13.19% · n 53
- **Buy & Hold (contexto):** 1039.89%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** -0.0332
- **Ventana:** 2019-09-08 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `521fd0a0a8dcfd03`

### 35. LOWVOL

- **Familia:** `xs_factor` — Factor cross-sectional.
- **Nombre/celda:** `LOWVOL` · **Símbolo:** LOWVOL · **TF:** 1h
- **Descripción:** LOWVOL
- **PF neto (IS):** 1.1505 · **Return neto:** -45.94% · **n trades:** 65 · **Win rate:** 52.31% · **Max DD:** -84.41%
- **OOS:** ret -41.29%
- **Buy & Hold (contexto):** 1177.32%
- **Costes:** no registrado (casa: 11 bps RT) · **Funding cobrado:** no
- **Ventana:** 2020-01-31 → 2026-11-02
- **Veredicto:** KILLED 0/3 (senal: 2/3 PF bruto < 1; concentracion y OOS; vecindario sin rescate)
- **Artefacto (run_id):** `5c5cbbe6443fb391`

### 36. Donchian-55 breakout

- **Familia:** `llm_pack` — Pack generado por LLM: rupturas, momentum, mean-reversion y filtros de volumen/flujo.
- **Nombre/celda:** `Donchian-55 breakout` · **Símbolo:** BTCUSDT · **TF:** 4h
- **Descripción:** Donchian-55 breakout
- **PF neto (IS):** 1.1480 · **Return neto:** 12.41% · **n trades:** 53 · **Win rate:** 43.40% · **Max DD:** -23.73%
- **OOS:** no disponible
- **Buy & Hold (contexto):** 24.3%
- **Costes:** 12.0 bps round-trip · **Funding cobrado:** sí
- **Ventana:** 2024-10-14 → 2026-10-14
- **Veredicto:** KILLED 0/48
- **Artefacto (run_id):** `245680f774f9975e`

### 37. multi-timeframe trend + pullback

- **Familia:** `p100screen` — Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.
- **Nombre/celda:** `id=90` · **Símbolo:** BASKET6 · **TF:** 1h
- **Descripción:** multi-timeframe trend + pullback
- **PF neto (IS):** 1.1430 · **Return neto:** 39.59% · **n trades:** 124 · **Win rate:** 56.45% · **Max DD:** -38.87%
- **OOS:** PF 1.3358 · ret 20.07% · n 53
- **Buy & Hold (contexto):** 1039.89%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -0.0043
- **Ventana:** 2019-09-08 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `f7fe875c09b5c786`

### 38. TRIX(15) zero-cross

- **Familia:** `p100screen` — Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.
- **Nombre/celda:** `id=52` · **Símbolo:** BTCUSDT · **TF:** 15m
- **Descripción:** TRIX(15) zero-cross
- **PF neto (IS):** 1.1320 · **Return neto:** 393.40% · **n trades:** 877 · **Win rate:** 14.48% · **Max DD:** -58.59%
- **OOS:** PF 1.0705 · ret 13.9% · n 179
- **Buy & Hold (contexto):** 1039.89%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** 0.0139
- **Ventana:** 2019-09-08 → 2026-11-15
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `9e93753caa755c27`

### 39. Pure Equal Weight Momentum

- **Familia:** `portfolio_momentum` — Momentum de portfolio.
- **Nombre/celda:** `Pure Equal Weight Momentum` · **Símbolo:** PORTFOLIO · **TF:** 1h
- **Descripción:** Pure Equal Weight Momentum
- **PF neto (IS):** 1.1192 · **Return neto:** 1098.37% · **n trades:** 316 · **Win rate:** 37.97% · **Max DD:** -80.21%
- **OOS:** no disponible
- **Costes:** no registrado (casa: 11 bps RT) · **Funding cobrado:** no registrado
- **Bootstrap CI lower (mean R):** -10056.2648
- **Ventana:** 2020-09-23 → 2026-10-24
- **Veredicto:** KILLED (concentracion: top-5 > 100% del PnL)
- **Artefacto (run_id):** `00d2a8549e6c898d`

### 40. DeepSeek DS5 (pack LLM DeepSeek)

- **Familia:** `deepseek_ds1-ds5` — Pack DeepSeek DS1-DS5 generado por LLM.
- **Nombre/celda:** `ds5` · **Símbolo:** LINKUSDT · **TF:** 1h
- **Descripción:** DeepSeek DS5 (pack LLM DeepSeek)
- **PF neto (IS):** 1.1108 · **Return neto:** 55.00% · **n trades:** 1241 · **Win rate:** 44.40% · **Max DD:** -62.82%
- **OOS:** no disponible
- **Costes:** no registrado (casa: 11 bps RT) · **Funding cobrado:** no registrado
- **Ventana:** 2020-01-17 → 2026-10-17
- **Veredicto:** medido a 11 bps RT: -90.4%
- **Artefacto (run_id):** `365bef751f370f6c`

### 41. funding-timestamp run-up

- **Familia:** `p100screen` — Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.
- **Nombre/celda:** `id=83` · **Símbolo:** BASKET6 · **TF:** 1h
- **Descripción:** funding-timestamp run-up
- **PF neto (IS):** 1.1080 · **Return neto:** 24.24% · **n trades:** 125 · **Win rate:** 47.20% · **Max DD:** -26.54%
- **OOS:** PF 1.4419 · ret 37.48% · n 53
- **Buy & Hold (contexto):** 1039.89%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -0.0024
- **Ventana:** 2019-09-08 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `8fb60fa563d679ae`

### 42. DeepSeek DS7 (pack LLM DeepSeek)

- **Familia:** `deepseek_ds6-ds10` — Pack DeepSeek DS6-DS10 generado por LLM.
- **Nombre/celda:** `ds7` · **Símbolo:** SPXUSDT · **TF:** 1h
- **Descripción:** DeepSeek DS7 (pack LLM DeepSeek)
- **PF neto (IS):** 1.1078 · **Return neto:** 44.97% · **n trades:** 296 · **Win rate:** 67.23% · **Max DD:** -45.98%
- **OOS:** no disponible
- **Costes:** no registrado (casa: 11 bps RT) · **Funding cobrado:** no registrado
- **Ventana:** 2024-12-10 → 2026-09-26
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `b898dfed4e6f2395`

### 43. D13 Fibonacci pullback

- **Familia:** `llm_pack` — Pack generado por LLM: rupturas, momentum, mean-reversion y filtros de volumen/flujo.
- **Nombre/celda:** `D13 Fibonacci pullback` · **Símbolo:** SUIUSDT · **TF:** 30m
- **Descripción:** D13 Fibonacci pullback
- **PF neto (IS):** 1.0993 · **Return neto:** 13.11% · **n trades:** 113 · **Win rate:** 50.44% · **Max DD:** -18.99%
- **OOS:** no disponible
- **Buy & Hold (contexto):** -54.12%
- **Costes:** 14.0 bps round-trip · **Funding cobrado:** sí
- **Ventana:** 2024-10-14 → 2026-10-14
- **Veredicto:** KILLED 0/46
- **Artefacto (run_id):** `0010a45b99243376`

### 44. volume-climax reversal

- **Familia:** `p100screen` — Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.
- **Nombre/celda:** `id=60` · **Símbolo:** HYPEUSDT · **TF:** 1h
- **Descripción:** volume-climax reversal
- **PF neto (IS):** 1.0964 · **Return neto:** 1.59% · **n trades:** 50 · **Win rate:** 22.00% · **Max DD:** -8.49%
- **OOS:** PF 1.3555 · ret 23.54% · n 141
- **Buy & Hold (contexto):** 35.3%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** -0.1636
- **Ventana:** 2025-05-30 → 2026-11-06
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `78649953dd61f9b1`

### 45. ATR-expansion breakout

- **Familia:** `llm_pack` — Pack generado por LLM: rupturas, momentum, mean-reversion y filtros de volumen/flujo.
- **Nombre/celda:** `ATR-expansion breakout` · **Símbolo:** SOLUSDT · **TF:** 4h
- **Descripción:** ATR-expansion breakout
- **PF neto (IS):** 1.0927 · **Return neto:** 64.91% · **n trades:** 94 · **Win rate:** 35.11% · **Max DD:** -56.22%
- **OOS:** no disponible
- **Buy & Hold (contexto):** -34.95%
- **Costes:** 12.0 bps round-trip · **Funding cobrado:** sí
- **Ventana:** 2024-10-14 → 2026-10-26
- **Veredicto:** KILLED 0/48
- **Artefacto (run_id):** `a7393f703e992b6b`

### 46. NR7 breakout

- **Familia:** `p100screen` — Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.
- **Nombre/celda:** `id=34` · **Símbolo:** SOLUSDT · **TF:** 1h
- **Descripción:** NR7 breakout
- **PF neto (IS):** 1.0910 · **Return neto:** 131.06% · **n trades:** 1561 · **Win rate:** 32.16% · **Max DD:** -36.26%
- **OOS:** PF 0.9596 · ret -8.46% · n 335
- **Buy & Hold (contexto):** 6096.16%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** -0.0234
- **Ventana:** 2020-09-14 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `91efe2579f12890a`

### 47. DeepSeek DS4 (pack LLM DeepSeek)

- **Familia:** `deepseek_ds1-ds5` — Pack DeepSeek DS1-DS5 generado por LLM.
- **Nombre/celda:** `ds4` · **Símbolo:** PORTFOLIO · **TF:** 1h
- **Descripción:** DeepSeek DS4 (pack LLM DeepSeek)
- **PF neto (IS):** 1.0839 · **Return neto:** 5.68% · **n trades:** 202 · **Win rate:** 53.47% · **Max DD:** -72.61%
- **OOS:** no disponible
- **Costes:** no registrado (casa: 11 bps RT) · **Funding cobrado:** no registrado
- **Ventana:** 2020-01-31 → 2026-10-17
- **Veredicto:** SIN MEDIR A COSTOS REPO (preset author = costo cero)
- **Artefacto (run_id):** `6a8b1adbc1447e81`

### 48. Tendencia con HMA (Hull MA) simple.

- **Familia:** `trend_hma_simple` — Tendencia con HMA (Hull MA) simple.
- **Nombre/celda:** `card=BTCUSDT` · **Símbolo:** BTCUSDT · **TF:** 1h
- **Descripción:** Tendencia con HMA (Hull MA) simple.
- **PF neto (IS):** 1.0831 · **Return neto:** 5.10% · **n trades:** 112 · **Win rate:** n/a · **Max DD:** -19.16%
- **OOS:** PF 1.7694 · ret 10.3% · n 36
- **Buy & Hold (contexto):** -7.87%
- **Costes:** no registrado (casa: 11 bps RT) · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -22.6406
- **Ventana:** 2019-09-08 → 2026-11-02
- **Veredicto:** KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs)
- **Artefacto (run_id):** `6246c97f560abc0b`

### 49. vwap fade

- **Familia:** `pack20` — Pack de 20 estrategias intradía (VWAP fade, ATR/vol breakout, TTM squeeze, etc.).
- **Nombre/celda:** `13_vwap_fade` · **Símbolo:** SOLUSDT · **TF:** 15m
- **Descripción:** vwap fade
- **PF neto (IS):** 1.0775 · **Return neto:** 405901.02% · **n trades:** 17850 · **Win rate:** n/a · **Max DD:** -76.34%
- **OOS:** PF 1.0792 · ret 457.04% · n 5597
- **Buy & Hold (contexto):** 2705.14%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** 3.5845
- **Ventana:** 2020-09-14 → 2026-11-07
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `44a23ab194b621be`

### 50. Heikin-Ashi trend

- **Familia:** `llm_pack` — Pack generado por LLM: rupturas, momentum, mean-reversion y filtros de volumen/flujo.
- **Nombre/celda:** `Heikin-Ashi trend` · **Símbolo:** SUIUSDT · **TF:** 4h
- **Descripción:** Heikin-Ashi trend
- **PF neto (IS):** 1.0774 · **Return neto:** 16.11% · **n trades:** 110 · **Win rate:** 32.73% · **Max DD:** -52.53%
- **OOS:** no disponible
- **Buy & Hold (contexto):** -59.08%
- **Costes:** 20.0 bps round-trip · **Funding cobrado:** sí
- **Ventana:** 2024-10-14 → 2026-10-26
- **Veredicto:** KILLED 0/48
- **Artefacto (run_id):** `8321c904af22c0ad`

### 51. squeeze rank breakout

- **Familia:** `pack20` — Pack de 20 estrategias intradía (VWAP fade, ATR/vol breakout, TTM squeeze, etc.).
- **Nombre/celda:** `15_squeeze_rank_breakout` · **Símbolo:** SOLUSDT · **TF:** 1h
- **Descripción:** squeeze rank breakout
- **PF neto (IS):** 1.0759 · **Return neto:** 89.98% · **n trades:** 684 · **Win rate:** n/a · **Max DD:** -33.71%
- **OOS:** PF 1.065 · ret 14.64% · n 204
- **Buy & Hold (contexto):** 2821.69%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -8.462
- **Ventana:** 2020-09-14 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `bd9100c8bd70d366`

### 52. D05 TTM squeeze release

- **Familia:** `llm_pack` — Pack generado por LLM: rupturas, momentum, mean-reversion y filtros de volumen/flujo.
- **Nombre/celda:** `D05 TTM squeeze release` · **Símbolo:** SUIUSDT · **TF:** 1h
- **Descripción:** D05 TTM squeeze release
- **PF neto (IS):** 1.0729 · **Return neto:** 39.80% · **n trades:** 328 · **Win rate:** 45.73% · **Max DD:** -48.67%
- **OOS:** no disponible
- **Buy & Hold (contexto):** -59.08%
- **Costes:** 14.0 bps round-trip · **Funding cobrado:** sí
- **Ventana:** 2024-10-14 → 2026-10-26
- **Veredicto:** KILLED 0/46
- **Artefacto (run_id):** `6b6ba8b42fce4efe`

### 53. D23 daily pivot bounce

- **Familia:** `llm_pack` — Pack generado por LLM: rupturas, momentum, mean-reversion y filtros de volumen/flujo.
- **Nombre/celda:** `D23 daily pivot bounce` · **Símbolo:** SUIUSDT · **TF:** 15m
- **Descripción:** D23 daily pivot bounce
- **PF neto (IS):** 1.0652 · **Return neto:** 4.75% · **n trades:** 87 · **Win rate:** 40.23% · **Max DD:** -21.24%
- **OOS:** no disponible
- **Buy & Hold (contexto):** -54.12%
- **Costes:** 14.0 bps round-trip · **Funding cobrado:** sí
- **Ventana:** 2024-10-14 → 2026-10-14
- **Veredicto:** KILLED 0/46
- **Artefacto (run_id):** `1791e653a68abc30`

### 54. ttm squeeze

- **Familia:** `pack20` — Pack de 20 estrategias intradía (VWAP fade, ATR/vol breakout, TTM squeeze, etc.).
- **Nombre/celda:** `16_ttm_squeeze` · **Símbolo:** XRPUSDT · **TF:** 1h
- **Descripción:** ttm squeeze
- **PF neto (IS):** 1.0483 · **Return neto:** 488.30% · **n trades:** 3396 · **Win rate:** n/a · **Max DD:** -74.33%
- **OOS:** PF 1.1163 · ret 142.18% · n 874
- **Buy & Hold (contexto):** 533.76%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -0.9676
- **Ventana:** 2020-01-06 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `ea426bb3fb821132`

### 55. D04 Ichimoku cloud breakout

- **Familia:** `llm_pack` — Pack generado por LLM: rupturas, momentum, mean-reversion y filtros de volumen/flujo.
- **Nombre/celda:** `D04 Ichimoku cloud breakout` · **Símbolo:** HYPEUSDT · **TF:** 30m
- **Descripción:** D04 Ichimoku cloud breakout
- **PF neto (IS):** 1.0379 · **Return neto:** 82.93% · **n trades:** 1512 · **Win rate:** 44.58% · **Max DD:** -58.73%
- **OOS:** no disponible
- **Buy & Hold (contexto):** 135.56%
- **Costes:** 14.0 bps round-trip · **Funding cobrado:** sí
- **Ventana:** 2025-05-30 → 2026-10-15
- **Veredicto:** KILLED 0/46
- **Artefacto (run_id):** `a40038eeccf8b222`

### 56. SKEW

- **Familia:** `xs_factor` — Factor cross-sectional.
- **Nombre/celda:** `SKEW` · **Símbolo:** SKEW · **TF:** 1h
- **Descripción:** SKEW
- **PF neto (IS):** 1.0338 · **Return neto:** -28.54% · **n trades:** 209 · **Win rate:** 54.55% · **Max DD:** -100.25%
- **OOS:** ret 71.1%
- **Buy & Hold (contexto):** 1310.07%
- **Costes:** no registrado (casa: 11 bps RT) · **Funding cobrado:** no
- **Ventana:** 2020-01-31 → 2026-11-02
- **Veredicto:** KILLED 0/3 (senal: 2/3 PF bruto < 1; concentracion y OOS; vecindario sin rescate)
- **Artefacto (run_id):** `08fa3e92ed79df46`

### 57. VOLCOMP

- **Familia:** `xs_relative_value` — Valor relativo cross-sectional.
- **Nombre/celda:** `VOLCOMP` · **Símbolo:** VOLCOMP · **TF:** 1h
- **Descripción:** VOLCOMP
- **PF neto (IS):** 1.0336 · **Return neto:** -23.37% · **n trades:** 239 · **Win rate:** 50.21% · **Max DD:** -82.56%
- **OOS:** ret -55.97%
- **Buy & Hold (contexto):** 1149.51%
- **Costes:** no registrado (casa: 11 bps RT) · **Funding cobrado:** no
- **Ventana:** 2020-01-31 → 2026-11-02
- **Veredicto:** KILLED 0/2 (ambas pierden en bruto; vecindario sin rescate)
- **Artefacto (run_id):** `bbd4ed10c0aa6f43`

### 58. Renko trend strategy on SUIUSDT 5 minute source data. Use Renko bricks sized at 0.5 ATR. Enter after two same-color bricks following a reversal. SL 2 bricks, TP 4 bricks. No trailing stop.

- **Familia:** `strategies_101_150` — Pack 101-150: estructura de mercado, trampas de liquidez, sesiones, flujo y valor relativo.
- **Nombre/celda:** `id=134` · **Símbolo:** SUIUSDT · **TF:** renko
- **Descripción:** Renko trend strategy on SUIUSDT 5 minute source data. Use Renko bricks sized at 0.5 ATR. Enter after two same-color bricks following a reversal. SL 2 bricks, TP 4 bricks. No trailing stop.
- **PF neto (IS):** 1.0249 · **Return neto:** 227.38% · **n trades:** 6089 · **Win rate:** 45.59% · **Max DD:** -75.93%
- **OOS:** PF 0.811 · ret -67.19% · n 2357
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** 0.0069
- **Ventana:** 2024-10-15 → 2026-10-15
- **Veredicto:** KILLED 0/37 (ruina por costes en intradia; ninguna celda pasa la bateria estandar)
- **Artefacto (run_id):** `1d6f571e60870ccb`

### 59. DeepSeek DS2 (pack LLM DeepSeek)

- **Familia:** `deepseek_ds1-ds5` — Pack DeepSeek DS1-DS5 generado por LLM.
- **Nombre/celda:** `ds2` · **Símbolo:** SUIUSDT · **TF:** 1h
- **Descripción:** DeepSeek DS2 (pack LLM DeepSeek)
- **PF neto (IS):** 1.0239 · **Return neto:** 10.54% · **n trades:** 725 · **Win rate:** 41.66% · **Max DD:** -37.22%
- **OOS:** no disponible
- **Costes:** no registrado (casa: 11 bps RT) · **Funding cobrado:** no registrado
- **Ventana:** 2023-05-03 → 2026-10-17
- **Veredicto:** SIN MEDIR A COSTOS REPO (preset author = costo cero)
- **Artefacto (run_id):** `dd870096ddf9dd22`

### 60. HTF FVG: fair value gaps en temporalidad superior.

- **Familia:** `htffvg` — HTF FVG: fair value gaps en temporalidad superior.
- **Nombre/celda:** `card=ETHUSDT` · **Símbolo:** ETHUSDT · **TF:** 15m
- **Descripción:** HTF FVG: fair value gaps en temporalidad superior.
- **PF neto (IS):** 1.0222 · **Return neto:** 12.31% · **n trades:** 630 · **Win rate:** 39.68% · **Max DD:** -34.36%
- **OOS:** PF 0.9269 · ret -8.88% · n 174
- **Costes:** 5.82451597630965 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -12.4427
- **Ventana:** 2019-11-27 → 2026-11-10
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `96cffffa95971b6c`

### 61. HTF FVG: fair value gaps en temporalidad superior.

- **Familia:** `htffvg` — HTF FVG: fair value gaps en temporalidad superior.
- **Nombre/celda:** `card=HYPEUSDT` · **Símbolo:** HYPEUSDT · **TF:** 15m
- **Descripción:** HTF FVG: fair value gaps en temporalidad superior.
- **PF neto (IS):** 1.0144 · **Return neto:** 2.12% · **n trades:** 204 · **Win rate:** 37.25% · **Max DD:** -15.59%
- **OOS:** PF 0.7746 · ret -9.84% · n 59
- **Costes:** 8.953708438950482 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -19.4584
- **Ventana:** 2025-05-30 → 2026-11-10
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `f955da402137a517`

### 62. rsi2 connors

- **Familia:** `pack20` — Pack de 20 estrategias intradía (VWAP fade, ATR/vol breakout, TTM squeeze, etc.).
- **Nombre/celda:** `10_rsi2_connors` · **Símbolo:** SOLUSDT · **TF:** 1h
- **Descripción:** rsi2 connors
- **PF neto (IS):** 1.0137 · **Return neto:** 64.32% · **n trades:** 2374 · **Win rate:** n/a · **Max DD:** -69.29%
- **OOS:** PF 0.7758 · ret -62.94% · n 716
- **Buy & Hold (contexto):** 2821.69%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -4.3187
- **Ventana:** 2020-09-14 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `aa6c9d276a9a0c03`

### 63. Tendencia con HMA (Hull MA) simple.

- **Familia:** `trend_hma_simple` — Tendencia con HMA (Hull MA) simple.
- **Nombre/celda:** `card=SOLUSDT` · **Símbolo:** SOLUSDT · **TF:** 1h
- **Descripción:** Tendencia con HMA (Hull MA) simple.
- **PF neto (IS):** 1.0128 · **Return neto:** 119.15% · **n trades:** 2011 · **Win rate:** n/a · **Max DD:** -78.93%
- **OOS:** PF 0.9243 · ret -164.47% · n 600
- **Buy & Hold (contexto):** 2677.28%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** -59.9174
- **Ventana:** 2020-09-14 → 2026-11-02
- **Veredicto:** KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs)
- **Artefacto (run_id):** `4b3728cfb4f054c3`

### 64. ema pullback

- **Familia:** `pack20` — Pack de 20 estrategias intradía (VWAP fade, ATR/vol breakout, TTM squeeze, etc.).
- **Nombre/celda:** `06_ema_pullback` · **Símbolo:** BTCUSDT · **TF:** 1h
- **Descripción:** ema pullback
- **PF neto (IS):** 1.0119 · **Return neto:** 13.51% · **n trades:** 1070 · **Win rate:** n/a · **Max DD:** -48.23%
- **OOS:** PF 0.9522 · ret -10.33% · n 330
- **Buy & Hold (contexto):** 674.83%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -9.5839
- **Ventana:** 2019-09-08 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `5e9fca474627e82d`

### 65. Tendencia con HMA (Hull MA) simple.

- **Familia:** `trend_hma_simple` — Tendencia con HMA (Hull MA) simple.
- **Nombre/celda:** `card=ETHUSDT` · **Símbolo:** ETHUSDT · **TF:** 1h
- **Descripción:** Tendencia con HMA (Hull MA) simple.
- **PF neto (IS):** 1.0103 · **Return neto:** 48.33% · **n trades:** 2298 · **Win rate:** n/a · **Max DD:** -69.28%
- **OOS:** PF 0.9829 · ret -20.57% · n 707
- **Buy & Hold (contexto):** 1456.39%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** -23.9752
- **Ventana:** 2019-11-27 → 2026-11-02
- **Veredicto:** KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs)
- **Artefacto (run_id):** `13330a919c10aa61`

### 66. order block

- **Familia:** `pack20` — Pack de 20 estrategias intradía (VWAP fade, ATR/vol breakout, TTM squeeze, etc.).
- **Nombre/celda:** `02_order_block` · **Símbolo:** XRPUSDT · **TF:** 1h
- **Descripción:** order block
- **PF neto (IS):** 1.0067 · **Return neto:** 27.77% · **n trades:** 1062 · **Win rate:** n/a · **Max DD:** -81.13%
- **OOS:** PF 0.9068 · ret -53.61% · n 332
- **Buy & Hold (contexto):** 533.76%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -16.2541
- **Ventana:** 2020-01-06 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `b40c0d432705fc83`

### 67. HTF FVG: fair value gaps en temporalidad superior.

- **Familia:** `htffvg` — HTF FVG: fair value gaps en temporalidad superior.
- **Nombre/celda:** `card=JUPUSDT` · **Símbolo:** JUPUSDT · **TF:** 15m
- **Descripción:** HTF FVG: fair value gaps en temporalidad superior.
- **PF neto (IS):** 1.0055 · **Return neto:** 0.97% · **n trades:** 239 · **Win rate:** 36.82% · **Max DD:** -16.84%
- **OOS:** PF 1.0795 · ret 4.2% · n 72
- **Costes:** 5.90072495684144 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -18.8362
- **Ventana:** 2024-01-31 → 2026-11-06
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `d7cf9f2832cbb19c`

### 68. ffs

- **Familia:** `ffs` — Motor ffs: estrategia de flujo/ruptura.
- **Nombre/celda:** `ffs` · **Símbolo:** HYPEUSDT · **TF:** 15m
- **Descripción:** ffs
- **PF neto (IS):** 1.0055 · **Return neto:** -11.46% · **n trades:** 305 · **Win rate:** 0.53% · **Max DD:** -27.69%
- **OOS:** no disponible
- **Costes:** no registrado (casa: 11 bps RT) · **Funding cobrado:** no registrado
- **Ventana:** 2025-05-30 → 2026-10-14
- **Veredicto:** KILLED (window-pick)
- **Artefacto (run_id):** `7a0dcdd7a146e941`

### 69. Hull MA trend

- **Familia:** `llm_pack` — Pack generado por LLM: rupturas, momentum, mean-reversion y filtros de volumen/flujo.
- **Nombre/celda:** `Hull MA trend` · **Símbolo:** JUPUSDT · **TF:** 4h
- **Descripción:** Hull MA trend
- **PF neto (IS):** 0.9992 · **Return neto:** -0.40% · **n trades:** 140 · **Win rate:** 34.29% · **Max DD:** -65.32%
- **OOS:** no disponible
- **Buy & Hold (contexto):** -65.35%
- **Costes:** 20.0 bps round-trip · **Funding cobrado:** sí
- **Ventana:** 2024-10-15 → 2026-10-15
- **Veredicto:** KILLED 0/48
- **Artefacto (run_id):** `0f725fc3a817c61a`

### 70. macd momentum

- **Familia:** `pack20` — Pack de 20 estrategias intradía (VWAP fade, ATR/vol breakout, TTM squeeze, etc.).
- **Nombre/celda:** `09_macd_momentum` · **Símbolo:** SOLUSDT · **TF:** 1h
- **Descripción:** macd momentum
- **PF neto (IS):** 0.9988 · **Return neto:** -6.86% · **n trades:** 2554 · **Win rate:** n/a · **Max DD:** -85.57%
- **OOS:** PF 0.9761 · ret -21.86% · n 777
- **Buy & Hold (contexto):** 2821.69%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -8.2996
- **Ventana:** 2020-09-14 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `757d37d023ee71b4`

### 71. break-of-structure pullback

- **Familia:** `p100screen` — Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.
- **Nombre/celda:** `id=69` · **Símbolo:** HYPEUSDT · **TF:** 15m
- **Descripción:** break-of-structure pullback
- **PF neto (IS):** 0.9962 · **Return neto:** -0.13% · **n trades:** 61 · **Win rate:** 44.26% · **Max DD:** -12.98%
- **OOS:** PF 0.7675 · ret -21.7% · n 151
- **Buy & Hold (contexto):** 34.79%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** -0.5033
- **Ventana:** 2025-05-30 → 2026-11-15
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `ee29eaea4d603b96`

### 72. Bollinger %B + RSI mean-reversion

- **Familia:** `p100screen` — Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.
- **Nombre/celda:** `id=4` · **Símbolo:** HYPEUSDT · **TF:** 1h
- **Descripción:** Bollinger %B + RSI mean-reversion
- **PF neto (IS):** 0.9943 · **Return neto:** -0.86% · **n trades:** 127 · **Win rate:** 59.06% · **Max DD:** -8.81%
- **OOS:** PF 0.7775 · ret -33.98% · n 386
- **Buy & Hold (contexto):** 35.3%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** -0.1395
- **Ventana:** 2025-05-30 → 2026-11-06
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `04b25ff8a046a387`

### 73. logreg walkforward

- **Familia:** `pack20` — Pack de 20 estrategias intradía (VWAP fade, ATR/vol breakout, TTM squeeze, etc.).
- **Nombre/celda:** `18_logreg_walkforward` · **Símbolo:** SOLUSDT · **TF:** 1h
- **Descripción:** logreg walkforward
- **PF neto (IS):** 0.9929 · **Return neto:** -64.90% · **n trades:** 4520 · **Win rate:** n/a · **Max DD:** -96.75%
- **OOS:** PF 0.9725 · ret -23.4% · n 1376
- **Buy & Hold (contexto):** 2821.69%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -6.6388
- **Ventana:** 2020-09-14 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `2977c4fd05502f38`

### 74. D14 Chandelier trend follower

- **Familia:** `llm_pack` — Pack generado por LLM: rupturas, momentum, mean-reversion y filtros de volumen/flujo.
- **Nombre/celda:** `D14 Chandelier trend follower` · **Símbolo:** JUPUSDT · **TF:** 1h
- **Descripción:** D14 Chandelier trend follower
- **PF neto (IS):** 0.9904 · **Return neto:** -8.99% · **n trades:** 384 · **Win rate:** 35.68% · **Max DD:** -64.08%
- **OOS:** no disponible
- **Buy & Hold (contexto):** -65.35%
- **Costes:** 14.0 bps round-trip · **Funding cobrado:** sí
- **Ventana:** 2024-10-15 → 2026-10-15
- **Veredicto:** KILLED 0/46
- **Artefacto (run_id):** `454bdfe185339e88`

### 75. D02 Donchian 55 breakout

- **Familia:** `llm_pack` — Pack generado por LLM: rupturas, momentum, mean-reversion y filtros de volumen/flujo.
- **Nombre/celda:** `D02 Donchian 55 breakout` · **Símbolo:** ETHUSDT · **TF:** 30m
- **Descripción:** D02 Donchian 55 breakout
- **PF neto (IS):** 0.9902 · **Return neto:** -9.10% · **n trades:** 832 · **Win rate:** 44.23% · **Max DD:** -44.07%
- **OOS:** no disponible
- **Buy & Hold (contexto):** -7.52%
- **Costes:** 14.0 bps round-trip · **Funding cobrado:** sí
- **Ventana:** 2024-10-14 → 2026-10-14
- **Veredicto:** KILLED 0/46
- **Artefacto (run_id):** `579192b36954b8a7`

### 76. daily-level bounce

- **Familia:** `llm_pack` — Pack generado por LLM: rupturas, momentum, mean-reversion y filtros de volumen/flujo.
- **Nombre/celda:** `daily-level bounce` · **Símbolo:** SOLUSDT · **TF:** 1h
- **Descripción:** daily-level bounce
- **PF neto (IS):** 0.9878 · **Return neto:** -1.51% · **n trades:** 114 · **Win rate:** 22.81% · **Max DD:** -33.09%
- **OOS:** no disponible
- **Buy & Hold (contexto):** -34.95%
- **Costes:** 12.0 bps round-trip · **Funding cobrado:** sí
- **Ventana:** 2024-10-14 → 2026-10-26
- **Veredicto:** KILLED 0/48
- **Artefacto (run_id):** `93e523512bba996c`

### 77. HTF FVG: fair value gaps en temporalidad superior.

- **Familia:** `htffvg` — HTF FVG: fair value gaps en temporalidad superior.
- **Nombre/celda:** `card=SOLUSDT` · **Símbolo:** SOLUSDT · **TF:** 15m
- **Descripción:** HTF FVG: fair value gaps en temporalidad superior.
- **PF neto (IS):** 0.9868 · **Return neto:** -11.44% · **n trades:** 895 · **Win rate:** 37.43% · **Max DD:** -57.40%
- **OOS:** PF 0.7966 · ret -32.22% · n 259
- **Costes:** 8.942757434271602 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -14.6969
- **Ventana:** 2020-09-14 → 2026-11-10
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `45ffecd2da31bb02`

### 78. sax

- **Familia:** `sax_scalper` — Scalper SAX (symbolic aggregate approximation).
- **Nombre/celda:** `sax` · **Símbolo:** AVAXUSDT · **TF:** 1h
- **Descripción:** sax
- **PF neto (IS):** 0.9822 · **Return neto:** -32.31% · **n trades:** 3120 · **Win rate:** 0.37% · **Max DD:** -55.46%
- **OOS:** no disponible
- **Costes:** no registrado (casa: 11 bps RT) · **Funding cobrado:** no registrado
- **Ventana:** 2020-09-23 → 2026-10-10
- **Veredicto:** UNRUNNABLE (engine borrado; 49 artefactos huerfanos)
- **Artefacto (run_id):** `4e09efe2c3d70396`

### 79. dual EMA 21/55 trend

- **Familia:** `llm_pack` — Pack generado por LLM: rupturas, momentum, mean-reversion y filtros de volumen/flujo.
- **Nombre/celda:** `dual EMA 21/55 trend` · **Símbolo:** ETHUSDT · **TF:** 4h
- **Descripción:** dual EMA 21/55 trend
- **PF neto (IS):** 0.9819 · **Return neto:** -2.39% · **n trades:** 45 · **Win rate:** 33.33% · **Max DD:** -38.76%
- **OOS:** no disponible
- **Buy & Hold (contexto):** -7.52%
- **Costes:** 12.0 bps round-trip · **Funding cobrado:** sí
- **Ventana:** 2024-10-14 → 2026-10-14
- **Veredicto:** KILLED 0/48
- **Artefacto (run_id):** `2741a7d46b9482f1`

### 80. donchian turtle

- **Familia:** `pack20` — Pack de 20 estrategias intradía (VWAP fade, ATR/vol breakout, TTM squeeze, etc.).
- **Nombre/celda:** `08_donchian_turtle` · **Símbolo:** ETHUSDT · **TF:** 1h
- **Descripción:** donchian turtle
- **PF neto (IS):** 0.9815 · **Return neto:** -45.31% · **n trades:** 1559 · **Win rate:** n/a · **Max DD:** -83.44%
- **OOS:** PF 0.9061 · ret -34.84% · n 483
- **Buy & Hold (contexto):** 1456.39%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -15.353
- **Ventana:** 2019-11-27 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `c864a85d90a4bd41`

### 81. DeepSeek DS8 (pack LLM DeepSeek)

- **Familia:** `deepseek_ds6-ds10` — Pack DeepSeek DS6-DS10 generado por LLM.
- **Nombre/celda:** `ds8` · **Símbolo:** PAIRS_BTC_ETH · **TF:** 1h
- **Descripción:** DeepSeek DS8 (pack LLM DeepSeek)
- **PF neto (IS):** 0.9671 · **Return neto:** -59.47% · **n trades:** 10590 · **Win rate:** 42.80% · **Max DD:** -77.39%
- **OOS:** no disponible
- **Costes:** no registrado (casa: 11 bps RT) · **Funding cobrado:** no registrado
- **Ventana:** 2019-09-08 → 2026-10-17
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `bccaa612918c561b`

### 82. pdh sweep

- **Familia:** `pack20` — Pack de 20 estrategias intradía (VWAP fade, ATR/vol breakout, TTM squeeze, etc.).
- **Nombre/celda:** `04_pdh_sweep` · **Símbolo:** ETHUSDT · **TF:** 15m
- **Descripción:** pdh sweep
- **PF neto (IS):** 0.9659 · **Return neto:** -79.44% · **n trades:** 3135 · **Win rate:** n/a · **Max DD:** -92.00%
- **OOS:** PF 0.8486 · ret -66.89% · n 984
- **Buy & Hold (contexto):** 1433.57%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -11.2196
- **Ventana:** 2019-11-27 → 2026-11-07
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `0d42eef92b4d8e32`

### 83. time-series momentum

- **Familia:** `p100screen` — Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.
- **Nombre/celda:** `id=47` · **Símbolo:** BTCUSDT · **TF:** 5m
- **Descripción:** time-series momentum
- **PF neto (IS):** 0.9656 · **Return neto:** -100.00% · **n trades:** 7900 · **Win rate:** 20.03% · **Max DD:** -100.00%
- **OOS:** PF 0.6031 · ret -99.98% · n 1627
- **Buy & Hold (contexto):** 1039.89%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** -0.2546
- **Ventana:** 2019-09-08 → 2026-11-06
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `a490502c2746732e`

### 84. gbm walkforward

- **Familia:** `pack20` — Pack de 20 estrategias intradía (VWAP fade, ATR/vol breakout, TTM squeeze, etc.).
- **Nombre/celda:** `20_gbm_walkforward` · **Símbolo:** SOLUSDT · **TF:** 1h
- **Descripción:** gbm walkforward
- **PF neto (IS):** 0.9646 · **Return neto:** -100.00% · **n trades:** 9699 · **Win rate:** n/a · **Max DD:** -100.00%
- **OOS:** PF 0.8007 · ret -97.86% · n 2973
- **Buy & Hold (contexto):** 2821.69%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -13.5963
- **Ventana:** 2020-09-14 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `4fd912b238550e7d`

### 85. Tendencia con HMA (Hull MA) simple.

- **Familia:** `trend_hma_simple` — Tendencia con HMA (Hull MA) simple.
- **Nombre/celda:** `card=SUIUSDT` · **Símbolo:** SUIUSDT · **TF:** 1h
- **Descripción:** Tendencia con HMA (Hull MA) simple.
- **PF neto (IS):** 0.9622 · **Return neto:** -4.07% · **n trades:** 113 · **Win rate:** n/a · **Max DD:** -39.63%
- **OOS:** PF 1.6794 · ret 12.32% · n 35
- **Buy & Hold (contexto):** -31.43%
- **Costes:** no registrado (casa: 11 bps RT) · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -52.4514
- **Ventana:** 2023-05-03 → 2026-11-02
- **Veredicto:** KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs)
- **Artefacto (run_id):** `58bbf6c26905b33c`

### 86. Parabolic SAR trend

- **Familia:** `llm_pack` — Pack generado por LLM: rupturas, momentum, mean-reversion y filtros de volumen/flujo.
- **Nombre/celda:** `Parabolic SAR trend` · **Símbolo:** SOLUSDT · **TF:** 1h
- **Descripción:** Parabolic SAR trend
- **PF neto (IS):** 0.9619 · **Return neto:** -12.98% · **n trades:** 360 · **Win rate:** 37.22% · **Max DD:** -42.93%
- **OOS:** no disponible
- **Buy & Hold (contexto):** -34.95%
- **Costes:** 12.0 bps round-trip · **Funding cobrado:** sí
- **Ventana:** 2024-10-14 → 2026-10-26
- **Veredicto:** KILLED 0/48
- **Artefacto (run_id):** `6e2c370ad9a43c21`

### 87. Tendencia con HMA (Hull MA) simple.

- **Familia:** `trend_hma_simple` — Tendencia con HMA (Hull MA) simple.
- **Nombre/celda:** `card=NVDAUSDT` · **Símbolo:** NVDAUSDT · **TF:** 1h
- **Descripción:** Tendencia con HMA (Hull MA) simple.
- **PF neto (IS):** 0.9598 · **Return neto:** -2.62% · **n trades:** 125 · **Win rate:** n/a · **Max DD:** -23.44%
- **OOS:** PF 0.7342 · ret -4.58% · n 35
- **Buy & Hold (contexto):** 13.76%
- **Costes:** no registrado (casa: 11 bps RT) · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -27.7917
- **Ventana:** 2026-03-26 → 2026-11-02
- **Veredicto:** KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs)
- **Artefacto (run_id):** `992a0531585148e0`

### 88. D07 previous-day high/low breakout

- **Familia:** `llm_pack` — Pack generado por LLM: rupturas, momentum, mean-reversion y filtros de volumen/flujo.
- **Nombre/celda:** `D07 previous-day high/low breakout` · **Símbolo:** SPXUSDT · **TF:** 1h
- **Descripción:** D07 previous-day high/low breakout
- **PF neto (IS):** 0.9571 · **Return neto:** -42.85% · **n trades:** 477 · **Win rate:** 45.91% · **Max DD:** -73.28%
- **OOS:** no disponible
- **Buy & Hold (contexto):** -22.98%
- **Costes:** 14.0 bps round-trip · **Funding cobrado:** sí
- **Ventana:** 2024-12-10 → 2026-09-26
- **Veredicto:** KILLED 0/46
- **Artefacto (run_id):** `009abf69321e2e2c`

### 89. True Strength Index (25,13)

- **Familia:** `p100screen` — Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.
- **Nombre/celda:** `id=53` · **Símbolo:** SOLUSDT · **TF:** 5m
- **Descripción:** True Strength Index (25,13)
- **PF neto (IS):** 0.9553 · **Return neto:** -99.42% · **n trades:** 3322 · **Win rate:** 19.11% · **Max DD:** -99.85%
- **OOS:** PF 0.5603 · ret -95.4% · n 711
- **Buy & Hold (contexto):** 6212.6%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** -0.2152
- **Ventana:** 2020-09-14 → 2026-11-06
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `1e2e095201dcee87`

### 90. hmaaoadx

- **Familia:** `trend_hma_ao_adx` — Tendencia HMA + Awesome Oscillator + ADX.
- **Nombre/celda:** `hmaaoadx` · **Símbolo:** SUIUSDT · **TF:** 1h
- **Descripción:** hmaaoadx
- **PF neto (IS):** 0.9549 · **Return neto:** -4.51% · **n trades:** 431 · **Win rate:** 33.87% · **Max DD:** -11.47%
- **OOS:** no disponible
- **Costes:** no registrado (casa: 11 bps RT) · **Funding cobrado:** no registrado
- **Ventana:** 2023-05-03 → 2026-10-24
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `b618c6e7552052d2`

### 91. scalpwave

- **Familia:** `scalp_wave` — scalp_wave
- **Nombre/celda:** `scalpwave` · **Símbolo:** SOLUSDT · **TF:** 5m
- **Descripción:** scalpwave
- **PF neto (IS):** 0.9497 · **Return neto:** -0.32% · **n trades:** 209 · **Win rate:** 31.10% · **Max DD:** -9.34%
- **OOS:** no disponible
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no registrado
- **Ventana:** 2026-08-18 → 2026-09-17
- **Veredicto:** KILLED (todas las celdas pierden a coste repo Y a coste cero: la senal es antipredictiva)
- **Artefacto (run_id):** `4c4cf4db8894f510`

### 92. intraday trend-day pullback

- **Familia:** `llm_pack` — Pack generado por LLM: rupturas, momentum, mean-reversion y filtros de volumen/flujo.
- **Nombre/celda:** `intraday trend-day pullback` · **Símbolo:** SUIUSDT · **TF:** 15m
- **Descripción:** intraday trend-day pullback
- **PF neto (IS):** 0.9481 · **Return neto:** -56.71% · **n trades:** 2313 · **Win rate:** 23.13% · **Max DD:** -88.16%
- **OOS:** no disponible
- **Buy & Hold (contexto):** -54.12%
- **Costes:** 20.0 bps round-trip · **Funding cobrado:** sí
- **Ventana:** 2024-10-14 → 2026-10-14
- **Veredicto:** KILLED 0/48
- **Artefacto (run_id):** `961a4618185a5149`

### 93. bb mean revert

- **Familia:** `pack20` — Pack de 20 estrategias intradía (VWAP fade, ATR/vol breakout, TTM squeeze, etc.).
- **Nombre/celda:** `11_bb_mean_revert` · **Símbolo:** SOLUSDT · **TF:** 1h
- **Descripción:** bb mean revert
- **PF neto (IS):** 0.9418 · **Return neto:** -98.89% · **n trades:** 2960 · **Win rate:** n/a · **Max DD:** -99.71%
- **OOS:** PF 0.8333 · ret -67.17% · n 869
- **Buy & Hold (contexto):** 2821.69%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -21.1005
- **Ventana:** 2020-09-14 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `ee47f05c4e8ea3e4`

### 94. keltner break hma

- **Familia:** `scalp_ma_suite` — Suite de 20 scalps de medias móviles (EMA/TEMA/HMA/ZLEMA/KAMA, ribbons, VWAP, Supertrend, MACD, squeeze).
- **Nombre/celda:** `16_keltner_break_hma` · **Símbolo:** SOLUSDT · **TF:** 5m
- **Descripción:** keltner break hma
- **PF neto (IS):** 0.9372 · **Return neto:** -100.00% · **n trades:** 27882 · **Win rate:** 40.58% · **Max DD:** -100.00%
- **OOS:** PF 0.6572 · ret -100.0% · n 7510
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** -0.7283
- **Ventana:** 2020-09-14 → 2026-11-06
- **Veredicto:** KILLED 0/120 (PF neto 0.32-0.94, net -100% a -4.5%, OOS PF<1 salvo 1 celda degenerada inf/16 trades; zero-cost PF max 1.1195 < gate 1.2: sin filo bruto sobre el gate + ruina por turnover a 11 bps; paridad de senal 100/100 vs fuente adjunta, self-test 40/40, 120 artefactos verify bit-a-bit)
- **Artefacto (run_id):** `0e65bca180992c19`

### 95. Chandelier breakout

- **Familia:** `llm_pack` — Pack generado por LLM: rupturas, momentum, mean-reversion y filtros de volumen/flujo.
- **Nombre/celda:** `Chandelier breakout` · **Símbolo:** ETHUSDT · **TF:** 4h
- **Descripción:** Chandelier breakout
- **PF neto (IS):** 0.9361 · **Return neto:** -22.42% · **n trades:** 181 · **Win rate:** 22.65% · **Max DD:** -68.28%
- **OOS:** no disponible
- **Buy & Hold (contexto):** -7.52%
- **Costes:** 12.0 bps round-trip · **Funding cobrado:** sí
- **Ventana:** 2024-10-14 → 2026-10-14
- **Veredicto:** KILLED 0/48
- **Artefacto (run_id):** `56051a9835e556da`

### 96. xrpneutral1m

- **Familia:** `grid_neutral` — Grid delta-neutral.
- **Nombre/celda:** `xrpneutral1m` · **Símbolo:** XRPUSDT · **TF:** 15m
- **Descripción:** xrpneutral1m
- **PF neto (IS):** 0.9326 · **Return neto:** -74.20% · **n trades:** 3018 · **Win rate:** 77.53% · **Max DD:** -81.46%
- **OOS:** no disponible
- **Buy & Hold (contexto):** 340.14%
- **Costes:** 14.0 bps round-trip · **Funding cobrado:** sí
- **Bootstrap CI lower (mean R):** -0.0162
- **Ventana:** 2020-01-06 → 2026-11-04
- **Veredicto:** KILLED (el mismo libro resuelto en 1m cae bajo PF 1 en el OOS; artefacto 18d686932bf06f78)
- **Artefacto (run_id):** `18d686932bf06f78`

### 97. RSI-2 snap-back

- **Familia:** `llm_pack` — Pack generado por LLM: rupturas, momentum, mean-reversion y filtros de volumen/flujo.
- **Nombre/celda:** `RSI-2 snap-back` · **Símbolo:** SUIUSDT · **TF:** 1h
- **Descripción:** RSI-2 snap-back
- **PF neto (IS):** 0.9326 · **Return neto:** -7.92% · **n trades:** 134 · **Win rate:** 67.16% · **Max DD:** -29.60%
- **OOS:** no disponible
- **Buy & Hold (contexto):** -59.08%
- **Costes:** 20.0 bps round-trip · **Funding cobrado:** sí
- **Ventana:** 2024-10-14 → 2026-10-26
- **Veredicto:** KILLED 0/48
- **Artefacto (run_id):** `80e8e4eab0cc90c8`

### 98. daily-open reversion

- **Familia:** `p100screen` — Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.
- **Nombre/celda:** `id=84` · **Símbolo:** BASKET6 · **TF:** 1h
- **Descripción:** daily-open reversion
- **PF neto (IS):** 0.9323 · **Return neto:** -76.92% · **n trades:** 2134 · **Win rate:** 46.44% · **Max DD:** -89.51%
- **OOS:** PF 0.8498 · ret -43.6% · n 463
- **Buy & Hold (contexto):** 1039.89%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -0.0014
- **Ventana:** 2019-09-08 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `06b1877cda503628`

### 99. zscore fade

- **Familia:** `pack20` — Pack de 20 estrategias intradía (VWAP fade, ATR/vol breakout, TTM squeeze, etc.).
- **Nombre/celda:** `12_zscore_fade` · **Símbolo:** SOLUSDT · **TF:** 15m
- **Descripción:** zscore fade
- **PF neto (IS):** 0.9256 · **Return neto:** -99.90% · **n trades:** 3957 · **Win rate:** n/a · **Max DD:** -99.95%
- **OOS:** PF 0.8034 · ret -78.98% · n 1179
- **Buy & Hold (contexto):** 2705.14%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -22.2511
- **Ventana:** 2020-09-14 → 2026-11-07
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `36c1914c7c52d88e`

### 100. adx di trend

- **Familia:** `pack20` — Pack de 20 estrategias intradía (VWAP fade, ATR/vol breakout, TTM squeeze, etc.).
- **Nombre/celda:** `07_adx_di_trend` · **Símbolo:** ETHUSDT · **TF:** 1h
- **Descripción:** adx di trend
- **PF neto (IS):** 0.9216 · **Return neto:** -81.83% · **n trades:** 1517 · **Win rate:** n/a · **Max DD:** -91.57%
- **OOS:** PF 0.7606 · ret -55.02% · n 433
- **Buy & Hold (contexto):** 1456.39%
- **Costes:** 11.0 bps round-trip · **Funding cobrado:** no
- **Bootstrap CI lower (mean R):** -22.0233
- **Ventana:** 2019-11-27 → 2026-11-02
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `89ea8eceb1b1e7c4`

---
*Generado por `code/_top100_catalog.py` desde artefactos verificados. Ranking relativo dentro de un corpus con 0 supervivientes; no es asesoramiento ni una lista de estrategias rentables. Datos: `results/top100_catalog.json` / `.csv`.*