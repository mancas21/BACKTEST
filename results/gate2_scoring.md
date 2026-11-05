# The claude2 near-misses, re-scored under the v2 gates

Artifacts `b97b59a512f29605`, `2cc68516438fa82e`, `e2daedc82289e093`, `800234f18604d653`, `d6481bbef532fd47`, `875c5767e5eee139` (adapter `gate2`,
engine `code/gate2_engine.py`): the six best candidates of the claude2 pack —
the two four-of-six prompts D05 and D13, the three-of-six prompts D04 and D23,
and the next two by profit factor, D02 and D14 — re-executed through the same
frozen rules and execution core and measured with `code/gate2.py`'s
statistical layer at the repo gate cost. Nothing is inherited from the pack50b
artifacts; every number here is a fresh measurement.

| prompt | run_id | n | exp. LB95 bps | folds PF>1 | buckets green/worst % | alpha t | top-5% net % | no-best-month % | PF at 2x | breakeven bps | P95 DD % | fails |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D02 | `b97b59a512f29605` | 832 | -10.11 | 1.09 / 0.88 | 0.40 | 0.56 / -12.6 | 0.57 | -1.40 | 13.40 / 6.73 | 0.929 | 7.62 | 70.8 | G1 G3 G4 G5 G6 G8 G9 |
| D04 | `2cc68516438fa82e` | 1512 | -3.03 | 1.14 / 1.07 | 0.60 | 0.65 / -22.8 | 1.55 | -3.88 | 94.84 / 118.39 | 0.992 | 10.74 | 77.8 | G1 G3 G4 G5 G6 G8 G9 |
| D05 | `e2daedc82289e093` | 328 | -19.49 | 1.10 / 1.17 | 0.60 | 0.56 / -29.7 | 0.99 | -0.58 | 27.09 / 50.05 | 1.056 | 15.82 | 73.8 | G1 G3 G4 G5 G6 G9 |
| D13 | `800234f18604d653` | 113 | -29.62 | 1.11 / 1.33 | 0.60 | 0.60 / -9.8 | 0.74 | -0.08 | 9.39 / 8.31 | 1.054 | 14.26 | 40.8 | G1 G3 G5 G6 G9 |
| D14 | `d6481bbef532fd47` | 384 | -43.98 | 1.22 / 0.80 | 0.40 | 0.48 / -35.3 | 0.61 | -2.43 | 12.65 / 29.82 | 1.016 | 12.70 | 90.4 | G1 G3 G4 G5 G6 G9 |
| D23 | `875c5767e5eee139` | 87 | -29.69 | 1.37 / 0.67 | 0.40 | 0.71 / -6.4 | 0.54 | -0.16 | -2.51 / 1.97 | 0.988 | 10.35 | 25.6 | G1 G2 G3 G5 G6 G8 |

`exp. LB95` is the block-bootstrap ninety-five percent lower bound of the
per-trade expectancy in bps. `folds PF>1` is the fraction of scorable folds
(six folds, boundary-crossing trades purged) with profit factor above one.
`buckets` is the monthly green fraction and the worst month as a percent of
starting capital. `top-5% net` and `no-best-month` are the nets after the two
concentration removals. `breakeven` is the per-side cost in bps at which the
book's profit factor reaches one, measured by bisection with real re-runs.
`P95 DD` is the bootstrapped ninety-fifth percentile of max drawdown on the
mark-to-market curve.

## Verdict

**None of the six passes the v2 set.** The gate that kills all of them is G1v2:
every expectancy lower bound is negative — the strongest book (D13) has a
per-trade expectancy whose ninety-five percent lower bound is
-29.62 bps — which is the quantitative
statement that the v1 near-misses were consistent with noise. The purged folds
agree (D13 is the best at 0.60, still short of
the seventy-percent bar with its sample), and the concentration pair removes
whatever margin the headlines had: after the top five percent of trades and
the best month, D13 nets 9.39 percent
of starting capital.

The one gate with survivors is **G8, cost robustness**: D05, D13, D14
stay profitable at twice the gate cost with a measured breakeven at or above
the doubled round trip. That is the honest residue of this pack — books whose
*cost* robustness is real but whose *expectancy* is not distinguishable from
zero, which is the same verdict the zero-cost control reached from the other
side. No candidate passes five or
more of the eight measured gates. All six artifacts carry
`pre_registered: false`, so the G7 multiple-testing haircut applies on top.

## Reproduce

    python code/_gate2_audit.py
    python code/vrun.py run --strategy gate2 --tf 1h --symbol SUIUSDT --set strat=30
    python code/vrun.py pverify --ids <ids from results/_gate2_ids.json> --workers 1
    python code/vrun.py guard --report results/gate2_scoring.md
