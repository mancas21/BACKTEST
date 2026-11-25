# Pre-registration — EMA×VWAP 50-Strategy Suite (one BTCUSDT cell per row)

Date: 2026-11-25. Written BEFORE the first artifact of this campaign exists.

## What this is

The attachment `Downloads/EMA×VWAP 50-Strategy Suite-claude.md` is a
natural-language specification, not code: fifty variants of one skeleton
(fast MA crosses a reference line; a close beyond both arms a 5-bar setup;
entry at the next open; exit on a close back across the fast MA at the next
open; shorts mirror). Per AGENTS.md, the SIGNAL must be ported to Python and
audited before any number is published.

The user chose **one pair per row**: BTCUSDT is the single symbol of every
cell. The first ten rows of the top-100 control had BTC-adjacent context;
this is a separate campaign with its own pre-registration, not an extension
of that control.

## Grid, fixed before running

* One artifact per numbered row, on BTCUSDT at the row's declared timeframe.
* Native CSVs exist only at `1m`, `5m`, `15m`, `1h` and `1d`. There is no
  `3m`, `30m`, `2h`, `4h`, `6h` or `12h` file, and the user did not ask for
  resampling, so those rows are **NO DATA by construction** — never
  estimated, never silently moved to another timeframe.
* Rows that require outside data that is not on disk are also **NO DATA**:
  open interest (30, 37), perp–spot basis (32), liquidation tape (35) and
  BTC dominance / alt-only context (34, 38). Funding (29) would be available
  but that row is 3m, so it is NO DATA for the timeframe reason.
* The CVD proxy (31) and taker buy/sell ratio (33) are computed from the
  taker fields of the BTC 5m kline CSV (`taker_buy_base`) and are declared
  approximations of the author's "CVD" and "taker flow". The funding
  settlement guard (36) uses the real BTC funding JSON at 00/08/16 UTC.

Rows expected to run: 1, 4, 5, 6, 7, 8, 10, 11, 13, 14, 15, 18, 19, 20, 21,
23, 24, 28, 31, 33, 36, 42, 43, 44, 49, 50. The remaining rows are declared
NO DATA in the report with their reason; no number is fabricated for them.

## Execution conventions (declared, not tuned)

* Signal on the closed bar; entry and exit filled at the NEXT bar's open.
* The cross arms the setup for 5 bars; the entry is the first close beyond
  BOTH the fast line and the reference line inside that window.
* One position per symbol, both directions mirrored; full-equity
  compounding 1x; no leverage cap needed; no stops except where the row
  explicitly defines one (rows 44–45 use R = 1.5×ATR(14)).
* Tie rule: on a bar where an entry and an exit condition both hold, the
  exit of an existing position is processed first, then a new entry.
* VWAP anchors reset at 00:00 UTC (daily), Monday 00:00 UTC (weekly), the
  1st at 00:00 UTC (monthly); the first 15 bars after a reset are skipped
  for entries. Custom anchors (07:00 UTC, 13:30 UTC, swing low, week low,
  90-day low, 30-day rolling) are computed from the served bars only.
* Costs: repo gate 5.0 bps fee + 0.5 bps slippage per side (11 bps RT),
  funding charged at the REAL settlement instants from the BTC funding JSON.
  The author's own block (0.04% taker + 1–2 bps slippage per side, no
  funding) is measured inside each artifact as a declared sensitivity, not
  as the headline. Zero-cost / no-funding controls are also measured in
  every artifact.
* Daily rows use the repo's `binance_klines_1d` file, which starts in 2026
  by construction; a cell with too few trades is labelled NO VERDICT, not a
  pass.

## Validation

* `code/_emavwap50_engine.py` is copied into `code/` (engine source hashed
  into every run_id). Known-answer tests cover every indicator family
  (EMA/HMA/ZLEMA/DEMA/TEMA/KAMA/ALMA, all VWAP anchors), both directions of
  entry/exit, cost charging on entry AND exit, funding sign, gap-through
  fills and the accounting invariant `eq[-1] − INIT == sum(pnl)` asserted
  inside each artifact.
* Every artifact asserts that invariant and publishes its cost fields,
  trade count, PF, net return, drawdown, buy & hold, funding paid and a
  zero-cost control. No number is assembled by the reader from others.
* Gate battery: the repo's screen floor (PF ex-cost > 1.2, n >= 30, cost
  share < 30–40%, period split, no extreme concentration, buy & hold
  comparison) is applied and printed as a verdict per cell. Walk-forward
  and bootstrap are measured inside each artifact. This is a fresh
  strategy family judged ONLY on its own artifacts (REGLA 1): the kill list
  of other EMA/crossover families is context, never a pre-gate.
* `vrun.py pverify` must be bit-for-bit clean on every artifact;
  `vrun.py guard --strict` must exit 0 on the report before publication.
