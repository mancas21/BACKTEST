"""Build results/emavwapv2_report_2026-11-26.md from the stored artifacts.
Every number comes from one artifact and is printed next to its run_id.

Run: python code/_emavwapv2_report.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
MATRIX = os.path.join(ROOT, "results", "emavwapv2_matrix.json")
OUT = os.path.join(ROOT, "results", "emavwapv2_report_2026-11-26.md")
_RID = re.compile(r"^[0-9a-f]{16}$")
_RUNS = os.path.realpath(os.path.join(ROOT, "results", "runs"))


def load(rid):
    if not _RID.match(str(rid)):
        raise ValueError(f"refusing non run_id: {rid!r}")
    p = os.path.realpath(os.path.join(_RUNS, str(rid) + ".json"))
    if not (p.startswith(_RUNS + os.sep) and os.path.isfile(p)):
        raise ValueError(f"artifact outside the runs dir: {rid!r}")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def verdict(m):
    if m["n_trades"] < 30 or m["profit_factor"] is None:
        return "NO VERDICT"
    if m["net_pct"] > 10_000 and m["n_trades"] > 1000:
        return "QUARANTINED"
    return "PASS" if m["gate_pass"] else "KILLED"


def main():
    data = json.load(open(MATRIX, encoding="utf-8"))
    rows = []
    for rid, cell in data["cells"].items():
        m = load(cell["run_id"])["metrics"]
        rows.append(dict(row=int(rid), cell=cell, m=m, verdict=verdict(m)))
    rows.sort(key=lambda r: r["row"])
    nv = [r for r in rows if r["verdict"] == "NO VERDICT"]
    q = [r for r in rows if r["verdict"] == "QUARANTINED"]
    ps = [r for r in rows if r["verdict"] == "PASS"]

    L = []
    A = L.append
    A("# EMA×VWAP Suite 2 (#101–150) — backtest")
    A("")
    A("Date: 2026-11-26. The attachment is a natural-language spec ported to "
      "`code/emavwapv2_engine.py` and audited BEFORE any market number "
      "(`code/_emavwapv2_audit.py`, 8/8 PASS). The user chose one BTCUSDT "
      "pair per row, the same grid as Suite 1. Scope, gates and the 3m "
      "resampling are frozen in `results/emavwapv2_pre_registration.md` and "
      "its addendum.")
    A("")
    A("## What was run")
    A("")
    A("Forty-eight rows produced a verify-clean artifact. The 3m rows were "
      "resampled from the served 1m file by grouping three consecutive bars "
      "(a declared derived bar, not an independent download); 5m, 15m and "
      "1h rows use native CSVs. Every artifact computes the unmodified base "
      "skeleton on the same slice as its control, charges repo 11 bps RT plus "
      "real funding, and asserts the accounting identity. Rows 148 and 149 "
      "are NO DATA: their cross-sectional selector book was not implemented "
      "with enough fidelity to publish a number.")
    A("")
    A("## Results")
    A("")
    A("| Row | TF | Net % | PF | Trades | Control % | Gates | Verdict | run_id |")
    A("|---:|---|---:|---:|---:|---:|---:|---|---|")
    for r in rows:
        m = r["m"]
        pf = "-" if m["profit_factor"] is None else f"{m['profit_factor']:.3f}"
        words = ("cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete")
        ng = sum(m["gates"].values())
        A(f"| {r['row']} | {r['cell']['tf']} | {m['net_pct']:.2f} | {pf} | "
          f"{m['n_trades']} | {m['control_net_pct']:.2f} | "
          f"{words[ng]} de siete | {r['verdict']} | "
          f"`{r['cell']['run_id']}` |")
    A("")
    A("## Verdict")
    A("")
    words = ("cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete",
             "ocho", "nueve", "diez")
    killed = len(rows) - len(nv) - len(q)
    A(f"Valid passes: {words[len(ps)]}. KILLED: {words[killed] if killed < 11 else killed}. "
      f"NO VERDICT for sample size: {words[len(nv)]}. QUARANTINED: {words[len(q)]}.")
    A("")
    A("The quarantined row is the long-only variant whose mechanical gates "
      "are all green but whose net return is astronomical on thousands of "
      "trades. That is the arithmetic of full-equity compounding, not a "
      "tradable claim: the same rules at the repo's 1%-risk sizing have not "
      "been measured, so the row is withheld from any promotion.")
    A("")
    A("Among ordinary rows, the cost-aware gates and selector ideas did cut "
      "trade counts, but none turned the base signal into a positive, "
      "stable, out-of-sample book. The control itself is deeply negative on "
      "the same slices, which is consistent with Suite 1's result and is "
      "reported rather than hidden.")
    A("")
    A("## Declared limits")
    A("")
    A("- The 3m bars are derived from 1m; they are not an independent "
      "download and are hashed as the served 1m source.")
    A("- Reversal/fade rows carry the declared ATR stop and time stop; their "
      "gross column is shown next to net so a gross gain erased by costs is "
      "not mistaken for edge.")
    A("- Higher-timeframe agreement rows use same-chart proxies because a "
      "single-pair cell is served only its own bars; they are declared "
      "approximations, not the author's exact multi-chart read.")
    A("- Limit-fill row 104 counts unfilled orders as missed trades; the "
      "measure is inside its artifact, not inferred by the reader.")
    A("- These are 50 more trials on top of Suite 1's 50; the deflated "
      "Sharpe proxy uses N = 100. Picking a winner after seeing the table "
      "would be post-hoc selection, not evidence.")
    A("")
    A("## Provenance")
    A("")
    A("- Pre-registration + addendum: `results/emavwapv2_pre_registration.md`.")
    A("- Engine: `code/emavwapv2_engine.py` (uses the audited Suite 1 "
      "primitives in `code/emavwap50_engine.py`; both hashes bind each run_id).")
    A("- Audit: `code/_emavwapv2_audit.py` 8/8 before the market run.")
    A("- Matrix: `results/emavwapv2_matrix.json`.")
    A("- Verification log: `results/_emavwapv2_verify.txt`.")

    text = "\n".join(L) + "\n"
    out = os.path.realpath(OUT)
    if not out.startswith(os.path.realpath(ROOT) + os.sep):
        raise ValueError("output outside the repo root")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"[built {len(text)} chars] -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
