# Por par: XRPUSDT — 62 estrategias


| # | TF | Estrategia | Ret declarado | Ret costo cero | Ret 11bps RT | PF | n | maxDD | Ventana (años) | Veredicto | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 15m | XRP delta-neutral grid v2 (25 USDT x 10x) | 9388264.86 | — | — | 1.307 | 5975 | 43.42 | 6.81 | KILLED (resolucion 1m: PF 0.93 vs 1.30 en el OOS 2023+; sonda _xrp_1m_resolution.py) | fe5c359a22c8dffe |
| 2 | 15m | XRP delta-neutral grid v1 (10k, 0.25x/lvl) | 1598.19 | — | — | 1.5 | 5888 | 10.18 | 6.81 | KILLED (resolucion 1m: PF 0.93 vs 1.30 en el OOS 2023+; sonda _xrp_1m_resolution.py) | 295c21687960fadd |
| 3 | 1h | ds1 | 411.76 | 411.76 | 5.92 | 1.285 | 2030 | -29.83 | — | medido a 11 bps RT: +5.9% | 11432b7a35eb6fbe |
| 4 | 1h | S02 Donchian + Flow Breakout | 190.62 | — | — | 1.634 | 223 | -26.71 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 90ad4a5727379013 |
| 5 | 1h | S10 Vol-Targeted Time-Series Momentum | 184.18 | — | — | 1.831 | 168 | -20.71 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 90ad4a5727379013 |
| 6 | 15m | botstrat | 54.3 | — | — | 1.424 | 583 | -24.3 | — | SIN VEREDICTO (15m = duplicado del 1h: engine hardcodea 1h) | 4c6b3e46b4ab1533 |
| 7 | 1h | S03 Squeeze Release | 28.4 | — | — | 1.188 | 196 | -12.04 | 2.03 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | db89577d5f9d9d34 |
| 8 | 15m | S10 Vol-Targeted Time-Series Momentum | 16.55 | — | — | 1.031 | 721 | -50.47 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 2477e973a25e9f52 |
| 9 | 1h | botstrat | 7.32 | — | — | 1.144 | 166 | -23.28 | — | SIN VEREDICTO (15m = duplicado del 1h: engine hardcodea 1h) | f063bb055aa6daaa |
| 10 | 15m | S02 Donchian + Flow Breakout | 3.43 | — | — | 1.006 | 654 | -55.72 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 2477e973a25e9f52 |
| 11 | 1h | cvrmd | 2.62 | — | — | 1.06 | 99 | -11.77 | — | FRAGILE/SUSPENDED (PF ~1.02 historia completa) | 5782b8db04b4bdcb |
| 12 | 1h | smqe | 1.5 | 9.21 | — | 1.036 | 100 | 12.19 | 6.8 | SUSPENDED (sin OOS posible) | 12cac307d46702ba |
| 13 | 1h | S01 Taker-Flow Drift Bands | -2.92 | — | — | 0.983 | 278 | -22.61 | 2.03 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | db89577d5f9d9d34 |
| 14 | 1h | fingrad | -10.72 | 15.87 | — | 0.901 | 512 | 15.77 | 6.78 | KILLED (y sin funding en perps: SUI 17.3%->1.6% con funding) | ec2f265c20361cfd |
| 15 | 1h | S07 Funding Extreme Fade | -13.71 | — | — | 0.543 | 41 | -16.0 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 13c4f7e196bc27a0 |
| 16 | 1h | S06 Session Range Breakout (UTC) | -18.08 | — | — | 0.93 | 533 | -35.73 | 2.03 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | db89577d5f9d9d34 |
| 17 | 15m | smqe | -20.11 | 1.98 | — | 0.759 | 152 | 26.61 | 6.8 | SUSPENDED (sin OOS posible) | aeb6dcec82fbcb01 |
| 18 | 15m | S07 Funding Extreme Fade | -21.43 | — | — | 0.723 | 116 | -23.6 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 2477e973a25e9f52 |
| 19 | 1h | S05 HTF Trend Pullback (RSI-2) | -21.54 | — | — | 0.85 | 581 | -26.53 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 90ad4a5727379013 |
| 20 | 5m | smqe | -25.38 | 11.23 | — | 0.706 | 159 | 26.79 | 2.0 | SUSPENDED (sin OOS posible) | 4a1b34c3cf4c5001 |
| 21 | 15m | cvrmd | -26.75 | — | — | 0.859 | 343 | -31.42 | — | FRAGILE/SUSPENDED (PF ~1.02 historia completa) | 2438df16b5088ee8 |
| 22 | 1h | emaadx | -29.58 | -7.72 | — | 0.959 | 270 | 67.93 | 6.78 | KILLED | f49cb9cb80c36ac3 |
| 23 | 1h | S09 Liquidity Sweep Reversal | -30.15 | — | — | 0.759 | 217 | -34.53 | 2.03 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | db89577d5f9d9d34 |
| 24 | 1h | S04 VWAP Fade (range regime only) | -30.33 | — | — | 0.656 | 177 | -33.75 | 2.03 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | db89577d5f9d9d34 |
| 25 | 1h | ds3 | -37.07 | — | — | 0.981 | 310 | -91.21 | — | SIN MEDIR A COSTOS REPO (preset author = costo cero) | 439b38a9a9a2609e |
| 26 | 5m | S07 Funding Extreme Fade | -46.86 | — | — | 0.727 | 282 | -50.17 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | c9ddbff5134e423a |
| 27 | 1h | ds2 | -54.31 | — | — | 0.847 | 1138 | -79.92 | — | SIN MEDIR A COSTOS REPO (preset author = costo cero) | 21ae77d3513516b4 |
| 28 | 1h | ffs | -58.36 | — | — | 0.695 | 393 | -59.74 | — | KILLED (window-pick) | 92a5bd883fec3e1f |
| 29 | 1h | hmaaoadx | -59.97 | — | — | 0.659 | 854 | -61.01 | 6.8 | SIN VEREDICTO | a54be9c72cefc23b |
| 30 | 1h | ds7 | -64.65 | — | — | 0.872 | 1067 | -75.46 | — | SIN VEREDICTO | a997c21e68d16aea |
| 31 | 15m | XRP delta-neutral grid v2 (25 USDT x 10x), fills resolved on 1m | -74.2 | — | — | 0.933 | 3018 | 81.46 | 3.75 | KILLED (el mismo libro resuelto en 1m cae bajo PF 1 en el OOS; artefacto 18d686932bf06f78) | 18d686932bf06f78 |
| 32 | 15m | S06 Session Range Breakout (UTC) | -78.78 | — | — | 0.735 | 693 | -80.5 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 2477e973a25e9f52 |
| 33 | 5m | S10 Vol-Targeted Time-Series Momentum | -82.8 | — | — | 0.923 | 2172 | -93.34 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | c9ddbff5134e423a |
| 34 | 1h | ds6 | -83.67 | — | — | 0.516 | 704 | -83.67 | — | SIN VEREDICTO | 76af36f653015376 |
| 35 | 15m | ffs | -84.17 | — | — | 0.838 | 1386 | -84.36 | — | KILLED (window-pick) | 1855e3a9ca59da0b |
| 36 | 15m | S03 Squeeze Release | -85.12 | — | — | 0.692 | 756 | -85.36 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 2477e973a25e9f52 |
| 37 | 1h | ds5 | -85.23 | — | — | 0.646 | 1304 | -88.9 | — | SIN MEDIR A COSTOS REPO (preset author = costo cero) | 91db3aa70062a247 |
| 38 | 15m | S04 VWAP Fade (range regime only) | -85.91 | — | — | 0.646 | 885 | -86.23 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 2477e973a25e9f52 |
| 39 | 15m | S05 HTF Trend Pullback (RSI-2) | -91.74 | — | — | 0.645 | 1874 | -91.85 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 2477e973a25e9f52 |
| 40 | 15m | S01 Taker-Flow Drift Bands | -92.41 | — | — | 0.824 | 1389 | -93.86 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 2477e973a25e9f52 |
| 41 | 5m | S06 Session Range Breakout (UTC) | -93.34 | — | — | 0.613 | 768 | -93.5 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | c9ddbff5134e423a |
| 42 | 1h | sax | -94.41 | — | — | 0.778 | 2888 | -95.19 | — | UNRUNNABLE (engine borrado; 49 artefactos huerfanos) | 5b75ec0806377dd4 |
| 43 | 1m | S06 Session Range Breakout (UTC) | -94.74 | — | — | 0.51 | 818 | -94.74 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 9ced74c7386c9cd2 |
| 44 | 15m | S09 Liquidity Sweep Reversal | -96.19 | — | — | 0.632 | 947 | -96.24 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 2477e973a25e9f52 |
| 45 | 15m | fingrad | -97.66 | -44.23 | — | 0.603 | 3155 | 97.7 | 6.79 | KILLED (y sin funding en perps: SUI 17.3%->1.6% con funding) | c7ad26c152e51f5c |
| 46 | 1m | S07 Funding Extreme Fade | -99.27 | — | — | 0.585 | 1469 | -99.31 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 9ced74c7386c9cd2 |
| 47 | 5m | S02 Donchian + Flow Breakout | -99.33 | — | — | 0.731 | 1791 | -99.38 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | c9ddbff5134e423a |
| 48 | 1h | ds9 | -99.63 | — | — | 0.831 | 3205 | -99.67 | — | SIN VEREDICTO | 3dc4af02c24e31a5 |
| 49 | 5m | S04 VWAP Fade (range regime only) | -99.73 | — | — | 0.723 | 2690 | -99.75 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | c9ddbff5134e423a |
| 50 | 5m | S03 Squeeze Release | -99.8 | — | — | 0.582 | 1755 | -99.8 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | c9ddbff5134e423a |
| 51 | 5m | S09 Liquidity Sweep Reversal | -99.98 | — | — | 0.688 | 2568 | -99.98 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | c9ddbff5134e423a |
| 52 | 5m | S05 HTF Trend Pullback (RSI-2) | -100.0 | — | — | 0.432 | 4391 | -100.0 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | c9ddbff5134e423a |
| 53 | 15m | sax | -100.0 | — | — | 0.741 | 12602 | -100.0 | — | UNRUNNABLE (engine borrado; 49 artefactos huerfanos) | 3638c5f2a9983f93 |
| 54 | 5m | S01 Taker-Flow Drift Bands | -100.0 | — | — | 0.715 | 4666 | -100.0 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | c9ddbff5134e423a |
| 55 | 1m | S03 Squeeze Release | -100.0 | — | — | 0.411 | 5561 | -100.0 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 9ced74c7386c9cd2 |
| 56 | 1m | S01 Taker-Flow Drift Bands | -100.0 | — | — | 0.292 | 25573 | -100.0 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 9ced74c7386c9cd2 |
| 57 | 1m | S02 Donchian + Flow Breakout | -100.0 | — | — | 0.606 | 9390 | -100.0 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 9ced74c7386c9cd2 |
| 58 | 1m | S04 VWAP Fade (range regime only) | -100.0 | — | — | 0.47 | 13378 | -100.0 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 9ced74c7386c9cd2 |
| 59 | 1m | S05 HTF Trend Pullback (RSI-2) | -100.0 | — | — | 0.07 | 18709 | -100.0 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 9ced74c7386c9cd2 |
| 60 | 1m | S09 Liquidity Sweep Reversal | -100.0 | — | — | 0.373 | 10483 | -100.0 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 9ced74c7386c9cd2 |
| 61 | 1m | S10 Vol-Targeted Time-Series Momentum | -100.0 | — | — | 0.565 | 12065 | -100.0 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 9ced74c7386c9cd2 |
| 62 | 1m | sax | -100.0 | — | — | 0.282 | 115438 | -100.0 | — | UNRUNNABLE (engine borrado; 49 artefactos huerfanos) | a7d7b519079f0329 |
