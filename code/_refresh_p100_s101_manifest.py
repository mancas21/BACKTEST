#!/usr/bin/env python
"""_refresh_p100_s101_manifest.py -- point the registry manifest's p100screen and
s101 entries at the FIXED-engine re-run artifacts (2026-11-19 audit fixes F2/F17
changed p100_screen_engine.py, orphaning the old run_ids). Matches each old entry
to the new artifact by CELL IDENTITY (params id/segment + symbol + tf), not by
run_id. Old artifacts stay append-only in results/runs/ (orphaned by design).
Run: python code/_refresh_p100_s101_manifest.py"""
import json, glob, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "results", "runs")
MAN = os.path.join(ROOT, "code", "_top100_rank.json")
NEW_P_SHA = "8250db6c"   # p100screen fixed-engine re-run
NEW_S_SHA = "c6f8cd3f"   # s101 fixed-engine re-run

new_p, new_s = {}, {}
for f in glob.glob(os.path.join(RUNS, "*.json")):
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception:
        continue
    sha = (d.get("core") or {}).get("engine_sha256", "")
    p = d.get("params", {})
    if d.get("strategy") == "p100screen" and sha.startswith(NEW_P_SHA):
        new_p[(p.get("id"), p.get("segment"), d["symbol"], d["timeframe"])] = d
    elif d.get("strategy") == "s101" and sha.startswith(NEW_S_SHA):
        new_s[(p.get("id"), d["symbol"], d["timeframe"])] = d

man = json.load(open(MAN, encoding="utf-8"))
updated, unmatched = 0, []
for r in man:
    ad = r.get("adapter")
    if ad not in ("p100screen", "s101"):
        continue
    op = os.path.join(RUNS, r["run_id"] + ".json")
    if not os.path.exists(op):
        unmatched.append((ad, r["run_id"], "no-old-artifact")); continue
    old = json.load(open(op, encoding="utf-8"))
    p = old.get("params", {})
    if ad == "p100screen":
        key = (p.get("id"), p.get("segment"), old["symbol"], old["timeframe"]); nd = new_p.get(key)
    else:
        key = (p.get("id"), old["symbol"], old["timeframe"]); nd = new_s.get(key)
    if nd is None:
        unmatched.append((ad, r["run_id"], key)); continue
    m = nd["metrics"]
    r["run_id"] = nd["run_id"]; r["ret"] = m.get("return_pct"); r["pf"] = m.get("profit_factor")
    r["n"] = m.get("n_trades"); r["dd"] = m.get("max_dd_pct")
    r["funding"] = m.get("funding_charged"); r["created"] = nd.get("created_utc")
    updated += 1

json.dump(man, open(MAN, "w", encoding="utf-8"), ensure_ascii=False)
print(f"manifest entries updated to fixed-engine run_ids: {updated}")
print(f"unmatched (left as-is): {len(unmatched)}")
for u in unmatched[:20]:
    print("  ", u)
print("p100screen new lookup:", len(new_p), " s101 new lookup:", len(new_s))
