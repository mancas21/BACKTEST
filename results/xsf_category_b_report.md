# Categoría B — valor relativo 1h (VOLCOMP / DDRELAY)

Campaña del dos de noviembre de dos mil veintiséis. Adaptador `xsb`, motor `code/xs_factor_b_engine.py` (xsb-1), que reutiliza SIN TOCAR la maquinaria de `xs_factor_engine.py` (categoría A — sus bytes quedaron fijados por los nueve artefactos de esa campaña); ambos ficheros entran en el hash del run_id. Harness `code/vrun.py`.

Protocolo REGLA 0: cada número de este informe sale de un artefacto citado; los seis artefactos verifican bit-for-bit. Los conteos van en palabras.

Definiciones de las cartas (declaradas en `provenance.conventions` de cada artefacto):
- VOLCOMP: z-score de sesenta dias de la volatilidad relativa (vol del lookback sobre la mediana cross-sectional de esa misma vol), rango ascendente; puerta de drift en las entradas (largo solo si el retorno de siete dias es positivo, corto solo si es negativo; la pata que falla deja su hueco en efectivo, así que el libro no siempre es plenamente dolar-neutro — declarado; las patas en cartera no se re-gatean).
- DDRELAY: libro condicionado a evento. Disparador evaluado en cada decisión semanal: mediana cross-sectional del retorno de treinta dias por debajo del umbral (menos veinte por ciento en la carta principal) con al menos ocho simbolos contribuyendo. Mientras dispara: largo las dos menos dibujadas y corto las dos más dibujadas desde su máximo de catorce dias; cuando el disparador se apaga, el libro entero cierra en la apertura siguiente y queda plano.
- Convenciones compartidas con la categoría A: decisión al cierre, ejecución en la apertura siguiente, coste por lado en cada fill, resize a equity/(2k) con base de coste promedio, histéresis, control de coste cero con decisiones idénticas dentro del artefacto, funding NO cobrado (declarado), bootstrap semillado de diez mil remuestreos.

## Resultados principales

| Carta | run_id | net % | gross % | PF | PF ex-cost | n | WR % | IS PF | OOS PF | top-5 % PnL | net sin top-5 % | maxDD % | B&H EW % | episodios | decisiones activas |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| VOLCOMP | `138c4b2f93fd62db` | -73.60 | -71.92 | 0.7758 | 0.7903 | 247 | 45.3 | 0.9773 | 0.5697 | n/a | -170.6 | -92.1 | 1036.2 | 1 | 155 |
| DDRELAY | `c7b83f8626bf21b4` | -47.07 | -45.12 | 0.7808 | 0.8014 | 121 | 43.8 | 0.7247 | 0.8898 | n/a | -125.3 | -52.8 | 61.2 | 23 | 51 |

Bandera del artefacto `138c4b2f93fd62db`: `FAIL-GATES:pf_ex_cost_gt_1.2,oos_pf_ge_1,green_years_frac,conc_top5_lt_100,net_without_top5_pos,cost_share_lt_40,boot_ci_low_pos,beats_bh_equal_weight`.
Bandera del artefacto `c7b83f8626bf21b4`: `FAIL-GATES:pf_ex_cost_gt_1.2,oos_pf_ge_1,green_years_frac,conc_top5_lt_100,net_without_top5_pos,cost_share_lt_40,boot_ci_low_pos,beats_bh_equal_weight`.

## Vecindario (gate de estabilidad; no es rescate)

| Carta | variante | run_id | net % | PF ex-cost | OOS PF | top-5 % | maxDD % |
|---|---|---|---|---|---|---|---|
| VOLCOMP | 240 | `233906b11726316d` | -61.05 | 0.8542 | 0.6003 | n/a | -90.6 |
| VOLCOMP | 480 | `bbd4ed10c0aa6f43` | -23.37 | 1.0499 | 0.6558 | 325.1 | -82.6 |
| DDRELAY | trig -0.15 | `1f065febc8cc9bfd` | -51.54 | 0.7826 | 1.1159 | n/a | -60.0 |
| DDRELAY | trig -0.25 | `05f467361fa13783` | -27.31 | 0.8538 | 0.7376 | n/a | -34.1 |

## Gates medidos por carta (tabla `gates` de cada artefacto principal)

Artefacto: `results/runs/138c4b2f93fd62db.json`

| gate | umbral | medido | pasa |
|---|---|---|---|
| pf_ex_cost_gt_1.2 | >1.2 | 0.7903 | NO |
| n_trades_ge_30 | >=30 | 247 | SI |
| oos_pf_ge_1 | >=1 (OOS PF < 1 = KILL) | 0.5697 | NO |
| green_years_frac | >=2/3 years green | 2/8 | NO |
| conc_top5_lt_100 | <100% of PnL | None | NO |
| net_without_top5_pos | >0% | -170.5665 | NO |
| cost_share_lt_40 | <40% of gross | None | NO |
| boot_ci_low_pos | >0 bps | -635.3026 | NO |
| g11_winrate_buffer | wr>=75 needs wr>=breakeven+5pp | 51.6780 | SI |
| beats_bh_equal_weight | net > B&H (1036.1684185922811) | False | NO |

Artefacto: `results/runs/c7b83f8626bf21b4.json`

| gate | umbral | medido | pasa |
|---|---|---|---|
| pf_ex_cost_gt_1.2 | >1.2 | 0.8014 | NO |
| n_trades_ge_30 | >=30 | 121 | SI |
| oos_pf_ge_1 | >=1 (OOS PF < 1 = KILL) | 0.8898 | NO |
| green_years_frac | >=2/3 years green | 2/8 | NO |
| conc_top5_lt_100 | <100% of PnL | None | NO |
| net_without_top5_pos | >0% | -125.2565 | NO |
| cost_share_lt_40 | <40% of gross | None | NO |
| boot_ci_low_pos | >0 bps | -527.8643 | NO |
| g11_winrate_buffer | wr>=75 needs wr>=breakeven+5pp | 49.9546 | SI |
| beats_bh_equal_weight | net > B&H (61.19249232019322) | False | NO |

## Desglose por simbolo (carta DDRELAY, tabla `per_symbol` del artefacto `results/runs/c7b83f8626bf21b4.json`)

| simbolo | n trades | WR % | PnL eq % |
|---|---|---|---|
| ADAUSDT | 8 | 37.5 | -9.24 |
| ARBUSDT | 5 | 40.0 | -2.67 |
| AVAXUSDT | 5 | 60.0 | 25.24 |
| BNBUSDT | 17 | 58.8 | -11.99 |
| BTCUSDT | 20 | 65.0 | 1.28 |
| DOGEUSDT | 5 | 60.0 | 8.34 |
| ETHUSDT | 5 | 20.0 | -8.88 |
| HYPEUSDT | 3 | 100.0 | 2.03 |
| JUPUSDT | 10 | 30.0 | -13.26 |
| LINKUSDT | 8 | 25.0 | -11.34 |
| NEARUSDT | 11 | 18.2 | 1.12 |
| SOLUSDT | 8 | 37.5 | -11.10 |
| SUIUSDT | 9 | 33.3 | -12.55 |
| XRPUSDT | 7 | 28.6 | -7.25 |

## Hallazgos declarados

- Ambas cartas pierden ANTES de costes (PF ex-cost por debajo de uno en las dos cartas principales): el fallo es de senal, no de coste.
- DDRELAY disparó veintitres episodios — no es una condición rara; el libro estuvo activo en cincuenta y una de sus decisiones y aun así perdió en bruto.
- El vecindario no rescata: las cuatro celdas fallan. La mejor celda de VOLCOMP en bruto (lookback cuatrocientos ochenta) sigue con OOS por debajo de uno y una concentracion extrema.
- Funding no cobrado (declarado); B&H medido desde la primera barra activa de cada libro.

## Veredicto

**Categoría B (VOLCOMP / DDRELAY sobre el universe-14 a una hora): KILLED — cero de dos cartas supera los gates; ambas pierden en bruto y el vecindario confirma que no es un problema de parametro.** La convergencia de volatilidad relativa y el relay de drawdown relativo no contienen edge en este universo ni en este coste. Con la categoría A killed el mismo dia, el bloque OHLCV-only del pack generado (categorías A y B) cierra con cero supervivientes.

