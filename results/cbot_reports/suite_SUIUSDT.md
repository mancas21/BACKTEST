# Strategy suite: SUIUSDT 5m, holding 3 bars

Data: SUIUSDT 5m Binance futures, 210240 bars, 2024-10-14 21:25:00+00:00 -> 2026-10-14 21:20:00+00:00
Costs assumed: taker 0.0500%/side, slippage 0.0100%/side, funding 0.0100%/8h (VERIFY).
Multiple testing: 10 strategies tested, so net t must exceed 2.58 (Bonferroni, alpha=0.05), plus net>0, permutation >= 90%, calibration slope 0.7-1.3, >= 100 trades.

**0 of 10 strategies pass.** No strategy shows demonstrated edge: do NOT automate.

| id | strategy | AUC | slope | gross edge bp | gross t | trades | net t | net bp/trade | net ret | maxDD | perm | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S06 | CVD / price divergence | 0.514 | 0.67 | 14.9 | +2.1 | 159 | +1.6 | +98.6 | +243.7% | 26.6% | 100% | FAIL: t>tcrit,slope |
| S10 | Calendar / funding-clock seasonality | 0.505 | 0.24 | 36.0 | +1.4 | 193 | +1.3 | +69.7 | +152.5% | 67.1% | n/a | FAIL: t>tcrit,perm>=90%,slope |
| S01 | Vol-normalised time-series momentum | 0.527 | 0.80 | 16.8 | +1.6 | 745 | +1.0 | +14.9 | +91.4% | 56.8% | n/a | FAIL: t>tcrit,perm>=90% |
| S02 | EMA z-score mean reversion | 0.529 | 0.85 | 17.2 | +2.2 | 772 | +0.5 | +7.3 | +10.9% | 61.5% | n/a | FAIL: t>tcrit,perm>=90% |
| S07 | Rolling-VWAP deviation | 0.526 | 0.85 | 18.4 | +1.6 | 384 | +0.2 | +5.3 | -17.3% | 70.2% | n/a | FAIL: t>tcrit,net>0,perm>=90% |
| S08 | Volume-shock follow-through | 0.506 | 0.54 | 19.4 | +0.5 | 375 | +0.1 | +3.5 | -26.8% | 50.0% | n/a | FAIL: t>tcrit,net>0,perm>=90%,slope |
| S04 | Volatility squeeze -> expansion | 0.513 | 0.62 | 38.8 | +2.3 | 474 | +0.0 | +0.4 | -34.7% | 63.6% | n/a | FAIL: t>tcrit,net>0,perm>=90%,slope |
| S03 | Donchian range position / breakout | 0.526 | 0.81 | 23.6 | +1.1 | 502 | -0.8 | -16.2 | -70.5% | 78.2% | n/a | FAIL: t>tcrit,net>0,perm>=90% |
| S09 | Autocorrelation regime switch | 0.502 | 0.00 | 57.8 | +1.3 | 79 | -1.7 | -209.3 | -93.8% | 95.7% | n/a | FAIL: t>tcrit,net>0,perm>=90%,slope,trades>=100 |
| S05 | Taker-flow imbalance (OFI proxy) | 0.513 | 0.63 | 26.6 | +1.5 | 67 | -2.8 | -173.8 | -72.2% | 72.7% | n/a | FAIL: t>tcrit,net>0,perm>=90%,slope,trades>=100 |

'gross t' = same signals at zero cost (is there any alpha before fees?). A high gross t with a failing net t means costs eat the edge.

## WHY THIS COULD STOP WORKING
1. El edge puede ser un artefacto del periodo muestreado: un solo regimen de volatilidad/tendencia no prueba robustez.
2. Los costos (comision, slippage, funding) son parametros asumidos; con otro tier o liquidez peor el edge neto desaparece.
3. Barras de 5 min con entrada al cierre ignoran la latencia real y el impacto en el libro; el slippage real es no lineal en tamano.
4. El modelo se reajusta periodicamente: si la relacion flujo->retorno cambia (estructura de mercado, competencia), la calibracion se degrada.
5. Con senal debil (AUC cercano a 0.5) basta un pequeno error de calibracion para convertir edge positivo en negativo tras costos.
6. Backtest sobre una sola moneda/exchange: sin validacion cruzada entre activos, el riesgo de sobreajuste por seleccion es alto.
7. Eventos de cola (liquidaciones en cascada, gaps, caidas de API, funding extremo) no estan bien representados en la muestra.