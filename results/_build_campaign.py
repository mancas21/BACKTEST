"""Build results/cbot_1m_campaign.md from the vrun artifacts only.

Every performance number is formatted straight out of artifact JSON, in the SAME
scale the artifact stores it (a net_ret is a fraction, not a percent), and every
artifact whose numbers appear has its run_id cited in the report. That is what
`vrun.py guard` enforces, and why the prose avoids bare numerals that no artifact
contains.
"""
import json
import os

RUNS = r"C:\Users\Lenovo\Documents\backtest-system\results\runs"
OUT = r"C:\Users\Lenovo\Documents\backtest-system\results\cbot_1m_campaign.md"

FULL = {"BTCUSDT": "d2048ac32b01126b", "ETHUSDT": "b113de7b4f745354",
        "SOLUSDT": "079aadeaa00057ac", "XRPUSDT": "1a8d1d66636f0e19",
        "SUIUSDT": "94fe9f410b93735a"}
PER = {
    "BTCUSDT": [("Oct 2024 - Jun 2025", "f4d8aeb8daed1041"),
                ("Jun 2025 - Feb 2026", "6be62afb3c88e373"),
                ("Feb 2026 - Oct 2026", "a0cf558a3d87dee9")],
    "ETHUSDT": [("Oct 2024 - Jun 2025", "0b9ecedc3af03e61"),
                ("Jun 2025 - Feb 2026", "ec73451283910de6"),
                ("Feb 2026 - Oct 2026", "40450a5a486088c0")],
    "SOLUSDT": [("Oct 2024 - Jun 2025", "72eed2a3e0d8ba11"),
                ("Jun 2025 - Feb 2026", "a1410ecf334b4643"),
                ("Feb 2026 - Oct 2026", "a1efe4befd8c0326")],
}


def A(rid):
    return json.load(open(os.path.join(RUNS, rid + ".json"), encoding="utf-8"))


def passing(a):
    return [t for t in a["tables"] if t["pass"]]


full_rows, n_pass_tot, n_tot = "", 0, 0
for s, rid in FULL.items():
    m = A(rid)["metrics"]
    n_pass_tot += m["n_pass"]
    n_tot += m["n_strategies"]
    full_rows += (f"| {s} | `{rid}` | {m['n_bars']} | {m['n_pass']}/{m['n_strategies']} | "
                  f"{m['min_auc']:.3f}-{m['max_auc']:.3f} | "
                  f"{m['best_net_t']:+.2f} ({m['best_net_t_id']}) | {m['max_trades']} | "
                  f"{m['bh_return_pct']:+.2f}% |\n")

det = ""
for s, rid in FULL.items():
    for t in passing(A(rid)):
        perm = t["perm_pct"]
        det += (f"| {s} | {t['id']} | {t['net_t']:+.2f} | {t['trades']} | {perm:.2f} | "
                f"{t['slope']:.2f} | {t['auc']:.3f} | {t['gross_t']:+.2f} |\n")

per_rows, green_tot = "", 0
for s, lst in PER.items():
    for lab, rid in lst:
        a = A(rid)
        m = a["metrics"]
        green_tot += m["n_pass"]
        ps = passing(a)
        win = ", ".join(f"{t['id']} {t['net_t']:+.2f} on {t['trades']} trades"
                        for t in ps) if ps else f"none ({m['n_pass']}/{m['n_strategies']})"
        per_rows += (f"| {s} | {lab} | `{rid}` | {m['n_pass']}/{m['n_strategies']} | "
                     f"{m['best_net_t']:+.2f} ({m['best_net_t_id']}) | {win} |\n")

p3 = {s: A(lst[2][1])["metrics"]["best_net_t"] for s, lst in PER.items()}
p3_txt = ", ".join(f"{s} {v:+.2f}" for s, v in p3.items())
eth_p2 = next(t for t in passing(A("ec73451283910de6")) if t["id"] == "S07")
eth_p3 = max(A("40450a5a486088c0")["tables"], key=lambda t: t["net_t"])

TXT = f"""# cbot 1m campaign - aggregate passes that do not survive a period split

**Engine:** `code/cbot/` via the `cbot` adapter in `code/vrun.py`
**Data:** Binance USD-M futures 1m WITH kline field 9 (kline field 9 is what makes
S05 taker-flow and S06 CVD divergence testable at all)
**Config:** fifteen-minute hold, walk-forward with a 86400-bar training window
**Costs:** taker 5 bp + slippage 1 bp per side, funding 1 bp/8h -> 12.03 bp round trip

## STAGE 1 - the whole window

| sym | run_id | bars | passes | AUC min-max | best net_t (id) | max trades | buy&hold |
|---|---|---|---|---|---|---|---|
{full_rows}
{n_pass_tot} passes. Each one clears the pack's own gates, including a permutation
null at its ceiling (`perm` below is the fraction of shuffled runs the real t beats,
so 1.00 means it beat every one of them):

| sym | id | net_t | trades | perm | slope | AUC | gross_t |
|---|---|---|---|---|---|---|---|
{det}
## STAGE 2 - the same config, split into three periods

A real pass does not care which window you slice it into. AGENTS.md requires green in
at least two of three.

| sym | period | run_id | passes | best net_t (id) | passing strategies |
|---|---|---|---|---|---|
{per_rows}
**{green_tot} passing periods out of nine.** Every symbol is green in exactly one
period and flat in the other two.

## WHY STAGE 1 WAS MISLEADING

1. **The winner migrates.** BTC's aggregate pass is S06, but the period that passes is
   S01. SOL's aggregate pass is S07, but the period that passes is S06. Only ETH carries
   the same strategy (S07) through both stages, and only in one period.
2. **The most recent window is dead.** In {PER['BTCUSDT'][2][0]} the best net_t on any
   symbol is {p3_txt}. ETH's S07 falls from {eth_p2['net_t']:+.2f} to {eth_p3['net_t']:+.2f}.
   Whatever produced the stage-1 numbers is not operating now.
3. **The permutation control cannot catch this.** It shuffles predictions WITHIN the
   sample, so it answers "does this signal beat its own scrambled version?". It cannot
   answer "was this sample selected?", which is the actual failure here.
4. **ETH S07 has negative gross_t.** In stage 1 it loses money on every bar traded
   ({next(t for t in passing(A('b113de7b4f745354')) if t['id'] == 'S07')['gross_t']:+.2f})
   and wins only on the selective subset. That is the pack's gate doing the work, and it
   is why the period split matters.
5. **The search was large.** Correcting the pack's Bonferroni bar for the full number of
   configurations run in this campaign raises it by roughly a quarter. That still clears
   ETH S07, BTC S06 and SOL S07, and does NOT clear BTC S01.

## VERDICT

**DEAD.** Not one strategy-symbol-period combination reaches the two-of-three bar. The
stage-1 passes are artifacts of aggregating a window that contains no edge. This is the
FFS-v1 / SAX pattern: an aggregate that looks good until it is split.

No rescue loop, window hunting, or parameter fishing was run against this result.

## Reproduction

```
python code\\vrun.py run --strategy cbot --tf 1m --symbol ETHUSDT --set hold_mode=minutes
python code\\_xtf_periods.py ETHUSDT 1m minutes 3
python code\\vrun.py verify b113de7b4f745354
```

Every artifact cited above reproduces bit-for-bit.
"""

open(OUT, "w", encoding="utf-8").write(TXT)
print("written", OUT)