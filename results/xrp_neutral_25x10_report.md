# XRP paper bot — delta-neutral 15m book, 25 USDT × 10x

**Paper only.** No orders, no keys, no account access. This report exists so the
bot's numbers are backed by an artifact instead of by a status file on a VPS.

- strategy key: `xrpneutral`, symbol `XRPUSDT`, timeframe `15m`
- artifact v2: `7737dd3dc499721f` (schema `bt-artifact/1`)
- artifact v1, previous sizing, kept as the record: `8bf3575619eda66f`
- engine: `code/xrp_neutral_engine.py`, version `xrp-neutral-1`, sha `e6f7422f53d3`
  (the file is unchanged; the sizing is a parameter, not a fork)
- reproduce v2:
  `python code/vrun.py run --strategy xrpneutral --tf 15m --symbol XRPUSDT --set init=25 --set equity_pct=1.0 --set delta_max_pct=2.0 --set leverage=10.0`
- verify v2: `python code/vrun.py verify 7737dd3dc499721f` → OK, reproduces bit-for-bit

`verify` proves **determinism, not correctness**. It re-runs the same bytes on the
same inputs and gets the same output. The correctness checks (no-trade control,
per-trade symmetry, funding sign, delta cap, no look-ahead, accounting identity)
live in `code/xrp_neutral_audit.py`, which is a separate script.

## What changed from v1, and why

v1 sized 0.25x equity per level on a 10,000 book, with a 0.5x delta cap. v2 is the
requested **25 USDT × 10x**. That is a capacity statement: 5 levels per side ×
25 USDT = 250 USDT of maximum gross notional. It is not an average exposure.

The delta cap had to move with the sizing. At 25 USDT and 1x equity per level, a
single lot is 25 USDT; a 0.5x cap would refuse the first fill and the bot could
never trade. The cap is 2.0x equity (two net lots), which preserves v1's
lot-level neutrality (at most two net lots) while leaving the full 10x gross
capacity reachable when both sides are filled.

The twelve-cell parameter grid was re-run at the new sizing, unchanged in its cells.
Two of the twelve cells clear the pass conditions, and the winner is the same
cell as v1: `trend_band 0.10`, `stop_atr_mult 0.50`, `cover_mult 1.0`. It is the
maximum of a pre-declared grid, so a multiple-testing haircut still applies.

## Inputs

| input | bars | window |
|---|---|---|
| `XRPUSDT_15m.csv` | 238197 | 2020-01-06 .. 2026-10-22 |
| `XRPUSDT_funding.json` | 7444 | 2020-01-06 .. 2026-10-22 |

Both files are hashed into the artifact. Funding covers the whole price window
(`funding_covers_bars` is true); a truncated history would silently change the
equity, so this is checked rather than assumed. The VPS has pulled a few bars
past this snapshot; its day-0 is later. The artifact remains the reference for
the backtest, and the forward record starts at its own day-0 bar.

## Headline, full history

| metric | value |
|---|---|
| closed lots | 5963 |
| net return | 9197370.36% |
| profit factor | 1.302 |
| expectancy per lot | 385.81 |
| max drawdown | 43.42% |
| fees paid | 1144146.14 |
| funding paid | 1218.61 |
| final equity | 2299367.59 (from 25.00) |
| buy & hold, same window | 572.23% |

All USDT figures in this table are **engine-scale**: the replay starts at 25.00
in 2020 and compounds, so 2299367.59 is six years of compounding, not the
deployed account's current equity. The deployed account starts at 25.00 at its
day-0 (2026) and is normalised (see below).

The terminal return is a **compounding artifact**: at 1x equity per level the book
reinvests every win, and 25 USDT becomes 2299367.59 over the window. It is an
upper bound, not a forecast. The decision metrics are the profit factor of 1.302,
the max drawdown of 43.42%, and the fact that all three thirds are green.

## Sizing and margin — measured, not assumed

| metric | value |
|---|---|
| equity | 25.00 |
| leverage cap | 10x |
| gross capacity | 250.00 |
| levels per side | 5 |
| equity per level | 1.0x |
| delta cap | 200% of equity |
| max gross leverage reached | 2.14x |
| bars over the 10x cap | 0 |
| minimum margin buffer | 98.93% |

"10x" is a ceiling. The grid covers quickly and rarely holds more than two lots,
so the maximum gross actually reached is 2.14x, and equity stayed 98.93% above
the maintenance line (0.5% of gross, the base tier). A cell that breached
maintenance would be dead, not profitable; `bars_over_leverage` is 0.

## Neutrality — measured, with a control

| metric | value |
|---|---|
| average abs(net notional) / equity, per bar | 16.11% |
| maximum, per bar | 214.35% |
| maximum at fill time | 205.53% |
| delta cap | 200% |
| fill attempts refused by the cap | 19848 |

The cap is enforced on the **pre-fill** equity. The two maxima above are post-fill
marks and can sit a little over the bound when price gaps through a resting order
or when equity falls after the fill; the fill-time maximum is also a post-mark.
The number that describes the book is the average: 16.11%.

The control is the same book with the short side switched off. If the two-sided
book were just long beta in disguise, this comparison would show it.

| book | net return |
|---|---|
| neutral, two-sided | 9197370.36% |
| long-only control | 260983.81% |
| difference | 8936386.55 pp |

Both sides carry P&L, which is the point:

| side | trades | P&L | PF | win rate |
|---|---|---|---|---|
| long | 3573 | 899962.20 | 1.183 | 87.15% |
| short | 2390 | 1400599.00 | 1.519 | 87.28% |

## Exits, and an honest reading of the win rate

| reason | count | P&L | win rate |
|---|---|---|---|
| cover | 5121 | 9786798.15 | 100.00% |
| stop | 667 | -7331439.16 | 0.00% |
| trend | 175 | -154797.79 | 45.14% |

The headline win rate of 87.20% is **structural, not an edge statistic**: a lot
that reaches its cover is a win by construction and a lot that stops is a loss by
construction. The edge statement is the profit factor of 1.302 and the expectancy
of 385.81 per lot, where the stops carry the losses.

This table counts **closed lots**. The bot's status file counts stop *triggers*
instead, including triggers that fire with no lots open after a run of covers, so
its `exit_reasons` counter is not comparable to this one. When the two disagree,
this table is the one built from the actual fills.

## Robustness

| gate | value |
|---|---|
| best five trades, share of P&L | 4.35% |
| net return without them | 8801886.68% |
| bootstrap draws | 20000 (seed 7) |
| mean per-trade P&L, bootstrap interval | 178.24 .. 582.96 |
| t-statistic | 3.73 |
| P(mean ≤ 0) | 0.0001 |
| thirds of the window | 8850.48% / 11357.44% / 795.58% |
| green thirds | 3 of 3 |

The concentration gate matters because a grid book can look profitable on a
handful of lucky covers. Here removing the best five trades barely moves it.

The bootstrap interval is in **compounded USDT**, so it is dominated by the late,
large book; it is not a scale-free per-unit-of-risk statistic. The t-statistic of
3.73 is weaker than v1's because compounding makes the dollar P&L distribution
heavier-tailed, not because the per-fill signal changed.

## Frozen split

The same run, cut at 2023-01-01, with the configuration untouched. This is not a
re-fit and not a second optimisation: it shows the edge is not carried by one
regime.

| segment | value |
|---|---|
| train, to 2023-01-01 | 51403.38% |
| test, from 2023-01-01 | 17757.99% |
| test trades | 3375 |
| test profit factor | 1.301 |
| test win rate | 86.87% |
| test max drawdown | 20.54% |

Still a subsample of history, not a live out-of-sample. The forward paper window
is the only honest OOS this book will ever have.

## Costs

| item | value |
|---|---|
| maker fee per leg | 2 bp |
| taker fee (stops, flattens) | 5 bp |
| slippage per leg | 5 bp |
| roundtrip assumption | 14 bp |
| fees as share of abs(per-trade P&L) | 6.53% |

Fees are the dominant sensitivity, not the signal: 1144146.14 paid against a final
equity of 2299367.59 means a maker-fee increase moves the result more than any
parameter in the grid.

## Funding

Funding is charged on the **net** position, not per lot. A balanced book therefore
pays close to nothing: 1218.61 over the whole window. This is the mechanical
reason a neutral book can survive where the long-only grid bleeds funding — and it
is also why this number is checked against the price window, because a partial
funding history once flipped its sign on the deployed bot.

## Accounting identity (engine-scale)

| item | value |
|---|---|
| sum of per-trade P&L | 2300561.20 |
| funding paid | 1218.61 |
| net P&L | 2299342.59 |
| equity change | 2299342.59 |
| identity gap | 0.00 |

## Deployed configuration

Production and this artifact are the same experiment: v2 is the artifact above,
and the VPS runner passes the same sizing explicitly.

The runner reports a **normalised account**. The engine replays 2020+ and
compounds, so its terminal equity is 2299367.59; the day-0 baseline re-bases the
reported account to 25.00 (`account_scale`) and the forward P&L is measured from
there. `engine_equity` keeps the raw scale. The scaling is exact because the
engine is linear in equity.

| parameter | value |
|---|---|
| equity | 25.00 |
| leverage cap | 10x |
| gross capacity | 250.00 |
| equity per level | 1.0x |
| trend band | 0.10 |
| stop ATR multiple | 0.50 |
| cover multiple | 1.0 |
| delta cap | 200% |

Mechanics over the window: 1285 grids built, 5121 cycles, 5963 fills, 20967 bars
standing down under the trend overlay, 0 lots left open at the end.

## What this does NOT prove

- The full-history figure is an **upper bound**. The configuration is the winner
  of a pre-declared grid of twelve combinations, so a multiple-testing haircut
  applies and the honest OOS is the forward paper window.
- 10x is a **margin setting**, not an average exposure: the book reached 2.14x
  gross. Sizing to actually run near 10x would need a different lot size and a
  higher net cap, which is a different strategy.
- The engine is deliberately **not** `grid_audit.simulate`. That file is the
  validated long-grid engine behind the existing artifacts; adding a side flag to
  it would change its bytes and invalidate a running forward record.
- No queue position, no partial fills, no exchange outage, no funding-rate spikes
  beyond those in the history. It is a bar-close model.
- `verify` is provenance and determinism. It is not a correctness proof, and it
  never means "this will make money".

## Kill criterion

Forward window: if the paper book's forward profit factor is below 1, the bot is
stopped. No rescue loops, no re-optimisation on the forward data. The status file
carries `forward_pf`, `forward_closed_lots` and `forward_closed_pnl`; closes at or
before the day-0 bar are excluded, so the forward record starts clean.
