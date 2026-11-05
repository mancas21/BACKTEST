"""Assert the report's totals against independently computed expectations.

AGENTS.md: 'guard is a PROVENANCE check, not a CORRECTNESS check. It passed on a
report whose builder was silently double-counting cells. Assert totals against
expectations yourself.'

This recomputes every count and every median in results/cbpack_backtest.md straight
from the artifacts, and fails loudly on any mismatch.
"""
import glob
import json
import os
import re
import sys

ROOT = r"C:\Users\Lenovo\Documents\backtest-system"
RUNS = os.path.join(ROOT, "results", "runs")
REPORT = os.path.join(ROOT, "results", "cbpack_backtest.md")
TFS = ["1h", "15m", "5m", "1m"]
SIDS = [f"S{i:02d}" for i in range(1, 11)]
GROSS = {"fee_bps": 0.0, "slippage_bps": 0.0}

fails = []


def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


# ── load
grid, gross = {}, {}
allids = set()
for p in sorted(glob.glob(os.path.join(RUNS, "*.json"))):
    if os.path.basename(p).startswith("_"):
        continue
    a = json.load(open(p, encoding="utf-8"))
    if a.get("schema") != "bt-artifact/1" or a.get("strategy") != "cbpack":
        continue
    allids.add(a["run_id"])
    prm = a.get("params") or {}
    if prm == {}:
        grid[(a["timeframe"], a["symbol"])] = a
    elif prm == GROSS:
        gross[(a["timeframe"], a["symbol"])] = a

text = open(REPORT, encoding="utf-8").read()
row = lambda a, sid: next((x for x in (a.get("tables") or []) if x.get("id") == sid), None)

print("grid artifacts on disk (full-window, params={}):")
check(len(grid) == 28, f"28 cells expected, {len(grid)} found")
check(sorted({tf for tf, _ in grid}) == sorted(TFS), "all four timeframes present")
check(len({s for _, s in grid}) == 7, f"7 symbols, {len({s for _, s in grid})} found")

# ── 1. coverage table rows
cov = re.findall(r"^\| (1h|15m|5m|1m) \| (\w+) \| \d+ \| .*\| `([0-9a-f]{16})` \|$", text, re.M)
check(len(cov) == 28, f"coverage table has 28 rows, found {len(cov)}")
check(len({(a, b) for a, b, _ in cov}) == 28, "coverage rows are unique cells")
check(all(grid[(tf, s)]["run_id"] == rid for tf, s, rid in cov),
      "every coverage row cites that cell's own artifact")

# ── 2. the headline pass counts vs an independent recount
independent = sum(1 for a in grid.values() for r in (a.get("tables") or [])
                  if r.get("status") == "ok" and r["PF"] > 1.2 and r["trades"] >= 30)
declared = sum(a["metrics"]["n_pf_gt_1p2_n30"] for a in grid.values())
check(independent == declared,
      f"passing (cell,strategy) pairs: recount {independent} == metrics sum {declared}")
per_tf = {}
for a in grid.values():
    per_tf.setdefault(a["timeframe"], 0)
    per_tf[a["timeframe"]] += a["metrics"]["n_pf_gt_1p2_n30"]
print(f"       per timeframe: {per_tf}")

# ── 3. every (cell, strategy) pass claimed in the grid table is real
bad = []
for m in re.finditer(r"^\| (1h|15m|5m|1m) \| (\w+) \| ([-\d.]+) \| ([\d.]+) \| (S\d\d) \| (\d+) of (\d+) \| ([-\d.]+) \| `([0-9a-f]{16})` \|$",
                     text, re.M):
    tf, sym, net, pf, sid, npass, nstrat, bh, rid = m.groups()
    a = grid[(tf, sym)]
    if a["run_id"] != rid:
        bad.append(f"{tf} {sym}: cites {rid}, artifact is {a['run_id']}")
        continue
    if f"{a['metrics']['best_net_pct']:.2f}" != net:
        bad.append(f"{tf} {sym}: best net% {net} vs artifact {a['metrics']['best_net_pct']:.2f}")
    if int(npass) != a["metrics"]["n_pf_gt_1p2_n30"]:
        bad.append(f"{tf} {sym}: pass count {npass} vs metrics {a['metrics']['n_pf_gt_1p2_n30']}")
    if int(nstrat) != a["metrics"]["n_strategies"]:
        bad.append(f"{tf} {sym}: strategy count {nstrat} vs metrics {a['metrics']['n_strategies']}")
check(not bad, f"grid table agrees with artifacts ({len(bad)} mismatches)"
      + ("" if not bad else "\n         " + "\n         ".join(bad[:8])))

# ── 4. medians in the per-strategy table
syms = sorted({s for _, s in grid})
bad = []
mism = []
for m in re.finditer(r"^\| (S\d\d) \| (1h|15m|5m|1m) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| (\d+) of (\d+) \|$",
                     text, re.M):
    sid, tf, gm, nm, drag, npos, ntot = m.groups()
    gv = sorted(row(gross[(tf, s)], sid)["PF"] for s in syms if (tf, s) in gross
                and row(gross[(tf, s)], sid) and row(gross[(tf, s)], sid).get("status") == "ok")
    nv = sorted(row(grid[(tf, s)], sid)["PF"] for s in syms if (tf, s) in grid
                and row(grid[(tf, s)], sid) and row(grid[(tf, s)], sid).get("status") == "ok")
    if not gv or not nv:
        continue
    if f"{gv[len(gv)//2]:.2f}" != gm or f"{nv[len(nv)//2]:.2f}" != nm:
        mism.append(f"{sid} {tf}: shown gross {gm}/net {nm}, recompute {gv[len(gv)//2]:.2f}/{nv[len(nv)//2]:.2f}")
    if f"{gv[len(gv)//2] - nv[len(nv)//2]:.2f}" != drag:
        mism.append(f"{sid} {tf}: drag {drag} != {gv[len(gv)//2]-nv[len(nv)//2]:.2f}")
    if int(npos) != sum(1 for v in gv if v > 1.0) or int(ntot) != len(gv):
        mism.append(f"{sid} {tf}: gross>1 {npos} of {ntot} != {sum(1 for v in gv if v>1.0)} of {len(gv)}")
check(not mism, f"zero-cost medians recompute ({len(mism)} mismatches)"
      + ("" if not mism else "\n         " + "\n         ".join(mism[:8])))

# ── 5. every cited run_id must exist (guard already checks this, but assert)
cited = set(re.findall(r"`([0-9a-f]{16})`", text))
missing = sorted(c for c in cited if c not in allids)
check(not missing, f"all {len(cited)} cited run_ids exist as artifacts"
      + ("" if not missing else f" -- missing {missing}"))

# ── 6. gate table row count vs the gate record
gates = json.load(open(os.path.join(ROOT, "results", "cbpack_gates.json"), encoding="utf-8"))
n_expected = sum(len(g["ids"]) for g in gates)
gate_rows = re.findall(r"^\| (1h|15m|5m|1m) \| (\w+) \| (S\d\d) \| [-\d.]+ \| [\d.]+ \| \d+ \| \d+ of \d+ \| \d+ of \d+ \| \d+ of \d+ \| [\d.]+ \| `[0-9a-f]{16}` \|$",
                      text, re.M)
check(len(gate_rows) == n_expected,
      f"gate summary table has {n_expected} rows (candidates x strategies), found {len(gate_rows)}")
wf_rows = re.findall(r"^\| (1h|15m|5m|1m) \| (\w+) \| (S\d\d) \| \d+/\d+ \| \d+ \| [-\d.]+ \| \d+ of \d+ \| [-\d.]+ \| `[0-9a-f]{16}` \|$",
                     text, re.M)
n_wf = sum(len(g["ids"]) * len(g["gates"]["walk_forward"]) for g in gates)
check(len(wf_rows) == n_wf, f"walk-forward detail has {n_wf} rows, found {len(wf_rows)}")
per_rows = re.findall(r"^\| (1h|15m|5m|1m) \| (\w+) \| (S\d\d) \| \d \| [-\d.]+ \| [-\d.]+ \| [-\d.]+ \| [\d.]+ \| \d+ \| [\d.]+ \| [-\d.]+ \| `[0-9a-f]{16}` \|$",
                      text, re.M)
n_per = sum(len(g["ids"]) * len(g["gates"]["periods"]) for g in gates)
check(len(per_rows) == n_per, f"period table has {n_per} rows, found {len(per_rows)}")

print()
if fails:
    print(f"{len(fails)} ASSERTION(S) FAILED")
    sys.exit(1)
print("all report totals reconcile")
