# Por par: SPCXUSDT — 3 estrategias


| # | TF | Estrategia | Ret declarado | Ret costo cero | Ret 11bps RT | PF | n | maxDD | Ventana (años) | Veredicto | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 5m | s101 prompt 150 | -9.09 | — | — | 0.0 | 17 | -9.09 | — | KILLED 0/37 (ruina por costes en intradia; ninguna celda pasa la bateria estandar) | ba5ca6d345c7e023 |
| 2 | 1h | hmatrend SPCXUSDT 1h claim-check (ventana del pack, coste cero) | -25.55 | — | — | 0.765 | 120 | -41.92 | 0.34 | KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs) | 671cf42e5afe8d9a |
| 3 | 1h | hmatrend SPCXUSDT 1h full-history battery | -40.56 | — | — | 0.688 | 165 | -48.13 | 0.45 | KILLED 0/11 (PF ex-cost 0.69-1.01, OOS PF < 1.11, CI bootstrap negativo x11; el claim externo es irreproducible desde sus propios outputs) | 006df3b25dbaf74c |
