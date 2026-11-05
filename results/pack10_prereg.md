# PRE-REGISTRATION — pack of ten declared designs ("the pack")

Status: DESIGN DOCUMENT and reference quality bar. No artifacts exist for this
pack; no backtest has been run; every number below is a declared parameter, an
arithmetic cost demand, a count expectation, or a descriptive data fact already
established elsewhere. AMENDED 2026-10-23: the registered run set of the pack
program is the graded Qwen pack (see results/qwen_pack10_grade.md) — these
reference cards are NOT a second run set; running both would breach the
twelve-cell C7 budget.
The outcome table at the end is filled only from verified `results/runs`
artifacts after the pack runs through the harness. Counts are written in words.

Compliance map: C1 causality, C2 long-window testability, C3 fixed costs
(22 bps taker round trip), C4 cost arithmetic shown per card, C5 no banned
families, C6 breadth, C7 pre-declared grid (twelve cells, section 7), C8 no
synthetic fallbacks, C9 no raw-bar ML. Seeds adopted: three (cards one, two,
three). The remaining seven are original designs against the same rails.

Symbol sets used: majors = BTC, ETH, SOL, XRP (funding coverage since 2020 or
earlier); full-history ten = BTC, ETH, SOL, XRP, ADA, AVAX, BNB, DOGE, LINK,
NEAR; SUI, HYPE, SPX are OOS-only add-ons (stub spans). Alts here means the
non-major names of the full-history ten.

---

## 1. SETTLEMENT WINDOW BOOK (seed S1, adopted)
family+pays: funding-levy mechanics. Leveraged directional holders pay carry at
   the 00/08/16 UTC settlements; for a few bars after settlement we hold the
   side that collects the levy, betting the crowd unwinds once the timestamp
   passes. The payer is whoever re-finances a crowded position.
data: long 1h klines (BTC ETH SOL XRP) + funding JSONs, six to seven years of
   settled rates. No flow columns. [C2 C8]
signal: unit opens at the close of the 1h bar BEFORE a settlement whose settled
   |rate| is above its trailing ninety-settlement 80th percentile; direction =
   the collector's side (short perp if rate > 0, long if rate < 0); the residual
   delta of a spotless hedge is DECLARED, not hidden; exit two bars after the
   settlement; stop 1.0 x ATR(50) beyond entry; equal notional per unit. [C1]
freq/hold: hold three bars unless stopped; expectation several hundred units
   across four symbols over the window.
cost math: demand per unit >= twenty-two bps round trip plus about one bp carry;
   the per-event favorable-move distribution is measured on filtered settlements
   BEFORE any simulation; that measurement sets pass or kill. [C4]
breadth: units spread over 2019 to 2026 and four names at equal size; kill if
   funding extremes cluster into one crowding episode and the best five units
   exceed forty percent of PnL. [C6]
family: nearest killed member = S07 funding-extreme fade (level z trigger, EMA
   confirmation, ATR stops and stops/targets over days of holding). Structural
   difference: fixed settlement-time exit, no level trigger, no confirmation
   indicator, hold measured in single bars. [C5]
grid: default, percentile 0.80, single cell.
ML: none.
kill: median favorable move over filtered settlements < 0.25 x cost demand.
my verdict: borderline. The settlement timestamp itself has never been measured
   here; the cost bar is the entire question.

## 2. FUNDING-DELTA ROTATION (seed S2, adopted)
family+pays: crowding financing. Chasers bid carry up into crowded longs; we
   take their counterparty cash flow at weekly granularity, never their trend
   thesis. Payers are the financiers of fresh crowding.
data: funding JSONs for the signal; 1h closes for accounting; BTC ETH SOL XRP. [C2]
signal: on the Sunday 20:00 UTC close, rank the four names by the trailing
   four-settlement DELTA of settled funding, lagged one full interval; weights
   proportional to tanh((0.5 - pct_rank(delta)) x 1.0); always-in, gross <= 1.0,
   funding charged every settlement on open notional. [C1 C3]
freq/hold: fifty-two rebalances x four legs = two hundred eight
   unit-equivalents per year; week-long holds.
cost math: weekly fee drag is turnover-bound: at weekly one-way notional
   churn between 0.3x and 1.4x of gross, eleven bps per side gives roughly
   three to eleven percent per year on a one-gross book, PLUS the funding the
   book pays or collects on held legs. Declared pass demand, measured from
   the files before anything is ported: interquartile range of the weekly
   funding-delta ranking spread >= 25 bps per week after the one-interval
   lag. [C4]
breadth: four names at gross <= 1.0 through 2020 to 2026; single-name weight
   bounded at half gross; no single week should dominate the book. [C6]
family: nearest killed = S07. Structural difference: portfolio rank on a
   cash-flow field with no price trigger and no stops, holding a week.
grid: default (four-settlement delta); alternate = trailing eight settlements
   delta instead. Two cells.
ML: none.
kill: funding-delta dispersion interquartile range < 25 bps/week on the
   diagnostic artifact; kill before a backtest is even built.
my verdict: expect kill on dispersion arithmetic. Included because the
   diagnostic is one cheap artifact and closes the question permanently.

## 3. STABILIZATION FADE, 15m (seed S7, adopted)
family+pays: forced-flow cascades. Stop cascades and liquidation chains
   overshoot and then exhaust; we supply depth after the forced flow ends. The
   payer is the forced liquidator we stand in front of.
data: 15m plain klines; majors full window, SUI/HYPE as OOS-only add-ons; no
   flow columns. [C2]
signal: shock bar closes with |ret| > 2.5 x ATR(50) AND volume > 4 x trailing
   thirty-day same-hour median; entry is NOT the shock bar: the first completed
   15m bar whose full range <= 0.6 x the shock bar's range; direction against
   the shock; stop 1.0 x the shock extreme; hard exit twenty-four bars after
   entry unless stopped. [C1 C8]
freq/hold: hold at most six hours; expectation several hundred units over six
   years on the majors.
cost math: demand >= twenty-two bps per round trip; per-event scale is two to
   four times the 15m ATR, so the edge requirement is comfortable ONLY if the
   stabilization filter selects exhaustion rather than continuation. That
   selectivity is exactly what the run measures. [C4]
breadth: events across symbols and years at equal notional; if the 2020-2021
   liquidation cycles produce more than forty percent of PnL, kill. [C6]
family: nearest killed = S09 sweep-reclaim (structural wick reclaim plus
   volume gate). Structural difference: exhaustion THEN a completed, smaller
   stabilization bar; no reclaim level, no swing structure, fixed time exit.
grid: default as above, single cell.
ML: none.
kill: fewer than thirty closed units on the majors' full window. [G2]
my verdict: the pack's strongest candidate. Its risk is selectivity against
   sample size, which the kill condition prices directly.

## 4. LOW-VOL CROSS-SECTION, LONG/FLAT
family+pays: lottery-flow overprices high-vol names and leaves the thin-vol
   tail cheap per unit of risk taken. Payers are holders of variance itself.
data: 1h plain closes, the full-history ten names over their common window. [C2]
signal: monthly close, rank by trailing 20d realized vol (std x sqrt 365); hold
   the three lowest-vol names equal weight, cash for everything else; skip a
   name whose own vol exceeds the panel median that month; then vol-target the
   book to 12% annualized. [C1]
freq/hold: twelve rebalances per year, at most thirty-six round trips at a
   small average gross; accounting counts a unit per leg change, keeping
   hundreds of closed units across the window for G2.
cost math: under about eight percent per year of notional drag, to be earned by
   the tilt plus the targeting. [C4]
breadth: dozens of units per year through 2020 to 2026; declared risk: a single
   regime (an alt-vol collapse or a euphoric year) could dominate - the run
   measures it. [C6]
family: nearest killed = S10 vol-targeted momentum. Structural difference:
   sorting key is trailing vol, the book holds the low-vol tail, no return
   signal exists anywhere in the design.
grid: default (three names), single cell.
ML: none.
kill: fails G5 against buy and hold over the full span.
my verdict: expect G5 failure in euphoric years; vol targeting may save it;
   genuinely uncertain and worth one artifact.

## 5. VOLATILITY-MANAGED LONG/FLAT MAJORS
family+pays: holders who do not scale by volatility leave the whole high-vol
   drawdown to themselves; the effect priced here is the timing discount they
   hand to anyone who does scale.
data: 1h plain BTC and ETH equal-weight basket since 2019; funding ignored. [C2]
signal: weight = clip(12% / RV_lagged(30d annualized), 0, 1); rebalance only
   when the weight crosses a hysteresis band of twenty percent relative to the
   last executed weight. [C1]
freq/hold: continuous exposure; expectation fifteen to forty round trips per
   year.
cost math: under nine percent per year at the stated turnover band; demand is
   trivial compared with the other cards, which is why it must clear everything
   else rather than the cost bar. [C4]
breadth: exposure across two names through the full window; single years
   dominate by construction when vol regimes persist - declared G4 risk, the
   run measures it. [C6]
family: nearest killed = ds1 time-series momentum and S10 (returns-based
   signals with a vol target). Structural difference: the sizing entry contains
   NO return sign; the book is pure exposure scaling of beta.
grid: default, single cell.
ML: none.
kill: fails G5 against buy and hold over the full span.
my verdict: narrow pass or narrow kill; the hysteresis is what keeps turnover
   from eating the effect.

## 6. CROWDING-SPREAD DE-RISK
family+pays: levered risk-on flow shows in alt financing before it shows in
   price; the payer is the crowded alt-financer we exit in front of.
data: funding JSONs (BTC ETH SOL XRP) plus 1h closes to define the two baskets
   and their returns. [C2]
signal: spread = median settled funding of the alts minus median settled
   funding of the majors over the trailing thirty settlements, lagged one full
   settlement; risk-on book = equal-weight six alts of the full-history ten;
   risk-off book = majors only; switch to majors when the spread is above its
   trailing one-year 80th percentile, back below with a twenty percent
   hysteresis band; at most one switch per week. [C1]
freq/hold: switches plus weekly reweights give on the order of one hundred
   units per year.
cost math: switch-bound. Each switch trades both baskets at one gross =
   about twenty-two bps; at ten to twenty switches a year that is two to four
   percent per year, plus small weekly-leg fees at fixed basket weights. Pass
   condition: each switch must avoid more than twice the round-trip demand in
   expected vol-adjusted damage, declared as the arithmetic gate Measured per
   run. [C4]
breadth: two-basket book across the full window with a funding income leg;
   no single week should dominate. [C6]
family: nearest killed = S07. Structural difference: a CROSS-SECTIONAL funding
   spread as a regime key, never a single-name level, no stops, baskets not
   single names.
grid: default, single cell.
ML: none.
kill: funding-spread state persistence < 3 weeks median on the diagnostic.
my verdict: honest coin flip. The mechanism is real if and only if alt
   financing decouples from majors financing after runs; the files decide.

## 7. VOLUME-SHOCK EVENT BOOK (both polarities)
family+pays: volume shocks move attention and flow; both continuation and
   reversion have a payer, and the run decides which one pays here rather than
   assuming the mechanism.
data: 1h plain closes, the full-history ten names. [C2]
signal: shock bar = volume > 5 x trailing thirty-day same-hour median AND
   |ret| > 2.5 x ATR(50); entry at the next bar's open in the shock's direction
   (CONT cell) or against it (FADE cell); stop 1.0 x ATR beyond the shock
   extreme; fixed exit five bars after entry; equal notional per unit. [C1]
freq/hold: several hundred units over six years across ten names at equal size.
cost math: demand >= twenty-two bps per unit; per-event scale is one to three
   percent for five-bar holds at 1h, so the bar is reachable on both sides of
   the polarity. [C4]
breadth: ten names, six years, two polarities at equal units; kill if the best
   five units exceed forty percent of PnL. [C6]
family: nearest killed = S02 channel breakout with flow gate, and the cbot
   breakout members. Structural difference: no price level exists anywhere in
   the trigger; the event is the volume-vs-ATR extreme itself.
grid: CONT default and FADE declared as the second cell (polarity only).
ML: none.
kill: profit factor < 1.0 in either half-window for either cell. [G3]
my verdict: the reversal-or-continuation question after volume shocks is a
   genuine open question in this repo; expectation is honestly symmetric.

## 8. TURN-OF-MONTH WINDOW
family+pays: month-end institutional rebalancing footprints a few days of
   demand at the turn; we hold that window and nothing else. Payers are
   passive flows executing on schedule.
data: 1h plain BTC+ETH basket since 2019; funding not needed. [C2]
signal: long the basket from the last day-of-month close through the third
   close of the new month; skip the unit when trailing 20d realized vol is above
   its panel median; flat otherwise. [C1]
freq/hold: twelve units per year, three-to-four day holds.
cost math: twelve round trips per year = about 2.6 percent per year; the
   per-unit edge demand is trivial. [C4]
breadth: seventy-eight units over the window at homogeneous size; kill if the
   best five exceed forty percent of PnL. [C6]
family: nearest killed = S06 session-range breakout (intraday Asia window).
   Structural difference: a calendar month window, no breakout level, a basket
   not a single name.
grid: default, single cell.
ML: none.
kill: fails G3 half-window balance.
my verdict: the effect is possibly real but tiny; the cost bar is trivial, so
   this is the cheapest honest calendar test in the pack.

## 9. CALM-WEEKEND HOLD
family+pays: weekend liquidity providers charge for thin-book exposure; holders
   of weekend risk receive whatever premium the makers charge through spread.
   The run tests the sign of that premium.
data: 1h plain BTC+ETH basket; window is Friday 16:00 UTC close to Sunday
   20:00 UTC close. [C2]
signal: hold the basket over the weekend unless the trailing-week realized-vol
   percentile is above eighty; flat otherwise. [C1]
freq/hold: about fifty-two units per year, each held two to three days.
cost math: fifty-two round trips per year = about eleven percent per year;
   demand is at least ~12 bps of favorable move per unit on the non-skipped
   weekends. [C4]
breadth: three hundred plus homogeneous units over the window. [C6]
family: nearest killed = none; the closest concept in the repo is S06 session
   windows, and there is no level trigger here at all.
grid: default, single cell.
ML: none.
kill: aggregate net weekend edge below the twelve bps per unit demand.
my verdict: likely too thin to pay. Its job is to close the calendar question
   with one artifact rather than one debate.

## 10. FLIGHT-TO-QUALITY BASKET SWITCH
family+pays: risk-on rotation exits get expensive at vol expansion; we swap to
   the majors basket the crowd has to buy late. Payers are late rotators.
data: 1h plain, majors basket (BTC ETH) and alts basket (six of the full-history
   ten). [C2]
signal: ratio = RV(30d, alts) / RV(30d, majors), lagged one bar; switch to
   majors above 1.60, back to alts below 1.25 (hysteresis); weekly check, at
   most one switch per week; no price level in the trigger. [C1]
freq/hold: switches plus weekly legs give on the order of one hundred units per
   year over the window.
cost math: switch-bound. Ten to twenty switches a year at about twenty-two bps
   each is two to five percent per year on one gross; the pass condition is
   that the avoided vol delta per switch exceeds three times the round-trip
   demand - an arithmetic gate, measured per run. [C4]
breadth: two baskets across the full window; no single-week dominance by
   design. [C6]
family: nearest killed = S10 vol-targeted momentum. Structural difference: the
   regime key is the CROSS-BASKET vol ratio, not any name's own vol or return.
grid: default, single cell.
ML: none.
kill: fewer than twenty switches over the window, or ratio-regime persistence
   under three weeks median.
my verdict: expect G3 half-window imbalance; the book lives or dies in 2022 and
   the run says which.

---

## 7 · Grid declaration (12 cells, all declared now; the pack runs these only)

```
card  1  settlement window  pctl 0.80                     1 cell
card  2  funding-delta rotation  4-set / 8-set delta      2 cells
card  3  stabilization fade  default                      1 cell
card  4  low-vol xs  k=3                                  1 cell
card  5  vol-managed long/flat  default                   1 cell
card  6  crowding-spread de-risk  pctl 0.80               1 cell
card  7  volume-shock  CONT / FADE                        2 cells
card  8  turn-of-month  default                           1 cell
card  9  calm-weekend hold  default                       1 cell
card 10  flight-to-quality switch  1.60/1.25              1 cell
total                                                    12 cells
```

## 8 · Ordered run plan (harness scope, no tuning after the runs start)

Step 0 — diagnostics first, three descriptive artifacts from raw files, no
   trade simulation: card two's funding-delta dispersion; card six's spread
   persistence; card one's filtered-settlement favorable-move distribution.
   Each carries its own kill verdict before anything is ported.
Step 1 — known-answer audit for the shared signal primitives (ATR conventions,
   percentile ranks, hysteresis scaler, funding lag) BEFORE any real-data run.
Step 2 — the twelve declared cells through the vrun harness, full window plus
   last-six-months split, repo6x5, funding per settlement where applicable.
Step 3 — period split and frozen-parameter OOS only for cells that clear G1-G6.
Step 4 — report, `guard`, `verify`. No parameter change re-runs: after the
   declared cells run, any re-specification is a new pre-registration, not a
   rescue.

## 9 · Honest prior on this pack (declared now, not after)

Two cards are expected to die on their own diagnostics before any engine is
written (two and six). One is expected to fail the return benchmark (four).
Two are near-certainly thin but priced that way on purpose (eight and nine).
Three are genuinely open (one, seven, ten). One is the pack's strongest prior
(three). That is the fair reading of the previous four packs' base rate and this
pack's own bars: the point of declaring it now is that nobody gets to soften it
after the runs.
