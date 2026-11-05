# 1m fill accounting for the neutral paper book

**Status: the accounting is proven and live; the forward record is accruing. No edge is
claimed.** The five-pair paper book has no validated edge and this change does not
create one. It makes the record stop flattering the fill model.

## The problem this fixes

The book is a two-sided grid whose exits are resting covers. The 15-minute OHLC
convention credits a cover whenever the SAME bar's high reaches the cover level, so an
entry and its exit can both be booked inside one bar, in an order OHLC cannot observe.
On this book that is not an edge case: on the probe slice below, every closed trade of
the retired single-pair bot was such a same-bar round trip.

A forward record built on that convention measures the convention, not fills.

## What was built

`code/xrp_neutral_engine_paper_1m.py` is a DUAL-MODE engine, **generated** by
`code/_neutral_1m_build.py` from `code/xrp_neutral_engine_paper.py` (the byte-identical
copy of the engine the VPS runs; the builder refuses a base whose sha differs). It is
never edited by hand.

- A bar is resolved minute by minute **only when its tape is complete** (at least
  fifteen distinct minutes). Every other bar keeps the original same-bar block byte for
  byte, which is what makes the pre-tape history bit-identical.
- A cover may fill only on a **strictly later minute** than its own entry. A
  same-minute touch is unresolvable from OHLC: it is counted and banned, never assumed.

`code/_neutral_1m_audit.py` writes `code/_neutral_1m_audit.json` and passes twelve
checks: no-tape identity with the 15-minute engine over the full history, a late tape
leaving every earlier bar bit-identical, five hand-built ordering cases (entry then
cover, cover before entry, same-minute ban, no tape, a partial tape of fourteen
minutes), and an exact reproduction of the published kill.

## Proof: the fill model, and nothing else

Both runs below use the same data, the same sizing and the same slice
(`2023-01-01` to `2026-10-01T13:45:00`). The only difference is the engine and the
tape.

| fill model | run_id | PF | trades | win % | return % | max DD % | final equity |
|---|---|---:|---:|---:|---:|---:|---:|
| same 15-minute bar | `c7f1063c88f3268f` | 1.3019 | 3317 | 86.95 | 17031.11 | 20.54 | 4282.78 |
| one-minute resolved | `18d686932bf06f78` | 0.9326 | 3018 | 77.53 | -74.2 | 81.46 | 6.45 |

Artifacts: `results/runs/c7f1063c88f3268f.json` and
`results/runs/18d686932bf06f78.json`; both reproduce bit-for-bit under
`python code/vrun.py verify` (checked at the time of writing). The repo kline
files are extended by a scheduled daily refresh, so a later `verify` will report
STALE rather than OK. That is the data-extension notice, not a fabrication: the
slice above contains no bars after `2026-10-01T13:45:00`, so its numbers do not
move. Re-run the two commands above if you need a fresh PASS. Two frozen
snapshots taken against the pre-refresh bytes of this same evening were
superseded by these artifacts and remain in the store untouched.

The one-minute side is fully resolved rather than partly: 131479 bars resolved, 0
partial, 0 without a tape, 1972185 minutes used. 290 touches fell in the same minute as
their entry and were banned rather than credited.

This is the same result the fill audit of late October published; what changed is that
it is now an artifact with an id instead of a number in a probe log.

A third artifact, `6f815d5b52cfd930`, re-runs the 15-minute book on the full history at
the current data (PF 1.2787, 5986 trades, win rate 87.17) and also reproduces
bit-for-bit. It exists because the two validated v1/v2 artifacts had gone STALE: the
kline and funding files have been extended since they were created, so they describe
older bytes. Refreshing them does not change what they measured.

## The live deployment

`~/neutral-paper/` runs five isolated pair directories (JUP, XRP, SOL, HYPE, SUI). Each
pair runs the 15-minute cycle and, one minute later, the one-minute accounting cycle.
The two runners share one lock per pair because they append to the same 15-minute kline
CSV: concurrency there would interleave rows and corrupt the file both records are built
from. The wait is bounded and a skipped cycle costs nothing, because every cycle is a
full replay.

The one-minute record is fully separate: its own status, event log, artifact and cron
line. It reuses the SAME day-0 file, so the difference between the two records is the
fill model and not a re-baselined account. Three flags decide whether the record is
usable, and the report fails closed on any of them:

- `day0_replay_matches` re-runs the pure 15-minute path over the prefix up to the day-0
  bar and requires bit-for-bit equality with the frozen baseline.
- `tape_isolated` requires the tape to start after the day-0 bar, so the baseline bar
  cannot be re-resolved.
- `forward_coverage_ok` requires every forward bar to have carried a complete tape.

The comparison is carried as columns, not as recollection: `daily_summary_1m.py` writes
`daily_summary_1m.csv` with the 15-minute equity beside the one-minute one, and
`weekly_report.py` carries a `1M FILL ACCOUNTING` section that reads the `_1m` status
files and marks a pair INVALID if any of the three flags fails.

## The old bot

The single-pair XRP paper bot was retired and deleted on this change. Its directory is
gone, its cron lines are gone, and its state is archived at
`/home/ubuntu/backups/xrp-paper-bot_retired_2026-11-04.tar.gz`. The 15-minute record of
the five-pair book is untouched: this change adds a second record, it does not rewrite
the first.

## What this does not claim

- The paper book still has no validated edge. The one-minute numbers are worse than the
  15-minute numbers on the probe slice, and they are worse for the honest reason: the
  covers the bar convention invented do not exist.
- A touch inside a one-minute bar is still ordered by that bar's OHLC, not by the tape.
  The resolution is one minute, not tick.
- Maker queue position is not modelled. A resting cover is assumed to fill when the
  tape trades through it.
- The probe is a backtest on one symbol. The forward paper record is the experiment, and
  it is measured on five.
