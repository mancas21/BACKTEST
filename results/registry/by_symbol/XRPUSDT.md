# Por par: XRPUSDT — 111 estrategias


| # | TF | Estrategia | Ret declarado | Ret costo cero | Ret 11bps RT | PF | n | maxDD | Ventana (años) | Veredicto | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 15m | XRP delta-neutral grid v2 (25 USDT x 10x) | 9388264.86 | — | — | 1.307 | 5975 | 43.42 | 6.81 | KILLED (resolucion 1m: PF 0.93 vs 1.30 en el OOS 2023+; sonda _xrp_1m_resolution.py) | fe5c359a22c8dffe |
| 2 | 15m | XRP delta-neutral grid v1 (10k, 0.25x/lvl) | 1598.19 | — | — | 1.5 | 5888 | 10.18 | 6.81 | KILLED (resolucion 1m: PF 0.93 vs 1.30 en el OOS 2023+; sonda _xrp_1m_resolution.py) | 295c21687960fadd |
| 3 | 1h | 16_ttm_squeeze | 488.3 | 24536.48 | — | 1.048 | 3396 | -74.33 | 6.82 | SIN VEREDICTO | ea426bb3fb821132 |
| 4 | 1h | ds1 | 411.76 | 411.76 | 5.92 | 1.285 | 2030 | -29.83 | — | medido a 11 bps RT: +5.9% | 11432b7a35eb6fbe |
| 5 | 1h | 17_atr_vol_breakout | 331.12 | 541.29 | — | 1.209 | 361 | -61.22 | 6.82 | SIN VEREDICTO | 0d78d36f19b8f49f |
| 6 | 1h | S02 Donchian + Flow Breakout | 190.62 | — | — | 1.634 | 223 | -26.71 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 90ad4a5727379013 |
| 7 | 1h | S10 Vol-Targeted Time-Series Momentum | 184.18 | — | — | 1.831 | 168 | -20.71 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 90ad4a5727379013 |
| 8 | 15m | botstrat | 54.3 | — | — | 1.424 | 583 | -24.3 | — | SIN VEREDICTO (15m = duplicado del 1h: engine hardcodea 1h) | 4c6b3e46b4ab1533 |
| 9 | 1h | S03 Squeeze Release | 28.4 | — | — | 1.188 | 196 | -12.04 | 2.03 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 2e93a59efb8170b0 |
| 10 | 1h | 02_order_block | 27.77 | 311.44 | — | 1.007 | 1062 | -81.13 | 6.82 | SIN VEREDICTO | b40c0d432705fc83 |
| 11 | 15m | 13_vwap_fade | 25.62 | 70107557800.95 | — | 1.002 | 18320 | -93.33 | 6.84 | SIN VEREDICTO | 310b62e31caa2c3d |
| 12 | 1h | 01_liq_fvg | 25.5 | 51.68 | — | 1.094 | 172 | -29.66 | 6.82 | SIN VEREDICTO | 52677740cad35881 |
| 13 | 1h | qs096 | 24.74 | 36.02 | — | 1.275 | 286 | -16.72 | — | SIN VEREDICTO | c4ad405b3c428ce5 |
| 14 | 1h | card=XRPUSDT | 19.63 | 19.63 | — | 1.226 | 104 | 15.87 | 0.34 | KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs) | 25f2aeb618b8c6ee |
| 15 | 15m | S10 Vol-Targeted Time-Series Momentum | 16.55 | — | — | 1.031 | 721 | -50.47 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 2477e973a25e9f52 |
| 16 | 1h | botstrat | 7.32 | — | — | 1.144 | 166 | -23.28 | — | SIN VEREDICTO (15m = duplicado del 1h: engine hardcodea 1h) | f063bb055aa6daaa |
| 17 | 15m | S02 Donchian + Flow Breakout | 3.43 | — | — | 1.006 | 654 | -55.72 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 2477e973a25e9f52 |
| 18 | 1h | cvrmd | 2.62 | — | — | 1.06 | 99 | -11.77 | — | FRAGILE/SUSPENDED (PF ~1.02 historia completa) | 45ccfbbb288a7ea7 |
| 19 | 1h | smqe | 1.5 | 9.21 | — | 1.036 | 100 | 12.19 | 6.8 | SUSPENDED (sin OOS posible) | 12cac307d46702ba |
| 20 | 1h | smqe11 | 0.9 | 9.42 | — | 1.019 | 102 | 12.91 | 6.82 | SIN VEREDICTO | 485251f8f069c2a0 |
| 21 | 1h | S01 Taker-Flow Drift Bands | -2.92 | — | — | 0.983 | 278 | -22.61 | 2.03 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 2e93a59efb8170b0 |
| 22 | 1d | ema921 | -3.02 | -2.86 | — | 0.333 | 14 | -3.7 | 0.87 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | df2da63773fd4cab |
| 23 | 1h | fingrad | -10.72 | 15.87 | — | 0.901 | 512 | 15.77 | 6.78 | KILLED (y sin funding en perps: SUI 17.3%->1.6% con funding) | ec2f265c20361cfd |
| 24 | 1h | S07 Funding Extreme Fade | -13.71 | — | — | 0.543 | 41 | -16.0 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 13c4f7e196bc27a0 |
| 25 | 1d | 16_ttm_squeeze | -15.29 | -14.06 | — | 0.494 | 13 | -21.84 | 0.87 | SIN VEREDICTO | 59096d3e022a64dd |
| 26 | 1h | S06 Session Range Breakout (UTC) | -18.08 | — | — | 0.93 | 533 | -35.73 | 2.03 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 2e93a59efb8170b0 |
| 27 | 15m | smqe | -20.11 | 1.98 | — | 0.759 | 152 | 26.61 | 6.8 | SUSPENDED (sin OOS posible) | aeb6dcec82fbcb01 |
| 28 | 1d | weekend-gap fade | -21.37 | -18.61 | — | 0.648 | 29 | 29.77 | 0.87 | KILLED 0/48 | 4fb38bf8a47fa642 |
| 29 | 15m | S07 Funding Extreme Fade | -21.43 | — | — | 0.723 | 116 | -23.6 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 2477e973a25e9f52 |
| 30 | 1h | S05 HTF Trend Pullback (RSI-2) | -21.54 | — | — | 0.85 | 581 | -26.53 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 90ad4a5727379013 |
| 31 | 15m | 01_liq_fvg | -25.12 | -21.07 | — | 0.465 | 48 | -27.0 | 6.84 | SIN VEREDICTO | 64d773454c617148 |
| 32 | 5m | smqe | -25.38 | 11.23 | — | 0.706 | 159 | 26.79 | 2.0 | SUSPENDED (sin OOS posible) | 4a1b34c3cf4c5001 |
| 33 | 15m | cvrmd | -26.75 | — | — | 0.859 | 343 | -31.42 | — | FRAGILE/SUSPENDED (PF ~1.02 historia completa) | 2438df16b5088ee8 |
| 34 | 1h | emaadx | -29.58 | -7.72 | — | 0.959 | 270 | 67.93 | 6.78 | KILLED | f49cb9cb80c36ac3 |
| 35 | 1h | S09 Liquidity Sweep Reversal | -30.15 | — | — | 0.759 | 217 | -34.53 | 2.03 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 2e93a59efb8170b0 |
| 36 | 1h | S04 VWAP Fade (range regime only) | -30.33 | — | — | 0.656 | 177 | -33.75 | 2.03 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 2e93a59efb8170b0 |
| 37 | 1h | 15_squeeze_rank_breakout | -30.67 | 43.3 | — | 0.945 | 661 | -39.6 | 6.82 | SIN VEREDICTO | d2167d697439c667 |
| 38 | 1h | ds3 | -37.07 | — | — | 0.981 | 310 | -91.21 | — | SIN MEDIR A COSTOS REPO (preset author = costo cero) | 439b38a9a9a2609e |
| 39 | 5m | S07 Funding Extreme Fade | -46.86 | — | — | 0.727 | 282 | -50.17 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | c9ddbff5134e423a |
| 40 | 1h | 10_rsi2_connors | -52.46 | 702.3 | — | 0.972 | 2568 | -78.56 | 6.82 | SIN VEREDICTO | c096c32622c34efc |
| 41 | 1h | ds2 | -54.31 | — | — | 0.847 | 1138 | -79.92 | — | SIN MEDIR A COSTOS REPO (preset author = costo cero) | 21ae77d3513516b4 |
| 42 | 1h | ffs | -58.36 | — | — | 0.695 | 393 | -59.74 | — | KILLED (window-pick) | 92a5bd883fec3e1f |
| 43 | 1h | hmaaoadx | -59.97 | — | — | 0.659 | 854 | -61.01 | 6.8 | SIN VEREDICTO | a54be9c72cefc23b |
| 44 | 1h | ds7 | -64.65 | — | — | 0.872 | 1067 | -75.46 | — | SIN VEREDICTO | a997c21e68d16aea |
| 45 | 1h | ema921 | -70.45 | 42.25 | — | 0.867 | 2773 | -72.59 | 6.82 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | b1f26549049a3e42 |
| 46 | 1h | 14_ou_stationary_fade | -72.77 | -34.79 | — | 0.91 | 791 | -79.03 | 6.82 | SIN VEREDICTO | f18122f1b1fd2f43 |
| 47 | 15m | xrpneutral1m | -74.2 | — | — | 0.933 | 3018 | 81.46 | 3.75 | KILLED (el mismo libro resuelto en 1m cae bajo PF 1 en el OOS; artefacto 18d686932bf06f78) | 18d686932bf06f78 |
| 48 | 1h | 06_ema_pullback | -74.22 | -14.04 | — | 0.922 | 1094 | -81.23 | 6.82 | SIN VEREDICTO | 7c375764799c8527 |
| 49 | 15m | S06 Session Range Breakout (UTC) | -78.78 | — | — | 0.735 | 693 | -80.5 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 2477e973a25e9f52 |
| 50 | 1h | 09_macd_momentum | -80.97 | 407.93 | — | 0.974 | 2983 | -92.66 | 6.82 | SIN VEREDICTO | 1e7322b01550a519 |
| 51 | 5m | S10 Vol-Targeted Time-Series Momentum | -82.8 | — | — | 0.923 | 2172 | -93.34 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | c9ddbff5134e423a |
| 52 | 1h | ds6 | -83.67 | — | — | 0.516 | 704 | -83.67 | — | SIN VEREDICTO | 76af36f653015376 |
| 53 | 15m | ffs | -84.17 | — | — | 0.838 | 1386 | -84.36 | — | KILLED (window-pick) | 1855e3a9ca59da0b |
| 54 | 15m | S03 Squeeze Release | -85.12 | — | — | 0.692 | 756 | -85.36 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 2477e973a25e9f52 |
| 55 | 1h | ds5 | -85.23 | — | — | 0.646 | 1304 | -88.9 | — | SIN MEDIR A COSTOS REPO (preset author = costo cero) | 91db3aa70062a247 |
| 56 | 1h | 12_zscore_fade | -85.86 | -52.04 | — | 0.875 | 1107 | -91.85 | 6.82 | SIN VEREDICTO | a065707546396595 |
| 57 | 15m | S04 VWAP Fade (range regime only) | -85.91 | — | — | 0.646 | 885 | -86.23 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 2477e973a25e9f52 |
| 58 | 15m | S05 HTF Trend Pullback (RSI-2) | -91.74 | — | — | 0.645 | 1874 | -91.85 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 2477e973a25e9f52 |
| 59 | 15m | S01 Taker-Flow Drift Bands | -92.41 | — | — | 0.824 | 1389 | -93.86 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 2477e973a25e9f52 |
| 60 | 1h | 19_hmm_regime_switch | -93.31 | -60.47 | — | 0.816 | 1611 | -97.59 | 6.82 | SIN VEREDICTO | 47a854728af43a8a |
| 61 | 5m | S06 Session Range Breakout (UTC) | -93.34 | — | — | 0.613 | 768 | -93.5 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | c9ddbff5134e423a |
| 62 | 1h | 08_donchian_turtle | -93.39 | -64.41 | — | 0.901 | 1523 | -97.11 | 6.82 | SIN VEREDICTO | cf90910d2a12e06d |
| 63 | 1h | sax | -94.41 | — | — | 0.778 | 2888 | -95.19 | — | UNRUNNABLE (engine borrado; 49 artefactos huerfanos) | 5b75ec0806377dd4 |
| 64 | 1m | S06 Session Range Breakout (UTC) | -94.74 | — | — | 0.51 | 818 | -94.74 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 9ced74c7386c9cd2 |
| 65 | 15m | 17_atr_vol_breakout | -95.21 | -69.34 | — | 0.774 | 1683 | -95.5 | 6.84 | SIN VEREDICTO | 1a0295f3d2777123 |
| 66 | 15m | S09 Liquidity Sweep Reversal | -96.19 | — | — | 0.632 | 947 | -96.24 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 2477e973a25e9f52 |
| 67 | 1h | 05_asian_sweep | -96.24 | -81.64 | — | 0.701 | 1441 | -96.79 | 6.82 | SIN VEREDICTO | 29da1a8c3cf5b315 |
| 68 | 15m | 14_ou_stationary_fade | -96.53 | 31.18 | — | 0.912 | 3300 | -96.68 | 6.84 | SIN VEREDICTO | 40bf851a03dc5229 |
| 69 | 15m | fingrad | -97.66 | -44.23 | — | 0.603 | 3155 | 97.7 | 6.79 | KILLED (y sin funding en perps: SUI 17.3%->1.6% con funding) | c7ad26c152e51f5c |
| 70 | 15m | 05_asian_sweep | -98.0 | -78.17 | — | 0.684 | 2172 | -98.29 | 6.84 | SIN VEREDICTO | 529b4d49b708cff5 |
| 71 | 1h | 07_adx_di_trend | -98.26 | -92.08 | — | 0.776 | 1373 | -98.34 | 6.82 | SIN VEREDICTO | 5cae09d0fc530f25 |
| 72 | 1h | 18_logreg_walkforward | -98.64 | 1043.01 | — | 0.925 | 6121 | -99.17 | 6.82 | SIN VEREDICTO | 8a67e318f11d0ac3 |
| 73 | 1h | 03_breaker_block | -99.06 | -73.47 | — | 0.825 | 3035 | -99.14 | 6.82 | SIN VEREDICTO | 946e581803e1d74d |
| 74 | 1m | S07 Funding Extreme Fade | -99.27 | — | — | 0.585 | 1469 | -99.31 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 9ced74c7386c9cd2 |
| 75 | 5m | S02 Donchian + Flow Breakout | -99.33 | — | — | 0.731 | 1791 | -99.38 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | c9ddbff5134e423a |
| 76 | 15m | 06_ema_pullback | -99.44 | -1.62 | — | 0.863 | 4695 | -99.5 | 6.84 | SIN VEREDICTO | bd0dfa20ca6deff6 |
| 77 | 1h | 04_pdh_sweep | -99.52 | -96.81 | — | 0.767 | 1727 | -99.61 | 6.82 | SIN VEREDICTO | 93249160bac33b32 |
| 78 | 1h | 11_bb_mean_revert | -99.58 | -84.25 | — | 0.875 | 3286 | -99.8 | 6.82 | SIN VEREDICTO | 125ab92e14003448 |
| 79 | 1h | ds9 | -99.63 | — | — | 0.831 | 3205 | -99.67 | — | SIN VEREDICTO | 3dc4af02c24e31a5 |
| 80 | 1h | 13_vwap_fade | -99.65 | -82.24 | — | 0.664 | 3566 | -99.67 | 6.82 | SIN VEREDICTO | 023b03a90cb3aa05 |
| 81 | 5m | S04 VWAP Fade (range regime only) | -99.73 | — | — | 0.723 | 2690 | -99.75 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | c9ddbff5134e423a |
| 82 | 15m | 15_squeeze_rank_breakout | -99.75 | -92.17 | — | 0.642 | 3110 | -99.75 | 6.84 | SIN VEREDICTO | e0a0ae1a07f56a05 |
| 83 | 15m | 02_order_block | -99.8 | -78.54 | — | 0.89 | 4239 | -99.85 | 6.84 | SIN VEREDICTO | 270b54e3328f1a5b |
| 84 | 5m | S03 Squeeze Release | -99.8 | — | — | 0.582 | 1755 | -99.8 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | c9ddbff5134e423a |
| 85 | 15m | 04_pdh_sweep | -99.91 | -96.74 | — | 0.788 | 3258 | -99.92 | 6.84 | SIN VEREDICTO | 36e75753e7e5642e |
| 86 | 15m | 10_rsi2_connors | -99.96 | 3907.08 | — | 0.881 | 10410 | -99.96 | 6.84 | SIN VEREDICTO | 7e05a722158c1314 |
| 87 | 15m | 12_zscore_fade | -99.96 | -94.07 | — | 0.742 | 4536 | -99.96 | 6.84 | SIN VEREDICTO | 6a9cc56ba6777b84 |
| 88 | 15m | 19_hmm_regime_switch | -99.98 | -81.22 | — | 0.828 | 6325 | -99.99 | 6.84 | SIN VEREDICTO | f3012b492829ddae |
| 89 | 5m | S09 Liquidity Sweep Reversal | -99.98 | — | — | 0.688 | 2568 | -99.98 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | c9ddbff5134e423a |
| 90 | 15m | 07_adx_di_trend | -100.0 | -98.63 | — | 0.683 | 5146 | -100.0 | 6.84 | SIN VEREDICTO | 57bf025db84040e5 |
| 91 | 1h | 20_gbm_walkforward | -100.0 | 297.9 | — | 0.877 | 10909 | -100.0 | 6.82 | SIN VEREDICTO | 0f58309a53fa3e7c |
| 92 | 5m | S05 HTF Trend Pullback (RSI-2) | -100.0 | — | — | 0.432 | 4391 | -100.0 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | c9ddbff5134e423a |
| 93 | 15m | sax | -100.0 | — | — | 0.741 | 12602 | -100.0 | — | UNRUNNABLE (engine borrado; 49 artefactos huerfanos) | 3638c5f2a9983f93 |
| 94 | 15m | 16_ttm_squeeze | -100.0 | 45.03 | — | 0.835 | 12470 | -100.0 | 6.84 | SIN VEREDICTO | 8ae9ab1385b77d02 |
| 95 | 15m | 08_donchian_turtle | -100.0 | -99.88 | — | 0.624 | 6629 | -100.0 | 6.84 | SIN VEREDICTO | 7e4580ddd4e5ad7b |
| 96 | 15m | ema921 | -100.0 | -40.13 | — | 0.708 | 11731 | -100.0 | 6.86 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | 5f0167b975200f58 |
| 97 | 15m | 11_bb_mean_revert | -100.0 | 1.69 | — | 0.786 | 12850 | -100.0 | 6.84 | SIN VEREDICTO | 77283dfe0726bebb |
| 98 | 5m | S01 Taker-Flow Drift Bands | -100.0 | — | — | 0.715 | 4666 | -100.0 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | c9ddbff5134e423a |
| 99 | 15m | 09_macd_momentum | -100.0 | -93.86 | — | 0.761 | 12350 | -100.0 | 6.84 | SIN VEREDICTO | 086141f5b1017973 |
| 100 | 15m | 03_breaker_block | -100.0 | -95.24 | — | 0.766 | 13386 | -100.0 | 6.84 | SIN VEREDICTO | cde23907d8fbd5a7 |
| 101 | 5m | ema921 | -100.0 | -34.91 | — | 0.554 | 10055 | -100.0 | 2.0 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | 66e4530c48e7cbfa |
| 102 | 1m | S03 Squeeze Release | -100.0 | — | — | 0.411 | 5561 | -100.0 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 9ced74c7386c9cd2 |
| 103 | 15m | 18_logreg_walkforward | -100.0 | 1317.15 | — | 0.728 | 24289 | -100.0 | 6.84 | SIN VEREDICTO | d48e33958b2701c1 |
| 104 | 1m | ema921 | -100.0 | -99.45 | — | 0.329 | 87686 | -100.0 | 3.75 | KILLED 0/101 (ninguna celda pasa la bateria; las 2 con PF>1.2 mueren por CI bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra) | 905d15d469657ad8 |
| 105 | 1m | S01 Taker-Flow Drift Bands | -100.0 | — | — | 0.292 | 25573 | -100.0 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 9ced74c7386c9cd2 |
| 106 | 1m | S02 Donchian + Flow Breakout | -100.0 | — | — | 0.606 | 9390 | -100.0 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 9ced74c7386c9cd2 |
| 107 | 1m | S04 VWAP Fade (range regime only) | -100.0 | — | — | 0.47 | 13378 | -100.0 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 9ced74c7386c9cd2 |
| 108 | 1m | S05 HTF Trend Pullback (RSI-2) | -100.0 | — | — | 0.07 | 18709 | -100.0 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 9ced74c7386c9cd2 |
| 109 | 1m | S09 Liquidity Sweep Reversal | -100.0 | — | — | 0.373 | 10483 | -100.0 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 9ced74c7386c9cd2 |
| 110 | 1m | S10 Vol-Targeted Time-Series Momentum | -100.0 | — | — | 0.565 | 12065 | -100.0 | 2.0 | KILLED (<1h por costos; 1h cae por concentracion con funding cobrado) | 9ced74c7386c9cd2 |
| 111 | 1m | sax | -100.0 | — | — | 0.282 | 115438 | -100.0 | — | UNRUNNABLE (engine borrado; 49 artefactos huerfanos) | a7d7b519079f0329 |
