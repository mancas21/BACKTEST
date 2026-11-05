# prompts100 survivors — formal validation runs

The five OOS survivors of the backtest_prompts100 screen through the frozen port
`code/prompts100_engine.py`, adapter `prompts100` in vrun.py. One run per
survivor, repo costs (five fee plus half-a-bp slippage per side = eleven bps
round trip). Conventions of the source screen carried over: signal on bar close,
fill at next open, stop wins ties, one-percent risk per ATR stop, the screen's
IS/OOS split by bar count. No funding charged (none of the five is a funding
strategy in the screen). All five artifacts verify bit-for-bit.

Data (frozen, hashed per artifact): BTC and ETH from the native klines dir; HYPE
native plus an appended API tail file (new data file, late-September to end of
October); JUP from the taker klines dir — a shorter window than the screen's
fetched file, so the JUP artifact is not directly comparable to its screen row.

## Results table (every number quoted from its artifact JSON)

| # | Strategy | Sym | run_id | FULL: trades / PF / net% / MDD% | OOS: trades / PF / net% / excess% | screen gates | kills |
|---|---|---|---|---|---|---|---|
| 28 | Donchian breakout | BTCUSDT | `5bab921c9169c282` | 430 / 1.37 / +113.7% / -21.4% | 138 / 1.30 / +19.2% / -24.6% | PASS both | benchmark |
| 44 | 168-bar breakout | BTCUSDT | `2c92741c86a3605a` | 161 / 2.54 / +368.0% / -21.4% | 52 / 1.52 / +18.7% / -25.1% | PASS both | benchmark |
| 60 | Keltner con RSI | HYPEUSDT | `4f8dc290e5089b0f` | 128 / 1.60 / +40.3% / -9.9% | 42 / 1.61 / +12.2% / -40.5% | PASS both | benchmark + concentration |
| 71 | Hour-of-day filter | JUPUSDT | `87d05e23be45b524` | 69 / 1.88 / +41.8% / -14.6% | 20 / 2.03 / +14.1% / -56.7% | FAIL OOS (thin) | thin + benchmark + concentration |
| 73 | Sunday-to-Monday reversion | ETHUSDT | `7045caa816d5517e` | 128 / 1.45 / +37.5% / -20.1% | 42 / 1.45 / +10.0% / +22.1% | PASS both | concentration |

Artifact paths: `results/runs/<run_id>.json`. Percent fields quoted are the
artifacts' own `full_pct` / `is_pct` / `oos_pct` blocks; the benchmark line is
`oos_pct.excess_pct` (net minus buy-and-hold over the same OOS window).

## Verdict

**Zero of the five become candidates.** The screen's gates (profit factor, trade
count, net — full and OOS) were necessary but not sufficient. The fuller gate set
kills all five on two axes the screen never tested:

1. **Benchmark.** Four of the five are long-biased books that lost to buy and
   hold over their OOS window — BTC, HYPE and JUP ripped upward through it. The
   only book that made money the market did not is #73, whose OOS excess is
   positive.
2. **Concentration.** Removing the best five trades of each book: #60 falls to
   PF 0.94, #71 to PF 0.93, #73 to PF 0.90 — each is a handful of lucky
   positions, with best-five share of net PnL above the whole book's PnL. #44 is
   the only one that survives top-trade removal (PF 1.23, top-five share 0.85);
   #28 survives it marginally (PF 1.04) — and both fail the benchmark gate
   instead.

Closest to life: **#44, the 168-bar breakout on BTC** — the highest profit factor
of the pack (2.54 full, 1.52 OOS), a robust trade count, and it holds up with its
best trades removed. Its problem is not the per-trade edge, it is the benchmark:
a long/flat breakout book on BTC over the recent window does not beat holding
BTC. That is a deployment-structure question (leverage, shorting, overlays), not
a signal question.

## Scope caveats

- These artifacts carry the screen's gate flags, not the full statistical
  campaign: no deflated Sharpe / PBO, no purged folds, no breakeven-cost
  bisection, no bootstrapped drawdown tail. Provenance carries
  `pre_registered: false` — one hundred strategies were screened to pick these
  five, so the multiple-testing haircut applies to any of these numbers.
- The trade-count gate of the repo (a hundred closed trades) is met by #28, #44,
  #60 and #73; #71 falls short of it on the repo's shorter JUP window.
- Funding: not charged, matching the screen. A live perp deployment pays funding
  on top of fees; multi-day breakout holds would pay materially more than the
  eleven bps round trip (the funding lesson in AGENTS.md).
