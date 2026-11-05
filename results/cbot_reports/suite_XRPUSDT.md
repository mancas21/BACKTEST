# Strategy suite: XRPUSDT 5m, holding 3 bars

Data: XRPUSDT 5m Binance futures, 210240 bars, 2024-10-14 21:25:00+00:00 -> 2026-10-14 21:20:00+00:00
Costs assumed: taker 0.0500%/side, slippage 0.0100%/side, funding 0.0100%/8h (VERIFY).
Multiple testing: 10 strategies tested, so net t must exceed 2.58 (Bonferroni, alpha=0.05), plus net>0, permutation >= 90%, calibration slope 0.7-1.3, >= 100 trades.

**0 of 10 strategies pass.** No strategy shows demonstrated edge: do NOT automate.

| id | strategy | AUC | slope | gross edge bp | gross t | trades | net t | net bp/trade | net ret | maxDD | perm | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S02 | EMA z-score mean reversion | 0.531 | 0.88 | 18.2 | +0.8 | 869 | +0.9 | +6.4 | +41.6% | 46.4% | n/a | FAIL: t>tcrit,perm>=90% |
| S01 | Vol-normalised time-series momentum | 0.529 | 0.84 | 18.1 | +1.1 | 769 | +0.8 | +6.6 | +35.7% | 51.6% | n/a | FAIL: t>tcrit,perm>=90% |
| S07 | Rolling-VWAP deviation | 0.528 | 0.85 | 17.6 | +2.0 | 563 | -0.2 | -2.1 | -25.8% | 55.8% | n/a | FAIL: t>tcrit,net>0,perm>=90% |
| S08 | Volume-shock follow-through | 0.511 | 0.69 | 21.2 | +1.9 | 414 | -0.6 | -11.2 | -54.7% | 67.9% | n/a | FAIL: t>tcrit,net>0,perm>=90%,slope |
| S04 | Volatility squeeze -> expansion | 0.513 | 0.62 | 21.5 | +2.4 | 314 | -0.7 | -15.4 | -50.6% | 57.0% | n/a | FAIL: t>tcrit,net>0,perm>=90%,slope |
| S10 | Calendar / funding-clock seasonality | 0.505 | 0.28 | 22.6 | -0.2 | 22 | -1.9 | -68.1 | -14.2% | 19.7% | n/a | FAIL: t>tcrit,net>0,perm>=90%,slope,trades>=100 |
| S03 | Donchian range position / breakout | 0.529 | 0.83 | 20.4 | +2.8 | 576 | -2.1 | -22.4 | -77.4% | 82.3% | n/a | FAIL: t>tcrit,net>0,perm>=90% |
| S09 | Autocorrelation regime switch | 0.505 | 0.36 | 25.3 | +4.1 | 72 | -2.1 | -92.4 | -51.4% | 53.6% | n/a | FAIL: t>tcrit,net>0,perm>=90%,slope,trades>=100 |
| S06 | CVD / price divergence | 0.520 | 0.79 | 17.2 | +1.6 | 357 | -2.6 | -31.8 | -71.0% | 74.8% | n/a | FAIL: t>tcrit,net>0,perm>=90% |
| S05 | Taker-flow imbalance (OFI proxy) | 0.515 | 0.69 | 20.3 | +2.0 | 75 | -3.0 | -148.4 | -69.9% | 71.1% | n/a | FAIL: t>tcrit,net>0,perm>=90%,slope,trades>=100 |

'gross t' = same signals at zero cost (is there any alpha before fees?). A high gross t with a failing net t means costs eat the edge.

## WHY THIS COULD STOP WORKING
1. El edge puede ser un artefacto del periodo muestreado: un solo regimen de volatilidad/tendencia no prueba robustez.
2. Los costos (comision, slippage, funding) son parametros asumidos; con otro tier o liquidez peor el edge neto desaparece.
3. Barras de 5 min con entrada al cierre ignoran la latencia real y el impacto en el libro; el slippage real es no lineal en tamano.
4. El modelo se reajusta periodicamente: si la relacion flujo->retorno cambia (estructura de mercado, competencia), la calibracion se degrada.
5. Con senal debil (AUC cercano a 0.5) basta un pequeno error de calibracion para convertir edge positivo en negativo tras costos.
6. Backtest sobre una sola moneda/exchange: sin validacion cruzada entre activos, el riesgo de sobreajuste por seleccion es alto.
7. Eventos de cola (liquidaciones en cascada, gaps, caidas de API, funding extremo) no estan bien representados en la muestra.