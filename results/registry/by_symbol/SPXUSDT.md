# Por par: SPXUSDT — 52 estrategias


| # | TF | Estrategia | Ret declarado | Ret costo cero | Ret 11bps RT | PF | n | maxDD | Ventana (años) | Veredicto | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1h | ds7 | 44.97 | — | — | 1.108 | 296 | -45.98 | — | SIN VEREDICTO | b898dfed4e6f2395 |
| 2 | 1h | botstrat | 38.72 | — | — | 3.079 | 31 | -4.17 | — | SIN VEREDICTO (15m = duplicado del 1h: engine hardcodea 1h) | f2aa1050b118e54f |
| 3 | 15m | A01-15m RSI14 L/S mean-reversion | 13.83 | — | — | — | 237 | 27.4 | 0.28 | KILLED 0/100 | 0b4ac2680e4c5f0e |
| 4 | 1h | ds1 | 12.87 | 12.87 | -6.51 | 1.103 | 500 | -17.52 | — | medido a 11 bps RT: -6.5% | dc9d4cdab4c59815 |
| 5 | 15m | A15-15m EMA(50) overextension reversion | 12.28 | — | — | — | 229 | 40.51 | 0.28 | KILLED 0/100 | 8389ecb85a1a8d1a |
| 6 | 1h | A06-1h Stochastic(14,3,3) reversion | -0.37 | — | — | — | 712 | 65.72 | 1.79 | KILLED 0/100 | 0c29bf1a131c0dc6 |
| 7 | 1h | cvrmd | -4.12 | — | — | 0.654 | 21 | -4.56 | — | FRAGILE/SUSPENDED (PF ~1.02 historia completa) | aa84ff4de9e1dbd9 |
| 8 | 1h | smqe | -4.23 | -3.53 | — | 0.624 | 21 | 4.66 | 1.79 | SUSPENDED (sin OOS posible) | 43ec33d730c4a800 |
| 9 | 1h | fingrad | -9.88 | -5.05 | — | 0.838 | 226 | 18.74 | 1.79 | KILLED (y sin funding en perps: SUI 17.3%->1.6% con funding) | d4558eb5be021fa6 |
| 10 | 15m | F71-15m engulfing-at-extreme | -9.95 | — | — | — | 97 | 17.27 | 0.28 | KILLED 0/100 | 1ef2b8ead85852f3 |
| 11 | 1h | hmaaoadx | -13.47 | — | — | 0.779 | 255 | -19.57 | 1.79 | SIN VEREDICTO | 98cb16430b8ec720 |
| 12 | 1h | ds2 | -13.53 | — | — | 0.964 | 412 | -57.58 | — | SIN MEDIR A COSTOS REPO (preset author = costo cero) | 5dd301c6d5331c4b |
| 13 | 15m | A03-15m Bollinger(20,2) reversion | -16.78 | — | — | — | 519 | 42.08 | 0.28 | KILLED 0/100 | 9ad4a7be697f1a91 |
| 14 | 15m | A06-15m Stochastic(14,3,3) reversion | -19.07 | — | — | — | 436 | 44.92 | 0.28 | KILLED 0/100 | 40995cc3c983532c |
| 15 | 15m | C39-15m previous-day high/low breakout | -19.61 | — | — | — | 22 | 41.14 | 0.28 | KILLED 0/100 | 302dee130ad66190 |
| 16 | 1h | A01-1h RSI14 L/S mean-reversion | -21.28 | — | — | — | 407 | 76.93 | 1.79 | KILLED 0/100 | 5b4bcbac0d962756 |
| 17 | 5m | A15-5m EMA(50) overextension reversion | -22.59 | — | — | — | 849 | 45.28 | 0.28 | KILLED 0/100 | 8c150ac3f0a52c62 |
| 18 | 1h | ds5 | -25.1 | — | — | 0.926 | 340 | -57.13 | — | SIN MEDIR A COSTOS REPO (preset author = costo cero) | 4abca197e4a0443c |
| 19 | 1h | ffs | -30.33 | — | — | 0.551 | 104 | -35.75 | — | KILLED (window-pick) | 6916073f822ec7df |
| 20 | 5m | C39-5m previous-day high/low breakout | -30.94 | — | — | — | 200 | 41.26 | 0.28 | KILLED 0/100 | 532c344d73a8c1a2 |
| 21 | 5m | F71-5m engulfing-at-extreme | -32.46 | — | — | — | 286 | 33.05 | 0.28 | KILLED 0/100 | 326acd9dd3da4831 |
| 22 | 5m | C31-5m opening-range breakout | -33.27 | — | — | — | 251 | 48.64 | 0.28 | KILLED 0/100 | 2c89d4ead28f7da3 |
| 23 | 1h | ds6 | -33.35 | — | — | 0.814 | 212 | -44.96 | — | SIN VEREDICTO | b5beb1b7f6a4f086 |
| 24 | 1h | F71-1h engulfing-at-extreme | -38.73 | — | — | — | 130 | 55.78 | 1.79 | KILLED 0/100 | 2bae2e2cca86cfe3 |
| 25 | 15m | C31-15m opening-range breakout | -40.32 | — | — | — | 14 | 50.83 | 0.28 | KILLED 0/100 | 43b47d1a733582a6 |
| 26 | 5m | A01-5m RSI14 L/S mean-reversion | -42.55 | — | — | — | 792 | 58.92 | 0.28 | KILLED 0/100 | 541c360f4a84015f |
| 27 | 1h | D07 previous-day high/low breakout | -42.85 | 11.55 | — | 0.957 | 477 | 73.28 | 1.79 | KILLED 0/46 | 009abf69321e2e2c |
| 28 | 1h | sax | -49.4 | — | — | 0.908 | 843 | -60.56 | — | UNRUNNABLE (engine borrado; 49 artefactos huerfanos) | e20a0831d386796c |
| 29 | 15m | B23-15m Parabolic SAR + EMA100 (long) | -52.51 | — | — | — | 215 | 54.82 | 0.28 | KILLED 0/100 | 11a2b3c3f17be2a4 |
| 30 | 1h | emaadx | -56.8 | -54.18 | — | 0.678 | 58 | 64.86 | 1.79 | KILLED | 7f4ef32199ee451b |
| 31 | 15m | D47-15m time-series momentum (long) | -58.07 | — | — | — | 349 | 59.56 | 0.28 | KILLED 0/100 | c0b85b73e150692b |
| 32 | 1h | D47-1h time-series momentum (long) | -58.63 | — | — | — | 488 | 88.24 | 1.79 | KILLED 0/100 | 314bff1cf3e2c7bf |
| 33 | 5m | B23-5m Parabolic SAR + EMA100 (long) | -59.41 | — | — | — | 625 | 61.06 | 0.28 | KILLED 0/100 | 8ce569c046c5744f |
| 34 | 15m | E63-15m Force Index trend (long) | -62.84 | — | — | — | 339 | 64.58 | 0.28 | KILLED 0/100 | 19cd56c9a87f3453 |
| 35 | 15m | D25 EMA ribbon trend | -63.78 | -45.9 | — | 0.677 | 286 | 67.46 | 0.28 | KILLED 0/46 | a5ef053c86b989e7 |
| 36 | 5m | D47-5m time-series momentum (long) | -68.85 | — | — | — | 921 | 69.94 | 0.28 | KILLED 0/100 | 65aa73d6580934a6 |
| 37 | 1h | ds9 | -69.54 | — | — | 0.851 | 820 | -71.39 | — | SIN VEREDICTO | 711f5bfe353cceeb |
| 38 | 1h | E63-1h Force Index trend (long) | -70.16 | — | — | — | 493 | 85.93 | 1.79 | KILLED 0/100 | 45a1ee605647c5e7 |
| 39 | 1h | A15-1h EMA(50) overextension reversion | -73.02 | — | — | — | 428 | 86.47 | 1.79 | KILLED 0/100 | 688d2af5126eef15 |
| 40 | 1h | B23-1h Parabolic SAR + EMA100 (long) | -74.19 | — | — | — | 336 | 89.79 | 1.79 | KILLED 0/100 | 5b3c7aac7c871427 |
| 41 | 1h | C39-1h previous-day high/low breakout | -74.49 | — | — | — | 25 | 89.24 | 1.79 | KILLED 0/100 | 385551b4d84d5bc1 |
| 42 | 5m | A06-5m Stochastic(14,3,3) reversion | -77.07 | — | — | — | 1405 | 81.4 | 0.28 | KILLED 0/100 | 0d808425baa199f1 |
| 43 | 5m | E63-5m Force Index trend (long) | -81.58 | — | — | — | 834 | 82.2 | 0.28 | KILLED 0/100 | 6402b17e3c36fb87 |
| 44 | 5m | A03-5m Bollinger(20,2) reversion | -83.59 | — | — | — | 1508 | 86.48 | 0.28 | KILLED 0/100 | 286c276453e06510 |
| 45 | 1h | A03-1h Bollinger(20,2) reversion | -84.56 | — | — | — | 832 | 92.64 | 1.79 | KILLED 0/100 | 4a465af2c64c9605 |
| 46 | 15m | D55-15m momentum acceleration | -91.44 | — | — | — | 1511 | 91.99 | 0.28 | KILLED 0/100 | 3a3e56c989d5270b |
| 47 | 1h | ds3 | -95.27 | — | — | 0.328 | 98 | -97.12 | — | SIN MEDIR A COSTOS REPO (preset author = costo cero) | dd1e158a5b503d1c |
| 48 | 5m | S15 EMA 20 pullback | -95.81 | -30.23 | — | 0.585 | 2008 | 95.82 | 0.28 | KILLED 0/46 | 28a77d2d9511e838 |
| 49 | 5m | D55-5m momentum acceleration | -99.1 | — | — | — | 4394 | 99.15 | 0.28 | KILLED 0/100 | 4b1141a4c0a4e0fe |
| 50 | 1m | sax | -99.76 | — | — | 0.427 | 7900 | -99.76 | — | UNRUNNABLE (engine borrado; 49 artefactos huerfanos) | 5f3fa0b72c7203b7 |
| 51 | 1h | D55-1h momentum acceleration | -99.91 | — | — | — | 2378 | 99.95 | 1.79 | KILLED 0/100 | ab53dde01e54511c |
| 52 | 1m | S25 Bollinger mean reversion | -99.99 | 29.94 | — | 0.56 | 7193 | 99.99 | 0.28 | KILLED 0/46 | 0718e20940498821 |
