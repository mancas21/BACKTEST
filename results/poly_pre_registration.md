# Polymarket Up/Down — pre-registration (Phase One: recorder)

Date: October twenty-second, twenty twenty-six.
Status: **PRE-DATA. No backtest number for Polymarket exists in this repo.**
This document pre-declares what will count as evidence before the data is
collected. It carries no run_id because nothing has been run through the
harness; it is a plan, not a result. Every quantity here is written in words
under the guard convention (guard cannot distinguish plan constants from
measured results, so plans must not carry bare numerals). All measured
quantities live in the recorder files, never here.

Origin: the Qwen chat blueprint ("Trading Algorithm Market Structure", dated
October the eighteenth, twenty twenty-six — extracted in full via browser)
proposes four bots for Polymarket binary Up/Down markets: Fair Probability,
Volatility/Timing, Mo-Money Inventory, Almach Execution. The blueprint itself
contains no performance numbers — nothing to verify there — and correctly
names its opening phase as a data recorder. Per user decision: recorder and
adapter first, no backtest attempted without data.

## What Phase One records (done, smoke-proven this same day)

`code/poly_recorder.py` (standard-library-only, keyless, paper-only) watches
the hourly Up/Down series `btc-up-or-down-hourly`, `eth-up-or-down-hourly`,
`xrp-up-or-down-hourly` (all verified live this day; a Solana series does not
exist) and appends, under `data/polymarket/`:

- one snapshots CSV per series per day — one row per token per sampling
  round: top-of-book, depth sums within the one-, two- and five-cent bands of
  the best level per side (columns dep_*_w1/w2/w5), tick size, minimum order
  size, last trade price, seconds left, the venue's own `price_to_beat` and
  `final_price`, the raw Binance hourly candle open plus its open time plus
  the previous candle close, spot, and clock drift against the CLOB server;
  plus the venue fee fields RECORDED RAW (fee_type, fee_rate, fee_rebate,
  fee_taker_only, maker and taker base fees). Nothing fee-related is
  interpreted by the recorder.
- one books JSONL per series per day — the full CLOB book for both tokens of
  every sampled market, level by level.
- one settlements CSV per series — resolved markets only (resolution status
  "resolved", the "proposed" limbo is skipped because it can still flip),
  with the venue winner and an independent cross-check against the raw
  Binance hourly candle, keyed by the candle's own open time.
- a `manifest.json` heartbeat per run, for staleness watchdogs.

Cadence policy: fast sampling inside a window from a quarter hour past expiry
to an hour before expiry (six-second rounds by default), pre-open books
within four hours of a candle's start on discovery rounds only (twice an
hour), settlements polled every two minutes.

Smoke evidence (this day, several short runs totalling eight recorded
rounds, zero errors): one hundred fifty open markets discovered across the
three series; snapshots and full books written for both tokens of every
sampled market; the settlement cross-check agreed with the venue winner on
every settlement row of the first backfill (the most recent thirty resolved
hours per series — every row). The smoke finding: the venue resolves exactly
as its rules state — "Up" iff the Binance USDT hourly close is greater than
or equal to the open — confirmed against raw Binance klines obtained from
Binance itself, not against the venue's narrative. Evidence paths:
`data/polymarket/*-up-or-down-hourly/`. One settlement cross-check batch of
the smoke was regenerated after the bug below; the superseded copy is
preserved beside the live file with a `.bak` suffix naming the bug, per
the append-only discipline.

## Bugs fixed during the smoke (recorded because they would bite later)

- Binance klines "startTime" semantics: the first cross-check call returned
  the NEXT hour's candle (the endpoint returns candles whose open time is at
  or after the requested start), producing roughly half of all settlement
  rows with false disagreements. Fixed by addressing each candle by its own
  open time and by ECHOING that open time in every settlement row, so the
  alignment is auditable rather than trusted.
- Recorder timestamps are pinned at emission to a single ISO-UTC format.
- The drift column is RAW: it includes the clock endpoint's request latency
  and is not a clean clock comparison. Any future calibration must model
  that before using it.

## Open items that MUST be resolved before any backtest number exists

- **Taker fee formula. RESOLVED TO FORMULA LEVEL (this day), flagship docs:
  `docs.polymarket.com/trading/fees.md`.** The rule is, per fill in USDC:
  fee equals shares times rate times price times one-minus-price; makers are
  never charged; the per-category taker rate for crypto is seven
  hundredths, with a maker rebate of twenty percent (matching the
  recorder's raw fee rebate field exactly); fees are rounded to five
  decimals with a negligible floor below which they round to zero. The
  documented worked example (one hundred shares at a half paying one and
  three quarters USDC) intersects the recorded rate at parity. This curve
  peaks at a half and decays toward the extremes: early-candle taker
  entries pay the maximum fee — cost will likely be a first-order killer
  here too. TWO residuals before any number: (a) the replay code must
  reproduce the formula and be unit-tested against the documented worked
  example; (b) the formula must be reproduced against at least one OBSERVED
  fill once trades are visible to us. Also noted: the raw maker/taker base
  fee integer fields the venue exposes do NOT map to this formula (the docs
  say the maker rate is zero) — recorded raw, never to be interpreted as
  the operative fee. **Kill rule remaining: a number may not be published
  until residuals (a) and (b) are closed.**
- **Fill model.** Book snapshots on a six-second cadence cannot prove queue
  position or latency. Conservative default: a taker crosses the spread at
  the next snapshot after its signal, prorated by displayed depth, paying
  the documented taker fee; no maker fills are modeled until queue evidence
  exists (the venue's maker-free-plus-rebate economics are acknowledged,
  but passive fills cannot be replayed honestly from snapshots alone — this
  also limits the eventual port of the blueprint's execution bot, which is
  a passive builder by design). Any strategy only working with maker fills
  is unbackable here and is killed, not re-modeled toward a pass.
- **Coverage threshold.** A market is analyzable only if at least sixty
  percent of its in-candle rounds carry both books. Markets failing that are
  dropped, and the drop ratio is reported, never hidden.
- **Minimum data horizon before any first attempt: twenty-one days** of
  continuous recording (target of at least thirty resolved markets per
  series with full books). No "preview" numbers from a shorter window.
- **Historical backfill option (later phase):** a one-shot paginated
  settlement backfill per series. Settlement facts extend far back; books do
  not — the venue data-api trades endpoint is the only historical
  microstructure source and its fidelity must be evaluated on its own
  before any use.

## Pre-declared gates for the eventual replay (same criteria as the repo)

For a strategy cell (series times strategy times configuration):

- Gate one — profit factor (strict: entry-side fees at the verified venue
  fee formula and the declared slippage assumption included) above one
  point two.
- Gate two — at least thirty closed markets in the scored window.
- Gate three — chronological halves: profit factor above one in each half.
- Gate four — beats the trivial baseline under the same cost model: always
  buying the mid-priced side at the candle open, and separately always
  buying at the recorded open print's ask. Reverse-tuning the fill model
  toward the naive side means the signal is not alpha.
- Gate five — concentration: net PnL excluding the five most profitable
  trades is positive (the cbpackf lesson: in that pack the best five trades
  carried more than the entire net PnL).
- Gate six — cost drag measured inside the artifact (a zero-cost control
  run on the same data) and stated next to any headline.
- Gate seven — out-of-sample with frozen parameters: first chronological
  half training, second half testing. A pass whose only window is the full
  record is refused. Where the cell comes out of a search grid, the number
  of cells tried is stated (multiple-testing haircut).

Kill rules already binding:
- any unverified synthetic fill assumption wins nothing; paper first;
- settlement agreement below ninety-nine percent between venue and Binance
  candles in the recorded data means a different market — re-examine the
  settlement rules before any backtesting;
- a recorder gap (stale manifest, short day files) invalidates the affected
  window; coverage gates are computed from the recorded rounds, never
  assumed.

## What is deliberately NOT built yet

- No `vrun.py` adapter for Polymarket exists. An adapter is added only when
  there is a dataset on disk to hash, so no fake-run path exists meanwhile.
- No strategy port. The four blueprint bots are ported only after the fee
  formula is verified and the data horizon exists.
- No order placement. Everything so far is public-read and paper.
