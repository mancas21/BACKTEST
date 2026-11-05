# XRP paper bot — delta-neutral 15m book

**Paper only.** No orders, no keys, no account access. This report exists so the
bot's numbers are backed by an artifact instead of by a status file on a VPS.

> **Superseded by v2 (25 USDT x 10x), artifact `7737dd3dc499721f`.** This report
> is the v1 record (10,000 USDT / 0.25x per level). Its numbers still verify; the
> deployed bot is the v2 experiment in `results/xrp_neutral_25x10_report.md`.

- strategy key: `xrpneutral`, symbol `XRPUSDT`, timeframe `15m`
- artifact: `8bf3575619eda66f` (schema `bt-artifact/1`)
- engine: `code/xrp_neutral_engine.py`, version `xrp-neutral-1`, sha `e6f7422f53d3`
- reproduce: `python code/vrun.py run --strategy xrpneutral --tf 15m --symbol XRPUSDT`
- verify: `python code/vrun.py verify 8bf3575619eda66f` → OK, reproduces bit-for-bit

`verify` proves **determinism, not correctness**. It re-runs the same bytes on the
same inputs and gets the same output. The correctness checks (no-trade control,
per-trade symmetry, funding sign, delta cap, no look-ahead, accounting identity)
live in `code/xrp_neutral_audit.py`, which is a separate script.

## Inputs

| input | bars | window |
|---|---|---|
| `XRPUSDT_15m.csv` | 238197 | 2020-01-06 .. 2026-10-22 |
| `XRPUSDT_funding.json` | 7444 | 2020-01-06 .. 2026-10-22 |

Both files are hashed into the artifact. Funding covers the whole price window
(`funding_covers_bars` is true); a truncated history would silently change the
equity, so this is checked rather than assumed.

## Headline, full history

| metric | value |
|---|---|
| closed lots | 5876 |
| net return | 1589.38% |
| profit factor | 1.50 |
| expectancy per lot | 27.09 |
| max drawdown | 10.18% |
| fees paid | 47785.84 |
| final equity | 168937.88 (from 10000) |
| buy & hold, same window | 572.23% |

## Accounting identity

The tables are **net of fees**, not gross. The engine stores each lot's entry fee
at open and subtracts it together with the exit fee at close, so `fees` is a
total, never a second deduction.

| item | value |
|---|---|
| sum of per-trade P&L | 159203.50 |
| funding paid | 265.62 |
| net P&L | 158937.88 |
| equity change | 158937.88 |
| identity gap | 0.00 |

## Neutrality — measured, with a control

| metric | value |
|---|---|
| average abs(net notional) / equity, per bar | 4.01% |
| maximum, per bar | 50.03% |
| maximum at fill time | 50.50% |
| delta cap | 50% |
| fill attempts refused by the cap | 20830 |

The cap is enforced on the **pre-fill** equity: a fill is refused if its notional
would breach the bound. The two maxima above are post-fill marks, and they can sit
a fraction over the cap when price gaps through a resting order or when equity
falls after the fill. The number that describes the book is the average: 4.01%.

The control is the same book with the short side switched off. If the two-sided
book were just long beta in disguise, this comparison would show it.

| book | net return |
|---|---|
| neutral, two-sided | 1589.38% |
| long-only control | 648.41% |
| difference | 940.97 pp |

A short-only mirror is run separately in `code/xrp_neutrality_check.py`; it is
not part of this artifact.

Both sides carry P&L, which is the point:

| side | trades | P&L | PF | win rate |
|---|---|---|---|---|
| long | 3564 | 99937.83 | 1.52 | 87.04% |
| short | 2312 | 59265.66 | 1.46 | 86.46% |

## Exits, and an honest reading of the win rate

| reason | count | P&L | win rate |
|---|---|---|---|
| cover | 5023 | 470579.21 | 100.00% |
| stop | 679 | -304952.17 | 0.00% |
| trend | 174 | -6423.54 | 44.83% |

The headline win rate of 86.81% is **structural, not an edge statistic**: a lot
that reaches its cover is a win by construction and a lot that stops is a loss by
construction. The edge statement is the profit factor of 1.50 and the expectancy
of 27.09 per lot, where 679 stops carry the losses.

This table counts **closed lots**. The bot's status file counts stop *triggers*
instead, including triggers that fire with no lots open after a run of covers, so
its `exit_reasons` counter is not comparable to this one. When the two disagree,
this table is the one built from the actual fills.

## Robustness

| gate | value |
|---|---|
| best five trades, share of P&L | 2.04% |
| net return without them | 1559.48% |
| bootstrap draws | 20000 (seed 7) |
| mean per-trade P&L, bootstrap interval | 20.78 .. 33.21 |
| t-statistic | 8.51 |
| P(mean ≤ 0) | 0.0% |
| thirds of the window | 202.30% / 220.83% / 74.12% |
| green thirds | 3 of 3 |

The concentration gate matters because a grid book can look profitable on a
handful of lucky covers. Here removing the best five trades barely moves it.

## Frozen split

The same run, cut at 2023-01-01, with the configuration untouched. This is not a
re-fit and not a second optimisation: it shows the edge is not carried by one
regime.

| segment | value |
|---|---|
| train, to 2023-01-01 | 365.46% |
| test, from 2023-01-01 | 262.95% |
| test trades | 3328 |
| test profit factor | 1.47 |
| test win rate | 86.54% |
| test max drawdown | 5.45% |

Still a subsample of history, not a live out-of-sample. The forward paper window
is the only honest OOS this book will ever have.

## Costs

| item | value |
|---|---|
| maker fee per leg | 2 bp |
| taker fee (stops, flattens) | 5 bp |
| slippage per leg | 5 bp |
| roundtrip assumption | 14 bp |
| fees as share of abs(per-trade P&L) | 5.98% |

Fees are the dominant sensitivity, not the signal: 47785.84 paid against a final
equity of 168937.88 means a maker-fee increase moves the result more than any
parameter in the grid.

## Funding

Funding is charged on the **net** position, not per lot. A balanced book therefore
pays close to nothing: 265.62 over the whole window. This is the mechanical reason
a neutral book can survive where the long-only grid bleeds funding — and it is
also why this number is checked against the price window, because a partial
funding history once flipped its sign on the deployed bot.

## Deployed configuration

The artifact's defaults are v1's config, the book that was deployed when this
report was written:

| parameter | value |
|---|---|
| trend band | 0.10 |
| stop ATR multiple | 0.50 |
| cover multiple | 1.0 |
| delta cap | 50% |

Mechanics over the window: 1285 grids built, 5023 cycles, 5876 fills, 20967 bars
standing down under the trend overlay, 0 lots left open at the end.

## What this does NOT prove

- The full-history figure is an **upper bound**. The configuration is the winner
  of a pre-declared grid of twelve combinations, so a multiple-testing haircut
  applies and the honest OOS is the forward paper window.
- The engine is deliberately **not** `grid_audit.simulate`. That file is the
  validated long-grid engine behind the existing artifacts; adding a side flag to
  it would change its bytes and invalidate a running forward record.
- No queue position, no partial fills, no exchange outage, no funding-rate spikes
  beyond those in the history. It is a bar-close model.
- `verify` is provenance and determinism. It is not a correctness proof, and it
  never means "this will make money".

## Kill criterion

Forward window: if the paper book's forward profit factor is below 1, the bot is
stopped. No rescue loops, no re-optimisation on the forward data.
