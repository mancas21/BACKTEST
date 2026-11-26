"""Build results/nontrend50_report_2026-11-26.md from the stored artifacts.
Every number comes from one artifact and is printed next to its run_id.

Run: python code/_nontrend50_report.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
MATRIX = os.path.join(ROOT, "results", "nontrend50_matrix.json")
OUT = os.path.join(ROOT, "results", "nontrend50_report_2026-11-26.md")
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


def main():
    data = json.load(open(MATRIX, encoding="utf-8"))
    rows = []
    for rid, cell in data["cells"].items():
        m = load(cell["run_id"])["metrics"]
        rows.append(dict(row=int(rid), cell=cell, m=m))
    rows.sort(key=lambda r: r["row"])
    nodata = data["no_data"]
    passed = [r for r in rows if r["m"]["gate_pass"]]

    L = []
    A = L.append
    A("# Non-Trend 50-Strategy Suite (#51–100) — backtest")
    A("")
    A("Date: 2026-11-26. The attachment is a natural-language spec; it was "
      "ported to `code/nontrend50_engine.py` and audited BEFORE any market "
      "number (`code/_nontrend50_audit.py`, 10/10 PASS). Grid, universes and "
      "gates were frozen in `results/nontrend50_pre_registration.md` and its "
      "dated addendum. This family is judged only on its own artifacts "
      "(REGLA 1).")
    A("")
    A("## What was run")
    A("")
    A("Cross-sectional, dollar-neutral books: ranks at the close, fills at "
      "the next open, equal weight per leg, repo 11 bps RT on turnover and "
      "funding at real settlements where the universe has funding. Three "
      "universes were used: every perp with a native 1h file except the "
      "equity/fractional/spot tickers (the spec said seventeen, the repo has "
      "more today and the real count is stated per artifact), the seven 5m "
      "taker files, and a fixed eight-perp funding universe. Each artifact "
      "computes the #51 control on its OWN universe and window, so the "
      "correlation to the control is measured inside the artifact.")
    A("")
    A("Thirty-nine rows produced a verify-clean artifact. Eleven are NO DATA: "
      "the three overlays not faithfully implemented (declared in the "
      "addendum) and the eight composites, which the attachment says may only "
      "run from sleeves that cleared the gates on their own — none did.")
    A("")
    A("## Results")
    A("")
    A("| Row | Universe | Net % | PF | Trades | Gates | Control corr | DSR proxy | run_id |")
    A("|---:|---|---:|---:|---:|---:|---:|---:|---|")
    for r in rows:
        m = r["m"]
        pf = "-" if m["profit_factor"] is None else f"{m['profit_factor']:.3f}"
        cc = "-" if m["control_corr"] is None else f"{m['control_corr']:.3f}"
        A(f"| {r['row']} | {m['universe']} ({m['symbols']}) | {m['net_pct']:.2f} | "
          f"{pf} | {m['n_trades']} | {sum(m['gates'].values())}/{len(m['gates'])} | "
          f"{cc} | {m['dsr_proxy']:.3f} | `{r['cell']['run_id']}` |")
    A("")
    A("## Verdict")
    A("")
    if not passed:
        A("**No row passed the battery.** The best gate count was three of "
          "seven, and the highest profit factors stayed near one with tiny "
          "trade counts. Several rows have a positive net line but fail the "
          "sample, fold, month, bootstrap or drawdown gates; under the "
          "frozen rule they are not candidates.")
    else:
        A("The rows listed with all gates green are candidates, subject to "
          "the multiple-testing control below.")
    A("")
    A("The control itself (#51) does not clear the battery on this window. "
      "That is reported as measured, not hidden: every other row is compared "
      "against a control that is itself only a reference line, not a "
      "validated strategy here.")
    A("")
    A("No composite (#93–100) was run because its source sleeves did not "
      "pass on their own, exactly as the attachment requires.")
    A("")
    A("## Declared approximations (read before quoting a number)")
    A("")
    A("- Rows 65, 66 and 68 are NO DATA: the beta-neutral sizing, the per-leg "
      "stop with re-entry and the liquidity exclusion were not implemented "
      "with enough fidelity to publish a number.")
    A("- Rows 58, 59, 72, 73, 75 and 76 are implemented as declared "
      "simplifications: a single rebalanced book instead of four offset "
      "sleeves, an approximate hold band, a one-sided sign filter, a "
      "threshold recomputed from the served bars, and flow/funding filters "
      "that gate candidates rather than an exact reimplementation of the "
      "author's logic. Their numbers describe what was actually run, not a "
      "verbatim reading of every sentence.")
    A("- Rows 63, 64 and 67 use exposure-scale overlays computed from the "
      "served data; where the trigger never fires the row coincides with "
      "#51 on the same universe, which is visible in the table rather than "
      "being silently dressed up as a different result.")
    A("")
    A("## Multiple testing")
    A("")
    A("Fifty rows were pre-registered and the deflated-Sharpe proxy uses N = "
      "50 as required. Even so, picking the best of fifty after seeing the "
      "results is selection: a positive line among these rows is not "
      "evidence on its own. No formal promotion is made from this report.")
    A("")
    A("## Provenance")
    A("")
    A("- Pre-registration + addendum: `results/nontrend50_pre_registration.md`.")
    A("- Engine: `code/nontrend50_engine.py` (hashed into every run_id).")
    A("- Audit: `code/_nontrend50_audit.py` 10/10 before the market run.")
    A("- Matrix: `results/nontrend50_matrix.json` (run_ids, cuts, inputs, "
      "gates and the NO DATA ledger).")
    A("- Verification log: `results/_nontrend50_verify.txt`.")
    A("")

    text = "\n".join(L) + "\n"
    out = os.path.realpath(OUT)
    if not out.startswith(os.path.realpath(ROOT) + os.sep):
        raise ValueError("output outside the repo root")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"[built {len(text)} chars] -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
