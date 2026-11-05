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
