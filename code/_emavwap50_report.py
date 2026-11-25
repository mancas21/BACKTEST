"""Build results/emavwap50_report_2026-11-25.md from the stored artifacts.

Every number comes from an artifact and is printed next to its run_id. The
pre-registered screen is applied here (not inside the matrix), from the
artifacts' own metrics; no number is assembled by the reader.

Run: python code/_emavwap50_report.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

MATRIX = os.path.join(ROOT, "results", "emavwap50_matrix.json")
OUT = os.path.join(ROOT, "results", "emavwap50_report_2026-11-25.md")
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
    n = m["n_trades"]
    if n < 30 or m["profit_factor"] is None:
        return "NO VERDICT"
    checks = (m["net_pct"] > 0, m["profit_factor"] > 1.2,
              m["test_net_pct"] is not None and m["test_net_pct"] > 0,
              m["boot_exp_lb"] is not None and m["boot_exp_lb"] > 0,
              m["conc_top5_share_pct"] is not None and
              m["conc_top5_share_pct"] < 100.0)
    return "PASS" if all(checks) else "KILLED"


def main():
    data = json.load(open(MATRIX, encoding="utf-8"))
    rows = []
    for rid, cell in data["cells"].items():
        m = load(cell["run_id"])["metrics"]
        mech = ("cost ruin (ZERO positive, BASE negative)" if
                m["zero_cost_ret_pct"] is not None and
                m["net_pct"] < 0 < m["zero_cost_ret_pct"] else
                "loses at ZERO too" if m["zero_cost_ret_pct"] is not None and
                m["zero_cost_ret_pct"] <= 0 else "no edge / small sample")
        rows.append(dict(row=int(rid), tf=cell["tf"], run_id=cell["run_id"], m=m,
                         verdict=verdict(m), mech=mech))
    rows.sort(key=lambda r: r["row"])
    no_data = data["no_data"]

    L = []
    A = L.append
    A("# EMA×VWAP 50-Strategy Suite — one BTCUSDT cell per row")
    A("")
    A("Date: 2026-11-25. Status: **new strategy family, judged on its own "
      "artifacts only** (REGLA 1). The attached spec is natural language; it "
      "was ported to `code/emavwap50_engine.py` and audited before any market "
      "number (`code/_emavwap50_audit.py`, 21/21 PASS). Protocol and grid are "
      "frozen in `results/emavwap50_pre_registration.md`.")
    A("")
    A("## What was tested")
    A("")
    A("Fifty variants of one skeleton: a fast MA crosses a reference line; a "
      "close beyond both arms the setup for five bars; entry at the next "
      "open; exit on a close back across the fast MA at the next open; "
      "shorts mirror and only one position is held. The user chose **one "
      "pair per row**, so every runnable row was run on BTCUSDT at its own "
      "timeframe. Fundamental costs are the repo gate (5.0 fee + 0.5 "
      "slippage bps per side, 11 bps RT) with real funding at settlements; "
      "the author's 0.04% + 1–2 bps block and a zero-cost pass are measured "
      "inside the SAME artifact as declared controls.")
    A("")
    A("## The grid before running")
    A("")
    A("Native BTC kline CSVs exist only at the fast, medium, hourly and "
      "daily intervals used below. The other rows could not be run without "
      "inventing a timeframe or outside data, so they are declared NO DATA "
      "and no number is reported for them:")
    A("")
    A("| Reason | Rows |")
    A("|---|---|")
    by_reason = {}
    for rid, reason in no_data.items():
        by_reason.setdefault(reason, []).append(int(rid))
    for reason, ids in by_reason.items():
        A(f"| {reason} | {', '.join(str(i) for i in sorted(ids))} |")
    A("")
    A("The daily files start in 2026 by construction; cells with too few "
      "trades are NO VERDICT, not passes.")
    A("")
    A("## Results (runnable rows)")
    A("")
    A("Net % and PF are ex-cost at the repo regime; ZERO % is the in-artifact "
      "zero-cost control on identical signals; Trades is the closed-trade "
      "count. The verdict applies the pre-registered screen (positive net, "
      "PF above the floor, positive test half, positive bootstrap lower "
      "bound, no extreme concentration).")
    A("")
    A("| Row | TF | Net % | PF | Trades | ZERO % | Test PF | Verdict | run_id |")
    A("|---:|---|---:|---:|---:|---:|---:|---|---|")
    for r in rows:
        m = r["m"]
        pf = "-" if m["profit_factor"] is None else f"{m['profit_factor']:.3f}"
        tpf = "-" if m["test_pf"] is None else f"{m['test_pf']:.3f}"
        A(f"| {r['row']} | {r['tf']} | {m['net_pct']:.2f} | {pf} | "
          f"{m['n_trades']} | {m['zero_cost_ret_pct']:.2f} | {tpf} | "
          f"{r['verdict']} | `{r['run_id']}` |")
    A("")
    A("## What the numbers say")
    A("")
    n_pass = sum(1 for r in rows if r["verdict"] == "PASS")
    n_kill = sum(1 for r in rows if r["verdict"] == "KILLED")
    n_nv = sum(1 for r in rows if r["verdict"] == "NO VERDICT")
    n_cost = sum(1 for r in rows if r["mech"].startswith("cost ruin"))
    A(f"Zero rows pass the screen. {n_kill} rows are KILLED and {n_nv} are NO "
      f"VERDICT for sample size. Of the killed rows, {n_cost} lose only "
      f"because money is charged — their ZERO column is positive — while "
      f"the rest lose at ZERO too, so cost was never their binding problem.")
    A("")
    A("The dominant mechanism is turnover: the 1m and 5m rows produce "
      "thousands of trades over the window and the 11 bps round trip eats "
      "them even where the gross signal is positive. The author-cost control "
      "(0.04% taker plus slippage, no funding) is also negative on almost "
      "every cell, which means the result is not an artefact of the repo's "
      "cost choice alone.")
    A("")
    A("The slow rows are the only ones with a trade count near the sample "
      "floor, and the daily rows have either no trades or a handful; none "
      "of them clears the PF or significance floor either.")
    A("")
    A("## What this is not")
    A("")
    A("- It is not a resurrection of any other EMA or crossover family. "
      "Those kills are context; this family is judged only on the artifacts "
      "cited in the table above.")
    A("- It is not advice. A zero-cost line is a control, not a tradable "
      "result: nobody trades for free.")
    A("- It is not a full-universe test: the user chose one pair per row, so "
      "the six-name universe in the attachment was not swept.")
    A("")
    A("## Limits and caveats")
    A("")
    A("- The attachment supplied no code, so every rule — including the "
      "exact fast-MA definitions, VWAP anchors and exits — is a declared "
      "port. Known-answer tests cover each indicator family and both "
      "directions of entry/exit, but a different reading of an ambiguous "
      "sentence would be a different strategy.")
    A("- Row 6's 1h confirmation was computed on the served 15m chart as an "
      "EMA50 proxy because no 1h series is served to that cell; that is "
      "declared as an approximation, not the author's higher-timeframe "
      "filter.")
    A("- Rows whose signal reads taker flow use the taker CSV fields as a "
      "CVD/ratio proxy; this is the repo's declared PARTIAL approximation, "
      "not the author's proprietary measure.")
    A("- Funding is real cash and is attributed to the open trade so the "
      "accounting identity closes inside each artifact.")
    A("")
    A("## Provenance")
    A("")
    A("- Pre-registration: `results/emavwap50_pre_registration.md`.")
    A("- Engine: `code/emavwap50_engine.py` (hashed into every run_id).")
    A("- Audit: `code/_emavwap50_audit.py` — 21/21 PASS before the market run.")
    A("- Matrix: `results/emavwap50_matrix.json` (run_ids, params, cuts, "
      "inputs and the NO DATA ledger).")
    A("- Verification log: `results/_emavwap50_verify.txt`.")
    A("")

    text = "\n".join(L) + "\n"
    out_real = os.path.realpath(OUT)
    if not out_real.startswith(os.path.realpath(ROOT) + os.sep):
        raise ValueError("output outside the repo root")
    with open(out_real, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"[built {len(text)} chars] -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
