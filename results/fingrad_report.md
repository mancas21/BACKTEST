# Fingrad HMA · AO · ADX — audit and backtest report

Date of record: 2026-10-23. Source of record:
`code/fingrad_hma_ao_adx_strategy.pine` — the attached
`Downloads/fingrad_hma_ao_adx_strategy.pine` copied byte-identical
(sha256 `d3aabd19a1795f30...`). Engine: `code/fingrad_engine.py`
(adapter `fingrad`, engine version `fingrad-1`). Every number below is read
from a persisted artifact in `results/runs/` cited by its `run_id`; all
one hundred fourteen cited artifacts (of one hundred twenty fingrad artifacts on disk)
reproduce bit-for-bit under `python code/vrun.py verify <run_id>`.
The known-answer audit is `results/fingrad_audit_known_answers.txt`:
twenty-two checks, ALL PASS, covering the indicator primitives against naive
references, hand-computed execution answers (next-open fills, edge trigger,
first-bar vs fill-anchored brackets, gap-through stops, reversal economics,
leverage cap, daily breaker), the cash identity with funding, a no-lookahead
truncation proof on real data, a vectorized-vs-loop dual of the whole signal
layer across every signal mode and ADX mode, and harness determinism.

## VERDICT: KILLED — the same verdict as every directional Pine port before it

No configuration passes the repo gate. Counted from the eighty-nine author-cost
cells across the signal modes, ADX modes, presets and timeframes below:

- Profit factor above the threshold with a trade count of at least thirty:
  five of eighty-nine cells.
- Of those, cells that ALSO clear the concentration gate (best five trades
  under full PnL): one. Every cell that clears profit factor
  fails concentration except one (the Day-preset ETH cell below).
- Cells whose first and second halves are both positive AND at least two of
  three thirds green: see the period columns in the tables — the winners'
  second halves and thirds go negative.
- Cells that beat buy & hold on the same bars: nine of eighty-nine —
  every one of them on SPXUSDT and SUIUSDT, the symbols whose own buy & hold was
  negative over the window (losing less than a falling market is not alpha).
- Cells with a positive net return at author costs: fifteen of eighty-nine,
  and every one of them is carried by its best five trades
  (top-five shares from about one hundred to over five hundred percent of
  total PnL, except the Day-preset ETH cell).

The zero-cost control is the interesting part, as with `cbpack`: several
symbols carry a real gross edge (BTC's zero-cost return is
42.39% against a costed -28.11%;
ETH's is 88.73% against 17.77%).
It is a cost problem, not a signal problem — and even at zero cost no cell
comes within an order of magnitude of passive holding on the same bars.

## What the Pine actually is (static audit)

The strategy runs two systems over one Hull MA on bar closes, orders filling
at the next bar's open (`process_orders_on_close = false`), commission of one
twentieth of a percent per side and a two-tick header slippage:

- System A: long when price closes above the HMA and the Awesome Oscillator
  is above zero and rising; short mirrored. Exit on the HMA close rule or the
  AO flip (the shipped default in non-B modes).
- System B: long when price closes above the HMA and ADX crossed above its
  threshold within a three-bar window with +DI leading; short mirrored —
  both sides use the cross-ABOVE event, direction comes from DI. The shipped
  "Literal" mode instead shorts on ADX crossing BELOW the threshold.
- Triggers are edge-triggered on the WHOLE state (signal mode AND HTF HMA
  direction AND cost gate), so a flicker of the cost gate or the HTF filter
  re-arms a fresh entry.
- Optional ATR hard stop (default on, twice ATR of the signal bar, distance
  frozen at the signal and re-anchored to the real fill by the management
  block), risk-based sizing of one percent of equity per stop distance capped
  at ten times notional, a daily-loss breaker at three percent of day-start
  equity, and a reverse-on-opposite-signal rule.

Findings, all pinned by the audit:

1. The HTF filter is the standard NON-repainting idiom (`request.security`
   with `lookahead_on` and the first/second prior HTF values): every chart bar
   sees the last two CLOSED higher-timeframe bars. The port reproduces the
   mapping exactly (audit checks D4/D5: hand-computed pairs, and changing the
   forming HTF bar moves nothing).
2. Same-direction fresh signals while positioned are unreachable no-ops (the
   `okL/okS` gate blocks them), so pyramiding never actually rejects anything.
   Cleaner than the `emaadx` Pine, which re-armed brackets in that case.
3. The header's two-tick slippage is effectively zero on these series while
   the strategy's own cost gate assumes one basis point per side. Both
   regimes are reported (`author` = the header, `repo6x5` = the repo's six
   plus five basis points per side; `zero` = control inside every artifact,
   `drag_pp` measured in-artifact).
4. TradingView strategies carry no funding model. The adapter can charge the
   real Binance settlements; measured effect below is negligible for this
   book, with a coverage caveat on four symbols.
5. With the Custom preset on a one-hour chart the HTF timeframe equals the
   chart timeframe — the "HTF filter" degenerates to a same-timeframe
   two-bar HMA slope filter. The Pine itself warns about this. The Day
   preset (thirty-four HMA / two hundred forty minute HTF) is the
   non-degenerate one-hour configuration and is measured as its own grid.
6. The daily breaker is near-inert at one hour — eight of the
   seventy-eight author-cost one-hour
   cells record any halt, at most two in a cell — while at
   fifteen minutes it fires in nine of twelve
   cells, up to three hundred two halts in one cell: the strategy keeps
   re-entering a falling day and the breaker keeps closing it.

## Results — one hour, shipped defaults (confluence, Custom preset, author costs)

| symbol | run_id | n | net % | PF | win % | maxDD % | B&H % | zero-cost % | drag pp | top-5 share % | green years |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ADAUSDT | 16089275ff48f91d | 842 | -25.81 | 0.831 | 32.7 | 40.8 | 307.7 | 5.52 | 31.33 | — | one of seven |
| AVAXUSDT | d3f416558ec09e59 | 764 | 4.28 | 1.025 | 33.6 | 18.1 | 141.9 | 39.58 | 35.31 | 568.2 | four of seven |
| BNBUSDT | a1df8c5722afc7ef | 887 | -34.38 | 0.819 | 30.8 | 36.6 | 2766.2 | 16.38 | 50.76 | — | two of seven |
| BTCUSDT | 749fc2eb9842d522 | 897 | -28.11 | 0.876 | 30.0 | 50.6 | 715.8 | 42.39 | 70.50 | — | three of eight |
| DOGEUSDT | ba6af07446f23007 | 778 | -20.90 | 0.872 | 31.1 | 26.7 | 2042.4 | 10.50 | 31.40 | — | four of seven |
| ETHUSDT | 56e238818e8cc08a | 865 | 17.77 | 1.080 | 32.0 | 22.0 | 1556.1 | 88.73 | 70.96 | 271.7 | five of eight |
| HYPEUSDT | 7934143c44479833 | 162 | 6.67 | 1.206 | 35.8 | 6.6 | 176.4 | 13.31 | 6.64 | 254.7 | two of two |
| LINKUSDT | 424ea5214eacefc3 | 870 | -23.27 | 0.862 | 32.6 | 25.9 | 330.7 | 7.46 | 30.73 | — | one of seven |
| NEARUSDT | b3dc6d8f0c114142 | 794 | -15.82 | 0.900 | 34.1 | 27.1 | 345.7 | 9.14 | 24.96 | — | two of seven |
| SOLUSDT | b406758485d91ba4 | 815 | -33.92 | 0.791 | 30.9 | 34.7 | 2990.4 | -9.62 | 24.30 | — | two of seven |
| SPXUSDT | ec91eb01e582fba1 | 250 | -14.26 | 0.742 | 35.6 | 19.1 | -29.1 | -9.31 | 4.95 | — | one of three |
| SUIUSDT | 16126bd5d2324a43 | 412 | 14.22 | 1.155 | 37.1 | 7.7 | -27.8 | 32.13 | 17.91 | 153.7 | four of four |
| XRPUSDT | 68fd0f1ef6349e7b | 828 | -33.90 | 0.804 | 30.4 | 36.0 | 536.7 | 0.48 | 34.37 | — | two of seven |

Win rate sits near a third on every symbol; the loss is uniform, not
symbol-specific. On every symbol whose buy & hold was positive, holding beats
the strategy by one to two orders of magnitude; the only cells that beat
passive sit on SPXUSDT and SUIUSDT, where passive itself lost.
`top5 share` is the best five trades as a percent of
total PnL (blank when total PnL is negative): where the book makes money, a
handful of trades carries all of it — ETH makes
17.77% net with a top-five share of
271.7% and would have made -171.74%
without those five trades.

## One hour, System B only (HMA + ADX, cross mode, author costs)

| symbol | run_id | n | net % | PF | maxDD % | B&H % |
|---|---|---|---|---|---|---|
| ADAUSDT | d9b7f49100445294 | 885 | -26.40 | 0.835 | 39.0 | 307.7 |
| AVAXUSDT | 421c6d03e4c884ee | 795 | -3.78 | 0.978 | 19.8 | 141.9 |
| BNBUSDT | cde216c4803b432c | 921 | -36.66 | 0.816 | 40.3 | 2766.2 |
| BTCUSDT | f4e45332a51935a7 | 935 | -29.14 | 0.876 | 52.4 | 715.8 |
| DOGEUSDT | 0f6f287d43830c50 | 827 | -23.06 | 0.865 | 28.5 | 2042.4 |
| ETHUSDT | 7b9729782cba2987 | 895 | 21.45 | 1.092 | 21.5 | 1556.1 |
| HYPEUSDT | e5bb19d43e627b8e | 167 | 7.25 | 1.221 | 6.1 | 176.4 |
| LINKUSDT | 08d59a18157567e4 | 909 | -26.43 | 0.849 | 30.7 | 330.7 |
| NEARUSDT | a1721cf757d44b91 | 821 | -16.03 | 0.902 | 27.3 | 345.7 |
| SOLUSDT | 128a29ff464d5c03 | 846 | -29.21 | 0.833 | 31.6 | 2990.4 |
| SPXUSDT | 8e544129009a962a | 258 | -14.46 | 0.751 | 19.2 | -29.1 |
| SUIUSDT | d954d5040a35b06e | 427 | 16.17 | 1.168 | 7.4 | -27.8 |
| XRPUSDT | 5a67e42976fe684b | 875 | -35.47 | 0.799 | 37.3 | 536.7 |

Removing the AO leg changes the shape but not the verdict — same uniform
loss, same concentration problem on the positive cells.

## One hour, Literal ADX mode (short on ADX crossing BELOW the threshold)

| symbol | run_id | n | net % | PF | maxDD % | B&H % |
|---|---|---|---|---|---|---|
| ADAUSDT | 73c5156c430a98f1 | 538 | -14.08 | 0.872 | 27.9 | 307.7 |
| AVAXUSDT | 2bd00a42643ef8a2 | 550 | -0.60 | 0.995 | 16.5 | 141.9 |
| BNBUSDT | 902a2f886b8f8a31 | 583 | -16.91 | 0.875 | 24.2 | 2766.2 |
| BTCUSDT | 4e8e06374142dc91 | 667 | -32.29 | 0.791 | 45.3 | 715.8 |
| DOGEUSDT | 5e0c8cf376d1e83a | 505 | -14.29 | 0.858 | 26.0 | 2042.4 |
| ETHUSDT | 5f51ef3458ef1fe2 | 555 | 34.40 | 1.258 | 13.4 | 1556.1 |
| HYPEUSDT | 2288aa01825d36ca | 137 | 8.84 | 1.327 | 4.2 | 176.4 |
| LINKUSDT | 6fd245c24170ff8e | 578 | -21.93 | 0.805 | 23.2 | 330.7 |
| NEARUSDT | ef7120886d75d229 | 612 | -10.01 | 0.914 | 18.4 | 345.7 |
| SOLUSDT | 407a2588ab7a8404 | 559 | -14.21 | 0.882 | 19.8 | 2990.4 |
| SPXUSDT | 0ebf8ffd7471ba5a | 211 | -20.61 | 0.568 | 21.9 | -29.1 |
| SUIUSDT | 47cdfc5c5798271b | 289 | 11.46 | 1.177 | 11.0 | -27.8 |
| XRPUSDT | ec2f265c20361cfd | 512 | -10.72 | 0.901 | 15.8 | 536.7 |

This is the best-looking family and exactly the trap the repo's gates exist
for: ETH shows PF 1.258 at
34.40% net, but its best five trades carry
132.5% of total PnL (without them the book is
-32.54% of PnL), and it makes
34.40% where holding makes 1556.1%.
HYPE shows PF 1.327 on
137 trades with a top-five share of
167.6%. These cells are selections — the best
of eighty-nine — and fail concentration and the passive benchmark
simultaneously.

## One hour, Day preset (HMA thirty-four, HTF two hundred forty minutes)

| symbol | run_id | n | net % | PF | win % | maxDD % | B&H % | zero-cost % | drag pp | top-5 share % | green years |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ADAUSDT | 371521fb4642449c | 785 | 1.85 | 1.009 | 34.9 | 23.4 | 307.7 | 41.13 | 39.28 | 1339.0 | four of seven |
| AVAXUSDT | 256a2bee063b82b4 | 738 | -10.23 | 0.948 | 35.1 | 23.0 | 141.9 | 18.94 | 29.17 | — | one of seven |
| BNBUSDT | 22f99befc300660b | 826 | -36.34 | 0.846 | 32.0 | 41.8 | 2766.2 | 9.19 | 45.54 | — | two of seven |
| BTCUSDT | 3da3a1a758cdd47b | 803 | -20.95 | 0.914 | 29.8 | 42.1 | 715.8 | 45.36 | 66.32 | — | four of eight |
| DOGEUSDT | 444e3e2600ee6c50 | 708 | -2.23 | 0.989 | 30.5 | 26.7 | 2042.4 | 33.15 | 35.38 | — | four of seven |
| ETHUSDT | cfc08b966ac07b08 | 781 | 65.76 | 1.215 | 33.5 | 19.0 | 1556.1 | 155.16 | 89.40 | 98.3 | six of eight |
| HYPEUSDT | 41d8367674e65759 | 150 | 3.39 | 1.100 | 35.3 | 4.8 | 176.4 | 9.25 | 5.87 | 485.2 | two of two |
| LINKUSDT | 995342d264290c96 | 818 | -27.40 | 0.864 | 33.7 | 33.5 | 330.7 | 0.50 | 27.90 | — | one of seven |
| NEARUSDT | 3a95eb2619db6e5b | 732 | 12.80 | 1.064 | 35.1 | 17.2 | 345.7 | 42.85 | 30.05 | 261.2 | five of seven |
| SOLUSDT | b41b348818679805 | 767 | -18.93 | 0.905 | 32.2 | 25.1 | 2990.4 | 9.23 | 28.17 | — | three of seven |
| SPXUSDT | d4558eb5be021fa6 | 226 | -9.88 | 0.838 | 38.5 | 18.7 | -29.1 | -5.05 | 4.83 | — | one of three |
| SUIUSDT | 43741380ba77a1f2 | 402 | 1.42 | 1.013 | 32.8 | 13.9 | -27.8 | 17.07 | 15.66 | 1781.9 | two of four |
| XRPUSDT | 792b1a59782360f2 | 783 | -17.52 | 0.927 | 29.4 | 40.1 | 536.7 | 24.34 | 41.86 | — | three of seven |

The Day-preset ETH cell is the only cell in the whole campaign that clears
profit factor AND concentration (top-five share 98.3%)
with both halves positive (58.0% then
4.9%) and all three thirds green
(31.8 / 4.4 /
20.5) across 781 trades. It is
also the best of eighty-nine cells (the multiple-testing haircut applies),
it makes 65.76% over six years against
1556.1% for holding, and the same symbol at repo
costs with the shipped default preset loses 33.31%.
A cost-fragile gross edge, not alpha.

## Repo costs (six bps fee + five bps slippage per side), one hour, defaults

| symbol | run_id | n | net % | PF | maxDD % | B&H % |
|---|---|---|---|---|---|---|
| ADAUSDT | 27f95c9d4e0681b1 | 842 | -51.30 | 0.654 | 55.4 | 307.7 |
| AVAXUSDT | 0b44207c0e0d5e33 | 764 | -26.24 | 0.844 | 30.7 | 141.9 |
| BNBUSDT | 06b860fbccb6f045 | 887 | -66.77 | 0.620 | 67.3 | 2766.2 |
| BTCUSDT | 07d3590d6a13d4bd | 897 | -68.34 | 0.667 | 76.2 | 715.8 |
| DOGEUSDT | e7a5cf437abbd4a4 | 778 | -47.13 | 0.701 | 49.3 | 2042.4 |
| ETHUSDT | f658045fc86a6592 | 865 | -33.31 | 0.837 | 46.2 | 1556.1 |
| HYPEUSDT | 4f5413eb0e2d1da4 | 162 | -0.79 | 0.978 | 9.7 | 176.4 |
| LINKUSDT | ba836137eb28b0e1 | 870 | -48.62 | 0.699 | 49.8 | 330.7 |
| NEARUSDT | 6704f69e57803a47 | 794 | -38.40 | 0.752 | 43.9 | 345.7 |
| SOLUSDT | a103d8942603bd70 | 815 | -54.51 | 0.656 | 55.1 | 2990.4 |
| SPXUSDT | 286cace36d595935 | 250 | -19.82 | 0.657 | 23.7 | -29.1 |
| SUIUSDT | 917ad57b6d9b7673 | 412 | -4.17 | 0.956 | 10.4 | -27.8 |
| XRPUSDT | 935afd96525208af | 828 | -60.09 | 0.635 | 60.7 | 536.7 |

The shipped-default book goes from uniformly mediocre to uniformly ruined.
The round trip costs 22 basis points at repo
costs against 10 at the Pine's own
assumptions, and the median holding period is a handful of bars — the edge
never covers it.

## Fifteen minutes (defaults, author costs) — ruin

| symbol | run_id | n | net % | PF | maxDD % | B&H % |
|---|---|---|---|---|---|---|
| BTCUSDT | c49e22c835ed0b48 | 2867 | -97.26 | 0.609 | 97.4 | 716.0 |
| ETHUSDT | 617d39cfe3fb329a | 3077 | -93.23 | 0.765 | 93.6 | 1557.2 |
| HYPEUSDT | 2453c8e79fbe39cb | 706 | -48.74 | 0.643 | 49.6 | 136.4 |
| SOLUSDT | 3d4f590927add604 | 2944 | -88.55 | 0.787 | 89.6 | 3019.2 |
| SUIUSDT | 1014adf3849c4198 | 1636 | -85.88 | 0.516 | 87.8 | -25.7 |
| XRPUSDT | c7ad26c152e51f5c | 3155 | -97.66 | 0.603 | 97.7 | 572.2 |

BTC loses 97.26% and XRP
97.66% with max drawdowns above ninety percent —
the same below-one-hour ruin pattern as `cbpack` and `cbot`. The "either"
signal mode at fifteen minutes is worse still: every symbol ends at or
within a rounding step of total loss (BTC artifact
89d3d32d42b2506d, net -100.00%;
the scalp preset is byte-equivalent in geometry to the Custom preset — same
HMA twenty-one and same HTF — and reproduces the same numbers under a
different run id, which is why its rows match the default table above).

## Five minutes (defaults, author costs) — thirty-day window, no sample

| symbol | run_id | n | net % | PF | maxDD % | B&H % |
|---|---|---|---|---|---|---|
| BTCUSDT | a8418b0cb30f88d7 | 25 | -9.12 | 0.137 | 10.6 | 19.8 |
| ETHUSDT | 683d8ddf656bbb16 | 41 | -12.44 | 0.186 | 12.8 | 29.7 |
| HYPEUSDT | 88533946bad45866 | 70 | -14.68 | 0.340 | 15.9 | 38.2 |
| SOLUSDT | d0e33b7a3423368f | 61 | -7.40 | 0.691 | 17.1 | 32.3 |
| SUIUSDT | 2b0fb9b8b7605425 | 71 | -7.33 | 0.668 | 13.3 | 11.2 |

The five-minute data on disk covers only about thirty days, so these cells
are a smoke test, not evidence: BTC opens 25 trades
(flagged INSUFFICIENT_SAMPLE) and every cell is negative.

## Funding charged (one hour, defaults, author costs + real Binance settlements)

| symbol | run_id | n | net % | PF | funding paid USD | covers bars? |
|---|---|---|---|---|---|---|
| BTCUSDT | 87b1de78e65471d4 | 897 | -28.17 | 0.876 | 0.15 | NO |
| ETHUSDT | 7e393b6f962e1d42 | 865 | 16.86 | 1.080 | 8.63 | NO |
| HYPEUSDT | 7a4d8c93bec8d852 | 162 | 6.60 | 1.206 | 0.67 | yes |
| SOLUSDT | 58d9ac1734fbeb24 | 815 | -34.20 | 0.792 | 3.50 | NO |
| SUIUSDT | 9b0e18f8065b2fe9 | 412 | 14.28 | 1.155 | -0.48 | NO |
| XRPUSDT | 196d845ae627641a | 828 | -34.11 | 0.804 | 2.65 | yes |

Funding barely moves a book that holds a risk-sized position for a handful
of bars at a time: BTC nets -28.17% with funding charged
against -28.11% without, ETH 16.86%
against 17.77%. CAVEAT, stated because this repo has been
burned by partial funding histories: the funding JSONs for BTC, ETH, SOL and
SUI start or end within days of the kline range but not exactly on it, and
the `covers bars?` column marks that — those cells undercharge a sliver of
the window. The measured funding amounts are small enough that the caveat
cannot change any verdict.

## The A-only and "either" families, for the record

System A alone (HMA + AO) over-trades catastrophically at one hour: BTC
artifact ea0cb0588d2158fb, 5595 trades, net
-95.85%, max drawdown 97.4% — the
AO rising/falling state flips far too often, and cost turns it into
instantaneous ruin. The "either" mode inherits the same disease (BTC
5ac447d035dacb52: 5619 trades, net
-95.88%).

## How to reproduce

    python code/_fingrad_audit.py                    # 22 known answers, ALL PASS
    python code/vrun.py matrix --strategy fingrad --tf 1h
    python code/vrun.py matrix --strategy fingrad --tf 1h --set sig_mode=b
    python code/vrun.py matrix --strategy fingrad --tf 1h --set adx_mode=literal
    python code/vrun.py matrix --strategy fingrad --tf 1h --set preset=day
    python code/vrun.py matrix --strategy fingrad --tf 1h --set costs=repo6x5
    python code/vrun.py matrix --strategy fingrad --tf 1h --set sig_mode=a
    python code/vrun.py matrix --strategy fingrad --tf 1h --set sig_mode=either
    python code/vrun.py matrix --strategy fingrad --tf 15m
    python code/vrun.py matrix --strategy fingrad --tf 15m --set sig_mode=either
    python code/vrun.py matrix --strategy fingrad --tf 5m
    python code/vrun.py run --strategy fingrad --tf 1h --symbol BTCUSDT --set funding=true
    python code/vrun.py guard --report results/fingrad_report.md

Cited artifacts: 04832565afd603a9, 06b860fbccb6f045, 07d3590d6a13d4bd, 08d59a18157567e4, 0b44207c0e0d5e33, 0d910a37150622a2, 0ebf8ffd7471ba5a, 0f16bacdd64fe6a7, 0f6f287d43830c50, 1014adf3849c4198, 128a29ff464d5c03, 13d4b3994ea82449, 16089275ff48f91d, 16126bd5d2324a43, 196d845ae627641a, 1d71d29db54fd3c8, 2288aa01825d36ca, 22f99befc300660b, 2453c8e79fbe39cb, 256a2bee063b82b4, 2604cef550c06cb2, 27f95c9d4e0681b1, 286cace36d595935, 2987bf9354bc99d3, 2b0fb9b8b7605425, 2bd00a42643ef8a2, 35862e1667abd61e, 371521fb4642449c, 3a95eb2619db6e5b, 3d4f590927add604, 3da3a1a758cdd47b, 407a2588ab7a8404, 41d8367674e65759, 421c6d03e4c884ee, 424ea5214eacefc3, 43741380ba77a1f2, 444e3e2600ee6c50, 47cdfc5c5798271b, 4e8e06374142dc91, 4f5413eb0e2d1da4, 56e238818e8cc08a, 5857d01d0ba97811, 58d9ac1734fbeb24, 592ffe757d8d6125, 5a67e42976fe684b, 5ac447d035dacb52, 5e0c8cf376d1e83a, 5f51ef3458ef1fe2, 60a421b68e423bf0, 615725deaede5295, 617d39cfe3fb329a, 6704f69e57803a47, 683d8ddf656bbb16, 68fd0f1ef6349e7b, 693564f159acf9f1, 6d70c353e32ee90f, 6fd245c24170ff8e, 73c5156c430a98f1, 749fc2eb9842d522, 792b1a59782360f2, 7934143c44479833, 79b53eeb0b4035c9, 7a4d8c93bec8d852, 7b9729782cba2987, 7c7cd615776a9a4e, 7e393b6f962e1d42, 87add17cc6f4e1db, 87b1de78e65471d4, 88533946bad45866, 89d3d32d42b2506d, 8d8a1949328c0347, 8e544129009a962a, 902a2f886b8f8a31, 917ad57b6d9b7673, 935afd96525208af, 995342d264290c96, 9b0e18f8065b2fe9, 9d3df8420ecfdc36, a103d8942603bd70, a1721cf757d44b91, a1df8c5722afc7ef, a8418b0cb30f88d7, ac22bed1f6065756, ae0d5f50f422cbd2, aebb0d8374ddf20b, b3dc6d8f0c114142, b406758485d91ba4, b41b348818679805, ba6af07446f23007, ba836137eb28b0e1, c49e22c835ed0b48, c7ad26c152e51f5c, cc1d2edc778d24ab, cd8ac043a9dfe34d, cde216c4803b432c, cfc08b966ac07b08, d0e33b7a3423368f, d3f416558ec09e59, d4558eb5be021fa6, d954d5040a35b06e, d9b7f49100445294, de415631d6c54abd, de8145cdb9203f80, df7f5f0da2e70275, e5bb19d43e627b8e, e7a5cf437abbd4a4, ea0cb0588d2158fb, ec2f265c20361cfd, ec91eb01e582fba1, ef4f82590122a362, ef7120886d75d229, f4e45332a51935a7, f658045fc86a6592, f8312403550f42fc.
