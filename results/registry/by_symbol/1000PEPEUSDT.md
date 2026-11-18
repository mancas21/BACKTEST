# Por par: 1000PEPEUSDT — 5 estrategias


| # | TF | Estrategia | Ret declarado | Ret costo cero | Ret 11bps RT | PF | n | maxDD | Ventana (años) | Veredicto | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1d | weekend-gap fade | 53.63 | 59.84 | — | 1.765 | 34 | 29.17 | 0.87 | KILLED 0/48 | 3586a215c95d6d87 |
| 2 | 1h | card=1000PEPEUSDT | -12.14 | -12.14 | — | 0.907 | 123 | 43.14 | 0.34 | KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs) | 543fbb65010d7a55 |
| 3 | 1h | ema921 | -18.11 | -12.34 | — | 0.621 | 151 | -19.69 | 0.36 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | 62fc20a4a1f349fd |
| 4 | 1d | 16_ttm_squeeze | -21.13 | -19.93 | — | 0.607 | 13 | -40.41 | 0.87 | SIN VEREDICTO | 6b201bf3ac5c4078 |
| 5 | 15m | ema921 | -56.06 | -22.42 | — | 0.606 | 625 | -57.2 | 0.36 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | f72e4a01cb0e5c36 |
