# Categoría A — libros cross-sectionales 1h (LOWVOL / SKEW / AUTOCORR)

Campaña del dos de noviembre de dos mil veintiséis. Adaptador `xsf`, motor `code/xs_factor_engine.py` (xsf-1), harness `code/vrun.py`. Los tres libros roten un universe-14 de perpetuos USDT-M por rango de factor (regla de inclusión por historial; símbolos que salen cuando sus datos terminan).

Protocolo REGLA 0: cada número de este informe sale de un artefacto citado; los nueve artefactos verifican bit-for-bit (comando `verify` ejecutado sobre cada uno). Los conteos van en palabras.

Convenciones medidas dentro de cada artefacto (`provenance.conventions`): decisión al cierre de la barra de rebalanceo y ejecución en la apertura siguiente; coste de comisión mas deslizamiento por lado, cobrado en cada fill; control de coste cero con la misma máquina de estados dentro del artefacto; resize de cada pata a `equity/(2k)` en cada rebalanceo con base de coste promedio; bandas de histéresis (entra en rank <= k, se mantiene mientras rank <= 2k); mínimo de sección transversal declarado (constante, no ajustada); funding NO cobrado — siete de catorce nombres no tienen fichero de funding en disco; bootstrap semillado de diez mil remuestreos.

## Resultados principales

| Carta | run_id | net % | gross % | PF | PF ex-cost | n | WR % | IS PF | OOS PF | top-5 % PnL | net sin top-5 % | maxDD % | B&H EW % | media/trade bps |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LOWVOL | `5c5cbbe6443fb391` | -45.94 | -44.27 | 1.1505 | 1.1650 | 65 | 52.3 | 1.3831 | 0.8624 | 354.5 | -329.7 | -84.4 | 1177.3 | 405.1 |
| SKEW | `c683ad80d93f965f` | -93.09 | -92.49 | 0.8728 | 0.8856 | 250 | 54.4 | 0.7359 | 1.1697 | n/a | -271.1 | -102.7 | 1113.1 | -192.5 |
| AUTOCORR | `78599c8a2cdd0982` | -89.73 | -88.58 | 0.8239 | 0.8381 | 420 | 45.5 | 0.8477 | 0.7898 | n/a | -255.6 | -90.7 | 1177.3 | -205.8 |

Ventana: los tres libros arrancan la primera decision con al menos ocho simbolos elegibles y corren hasta el final comun del indice (fechas exactas `start_utc` / `end_utc` / `first_active_utc` en cada artefacto).

Bandera del artefacto `5c5cbbe6443fb391`: `FAIL-GATES:pf_ex_cost_gt_1.2,oos_pf_ge_1,green_years_frac,conc_top5_lt_100,net_without_top5_pos,cost_share_lt_40,boot_ci_low_pos,beats_bh_equal_weight`.
Bandera del artefacto `c683ad80d93f965f`: `FAIL-GATES:pf_ex_cost_gt_1.2,green_years_frac,conc_top5_lt_100,net_without_top5_pos,cost_share_lt_40,boot_ci_low_pos,beats_bh_equal_weight`.
Bandera del artefacto `78599c8a2cdd0982`: `FAIL-GATES:pf_ex_cost_gt_1.2,oos_pf_ge_1,green_years_frac,conc_top5_lt_100,net_without_top5_pos,cost_share_lt_40,boot_ci_low_pos,beats_bh_equal_weight`.

## Vecindario (gate de estabilidad; no es rescate)

| Carta | lb | run_id | net % | PF ex-cost | OOS PF | top-5 % | maxDD % |
|---|---|---|---|---|---|---|---|
| LOWVOL | 240 | `8c719aa2675607c7` | -53.99 | 1.1325 | 0.5864 | 352.7 | -88.8 |
| LOWVOL | 480 | `66f2932cef28ac12` | -49.83 | 1.0346 | 1.2142 | 1101.3 | -82.0 |
| SKEW | 480 | `d5bced1d6604b6f3` | -102.79 | 0.7738 | 1.1647 | n/a | -129.6 |
| SKEW | 960 | `08fa3e92ed79df46` | -28.54 | 1.0480 | 1.4231 | n/a | -100.2 |
| AUTOCORR | 240 | `e6b0133110704e30` | -140.18 | 0.8127 | 0.7663 | n/a | -333.1 |
| AUTOCORR | 480 | `ddf318cf72aa9b97` | -101.34 | 0.6733 | 0.7449 | n/a | -183.2 |

## Gates medidos por carta (tabla `gates` de cada artefacto principal)

Artefacto: `results/runs/5c5cbbe6443fb391.json`

| gate | umbral | medido | pasa |
|---|---|---|---|
| pf_ex_cost_gt_1.2 | >1.2 | 1.1650 | NO |
| n_trades_ge_30 | >=30 | 65 | SI |
| oos_pf_ge_1 | >=1 (OOS PF < 1 = KILL) | 0.8624 | NO |
| green_years_frac | >=2/3 years green | 3/8 | NO |
| conc_top5_lt_100 | <100% of PnL | 354.4896 | NO |
| net_without_top5_pos | >0% | -329.6685 | NO |
| cost_share_lt_40 | <40% of gross | None | NO |
| boot_ci_low_pos | >0 bps | -1915.1740 | NO |
| g11_winrate_buffer | wr>=75 needs wr>=breakeven+5pp | 48.8041 | SI |
| beats_bh_equal_weight | net > B&H (1177.3195692424513) | False | NO |

Artefacto: `results/runs/c683ad80d93f965f.json`

| gate | umbral | medido | pasa |
|---|---|---|---|
| pf_ex_cost_gt_1.2 | >1.2 | 0.8856 | NO |
| n_trades_ge_30 | >=30 | 250 | SI |
| oos_pf_ge_1 | >=1 (OOS PF < 1 = KILL) | 1.1697 | SI |
| green_years_frac | >=2/3 years green | 3/8 | NO |
| conc_top5_lt_100 | <100% of PnL | None | NO |
| net_without_top5_pos | >0% | -271.0728 | NO |
| cost_share_lt_40 | <40% of gross | None | NO |
| boot_ci_low_pos | >0 bps | -990.8026 | NO |
| g11_winrate_buffer | wr>=75 needs wr>=breakeven+5pp | 57.7495 | SI |
| beats_bh_equal_weight | net > B&H (1113.1136179101657) | False | NO |

Artefacto: `results/runs/78599c8a2cdd0982.json`

| gate | umbral | medido | pasa |
|---|---|---|---|
| pf_ex_cost_gt_1.2 | >1.2 | 0.8381 | NO |
| n_trades_ge_30 | >=30 | 420 | SI |
| oos_pf_ge_1 | >=1 (OOS PF < 1 = KILL) | 0.7898 | NO |
| green_years_frac | >=2/3 years green | 1/8 | NO |
| conc_top5_lt_100 | <100% of PnL | None | NO |
| net_without_top5_pos | >0% | -255.6031 | NO |
| cost_share_lt_40 | <40% of gross | None | NO |
| boot_ci_low_pos | >0 bps | -529.1892 | NO |
| g11_winrate_buffer | wr>=75 needs wr>=breakeven+5pp | 50.3052 | SI |
| beats_bh_equal_weight | net > B&H (1177.3195692424513) | False | NO |

## Desglose por simbolo (carta LOWVOL, tabla `per_symbol` del artefacto `results/runs/5c5cbbe6443fb391.json`)

| simbolo | n trades | WR % | PnL eq % |
|---|---|---|---|
| ADAUSDT | 7 | 57.1 | 12.12 |
| ARBUSDT | 3 | 33.3 | 11.50 |
| AVAXUSDT | 7 | 42.9 | -24.60 |
| BNBUSDT | 4 | 50.0 | 155.94 |
| BTCUSDT | 2 | 100.0 | 91.51 |
| DOGEUSDT | 10 | 70.0 | 11.91 |
| ETHUSDT | 4 | 75.0 | 33.83 |
| HYPEUSDT | 1 | 0.0 | -12.52 |
| JUPUSDT | 3 | 66.7 | -11.67 |
| LINKUSDT | 5 | 60.0 | -4.77 |
| NEARUSDT | 6 | 16.7 | -100.76 |
| SOLUSDT | 4 | 50.0 | -45.02 |
| SUIUSDT | 2 | 0.0 | -40.19 |
| XRPUSDT | 7 | 57.1 | 2.75 |

## Hallazgos declarados

- El promedio de exposicion bruta de LOWVOL se mide en su artefacto (107.6 por ciento): el resize funciona. En SKEW y AUTOCORR el promedio de exposicion es bajo porque el libro perdio casi todo en dos mil veinte y dos mil veintiuno y siguio operando a fraccion constante del equity restante — consecuencia del resultado, no un defecto mecanico.
- SKEW y AUTOCORR pierden ANTES de costes (PF ex-cost por debajo de uno): el fallo es de senal, no de coste.
- LOWVOL tiene PF bruto por encima de uno pero por debajo del umbral, concentracion extrema y OOS por debajo de uno.
- El vecindario no resucita ninguna carta: las seis celdas fallan.
- Funding no cobrado (declarado): para un libro dolar-neutro de holding catorce dias es de segundo orden, pero no medido aqui.

## Veredicto

**Categoría A (LOWVOL / SKEW / AUTOCORR sobre el universe-14 a una hora): KILLED — cero de tres cartas supera los gates, y el vecindario confirma que no es un problema de parametro.** La familia cross-sectional de factores de precio OHLCV (volatilidad, skewness, autocorrelacion) muere por senal (dos de tres PF bruto < 1), concentracion y OOS; el resultado es consistente con el kill previo del libro de momentum equal-weight (concentracion, artefacto `00d2a8549e6c898d`). La reivindicacion de MP-18 del prompt externo sigue sin artefacto en este repositorio: estos nueve artefactos no la confirman.

