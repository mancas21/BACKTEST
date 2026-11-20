"""Known-answer audit for the 2026-11-20 rows 11-20 zero-cost control.

THE QUESTION THIS FILE ANSWERS, BEFORE ANY NUMBER IS PUBLISHED: when the
control says "zero", did the engine actually run at zero? And when it says
"base", did the engine run at its published constants?

Every adapter is checked against an INDEPENDENT invocation of the same
engine -- a freshly loaded module with its cost constants set BY HAND -- so
the check cannot pass just because the adapter agrees with itself. Where an
engine publishes its OWN zero-cost reference inside the artifact (`pf_zero`
for smqe, `profit_factor_zero` for cand7, `drag_pp` for eqpack), that number
is the reference. Where the ranking's input bytes did not change since
2026-10-31, the BASE artifact must reproduce the published figure exactly.

Run:  python code/_zerocost_rows11_20_audit.py
Exit: 0 all pass, 2 any fail.
"""
import importlib
import importlib.util
import json
import os
import re
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE)
os.chdir(ROOT)
sys.path.insert(0, CODE)

import vrun as V  # noqa: E402

PASS, FAIL, PAIRS = [], [], []
_RID = re.compile(r"^[0-9a-f]{16}$")


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + (("  | " + str(detail)) if detail else ""))


def pair(a, b, tag):
    PAIRS.append((tag, a, b))


def fresh(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def art(adapter, tf, sym, params):
    # legacy full-file cut: the direct engine calls below read the real
    # files, so the artifact must describe those same bytes
    return V.make_artifact(adapter, tf, sym, params, cut_ts=None)


# ---------------------------------------------------------------- botstrat
print("\n== botstrat (4 symbols x 1h) ==")
BS_PUB = {"AVAXUSDT": ("f0b5da9763ca3402", 50.20),
          "ETHUSDT": ("6709e6de73b6b6d4", 27.88),
          "SOLUSDT": ("fb995a742183a68b", 37.39),
          "BTCUSDT": ("a4f19ccd7cbc61bd", 19.75)}
BS_UNCHANGED = {"AVAXUSDT", "SOLUSDT"}   # inputs byte-identical since the ranking
for sym in BS_PUB:
    base = art("botstrat", "1h", sym, {"costs": "repo"})
    zero = art("botstrat", "1h", sym, {"costs": "zero"})
    pair(base, zero, "botstrat-" + sym)
    B = fresh(os.path.join(CODE, "botstrat_backtest.py"), "bs_" + sym)
    B.D1H = os.path.join(ROOT, "data", "binance_klines_1h")
    eq_direct = float(B.run(sym, B.load(sym))[0])
    check(f"botstrat {sym} BASE == engine with its native COST/SLIP",
          base["metrics"]["final_equity"] == eq_direct,
          f"{base['metrics']['final_equity']} vs {eq_direct}")
    B2 = fresh(os.path.join(CODE, "botstrat_backtest.py"), "bsz_" + sym)
    B2.D1H = os.path.join(ROOT, "data", "binance_klines_1h")
    B2.COST = 0.0
    B2.SLIP = 0.0
    eq_zero_direct = float(B2.run(sym, B2.load(sym))[0])
    check(f"botstrat {sym} ZERO == engine with COST=SLIP=0",
          zero["metrics"]["final_equity"] == eq_zero_direct,
          f"{zero['metrics']['final_equity']} vs {eq_zero_direct}")
    check(f"botstrat {sym} ZERO declares 0 bps and no funding",
          zero["metrics"]["fee_bps_per_side"] == 0.0 and
          zero["metrics"]["slippage_bps_per_side"] == 0.0 and
          zero["metrics"]["funding_charged"] is False)
    if sym in BS_UNCHANGED:
        check(f"botstrat {sym} BASE reproduces the published net (bytes unchanged)",
              abs(base["metrics"]["return_pct"] - BS_PUB[sym][1]) < 0.005,
              f"{base['metrics']['return_pct']:.4f} vs published {BS_PUB[sym][1]}")
    else:
        check(f"botstrat {sym} BASE is a re-measurement (input grew; must differ "
              f"from the published net)",
              abs(base["metrics"]["return_pct"] - BS_PUB[sym][1]) > 0.005,
              f"{base['metrics']['return_pct']:.4f} vs published {BS_PUB[sym][1]}")

# ------------------------------------------------------------------- cvrmd
print("\n== cvrmd (SOLUSDT 1h) ==")
base = art("cvrmd", "1h", "SOLUSDT", {"costs": "repo"})
zero = art("cvrmd", "1h", "SOLUSDT", {"costs": "zero"})
pair(base, zero, "cvrmd")
kl = os.path.join(ROOT, "data", "binance_klines_1h")
C = fresh(os.path.join(CODE, "cvrmd_backtest.py"), "cv_direct_sol")
eq_direct = float(C.run("SOLUSDT", C.load("SOLUSDT", kl, "1h"))[0])
check("cvrmd SOL BASE == engine with its native COST/SLIP",
      base["metrics"]["final_equity"] == eq_direct,
      f"{base['metrics']['final_equity']} vs {eq_direct}")
C2 = fresh(os.path.join(CODE, "cvrmd_backtest.py"), "cv_direct_sol_zero")
C2.COST = 0.0
C2.SLIP = 0.0
eq_zero_direct = float(C2.run("SOLUSDT", C2.load("SOLUSDT", kl, "1h"))[0])
check("cvrmd SOL ZERO == engine with COST=SLIP=0",
      zero["metrics"]["final_equity"] == eq_zero_direct,
      f"{zero['metrics']['final_equity']} vs {eq_zero_direct}")
check("cvrmd SOL ZERO declares 0 bps",
      zero["metrics"]["fee_bps_per_side"] == 0.0 and
      zero["metrics"]["slippage_bps_per_side"] == 0.0)
check("cvrmd SOL signals do not depend on the cost regime (same trade count)",
      zero["metrics"]["n_trades"] == base["metrics"]["n_trades"],
      f"{base['metrics']['n_trades']} vs {zero['metrics']['n_trades']}")

# ---------------------------------------------------------------------- qs
print("\n== qs (QS-001 HYPEUSDT 1h) ==")
base = art("qs", "1h", "HYPEUSDT",
           {"strat": "QS-001", "variant": "two-sided", "costs": "repo", "funding": True})
zero = art("qs", "1h", "HYPEUSDT",
           {"strat": "QS-001", "variant": "two-sided", "costs": "zero", "funding": False})
pair(base, zero, "qs")

Q = fresh(os.path.join(CODE, "qs_run.py"), "qs_direct")
paths = V.ADAPTERS["qs"]["inputs"]("1h", "HYPEUSDT")
m_direct = Q.run_one(paths, {"strat": "QS-001", "variant": "two-sided", "tf": "1h"})[0]
check("qs BASE == engine with its native COSTS ladder",
      abs(m_direct["return_base_pct"] - base["metrics"]["return_base_pct"]) < 1e-9,
      f"{m_direct['return_base_pct']} vs {base['metrics']['return_base_pct']}")

Q2 = fresh(os.path.join(CODE, "qs_run.py"), "qs_direct_zero")
saved = {ck: dict(c) for ck, c in Q2.E.COSTS.items()}
Q2.E.COSTS = {ck: {"fee": 0.0, "slip": 0.0, "stop_slip_mult": c["stop_slip_mult"]}
              for ck, c in saved.items()}
paths0 = [p for p in paths if not p.endswith(".json")]
m_zero_direct = Q2.run_one(paths0, {"strat": "QS-001", "variant": "two-sided", "tf": "1h"})[0]
Q2.E.COSTS = saved
check("qs ZERO == engine with the COSTS ladder zeroed by hand and no funding file",
      abs(m_zero_direct["return_base_pct"] - zero["metrics"]["return_base_pct"]) < 1e-9,
      f"{m_zero_direct['return_base_pct']} vs {zero['metrics']['return_base_pct']}")
check("qs ZERO declares 0 bps, funding off, zero label",
      zero["metrics"]["fee_bps_per_side"] == 0.0 and
      zero["metrics"]["slippage_bps_per_side"] == 0.0 and
      zero["metrics"]["funding_charged"] is False and
      zero["metrics"]["costs_primary"] == "zero(0bps RT)")
check("qs BASE declares the published 5.0/2.0 ladder and funding on",
      base["metrics"]["fee_bps_per_side"] == 5.0 and
      base["metrics"]["slippage_bps_per_side"] == 2.0 and
      base["metrics"]["funding_charged"] is True)
check("qs ZERO funding events are zero",
      zero["metrics"]["n_funding_events"] == 0 and zero["metrics"]["funding_paid"] == 0.0)
mz = zero["metrics"]
check("qs ZERO four cost points coincide (base == adverse == gate)",
      mz["return_base_pct"] == mz["return_adverse_pct"] == mz["return_gate_pct"],
      f"{mz['return_base_pct']} / {mz['return_adverse_pct']} / {mz['return_gate_pct']}")
pub_qs = json.load(open(os.path.join(ROOT, "results/runs/41ae8c79fe005541.json"),
                        encoding="utf-8"))["metrics"]
check("qs BASE reproduces the published ranking net and PF exactly",
      base["metrics"]["return_base_pct"] == pub_qs["return_base_pct"] and
      base["metrics"]["pf"] == pub_qs["pf"],
      f"{base['metrics']['return_base_pct']} / {base['metrics']['pf']}")

# ------------------------------------------------------------------- cand7
print("\n== cand7 (C7 SOLUSDT 1h) ==")
base = art("cand7", "1h", "SOLUSDT", {"cand": 7, "costs": "repo", "funding": True})
zero = art("cand7", "1h", "SOLUSDT", {"cand": 7, "costs": "zero", "funding": False})
pair(base, zero, "cand7")

CD = fresh(os.path.join(CODE, "cand7_engine.py"), "cand7_direct")
m_direct = CD.run_one(V.ADAPTERS["cand7"]["inputs"]("1h", "SOLUSDT"), {"cand": 7})[0]
check("cand7 BASE == engine with its native BASE block",
      abs(m_direct["return_pct"] - base["metrics"]["return_pct"]) < 1e-9,
      f"{m_direct['return_pct']} vs {base['metrics']['return_pct']}")
pub_c7 = json.load(open(os.path.join(ROOT, "results/runs/f9fd115fb70b6e8e.json"),
                        encoding="utf-8"))["metrics"]
check("cand7 BASE reproduces the published ranking net and PF exactly",
      base["metrics"]["return_pct"] == pub_c7["return_pct"] and
      base["metrics"]["profit_factor"] == pub_c7["profit_factor"],
      f"{base['metrics']['return_pct']} / {base['metrics']['profit_factor']}")

CD2 = fresh(os.path.join(CODE, "cand7_engine.py"), "cand7_direct_zero")
CD2.BASE = CD2.C.Costs(0.0, 0.0)
_orig = CD2._run
import numpy as np


def _zf(f):
    if f is None:
        return None
    if isinstance(f, list):
        return [_zf(x) for x in f]
    a, b = f
    if isinstance(a, tuple) and isinstance(b, tuple):
        return (_zf(a), _zf(b))
    return (a, b * 0.0)


def _run_zf(plan, c, funding, **kw):
    zero_block = (float(getattr(c, "fee_bps", 1.0)) == 0.0
                  and float(getattr(c, "slip_bps", 1.0)) == 0.0)
    return _orig(plan, c, _zf(funding) if zero_block else funding, **kw)


CD2._run = _run_zf
m_zero_direct = CD2.run_one(V.ADAPTERS["cand7"]["inputs"]("1h", "SOLUSDT"),
                            {"cand": 7})[0]
check("cand7 ZERO == engine with BASE=(0,0) and zeroed funding rates, by hand",
      abs(m_zero_direct["return_pct"] - zero["metrics"]["return_pct"]) < 1e-9,
      f"{m_zero_direct['return_pct']} vs {zero['metrics']['return_pct']}")
check("cand7 ZERO internal control matches the headline (res == res_zero)",
      zero["metrics"]["return_pct"] == zero["metrics"]["return_zero_pct"] and
      zero["metrics"]["pf_pct"] == zero["metrics"]["profit_factor_zero"])
check("cand7 ZERO declares 0 bps, funding cash flow off, signal input kept",
      zero["metrics"]["fee_bps_per_side"] == 0.0 and
      zero["metrics"]["slippage_bps_per_side"] == 0.0 and
      zero["metrics"]["funding_charged"] is False and
      zero["metrics"]["funding_signal_input"] is True)
check("cand7 ZERO fees and funding cash flow are zero",
      zero["metrics"]["fees_paid"] == 0.0 and
      zero["metrics"]["funding_net_usdt"] == 0.0)
check("cand7 BASE declares the published 5.0/2.0 block and funding on",
      base["metrics"]["fee_bps_per_side"] == 5.0 and
      base["metrics"]["slippage_bps_per_side"] == 2.0 and
      base["metrics"]["funding_charged"] is True)

# -------------------------------------------------------------------- smqe
print("\n== smqe (SOLUSDT 1h) ==")
base = art("smqe", "1h", "SOLUSDT", {"cost_mode": "repo", "funding": True})
zero = art("smqe", "1h", "SOLUSDT", {"cost_mode": "zero", "funding": False})
pair(base, zero, "smqe")

SM = fresh(os.path.join(CODE, "smqe_engine.py"), "smqe_direct")
m_direct = SM.run_symbol([os.path.join(ROOT, "data", "binance_klines_1h", "SOLUSDT_1h.csv")],
                         {"cost_mode": "repo", "tf": "1h"})
check("smqe BASE == engine with its native repo constants",
      abs(m_direct["metrics"]["return_pct"] - base["metrics"]["return_pct"]) < 1e-9,
      f"{m_direct['metrics']['return_pct']} vs {base['metrics']['return_pct']}")

SM2 = fresh(os.path.join(CODE, "smqe_engine.py"), "smqe_direct_zero")
SM2.PINE["fund_rate_8h_pct"] = 0.0
m_zero_direct = SM2.run_symbol([os.path.join(ROOT, "data", "binance_klines_1h", "SOLUSDT_1h.csv")],
                               {"cost_mode": "zero", "tf": "1h"})
check("smqe ZERO == engine with cost_mode=zero and the funding rate zeroed by hand",
      abs(m_zero_direct["metrics"]["return_pct"] - zero["metrics"]["return_pct"]) < 1e-9,
      f"{m_zero_direct['metrics']['return_pct']} vs {zero['metrics']['return_pct']}")
check("smqe ZERO declares funding off and zero funding cash",
      zero["metrics"]["funding_charged"] is False and
      zero["metrics"]["funding_paid_usd"] == 0.0)
check("smqe ZERO fees are zero and pf_zero matches the independent recompute",
      zero["metrics"]["fees"] == 0.0 and
      abs(zero["metrics"]["pf_zero"] - m_zero_direct["metrics"]["pf_zero"]) < 1e-9,
      f"pf_zero {zero['metrics']['pf_zero']} vs direct {m_zero_direct['metrics']['pf_zero']}")
check("smqe BASE declares the repo 5.0/0.5 block and funding on",
      base["metrics"]["fee_bps_per_side"] == 5.0 and
      base["metrics"]["slip_bps_per_side"] == 0.5 and
      base["metrics"]["funding_charged"] is True)

# ------------------------------------------------------------------ eqpack
print("\n== eqpack (QQQ 1d, S01 + S05 rows) ==")
eb = art("eqpack", "1d", "QQQ", {"costs": "eq"})
ez = art("eqpack", "1d", "QQQ", {"costs": "zero"})
pair(eb, ez, "eqpack")
for sid, pub_net, pub_pf in (("S01", 24.18, 1.427), ("S05", 11.43, 1.411)):
    rb = {r["id"]: r for r in eb["tables"] if r.get("net_%") is not None}[sid]
    rz = {r["id"]: r for r in ez["tables"] if r.get("net_%") is not None}[sid]
    check(f"eqpack {sid} ZERO-BASE == the engine's own measured drag_pp",
          abs((rz["net_%"] - rb["net_%"]) - rb["drag_pp"]) < 1e-9,
          f"residual {(rz['net_%'] - rb['net_%']) - rb['drag_pp']:.3e}")
    check(f"eqpack {sid} BASE reproduces the published ranking row exactly",
          abs(rb["net_%"] - pub_net) < 0.005 and abs(rb["PF"] - pub_pf) < 0.0005,
          f"{rb['net_%']:.4f} / {rb['PF']:.4f}")

# ------------------------------------------------------------- ids, scope
print("\n== provenance ==")
check("BASE and ZERO are different run_ids in every adapter pair",
      all(a["run_id"] != b["run_id"] for _, a, b in PAIRS) and len(PAIRS) >= 6,
      f"{len(PAIRS)} pairs, all distinct")
check("every BASE/ZERO pair shares the same engine hash",
      all(a["core"]["engine_sha256"] == b["core"]["engine_sha256"] for _, a, b in PAIRS))

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(2)
print("ALL PASS")
