# Repo re-audit — 2026-10-25 (execution / math / algorithmic / statistics / architecture)

ENGINEERING AUDIT NOTE — not a results report. It cites run_ids only where a
persisted artifact backs the number; the one-off diagnostic numbers from the
lookahead experiment below are UNVERIFIED DIAGNOSTICS (no artifact, run on
current extended data), labelled as such and never to be quoted as results.

Scope: deep read of the harness (`vrun.py`), `cbpack_engine.py` /
`cbpack_funding_engine.py`, `emaadx_engine.py`, `hmaaoadx_engine.py`,
`dspack_engine.py`, `fingrad_engine.py` (core executor), `xrp_neutral_engine.py`,
`xrp_paper_bot.py`, `cvrmd_backtest.py`, `smqe_engine.py`, and the audit
helpers. NOT line-audited this pass: `cbot/` suite internals, `mps20/`,
`mp20_report_ports.py`, `ffs_engine*.py`, `botstrat_backtest.py`,
`adxhma_strategy.py` (legacy, killed verdicts; flagging them as unaudited
this pass rather than pretending).

## Findings

### F1 — CRITICAL (defect; verdict direction measured CONSERVATIVE)
`xrp_neutral_engine.py:150-152` (`trend_strength`): each 15m bar is mapped
(via `searchsorted(T1, open_times, side="right")-1`) to its CONTAINING 1h bar
and reads that hour's CLOSE. For the first three 15m bars of every hour that
close is up to 45 minutes in the future at the bar's decision time — the
trend stand-down/flatten overlay is decided on future information in 3 of
every 4 bars (flag disagreement vs a last-completed-hour mapping: ~5.3% of
all bars on XRP 15m). The audit's T5 "no look-ahead" test cannot see this:
it compares a truncation at a bar count divisible by four, where the partial
hour closes at the same bar in both runs.
- Impact on published numbers: the as-is mapping reproduces the v2 artifact
  `7737dd3dc499721f` (PF 1.302, 5,963 trades, maxDD 43.42% — artifact-backed).
  A causal-mapping diagnostic re-run (UNVERIFIED, current data, no run_id)
  came out BETTER on every metric (higher PF, lower maxDD, far higher
  terminal equity), i.e. the violation biases the published record
  PESSIMISTICALLY, not favorably. The deployed bot replays only data up to
  now, so its wall-clock record is causal and unaffected.
- Required action: rebuild the engine with a causal mapping (an engine-byte
  change -> new run_ids -> re-run the 12-cell grid + gauntlet) so the
  artifact record describes a real-time-implementable strategy. Until then,
  the historical numbers carry this asterisk; the paper bot's forward record
  is the clean evidence.

### F2 — CRITICAL (metric family; understates fee load ~2x)
`emaadx_engine.py:431`: `fees_total = sum(abs(tr["qty"]) * tr["entry"] *
ck["fee"])` counts ENTRY fees only; every exit fee (half the true total) is
missing, so `fee_total` and `fee_over_gross_pct` in every emaadx artifact
read ~half of truth. The trades table itself carries correct
`fees=entry_fee+exit_fee`. Verdicts: emaadx was KILLED on PF far below 1, so
no verdict flips; but any future gate that leans on `fee_over_gross_pct`
(commission/gross < 30-40%) passes too easily for this adapter. Same-family
check: fingrad_engine sums `tr["fees"]`+open fee (correct); cbpack sums
`trades.fees` (correct); smqe fee identity is audit-pinned (correct).

### F3 — MAJOR (process; forward audit trail)
`xrp_paper_bot.py` (event-log dedup): forward trades are deduplicated on
`(ts, side)`. A stop/trend flatten closes MULTIPLE same-side lots at the same
bar — identical keys — so all but one row per (ts, side) is silently dropped
from the append-only EVENTS csv. Forward metrics are computed from the trade
list (unaffected), but any future reconciliation FROM the event log will
under-count lots. Key should include qty/entry or a sequence number.

### F4 — MAJOR (consistency; two ports of one Pine)
`fingrad_engine.py` vs `hmaaoadx_engine.py` are two independent ports of the
SAME Pine with DIFFERENT declared bracket conventions (fingrad anchors the
bracket at the signal close on the fill bar and re-anchors to
position_avg_price from the next close; hmaaoadx arms from the fill price at
the fill bar). At most one matches TradingView exactly. Each passes its own
known-answer audit, but no cross-port parity gate exists; run both on the
same bars and reconcile, or document which one deviates and why it is
accepted. (Their published verdicts are both KILLED, so no decision is at
risk.)

### F5 — MAJOR (known execution optimism, documented cross-file)
`emaadx_engine.py` (and `cvrmd_backtest.py`): stop orders on gap-through bars
fill AT THE STOP LEVEL, not at the open (TradingView fills market orders at
the open when gapped through). On violent bars the port books a better exit
price than reality. fingrad/hmaaoadx model gap fills at the open correctly;
the fingrad docstring explicitly notes "the adxhma port did not". Affects
emaadx/cvrmd-class results optimistically on rare bars; both families are
KILLED/SUSPENDED anyway.

### F6 — MAJOR (intra-bar ordering inconsistency)
`cvrmd_backtest.py` (long branch ~line 118, short ~line 149): the TP1 partial
is evaluated BEFORE the stop on the same bar — a wide-range bar touching both
books the partial first (optimistic), contradicting the repo's declared
SL-first-on-ties convention used by every other engine. Rare bars; cvrmd is
already killed/suspended; consistency debt only.

### F7 — MAJOR (recorded metric wrong by 1e6; no report impact)
`dspack_engine.py:571,663` (`_spacing` / `bars_per_year_measured`): the index
is datetime64[ms] (pandas 3 keeps the unit), so `view("int64")` returns
MILLISECONDS, but the consumer divides by 1e9 assuming NANOSECONDS. Every
dspack/dspack2/hmaaoadx artifact records `bars_per_year_measured =
8766000000.0` where the docstring promises 8766. The value is recorded, never
used (sharpe uses the 8760 constant), and no report cites it — but it is a
wrong number sitting in published artifacts, and the module docstring
contradicts the code.

### F8 — MINOR (latent warmup contamination, unreachable)
`cvrmd_backtest.py:41-42,102-103`: `np.roll` wraps circularly, so
`slope[1..4]` and the RSI-rising flag at bars 0..4 read series values from
the END of the data (future). The executor starts trading at bar 500, so no
trade can be affected; still, the signal ARRAYS at the head are wrong and
any future reuse of them before bar 5 inherits future data.

### F9 — MINOR (metric semantics drift across adapters)
`win_rate`: fraction (cvrmd/botstrat/ffs adapters) vs percent (everything
else). `conc_net_without_top5_pct`: percent of total PnL (emaadx, cbpackf,
smqe) vs percent of STARTING EQUITY (dspack family). Same metric name,
different units — a cross-adapter table or report written loosely would
compare incommensurables. Document a units table or rename.

### F10 — MINOR (version fragility, fails SAFE)
`dspack_engine.load_csv` and `hmaaoadx_engine.run_suite` rely on
`df.index.view("int64")` returning MILLISECONDS (pandas 3 keeps
datetime64[ms]). On pandas <3 (ns default) the 1h spacing gate in load_csv
refuses loudly before anything silent can happen — the right failure mode —
but the ms assumption is implicit in two places (`86_400_000` day math,
`_spacing`) and deserves one assert.

### F11 — MINOR (self-audit of smqe_engine.py, written this session)
- `open_pnl_usd` marks the surviving position at `c[-1]` (last bar of DATA)
  instead of the window end `c[en]` — mispriced only for sim_end-windowed
  runs with an open position (none exist in the campaign; all windows end at
  data end).
- `fee_over_gross_pct` divides fees that include the OPEN position's entry
  fee by CLOSED-trade gross — a small denominator mismatch.
- Dead `ymask` variable in the year-table loop.
None affect any published smqe number (the fee identity, cash identity,
no-lookahead and determinism are audit-pinned, 40/40).

### F12 — NOTED (architecture, working as designed — verified this pass)
- cbpack `backtest()`: both-side fees on every fill, SL-first ties, next-open
  fills, non-overlapping walk-forward train/test bounds, end_of_data closes
  counted with reason recorded — clean.
- cbpackf funding EVENTS: settlements snap into the containing bar, multiple
  settlements in one bar are summed, gaps raise, per-trade funding inside
  pnl, parity-audited — clean.
- dspack `_asof_to_bars` (funding/OI known-at semantics), `htf_trend`
  `.shift(1)` last-completed-HTF convention — causal, clean.
- `vrun.py` verify: does not rewrite artifacts; `int 1` vs `float 1.0` JSON
  mismatch refuses (conservative); NaN==NaN equality is acceptable given
  deterministic recomputation. guard is provenance-not-correctness (known,
  documented). pmatrix prints errors per cell (no silent partial sweeps).
- The smqe adapter's conditional native-vs-taker input lambda records the
  chosen path in `inputs` (hashed) — no unhashed read.

## Verdict impact summary

No KILLED verdict changes sign under these findings. The one strategy with a
passing record — the neutral XRP book — carries F1 (information-set defect,
measured CONSERVATIVE: the causal variant is stronger, so the published
+1589%/PF 1.498 (v1) and PF 1.302 (v2) are not inflated by it), and F3
(forward log under-counts flatten events). Recommended actions, in order:
(1) rebuild `xrp_neutral_engine.py` with the causal mapping and re-run its
grid/gauntlet/artifacts; (2) fix the emaadx `fees_total` metric (F2) —
engine bytes change, so emaadx artifacts go stale-by-design and the killed
verdict re-render is mechanical; (3) fix the paper bot's dedup key (F3);
(4) add the cross-port parity gate (F4) and the ms-unit assert (F10).
