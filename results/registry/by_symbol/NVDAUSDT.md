# Por par: NVDAUSDT — 4 estrategias


| # | TF | Estrategia | Ret declarado | Ret costo cero | Ret 11bps RT | PF | n | maxDD | Ventana (años) | Veredicto | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1h | hmatrend NVDAUSDT 1h claim-check (ventana del pack, coste cero) | -2.62 | — | — | 0.96 | 125 | -23.44 | 0.34 | KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs) | eaff1ab244fa05a8 |
| 2 | 1h | hmatrend NVDAUSDT 1h full-history battery | -13.81 | — | — | 0.858 | 205 | -28.39 | 0.61 | KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs) | e9bf4de86c939484 |
| 3 | 5m | s101 prompt 141 | -22.62 | — | — | 0.575 | 252 | -25.96 | — | KILLED 0/37 (ruina por costes en intradia; ninguna celda pasa la bateria estandar) | 99ef4ec447372fc0 |
| 4 | 5m | s101 prompt 144 | -32.97 | — | — | 0.056 | 67 | -32.97 | — | KILLED 0/37 (ruina por costes en intradia; ninguna celda pasa la bateria estandar) | 9c63f85f4b6aeac8 |
