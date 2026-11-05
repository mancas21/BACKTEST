# cbpack with FUNDING CHARGED and CONCENTRATION measured

Adapter `cbpackf` (`code/cbpack_funding_engine.py`, a fork of `code/cbpack_engine.py`).
Every number below is read from a persisted artifact; the `run_id` is in the table.

## What changed and why

The `cbpack-1` engine attaches a `funding_rate` column but never debits it from PnL.
Its own docstring says: *"No funding payments, no liquidation engine, no partial fills
(state this in any report you produce)."* A Binance USDT-M perpetual charges funding
every 8h on the open notional, and the long side pays whenever the rate is positive.

`funding_attached: true` in a `cbpack-1` artifact means **the column was attached**,
not that **the cost was charged**. A reader who takes the flag at face value will
overstate what a perpetual holder actually earns.

Two further points on the fork:

* `attach_funding()` in the pack carries the last known rate FORWARD onto every
  later bar. That is what a z-score of funding needs (S07 reads it that way) but it
  is not a billing schedule: on 1h data it bills eight settlements for every real
  one. The fork therefore bills from a separate `funding_event_rate` column built
  from the raw settlement timestamps.
* The fork is proven equivalent to the original with funding zeroed:
  `code/_cbpack_funding_parity.py` (all checks pass; every shared metric column
  identical across the strategies), plus known-answer funding cases and a per-trade
  independent recomputation from the raw settlement column.

The funding drag is stored as a MEASURED field (`funding_drag_pp`), computed inside
the artifact by running the no-funding engine on the same data, so a report can cite
it without subtracting anything by hand.

## Full matrix — funding charged, pack costs (5+2 bps/side)

Source: `results/runs/_matrix_cbpackf.csv` (seven symbols x four timeframes).

| tf | symbol | run_id | net % | PF | maxDD % | cells passing |
|---|---|---|---|---|---|---|
| 1h | XRPUSDT | `9eba05720c385e77` | +178.62 | 1.80 | -21.02 | two of ten |
| 1h | SOLUSDT | `f72ee7ef452b4986` | +71.99 | 1.62 | -21.63 | one of ten |
| 1h | SUIUSDT | `47b272cd3ce61952` | +33.31 | 1.19 | -24.45 | none |
| 1h | ETHUSDT | `3523072245548bb1` | +24.29 | 1.18 | -25.01 | none |
| 1h | JUPUSDT | `fdbb4e82983833a9` | +23.58 | 1.15 | -17.36 | none |
| 1h | HYPEUSDT | `584efbc6ab8f52bc` | +18.68 | 1.18 | -16.73 | none |
| 1h | BTCUSDT | `16ed9c9f882abb9c` | +10.57 | 1.06 | -31.36 | none |
| 15m | JUPUSDT | `6f6268b058c7ae16` | +37.08 | 1.07 | -31.27 | none |
| 15m | HYPEUSDT | `bb720c344ba68c9d` | +22.86 | 1.30 | -13.50 | one of ten |
| 15m | XRPUSDT | `cd3e51be39b5713b` | +16.55 | 1.03 | -50.47 | none |
| 15m | SOLUSDT | `b6dc3abb12963368` | +15.14 | 1.03 | -42.98 | none |
| 15m | SUIUSDT | `37aaf1d3abdad552` | +3.13 | 1.01 | -53.45 | none |
| 15m | ETHUSDT | `4c237a606628e4f6` | -4.06 | 0.97 | -20.47 | none |
| 15m | BTCUSDT | `c28e5e79bf931004` | -44.45 | 0.91 | -63.88 | none |
| 5m | SOLUSDT | `29a2e5f494b11a14` | -44.72 | 0.83 | -48.89 | none |
| 5m | SUIUSDT | `0b5e67a9b389575a` | -22.06 | 0.89 | -34.76 | none |
| 5m | HYPEUSDT | `27eed74ea2276ce1` | -14.21 | 0.93 | -35.14 | none |
| 5m | ETHUSDT | `0ab1f2287ee827bb` | -56.99 | 0.81 | -62.17 | none |
| 5m | JUPUSDT | `d1eff8bafabee9fc` | -73.21 | 0.88 | -84.12 | none |
| 5m | XRPUSDT | `ee6ad0d1f317d27f` | -46.86 | 0.92 | -50.17 | none |
| 5m | BTCUSDT | `1def6ae7c9a51486` | -83.92 | 0.67 | -84.43 | none |
| 1m | BTCUSDT | `6360008f0d38101c` | -96.62 | 0.33 | -96.65 | none |
| 1m | ETHUSDT | `f269f517adcdc689` | -95.69 | 0.48 | -95.72 | none |
| 1m | HYPEUSDT | `46db447f900f284a` | -79.26 | 0.69 | -79.38 | none |
| 1m | JUPUSDT | `47ec6dfbdad8396c` | -96.11 | 0.69 | -96.19 | none |
| 1m | SOLUSDT | `aecce02a44fd0636` | -96.21 | 0.58 | -96.28 | none |
| 1m | SUIUSDT | `8c1c907276b87991` | -93.42 | 0.73 | -93.44 | none |
| 1m | XRPUSDT | `9ced74c7386c9cd2` | -94.74 | 0.61 | -94.74 | none |

## Funding drag, measured

`net_no_funding_pct` is the same pack on the same data with the same costs, run
inside the same artifact; `funding_drag_pp` is the difference.

| cell | run_id | net % (no funding) | net % (funding charged) | drag pp | funding % of equity |
|---|---|---|---|---|---|
| 1h SOLUSDT S10 | `f72ee7ef452b4986` | +75.45 | +71.99 | -3.45 | 2.51 |
| 1h XRPUSDT S10 | `9eba05720c385e77` | +184.22 | +178.62 | -5.59 | 4.75 |
| 1h XRPUSDT S02 | `9eba05720c385e77` | +184.01 | +177.90 | -6.11 | 4.26 |
| 15m HYPEUSDT S07 | `bb720c344ba68c9d` | +22.10 | +22.86 | +0.76 | -0.66 |

HYPE S07's funding is negative: the strategy is short and receives funding, so the
drag is a gain. The SOL and XRP cells are long-biased and pay.

## The concentration gate

A strategy whose best five trades exceed its whole PnL is a handful of lucky
positions, not an edge. `conc_passes` is true only when the return survives removing
the best five trades.

| cell | run_id | best five as % of PnL | net without the best five | gate |
|---|---|---|---|---|
| 1h SOLUSDT S10 | `f72ee7ef452b4986` | 108.14 | -5.86 | FAIL |
| 1h XRPUSDT S10 | `9eba05720c385e77` | 135.84 | -64.02 | FAIL |
| 1h XRPUSDT S02 | `9eba05720c385e77` | 129.38 | -52.26 | FAIL |
| 15m HYPEUSDT S07 | `bb720c344ba68c9d` | 47.85 | +11.92 | PASS |

## Verdict

**No cell in the `cbpack` family survives every gate.** The two 1h candidates that
cleared the `cbpack-1` grid both fail the concentration gate: their best five trades
carry more than their entire PnL, and removing them turns the result negative.

The concentration gate is the one that was missing. The pack's own zero-cost control
already showed a genuine gross edge at the lower timeframes that costs destroy; this
campaign adds the other half of the story — at 1h, where costs are survivable, what
remains is concentrated in a handful of trades.

`cbpack` remains KILLED below 1h and CONDITIONAL at 1h, with the 1h condition now
carrying a further condition: it does not survive removing its best five trades.

## Correction to an earlier figure

An earlier measurement of the funding drag on 1h SOL S10 was wrong by roughly a
factor of twenty. It summed the carry-forward rate over every bar of each holding
window, billing eight settlements for every real one. The measured drag is the
`funding_drag_pp` field above. The concentration, significance and cross-engine
findings do not involve funding and are unaffected.

## Reproducing

```
python code/_cbpack_funding_parity.py      # fork == original with funding zeroed
python code/_cbpack_gates.py               # all gates, writes results/cbpack_gates.json
python code/vrun.py matrix --strategy cbpackf
python code/vrun.py verify <run_id>
```
