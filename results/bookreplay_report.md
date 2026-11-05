# Fill-Resolution Replay on Real Executions (bookreplay) — 2026-11-01

Adapter `bookreplay`, engine `code/bookreplay_engine.py` (v `bookreplay-1`).
Campaign: closing the four gaps left by the external master-prompt analysis
(W4b of the 2026-11-01 delta plan; W1-W3 and the recorder audit are referenced
at the end).

## What this measures

The SAME resting-maker grid resolved two ways on the SAME window and the SAME
levels, so the only difference is fill resolution:

- **MODEL TRADES** — fills resolved on real executed aggTrades (official Binance
  bulk archive, `data/aggtrades/XRPUSDT/`, sha256 manifest
  `data/AGGTRADES_XRPUSDT_IMPORT.json`, 17 contiguous days asserted by the
  engine). A resting BUY at level L fills the moment a trade prints at price
  <= L; a resting SELL at H fills on a trade at >= H. No cancel ambiguity:
  these are actual executions.
- **MODEL 15M** — the same levels on the repo's 15m bar convention: bid rung
  fills when bar.low <= L, cover when bar.high >= cover, same-bar entry+cover
  CREDITED (the optimistic convention the XRP neutral 15m engine used, and
  whose 1m-resolution audit measured that 100% of the book's trades were
  same-bar round trips).

Grid: anchored once at the first trade price, levels_per_side x spacing
below/above, no re-anchoring, cover at one rung, maker fee on every fill,
funding excluded from BOTH models, static levels, single symbol XRPUSDT.
Window: 17 days (2026-10-11 .. 2026-10-27), bounded by the trade archive.

## Cells (artifacts, both verified bit-for-bit twice)

| cell | run_id | params |
|---|---|---|
| wide | `ce46399b5b500a43` | spacing_pct 0.30, levels 5, notional 25, equity0 25 |
| kill-geometry | `ecf93a9ee8475a93` | spacing_pct 0.05, levels 20, notional 25, equity0 25 |

## Findings (all numbers from the two artifacts above)

**Wide cell `ce46399b5b500a43`** — fills_trades 51 vs fills_15m 67;
same_bar_rt_15m 24, same_bar_rt_share_pct 38.71; net_return_pct_trades
11.9598 vs net_return_pct_15m 16.1198; fill_inflation_pp 4.16. The bar
convention fabricated 24 round trips that no real execution sequence contains
(38.71 percent of its closed trades) and inflated the realized return by 4.16
percentage points over the 17 days.

**Kill-geometry cell `ecf93a9ee8475a93`** — fills_trades 948 vs fills_15m 647;
same_bar_rt_15m 439, same_bar_rt_share_pct 70.02; net_return_pct_trades 9.2801
vs net_return_pct_15m 6.2702; fill_inflation_pp -3.0099. At tight maker
distances the bias FLIPS SIGN: real trades chop through a level many times per
bar and the bar model, which allows at most one crossing episode per rung per
bar, misses most of them — while STILL fabricating same-bar covers for 70.02
percent of its closed trades.

Margin/leverage sanity (tape-model curves, full-capacity gross): wide cell
min_margin_buffer_pct 95.0, kill-geometry cell 80.01; bars_over_leverage zero
in both.

## Verdict

**The 15m OHLC bar convention is not a conservative approximation at maker
distances — it is unfaithful in BOTH directions, and neither direction is
safe.** At wide spacing it inflates (phantom same-bar covers, +4.16 pp); at
tight spacing it deflates (missed intra-bar re-crossings, -3.01 pp) while
fabricating an even larger share of same-bar round trips. This is the forward,
real-execution confirmation of the repo fill-model rule: maker/intra-bar
strategies are NOT certifiable on OHLC >= 5m bars. It does NOT resurrect the
XRP neutral book — its geometry (per-cycle re-anchoring, stop logic) is not
this probe's static grid; it does tell future campaigns that bar-resolution
numbers for resting-maker books are structurally unreliable, in either
direction.

## Provenance and orphans

- Real data only: aggTrades from the official Binance archive (hash-listed in
  each artifact's inputs), 15m klines from `data/binance_klines_15m/`.
- Intermediate engine versions during this session produced
  `014c81eae30dbcd3`, `125f32903cff2de4`, `740ea9ead28f2309` and
  `902adfb8fba3e730`; those bytes are superseded (verify exit 2, engine drift)
  and are kept append-only but are NOT citable. The citable pair is
  `ce46399b5b500a43` + `ecf93a9ee8475a93`.
- Declared in every artifact (prov.declared_simplifications): static grid, no
  re-anchoring, no queue-position modeling, fill price = level, no funding.
- Companion recorder-tape audit (quality only, no run artifacts):
  `results/recorder_replay_2026-11-01.txt` (guard OK; findings in words, exact
  figures in the sibling JSON). Headline in words: the bookTicker tape is
  clean (zero crossed events across the readable window), a majority of the
  recorded days are footerless losses from the pre-rotation kill window, the
  live `stream_breaks` counter is inflated by design (futures update ids are
  sparse; the true continuity rule is `pu == previous u`), and the REST
  snapshot id space was foreign to the websocket diff id space until the
  upgraded recorder took effect — full-book anchoring is possible only on the
  forward tape from that day.

## The other three gaps closed the same day (no artifacts needed)

- `code/datacheck_klines.py` + `data/KLINES_MANIFEST.json` + `results/klines_datacheck_2026-11-01.txt`
  (guard OK): every kline CSV under `data/binance_klines*/` is monotonic,
  gap-free, OHLC-valid; manifest carries per-file sha256.
- `code/quant_metrics.py` VaR/CVaR added (known-answer selftest
  `code/_quant_metrics_selftest.py` ALL PASS; existing artifacts untouched;
  `stats` output diff = only the new tail-risk section).
- `code/fetch_instruments.py` + `code/instruments_check.py` +
  `data/INSTRUMENTS_MANIFEST.json`: current exchangeInfo snapshot, cross-checked
  live for three symbols; point-in-time historical rules remain unavailable
  (limitation recorded in the manifest).
