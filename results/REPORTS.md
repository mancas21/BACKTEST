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

## Control de coste cero sobre las filas 21-30 del top-100 (2026-11-20) — experimento, sin veredicto

| Informe | Qué | Guard hoy |
|---|---|---|
| `zerocost_rows21_30_report_2026-11-20.md` | las filas 21-30 de `top100_2026-10-31.md` (B17-1h, F75-1h, QS-004 x2, S46, QS-007, QS-005, ds1, QS-006, QS-093) re-corridas dos veces sobre el mismo corte congelado (BASE con su régimen publicado; ZERO con fees, slippage y funding a cero), sin aplicar gates; ds1 se publicó a coste cero (régimen `author`), así que su BASE y ZERO son el mismo artefacto y su corrida informativa es la COSTADA (`repo6x5`); veinte artefactos verify bit a bit; pre-registro `zerocost_rows21_30_pre_registration.md` (con addenda fechada sobre la semántica de reproducción), matriz `zerocost_rows21_30_matrix.json`, auditoría `code/_zerocost_rows21_30_audit.py` (45/45) | **OK (strict)** |

## Campana audit-fix del harness (2026-11-21) — fixes N1-N11 + A2/A3, re-medidos

| Informe | Qué | Guard hoy |
|---|---|---|
| `auditfix_report_2026-11-21.md` | la auditoria externa del harness (Qwen) verificada contra el codigo y arreglada: batería `bt one` fail-closed (N1 conc canónica, N2 N-A/pf-null/v2), bootstrap por chunks + piso de réplicas (N3), PBO delegado a la referencia (N4), stops intrabar de pares + fee-beta de entrada + funding-antes-de-stops (N5/N11), consumo del slice servido + funding/cost-model como inputs (N6), bootstrap_r con bloque escalado (N7), gates_v2 recalculado + policy_hash (N8), coste medido por símbolo cableado (N9), vecindario con `--set` + conjunción estricta (N10), cadena de drift que compone (A2) + recalibración `1d938af1df8dbfc0` verify OK (G5 monotono, conjunción v1 n300/d20 0.0175 -> 0.31, v2 0.095 genuino); selftest 44/44; re-screen regenerado y ciento ochenta y una artefactos verify OK | **OK (strict)** |
| `prompts100_rescreen_report.md` (regenerado 2026-11-21) | el mismo re-screen sobre la generación actual del engine (coste resuelto por símbolo, funding antes de stops, stops intrabar de pares): cuatro prompts pasan la criba DEV y CERO el veredicto OOS — veredicto sin cambios, todos los movimientos en dirección conservadora | **OK (strict)** |

## Campana audit-fix ronda 2 (2026-11-21) — NEW-1..6 de la re-auditoria sobre el commit 7b1b27a

| Informe | Qué | Guard hoy |
|---|---|---|
| `auditfix2_report_2026-11-21.md` | los seis defectos que la re-auditoria (pinnada al SHA) encontro en la ronda 1, todos arreglados: CI de muestra fina None en vez de `ci_high` fabricado (NEW-1, REGLA 0), piso de replicas lee el conteo logrado sin global (NEW-2), coste sobre nocional real al rt resuelto (NEW-3), colision de basenames del slice servido falla alto (NEW-4), centro del vecindario por valor mediano (NEW-5), nota de procedencia con el coste resuelto (NEW-6); selftest 55/55; generacion 3: 180 celdas + gatecal `d590af40751a6002` (metricas bit-identicas a la gen-2) | **OK (strict)** |

## Campana audit-fix ronda 3 (2026-11-21) — R1/R2/R3/R7 de la re-auditoria a fad193a + bonus (B&H de cestas)

| Informe | Qué | Guard hoy |
|---|---|---|
| `auditfix3_report_2026-11-21.md` | R1: el sobre intrabar de las puestas FALLA ALTO (la pierna sintetica ALT-BASKET del par ochenta y ocho se RECHAZA, no se degrada; modelo de stop y barras con rango viajan en el artefacto); R2: modo servido ESTRICTO (una lectura no declarada levanta error); R3: el sobre se prueba a la beta DE ENTRADA mantenida; R5 limpio por grep; R6 reconocida; R7 centinela de orden; BONUS encontrado verificando R2: el benchmark de las cestas era el B&H de BTC — ahora igual-ponderado de sus propias piernas (`bh_equal_weight`, artefactos BASKET6); R4 (ledger linealizado re-cobrado) APLAZADA a la campana trades_v2, declarada abierta. Gen-4: ciento setenta y ocho celdas (par ochenta y ocho declarado no medible) + gatecal intacto, sweep todo OK | **OK (strict)** |

## Campana audit-fix ronda cuatro (2026-11-21) — D2/D5/D6/D3/D4/D1/D7 + RETRACTACION del par ochenta y ocho

| Informe | Qué | Guard hoy |
|---|---|---|
| `auditfix4_report_2026-11-21.md` | D2 (alto): la reescritura R1 habia soltado el guard de finitud — una barra NaN de una pierna APAGABA el stop silenciosamente (y log(0)=-inf lo fabricaba); ahora la ventana operada debe ser finita y con rango real, si no REFUSA. D5: el benchmark de cestas usa la ventana alineada PROPIA (antes cada pierna usaba su fecha de listado). D6: `spread_envelope_built` es MEDICION (barras finas sobre la ventana operada), no inferencia de modo. D7: `spread_pnl_basis` declarado en el artefacto (linearizacion re-cobrada por-barra; el ledger de piernas R4 abre la campana trades_v2). D3/D4/D1 borrados. RETRACTACION: los numeros del par ochenta y ocho de TODAS las generaciones hasta la gen-3 salieron del modelo open-only degradado — RETIRADOS, no solo reemplazados (el engine estaba mal). Gen-5: ciento setenta y ocho celdas + gatecal intacto, sweep todo OK; diez celdas de pares publican barras finas/rango medidas | **OK (strict)** |

## Campana audit-fix ronda cinco (2026-11-22) — E1 ventana de medicion + trampa del piso de replicas + tabla de potencia v2 POR GATE

| Informe | Qué | Guard hoy |
|---|---|---|
| `auditfix5_report_2026-11-22.md` | E1 (alto): el rango del sobre se media sobre la SERIE COMPLETA mientras la finitud cubria la ventana operada — una celda OOS llevaba ~244k barras de rango sobre una ventana de ~36k, y una ventana operada todo-cero pasaba el guard: el modelo open-only re-entraba por el desajuste de ventanas; ahora el rango se mide SOBRE la ventana operada, cero REFUSA y la invariante rango ≤ finita se aserta (gen-6: p.ej. par ochenta y uno OOS finas=rango, par ochenta y nueve OOS finas=rango). TRAMPA DEL PISO confirmada en el artefacto: el cross-check de la capa de referencia corria a reps=400 < piso 500 → G1 y G9 fallaban cerrados en TODA simulacion (G1 0.0/G9 0.0 hasta en edge veinte con G4 a media potencia) — la tabla por-gate estaba SUPRIMIDA por el piso, no medida. null_calibration: defecto 2000 + RECHAZA por debajo del piso; gatecal xref re-provisionado (reps=2000, n_sims=400, doce celdas). TABLA DE POTENCIA v2 POR GATE publicada + el sanity check pasa EXACTO (expectancy d20 − d0 = veinte bps); los asesinos de la conjuncion nombrados a n300/d20: G6 0.0925 (concentracion), G8 0.115 (coste), G5 0.1525 (benchmark), G7 0.2575 (DSR); el joint head-line 0.095 confirmado GENUINO (los booleans v2 del engine llaman a gate2 directamente, sin piso). book_type por sid (neutral/directional) en todos los artefactos. Gen-6: ciento setenta y ocho celdas + gatecal nuevo `9183c116b24003c3` verify OK, sweep todo OK | **OK (strict)** |

## Campana audit-fix ronda seis (2026-11-22) — el filo plantado era BRUTO, no neto: gates exonerados y curva de potencia en t-units

| Informe | Qué | Guard hoy |
|---|---|---|
| `auditfix6_report_2026-11-22.md` | la sexta re-auditoria pesco la interpretacion que cinco rondas arrastraban: el drift plantado es BRUTO (net = bruto − coste − funding) — el viejo d20 era un filo NETO de +9 bps/trade a n=300, un t de ~0.5 sobre dispersion de cientos de bps: RUIDO, y las tasas bajas de G6/G5/G7/G8 eran la respuesta correcta. null_calibration devuelve el NIVEL (expectancy_bps neto + net_std_bps) con el aviso bruto-no-neto en su docstring; gatecal crecio `power_by_t`: filos plantados en t-units (t 1/2/3/5 × n 100/300, cuatrocientas sims por celda a reps 2000) con la invariante joint ≤ min-gate en las ocho celdas y el piso de G8 declarado (22 bps = 2x el RT; la primera corrida declaro 11 — desliz mio, corregido y re-run). LA CURVA: n300 t3 joint 0.735, t5 0.9675, t medidos clavados al objetivo (3.09 para t=3) — **el gate set esta a la altura en filos detectables y la conclusion del corpus pasa a SER SOSTENIDA: ningun filo de t≥3 fue detectado en este corpus por una batería con 73.5% de potencia a t=3**. E respondido: la store esta mas fresca que el brief (ETHUSDT 15m hasta 2026-11-15; la fecha del brief era un snapshot). `compute_gates_v2` SI lee book_type al GateContext. Gen-6 p100 intacta; gatecal `0c06de045d2044b6` verify OK; selftest 72/72 | **OK (strict)** |

## Campana audit-fix ronda siete (2026-11-22) — F1 rebinding, las DOS curvas de potencia (undeflated vs deflated al ledger real) y la decision de politica puesta al operador

| Informe | Qué | Guard hoy |
|---|---|---|
| `auditfix7_report_2026-11-22.md` | F1 (alto): la edicion de la ronda cinco RE-ató el nombre `cells` — las doce celdas v1/v2 desaparecieron de todo artefacto gatecal de esa generacion (m["cells"] eran las seis xref); restauradas + asserts duros 12/6/8 en el engine. F2 (alto): n_trials=1 APAGABA la deflacion DSR — cada celda power_by_t corre DOS veces con sims identicas: undeflated vs DEFLATED al ledger REAL (mil cuatrocientas ochenta y seis trials medidas del jsonl): n300 t3 undef 0.735 → DEF 0.065, t5 0.9675 → DEF 0.4725; **G7 SOLO acota el joint** (def G7 0.065 a t3 con G1/G5/G6 a 0.84-0.92). F5: variante de holds del corpus (deflated): t3 0.07, t5 0.4525. F3: la nota retracted reescrita. La sentencia honesta: gates sanos, potencia 10-40% contra filos realistas undeflated y ~0-47% deflated, y AUN no aplicados al corpus en forma medida (nada emite trades_v2). DECISION DE POLITICA al operador: ledger global vs por-familia para campanas pre-registradas (ambas maquinarias existen; los numeros de ambas curvas estan en el artefacto). Gatecal `c7a5d888839717c9` verify OK | **OK (strict)** |

## Control de coste cero sobre las filas 31-40 del top-100 (2026-11-23) — experimento, sin veredicto

| Informe | Qué | Guard hoy |
|---|---|---|
| `zerocost_rows31_40_report_2026-11-23.md` | las filas 31-40 de `top100_2026-10-31.md` (QS-009 JUP, S10 ETH, rsimr SOLUSDC, QS-004 SOL, QS-006 SUI/HYPE, fingrad ETH, ds1 BNB/DOGE, QS-005 ETH) re-corridas dos veces sobre el mismo corte congelado (BASE con su régimen publicado; ZERO con fees, slippage y funding a cero), sin aplicar gates; ds1 se publicó a coste cero (`costs=author`, sin funding), así que sus BASE y ZERO son el mismo artefacto y sus corridas informativas son las COSTADAS (`repo6x5`); veinte artefactos verify bit a bit; pre-registro `zerocost_rows31_40_pre_registration.md`, matriz `zerocost_rows31_40_matrix.json`, auditoría `code/_zerocost_rows31_40_audit.py` (47/47) | **OK (strict)** |

## Control de coste cero sobre las filas 41-50 del top-100 (2026-11-23) — experimento, sin veredicto

| Informe | Qué | Guard hoy |
|---|---|---|
| `zerocost_rows41_50_report_2026-11-23.md` | las filas 41-50 de `top100_2026-10-31.md` (S02 SUI, S03 XRP, QS-001 BTC 15m, fingrad SUI, ds1 HYPE, S02 ETH, QS-002 SOL, QS-007 SUI, QS-006 JUP, QS-003 SUI) re-corridas dos veces sobre el mismo corte congelado (BASE con su régimen publicado; ZERO con fees, slippage y funding a cero), sin aplicar gates; ds1 se publicó a coste cero (`costs=author`), así que su BASE y ZERO son el mismo artefacto y su corrida informativa es la COSTADA (`repo6x5`); los dos artefactos `cbpackf` ETH se reutilizan de la tanda 31-40; veinte artefactos verify bit a bit; pre-registro `zerocost_rows41_50_pre_registration.md`, matriz `zerocost_rows41_50_matrix.json`, auditoría `code/_zerocost_rows41_50_audit.py` (48/48) | **OK (strict)** |

## Control de coste cero sobre las filas 51-60 del top-100 (2026-11-23) — experimento, sin veredicto

| Informe | Qué | Guard hoy |
|---|---|---|
| `zerocost_rows51_60_report_2026-11-23.md` | las filas 51-60 de `top100_2026-10-31.md` (P08 ETH, QS-009 SUI, S10 SUI/HYPE, QS-006 ETH, S07 ETH, C44-1h ETH, ds3 SOL, QS-003 SOL, MP-V3-S10 PORTFOLIO) re-corridas dos veces sobre el mismo corte congelado, sin aplicar gates; ds3 se publicó con `repo6x5` (régimen costado), así que su ZERO usa el preset `author` del engine; switch aditivo nuevo en `vrun.py` para `pack50d` y opción `funding_signal` para `cbpackf` (la señal de S07 lee la columna de funding, que se conserva sin cobrar); deriva de engine de los artefactos de ranking anterior al audit-fix declarada; veinte artefactos verify bit a bit; pre-registro `zerocost_rows51_60_pre_registration.md` con addenda, matriz `zerocost_rows51_60_matrix.json`, auditoría `code/_zerocost_rows51_60_audit.py` (50/50) | **OK (strict)** |

## Control de coste cero sobre las filas 61-70 del top-100 (2026-11-23) — experimento, sin veredicto

| Informe | Qué | Guard hoy |
|---|---|---|
| `zerocost_rows61_70_report_2026-11-23.md` | las filas 61-70 de `top100_2026-10-31.md` (QS-003/002/001/004 JUP, S02 y S03 HYPE en un mismo artefacto `cbpackf`, ds7 SPX, QS-001 SOL 15m, ds5 LINK, F75-15m SUI) re-corridas dos veces sobre el mismo corte congelado, sin aplicar gates; ds5 se publicó a coste cero (`author`, su BASE y ZERO comparten artefacto y su corrida informativa es la COSTADA), ds7 se publicó a `repo6x5`; los artefactos HYPE se reutilizan de la tanda anterior; dieciocho artefactos únicos verify bit a bit; pre-registro `zerocost_rows61_70_pre_registration.md`, matriz `zerocost_rows61_70_matrix.json`, auditoría `code/_zerocost_rows61_70_audit.py` (45/45) | **OK (strict)** |
