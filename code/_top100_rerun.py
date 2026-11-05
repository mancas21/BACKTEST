"""_top100_rerun.py — re-run the recorded `cmd` of each cited artifact verbatim
on the CURRENT data bytes, 8 workers, and capture each new run_id.

The new artifact is a fresh measurement pinned to today's data + engine.
Writes code/_top100_rerun_map.json: [{cmd, old_run_id, new_run_id, rc, err}].
"""

import json
import os
import re
import shlex
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

PY = sys.executable.replace("\\", "/")

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
CMDS = os.path.join(os.path.dirname(__file__), "_top100_cmds.txt")
OUT = os.path.join(os.path.dirname(__file__), "_top100_rerun_map.json")

# cmd -> the run_id whose row(s) it produced (for tracing); several ids can
# share one cmd (a cbpackf cell carries ten strategies).
kept = json.load(open(os.path.join(os.path.dirname(__file__), "_top100_kept.json")))
old_by_cmd = {}
for r in kept:
    p = os.path.join(ROOT, "results", "runs", r["run_id"] + ".json")
    d = json.load(open(p))
    old_by_cmd.setdefault(d.get("cmd", ""), []).append(r["run_id"])

cmds = [c for c in open(CMDS, encoding="utf-8").read().splitlines() if c.strip()]
results = []


def one(cmd):
    argv = shlex.split(cmd)
    argv[0] = sys.executable
    p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True,
                       timeout=3600)
    m = re.search(r"artifact\s*:\s*(\S+)", p.stdout)
    new_id = os.path.basename(m.group(1))[:-5] if m else None
    err = ""
    if p.returncode != 0 or not new_id:
        err = (p.stderr or p.stdout)[-500:]
    return {"cmd": cmd, "old_run_ids": old_by_cmd.get(cmd, []), "new_run_id": new_id,
            "rc": p.returncode, "err": err}


with ThreadPoolExecutor(max_workers=8) as ex:
    futs = {ex.submit(one, c): c for c in cmds}
    for i, fut in enumerate(as_completed(futs), 1):
        r = fut.result()
        results.append(r)
        tag = r["new_run_id"] or f"RC={r['rc']}"
        print(f"[{i}/{len(cmds)}] {tag}  <- {r['cmd'][:100]}", flush=True)
        if r["err"]:
            print("   ERR:", r["err"].replace(chr(10), " | ")[:300], flush=True)

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=1)
ok = sum(1 for r in results if r["new_run_id"])
print(f"DONE {ok}/{len(cmds)} re-runs produced new artifacts; map -> {OUT}")
