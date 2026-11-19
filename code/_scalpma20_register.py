#!/usr/bin/env python
"""_scalpma20_register.py -- append the 120 scalpma20 screen artifacts to the
registry manifest code/_top100_rank.json (the registry's static source), preserving
every existing entry. Idempotent. Then re-run strategy_registry.py."""
from __future__ import annotations
import json, glob, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAN = os.path.join(ROOT, "code", "_top100_rank.json")
base = json.load(open(MAN, encoding="utf-8"))
have = {r["run_id"] for r in base if r.get("adapter") == "scalpma20"}
added = 0
for f in glob.glob(os.path.join(ROOT, "results", "runs", "*.json")):
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception:
        continue
    if d.get("strategy") != "scalpma20":
        continue
    rid = d["run_id"]
    if rid in have:
        continue
    m = d.get("metrics", {})
    base.append({
        "run_id": rid, "adapter": "scalpma20",
        "symbol": d.get("symbol"), "tf": d.get("timeframe"),
        "label": f"{int(m.get('strategy_id',0)):02d}_{m.get('strategy_name')}",
        "ret": m.get("return_pct"), "pf": m.get("profit_factor"),
        "n": m.get("n_trades"), "dd": m.get("max_dd_pct"),
        "bh": None, "window": None, "fee": None, "slip": None,
        "funding": m.get("funding_charged"), "created": d.get("created_utc"),
        "gates": None,
    })
    have.add(rid); added += 1
json.dump(base, open(MAN, "w", encoding="utf-8"), ensure_ascii=False)
print(f"manifest entries total={len(base)}  scalpma20 added={added}  "
      f"scalpma20 present={sum(1 for r in base if r.get('adapter')=='scalpma20')}")
