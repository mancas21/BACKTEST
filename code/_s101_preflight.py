"""_s101_preflight.py — pre-flight validator for the s101 pack.

Runs EVERY cell of the plan end-to-end on a short slice (~60 days) BEFORE
the long screen pass: catches input-resolution failures, build_frame gaps,
signal-machine exceptions, tables-schema mismatches and broken accounting
invariants in minutes instead of after an 86-minute screen with 34 errors.

Sliced kline files are written to data/_s101_preflight_tmp/ under their
ORIGINAL basename (the engine's _pick matches basename suffixes); funding
JSONs pass through untouched (funding_events outside the slice window is
harmless: the book is flat there, nothing is billed).

Usage: python code/_s101_preflight.py [--days 60]
Exit 0 = all cells pass pre-flight; exit 1 = failures listed.
"""

import argparse
import importlib
import json
import os
import shutil
import sys
import time

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=60)
    args = ap.parse_args()

    import s101_engine as eng
    importlib.reload(eng)
    import vrun

    plan = json.load(open(os.path.join(ROOT, "results", "bt_plans",
                                       "s101.json"), encoding="utf-8"))
    tmpdir = os.path.join(ROOT, "data", "_s101_preflight_tmp")
    os.makedirs(tmpdir, exist_ok=True)
    fails = []
    ok = 0
    try:
        for job in plan["jobs"]:
            idn = int(dict(kv.split("=", 1) for kv in job["set"])["id"])
            sym = job["symbol"]
            label = job["label"]
            t0 = time.time()
            sliced = []
            try:
                paths = vrun.ADAPTERS["s101"]["inputs"]("15m", sym)
                if not paths:
                    raise ValueError("no inputs resolved")
                for p in paths:
                    if "funding" in p:
                        sliced.append(p)  # pass through, untouched
                        continue
                    df = eng._frame_from(p)
                    cut = df["timestamp"].iloc[-1] - pd.Timedelta(
                        days=args.days)
                    sl = df[df["timestamp"] >= cut]
                    if len(sl) < 100:
                        raise ValueError(
                            f"slice too small: {os.path.basename(p)}")
                    outp = os.path.join(tmpdir, os.path.basename(p))
                    sl.to_csv(outp, index=False)
                    sliced.append(outp)
                m, prov, tabs = eng.dispatch(sliced, {"id": idn})
                # schema + invariant checks
                if not isinstance(tabs, list) or not tabs \
                        or not isinstance(tabs[0], dict) \
                        or "id" not in tabs[0]:
                    raise ValueError("tables not in bt.py list-of-rows form")
                if m["n_trades"] > 0 \
                        and abs(float(m.get("pnl_identity_resid", 0.0))) > 1.0:
                    raise ValueError(
                        f"invariant resid {m['pnl_identity_resid']}")
                if m["n_trades"] == 0:
                    print(f"  {label}: OK (0 trades on slice) "
                          f"[{time.time() - t0:.1f}s]")
                else:
                    print(f"  {label}: OK n={m['n_trades']} "
                          f"[{time.time() - t0:.1f}s]")
                ok += 1
            except Exception as e:
                fails.append((label, f"{type(e).__name__}: {e}"))
                print(f"  {label}: FAIL {type(e).__name__}: {e} "
                      f"[{time.time() - t0:.1f}s]")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    print(f"\npre-flight: {ok}/{len(plan['jobs'])} cells OK")
    if fails:
        print("FAILURES:")
        for label, err in fails:
            print(f"  {label}: {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
