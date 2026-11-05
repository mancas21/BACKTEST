"""_xrp_fill_stress.py — fill-model stress for the XRP delta-neutral book.

The audit (2026-10-31, external) flagged the maker fill model as optimistic:
  (a) entries fill at the exact resting price (no adverse cushion),
  (b) the cover loop runs AFTER the entry loop on the same bar, so a lot whose
      cover level sits inside the same bar's range always books its round trip,
  (c) covers fill at the exact cover price with `>=` / `<=`.

This probe does NOT touch the locked engine (code/xrp_neutral_engine.py, sha
pinned in _engine_lock.json). It builds code/xrp_neutral_engine_stress.py by
LITERAL replacements — each must match exactly once or the build aborts — with:

  K_BPS cushion on both maker legs (entry must trade THROUGH the level by k bps),
  same-bar covers banned and COUNTED (they are the ghost round trips).

Runs: original engine (parity check vs artifact fe5c359a22c8dffe) then
k in {0, 1, 2, 5} bps, v2 sizing (init 25, equity_pct 1.0, delta cap 2.0,
leverage 10). Writes code/_xrp_fill_stress_out.json.
"""

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

ENGINE = os.path.join(ROOT, "code", "xrp_neutral_engine.py")
STRESS = os.path.join(ROOT, "code", "xrp_neutral_engine_stress.py")

REPL = [
    # 1. store the entry bar on the lot
    ("lots.append([side * q, fill_px, cover, f])",
     "lots.append([side * q, fill_px, cover, f, t])"),
    # 2. entry touch must trade THROUGH the level by K
    ("touched = (L[t] < px) if side > 0 else (H[t] > px)",
     "touched = (L[t] < px * (1 - K)) if side > 0 else (H[t] > px * (1 + K))"),
    # 3. covers: no same-bar cover (counted), and THROUGH the level by K
    ("""        for lot in list(lots):
            px = lot[2]
            touched = (H[t] >= px) if lot[0] > 0 else (L[t] <= px)""",
     """        for lot in list(lots):
            px = lot[2]
            if lot[4] == t:
                same_bar_covers += 1
                if track is not None:
                    track["same_bar_covers"] = same_bar_covers
                continue
            touched = (H[t] >= px * (1 + K)) if lot[0] > 0 else (L[t] <= px * (1 - K))"""),
    # 4. counter init
    ("grids_built = fills = n_cycles = 0",
     "grids_built = fills = n_cycles = same_bar_covers = 0"),
    # 5. K from env (bps)
    ("MAKER_FEE = 0.0002",
     "MAKER_FEE = 0.0002\nK = float(os.environ.get('XRP_STRESS_K', '0')) / 1e4"),
]


def build():
    src = open(ENGINE, encoding="utf-8").read()
    for old, new in REPL:
        n = src.count(old)
        if n != 1:
            raise SystemExit(f"ABORT: replacement matches {n}x (want 1): {old[:60]!r}")
        src = src.replace(old, new)
    open(STRESS, "w", encoding="utf-8").write(src)
    return src


def load_fresh(path, name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run_engine(module, k_bps):
    import glob as _g
    module.EQUITY_PCT = 1.0
    module.LEVERAGE = 10.0
    klines = os.path.join(ROOT, "data", "binance_klines_15m", "XRPUSDT_15m.csv")
    funding = os.path.join(ROOT, "data", "binance_funding", "XRPUSDT_funding.json")
    raw = pd.read_csv(klines)
    raw.columns = [str(c).strip().lower() for c in raw.columns]
    raw = raw.sort_values("open_ts")
    bars = [(int(r.open_ts), float(r.open), float(r.high), float(r.low),
             float(r.close), float(r.volume)) for r in raw.itertuples(index=False)]
    tr = {}
    eq = module.simulate(
        bars, "XRPUSDT", track=tr, init=25.0,
        trend_band=0.10, stop_atr_mult=0.5, cover_mult=1.0,
        delta_max_pct=2.0, leg_fee=2.0 / 1e4, flat_fee=5.0 / 1e4,
        flat_slip=5.0 / 1e4, funding=True, fund_dir=os.path.dirname(funding))
    cp = np.asarray(tr["closed_pnl"], float)
    pf, win, n_tr = module.metrics(list(cp))
    eqc = np.asarray(tr["eq_curve"], float)
    pk = np.maximum.accumulate(eqc)
    mdd = float(np.max((pk - eqc) / np.maximum(pk, 1e-9)) * 100.0)
    return {
        "k_bps": k_bps,
        "profit_factor": round(float(pf), 4),
        "n_trades": int(n_tr),
        "win_rate": round(float(win), 2),
        "return_pct": round(100.0 * (float(eqc[-1]) / 25.0 - 1.0), 2),
        "max_dd_pct": round(mdd, 2),
        "same_bar_covers_blocked": int(tr.get("same_bar_covers", 0)),
        "final_equity_usdt": round(float(eqc[-1]), 2),
    }


def main():
    build()
    out = []
    base = load_fresh(ENGINE, "xrp_orig_probe")
    r = run_engine(base, 0)
    r["config"] = "ORIGINAL engine (parity vs fe5c359a22c8dffe)"
    out.append(r)
    print(json.dumps(r), flush=True)
    for k in (0, 1, 2, 5):
        os.environ["XRP_STRESS_K"] = str(k)
        m = load_fresh(STRESS, f"xrp_stress_probe_k{k}")
        r = run_engine(m, k)
        r["config"] = f"STRESS ban-same-bar-cover + {k} bps cushion"
        out.append(r)
        print(json.dumps(r), flush=True)
    art = json.load(open(os.path.join(ROOT, "results", "runs", "fe5c359a22c8dffe.json")))
    out.append({"parity_check": {
        "artifact_pf": art["metrics"]["profit_factor"],
        "probe_pf": out[0]["profit_factor"],
        "artifact_ret": art["metrics"]["return_pct"],
        "probe_ret": out[0]["return_pct"],
        "match": abs(art["metrics"]["profit_factor"] - out[0]["profit_factor"]) < 1e-6
                 and abs(art["metrics"]["return_pct"] - out[0]["return_pct"]) < 1e-6}})
    json.dump(out, open(os.path.join(HERE, "_xrp_fill_stress_out.json"), "w"), indent=1)
    print("PARITY:", json.dumps(out[-1]["parity_check"]))


if __name__ == "__main__":
    main()
