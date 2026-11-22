# `ml4tfund` — pre-registration (frozen before the first market run)

**Date:** 2026-11-22
**Source strategy:** ML4T case study *Crypto Perpetuals Funding*
(`case_studies/crypto_perps_funding/`, stefan-jansen/machine-learning-for-trading),
read from `config/setup.yaml`, `config/backtest/base.yaml`, `funding_backtest.py`,
`case_studies/utils/allocation.py`, `13_backtest.py`, `16_costs.py`.
**Engine:** `code/ml4tfund_engine.py` (to be written after this file is frozen).
**Adapter:** `ml4tfund` in `code/vrun.py`.

Nothing below was chosen after seeing a result. The numbers in this file are
panel facts measured on the data files (written down here so the reader can
check the scope), not performance.

---

## 1. What is being tested, and what is not

The published case study is an eighteen-notebook ML pipeline: forty-four
features, four model families, then a portfolio. Its **return source** is the
eight-hour funding settlement of Binance USD-M perpetuals, traded as a
cross-sectional long-short book: long the contracts the ranking likes, short
the ones it does not, equal weight, rebalanced at every funding timestamp.

This port reproduces the **mechanism and the execution**, not the ML layer. The
score that ranks the cross-section is the funding rate itself (and, as a second
declared ranking, its fourteen-day z-score — one of the forty-four published
features). That is a deliberate substitution, declared here:

* Reproducing a CUDA LightGBM/LSTM/TCN pipeline from another repository would
  not be *their* model; it would be a different model wearing its name. The
  testable question is whether the underlying return source pays.
* The case study's own baseline is "a ranking, equal weight, no sizing
  information". The funding rank is a ranking. The difference between it and a
  model rank is exactly what the ML layer claims to add, and that claim is not
  what this run measures.

Every portfolio rule below is copied from their code, not invented:

| rule | value | source |
|---|---|---|
| cadence | 8h, aligned to funding settlements (00/08/16 UTC) | `setup.yaml: decision.cadence` |
| snapshot | pre-funding timestamp, fill at the funding timestamp | `setup.yaml: decision` |
| selection | `k` highest scored long, `k` lowest short, `k_eff = min(k, n//2)` | `utils/allocation.py::_select_top_bottom` |
| weights | equal **within each side**, long side sums to +1, short side to −1 (gross 2.0) | `utils/allocation.py::_equal_weight_rows` |
| funding | position-signed, charged at the settlement against the position held, `cash -= qty * mark * rate` | `funding_backtest.py::FundingSettlementLedger` |
| cost (engine) | 4 bps commission + 1 bps slippage **per leg** | `config/backtest/base.yaml` |
| cost (narrative tier) | majors 2 bps, alts 4 bps per leg | `setup.yaml: costs.fee_schedule`, `features.majors` |
| universes | 19 perps, unbalanced, enter at listing, no backfill | `setup.yaml: universe` |
| Sharpe | daily-equivalent returns, `periods_per_year = 365` | `setup.yaml: evaluation` |

Two cost tiers are run because the case study is internally inconsistent about
this and both are defensible: the **engine** charges a flat 5 bps per leg to
everything, while the **narrative** (README, setup.yaml, Ch18) charges majors
2 bps and alts 4 bps. A strategy whose verdict flips between those two is a
strategy with no margin, and this port reports both rather than picking.

## 2. Universe and data

The nineteen contracts `setup.yaml` names: AAVE, ADA, APT, ATOM, AVAX, BNB,
BTC, COMP, DOGE, DOT, ETH, INJ, LINK, MKR, NEAR, SOL, SUI, UNI, XRP (all
`USDT`).

The store carried eleven of them with both klines and funding. The other eight
— all mid-cap alts, i.e. exactly the names whose funding goes most extreme and
therefore the short leg the mechanism lives on — were downloaded on 2026-11-22
by `code/fetch_ml4t_universe.py` (Binance USD-M public REST, append-only,
idempotent). A test on the eleven would not have measured the published
strategy; this one does.

Measured panel breadth at 8h stamps (symbols with both a settlement at the
stamp and a bar opening at it): 15–16 through 2021–2022, 18–19 from 2023,
median 19 thereafter. This matches the case study's own breadth figure (14
names in January 2022 rising to 19).

Two data facts are declared because they change the cash flows:

1. **Millisecond noise.** Part of the funding history is stamped `08:00:00.001`
   rather than `08:00:00.000`. Timestamps are floored to the second before
   alignment; without this, whole years fall off an exact 8h grid.
2. **Irregular settlement spacing.** SOL carries 75 settlements at 4h/2h
   spacing during 9–11 November 2022. A position held over `(T, T+8h]` therefore
   receives **every** settlement in that half-open window, not just the one at
   `T+8h`. Funding is summed per window; it is never assumed to be one payment.

Eligibility at stamp `T`: a settlement exists at exactly `T` **and** a 1h bar
opens at exactly `T`. MKR's funding series ends 2025-09-08, so MKR leaves the
panel there while its prices continue; the rule excludes it rather than
charging it zero.

## 3. The book

At each grid stamp `T`:

1. Score: `s_i = -f_i(T)` for the **level** ranking, where `f_i(T)` is the rate
   settled at `T`. (The settled rate is public at `T`; nothing later is read.)
   The **z** ranking uses `s_i = -(f_i(T) - mean_14d) / std_14d` over the last
   42 settlements of that symbol, with a minimum of 21.
2. `n` = eligible names at `T`; `k_eff = min(k, n//2)`; if `k_eff < 1`, the book
   is flat for the period and the stamp is counted as skipped.
3. Long the `k_eff` highest scores, short the `k_eff` lowest. Overlap is
   impossible by construction (`2*k_eff <= n`).
4. Target weights: `+1/k_eff` per long, `-1/k_eff` per short. Gross 2.0, net 0.
5. Fill at `open(T)`. Close the old book and open the new one at the same
   price; cost is charged on `sum |w_new - w_old_drifted|`, where
   `w_old_drifted` is the previous target carried through the period's return.
6. Over `(T, T+8h]` the book earns
   `sum_i w_i * (open_i(T+8h)/open_i(T) - 1) - sum_i w_i * F_i`,
   with `F_i` the sum of settlements in the window. A long pays a positive
   rate; a short receives it.

No stop, no target, no volatility scaling, no leverage cap, no cash yield.
Their engine has none of these either at this stage (`14`/`15` are where sizing
and exits start).

## 4. Windows

| label | window | why |
|---|---|---|
| `val` | 2022-01-01 .. 2023-12-31 | the case study's two 1-year validation folds (2Y train + 1Y validation, twice) |
| `holdout` | 2024-01-01 .. 2025-12-31 | their declared holdout, the window their verdict rests on |
| `ext` | 2026-01-01 .. 2026-11-02 | **beyond the published history**; our data reaches past their study, so the question "is it still dead" is answerable |

The window is applied to the grid stamps, not to the data files. A run's first
stamp opens the book from flat (turnover 2.0, cost charged).

## 5. Matrix (24 cells, all pre-declared)

`score` ∈ {`level`, `z`} × `k` ∈ {3, 5} × `cost` ∈ {`cs_engine`, `cs_tiered`} ×
window ∈ {`val`, `holdout`, `ext`}.

**Primary cell, fixed now: `level`, `k=5`, `cs_engine`, and its verdict is the
verdict.** The notebook's own prose uses five-a-side; `k=3` is the
concentration robustness check; the `z` ranking is the feature robustness
check; `cs_tiered` is the cost robustness check. None of the other twenty-three
cells may rescue the primary. Twenty-four cells on one dataset is a
multiple-testing family and every table in the report says so.

A zero-cost path is computed **inside every artifact** (not as separate cells),
so the cost drag is measured rather than derived, and the funding/price
decomposition is measured on the same path.

## 6. Gates (declared before the run)

* **G1** primary net Sharpe in `val` > 0.5.
* **G2** primary net Sharpe in `holdout` > 0.
* **G3** primary net total return in `holdout` > 0.
* **G4** primary zero-cost Sharpe > primary net Sharpe (costs must bind; if
  they do not, the cost model is wrong).
* **G5** primary funding contribution > 0 in `val` (the mechanism transfers
  money at all).
* **G6** primary trades at least 95% of eligible stamps (no silent flat book).
* **G7** accounting invariant `eq[-1] - INIT == sum(period pnl)` inside every
  artifact, residual < 1e-6 relative.

Verdict mapping:

* **PASS** = G1 ∧ G2 ∧ G3 ∧ G7.
* **MECHANISM WITHOUT EDGE** = G5 ∧ (¬G1 ∨ ¬G2): funding pays, the book does not.
* **KILL** = ¬G5, or G1/G2 fail with no funding contribution.

## 7. What would make this test wrong

Written down so a reader can attack it:

* **Breadth.** Nineteen names is the smallest cross-section in the case study's
  fleet; the ranking is noisy. Our breadth now matches theirs, but not before
  2023.
* **No ML layer.** If the models carried the edge rather than the mechanism,
  this test cannot see it. It can only show whether the mechanism pays.
* **Fill price.** We fill at `open(T)`; their engine fills at the bar's close,
  which is the same instant on an 8h grid, but the two can differ by a tick.
* **Costs.** The case study is internally inconsistent (flat 5 bps per leg in
  the engine, 2/4 bps tiered in the narrative). Both are run.
* **Funding on the mark.** Binance charges funding on the mark price at the
  settlement; we charge on `open(T+8h)`. The difference is a basis point of
  notional per settlement, not a sign.
* **Survivorship.** The universe is the contracts that were listed and still
  have history on the store. A perp that was delisted and removed from the
  store cannot appear. MKR's 2025 delisting IS visible (funding stops) and is
  handled by the eligibility rule.
