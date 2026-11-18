# Por par: ARBUSDT — 18 estrategias


| # | TF | Estrategia | Ret declarado | Ret costo cero | Ret 11bps RT | PF | n | maxDD | Ventana (años) | Veredicto | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1h | S02 Donchian + Flow Breakout | 57.17 | — | — | 1.325 | 226 | -18.88 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 10eba614697a8f9c |
| 2 | 1h | S09 Liquidity Sweep Reversal | 26.92 | — | — | 1.191 | 214 | -11.89 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 10eba614697a8f9c |
| 3 | 1h | S03 Squeeze Release | 16.32 | — | — | 1.129 | 172 | -16.54 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 10eba614697a8f9c |
| 4 | 1h | S10 Vol-Targeted Time-Series Momentum | 11.91 | — | — | 1.111 | 172 | -17.41 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 10eba614697a8f9c |
| 5 | 1h | S04 VWAP Fade (range regime only) | 5.47 | — | — | 1.052 | 189 | -21.43 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 10eba614697a8f9c |
| 6 | 1d | S05 HTF Trend Pullback (RSI-2) | -1.47 | — | — | 0.508 | 10 | -2.58 | 0.87 | KILLED 0/7 (QQQ; ninguna bate B&H) | 9935f847764ca31f |
| 7 | 1d | ema921 | -1.88 | -1.82 | — | 0.476 | 10 | -3.66 | 0.87 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | 568594626978297f |
| 8 | 1h | S07 Funding Extreme Fade | -3.7 | — | — | 0.85 | 35 | -10.92 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 10eba614697a8f9c |
| 9 | 15m | qs096 | -11.13 | 0.33 | — | 0.888 | 373 | -22.33 | — | SIN VEREDICTO | ff432d2629e1024a |
| 10 | 1h | qs096 | -14.05 | -12.93 | — | 0.424 | 67 | -14.37 | — | SIN VEREDICTO | b656de4f0c03f518 |
| 11 | 1h | S05 HTF Trend Pullback (RSI-2) | -16.12 | — | — | 0.89 | 616 | -21.36 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 10eba614697a8f9c |
| 12 | 1h | S01 Taker-Flow Drift Bands | -20.85 | — | — | 0.89 | 302 | -22.95 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 10eba614697a8f9c |
| 13 | 1h | card=ARBUSDT | -28.53 | -28.53 | — | 0.727 | 114 | 37.65 | 0.34 | KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs) | 3e144011ed676dcf |
| 14 | 1h | S06 Session Range Breakout (UTC) | -33.84 | — | — | 0.862 | 508 | -46.91 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 10eba614697a8f9c |
| 15 | 1d | weekend-gap fade | -34.41 | -31.86 | — | 0.57 | 32 | 44.12 | 0.87 | KILLED 0/48 | 1f43030f517d71d5 |
| 16 | 1h | ema921 | -38.36 | -18.73 | — | 0.836 | 820 | -42.71 | 2.0 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | c5fd2fe692693968 |
| 17 | 15m | ema921 | -88.3 | 26.72 | — | 0.826 | 3160 | -90.42 | 2.0 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | da0c387b3e8aaf3e |
| 18 | 5m | ema921 | -100.0 | 146.96 | — | 0.749 | 9800 | -100.0 | 2.0 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | 936be43e12f25203 |
