# MAP.md — mapa de `code/` (documento, no movimiento)

`code/` no se reorganiza físicamente: los engines están hash-locked
(`_engine_lock.json`) y el `run_id` de cada artefacto depende de los bytes del
engine en su ruta. Este mapa es la capa documental: qué es cada cosa, qué no
se toca, y quién la verifica. Generado 2026-10-31 (203 .py + subdirectorios).

## 0. El harness — lo único que todos usan

| Archivo | Qué es |
|---|---|
| `vrun.py` | EL harness: registro de adaptadores, run_id = sha256(engine+params+data), run/render/verify/matrix/guard/stats/stale/pverify/nullgate. Es fichero caliente (sesiones paralelas): re-leer antes de editar. |
| `_engine_lock.json` | sha256 de los engines que NO deben cambiar + registro de engines sustituidos (orphaned vs current). |
| `gate2.py` / `_gates_v2.py` | capa estadística G1-G10 sobre los gates v1; calibrada con nulos. |

## 1. Engines HASH-LOCKED — no editar jamás (invalidan artefactos)

`cbpack_engine.py`, `cvrmd_backtest.py`, `botstrat_backtest.py` (hardcodea 1h —
guard en el adaptador `run_botstrat`), `mp20_report_ports.py`, `grid_audit.py`,
`xrp_neutral_engine.py` (KILLED por resolución 1m el 2026-10-31; intacto como
registro histórico). El costo repo (5+0.5 bps) se inyecta por parámetro, nunca
editando el engine.

## 2. Engines de familias (uno por familia del registro)

| Familia (`results/registry/`) | Archivos |
|---|---|
| pack_S01-S10_taker_flow | `cbpack_funding_engine.py` (generado por `_build_funding_engine.py` — patches literales), `eqpack_engine` vía adaptador |
| llm_pack (48/46/42/48/100 prompts) | `pack50_core.py` + `pack50{,b,c,d}_engine.py` + `pack50{,b,c,d}_strats.py` + `pack100_engine.py` + `pack100_strats{,2,3}.py` |
| risk_sized_book (QS) | `qs_engine.py`, `qs_run.py`, `qs_strats.py`, `qs_flow_strats.py` |
| deepseek_ds1-ds5 / ds6-ds10 | `deepseek_pack.py` + `dspack_engine.py`; `deepseek_pack2.py` + `dspack2_engine.py` |
| trend_ema_adx | `emaadx_engine.py` |
| trend_hma_ao_adx | `fingrad_engine.py` (+ `fingrad_hma_ao_adx_strategy.pine` fuente), `hmaaoadx` pack |
| smc_composite | `smqe_engine.py` (+ `smqe_v2_strategy.pine`) |
| vwap_cvd_divergence | `cvrmd_backtest.py` (locked) |
| pivot_box_breakout | `botstrat_backtest.py` (locked) |
| qwen_cards | `q10_engine.py`, `q10_diag.py` |
| portfolio_momentum | `mpv3_engine.py` + `claude_mp20_v3/strategies.py` |
| grid_neutral (KILLED) | `xrp_neutral_engine.py` (locked) |
| rsi_mean_reversion | `rsi_mr_engine.py` |
| cbot suite | `cbot/` (10 estrategias, own dir) |
| equities | `fetch_alpaca_equities.py` + datos Alpaca en `data/` |

## 3. Variantes de sonda (2026-10-31, auditoría de fills) — NO son engines del harness

`xrp_neutral_engine_stress.py`, `xrp_neutral_engine_1m.py`,
`xrp_neutral_engine_count.py`, `xrp_neutral_engine_cushion.py` — construidos
por reemplazos literales desde el locked por `_xrp_fill_stress.py` y
`_xrp_1m_resolution.py`. Sus salidas: `code/_xrp_fill_stress_out.json`,
`_xrp_fill_stress_decomp.json`, `_xrp_1m_resolution_out.json`.

Adapter de sonda en el harness (2026-11-01): `bookreplay_engine.py` + adapter
`bookreplay` en `vrun.py` — replay de resolución de fills: la MISMA rejilla
maker resuelta sobre aggTrades REALES (archivo oficial, `data/aggtrades/`,
manifest sha256) y sobre la convención de barra 15m. Artefactos citables:
`ce46399b5b500a43` (0.30%) y `ecf93a9ee8475a93` (0.05%); informe
`results/bookreplay_report.md` (guard OK strict). Los 4 artefactos de versiones
intermedias del engine (014c81eae30dbcd3, 125f32903cff2de4, 740ea9ead28f2309,
902adfb8fba3e730) quedaron huérfanos por drift del engine — append-only, no
citables. Excluido del universo de estrategias (EXCLUDE en strategy_registry).

## 3b. Contabilidad 1m del libro neutral (2026-11-04) — engines vivos del VPS

El engine 1m del libro desplegado NO es `xrp_neutral_engine_1m.py` (sonda de
un solo par, KILLED). Es un engine DUAL generado por script:

| Archivo | Qué es |
|---|---|
| `xrp_neutral_engine_paper.py` | copia BYTE-IDÉNTICA del engine que corre el VPS (sha256 `834f3de9…`, desplegado como `~/neutral-paper/<PAR>/xrp_neutral_engine.py`). El builder la exige: si el sha no coincide, se REHÚSA a generar. |
| `_neutral_1m_build.py` | constructor: reemplaza el bloque same-bar por el pase por minuto SOLO cuando el tape de la barra está completo (≥ quince minutos distintos); cada ancla debe matchear exactamente una vez o aborta. |
| `xrp_neutral_engine_paper_1m.py` | el engine DUAL, GENERADO (sha256 `9108aa8d…`). No editar a mano: reconstruir. |
| `_neutral_1m_audit.py` → `_neutral_1m_audit.json` | auditoría de doce checks: identidad bit-a-bit sin tape (toda la historia), tape tardío deja el prefijo intacto, cinco casos sintéticos de ordenado, y reproducción EXACTA del kill publicado (`code/_xrp_1m_resolution_out.json`). |
| `neutral_paper_1m.py` | runner en vivo: escribe `_1m`-sufijados status/events/artifact, comparte el `xrp_paper_bot_day0.json`, y fija `day0_replay_matches` re-corriendo el path 15m puro sobre el prefijo. |
| `paper_daily_summary_1m.py` | resumen diario (00:20) con columnas 1m y deltas vs 15m. |

Adaptador nuevo en `vrun.py`: `xrpneutral1m` (misma matemática, tape 1m como
INPUT; artefactos `c7f1063c88f3268f` 15m baseline, `18d686932bf06f78` 1m —
los dos `verify` OK). `xrpneutral` NO cambió: mismos run_ids.

## 3c. Pack WAVE_1 scalp (2026-11-11) — port desde `Downloads/scalp_wave1_v1.1.0`

Paquete Python de 4 indicadores kline-only (IND-04 VWAP de sesión ±σ, IND-05
gate de régimen, IND-06 liquidity sweep, IND-07a squeeze/burst) para perps
Binance USD-M 1m–15m. El pack original es de otro autor y vive en
`Downloads/`, que NO es durable: la lógica de señal está COPIADA aquí.

| Archivo | Qué es |
|---|---|
| `scalp_wave_engine.py` | el engine del repo: `compute_all` (las 39 columnas de indicadores, copiadas del pack), `generate_signals` (eventos con gate de costes), `execute` (next-open, stop-first, gap-through al open, una posición a la vez, 1% de riesgo) y `run_symbol`. Sus 7 known-answers cubren largo Y corto. |
| `_scalp_wave_parity.py` → `_scalp_wave_parity.json` | PARITY contra el pack ORIGINAL (importado como segundo engine): 39 columnas de indicadores a rtol 1e-9 y conjunto de eventos IDÉNTICO, en datos reales de 5m y 15m. |
| `_scalp_wave_report.py` | genera `results/scalpwave_report_2026-11-11.md` LEYENDO los artefactos (ningún número escrito a mano). |

Adapter `scalpwave` en `vrun.py`. Sus directorios de entrada NO son los de
`TF_DIR`: 5m apunta a `data/binance_klines_5m/` (la historia real), no a
`data/binance_klines/` (un stub de 30 días).

**Dos defectos encontrados por la auditoría, ambos corregidos** (habrían dado
números plausibles pero falsos): (1) la salida del corto se cobraba con
`(1-fee)` en vez de `(1+fee)`, subestimando la fee de recompra de cada corto;
(2) el PnL por trade no incluía fees, así que el PF era pre-coste mientras la
curva de equity era neta — una familia podía mostrar PF > 1 y aun así perder
dinero. El invariante `eq[-1]-INIT == sum(pnl)` ahora se aserta DENTRO de cada
artefacto.

## 3d. Transferencia al S&P 500 (2026-11-11) — el mismo engine sobre otra serie

El store de equities es `data/alpaca_1d` (SPY = ETF del S&P 500, QQQ = Nasdaq
100; 2.722 sesiones diarias reales de Alpaca). **`SPXUSDT` NO es el índice**
(medido: corr con SPY 0.31, corr SPY-QQQ 0.95): es un perp cripto.

| Archivo | Qué es |
|---|---|
| `code/vrun.py` (`make_artifact`) | override `data_dir`: reapunta las entradas a `<data_dir>/<SÍMBOLO>_<TF>.csv` y descarta lo que no exista ahí. El directorio entra en el `core` (el `run_id` no colisiona con el cripto) y se elimina de los params que ve el runner. |
| `_equities_sweep.py` → `_equities_sweep.json` | el barrido: cada adapter símbolo×tf × SPY/QQQ × regímenes de coste (repo y cero), con el vocabulario de coste de CADA engine (nunca inventado). Registra los rechazos con su razón. |
| `_equities_transfer_report.py` | genera `results/equities_transfer_2026-11-11.md` leyendo los artefactos (ningún número escrito a mano). |
| `_equities_rank.py` | añade las celdas de equity al universo (`_top100_rank.json`), con el activo y el régimen de coste en la etiqueta, y limpia las filas de una pasada anterior. |

Resultado: 60 celdas intentadas, 20 con artefacto, 40 rechazadas por los
guards de cada engine. **Ningún edge transfiere al S&P 500.**

## 3e. Libro cross-sectional con filtro ML, `xsml` (2026-11-11)

| file | qué es |
|---|---|
| `code/xsml_engine.py` | el libro, con la ejecución DEL REPO (next open, stop-first, gap al open, 11 bps RT por pierna, funding en los settlements reales). **VERSION 2 del engine usa UNA sola cantidad firmada en todo el ledger**: `cash -= qty*fill + fee` al entrar, `cash += qty*fill − fee` al salir, `equity = cash + qty*mark`, `funding −= qty*mark*rate` (un largo PAGA un rate positivo, un corto lo RECIBE). La version 1 multiplicaba por `side` una cantidad que YA era firmada, lo que invertia cada pierna corta y ACREDITABA su comisión; lo detectó el invariante contable del repo (residuo 1689.65 USDT = cuatro comisiones por cada uno de los 507 trades cortos). El invariante ahora se **aserta dentro de cada artefacto** y el residuo se publica (`pnl_identity_resid`). |
| `code/_xsml_engine_audit.py` | suite de respuestas conocidas del LEDGER, **en ambas direcciones** (fill, PnL, stop-first, gap, signo del funding, invariante, las dos lecturas del turnover, stop/objetivo asimétricos). 32/32 PASS. El lado corto está cubierto en todas las reglas porque WAVE_1 ya pagó un bug de comisión en el corto. |
| `code/xsml_features.py` | las diez features DECLARADAS, con el motor de indicadores de pybroker (sin su backtester). |
| `code/_xsml_feature_audit.py` | auditoría de features, con el test **bump-last-bar** de look-ahead que este repo no tenía. 5/5 PASS. |
| `code/xsml_model.py` | un ajuste por variante sobre DEV, hiperparámetros fijos, sin grid/Optuna/selección por score. `--variant v1\|v2\|v3\|v4`. |
| `code/_xsml_report.py` | el informe del libro base, construido desde el artefacto. |
| `code/_xsml_variants_report.py` | el informe de variantes (cinco libros × dos lecturas del turnover), construido desde los artefactos. |
| `results/xsml_pre_registration.md` | el spec congelado (escrito antes de la primera corrida de mercado). |
| `results/xsml_variants_pre_registration.md` | el spec congelado de V2..V5. |
| `results/xsml_turnover_pre_registration.md` | el spec congelado de la ambigüedad del turnover (las dos lecturas, declaradas y reportadas). |
| `results/_xsml_variants_cells.json` | los run_id de las doce celdas (los lee el generador de informes). |

El param `turnover` del adapter (`full` \| `keep`) es la ÚNICA lectura del spec
congelado que este no determina del todo: el spec dice que la cartera es
top-3/bottom-3 en cada rebalance, pero no dice si una pierna que SIGUE
seleccionada se cierra y se reabre. Las dos lecturas se declaran, se corren y se
reportan; el veredicto es robusto a la ambigüedad (las doce celdas tienen
profit factor out-of-sample por debajo de uno).

### 3g. Ficheros de bot RETIRADOS (no desplegan nada)

| file | que era |
|---|---|
| `code/paper_live.py` | el bot paper de CVRMD (VPS `~/paper`, cron `*/5`) — **borrado del VPS el 2026-11-16** |
| `code/mp18_v2_paper.py` | el paper tracker de MP-18 v2 (VPS `~/mp18`) — **borrado el 2026-11-16** |
| `code/paper_s20_s8_s10.py` | el paper tracker de S20/S8/S10 (VPS `~/mp18`) — **borrado el 2026-11-16** |
| `code/mp18_forward.py` | el paper tracker de MP-18 previo al v2 — **borrado el 2026-11-16** |
| `code/xrp_bot_status_line.py` | el lector de estado del bot XRP de una pareja (VPS `~/xrp-paper-bot`, retirado el 2026-11-04) |

Cada uno lleva un banner `RETIRADO` en su docstring. **Ninguno despliega ni
corre nada**: no hay cron ni tarea programada que los lance, y no deben volver a
desplegarse. El material borrado del VPS esta archivado y verificado en
`backups/vps_retired_paper_mp18_20261116T213657Z.tar.gz`.

## 3f. El re-screen de los 100 prompts del pack (2026-11-12)

| file | qué es |
|---|---|
| `code/prompts100/` | el código del pack **copiado verbatim** (el pack vive en `Downloads/`, que no es durable) con `MANIFEST.json` y el sha256 de cada fichero: si alguien edita esa copia, la prueba de paridad deja de significar nada |
| `code/prompts100/pairs_signals.py` | el port de las **señales** de los prompts de par (81, 82, 85, 86, 88, 89) y de las cestas (83, 84, 87, 90), recortado del motor del pack: la parte de indicadores y las reglas de entrada/salida son suyas, la ejecución no |
| `code/p100_screen_engine.py` | el motor del repo: el libro de una pierna, el libro de dos piernas del spread y el libro de pesos de la cesta, con las convenciones del repo (next open, stop-first, hueco al open, 11 bps RT por pierna, funding en los settlements reales) y el invariante contable asertado dentro del artefacto |
| `code/_prompts100_parity.py` | **paridad a nivel de trade** contra el motor del pack en 29 prompts: los trades y las metricas son identicos con las convenciones del pack |
| `code/_p100_pairs_parity.py` | la misma paridad para los seis pares: las arrays de señal Y los trades y el PnL |
| `code/_prompts100_audit.py` | respuestas conocidas del motor, **en ambas direcciones** (fill, PnL, stop-first, hueco a través del stop, hueco de entrada, signo del funding, invariante, y el modo de convenciones del pack) |
| `code/_p100_screen_run.py` | la criba: un artefacto por (prompt, tramo), un fichero por celda para que doscorridas no se pisen |
| `code/_p100_screen_report.py` | el informe, construido desde los artefactos (guard `--strict` obligatorio) |
| `results/prompts100_rescreen_pre_registration.md` | el spec congelado antes de la primera corrida (tramos, gates, control de multiplicidad y las diferencias declaradas con el pack) |
| `results/_p100_cells/` | una celda por fichero (la criba en curso) |

Adapter: `p100screen` en `code/vrun.py` (params: `id`, `segment`). **No**
confundir con el adapter `prompts100` que ya existia en el repo (las cinco
supervivientes OOS del pack, con su port congelado en
`code/prompts100_engine.py`): ese se queda intacto.

El param `turnover` no existe aqui: el re-screen usa las dos lecturas del
spec (giro completo vs. solo lo que sale del ranking) solo en la familia A del
pack de 5 survivors, no en las cien.

## 4. Herramientas de auditoría por familia (`_*_audit.py`, `_*_gates.py`)

`_cbpack_audit.py` (known-answer), `_cbpack_cost.py` (control costo cero),
`_cbpack_gates.py` (period split + walk-forward + repo costs),
`_cbpack_funding_parity.py` (paridad con funding a cero — re-ejecutar tras
cualquier cambio del funding engine), `_pack50*_audit.py`, `_dspack*_audit.py`,
`_qs_audit.py` / `_qsf_*`, `_xrp_neutral_audit.py` (known-answer + parity +
causality + determinism + regression lock), `xrp_neutral_gauntlet.py`,
`xrp_neutral_grid.py`, `xrp_neutral_baseline.py`, `xrp_neutrality_check.py`
(neutral vs long-only vs short-only), `_verify_strategy.py`,
`_assert_report_totals.py` (los recuentos se reconcilian, no se declaran).

## 5. Ranking y registro (la capa de índice)

`strategy_registry.py` — el registro consultable + vistas por par/tf/familia
(`results/registry/`, regenerable). `_top100_rank.py` (extractor de métricas
por familia), `_top100_rerun.py` (re-ejecuta cmds verbatim en paralelo),
`_top100_refresh.py` / `_top100_v2.py` (rankings corregidos), `_top100_bundle.py`
(pack de entrega), `_top100_report.py`.

## 6. Builders de informes (`_*_build_report.py`, `_*_assemble_report.py`, `_*_report_table.py`)

Uno por campaña; todos deben re-renderizar DESDE artefactos, nunca con números
en el código. El estándar de recuentos en palabras y `guard` está en AGENTS.md.

## 7. Datos

Fetchers: `fetch_funding_all.py`, `fetch_alpaca_equities.py`, `fetch_solusdc_1h.py`,
`convert_edge_panel.py`, `fetch_aggtrades.py` (archivo bulk oficial de
aggTrades -> `data/aggtrades/<SYM>/` + `data/AGGTRADES_<SYM>_IMPORT.json`),
`fetch_instruments.py` (snapshot exchangeInfo spot+fapi -> `data/instruments/`
+ `data/INSTRUMENTS_MANIFEST.json`; consumidor `instruments_check.py`).
Auditorías de datos (2026-11-01): `datacheck_klines.py` (calidad + sha256 de
todo `data/binance_klines*/` -> `data/KLINES_MANIFEST.json`), `recorder_replay.py`
(auditoría de la cinta grabada del recorder; hallazgo: contador `stream_breaks`
inflado por diseño — la regla real de continuidad es `pu == prev_u` — y espacios
de id snapshot/diff extranjeros hasta que el recorder actualizado tomó efecto). Los CSV de klines/funding viven en `data/` organizados
por timeframe (append-only; su sha256 es parte de cada run_id).
`recorder/` (raíz) es el Track-R de order-flow, proyecto aparte y vivo.
`_find_duplicate_data.py` hashea `data/` y `recorder/data` y agrupa contenido
idéntico: es la comprobación de "no se duplique", por bytes y no por nombre.

## 8. Estadística transversal — `edge_stats.py` (vendored, 2026-11-01)

Copia vendorizada de `edge/engine/stats.py` (proyecto EDGE-first, terminal), con
cabecera de procedencia y cuerpo byte-idéntico bajo la línea marcador.
`_edge_stats_vendor.py` la regenera y `--check` demuestra la paridad; si alguien
edita la copia en vez del origen, el check falla.
`_edge_stats_audit.py` la verifica con **diecinueve** respuestas conocidas
(BH contra una implementación step-up independiente, `cluster_t` contra una CR1
escrita aparte, `effective_n` a mano, `mde_bps` contra su fórmula, SPA contra un
trial dominante y uno idéntico, y determinismo con semilla fija); salida en
`results/edge_stats_audit_known_answers.txt`. Ojo con dos firmas que no son
obvias: `effective_n` devuelve el **número de clústeres** en un diseño
balanceado, y `circular_shift_null` devuelve **dos valores** (p y la
distribución nula).

Lo que aporta y NO existía en `code/` (grep previo: cero ficheros): `cluster_t`
(t por día, CR1), `benjamini_hochberg` (FDR sobre TODOS los ensayos del ledger),
`spa_test` (Hansen), `mde_bps` + `effective_n` (potencia), `matched_timing_null`,
`circular_shift_null`, `factor_regression` (Newey-West vs BTC + cesta).
`deflated_sharpe` y `pbo_cscv` se mantienen por paridad de API pero su fuente
canónica sigue siendo `quant_metrics.py` — no editar allí desde aquí.

## Regla de casa

Toda campaña nueva termina con: (1) sus artefactos en `results/runs/`,
(2) su informe en `results/` con `guard` corrido y anotado en
`results/REPORTS.md`, (3) su fila en el registro
(`python code/strategy_registry.py` — regenera todo), (4) su veredicto en
AGENTS.md si cambia el estado del mundo.
