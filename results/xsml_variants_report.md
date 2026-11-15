# `xsml` — libro cross-sectional con filtro ML: campaña de variantes (V1–V5) y lectura del turnover

- generated: `2026-11-12`
- spec congelado antes de la primera corrida: `results/xsml_pre_registration.md`
- spec de las variantes V2..V5: `results/xsml_variants_pre_registration.md`
- spec de la ambiguedad del turnover: `results/xsml_turnover_pre_registration.md`
- engine: `code/xsml_engine.py` · adapter `xsml` · features `code/xsml_features.py` (motor de indicadores de pybroker, sin su backtester) · modelo `code/xsml_model.py`
- auditoria del engine: `code/_xsml_engine_audit.py` (respuestas conocidas, AMBAS direcciones)
- universo: los ocho perps con 1h **y** funding real; el funding no es opcional en un perp
- costes: 11 bps round trip por pierna, en entrada y salida, en las dos piernas; **funding en los settlements reales**

## Veredicto

**LOS DOCE LIBROS MUEREN.** Ni la lectura mas cara del turnover ni la mas barata salvage ninguno: el profit factor out-of-sample esta por debajo de uno en las doce celdas. El control a coste cero (medido dentro de cada artefacto) es negativo en la mitad de las celdas y positivo en la otra mitad, asi que ninguna de las dos lecturas salva el libro. La conclusion es ROBUSTA a la ambiguedad del spec: no depende de que lectura se tomase.

Lo que mataba al libro base no era el modelo: era el coste del giro. El libro base, sin costes, era marginalmente positivo; con los 11 bps por pierna que el repo cobra, cada rebalance se come el edge entero. Y en el centro del problema esta un hecho comodo que conviene decir de frente: **el forecast correlaciona out-of-sample y el libro pierde igual**.

| libro | lectura | run_id | net % | PF | n | win % | maxDD % | sin costes % | drag pp | residuo |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V1-base | full | `d5cefbaf8e3dcb85` | -20.75 | 0.8969 | 1116 | 50.2 | -29.34 | 1.16 | 21.91 | 0.000000000248 |
| V1-base | keep | `0e8adaec680f1812` | -16.40 | 0.9162 | 1011 | 50 | -33.24 | 3.77 | 20.17 | 0.000000000254 |
| V2-payoff | full | `06037549e0434944` | -33.60 | 0.8381 | 1116 | 50 | -36.89 | -11.69 | 21.90 | 0.000000000191 |
| V2-payoff | keep | `9c79769109b9bb82` | -30.16 | 0.8514 | 1014 | 49.1 | -34.30 | -10.12 | 20.05 | 0.000000000202 |
| V3-72bars | full | `8ffa1a048fd876f5` | -5.62 | 0.9236 | 372 | 51.1 | -15.39 | 0.88 | 6.50 | 0.000000000126 |
| V3-72bars | keep | `ca7c886dea55eba4` | -5.07 | 0.9307 | 371 | 51.2 | -14.84 | 1.42 | 6.48 | 0.000000000124 |
| V4-asymRR | full | `dd55ec2a475e10c4` | -30.66 | 0.8116 | 1116 | 27 | -47.59 | -10.24 | 20.41 | 0.000000000275 |
| V4-asymRR | keep | `8b8d501fffe01ec4` | -26.48 | 0.8337 | 1036 | 25.2 | -60.08 | -7.39 | 19.09 | 0.000000000291 |
| V5-long | full | `93360e729828ae14` | -13.23 | 0.8733 | 558 | 50.4 | -20.86 | -2.49 | 10.74 | 0.000000000052 |
| V5-long | keep | `b42c416f294a1fa1` | -15.18 | 0.8535 | 526 | 49.4 | -34.16 | -4.84 | 10.33 | 0.000000000060 |
| V5-short | full | `8dd9aaac81213d5f` | -7.52 | 0.9213 | 558 | 50 | -19.17 | 3.65 | 11.17 | 0.000000000290 |
| V5-short | keep | `a1f1082585188e08` | -8.05 | 0.9154 | 523 | 49.7 | -18.67 | 2.48 | 10.53 | 0.000000000269 |

El residuo es el invariante contable (el equity final menos el inicial tiene que igualar la suma de los PnL de los trades menos el funding pagado) medido dentro del artefacto: en el orden de las maquinas de coma flotante, es decir, la contabilidad cierra.

## El defecto que obligo a re-correr todo

El engine multiplicaba por `side` una cantidad que **ya era firmada** (`qty = side * notional / fill`). Cada pierna corta se contabilizaba como un espejo-largo y su comision se **acreditaba** en vez de cobrarse. Lo detecto el invariante contable del repo, que el engine no asertaba: el residuo era de mil seiscientos ochenta y nueve dolares con sesenta y cinco centavos, exactamente cuatro comisiones por cada uno de los quinientos siete trades cortos de la corrida original.

Consecuencias, y hay que ser explicito: el artefacto base y su informe publicados antes publicaban cifras de un libro **mal contabilizado**, asi que quedan **retirados**. El engine ahora aserta el invariante DENTRO de cada artefacto y lo publica (`pnl_identity_resid`), de modo que un ledger roto falla ruidosamente en vez de producir un profit factor creible. Y la suite de respuestas conocidas cubre el lado corto en todas las reglas —fill, PnL, stop-first, gap a traves del stop, signo del funding, invariante— porque WAVE_1 ya pago esa factura: tests solo del lado largo y un bug de comision en el corto durante toda la campana.

La correccion no fue una eleccion: un libro con la contabilidad rota no es un libro, y el harness lo dice (invariante asertado dentro del artefacto).

## Gates, celda por celda

### V1-base · lectura `full`

- V1 — el libro base: etiqueta = retorno a 24 barras, demeaned cross-sectional; stop y objetivo a 2x ATR
- lectura del turnover: giro COMPLETO: en cada rebalance se cierran las seis piernas y se abren las seis nuevas (la cartera ES top-3/bottom-3 en cada barra de rebalance y cada stop se congela en la barra de senal de ESE rebalance)
- artefacto: `results/runs/d5cefbaf8e3dcb85` (run_id `d5cefbaf8e3dcb85`, reproduce bit a bit)

| gate | resultado | medido |
|---|---|---|
| G1 at least one hundred closed trades | PASS | n = 1116 |
| G2 profit factor ex-cost above one point two | FAIL | PF = 0.8969 |
| G3 net return above zero | FAIL | net = -20.75 % |
| G4 commission over gross below thirty per cent | FAIL | commission/gross = - % |
| G5 concentration: without the five best trades the result is still positive | FAIL | net without the five best = -26.03 % |
| G6 thirds: green in two of three | FAIL | 1 of three green (-17.98 / -10.95 / 8.70) |
| G11 a win rate of seventy-five per cent must clear the breakeven win rate by five points | PASS | win rate = 50.2 % |
| KILL out-of-sample profit factor below one | FAIL | PF = 0.8969 |

**2 de 8 gates pasan.**

### V1-base · lectura `keep`

- V1 — el libro base: etiqueta = retorno a 24 barras, demeaned cross-sectional; stop y objetivo a 2x ATR
- lectura del turnover: se cierra SOLO lo que SALE del ranking: una pierna que sigue seleccionada conserva su posicion, su stop y su tamano
- artefacto: `results/runs/0e8adaec680f1812` (run_id `0e8adaec680f1812`, reproduce bit a bit)

| gate | resultado | medido |
|---|---|---|
| G1 at least one hundred closed trades | PASS | n = 1011 |
| G2 profit factor ex-cost above one point two | FAIL | PF = 0.9162 |
| G3 net return above zero | FAIL | net = -16.40 % |
| G4 commission over gross below thirty per cent | FAIL | commission/gross = - % |
| G5 concentration: without the five best trades the result is still positive | FAIL | net without the five best = -21.88 % |
| G6 thirds: green in two of three | FAIL | 1 of three green (-18.55 / -9.19 / 13.22) |
| G11 a win rate of seventy-five per cent must clear the breakeven win rate by five points | PASS | win rate = 50 % |
| KILL out-of-sample profit factor below one | FAIL | PF = 0.9162 |

**2 de 8 gates pasan.**

### V2-payoff · lectura `full`

- V2 — etiqueta = el payoff que el libro REALIZA (stop 2x ATR, objetivo 2x ATR), en unidades R
- lectura del turnover: giro COMPLETO: en cada rebalance se cierran las seis piernas y se abren las seis nuevas (la cartera ES top-3/bottom-3 en cada barra de rebalance y cada stop se congela en la barra de senal de ESE rebalance)
- artefacto: `results/runs/06037549e0434944` (run_id `06037549e0434944`, reproduce bit a bit)

| gate | resultado | medido |
|---|---|---|
| G1 at least one hundred closed trades | PASS | n = 1116 |
| G2 profit factor ex-cost above one point two | FAIL | PF = 0.8381 |
| G3 net return above zero | FAIL | net = -33.60 % |
| G4 commission over gross below thirty per cent | FAIL | commission/gross = - % |
| G5 concentration: without the five best trades the result is still positive | FAIL | net without the five best = -38.81 % |
| G6 thirds: green in two of three | FAIL | 0 of three green (-18.87 / -12.57 / -6.18) |
| G11 a win rate of seventy-five per cent must clear the breakeven win rate by five points | PASS | win rate = 50 % |
| KILL out-of-sample profit factor below one | FAIL | PF = 0.8381 |

**2 de 8 gates pasan.**

### V2-payoff · lectura `keep`

- V2 — etiqueta = el payoff que el libro REALIZA (stop 2x ATR, objetivo 2x ATR), en unidades R
- lectura del turnover: se cierra SOLO lo que SALE del ranking: una pierna que sigue seleccionada conserva su posicion, su stop y su tamano
- artefacto: `results/runs/9c79769109b9bb82` (run_id `9c79769109b9bb82`, reproduce bit a bit)

| gate | resultado | medido |
|---|---|---|
| G1 at least one hundred closed trades | PASS | n = 1014 |
| G2 profit factor ex-cost above one point two | FAIL | PF = 0.8514 |
| G3 net return above zero | FAIL | net = -30.16 % |
| G4 commission over gross below thirty per cent | FAIL | commission/gross = - % |
| G5 concentration: without the five best trades the result is still positive | FAIL | net without the five best = -35.62 % |
| G6 thirds: green in two of three | FAIL | 0 of three green (-17.35 / -12.59 / -3.13) |
| G11 a win rate of seventy-five per cent must clear the breakeven win rate by five points | PASS | win rate = 49.1 % |
| KILL out-of-sample profit factor below one | FAIL | PF = 0.8514 |

**2 de 8 gates pasan.**

### V3-72bars · lectura `full`

- V3 — etiqueta a 72 barras y rebalance cada 72 barras (tres veces menos giros)
- lectura del turnover: giro COMPLETO: en cada rebalance se cierran las seis piernas y se abren las seis nuevas (la cartera ES top-3/bottom-3 en cada barra de rebalance y cada stop se congela en la barra de senal de ESE rebalance)
- artefacto: `results/runs/8ffa1a048fd876f5` (run_id `8ffa1a048fd876f5`, reproduce bit a bit)

| gate | resultado | medido |
|---|---|---|
| G1 at least one hundred closed trades | PASS | n = 372 |
| G2 profit factor ex-cost above one point two | FAIL | PF = 0.9236 |
| G3 net return above zero | FAIL | net = -5.62 % |
| G4 commission over gross below thirty per cent | FAIL | commission/gross = - % |
| G5 concentration: without the five best trades the result is still positive | FAIL | net without the five best = -10.91 % |
| G6 thirds: green in two of three | FAIL | 1 of three green (-4.49 / -7.34 / 6.86) |
| G11 a win rate of seventy-five per cent must clear the breakeven win rate by five points | PASS | win rate = 51.1 % |
| KILL out-of-sample profit factor below one | FAIL | PF = 0.9236 |

**2 de 8 gates pasan.**

### V3-72bars · lectura `keep`

- V3 — etiqueta a 72 barras y rebalance cada 72 barras (tres veces menos giros)
- lectura del turnover: se cierra SOLO lo que SALE del ranking: una pierna que sigue seleccionada conserva su posicion, su stop y su tamano
- artefacto: `results/runs/ca7c886dea55eba4` (run_id `ca7c886dea55eba4`, reproduce bit a bit)

| gate | resultado | medido |
|---|---|---|
| G1 at least one hundred closed trades | PASS | n = 371 |
| G2 profit factor ex-cost above one point two | FAIL | PF = 0.9307 |
| G3 net return above zero | FAIL | net = -5.07 % |
| G4 commission over gross below thirty per cent | FAIL | commission/gross = - % |
| G5 concentration: without the five best trades the result is still positive | FAIL | net without the five best = -10.36 % |
| G6 thirds: green in two of three | FAIL | 1 of three green (-3.94 / -7.29 / 6.82) |
| G11 a win rate of seventy-five per cent must clear the breakeven win rate by five points | PASS | win rate = 51.2 % |
| KILL out-of-sample profit factor below one | FAIL | PF = 0.9307 |

**2 de 8 gates pasan.**

### V4-asymRR · lectura `full`

- V4 — reward:risk asimetrico: stop 1x ATR, objetivo 3x ATR
- lectura del turnover: giro COMPLETO: en cada rebalance se cierran las seis piernas y se abren las seis nuevas (la cartera ES top-3/bottom-3 en cada barra de rebalance y cada stop se congela en la barra de senal de ESE rebalance)
- artefacto: `results/runs/dd55ec2a475e10c4` (run_id `dd55ec2a475e10c4`, reproduce bit a bit)

| gate | resultado | medido |
|---|---|---|
| G1 at least one hundred closed trades | PASS | n = 1116 |
| G2 profit factor ex-cost above one point two | FAIL | PF = 0.8116 |
| G3 net return above zero | FAIL | net = -30.66 % |
| G4 commission over gross below thirty per cent | FAIL | commission/gross = - % |
| G5 concentration: without the five best trades the result is still positive | FAIL | net without the five best = -37.48 % |
| G6 thirds: green in two of three | FAIL | 0 of three green (-8.60 / -10.88 / -14.61) |
| G11 a win rate of seventy-five per cent must clear the breakeven win rate by five points | PASS | win rate = 27 % |
| KILL out-of-sample profit factor below one | FAIL | PF = 0.8116 |

**2 de 8 gates pasan.**

### V4-asymRR · lectura `keep`

- V4 — reward:risk asimetrico: stop 1x ATR, objetivo 3x ATR
- lectura del turnover: se cierra SOLO lo que SALE del ranking: una pierna que sigue seleccionada conserva su posicion, su stop y su tamano
- artefacto: `results/runs/8b8d501fffe01ec4` (run_id `8b8d501fffe01ec4`, reproduce bit a bit)

| gate | resultado | medido |
|---|---|---|
| G1 at least one hundred closed trades | PASS | n = 1036 |
| G2 profit factor ex-cost above one point two | FAIL | PF = 0.8337 |
| G3 net return above zero | FAIL | net = -26.48 % |
| G4 commission over gross below thirty per cent | FAIL | commission/gross = - % |
| G5 concentration: without the five best trades the result is still positive | FAIL | net without the five best = -33.62 % |
| G6 thirds: green in two of three | FAIL | 0 of three green (-8.91 / -7.34 / -12.63) |
| G11 a win rate of seventy-five per cent must clear the breakeven win rate by five points | PASS | win rate = 25.2 % |
| KILL out-of-sample profit factor below one | FAIL | PF = 0.8337 |

**2 de 8 gates pasan.**

### V5-long · lectura `full`

- V5-long — solo la pierna larga (control de falsificacion de H0)
- lectura del turnover: giro COMPLETO: en cada rebalance se cierran las seis piernas y se abren las seis nuevas (la cartera ES top-3/bottom-3 en cada barra de rebalance y cada stop se congela en la barra de senal de ESE rebalance)
- artefacto: `results/runs/93360e729828ae14` (run_id `93360e729828ae14`, reproduce bit a bit)

| gate | resultado | medido |
|---|---|---|
| G1 at least one hundred closed trades | PASS | n = 558 |
| G2 profit factor ex-cost above one point two | FAIL | PF = 0.8733 |
| G3 net return above zero | FAIL | net = -13.23 % |
| G4 commission over gross below thirty per cent | FAIL | commission/gross = - % |
| G5 concentration: without the five best trades the result is still positive | FAIL | net without the five best = -18 % |
| G6 thirds: green in two of three | FAIL | 1 of three green (-13.17 / -2.26 / 1.92) |
| G11 a win rate of seventy-five per cent must clear the breakeven win rate by five points | PASS | win rate = 50.4 % |
| KILL out-of-sample profit factor below one | FAIL | PF = 0.8733 |

**2 de 8 gates pasan.**

### V5-long · lectura `keep`

- V5-long — solo la pierna larga (control de falsificacion de H0)
- lectura del turnover: se cierra SOLO lo que SALE del ranking: una pierna que sigue seleccionada conserva su posicion, su stop y su tamano
- artefacto: `results/runs/b42c416f294a1fa1` (run_id `b42c416f294a1fa1`, reproduce bit a bit)

| gate | resultado | medido |
|---|---|---|
| G1 at least one hundred closed trades | PASS | n = 526 |
| G2 profit factor ex-cost above one point two | FAIL | PF = 0.8535 |
| G3 net return above zero | FAIL | net = -15.18 % |
| G4 commission over gross below thirty per cent | FAIL | commission/gross = - % |
| G5 concentration: without the five best trades the result is still positive | FAIL | net without the five best = -19.94 % |
| G6 thirds: green in two of three | FAIL | 1 of three green (-13.77 / -2.25 / 0.31) |
| G11 a win rate of seventy-five per cent must clear the breakeven win rate by five points | PASS | win rate = 49.4 % |
| KILL out-of-sample profit factor below one | FAIL | PF = 0.8535 |

**2 de 8 gates pasan.**

### V5-short · lectura `full`

- V5-short — solo la pierna corta (control de falsificacion de H0)
- lectura del turnover: giro COMPLETO: en cada rebalance se cierran las seis piernas y se abren las seis nuevas (la cartera ES top-3/bottom-3 en cada barra de rebalance y cada stop se congela en la barra de senal de ESE rebalance)
- artefacto: `results/runs/8dd9aaac81213d5f` (run_id `8dd9aaac81213d5f`, reproduce bit a bit)

| gate | resultado | medido |
|---|---|---|
| G1 at least one hundred closed trades | PASS | n = 558 |
| G2 profit factor ex-cost above one point two | FAIL | PF = 0.9213 |
| G3 net return above zero | FAIL | net = -7.52 % |
| G4 commission over gross below thirty per cent | FAIL | commission/gross = - % |
| G5 concentration: without the five best trades the result is still positive | FAIL | net without the five best = -12.65 % |
| G6 thirds: green in two of three | FAIL | 1 of three green (-4.81 / -7.37 / 5.37) |
| G11 a win rate of seventy-five per cent must clear the breakeven win rate by five points | PASS | win rate = 50 % |
| KILL out-of-sample profit factor below one | FAIL | PF = 0.9213 |

**2 de 8 gates pasan.**

### V5-short · lectura `keep`

- V5-short — solo la pierna corta (control de falsificacion de H0)
- lectura del turnover: se cierra SOLO lo que SALE del ranking: una pierna que sigue seleccionada conserva su posicion, su stop y su tamano
- artefacto: `results/runs/a1f1082585188e08` (run_id `a1f1082585188e08`, reproduce bit a bit)

| gate | resultado | medido |
|---|---|---|
| G1 at least one hundred closed trades | PASS | n = 523 |
| G2 profit factor ex-cost above one point two | FAIL | PF = 0.9154 |
| G3 net return above zero | FAIL | net = -8.05 % |
| G4 commission over gross below thirty per cent | FAIL | commission/gross = - % |
| G5 concentration: without the five best trades the result is still positive | FAIL | net without the five best = -13.19 % |
| G6 thirds: green in two of three | FAIL | 1 of three green (-5.58 / -6.91 / 5.08) |
| G11 a win rate of seventy-five per cent must clear the breakeven win rate by five points | PASS | win rate = 49.7 % |
| KILL out-of-sample profit factor below one | FAIL | PF = 0.9154 |

**2 de 8 gates pasan.**

## Que hizo cada libro

| libro | lectura | fees USDT | funding USDT | rebalances | fechas sin operar | exits stop/target/rebalance | corr pred-etiqueta |
|---|---|---:|---:|---:|---:|---|---:|
| V1-base | full | 1859.74 | -13.78 | 186 | 4 | 502 / 484 / 130 | 0.1484 |
| V1-base | keep | 1684.67 | -13.71 | 186 | 4 | 488 / 486 / 36 | 0.1484 |
| V2-payoff | full | 1859.38 | -12.95 | 186 | 4 | 504 / 483 / 129 | 0.2006 |
| V2-payoff | keep | 1689.32 | -13.09 | 186 | 4 | 498 / 474 / 42 | 0.2006 |
| V3-72bars | full | 619.05 | -8.26 | 62 | 2 | 182 / 187 / 2 | 0.0286 |
| V3-72bars | keep | 617.39 | -8.53 | 62 | 2 | 181 / 188 / 1 | 0.0286 |
| V4-asymRR | full | 1859.13 | -5.65 | 186 | 4 | 794 / 224 / 97 | 0.1619 |
| V4-asymRR | keep | 1725.60 | -5.77 | 186 | 4 | 766 / 237 / 31 | 0.1619 |
| V5-long | full | 929.81 | 17.79 | 186 | 4 | 253 / 237 / 68 | 0.1484 |
| V5-long | keep | 876.35 | 17.90 | 186 | 4 | 250 / 231 / 44 | 0.1484 |
| V5-short | full | 929.93 | -31.57 | 186 | 4 | 249 / 247 / 62 | 0.1484 |
| V5-short | keep | 871.65 | -32.16 | 186 | 4 | 248 / 245 / 30 | 0.1484 |

El funding es **neto**: un valor negativo significa que el libro lo recibio. Las dos piernas pagan el funding con signo contrario, asi que un libro neutral no lo esquiva.

## Lo que dice cada libro (por su propia lectura)

**V1-base / full** — V1 — el libro base: etiqueta = retorno a 24 barras, demeaned cross-sectional; stop y objetivo a 2x ATR

- retorno neto -20.75 %, profit factor 0.8969, 1116 trades cerrados, win rate 50.2 %, max drawdown -29.34 %
- **sin costes** 1.16 % (control medido dentro del artefacto), drag de costes 21.91 pp
- tercios: -17.98 % / -10.95 % / 8.70 % (1 de tres verdes)
- concentracion: net sin los cinco mejores trades -26.03 %
- forecast correlacionado con la etiqueta en la ventana operada: 0.1484 (sobre 35649 filas)

**V1-base / keep** — V1 — el libro base: etiqueta = retorno a 24 barras, demeaned cross-sectional; stop y objetivo a 2x ATR

- retorno neto -16.40 %, profit factor 0.9162, 1011 trades cerrados, win rate 50 %, max drawdown -33.24 %
- **sin costes** 3.77 % (control medido dentro del artefacto), drag de costes 20.17 pp
- tercios: -18.55 % / -9.19 % / 13.22 % (1 de tres verdes)
- concentracion: net sin los cinco mejores trades -21.88 %
- forecast correlacionado con la etiqueta en la ventana operada: 0.1484 (sobre 35649 filas)

**V2-payoff / full** — V2 — etiqueta = el payoff que el libro REALIZA (stop 2x ATR, objetivo 2x ATR), en unidades R

- retorno neto -33.60 %, profit factor 0.8381, 1116 trades cerrados, win rate 50 %, max drawdown -36.89 %
- **sin costes** -11.69 % (control medido dentro del artefacto), drag de costes 21.90 pp
- tercios: -18.87 % / -12.57 % / -6.18 % (0 de tres verdes)
- concentracion: net sin los cinco mejores trades -38.81 %
- forecast correlacionado con la etiqueta en la ventana operada: 0.2006 (sobre 35833 filas)

**V2-payoff / keep** — V2 — etiqueta = el payoff que el libro REALIZA (stop 2x ATR, objetivo 2x ATR), en unidades R

- retorno neto -30.16 %, profit factor 0.8514, 1014 trades cerrados, win rate 49.1 %, max drawdown -34.30 %
- **sin costes** -10.12 % (control medido dentro del artefacto), drag de costes 20.05 pp
- tercios: -17.35 % / -12.59 % / -3.13 % (0 de tres verdes)
- concentracion: net sin los cinco mejores trades -35.62 %
- forecast correlacionado con la etiqueta en la ventana operada: 0.2006 (sobre 35833 filas)

**V3-72bars / full** — V3 — etiqueta a 72 barras y rebalance cada 72 barras (tres veces menos giros)

- retorno neto -5.62 %, profit factor 0.9236, 372 trades cerrados, win rate 51.1 %, max drawdown -15.39 %
- **sin costes** 0.88 % (control medido dentro del artefacto), drag de costes 6.50 pp
- tercios: -4.49 % / -7.34 % / 6.86 % (1 de tres verdes)
- concentracion: net sin los cinco mejores trades -10.91 %
- forecast correlacionado con la etiqueta en la ventana operada: 0.0286 (sobre 35265 filas)

**V3-72bars / keep** — V3 — etiqueta a 72 barras y rebalance cada 72 barras (tres veces menos giros)

- retorno neto -5.07 %, profit factor 0.9307, 371 trades cerrados, win rate 51.2 %, max drawdown -14.84 %
- **sin costes** 1.42 % (control medido dentro del artefacto), drag de costes 6.48 pp
- tercios: -3.94 % / -7.29 % / 6.82 % (1 de tres verdes)
- concentracion: net sin los cinco mejores trades -10.36 %
- forecast correlacionado con la etiqueta en la ventana operada: 0.0286 (sobre 35265 filas)

**V4-asymRR / full** — V4 — reward:risk asimetrico: stop 1x ATR, objetivo 3x ATR

- retorno neto -30.66 %, profit factor 0.8116, 1116 trades cerrados, win rate 27 %, max drawdown -47.59 %
- **sin costes** -10.24 % (control medido dentro del artefacto), drag de costes 20.41 pp
- tercios: -8.60 % / -10.88 % / -14.61 % (0 de tres verdes)
- concentracion: net sin los cinco mejores trades -37.48 %
- forecast correlacionado con la etiqueta en la ventana operada: 0.1619 (sobre 35833 filas)

**V4-asymRR / keep** — V4 — reward:risk asimetrico: stop 1x ATR, objetivo 3x ATR

- retorno neto -26.48 %, profit factor 0.8337, 1036 trades cerrados, win rate 25.2 %, max drawdown -60.08 %
- **sin costes** -7.39 % (control medido dentro del artefacto), drag de costes 19.09 pp
- tercios: -8.91 % / -7.34 % / -12.63 % (0 de tres verdes)
- concentracion: net sin los cinco mejores trades -33.62 %
- forecast correlacionado con la etiqueta en la ventana operada: 0.1619 (sobre 35833 filas)

**V5-long / full** — V5-long — solo la pierna larga (control de falsificacion de H0)

- retorno neto -13.23 %, profit factor 0.8733, 558 trades cerrados, win rate 50.4 %, max drawdown -20.86 %
- **sin costes** -2.49 % (control medido dentro del artefacto), drag de costes 10.74 pp
- tercios: -13.17 % / -2.26 % / 1.92 % (1 de tres verdes)
- concentracion: net sin los cinco mejores trades -18 %
- forecast correlacionado con la etiqueta en la ventana operada: 0.1484 (sobre 35649 filas)

**V5-long / keep** — V5-long — solo la pierna larga (control de falsificacion de H0)

- retorno neto -15.18 %, profit factor 0.8535, 526 trades cerrados, win rate 49.4 %, max drawdown -34.16 %
- **sin costes** -4.84 % (control medido dentro del artefacto), drag de costes 10.33 pp
- tercios: -13.77 % / -2.25 % / 0.31 % (1 de tres verdes)
- concentracion: net sin los cinco mejores trades -19.94 %
- forecast correlacionado con la etiqueta en la ventana operada: 0.1484 (sobre 35649 filas)

**V5-short / full** — V5-short — solo la pierna corta (control de falsificacion de H0)

- retorno neto -7.52 %, profit factor 0.9213, 558 trades cerrados, win rate 50 %, max drawdown -19.17 %
- **sin costes** 3.65 % (control medido dentro del artefacto), drag de costes 11.17 pp
- tercios: -4.81 % / -7.37 % / 5.37 % (1 de tres verdes)
- concentracion: net sin los cinco mejores trades -12.65 %
- forecast correlacionado con la etiqueta en la ventana operada: 0.1484 (sobre 35649 filas)

**V5-short / keep** — V5-short — solo la pierna corta (control de falsificacion de H0)

- retorno neto -8.05 %, profit factor 0.9154, 523 trades cerrados, win rate 49.7 %, max drawdown -18.67 %
- **sin costes** 2.48 % (control medido dentro del artefacto), drag de costes 10.53 pp
- tercios: -5.58 % / -6.91 % / 5.08 % (1 de tres verdes)
- concentracion: net sin los cinco mejores trades -13.19 %
- forecast correlacionado con la etiqueta en la ventana operada: 0.1484 (sobre 35649 filas)

## El libro base, symbolo por symbolo (lectura `full`)

| symbol | trades | PF | PnL USDT |
|---|---:|---:|---:|
| ARBUSDT | 150 | 1.0886 | 320.21 |
| BTCUSDT | 138 | 0.6660 | -448.14 |
| ETHUSDT | 125 | 0.8153 | -276.53 |
| HYPEUSDT | 148 | 0.8991 | -322.39 |
| JUPUSDT | 149 | 0.8881 | -426.02 |
| SOLUSDT | 133 | 0.8729 | -249.27 |
| SUIUSDT | 145 | 0.7917 | -661.79 |
| XRPUSDT | 128 | 0.9853 | -24.61 |

Y en la lectura `keep`:

| symbol | trades | PF | PnL USDT |
|---|---:|---:|---:|
| ARBUSDT | 135 | 1.1149 | 396.21 |
| BTCUSDT | 126 | 0.5780 | -605.78 |
| ETHUSDT | 112 | 0.8769 | -175.58 |
| HYPEUSDT | 131 | 0.9875 | -36.74 |
| JUPUSDT | 138 | 0.9062 | -351.81 |
| SOLUSDT | 124 | 0.8830 | -224.96 |
| SUIUSDT | 129 | 0.8018 | -619.85 |
| XRPUSDT | 116 | 0.9788 | -35.41 |

## Como leer esto

- **El forecast correlaciona y el libro pierde igual.** La correlacion out-of-sample con la etiqueta es real (medida dentro de cada artefacto) y aun asi el libro pierde: un rank de esa magnitud no cubre el coste de giro de un libro cross-sectional que rota cada dia.
- **El libro base sin costes era marginalmente positivo.** Eso es lo mas incomodo del resultado: el problema no es que la senal sea nula, es que el edge por operacion es mas pequeno que el coste de tener la posicion. La lectura `keep` reduce el giro y con ella el drag, pero no basta.
- **V4 (reward:risk asimetrico) tiene el peor profit factor de las doce celdas.** Con objetivo tres veces el ATR y stop una vez, la tasa de acierto se desploma a menos de un tercio y el libro pierde mas: arreglar el balance reward:risk no arregla un edge pequeno, lo amplifica en la direccion equivocada. El que pierde mas en terminos absolutos es V2, la etiqueta alineada con el payoff.
- **V2 (etiqueta alineada con el payoff) pierde mas que la base.** Alentar al modelo a predecir el payoff realizado no ayuda: la correlacion sube y el resultado baja. La etiqueta no era el cuello de botella.
- **V3 (menos giros) es el menos malo**, como cabe esperar si el coste es el problema, pero sigue por debajo del equilibrio.
- **V5 falsifica H0 en las dos lecturas:** el lado corto pierde y el lado largo tambien, asi que no es que el libro neutral este midiendo el lado equivocado; es que el rank no tiene contenido operable.
- Cada libro se juzga por SUS artefactos (REGLA 1). Ningun otro libro de este repo es evidencia sobre estos.

## Limites declarados

- La ventana es corta: el estudio empieza cuando el sexto nombre tiene 1h y funding, y el out-of-sample son unos meses.
- El modelo se ajusto UNA vez por variante, con hiperparametros fijos declarados; no hay grid, ni Optuna, ni seleccion por score. No hay conteo de trials que descontar, pero tampoco hay ensemble ni comprobacion de robustez entre subconjuntos de features (hubieran sido trials nuevos, y el spec los prohibe).
- El tamano de las piernas se congela en el equity inicial, no se recompone con el equity corriente; el libro no escala su nocional al crecer o encogerse.
- Sin modelo de margen ni de liquidacion: el gross exposure no puede superar el tope declarado, pero no hay comprobacion de collateral.
- Esto es una mediccion sobre las klines del repo. No se enviaron ordenes.

## Reproduccion

```
python code/vrun.py run --strategy xsml --tf 1h --symbol XSML8 --params '{"split": "OOS", "turnover": "full"}'
python code/vrun.py verify d5cefbaf8e3dcb85
python code/_xsml_engine_audit.py
```

Las features y el modelo son upstream del artefacto y se reproducen con:

```
& "$HOME\.venvs\pybroker\Scripts\python.exe" code/xsml_features.py
& "$HOME\.venvs\pybroker\Scripts\python.exe" code/_xsml_feature_audit.py
& "$HOME\.venvs\pybroker\Scripts\python.exe" code/xsml_model.py --variant v1
```

