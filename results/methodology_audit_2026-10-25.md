# Methodology audit — the backtesting framework itself — 2026-10-25

AUDIT OF METHOD, not of engines: the statistics, the cost/execution theory,
the gate design, the data/universe rules, and the verification framework.
The empirical numbers below come from one-off diagnostic experiments run
this session (null-strategy calibration through a real executor; a guard
collision test). They are labelled DIAGNOSTIC — no run_id, not artifacts,
never to be quoted in a results table. The standing fix for that labelling
burden is recommendation R1.

## What was measured this session (DIAGNOSTIC)

- NULL CALIBRATION, high-n regime: two hundred random-entry strategies (no
  edge, real BTC 1h data, real executor, repo costs, ~176 trades median)
  against the repo gate set. Result: zero of two hundred pass the joint
  gates; the best noise PF was one point one six six against the one point
  two gate. The gate set is not loose when trade counts are ample.
- NULL CALIBRATION, n-floor regime: three hundred random strategies on the
  2024+ window (~seventy-five trades median — the regime where the corpus's
  short cells live, n between thirty and one hundred). Result: five percent
  pass PF>1.2 together with n>=30. At a sweep of a hundred cells that is
  about five expected noise survivors of the PF gate — the defense against
  them is the second-tier gates (halves, period split, concentration), which
  is exactly how the corpus's own "aggregate passes that die on period
  split" pattern arises.
- GUARD COLLISION: a fabricated report citing one real artifact. Distinctive
  unbacked numbers were refused; fabricated small integers (counts like
  seventeen, thirty, three, two) passed, because they collide with values
  that exist inside the cited artifact.

## Findings (M-series), ranked by leverage

M1 — GATE STATISTICS: the PF>1.2 gate with an n>=30 floor has a measured
~5% per-cell false-positive rate in the n<=100 regime (diagnostic above).
n=30 is CLT-adequate for a mean, not for a ratio estimator over skewed trade
PnLs. The walk-forward selector's min_trades default (twenty) sits below
even that floor. Fix: scale the n floor to the claim (n>=100 for a PF
headline), or derive the PF threshold from a null calibration at the
family's own trade geometry (R1).

M2 — MULTIPLE TESTING IS ACKNOWLEDGED BUT NEVER QUANTIFIED: the repo's own
lesson says a permutation control cannot detect a selected sample, and the
XRP report admits a "haircut applies" — but no sweep report states its
expected false-pass count (cells x measured per-cell rate). With the
diagnostic rate above, a hundred-cell sweep should state "about five
expected noise survivors of PF+n; survivors are only candidates until the
period-split/concentration gates run", as a number, not a vibe.

M3 — BOOTSTRAP IS I.I.D. OVER TRADES: per-trade PnLs cluster with volatility
regimes; i.i.d. resampling understates the variance of the mean and yields
too-narrow CIs. The XRP result survives any plausible correction (its
t-statistic is enormous), but the method should be block bootstrap by
calendar blocks so the next strategy's CI is right by construction, not by
luck.

M4 — THE BUY&HOLD ALPHA GATE HAS NO EXPOSURE ADJUSTMENT: a long-only book
holding forty percent of bars is compared raw against a fully-exposed
index; and "beats B&H only where B&H fell" was treated as non-alpha (the
fingrad SPX/SUI cells), which is backwards for a two-sided book — holding
value while the underlying falls IS the alpha claim there. Fix: exposure-
matched B&H (index return x realized exposure) or a DD-matched leverage
comparison, and apply the "falling market" clause only to long-only books.

M5 — MAKER-FILL-ON-TOUCH (grid family): the neutral books charge maker fees
and fill a level whenever the bar touches it (entries require a strict
through). Real post-only fills need queue position and suffer adverse
selection — your resting order fills precisely when price is going through
it. For a strategy whose edge IS many small maker wins, this is the
load-bearing optimistic assumption, and no gate or sensitivity pass prices
it. Fix: a fill-probability haircut (fill only when the bar crosses the
level by k x ATR, or charge taker on a fraction of fills) as a standing
sensitivity, in-artifact, the way funding drag is measured today. The
forward paper run measures it honestly — but the backtest record should
carry the assumption's cost.

M6 — COST MODEL: a single fixed eleven-bps roundtrip for all sizes, times
and symbols, measured once at a ten-thousand-dollar clip, while equities in
the compound paths reach sizes where that clip's impact does not apply (and
the twenty-five-USDT bot pays effectively none). The per-symbol measured
table exists (results/cost_model_2026-10-25.json) but no engine consumes
it. Funding treatment also varies across the corpus (charged real in
cbpackf/xrpneutral; constant-rate ledger in smqe; absent elsewhere),
so cross-family comparisons are not like-for-like. Fix: size-dependent
slippage schedule; engines consume the measured per-symbol RT; declare a
funding convention per family in one place.

M7 — UNIVERSE AND WINDOWS: the symbol set is the survivors with data (no
delisted names) — fine for per-symbol kills, inflating for any
portfolio-level or median-across-symbols claim. Histories are
heterogeneous (SUI 2023, JUP 2024, majors 2017-2019), so "green in >= 2/3
years" is a different test on three years than on seven, and there is no
per-year trade floor (a year green on three trades is noise). Fix: per-year
minimum n or shrinkage; state each cell's window in every table it feeds.

M8 — FILL-TIME CONVENTION IS NOT NORMALIZED: ports preserve each Pine's own
convention (some fill at the signal close, some at the next open) —
faithful to TradingView, but the corpus then mixes microstructure
assumptions, and same-close fills are optimistic relative to anything
executable. No same-close survivor has been re-scored under next-open
fills. (Self-criticism: my own smqe campaign is a same-close port and I did
not run that sensitivity.) Fix: a mandatory next-open re-score column for
every same-close survivor, in-artifact.

M9 — VERIFICATION THEORY: verify proves determinism and provenance, not
correctness — correctness lives in hand-built known-answer audits with no
coverage criterion, and the audits themselves are unaudited code (this
session: one real engine bug found, and more expectation bugs in the tests
than in the engine). Artifacts pin engine bytes and data bytes but NOT the
interpreter/library versions, while library behavior is load-bearing (the
datetime64 ms resolution is assumed in two engines; one diagnostic metric
is already wrong under it — see the companion repo re-audit, F7). Fix:
record python/numpy/pandas versions in provenance and assert them in
verify; mutation-test the audits occasionally (flip one constant in the
engine, require the audit to fail).

M10 — GUARD'S COLLISION RATE: measured — small integers and round numbers
pass by coincidence while distinctive numbers are refused. "Guard OK" is
weaker than it reads for counts and small percentages. Fix: ignore tokens
below two significant digits (they must be written in words — the repo
already has that rule for tallies; make guard enforce it mechanically), or
scope matching to the artifact cited nearest the number.

M11 — STRUCTURE: the per-sweep index CSV is overwritten by every pmatrix
pass (observed twice this session) — the artifacts persist but the sweep's
table of record does not; _load_module caching means any future adapter
that mutates module globals without _load_fresh leaks sizing across runs
in-process; cbpack's equity .ffill() can silently bridge data gaps.

M12 — REPORTING STATISTICS: period thirds and calendar years are computed
from the equity curve, halves from trade PnLs — three overlapping,
non-independent stability statistics reported as if they were separate
confirmations. They are one statistic viewed three ways. Fix: say so in
the reports, and treat "period split" as the single mandatory stability
gate it already is in practice.

## What the framework gets right (also measured)

Zero of two hundred null strategies pass the joint gate set at ample trade
counts — the PF floor plus period split plus concentration is a genuinely
hard filter under real costs. Fees are charged on both sides of every fill
in every audited engine. SL-first tie resolution is conservative.
Walk-forward train/test bounds do not overlap. Funding settlement
accounting (cbpackf) sums multi-settlement bars and refuses gaps.
Determinism is real: verify reproduces bit-for-bit, and the known-answer
layer has caught real bugs (twice this session alone).

## Recommendations, in order of leverage

R1. Add a standing `vrun nullgate --strategy X` command: generate the null
    PF/pass distribution at the family's own trade geometry (random entries,
    same executor, same costs), store it as an artifact, and cite the
    measured per-cell false-positive rate and the null PF p95 in every
    sweep report. This converts M1, M2 and every future threshold debate
    from asserted to measured — and the experiments above become the first
    such artifacts instead of one-off diagnostics.
R2. Exposure-matched B&H gate (M4) and a next-open re-score column for
    same-close survivors (M8) — both cheap, both close an optimism hole.
R3. Maker-fill sensitivity pass for the grid family (M5), in-artifact,
    measured like funding drag.
R4. Block bootstrap (M3); per-year trade floors (M7); version pinning in
    provenance (M9); guard small-number policy (M10); append-only sweep
    indexes (M11).
