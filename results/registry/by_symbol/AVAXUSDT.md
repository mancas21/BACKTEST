# Por par: AVAXUSDT — 18 estrategias


| # | TF | Estrategia | Ret declarado | Ret costo cero | Ret 11bps RT | PF | n | maxDD | Ventana (años) | Veredicto | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1h | ds1 | 289.49 | 289.49 | 34.4 | 1.269 | 1831 | -25.9 | — | medido a 11 bps RT: +34.4% | 7e2a351fb3d6de1a |
| 2 | 1h | ds3 | 193.07 | 193.07 | 51.2 | 1.013 | 300 | -95.88 | — | medido a 11 bps RT: +51.2% | ecf8f6a13d502014 |
| 3 | 1h | botstrat | 51.41 | — | — | 1.525 | 146 | -21.47 | — | SIN VEREDICTO (15m = duplicado del 1h: engine hardcodea 1h) | 80ed06ac9997dd63 |
| 4 | 1h | qs096 | 4.51 | 13.64 | — | 1.049 | 255 | -14.0 | — | SIN VEREDICTO | c29b5798f9f69df7 |
| 5 | 1h | fingrad | 4.28 | 39.58 | — | 1.025 | 764 | 18.07 | 6.07 | KILLED (y sin funding en perps: SUI 17.3%->1.6% con funding) | d3f416558ec09e59 |
| 6 | 1h | cvrmd | 0.5 | — | — | 1.019 | 90 | -12.38 | — | FRAGILE/SUSPENDED (PF ~1.02 historia completa) | c86439c3c5534fac |
| 7 | 1h | smqe | -1.33 | 3.76 | — | 0.97 | 91 | 12.58 | 6.08 | SUSPENDED (sin OOS posible) | 8084f24e5fde8ec5 |
| 8 | 1h | emaadx | -9.61 | 11.84 | — | 0.981 | 213 | 44.28 | 6.07 | KILLED | 8af35224ae3770d5 |
| 9 | 1h | hmaaoadx | -22.97 | — | — | 0.87 | 787 | -27.75 | 6.08 | SIN VEREDICTO | 1d2762499a8ab429 |
| 10 | 1h | ema921 | -27.04 | 79.77 | — | 0.96 | 2391 | -36.98 | 6.11 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | 24b242051b5957a7 |
| 11 | 1h | ds7 | -31.65 | — | — | 0.98 | 946 | -85.81 | — | SIN VEREDICTO | 5b4b9ecba4bf8833 |
| 12 | 1h | sax | -32.31 | — | — | 0.982 | 3120 | -55.46 | — | UNRUNNABLE (engine borrado; 49 artefactos huerfanos) | 4e09efe2c3d70396 |
| 13 | 1h | ds5 | -32.47 | — | — | 0.909 | 1012 | -65.86 | — | SIN MEDIR A COSTOS REPO (preset author = costo cero) | 4f4160d7b52a04a4 |
| 14 | 1h | ffs | -46.52 | — | — | 0.708 | 306 | -49.64 | — | KILLED (window-pick) | cb7d8733cfbd8e46 |
| 15 | 1h | ds2 | -63.23 | — | — | 0.862 | 1368 | -76.18 | — | SIN MEDIR A COSTOS REPO (preset author = costo cero) | 58baf5d2d46b23fb |
| 16 | 1h | ds6 | -82.48 | — | — | 0.69 | 655 | -86.7 | — | SIN VEREDICTO | 88e438bd901c6377 |
| 17 | 15m | ema921 | -86.9 | -3.76 | — | 0.703 | 1815 | -87.5 | 1.11 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | c64f79068659b9eb |
| 18 | 1h | ds9 | -98.32 | — | — | 0.912 | 2852 | -99.05 | — | SIN VEREDICTO | 801803b176683d77 |
