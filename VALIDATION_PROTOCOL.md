# VALIDATION PROTOCOL — "no number without an artifact"

## The incident this exists to prevent
On 2026-10-10 an agent reported a full backtest for "SAX Scalper PRO"
(`+18.42% PF 1.31`, later `+19.67% PF 1.35`, plus an estimated pair x timeframe
PF matrix). **None of those numbers came from a program.** They were written in
prose with no run behind them. The reference engine, when actually executed,
gives the opposite result: **PF < 1 on every pair and every timeframe** (see
STATUS.md, "SAX v3.0"). There was no artifact to contradict the fabrication
because the repo had no artifact binding at all: every script printed loose text.

Root cause: **reporting was decoupled from execution.** Fixing that is not
editing one script; it is making it structurally impossible to present a number
that has no persisted, reproducible run behind it.

## The rule
> A number is a result only if there is a run artifact for it, and that artifact
> verifies. Otherwise it is text, and it must not be reported.

## How it is enforced (`code/vrun.py`)
Every run is identified by a content hash:

```
run_id = sha256( engine_source_bytes
               + canonical_json(params)
               + [ (data_path, data_sha256, bars) ] )[:16]
```

- `engine_source_bytes` — the exact engine file, hashed.
- `params` — canonical JSON of the parameters.
- `data` — SHA-256 of the actual CSV bytes used.

If any of those change, the `run_id` changes. A result can therefore never be
silently detached from the exact engine + parameters + data that produced it.

## Commands
```powershell
cd C:\Users\Lenovo\Documents\backtest-system

# run one combination -> writes results/runs/<run_id>.json and prints it
python code\vrun.py run --strategy sax --tf 1h --symbol ETHUSDT
python code\vrun.py run --strategy sax --tf 1h --symbol ETHUSDT --set trend_len=100
# (--set k=v is preferred on PowerShell; --params '{...}' also works but quoting is fragile)

# render: numbers are read ONLY from the artifact file (never from memory)
python code\vrun.py render 2380397d4236b845

# verify: re-runs and asserts the artifact still reproduces bit-for-bit
python code\vrun.py verify 2380397d4236b845

# full matrix (all data files present), writes results/runs/_matrix_<strategy>.csv
python code\vrun.py matrix --strategy sax

# guard a report file: refuse numbers that no artifact contains (--strict verifies symbol context)
python code\vrun.py guard --report report.md [--strict]

# institutional stats scorecard (Sharpe, Sortino, Calmar, Ljung-Box, block bootstrap, margin check)
python code\vrun.py stats <run_id>

# audit which artifacts are STALE or DATA_MISSING relative to current data files on disk
python code\vrun.py stale [--data <filename>]

# parameter neighborhood stability sweep
python code\vrun.py neighborhood --strategy xrpneutral --tf 15m --symbol XRPUSDT --param trend_band --values 0.08,0.10,0.12

# parallel verify of artifacts (--skip-orphaned ignores deleted engine artifacts like SAX)
python code\vrun.py pverify --strategy cbpackf [--skip-orphaned] [--workers 4]

# list every artifact on disk
python code\vrun.py show
```

Strategies: `sax`, `cvrmd`, `botstrat`, `ffs`, `mp20`, `cbpack`, `cbpackf`, `xrpneutral`, `smqe`, `dspack`, `dspack2`, `hmaaoadx` (see the adapters table below).

`verify` re-runs the artifact and compares. Exit codes:
- **0 OK** — reproduces bit-for-bit.
- **2 REFUSED** — engine/params changed (tampering) or metrics do not reproduce.
  Do not publish.
- **3 STALE** — the data bytes changed since the artifact was written (the local
  klines are live-updated by `recorder`/fetch jobs). The artifact is a frozen
  snapshot of the OLD bytes; re-run to refresh. Not a fabrication.
- **4 ORPHANED** — engine source file is missing from disk (e.g. SAX v3 engine deleted;
  known killed). Artifact is permanently orphaned rather than tampered with. Use
  `pverify --skip-orphaned` to avoid noise in validation sweeps.

**Tradeoff, stated plainly:** because every run_id binds the exact CSV bytes,
any data update invalidates prior artifacts. That is intentional — it means a
number can always be traced to the exact bytes behind it — but it also means
artifacts are snapshots and must be refreshed after a data refresh.

### Recommended for a validation campaign: freeze the data
The local klines are rewritten live by `recorder.py` / `ind0607_study.py`, so a
matrix can go stale mid-run. Before a campaign that has to be reproducible
later, copy the CSV set into a dated folder and run against that copy
(e.g. `data/_frozen/2026-10-10/`). Then every artifact stays `verify`=0 forever.
Until that is wired into the CLI, treat `verify`=3 as "refresh the snapshot".

## Obligations for any agent (or human) writing a report
1. Run `vrun.py`. Do not hand-write metrics.
2. Render the table with `vrun.py render` (or copy it verbatim from the artifact).
3. **Cite the `run_id` and the artifact path next to every table.** A table
   without a `run_id` is not admissible.
4. Before publishing, `vrun.py verify <run_id>`. If it refuses, the numbers do
   not go out.
5. Synthetic / illustrative / hypothetical scenarios must be labelled as such and
   carry no `run_id`; they are never mixed into a results table.

## What is NOT fixed by this
This makes fabrication *detectable and refusable*; it cannot make an LLM
incapable of emitting a wrong sentence. The enforcement is: the harness is the
only source of numbers, `render` reads files not memory, and `verify` is the
check you run before believing anything. If a number has no `run_id`, treat it
as fabricated until proven otherwise.

## Status of the existing scripts
`code/*.py` (cvrmd_backtest, botstrat_backtest, mp20_report_ports, ffs_engine2,
ahmad_*, donchian_ao, ...) still print loose text, so their output is not
artifact-bound. `vrun.py` wraps the ones that matter as adapters **without
modifying them**:

| strategy key | engine | unit |
|---|---|---|
| `sax` | `Downloads/sax_engine-claude.py` | symbol x tf |
| `cvrmd` | `code/cvrmd_backtest.py` | symbol (1h) |
| `botstrat` | `code/botstrat_backtest.py` | symbol (1h) |
| `ffs` | `code/ffs_engine2.py` | symbol (5m) |
| `mp20` | `code/mp20_report_ports.py` | portfolio (BTC/ETH/SOL/AVAX/LINK) |

Adding an engine = adding one entry in `ADAPTERS`; hashing, render, verify and
guard then apply to it automatically. The remaining scripts are the migration
backlog.

## Guard — reject numbers that no artifact backs
```powershell
python code\vrun.py guard --report report.md
```
`guard` extracts every metric-looking number from the report, loads the
`run_id`s it cites, and REFUSES (exit 2) if any number is not present in the
cited artifacts (or if no valid `run_id` is cited at all). It ignores years, ids
and dotted versions. Demonstrated: a report claiming `+19.67% PF 1.35` against
the ETH 1h artifact is refused; the artifact's own `render` output passes.

## Agent contract
`AGENTS.md` at the repo root restates REGLA 0 and the enforcement steps for any
agent working here: run the harness, cite the `run_id`, `verify` before
publishing, `guard` the report file.
