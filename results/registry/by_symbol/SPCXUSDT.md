# Por par: SPCXUSDT — 8 estrategias


| # | TF | Estrategia | Ret declarado | Ret costo cero | Ret 11bps RT | PF | n | maxDD | Ventana (años) | Veredicto | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1h | qs096 | 14.78 | 12.8 | — | 3.026 | 15 | -7.76 | — | SIN VEREDICTO | 0a01daba59fc6683 |
| 2 | 1d | weekend-gap fade | 10.89 | 12.35 | — | 1.98 | 11 | 7.99 | 0.48 | KILLED 0/48 | d00c72b58dc3b80e |
| 3 | 5m | id=150 | -9.09 | — | — | 0.0 | 17 | -9.09 | — | KILLED 0/37 (ruina por costes en intradia; ninguna celda pasa la bateria estandar) | 1fa4a9eaaef8dfd1 |
| 4 | 15m | qs096 | -12.18 | -7.42 | — | 0.711 | 93 | -22.1 | — | SIN VEREDICTO | 999b7292cf3623be |
| 5 | 1h | ema921 | -13.77 | -2.84 | — | 0.744 | 149 | -19.13 | 0.42 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | 50f2ceec710bc42e |
| 6 | 1h | card=SPCXUSDT | -25.55 | -25.55 | — | 0.765 | 120 | 41.92 | 0.34 | KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs) | 634f1688adbf209b |
| 7 | 15m | ema921 | -76.55 | -18.26 | — | 0.487 | 647 | -78.11 | 0.42 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | d951ff1f11b14448 |
| 8 | 5m | ema921 | -98.09 | 107.15 | — | 0.558 | 1708 | -98.13 | 0.42 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | 07054c31ab45418c |
