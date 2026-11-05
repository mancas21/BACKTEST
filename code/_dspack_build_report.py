#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_dspack_build_report.py — build results/dspack_report.md entirely from the
canonical dspack artifacts. Every metric comes from the cited artifact's own
tables[0] (the engine's scored row) or metrics; nothing hand-typed.

Canonical cell selection is DERIVED, not hand-copied: run_id is a pure
function of (params, inputs, engine bytes), so each
(strat, pair, window, costs) cell has exactly one resulting artifact. The
script scans results/runs/*.json for strategy == "dspack", builds the
cell -> run_id map, refuses if any expected cell is missing, and refuses if
the engine's stored gates_pass_all disagrees with this script's independent
gate evaluation from the same row.
"""
from __future__ import annotations

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(os.path.dirname(HERE), "results", "runs")
OUT = os.path.join(os.path.dirname(HERE), "results", "dspack_report.md")

SYMS = ["ADAUSDT", "AVAXUSDT", "BNBUSDT", "BTCUSDT", "DOGEUSDT", "ETHUSDT",
        "HYPEUSDT", "LINKUSDT", "NEARUSDT", "SOLUSDT", "SPXUSDT", "SUIUSDT",
        "XRPUSDT"]
STRATS = ["ds1", "ds2", "ds3", "ds5"]
CELLS = [("full", "author"), ("full", "repo6x5"),
         ("last6mo", "author"), ("last6mo", "repo6x5")]

WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven",
         "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
         "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
         "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def nword(n: int) -> str:
    if n < 20:
        return WORDS[n]
    if n % 10 == 0:
        return WORDS[n // 10 + 18]
    return "%s-%s" % (WORDS[n // 10 + 18], WORDS[n % 10])


def load(rid: str) -> dict:
    with open(os.path.join(RUNS, rid + ".json"), encoding="utf-8") as f:
        return json.load(f)


def gates_from_row(row: dict, window: str):
    """Independent re-evaluation of the pre-declared gates from the row."""
    pf = row.get("pf_strict")
    g1 = (pf is not None) and pf > 1.2
    g2 = (row.get("n_trades") or 0) >= 30
    h1, h2 = row.get("pf_h1"), row.get("pf_h2")
    g3 = (h1 is not None and h2 is not None and h1 > 1 and h2 > 1)
    yrs = [y.get("ret_pct") for y in (row.get("year_returns") or [])]
    n_green = len([v for v in yrs if v is not None and v > 0])
    g4 = (len(yrs) >= 1 and n_green * 3 >= len(yrs) * 2) \
        if window == "full" else None
    g5 = bool(row.get("beats_bh"))
    c = row.get("conc_net_without_top5_pct")
    g6 = c is not None and c > 0
    gs = [g for g in (g1, g2, g3, g4, g5, g6) if g is not None]
    return all(gs), dict(g1=g1, g2=g2, g3=g3, g4=g4, g5=g5, g6=g6,
                         n_green=n_green, n_years=len(yrs), conc=c)


def build_canon():
    canon = {}
    for p in sorted(glob.glob(os.path.join(RUNS, "*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                a = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if a.get("strategy") != "dspack":
            continue
        m = a["metrics"]
        pair = a["symbol"]
        key = (m.get("strat"), pair, m.get("window"), m.get("costs"))
        rid = a.get("run_id")
        if key in canon and canon[key] != rid:
            raise SystemExit(
                "REFUSED: two different run_ids for one cell %r: %s vs %s "
                "(engine or data changed mid-matrix; reconcile first)"
                % (key, canon[key], rid))
        canon[key] = rid
    return canon


def fmt(v, nd=4):
    if v is None:
        return "-"
    if isinstance(v, bool):
        return "Y" if v else "N"
    return format(v, "." + str(nd) + "f")


def main():
    canon = build_canon()
    missing = []
    for s in STRATS:
        for sym in SYMS:
            for w, c in CELLS:
                if (s, sym, w, c) not in canon:
                    missing.append((s, sym, w, c))
    for w, c in CELLS:
        if ("ds4", "PORTFOLIO", w, c) not in canon:
            missing.append(("ds4", "PORTFOLIO", w, c))
    if missing:
        print("REFUSED: %d canonical cells missing: %s"
              % (len(missing), missing[:8]), file=sys.stderr)
        sys.exit(2)

    # verify gate agreement; collect rows
    rows = {}
    for k, rid in sorted(canon.items()):
        a = load(rid)
        row = a["tables"][0]
        window = k[2]
        own, det = gates_from_row(row, window)
        if own != bool(row.get("gates_pass_all")):
            raise SystemExit(
                "REFUSED: gate disagreement at %r (%s): independent=%s, "
                "engine=%s, detail=%s" % (k, rid, own,
                                          row.get("gates_pass_all"), det))
        rows[k] = (rid, row, a["metrics"], det)

    lines = []
    for s in STRATS:
        for w, c in CELLS:
            lines.append("### %s, %s window, %s costs" % (s, w, c))
            lines.append("")
            lines.append("| run_id | symbol | ret%% | PF | PF h1 | PF h2 | n | "
                         "green years | B&H%% | conc w/o top5 %% | drag pp | verdict |")
            lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
            for sym in SYMS:
                k = (s, sym, w, c)
                rid, row, m, det = rows[k]
                gy = "%d/%d" % (det["n_green"], det["n_years"]) \
                    if w == "full" else "n/a"
                verdict = "PASS" if bool(row.get("gates_pass_all")) else "fail"
                lines.append("| %s | %s | %s | %s | %s | %s | %d | %s | %s | %s"
                             " | %s | %s |" % (
                                 rid, sym,
                                 fmt(row.get("ret_pct")),
                                 fmt(row.get("pf_strict"), 2),
                                 fmt(row.get("pf_h1"), 2),
                                 fmt(row.get("pf_h2"), 2),
                                 row.get("n_trades") or 0,
                                 gy,
                                 fmt(m.get("bench_ret_pct")),
                                 fmt(row.get("conc_net_without_top5_pct")),
                                 fmt(row.get("drag_pp")),
                                 verdict))
            passes = sum(1 for sym in SYMS
                         if bool(rows[(s, sym, w, c)][1].get("gates_pass_all")))
            lines.append("")
            lines.append("(reconciled in words: %s of %s symbols pass G1..G6 "
                         "in this cell-set)"
                         % (nword(passes), nword(len(SYMS))))
            lines.append("")
    # ds4 rows
    lines.append("### ds4 (cross-sectional book, symbol PORTFOLIO)")
    lines.append("")
    lines.append("| run_id | window | ret%% | PF | PF h1 | PF h2 | n | "
                 "green years | B&H%% | conc w/o top5 %% | drag pp | verdict |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for w, c in CELLS:
        k = ("ds4", "PORTFOLIO", w, c)
        rid, row, m, det = rows[k]
        gy = "%d/%d" % (det["n_green"], det["n_years"]) if w == "full" else "n/a"
        verdict = "PASS" if bool(row.get("gates_pass_all")) else "fail"
        lines.append("| %s | %s/%s | %s | %s | %s | %s | %d | %s | %s | %s"
                     " | %s | %s |" % (
                         rid, w, c,
                         fmt(row.get("ret_pct")),
                         fmt(row.get("pf_strict"), 2),
                         fmt(row.get("pf_h1"), 2),
                         fmt(row.get("pf_h2"), 2),
                         row.get("n_trades") or 0,
                         gy,
                         fmt(m.get("bench_ret_pct")),
                         fmt(row.get("conc_net_without_top5_pct")),
                         fmt(row.get("drag_pp")),
                         verdict))
    lines.append("")
    sys.stdout.write("\n".join(lines) + "\n")

    # counts for the md author (the prose is written after seeing these)
    per = {}
    for s in STRATS + ["ds4"]:
        pairs = SYMS if s != "ds4" else ["PORTFOLIO"]
        for w, c in CELLS:
            k = (s, w, c)
            tot = len(pairs)
            ok = sum(1 for sym in pairs
                     if bool(rows[(s, sym, w, c)][1].get("gates_pass_all")))
            per[k] = (ok, tot)
    with open(os.path.join(os.path.dirname(HERE), "results",
                           "dspack_gate_counts.json"), "w",
              encoding="utf-8") as f:
        json.dump({"counts": {("%s/%s/%s" % k): v for k, v in per.items()},
                   "canon": {"%s|%s|%s|%s" % k: v for k, v in canon.items()}},
                  f, indent=2, sort_keys=True)
    print("\nper-cell gate pass counts (tool output, also in "
          "results/dspack_gate_counts.json):", file=sys.stderr)
    for k in sorted(per):
        print("  %s/%s/%s: %d of %d pass" % (k[0], k[1], k[2],
                                             per[k][0], per[k][1]), file=sys.stderr)


if __name__ == "__main__":
    main()
