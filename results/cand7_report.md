# The seven prespecified candidates: measured

Source document: `Downloads/strategy_candidates_v2-claude.md` (Batch v2.0, 2026-10-27). The document states that no backtest had been run and that every performance figure in it is UNVERIFIED. This is the run: seven candidates, one artifact each, every artifact verified bit-for-bit against its own engine and data hashes by `vrun.py pverify`.

The document's prose is not evidence and none of it is repeated as a result. Every figure below is read out of an artifact, and each artifact records the declared rules it was run under (`declared` in the metrics), plus the repo cost, the old stress preset and a zero-cost control measured on the same signals, so a claim about a stop multiple or a fee can be checked against the artifact rather than against this text.

## How the numbers were produced

- **Execution.** Signals on closed bars, fills at the next open. Stops and targets are intrabar; stop first when both are touched; a gap through a stop fills at the bar open, adverse. A signal exit fills at the next open. Directional books size a fixed fraction of equity at the stop with a leverage cap; the basket and pair books hold fixed gross exposure.
- **Funding.** Charged at each symbol's real settlement instants on the open notional, at the close of the bar containing the settlement. At the entry instant a settlement is charged when the position pays it and not credited when the position receives it — the candidates' own convention, applied symmetrically to both directions.
- **Costs.** The candidates' own block (fee plus slippage per side) drives the headline. The repo gate cost, the old stress preset and a zero-cost control are re-run on the same signals inside the same artifact.
- **Gates.** The repo v1 set G1-G6 and the v2 layer of `code/gate2.py` (expectancy bootstrap lower bound, effective N, purged split, purged folds, monthly buckets, beta-alpha t, top-5% / best-month / best-week concentration, cost share, P95 drawdown, breakeven).
- **Audit.** `code/_cand7_audit.py` runs twenty-seven known-answer checks with hand-computed expectations. It caught four defects before publication: the basket period rows did not carry their fees or funding; the pair book marked both legs as long, which inverted the mirrored C6 direction; time exits were labelled as signal exits; and the C4 low-dispersion branch flattened the book instead of skipping the rebalance. The engine was fixed at source in each case and the checks were extended so the defects cannot return silently.

## Scoreboard

| # | Book | Unit | n | Net % | PF | Zero PF | Repo PF | Stress PF | Exp LB bps | Breakeven bps | v1 fails | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | ETHUSDT | trade | 231 | -8.45 | 0.7891 | 0.9919 | 0.8311 | 0.7063 | -9.59 | 0.00 | G1, G3, G4, G5, G6 | `c1213a34bbd85b49` |
| C2 | SOLUSDT | trade | 12 | 0.74 | 1.5286 | 1.7765 | 1.5815 | 1.4151 | -8.38 | 28.42 | G2, G4, G6 | `d6a2e71b02126d68` |
| C3 | ETHUSDT | trade | 38 | -4.87 | 0.3687 | 0.4481 | 0.3871 | 0.3372 | -22.47 | 0.00 | G1, G3, G4, G6 | `7f09a78aede368e6` |
| C4 | BASKET5 | period | 90 | 9.38 | 1.1722 | 1.2817 | 1.2128 | 1.1481 | -27.69 | 25.10 | G1, G5, G6 | `293ed0b0ccf3b3c8` |
| C5 | BASKET5 | period | 3 | -0.71 | 0.5373 | 0.6318 | 0.5620 | 0.5038 | -150.47 | 0.00 | G1, G2, G3, G4, G5, G6 | `04362ac9748dd828` |
| C6 | SOLUSDT+BTCUSDT | pair | 8 | -0.90 | 0.5872 | 0.7709 | 0.6255 | 0.5102 | -43.05 | 0.00 | G1, G2, G3, G4, G6 | `e02625eed7daa3f0` |
| C7 | SOLUSDT | trade | 33 | 2.48 | 1.4770 | 1.6217 | 1.5113 | 1.4201 | -6.37 | 37.79 | G6 | `c48057ec91da83e0` |

`Exp LB bps` is the v2 expectancy bootstrap lower bound per trade; `Breakeven` is the per-side cost at which the book's net return reaches zero, found by real re-runs. They are different quantities and they are listed separately. A breakeven of 0.00 means the book loses even at zero cost, so no per-side cost level makes it break even.

No candidate clears the v1 gates and no candidate clears the v2 gates. The best v1 showing is C7, which fails only the concentration gate; the best v2 showing is a three-way tie — C2, C4 and C7 each fail five of the eight v2 gates.

## C1 — ETHUSDT signed taker-flow persistence

231 trades from 306 first-crossing signals. Net -8.45%, PF 0.7891, win rate 35.93%. The zero-cost control returns -0.53% at PF 0.9919: **before any fee the book is a coin flip**. What turns a flat book into a loss is execution, not signal: 573.08 USDT of fees and slippage. Exits: 153 signal, 36 stop, 42 time_stop. The expectancy lower bound is -9.59 bps and the beta-alpha t is -1.1822, both negative. Fails G1, G3, G4, G5, G6.

## C2 — SOLUSDT absorption of forced flow

12 trades, net 0.74%, PF 1.5286, maximum drawdown 1.06%. The exit mix is 10 timeouts and 2 stops; no bar touched both the stop and the target (counter 0), so the tie rule never had to fire. The book breaks even at 28.42 bps per side, several times the declared cost, and the zero-cost PF is 1.7765 — cost is not what stops this candidate.

The sample is twelve trades, and the whole net gain lands in one year: the 2026 trades made 77.61 USDT while 2024 and 2025 made -3.42 and -0.22. The five best trades are 285.08% of total PnL; remove them and the book is -1.37%. The expectancy lower bound is -8.38 bps, i.e. the sign of the edge is not established. Fails G2, G4, G6.

## C3 — ETHUSDT overnight extension fade

38 trades, net -4.87%, PF 0.3687, win rate 31.58%. The zero-cost book also loses (-3.95%, PF 0.4481), so this is not a cost problem: the fade has no gross edge. Exits: 10 stop, 28 time_stop.

It does beat buy & hold, and that is the trap the repo's rules warn about: ETH fell over the window, the book returned -4.87% against a benchmark of -7.52%, and a smaller loss in a falling market is not alpha. The beta-alpha t is -2.4415, the worst of the seven.

## C4 — five-asset vol-adjusted 72h rotation

90 holding periods from 232 scheduled rebalances; 142 were skipped because the cross-sectional dispersion was under the declared gate (a skipped rebalance holds the existing book, it does not flatten). Net 9.38%, PF 1.1722, drawdown 17.97%, turnover 7.86% of equity per day.

This is the largest net gain in the batch and it still fails: buy & hold returned 14.94% over the same window, so G5 fails outright. The five best periods are 220.31% of total PnL and removing them leaves -11.28%, which is G6. PF 1.1722 is under the threshold at the declared cost; at the repo cost it is 1.2128, and the zero-cost PF is 1.2817 — the gross edge is real but thin, and fees and slippage take 406.58 USDT of it.

Funding is a near-wash at book level but not a small flow in gross: 276.65 USDT paid against 272.18 received, net -4.47 over the window (a small net payment). The per-period split is 1.0204 in sample and 1.8714 out, so the halves agree in sign.

The book kill is inert by construction: four legs at 0.08 stop on a 0.5 gross book cannot reach the 0.15 kill without gaps, and it fired 0 times in 90 traded periods. A risk control that cannot bind is not a risk control; the real exposure is the four stops plus the correlation between the long and short legs.

## C5 — dispersion-gated 24h reversal

The dispersion gate is essentially never satisfied: 3 trades in 699 days, 696 days skipped. Three observations cannot distinguish this rule from no rule. Net -0.71%, PF 0.5373, and every one of the six v1 gates fails.

The failure is in the units of the gate, not in the tape: the score is a vol-scaled 24-bar return, and the gate asks the best and worst scores to sit 3.0 units apart at the same hour. The document declared the gate prespecified, so it was not moved; the honest reading is that the candidate is untestable as written on this universe.

## C6 — SOLUSDT vs BTCUSDT funding differential

14 entry signals produced 8 trades. Every signal was the same direction: 14 entries long SOL / short BTC and 0 the other way. The reason is measured in the artifact: the differential was at or below the negative threshold in 0.0681 of settlements and at or above the positive threshold in 0.0276. In this window SOL funding sat below BTC funding, so the symmetric design was a one-sided long-SOL book.

Net -0.90%, PF 0.5872. Funding was a net credit: 12.20 USDT on the SOL leg and 0.29 on the BTC leg, 12.48 in total, and the book still lost money. This is the document's own stated failure condition — funding receipts offset by adverse spread movement — arriving on schedule. Fees and slippage equal 0.3451 of the gross profit from its winning trades, and the zero-cost PF is 0.7709, so the book does not work before costs either. Exits: 4 on the differential returning and 4 at the holding limit.

## C7 — SOLUSDT funding-extreme fade

33 trades from 54 signals, net 2.48%, PF 1.4770, drawdown 1.80%. Breakeven 37.79 bps per side; zero-cost PF 1.6217. This is the only candidate that fails just one v1 gate.

The gate it fails is concentration: the five best trades are 191.49% of total PnL, and without them the book is -2.27%. It also beats buy & hold by being short in a falling market (2.48% against -34.95%), and the beta-adjusted alpha t is 0.8494 — not significant. The expectancy lower bound is -6.37 bps, the out-of-sample side holds only 8 trades, and the funding the short collects is 10.91 USDT on a 10000 USDT account. The v2 layer fails five of eight, including the sample and the expectancy bound.

Note the two concentration measures disagree in a way worth stating: the v1 gate removes the five largest trades and the book turns negative, while the v2 gate removes the best five percent of trades (two of thirty-three) and leaves the book at 0.0023% — economically zero. Both are measured; they answer different questions, and the stricter one is the v1 gate here.

## What the seven have in common

**Four of the seven have no gross edge at all.** C1, C3, C5 and C6 return -0.53%, -3.95%, -0.55% and -0.46% with zero costs. For those books the question is not execution or fees; the signal does not predict the next move.

**Where a gross edge exists, concentration is what kills it.** C2, C4 and C7 have zero-cost PFs of 1.7765, 1.2817 and 1.6217, and their five best positions carry 285.08%, 220.31% and 191.49% of total PnL respectively. This is the same shape that killed the strategy pack and the fifty-prompt packs: a handful of positions, not a distribution.

**Beating buy & hold is not alpha.** Four of the seven beat their benchmark — C2, C3, C6 and C7 — and every one of those benchmarks fell over the window. None of the seven reaches the v2 alpha threshold of 2.0: the best is C4 at 0.8757, and C3 is at -2.4415. The repo rule is explicit that losing less than a collapsing market is not alpha.

**By the v1 sample floor four books qualify; by the v2 floor one does.** C1 has 231 trades; C3 has 38 trades, C7 33, and C4 has 90 holding periods, all above thirty; C2 has 12, C6 8 and C5 3 and do not. The v2 layer wants a hundred trades and an effective N of fifty, which only C1 reaches. The v2 expectancy lower bound is negative for all seven, so that gate fails everywhere it is computed.

**Two designs contain a control that cannot act.** C4's book kill needs a gap because the four stops cap the period loss below the kill; it fired 0 times. C5's dispersion gate fired on 3 of 699 days. Both were prespecified and neither was moved after the fact, but as written they make the candidate partly untestable, which is a design finding rather than a market finding.

## Verdict

Zero of seven candidates clear the v1 gates; zero clear the v2 gates. Three books (C2, C4, C7) show a measurable gross signal, and none of the three survives the sample, concentration and significance requirements together. The batch is rejected as a source of a deployable strategy. It is not rejected as evidence: C2 and C7 are cheap, well-defined events that can be re-specified with a larger sample and a concentration-aware exit, and C4's gross edge is worth one honest attempt at a cost model that reflects the actual per-leg fills rather than a flat per-side rate.

What is **not** measured here: order-book depth, queue position, partial fills, borrow, and any execution beyond the next open. The candidate document's own preflight marked execution as a design review, not a measurement, and that remains true.

## Reproduction

```
python code\vrun.py render c1213a34bbd85b49   # C1, ETHUSDT
python code\vrun.py render d6a2e71b02126d68   # C2, SOLUSDT
python code\vrun.py render 7f09a78aede368e6   # C3, ETHUSDT
python code\vrun.py render 293ed0b0ccf3b3c8   # C4, BASKET5
python code\vrun.py render 04362ac9748dd828   # C5, BASKET5
python code\vrun.py render e02625eed7daa3f0   # C6, SOLUSDT+BTCUSDT
python code\vrun.py render c48057ec91da83e0   # C7, SOLUSDT
python code\vrun.py pverify --ids c1213a34bbd85b49,d6a2e71b02126d68,7f09a78aede368e6,293ed0b0ccf3b3c8,04362ac9748dd828,e02625eed7daa3f0,c48057ec91da83e0
python code\_cand7_audit.py            # twenty-seven checks, all pass
```

Artifacts live in `results/runs/`. The engine is `code/cand7_engine.py` on `code/cand7_core.py` and `code/cand7_strats.py`; the gate layer is `code/gate2.py`.
