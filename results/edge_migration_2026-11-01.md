# EDGE migration closure record — first of November, twenty twenty-six

This file records what was imported from the sealed EDGE-first project into this
repository, what was fixed so it runs, what was deleted so nothing is duplicated,
and what is deliberately left alone. It is a housekeeping record: **it contains no
backtest result**, so it cites no `run_id`, and every count below is written in
words on purpose. `guard` returns OK on it precisely because there is no metric
number in it to back.

Companion documents: `AGENTS.md` (the migration section and the kill list),
`edge/REPORT.md` and `edge/V6_REPORT.md` (the campaign's own verdicts), and the
folder-audit report that sits beside this file (dated twenty-ninth of October).

## Verdict carried over: TERMINAL

The campaign does not change the state of the world in this repo, and it must not
be re-run expecting a different answer. Pre-registered batch A and batch B produced
zero survivors; the single sealed out-of-sample read failed its own cluster-t gate;
the v-six bridge stopped at its first phase; the AMD reversal candidate is negative
**before** costs. Its families join the killed list in `AGENTS.md`. What the import
buys is the **denominator** — the ledger of every trial that was run — so that a
future screen on the same data can apply a false-discovery correction instead of
rediscovering the same ideas as if they were new.

## What was imported, and where it lives

| Destination | Content | Measured size |
|---|---|---:|
| `edge/` | the whole sealed project: engine, `amd_engine`, tests, tools, fifteen dossiers, six spec files, ledger, figures, results, the three reports | thirteen mebibytes |
| `recorder/` (repo root) | the live Track R recorder, its day-partitioned parquet and its coverage file | two thousand three hundred and four mebibytes |
| `data/edge_panel/` | the one-minute kline + funding panel, eighty-two parquet | one thousand and eighty-two mebibytes |
| `data/binance_klines_1h_taker/` | twenty-five new symbols resampled to one hour | nineteen mebibytes |
| `data/binance_klines_15m_taker/` | the same twenty-five symbols at fifteen minutes | seventy-two mebibytes |
| `data/EDGE_V41_IMPORT.json` | sha256 of every source parquet and every output CSV, plus row counts and first/last timestamps | fifteen kilobytes |
| `code/edge_stats.py` | vendored `edge/engine/stats.py`, provenance header, body byte-identical | fourteen kilobytes |
| `code/_edge_stats_vendor.py` | regenerates the vendored copy and proves body parity | — |
| `code/convert_edge_panel.py` | the parquet-to-CSV converter, refuses to overwrite, emits only complete buckets | — |
| the git-history bundle under `backups/` | the pre-registration commit history, the only record that those specs were frozen before the screens | thirty-four mebibytes |

The panel was measured, not assumed: **thirty-one** symbols carry one-minute
klines and **thirty-one** carry funding, not the forty-one that the earlier text
in `AGENTS.md` quoted. That figure was the project's candidate universe. The
twenty-five imported symbols are the ones the repo did not already have; the six
it did have (BTC, ETH, SOL, SUI, XRP, HYPE) were skipped rather than overwritten.

## Why `code/edge_stats.py` exists at all

It is the one piece of code in that project this repo genuinely lacked. Before the
import, a grep over `code/` found **zero** files containing
Benjamini-Hochberg, Hansen's SPA, a minimum-detectable-effect calculation, a
day-clustered t-statistic, or a matched-timing null. Those five are exactly the
tools the pack campaigns could not use to defend themselves against their own
trial counts, so they are now importable from the harness directory:

    PYTHONPATH=code python -c "import edge_stats"

`deflated_sharpe` and `pbo_cscv` already existed in `code/quant_metrics.py` and are
kept in the vendored file only for API parity — `quant_metrics.py` stays their
canonical source. The body below the marker line is byte-identical to
`edge/engine/stats.py`; `python code/_edge_stats_vendor.py --check` fails loudly if
anyone edits the copy instead of the source.

**Imported statistics are not trusted statistics.** `code/_edge_stats_audit.py`
runs nineteen known-answer checks and writes them to
`results/edge_stats_audit_known_answers.txt`; all nineteen pass. The checks do not
ask "does it run", they ask "does it give the answer that can be computed by hand
or by an independent implementation": Benjamini-Hochberg against a separate
step-up implementation over three random inputs, `cluster_t` against an
independently written CR1 formula to one part in a thousand million, `effective_n`
against the hand value for clusters of eight, one and one, `mde_bps` against
`(z + z) * sigma / sqrt(n)`, SPA against a trial that dominates its benchmark
(small p) and a trial identical to it (not small), and determinism of SPA,
`bootstrap_ci` and the circular shift under a fixed seed.

Writing that audit already corrected two wrong assumptions of mine, which is the
point of it: `effective_n` returns the **number of clusters** for a balanced
design, not half the observations, and `circular_shift_null` returns a **pair**
(the p-value and the null distribution), not a float. A future gate that unpacks
these the other way will break silently, so both are stated here.

## What was deleted, and the proof that it was duplication

Every deletion below was verified by cryptographic hash file by file **before** the
delete, not by filename.

| Deleted | Size | Proof |
|---|---:|---|
| `docs/edge_v41/` (twenty-eight files) | under one mebibyte | fifteen dossiers identical to `edge/dossiers/`, six spec files identical to `edge/specs/`, seven reports and tables identical to files at the root of `edge/` |
| `results/edge_v41/` (twenty-three files) | twelve mebibytes | twenty-two identical to their counterpart under `edge/results/`, the twenty-third identical to `edge/results/AMD/all_metrics.json` |
| per-run `equity.csv` and `trades.csv` under `edge/results/AMD/` (thirty-nine directories) | one hundred and forty-four mebibytes | the candidate is negative before costs, so its per-run curves answer a question nobody may ask again; the per-run `metrics.json` and the aggregate `all_metrics.json` were kept |
| the launcher backup under `recorder/` | four kilobytes | superseded launchers: the Scheduled Task and the Startup shortcut both point at `recorder/keepalive.ps1` now |

The source folder itself, its virtual environment, its raw kline zips, the bulk
`aggTrades` archive, the mark-price and premium-index dumps and the original
`data/processed/` tree are gone with it. The `aggTrades` question resolved itself:
it was deleted rather than parked, because it had no consumer and the one thing it
would have enabled — a maker fill model — is not something any strategy here
currently claims.

## Duplication audit after the move

`code/_find_duplicate_data.py` hashes every file under `data/` and
`recorder/data` and groups identical content. Result: **four hundred and sixty-three
files, four thousand seven hundred and eighty-nine mebibytes hashed, ZERO groups of
byte-identical files.** The EDGE panel and the taker directories describe the same
market, but they are not copies of the same bytes — different windows, different
columns — and the manifest is what ties them together.

## The recorder: three defects fixed, one limit that cannot be

Fixed, each measured before the fix:

- **Two recorders writing at once.** The Scheduled Task and the Startup launcher
   could both pass the "is it running" check in the same second. A named mutex now
   wraps check-then-start. Live proof after the fix: exactly one process, started
   by the keepalive itself, and the log line reads `STARTED (was down)` followed by
   `OK running(pid=…)`.
- **The start stamp was rewritten on every restart**, which reset the fifty-six
   valid day milestone to "today" each time the machine came back. It is now
   written once. The file still reads twenty-ninth of October.
- **A restart truncated the current UTC day.** `pyarrow`'s writer opens in write
   mode, so the day file was wiped and rewritten — the visible symptom was a day of
   fourteen mebibytes next to a day of two hundred and forty-five. An existing day
   file is now rotated to a `prev` segment instead, and the current day shows three
   such segments.

**The limit:** the recorder cannot record while the machine is off. It was off
overnight into the first of November — no keepalive line for eleven hours — so that
day is not a valid recording day. Any `R_READY` arithmetic must subtract it, and it
must read the `prev` segments too, because `{stream}.parquet` alone is only the last
segment of a day, never the whole day.

## What is deliberately NOT imported

- **The numbers.** That project's evidence chain is commit plus pre-registration
  hash plus its own verifier, not `vrun verify`. Nothing measured there has a
  `run_id`, so nothing from it may be quoted as a result here. Quote the verdict,
  never a profit factor.
- **`engine/sim.py`, `costs.py`, `data.py`, `metrics.py`.** This repo already has a
  simulator and an eleven-basis-point cost model. Two engines are two truths.
- **`amd_engine/`.** Its candidate is negative before costs; porting a corpse with a
  green test suite is work with a known answer.
- **The panel's one-minute history as a new repo directory.** It stays at
  `data/edge_panel/` because the converter and the manifest point at it; the
  derived one-hour and fifteen-minute taker CSVs are what the harness reads.

## Reproduce the two things that are reproducible

    python code/_edge_stats_vendor.py --check      # vendored stats body still identical
    python code/_edge_stats_audit.py               # nineteen known-answer checks, all must pass
    python code/_find_duplicate_data.py            # zero byte-identical files in data/

Both are read-only. Neither produces a strategy result, and neither should.
