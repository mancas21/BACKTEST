# Índice de informes — verificado con `guard` el 2026-11-04

`guard` es una comprobación de **procedencia** (¿cada número está respaldado por
un artefacto citado?), no de corrección. REFUSED significa que el archivo
contiene números sin artefacto detrás: **no citar sus números**; leerlo solo
como narrativa o historia. Estado de guard puede cambiar cuando los datos
subyacentes cambian — regenerar este índice re-corriendo los comandos.

## Campañas de packs (veredictos de kill)

| Informe | Familia | Veredicto | Guard hoy |
|---|---|---|---|
| `pack50_report.md` | llm_pack (48 prompts) | KILLED 0/48 | **OK** |
| `pack50b_report.md` | llm_pack claude2 | KILLED 0/46 | OK |
| `pack50c_report.md` | llm_pack Qwen-50 | KILLED 0/42 | OK |
| `pack50d_report.md` | llm_pack DeepSeek | KILLED 0/48 | OK |
| `pack100_report.md` | llm_pack Sonnet-100 | KILLED 0/100 | **OK** |
| `qs_report.md` | risk_sized_book familia A | KILLED 0/10 | **OK** |
| `qsf_report.md` | risk_sized_book trade-flow | KILLED 0/8 | **OK** |
| `qsb_report.md` | risk_sized_book familia B (mean reversion) | KILLED 0/12 | **OK** |
| `qsc_report.md` | risk_sized_book familia C (vol/breakout) | KILLED 0/10 (2 near-misses g6) | **OK** |
| `qsd_report.md` | risk_sized_book familia D (market structure) | KILLED 0/10 (2 near-misses g6) | **OK** |
| `cand7_report.md` | 7 candidatos pre-especificados | KILLED 0/7 | **OK** |
| `top10_report.md` | llm_pack_shortlist (criba de cien prompts, 2026-11-01) | 2 de 10 CANDIDATE (#44 #28); 8 KILLED | **OK strict** |
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
