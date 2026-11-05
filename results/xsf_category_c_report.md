# Categoría C — libros filtrados por funding (FUNDGATE / FUNDTAIL)

Campaña del dos de noviembre de dos mil veintiséis. Adaptador `xsc`, motor `code/xs_factor_c_engine.py` (xsc-1), que reutiliza SIN TOCAR la maquinaria de `xs_factor_engine.py` (categoría A — fijada por sus nueve artefactos); ambos ficheros entran en el hash del run_id. Universo de SIETE nombres con fichero de funding en disco. Harness `code/vrun.py`.

Protocolo REGLA 0: cada número de este informe sale de un artefacto citado; los seis artefactos verifican bit-for-bit. Los conteos van en palabras.

A diferencia de las categorías A y B (funding declarado sin cobrar), aquí el funding se COBRA de verdad en cada simulación: cada settlement real del fichero de funding de una pata abierta factura -dir * unidades * apertura * tarifa cruda dentro de la ventana de la barra (JUP y HYPE liquidan cada cuatro horas: dos settlements reales, no uno doblado). Tres simulaciones por artefacto con decisiones idénticas (asegurado): neta (costes + funding), bruta sin costes de trading con funding (control ex-coste), y bruta sin costes NI funding — `funding_pnl_pct` es la contribución del funding al libro. Cobertura según `data/FUNDING_MANIFEST.json`: el gap de cabeza de JUP a una hora es de doscientos cuarenta y tres días, así que los libros arrancan con el primer funding de JUP (octubre de dos mil veinticuatro) y HYPE entra con su propia primera barra (mayo de dos mil veinticinco); la cola de JUP descubre dos días y medio. Gate de funding normalizado por ocho horas (tarifa cruda por ocho entre la cadencia modal del símbolo). Estadísticas de ventana (tercios, mitades, años, split setenta-treinta) medidas sobre la ventana ACTIVA del libro, no sobre el índice unión.

Definiciones de las cartas (declaradas en `provenance.conventions`):
- FUNDGATE: libro base ROC del lookback clasificado descendente, dos patas por lado fijo; gate de signo de funding en las entradas — un candidato largo se mantiene solo si la última tarifa por ocho horas es menor o igual que cero (cobra o neutra) y un candidato corto solo si es mayor que cero (cobra); el candidato que falla deja su hueco en efectivo (libro no siempre plenamente dolar-neutro — declarado); las patas en cartera no se re-gatean.
- FUNDTAIL: libro de baja volatilidad (la carta LOWVOL de la categoría A restringida al universo de siete), dos patas por lado fijo, con exclusión de funding extremo: candidato largo excluido si la tarifa por ocho horas supera el umbral (pagaría), candidato corto excluido si es menor que el umbral negativo; umbral declarado cinco puntos básicos por ocho horas.

## Resultados principales

| Carta | run_id | net % | gross % | sin funding % | funding PnL pp | PF | PF ex-cost | n | IS PF | OOS PF | maxDD % | B&H EW % | eventos facturados |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FUNDGATE | `f8c556f2a7d194c3` | -18.32 | -16.79 | -18.87 | 2.09 | 0.9197 | 0.9392 | 57 | 0.9358 | 0.9000 | -43.8 | 11.9 | 7873 |
| FUNDTAIL | `7d82a4921ea6cbd9` | -2.55 | -1.91 | 2.96 | -4.87 | 1.0936 | 1.1772 | 6 | n/a | 1.0936 | -37.9 | 11.9 | 11124 |

Bandera del artefacto `f8c556f2a7d194c3`: `FAIL-GATES:pf_ex_cost_gt_1.2,oos_pf_ge_1,green_years_frac,conc_top5_lt_100,net_without_top5_pos,cost_share_lt_40,boot_ci_low_pos,beats_bh_equal_weight`.
Bandera del artefacto `7d82a4921ea6cbd9`: `FAIL-GATES:pf_ex_cost_gt_1.2,n_trades_ge_30,green_years_frac,conc_top5_lt_100,net_without_top5_pos,cost_share_lt_40,boot_ci_low_pos,beats_bh_equal_weight`.

## Vecindario (gate de estabilidad; no es rescate)

| Carta | variante | run_id | net % | PF ex-cost | funding PnL pp | OOS PF | n |
|---|---|---|---|---|---|---|---|
| FUNDGATE | lb 240 | `ca0d1b5a0acf62dc` | -32.63 | 0.8216 | 1.84 | 0.9501 | 64 |
| FUNDGATE | lb 480 | `30a4ab1415cc17d5` | -44.02 | 0.7270 | 1.32 | 1.1614 | 55 |
| FUNDTAIL | cap 0.0003 | `66657dd972ffb3f5` | 4.44 | 1.6146 | -4.85 | 1.5125 | 6 |
| FUNDTAIL | cap 0.001 | `ddaea3cc7fa01765` | -10.24 | 0.7960 | -4.89 | 0.7504 | 6 |

## Gates medidos por carta (tabla `gates` de cada artefacto principal)

Artefacto: `results/runs/f8c556f2a7d194c3.json`

| gate | umbral | medido | pasa |
|---|---|---|---|
| pf_ex_cost_gt_1.2 | >1.2 | 0.9392 | NO |
| n_trades_ge_30 | >=30 | 57 | SI |
| oos_pf_ge_1 | >=1 (OOS PF < 1 = KILL) | 0.9000 | NO |
| green_years_frac | >=2/3 years green | 1/3 | NO |
| conc_top5_lt_100 | <100% of PnL | None | NO |
| net_without_top5_pos | >0% | -67.5881 | NO |
| cost_share_lt_40 | <40% of gross | None | NO |
| boot_ci_low_pos | >0 bps | -904.7345 | NO |
| g11_winrate_buffer | wr>=75 needs wr>=breakeven+5pp | 51.2143 | SI |
| beats_bh_equal_weight | net > B&H (11.943261896608554) | False | NO |

Artefacto: `results/runs/7d82a4921ea6cbd9.json`

| gate | umbral | medido | pasa |
|---|---|---|---|
| pf_ex_cost_gt_1.2 | >1.2 | 1.1772 | NO |
| n_trades_ge_30 | >=30 | 6 | NO |
| oos_pf_ge_1 | >=1 (OOS PF < 1 = KILL) | 1.0936 | SI |
| green_years_frac | >=2/3 years green | 1/3 | NO |
| conc_top5_lt_100 | <100% of PnL | 1025.6661 | NO |
| net_without_top5_pos | >0% | -18.8740 | NO |
| cost_share_lt_40 | <40% of gross | None | NO |
| boot_ci_low_pos | >0 bps | -2490.9557 | NO |
| g11_winrate_buffer | wr>=75 needs wr>=breakeven+5pp | 47.7640 | SI |
| beats_bh_equal_weight | net > B&H (11.943261896608554) | False | NO |

## Desglose por simbolo (carta FUNDGATE, tabla `per_symbol` del artefacto `results/runs/f8c556f2a7d194c3.json`)

| simbolo | n trades | WR % | PnL eq % |
|---|---|---|---|
| BTCUSDT | 11 | 36.4 | -5.13 |
| ETHUSDT | 7 | 85.7 | 19.01 |
| HYPEUSDT | 6 | 33.3 | -4.41 |
| JUPUSDT | 12 | 25.0 | -20.10 |
| SOLUSDT | 5 | 60.0 | 8.75 |
| SUIUSDT | 11 | 81.8 | 35.70 |
| XRPUSDT | 5 | 20.0 | -44.97 |

## Hallazgos declarados

- FUNDGATE pierde en las tres celdas (PF ex-cost entre cero coma setenta y tres y cero coma noventa y cuatro): el viento de cola del funding existe pero es diminuto — entre uno coma tres y dos coma uno puntos porcentuales en dos anos, muy lejos de compensar la senal perdedora.
- FUNDTAIL hace SEIS trades en dos anos en cualquier umbral: muere por suelo de muestra antes que por todo lo demas. La celda del vecindario con umbral mas estricto muestra un neto positivo, pero con seis trades es exactamente el ruido que la calibracion nula del repositorio mide (un nulo pasa los gates hasta en un cinco por ciento de las veces con muestras pequenas) — sin valor de evidencia y sin rescate.
- El gate de signo de funding deja huecos en efectivo con frecuencia (exposicion bruta media muy por debajo de cien por ciento en ambas cartas): en un universo de siete perpes, largos que cobran funding son raros porque casi todo el sector paga funding positivo la mayor parte del tiempo.

## Veredicto

**Categoría C (FUNDGATE / FUNDTAIL sobre el universo de siete con funding, funding COBRADO): KILLED — cero de dos cartas supera los gates.** FUNDGATE pierde por senal con un viento de funding real pero dos ordenes de magnitud menor que lo necesario; FUNDTAIL muere por muestra. La familia funding-como-filtro (no como carry, familia esa ya terminal por la auditoria EDGE) queda medida muerta en este repositorio.

