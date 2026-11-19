# ESTRATEGIAS POR VALIDEZ OUT-OF-SAMPLE + FILTRO DE ROBUSTEZ

> **Versión alternativa al top-100 por IS PF.** El ranking aquí es por **PF neto OOS** (validez out-of-sample) y se aplica un **filtro de robustez** para aislar las candidatas que realmente merecen seguimiento. Mismo corpus (0 supervivientes confirmados por la batería completa): esto es una **priorización de investigación**, NO una lista de estrategias rentables validadas ni recomendaciones de trading. Regla de la casa: OOS con n<200 se etiqueta FRÁGIL.

- **Universo:** 294 estrategias distintas (n≥30 IS, métricas limpias, artefacto verificado).
- **Con OOS PF disponible:** 176 · **con OOS PF>1 y OOS n≥30:** 29.
- **Filtro de robustez** (IS n≥100 · PF neto IS>1 · OOS PF>1 · OOS n≥30 · bootstrap CI lower>0): **6 pasan**.

## A) Filtro de robustez — candidatas que merecen seguimiento

| # | Estrategia | Familia | Símbolo | TF | PF IS | PF OOS | OOS ret% | OOS n | n IS | boot CI lo | Veredicto | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | mid-day-lull mean-reversion | p100screen | HYPEUSDT | 1h | 2.607 | 3.100 | 428.78 | 383 | 127 | 0.0894 | SIN VEREDICTO | `b6ebfc6ec584042f` |
| 2 | atr vol breakout | pack20 | ETHUSDT | 1h | 1.585 | 1.625 | 159.11 | 118 ⚠FRÁGIL | 388 | 24.6209 | SIN VEREDICTO | `3aaf8d34f49f1187` |
| 3 | vwap fade | pack20 | SOLUSDT | 15m | 1.077 | 1.079 | 457.04 | 5597 | 17850 | 3.5845 | SIN VEREDICTO | `44a23ab194b621be` |
| 4 | TRIX(15) zero-cross | p100screen | BTCUSDT | 15m | 1.132 | 1.071 | 13.9 | 179 ⚠FRÁGIL | 877 | 0.0139 | SIN VEREDICTO | `9e93753caa755c27` |
| 5 | triple EMA (8/21/55) pullback | p100screen | ETHUSDT | 1h | 1.262 | 1.035 | 3.15 | 183 ⚠FRÁGIL | 942 | 0.0471 | SIN VEREDICTO | `2f8f3ce69d850de1` |
| 6 | impulse-bar continuation | p100screen | ETHUSDT | 1h | 1.275 | 1.014 | 0.78 | 124 ⚠FRÁGIL | 622 | 0.0127 | SIN VEREDICTO | `df3d84f2bad4b17b` |

**Importante — esto NO es la batería completa.** El filtro de arriba es un SUBCONJUNTO ligero de G1-G11. Las candidatas listadas **NO son supervivientes validadas**: les falta el estrés a **2× coste**, el **Deflated Sharpe (DSR** por múltiples pruebas), la **concentración** (top-5 trades), el **P95 de drawdown**, el **alfa t>2** y la comparación **B&H**. La mayoría están `SIN VEREDICTO` (nunca se juzgaron con la batería completa). Un PF OOS apenas >1 (p.ej. 1.01-1.08) con turnover alto muere casi seguro al doblar costes. Son una **priorización para investigar**, no edges confirmados.

## B) Ranking por PF neto OOS (top 50 con OOS disponible)

*Ranking CRUDO por OOS PF: incluye celdas con OOS n<30 (ruido — un OOS PF alto con ~20 trades no es evidencia) y celdas con IS pésimo, bootstrap CI negativo o veredicto KILLED. Solo como panorama; las listas accionables son la A (filtro de robustez) y la C (OOS PF>1 con OOS n≥30).*

| #OOS | Estrategia | Familia | Símbolo | TF | PF IS | PF OOS | OOS ret% | OOS n | n IS | boot CI lo | Veredicto |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Motor qs096: estrategia cuantitativa c | qs096 | HYPEUSDT | 1h | 2.609 | 6.409 | 28.33 | 23 | 68 | 1.1066 | SIN VEREDICTO |
| 2 | mid-day-lull mean-reversion | p100screen | HYPEUSDT | 1h | 2.607 | 3.100 | 428.78 | 383 | 127 | 0.0894 | SIN VEREDICTO |
| 3 | Tendencia con HMA (Hull MA) simple. | trend_hma_simple | HYPEUSDT | 1h | 1.378 | 2.365 | 34.97 | 30 | 113 | -40.7194 | KILLED 0/11 (PF ex-cos |
| 4 | double-bottom breakout | p100screen | ETHUSDT | 1h | 1.469 | 2.057 | 8.6 | 19 | 106 | -0.091 | SIN VEREDICTO |
| 5 | Bollinger Band walk | p100screen | HYPEUSDT | 5m | 0.046 | 2.045 | 48.33 | 63 | 53 | -1.2318 | SIN VEREDICTO |
| 6 | Tendencia con HMA (Hull MA) simple. | trend_hma_simple | BTCUSDT | 1h | 1.083 | 1.769 | 10.3 | 36 | 112 | -22.6406 | KILLED 0/11 (PF ex-cos |
| 7 | Tendencia con HMA (Hull MA) simple. | trend_hma_simple | SUIUSDT | 1h | 0.962 | 1.679 | 12.32 | 35 | 113 | -52.4514 | KILLED 0/11 (PF ex-cos |
| 8 | variance-ratio regime | p100screen | BTCUSDT | 1h | 1.244 | 1.656 | -13.13 | 368 | 2433 | -0.0077 | SIN VEREDICTO |
| 9 | Tendencia con HMA (Hull MA) simple. | trend_hma_simple | JUPUSDT | 1h | 1.211 | 1.626 | 25.65 | 36 | 111 | -40.3737 | KILLED 0/11 (PF ex-cos |
| 10 | atr vol breakout | pack20 | ETHUSDT | 1h | 1.585 | 1.625 | 159.11 | 118 | 388 | 24.6209 | SIN VEREDICTO |
| 11 | Cruce de EMAs 9/21 con filtro de tende | trend_ema_crossover | LABUSDT | 1h | 1.270 | 1.558 | 13.21 | 88 | 345 | -1.9495 | KILLED 0/101 (ninguna  |
| 12 | funding-timestamp run-up | p100screen | BASKET6 | 1h | 1.108 | 1.442 | 37.48 | 53 | 125 | -0.0024 | SIN VEREDICTO |
| 13 | fractal breakout | p100screen | BTCUSDT | 1h | 2.293 | 1.382 | 5.94 | 22 | 136 | 0.4225 | SIN VEREDICTO |
| 14 | volume-climax reversal | p100screen | HYPEUSDT | 1h | 1.096 | 1.355 | 23.54 | 141 | 50 | -0.1636 | SIN VEREDICTO |
| 15 | Motor qs097: variante cuantitativa con | qs097 | HYPEUSDT | 1h | 1.181 | 1.355 | 7.43 | 55 | 162 | -16.5086 | SIN VEREDICTO |
| 16 | multi-timeframe trend + pullback | p100screen | BASKET6 | 1h | 1.143 | 1.336 | 20.07 | 53 | 124 | -0.0043 | SIN VEREDICTO |
| 17 | Motor qs097: variante cuantitativa con | qs097 | JUPUSDT | 1h | 0.849 | 1.292 | 3.11 | 42 | 158 | -15.5268 | SIN VEREDICTO |
| 18 | Tendencia con HMA (Hull MA) simple. | trend_hma_simple | XRPUSDT | 1h | 1.226 | 1.280 | 5.02 | 34 | 104 | -33.7528 | KILLED 0/11 (PF ex-cos |
| 19 | Motor qs097: variante cuantitativa con | qs097 | ETHUSDT | 1h | 1.234 | 1.234 | 25.99 | 306 | 306 | -7.1405 | SIN VEREDICTO |
| 20 | Tendencia con HMA (Hull MA) simple. | trend_hma_simple | 1000PEPEUSDT | 1h | 0.907 | 1.192 | 5.15 | 35 | 123 | -65.0413 | KILLED 0/11 (PF ex-cos |
| 21 | Motor smqe11: variante SMC cuantitativ | smqe11 | SUIUSDT | 1h | 1.661 | 1.192 | 1.68 | 18 | 53 | n/a | SIN VEREDICTO |
| 22 | Motor qs097: variante cuantitativa con | qs097 | SUIUSDT | 1h | 1.192 | 1.134 | 12.06 | 210 | 295 | -12.1402 | SIN VEREDICTO |
| 23 | Tendencia con HMA (Hull MA) simple. | trend_hma_simple | ARBUSDT | 1h | 0.727 | 1.127 | 3.73 | 37 | 114 | -62.7364 | KILLED 0/11 (PF ex-cos |
| 24 | ttm squeeze | pack20 | XRPUSDT | 1h | 1.048 | 1.116 | 142.18 | 874 | 3396 | -0.9676 | SIN VEREDICTO |
| 25 | engulfing-at-extreme | p100screen | JUPUSDT | 1h | 0.685 | 1.112 | 3.74 | 43 | 62 | -0.7402 | SIN VEREDICTO |
| 26 | HTF FVG: fair value gaps en temporalid | htffvg | JUPUSDT | 15m | 1.006 | 1.079 | 4.2 | 72 | 239 | -18.8362 | SIN VEREDICTO |
| 27 | vwap fade | pack20 | SOLUSDT | 15m | 1.077 | 1.079 | 457.04 | 5597 | 17850 | 3.5845 | SIN VEREDICTO |
| 28 | TRIX(15) zero-cross | p100screen | BTCUSDT | 15m | 1.132 | 1.071 | 13.9 | 179 | 877 | 0.0139 | SIN VEREDICTO |
| 29 | squeeze rank breakout | pack20 | SOLUSDT | 1h | 1.076 | 1.065 | 14.64 | 204 | 684 | -8.462 | SIN VEREDICTO |
| 30 | triple EMA (8/21/55) pullback | p100screen | ETHUSDT | 1h | 1.262 | 1.035 | 3.15 | 183 | 942 | 0.0471 | SIN VEREDICTO |
| 31 | Motor qs097: variante cuantitativa con | qs097 | BTCUSDT | 1h | 0.902 | 1.015 | 0.21 | 104 | 332 | -11.3451 | SIN VEREDICTO |
| 32 | impulse-bar continuation | p100screen | ETHUSDT | 1h | 1.275 | 1.014 | 0.78 | 124 | 622 | 0.0127 | SIN VEREDICTO |
| 33 | range-box breakout strategy with volum | p100screen | JUPUSDT | 1h | 0.881 | 1.010 | 2.67 | 805 | 1374 | -0.0926 | SIN VEREDICTO |
| 34 | Tendencia con HMA (Hull MA) simple. | trend_hma_simple | ETHUSDT | 1h | 1.010 | 0.983 | -20.57 | 707 | 2298 | -23.9752 | KILLED 0/11 (PF ex-cos |
| 35 | macd momentum | pack20 | SOLUSDT | 1h | 0.999 | 0.976 | -21.86 | 777 | 2554 | -8.2996 | SIN VEREDICTO |
| 36 | logreg walkforward | pack20 | SOLUSDT | 1h | 0.993 | 0.973 | -23.4 | 1376 | 4520 | -6.6388 | SIN VEREDICTO |
| 37 | Stop-run continuation strategy on JUPU | strategies_101_150 | JUPUSDT | 15m | 0.868 | 0.966 | -1.18 | 101 | 297 | -0.2066 | KILLED 0/37 (ruina por |
| 38 | momentum-acceleration | p100screen | SUIUSDT | 15m | 0.780 | 0.961 | -14.95 | 503 | 1339 | -0.205 | SIN VEREDICTO |
| 39 | NR7 breakout | p100screen | SOLUSDT | 1h | 1.091 | 0.960 | -8.46 | 335 | 1561 | -0.0234 | SIN VEREDICTO |
| 40 | Hull MA(55) slope | p100screen | JUPUSDT | 1h | 0.771 | 0.959 | -3.24 | 174 | 349 | -0.219 | SIN VEREDICTO |
| 41 | ema pullback | pack20 | BTCUSDT | 1h | 1.012 | 0.952 | -10.33 | 330 | 1070 | -9.5839 | SIN VEREDICTO |
| 42 | HTF FVG: fair value gaps en temporalid | htffvg | ETHUSDT | 15m | 1.022 | 0.927 | -8.88 | 174 | 630 | -12.4427 | SIN VEREDICTO |
| 43 | Tendencia con HMA (Hull MA) simple. | trend_hma_simple | SOLUSDT | 1h | 1.013 | 0.924 | -164.47 | 600 | 2011 | -59.9174 | KILLED 0/11 (PF ex-cos |
| 44 | Motor qs097: variante cuantitativa con | qs097 | SOLUSDT | 1h | 0.920 | 0.920 | -6.08 | 181 | 181 | -18.0423 | SIN VEREDICTO |
| 45 | session VWAP deviation mean-reversion | p100screen | SUIUSDT | 1h | 0.910 | 0.917 | -2.23 | 79 | 171 | -0.1251 | SIN VEREDICTO |
| 46 | hour-of-day seasonality | p100screen | SOLUSDT | 1h | 0.293 | 0.916 | 186.78 | 44 | 215 | -0.2105 | SIN VEREDICTO |
| 47 | Turtle 55/20 breakout | p100screen | SUIUSDT | 1h | 0.827 | 0.915 | -4.96 | 108 | 339 | -0.2271 | SIN VEREDICTO |
| 48 | order block | pack20 | XRPUSDT | 1h | 1.007 | 0.907 | -53.61 | 332 | 1062 | -16.2541 | SIN VEREDICTO |
| 49 | donchian turtle | pack20 | ETHUSDT | 1h | 0.982 | 0.906 | -34.84 | 483 | 1559 | -15.353 | SIN VEREDICTO |
| 50 | Stochastic (14,3,3) oversold/overbough | p100screen | JUPUSDT | 1h | 0.803 | 0.905 | -7.47 | 249 | 421 | -0.1506 | SIN VEREDICTO |

## C) Fichas de las que sostienen OOS (OOS PF>1, OOS n≥30): 29

### mid-day-lull mean-reversion
- `p100screen` · HYPEUSDT 1h · celda `id=85`
- **IS:** PF 2.6073 · ret 28.1% · n 127 · DD -3.04%
- **OOS:** PF 3.0997 · ret 428.78% · n 383
- **Bootstrap CI lower (mean R):** 0.0894
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `b6ebfc6ec584042f`

### Tendencia con HMA (Hull MA) simple.
- `trend_hma_simple` · HYPEUSDT 1h · celda `card=HYPEUSDT` · **⚠FRÁGIL (OOS n<200)**
- **IS:** PF 1.3784 · ret 58.64% · n 113 · DD -27.05%
- **OOS:** PF 2.3653 · ret 34.97% · n 30
- **Bootstrap CI lower (mean R):** -40.7194
- **Veredicto:** KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs)
- **Artefacto (run_id):** `0c7aebcfe691bdaa`

### Bollinger Band walk
- `p100screen` · HYPEUSDT 5m · celda `id=41` · **⚠FRÁGIL (OOS n<200)**
- **IS:** PF 0.0459 · ret -48.59% · n 53 · DD -56.54%
- **OOS:** PF 2.0449 · ret 48.33% · n 63
- **Bootstrap CI lower (mean R):** -1.2318
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `db4cc1b874b1f993`

### Tendencia con HMA (Hull MA) simple.
- `trend_hma_simple` · BTCUSDT 1h · celda `card=BTCUSDT` · **⚠FRÁGIL (OOS n<200)**
- **IS:** PF 1.0831 · ret 5.1% · n 112 · DD -19.16%
- **OOS:** PF 1.7694 · ret 10.3% · n 36
- **Bootstrap CI lower (mean R):** -22.6406
- **Veredicto:** KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs)
- **Artefacto (run_id):** `6246c97f560abc0b`

### Tendencia con HMA (Hull MA) simple.
- `trend_hma_simple` · SUIUSDT 1h · celda `card=SUIUSDT` · **⚠FRÁGIL (OOS n<200)**
- **IS:** PF 0.9622 · ret -4.07% · n 113 · DD -39.63%
- **OOS:** PF 1.6794 · ret 12.32% · n 35
- **Bootstrap CI lower (mean R):** -52.4514
- **Veredicto:** KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs)
- **Artefacto (run_id):** `58bbf6c26905b33c`

### variance-ratio regime
- `p100screen` · BTCUSDT 1h · celda `id=88`
- **IS:** PF 1.2442 · ret -95.9% · n 2433 · DD -96.47%
- **OOS:** PF 1.6560 · ret -13.13% · n 368
- **Bootstrap CI lower (mean R):** -0.0077
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `5636a3a9936646fc`

### Tendencia con HMA (Hull MA) simple.
- `trend_hma_simple` · JUPUSDT 1h · celda `card=JUPUSDT` · **⚠FRÁGIL (OOS n<200)**
- **IS:** PF 1.2110 · ret 28.86% · n 111 · DD -25.23%
- **OOS:** PF 1.6260 · ret 25.65% · n 36
- **Bootstrap CI lower (mean R):** -40.3737
- **Veredicto:** KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs)
- **Artefacto (run_id):** `2411025b023d0bbf`

### atr vol breakout
- `pack20` · ETHUSDT 1h · celda `17_atr_vol_breakout` · **⚠FRÁGIL (OOS n<200)**
- **IS:** PF 1.5855 · ret 882.14% · n 388 · DD -25.14%
- **OOS:** PF 1.6250 · ret 159.11% · n 118
- **Bootstrap CI lower (mean R):** 24.6209
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `3aaf8d34f49f1187`

### Cruce de EMAs 9/21 con filtro de tendencia. (motor/candidato ema921)
- `trend_ema_crossover` · LABUSDT 1h · celda `ema921` · **⚠FRÁGIL (OOS n<200)**
- **IS:** PF 1.2701 · ret 28.44% · n 345 · DD -14.99%
- **OOS:** PF 1.5581 · ret 13.21% · n 88
- **Bootstrap CI lower (mean R):** -1.9495
- **Veredicto:** KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra)
- **Artefacto (run_id):** `dfab81a68433a1fd`

### funding-timestamp run-up
- `p100screen` · BASKET6 1h · celda `id=83` · **⚠FRÁGIL (OOS n<200)**
- **IS:** PF 1.1080 · ret 24.24% · n 125 · DD -26.54%
- **OOS:** PF 1.4419 · ret 37.48% · n 53
- **Bootstrap CI lower (mean R):** -0.0024
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `8fb60fa563d679ae`

### volume-climax reversal
- `p100screen` · HYPEUSDT 1h · celda `id=60` · **⚠FRÁGIL (OOS n<200)**
- **IS:** PF 1.0964 · ret 1.59% · n 50 · DD -8.49%
- **OOS:** PF 1.3555 · ret 23.54% · n 141
- **Bootstrap CI lower (mean R):** -0.1636
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `78649953dd61f9b1`

### Motor qs097: variante cuantitativa con filtros de régimen.
- `qs097` · HYPEUSDT 1h · celda `card=HYPEUSDT` · **⚠FRÁGIL (OOS n<200)**
- **IS:** PF 1.1805 · ret 10.55% · n 162 · DD -12.03%
- **OOS:** PF 1.3549 · ret 7.43% · n 55
- **Bootstrap CI lower (mean R):** -16.5086
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `6f5ec1d20c40a815`

### multi-timeframe trend + pullback
- `p100screen` · BASKET6 1h · celda `id=90` · **⚠FRÁGIL (OOS n<200)**
- **IS:** PF 1.1430 · ret 39.59% · n 124 · DD -38.87%
- **OOS:** PF 1.3358 · ret 20.07% · n 53
- **Bootstrap CI lower (mean R):** -0.0043
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `f7fe875c09b5c786`

### Motor qs097: variante cuantitativa con filtros de régimen.
- `qs097` · JUPUSDT 1h · celda `card=JUPUSDT` · **⚠FRÁGIL (OOS n<200)**
- **IS:** PF 0.8487 · ret -6.98% · n 158 · DD -16.31%
- **OOS:** PF 1.2925 · ret 3.11% · n 42
- **Bootstrap CI lower (mean R):** -15.5268
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `58d3c47abbc41ee5`

### Tendencia con HMA (Hull MA) simple.
- `trend_hma_simple` · XRPUSDT 1h · celda `card=XRPUSDT` · **⚠FRÁGIL (OOS n<200)**
- **IS:** PF 1.2265 · ret 19.63% · n 104 · DD -15.87%
- **OOS:** PF 1.2804 · ret 5.02% · n 34
- **Bootstrap CI lower (mean R):** -33.7528
- **Veredicto:** KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs)
- **Artefacto (run_id):** `25f2aeb618b8c6ee`

### Motor qs097: variante cuantitativa con filtros de régimen.
- `qs097` · ETHUSDT 1h · celda `card=ETHUSDT`
- **IS:** PF 1.2336 · ret 25.99% · n 306 · DD -16.03%
- **OOS:** PF 1.2336 · ret 25.99% · n 306
- **Bootstrap CI lower (mean R):** -7.1405
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `50b60069f86c09ec`

### Tendencia con HMA (Hull MA) simple.
- `trend_hma_simple` · 1000PEPEUSDT 1h · celda `card=1000PEPEUSDT` · **⚠FRÁGIL (OOS n<200)**
- **IS:** PF 0.9067 · ret -12.14% · n 123 · DD -43.14%
- **OOS:** PF 1.1916 · ret 5.15% · n 35
- **Bootstrap CI lower (mean R):** -65.0413
- **Veredicto:** KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs)
- **Artefacto (run_id):** `543fbb65010d7a55`

### Motor qs097: variante cuantitativa con filtros de régimen.
- `qs097` · SUIUSDT 1h · celda `card=SUIUSDT`
- **IS:** PF 1.1921 · ret 26.08% · n 295 · DD -16.23%
- **OOS:** PF 1.1342 · ret 12.06% · n 210
- **Bootstrap CI lower (mean R):** -12.1402
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `0be0854a2f52fe2e`

### Tendencia con HMA (Hull MA) simple.
- `trend_hma_simple` · ARBUSDT 1h · celda `card=ARBUSDT` · **⚠FRÁGIL (OOS n<200)**
- **IS:** PF 0.7271 · ret -28.53% · n 114 · DD -37.65%
- **OOS:** PF 1.1267 · ret 3.73% · n 37
- **Bootstrap CI lower (mean R):** -62.7364
- **Veredicto:** KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs)
- **Artefacto (run_id):** `3e144011ed676dcf`

### ttm squeeze
- `pack20` · XRPUSDT 1h · celda `16_ttm_squeeze`
- **IS:** PF 1.0483 · ret 488.3% · n 3396 · DD -74.33%
- **OOS:** PF 1.1163 · ret 142.18% · n 874
- **Bootstrap CI lower (mean R):** -0.9676
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `ea426bb3fb821132`

### engulfing-at-extreme
- `p100screen` · JUPUSDT 1h · celda `id=71` · **⚠FRÁGIL (OOS n<200)**
- **IS:** PF 0.6853 · ret -14.55% · n 62 · DD -23.59%
- **OOS:** PF 1.1123 · ret 3.74% · n 43
- **Bootstrap CI lower (mean R):** -0.7402
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `1510aae9976c0d28`

### HTF FVG: fair value gaps en temporalidad superior.
- `htffvg` · JUPUSDT 15m · celda `card=JUPUSDT` · **⚠FRÁGIL (OOS n<200)**
- **IS:** PF 1.0055 · ret 0.97% · n 239 · DD -16.84%
- **OOS:** PF 1.0795 · ret 4.2% · n 72
- **Bootstrap CI lower (mean R):** -18.8362
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `d7cf9f2832cbb19c`

### vwap fade
- `pack20` · SOLUSDT 15m · celda `13_vwap_fade`
- **IS:** PF 1.0775 · ret 405901.02% · n 17850 · DD -76.34%
- **OOS:** PF 1.0792 · ret 457.04% · n 5597
- **Bootstrap CI lower (mean R):** 3.5845
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `44a23ab194b621be`

### TRIX(15) zero-cross
- `p100screen` · BTCUSDT 15m · celda `id=52` · **⚠FRÁGIL (OOS n<200)**
- **IS:** PF 1.1320 · ret 393.4% · n 877 · DD -58.59%
- **OOS:** PF 1.0705 · ret 13.9% · n 179
- **Bootstrap CI lower (mean R):** 0.0139
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `9e93753caa755c27`

### squeeze rank breakout
- `pack20` · SOLUSDT 1h · celda `15_squeeze_rank_breakout`
- **IS:** PF 1.0759 · ret 89.98% · n 684 · DD -33.71%
- **OOS:** PF 1.0650 · ret 14.64% · n 204
- **Bootstrap CI lower (mean R):** -8.462
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `bd9100c8bd70d366`

### triple EMA (8/21/55) pullback
- `p100screen` · ETHUSDT 1h · celda `id=26` · **⚠FRÁGIL (OOS n<200)**
- **IS:** PF 1.2622 · ret 319.04% · n 942 · DD -29.79%
- **OOS:** PF 1.0348 · ret 3.15% · n 183
- **Bootstrap CI lower (mean R):** 0.0471
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `2f8f3ce69d850de1`

### Motor qs097: variante cuantitativa con filtros de régimen.
- `qs097` · BTCUSDT 1h · celda `card=BTCUSDT` · **⚠FRÁGIL (OOS n<200)**
- **IS:** PF 0.9021 · ret -9.22% · n 332 · DD -16.73%
- **OOS:** PF 1.0153 · ret 0.21% · n 104
- **Bootstrap CI lower (mean R):** -11.3451
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `2053d078008e9ba3`

### impulse-bar continuation
- `p100screen` · ETHUSDT 1h · celda `id=45` · **⚠FRÁGIL (OOS n<200)**
- **IS:** PF 1.2748 · ret 264.63% · n 622 · DD -40.94%
- **OOS:** PF 1.0137 · ret 0.78% · n 124
- **Bootstrap CI lower (mean R):** 0.0127
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `df3d84f2bad4b17b`

### range-box breakout strategy with volume confirmation
- `p100screen` · JUPUSDT 1h · celda `id=37`
- **IS:** PF 0.8808 · ret -49.48% · n 1374 · DD -52.08%
- **OOS:** PF 1.0100 · ret 2.67% · n 805
- **Bootstrap CI lower (mean R):** -0.0926
- **Veredicto:** SIN VEREDICTO
- **Artefacto (run_id):** `2f65081b0c480767`

---
*Generado por `code/_top100_catalog.py` (vista OOS/robustez) desde artefactos verificados. Datos: `results/top_oos_robust.json`. Priorización de seguimiento, no recomendación rentable.*