# Strategy suite: ETHUSDT 5m, holding 3 bars

Data: ETHUSDT 5m Binance futures, 210240 bars, 2024-10-14 21:25:00+00:00 -> 2026-10-14 21:20:00+00:00
Costs assumed: taker 0.0500%/side, slippage 0.0100%/side, funding 0.0100%/8h (VERIFY).
Multiple testing: 10 strategies tested, so net t must exceed 2.58 (Bonferroni, alpha=0.05), plus net>0, permutation >= 90%, calibration slope 0.7-1.3, >= 100 trades.

**0 of 10 strategies pass.** No strategy shows demonstrated edge: do NOT automate.

| id | strategy | AUC | slope | gross edge bp | gross t | trades | net t | net bp/trade | net ret | maxDD | perm | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S10 | Calendar / funding-clock seasonality | 0.502 | 0.00 | 14.7 | -0.7 | 9 | +2.8 | +257.7 | +25.4% | 1.3% | n/a | FAIL: perm>=90%,slope,trades>=100 |
| S06 | CVD / price divergence | 0.521 | 0.77 | 13.1 | -2.0 | 37 | +2.1 | +54.1 | +21.6% | 4.2% | 100% | FAIL: t>tcrit,trades>=100 |
| S05 | Taker-flow imbalance (OFI proxy) | 0.521 | 0.83 | 14.8 | +0.8 | 22 | +0.9 | +39.3 | +8.5% | 6.6% | n/a | FAIL: t>tcrit,perm>=90%,trades>=100 |
| S07 | Rolling-VWAP deviation | 0.536 | 0.88 | 15.0 | -0.3 | 178 | +0.3 | +3.3 | +3.7% | 19.8% | n/a | FAIL: t>tcrit,perm>=90% |
| S03 | Donchian range position / breakout | 0.532 | 0.86 | 18.0 | -1.2 | 325 | +0.2 | +1.8 | +2.8% | 18.1% | n/a | FAIL: t>tcrit,perm>=90% |
| S09 | Autocorrelation regime switch | 0.505 | 0.34 | 18.1 | -1.2 | 24 | -0.5 | -19.8 | -5.0% | 8.0% | n/a | FAIL: t>tcrit,net>0,perm>=90%,slope,trades>=100 |
| S04 | Volatility squeeze -> expansion | 0.521 | 0.83 | 18.4 | +1.5 | 205 | -0.8 | -9.3 | -19.5% | 22.3% | n/a | FAIL: t>tcrit,net>0,perm>=90% |
| S02 | EMA z-score mean reversion | 0.538 | 0.89 | 16.2 | -0.7 | 607 | -1.0 | -5.6 | -32.5% | 37.6% | n/a | FAIL: t>tcrit,net>0,perm>=90% |
| S01 | Vol-normalised time-series momentum | 0.536 | 0.86 | 16.0 | -0.7 | 555 | -1.7 | -10.3 | -46.6% | 50.4% | n/a | FAIL: t>tcrit,net>0,perm>=90% |
| S08 | Volume-shock follow-through | 0.511 | 0.76 | 17.2 | -1.5 | 259 | -1.9 | -20.7 | -43.8% | 45.2% | n/a | FAIL: t>tcrit,net>0,perm>=90% |

'gross t' = same signals at zero cost (is there any alpha before fees?). A high gross t with a failing net t means costs eat the edge.

## WHY THIS COULD STOP WORKING
1. El edge puede ser un artefacto del periodo muestreado: un solo regimen de volatilidad/tendencia no prueba robustez.
2. Los costos (comision, slippage, funding) son parametros asumidos; con otro tier o liquidez peor el edge neto desaparece.
3. Barras de 5 min con entrada al cierre ignoran la latencia real y el impacto en el libro; el slippage real es no lineal en tamano.
4. El modelo se reajusta periodicamente: si la relacion flujo->retorno cambia (estructura de mercado, competencia), la calibracion se degrada.
5. Con senal debil (AUC cercano a 0.5) basta un pequeno error de calibracion para convertir edge positivo en negativo tras costos.
6. Backtest sobre una sola moneda/exchange: sin validacion cruzada entre activos, el riesgo de sobreajuste por seleccion es alto.
7. Eventos de cola (liquidaciones en cascada, gaps, caidas de API, funding extremo) no estan bien representados en la muestra.