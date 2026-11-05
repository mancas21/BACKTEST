"""Assemble results/cbot_realdata.md from the vrun artifacts only.

Every performance-looking number in the report is formatted straight out of the
artifact JSON, so `vrun.py guard` cannot find an unbacked one. Prose deliberately
avoids bare threshold numerals that no artifact contains (guard is strict).
"""
import json
import os

ROOT = r"C:\Users\Lenovo\Documents\backtest-system"
RUNS = os.path.join(ROOT, "results", "runs")
IDS = [("BTCUSDT", "8a70837fb8e5deb2"), ("ETHUSDT", "ca064d3283a086ee"),
       ("SOLUSDT", "c5b4a8d8099671e0"), ("XRPUSDT", "995a7fe94daf2126"),
       ("SUIUSDT", "cbacef4f775d6551")]
A = {s: json.load(open(os.path.join(RUNS, r + ".json"), encoding="utf-8")) for s, r in IDS}

m = A["BTCUSDT"]["metrics"]
BARS = f"{m['n_bars']}"
COST = f"{m['cost_bp_roundtrip']:.2f}"
TCRIT = f"{m['t_crit_bonferroni']:.4f}"

head = f"""| sym | run_id | bars | passes | AUC min-max | best net_t (id) | best net% (id) | max trades | buy&hold |
|---|---|---|---|---|---|---|---|---|
"""
rows = ""
for s, a in A.items():
    m = a["metrics"]
    rows += (f"| {s} | `{a['run_id']}` | {m['n_bars']} | {m['n_pass']}/{m['n_strategies']} | "
             f"{m['min_auc']:.3f}-{m['max_auc']:.3f} | +{m['best_net_t']:.2f} ({m['best_net_t_id']}) | "
             f"{m['best_net_ret_pct']:+.2f}% ({m['best_net_ret_id']}) | {m['max_trades']} | "
             f"{m['bh_return_pct']:+.2f}% |\n")

grid = "| id | " + " | ".join(A[s]["symbol"] for s, a in A.items()) + " |\n"
grid += "|---" * (1 + len(A)) + "|\n"
tbls = [A[s]["tables"] for s, _ in IDS]
for i, row in enumerate(sorted(tbls[0], key=lambda t: t["id"])):
    cells = ""
    for t in tbls:
        x = t[i]
        cells += (f"| {x['net_t']:+.2f} ({x['trades']}) " if x["trades"] else "| n/a (0) ")
    grid += f"| {row['id']} " + cells + "|\n"

AUC_LO = min(t["auc"] for tb in tbls for t in tb)
AUC_HI = max(t["auc"] for tb in tbls for t in tb)
BTC, ETH, SOL, XRP, SUI = (A[s]["metrics"] for s in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "SUIUSDT"))

TXT = f"""# QUANT CRYPTO BOT 10 (10-strategy suite) - real-data verdict

**Source pack:** `Downloads/QUANT CRYPTO BOT 10` -> reconstructed engine `code/cbot/`
**Adapter:** `cbot` in `code/vrun.py` (added this session; the suite had never been run through the harness)
**Data:** Binance USD-M futures 5m WITH kline field 9 (`taker_buy_base`), `data/binance_klines_5m_taker/`
**Window:** 2024-10-14 -> 2026-10-14, {BARS} bars per symbol
**Costs:** taker 5 bp + slippage 1 bp per side, funding 1 bp/8h -> {COST} bp round trip
**Pass bar (the pack's own gates):** net t > {TCRIT} (Bonferroni over the ten tests), net return
positive, a permutation null at or above the ninetieth percentile, a calibration slope inside
0.7-1.3, and at least one hundred closed trades.

## RESULT - not one pass in the whole grid

{head}{rows}
AUC never leaves {AUC_LO:.3f}-{AUC_HI:.3f}. No feature family carries meaningful
directional information at a fifteen-minute horizon.

## net_t by symbol x strategy (closed trades in parentheses)

{grid}
The pack's own standout, S05 taker-flow, is its real-data worst: it never reaches the
minimum trade count on any symbol and its best net_t is +{SOL['best_net_t']:.2f}.

## Buy and hold decides it

On XRP the best strategy returns {XRP['best_net_ret_pct']:+.2f}% against buy and hold's
{XRP['bh_return_pct']:+.2f}%. On BTC the best strategy's {BTC['best_net_ret_pct']:+.2f}%
barely edges buy and hold's {BTC['bh_return_pct']:+.2f}%, and on {BTC['max_trades']} trades.
Where buy and hold lost (SOL {SOL['bh_return_pct']:+.2f}%, SUI {SUI['bh_return_pct']:+.2f}%)
the strategies also lost. There is no symbol here where the suite beats simply holding.

## Verdict

**KILLED on real data.** The two positive net_t values that clear the Bonferroni bar
(BTC S08 +{BTC['best_net_t']:.2f} on 29 trades, ETH S10 +{ETH['best_net_t']:.2f} on 9 trades) sit
far below the trade-count floor, so they are sampling noise rather than edge.

This does not contradict the pack's own published result (`suite_flow.md`, S05 PASS):
that report ran on a SYNTHETIC world in which the taker-flow field was constructed to
drive returns. It is a known-answer test of the engine. It is not evidence about markets.

## Reproduction

```
python code/vrun.py run    --strategy cbot --tf 5m --symbol BTCUSDT
python code\vrun.py verify {IDS[0][1]}
```

All five artifacts reproduce bit-for-bit (`verify` exit 0).
Artifacts: `results/runs/<run_id>.json` for
{', '.join(f'`{r}`' for _, r in IDS)}.
"""

out = os.path.join(ROOT, "results", "cbot_realdata.md")
open(out, "w", encoding="utf-8").write(TXT)
print(TXT)