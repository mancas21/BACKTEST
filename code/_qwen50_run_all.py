"""_qwen50_run_all.py — run all 48 runnable qwen50 cells through
vrun.make_artifact (cut_ts=auto) + save_artifact, 8 process workers, one
artifact per cell. The same in-process idiom as the house shard scripts and
_top100_rerun_20261119.py. Writes results/_qwen50_run_all_map.json."""

import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))
OUT = ROOT / "results" / "_qwen50_run_all_map.json"


def run_job(idn):
    rec = {"id": idn, "new_run_id": None, "rc": None, "err": "",
           "metrics": {}}
    try:
        import vrun  # in the worker process

        symbol, tf_label, tf_minutes, _src = __import__(
            "qwen50_engine").CELLS[idn]
        a = vrun.make_artifact("qwen50", tf_label, symbol, {"id": idn},
                               cut_ts="auto")
        vrun.save_artifact(a)
        rec["new_run_id"] = a["run_id"]
        rec["symbol"] = symbol
        rec["tf"] = tf_label
        rec["rc"] = 0
        m = a.get("metrics", {})
        rec["metrics"] = {k: m.get(k) for k in (
            "profit_factor", "return_pct", "n_trades", "max_dd_pct",
            "oos_profit_factor", "oos_return_pct", "oos_n_trades",
            "cost_bp_roundtrip", "boot_ci_lo", "funding_paid_usdt",
            "bh_return_pct") if m.get(k) is not None}
        rec["created_utc"] = a.get("created_utc")
    except Exception as e:
        rec["rc"] = -1
        rec["err"] = f"{type(e).__name__}: {e}"[:500]
    return rec


def main():
    import qwen50_engine as Q
    ids = sorted(Q.CELLS)
    print(f"{len(ids)} runnable cells", flush=True)
    results = []
    with ProcessPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(run_job, i): i for i in ids}
        for k, fut in enumerate(as_completed(futs), 1):
            rec = fut.result()
            results.append(rec)
            tag = rec["new_run_id"] or f"RC={rec['rc']}"
            m = rec["metrics"]
            print(f"[{k}/{len(ids)}] id={rec['id']} -> {tag} "
                  f"{rec.get('symbol', '')} {rec.get('tf', '')} "
                  f"n={m.get('n_trades')} pf={m.get('profit_factor')}",
                  flush=True)
            if rec["err"]:
                print(f"   ERR id {rec['id']}:", rec["err"][:300], flush=True)
    OUT.write_text(json.dumps(results, indent=1), encoding="utf-8")
    ok = sum(1 for r in results if r["new_run_id"])
    print(f"DONE {ok}/{len(ids)} artifacts; map -> {OUT}", flush=True)
    return 0 if ok == len(ids) else 1


if __name__ == "__main__":
    sys.exit(main())
