# Por par: LINKUSDT — 17 estrategias


| # | TF | Estrategia | Ret declarado | Ret costo cero | Ret 11bps RT | PF | n | maxDD | Ventana (años) | Veredicto | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1h | ds1 | 291.27 | 291.27 | 17.36 | 1.283 | 2001 | -18.22 | — | medido a 11 bps RT: +17.4% | afa8324fb46f8ff4 |
| 2 | 1h | emaadx | 168.68 | 236.65 | — | 1.143 | 226 | 34.69 | 6.78 | KILLED | d91d4860ad35c60d |
| 3 | 1h | ds5 | 55.0 | 55.0 | -90.41 | 1.111 | 1241 | -62.82 | — | medido a 11 bps RT: -90.4% | 365bef751f370f6c |
| 4 | 1h | qs096 | 1.87 | 7.59 | — | 1.02 | 291 | -18.68 | — | SIN VEREDICTO | b29f619911482c3c |
| 5 | 1h | botstrat | -7.75 | — | — | 0.934 | 160 | -27.95 | — | SIN VEREDICTO (15m = duplicado del 1h: engine hardcodea 1h) | 9118223dee1efba7 |
| 6 | 1h | smqe | -12.3 | -9.81 | — | 0.456 | 41 | 13.72 | 6.77 | SUSPENDED (sin OOS posible) | 496eff6efc05029e |
| 7 | 1h | cvrmd | -13.02 | — | — | 0.757 | 97 | -17.54 | — | FRAGILE/SUSPENDED (PF ~1.02 historia completa) | f483544f77f343d0 |
| 8 | 1h | fingrad | -21.93 | -1.26 | — | 0.805 | 578 | 23.16 | 6.75 | KILLED (y sin funding en perps: SUI 17.3%->1.6% con funding) | 6fd245c24170ff8e |
| 9 | 1h | ffs | -35.91 | — | — | 0.833 | 328 | -37.9 | — | KILLED (window-pick) | 413474ab8e691aee |
| 10 | 1h | ema921 | -46.59 | 48.6 | — | 0.932 | 2613 | -56.51 | 6.79 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | e27446c19ccc2a97 |
| 11 | 1h | ds2 | -47.44 | — | — | 0.905 | 1462 | -64.29 | — | SIN MEDIR A COSTOS REPO (preset author = costo cero) | 27bd4f99529e53d5 |
| 12 | 1h | hmaaoadx | -51.58 | — | — | 0.699 | 899 | -52.68 | 6.77 | SIN VEREDICTO | 39ed1a63df3467e5 |
| 13 | 1h | ds7 | -53.56 | — | — | 0.93 | 1173 | -80.25 | — | SIN VEREDICTO | 686beb73e0fe2fcc |
| 14 | 1h | ds3 | -84.45 | — | — | 0.918 | 336 | -97.94 | — | SIN MEDIR A COSTOS REPO (preset author = costo cero) | c368685dd81cb7f7 |
| 15 | 1h | sax | -90.13 | — | — | 0.892 | 3392 | -90.57 | — | UNRUNNABLE (engine borrado; 49 artefactos huerfanos) | 6edff58ca1e32e5f |
| 16 | 1h | ds6 | -91.14 | — | — | 0.492 | 717 | -91.16 | — | SIN VEREDICTO | ddf34f6fde856d40 |
| 17 | 1h | ds9 | -99.82 | — | — | 0.813 | 3115 | -99.82 | — | SIN VEREDICTO | c3c4224788c9727f |
