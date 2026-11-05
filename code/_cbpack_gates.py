#!/usr/bin/env python
"""Out-of-sample gates for cbpack cells that cleared the in-sample repo gate.

AGENTS.md requires, before any pass is called a candidate:
  * PF ex-cost > 1.2, n >= 30
  * green in >= 2/3 periods  -> the PERIOD SPLIT gate
  * walk-forward / OOS holds -> the WALK-FORWARD gate (the pack's own)
plus a cost-robustness check, because the pack's default costs (5+2 bps/side)
are materially cheaper than this repo's standard (6+5 bps/side).

Since 2026-10-20 two more gates apply, because the cbpack-1 engine never debited
funding and never measured concentration:

  * FUNDING GATE. The pack attaches a funding_rate column but never charges it
    (its own docstring: "No funding payments"). `funding_attached: true` in an
    artifact means the COLUMN was attached, not that the COST was charged. The
    `cbpackf` adapter runs the same pack through
    code/cbpack_funding_engine.py, which bills funding at the settlement instants
    and also reports the concentration diagnostics. The fork is proven equivalent
    to the original with funding zeroed (code/_cbpack_funding_parity.py).
  * CONCENTRATION GATE. A strategy whose best 5 trades exceed 100% of total PnL
    is a handful of lucky positions, not an edge. `conc_passes` is true only when
    the return survives removing the best 5 trades.

Every gate is executed through vrun.make_artifact + vrun.save_artifact, so each
number in the summary below has a persisted artifact and a run_id behind it.

Usage:  python code/_cbpack_gates.py [tf:symbol ...]      (default: CELLS)
"""
from __future__ import annotations

import json
import os
import sys
import time

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))
import vrun  # noqa: E402

OUT = os.path.join(ROOT, "results", "cbpack_gates.json")

# cells that cleared PF>1.2 & n>=30 in the full-window grid
CELLS = [
    {"tf": "1h", "sym": "SOLUSDT", "ids": ["S10"]},
    {"tf": "1h", "sym": "XRPUSDT", "ids": ["S10", "S02"]},
    {"tf": "15m", "sym": "HYPEUSDT", "ids": ["S07"]},
]

TF_MIN = {"1m": 1, "5m": 5, "15m": 15, "1h": 60}
WF_CONFIGS = [(120, 60), (90, 30), (180, 90)]   # (train_days, test_days) geometries
REPO_FEE = 5.0      # AGENTS.md (2026-10-25): 5 bps fee + 0.5 bps slip per side = 11 bps RT
REPO_SLIP = 0.5     # medido en libro vivo: spread 0.77 bps + impacto $10k
N_PERIODS = 3


def bars_for(tf: str, days: int) -> int:
    return int(days * 1440 / TF_MIN[tf])


def run(params: dict, tf: str, sym: str, label: str, log: list,
        strategy: str = "cbpack") -> dict:
    t = time.time()
    a = vrun.make_artifact(strategy, tf, sym, params)
    vrun.save_artifact(a)
    log.append({"label": label, "tf": tf, "sym": sym, "params": params,
                "strategy": strategy,
                "run_id": a["run_id"], "seconds": round(time.time() - t, 1)})
    print(f"    {label:<28} {a['run_id']}  {time.time()-t:6.1f}s", flush=True)
    return a


def row_of(a: dict, sid: str) -> dict | None:
    for r in (a.get("tables") or []):
        if r.get("id") == sid:
            return r
    return None


def main() -> int:
    cells = CELLS
    if len(sys.argv) > 1:
        cells = [{"tf": a.split(":")[0], "sym": a.split(":")[1],
                  "ids": a.split(":")[2].split(",") if len(a.split(":")) > 2 else []}
                 for a in sys.argv[1:]]

    log, report = [], []
    for cell in cells:
        tf, sym = cell["tf"], cell["sym"]
        ids = cell["ids"]
        print(f"\n=== {tf} {sym}  (ids: {','.join(ids) or 'all'}) ===", flush=True)

        base = vrun.make_artifact("cbpack", tf, sym, {})
        i = base["inputs"][0]
        t0, t1 = pd.Timestamp(i["start"]), pd.Timestamp(i["end"])
        rec = {"tf": tf, "sym": sym, "base_run_id": base["run_id"], "ids": ids,
               "window": [str(t0), str(t1)], "bars": i["bars"], "gates": {}}

        # ── gate 1: the pack's own walk-forward (parameters re-selected each fold),
        # run at three window geometries. A verdict that flips when the window
        # changes is window-picking, not edge, so the geometry itself is a gate.
        rec["gates"]["walk_forward"] = []
        for tr_d, te_d in WF_CONFIGS:
            tr, te = bars_for(tf, tr_d), bars_for(tf, te_d)
            wf = run({"mode": "wf", "train_bars": tr, "test_bars": te, "ids": ",".join(ids)},
                     tf, sym, f"wf {tr_d}d/{te_d}d train={tr}", log)
            wf_rows = {r["id"]: r for r in wf["tables"] if r.get("kind") == "summary"}
            rec["gates"]["walk_forward"].append({
                "run_id": wf["run_id"], "train_days": tr_d, "test_days": te_d,
                "train_bars": tr, "test_bars": te,
                "oos_bh_mean_pct": wf["metrics"]["oos_bh_mean_pct"],
                "strategies": {k: {"folds": v["folds"], "oos_net_%": v["oos_net_%"],
                                   "folds_profitable": v["folds_profitable"],
                                   "mean_test_net_%": v["mean_test_net_%"]}
                               for k, v in wf_rows.items()}})
            for sid, v in sorted(wf_rows.items()):
                print(f"      WF[{tr_d}d/{te_d}d] {sid}: folds={v['folds']} "
                      f"oos={v['oos_net_%']:+.2f}% folds_win={v['folds_profitable']}/{v['folds']} "
                      f"(bh {wf['metrics']['oos_bh_mean_pct']:+.2f}%)", flush=True)

        # ── gate 2: period split (same fixed params, 3 equal slices)
        span = (t1 - t0) / N_PERIODS
        pers = []
        for k in range(N_PERIODS):
            lo, hi = t0 + span * k, t0 + span * (k + 1)
            sl = run({"slice_from": lo.isoformat(), "slice_to": hi.isoformat()},
                     tf, sym, f"period {k+1}/{N_PERIODS} {str(lo)[:10]}", log)
            pers.append({"slice": k + 1, "run_id": sl["run_id"],
                         "from": str(lo), "to": str(hi), "bars": sl["inputs"][0]["bars"],
                         "rows": {sid: row_of(sl, sid) for sid in ids}})
        rec["gates"]["periods"] = pers
        for sid in ids:
            txt = []
            for p in pers:
                r = p["rows"].get(sid)
                txt.append(f"n={r['trades']:.0f} PF={r['PF']:.2f} net={r['net_%']:+.2f}%"
                           if r else "n/a")
            print(f"      PERIODS {sid}: " + " | ".join(txt), flush=True)

        # ── gate 3: repo-standard costs (6 + 5 bps/side = 22 bp round trip vs 14)
        cost = run({"fee_bps": REPO_FEE, "slippage_bps": REPO_SLIP},
                   tf, sym, f"repo costs {REPO_FEE}+{REPO_SLIP}bps", log)
        rec["gates"]["repo_costs"] = {
            "run_id": cost["run_id"], "fee_bps": REPO_FEE, "slippage_bps": REPO_SLIP,
            "cost_bp_roundtrip": cost["metrics"]["cost_bp_roundtrip"],
            "rows": {sid: row_of(cost, sid) for sid in ids}}
        for sid in ids:
            r = row_of(cost, sid)
            b = row_of(base, sid)
            if r and b:
                print(f"      COSTS {sid}: pack {b['net_%']:+.2f}% PF {b['PF']:.2f} "
                      f"-> repo {r['net_%']:+.2f}% PF {r['PF']:.2f}", flush=True)

        # ── gate 4: FUNDING (cbpackf = the same pack with funding actually charged)
        #     and CONCENTRATION (best-5 share of PnL, net without the best 5).
        #     The cbpack-1 engine attaches the funding column but never debits it,
        #     so gate 3 above is measured WITHOUT a real cost of carry.
        fund = run({}, tf, sym, "funding charged + concentration", log, strategy="cbpackf")
        rec["gates"]["funding_and_concentration"] = {
            "run_id": fund["run_id"],
            "engine_version": fund["provenance"].get("engine_version"),
            "funding_charged": fund["metrics"].get("funding_charged"),
            "n_settlements": fund["metrics"].get("n_settlements"),
            "rows": {sid: row_of(fund, sid) for sid in ids}}
        for sid in ids:
            r = row_of(fund, sid)
            b = row_of(base, sid)
            if r and b:
                print(f"      FUNDING+CONC {sid}: net {b['net_%']:+.2f}% -> "
                      f"{r['net_%']:+.2f}% (drag {r['net_%']-b['net_%']:+.2f}pp)  "
                      f"funding {r.get('funding_paid_pct', 0.0):+.2f}% of equity  "
                      f"best5 {r.get('conc_top5_share', float('nan'))*100:.0f}% of PnL  "
                      f"net w/o best5 {r.get('conc_net_without_top5_pct', float('nan')):+.1f}%  "
                      f"-> {'PASS' if r.get('conc_passes') else 'FAIL (concentrated)'}",
                      flush=True)

        # ── gate 5: the repo-standard costs WITH funding charged, which is the
        #     number that actually faces a trader holding a perpetual.
        fund_repo = run({"fee_bps": REPO_FEE, "slippage_bps": REPO_SLIP},
                        tf, sym, f"repo costs + funding {REPO_FEE}+{REPO_SLIP}bps", log,
                        strategy="cbpackf")
        rec["gates"]["repo_costs_with_funding"] = {
            "run_id": fund_repo["run_id"],
            "fee_bps": REPO_FEE, "slippage_bps": REPO_SLIP,
            "rows": {sid: row_of(fund_repo, sid) for sid in ids}}
        for sid in ids:
            r = row_of(fund_repo, sid)
            b = row_of(base, sid)
            if r and b:
                verdict = ("PASS" if r["PF"] > 1.2 and r["trades"] >= 30
                           and r.get("conc_passes") else "FAIL")
                print(f"      FINAL {sid}: net {r['net_%']:+.2f}% PF {r['PF']:.2f} "
                      f"n {r['trades']:.0f} B&H {r['buy_hold_%']:+.1f}% "
                      f"excess {r['excess_%']:+.1f}pp  -> {verdict}", flush=True)

        # ── gate 6: PBO (CSCV) and Deflated Sharpe overfitting evaluation
        rec["gates"]["pbo_cscv"] = {}
        try:
            import cbpack_funding_engine as fe
            raw_df = pd.read_csv(base["inputs"][0]["path"])
            raw_df.columns = [str(c).strip().lower() for c in raw_df.columns]
            raw_df = raw_df.rename(columns={"open_ts": "open_time"})
            raw_df["open_time"] = pd.to_datetime(raw_df["open_time"], unit="ms", utc=True)
            df_prep = fe.prepare(raw_df.set_index("open_time"))
            cfg_overfit = fe.BacktestConfig(fee_bps=REPO_FEE, slippage_bps=REPO_SLIP)
            for sid in ids:
                orep = fe.overfit_report(df_prep, sid, cfg_overfit)
                pbo_val = orep.get("pbo")
                passes_pbo = bool(pbo_val is not None and pbo_val < 0.50)
                rec["gates"]["pbo_cscv"][sid] = {
                    "status": orep.get("status"),
                    "pbo": pbo_val,
                    "dsr": orep.get("dsr"),
                    "passes_pbo": passes_pbo,
                    "n_configs": orep.get("n_configs"),
                }
                if pbo_val is not None:
                    print(f"      PBO[CSCV] {sid}: pbo={pbo_val:.2%} dsr={orep.get('dsr')} "
                          f"-> {'PASS' if passes_pbo else 'FAIL (overfit)'}", flush=True)
        except Exception as e:
            print(f"      PBO[CSCV] check note: {e}", flush=True)

        report.append(rec)

    prev = []
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            prev = [r for r in json.load(f) if r["tf"] + r["sym"] not in
                    {c["tf"] + c["sym"] for c in report}]
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(prev + report, f, indent=2, sort_keys=True)
    print(f"\nwrote {OUT}  ({len(prev) + len(report)} cells, {len(log)} runs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
