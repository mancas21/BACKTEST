# STRATEGY_GENERATOR_PROMPT v2.0 — audit against the measured record (2026-11-20)

Auditor note, not a results report: every number below cites a manifest,
an artifact, or a measurement already logged in AGENTS.md/STATUS.md.

- v2 of record: `STRATEGY_GENERATOR_PROMPT_v2.md`
  (sha256 `8a1d0536d5564f3f1b4aa44a84820259823c606d7b3b3d6aa862654e1181e5f2`,
  copied byte-identical from `Downloads/STRATEGY_GENERATOR_SUPER_PROMPT_v2-claude.md`).
- v1 of record: `STRATEGY_GENERATOR_PROMPT.md`
  (sha256 `e31c7d4cc44885883db91df70c358a89a6ccbc013f3da2e04800ad419769505a`), untouched.
- External audit that motivated v2: the operator's per-gate review of the four
  killed 50-prompt packs (184 deduped books, 0 all-gate passes, 162/184 net
  non-positive, concentration fails 21 of the 22 net-positive books) plus the
  planted-edge power audit of 2026-10-30 (a +51 bps net planted edge passes
  34.5% of the time; false-pass 0/400).

## What v2 fixes (confirmed against the record)

1. The v1 §3/§4 contradiction (dead list vs near-miss anchoring) is resolved:
   the near misses are reclassified NULL-CONSISTENT with the measured
   t-approx-1.9 < 2.2 best-of-50 null argument, and bar-pattern event books
   are capped at ONE candidate per output (Tier 3).
2. The unverifiable self-report fields (Trades/2y estimate, Expected net
   edge) are gone, replaced by design arithmetic (required per-trade IR for
   t = 3.5; the table's values check out exactly: 3.5/sqrt(n)).
3. SPCX deleted with the measured reason (crypto perp, 0.31 correlation with
   SPY, 3 months of 1m — cannot satisfy any gate).
4. The concentration-vs-skew arithmetic (3d) and the feedback/mutation
   protocol (section 10) are both aligned with what actually binds in the
   corpus (concentration killed 21 of 22 profitable books).
5. Widened event-entry slippage and trade-through maker fills are now
   declared contract items, both matching the repo's measured cost and
   fill-fidelity findings.

## Findings (each with its repo receipt)

**F1 — Section 4 CREDIBLE-1 must be demoted.** "Slow, broad, cross-sectional
momentum... survived at all in the sibling backtest system (11 perps, ~7
years)" is the MP-18 claim. The repo record: that claim has NO artifact (the
external system's outputs were never reproducible here), and the one measured
cousin of that exact family — the equal-weight short-horizon momentum
rotation — was KILLED on concentration (`00d2a8549e6c898d`). As written, v2
steers generation back into a measured-dead family while calling it credible.
Required edit: demote to "shape hypothesis whose measured cousin died on
concentration; any T1-A book must carry an explicit anti-concentration sizing
rule or it is dead on arrival."

**F2 — Section 3 omits two gates that bind.** The battery that will judge the
output is G1-G11 (`code/gate2.py` / `GATES_AND_RULES.md`): the listed gates
plus (i) the null-calibration gate — a book must beat the calibrated random
entry null at its own sample size (measured false-pass 0-0.25%), and (ii) the
win-rate breakeven gate G11 — a win rate >= 75% must sit >= 5 points above
its breakeven win rate. Both were added after the pack batteries; v2's list
should name them so generated specs anticipate them.

**F3 — Engine capability check (BEFORE USE item 3), measured answers:**
multi-asset baskets: YES (`xsf`/`xsb`/`xsc`/`xsml` adapters, resize-to-target
with average-cost basis, funding on both legs). Resting-limit simulation: YES
(`xrp_neutral_engine*`, plus the aggTrades certifier `bookreplay` — but
aggTrades exist for XRPUSDT ONLY (17 days), so T2-C certification beyond one
symbol is not currently possible). Walk-forward ML refit: NOT an engine
capability — `xsml` was deliberately frozen-hyperparameter, and purged folds
exist only as an evaluation device in `gate2.py`. T2-D as specced (refit
cadence, CPCV) is engine-blocked until a refit harness exists: either mark
T2-D blocked or scope it to frozen-spec models judged by the purged-fold
evaluation only. Portfolio-level gate: NOT implemented (no cross-book
portfolio artifact exists anywhere in the store).

**F4 — Section 1 inventory, the measured truth (fill the operator block with
this):**
- 1h taker: 33 symbols, but the window is NOT uniform. Majors (BTC, ETH,
  SOL, XRP) start 2024-10-15; SUI 2024-10, JUP 2024-10 (shorter); the
  extended universe (ADA, AVAX, BNB, DOGE, ENA, 1000PEPE, and ~20 more)
  starts 2025-09-01 or later — at most ~14 months, several only months
  (AKE 2025-09, BEAT 2025-11, CYS 2025-12). Point-in-time universe rules
  (v2 already requires them) are therefore load-bearing, not hygiene.
- 15m taker: 32 symbols, same date structure.
- 5m and 1m taker: SEVEN symbols only (BTC, ETH, SOL, SUI, XRP from
  2024-10; HYPE, JUP later). The 1m panel in `data/edge_panel/` covers 31
  symbols but only 2025-09-01..2026-09-30.
- Funding: 37 files, LONGER than the klines (BTC from 2019-09, ETH
  2019-11, SOL 2020-09, XRP 2020-01, ARB 2023-03, SUI 2023-05, JUP
  2024-10, HYPE 2025-05, all through 2026-11-14). Funding is never the
  binding history constraint; the klines are.
- aggTrades: XRPUSDT only, 17 days.
- Equities: Alpaca 1d SPY/QQQ from 2016 exist under `data/alpaca_1d/`
  (hashed, manifest-checked). v2's "no equities" rule contradicts the
  repo's current capability; the operator must decide in or out (the
  NEW-100 F7 block declared them in).

**F5 — The named stress date is wrong per symbol.** "2025-10-10/11" is a
real cascade for the alts (SUI -25.8%, SOL -18.0%, ETH -14.6% over 24h
inside the window) but NOT the worst on disk: the per-symbol worst 24h
windows are ETH -20.8% (2025-02-02/03), SOL -20.8% (2025-03-03/04), SUI
-28.5% (2025-02-02/03), BTC -14.0% (2026-02-04/05; worst 48h -17.1%).
Required edit: define the stress window as "each book's own worst 48h in its
data plus the 2025-10-10/11 window", not one fixed date.

**F6 — Power numbers, measured anchor.** v2's analytic power table is
consistent with the one measurement the repo has: a planted +51 bps net edge
passes 34.5% (2026-10-30 audit kit). Cite that number in the operator block
so the analytic table is anchored, not asserted.

## Verdict

v2 is a real improvement and is FILED as the generator of record with the
original v1 preserved. It should not be pasted until the operator block is
filled with the inventory above and the three required edits (F1 demotion,
F2 gate list, F5 stress-window definition) are applied — all three are
one-paragraph edits; none changes the architecture. T2-D and the
portfolio-level gate remain engine-blocked until built.
