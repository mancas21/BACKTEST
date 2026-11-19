"""_top100_rerun_20261119.py — fresh re-run of the TOP-100 catalog, in-process.

For each cited run_id in results/top100_catalog.json (the 2026-11-19 list cited
by results/TOP100_ESTRATEGIAS.md), rebuild the job from the artifact's
structured fields (strategy, timeframe, symbol, params) and call
vrun.make_artifact(..., cut_ts="auto") + vrun.save_artifact — the same idiom as
the house shard scripts (code/_qs_shard.py). cut_ts="auto" freezes the data cut
at creation day, so every cell is measured against the current data bytes
(run_id generation 2). No subprocess, no shell. Append-only: only new files in
results/runs/.

Extra coverage: the 23 p100screen ranks cite only their DEV cell; their OOS
sibling cells (segment="OOS", same id/symbol/tf, resolved through
results/_p100_screen_cells.json) are re-run too, so OOS numbers refresh.

8 process workers. Writes results/_top100_rerun_20261119_map.json.
"""

import json
import re
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))
CATALOG = ROOT / "results" / "top100_catalog.json"
P100_CELLS = ROOT / "results" / "_p100_screen_cells.json"
OUT = ROOT / "results" / "_top100_rerun_20261119_map.json"
RUNS_DIR = (ROOT / "results" / "runs").resolve()

# run_ids are 16 lowercase-hex chars produced by vrun; enforce before any
# filesystem use so a stray catalog value can never traverse out of runs/.
RUN_ID_RE = re.compile(r"^[0-9a-f]{16}$")


def load_artifact(run_id: str) -> dict:
    """Read one run artifact, with strict id validation + containment."""
    if not RUN_ID_RE.match(run_id):
        raise ValueError(f"refusing non-hex run_id: {run_id!r}")
    p = (RUNS_DIR / f"{run_id}.json").resolve()
    if p.parent != RUNS_DIR:
        raise ValueError(f"path escapes runs dir: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


METRIC_KEYS = (
    "profit_factor",
    "return_pct",
    "n_trades",
    "max_dd_pct",
    "oos_profit_factor",
    "oos_return_pct",
    "oos_n_trades",
    "funding_charged",
    "cost_bp_roundtrip",
    "boot_ci_lo",
)


def run_job(job):
    """Worker: build one fresh artifact. Returns a picklable record."""
    rec = dict(job)  # keep ALL job keys (incl. ranks_extra) for the parent
    rec["new_run_id"] = None
    rec["rc"] = None
    rec["err"] = ""
    rec["metrics"] = {}
    try:
        import vrun  # imported inside the worker process

        a = vrun.make_artifact(job["strategy"], job["tf"], job["symbol"],
                               job["params"], cut_ts="auto")
        vrun.save_artifact(a)
        rec["new_run_id"] = a["run_id"]
        rec["rc"] = 0
        m = a.get("metrics", {})
        rec["metrics"] = {k: m.get(k) for k in METRIC_KEYS if m.get(k) is not None}
        rec["created_utc"] = a.get("created_utc")
    except Exception as e:  # per-job isolation; one failure never stops the batch
        rec["rc"] = -1
        rec["err"] = f"{type(e).__name__}: {e}"[:500]
    return rec


def main():
    rows = json.loads(CATALOG.read_text(encoding="utf-8"))
    cells = {}
    if P100_CELLS.exists():
        cells = json.loads(P100_CELLS.read_text(encoding="utf-8"))

    jobs, seen = [], {}

    def add_job(rank, family, name, symbol, tf, strategy, params, old_run_id, kind):
        job = {"rank": rank, "family": family, "name": name, "symbol": symbol,
               "tf": tf, "strategy": strategy, "params": params,
               "old_run_id": old_run_id, "kind": kind}
        key = json.dumps([strategy, tf, symbol, params], sort_keys=True)
        prev = seen.get(key)
        if prev is not None:
            prev["ranks_extra"].append(job)
            return
        job["ranks_extra"] = []
        seen[key] = job
        jobs.append(job)

    for r in rows:
        art = load_artifact(r["run_id"])
        add_job(r["rank"], r["family"], r["name"], art["symbol"], art["timeframe"],
                art["strategy"], art["params"], r["run_id"], "cited")

        # p100screen: also re-run the OOS sibling cell of the same id/sym/tf
        if art["strategy"] == "p100screen":
            m = re.search(r"id=(\d+)", r["name"])
            if m:
                sid = int(m.group(1))
                for entry in cells.values():
                    if (entry.get("id") == sid and entry.get("segment") == "OOS"
                            and entry.get("symbol") == art["symbol"]
                            and entry.get("tf") == art["timeframe"]):
                        add_job(r["rank"], r["family"], r["name"],
                                art["symbol"], art["timeframe"], "p100screen",
                                {"id": sid, "segment": "OOS"},
                                entry.get("run_id"), "oos_sibling")
                        break

    n_extra = sum(len(j["ranks_extra"]) for j in jobs)
    print(f"{len(rows)} catalog rows -> {len(jobs)} unique jobs "
          f"({n_extra} catalog ranks linked)", flush=True)

    results = []
    try:
        with ProcessPoolExecutor(max_workers=8) as ex:
            futs = {ex.submit(run_job, j): j for j in jobs}
            for i, fut in enumerate(as_completed(futs), 1):
                rec = fut.result()
                results.append(rec)
                ranks = [rec["rank"]] + [x["rank"] for x in rec["ranks_extra"]]
                tag = rec["new_run_id"] or f"RC={rec['rc']}"
                print(f"[{i}/{len(jobs)}] rank(s) {ranks} [{rec['kind']}] -> {tag} "
                      f"| {rec['strategy']} {rec['symbol']} {rec['tf']} "
                      f"params={json.dumps(rec['params'])[:60]}", flush=True)
                if rec["err"]:
                    print(f"   ERR rank {ranks}:", rec["err"][:300], flush=True)
    finally:
        # write whatever finished, even if the batch is interrupted
        OUT.write_text(json.dumps(results, indent=1), encoding="utf-8")

    ok = sum(1 for r in results if r["new_run_id"])
    ranks_ok = sum(1 + len(r["ranks_extra"]) for r in results if r["new_run_id"])
    print(f"DONE {ok}/{len(jobs)} jobs -> {ranks_ok}/{len(rows)} ranks with fresh "
          f"artifacts; map -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
