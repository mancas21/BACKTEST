# Por familia: grid_neutral — 3 estrategias


| # | TF | Estrategia | Ret declarado | Ret costo cero | Ret 11bps RT | PF | n | maxDD | Ventana (años) | Veredicto | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 15m | XRP delta-neutral grid v2 (25 USDT x 10x) | 9388264.86 | — | — | 1.307 | 5975 | 43.42 | 6.81 | KILLED (resolucion 1m: PF 0.93 vs 1.30 en el OOS 2023+; sonda _xrp_1m_resolution.py) | fe5c359a22c8dffe |
| 2 | 15m | XRP delta-neutral grid v1 (10k, 0.25x/lvl) | 1598.19 | — | — | 1.5 | 5888 | 10.18 | 6.81 | KILLED (resolucion 1m: PF 0.93 vs 1.30 en el OOS 2023+; sonda _xrp_1m_resolution.py) | 295c21687960fadd |
| 3 | 15m | XRP delta-neutral grid v2 (25 USDT x 10x), fills resolved on 1m | -74.2 | — | — | 0.933 | 3018 | 81.46 | 3.75 | KILLED (el mismo libro resuelto en 1m cae bajo PF 1 en el OOS; artefacto 18d686932bf06f78) | 18d686932bf06f78 |
