# Índice de informes — verificado con `guard` el 2026-11-04

`guard` es una comprobación de **procedencia** (¿cada número está respaldado por
un artefacto citado?), no de corrección. REFUSED significa que el archivo
contiene números sin artefacto detrás: **no citar sus números**; leerlo solo
como narrativa o historia. Estado de guard puede cambiar cuando los datos
subyacentes cambian — regenerar este índice re-corriendo los comandos.

## Catálogos / rankings (referencia, no veredictos de kill)

| Informe | Contenido | Nota |
|---|---|---|
| `TOP100_ESTRATEGIAS.md` | Top-100 estrategias distintas por PF neto IS (artefacto verificado), con descripción, familia, símbolo/TF, métricas IS/OOS, costes, funding, ventana, veredicto y run_id. Datos: `top100_catalog.json` / `.csv`. Builder: `code/_top100_catalog.py`. | Ranking RELATIVO dentro de un corpus con 0 supervivientes; solo 68/100 con PF neto>1. Números por estrategia citan run_id (fichas); los conteos del resumen son agregaciones (no guard-certificado). |
| `TOP_OOS_ROBUST.md` | Vista alternativa: ranking por PF neto OOS + filtro de robustez (IS n≥100, PF IS>1, OOS PF>1, OOS n≥30, boot CI>0). 6 pasan el filtro ligero; 29 sostienen OOS. Datos: `top_oos_robust.json`. | El filtro es SUBCONJUNTO de G1-G11 (faltan 2× coste, DSR, concentración, P95 DD, B&H); las 6 NO son supervivientes validadas (mayoría SIN VEREDICTO). Priorización de investigación. |
| `CANDIDATES_V2_VALIDATION.md` | Batería G1-G11 COMPLETA sobre las candidatas robustas. 3 family-A re-corridas con el Book del repo, paridad DEV bit-a-bit, esquema v2 reconstruido (gross/cost/funding/MAE). **0/3 pasan**. Datos: `candidates_v2_validation.json`. Validator: `code/_validate_candidates_v2.py`. | TRIX BTC 15m pasa G1/G2/G8/G11 pero cae G3/G4/G5/G6/G7/G9 (DSR 0.089, concentración, no bate B&H, liquidaciones). id=85 spread + 2 pack20 pendientes de instrumentación de su book. |
| `CANDIDATE_SPREAD_V2.md` | Batería G1-G11 sobre el SPREAD id=85 (mid-day-lull HYPE/SOL, beta Kalman). SpreadBook instrumentado en memoria, paridad DEV OK, esquema v2 en fracciones del notional de exchange, book neutral (benchmark cash). **Pasa 9/10, solo falla G8**. Datos: `candidate_spread_v2.json`. Validator: `code/_validate_spread_v2.py`. | DSR=1.0, alfa t=3.90, OOS PF 1.97, DD 9.1%; G8 falla (cost_share 54%, PF@2×coste 0.997). Leverage de exchange 36x > cap 20x (tradeability). F23 corregido (G5 benchmark neutral singular). NO es superviviente validada. |
| `TOP100_RERUN_2026-11-19.md` | Corrida fresca del top-100 completo (in-process, `make_artifact` con cut auto, ocho procesos): 25 REPRODUCED (mismo run_id, reproducción bit a bit), 74 REFRESHED (datos crecidos desde la creación del artefacto citado → run_id nuevo), 1 ORPHANED (sax, engine borrado). 23 celdas OOS hermanas de p100screen re-corridas. `pverify`: 122/122 OK. Mapa: `_top100_rerun_20261119_map.json`; ids frescos: `_top100_fresh_ids_20261119.txt`. Runner: `code/_top100_rerun_20261119.py`. Builder: `code/_top100_rerun_report_20261119.py`. | Medición, no veredictos (REGLA 1): re-correr no cambia ningún veredicto ni crea supervivientes. Guard --strict OK hoy. Mayores movimientos: r91 scalpwave PF 0.950→0.776 (SOL 5m), r4 qs096 OOS PF 6.41→7.99. Único flip OOS: r30 qs097 SUI. |

## Campañas de packs (veredictos de kill)

| Informe | Familia | Veredicto | Guard hoy |
|---|---|---|---|
| `pack50_report.md` | llm_pack (48 prompts) | KILLED 0/48 | **OK** |
| `pack50b_report.md` | llm_pack claude2 | KILLED 0/46 | OK |
| `QWEN50_REPORT_2026-11-19.md` | qwen50 (50 prompts 51-100, Qwen; 48 corridas, 2 NO-DATA declarados: 93 sin NVDA 1m, 98 sin SPCX 1m) | KILLED 0/48 (screen: mejor PF 0.99, ninguno llega a 1.0; 1m arrasado por costes, PF 0.02-0.38) | **OK** |
| `pack50c_report.md` | llm_pack Qwen-50 | KILLED 0/42 | OK |
| `pack50d_report.md` | llm_pack DeepSeek | KILLED 0/48 | OK |
| `pack100_report.md` | llm_pack Sonnet-100 | KILLED 0/100 | **OK** |
| `qs_report.md` | risk_sized_book familia A | KILLED 0/10 | **OK** |
| `qsf_report.md` | risk_sized_book trade-flow | KILLED 0/8 | **OK** |
| `qsb_report.md` | risk_sized_book familia B (mean reversion) | KILLED 0/12 | **OK** |
| `qsc_report.md` | risk_sized_book familia C (vol/breakout) | KILLED 0/10 (2 near-misses g6) | **OK** |
| `qsd_report.md` | risk_sized_book familia D (market structure) | KILLED 0/10 (2 near-misses g6) | **OK** |
| `cand7_report.md` | 7 candidatos pre-especificados | KILLED 0/7 | **OK** |
| `top10_report.md` | llm_pack_shortlist (criba de cien prompts, 2026-11-01; artefactos refrescados 2026-11-12) | 1 de 10 CANDIDATE (#44); 9 KILLED | **OK strict** |
| `cbpack_funding_report.md` | pack S01-S10 CON funding | KILLED (concentración 1h) | **OK** |
| `cbpack_backtest.md` | pack S01-S10 sin funding | KILLED <1h | **REFUSED hoy** — números no citables |
| `xtf_backtest.md` | cbot suite multi-tf | KILLED | **REFUSED** (tally no respaldado, conocido) |
| `cbot_1m_campaign.md` | cbot 1m | KILLED | **OK** |
| `cbot_realdata.md` | cbot | KILLED | **REFUSED hoy** |
| `q10_pack_results.md` | qwen cards | diagnostico | OK |
| `q10_step0.md` | qwen cards | diagnostico | OK |
| `qwen_pack10_grade.md` | qwen 10 | RECHAZO pre-port | REFUSED (narrativa) |
| `pack10_prereg.md` | pre-registro | — | REFUSED (narrativa) |

## Familias individuales / puertos

| Informe | Familia | Veredicto | Guard hoy |
|---|---|---|---|
| `dspack_report.md` | deepseek ds1-ds5 | KILLED (costo cero fantasma; 11bps RT en registro) | **OK** |
| `dspack2_report.md` | deepseek ds6-ds10 | KILLED | **OK** |
| `emaadx_report.md` | trend EMA+ADX | KILLED | **OK** |
| `fingrad_report.md` | HMA·AO·ADX | KILLED (+ sin funding; SUI 17.3→1.6 con funding) | **OK** |
| `hmaaoadx_report.md` | HMA/AO/ADX pack | KILLED | **OK** |
| `smqe_report.md` | SMC compuesto | SUSPENDED | **OK** |
| `eqpack_qqq_report.md` | equities QQQ | KILLED 0/7 | **OK** |
| `mpv3_s10_institutional_audit.md` | momentum cartera | KILLED concentración | **REFUSED hoy** |
| `mps20_report.md` | cartera MPS20 | — | OK |

## XRP neutral (el libro que fue el único PASS, hasta el 2026-10-31)

| Informe | Estado | Guard hoy |
|---|---|---|
| `xrp_neutral_report.md` | v1 — histórico; citaba el par hoy STALE | OK |
| `xrp_neutral_25x10_report.md` | v2 — histórico; citaba el par hoy STALE | OK |
| `top100_2026-10-31.md` / `top100_ranking_2026-10-31.md` / `top100_ranking_refresh_2026-10-31.md` | rankings descriptivos del corpus | **OK** |

**KILL 2026-10-31 (ahora artefacto, no solo sonda):** resolución 1m de los
fills (`code/_xrp_1m_resolution.py`, engine variante sha `c7975777c032f3a5`)
sobre el segmento OOS 2023+: PF 1.3019 → **0.9326**, win 86.9 → 77.5%,
+17.031% → **−74.2%**. Sonda: `code/_xrp_1m_resolution_out.json`. Desde el
2026-11-04 la misma cifra vive en artefactos del harness: `c7f1063c88f3268f`
(15m, baseline) y `18d686932bf06f78` (1m), ambos `verify` OK. El libro está
KILLED como simulado; el paper bot del VPS sigue corriendo como registro
forward (día-0 2026-10-23: PF 1.203 en 21 lotes) — hoy reemplazado por el
libro de cinco pares con contabilidad 1m.

## El pack de 100 prompts re-screeneado (2026-11-12)

| Informe | Qué | Guard hoy |
|---|---|---|
| `prompts100_rescreen_report.md` | los cien prompts del pack con la senal del pack (verbatim, copiada al repo con manifiesto sha256) y la EJECUCION del repo (11 bps RT, funding real, invariante asertado en el artefacto), con seleccion sobre DEV y veredicto sobre OOS: la criba sin contaminar que el pack no podia hacer | **OK strict** |

La tabla "Top 5" del pack es fiel a su CSV, pero sus numeros no son
evidencia: el pack ordeno los cien por su propio OOS Profit Factor y corria
a **1.1 bps round trip** (su constante es 0.55 bps por lado, no los 5.5 que
documenta), con el PnL por trade **sin la comision de entrada** y **sin
funding**. Los libros de par implican un nocional bruto de hasta **2.215.983x
el equity**: no son certificables. Pre-registro:
`results/prompts100_rescreen_pre_registration.md`.

## `xsml` — libro cross-sectional con filtro ML (2026-11-11) — KILLED, y una
## corrección de contabilidad

| Informe | Qué | Guard hoy |
|---|---|---|
| `xsml_report.md` | el libro base (V1), pre-registrado antes de la primera corrida: features con el motor de indicadores de pybroker, modelo con hiperparámetros fijos y purga/embargo, ejecución DEL REPO (next-open, stop-first, gap-through al open, 11 bps RT por pierna, funding en settlements reales) | **OK strict** (artefacto `d5cefbaf8e3dcb85`) |
| `xsml_variants_report.md` | la campaña de variantes V2..V5 **y las dos lecturas del turnover** que el spec congelado deja abiertas: doce artefactos, gate por gate | **OK strict** (12 artefactos citados) |

Veredicto: **KILLED** — los doce libros (cinco variantes por dos lecturas del
turnover) tienen profit factor out-of-sample por debajo de uno, así que la
conclusión es robusta a la ambigüedad del spec.

**Corrección de contabilidad (importante).** La primera versión del engine
multiplicaba por `side` una cantidad que **ya era firmada**, así que cada
pierna corta se contabilizaba como un espejo-largo y su comisión se
**acreditaba** en vez de cobrarse. Lo detectó el invariante contable del repo,
que el engine no asertaba: el residuo era de mil seiscientos ochenta y nueve
dólares con sesenta y cinco centavos, exactamente cuatro comisiones por cada
uno de los quinientos siete trades cortos. El artefacto `a2fc128ff0f42f5d` y
las cifras del informe original quedan **RETIRADOS**: publicaban un libro mal
contabilizado. El engine ahora aserta el invariante **dentro** de cada
artefacto y lo publica (`pnl_identity_resid`), y la suite de respuestas
conocidas (`code/_xsml_engine_audit.py`, 32/32 PASS) cubre el lado corto en
todas las reglas.

Lo que queda: el forecast **sí correlaciona** out-of-sample y el libro pierde
igual. El libro base sin costes era marginalmente positivo, o sea que el
problema es que el edge por operación no cubre el coste del giro, no que la
señal sea nula. V5 falsifica H0 en las dos lecturas (pierde el lado largo y el
corto), V4 (reward:risk asimétrico) es el peor de los seis y V3 (menos giros)
el menos malo.

Pre-registros: `results/xsml_pre_registration.md`,
`results/xsml_variants_pre_registration.md`,
`results/xsml_turnover_pre_registration.md`. Auditoría de features 5/5
(incluye el test bump-last-bar de look-ahead); auditoría del engine 32/32.

## Transferencia al S&P 500 (2026-11-11) — cada estrategia del repo sobre la serie de equities

| Informe | Qué | Guard hoy |
|---|---|---|
| `equities_transfer_2026-11-11.md` | cada estrategia símbolo×tf del repo corrida sobre `data/alpaca_1d` (SPY = el ETF del S&P 500, QQQ): 60 celdas intentadas, 20 con artefacto, 40 rechazadas por los guards de cada engine; regímenes de coste repo y coste cero | **OK strict** (24 artefactos citados) |

Adapter sin cambios: el override `data_dir` del harness (`code/vrun.py`,
`make_artifact`) reapunta la entrada a otro directorio y el directorio entra en
el `core`. Veredicto: **ningún edge transfiere al S&P 500**; sobre SPY todo lo
que negocia pierde, y a coste cero también. Aclaración: **`SPXUSDT` no es el
índice** (corr con SPY 0.31; con QQQ 0.95): es un perp cripto cuyo activo base
es `SPX`. Artefactos: `results/runs/<run_id>`.

## WAVE_1 scalp pack (2026-11-11) — port desde `Downloads/scalp_wave1_v1.1.0`

| Informe | Qué | Guard hoy |
|---|---|---|
| `scalpwave_report_2026-11-11.md` | port del pack WAVE_1 (IND-04/06/07a) al harness: 12 celdas + 3 sondas, desglose por familia de señal, paridad contra el pack original | **OK strict** (15 artefactos citados) |

Adapter `scalpwave` (familia de registro `scalp_wave`), engine
`code/scalp_wave_engine.py`. Veredicto: **KILLED** — 0 de 12 celdas pasan
(PF ex-cost 0.6644–0.8624) y las 12 pierden también a coste cero. Paridad
con el pack original 25/25 (`code/_scalp_wave_parity.py`). 24 artefactos de
versiones intermedias del engine quedan obsoletos por drift y NO son citables.

## 1m fill accounting — 2026-11-04 (bot retirado, cinco pares en marcha)

| Informe | Qué | Guard hoy |
|---|---|---|
| `xrp_neutral_1m_fill_accounting_2026-11-04.md` | contabilidad 1m del libro neutral de cinco pares; el builder rehúsa una base distinta al engine desplegado; la barra se resuelve por minuto solo con tape completo; el wick same-minute se cuenta y se banea | **OK** |

Artefactos: `results/runs/c7f1063c88f3268f.json` (15m baseline, OOS), `results/runs/18d686932bf06f78.json` (1m, OOS), `results/runs/6f815d5b52cfd930.json` (15m, historia completa a datos actuales). Los tres `verify` OK. Engine: `code/xrp_neutral_engine_paper_1m.py` (GENERADO por `code/_neutral_1m_build.py`); auditoría `code/_neutral_1m_audit.py` → `_neutral_1m_audit.json` (12/12 PASS). Deploy: `~/neutral-paper/` (5 pares, cron 1m un minuto tras el 15m, lock compartido); el bot de un solo par `/home/ubuntu/xrp-paper-bot/` fue retirado y borrado, archivo en `/home/ubuntu/backups/xrp-paper-bot_retired_2026-11-04.tar.gz`.

## Gobernanza, auditorías, infraestructura

| Informe | Qué es | Guard hoy |
|---|---|---|
| `gate2_scoring.md` | capa estadística v2 (G1-G10) | **OK** |
| `gate_calibration_report.md` | calibración nula del gate | **OK** |
| `methodology_audit_2026-10-25.md` | auditoría de metodología | REFUSED (narrativa) |
| `repo_reaudit_2026-10-25.md` | re-auditoría del repo | REFUSED (narrativa) |
| `doc_audit_2026-10-29.md` | auditoría de documentos | **OK** |
| `edge_folder_audit_2026-10-29.md` | auditoría + migración EDGE | OK (sin números) |
| `edge_migration_2026-11-01.md` | cierre de la migración: qué entró, qué se arregló, qué se borró y la auditoría de duplicados | **OK** (sin números) |
| `inventory_2026-10-29.md` | inventario del repo | **OK** |
| `tactical_screen_2026-10-25.md` | screen táctico | REFUSED (narrativa) |
| `poly_pre_registration.md` | pre-registro | OK (sin números) |
| `STRATEGY_GENERATOR_PROMPT-GLM5.3_corrected.md` | contrato del generador | REFUSED (spec, no informe) |

## Cómo usar este índice

1. Números citables solo de informes con **guard OK hoy** y solo con su run_id.
2. Los REFUSED por narrativa (auditorías, pre-registros, specs) son legítimos
   como documentos, jamás como fuentes de métricas.
3. Para regenerar: `for f in results/*.md; do python code/vrun.py guard --report $f; done`
4. El universo de estrategias vive en `results/registry/` (ver su README).

## Añadidos 2026-11-01 (campaña del delta)

| Informe | Familia | Veredicto | Guard hoy |
|---|---|---|---|
| `bookreplay_report.md` | fill-resolution replay (bookreplay) | hallazgo de fill-model: convención 15m infiel en ambas direcciones | **OK (strict)** |
| `klines_datacheck_2026-11-01.txt` | auditoría de calidad de datos | limpio (hallazgos en palabras; exactitud en `data/KLINES_MANIFEST.json`) | **OK** |
| `recorder_replay_2026-11-01.txt` | auditoría de calidad de cinta | usable para fills en bookTicker; anclaje de libro solo hacia adelante | **OK** |
| `recorder_book_audit.md` | reconstrucción del libro desde depth + bookTicker | FAIL en BTCUSDT (peor célula por debajo del umbral warn); depth y depth_snapshot se borran | **OK** (sin números) |

## Añadidos 2026-11-02

| Informe | Familia | Veredicto | Guard hoy |
|---|---|---|---|
| `xsf_category_a_report.md` | cross-sectional factores OHLCV 1h (xsf: LOWVOL/SKEW/AUTOCORR, universe-14) | KILLED — cero de tres PASS, vecindario sin rescate (9 artefactos verify OK) | **OK (strict)** |
| `xsf_category_b_report.md` | valor relativo 1h (xsb: VOLCOMP/DDRELAY, universe-14) | KILLED — cero de dos PASS, ambas pierden en bruto, vecindario sin rescate (6 artefactos verify OK) | **OK (strict)** |
| `xsf_category_c_report.md` | funding-como-filtro 1h (xsc: FUNDGATE/FUNDTAIL, 7 nombres, funding COBRADO) | KILLED — cero de dos PASS; FUNDGATE pierde por senal, FUNDTAIL por suelo de muestra (6 artefactos verify OK) | **OK (strict)** |

## 2026-11-06 — capa rápida del pipeline

| Informe | Familia | Veredicto | Guard hoy |
|---|---|---|---|
| `results/bt_pipeline-demo_report.md` | bt.py demo (machinery check: top10 #28/#44 + prompts100 #60, cbpack WF+neighborhood) | machinery demo, not a strategy verdict | OK (strict) |

Notas de la campaña: los números del informe salen de artefactos citados por
run_id; los timings viven en `results/bt_timings/` (guard no los respalda y
no se citan). Regenerado el registro (`strategy_registry.py`, one thousand
seven hundred twenty-one estrategias). Los artefactos de generación 2 llevan
`core.cut_ts` — la auditoría `stale` los lee OK aunque los ficheros de datos
hayan crecido después del corte.

| `results/smqe11_report.md` | smqe11 (SMQE v1.1 adjunto, core CVRMD + simulador v1.1) | KILLED — cero de diez celdas pasa todos los gates; SUI 1h repo+funding falla solo el IC bootstrap | OK (strict) |

| `results/qs097_report.md` | qs097 (QS-097 cross-asset confirmation, catálogo familia J) | KILLED - cero de veinticuatro celdas pasa la batería estándar; mejor celda ETH 1h two_side falla concentración y IC | OK (strict) |

| `results/htffvg_report.md` | htffvg (4H FVG -> 15M tap -> 15M FVG, adjunto Python) | KILLED - cero de doce celdas pasa; el modo limit no es certificable por fill-model | OK (strict) |
| `fvgup_report_2026-11-13.md` | ICT 4H FVG→15M FVG + 1m intrabar + sesiones (fvgup, adjunto 2026-11-13) | KILLED — cero de cuatro PASS; paridad dual-motor del pack FALLA en BTC (declarada), OK en ETH; dos bugs de unidades pandas-3.0 corregidos en el puerto | **OK (strict)** |
| `results/top100_1d_2026_report.md` | Top-100 del ranking 2026-11-09 transferido VERBATIM a tf=1d x 11 pares (JUP HYPE SUI ARB SOL ETH NVDA SPCX 1000PEPE XRP BTC), datos SOLO 2026 en los bytes (fetch_1d_pairs.py); 150 celdas con artefacto de 539 intentadas, las demas rechazadas por sus propios guards (piso G5 nueve mil barras QS, piso quinientas cbpackf, guards solo-1h, panel qs097) | DESCRIPTIVA (transferencia, no veredicto de gates) | **OK (strict)** |

| `s101_report.md` | STRATEGIES 101-150 pack (37 celdas intradía: estructura/traps/sesiones/flujo/RV; 13 NO-DATA saltadas por la regla #19 del pack) | KILLED — cero de treinta y siete PASS; ruina por costes en intradía (37 artifacts verify OK) | **OK (strict)** |

| `hmatrend_report_2026-11-14.md` | hmatrend (pack externo hermes HMA(34) Trend, 12 pares 1h 2026; reconstrucción declarada - el código fuente del pack NO sobrevivió) | KILLED — cero de once celdas pasa la batería (22 artifacts verify OK); el claim es irreproducible desde sus propios outputs; XAU NO DATA | **OK (strict)** |

| `ema921_report_2026-11-17.md` | ema921 (9-21 EMA crossover, adjunto 2026-11-17; 101 celdas: ocho 1m, diez 5m, treinta y cinco 15m, treinta y siete 1h, once 1d) | KILLED — cero de ciento una celdas pasa la batería; las dos con PF>1.2 (LAB y ZEC 1h) mueren por IC bootstrap y por B&H; ruina por coste de giro en 1m-1h; 1d sin muestra | **OK (strict)** |

| `scalpma20_report_2026-11-18.md` | scalpma20 (20 estrategias MA de scalping 1m-5m del adjunto `scalp_ma_suite-20 STATEGIES-CLAUDE.py`; SOL/SUI/HYPE × {5m,1m} × 20 = 120 celdas screen) | KILLED — cero de ciento veinte celdas pasa la batería; PF neto 0.32-0.94, net −100% a −4.5%, OOS PF<1 salvo una celda degenerada (inf/16 trades); zero-cost PF máx 1.1195 < gate 1.2 → sin filo bruto sobre el gate + ruina por turnover a 11 bps; paridad de señal 100/100 vs fuente adjunta, self-test 40/40, 120 artifacts verify bit-a-bit | **OK (strict)** |

## Control de coste cero sobre el top-10 (2026-11-20) — experimento, sin veredicto

| Informe | Qué | Guard hoy |
|---|---|---|
| `zerocost_report_2026-11-20.md` | las diez primeras filas de `top100_2026-10-31.md` re-corridas dos veces sobre el mismo corte congelado (BASE con su régimen publicado; ZERO con fees, slippage y funding a cero), sin aplicar gates; dieciocho artefactos verify bit a bit; pre-registro `zerocost_pre_registration.md`, matriz `zerocost_matrix_2026-11-20.json`, auditoría `code/_zerocost_audit.py` (23/23) | **OK (strict)** |

## Control de coste cero sobre las filas 11-20 del top-100 (2026-11-20) — experimento, sin veredicto

| Informe | Qué | Guard hoy |
|---|---|---|
| `zerocost_rows11_20_report_2026-11-20.md` | las filas 11-20 de `top100_2026-10-31.md` (QS-001, botstrat AVAX/ETH/SOL/BTC, C7, S01+S05 QQQ, smqe, cvrmd SOL) re-corridas dos veces sobre el mismo corte congelado (BASE con su régimen publicado; ZERO con fees, slippage y funding a cero), sin aplicar gates; dieciocho artefactos verify bit a bit (dos compartidos con la tanda de filas 1-10); pre-registro `zerocost_rows11_20_pre_registration.md` (con adenda fechada), matriz `zerocost_rows11_20_matrix.json`, auditoría `code/_zerocost_rows11_20_audit.py` (45/45) | **OK (strict)** |
