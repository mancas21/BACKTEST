# GRADE — the Qwen ten-card pack (received 2026-10-23)

Paper grading of the ten cards pasted verbatim from the Qwen thread against
`incoming/qwen_10idea_brief.md`. Nothing below is a measured result: no
backtest has run, no artifact is cited, every number is a card's DECLARED
arithmetic, a declared count, or a compliance reading. The cost lines of all
ten cards were re-checked line by line by script in this session (twenty-one
of twenty-one reconcile; section below). Counts are written in words.

DECISION RECORDED HERE: with this grade, the registered run set of the pack
program is THESE ten cells. `results/pack10_prereg.md` remains the reference
quality bar only — running both packs would breach the twelve-cell C7 budget.
Its header is amended to say the same.

## Verdict table

| card | key | C1 causality | long-window | C4 arithmetic | C5 adjacency | units | honest reading |
|---|---|---|---|---|---|---|---|
| 1 | funding-delta monthly L/S | pass (lagged one settlement) | pass | pass | pass (delta, not level) | seventy-two books / two-eighty-eight legs | cadence flag F3 |
| 2 | low-vol monthly XS L/S | pass | pass (plain ten names) | pass | pass (vol key, not return) | seven-twenty leg-months | strongest cell |
| 3 | turn-of-month BTC/ETH | pass | pass | pass | pass (date-only trigger) | seventy-two | cheap honest calendar test |
| 4 | funding-regime biweekly L/F | pass | pass | pass (ceiling, F5) | pass (regime, not fade) | one-fifty-six | beta in calm regimes; G5 risk |
| 5 | funding-carry quartile L/S | pass | pass | pass | SPIRIT flag F2 | two-eighty-eight | carry spread + price path decide |
| 6 | weekend funding rider | pass | pass | pass (labelled worst case) | pass | three-twelve | weekend premium sign test |
| 7 | month-open four-hour ride | pass | pass | pass | pass | seventy-two / two-eighty-eight | likely dies on thin edge |
| 8 | settlement-hour carry (monthly) | pass | pass | pass | pass | two-eighty-eight | convention flag F1 |
| 9 | vol term-structure L/F | pass | pass | pass (ceiling, F5) | pass | seventy-two | near-duplicate of card four, F4 |
| 10 | low volume-growth XS L/S | pass | pass | pass | pass | seven-twenty | key correlates with momentum |

Reading: ten of ten cards pass every hard constraint on the letter. Seeds
adopted are exactly the capped three (S2 in card one, S3 in card two, S8 in
card three), each with its declared structural difference. No flow columns,
no synthetic anything, no ML. Grid: ten cells, zero alternates, inside the
twelve-cell budget. The C4 requirement — cost arithmetic in the card, before
anything else — was met on every card.

## Arithmetic reconciliation

The load-bearing claim, shared by the four L/S cards, is algebraically true:
a total-gross-1x book rolled fully every month pays exactly 264 bps/yr
independent of leg count (close half + open half, both sides = 2.0 gross of
fills per month x 11 bps per side = 22 bps/month). Declared funding budgets
use a 2.7 bps/day majors basis — a good midpoint of the measured settled-rate
medians (0.84 to 1.0 bp per 8h settlement on the four majors, a descriptive
property of the funding files on disk). Per-card totals, minimum-edge
per-unit demands and unit counts all reconcile within rounding tolerance.
This also pins the notional reading: "equal gross 1x" means TOTAL gross of
one (half long / half short) — the only reading consistent with the declared
fee basis.

## Flags (substantive, all pre-run, none a rejection)

F1 · CARD EIGHT — which settlement does the unit collect? Decision at the
   23:00 bar close, fill at the 00:00 bar open, exit "after 8 bars" puts the
   exit AT or BEFORE the 08:00 settlement instant depending on the reading.
   Under the repo's funding convention (settlements strictly after entry),
   the wrong exit instant means the unit collects NO levy and the card's
   only cash flow is the price move. Pinned porting convention: hold through
   the 08:00 settlement, exit at the 09:00 bar open — exactly one levy.
   Second defect: the sign-keyed direction can sit the whole panel on ONE
   side (all four 30d-avg funding signs agree happens often; majors funding
   is usually positive) — the card is then a 1x short basket in a bull
   market, not neutral. Admissible as declared, but this composition risk
   is undeclared and the run must report the per-month side balance.
F2 · CARD FIVE is the nearest to the killed S07 in PnL ENGINE (shorting the
   crowded high-funding names). Letter-compliant: no stops, monthly, slow
   carry rotator, both sides. The pre-engine diagnostic must therefore
   measure not only the carry spread but the PRICE-path differential between
   the high-funding and low-funding buckets (the classic carry-crash check:
   high-funding names usually rise, and the price side can eat the carry).
F3 · CARD ONE ranks a seven-day funding delta at a monthly cadence — chasing
   a signal whose half-life is days with a hold of a month. The diagnostic
   must report rank staleness (delta persistence over 30 days).
F4 · CARDS FOUR AND NINE are the same book shape (long/flat majors in calm
   regimes, two different regime keys). Both carry the same G5 exposure
   risk against buy & hold. Not banned, but the pack's breadth is thinner
   than ten cards suggests.
F5 · FEE CEILINGS: cards four, six and nine declare round trips at a
   one-hundred-percent in-market rate; card four's 572 bps/yr is the ceiling
   of a gate that is flat part of the time (its own funding line assumes
   fifty percent). Honest drag is regime-transition-bound and several times
   lower. Engines count fills; nobody should quote the 41-bp-per-decision
   demand as the kill bar for card four.
F6 · G5 BENCHMARK PIN (needed before any run, else post-hoc gaming):
   L/S books (cards one, two, five, ten) benchmark against the equal-weight
   basket buy & hold; long/flat and window books (three, four, six, seven,
   eight, nine) against their own basket buy & hold.

## Step zero, rewritten in this pack's numbering (three descriptive scripts, no trading)

D1 funding-file read — cards one, four, five, eight: lagged funding-delta
   dispersion and 30-day rank staleness (one); in-market fraction and regime
   persistence of the 365d-median gate (four); monthly realized carry
   collection AND high-minus-low price differential between 30d-avg funding
   quartiles (five); distribution of post-00:00-settlement moves keyed by
   the 30d-avg funding sign, under the F1-held convention (eight).
D2 price-file calendar read — cards three, six, seven: per-episode means of
   the turn-of-month window (close day-27 to close day-2), the conditional
   weekend window (Fri 12:00 to Mon 00:00), and the month-open four-hour
   window, on BTC/ETH and the four majors, full long window.
D3 rank diagnostics — cards two and ten: monthly rank churn (turnover of
   the vol-rank and volume-growth-rank panels) and cross-rank correlation of
   both keys against past returns (how non-momentum each book truly is).

Declared pre-engine kill bars (stated now, in the cards' own demand units):
card five dies if median monthly carry collection < 22 bps on the book; card
four dies if the gate keeps the book in-market below a quarter or above
three-quarters of days; card eight dies if the median favorable move under
its sign key is below half the 23 bps demand; card three if the turn-of-month
episode mean is below 18 bps; card seven if the month-open four-hour mean is
below 12 bps; card six if the conditional weekend mean is below 12 bps.
Diagnostics that inform without killing: one (dispersion + staleness) and
all of D3. Each diagnostic persists its own artifact — kill decisions are
numbers, so they need artifact backing like any other.

## Honest prior

The cards' own verdict lines concede likely death on all ten. My prior is
zero to two cells clearing the G-set after costs, with card two the
strongest, cards three and six honest cheap tests, and the rest dying on
thin per-unit edge — exactly what Step zero settles before any engine is
written. The brief did its job: specific cards, correct arithmetic, no
banned-family re-dress on the letter.
