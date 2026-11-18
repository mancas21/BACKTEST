# Por par: NEARUSDT — 18 estrategias


| # | TF | Estrategia | Ret declarado | Ret costo cero | Ret 11bps RT | PF | n | maxDD | Ventana (años) | Veredicto | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1h | ds1 | 206.32 | 206.32 | 16.87 | 1.236 | 1854 | -15.57 | — | medido a 11 bps RT: +16.9% | c20fbec817f6087d |
| 2 | 1h | ds7 | 32.66 | — | — | 1.021 | 1023 | -61.38 | — | SIN VEREDICTO | d9bab10e9203cd71 |
| 3 | 1h | qs096 | 20.69 | 29.18 | — | 1.173 | 279 | -13.31 | — | SIN VEREDICTO | da9f1b3771077f89 |
| 4 | 1h | ds3 | 13.34 | — | — | 1.006 | 282 | -91.9 | — | SIN MEDIR A COSTOS REPO (preset author = costo cero) | 2a900e46df06499a |
| 5 | 1h | fingrad | 12.8 | 42.85 | — | 1.064 | 732 | 17.21 | 6.01 | KILLED (y sin funding en perps: SUI 17.3%->1.6% con funding) | 3a95eb2619db6e5b |
| 6 | 1h | botstrat | 9.55 | — | — | 1.137 | 143 | -12.86 | — | SIN VEREDICTO (15m = duplicado del 1h: engine hardcodea 1h) | 9e6e85ff95700ef5 |
| 7 | 1h | cvrmd | -6.45 | — | — | 0.858 | 81 | -8.97 | — | FRAGILE/SUSPENDED (PF ~1.02 historia completa) | 2a295b1756338181 |
| 8 | 1h | emaadx | -6.69 | 14.83 | — | 0.989 | 207 | 49.43 | 6.01 | KILLED | 7d13b9d8f0bce6a4 |
| 9 | 1h | ema921 | -6.99 | 109.61 | — | 0.99 | 2388 | -43.13 | 6.05 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | fda8a5fbb6ace66b |
| 10 | 1h | smqe | -7.79 | -5.59 | — | 0.687 | 45 | 8.24 | 6.02 | SUSPENDED (sin OOS posible) | 34052e48cc7eb503 |
| 11 | 1h | hmaaoadx | -34.78 | — | — | 0.795 | 811 | -38.85 | 6.02 | SIN VEREDICTO | 23fefd761dbdbed7 |
| 12 | 1h | ffs | -55.52 | — | — | 0.67 | 324 | -58.35 | — | KILLED (window-pick) | 3001e53cce8648a4 |
| 13 | 1h | ds5 | -63.26 | — | — | 0.86 | 1116 | -75.42 | — | SIN MEDIR A COSTOS REPO (preset author = costo cero) | 12d65f65333e8b98 |
| 14 | 1h | ds2 | -71.73 | — | — | 0.837 | 1353 | -77.7 | — | SIN MEDIR A COSTOS REPO (preset author = costo cero) | c556b4e395c0545e |
| 15 | 1h | sax | -77.9 | — | — | 0.949 | 2939 | -84.9 | — | UNRUNNABLE (engine borrado; 49 artefactos huerfanos) | 181cc07917f16b3c |
| 16 | 1h | ds6 | -83.36 | — | — | 0.65 | 714 | -85.75 | — | SIN VEREDICTO | 6283feea158ba8fb |
| 17 | 15m | ema921 | -83.94 | -30.6 | — | 0.756 | 1833 | -85.39 | 1.11 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | d9ac6e6c9c846596 |
| 18 | 1h | ds9 | -99.71 | — | — | 0.85 | 2732 | -99.78 | — | SIN VEREDICTO | d8291de31a75dc21 |
