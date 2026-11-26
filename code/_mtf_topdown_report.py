"""Build results/mtf_topdown_report_2026-11-26.md from the stored artifact.
Every number comes from the artifact and carries its run_id.

Run: python code/_mtf_topdown_report.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
MATRIX = os.path.join(ROOT, "results", "mtf_topdown_matrix.json")
OUT = os.path.join(ROOT, "results", "mtf_topdown_report_2026-11-26.md")
_RID = re.compile(r"^[0-9a-f]{16}$")


def main():
    data = json.load(open(MATRIX, encoding="utf-8"))
    c = data["cells"][0]
    rid = c["run_id"]
    if not _RID.match(rid):
        raise ValueError("bad run_id")
    a = json.load(open(os.path.join(ROOT, "results", "runs", rid + ".json"),
                       encoding="utf-8"))
    m = a["metrics"]
    pf = "-" if m["profit_factor"] is None else f"{m['profit_factor']:.3f}"
    tpf = "-" if m["test_pf"] is None else f"{m['test_pf']:.3f}"
    L = []
    A = L.append
    A("# MTF top-down (attached Python source) — SOLUSDT 5m")
    A("")
    A("Date: 2026-11-26. Status: **new strategy, own verdict**. The attached "
      "Python strategy was copied byte-identically into `code/mtf_topdown_source.py` "
      "(sha `833aedf770bad9c3f7b0b7860d5cbe9d2a2a2c790319b1b175a4f62f16a2d945`) "
      "and imported by identity: the harness did NOT rewrite its signal. "
      "Grid and execution conventions are frozen in "
      "`results/mtf_topdown_pre_registration.md`.")
    A("")
    A("## Proof before the number")
    A("")
    A("`code/_mtf_topdown_audit.py` 9/9 PASS before any market read: source "
      "hash matches the attachment, the source's OWN `test_causality()` passes "
      "on real SOL 5m, and the harness executor reproduces the source's "
      "engine trade-for-trade on the full trade set, identically, on the "
      "same signals and its own "
      "4+1 bps costs. Funding sign and the accounting identity are asserted "
      "inside the artifact.")
    A("")
    A("## Result")
    A("")
    A(f"**KILLED.** Base cost regime is the repo gate (5.0 fee + 0.5 slip bps "
      f"per side, 11 bps RT) with real funding at settlements. Net "
      f"{m['net_pct']:.2f}%, PF {pf}, {m['n_trades']} trades, win rate "
      f"{m['win_pct']:.2f}%, max DD {m['max_dd_pct']:.2f}%, funding paid "
      f"{m['funding_paid']:.2f} USDT, run_id `{rid}`.")
    A("")
    A("| Regime (same signals) | Net % | PF | Trades | run_id |")
    A("|---|---:|---:|---:|---|")
    A(f"| BASE repo 11 bps + funding | {m['net_pct']:.2f} | {pf} | "
      f"{m['n_trades']} | `{rid}` |")
    A(f"| author 4+1 bps, no funding | {m['net_author_pct']:.2f} | - | "
      f"{m['n_trades']} | `{rid}` |")
    A(f"| zero cost, no funding | {m['net_zero_pct']:.2f} | - | "
      f"{m['n_trades']} | `{rid}` |")
    A("")
    A(f"Buy & hold over the same window is {m['bh_return_pct']:.2f}% and the "
      f"out-of-sample half is {m['test_net_pct']:.2f}% at PF {tpf} on "
      f"{m['test_n']} trades (`{rid}`). The bootstrap lower bound is "
      f"{m['boot_exp_lb']:.3f} and the best five trades are "
      f"{m['conc_top5_share_pct']:.2f}% of positive PnL (`{rid}`), so "
      f"concentration is not the problem: the book simply loses.")
    A("")
    A("## Reading")
    A("")
    A("Removing money improves the result but does not make it positive "
      "(the zero-cost control is still negative), so this is not a cost-only "
      "kill. The signal's own gross edge is insufficient at the declared "
      "1%-risk sizing, and it loses badly to simply holding the symbol over "
      "a window where buy & hold multiplied many times.")
    A("")
    A("The user chose SOLUSDT only. The source's default parameters were "
      "frozen; no grid, no tuning and no parameter rescue were run.")
    A("")
    A("## Provenance")
    A("")
    A("- Attachment: `C:\\Users\\Lenovo\\Downloads\\mtf_topdown-strategy-claude.py` "
      "(byte-identical copy in `code/mtf_topdown_source.py`).")
    A("- Adapter: `code/mtf_topdown_engine.py` (hashed into the run_id together "
      "with the source).")
    A("- Audit: `code/_mtf_topdown_audit.py` 9/9 before the market run.")
    A("- Matrix: `results/mtf_topdown_matrix.json`; verification log: "
      "`results/_mtf_topdown_verify.txt`.")
    A("")
    text = "\n".join(L) + "\n"
    out = os.path.realpath(OUT)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"[built {len(text)} chars] -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
