# Strategy suite: SOLUSDT 5m, holding 3 bars

Data: SOLUSDT 5m Binance futures, 210240 bars, 2024-10-14 21:25:00+00:00 -> 2026-10-14 21:20:00+00:00
Costs assumed: taker 0.0500%/side, slippage 0.0100%/side, funding 0.0100%/8h (VERIFY).
Multiple testing: 10 strategies tested, so net t must exceed 2.58 (Bonferroni, alpha=0.05), plus net>0, permutation >= 90%, calibration slope 0.7-1.3, >= 100 trades.

**0 of 10 strategies pass.** No strategy shows demonstrated edge: do NOT automate.

| id | strategy | AUC | slope | gross edge bp | gross t | trades | net t | net bp/trade | net ret | maxDD | perm | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S05 | Taker-flow imbalance (OFI proxy) | 0.517 | 0.76 | 16.3 | +0.4 | 28 | +1.7 | +137.6 | +43.3% | 4.9% | n/a | FAIL: t>tcrit,perm>=90%,trades>=100 |
| S02 | EMA z-score mean reversion | 0.528 | 0.87 | 16.5 | -0.4 | 226 | +1.4 | +30.5 | +75.3% | 60.6% | n/a | FAIL: t>tcrit,perm>=90% |
| S10 | Calendar / funding-clock seasonality | 0.504 | 0.27 | 27.1 | +0.7 | 59 | +1.2 | +57.0 | +35.0% | 11.6% | n/a | FAIL: t>tcrit,perm>=90%,slope,trades>=100 |
| S03 | Donchian range position / breakout | 0.526 | 0.85 | 18.1 | -0.9 | 232 | +1.2 | +16.7 | +39.7% | 21.5% | n/a | FAIL: t>tcrit,perm>=90% |
| S01 | Vol-normalised time-series momentum | 0.526 | 0.82 | 16.5 | -1.2 | 205 | +1.1 | +25.9 | +50.0% | 62.5% | n/a | FAIL: t>tcrit,perm>=90% |
| S06 | CVD / price divergence | 0.517 | 0.74 | 17.7 | +0.9 | 71 | +0.9 | +40.5 | +27.3% | 20.8% | n/a | FAIL: t>tcrit,perm>=90%,trades>=100 |
| S07 | Rolling-VWAP deviation | 0.526 | 0.87 | 20.8 | -0.9 | 56 | +0.5 | +27.6 | +11.9% | 22.5% | n/a | FAIL: t>tcrit,perm>=90%,trades>=100 |
| S09 | Autocorrelation regime switch | 0.504 | 0.26 | 26.3 | +1.1 | 32 | +0.2 | +18.5 | +2.2% | 22.4% | n/a | FAIL: t>tcrit,perm>=90%,slope,trades>=100 |
| S04 | Volatility squeeze -> expansion | 0.515 | 0.70 | 28.3 | +3.2 | 173 | +0.2 | +4.5 | -2.2% | 41.6% | n/a | FAIL: t>tcrit,net>0,perm>=90%,slope |
| S08 | Volume-shock follow-through | 0.510 | 0.64 | 17.3 | -0.5 | 204 | -0.0 | -0.1 | -5.8% | 26.6% | n/a | FAIL: t>tcrit,net>0,perm>=90%,slope |

'gross t' = same signals at zero cost (is there any alpha before fees?). A high gross t with a failing net t means costs eat the edge.

## WHY THIS COULD STOP WORKING
1. El edge puede ser un artefacto del periodo muestreado: un solo regimen de volatilidad/tendencia no prueba robustez.
2. Los costos (comision, slippage, funding) son parametros asumidos; con otro tier o liquidez peor el edge neto desaparece.
3. Barras de 5 min con entrada al cierre ignoran la latencia real y el impacto en el libro; el slippage real es no lineal en tamano.
4. El modelo se reajusta periodicamente: si la relacion flujo->retorno cambia (estructura de mercado, competencia), la calibracion se degrada.
5. Con senal debil (AUC cercano a 0.5) basta un pequeno error de calibracion para convertir edge positivo en negativo tras costos.
6. Backtest sobre una sola moneda/exchange: sin validacion cruzada entre activos, el riesgo de sobreajuste por seleccion es alto.
7. Eventos de cola (liquidaciones en cascada, gaps, caidas de API, funding extremo) no estan bien representados en la muestra.