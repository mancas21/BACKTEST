#!/usr/bin/env python
"""Top-100 x 11 pairs x tf=1d x 2026-only campaign runner (2026-11-14).

Takes the repo's current top-100 ranking
(results/top100_2026-11-09_strategies.json), transfers EVERY strategy
verbatim (adapter + params) to tf=1d on the eleven user-named pairs, and
runs each cell through `code/vrun.py run`. "Only 2026 data" is enforced at
the bytes: data/binance_klines_1d/*.csv start at 2026-01-01 (built by
code/fetch_1d_pairs.py), so no engine can see pre-2026 bars; warmup comes
out of the window itself.

Cells whose engines carry minimum-history floors (qsc/qsd: 9000 bars,
cbpackf: 500) or hard timeframe guards (top10/smqe11/dspack/dspack2/botstrat:
1h only) are ATTEMPTED anyway and recorded with the actual refusal text —
nothing is pre-classified. REGLA 1: every runnable cell is judged only on
its own artifact; a refusal is that cell's own measured outcome.

Deduplication: the ranking contains repeated strategies (identical adapter +
params under several ranks); identical commands collapse to one cell and the
rank->cell map is preserved for the report.

Resumable: status checkpoint at results/_top100_1d2026_status.json.
Sequential on purpose (no pools). Public data only, no keys.
"""
import json
import os
import re
import shlex
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RANKING = os.path.join(ROOT, "results", "top100_2026-11-09_strategies.json")
STATUS = os.path.join(ROOT, "results", "_top100_1d2026_status.json")

PAIRS = ["JUPUSDT", "HYPEUSDT", "SUIUSDT", "ARBUSDT", "SOLUSDT",
         "ETHUSDT", "NVDAUSDT", "SPCXUSDT", "1000PEPEUSDT", "XRPUSDT",
         "BTCUSDT"]

# adapters whose normal input paths ignore TF_DIR at 1d (hardcoded 1h /
# alpaca / pack dirs): re-point them with the harness data_dir param at the
# 2026 1d store. Harmless for adapters that refuse tf=1d anyway.
DATA_DIR_ADAPTERS = {"rsimr", "eqpack", "pack50", "dspack", "dspack2"}

TF = "1d"


def build_cells():
    rows = json.load(open(RANKING, encoding="utf-8"))
    cells, rank_map = {}, {}
    for x in rows:
        tmpl = x["same_engine_command_template"]
        for pair in PAIRS:
            cmd = re.sub(r"--tf \S+", f"--tf {TF}", tmpl)
            cmd = re.sub(r"--symbol \S+", f"--symbol {pair}", cmd)
            if x["adapter"] in DATA_DIR_ADAPTERS:
                cmd += " --set data_dir=data/binance_klines_1d"
            key = cmd.split("--params")[0].strip() + "|" + \
                (cmd.split("--params", 1)[1] if "--params" in cmd else "")
            if key not in cells:
                cells[key] = {"cmd": cmd, "adapter": x["adapter"],
                              "params": x.get("params", {}), "pairs": {}}
            cells[key]["pairs"][pair] = True
            rank_map.setdefault(x["rank"], set()).add(key)
    # one cell per (unique strategy, pair)
    out = []
    for key, c in cells.items():
        for pair in sorted(c["pairs"]):
            out.append({"key": key, "adapter": c["adapter"],
                        "params": c["params"], "pair": pair,
                        "cmd": c["cmd"] if pair == sorted(c["pairs"])[0]
                        else re.sub(r"--symbol \S+", f"--symbol {pair}",
                                    c["cmd"].split(" --set data_dir")[0])
                        + (" --set data_dir=data/binance_klines_1d"
                           if c["adapter"] in DATA_DIR_ADAPTERS else "")})
    return out, rank_map


def run_cell(cell):
    """Run one vrun cell. Returns dict(status, run_id|None, reason)."""
    # shlex (NOT .split()): the --params payload is quoted JSON that may
    # contain spaces. [2:] drops the template's "python code/vrun.py" and
    # KEEPS the "run" subcommand.
    argv = [sys.executable, "code/vrun.py"] + \
        shlex.split(cell["cmd"])[2:]
    try:
        p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True,
                           timeout=600)
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "run_id": None, "reason": "timeout 600s"}
    out = (p.stdout or "") + (p.stderr or "")
    m = re.search(r"results[\\/]runs[\\/]([0-9a-f]{16})\.json", out)
    if p.returncode == 0 and m:
        return {"status": "OK", "run_id": m.group(1), "reason": ""}
    tail = [ln for ln in out.strip().splitlines() if ln.strip()][-3:]
    return {"status": "REFUSED", "run_id": None,
            "reason": " | ".join(tail)[:400]}


def main():
    cells, rank_map = build_cells()
    print(f"{len(cells)} unique cells "
          f"({sum(len(v) for v in rank_map.values())} rank-pair mappings)")
    status = {}
    if os.path.exists(STATUS):
        loaded = json.load(open(STATUS, encoding="utf-8"))
        # tolerate BOTH formats: the flat during-run checkpoint and the
        # nested {"cells":...,"rank_map":...} final write (a flat/nested
        # mismatch once silently re-ran every cell — never again).
        if "cells" in loaded and isinstance(loaded.get("cells"), dict):
            status = {k: v for k, v in loaded["cells"].items()
                      if isinstance(v, dict) and "status" in v}
        else:
            status = {k: v for k, v in loaded.items()
                      if isinstance(v, dict) and "status" in v}
    for i, cell in enumerate(cells, 1):
        ck = f"{cell['adapter']}|{cell['pair']}|" \
             f"{json.dumps(cell['params'], sort_keys=True)}"
        if ck in status:
            continue
        r = run_cell(cell)
        r["cmd"] = cell["cmd"]
        status[ck] = r
        if i % 10 == 0 or r["status"] != "OK":
            with open(STATUS, "w") as f:
                json.dump({"cells": status}, f, indent=1)
        tag = r["run_id"] or r["reason"][:80]
        print(f"[{i}/{len(cells)}] {cell['adapter']} {cell['pair']} "
              f"{json.dumps(cell['params'], sort_keys=True)[:60]} -> "
              f"{r['status']} {tag}", flush=True)
    with open(STATUS, "w") as f:
        json.dump({"cells": status, "rank_map":
                   {str(k): sorted(v) for k, v in rank_map.items()}}, f,
                  indent=1)
    ok = sum(1 for v in status.values() if isinstance(v, dict)
             and v.get("status") == "OK")
    print(f"DONE: {ok}/{len(cells)} cells produced artifacts")


if __name__ == "__main__":
    main()
