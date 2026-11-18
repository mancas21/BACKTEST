# AGENTS.md — Backtest System

Rules for any agent (or human) working in this repository. These are not
optional. The first rule exists because it was violated: an agent once reported
a full backtest that was never run.

## REGLA 0 — ningún número sin artefacto (the one rule that matters most)

> A number is a result only if a persisted run artifact backs it and that
> artifact verifies. Otherwise it is text and must not be reported.

Use the harness `code/vrun.py`. Never hand-write metrics.

```powershell
python code\vrun.py run    --strategy sax --tf 1h --symbol BTCUSDT
python code\vrun.py render <run_id>      # numbers come ONLY from the artifact file
python code\vrun.py verify <run_id>      # re-runs; REFUSED unless bit-for-bit identical
python code\vrun.py matrix --strategy sax
python code\vrun.py guard  --report report.md   # rejects unbacked numbers
python code\vrun.py show
```

- `run_id = sha256(engine_bytes + params + [(data_path, data_sha256, bars)])[:16]`.
  If the engine, the params or the data change, the id changes.
- **Data cuts (run_id generation 2, 2026-11-06).** Data files are append-only and
  grow, so full-file hashes went STALE for the whole corpus on every append
  (1,280 stale after one extension). New artifacts freeze a `core.cut_ts` (UTC,
  default = creation day) and hash only the bytes BEFORE it: kline CSV rows with
  `open_ts < cut_ts` (byte-exact prefix; the taker CSVs' blank CRLF lines are
  skipped by the search but hashed), funding JSON records with `t < cut_ts`
  (canonical serialization). The engine is SERVED that same slice from a temp
  dir under the original basename, so the hash covers exactly the bytes the
  engine read. **An append can no longer stale an artifact**; STALE means an
  edit inside the cut, a changed engine, or changed params. Legacy artifacts
  (no `cut_ts` in core) keep the full-file comparison — the museum is not
  migrated. `--cut-ts <ISO>` pins an instant (reproduce an old window:
  max(input end)+1s), `--cut-ts full` restores legacy hashing for one run.
  Selftest: `python code/_cut_hash_selftest.py`.
- **Fast layer (2026-11-06).** `bt.py` is the staged idea→verdict pipeline
  (screen gates → WF → neighborhood → stats → report + `guard --strict`, each
  stage only for survivors, early stop when a stage empties; plans in
  `results/bt_plans/`). New adapters start from `code/adapter_template.py`
  (checklist inside: port → known answers BEFORE real data → register → run →
  gates → guarded report). `matrix`/`neighborhood` take `--workers N` (>1 =
  process pool, same artifacts and order as sequential); `pverify`/`pmatrix`
  remain the batch-parallel forms; `verify` of a single artifact stays
  sequential (the engine run is one job — there is nothing to fan out).
- **Alternative data source (`data_dir`, 2026-11-11).** A param that re-points
  an adapter's input at another directory: `make_artifact` replaces every input
  with `<data_dir>/<SYMBOL>_<TF>.csv` and DROPS what does not exist there
  (equities carry no perp funding file; a fixed-universe book ends up with no
  inputs and fails loudly instead of silently reading the crypto file). The
  directory is part of `core`, so a run on another market can never collide
  with the crypto one, and the engine is served the new bytes unchanged — the
  same engine, another market, no edit. The param is stripped before the
  runner sees it (most runners reject unknown params).
  `python code/_equities_sweep.py` is the S&P 500 transfer sweep.
- **Every results table must cite its `run_id` and the artifact path.**
- Run `verify` before publishing. Exit codes: `0` OK, `2` REFUSED (tampering /
  non-reproducible — do not publish), `3` STALE (data bytes changed since the
  artifact — re-run to refresh; not a fabrication), `4` ORPHANED (engine file
  missing from disk, e.g. SAX v3; use `pverify --skip-orphaned`).
- Run `guard [--strict]` on any report file before sending it. `guard` exit code 2 = the
  report contains performance-looking numbers that no artifact contains (`--strict`
  additionally enforces symbol and timeframe context alignment).
- Use `stats <run_id>` for institutional scorecard metrics (Sharpe, Sortino, Calmar,
  autocorrelation, block bootstrap, margin/liquidation buffer).
- Use `stale [--data <file>]` to audit which artifacts are affected by extended datasets.
- Synthetic / illustrative / hypothetical scenarios must be labelled as such
  and carry **no** `run_id`; they are never mixed into a results table.

Details: `VALIDATION_PROTOCOL.md`.

## Adapters (approved engines)

`vrun.py` wraps the existing engines without modifying them:

| strategy key | engine | unit | data |
|---|---|---|---|
| `sax` | `Downloads/sax_engine-claude.py` **(gone — unrunnable)** | symbol x tf | `data/binance_klines*` |
| `cvrmd` | `code/cvrmd_backtest.py` | symbol (1h) | `data/binance_klines_1h` |
| `botstrat` | `code/botstrat_backtest.py` | symbol (1h) | `data/binance_klines_1h` |
| `scalpwave` | `code/scalp_wave_engine.py` (**WAVE_1 scalp pack ported from `Downloads/scalp_wave1_v1.1.0`**; IND-04/06/07a signals; parity vs the original pack in `code/_scalp_wave_parity.py`) | symbol x tf (1m/5m/15m) | `data/binance_klines_1m` + `data/binance_klines_5m` + `data/binance_klines_15m` |
| `xsml` | `code/xsml_engine.py` (**cross-sectional ML book, pre-registered before its first market run**; features from pybroker's indicator engine in `code/xsml_features.py`, fixed-hyperparameter model in `code/xsml_model.py`, repo execution: next-open, stop-first, gap-at-open, funding at real settlements) | bundle (8 perps) | `data/binance_klines_1h` (8 symbols) + `data/xsml_preds.csv` |
| `ffs` | `code/ffs_engine2.py` | symbol (5m) | `data/binance_klines` |
| `mp20` | `code/mp20_report_ports.py` | portfolio (5 names) | `data/binance_klines_1h` |
| `cbot` | `code/cbot/*.py` (10-strategy suite) | symbol (5m) | `data/binance_klines_5m_taker` |
| `cbpack` | `code/cbpack_engine.py` (10 rule-based strategies) | symbol x tf | `data/binance_klines_<tf>_taker` |
| `cbpackf` | `code/cbpack_funding_engine.py` (**same pack, funding charged**) | symbol x tf | `data/binance_klines_<tf>_taker` |
| `xrpneutral` | `code/xrp_neutral_engine.py` (**delta-neutral two-sided grid**) | symbol (15m) | `data/binance_klines_15m` + `data/binance_funding` |
| `xrpneutral1m` | `code/xrp_neutral_engine_paper_1m.py` (**same neutral book, fills resolved on a 1m tape**; GENERATED by `code/_neutral_1m_build.py`, audited by `code/_neutral_1m_audit.py`) | symbol (15m) | `data/binance_klines_15m` + `data/binance_klines_1m` + `data/binance_funding` |
| `top10` | `code/top10_engine.py` (**TOP10 shortlist of the prompts-100 screen**, frozen port; audits `code/_top10_audit.py` + `code/_top10_parity.py`) | symbol x tf (registry-bound ids) | `data/binance_klines_1h` (+ HYPE tail; `JUPUSDT_1h.csv` added 2026-11-01; SUI funding for #95) |
| `hmatrend` | `code/hma_trend_engine.py` (**external "hermes" HMA(34) Trend pack, DECLARED reconstruction** — source code lost, outputs in `code/hma_trend_sources/`; audit `code/_hma_trend_audit.py` + parity `code/_hma_trend_parity.py`) | symbol (1h) | `data/binance_klines_1h` (PEPE via `_1h_taker`; funding where a file exists; XAUUSDT NO DATA) |

### Bots that USED to run on the VPS — ALL RETIRED (2026-11-16)

**There is NO trading bot deployed on the VPS any more.** The VPS (`vps-japan`,
52.195.120.63) keeps only the market-data readers and the scanner. Every
trading bot that used to live there has been removed, and this section is a
tombstone, not a description of anything running.

| bot | que era | donde | que paso |
|---|---|---|---|
| `paper` | el mirror forward de **CVRMD** (pierna `CVRMD-SUI-1H` con `code/cvrmd_backtest.py` + pierna `BOT-ETH-1H`) | `/home/ubuntu/paper`, cron `*/5` | **borrado** el 2026-11-16; su cron ya no existia (el ultimo ciclo fue el 2026-10-31T20:40Z) |
| `mp18` | los dos paper trackers de MP-18 (`mp18_v2_paper.py`) y de S20/S8/S10 (`paper_s20_s8_s10.py`) | `/home/ubuntu/mp18/backtest-system`, cron horario | **borrado** el 2026-11-16 (con sus dos lineas de cron) |
| `neutral-paper` | el libro neutral de 5 parejas (JUP/XRP/SOL/HYPE/SUI) | `/home/ubuntu/neutral-paper/<PAR>/` | **borrado** antes del 2026-11-16 (el directorio y sus crons ya no estaban) |
| `xrp-paper-bot` | el bot XRP de una sola pareja | `/home/ubuntu/xrp-paper-bot` | **retirado y borrado** el 2026-11-04; archivado en el VPS |
| `grid-paper`, `cqb`, `freqtrade` | — | `/home/ubuntu/...` | ya no estan |

**Material archivado (no se borro sin copia).** Lo borrado el 2026-11-16 esta
en el repo, verificado por sha256:
`backups/vps_retired_paper_mp18_20261116T213657Z.tar.gz`
(sha256 `3f959444a88f5070f0d4716e2f68283605619dea14b8b2ee3d292db5ecf28a56`;
la foto del crontab anterior a la limpieza va dentro). El tar del VPS tambien se
borro: la copia vive en el repo.

**Tambien se borraron los snapshots de crontab** que citaban a los bots
(`crontab.bak.20261031`, `crontab.bak.20261116-pre-wipe`,
`backups/crontab_20261104T214737Z.txt`,
`archive/crontab.snapshot-20261114-pre-halt`,
`archive/crontab.snapshot-20261116-pre-retirement`): archivados igual, en
`backups/vps_crontab_snapshots_20261116T214808Z.tar.gz`
(sha256 `3e27c05865911033db3a06ff35b1ae1f7c5422b7f925b375e1ea0613634195ed`).
Verificacion final del VPS: **cero** rastros de `cvrmd`/`mp18`/`paper_live`
por nombre y por contenido en ficheros de texto, crontab vacio. (Las caches de
npm/pip y el binario `watchfiles` dan coincidencias en base64: son falsos
positivos y no se tocaron.)

**Fuentes en el repo.** Los ficheros `code/paper_live.py`, `code/mp18_v2_paper.py`,
`code/paper_s20_s8_s10.py`, `code/mp18_forward.py` y
`code/xrp_bot_status_line.py` son el ARCHIVO de esos bots (el repo es
append-only, no se borran), y cada uno lleva un banner `RETIRADO` en su
docstring. **No hay ninguna tarea programada ni linea de cron que despliegue
ninguno de ellos**, y no deben volver a desplegarse: el veredicto de una
estrategia esta en sus artefactos (`results/runs/`), no en un bot desplegado.

**Lo que SIGUE en el VPS:** `~/scanner-engine` (scanner en el puerto 8090),
`~/paper-monitor*` y `~/paper-monitors*` (monitores de otros libros, de
septiembre, sin relacion con CVRMD ni con MP-18), `~/vps-reader*`,
`~/data`, `~/logs`, `~/results`, `~/archive`, `~/backups`, `~/workspace`. El
crontab del usuario esta **vacio**.

**Y lo que corre en ESTA maquina** (Windows, `C:\Users\Lenovo\trading-engines`,
un repo DISTINTO de este): el recorder de order-flow de ESTE repo
(`recorder/recorder.py`, con su tarea `EDG_recorder_keepalive_15min`), y en
`trading-engines`: `reader_supervisor.py` (lector), `scanner.py` (escaneo),
`bridge_server.py` (puente de TradingView) y
`execution/neutral_bot.py --execute --loop --interval 20`, que es un bot de
**TESTNET** de Binance (su propio log lo dice: "EJECUTANDO EN TESTNET"), con
`ALLOW_ORDERS=1` y `ALLOW_ALPACA_ORDERS=0`. Ese NO es un bot de este repo ni
usa la estrategia `cvrmd`: su docstring dice "Opera TODOS los pares sin sesgo
direccional. No usa estrategias S02-S10".

### La estrategia `cvrmd` en ESTE repo (backtest, no bot)

`cvrmd` sigue siendo un adapter de backtest (`code/cvrmd_backtest.py`, la
validacion CVRMD-v1.1: VWAP de sesion +1sd, pendiente de CVD por CLV,
divergencia de pivotes MACD 12/26/9, SL 1.5x ATR congelado, TP1 = media VWAP,
TP2 = 2R, cooldown 3, riesgo 1 % con tope 3x, 6 bps por lado). Su veredicto
esta en los artefactos y en `STATUS.md`: **CVRMD-ETH 1h esta SUSPENDIDO**
(historia completa PF 1.02, plano) y el edge de SUI/ETH es reciente y sensible
a la muestra. **Lo que se borro el 2026-11-16 fue el BOT que la corria en el
VPS, no la estrategia ni su adapter de backtest.**

El grid del repo (`code/grid_core.py`, "ATR Long Grid") usa CVRMD como senal de
brazo (`cvrmd_longonly.arm_series`); su bot paper era el mismo `paper_live.py`
que se ha retirado.

**Dos lecciones que NO se van con los bots (leelas antes de tocar cualquier
perp):**
1. **EL FUNDING.** El engine `cbpack-1` adjunta una columna `funding_rate` y
   nunca la debita. `funding_attached: true` significa que la COLUMNA se
   adjunto, no que el COSTE se cobro. Un perp paga funding cada 8h sobre el
   nocional abierto. La misma clase de bug ya bitó a un bot desplegado: su
   historico de funding cubria solo 400 dias, asi que las barras iniciales no
   cobraron NADA y el equity estaba silenciosamente mal (`funding_paid` leia
   −49.96 en vez de +266.14). `funding_covers_bars` es el control que lo
   caza. **Un backtest con funding a medias es otro backtest.**
2. **COPIA EL ENGINE AL REPO ANTES DE CORRER.** `Downloads/` no es durable: el
   engine del SAX v3 se borro de ahi y se llevo la verificabilidad de 49
   artefactos. Todo engine que se vaya a ejecutar en este repo vive en
   `code/`, con su sha en el `run_id`.

### `cbpack` does NOT charge funding. `cbpackf` does.

The `cbpack-1` engine attaches a `funding_rate` column and never debits it from PnL.
Its own docstring says: *"No funding payments, no liquidation engine, no partial
fills (state this in any report you produce)."* **`funding_attached: true` in an
artifact means the COLUMN was attached, not that the COST was charged.** A perpetual
pays funding every 8h on the open notional.

Use `cbpackf` for any number that describes holding a perpetual. It is the same pack
through `code/cbpack_funding_engine.py`, which:
- bills funding at the settlement instants (the pack's own `attach_funding()` carries
  the last rate FORWARD onto every later bar — correct for S07's z-score, wrong for
  billing: on 1h data it bills eight settlements for every real one);
- reports per-trade `funding` and a `funding_drag_pp` field measured inside the
  artifact by also running the no-funding engine on the same data;
- reports concentration: `conc_top5_share_pct` (the best five trades as a share of
  total PnL) and `conc_net_without_top5_pct` (the return without them).

**Proven equivalent to the original with funding zeroed:**
`code/_cbpack_funding_parity.py` — known-answer funding cases, per-trade independent
recomputation from the raw settlement column, and a full metric-by-metric comparison.
Re-run it after ANY change to `code/cbpack_funding_engine.py` (the engine is
generated by `code/_build_funding_engine.py`, which patches the original with
literal replacements; each patch must match exactly once or the build aborts).

Standard helper for new engines, all harness-powered:
`code/_cbpack_audit.py` (known-answer execution audit), `code/_cbpack_cost.py`
(zero-cost control), `code/_cbpack_gates.py` (period split + walk-forward + repo
costs), `code/_verify_strategy.py <strategy>`, `code/_assert_report_totals.py`.
Exposed as `cbpack` adapter modes: `mode=full` (default) and `mode=wf`
(`train_bars`, `test_bars`, `ids`).

For the neutral XRP bot: `code/xrp_neutral_audit.py` (known-answer + parity +
causality + determinism + a regression lock on the validated engines),
`code/xrp_neutral_baseline.py` (day-0 reference and the kill criteria),
`code/xrp_neutral_grid.py` (the PRE-DECLARED 12-combination grid),
`code/xrp_neutral_gauntlet.py` (concentration, significance, period split,
out-of-sample with frozen parameters, neutrality),
`code/xrp_neutrality_check.py` (neutral vs long-only vs short-only).
`code/_engine_lock.json` pins the sha256 of the engines that must not change;
the audit checks them.

**A slice is not a window — ask whether it carries a warmup.** `cbot` slices run
`[slice_from - 63 days, slice_to)` so the walk-forward has training history before
the scored region; `cbpack` slices run `[slice_from, slice_to)` with no warmup. Both
are correct for their own artifacts. The trap this creates: a slice clipped by the
start of the data reproduces under EITHER convention, so testing only the first
window of a series cannot tell them apart (STATUS.md, "Third reconstruction gap").

### The EDGE Track-R order-flow recorder — MIGRATED into this repo (2026-10-29)

The sealed EDGE-first research project (`Downloads/EDGE STRATEGY-2-V4-1-CLAUDE`,
audited in `results/edge_folder_audit_2026-10-29.md`) was consolidated into this
repo and the source folder deleted. What lives where now:

- **`recorder/` (repo root) — the LIVE Track R order-flow recorder.** Same
  relative layout it always had (`recorder/data` day parquet, `recorder/coverage`),
  so `recorder.py` runs unmodified: `ROOT = parent.parent` resolves to the repo
  root. Streams: bookTicker, depth@100ms diffs + REST snapshots, and the
  all-market `!forceOrder@arr` liquidations — the three stream types with NO bulk
  archive (aggTrade/kline/markPrice are re-downloadable from data.binance.vision
  and were deliberately dropped). Keepalive: scheduled task
  `EDG_recorder_keepalive_15min` + Startup-folder `EDG_recorder_keepalive.vbs`,
  both repointed here; interpreter is the system Python 3.12 (pyarrow + websockets).
  R_READY bar: 56 valid UTC days of continuous recording → earliest forward
  verdict ~December 2026. `funding_covers_bars`-style honesty applies: check
  `recorder/coverage/coverage_live.json` before quoting anything built on it.

  **Three live defects were fixed on 2026-10-29, and one limit cannot be fixed.**
  Fixed, each one measured before and after: (1) two recorders were writing the
  same files at once (pids 17976 from the deleted venv + 7460 from system
  Python) because the scheduled task and the Startup launcher could both pass the
  "not running" check in the same second — now a named mutex
  `Local\EDG_recorder_keepalive` wraps check-then-start; (2) `recorder.py`
  rewrote `recorder_started_utc.txt` on every restart, pushing the 56-day
  milestone to "today" each time — now written once (the file still reads
  2026-10-29T14:36:02Z); (3) `pyarrow.ParquetWriter` opens in WRITE mode, so
  every restart TRUNCATED the current UTC day (2026-10-28 = 13.9 MiB against
  244.8 MiB on 2026-10-25) — now an existing day file is rotated to
  `{stream}.prev{HHMMSS}.parquet` instead. The limit: the recorder cannot record
  while the machine is asleep or off, and it was (2026-11-01T01:42Z to
  12:52Z, no keepalive log line in between), so `R_READY` counts VALID days and
  an overnight gap voids them. Read `recorder/keepalive.log` before quoting any
  R_READY arithmetic, and read the `*.prev*.parquet` segments too — a day can be
  split across several files and `{stream}.parquet` alone is NOT the whole day.
- **`edge/` — the whole sealed v4.1 + v6 project** (engine, amd_engine, tests,
  tools, dossiers, specs, ledger, figures, results, reports). Its verdict is
  TERMINAL: pre-registered, batch A and B zero survivors, the one sealed OOS
  read failed its cluster-t gate, v6 stopped at P1, AMD reversal negative before
  costs. Do not re-run it expecting a different verdict (same rule as the packs).
  Git history: `backups/edge_project_git_history_2026-10-29.bundle`.
- **`data/edge_panel/` — the one-minute kline + funding panel.** MEASURED on
  2026-11-01: 82 parquet, 1,082 MiB, of which **31 symbols** carry
  `*_klines_1m.parquet` and 31 carry `*_funding.parquet` (581,760 one-minute bars
  each, 2025-09-01..2026-09-30, with the taker columns). The "41 symbols" figure
  in the earlier version of this file was the project's candidate UNIVERSE, not
  what is on disk — do not quote forty-one. The 25-symbol import into
  `data/binance_klines_{1h,15m}_taker/` was made by `code/convert_edge_panel.py`
  with sha manifest `data/EDGE_V41_IMPORT.json` (25 imported, 6 skipped because
  the repo already had them: BTC, ETH, SOL, SUI, XRP, HYPE). Those taker CSVs are
  RESAMPLED from one source, not independent downloads — cite the manifest in any
  campaign built on them. Duplication check `code/_find_duplicate_data.py` found
  **zero** byte-identical files across `data/` and `recorder/data` (463 files,
  4,789 MiB hashed), so the panel and the taker dirs are near-copies of the same
  market, never copies of the same bytes.
- The EDGE families join the killed list: funding-carry XS, premium-z reversion,
  short-rich-into-settle, XS momentum (terminal after the sealed read),
  OI-collapse reversion, capitulation burst, 1m BTC lead-lag, CVD continuation,
  absorption, AMD reversal. Their measured all-in taker RT cost wall
  (mid-twelve bps, symbol-dependent) agrees with this repo's eleven-bps block.

## Sources of truth

- **Binance CSVs (`data/binance_klines*`) = the only market data.** Everything is
  computed from these bytes; their SHA-256 is part of every `run_id`.
- **`SPXUSDT` is NOT the S&P 500 (2026-11-11, measured).** It is a Binance
  perpetual whose base asset is `SPX`, a crypto token: the daily-return
  correlation with the real SPY series over the overlap is **0.31**, while the
  correlation of SPY with QQQ is **0.95**. The repo's 52 `SPXUSDT` rows are
  not index exposure. The genuine S&P 500 in this repo is
  `data/alpaca_1d/SPY_1d.csv` (real Alpaca daily bars, 2,722 sessions from
  2016), with QQQ alongside it; the equities campaign runs through the
  `data_dir` override, see `results/equities_transfer_2026-11-11.md`.
- **TradingView = eyeball only. Never numbers.** The free account returns ~9
  months of 1H and silently truncates, so the strategy tester cannot validate
  multi-year. Use `node tv_call.js pine_check` for syntax, nothing else.
- **Synthetic / GBM / author-reported figures are not evidence.** If a spec ships
  numbers, treat them as unverified until reproduced by the harness.
- **Funding files are coverage-audited, and verify binds id to content**
  (2026-11-01, adopted from the external qbt audit): `code/datacheck_funding.py`
  → `data/FUNDING_MANIFEST.json` checks every `data/binance_funding/*.json`
  against every kline window — a short funding file means early/late bars were
  charged NOTHING (JUP 1h: the first ~243 days of bars carry no funding; BTC 1h:
  ~1.6 head days). Read the manifest before citing any funding-sensitive number.
  `vrun verify` now refuses any artifact whose stored `core` does not hash to its
  `run_id`, and `code/_verify_id_binding.py` sweeps the corpus (all artifacts
  bound as of the 2026-11-01 sweep). Gate policy v2.1 adds **G11** (win-rate ≥
  75% must sit ≥ 5pp over the breakeven win rate) — see `GATES_AND_RULES.md`.

## Validation criteria (not negotiable)

**READER NOTE (2026-11-06):** the battery below is the SCREEN floor. The full
gate battery is v2 (`GATES_AND_RULES.md`, G1–G11: n ≥ 100 for the full
verdict, expectancy Ljung-Box, walk-forward folds, cost < 30%, win-rate
breakeven G11, null calibration) — anyone judging a candidate applies THAT
battery, not the screen floor alone; the two documents are meant to be read
together and GATES v2 states which numbers supersede these.

- PF ex-cost > 1.2; commission/gross < 30–40%; n ≥ 30 closed trades;
  green in ≥ 2/3 years; neighborhood stable; walk-forward / OOS holds.
- **OOS PF < 1 = KILL.** No rescue loops, no window-picking, no parameter
  fishing to revive a dead result.
- A strategy that only wins by losing less than a collapsing market is not alpha
  (compare vs buy & hold).
- Costs: directional 5 bps fee + 0.5 bps slip per side = **11 bps roundtrip**
  (measured 2026-10-25 on live books: Binance/OKX/Bybit/Kraken spread 0.77 bps,
  $10k impact 0.4-2 bps, tier-0 fee 5 bps). The old 6+5 = 22 bps preset stays as
  a sensitivity only, never as the gate. Per-symbol measured RT (10.0-30.5 bps)
  lives in `results/cost_model_2026-10-25.json` — use it for thin names.
  Grid maker 0.02% / taker 0.05%.
  Where it is enforced: `code/vrun.py` defaults `fee_bps=5.0 / slippage_bps=0.5`,
  `code/_cbpack_gates.py` `REPO_FEE=5.0 / REPO_SLIP=0.5`, and the scanner's
  `backtest_link.REPO_COST_RT_BPS=11.0` (an artifact is only admitted if it
  declares exactly 5.0 / 0.5 / 11.0). The `BacktestConfig()` constructor of
  `cbpack_engine.py` / `cbpack_funding_engine.py` keeps its audited default of
  2.0 bps slip on purpose: the audit pins those files by SHA-256 for zero-funding
  parity, so the cost is injected by the caller, never by editing the engine.

## Porting a Pine script (mandatory before trusting any number)

1. Port the signal logic to Python; keep the Pine's constants and execution
   conventions (entry at next open, SL-first on ties, fees on every fill).
2. Run a parity / self-check against the Pine or a dual engine; require ALL PASS.
3. Only then run through `vrun.py` and report with a `run_id`.
   Ports that "return zero signals" are usually a silent bug (see STATUS.md:
   `ta.pivothigh` is not `rolling_max`; pandas tz-aware `astype("int64")` is
   unit-dependent and broke session grouping) — assert, don't assume.

**When the source is ALREADY Python (a foreign pack), the same rule applies to
the SIGNAL, not to the strategy.** A pack that emits signals is not a strategy:
it has no positions, no sizing, no PnL. Porting it means choosing and
DECLARING the execution conventions (fill bar, tie rule, gap rule, sizing,
costs, one-position-or-not, multi-signal priority) and then measuring them.
The proof chain that the repo expects, in order:

1. **Parity with the original** — import the source pack as a second engine
   and require its indicator columns and its signal event set to match on REAL
   data (`code/_scalp_wave_parity.py` for the WAVE_1 pack: 25/25 PASS, rtol
   1e-9 on 39 columns, identical event sets). Parity proves the SIGNAL; it
   proves nothing about the execution you added on top.
2. **Known answers for EVERY execution rule, in BOTH directions.** The
   WAVE_1 port shipped long-only tests and missed a short-side fee bug for a
   whole campaign; the tests now cover long and short, target, stop,
   stop-first tie, gap-through and end-of-data, plus a sizing case on an
   EXPENSIVE asset (a stop-out must risk ~1% of cash whatever the price is —
   a position sized as `cash*risk/stop/fill` risks 1/price of the budget and
   looks like a strategy that simply does not trade).
3. **An accounting invariant asserted INSIDE every artifact**:
   `eq[-1] − INIT == sum(pnl)`. It is what catches a fee charged on the wrong
   side, and it fails loudly instead of producing a plausible-looking PF.
4. **The PF you publish is EX-COST.** If the trade PnL excludes fees while the
   equity curve includes them, a family can show a PF above one and still
   lose money. (Both defects above were found by exactly this discipline.)

## Do / Don't

- **Do** keep `run_id` next to every metric; keep artifacts in `results/runs/`.
- **Do** re-fetch/extend data with the documented scripts; re-verify after.
- **Don't** overwrite or delete files in `results/runs/`, `data/`, `code/`, or
  `backups/` — treat them as append-only records.
- **Don't** present a number whose artifact fails `verify`.
- **Don't** cite the fabricated SAX figures (`+18.42% PF 1.31`, `+19.67%
  PF 1.35`, or the estimated pair x timeframe matrix). Real SAX v3.0 is in
  STATUS.md: **PF < 1 on 31/31 pair x tf combinations — KILLED.**

## REGLA 1 — aislamiento de veredicto (2026-11-06, decisión del usuario)

> Cada estrategia es única y se juzga SOLAMENTE sobre sus propios artefactos.
> Que otra estrategia distinta haya fallado en algo parecido no es evidencia de
> nada sobre esta. Un veredicto que cite el fallo de un hermano está roto.

- **Una estrategia = un veredicto.** El veredicto sale de la batería de gates
  aplicada a LOS ARTEFACTOS DE ESA ESTRATEGIA (PF, n, net, tercios, OOS,
  concentración, bootstrap CI — todo medido dentro de su propio artefacto) y
  de nada más.
- **La kill list es historia, nunca un pre-gate.** La sección "Current kills"
  registra qué se probó y qué salió; NO autoriza a rechazar un porte nuevo sin
  correrlo. Un pariente muerto no condena al nuevo: el nuevo corre y produce
  sus propios números. (Lo que sí sigue prohibido por REGLA 0: citar números
  de otra estrategia como si fueran de esta.)
- **Prohibida la transferencia de fallo.** "La familia X ya falló", "el pack
  murió así que este prompt también", "su primo murió por concentración" —
  ninguna de esas frases puede formar parte de un veredicto. Mencionar el
  contexto como información (con sus run_ids) está permitido; deducir el
  veredicto del contexto, no.
- **Reglas y costos declarados, iguales para todas.** La batería estándar y el
  régimen de costes (11 bps RT repo + funding real donde exista) se aplican
  igual a cada estrategia y se IMPRIMEN en cada veredicto. El comando único es
  `python code/bt.py one --strategy <s> --tf <tf> --symbol <sym>`: un
  artefacto, una batería, un veredicto, cero comparaciones con hermanos.
- **La incertidumbre es propia, no heredada.** Lo que sustituye a los haircuts
  entre hermanos es la incertidumbre DE LA PROPIA estrategia (bootstrap CI de
  su serie de trades) y, cuando se pida, su propio null de entrada aleatoria
  (`vrun nullgate`/gatecal) — ambos internos al artefacto. El conteo
  program-level de trials se puede registrar como dato, pero no modifica el
  veredicto individual.

## Current kills (from STATUS.md — read it for the full list)

- **9-21 EMA crossover (2026-11-17 attachment; adapter `ema921`, 101 cells: 8 at 1m, 10 at 5m, 35 at 15m, 37 at 1h, 11 at 1d): KILLED — zero cells pass the battery, and the loss pattern is turnover, not a misplaced constant.** Source of record `code/ema921_source.py` byte-identical to the attachment (sha `8be0020d…`); port `code/ema921_engine.py` keeps the source's rules verbatim (EMA9/21 SMA-seeded, signal on close, next-open entry, 10-bar swing stop, 2R target, slow-EMA cross exit, 1% risk, 5x cap) and adds only the repo regime (11 bps RT, funding at real settlements, window trimmed to the funded span at both ends, `eq[-1]−INIT == sum(pnl)` asserted inside every artifact, zero-cost and no-funding controls measured inside each artifact). Audit `code/_ema921_audit.py` 46/46 PASS in both directions (it caught a real pandas-3 unit bug pre-market: the index came back in µs, `asi8 // 1e6` produced SECONDS, and the funding trim ate 62,686 of 62,687 bars); parity `code/_ema921_parity.py` 4/4 cells bit-identical (BTC 1h, ETH 15m, SUI 5m, XRP 1d) under the source's own 4/1 bps with funding off. Grid via `code/_ema921_matrix.py`; 101 artifacts verify bit-for-bit. **Only two cells reach full-window PF>1.2 with n ≥ 30 and both die on significance and on B&H:** LABUSDT 1h `dfab81a68433a1fd` net +28.44%, PF 1.270, OOS PF 1.558, thirds 3/3, bootstrap CI [−1.950, 18.696], B&H −83.22% (wins by losing less); ZECUSDT 1h `d620f41a9ece082a` net +33.06%, PF 1.262, OOS PF 1.324, CI [−1.297, 18.243], B&H +2884.79%. The zero-cost control shows the gross edge is real but tiny and the turnover eats it: at 1m ONE of eight cells is above 1.0 before costs (SPXUSDT `67d8a9a9cd843510`, 1.022) and ETHUSDT 1m `1e231a62c3ecc4d9` runs PF 0.134 on 83475 trades; 5m 6 of 10 above 1.0 and none at 1.2; 15m 15 of 35 above 1.0, none at 1.2; 1h 25 of 37 above 1.0 and 5 at 1.2. BTCUSDT 1h `61da2863c36f44da` pays 14588.02 USDT in fees on 2812 trades (PF 0.891 with costs vs 1.082 without); SOLUSDT 15m `abc036cc36e2849c` pays 39109.08. Funding is charged everywhere (`funding_covers_bars` true on all 101; largest drag AVAXUSDT 1h `24b242051b5957a7` −1.97 pp; some shorts RECEIVE, LABUSDT 1h −11.99) and never changes a verdict. **1d is NO VERDICT, not a win**: the daily files start in 2026 by construction, no cell reaches thirty trades. Report `results/ema921_report_2026-11-17.md` (guard OK strict, 101 run_ids cited), matrix `results/ema921_matrix_2026-11-17.json`, registry family `trend_ema_crossover`. Registry bookkeeping fix shipped with it: `code/_top100_rank.py` now drops sub-10-trade artifacts BEFORE the per-cell dedupe (a zero-trade pre-fix run had return 0.0 and shadowed the real 2812-trade BTC 1h cell).

- **External "hermes" HMA(34) Trend pack (2026-11-14; adapter `hmatrend`, 12 pairs 1h from a foreign CLI session's scratch JSONs): KILLED — zero of 11 measurable cells pass the screen battery, AND the external claim is UNREPRODUCIBLE FROM ITS OWN OUTPUTS.** The source engine's code did NOT survive (only output JSONs, byte-identical in `code/hma_trend_sources/` with MANIFEST, all sha-bound into every run_id). MEASURED from its own trades: next-open fills (247/247), stop = entry − 3.0×ATR(14 Wilder @ signal bar) exact (18/18), ZERO fees, ZERO funding on perps, long-only, full-equity compounding, pct-weighted PF (money-weighted 2.1709 vs published 2.2533), one ~38-day OOS slice per pair (NVDA/SPCX shifted windows), 5 of 12 pairs already losing to B&H at zero cost. DECLARED (not recoverable): the exact exit predicate — no candidate family separates the 229 exit bars from the 2970 hold bars; frozen spec = entry HMA(34) rising, exit HMA falling, the pack's own label. On the pack's OWN bytes the declared book reproduces the trade count (292 vs 247) and hold profile (12.7 vs 12.9 bars) but NOT the return (+86.4% vs the claimed +890.5%, PF 1.18 vs 2.25). Repo battery (full history, 11 bps RT, funding at real settlements, zero-cost control inside each artifact): PF ex-cost 0.6883–1.0128, OOS PF 0.7470–1.1074, bootstrap CI negative on all eleven cells; JUPUSDT `30ef63651b4760db` net −69.26% PF 0.9056 (912 trades) with zero-cost −20.09% PF 0.9798 — the signal loses at zero cost too (antipredictive on the full window, not a cost kill); funding_paid is NEGATIVE −206.76 (the long book RECEIVES: JUP funding ran negative over 2026). XAUUSDT NO DATA (no file anywhere under data/). Report `results/hmatrend_report_2026-11-14.md` (guard OK strict, 22 artifacts verify bit-for-bit, `results/_hmatrend_verify.txt`); claim + parity numbers carried INSIDE the hermes artifacts (`claim_*`, `parity_*`) so the report cites only artifact-backed numbers. Engine audit `code/_hma_trend_audit.py` 16/16 PASS (caught two real engine defects pre-market: ATR-warmup self-stop, entry-fee pnl basis); parity `code/_hma_trend_parity.py` 12/12 PASS. Adapter registered with `card_from_symbol` (engine reads `card`), PEPE 1h resolved from the taker dir by `_hmatrend_input`.

- **STRATEGIES 101-150 pack (2026-11-13 attachment; adapter `s101`, 37 of 50 prompts runnable, 13 NO-DATA skips per the pack's own rule #19): KILLED — zero of 37 cells pass the screen battery; the dominant pattern is intraday cost ruin.** Sources of record byte-identical (`code/prompts_101_150.txt`, sha `ba1b3491…`); engine `code/s101_engine.py` over the audited p100 `Book` (signal on close, enter next open, stop-first, repo 11 bps RT, 0.5% risk/trade, the pack's daily counters — 3 losses/day and 6 trades/day on 1m-3m, MEASURED binding after a day-bucket unit bug was fixed: the constant was 8.64e10 ns instead of 8.64e13, so the caps never accumulated), funding at real settlements for the perps (NVDA/SPCX none, declared), 70/30 chronological. Screen via bt.py: thirty-seven artifacts verify bit-for-bit (`results/_s101_verify.txt`); report `results/s101_report.md` (guard OK strict); pre-registration `results/s101_pre_registration.md`. Headline cells: 101 BTC 5m structure-retest `e7b92b1b89d5f276` net -100% (PF 0.14, 5207 trades); 103 BTC 1m failed-breakout `5f7997379c6c67b2` net -100% (PF 0.02); the pairs 117/118 (SOL/BTC cointegration `b3d22f048e9805dd`, SOL/ETH spread `34f5f0a4b8f84155`) net -100% PF 0.28/0.15 — mean-reversion pairs join the measured cost-wall families; best cell 138 JUP 15m stop-run `46a8ce34bf84ad03` net -12.65% PF 0.868 — still fails; 128 (wick >= 2 ATR) measured dead by construction: zero trades in the window, declared as the prompt asked. NO-DATA: 111/113/114/132/136/137/142/143/145/146/147/148/149 (liquidations, OI, spot ETH, calendar, ticks, order book, NVDA 1m, SMH, SPCX 1m, SPY, VIX, breadth). **PIPELINE FIXES shipped with this campaign:** pre-flight validator `code/_s101_preflight.py` (37/37 cells on 60-day slices in minutes — catches every port-bug class that caused the three failed 86-min screen passes of this session before any long run), bt.py `_metric` now tolerates dict-form tables (one line), and the input-resolution helper `_s101_input` in vrun resolves 1m to the TAKER dir first (the native/taker 1m basename collides in the gen-2 cut slice).

- **ICT 4H FVG → 15M FVG with 1m intrabar resolution + DST sessions (adapter `fvgup`, attachments 2026-11-13): KILLED — zero of four cells pass the screen battery.** Sources of record byte-identical (`code/fvg_system.py` + `code/fvg_upgrades.py`, second one sha-pinned `8b46d5bd…`); adapter engine `code/fvgup_engine.py`; pre-registration `results/fvgup_pre_registration.md` (with a dated addendum); report `results/fvgup_report_2026-11-13.md` (guard OK strict), four artifacts verify bit-for-bit. Window = the 1m coverage (2023-01..2026-10); repo costs injected by the caller; funding = the pack's constant-rate model (declared approximation). **BTCFINE** `7dfd3c4de2f6765e`: net -0.59%, PF ex-cost 2.6627, n 28 (under the floor), top-5 171.99% of PnL, loses to B&H +405.99%. **BTCCOARSE** `7924a180df2bbb96` (declared NOT certifiable comparison): net -0.90%, top-5 201.59%. **BTCNOSESS** `bc3d3dc1af3fcd47`: net -19.29%, PF net 0.7354, OOS PF 0.5199 — the sessions ablation shows the pack's session filter removes the losing hours (without them the book bleeds), but the filtered book still fails. **ETHFINE** `fdf4391a289b3fd6`: net -3.73%, PF net 0.8604. The gross edge is real (PF ex-cost 1.56-2.66) and the 11 bps regime consumes it — same pattern as the rest of the corpus. **PACK DEFECTS MEASURED (for the author):** (1) the pack's own dual-engine parity FAILS on BTC (vector 27 vs event 28; one event-only long, bull zone 323, filled 2024-09-11 08:30 UTC — the two engines disagree on zone re-arm semantics; a one-line invalidation-reset patch was tried and did NOT resolve it, reverted) and PASSES on ETH; every artifact publishes `parity_ok` + the divergence trade-by-trade. (2) pandas-3.0 unit bugs: FineData's 1m window mixed us datetime ints with a ns Timedelta int (window 1000x wide, fine silently dead — fixed by the generated `code/fvg_upgrades_portfix.py`, builder sha-pinned) and `to_datetime(unit="ms")` keeps an ms index against the pack's ns arithmetic (zero fills — fixed in the adapter by normalizing indexes to ns). (3) the pack charges the ENTRY fee outside the trade pnl and funding outside pnl — the repo invariant was reformulated and closes to the cent (`pnl_identity_resid`). The 1m execution-fidelity claim WORKS after the port fixes: ~131k bars resolved on the 1m tape, stop/target ambiguity 6 -> 0.

*Historical record only. Per REGLA 1 this list never pre-condemns a new
strategy: a new port runs and is judged on its own artifacts, and these
entries are context, not verdicts.*

- **`xsml` — cross-sectional ML book on 1h perps (2026-11-11): KILLED — the forecast correlates out of sample and the book still loses. AND A LEDGER DEFECT FOUND AND FIXED.** Adapter `xsml`, engine `code/xsml_engine.py`, PRE-REGISTERED before its first market run (`results/xsml_pre_registration.md`: thesis, ten declared features, a fixed-hyperparameter model with no grid and no model selection, the DEV/OOS split with a 24-bar purge/embargo, the gates and the risks, all frozen). Universe: the eight perps that carry BOTH 1h klines and a real funding file (BTC, ETH, SOL, XRP, SUI, ARB, JUP, HYPE) — on a perp, funding is not optional. Features come from pybroker's INDICATOR engine with NO backtester involved (`code/xsml_features.py`); the model is a single `HistGradientBoostingRegressor` fit on DEV (`code/xsml_model.py`); the EXECUTION is the repo's, not pybroker's: next open, stop first on ties, gap-through at the open, stop and target at twice the ATR, 11 bps round trip per leg, and funding charged at the real settlements on both legs. **The variant campaign (V2..V5) plus the two readings of the turnover that the frozen spec leaves open is `results/xsml_variants_report.md`: twelve artifacts, all verifying bit-for-bit, guard OK strict.**

  **THE DEFECT (the part worth remembering).** Engine version 1 multiplied by `side` a quantity that was ALREADY SIGNED (`qty = side * notional / fill`), so every short leg was booked as a mirror-long and its fee was CREDITED instead of charged. The repo's own accounting invariant caught it — but the engine did not ASSERT it, so the book ran and published a plausible-looking number. The residual was 1689.65 USDT, exactly four commissions for each of the 507 short trades. The first artifact (`a2fc128ff0f42f5d`) and its report are **WITHDRAWN**: they published a mis-accounted book. The engine now asserts the invariant INSIDE every artifact and publishes the residual (`pnl_identity_resid`); the known-answer suite `code/_xsml_engine_audit.py` (32/32 PASS) covers the SHORT side on every rule — fill, PnL, stop-first, gap, funding sign, invariant — because WAVE_1 already paid that bill once ("long-only tests and missed a short-side fee bug for a whole campaign"). The corrected base book is `d5cefbaf8e3dcb85` (turnover `full`): net -20.75%, PF ex-cost 0.8969, 1116 closed trades, win rate 50.2%, max DD -29.3%. **The zero-cost control is POSITIVE but marginal (+1.16%), so this kill is a cost-regime kill meeting a weak-but-real forecast** — and the forecast correlation with the label ON THE TRADED WINDOW is 0.1484 (measured inside the artifact). The `keep` reading of the turnover, declared before it was run (`results/xsml_turnover_pre_registration.md`), gives net -16.40%, PF 0.9162, zero-cost +3.77%: the conclusion is ROBUST to the ambiguity — all twelve cells have OOS PF below one.

  **WHAT THE VARIANTS SAID (twelve artifacts, five books by two turnover readings).** V2 (label aligned with the realized payoff) is WORSE than the base (-33.60% full, PF 0.8381) even though its forecast correlation is HIGHER (0.2006): the label was not the bottleneck. V3 (72-bar horizon and rebalance, three times fewer turns) is the least bad (-5.62% full, PF 0.9236, zero-cost +0.88%) — as expected when the cost is the problem, but still below break-even. V4 (asymmetric reward:risk, stop 1x ATR and target 3x ATR) has the WORST profit factor of the twelve (0.8116 full, win rate 27.0%): fixing the reward:risk does not fix a small edge, it amplifies it the wrong way. The one that loses most in absolute terms is V2. V5 falsifies H0 in BOTH readings: the long leg loses and the short leg loses, so the neutral book is not measuring the wrong side — the rank has no operable content. The line closes here: no fifth variant.

- **WAVE_1 scalp pack, ported from `Downloads/scalp_wave1_v1.1.0` (2026-11-11): KILLED — zero of twelve cells pass, and the loss is NOT a cost effect.** Adapter `scalpwave`, engine `code/scalp_wave_engine.py` (the pack's own signal logic copied into the repo, because `Downloads/` is not durable), four kline-only indicators on Binance USD-M 1m–15m (IND-04 session VWAP ±σ reversion, IND-05 regime gate with no events, IND-06 liquidity sweep, IND-07a squeeze/burst). Repo costs (5 bps fee + 0.5 bps slip per side, charged on entry AND exit); funding NOT charged (the pack is kline-only with no funding input — a declared limit). Twelve cells: SOL/SUI/HYPE at 5m and 15m on the full repo history plus 1m on the pack's own declared twelve-month window, with BTCUSDT as the pack's context symbol; LINKUSDT could not be measured (no 1m/5m/15m file in this repo). Every cell loses: PF ex-cost 0.6644–0.8624, and ALL TWELVE also lose at ZERO cost, so no fill model rescues it. Per signal family (the pack analyses families separately): of ninety-six family×cell combinations, ONE reaches PF 1 — IND-04:VWAP_EXT_DN on HYPEUSDT 5m, PF 1.0059, net +3.08%, n 1018 — the maximum of ninety-six draws and far under the repo's 1.2 gate. Sensitivity probes fail too: the pack's own declared cost gate gives PF 0.7715 on SOL 5m (`b5508330cf8436d2`) and 0.8121 on SUI 5m (`fd8301a9c82108cd`), and the IND-05 regime filter gives 0.7830 (`a3ba999fbaa607f5`). Report `results/scalpwave_report_2026-11-11.md` (guard OK strict, fifteen artifacts cited); the fifteen artifacts of the current engine verify bit-for-bit. The port's own audit found and fixed THREE defects that would all have produced plausible-but-wrong numbers (a short's exit charged `(1-fee)` instead of `(1+fee)`; a trade PnL that excluded fees while the equity curve included them, so the PF was pre-cost; and a position size that divided by the price twice, which made an expensive asset risk 1/price of the budget) — the known-answer suite now covers both directions, and the invariant `eq[-1] − INIT == sum(pnl)` is asserted inside every artifact.

- **Funding-filtered books, Category C (2026-11-02): KILLED — zero of two cards pass, with funding CHARGED for real this time.** Adapter `xsc`, engine `code/xs_factor_c_engine.py` (xsc-1), on the seven funding-covered names; every sim bills funding at the real settlement instants (raw file rates; JUP/HYPE 4h cadence billed as two real settlements; gate rates normalized per 8h), with a no-funding control inside each artifact. FUNDGATE (ROC rank + funding-sign entry gate) `f8c556f2a7d194c3`: net -18.32%, PF ex-cost 0.9392, funding contribution +2.09pp over the ~2-year active window — the tailwind is real but two orders of magnitude short. FUNDTAIL (low-vol + extreme-funding exclusion) `7d82a4921ea6cbd9`: six trades in two years at any threshold — dies on the sample floor; its stricter-threshold neighborhood cell shows a positive net that is null-noise at that n, not evidence. JUP's 243-day funding head_gap (FUNDING_MANIFEST) sets the book start; thirds/halves/yearly and the 70/30 split are measured on the ACTIVE window. Neighborhoods all fail. Report `results/xsf_category_c_report.md` (guard OK strict), six artifacts verify bit-for-bit. Categories A+B+C of the generated pack close with zero survivors.

- **Cross-sectional relative-value books, Category B (2026-11-02): KILLED — zero of two cards pass; BOTH lose before costs, and the neighborhood probes fail too.** Adapter `xsb`, engine `code/xs_factor_b_engine.py` (xsb-1), which REUSES the Category A machinery untouched (that file is hash-pinned by its nine artifacts) — both files are hashed into the xsb run_id. VOLCOMP (relative-vol compression z-score + ROC drift gate on entries) `138c4b2f93fd62db`: net -73.60%, PF ex-cost 0.7903, OOS PF 0.57. DDRELAY (event-conditional relative-drawdown relay; the -20% median-30d trigger fired twenty-three times, so it is not a rare-event excuse) `c7b83f8626bf21b4`: net -47.07%, PF ex-cost 0.8014. Neighborhoods (lb 240/480 for VOLCOMP, trig -0.15/-0.25 for DDRELAY) all fail. Report `results/xsf_category_b_report.md` (guard OK strict), six artifacts verify bit-for-bit. With Category A killed the same day, the OHLCV-only block of the generated pack (categories A and B) closes with zero survivors.

- **Cross-sectional factor books, Category A (2026-11-02): KILLED — zero of three cards pass, and the six neighborhood probes fail too.** Adapter `xsf`, engine `code/xs_factor_engine.py` (xsf-1): rank-rotation books on the 1h universe-14, decision on the rebalance bar's close, execution next open, 11 bps RT, resize-to-target every rebalance (average-cost basis; without it kept units compound without bound — measured 4.75x gross average before the fix), hysteresis bands, declared minimum cross-section of eight, zero-cost control inside each artifact. LOWVOL (336h realized vol) `5c5cbbe6443fb391`: net -45.94%, PF ex-cost 1.165 (under the 1.2 gate), top-5 trades 354% of PnL, OOS PF 0.862. SKEW (720h skewness) `c683ad80d93f965f`: PF ex-cost 0.886 — it loses BEFORE costs; shorting the high-skew names of the 2020-2021 alt bubble did the damage. AUTOCORR (336h lag-1 AC) `78599c8a2cdd0982`: PF ex-cost 0.838. Neighborhood (lb one step each side) all fail: not a parameter problem. Funding NOT charged (declared: seven of fourteen names have no funding file on disk). Report `results/xsf_category_a_report.md` (guard OK strict), nine artifacts verify bit-for-bit. The external prompt's MP-18 claim (+494.7%) has no artifact here and this measured kill is consistent with the EW-momentum concentration kill (`00d2a8549e6c898d`).

- **TOP10 shortlist of the prompts-100 screen (2026-11-01, refrescado 2026-11-12):
  ONE of ten CANDIDATE — the first directional book to clear every measured gate
  with artifacts. NOT validated alpha.** Adapter `top10`, engine
  `code/top10_engine.py` (frozen port of `trading-engines/backtest_prompts100/`:
  known answers 19/19, trade-level parity with the source engine 110/110 on the
  same bytes, `results_100.csv` reproduced, truncation invariance; report
  `results/top10_report.md` guard OK strict). **#44 168-bar breakout BTC 1h
  `d544d85516c7158a`** passes screen gates (full and OOS), concentration (best
  five = 84.97% of PnL; without them net +25.01% and PF 1.2322), thirds (three of
  three green) and the bootstrap CI above zero ([0.2609, 2.2078], t 2.209); it also
  survives DOUBLE costs (OOS PF 1.3866) and its implied leverage peaks at 1.54,
  so the pack's 20x cap never binds. **#28 Donchian breakout BTC 1h
  `ccba31d818c05bec` no longer clears it: with the extended data its bootstrap CI
  is [-0.0049, 0.4377] (t 1.660) — it includes zero, so it dies on
  significance** (concentration, thirds and double-cost survival still pass; OOS
  PF 1.2539). The other eight die with the measured reason: #60/#73/#71
  concentration (best-five trades over 100% of PnL), #95/#26/#34/#59 OOS PF under
  the gate, #56 net. Three findings that change the state of the world: the
  screen's numbers are real and reproduce bit-for-bit; the source doc's "stop
  wins ties" claim is wrong (the source engine executes the exit signal at the
  open first — the tie counts are measured per artifact); and the shortlist's OOS
  is selection-contaminated (the screen ranked the 100 by OOS PF), so the
  multiple-testing haircut applies in full — the one surviving candidate also
  loses to buy & hold OOS by 17.5pp. Next step per doctrine: a FORWARD paper
  record on new bars, not more re-runs.

- **The 100-prompt pack RE-SCREENED with the repo's harness (2026-11-12): the
  pack's own "Top 5" does not survive a non-contaminated split, and its books
  are run at a tenth of the house cost.** Adapter `p100screen`, engine
  `code/p100_screen_engine.py`; the pack's source is copied VERBATIM into
  `code/prompts100/` with a sha256 manifest (`code/prompts100/MANIFEST.json`),
  because `Downloads/` is not durable. Spec (frozen before the first run):
  `results/prompts100_rescreen_pre_registration.md`; report
  `results/prompts100_rescreen_report.md`.

  **WHY A RE-SCREEN AND NOT A PORT.** The pack ranked its hundred prompts by
  their OWN out-of-sample profit factor and published a "Top 5" from that
  ranking. Choosing on an out-of-sample metric turns that window into a
  selection window, so the metric stops being an out-of-sample estimate. The
  re-screen selects on DEV only (everything before 2025-10-01), does not
  trade a purge month, and reads the verdict from 2025-11-01 on. The pack's
  published numbers are NOT treated as evidence here; they are the thing being
  checked.

  **FOUR DEFECTS OF THE PACK MEASURED WHILE PORTING IT** (each one found by
  the repo's own discipline, not by reading the pack's docs):
  1. **COSTS: the pack's constant is `FEE_PER_SIDE = 0.000055`, which is 0.55
     bps per side, not the 5.5 bps its comment and its documentation claim**
     (1 bp = 1e-4). And it charges that constant TWICE per side — once
     folded into the fill price and once as a fee — so its books run at
     **2.2 bps round trip** against the repo's 11.0 bps: **5 times cheaper**
     than the house standard, and a hundred times cheaper than a real Binance
     perp taker round trip. Found by the parity test: the pack's fills are
     cheaper than the repo's by exactly that factor. The constants are
     MEASURED inside the artifact (`pack_cost_per_side_bps`,
     `pack_cost_roundtrip_bps`, `pack_cost_constant`), not asserted here.
  2. **PROFIT FACTOR NOT FULLY EX-COST: the pack's trade PnL omits the ENTRY
     fee** (it only charges it to cash), so its cash and its reported PnL do
     not describe the same money. The repo's port deducts both fees, so the
     published PF is ex-cost and the accounting invariant closes.
  3. **THE PAIR BOOKS ARE NOT HOLDABLE.** Their sizing (N = risk/dist in
     LOG-spread units, capped at 20x equity *in units*) implies a gross
     exchange notional of **30651x the equity (median) and 2215984x (max)** on
     prompt 82, and 236795x on prompt 89. At that leverage the perp funding —
     which the pack does not charge — becomes the main driver of the result:
     a few per cent of equity per settlement dwarfs the spread. The cost the
     repo's regime would charge on that real notional is **2345456 USDT per trade**
     on a 10,000 USDT account. The re-screen's gate for the pairs is
     therefore CERTIFIABILITY (the pack's own 20x cap), not the profit
     factor: prompt 85 is the only survivor of the screen whose OOS metrics
     look good (PF 3.0997), and its implied notional is 52.4x the equity — over the
     pack's own cap — so it is NOT CERTIFIABLE either.
  4. **THE PACK DROPS A TRADE WHOSE ENTRY GAP ALREADY CROSSED THE STOP**
     ("the setup is invalid"). The repo does not discard trades: a bad gap is
     a bad fill, not a trade that never existed.

  **THE PROOF CHAIN** (the repo's, in order): the pack's signal is used
  UNCHANGED and proved by **trade-level parity** against the pack's own
  engine — `code/_prompts100_parity.py` (29 of 29 prompts: identical trades
  and identical metrics under the pack's conventions) and
  `code/_p100_pairs_parity.py` (six pairs: identical signal arrays AND
  identical trades and PnL). The repo's execution is then layered on top with
  the differences DECLARED, and the known-answer suite
  `code/_prompts100_audit.py` (27/27 PASS, both directions) plus the
  accounting invariant asserted inside every artifact close the loop. The
  engine's own bugs were caught by that invariant, exactly as it is meant to
  be: the basket leg was charging the funding on the PRICE instead of on the
  notional, and the rebalance fee was missing from the period PnL — both
  aborted the run instead of producing a plausible-looking number.

  **WHAT THE RE-SCREEN FOUND.** Of the prompts that clear the screen on DEV,
  NONE clears the verdict on OOS; the empirical null of the screen (the
  distribution of the OOS profit factor of every measurable prompt) is
  published in the report, and the multiple-testing control declared in the
  spec is applied to it. The family of prompts 91-100 (the pack's funding
  books) is a third book shape and was NOT measured: it is declared as not
  measured, never estimated.

- **The fifty-prompt pack (`Downloads/50_strategies_crypto-claude1.md`, 2026-10-27):
  KILLED — zero of forty-eight runnable prompts clear the six gates.** Adapter `pack50`,
  one artifact per prompt, report `results/pack50_report.md` (guard OK, every artifact
  `pverify`-clean). S46 weekend-gap fade BTC 1h `be0a85f7ab2b522c` is the near miss and
  fails only concentration (net +26.68%, and -8.65% without its five best trades). S05
  `8321c904af22c0ad` reaches four of six; S01 `1dac06b2e17c8562`, S32 `8d5242a3a743b39d`
  and S45 `fdd964c4e8c669e5` reach three. The zero-cost control is measured inside each
  artifact, and it does NOT show a pack of cost-destroyed winners: the breakout block's
  best gross factor is 1.116 before any fee. Funding is charged at the settlement
  instants (S25 pays $1042.49, the largest drag; S16 receives $715.14 short JUP).
  S34 and S49 are **NO DATA** (no NVDA series on disk) and must never be estimated.
  Do not re-run this pack expecting a different verdict, and do not re-port single
  prompts out of it: the failures are cost and sample, not a misplaced constant.
- **cand7 — the seven prespecified candidates (`Downloads/strategy_candidates_v2-claude.md`,
  2026-10-28): KILLED — zero of seven clear the v1 gates, zero clear v2.** Adapter
  `cand7`, report `results/cand7_report.md` (guard OK, seven artifacts `pverify`-clean).
  C7 `f9fd115fb70b6e8e` is the closest (PF 1.4770, fails concentration only: its five
  best trades are 191.49% of PnL, -2.27% without them). C2 `40b92e7f9cc558dd` has a
  gross edge (zero-cost PF 1.7765) on twelve trades; C4 `ab39449d95dca11b` nets 9.40%
  against buy & hold 14.94% over ninety periods. Two controls are inert by construction:
  C4's book kill cannot bind (fired zero times) and C5's dispersion gate fired on three
  of 699 days. Do not re-run the batch expecting a different verdict; the failures are
  sample, concentration and cost, not a misplaced constant.
- Qwen ten-strategy pack (2026-10-23): **REJECTED BEFORE PORTING — no artifacts, no run;
  do not generate a run for it, and do not re-propose the ten from a new LLM thread.**
  Five of ten need data that does not exist on disk (spot/borrow for carry, L2 history
  for market making, options IV for VRP, liquidation tape, on-chain stablecoin flows);
  four more sit in already-killed families (HMM regime switching ≈ `emaadx`/`cbpack`,
  cointegration stat arb ≈ COINT-DYN/`dspack2` ds8, changepoint trend ≈ SAX/FFS/`dspack`,
  lead-lag ≈ XPROP-LAG). The cascade-fade code enters on the cascade bar its own design
  forbids;
  the meta-labeling design has no base with broad enough PnL to filter — the strongest
  gross-edge book in the corpus is `ds7` RSI-2 SOLUSDT `de5a02eb67f6100a` (top five
  trades 344.51% of PnL, net without them −96.49%). Code defects not to re-import:
  unpurged label split plus a forward-looking `except` fallback, one-way fees with no
  slippage or funding, and silent synthetic fallbacks for funding/order book/IV/
  liquidations/stablecoins. Full reasons table: STATUS.md, "RECHAZO (2026-10-23) —
  pack Qwen de diez estrategias". Its gate is weaker than the repo G-set (no top-five
  concentration, no period split, no buy&hold, no neighbourhood, no n floor).
- FFS-v1: KILLED (window-pick; full −46.6% PF 0.93).
- SAX Scalper PRO v3.0: KILLED (31/31 PF < 1; gross edge ≈ 0).
- XPROP-LAG / COINT-DYN: lose to passive on every pair.
- CVRMD-ETH: full history PF 1.02 → fragile/suspended; CVRMD SUI/ETH edge is
  recent and n-sensitive.
- QUANT CRYPTO BOT 10 suite (cbot): KILLED at every timeframe, 7 symbols,
  ~510 strategy-runs → 5 aggregate passes → 0 that survive a period split.
  Reports `results/xtf_backtest.md` and `results/cbot_1m_campaign.md`.
  **`cbot_1m_campaign.md` is guard OK; `xtf_backtest.md` is NOT** — it carries one
  unbacked tally ("510 strategy-runs") that exists in no artifact and cannot be
  re-derived from the 65 cbot artifacts on disk. Do not repeat that figure; the
  pass counts and metrics it sits next to are artifact-backed. Its synthetic
  "S05 PASS" is a known-answer test, not market evidence.
- **Write tallies in words.** A count of cells/runs is a derived number, not a
  measurement, so `guard` cannot back it and will refuse the report. State
  measurements as numerals with a `run_id`, counts as words, and reconcile the
  counts by recomputation (`code/_assert_report_totals.py` is the template).
- **`guard` is a PROVENANCE check, not a COMPLETENESS check.** It asks "is this
  number in a cited artifact?", not "is this the right number for this question?".
  It also cannot back a DERIVED number (a difference of two cited values), so a
  quantity that a report needs must be MEASURED inside an artifact, not assembled
  by the reader. `cbpackf` does this for the funding drag (`funding_drag_pp`) and
  for concentration (`conc_*`) for exactly that reason. When a report is refused
  for an unbacked number, the fix is to measure it, not to delete it.
- **strategy_pack.py (adapter `cbpack`, a DIFFERENT artifact from the `cbot`
  suite above — single file, ten rule-based strategies): KILLED below 1h and
  CONDITIONAL at 1h.** 5m and 1m: 0 of 7 symbols clear the gate; 1m is ruin
  (−79% to −96% net at 800+ trades). 15m HYPE S07 KILLED (walk-forward negative
  in 3/3 window geometries while buy&hold rose, and PF 1.29 → 1.10 at repo
  costs). At 1h two candidates survive every gate — **XRP S02 `a30083333490d945`**
  and **SOL S10 `814c80675d570aae`** — but as a seven-symbol portfolio the median
  1h net PF (1.15) is under the repo threshold, and the XRP headline win is
  drawdown avoidance, not alpha. Report `results/cbpack_backtest.md` (guard OK,
  111 artifacts, all `verify` clean). The zero-cost control is the interesting
  part: several strategies carry a genuine gross edge at 5m/15m that cost
  destroys — a cost problem, not a signal problem.
- **strategy_pack.py re-run with FUNDING CHARGED and CONCENTRATION measured
  (adapter `cbpackf`, 2026-10-20): still KILLED below 1h, and the 1h survivors
  now FAIL the concentration gate.** Report `results/cbpack_funding_report.md`
  (guard OK, 28 artifacts, all `verify` clean). Two findings:
  1. **Funding was never charged by `cbpack-1`.** Measured drag on the survivors:
     SOL S10 −3.45pp, XRP S10 −5.59pp, XRP S02 −6.11pp, and HYPE S07 **+0.76pp**
     (it is short and receives funding). Real, but an order of magnitude smaller
     than a naive carry-forward sum suggests.
  2. **CONCENTRATION is the gate that was missing.** The best five trades carry
     108% (SOL S10), 136% (XRP S10) and 129% (XRP S02) of total PnL. Remove them
     and the result is −5.86%, −64.02% and −52.26%. The 1h "wins" are a handful
     of positions, not an edge. HYPE S07 passes concentration (47.85% / +11.92%)
     but dies on PF at repo costs.
  At repo costs WITH funding charged, no `cbpack` cell passes every gate.
- **The NEUTRAL XRP book (2026-10-22): WAS the only strategy to clear every
  gate — KILLED 2026-10-31 by 1m fill resolution.** The 15m OHLC simulation
  credits a cover whenever the same 15m bar's high reaches the cover level, and
  the 2026-10-31 external fill audit + probes measured that **100% of the
  book's 5,975 trades are such same-bar round trips**. With touches resolved in
  real 1m temporal order on the OOS segment (2023-01-01..2026-10-01,
  `code/_xrp_1m_resolution.py`, variant engine sha `c7975777c032f3a5`, locked
  engine untouched): PF 1.3019 → **0.9326**, win 86.9% → 77.5%,
  +17,031% → **−74.2%**. OOS PF < 1 = KILL. Maker-fill/intra-bar strategies
  are NOT certifiable on OHLC ≥ 5m — they need 1m resolution or a forward
  record. The history below is kept as the record of what was believed and why
  (the forward paper bot, day-0 2026-10-23, PF 1.203 on 21 lots, is too short
  to contradict the kill). Engine `code/xrp_neutral_engine.py`, deployed as the
  "XRP paper bot" on the VPS. Full history: net +1589%, PF 1.498, 5,876 closed trades,
  86.8% win, maxDD 10.2%, funding paid $265.62.
  It passes what killed every other candidate:
  - **Concentration**: best 5 trades = 2% of total PnL (vs 108-136% for the pack
    survivors). Net without them +1580.8%.
  - **Significance**: bootstrap CI of mean per trade [+21.16, +33.59], t = +8.67,
    P(mean<=0) = 0.0%.
  - **Period split**: green in 3 of 3 (+203.4% / +219.1% / +76.4%).
  - **Out-of-sample with frozen parameters**: train 2020-2022 (+365.5%) -> test
    2023-2026 (+267.0%, PF 1.482, 3,317 trades, maxDD 5.5%); and first-half ->
    second-half (+449.6% -> +210.2%).
  - **Neutrality**: average |net delta| 4.0% of equity, and the two-sided book
    beats BOTH single-sided books (neutral +1608% vs long-only +655% vs
    short-only −100%), so the result is not directional beta.
  The caveat stated plainly: it is the MAX over a PRE-DECLARED 12-combination
  grid (2 of 12 passed), so the multiple-testing haircut applies, and the
  full-history number is an upper bound. The paper run measures the forward
  window, which is the real out-of-sample.
- **v2 (2026-10-23): the same book at 25 USDT x 10x.** Same pre-declared 12
  cells, re-run at the new sizing: 2 of 12 pass, same winner (0.10 / 0.50 / 1.0).
  PF 1.302, 5,963 trades, 87.20% win, maxDD 43.42%, max gross 2.14x, min margin
  buffer 98.93%, 3/3 green thirds, test (2023+) PF 1.301 with 3,375 trades.
  Artifact `7737dd3dc499721f`; report `results/xrp_neutral_25x10_report.md`.
  The deployed account is normalised to 25 USDT at day-0; the engine's raw
  compounded scale is exposed as `engine_equity`.
- sax: adapter present but **UNRUNNABLE** — `Downloads/sax_engine-claude.py`
  is gone from disk, so all **49** pre-existing SAX artifacts fail `verify`.
  Already KILLED, but recover the file or drop the adapter.
- Two lessons from that campaign, both repo-wide:
  1. A permutation control shuffles predictions WITHIN a sample and cannot
     detect that the SAMPLE was selected. A period-split stability probe is a
     separate, mandatory gate before any aggregate pass becomes a candidate.
  2. `guard` is a PROVENANCE check (is this number artifact-backed?), not a
     CORRECTNESS check. It passed on a report whose builder was silently
     double-counting cells. Assert totals against expectations yourself.

## Registry and repo organization (2026-10-31)

The logical index layer — the physical layout stays content-hashed and
append-only (see `code/MAP.md`):

- **`results/registry/`** — the strategy universe: one row per deduped
  strategy (family, adapter, symbol, tf, declared/zero-cost/11bps returns, PF,
  n, window years, cost regime, funding flag, fill model, verdict, run_ids).
  NEVER hand-edited; regenerate with `python code/strategy_registry.py`
  (queries: `--symbol`, `--tf`, `--family`, `--verdict`). Views:
  `by_symbol/<SYM>.md`, `by_tf/<TF>.md`, `by_family/<FAM>.md`.
- **`results/REPORTS.md`** — every report file with its `guard` status; only
  guard-OK reports are citable for numbers. Re-run the sweep after any data
  extension.
- **`code/MAP.md`** — what every engine/tool is, which files are hash-locked,
  and where the fill-model probe variants live.
- **House rule**: every campaign ends with (1) artifacts in `results/runs/`,
  (2) a report with `guard` run and logged in `results/REPORTS.md`,
  (3) `python code/strategy_registry.py` regenerated,
  (4) a verdict here if the state of the world changed.
- **Fill-model rule (from the XRP kill)**: any strategy whose fills are
  resting/limit (maker, intra-bar) is NOT certifiable on OHLC ≥ 5m bars — it
  needs 1m-resolution fills or a forward record before any PASS claim.
  `fill_model: maker_intrabar` rows in the registry carry that warning.
  **Forward real-execution confirmation (2026-11-01, adapter `bookreplay`)**:
  the same static maker grid resolved on REAL aggTrades (official archive,
  17 days XRPUSDT, artifacts `ce46399b5b500a43` + `ecf93a9ee8475a93`, both
  verify bit-for-bit, report `results/bookreplay_report.md` guard OK strict)
  shows the 15m bar convention is unfaithful in BOTH directions — at 0.30%
  spacing it fabricates same-bar covers (38.71% of its closed trades) and
  inflates +4.16 pp; at 0.05% spacing it fabricates even more (70.02%) while
  missing intra-bar re-crossings and DEFLATING −3.0099 pp. Neither direction is
  safe; bar-resolution numbers for resting-maker books are structurally
  unreliable. Does NOT resurrect the XRP neutral book (different geometry).
  Tooling added the same day: `code/datacheck_klines.py` +
  `data/KLINES_MANIFEST.json` (kline bulk: zero gaps/dupes/invalid OHLC),
  `code/fetch_aggtrades.py` + `data/aggtrades/`, `code/fetch_instruments.py` +
  `code/instruments_check.py` + `data/INSTRUMENTS_MANIFEST.json` (current
  exchangeInfo snapshot; PIT historical rules unavailable), VaR/CVaR in
  `code/quant_metrics.py` (selftest `_quant_metrics_selftest.py`), and
  `code/recorder_replay.py` (recorder tape audit: `stream_breaks` counter
  inflated by design — true continuity rule is `pu == prev_u`; snapshot-vs-diff
  id spaces were foreign until the upgraded recorder took effect).
