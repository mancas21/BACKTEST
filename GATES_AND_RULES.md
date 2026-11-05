# GATES AND RULES — the validation contract of this repo (v2)

A single reference for the gate set and every standing rule a backtest in this
repository must pass. It consolidates `AGENTS.md` and `VALIDATION_PROTOCOL.md`;
those two remain the canonical texts.

**Scope note (so the tooling and this document cannot fight each other):** this
is a policy document, not a results report. It states rule constants and
thresholds; it quotes **no performance results** — every result in this repo
lives in `results/*.md` with its `run_id`, and those reports are the guard
targets. Measured properties of the gate set itself (false-positive rate,
power) live in `results/gate_calibration_report.md`.

**Version history.** v1 (2026-10-27) codified the six gates the pack engines
had been using. v2 (2026-10-27, same day) is the response to an external audit
of v1: the gate set gains a measured calibration, a trial ledger, and the
statistical gates G7–G10; the PF definition is corrected; the cost rule is
amended; several criteria become machine-checkable. **Existing artifacts keep
their v1 verdicts** — the gates are part of the artifact bytes and are never
retroactively re-applied. v2 applies to new campaigns, and the claude2 pack's
near-miss candidates have been re-scored under v2 (`results/gate2_scoring.md`).

**v2.1 (2026-10-27): a second, independent implementation of the same audit
arrived (`BACKTEST AUDIT FIXES-CLAUDE.zip`) and was cross-checked against this
repo's layer.** It is adopted as the **reference layer** with two fixes, and
its ideas are merged: policy constants live in a `POLICY` dict whose hash is
written into every artifact; the artifact store is hash-chained; the trial
ledger is chained; G3 is a purged split **and** folds; G2 enforces effective
N; G4 buckets by exit month with a six-scored-bucket floor; G6 also removes
the best ISO week; G9 fails closed without declared leverage or per-trade MAE
and adds a liquidation-distance check. The cross-validation results are
measured inside the calibration artifact (`results/gate_calibration_report.md`).

---

## 1. The v2 gate set (G1–G11)

The statistical gates are **measured inside each artifact** by
`code/gate2.py` (self-audit: `code/_gate2_audit.py`), never assembled by the
reader. The **reference layer** `code/_gates_v2.py` (adopted from the second
implementation, self-test `code/_gates_v2_selftest.py`) carries the same
policy values and the auxiliary tooling. A candidate must pass **all
applicable gates**.

| Gate | Name | Rule | Where implemented |
|---|---|---|---|
| **G1** | Expectancy (primary) / profit factor (secondary) | Block-bootstrap **95% lower bound of per-trade expectancy > 0 bps**, with PF > 1.2 kept as a secondary condition. Expectancy and PF are defined on **per-trade percentage returns at fixed size** (see §7). | `gate2.expectancy_lb_bps`, `gate2.profit_factor_pct` |
| **G2** | Sample size | **≥ 100 closed trades**, and **≥ 30 per symbol** for multi-symbol books; **effective N** (autocorrelation-adjusted) is reported next to the raw count. | `gate2.effective_n` |
| **G3** | Split and folds | **(a)** The purged 70/30 split on entry time: boundary-crossing trades removed from both sides, both halves PF > 1, the out-of-sample half ≥ 30 trades. **(b)** Five equal-time folds, boundary-crossers purged from both adjacent folds, **≥ 70% of scorable folds** (≥ 10 trades each) PF > 1. Both must hold. Parameters are **frozen**; any fitting happens before them. | `gate2.purged_split`, `gate2.purged_folds` |
| **G4** | Calendar buckets | Net PnL bucketed by **exit month** (declared). ≥ 5 trades per scored bucket, **at least six scored buckets** (fewer = insufficient sample = fail), **≥ 60% green**, worst bucket no worse than −15% of starting capital. | `gate2.period_buckets` |
| **G5** | Benchmark | For directional books: **beats buy & hold**. For neutral / long-short / low-exposure books: **beta-adjusted alpha with t > 2** (block-bootstrapped) against the same market series, plus a vol-matched buy & hold comparison. | `gate2.beta_alpha_t` |
| **G6** | Concentration | Net result stays **> 0 after removing the top 5% of trades** (scale-free, minimum five), **the best calendar month**, **and the best ISO week**. Clustered wins from one event are concentration too. | `gate2.top_frac_concentration`, `gate2.best_month_removal`, `gate2.best_week_removal` |
| **G7** | Multiple testing | **Deflated Sharpe Ratio** using the trial count from the ledger (`results/_trial_ledger.json`), or **PBO via CSCV**, or White's Reality Check / Hansen SPA / BH-FDR. The campaign-level DSR/PBO verdict is a campaign artifact, not a per-run one. | `gate2.deflated_sharpe`, `gate2.pbo_cscv` |
| **G8** | Cost robustness | **PF > 1 at twice the gate cost**, and the **breakeven per-side cost** (measured inside the artifact by bisection with real engine re-runs) **≥ twice the gate cost**. | `gate2.breakeven_side_cost` |
| **G9** | Drawdown / ruin | **P95 of the bootstrapped max drawdown ≤ 35%** of starting capital on the **mark-to-market** series; **fail closed** if leverage is not declared; **fail closed** if the engine does not emit per-trade MAE; **no trade whose MAE reaches the liquidation distance** (`1/leverage − maintenance margin`). The null distribution of P95 drawdown is measured (median near a third of capital), so the cap is a genuine tail gate. | `gate2.p95_max_dd`, `gate2.drawdown_stats`, engine MAE |
| **G10** | Pre-registration | The spec, grid, gates and a **locked final holdout** are committed (commit hash) **before** the run; every query of the holdout is counted. An un-pre-registered campaign carries `pre_registered: false` in its artifacts and is judged with the multiple-testing haircut of G7. | process rule; artifacts carry the flag |
| **G11** | Win-rate margin *(added 2026-11-01)* | If **win rate ≥ 75%**, it must sit **≥ 5 percentage points above the breakeven win rate** `1/(1+payoff)` (payoff = mean win / mean loss on the net series; a book with no losers passes trivially). Static fragility signature of high-win-rate negative-skew books — they die on the left tail and on fill-model optimism, not on the right tail; the killed XRP grid ran ~87% win at ~3pp margin. Adopted from the external qbt gate audit (its G7). Enforced in `_gates_v2.evaluate_gates_v2`; not yet in the G1–G9 null-calibration joint (fold in at the next recalibration). | `_gates_v2.gate_g11` |

**Cost admission (amended by the cross-check).** The repo's own cost file
measures eleven USDT-M symbols **above** the 11 bps gate round trip (XRP, SOL,
SUI, HYPE, JUP, SPX among them). The scanner rule is therefore: a thin-name
artifact must declare the **resolved** gate cost — the greater of the repo
default and the measured per-symbol round trip — not the default.
`code/_gates_v2.load_cost_model` reads the real cost-file schema and
`admit_declared_costs` enforces it.

**Data integrity and funding intervals are tooling, not prose.**
`_gates_v2.data_integrity_report` (duplicates, gaps, bad OHLC, wick outliers)
runs clean on the store's BTC 1h, ETH 5m and SPX 1m files.
`_gates_v2.infer_funding_intervals` confirmed on real funding files that the
8-hour assumption is false in this data: JUP's modal interval is four hours,
and BTC's history contains sixteen-hour intervals — funding must always be
charged from each symbol's own settlement file, which the pack engines do.

**Tamper evidence.** The artifact store is hash-chained sidecar-first:
`results/runs/_CHAIN.jsonl` (built and verified by `code/_artifact_chain.py`)
pins the bytes of every artifact without touching `run_id`; the trial ledger
has a chained form at `results/_trial_ledger.jsonl`. Byte changes to any
chained artifact are detectable independently of the harness's bit-for-bit
re-run.

**Gate calibration is part of the contract.** The gate set itself is measured:
seeded random-entry null books on real prices, run through the same audited
execution core, give the empirical **false-positive rate** at zero edge and the
**power curve** at planted edges of a few bps per trade. The current
calibration artifact is cited in `results/gate_calibration_report.md`, and it
also records the **reference layer's** rates on the same real market from its
own null generator — the two implementations' agreement is a measurement, not
an assertion. When the gates change, the calibration is re-run. A gate change
that raises the measured false-positive rate needs an explicit justification
in this document.

**Cross-check outcome (2026-10-27), for the record.** The reference layer's
self-test passes in full. Head-to-head: the DSR implementations agree to four
decimals when fed the same across-trial Sharpe variance; PBO agrees on a
planted matrix; the null false-positive rates agree on real data. The
cross-check found two real defects in the reference layer — a silent
garbage-timestamp trap on positional indexes (fixed: it now fails loud) and a
cost-model parser that missed this repo's schema (fixed: it reads it) — and
one gap in this repo's layer (the best-week removal), closed here. Legitimate
differences that remain, declared: the reference layer's G5 uses daily
Newey-West alpha while this repo's uses bar-level block-bootstrap alpha; its
G8 breakeven is algebraic on the cost column while this repo's re-runs the
engine (exact slippage-in-price); its G9 bootstraps the trade sequence while
this repo's uses the mark-to-market bar series. Where the two layers
disagree, the stricter reading wins.

---

## 2. What v2 changed, finding by finding

- **False positives and trial count (was C1).** The v1 set was never
  calibrated and the verdict list had burned well over a hundred candidates
  with no accounting. Now: the calibration harness measures the false-positive
  rate and the power curve; the **trial ledger** (`code/_trial_ledger.py`,
  derived from the append-only run store) counts every tried candidate; G7
  deflates survivor claims by that count. The one surviving book carries a
  **program-level haircut on top of its own grid haircut** until its forward
  paper run speaks.
- **Power at small n (was C2).** G1-v1 (PF > 1.2 at 30 trades) had almost no
  power: at a fifty-percent win rate, PF 1.2 is roughly a t-stat of a half at
  thirty trades and needs hundreds to reach two. G1v2 gates on the
  bootstrap lower bound of expectancy in bps; G2v2 raises the floor to one
  hundred trades.
- **The burned holdout (was C3).** Reusing the same 30% tail to judge every
  candidate made it in-sample. G3v2 replaces the single split with purged
  folds; the **locked final holdout is the forward paper run**, and querying
  it is countable and counted. Pre-registration (G10) is now part of the
  contract.
- **Inventory blindness (was C4).** Closed-trade metrics can look perfect while
  a grid is underwater. G9v2 is a mark-to-market gate: the drawdown is computed
  on the equity series that includes open positions, and the end-of-test
  inventory is closed out with exit costs inside the engines. For grid books
  specifically: maker fills must be modeled conservatively (a fill requires
  trade-through, or a declared probabilistic fill model), because "filled on
  touch" ignores queue position and adverse selection; tick-level validation is
  a **declared limitation** until tick data exists on disk. The neutral XRP
  book's artifact already carries the margin buffer, the leverage-ceiling
  check and the long-only/short-only controls; the short-leg liquidation and
  ADL scenarios are required before any real-money promotion.
- **Sizing and the PF definition (was H2).** The v1 text was wrong: risk-based
  sizing reweights trades by stop distance, so it **changes** profit factor.
  Correct statement: PF is invariant to a *common* scaling of every trade, not
  to per-trade reweighting; under compounding, currency-PF also overweights
  late-equity trades. **v2 defines PF, expectancy and the G4/G6 sums on
  per-trade percentage returns at fixed size**; compounded currency results are
  reported separately and labeled.
- **Cost model (was H3).** The 11 bps round trip stays the default gate for
  liquid majors, with three amendments: (1) **G8** requires the book to survive
  twice the gate cost and measures its own breakeven; (2) for **thin names the
  measured per-symbol round trip (10.0–30.5 bps, `results/cost_model_2026-10-25.json`)
  is binding, not advisory** — a thin-name artifact that declares only the
  default cost is incomplete; (3) the cost snapshot is a single regime
  (2026-10-25) applied across years with different fee and liquidity regimes,
  and stop exits are the stress fills — engines that live by stops must declare
  a stop slippage assumption. Size-dependent impact under compounding is a
  declared caveat: breakeven cost is the honest control, and it is measured.
- **The benchmark (was H4).** Raw return versus buy & hold is unfair in both
  directions to neutral and low-exposure books. G5v2 adds the beta-adjusted
  alpha t-test and the vol-matched comparison.
- **Scale-dependent concentration (was H5).** Removing five trades is
  seventeen percent of a thirty-trade sample and a rounding error at three
  thousand. G6v2 removes the top five **percent** and the best month.
- **Crude calendar years (was H6).** G4v2 uses monthly buckets with a minimum
  trade count, a worst-bucket cap, and thin buckets reported; partial first and
  last months no longer carry equal weight.
- **Machine-checkable criteria (was M1).** Cost share is now a hard rule:
  **fees as a share of strict gross profit < 30%** (was a 30–40% range).
  Neighborhood stability is a rule for fitted-parameter engines: **≥ 70% of
  ±1-step parameter neighbors must pass G1 and G3** (not applicable to prompt
  packs whose constants are the prompt's own, and declared as such).
- **Dependence across books (was M2).** All bootstraps in `gate2.py` are
  **moving-block**, not iid, and effective N is reported. Trades pooled across
  symbols share market beta; portfolio verdicts must report effective N and
  treat the pool as correlated.
- **Look-ahead (was M3).** Beyond the existing no-look-ahead and
  no-stopless-entry audit groups, engines must pass a **truncation-invariance
  test**: signals computed on `data[:T]` equal signals computed on `data[:T+k]`
  up to `T` (this catches higher-timeframe bars merged on `open_time`), and
  entry-bar stop handling is asserted.
- **Data risks (was M4).** Declared per campaign: survivorship (delisted perps
  are absent from the store — a known, uncorrectable-today bias toward
  survivors); wick/gap cleaning rules; per-symbol funding intervals (1h/4h/8h —
  funding is charged from each symbol's own settlement file, never a global
  8-hour assumption); last-price vs mark-price for stops; explicit slippage
  assumptions for stress windows (May 2021, the 2022 exchange collapse, the
  October 2025 liquidation cascade).
- **Reproducibility (was M5).** New engines record Python/numpy/pandas
  versions, seeds and gate constants inside the artifact. **Debt, declared:**
  the `run_id` binds engine bytes, params and data bytes but not the
  environment; binding environment metadata into the hash would orphan the
  existing corpus, so it is recorded-but-not-bound until the next deliberate
  protocol break. An artifact hash chain is the same class of deferred work.

---

## 3. REGLA 0 — the artifact protocol (unchanged by v2)

> A number is a result only if a persisted run artifact backs it and that
> artifact verifies. Otherwise it is text and must not be reported.

- All runs go through the harness `code/vrun.py`. Never hand-write metrics.
- `run_id = sha256(engine_bytes + canonical params + [(data_path, data_sha256,
  bars)])[:16]`. Change the engine, the params or the data and the id changes.
- Every results table cites its `run_id` and artifact path; `results/runs/` is
  append-only.
- `verify` before publishing — exit `0` OK · `2` REFUSED (never publish) ·
  `3` STALE (re-run) · `4` ORPHANED.
- `guard [--strict]` on any results report before it is sent. Guard is a
  **provenance** check, not completeness or correctness; it cannot back a
  derived number — the needed quantity must be **measured inside an artifact**.
- **Tallies:** new engines measure their own counts inside the artifact
  (`n_pass_gates`-style fields); derived counts in prose are written in words
  and reconciled by recomputation (`code/_assert_report_totals.py` template).
- Synthetic or illustrative scenarios are labelled, carry no `run_id`, and
  never enter a results table. (The null-calibration artifact is not synthetic
  market data: its nulls trade real prices; only the entry times are random.)

## 4. Sources of truth (unchanged)

Binance CSVs are the only market data. TradingView is eyeball only. Synthetic,
GBM and author-reported figures are not evidence until reproduced.

## 5. Porting rules (v2 additions in place)

1. Port with the source's constants and execution conventions: entry at next
   open, SL-first on ties, fees on every fill.
2. Parity / self-check ALL PASS before any market run.
3. Then `vrun.py`, then report with a `run_id`.
4. Known silent-bug classes: `ta.pivothigh` is not a rolling max; tz-aware
   `astype("int64")` is unit-dependent; **a negated-NaN gate like
   `~(ema50 > ema200)` is True during warmup and opens stopless positions**;
   higher-timeframe frames merged on `open_time` leak forward.
5. **No entry may fire on a bar whose stop level is undefined.**
6. **Truncation invariance** must be asserted (§2, M3).
7. A scored slice must state its warmup convention.
8. Audit-test failures are usually the test's fault — check data ranges, epoch
   constants, month lengths and closed-vs-open conventions before touching the
   engine.

## 6. Execution conventions (v2 additions marked)

- Signals on a closed bar; fills at the next open; signal exits one bar late;
  stops and targets intrabar; **stop fills first** on ties.
- Flat-by-time rules fire one bar late. Higher-timeframe filters use only the
  last fully closed bar.
- **PF and expectancy are per-trade percentage returns at fixed size;
  compounded currency results are reported separately and labeled** (H2).
- Pair books are dollar-neutral, half the equity per leg, costs and funding on
  both legs. **Maker fills for grid books require trade-through or a declared
  probabilistic model** (C4).
- One artifact carries the same signals at the pack's own block, the repo gate
  cost, twice the gate cost, zero cost, and (for candidate books) the measured
  breakeven (G8).

## 7. Do / Don't

**Do**
- Keep `run_id` next to every metric; keep artifacts in `results/runs/`.
- Re-fetch/extend data only with the documented scripts, then re-verify.
- Re-read files before editing (parallel sessions edit this repo); re-verify
  artifacts before publishing.
- Pre-register spec, grid and gates before the run (G10); count holdout queries.

**Don't**
- Don't overwrite or delete `results/runs/`, `data/`, `code/`, `backups/`.
- Don't present a number whose artifact fails `verify`.
- Don't cite the two fabricated SAX figures AGENTS.md warns about, or any
  number from a killed campaign re-derived by hand.
- Don't re-run a killed pack expecting a different verdict; the documented
  failures are failures of signal and sample, not of a misplaced constant.
- Don't let a rules document and a results report blur: results carry
  `run_id`s and are guard targets; this policy document is not.

## 8. Limitations register (declared, not hidden)

1. **Tick-level maker fills** do not exist on disk; grid backtests run on OHLC
   bars with conservative fill rules, and their fidelity is bounded by that.
2. **Survivorship**: delisted perps are missing from the store.
3. **Cost regime**: one live-book snapshot (2026-10-25) across all years;
   G8's breakeven is the control, not a regime model.
4. **Environment binding**: versions and seeds are recorded in new artifacts
   but not yet hashed into the `run_id` (deferred to avoid orphaning the
   corpus); no artifact hash chain yet.
5. **PBO/CSCV** is implemented but a campaign-wide PBO needs the full
   candidate returns matrix; the near-miss re-scoring covers the claude2
   candidates only.
6. **G10** was introduced after every campaign to date: all current artifacts
   carry `pre_registered: false` and are judged accordingly.

## 9. Standing verdicts (summary)

Killed or rejected: SAX Scalper PRO v3.0 · FFS-v1 · XPROP-LAG / COINT-DYN ·
CVRMD (fragile/suspended) · the QUANT CRYPTO BOT ten-strategy suite ·
`cbpack` below 1h with its 1h survivors gone on concentration · `cbpackf` at
every cell once funding and concentration are measured · the Qwen
ten-strategy pack (rejected before porting) · the claude1 fifty-prompt pack ·
the claude2 fifty-prompt pack. Full reasons and run_ids: `STATUS.md` and the
campaign reports in `results/`.

The one book that has cleared every v1 gate to date: the **delta-neutral XRP
grid** (`xrpneutral`) — carrying both its declared twelve-combination grid
haircut and the program-level trial haircut of G7, with its forward paper run
as the locked holdout (G10), and with the C4 leg-risk scenarios required before
any real-money promotion.
