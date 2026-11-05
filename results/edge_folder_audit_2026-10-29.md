# Audit of the EDGE-first research project (v4.1 + v6 bridge) under Downloads — twenty-ninth of October, twenty twenty-six

> **Updated the first of November.** The provisional mirror directories this
> document names (`docs/edge_v41/` and `results/edge_v41/`) no longer exist: that
> content was consolidated into `edge/` and the copies were deleted after a
> file-by-file hash comparison proved them identical. The source folder under
> `Downloads/` is gone too. The verdict below stands unchanged; the record of the
> move is in the migration closure file sitting beside this one.

Scope: the complete EDGE-first research project folder under `Downloads/`
(exact path recorded verbatim in `data/EDGE_V41_IMPORT.json`, `source_dir`),
as an external source of evidence, data and code
for this repository. Every precise figure produced by that project lives in
its own verified artifacts inside the folder; this report states its findings
in words and points at those artifacts, per this repo's rule that a number is
backed where it was measured. All verification commands below were executed
today in the folder with its own pinned venv.

## Verdict

**The project is healthy, sealed, and terminally negative as a strategy
campaign — and it is worth keeping for three assets that this repo does not
have.** Its evidence chain verified end to end today: the pre-registration
seals check out file by file, the engine test suite passes in full, the data
integrity report is clean on every symbol, and the union ledger row count is
exactly the documented post-batch-B total. The one strategy that reached a
sealed out-of-sample read failed its cluster-t gate and is terminal by its
own protocol; no rescue loops are permitted there, matching this repo's kill
discipline.

## What the project is

A pre-registered microstructure research funnel over Binance USDT-M perps
(five majors for the kline layers, four symbols of raw aggTrade tape, the
full perp universe for the cross-sectional screens), run in mid-October
twenty twenty-six under git with frozen pre-registrations. Batch A screened fifteen
variant-trials across eight idea families; zero survivors, with every gross
edge sitting below the measured all-in taker round-trip cost wall (mid twelves
in bps, per symbol in REPORT.md). Batch B added two more screens (one with
negative gross, one sample-starved by its pre-declared warm-up) plus the one
declared sealed read for the cross-sectional momentum candidate: it passed
three of four screen criteria and failed the cluster-t gate — terminal, the
sealed block consumed. The v6 bridge then stopped at its P1 gate: zero
indicators informative on the W5 cells. The AMD reversal port loses
before costs — negative gross expectancy — which is the same "no gross edge"
class of death this repo has measured repeatedly.

## Verification performed today (all PASS)

- The two pre-registration seals verify against the current bytes of every
  listed dossier and spec — nineteen sealed files, no drift.
- The engine and AMD test suites pass in full (twenty-nine tests).
- `tools/build_v6_section7.py --verify` prints fourteen of eighteen checks
  PASS; the four failures are the documented consequence of batch-B rows
  appended to the union ledger and screen count after the P1 snapshot
  (STATE.md records exactly this: the P1 artifacts stay frozen at eight
  hundred twenty-four ledger rows; the ledger now holds eight hundred
  twenty-nine). This is expectation drift in the verify script, not
  tampering — the same known-answer-expectation class noted in this repo's
  audit memory. Suggested fix upstream: teach the verify tool the post-batch-B
  totals or verify against the P1 tag.
- `tools/verify_report.py` fails on the batch-B screen numbers because
  REPORT.md is the batch-A document and batch B results live in worklog.md
  and STATE.md; the batch-B rows in the trial ledger match the worklog
  figures. Documentation gap, not a fabrication. Suggested fix upstream:
  regenerate REPORT.md from the ledger or scope the verifier to batch A.
- The ledger, the sealed one-shot row, and the worklog agree on every
  number cross-checked.
- `data/integrity_report.json`: every symbol passes with zero missing
  one-minute bars and OHLC sanity; funding interval mode eight hours.

## The three assets worth keeping

- **Track R — the live order-flow recorder (RUNNING NOW).** The keepalive
   log shows the recorder alive today; day folders run continuously from
   October tenth through today (twenty day folders, no calendar gap), about
   one point nine GB of parquet: aggTrade tape, bookTicker, depth diffs and
   snapshots, markPrice at one second, one-minute klines, and forceOrder
   liquidations — a data class this repo entirely lacks (the Qwen pack was
   rejected partly because L2 and liquidation tape did not exist on disk).
   Its own readiness bar is fifty-six valid UTC days, so the earliest
   forward verdict lands around early December at the present rate. Depth
   resync gaps are being counted per symbol (thousands per symbol since the
   start) — the coverage counters should be watched, and the five-stream
   buffer visible today (bookTicker and depth for BTC/SOL/SUI) should be
   confirmed against the twenty-one configured streams.
- **The one-minute kline panel** — five hundred eighty-one thousand seven
   hundred sixty bars per symbol over the twenty-five-symbol universe, fully
   integrity-checked. A parallel session already converted it today into
   this repo's taker-directory CSV convention via `code/convert_edge_panel.py`
   with a complete sha manifest (`data/EDGE_V41_IMPORT.json`); the manifest's
   hashes spot-check clean against the written files today. Note that these
   series are resampled from the same one-minute source, not independent
   downloads — a campaign built on them must cite the manifest.
- **The evidence and the engine.** The dossiers (all fifteen byte-identical
   in this repo's `docs/edge_v41/` mirror), the sealed-protocol machinery,
   and the stats layer (cluster-t, BH across screens, stationary bootstrap,
   DSR/SPA/PBO, MDE) are reusable method. The negative results are real
   evidence for the killed-families list: funding-carry, premium-z reversion,
   short-rich-into-settle, cross-sectional momentum (terminal after the
   sealed read), OI-collapse reversion, capitulation burst, one-minute
   lead-lag, CVD continuation, absorption, and the AMD reversal port.

## What this changes in the backtest repo

- STATUS.md / AGENTS.md killed-families lists gain the EDGE families above
  (pre-registered, sealed, terminal — same standing as this repo's kills).
- The recorded Track R data unlocks the order-flow families previously
  untestable here — but only after the recorder accumulates its full
  readiness window; nothing to run today.
- The two upstream tool defects above (verify expectations post-batch-B,
  REPORT.md lacking batch B) are fixes inside the EDGE project, optional,
  and non-urgent because its verdict is terminal either way.
- The maker-fill simulator dossier (EDG twelve, left blocked by the project
  itself) remains pending the user decisions that project lists as
  unanswered (real account size, fee tier, whether real-order calibration
  probes will ever be approved).

## Register of what was NOT changed

Nothing in the EDGE folder was modified. The repository side of this audit
wrote only this report (and, earlier today, the unrelated repo inventory).
The recorder process is owned by its scheduled keepalive task and was left
running.
