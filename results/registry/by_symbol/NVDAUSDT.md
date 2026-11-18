# Por par: NVDAUSDT — 9 estrategias


| # | TF | Estrategia | Ret declarado | Ret costo cero | Ret 11bps RT | PF | n | maxDD | Ventana (años) | Veredicto | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1h | qs096 | 9.88 | 12.9 | — | 2.612 | 16 | -3.64 | — | SIN VEREDICTO | c5d7c8d3ad8af6ac |
| 2 | 1h | ema921 | 7.36 | 29.42 | — | 1.154 | 134 | -13.89 | 0.42 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | 5e3f98cc35604871 |
| 3 | 15m | qs096 | 4.36 | 20.63 | — | 1.116 | 85 | -14.95 | — | SIN VEREDICTO | 9a869c49aaa083d6 |
| 4 | 1h | card=NVDAUSDT | -2.62 | -2.62 | — | 0.96 | 125 | 23.44 | 0.34 | KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs) | 992a0531585148e0 |
| 5 | 1d | weekend-gap fade | -7.55 | -6.43 | — | 0.594 | 10 | 14.65 | 0.64 | KILLED 0/48 | 393b1cea0eed70b2 |
| 6 | 5m | id=141 | -22.62 | — | — | 0.575 | 252 | -25.96 | — | KILLED 0/37 (ruina por costes en intradia; ninguna celda pasa la bateria estandar) | 99ef4ec447372fc0 |
| 7 | 5m | id=144 | -32.97 | — | — | 0.056 | 67 | -32.97 | — | KILLED 0/37 (ruina por costes en intradia; ninguna celda pasa la bateria estandar) | 46d1df678d923890 |
| 8 | 15m | ema921 | -75.52 | 20.75 | — | 0.468 | 580 | -76.86 | 0.41 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | 038d536e63fd7345 |
| 9 | 5m | ema921 | -99.76 | 9.71 | — | 0.364 | 1649 | -99.77 | 0.41 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | 457797799495720c |
