# Por par: DOGEUSDT — 15 estrategias


| # | TF | Estrategia | Ret declarado | Ret costo cero | Ret 11bps RT | PF | n | maxDD | Ventana (años) | Veredicto | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1h | ds3 | 971.37 | 971.37 | 457.62 | 1.067 | 296 | -76.85 | — | medido a 11 bps RT: +457.6% | ed387f4ba682f64b |
| 2 | 1h | ds1 | 223.71 | 223.71 | -17.41 | 1.193 | 1983 | -28.76 | — | medido a 11 bps RT: -17.4% | 26249a763343bca4 |
| 3 | 1h | ds7 | 43.69 | — | — | 1.031 | 889 | -58.32 | — | SIN VEREDICTO | b5c18361f8cb3659 |
| 4 | 1h | botstrat | -2.18 | — | — | 1.02 | 135 | -20.69 | — | SIN VEREDICTO (15m = duplicado del 1h: engine hardcodea 1h) | 75c101d35f97fce0 |
| 5 | 1h | fingrad | -2.23 | 33.15 | — | 0.989 | 708 | 26.65 | 6.27 | KILLED (y sin funding en perps: SUI 17.3%->1.6% con funding) | 444e3e2600ee6c50 |
| 6 | 1h | smqe | -6.77 | -4.57 | — | 0.639 | 37 | 9.57 | 6.29 | SUSPENDED (sin OOS posible) | 52a357c549d6a1a7 |
| 7 | 1h | cvrmd | -14.14 | — | — | 0.652 | 73 | -17.78 | — | FRAGILE/SUSPENDED (PF ~1.02 historia completa) | 3f8c5dd54278825c |
| 8 | 1h | ds2 | -24.42 | — | — | 0.962 | 1069 | -65.73 | — | SIN MEDIR A COSTOS REPO (preset author = costo cero) | 4d494de14888b1d3 |
| 9 | 1h | ds5 | -28.53 | — | — | 0.94 | 1183 | -71.21 | — | SIN MEDIR A COSTOS REPO (preset author = costo cero) | 961ef9b0a3e251cd |
| 10 | 1h | hmaaoadx | -47.92 | — | — | 0.706 | 787 | -50.67 | 6.29 | SIN VEREDICTO | 8818f81e243f086b |
| 11 | 1h | ffs | -61.58 | — | — | 0.627 | 373 | -64.37 | — | KILLED (window-pick) | a9f6a20c8bdf14d6 |
| 12 | 1h | ds6 | -76.2 | — | — | 0.633 | 648 | -77.29 | — | SIN VEREDICTO | a1656c996bc20423 |
| 13 | 1h | emaadx | -79.41 | -74.09 | — | 0.702 | 228 | 80.04 | 6.27 | KILLED | b041915046dd6473 |
| 14 | 1h | sax | -91.43 | — | — | 0.754 | 2733 | -91.86 | — | UNRUNNABLE (engine borrado; 49 artefactos huerfanos) | 3906967986cd22fa |
| 15 | 1h | ds9 | -99.33 | — | — | 0.771 | 2990 | -99.53 | — | SIN VEREDICTO | ceaa506a554bbdd1 |
