# RUNBOOK — correr los backtests en otro agente/máquina

## Paper forward de 5 pares (VPS) — `~/neutral-paper`

Bot independiente: grid DELTA-NEUTRAL sobre cinco perpetuos (JUP, XRP, SOL, HYPE,
SUI de Binance USDT-M), 15m, paper only. Un directorio por par, con su propio
estado, logs y datos. **No toca** `~/paper`, `~/grid-paper`, `~/cqb`,
`~/freqtrade` ni `~/mp18`.

El bot viejo de un solo par (`/home/ubuntu/xrp-paper-bot/`) fue **retirado y
borrado** el 2026-11-04: archivo en
`/home/ubuntu/backups/xrp-paper-bot_retired_2026-11-04.tar.gz`, cero lineas de
cron. Si aparece una referencia a el en un runbook o en un cron, esta muerta.

    /home/ubuntu/neutral-paper/
      base/                              fuentes que se despliegan
        xrp_neutral_engine.py              engine 15m (convencion same-bar)
        xrp_neutral_engine_paper_1m.py     engine DUAL (1m si el tape esta completo)
        xrp_neutral_audit.py               auditoria known-answer del engine 15m
        neutral_paper_1m.py                runner 1m
      neutral_paper_bot.py               runner 15m (staged)
      deploy_neutral.sh                  instala los 5 pares (15m + 1m), atomico
      install_1m_cron.sh                 instala el bloque cron 1m (idempotente)
      daily_summary.py                   00:05  -> daily_summary.csv
      daily_summary_1m.py                00:20  -> daily_summary_1m.csv
      weekly_report.py                   00:10  -> WEEKLY_REPORT.md
      status_all.py                      estado de los 5 pares, dos tablas
      final_report.sh                    informe final
      <PAR>/                             JUP XRP SOL HYPE SUI
        xrp_neutral_engine.py              engine 15m
        xrp_neutral_engine_paper_1m.py     engine dual
        neutral_paper_bot.py               runner 15m
        neutral_paper_1m.py                runner 1m
        run.sh / run_1m.sh                 wrappers con flock
        xrp_paper_bot_status.json          estado 15m
        xrp_paper_bot_status_1m.json       estado 1m (+ bloque vs_15m)
        xrp_paper_bot_day0.json            baseline Dia-0 (COMPARTIDO)
        xrp_paper_bot_day0_1m_check.json   prueba de que el baseline no se movio
        xrp_paper_bot_events.csv           trades 15m (append-only)
        xrp_paper_bot_events_1m.csv        trades 1m (append-only)
        data/                              klines 15m + 1m + funding

Cron (propio; no toca las lineas de los otros bots). El 1m va un minuto despues
del 15m de cada par, y los pares van 60 s escalonados:

    # 15m
    1,16,31,46 * * * * JUP/run.sh     4,19,34,49 * * * * XRP/run.sh
    7,22,37,52 * * * * SOL/run.sh    10,25,40,55 * * * * HYPE/run.sh
    13,28,43,58 * * * * SUI/run.sh
    # 1m
    2,17,32,47 * * * * JUP/run_1m.sh   5,20,35,50 * * * * XRP/run_1m.sh
    8,23,38,53 * * * * SOL/run_1m.sh  11,26,41,56 * * * * HYPE/run_1m.sh
    14,29,44,59 * * * * SUI/run_1m.sh
    5 0 * * *    daily_summary.py         20 0 * * *  daily_summary_1m.py
    10 0 * * *   weekly_report.py        0 23 7 11 * final_report.sh

Operaciones:

    cd /home/ubuntu/neutral-paper && python3 status_all.py      # ambos registros
    cd /home/ubuntu/neutral-paper && python3 weekly_report.py
    cd /home/ubuntu/neutral-paper/JUP && bash run_1m.sh         # un ciclo 1m

**Los dos runners comparten UN lock por par** (`/tmp/neutral-<PAR>-paper.lock`)
porque ambos escriben el MISMO CSV de klines 15m: dos ciclos concurrentes podrian
intercalar filas y corromper el archivo del que salen los dos registros. Van un
minuto separados, pero un ciclo lento (bootstrap, reintentos REST) debe serializar,
no colisionar. La espera esta acotada a 60 s; si no entra, sale con rc 0 y el
siguiente slot lo recoge, porque cada ciclo es un replay completo.

**Un solo baseline.** El registro 1m NO crea su propio dia-0: comparte
`xrp_paper_bot_day0.json`. Asi la diferencia entre los dos registros es el modelo
de fill y nada mas. `day0_replay_matches` prueba que el prefijo reproduce bit a
bit el `mtm_engine` congelado; si sale `false`, el baseline se movio y los numeros
no son comparables. `tape_isolated` prueba que el tape arranca despues de la barra
de dia-0.

**El registro 15m no es evidencia de fill.** La auditoria del 2026-10-31 mostro
que la convencion same-bar fabrica covers (100% de los trades del bot XRP retirado).
El 1m resuelve por minuto cuando el tape de la barra esta COMPLETO (>= 15 minutos
distintos); un toque en el mismo minuto que la entrada es irresoluble con OHLC, se
CUENTA (`same_minute_touched`) y se PROHIBE, nunca se asume.

**Si `forward_coverage_pct` < 100**, el tape tiene un hueco: esas barras vuelven al
modelo 15m, `forward_coverage_ok` = false y el numero no es 1m. Lo mismo si
`forward_same_bar_covers` > 0 en la ventana forward: quedaria un cover acreditado
por la convencion vieja.

**Si el equity del bot no coincide con el del repo, el primer sospechoso es el
historial de funding.** `funding_covers_bars` en el status lo dice; un historial
truncado cobra cero en las barras viejas y el equity sale mal en silencio.

**Si el status envejece, el cron esta muerto.** Es la falla que dejo los trackers
locales 21 dias sin que nadie lo notara.

Repo (durable):

    code/xrp_neutral_engine.py              engine 15m LOCKED (hash-pinned, no tocar)
    code/xrp_neutral_engine_paper.py        copia byte-identica del engine desplegado
    code/_neutral_1m_build.py               genera el engine dual desde esa copia
    code/xrp_neutral_engine_paper_1m.py     engine dual GENERADO
    code/_neutral_1m_audit.py               auditoria de 12 checks (debe dar PASS)
    code/neutral_paper_1m.py                runner 1m
    code/paper_daily_summary_1m.py          resumen diario 1m

## Requisitos
- Python 3.12, `pip install pandas numpy requests`
- Estructura esperada (rutas absolutas originales):
  - `code/*.py` — scripts
  - `data/binance_klines_1h/*.csv`, `data/binance_klines_1m/*.csv`, `data/binance_klines/*.csv`
- Los scripts usan rutas `C:\Users\Lenovo\...`. En otra máquina, editar las
  constantes `D1H`/`D1M`/`DATA` al inicio de cada script.

## Datos
- CSVs con columnas `open_ts,open,high,low,close,volume` (ms UTC).
- Para refrescar: `code/fetch_*.py` y `extend_1h_all.py` (usan fapi.binance.com).

## Backtests validados (comando → qué corre)
- `python code/cvrmd_backtest.py 1H` — CVRMD-v1.1, BTC/ETH/SOL/SUI 1H + splits 24/25/26.
  HYPE/SPX/XRP: `python -c "import sys; sys.path.insert(0,'code'); from cvrmd_backtest import run,rep,load; ..."`
- `python code/botstrat_backtest.py` — BOT-Strat, 6 símbolos 1H.
- `python code/ffs_engine2.py` vía `ffs_final.py` — FFS-v1 HYPE/SUI 5m + neighborhood.
- `python code/kimi20_run.py` + `kimi20_splits.py` — 20 estrategias Kimi + splits.
- `python code/grid_sweep.py` — sweep de grid neutro (requiere `grid_binance_backtest.py`).
- `python code/revbounce_v40.py` — RevBounceBrk v4.0 + threshold sweep (requiere `revbounce_v30.py`).
- `superew_backtest.py`, `bjbot_backtest.py`, `ofp70_backtest.py`, `mdiv15_backtest.py`,
  `revbounce_v20/v22.py`, `cvrmd_scalp_sweep.py`, `flush_study.py`, `retest_study.py`,
  `strict_study.py`, `retest15m.py`, `botstrat_sens.py`, `sui_cvrmd_hood.py`,
  `cvrmd_fixed_validate.py`, `ffs_hood.py`, `ffs_hype.py` — estudios de soporte.
- `python code/ahmad_pro_v2.py all` — port de Ahmad PRO+ v2 (archivado, 0/7 gate).
  Requiere `python3 code/ahmad_fetch_1h.py` primero: las klines 1h ya vienen de 2017
  porque el EMA200 semanal necesita ~200 semanas de warmup.
  `ahmad_selfcheck.py` (21 checks de fidelidad, corre en ~2 min) debe dar ALL PASS
  antes de creerse cualquier número de `ahmad_pro_v2.py`.
- `python code/donchian_ao.py sig` — port de Donchian+AO (archivado, no bate al
  pasivo). 6 variantes: current/prior band x band-exit/ATR-stop x 2-sided/long-only.
  `donchian_ao_selfcheck.py` (23 checks) debe dar ALL PASS antes. El veredicto
  final está en `donchian_ao_bench.py` (estrategia vs buy&hold, DD-matched) —
  un PF > 1.2 sin superar al pasivo no cuenta.
- `python code/cvrmd_port.py check` — port de CVRMD-v1.1 (swing) y
  CVRMD-Scalp-v1.1, ambos archivados. `check` valida el motor de señales contra
  `cvrmd_backtest.py`: con `--div oneshot` las series deben salir byte-idénticas
  en SUI/ETH (`cvrmd_align.py` lo imprime). OJO: los Pines usan `EMA(delta)`
  (`--cvd ema_delta`, el default) y el port validado usa `EMA(cum(delta))`
  (`--cvd ema_cum`) — **no son la misma estrategia**, la diferencia vale 11pp en SUI.
  `cvrmd_scalp_diag.py` muestra que el filtro dead-market [S-5] del scalp es
  aritméticamente imposible en perps (pide ATR >= 2.7% en una barra de $100).
  El `cvrmd_backtest.py` validado en STATUS.md es la versión buena; no la
  borres ni la reemplaces por el port del Pine.

## Costos modelados (medidos, no conservadores — 2026-10-25)
- Direccionales: **5bps fee + 0.5bps slip por lado = 11bps RT**, medido en libro
  vivo (spread 0.77bps, impacto $10k 0.4-2bps). El preset 6+5 = 22bps queda solo
  como sensibilidad. Por simbolo: `results/cost_model_2026-10-25.json`.
  Los constructores de `cbpack_engine`/`cbpack_funding_engine` conservan su slip
  2.0 de auditoria (SHA-256); el coste se inyecta desde `vrun`/`_cbpack_gates`.
- Grid: maker 0.02% / taker 0.05%. USDC-M promo: maker 0% + taker 0.04% (verificar vigencia).

## Criterios de validación (no negociar)
- PF ex-costos > 1.2, comisión/bruto < 30-40%, verde en ≥2/3 años,
  neighborhood estable, n ≥ 30. OOS PF < 1 = kill, sin rescates.

## REGLA 0 — ningún número sin artefacto (harness `code/vrun.py`)
Contra el incidente del 2026-10-10 (un informe de backtest inventado en prosa,
sin corrida). Todo resultado debe salir de un artefacto persistido y verificado.
Ver `VALIDATION_PROTOCOL.md`.

```powershell
python code\vrun.py run    --strategy sax --tf 1h --symbol ETHUSDT
python code\vrun.py render <run_id>     # los números salen SOLO del artefacto
python code\vrun.py verify <run_id>     # re-corre y exige reproducción bit-for-bit
python code\vrun.py matrix --strategy sax
python code\vrun.py show
```

`run_id = sha256(engine + params + datos)`. Si algo cambia, cambia el id.
`verify` sale con código 2 y dice REFUSED si no reproduce. Toda tabla debe citar
su `run_id` y la ruta del artefacto; sin eso, no es admisible.

## Datos 1m profundos (2026-09-26)
`data/binance_klines_1m/` tiene 10.4M barras / 549 MB / 45 meses (BTC, ETH,
XRP, SOL), 41 (SUI, listó 2023-05) y 16 (HYPE, listó 2025-05). Detalle y
verificación en `data/binance_klines_1m/README.md`.

```bash
python code/cvrmd_fetch_1m.py --status                          # ver qué hay
python code/cvrmd_fetch_1m.py --symbols BTCUSDT --from 2024-01   # extender
```

Usa los ZIP mensuales de `data.binance.vision`, no el REST API (1 request/mes
en vez de 350 con rate limit). Merge idempotente por timestamp; re-correr es
seguro. Detecta el mes de listado del perp por búsqueda binaria, así que un 404
por "todavía no existía" no se confunde con un error.

**Para 5m/15m no hace falta bajar más TF:** `cvrmd_port.resample(bars, N)`.
Ojo: SPX solo tiene 3 meses, ningún test multi-año sobre SPX es válido.

**CVRMD en 15m está PROBADO Y DESCARTADO** — ver STATUS.md. No reintentar con
estos parámetros; el problema es resolución del setup (MFE 0.4-1.4R vs TP2 en
2R), no costo ni símbolo. Este dataset queda igual para cualquier otro
trabajo en TF bajos.

## TradingView (solo eyeball, no números)
CDP en 127.0.0.1:9222. El MCP no está en el toolset de Hermes, así que se llama
por stdio con `node tv_call.js <tool> '<json>'` desde
`claudeverstradingview-main/claudeverstradingview-main/`. Detalle, tools que
fallan y trampas de la UI en español: `HERMES_ACCESS.md` de ese repo.

- Validar Pine SIN tocar el editor: `node tv_call.js pine_check '{"source":"<código>"}'`
  → `compiled / error_count / warning_count`. Es el único check fiable.
- La cuenta free solo da ~9 meses de 1H y recorta en silencio: `chart_set_visible_range`
  pide 2022 y devuelve 2026. El strategy tester no puede validar multi-año.
- Para métricas del tester hay que leer el DOM:
  `node tv_call.js ui_evaluate '{"expression":"document.querySelector(\'[class*=\\\"backtesting\\\"]\').textContent.slice(0,400)"}'`
