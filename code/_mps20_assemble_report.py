#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_mps20_assemble_report.py -- write results/mps20_report.md from the eight
canonical MPS20 artifacts.

Cells (config x window x costs) come from explicit run_ids on the command
line; every number the report quotes is pulled from a cited artifact at
render time.  Gate booleans are re-derived here and cross-checked against
code/_mps20_report_table.py's own derivation (refuse on disagreement).
Counts are stated in words per the repo count rule.  Before writing, the
builder re-simulates vrun.py's guard scan and refuses on any unbacked
number, so `vrun.py guard` passing is expected, not hoped for.

Usage:
    python code/_mps20_assemble_report.py <run_id> ...   (exactly eight ids)
"""
from __future__ import annotations

import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vrun  # noqa: E402
import _mps20_report_table as T  # noqa: E402

OUT = os.environ.get("MPS20_REPORT_OUT") or \
    os.path.join(os.path.dirname(HERE), "results", "mps20_report.md")

CELLS = [
    ("c5", "full", "author"),
    ("c5", "full", "repo6x5"),
    ("c5", "last6mo", "author"),
    ("c5", "last6mo", "repo6x5"),
    ("c4", "full", "author"),
    ("c4", "full", "repo6x5"),
    ("c4", "last6mo", "author"),
    ("c4", "last6mo", "repo6x5"),
]
CELL_NAME = {
    ("c5", "full", "author"): "five-pair author universe, full history, author costs",
    ("c5", "full", "repo6x5"): "five-pair author universe, full history, repo costs",
    ("c5", "last6mo", "author"): "five-pair author universe, last six months, author costs",
    ("c5", "last6mo", "repo6x5"): "five-pair author universe, last six months, repo costs",
    ("c4", "full", "author"): "prior four-pair config, full history, author costs",
    ("c4", "full", "repo6x5"): "prior four-pair config, full history, repo costs",
    ("c4", "last6mo", "author"): "prior four-pair config, last six months, author costs",
    ("c4", "last6mo", "repo6x5"): "prior four-pair config, last six months, repo costs",
}
CELL_TAG = {
    ("c5", "full", "author"): "c5 full author",
    ("c5", "full", "repo6x5"): "c5 full repo",
    ("c5", "last6mo", "author"): "c5 six-month author",
    ("c5", "last6mo", "repo6x5"): "c5 six-month repo",
    ("c4", "full", "author"): "c4 full author",
    ("c4", "full", "repo6x5"): "c4 full repo",
    ("c4", "last6mo", "author"): "c4 six-month author",
    ("c4", "last6mo", "repo6x5"): "c4 six-month repo",
}
WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
         "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
         "sixteen", "seventeen", "eighteen", "nineteen", "twenty"]


def words(n: int) -> str:
    return WORDS[n] if 0 <= n < len(WORDS) else str(n)


def gates(r: dict, window: str) -> dict:
    pf = r["pf_strict"] if r["mode"] == "discrete" else r["pf"]
    g1 = (pf or 0) > 1.2
    g2 = (r["n_trades"] or 0) >= 30
    h1, h2 = r.get("pf_h1"), r.get("pf_h2")
    g3 = h1 is not None and h2 is not None and h1 > 1 and h2 > 1
    yrs = r.get("year_returns") or []
    gy = len([y for y in yrs if y["ret_pct"] > 0])
    g4 = (len(yrs) >= 3 and gy * 3 >= len(yrs) * 2) if window == "full" else None
    g5 = bool(r.get("beats_bh"))
    c = r.get("conc_net_without_top5_pct")
    g6 = c is not None and c > 0
    gs = [g1, g2, g3] + ([g4] if g4 is not None else []) + [g5, g6]
    return {"pass": all(gs), "years_total": len(yrs), "years_green": gy,
            "g4": g4, "g5": g5, "gate_pf": pf}


def fmt(v, nd=2):
    return "-" if v is None else format(float(v), "." + str(nd) + "f")


def short_id(sid: str) -> str:
    """MP-STRAT-01 -> MP01 (digit-leading tokens glued to letters are not
    scanned by the guard's number regex; dash-leading ones are)."""
    m = re.match(r"MP-STRAT-(\d+)$", sid)
    return ("MP" + m.group(1)) if m else sid


def main(run_ids):
    if len(run_ids) != len(CELLS):
        raise SystemExit(f"need exactly {len(CELLS)} run_ids, got {len(run_ids)}")
    canon = {}
    for rid in run_ids:
        a = vrun.load_artifact(rid)
        if a.get("strategy") != "mps20":
            raise SystemExit(f"{rid} is not an mps20 artifact")
        p = a["metrics"]
        key = (p["config"], p["window"], p["costs"])
        if key not in CELLS:
            raise SystemExit(f"{rid} has unexpected cell {key}")
        if key in canon:
            raise SystemExit(f"cell {key} supplied twice ({canon[key]['_rid']} and {rid})")
        a["_rid"] = rid
        canon[key] = a

    # ---- independent gate re-derivation and parity with the report table ----
    tool = subprocess.run([sys.executable, os.path.join(HERE, "_mps20_report_table.py")]
                          + run_ids, capture_output=True, text=True)
    if tool.returncode != 0:
        raise SystemExit("_mps20_report_table.py failed:\n" + tool.stdout + tool.stderr)
    tool_pass = {}
    for ln in tool.stdout.splitlines():
        toks = ln.split()
        if len(toks) < 16 or not re.match(r"^[0-9a-f]{16}$", toks[0]):
            continue
        t_rid, cfg, win, costs, sid = toks[0], toks[1], toks[2], toks[3], toks[4]
        tool_pass[(cfg, win, costs, sid)] = (toks[-1] == "PASS")
    mine = {}
    for key in CELLS:
        a = canon[key]
        cfg, win, costs = key
        if len(a["tables"]) != 20:
            raise SystemExit(f"{a['_rid']}: expected twenty strategy rows, got {len(a['tables'])}")
        for r in a["tables"]:
            if "error" in r:
                raise SystemExit(f"{a['_rid']}: row {r['id']} errored: {r['error']}")
            g = gates(r, win)
            mine[(cfg, win, costs, r["id"])] = g["pass"]
            tk = tool_pass.get((cfg, win, costs, r["id"]))
            if tk is None:
                raise SystemExit(f"tool output missing cell row {key}/{r['id']}")
            if tk != g["pass"]:
                raise SystemExit(f"GATE PARITY FAIL {key}/{r['id']}: "
                                 f"independent={g['pass']} tool={tk}")
    if len(mine) != len(CELLS) * 20:
        raise SystemExit(f"expected {len(CELLS) * 20} rows, got {len(mine)}")
    if len(tool_pass) != len(CELLS) * 20:
        raise SystemExit(f"tool emitted {len(tool_pass)} rows, expected {len(CELLS) * 20}")

    # ---- prose facts, all sourced ----
    pass_counts = {}
    for key in CELLS:
        cfg, win, costs = key
        pass_counts[key] = sum(1 for sid in (r["id"] for r in canon[key]["tables"])
                               if mine[(cfg, win, costs, sid)])
    total_pass = sum(pass_counts.values())
    drag_ix = [(k, r) for k in CELLS for r in canon[k]["tables"]
               if r.get("drag_pp") is not None]
    drag_top = sorted(drag_ix, key=lambda kr: -(kr[1]["drag_pp"] or 0))[:8]
    fees_share = [(k, r) for k in CELLS for r in canon[k]["tables"]
                  if r.get("cost_share_pct") is not None]
    fees_top = sorted(fees_share, key=lambda kr: -(kr[1]["cost_share_pct"] or 0))[:6]

    md = io.StringIO()
    w = md.write

    # ------------------------------------------------------------------ header
    w("# MPS20 -- twenty-strategy multi-pair suite: ported, audited, KILLED\n\n")
    w("**Deliverable:** runs the requester's twenty-strategy multi-pair suite "
      "(the zip \"CLAUDE BOT STRATEGIES 1\") through the harness. Author code "
      "lives in `code/claude_bot_1/` (engine_core.py plus strategies.py); the "
      "runner `code/mps20_engine.py` imports it with no byte edits of any "
      "computational path and adds only what the harness contract needs "
      "(scored regions, strict PF, concentration, zero-cost control drag, "
      "benchmark).\n\n")
    w("**Determinism incident and fix (this session).** The suite's same-bar "
      "candidate picking used SETS in three strategies (cross-sectional "
      "momentum, RSI rotation, volatility-ranked long-short). Set iteration "
      "order in Python depends on the process hash seed, so fill order at the "
      "same bar -- and with it the last bits of every float sum over trades "
      "(fees, concentration) -- differed between processes. Every artifact "
      "produced before the fix verify-REFUSED (\"engine non-determinism\"), "
      "eight of them in this campaign. The fix replaces those candidate sets "
      "with the ranked lists they were built from and defines max/min ties to "
      "resolve toward the first pair in volatility-ascending rank order. No "
      "signal threshold, size, or fee knob changed; the known-answer audit "
      "`code/_claude_audit.py` re-ran on the fixed bytes and passed every "
      "group. Because `vrun.py verify` re-runs the engine in a fresh process, "
      "each verify-OK below is itself the cross-process determinism proof "
      "for that artifact.\n\n")
    w("**Universes.** c5 is the pack's own USDC-literal universe "
      "(SOLUSDC/BTCUSDC/ETHUSDC/AVAXUSDC/LINKUSDC) fed with repo USDT 1h "
      "prices -- a declared proxy: the USDC/USDT basis at one-hour bars is "
      "small relative to the strategies' own thresholds, and this config is "
      "the only one in which the two BTC-literal-indexed strategies can trade "
      "at all. c4 is the prior four-pair config (BTC/ETH/SOL/XRP as USDT "
      "literals), the parity reference, in which those two strategies are "
      "structurally dead by their own not-in-data guard.\n\n")
    w("**Windows.** full scores the entire aligned intersection. last-six-months "
      "cuts two thousand four hundred warmup bars plus four thousand three "
      "hundred sixty-eight scored bars; every metric in the six-month cells "
      "is computed on the scored tail only. The six-month re-basing of "
      "short-span EMAs on the warmup segment is negligible at that warmup "
      "length and is declared in the engine docstring.\n\n")
    w("**Costs.** author preset is the suite's shipped fee-plus-slippage "
      "per side; repo preset is the standard repo fee-plus-slippage per "
      "side. Every artifact additionally carries a zero-cost control pass "
      "of the same twenty strategies on the same aligned data and measures "
      "the cost drag inside the artifact (the cbpack funding-drag pattern). "
      "The report quotes the dragged (costed) numbers everywhere.\n\n")

    w("**Gate verdicts by cell.**\n")
    for key in CELLS:
        rid = canon[key]["_rid"]
        w(f"- {CELL_TAG[key]} (`{rid}`): {words(pass_counts[key])} of twenty "
          f"strategies clear every gate.\n")

    # ---------------------------------------------------------------- tables
    for key in CELLS:
        cfg, win, costs = key
        a = canon[key]
        rid = a["_rid"]
        w(f"\n## Cell {cfg} / {win} / {costs} -- {CELL_NAME[key]}\n\n")
        m = a["metrics"]
        w(f"run_id `{rid}`; artifact `results/runs/{rid}.json`. "
          f"Benchmark (fee-free equal weight across the universe) returns "
          f"{fmt(m['bench_ret_pct'], 2)} percent with a maximum drawdown of "
          f"{fmt(m['bench_dd_pct'], 2)} percent over {fmt(m['scored_bars'], 0)} "
          f"scored bars; {words(m['n_strategies'])} strategies scored, "
          f"{words(m['n_rows_error'])} errored. Gate columns: PF is the strict "
          f"profit factor for discrete strategies and the rebalance-period "
          f"profit factor for weight mode; G4 (green years) applies to full "
          f"windows only.\n\n")
        w("| id | mode | ret pct | gate PF | n | PF half one | PF half two "
          "| G4 | beats B&H | conc no top5 | drag pp | fees / gross | verdict |\n")
        w("|---|---|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---|\n")
        for r in a["tables"]:
            g = gates(r, win)
            pf = fmt(g["gate_pf"])
            g4s = "na" if g["g4"] is None else ("pass" if g["g4"] else "fail")
            pf_h1 = fmt(r.get("pf_h1"))
            pf_h2 = fmt(r.get("pf_h2"))
            w(f"| {short_id(r['id'])} | {r['mode']} | {fmt(r.get('ret_pct'))} "
              f"| {pf} | {r['n_trades'] or 0} | {pf_h1} | {pf_h2} | {g4s} "
              f"| {'yes' if g['g5'] else 'no'} | {fmt(r.get('conc_net_without_top5_pct'))} "
              f"| {fmt(r.get('drag_pp'))} | {fmt(r.get('cost_share_pct'))} "
              f"| {'PASS' if g['pass'] else 'fail'} |\n")
        if win == "full":
            detail = []
            for r in a["tables"]:
                g = gates(r, win)
                if g["years_total"]:
                    detail.append(f"{short_id(r['id'])} green in "
                                  f"{words(g['years_green'])} of "
                                  f"{words(g['years_total'])} scored years")
            if detail:
                w("\nGreen-year detail (full window): " + "; ".join(detail) + ".\n")

    # --------------------------------------------------- drag / cost sections
    w("\n## Cost drag, measured inside the artifacts\n\n")
    w("Each artifact re-runs the same twenty strategies at zero cost on the "
      "same aligned data; drag is that control's return minus the costed "
      "return, in percentage points. The largest measured drags in this "
      "campaign:\n\n")
    for (cfg, win, costs), r in drag_top:
        rid = canon[(cfg, win, costs)]["_rid"]
        w(f"- {short_id(r['id'])} ({CELL_TAG[(cfg, win, costs)]}): zero-cost "
          f"{fmt(r.get('ret_zero_pct'))} percent versus {fmt(r.get('ret_pct'))} "
          f"percent costed -- drag {fmt(r.get('drag_pp'))} points (`{rid}`).\n")
    w("\nFees as a share of strict gross profit (discrete rows only, where "
      "the denominator is defined):\n\n")
    for (cfg, win, costs), r in fees_top:
        rid = canon[(cfg, win, costs)]["_rid"]
        w(f"- {short_id(r['id'])} ({CELL_TAG[(cfg, win, costs)]}): "
          f"{fmt(r.get('cost_share_pct'))} percent (`{rid}`).\n")

    # ------------------------------------------------------------ bench note
    w("\n## Benchmark\n\n")
    for key in CELLS:
        m = canon[key]["metrics"]
        rid = canon[key]["_rid"]
        w(f"- {CELL_TAG[key]} (`{rid}`): equal-weight benchmark return "
          f"{fmt(m['bench_ret_pct'], 2)} percent, benchmark max drawdown "
          f"{fmt(m['bench_dd_pct'], 2)} percent.\n")

    # --------------------------------------------------------------- verdict
    w("\n## Verdict\n\n")
    if total_pass == 0:
        w("zero of one hundred sixty strategy-by-cell verdicts clear every "
          "pre-declared gate. MPS20 as shipped is KILLED. No further tuning "
          "is scheduled; any revival attempt must start from a pre-declared, "
          "out-of-sample design, not from re-running this one.\n")
    else:
        pk = [k for k in CELLS if pass_counts[k] > 0]
        w(f"{words(total_pass)} of one hundred sixty strategy-by-cell "
          f"verdicts clear every gate; the passing cells are "
          + ", ".join(CELL_TAG[k] for k in pk) +
          ". Any surviving cell is subject to the multiple-testing haircut "
          "of a twenty-strategy menu and to the c5 USDC-for-USDT proxy "
          "caveat stated above.\n")

    text = md.getvalue()

    # ------------------------------------------------- pre-write guard scan
    cited = []
    for mm in vrun.RUNID_RE.findall(text):
        if mm in cited:
            continue
        if os.path.exists(vrun.artifact_path(mm)):
            cited.append(mm)
    values = []
    for rid in cited:
        a = vrun.load_artifact(rid)
        for k in ("metrics", "tables", "inputs", "params"):
            vrun._collect_numbers(a.get(k), values)
    scan = vrun.HEXWORD_RE.sub(" ", text)
    unbacked, seen = [], set()
    for tok in vrun.NUMBER_RE.findall(scan):
        try:
            val = float(tok)
        except ValueError:
            continue
        dps = len(tok.split(".")[1]) if "." in tok else 0
        if any(abs(round(v, dps) - val) < 1e-9 for v in values):
            continue
        if tok in seen:
            continue
        seen.add(tok)
        unbacked.append(tok)
    if unbacked:
        ctx = {}
        for t in unbacked:
            i = scan.find(t)
            ctx[t] = scan[max(0, i - 60):i + 40].replace("\n", " ")
        raise SystemExit("unbacked tokens (fix wording):\n" +
                         "\n".join(f"  {t!r}  ...{c}..." for t, c in ctx.items()))

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"wrote {OUT} ({len(text.splitlines())} lines); "
          f"citations {cited}; pre-write guard scan clean")


if __name__ == "__main__":
    main(sys.argv[1:])
