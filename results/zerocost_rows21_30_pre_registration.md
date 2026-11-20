# Pre-registration — the zero-cost / no-rules control, rows 21-30

Date: 2026-11-20. Written BEFORE the first artifact of this campaign exists.

## What this experiment is

The third batch of the same control (`results/zerocost_pre_registration.md`,
rows 1-10; `results/zerocost_rows11_20_pre_registration.md`, rows 11-20): the
user asked to continue with the next ten rows of
`results/top100_2026-10-31.md`. Every protocol rule carries over unchanged:
**CONTROL, not a verdict** — no gate is evaluated, no pass/fail is published,
nothing resurrects a killed verdict, and no row is evidence of alpha (REGLA 1).

## Which thirty...

Rows 21-30 of `results/top100_2026-10-31.md`, verbatim, in published order.
The list predates this campaign; nothing was selected on its outcome.

| row | book | market | adapter | ranking `run_id` |
|---:|---|---|---|---|
| 21 | B17-1h EMA 20/50 trend + EMA200 filter (long) | HYPEUSDT 1h | `pack100` (`strat=B17-1h`) | `0e0d2501a65f1a81` |
| 22 | F75-1h equal-highs liquidity grab (short) | SUIUSDT 1h | `pack100` (`strat=F75-1h`) | `30f67b5380bcd458` |
| 23 | QS-004 Donchian channel breakout | SUIUSDT 1h | `qs` (`strat=QS-004`, `variant=two-sided`) | `b48f30800df51639` |
| 24 | S46 weekend-gap fade | BTCUSDT 1h | `pack50` (`strat=46`) | `1b13cbd18f8b00eb` |
| 25 | QS-007 Higher-timeframe trend, lower-timeframe entries | HYPEUSDT 1h | `qs` (`strat=QS-007`, `variant=two-sided`) | `8551ead0bf1325fc` |
| 26 | QS-005 Time-series momentum | SUIUSDT 1h | `qs` (`strat=QS-005`, `variant=two-sided`) | `59a513a240fff675` |
| 27 | ds1 | XRPUSDT 1h | `dspack` (`strat=ds1`, `costs=author`, `window=full`) | `437c47539b4dc9ae` |
| 28 | QS-004 Donchian channel breakout | ETHUSDT 1h | `qs` (`strat=QS-004`, `variant=two-sided`) | `ec9bbc4dc8c8f218` |
| 29 | QS-006 ADX-filtered directional continuation | SOLUSDT 1h | `qs` (`strat=QS-006`, `variant=two-sided`) | `d9d44100b54c4c40` |
| 30 | QS-093 VWAP plus trade-flow confluence | JUPUSDT 1h | `qsf` (`strat=QS-093`, `variant=two-sided`) | `3630fe2670e70f15` |

Ten books, ten adapter cells, two regimes each: twenty artifacts minted.
One of them (row 27) collapses to a single artifact, see below; one extra
artifact is minted for that row's costed re-run.

## The two regimes

* **BASE** — the regime the book was published under, from the ranking
  artifact's own declared costs: `pack100` 5.5 bps per side combined with
  funding charged; `qs`/`qsf` the catalog's base ladder (5.0 fee + 2.0 slip
  bps per side, 14 bps RT) with funding at the real settlements;
  `pack50` the pack's own per-symbol block (BTC 1h: 4.0 fee + 2.0 slip bps
  per side, 12 bps RT) with funding charged; **`dspack` `costs=author` — the
  pack file declares NO costs, so the published ds1 number was measured at
  ZERO fees and ZERO slippage already** (declared in the ranking artifact's
  own params), and the engine charges no funding (kline-only).
* **ZERO** — fees 0.0, slippage 0.0 and funding cash flow 0.0, in the same
  engine bytes.

## The ds1 row is a special case, declared before the run

ds1's published regime IS the zero-cost regime (`costs=author`), so its
BASE and ZERO runs carry identical params and are the SAME artifact — the
table will show the same run_id twice for row 27, and that identity is the
point: for this book the informative comparison runs the other way. A third
artifact with `costs=repo6x5` (the engine's 6 + 5 bps per side preset) is
minted for row 27 to answer the campaign's question for it: what the same
signals do once money is actually charged. This extra run is a measurement
of the row, not a new regime of the campaign; no gate is evaluated on it.

## Switches, and what must NOT change

Two adapters need new harness switches (`qsf`, `pack50`); `qs`, `pack100`
already expose theirs from batches 1-2; `dspack` already exposes `costs`
natively (`author` / `repo6x5` presets in the engine). All switches live in
`code/vrun.py` and are ADDITIVE:

* `qsf`: the same switch `qs` received in batch 2 — `costs` ("repo" |
  "zero") zeroes the module's four-point COSTS ladder (the random-entry null
  included); `funding=False` withholds the funding JSON from the engine.
  Same engine module (`qs_run`), same engine files, byte-untouched.
* `pack50`: `costs` ("repo" | "zero") replaces the pack's per-symbol cost
  table (`S.costs_for`) with `(0.0, 0.0)` on the module object, restored in
  a finally; `funding=False` withholds the funding JSON, which flips the
  ENGINE'S OWN `funding_charged` flag and routes it through the engine's
  empty-funding path. The engine's internal zero-fee control
  (`zero_cost_ret_pct` / `zero_cost_pf`) keeps real funding in BASE — the
  same precedent as `pack100`'s `zero_cost_pf`.
* **Engine files are byte-untouched.** `qs_run.py`, `qs_engine.py`,
  `qs_strats.py`, `qs_flow_strats.py`, `pack50_engine.py`, `pack50_core.py`,
  `pack50_strats.py`, `dspack_engine.py`, `deepseek_pack.py` are all hashed
  into run_ids. Absent the keys every runner behaves exactly as before.
* The funding file STAYS in the hashed inputs at ZERO for every adapter
  whose runner withholds it from the engine (the batch 1-2 precedent: the
  regime is distinguished by the params key, and the audit proves the
  engine charged nothing). `pack50` is the exception where the ENGINE
  itself declares `funding_charged=false` because no funding file was
  handed to it.

## Falsifiable expectations, declared before running

* If a book was killed by cost, ZERO must move it above BASE; the gap is the
  measured cost drag. A ZERO number larger than BASE is NOT an edge claim.
* For ds1 the gap must be ZERO by construction (identical params), and the
  `repo6x5` re-run must land far below it — that is the row's answer, not a
  surprise to be explained after the fact.
* The qs/qsf four cost points (base/adverse/stress/gate) must COINCIDE at
  ZERO — the same internal consistency check batch 2 declared.
* pack50's internal `zero_cost_pf` (zero fees, funding still charged) must
  sit BETWEEN its BASE and its ZERO headline in the ZERO artifact ordering
  sense — closer to the ZERO headline the smaller the funding bill is.
* Funding sign conventions differ per engine and are quoted AS STORED:
  `qs`/`qsf` `funding_paid` positive = paid; `pack100` `funding_paid`
  negative = paid (net cash flow); `pack50` `funding_paid` positive = paid.
  No cross-engine funding comparison is made.

## Addendum, 2026-11-20 (after the first audit pass, before publication)

The mechanics paragraph above says exact reproduction may only be claimed
where the ranking's input bytes are unchanged. The first audit pass found a
stronger and cleaner pattern: on eight of the ten rows the ONLY grown inputs
are funding JSON tail records (HYPE, SUI, ETH, SOL, BTC funding files), and
the BASE figures STILL reproduce the published numbers to full float
precision (for example B17-1h at 53.725699562835615, both regimes of the
equity path identical). Bit-exact equality of the whole equity-derived
metric set is itself the proof that the appended funding records never
touch an open position in the measured window — no separate byte-level
argument is needed. The audit's reproduction check was therefore rewritten
BEFORE any number was published: equality to the published figure is
accepted as exact reproduction with the grown-input list quoted; an
inequality is only accepted when an input file really grew (a difference on
byte-unchanged inputs would be an alarm). Only ds1 (XRP 1h klines grew) and
QS-093 (JUP klines and funding grew) are true re-measurements. Nothing else
in this pre-registration changes.

## Mechanics

* `code/_zerocost_rows21_30_matrix.py` mints the artifacts and writes
  `results/zerocost_rows21_30_matrix.json`.
* `code/_zerocost_rows21_30_audit.py` must pass before publication:
  identity (BASE == the engine with its native constants), independent
  zero-cost recomputation (fresh module, constants set by hand), the
  engines' own published zero-cost references (`zero_cost_pf` for pack100
  and pack50, `drag_pp` for dspack), and exact reproduction asserted only
  where the ranking's input bytes did not change.
* `guard --strict` must pass on the report before it is published.
* BASE artifacts are re-measurements on today's bytes, not copies of the
  published numbers; only rows whose inputs are byte-unchanged may claim
  exact reproduction.
