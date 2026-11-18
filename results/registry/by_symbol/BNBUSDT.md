# Por par: BNBUSDT — 18 estrategias


| # | TF | Estrategia | Ret declarado | Ret costo cero | Ret 11bps RT | PF | n | maxDD | Ventana (años) | Veredicto | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1h | ds1 | 248.78 | 248.78 | -51.93 | 1.212 | 2031 | -20.88 | — | medido a 11 bps RT: -51.9% | f68de1cf973c8037 |
| 2 | 1h | ds3 | 91.61 | 91.61 | -7.9 | 1.042 | 320 | -72.43 | — | medido a 11 bps RT: -7.9% | 621aad7cc886dd58 |
| 3 | 1h | botstrat | 50.56 | — | — | 1.833 | 149 | -16.93 | — | SIN VEREDICTO (15m = duplicado del 1h: engine hardcodea 1h) | 79cb2fba8cfc251c |
| 4 | 1h | cvrmd | 8.92 | — | — | 1.22 | 85 | -6.71 | — | FRAGILE/SUSPENDED (PF ~1.02 historia completa) | 1e6d5ad221e0b6eb |
| 5 | 1h | smqe | 6.12 | 16.4 | — | 1.141 | 86 | 7.29 | 6.7 | SUSPENDED (sin OOS posible) | 4f31584e29761698 |
| 6 | 1h | ds5 | -4.3 | — | — | 0.991 | 1355 | -35.01 | — | SIN MEDIR A COSTOS REPO (preset author = costo cero) | f9b16b6a52d55e03 |
| 7 | 1h | fingrad | -16.91 | 23.91 | — | 0.875 | 583 | 24.22 | 6.68 | KILLED (y sin funding en perps: SUI 17.3%->1.6% con funding) | 902a2f886b8f8a31 |
| 8 | 1h | ds2 | -19.35 | — | — | 0.965 | 1412 | -52.95 | — | SIN MEDIR A COSTOS REPO (preset author = costo cero) | 90ba7ad0c68906c1 |
| 9 | 1h | qs096 | -20.7 | -13.59 | — | 0.705 | 298 | -25.01 | — | SIN VEREDICTO | 2770b4aba1ec4c1d |
| 10 | 1h | emaadx | -23.79 | -2.6 | — | 0.92 | 245 | 60.83 | 6.68 | KILLED | 19873d70ce87189b |
| 11 | 1h | ffs | -47.72 | — | — | 0.775 | 374 | -50.34 | — | KILLED (window-pick) | b155825805413aa5 |
| 12 | 1h | ds7 | -65.73 | — | — | 0.88 | 1277 | -79.18 | — | SIN VEREDICTO | 068738bad1d7bb57 |
| 13 | 1h | hmaaoadx | -69.98 | — | — | 0.623 | 918 | -70.22 | 6.7 | SIN VEREDICTO | 22a8d44e90047e9e |
| 14 | 1h | ema921 | -72.73 | 77.98 | — | 0.888 | 2750 | -77.02 | 6.73 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | fcb6d90b325bc19c |
| 15 | 1h | ds6 | -90.36 | — | — | 0.314 | 659 | -90.44 | — | SIN VEREDICTO | 0921926cba254297 |
| 16 | 1h | sax | -94.58 | — | — | 0.866 | 3371 | -95.25 | — | UNRUNNABLE (engine borrado; 49 artefactos huerfanos) | 79ae65432fcc6fba |
| 17 | 15m | ema921 | -96.33 | -11.56 | — | 0.592 | 1794 | -96.39 | 1.11 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | 54b9700825f630a4 |
| 18 | 1h | ds9 | -99.78 | — | — | 0.702 | 3136 | -99.78 | — | SIN VEREDICTO | 28903bf4e45815d7 |
