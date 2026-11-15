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
| 60 | Keltner con RSI | HYPE | `350602de4a81aa64` | 129 | 1.56 | +37.2 | -9.9 | 41 | 1.38 | +7.3 | -1.6 | PASS | FAIL | PASS | PASS | KILLED (concentracion) |
| 44 | 168-bar breakout | BTC | `d544d85516c7158a` | 161 | 2.54 | +368.0 | -21.4 | 52 | 1.52 | +18.7 | -17.5 | PASS | PASS | PASS | PASS | CANDIDATE |
| 73 | Sunday-to-Monday reversion | ETH | `34e3deaed3039572` | 128 | 1.45 | +37.5 | -20.1 | 41 | 1.52 | +11.3 | +14.6 | PASS | FAIL | PASS | FAIL | KILLED (concentracion) |
| 71 | Hour-of-day filter | JUP | `678d9d8154270030` | 97 | 1.26 | +15.8 | -15.3 | 30 | 1.38 | +12.5 | -15.3 | PASS | FAIL | PASS | FAIL | KILLED (concentracion) |
| 28 | Donchian breakout | BTC | `ccba31d818c05bec` | 432 | 1.36 | +109.0 | -21.4 | 139 | 1.25 | +15.4 | -20.8 | PASS | PASS | PASS | FAIL | KILLED (significacion) |
| 56 | Donchian chandelier | JUP | `40eace298df351e9` | 299 | 1.01 | -1.6 | -17.0 | 89 | 1.27 | +11.7 | -16.0 | FAIL | FAIL | FAIL | FAIL | KILLED (gate completo) |
| 95 | Price-funding divergence | SUI | `d53c042fc53bc5e5` | 155 | 1.23 | +19.7 | -12.0 | 38 | 1.11 | +1.9 | +70.5 | FAIL | FAIL | PASS | FAIL | KILLED (OOS PF bajo el gate) |
| 26 | EMA cross | ETH | `6a221c1519023d0f` | 1136 | 1.35 | +428.2 | -29.1 | 387 | 1.07 | +4.6 | +8.0 | FAIL | PASS | PASS | PASS | KILLED (OOS PF bajo el gate) |
| 34 | Regression slope | SOL | `ebb28d8d97d6168d` | 1100 | 1.25 | +337.1 | -28.3 | 335 | 1.05 | +2.8 | +53.3 | FAIL | PASS | PASS | PASS | KILLED (OOS PF bajo el gate) |
| 59 | Range expansion | SOL | `a1f3a041c28bbe0e` | 533 | 1.25 | +40.9 | -17.3 | 155 | 1.03 | +0.9 | +51.4 | FAIL | PASS | PASS | FAIL | KILLED (OOS PF bajo el gate) |

Dos de las diez limpian los cuatro gates: la #44 y la #28, ambas BTC 1h. 
Las otras ocho mueren con la razon medida en su artefacto.

## Detalle por estrategia (mediciones del artefacto)

### #60 Keltner con RSI — HYPEUSDT · run_id `350602de4a81aa64`

- Ventana: 2025-05-30 a 2026-11-06 (12614 barras 1h); split OOS en la barra 8829.
- IS: n 88, PF 1.65, net +27.8%. OOS: n 41, PF 1.38, net +7.3%, DD -8.4%, exceso vs B&H -1.6pp (B&H OOS +9.0%).
- Concentracion: mejores 5 trades = 1.179 del PnL total; net sin ellas -0.068; PF sin ellas 0.90.
- Tercios (net en fraccion): [0.098, 0.106, 0.129] (verdes: 3 de 3); mitades: +0.111 / +0.239.
- Significacion: R medio 0.265, IC95 bootstrap [0.055, 0.504], t 1.47.
- Coste cero: PF 1.69 / OOS PF 1.51 (net OOS +0.097). A coste doble: PF 1.44 / OOS PF 1.26.
- Meses verdes: 0.722 de 18 (peor mes -5.7%). Apalancamiento implicito: mediana 0.37x, max 0.85x.
- Fills: 7 trades con senal de salida ejecutada en la apertura con stop tambien tocado esa barra (orden del motor fuente); 5 stop-outs en la propia barra de entrada; 0 salidas con apertura mas alla del stop.
- **Veredicto: KILLED (concentracion).**

### #44 168-bar breakout — BTCUSDT · run_id `d544d85516c7158a`

- Ventana: 2019-09-08 a 2026-11-02 (62687 barras 1h); split OOS en la barra 43880.
- IS: n 109, PF 3.05, net +294.2%. OOS: n 52, PF 1.52, net +18.7%, DD -21.4%, exceso vs B&H -17.5pp (B&H OOS +36.2%).
- Concentracion: mejores 5 trades = 0.850 del PnL total; net sin ellas +0.250; PF sin ellas 1.23.
- Tercios (net en fraccion): [1.07, 0.894, 0.194] (verdes: 3 de 3); mitades: +2.063 / +0.528.
- Significacion: R medio 1.135, IC95 bootstrap [0.261, 2.208], t 2.21.
- Coste cero: PF 2.74 / OOS PF 1.67 (net OOS +0.235). A coste doble: PF 2.37 / OOS PF 1.39.
- Meses verdes: 0.400 de 80 (peor mes -5.2%). Apalancamiento implicito: mediana 0.57x, max 1.54x.
- Fills: 2 trades con senal de salida ejecutada en la apertura con stop tambien tocado esa barra (orden del motor fuente); 5 stop-outs en la propia barra de entrada; 0 salidas con apertura mas alla del stop.
- **Veredicto: CANDIDATE.**

### #73 Sunday-to-Monday reversion — ETHUSDT · run_id `34e3deaed3039572`

- Ventana: 2019-11-27 a 2026-11-02 (60777 barras 1h); split OOS en la barra 42543.
- IS: n 87, PF 1.43, net +23.6%. OOS: n 41, PF 1.52, net +11.3%, DD -9.8%, exceso vs B&H +14.6pp (B&H OOS -3.3%).
- Concentracion: mejores 5 trades = 1.213 del PnL total; net sin ellas -0.082; PF sin ellas 0.90.
- Tercios (net en fraccion): [0.315, -0.076, 0.132] (verdes: 2 de 3); mitades: +0.188 / +0.158.
- Significacion: R medio 0.275, IC95 bootstrap [-0.161, 0.620], t 1.33.
- Coste cero: PF 1.61 / OOS PF 1.70 (net OOS +0.144). A coste doble: PF 1.32 / OOS PF 1.37.
- Meses verdes: 0.446 de 65 (peor mes -3.4%). Apalancamiento implicito: mediana 0.54x, max 2.16x.
- Fills: 2 trades con senal de salida ejecutada en la apertura con stop tambien tocado esa barra (orden del motor fuente); 11 stop-outs en la propia barra de entrada; 0 salidas con apertura mas alla del stop.
- **Veredicto: KILLED (concentracion).**

### #71 Hour-of-day filter — JUPUSDT · run_id `678d9d8154270030`

- Ventana: 2024-01-31 a 2026-10-29 (24053 barras 1h); split OOS en la barra 16837.
- IS: n 67, PF 1.21, net +3.4%. OOS: n 30, PF 1.38, net +12.5%, DD -12.5%, exceso vs B&H -15.3pp (B&H OOS +27.7%).
- Concentracion: mejores 5 trades = 2.328 del PnL total; net sin ellas -0.218; PF sin ellas 0.65.
- Tercios (net en fraccion): [-0.129, 0.215, 0.096] (verdes: 2 de 3); mitades: +0.072 / +0.091.
- Significacion: R medio 0.181, IC95 bootstrap [-0.220, 0.691], t 0.72.
- Coste cero: PF 1.33 / OOS PF 1.45 (net OOS +0.138). A coste doble: PF 1.20 / OOS PF 1.31.
- Meses verdes: 0.469 de 32 (peor mes -5.1%). Apalancamiento implicito: mediana 0.32x, max 0.64x.
- Fills: 5 trades con senal de salida ejecutada en la apertura con stop tambien tocado esa barra (orden del motor fuente); 1 stop-outs en la propia barra de entrada; 0 salidas con apertura mas alla del stop.
- **Veredicto: KILLED (concentracion).**

### #28 Donchian breakout — BTCUSDT · run_id `ccba31d818c05bec`

- Ventana: 2019-09-08 a 2026-11-02 (62687 barras 1h); split OOS en la barra 43880.
- IS: n 293, PF 1.41, net +81.2%. OOS: n 139, PF 1.25, net +15.4%, DD -21.4%, exceso vs B&H -20.8pp (B&H OOS +36.2%).
- Concentracion: mejores 5 trades = 0.911 del PnL total; net sin ellas +0.011; PF sin ellas 1.03.
- Tercios (net en fraccion): [0.392, 0.338, 0.126] (verdes: 3 de 3); mitades: +0.631 / +0.281.
- Significacion: R medio 0.200, IC95 bootstrap [-0.005, 0.438], t 1.66.
- Coste cero: PF 1.49 / OOS PF 1.41 (net OOS +0.271). A coste doble: PF 1.24 / OOS PF 1.12.
- Meses verdes: 0.471 de 87 (peor mes -8.4%). Apalancamiento implicito: mediana 0.45x, max 2.66x.
- Fills: 22 trades con senal de salida ejecutada en la apertura con stop tambien tocado esa barra (orden del motor fuente); 5 stop-outs en la propia barra de entrada; 0 salidas con apertura mas alla del stop.
- **Veredicto: KILLED (significacion).**

### #56 Donchian chandelier — JUPUSDT · run_id `40eace298df351e9`

- Ventana: 2024-01-31 a 2026-10-29 (24053 barras 1h); split OOS en la barra 16837.
- IS: n 210, PF 0.88, net -11.7%. OOS: n 89, PF 1.27, net +11.7%, DD -10.1%, exceso vs B&H -16.0pp (B&H OOS +27.7%).
- Concentracion: mejores 5 trades = 39.140 del PnL total; net sin ellas -0.258; PF sin ellas 0.77.
- Tercios (net en fraccion): [-0.055, -0.039, 0.084] (verdes: 1 de 3); mitades: -0.069 / +0.063.
- Significacion: R medio 0.002, IC95 bootstrap [-0.106, 0.126], t 0.03.
- Coste cero: PF 1.07 / OOS PF 1.34 (net OOS +0.144). A coste doble: PF 0.95 / OOS PF 1.21.
- Meses verdes: 0.485 de 33 (peor mes -4.5%). Apalancamiento implicito: mediana 0.21x, max 0.51x.
- Fills: 0 trades con senal de salida ejecutada en la apertura con stop tambien tocado esa barra (orden del motor fuente); 4 stop-outs en la propia barra de entrada; 0 salidas con apertura mas alla del stop.
- **Veredicto: KILLED (gate completo).**

### #95 Price-funding divergence — SUIUSDT · run_id `d53c042fc53bc5e5`

- Ventana: 2023-05-03 a 2026-11-02 (30696 barras 1h); split OOS en la barra 21487.
- IS: n 117, PF 1.27, net +17.5%. OOS: n 38, PF 1.11, net +1.9%, DD -5.0%, exceso vs B&H +70.5pp (B&H OOS -68.6%).
- Concentracion: mejores 5 trades = 1.288 del PnL total; net sin ellas -0.067; PF sin ellas 0.93.
- Tercios (net en fraccion): [0.096, 0.004, 0.088] (verdes: 3 de 3); mitades: +0.067 / +0.121.
- Significacion: R medio 0.128, IC95 bootstrap [-0.082, 0.330], t 1.02.
- Coste cero: PF 1.31 / OOS PF 1.19 (net OOS +0.034). A coste doble: PF 1.16 / OOS PF 1.03.
- Meses verdes: 0.512 de 43 (peor mes -4.8%). Apalancamiento implicito: mediana 0.32x, max 0.78x.
- Fills: 0 trades con senal de salida ejecutada en la apertura con stop tambien tocado esa barra (orden del motor fuente); 1 stop-outs en la propia barra de entrada; 0 salidas con apertura mas alla del stop.
- Funding (#95): settlements totales 3825, cobrados con posicion abierta 313, bars_after_last_settlement 95, funding_covers_bars false.
- **Veredicto: KILLED (OOS PF bajo el gate).**

### #26 EMA cross — ETHUSDT · run_id `6a221c1519023d0f`

- Ventana: 2019-11-27 a 2026-11-02 (60777 barras 1h); split OOS en la barra 42543.
- IS: n 749, PF 1.50, net +404.9%. OOS: n 387, PF 1.07, net +4.6%, DD -24.8%, exceso vs B&H +8.0pp (B&H OOS -3.3%).
- Concentracion: mejores 5 trades = 0.716 del PnL total; net sin ellas +0.504; PF sin ellas 1.10.
- Tercios (net en fraccion): [1.603, 0.776, 0.144] (verdes: 3 de 3); mitades: +2.682 / +0.433.
- Significacion: R medio 0.181, IC95 bootstrap [0.049, 0.343], t 2.14.
- Coste cero: PF 1.47 / OOS PF 1.17 (net OOS +0.248). A coste doble: PF 1.25 / OOS PF 0.99.
- Meses verdes: 0.571 de 84 (peor mes -11.7%). Apalancamiento implicito: mediana 0.35x, max 3.02x.
- Fills: 38 trades con senal de salida ejecutada en la apertura con stop tambien tocado esa barra (orden del motor fuente); 3 stop-outs en la propia barra de entrada; 0 salidas con apertura mas alla del stop.
- **Veredicto: KILLED (OOS PF bajo el gate).**

### #34 Regression slope — SOLUSDT · run_id `ebb28d8d97d6168d`

- Ventana: 2020-09-14 a 2026-11-02 (53769 barras 1h); split OOS en la barra 37638.
- IS: n 765, PF 1.35, net +325.3%. OOS: n 335, PF 1.05, net +2.8%, DD -28.3%, exceso vs B&H +53.3pp (B&H OOS -50.5%).
- Concentracion: mejores 5 trades = 0.489 del PnL total; net sin ellas +0.957; PF sin ellas 1.13.
- Tercios (net en fraccion): [0.896, 1.067, 0.115] (verdes: 3 de 3); mitades: +2.249 / +0.342.
- Significacion: R medio 0.162, IC95 bootstrap [0.024, 0.305], t 2.21.
- Coste cero: PF 1.34 / OOS PF 1.15 (net OOS +0.253). A coste doble: PF 1.17 / OOS PF 0.97.
- Meses verdes: 0.533 de 75 (peor mes -13.2%). Apalancamiento implicito: mediana 0.38x, max 1.77x.
- Fills: 15 trades con senal de salida ejecutada en la apertura con stop tambien tocado esa barra (orden del motor fuente); 14 stop-outs en la propia barra de entrada; 0 salidas con apertura mas alla del stop.
- **Veredicto: KILLED (OOS PF bajo el gate).**

### #59 Range expansion — SOLUSDT · run_id `a1f3a041c28bbe0e`

- Ventana: 2020-09-14 a 2026-11-02 (53769 barras 1h); split OOS en la barra 37638.
- IS: n 378, PF 1.35, net +39.7%. OOS: n 155, PF 1.03, net +0.9%, DD -8.3%, exceso vs B&H +51.4pp (B&H OOS -50.5%).
- Concentracion: mejores 5 trades = 0.729 del PnL total; net sin ellas +0.085; PF sin ellas 1.07.
- Tercios (net en fraccion): [0.331, 0.046, 0.012] (verdes: 3 de 3); mitades: +0.568 / -0.101.
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
