# Full-repo inventory — 2026-10-29

> **Updated the first of November.** The two provisional EDGE directories this
> inventory lists under `docs/` and `results/` were deleted after a hash
> comparison against `edge/`, where that content now lives; the same applies to
> the source folder under `Downloads/`. Read the migration closure file beside
> this one for what moved and what was cut.

Scope: every directory, engine, dataset, artifact and report in the repository,
classified into WORKING / STALE / DAMAGED / DEAD, with the recomputable method
for every count. All counts in this file were recomputed today by:

- `python code/vrun.py stale > results/_inventory_stale_2026-10-29.txt`
  (data-state of every artifact against the current bytes on disk);
- `results/_inventory_state_2026-10-29.json` (per-artifact engine-hash state,
  computed with `vrun.py`'s own `_sha256_engine` over the ADAPTERS registry);
- the report cross-check in this file (cited run_ids per report crossed with
  both maps).

This is a state audit, not a performance report: no number below is a
strategy result. Every strategy verdict cited is already measured in the
artifacts and reports listed.

---

## 1. Executive verdict

The harness and its protocol are healthy. The data is current and larger than
most artifacts expect. The damage is one cause, three symptoms:

**One cause:** on 2026-10-27 a concurrent session extended the 1h dataset
(and touched several other series) without re-running the affected grids.
Every artifact whose inputs hash the old bytes went STALE at once. During
this audit (2026-10-29) a second, necessary extension was applied: the
funding histories of five of the eight symbols ended 2026-10-01 while the
klines reached 2026-10-27, so every funding-hashing run charged nothing for
its tail — the exact bug class AGENTS.md documents ("a partially-funded
backtest is a different backtest"). `code/fetch_funding_all.py` appended the
missing settlements (append-only, same schema) and all eight files now end
2026-10-29 08:00 UTC.

**Symptom one — staleness:** as of the post-extension audit, two hundred
thirty-eight of the fifteen hundred eighteen artifacts verify against the
current data and twelve hundred eighty are STALE (exit three: re-runnable,
not fabrications). Before the funding extension the split was seven hundred
fifty-nine OK / seven hundred fifty-five STALE; the extension moved every
artifact that hashes a funding file (pack50 family, gate2, gatecal, cand7,
cbpack, cbpackf, fingrad, q10, xrpneutral, smqe-5m and their reports) into
STALE. The verdicts those artifacts carry are unaffected — kills are final
and re-runs are only owed when a number is quoted.

**Symptom two — engine drift:** three hundred seventy-eight artifacts hash
engine bytes that are no longer on disk (exit two: REFUSED). Two of these
drifts are *new* since `code/_engine_lock.json` was last updated:
`cbpack_funding_engine.py` and `smqe_engine.py` are each in a third state
(neither the locked "current" sha nor the recorded orphaned sha). The rest
(pack50*, cand7, mps20, mpv3, gate2, gatecal) are earlier iterations whose
report-cited successors were produced with the current bytes. The cbpackf
third state is legitimate: `code/_cbpack_funding_parity.py` re-run today on
the current bytes prints ALL PARITY CHECKS PASS (known-answer funding cases,
per-trade independent recomputation from the raw settlement column, drag
not-double-count). The engine only needs re-running artifacts + a lockfile
update, not a rebuild.

**Symptom three — reports:** after both extensions, two of the twenty-six
reports in `results/` stand (the two cbot reports — cbot hashes no funding
file). Every other report cites at least one STALE or REFUSED artifact and
must not be quoted until its strategy is re-run. Before the funding
extension the standing list was nine reports; the extension is a deliberate
trade documented in §7: refreshed, publishable XRP artifacts and an honest
funding tail in exchange for re-running the kill packs' cells whenever their
numbers are next quoted.

## 2. Harness and adapters — WORKING

`code/vrun.py` exposes run / render / verify / matrix / pmatrix / pverify /
guard / stale / stats / neighborhood / show. Twenty-six adapters are
registered. Engine presence on disk, checked today:

- Present and hashing to the bytes their artifacts record: smqe* (engine file
  itself drifted — see §4), fingrad, cbpack, xrpneutral, cvrmd, botstrat,
  ffs, mp20, cbot (nine files under `code/cbot/`), pack50 family (five
  engine/strat sets), cand7, dspack, dspack2, emaadx, hmaaoadx, mps20
  (`code/claude_bot_1/`), mpv3, gate2, gatecal, q10, q10diag.
- **Missing:** `Downloads/sax_engine-claude.py` — gone. All forty-nine SAX
  artifacts stay ORPHANED (exit four). SAX v3 is already KILLED on its own
  evidence (PF below one on every combination), so the orphaning costs no
  live conclusion. A `sax_v4_engine.py` + `sax_v4_adapter.py` pair exists in
  `code/` (audited port, 2026-10-25) but is **not registered** in ADAPTERS.
- Not in backups either: the September twenty twenty-six zips contain the SAX v2 Pine only.

Engine-lock state (`code/_engine_lock.json`):

| file | lock state |
|---|---|
| cbpack_engine.py, cvrmd_backtest.py, botstrat_backtest.py, mp20_report_ports.py, grid_audit.py | match disk |
| cbpack_funding_engine.py | THIRD STATE — rebuilt again after the lockfile's "current" sha |
| smqe_engine.py | THIRD STATE — same class |

## 3. Data — WORKING, with two known gaps

Canonical market data (Binance CSVs, the only market data in the repo):

| directory | files | window |
|---|---|---|
| `data/binance_klines_1h` | thirteen symbols | September twenty nineteen → 2026-10-27 |
| `data/binance_klines_15m` | six symbols | from late twenty nineteen → 2026-10-27 |
| `data/binance_klines_1m` | seven symbols | January first of twenty twenty-three → 2026-10-01 (fixed window) |
| `data/binance_klines_5m_taker` | seven symbols | from October twenty twenty-four → mid-October twenty twenty-six |
| `data/binance_klines_1m_taker` | seven symbols | January twenty twenty-three → 2026-10-01 |
| `data/binance_klines_1h_taker` | thirty-two symbols | from October twenty twenty-four → October twenty twenty-six (staggered ends) |
| `data/binance_klines_15m_taker` | thirty-two symbols | same as 1h taker |
| `data/binance_funding` | eight symbols (JSON) | full history (JUP completed) |
| `data/binance_klines` (5m native) | seven symbols | per-symbol history |
| `data/binance_klines_15m_cache`, `data/_1m_cache`, `data/etf` | caches / empty | — |

Secondary: `data/mp_suite` (forty-eight files), `data/multipair_1h`,
`data/mp20_real_6m`, `data/mp20_real_full`, `data/polymarket` (thirteen
files, from `code/poly_recorder.py`), `data/futures` (one file).

Gaps to note (not damage, but they bound any new campaign):

- HYPE native 1h ends on September twenty-six of twenty twenty-six while the
  taker copy reaches October twenty-six — one series two windows long.
- SPXUSDT 1m covers roughly three months and its files carry no taker-buy
  field (already stated in `results/doc_audit_2026-10-29.md`).

## 4. Artifacts — one frozen store, three states

`results/runs/` holds fifteen hundred eighteen artifact JSONs (the two
mid-audit XRP re-runs are superseded by two later runs — see §7 Tier 1)
plus the chain file and per-matrix CSVs. State, computed today after the
funding extension:

| state | count | meaning |
|---|---|---|
| engine-current + data-clean | two hundred thirty-eight | verify bit-for-bit today |
| engine-current + data-STALE | twelve hundred eighty | exit three; re-run to refresh |
| engine-drift | three hundred seventy-eight | exit two; the engine was edited after they were written |
| orphaned (sax) | forty-nine | exit four; engine file gone |

Drift per strategy: pack50d ninety-two, cbpackf sixty-seven, pack50
forty-nine, smqe forty-eight, pack50b forty-six, pack50c thirty-four, cand7
twenty-one, mps20 eight, gate2 six, mpv3 six, gatecal one.

Reading of the drift classes: for pack50 / pack50b / pack50c / pack50d /
cand7 / gate2 / gatecal the drifted copies are superseded iterations — the
artifacts their reports cite were produced with the current bytes (they are
now STALE by data, not REFUSED by engine). For **cbpackf** and **smqe** the
drift is live: their engines were rebuilt after the lockfile was updated,
and the cbpackf report's twenty-eight cited artifacts are all REFUSED.

## 5. Reports — two stand, twenty-four must not be quoted

Cited-run-id cross-check, state AFTER the funding extension of this audit
(pre-extension the standing list was nine: cand7, cbot x two, gate2,
gate_calibration, pack50 x four):

| report | cited | clean | stale | drift | status |
|---|---|---|---|---|---|
| cbot_1m_campaign.md | fourteen | fourteen | — | — | **STANDS** |
| cbot_realdata.md | five | five | — | — | **STANDS** |
| xrp_neutral_report.md | two | — | two | — | **REFRESHED** — superseded artifacts re-run, see §7 |
| xrp_neutral_25x10_report.md | two | — | two | — | **REFRESHED** — superseded artifacts re-run, see §7 |
| cand7_report.md | seven | — | seven | — | re-run when quoted |
| gate2_scoring.md | six | one | five | — | re-run when quoted |
| gate_calibration_report.md | one | — | one | — | re-run when quoted |
| pack50_report.md | forty-eight | five | forty-three | — | killed; re-run when quoted |
| pack50b_report.md | forty-six | five | forty-one | — | killed; re-run when quoted |
| pack50c_report.md | forty-two | seven | thirty-five | — | killed; re-run when quoted |
| pack50d_report.md | forty-eight | five | forty-three | — | killed; re-run when quoted |
| cbpack_backtest.md | one hundred eleven | fourteen | ninety-seven | — | killed; re-run when quoted |
| cbpack_funding_report.md | twenty-eight | — | — | twenty-eight | DEAD — engine rebuilt after report |
| mpv3_s10_institutional_audit.md | five | — | — | five | DEAD — engine drift |
| smqe_report.md | forty-two | thirteen | twenty-eight | one | re-run grid |
| dspack_report.md | two hundred twelve | thirty-two | one hundred eighty | — | killed; re-run when quoted |
| dspack2_report.md | eighty-one | twelve | sixty-nine | — | killed; re-run when quoted |
| emaadx_report.md | fifty-five | eight | forty-seven | — | killed; re-run when quoted |
| fingrad_report.md | one hundred fourteen | — | one hundred fourteen | — | killed; re-run when quoted |
| hmaaoadx_report.md | twenty-six | four | twenty-two | — | killed; re-run when quoted |
| mps20_report.md | eight | — | eight | — | re-run when quoted |
| q10_pack_results.md | eight | — | eight | — | re-run when quoted |
| q10_step0.md | three | — | three | — | re-run when quoted |
| xtf_backtest.md | one hundred thirty-three | sixty | seventy-three | — | killed campaign (already carries an unbacked tally — see AGENTS.md) |
| repo_reaudit_2026-10-25.md | one | — | one | — | one stale citation |
| doc_audit_2026-10-29.md | eleven | — | eleven | — | cites pre-extension artifacts |

The XRP-neutral reports still cite the October twenty-third artifacts
(`7737dd3dc499721f`, `8bf3575619eda66f`), which are STALE. Their
replacements verify bit-for-bit today: v1 `295c21687960fadd` (PF 1.4997,
five thousand eight hundred eighty-eight trades, net +1598.19 percent,
maxDD 10.18 percent, funding paid net $252.70) and v2 `fe5c359a22c8dffe`
(PF 1.3071, five thousand nine hundred seventy-five trades, maxDD 43.42
percent, min margin buffer 98.93 percent, `bars_over_leverage` zero,
funding net $518.86). Both carry `funding_covers_bars = true`. Re-rendering
the two reports' prose onto the new ids is the open half of Tier 1.

Note on `mpv3_s10_institutional_audit.md`: mpv3_engine.py drifted and five of
five cited artifacts are REFUSED. That audit's verdict must be re-derived or
retired before anyone quotes it.

## 6. Code classification (three hundred eighteen entries under `code/`)

**WORKING — canonical (do not touch without an audit):** `vrun.py`; the
twenty-six adapter engine sets from §2; the audit/control layer
(`_cbpack_*.py`, `xrp_neutral_*.py`, `gate2.py`, `_gates_v2.py` +
selftest, `_gate2_audit.py`, `_verify_strategy.py`,
`_assert_report_totals.py`, `code/audit/../test_cbpack_funding_engine.py`,
`_cbpack_funding_parity.py`, `_build_funding_engine.py`,
`_engine_lock.json`); report builders (`*_assemble_report.py`,
`*_build_report.py`, `_pack50*_run_*.py`, `_xtf_periods.py`); data tooling
(`fetch_*.py`, `extend_*.py`, `build_daily.py`, `build_incremental.py`,
`dl_data.py`, `merge_parquet.py`, `verify_data*.py`); the deployable paper
bots (`xrp_paper_bot.py` + `deploy_xrp_paper_bot.sh` +
`xrp_bot_status_line.py`, `paper_forward.py`, `paper_live.py`,
`paper_grid.py`, `poly_recorder.py`).

**NO ADAPTER — ported engines that never entered the harness** (kept as
reference; do not quote numbers from them): `kimi20_*`, `adxhma_strategy.py`
(superseded by the registered `hmaaoadx` adapter), `donchian_ao*`,
`revbounce` version series, `mdiv15_backtest.py`, `smc4_backtest.py`,
`ew_backtest.py`, `superew_backtest.py`, `bjbot_backtest.py`,
`ds20_backtest.py`, `ofp70_*`, `ahmad_*`, the `sax_v4_*` pair (audited,
registration pending), `survivors_strategy.py`, `sfs_port.py`,
`vault_*` transpile tooling, `docs/edge_v41/` + `results/edge_v41/`
(EDG port campaign, twenty-three docs).

**FOREIGN — belongs to another project** (`C:\Users\Lenovo\trading-engines\
quant-alert-engine` hardcoded in their paths): `test_toast.py`,
`test_toast_mt.py`, `ui_fix_test.py`, `ui_symbol_test.py`, `cardtest/`,
`code/temp-extra/cardtest/`, `trim_card.py`, `card_upgrade_test.py`,
`render_card_test.py`, `check_vps.py`, `list_alerts.py`. Misplaced, harmless.

**SCRATCH — one-off diagnostics** (`diag1-7`, `check_*`, `find_*`,
`_probe*`, `read_bt*`, `_dbg_*`, `_smoke*`, `_patch_debug.py`, `_fixer.py`,
`_trim.py`, `_test_write.py`, `temp_out.txt` / `temp_output.txt` at root):
safe to archive.

**SUPERSEDED/BACKUP dirs:** `code/attic/` (one broken vrun copy),
`code/temp-root-extra/`, `incoming/` (staging for claude_bot_1 — already
registered as mps20), `code/grid_audit_v1.bak.py`.

**Paper-trading state at root:** `grid_forward_*` (updated 2026-10-27 — two
days behind today), `mp18_forward_*` and `grid_paper_*` (October one —
dormant). The XRP paper bot itself lives on the VPS; its repo-side evidence
is the xrpneutral adapter.

**Docs:** AGENTS.md / STATUS.md / GATES_AND_RULES.md / RUNBOOK.md /
VALIDATION_PROTOCOL.md / STRATEGY_GENERATOR_PROMPT.md — current (AGENTS.md
and STATUS.md edited 2026-10-29).

## 7. Plan (statuses as of end of this audit)

**Tier 0 — funding tail. DONE this audit.** The funding files of five of
the eight symbols ended 2026-10-01 against klines reaching 2026-10-27;
`funding_covers_bars` was false on the first re-run. `code/fetch_funding_all.py`
(append-only, public REST, same `{"t","r","T"}` schema) extended all files to
2026-10-29 08:00 UTC. Side effect, accepted and documented: every
funding-hashing artifact is now STALE (§4). Rule going forward: extend
klines AND funding in the same session, then re-run what will be quoted.

**Tier 1 — restore the live evidence. ARTIFACTS DONE, reports pending.**
- v1 artifact `295c21687960fadd` — verify OK bit-for-bit.
- v2 artifact `fe5c359a22c8dffe` — verify OK bit-for-bit.
- Both `funding_covers_bars = true`; the tail funding was a net RECEIPT
  (the book was net-short at the tail settlements), which is why
  `funding_paid` reads lower than the partially-funded superseded run —
  measured: the final-equity gain and the funding delta agree in magnitude
  to within a few dollars, opposite in sign, as expected.
- Remaining: re-render `xrp_neutral_report.md` and
  `xrp_neutral_25x10_report.md` onto the new run_ids (prose edit, then
  `guard`), and re-run the neutrality/gauntlet controls
  (`xrp_neutrality_check.py`, `xrp_neutral_gauntlet.py`) so the standing
  claims (neutral beats long-only and short-only; bootstrap CI; period
  split) are re-measured on current data.

**Tier 2 — resolve the two third-state engines. PARTLY DONE.**
1. cbpackf: parity PASS on current bytes (this audit). Remaining: re-run
   the funding matrix, re-render `cbpack_funding_report.md`, update
   `_engine_lock.json` (current_sha → the on-disk bytes, and archive the
   old "current" as a superseded entry).
2. smqe: parity = `_smqe_audit.py` on current bytes, then re-run the smqe
   grid and re-render `smqe_report.md`.
3. Re-derive or retire `mpv3_s10_institutional_audit.md` (five of five
   cited artifacts REFUSED).

**Tier 3 — freeze the killed campaigns instead of re-proving kills.**
For the reports whose strategies are already KILLED (dspack, dspack2,
emaadx, fingrad, hmaaoadx, xtf, cbpack_backtest, mps20, q10, and the four
pack50 reports): prepend a STALE banner stating the artifact date, the two
data-extension dates (2026-10-27 klines, 2026-10-29 funding), and that the
verdict is final (AGENTS.md forbids rescue loops). Re-running hundreds of
cells to refresh numbers nobody is quoting buys nothing. If a number from
one of these is ever needed again, re-run that cell then.

**Tier 4 — hygiene (batch, no urgency).**
1. Decide SAX: drop the dead adapter or register the audited `sax_v4`
   pair as `saxv4`.
2. Move the foreign quant-alert-engine files out of `code/` (or archive
   them under `code/attic/foreign/`).
3. Archive the scratch/diagnostic layer into `code/attic/scratch/`.
4. Refresh the root paper-state files or mark them dormant
   (`grid_forward_*` two days behind; `mp18_*`/`grid_paper_*` dormant).
5. Extend HYPE native 1h to match its taker copy, or record the gap in
   AGENTS.md's data section.
6. After every tier: `pverify` the touched strategies and `guard` every
   re-rendered report before anyone quotes it.

**Standing rule for all new work:** no engine edit without re-running its
artifacts or updating `_engine_lock.json` in the same session — the drift
found here is entirely silent engine edits without that bookkeeping. And no
klines extension without the funding extension: `funding_covers_bars` in
the artifact is the check that catches the mismatch.
