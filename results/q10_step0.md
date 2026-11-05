# STEP ZERO — the Qwen ten-card pack: pre-engine diagnostics (2026-10-23)

Three descriptive diagnostic artifacts, no engine, no trading, no costs. Every
number below is quoted from its artifact; the run_ids are constant throughout:
funding read `fb5f3c9400e9d423`, calendar read `6b3e93b908b66ed0`, ranks read
`78821d5e9a43b8a2` (all three `verify` OK, bit-for-bit reproduced). Counting is
in words; per-unit figures are bps on total gross of one, exactly per the
pinned conventions in `results/qwen_pack10_grade.md`.

Self-checks, measured inside the funding artifact: settled prints per day
range two-ninety-nine-point-seven to three-point-zero-three across the four
majors (three expected), the collection rotation's vectorized and looped
forms agree to one-e-12 bps (the artifact's own parity gate), and all three
kline files carry an hourly grid. The funding history covers every scored
month; nothing was extrapolated.

## KILLS — four of ten cells die before any engine exists

- CARD FIVE (funding-carry quartile rotation): median monthly carry
  collection nine-point-three-one bps on the declared buckets
  (`fb5f3c9400e9d423`) against the twenty-two bps demand — seventy-three
  back by month, fifty-two of seventy-one months... precise: positive in
  eighty-four-point-five percent of scored months but far too thin in level.
  KILLED under its pre-declared bar (median < twenty-two bps). Note for the
  record, not a rescue: the price-side differential median of +sixty-nine
  bps is a diagnostic of the same buckets' relative returns; the declared
  bar was the carry, and the carry failed by a factor of about two-and-a-
  half. The carry-crash check the grade file asked for also lands: the long
  bucket (lowest 30d-avg funding) OUT-EARNED the short bucket on price,
  i.e. the high-funding names kept rising — the price side of this carry
  book works AGAINST the hypothesized funding fade.
- CARD EIGHT (settlement-hour carry): median favorable move per episode
  zero-point-seven-two bps over two-hundred-eighty-four episodes against a
  half-demand bar of eleven-point-five bps (`fb5f3c9400e9d423`). KILLED.
  The levy itself measured a median of one-point-zero bps: one settlement
  of carry cannot pay twenty-three bps of round trip. The composition flag
  F1 also materialized: sixty-seven-point-six percent of months put all
  four legs on ONE side (long share of legs just sixteen-point-five
  percent) — the book is a funding-sign bet on the whole panel, not
  neutral, in most months.
- CARD SEVEN (month-open four-hour ride): mean open-to-open move over the
  month's first four hours, four-name basket: +four-point-five-two bps per
  episode across seventy-one months (`6b3e93b908b66ed0`) against a twelve
  bps bar. KILLED. The month-open drift is roughly one-fifth of the round
  trip, before any funding or slippage assumptions.
- CARD SIX (weekend funding rider): gated weekend mean negative
  twelve-point-four-nine bps against a positive-twelve bar
  (`6b3e93b908b66ed0`), over two-hundred-seventy-one weekends with the gate
  active in sixty-five-point-seven percent of them. KILLED — and the sign
  is INFORMATIVE: calm-funding weekends carried NEGATIVE drift in mean
  (median +thirty-three-point-five bps only by right-skew), so the "thin
  books pay carriers" prior reads backwards on this gate.

## SURVIVORS at Step zero — six cells remain, cards one, two, three, four, nine, ten

- CARD THREE (turn-of-month): NOT killed — and stronger than its prior.
  Mean per-episode move of the declared close-day-27 to close-day-2 window
  is +one-hundred-forty-four-point-four-five bps, and the executable
  fill-t+1 variant (open day-28) differs from it by less than
  one-hundredth of a bps (`6b3e93b908b66ed0`, seventy-one months). The
  median is +one-twenty-three-point-two bps. Against the card's own
  thirty-six bps demand, headroom is four times the cost. The declared open
  risk is unchanged and is a GATE question, not a drift question: the
  window sits inside a long decade for BTC/ETH, so G5 (beat basket B&H),
  G3 balance and concentration decide at the engine step.
- CARD FOUR (funding-regime biweekly L/flat): NOT killed — the panel gate's
  in-market fraction is sixty-six-point-four-two percent, in-band
  (`fb5f3c9400e9d423`, one-hundred-thirty-four valid decisions). Flag for
  the engine step: the by-year in-market split is one-hundred percent in
  the twenty-twenty-two column and ninety-two-point-three percent in
  twenty-twenty-five — the gate keeps the book long through the one year
  that dropped most of what the G3/G5 gates punish. Median long spell
  three-and-a-half decisions (about seven weeks).
- CARD ONE (funding-delta monthly rotation): informer, no pre-declared
  bar. Reads bad: the monthly funding differential between its buckets is a
  median of +two-point-nine-two bps (tail months carry the mean, which is
  negative at −six-point-four-three), the price differential between the
  same buckets has a NEGATIVE median of −fifty-one-point-nine-eight bps,
  and the rank-staleness Spearman median is +zero-point-two-six — the 7d
  delta barely ranks next month's funding at all. Per-year median
  combined: seven months of single-digit or negative bps except twenty-
  twenty (`+seventy-eight-point-six-seven`) (`fb5f3c9400e9d423`). Against a
  twenty-two bps monthly cost demand this cell enters the engine step as
  the pack's weakest; per the no-rescue rule it runs as declared, and the
  runaway favorite outcome is the gate killing it on its own metrics.
- CARD TWO (low-vol monthly L/S): informer. The vol-rank's side flips run
  a median of twenty percent of legs per month (`78821d5e9a43b8a2`) — the
  book churns about a tenth of full monthly replacement, so realized fee
  drag should come in under the declared two-sixty-four bps/yr ceiling.
  The vol key's Spearman against trailing returns is −zero-point-oh-four
  median: as declared, this is NOT a momentum book on the sorting key
  (|corr| > half in forty-one percent of months).
- CARD TEN (volume-growth monthly L/S): informer. The growth key carries
  a +zero-point-three-six median Spearman against trailing returns
  (`78821d5e9a43b8a2`) — the momentum-correlation the grade file predicted
  is real; the flipping runs forty percent of legs per month, roughly
  double card two's churn, so the same cost ceiling does not apply to it.
- CARD NINE (vol term-structure long/flat): no dedicated diagnostic was
  sacrificed to it — it shares card four's book shape (grade file flag F4)
  and enters the engine step with the same gate-family exposure risk that
  card four's twenty-twenty-two column demonstrates.

## Status

Four cells withdrawn by their own declared pre-engine bars: five, six,
seven, eight. No alternates were declared for any card, so the pack's
declared run set is unchanged in composition — it is now six cells, cards
one, two, three, four, nine, ten — and nothing else was tuned, swapped or
rescued. Run order per the pre-registration: engines next, known-answer
audit of the shared primitives BEFORE any real-data run, repo6x5 costs,
funding charged where a card says to charge it. Step zero verdict is final
against its own pre-declarations.
