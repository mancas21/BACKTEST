# PACK RESULTS — the Qwen ten-card pack: the six surviving cells

Engine `code/q10_engine.py` with conventions module `code/q10_diag.py`
(both hashed into every artifact), run through the `q10` adapter of
`code/vrun.py`; the engine sha begins `51cc6379044b`. Before any real-data
run, the known-answer audit `code/_q10_audit.py` (transcript
`results/q10_engine_audit.txt`) ran on these exact engine bytes and passed
all of its synthetic cases — sixty-nine of sixty-nine, labelled known
answers, no run_id. Costs are the pinned repo taker basis (six bps fee plus
five bps slippage per fill, applied at every redollarization; a side- and
weight-preserving roll is not a fill), funding is billed on settled prints
strictly inside each leg's window in both directions, and every artifact
carries the in-run unit/equity parity assertion plus the benchmark
telescoping assertion.

Every number below is read from a verified artifact and cites its `run_id`;
all six artifacts reproduce bit-for-bit under `verify`. Counts are in
words. `profit_factor` is the net per-unit PF; `profit_factor_zero_fee` is
the same units with the fill fees removed from them (funding stays billed)
— the cost control.

## Harness-incident note (before these runs, fixed then re-run)

Two cells of the majors group share one input file set, and the first
harness wiring did not put the card key in the artifact core. Two runs
consequently collapsed onto one run_id and one artifact file was
overwritten by the other cell's metrics. The harness now records the card
inside core params, so each card is its own id. The two affected files were
renamed out of the artifact namespace and kept as evidence, NOT results:
`4596f8f583d53b6d.COLLIDED-cardid.json` (holds a merged record of two runs)
and `aa28f0084a37a6eb.PREFIX-no-card.json` (a self-consistent CARD3 run
whose core predates the card-in-params change). All six cells were re-run
after the fix and only the post-fix artifacts below count.

## Cells run — all `verify` OK

| card | run_id | book (pinned, declared before any run) |
|---|---|---|
| CARD1 | `0f23886c0607a21a` | majors funding-delta monthly rotation: long low / short high trailing settled-delta buckets, quarter legs, monthly decisions with hold-on-undecidable |
| CARD2 | `76955428d8de4012` | ten-name monthly cross-section low-vol L/S: long the five lowest trailing-month realized vols, short the five highest (funding billed on the four majors only; no files exist for the other six and none were synthesized) |
| CARD3 | `beec2fbb495b611b` | turn-of-month BTC/ETH: one long basket window per month from the day-twenty-seven-close decision, entry at the day-twenty-eight open, exit at this month's day-three open |
| CARD4 | `f8afa8673577bf59` | majors funding-regime biweekly long/flat: the panel gate's calm-recent-vs-year-median condition decides quarter legs or flat |
| CARD9 | `abea6c8039307385` | majors vol term-structure monthly long/flat: quarterly legs while the panel trailing-week RV sits below a large fraction of the trailing-month RV |
| CARD10 | `1261a609ec97809c` | ten-name monthly volume-growth L/S: long the five lowest short-window/long-window mean-volume growth, short the five highest (funding again billed on the majors only) |

## Full-history headline metrics

`net%` is the linear book return on total gross of one; `bench%` is the
declared equal-weight buy-and-hold of each card's own benchmark basket over
the very same scored span, linear, no rebalancing.

| card | run_id | net % | bench % | excess pp | PF net | PF fee-free | units | fills | maxDD % |
|---|---|---|---|---|---|---|---|---|---|
| CARD1 | `0f23886c0607a21a` | 15.39 | 239.53 | -224.14 | 1.02 | 1.01 | 288 | 280 | 58.22 |
| CARD2 | `76955428d8de4012` | 63.01 | 173.14 | -110.13 | 1.09 | 1.08 | 700 | 280 | 37.58 |
| CARD3 | `beec2fbb495b611b` | 112.74 | 264.35 | -151.60 | 1.74 | 1.59 | 83 | 332 | 24.79 |
| CARD4 | `f8afa8673577bf59` | -18.94 | 29.84 | -48.77 | 0.96 | 0.95 | 89 | 96 | 102.75 |
| CARD9 | `abea6c8039307385` | -93.70 | -9.35 | -84.35 | 0.53 | 0.52 | 17 | 96 | 118.83 |
| CARD10 | `1261a609ec97809c` | 0.50 | -36.29 | 36.79 | 1.00 | 0.99 | 650 | 464 | 53.62 |

## Gate table

Letters read: the repo profit-factor gate, the closed-unit count floor, the
both-halves gate, the green-calendar-years gate, the decide-over-your-own-
basket-benchmark gate, and the net-green-without-the-best-five gate.

| card | run_id | G1 PF | G2 count | G3 halves | G4 years | G5 bench | G6 top-5 | gates passed |
|---|---|---|---|---|---|---|---|---|
| CARD1 | `0f23886c0607a21a` | fail | PASS | fail | fail | fail | fail | 1 |
| CARD2 | `76955428d8de4012` | fail | PASS | PASS | fail | fail | fail | 2 |
| CARD3 | `beec2fbb495b611b` | PASS | PASS | fail | PASS | fail | PASS | 4 |
| CARD4 | `f8afa8673577bf59` | fail | PASS | fail | fail | fail | fail | 1 |
| CARD9 | `abea6c8039307385` | fail | fail | fail | fail | fail | fail | 0 |
| CARD10 | `1261a609ec97809c` | fail | PASS | fail | PASS | PASS | fail | 3 |

## VERDICT

**Zero of the six delivered cells clear the full gate set.** Every cell's
artifact records `gates_pass_all: false`. Per the pre-registration, the
frozen-parameter out-of-sample step belongs only to cells that clear
everything — none do — so no out-of-sample step is run, there is no rescue
loop, and all six cells die here. The Qwen pack program is closed with
these six artifacts plus the step-zero kills: the pack produced no
tradeable book at the repo cost basis, and its two closest misses are
documented below rather than tuned.

## Per-cell notes

- **CARD1** (`0f23886c0607a21a`) — the best five weighted legs carry
  791.03 percent of the book total, and the book without them is
  -10634.09 bps. Gross book on gross of one is 1538.87 bps with 770.0 bps
  of fills and -472.99 bps funding, and the fee-free control PF is 1.01 —
  the gross edge is approximately nonexistent, which is exactly what the
  step-zero staleness read predicted (chasing a slow-moving settled-rate
  delta at a monthly cadence). Six of seventy-two scored months were
  undecidable and held the prior state; no month needed the final
  liquidation.
- **CARD2** (`76955428d8de4012`) — the most balanced book of the pack:
  both halves clear their PF gate (their half PFs are 1.09 and 1.08) and
  the fee-free control barely moves (1.08 vs 1.09) because the whole book
  pays 308.0 bps in fills. But the net PF 1.09 sits far under the repo gate, the
  funding billed on the four majors is -1314.99 bps, the best five
  contributions carry 114.32 percent of the total, and the book without
  them is -902.60 bps. Killed, honestly, on signal size.
- **CARD3** (`beec2fbb495b611b`) — the clear best of the pack and still
  killed. Net PF 1.74 (fee-free 1.59), net book 11274.29 bps on gross of
  one, 59.04 percent of windows win, concentration passes cleanly (the
  best five carry 62.61 percent; without them the book is still
  +4215.02 bps), funding -1553.17 bps and 1826.0 bps of window fees, and
  the equity path stays green in four of six full calendar years — the
  green-years floor. It dies on timing stability: the first half's unit PF
  is 5.14 while the second half's is 0.60 (the window edge decayed hard
  after the span midpoint), and its own basket buy-and-hold made 264.35
  percent over the same span versus the window book's 112.74 percent —
  the classic repo verdict that a buy-in-the-middle-of-every-month filter
  does not beat just holding the basket. All eighty-three windows were
  decidable; none required the final liquidation.
- **CARD4** (`f8afa8673577bf59`) — the panel regime gate kept the book
  long 66.42 percent of valid decisions (eighty-nine in-market states of
  one hundred thirty-four validated decisions), the funding panel covered
  0.86 of the span in full, and the book still nets -18.94 percent at a
  102.75 percent max drawdown against a bench of 29.84 percent. The
  regime condition buys calm funding — which is where the majors bled in
  the measured span. Killed; its declared one-hundred-percent in-market
  demand was never close.
- **CARD9** (`abea6c8039307385`) — dead on arrival: seventeen in-market
  units against the thirty-unit floor, in-market 23.61 percent of
  decisions, net -93.70 percent, PF 0.53, fee-free 0.52, fill fees
  264.0 bps,
  funding -788.34 bps. The vol term-structure condition is a crash-buy in
  the wrong direction: it goes long the majors precisely when the panel's
  recent vol is calm relative to its month, which the measured span
  punishes. Also the first pack cell whose benchmark basket itself fell
  (-9.35 percent) yet the book lost far more.
- **CARD10** (`1261a609ec97809c`) — the volume-growth keyed rotation sits
  at net 0.50 percent with a fee-free PF of 0.99 — no gross edge at all —
  while funding on its short book actually pays +174.06 bps and fills cost
  510.4 bps. The "beats the bench" line is the standing trap: the ten-name
  equal-weight basket itself ended -36.29 percent, and winning by losing
  less than a collapsing basket is not alpha by the repo's own rule. The
  book without its best five legs is -5260.10 bps. Killed.

## Cross-checks measured inside the artifacts

- The unit/equity parity residual stays below a thousandth of a basis
  point in every artifact; the unit P&L decomposition (price plus funding
  minus fees equals net) is asserted in-run for every card.
- The benchmark series passes the telescoping closed-form assertion in
  every artifact (the per-bar mean of log returns equals the log price
  ratio of the basket over the span).
- All six scored spans sit inside gapless hourly kline grids; no funding
  rates were synthesized anywhere, and the ten-name books disclose that
  six of their names carry no billable funding at all.
- Undecidable decisions hold the prior state by the pinned convention
  (C8) — measured as six skipped months in CARD1, all other cards zero.
- The executor's roll/not-a-fill convention held: CARD1's rotation is
  fee'd exactly where sides changed, and no book required a final
  liquidation line (zero flagged legs in all six artifacts).

## Program close-out

Of the declared twelve-cell budget, six cells were consumed by these runs;
cards five, six, seven and eight died at step zero by their own
pre-declared diagnostic bars (`results/q10_step0.md`), and the reference
pack stays a document only. Final standing of the Qwen threads' strategies
in this repo: **every card killed or unrun; nothing survives the gate
set.** The one book that even conceptually deserves a second look —
CARD3's turn-of-month basket — is recorded as killed with its artifact
open: its first-half PF of 5.14 collapsing to 0.60 in the second half and
its 264.35 percent basket benchmark are precisely the kind of
recent-window decay the standing gates exist to catch before capital
meets it.
