# fvgup — ICT 4H FVG → 15M FVG con resolución 1m y sesiones (adjunto del 13 de noviembre de 2026)

## VEREDICTO: KILLED — cero de cuatro celdas pasa la batería estándar

La tesis de ejecución del adjunto SÍ se materializó tras el porte (la resolución
intrabar a 1m funciona, la ambigüedad stop/target se resuelve, la integridad de la
cinta es cercana al cien por ciento), pero el libro resultante no supera la batería:
muestra por debajo del suelo en las tres cartas de BTC, concentración extrema, y
ninguna celda bate a comprar-y-mantener. El filo bruto existe (PF ex-cost entre
uno coma cinco y dos coma siete) y el régimen de costes del repo lo consume: las
comisiones totales rondan el cinco por ciento del equity en la ventana.

Fuente de registro: `code/fvg_system.py` + `code/fvg_upgrades.py` (adjuntos
byte-idénticos; sha del segundo fijado en `code/_fvgup_build_sha.json`). Adaptador
`fvgup`, motor `code/fvgup_engine.py`. Pre-registro con adición fechada:
`results/fvgup_pre_registration.md`. Ventana: la cobertura 1m del repositorio,
del uno de enero de dos mil veintitrés al uno de octubre de dos mil veintiséis.
Costes repo inyectados por el llamador (cinco bps de comisión más medio de
deslizamiento por lado); funding = modelo de tarifa constante del pack
(aproximación declarada; los ficheros reales de funding no están cableados al
motor del pack, que no es editable).

## Defectos del pack medidos durante el puerto

- **La paridad dual-motor del pack FALLA en BTC y PASA en ETH.** En la carta
  BTCFINE el artefacto mide veintisiete trades del motor vector contra
  veintiocho del motor de eventos: un LONG solo del motor de eventos
  (entrada 56331.8, llenado 2024-09-11 08:30 UTC, bars=0, zona bull 323) que
  el motor vector no genera — los dos motores discrepan en la semántica de
  re-arme de una zona viva. Un parche de una línea (resetear el estado en la
  invalidación, semántica vector) se probó y NO resolvió la divergencia: se
  revirtió; la reconciliación es decisión del autor. En la carta ETHFINE la
  paridad del pack SÍ se cumple. Cada artefacto publica `parity_ok` y la tabla
  `parity_divergence` trade a trade; el pack se niega a publicar sus propios
  números en este estado y esta campaña declara la desviación en cada celda.
- **Dos defectos de unidades de pandas 3.0** (el pack es código de pandas 2.x;
  el repo corre 3.0.5). Primero: la ventana de búsqueda de FineData mezclaba
  enteros de microsegundo del índice con un entero de nanosegundo del
  Timedelta — ventana mil veces más ancha, integridad fallida en todas las
  barras y el libro fino corría grueso sin decrirlo (medido: cnt ≈ quince mil
  barras de un minuto por barra de quince minutos). Corregido con el builder
  `code/_fvgup_build.py` → `code/fvg_upgrades_portfix.py` (un parche literal,
  sha fijado). Segundo: `to_datetime(unit="ms")` conserva la unidad en
  pandas 3.0 y el índice quedaba en milisegundos contra aritmética de
  nanosegundos del pack — ninguna orden fina llenaba (cero trades). Corregido
  en el adaptador normalizando ambos índices a nanosegundos.
- **La contabilidad del pack cobra la comisión de entrada FUERA del pnl del
  trade** (la columna fees la incluye, el pnl no la resta) y el funding fuera
  del pnl también. La invariante del repositorio se reformuló para esta
  contabilidad y cierra al céntimo: equity final − inicial == Σpnl − Σfunding
  − Σ(comisión de entrada por trade); residual publicado en cada artefacto.

## Las cuatro celdas (verificadas bit-for-bit; run_id citado por línea)

| Carta | run_id | net % | PF | PF ex-cost | n | WR % | IS PF | OOS PF | maxDD % | B&H % | top-5 % PnL | comisiones USDT | fine usable % | paridad pack |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BTCFINE | `7dfd3c4de2f6765e` | -0.59 | 1.3335 | 2.6627 | 28 | 64.3 | 1.4775 | 1.1934 | -2.91 | 405.99 | 172.0 | 506.3 | 99.99 | FALLA (declarada) |
| BTCCOARSE | `7924a180df2bbb96` | -0.90 | 1.2560 | 2.4458 | 28 | 60.7 | 1.3041 | 1.1998 | -2.73 | 405.99 | 201.6 | 505.6 | n/a | FALLA (declarada) |
| BTCNOSESS | `bc3d3dc1af3fcd47` | -19.29 | 0.7354 | 1.5552 | 126 | 52.4 | 0.8100 | 0.5199 | -20.03 | 405.99 | n/a | 2127.0 | 99.99 | FALLA (declarada) |
| ETHFINE | `fdf4391a289b3fd6` | -3.73 | 0.8604 | 1.7030 | 34 | 58.8 | 0.7428 | 1.0243 | -5.35 | 124.79 | n/a | 522.1 | 99.99 | OK |

Bandera por artefacto:

- `7dfd3c4de2f6765e`: `FAIL-GATES:n_trades_ge_30,green_years_frac,conc_top5_lt_100,net_without_top5_pos,beats_bh`
- `7924a180df2bbb96`: `FAIL-GATES:n_trades_ge_30,green_years_frac,conc_top5_lt_100,net_without_top5_pos,beats_bh`
- `bc3d3dc1af3fcd47`: `FAIL-GATES:oos_pf_ge_1,green_years_frac,conc_top5_lt_100,net_without_top5_pos,beats_bh`
- `fdf4391a289b3fd6`: `FAIL-GATES:green_years_frac,conc_top5_lt_100,net_without_top5_pos,beats_bh`

Modelo de fill por carta: BTCFINE / BTCNOSESS / ETHFINE resuelven los llenados
maker en la cinta de 1m (certificables según la regla fill-model); BTCCOARSE usa
la convención de barra de 15m (NO certificable, comparación declarada). La
resolución fina funciona tras el parche de unidades: en las cartas finas el
número de barras resueltas en cinta es de unos ciento treinta mil contra unas
veinte gruesas, y la ambigüedad stop/target del convenio grueso (seis casos en
BTCCOARSE) baja a cero.

## Atribución por sesión (carta BTCFINE, tabla `session_attribution` del
artefacto `results/runs/7dfd3c4de2f6765e.json`)

| sesión | n trades | WR % | exp_r | PnL USDT | PF |
|---|---|---|---|---|---|
| ny_am | 16 | 62.5 | 0.172 | 133.04 | 1.3841 |
| outside | 4 | 75.0 | 0.302 | 59.91 | 2.0345 |
| london | 8 | 62.5 | 0.009 | 3.20 | 1.0174 |

La ablación de sesiones es el hallazgo vivo del adjunto: sin ventanas, el libro
pierde casi veinte por ciento (carta BTCNOSESS); con London + NY-AM el libro
queda cerca del cero. El filtro de sesiones ELIMINA las horas perdedoras — pero
el libro resultante sigue sin pasar la batería.

## Gates medidos por carta (tabla `gates` de cada artefacto)

Artefacto: `results/runs/7dfd3c4de2f6765e` (json)

| gate | umbral | medido | pasa |
|---|---|---|---|
| pf_ex_cost_gt_1.2 | >1.2 | 2.6627 | SI |
| n_trades_ge_30 | >=30 | 28 | NO |
| oos_pf_ge_1 | >=1 (OOS PF < 1 = KILL) | 1.1934 | SI |
| green_years_frac | >=2/3 years green | 2/4 | NO |
| conc_top5_lt_100 | <100% of PnL | 171.9941 | NO |
| net_without_top5_pos | >0% | -3.9603 | NO |
| g11_winrate_buffer | wr>=75 needs wr>=breakeven+5pp | 57.2955 | SI |
| beats_bh | net > B&H (405.99307397047954) | False | NO |

Artefacto: `results/runs/7924a180df2bbb96` (json)

| gate | umbral | medido | pasa |
|---|---|---|---|
| pf_ex_cost_gt_1.2 | >1.2 | 2.4458 | SI |
| n_trades_ge_30 | >=30 | 28 | NO |
| oos_pf_ge_1 | >=1 (OOS PF < 1 = KILL) | 1.1998 | SI |
| green_years_frac | >=2/3 years green | 2/4 | NO |
| conc_top5_lt_100 | <100% of PnL | 201.5922 | NO |
| net_without_top5_pos | >0% | -4.2342 | NO |
| g11_winrate_buffer | wr>=75 needs wr>=breakeven+5pp | 55.0025 | SI |
| beats_bh | net > B&H (405.99307397047954) | False | NO |

Artefacto: `results/runs/bc3d3dc1af3fcd47` (json)

| gate | umbral | medido | pasa |
|---|---|---|---|
| pf_ex_cost_gt_1.2 | >1.2 | 1.5552 | SI |
| n_trades_ge_30 | >=30 | 126 | SI |
| oos_pf_ge_1 | >=1 (OOS PF < 1 = KILL) | 0.5199 | NO |
| green_years_frac | >=2/3 years green | 0/4 | NO |
| conc_top5_lt_100 | <100% of PnL | None | NO |
| net_without_top5_pos | >0% | -22.6543 | NO |
| g11_winrate_buffer | wr>=75 needs wr>=breakeven+5pp | 59.8975 | SI |
| beats_bh | net > B&H (405.99307397047954) | False | NO |

Artefacto: `results/runs/fdf4391a289b3fd6` (json)

| gate | umbral | medido | pasa |
|---|---|---|---|
| pf_ex_cost_gt_1.2 | >1.2 | 1.7030 | SI |
| n_trades_ge_30 | >=30 | 34 | SI |
| oos_pf_ge_1 | >=1 (OOS PF < 1 = KILL) | 1.0243 | SI |
| green_years_frac | >=2/3 years green | 1/4 | NO |
| conc_top5_lt_100 | <100% of PnL | None | NO |
| net_without_top5_pos | >0% | -6.6348 | NO |
| g11_winrate_buffer | wr>=75 needs wr>=breakeven+5pp | 62.1695 | SI |
| beats_bh | net > B&H (124.78920883187783) | False | NO |

## Veredicto

**Campaña fvgup: KILLED — cero de cuatro celdas pasa la batería estándar.**
Las tres cartas de BTC mueren por muestra (veintiocho trades en tres años y
tres cuartos, por debajo del suelo de treinta), concentración (el top cinco de
trades es entre ciento setenta y dos y doscientos uno por ciento del PnL) y
ausencia de ventaja contra comprar-y-mantener (+405.99 por ciento en la misma
ventana). La celda sin sesiones pierde diecinueve por ciento neto con PF neto
por debajo de uno y OOS PF cero coma cinco dos — kill directo. La carta de ETH
alcanza muestra y OOS, pero pierde neto (PF neto cero coma ocho seis) y falla
concentración y B&H. El filo bruto es real (PF ex-cost entre uno coma cinco y
dos coma siete) y el régimen de costes del repo lo consume — el mismo patrón
que el resto del corpus. La paridad dual-motor del pack queda marcada como
defecto del autor: falla en BTC, pasa en ETH; ningún número de este informe
usa la verificación dual hasta que el autor reconcilie la semántica de re-arme.

