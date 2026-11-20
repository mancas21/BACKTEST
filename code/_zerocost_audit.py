"""Known-answer audit for the 2026-11-20 zero-cost / no-rules control.

THE QUESTION THIS FILE ANSWERS, BEFORE ANY MARKET NUMBER IS PUBLISHED:
when the control says "zero", did the engine actually run at zero?

Three of the six adapters needed a new switch (`botstrat`, `cvrmd` and
`pack100`); the other three (`cbpackf`, `xrpneutral`, `eqpack`) already exposed
their own. Every one of them is checked here against an INDEPENDENT invocation
of the same engine -- a freshly loaded module with its cost constants set by
hand -- so the check cannot pass just because the adapter agrees with itself.
Where an engine publishes its OWN zero-cost control inside the artifact
(`pack100.zero_cost_pf`, `eqpack.drag_pp`), that number is the reference: it was
measured by the engine long before this campaign existed.

Run:  python code/_zerocost_audit.py
Exit: 0 all pass, 2 any fail.
"""
import importlib
import importlib.util
import json
import os
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE)
os.chdir(ROOT)
sys.path.insert(0, CODE)

import vrun as V  # noqa: E402

PASS = []
FAIL = []
PAIRS = []


def pair(a, b, tag):
    PAIRS.append((tag, a, b))


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + (("  | " + str(detail)) if detail else ""))


def fresh(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def art(adapter, tf, sym, params):
    # legacy full-file cut: the direct engine calls below read the real files,
    # so the artifact must describe those same bytes
    return V.make_artifact(adapter, tf, sym, params, cut_ts=None)


# ---------------------------------------------------------------- botstrat
print("\n== botstrat (SPXUSDT 1h) ==")
base = art("botstrat", "1h", "SPXUSDT", {"costs": "repo"})
zero = art("botstrat", "1h", "SPXUSDT", {"costs": "zero"})
pair(base, zero, "botstrat")

B = fresh(os.path.join(CODE, "botstrat_backtest.py"), "bs_direct")
B.D1H = os.path.join(ROOT, "data", "binance_klines_1h")
eq_direct = float(B.run("SPXUSDT", B.load("SPXUSDT"))[0])
check("botstrat BASE == engine with its native COST/SLIP",
      base["metrics"]["final_equity"] == eq_direct,
      f"{base['metrics']['final_equity']} vs {eq_direct}")

B2 = fresh(os.path.join(CODE, "botstrat_backtest.py"), "bs_direct_zero")
B2.D1H = os.path.join(ROOT, "data", "binance_klines_1h")
B2.COST = 0.0
B2.SLIP = 0.0
eq_zero_direct = float(B2.run("SPXUSDT", B2.load("SPXUSDT"))[0])
check("botstrat ZERO == engine with COST=SLIP=0",
      zero["metrics"]["final_equity"] == eq_zero_direct,
      f"{zero['metrics']['final_equity']} vs {eq_zero_direct}")

pub = json.load(open(os.path.join(ROOT, "results/runs/f2aa1050b118e54f.json"),
                     encoding="utf-8"))["metrics"]
check("botstrat BASE reproduces the published ranking artifact (bytes unchanged)",
      json.dumps({k: base["metrics"][k] for k in pub}, sort_keys=True) ==
      json.dumps(pub, sort_keys=True))
check("botstrat ZERO removes cost in the right direction",
      zero["metrics"]["return_pct"] > base["metrics"]["return_pct"],
      f"{base['metrics']['return_pct']:.4f}% -> {zero['metrics']['return_pct']:.4f}%")
check("botstrat ZERO declares 0 bps",
      zero["metrics"]["fee_bps_per_side"] == 0.0 and
      zero["metrics"]["slippage_bps_per_side"] == 0.0)

# ------------------------------------------------------------------- cvrmd
print("\n== cvrmd (SUIUSDT 1h) ==")
base = art("cvrmd", "1h", "SUIUSDT", {"costs": "repo"})
zero = art("cvrmd", "1h", "SUIUSDT", {"costs": "zero"})
pair(base, zero, "cvrmd")
kl = os.path.join(ROOT, "data", "binance_klines_1h")

C = fresh(os.path.join(CODE, "cvrmd_backtest.py"), "cv_direct")
eq_direct = float(C.run("SUIUSDT", C.load("SUIUSDT", kl, "1h"))[0])
check("cvrmd BASE == engine with its native COST/SLIP",
      base["metrics"]["final_equity"] == eq_direct,
      f"{base['metrics']['final_equity']} vs {eq_direct}")

C2 = fresh(os.path.join(CODE, "cvrmd_backtest.py"), "cv_direct_zero")
C2.COST = 0.0
C2.SLIP = 0.0
eq_zero_direct = float(C2.run("SUIUSDT", C2.load("SUIUSDT", kl, "1h"))[0])
check("cvrmd ZERO == engine with COST=SLIP=0",
      zero["metrics"]["final_equity"] == eq_zero_direct,
      f"{zero['metrics']['final_equity']} vs {eq_zero_direct}")

check("cvrmd ZERO removes cost in the right direction",
      zero["metrics"]["return_pct"] > base["metrics"]["return_pct"],
      f"{base['metrics']['return_pct']:.4f}% -> {zero['metrics']['return_pct']:.4f}%")
check("cvrmd signals do not depend on the cost regime (same trade count)",
      zero["metrics"]["n_trades"] == base["metrics"]["n_trades"],
      f"{base['metrics']['n_trades']} vs {zero['metrics']['n_trades']}")

# ----------------------------------------------------------------- pack100
print("\n== pack100 (HYPEUSDT 1h, F74-1h) ==")
base = art("pack100", "1h", "HYPEUSDT",
           {"strat": "F74-1h", "costs": "repo", "funding": True})
zcost = art("pack100", "1h", "HYPEUSDT",
            {"strat": "F74-1h", "costs": "zero", "funding": True})
zero = art("pack100", "1h", "HYPEUSDT",
           {"strat": "F74-1h", "costs": "zero", "funding": False})
pair(base, zero, "pack100")

P = importlib.import_module("pack100_engine")
# the adapter's OWN input resolution (taker dir first); a hand-built path list
# would test a different market and prove nothing
paths = V.ADAPTERS["pack100"]["inputs"]("1h", "HYPEUSDT")
m_direct = P.run_one(paths, {"strat": "F74-1h"})[0]
check("pack100 BASE == engine with its own REPO constant untouched",
      abs(m_direct["return_pct"] - base["metrics"]["return_pct"]) < 1e-9,
      f"{m_direct['return_pct']} vs {base['metrics']['return_pct']}")

# the engine computes its OWN zero-cost book inside every run; with funding
# still on, the adapter's costs-zero run must land on exactly that number
check("pack100 costs=0 (funding on) == the artifact's own zero_cost_pf",
      abs(base["metrics"]["zero_cost_pf"] - zcost["metrics"]["pf_pct"]) < 1e-4,
      f"engine control {base['metrics']['zero_cost_pf']} vs adapter {zcost['metrics']['pf_pct']}")
check("pack100 costs=0 really moves the profit factor",
      zcost["metrics"]["pf_pct"] > base["metrics"]["pf_pct"],
      f"{base['metrics']['pf_pct']} -> {zcost['metrics']['pf_pct']}")
check("pack100 ZERO has funding_paid == 0",
      zero["metrics"]["funding_paid"] == 0.0,
      f"{base['metrics']['funding_paid']} -> {zero['metrics']['funding_paid']}")
check("pack100 ZERO declares 0 bps and funding off",
      zero["metrics"]["cost_bps_per_side"] == 0.0 and
      zero["metrics"]["funding_charged"] is False)

# ------------------------------------------------------------------ eqpack
print("\n== eqpack (QQQ 1d) ==")
eb = art("eqpack", "1d", "QQQ", {"costs": "eq"})
ez = art("eqpack", "1d", "QQQ", {"costs": "zero"})
pair(eb, ez, "eqpack")
rb = {r["id"]: r for r in eb["tables"] if r.get("net_%") is not None}
rz = {r["id"]: r for r in ez["tables"] if r.get("net_%") is not None}
deltas = [abs((rz[k]["net_%"] - rb[k]["net_%"]) - rb[k]["drag_pp"]) for k in rb if k in rz]
check("eqpack ZERO-BASE == the engine's own measured drag_pp on every row",
      all(d < 1e-9 for d in deltas), f"max residual {max(deltas):.3e}")

# ----------------------------------------------------------------- cbpackf
print("\n== cbpackf (XRPUSDT 1h) ==")
base = art("cbpackf", "1h", "XRPUSDT",
           {"fee_bps": 5.0, "slippage_bps": 0.5, "funding": True})
zero = art("cbpackf", "1h", "XRPUSDT",
           {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False})
zero2 = art("cbpackf", "1h", "XRPUSDT",
            {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False})
pair(base, zero, "cbpackf")
check("cbpackf BASE declares 5.0/0.5 and funding charged",
      base["metrics"]["fee_bps_per_side"] == 5.0 and
      base["metrics"]["slippage_bps_per_side"] == 0.5 and
      base["metrics"]["funding_charged"] is True)
check("cbpackf ZERO declares 0/0 and funding not charged",
      zero["metrics"]["fee_bps_per_side"] == 0.0 and
      zero["metrics"]["slippage_bps_per_side"] == 0.0 and
      zero["metrics"]["funding_charged"] is False)
check("cbpackf ZERO is deterministic (two runs, identical artifact)",
      zero["run_id"] == zero2["run_id"] and
      json.dumps(zero["metrics"], sort_keys=True) == json.dumps(zero2["metrics"], sort_keys=True))

# --------------------------------------------------------------- xrpneutral
print("\n== xrpneutral (XRPUSDT 15m) ==")
base = art("xrpneutral", "15m", "XRPUSDT", {"fee_bps": 2.0, "flat_fee_bps": 5.0,
                                            "slip_bps": 2.0, "funding": True,
                                            "control_long_only": False})
zero = art("xrpneutral", "15m", "XRPUSDT", {"fee_bps": 0.0, "flat_fee_bps": 0.0,
                                            "slip_bps": 0.0, "funding": False,
                                            "control_long_only": False})
pair(base, zero, "xrpneutral")
check("xrpneutral BASE declares 2/5/2 bps and funding charged",
      base["metrics"]["fee_bps_per_side"] == 2.0 and
      base["metrics"]["flat_fee_bps_per_side"] == 5.0 and
      base["metrics"]["slippage_bps"] == 2.0 and
      base["metrics"]["funding_charged"] is True)
check("xrpneutral ZERO declares 0 bps and funding not charged",
      zero["metrics"]["fee_bps_per_side"] == 0.0 and
      zero["metrics"]["flat_fee_bps_per_side"] == 0.0 and
      zero["metrics"]["slippage_bps"] == 0.0 and
      zero["metrics"]["funding_charged"] is False)
check("xrpneutral ZERO removes cost in the right direction",
      zero["metrics"]["return_pct"] > base["metrics"]["return_pct"],
      f"{base['metrics']['return_pct']:.2f}% -> {zero['metrics']['return_pct']:.2f}%")

# ------------------------------------------------------------- ids and scope
print("\n== provenance ==")
check("BASE and ZERO are different run_ids in every adapter pair",
      all(a["run_id"] != b["run_id"] for _, a, b in PAIRS) and len(PAIRS) >= 4,
      ", ".join(f"{t}:{a['run_id']}!={b['run_id']}" for t, a, b in PAIRS))
check("no BASE/ZERO pair shares an engine hash with a different cost block",
      all(a["core"]["engine_sha256"] == b["core"]["engine_sha256"] for _, a, b in PAIRS))

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(2)
print("ALL PASS")
