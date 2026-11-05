# Recorder book-reconstruction audit

## Question

Can the recorded depth stream rebuild the order book, well enough that the depth data is an asset rather than decorative disk?

## Method (frozen before seeing any number)

Replay depth diffs in exchange event time, never receive order. Bind each depth snapshot at the first diff whose range satisfies the documented rule: U minus one less than or equal to lastUpdateId less than or equal to u minus one. This prevents lookahead. After binding, apply diffs when previous update id matches pu; any break marks the book invalid and ticks while invalid count as no state, never as match or mismatch. Recovery requires binding a newer snapshot at a later diff.

Compare once per applied diff against the bookTicker most recent at or before that diff's exchange time. Depth diffs aggregate every hundred milliseconds while bookTicker ticks continuously, so tick-by-tick comparison would mismatch inherently.

Control: each ticker compared against itself fifty thousand ticks later must score at most zero point nine zero zero, or the test proves nothing.

Thresholds frozen in advance on BTCUSDT (deepest book, hardest case):
- exact match at or above zero point nine nine zero = PASS
- exact match zero point nine five zero to zero point nine nine zero = WARN, usable with resync repair
- exact match below zero point nine five zero = FAIL, delete depth, keep forceOrder

## Result (measurements live in `recorder/coverage/book_audit.json`)

The worst cell is BTCUSDT below the nine five per cent warn floor. Exact match is zero point nine four four zero on roughly forty five thousand comparisons, with one sequence break repaired by the next snapshot and placebo at zero point zero zero zero. Price-only match is zero point nine nine nine eight: best bid and ask prices reconstruct essentially perfectly; quantities fall short by a few percent, inherent to hundred-millisecond diff aggregation.

The other three symbols land in the warn band:
- XRPUSDT zero point nine seven three three
- SOLUSDT zero point nine six five zero
- SUIUSDT zero point nine eight one two

All four symbols show zero placebo self-match: the test has teeth. All four show essentially perfect price reconstruction.

## Verdict

FAIL. The worst cell (BTCUSDT) is below the nine five per cent floor. Under the pre-agreed decision rule, depth and depth_snapshot are not an asset: they cannot be anchored to the REST snapshot sequence and cannot certify a resting-maker fill model. They are deleted. forceOrder (the liquidation tape, needs no reconstruction) and bookTicker (independent ground truth) are kept.

## Consequence

No consumer exists in the repo for L2 depth today: no certifiable maker strategy, no grid, no momentum strategy reads it. The fill-model rule forbids certifying resting-maker fills on OHLC at five minutes or above without one-minute resolution or a forward record. With the reconstruction test failed on the deepest book, keeping more than two hundred megabytes per day of unanchored depth violates the house rule: delete dead weight, keep only what has value, nothing duplicated, nothing wasting space.

## Files

- `recorder/_audit_book.py` — the audit, read-only over `recorder/data/`
- `recorder/coverage/book_audit.json` — the measured numbers behind every percentage above
- `recorder/coverage/coverage_live.json` — live coverage counters
