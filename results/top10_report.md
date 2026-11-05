# top10 — validacion formal de la shortlist de la criba de cien prompts

Las diez estrategias de `TOP10_ESTRATEGIAS.md` (criba 2026-11-01 sobre cien prompts) 
a traves del puerto congelado `code/top10_engine.py` (adaptador `top10`). Coste 
oficial del repo: fee 5.0 bps + slippage 0.5 bps por lado = 11.0 bps roundtrip. 
Sizing de la criba: uno por ciento de equity en riesgo por trade; el split IS/OOS por numero de barras es el del artefacto (campo split_bar).

**Auditoria del puerto (antes de cualquier run):** respuestas conocidas 
`code/_top10_audit.py`, todas PASS (fill siguiente apertura, gap-through, 
stop-out en barra de entrada, empate senal-stop, trailing chandelier, time stop, 
signos de funding, coste en R, flip long-short, timing de #73/#71/#95/#59/#34/#28/#60). 
Paridad `code/_top10_parity.py` completa, PASS: trade a trade identico al motor 
fuente `backtest_prompts100/btlib.py` sobre los mismos bytes, curvas de equity 
bit a bit, y TODAS las metricas publicadas de la criba (`results_100.csv`) 
reproducidas; ademas invarianza por truncamiento (sin lookahead).

Los 10 artefactos verifican bit a bit (`vrun verify`). Cada tabla cita su run_id; 
el path del artefacto es `results/runs/<run_id>.json`.

## Gates aplicados (declarados antes de leer los veredictos)

- **screen** (contrato de la criba): PF mayor que 1.2, n >= 30, net mayor que 0 — en la ventana 
  completa Y en el segmento OOS.
- **conc** (forma cbpackf): share del PnL en las mejores cinco trades menor que uno y net sin ellas mayor que cero (campos top5_pnl_share y net_without_top5).
- **thirds**: net positivo en al menos 2 de 3 tercios del window.
- **sig**: bootstrap por bloques (bloque de 10 trades, 2000 remuestreos, seed 
  20261101) del R medio por trade con IC95 excluyendo cero.

Controles medidos dentro de cada artefacto (no deciden, diagnostican): coste 
cero, coste doble, mitades, meses verdes, apalancamiento implicito, empates 
senal-stop, funding para la #95.

## Resumen (11 bps; todos los numeros de los artefactos)

| # | Estrategia | Par | run_id | n | PF | net% | DD% | OOS n | OOS PF | OOS net% | OOS exceso% | screen | conc | thirds | sig | veredicto |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 60 | Keltner con RSI | HYPE | `de7605f0ed27044a` | 128 | 1.60 | +40.3 | -9.9 | 42 | 1.61 | +12.2 | -40.5 | PASS | FAIL | PASS | PASS | KILLED (concentracion) |
| 44 | 168-bar breakout | BTC | `62468f4aaf6ede7a` | 161 | 2.54 | +368.0 | -21.4 | 52 | 1.52 | +18.7 | -25.1 | PASS | PASS | PASS | PASS | CANDIDATE |
| 73 | Sunday-to-Monday reversion | ETH | `04c2ae793f3fcb97` | 128 | 1.45 | +37.5 | -20.1 | 42 | 1.45 | +10.0 | +22.1 | PASS | FAIL | PASS | FAIL | KILLED (concentracion) |
| 71 | Hour-of-day filter | JUP | `fdc6a1783b45c877` | 97 | 1.26 | +15.8 | -15.3 | 30 | 1.38 | +12.5 | -15.3 | PASS | FAIL | PASS | FAIL | KILLED (concentracion) |
| 28 | Donchian breakout | BTC | `e80247ec32b0579b` | 430 | 1.37 | +113.7 | -21.4 | 138 | 1.30 | +19.2 | -24.6 | PASS | PASS | PASS | PASS | CANDIDATE |
| 56 | Donchian chandelier | JUP | `0a50a498888f4e76` | 299 | 1.01 | -1.6 | -17.0 | 89 | 1.27 | +11.7 | -16.0 | FAIL | FAIL | FAIL | FAIL | KILLED (gate completo) |
| 95 | Price-funding divergence | SUI | `2238dab3387fa706` | 153 | 1.25 | +21.0 | -12.0 | 36 | 1.17 | +1.4 | +64.8 | FAIL | FAIL | PASS | FAIL | KILLED (OOS PF bajo el gate) |
| 26 | EMA cross | ETH | `a861c6d5259fe18f` | 1134 | 1.36 | +444.7 | -29.1 | 385 | 1.09 | +15.6 | +27.7 | FAIL | PASS | PASS | PASS | KILLED (OOS PF bajo el gate) |
| 34 | Regression slope | SOL | `805f2d1edbbd61fc` | 1096 | 1.26 | +355.0 | -26.5 | 332 | 1.06 | +4.8 | +51.4 | FAIL | PASS | PASS | PASS | KILLED (OOS PF bajo el gate) |
| 59 | Range expansion | SOL | `5f69e40e4c3f5674` | 533 | 1.25 | +40.9 | -17.3 | 155 | 1.03 | +0.9 | +47.4 | FAIL | PASS | PASS | FAIL | KILLED (OOS PF bajo el gate) |

Dos de las diez limpian los cuatro gates: la #44 y la #28, ambas BTC 1h. 
Las otras ocho mueren con la razon medida en su artefacto.

## Detalle por estrategia (mediciones del artefacto)

### #60 Keltner con RSI — HYPEUSDT · run_id `de7605f0ed27044a`

- Ventana: 2025-05-30 a 2026-10-29 (12421 barras 1h); split OOS en la barra 8694.
- IS: n 86, PF 1.60, net +25.1%. OOS: n 42, PF 1.61, net +12.2%, DD -8.4%, exceso vs B&H -40.5pp (B&H OOS +52.6%).
- Concentracion: mejores 5 trades = 1.105 del PnL total; net sin ellas -0.047; PF sin ellas 0.94.
- Tercios (net en fraccion): [0.098, 0.064, 0.203] (verdes: 3 de 3); mitades: +0.119 / +0.254.
- Significacion: R medio 0.285, IC95 bootstrap [0.060, 0.516], t 1.56.
- Coste cero: PF 1.74 / OOS PF 1.76 (net OOS +0.147). A coste doble: PF 1.48 / OOS PF 1.47.
- Meses verdes: 0.765 de 17 (peor mes -5.7%). Apalancamiento implicito: mediana 0.37x, max 0.85x.
- Fills: 7 trades con senal de salida ejecutada en la apertura con stop tambien tocado esa barra (orden del motor fuente); 5 stop-outs en la propia barra de entrada; 0 salidas con apertura mas alla del stop.
- **Veredicto: KILLED (concentracion).**

### #44 168-bar breakout — BTCUSDT · run_id `62468f4aaf6ede7a`

- Ventana: 2019-09-08 a 2026-10-27 (62548 barras 1h); split OOS en la barra 43783.
- IS: n 109, PF 3.05, net +294.2%. OOS: n 52, PF 1.52, net +18.7%, DD -21.4%, exceso vs B&H -25.1pp (B&H OOS +43.8%).
- Concentracion: mejores 5 trades = 0.850 del PnL total; net sin ellas +0.250; PF sin ellas 1.23.
- Tercios (net en fraccion): [1.07, 0.894, 0.194] (verdes: 3 de 3); mitades: +2.063 / +0.528.
- Significacion: R medio 1.135, IC95 bootstrap [0.261, 2.208], t 2.21.
- Coste cero: PF 2.74 / OOS PF 1.67 (net OOS +0.235). A coste doble: PF 2.37 / OOS PF 1.39.
- Meses verdes: 0.400 de 80 (peor mes -5.2%). Apalancamiento implicito: mediana 0.57x, max 1.54x.
- Fills: 2 trades con senal de salida ejecutada en la apertura con stop tambien tocado esa barra (orden del motor fuente); 5 stop-outs en la propia barra de entrada; 0 salidas con apertura mas alla del stop.
- **Veredicto: CANDIDATE.**

### #73 Sunday-to-Monday reversion — ETHUSDT · run_id `04c2ae793f3fcb97`

- Ventana: 2019-11-27 a 2026-10-27 (60638 barras 1h); split OOS en la barra 42446.
- IS: n 86, PF 1.46, net +25.0%. OOS: n 42, PF 1.45, net +10.0%, DD -9.8%, exceso vs B&H +22.1pp (B&H OOS -12.1%).
- Concentracion: mejores 5 trades = 1.213 del PnL total; net sin ellas -0.082; PF sin ellas 0.90.
- Tercios (net en fraccion): [0.315, -0.066, 0.12] (verdes: 2 de 3); mitades: +0.188 / +0.158.
- Significacion: R medio 0.275, IC95 bootstrap [-0.161, 0.620], t 1.33.
- Coste cero: PF 1.61 / OOS PF 1.62 (net OOS +0.133). A coste doble: PF 1.32 / OOS PF 1.30.
- Meses verdes: 0.446 de 65 (peor mes -3.4%). Apalancamiento implicito: mediana 0.54x, max 2.16x.
- Fills: 2 trades con senal de salida ejecutada en la apertura con stop tambien tocado esa barra (orden del motor fuente); 11 stop-outs en la propia barra de entrada; 0 salidas con apertura mas alla del stop.
- **Veredicto: KILLED (concentracion).**

### #71 Hour-of-day filter — JUPUSDT · run_id `fdc6a1783b45c877`

- Ventana: 2024-01-31 a 2026-10-29 (24053 barras 1h); split OOS en la barra 16837.
- IS: n 67, PF 1.21, net +3.4%. OOS: n 30, PF 1.38, net +12.5%, DD -12.5%, exceso vs B&H -15.3pp (B&H OOS +27.7%).
- Concentracion: mejores 5 trades = 2.328 del PnL total; net sin ellas -0.218; PF sin ellas 0.65.
- Tercios (net en fraccion): [-0.129, 0.215, 0.096] (verdes: 2 de 3); mitades: +0.072 / +0.091.
- Significacion: R medio 0.181, IC95 bootstrap [-0.220, 0.691], t 0.72.
- Coste cero: PF 1.33 / OOS PF 1.45 (net OOS +0.138). A coste doble: PF 1.20 / OOS PF 1.31.
- Meses verdes: 0.469 de 32 (peor mes -5.1%). Apalancamiento implicito: mediana 0.32x, max 0.64x.
- Fills: 5 trades con senal de salida ejecutada en la apertura con stop tambien tocado esa barra (orden del motor fuente); 1 stop-outs en la propia barra de entrada; 0 salidas con apertura mas alla del stop.
- **Veredicto: KILLED (concentracion).**

### #28 Donchian breakout — BTCUSDT · run_id `e80247ec32b0579b`

- Ventana: 2019-09-08 a 2026-10-27 (62548 barras 1h); split OOS en la barra 43783.
- IS: n 292, PF 1.41, net +79.2%. OOS: n 138, PF 1.30, net +19.2%, DD -21.4%, exceso vs B&H -24.6pp (B&H OOS +43.8%).
- Concentracion: mejores 5 trades = 0.888 del PnL total; net sin ellas +0.034; PF sin ellas 1.04.
- Tercios (net en fraccion): [0.392, 0.34, 0.146] (verdes: 3 de 3); mitades: +0.648 / +0.296.
- Significacion: R medio 0.206, IC95 bootstrap [0.009, 0.438], t 1.70.
- Coste cero: PF 1.51 / OOS PF 1.46 (net OOS +0.311). A coste doble: PF 1.25 / OOS PF 1.16.
- Meses verdes: 0.477 de 86 (peor mes -8.4%). Apalancamiento implicito: mediana 0.45x, max 2.66x.
- Fills: 22 trades con senal de salida ejecutada en la apertura con stop tambien tocado esa barra (orden del motor fuente); 5 stop-outs en la propia barra de entrada; 0 salidas con apertura mas alla del stop.
- **Veredicto: CANDIDATE.**

### #56 Donchian chandelier — JUPUSDT · run_id `0a50a498888f4e76`

- Ventana: 2024-01-31 a 2026-10-29 (24053 barras 1h); split OOS en la barra 16837.
- IS: n 210, PF 0.88, net -11.7%. OOS: n 89, PF 1.27, net +11.7%, DD -10.1%, exceso vs B&H -16.0pp (B&H OOS +27.7%).
- Concentracion: mejores 5 trades = 39.140 del PnL total; net sin ellas -0.258; PF sin ellas 0.77.
- Tercios (net en fraccion): [-0.055, -0.039, 0.084] (verdes: 1 de 3); mitades: -0.069 / +0.063.
- Significacion: R medio 0.002, IC95 bootstrap [-0.106, 0.126], t 0.03.
- Coste cero: PF 1.07 / OOS PF 1.34 (net OOS +0.144). A coste doble: PF 0.95 / OOS PF 1.21.
- Meses verdes: 0.485 de 33 (peor mes -4.5%). Apalancamiento implicito: mediana 0.21x, max 0.51x.
- Fills: 0 trades con senal de salida ejecutada en la apertura con stop tambien tocado esa barra (orden del motor fuente); 4 stop-outs en la propia barra de entrada; 0 salidas con apertura mas alla del stop.
- **Veredicto: KILLED (gate completo).**

### #95 Price-funding divergence — SUIUSDT · run_id `2238dab3387fa706`

- Ventana: 2023-05-03 a 2026-10-27 (30557 barras 1h); split OOS en la barra 21389.
- IS: n 117, PF 1.27, net +12.1%. OOS: n 36, PF 1.17, net +1.4%, DD -5.0%, exceso vs B&H +64.8pp (B&H OOS -63.4%).
- Concentracion: mejores 5 trades = 1.220 del PnL total; net sin ellas -0.056; PF sin ellas 0.95.
- Tercios (net en fraccion): [0.096, 0.021, 0.083] (verdes: 3 de 3); mitades: +0.067 / +0.133.
- Significacion: R medio 0.137, IC95 bootstrap [-0.084, 0.340], t 1.08.
- Coste cero: PF 1.33 / OOS PF 1.26 (net OOS +0.029). A coste doble: PF 1.17 / OOS PF 1.09.
- Meses verdes: 0.524 de 42 (peor mes -4.8%). Apalancamiento implicito: mediana 0.32x, max 0.78x.
- Fills: 0 trades con senal de salida ejecutada en la apertura con stop tambien tocado esa barra (orden del motor fuente); 1 stop-outs en la propia barra de entrada; 0 salidas con apertura mas alla del stop.
- Funding (#95): settlements totales 3825, cobrados con posicion abierta 313, bars_after_last_settlement 0, funding_covers_bars true.
- **Veredicto: KILLED (OOS PF bajo el gate).**

### #26 EMA cross — ETHUSDT · run_id `a861c6d5259fe18f`

- Ventana: 2019-11-27 a 2026-10-27 (60638 barras 1h); split OOS en la barra 42446.
- IS: n 749, PF 1.50, net +371.7%. OOS: n 385, PF 1.09, net +15.6%, DD -24.8%, exceso vs B&H +27.7pp (B&H OOS -12.1%).
- Concentracion: mejores 5 trades = 0.706 del PnL total; net sin ellas +0.551; PF sin ellas 1.11.
- Tercios (net en fraccion): [1.569, 0.793, 0.187] (verdes: 3 de 3); mitades: +2.674 / +0.480.
- Significacion: R medio 0.184, IC95 bootstrap [0.052, 0.351], t 2.17.
- Coste cero: PF 1.48 / OOS PF 1.19 (net OOS +0.377). A coste doble: PF 1.25 / OOS PF 1.00.
- Meses verdes: 0.578 de 83 (peor mes -11.7%). Apalancamiento implicito: mediana 0.35x, max 3.02x.
- Fills: 38 trades con senal de salida ejecutada en la apertura con stop tambien tocado esa barra (orden del motor fuente); 3 stop-outs en la propia barra de entrada; 0 salidas con apertura mas alla del stop.
- **Veredicto: KILLED (OOS PF bajo el gate).**

### #34 Regression slope — SOLUSDT · run_id `805f2d1edbbd61fc`

- Ventana: 2020-09-14 a 2026-10-27 (53630 barras 1h); split OOS en la barra 37541.
- IS: n 764, PF 1.35, net +333.3%. OOS: n 332, PF 1.06, net +4.8%, DD -26.4%, exceso vs B&H +51.4pp (B&H OOS -46.5%).
- Concentracion: mejores 5 trades = 0.478 del PnL total; net sin ellas +1.037; PF sin ellas 1.13.
- Tercios (net en fraccion): [0.916, 1.011, 0.185] (verdes: 3 de 3); mitades: +2.214 / +0.418.
- Significacion: R medio 0.167, IC95 bootstrap [0.027, 0.308], t 2.26.
- Coste cero: PF 1.35 / OOS PF 1.16 (net OOS +0.275). A coste doble: PF 1.18 / OOS PF 0.98.
- Meses verdes: 0.541 de 74 (peor mes -13.2%). Apalancamiento implicito: mediana 0.38x, max 1.77x.
- Fills: 15 trades con senal de salida ejecutada en la apertura con stop tambien tocado esa barra (orden del motor fuente); 14 stop-outs en la propia barra de entrada; 0 salidas con apertura mas alla del stop.
- **Veredicto: KILLED (OOS PF bajo el gate).**

### #59 Range expansion — SOLUSDT · run_id `5f69e40e4c3f5674`

- Ventana: 2020-09-14 a 2026-10-27 (53630 barras 1h); split OOS en la barra 37541.
- IS: n 378, PF 1.35, net +39.7%. OOS: n 155, PF 1.03, net +0.9%, DD -8.3%, exceso vs B&H +47.4pp (B&H OOS -46.5%).
- Concentracion: mejores 5 trades = 0.729 del PnL total; net sin ellas +0.085; PF sin ellas 1.07.
- Tercios (net en fraccion): [0.335, 0.057, -0.001] (verdes: 2 de 3); mitades: +0.568 / -0.101.
- Significacion: R medio 0.069, IC95 bootstrap [-0.021, 0.163], t 1.64.
- Coste cero: PF 1.41 / OOS PF 1.20 (net OOS +0.086). A coste doble: PF 1.11 / OOS PF 0.89.
- Meses verdes: 0.534 de 73 (peor mes -4.6%). Apalancamiento implicito: mediana 0.30x, max 1.06x.
- Fills: 32 trades con senal de salida ejecutada en la apertura con stop tambien tocado esa barra (orden del motor fuente); 12 stop-outs en la propia barra de entrada; 0 salidas con apertura mas alla del stop.
- **Veredicto: KILLED (OOS PF bajo el gate).**

## Hallazgos de la auditoria (cambian el estado del mundo)

1. **La criba es real y reproducible.** El motor fuente y sus 10 filas de 
`results_100.csv` se reproducen bit a bit desde los bytes de datos del repo; 
los numeros de `TOP10_ESTRATEGIAS.md` no eran texto suelto.

2. **El doc fuente describe mal una convencion.** Dice *el stop gana empates* 
pero el motor fuente ejecuta la senal de salida en la apertura ANTES del check 
de stop (orden mas favorable). El puerto sigue al MOTOR (es lo que se midio) y 
cuenta los afectados: 7 en #60, 2 en #44, 2 en #73, 5 en #71, 22 en #28, 
0 en #56, 0 en #95, 38 en #26, 15 en #34, 32 en #59. Con la convencion del doc 
los resultados serian algo peores, no mejores.

3. **El OOS de la shortlist esta contaminado por seleccion.** La criba ordeno 
las cien por OOS PF y shortliste las diez mejores: ese OOS ya no es out-of-sample 
para ellas. Con cien ensayos (y mas de mil artefactos repo-wide) el haircut de 
multiples pruebas se aplica entero: ninguna de las dos CANDIDATE sobrevive una 
correccion tipo Bonferroni sobre cien ensayos. El reporte de los cinco supervivientes 
de 2026-10-29 (`results/prompts100_survivors_report.md`, sin guard) ya exigia 
deflated Sharpe / PBO; sigue pendiente.

4. **B&H: las dos CANDIDATE pierden contra el activo en su OOS** (exceso 
de alrededor de veinticinco puntos ambas, campo OOS exceso de cada artefacto): son libros long/flat en una ventana alcista de BTC. 
Es una question de estructura de despliegue, no de senal — el reporte previo ya 
lo decia.

5. **Datos:** JUPUSDT 1h (24053 barras, 2024-01-31 a 2026-10-29) entro al repo 
como archivo nuevo `data/binance_klines_1h/JUPUSDT_1h.csv`, sha 940da24b8416a793, 
datacheck limpio (cero huecos/duplicados/OHLC invalido) y anotado en 
`data/KLINES_MANIFEST.json`. La cola HYPE del repo es byte-identica a la de la 
criba (sha de4e8815401ee17a). El funding de SUI cubre todas las barras de la #95.

## Veredicto

**Dos de diez (#44 168-bar breakout BTC 1h y #28 Donchian breakout BTC 1h) 
limpian los cuatro gates medidos — los primeros libros direccionales de la 
historia del repo en hacerlo con artefactos.** NO son alfa validada: el OOS 
vino de una seleccion sobre cien estrategias, el haircut de multiples pruebas 
se aplica entero, y la #28 es fina incluso antes del haircut (IC bootstrap bajo 
en 0.009; PF 1.04 sin sus mejores cinco trades; OOS PF 1.16 a coste doble). La #44 
es la mas solida de la shortlist (PF 2.54 en la ventana completa y 1.52 en OOS, IC bootstrap excluyendo cero, tercios tres de tres, aguanta a coste doble con OOS PF 1.39). Siguiente paso obligatorio segun la doctrina 
del repo: registro FORWARD en barras nuevas (lo que certifico y luego mato al 
libro neutral XRP), no mas re-corridas sobre la misma historia.
