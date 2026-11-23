"""Known-answer audit for the 2026-11-23 rows 51-60 zero-cost control.

Before any number is published: did "zero" actually run at zero, and did
"base" run at the published constants? Each adapter is checked against an
INDEPENDENT invocation of its engine -- a freshly loaded module with cost
constants set by hand -- or, for cbpackf, against its declared fields,
in-artifact references and a determinism re-run.

Engine drift (2026-11-21 audit-fix campaign) affected the OLD ranking
artifacts of pack50d, pack100 and qs. Those artifacts are still readable as
inputs; the audit states the drift instead of hiding it. New artifacts minted
here are on current engine bytes and verify bit-for-bit.

Run:  python code/_zerocost_rows51_60_audit.py
Exit: 0 all pass, 2 any fail.
"""
import hashlib
import importlib.util
import json
import os
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE)
os.chdir(ROOT)
sys.path.insert(0, CODE)

import vrun as V  # noqa: E402

PASS, FAIL, PAIRS = [], [], []


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
    return V.make_artifact(adapter, tf, sym, params, cut_ts=None)


def published(rid):
    return json.load(open(os.path.join(ROOT, "results", "runs", str(rid) + ".json"),
                          encoding="utf-8"))


def drift(rid):
    p = published(rid)
    a = p["provenance"]["adapter"]
    return V._sha256_engine(V.ADAPTERS[a]["sources"]) != p["provenance"]["engine_sha256"]


def repro_check(name, base, rid, pub_net, pub_pf, net_key, pf_key):
    p = published(rid)
    grew = [os.path.basename(i["path"]) for i in p.get("inputs") or []
            if i.get("path") and i.get("sha256") and
            hashlib.sha256(open(i["path"], "rb").read()).hexdigest() != i["sha256"]]
    m = base["metrics"]
    same = abs(m[net_key] - pub_net) < 1e-9 and m[pf_key] == pub_pf
    detail = f"grew: {', '.join(grew) if grew else 'none'}; engine drift: {drift(rid)}; " \
             f"{m[net_key]:.4f} vs published {pub_net:.4f}"
    if same:
        check(name + " (exact FIGURE reproduction under current engine bytes)", True, detail)
    else:
        check(name + " (re-measurement: grown inputs and/or engine drift)",
              len(grew) > 0 or drift(rid), detail)


def main():
    # ------------------------------------------------------------- pack50d
    print("\n== pack50d (P08 ETHUSDT 1h; NEW additive switch) ==")
    base = art("pack50d", "1h", "ETHUSDT", {"strat": 8, "costs": "repo", "funding": True})
    zero = art("pack50d", "1h", "ETHUSDT", {"strat": 8, "costs": "zero", "funding": False})
    pair(base, zero, "pack50d-P08")
    P = fresh(os.path.join(CODE, "pack50d_engine.py"), "p50d_direct")
    paths = V.ADAPTERS["pack50d"]["inputs"]("1h", "ETHUSDT")
    m_direct = P.run_one(paths, {"strat": 8})[0]
    check("pack50d BASE == engine with its native REPO block and cost table",
          abs(m_direct["return_pct"] - base["metrics"]["return_pct"]) < 1e-9,
          f"{m_direct['return_pct']} vs {base['metrics']['return_pct']}")
    P2 = fresh(os.path.join(CODE, "pack50d_engine.py"), "p50d_direct_zero")
    P2.REPO = P2.Costs(fee_bps=0.0, slip_bps=0.0)
    P2.SD.costs_for = lambda sym, tf: (0.0, 0.0)
    paths0 = [p for p in paths if not p.endswith(".json")]
    m_zero_direct = P2.run_one(paths0, {"strat": 8})[0]
    check("pack50d ZERO == engine with REPO+cost table zeroed by hand, no funding file",
          abs(m_zero_direct["return_pct"] - zero["metrics"]["return_pct"]) < 1e-9,
          f"{m_zero_direct['return_pct']} vs {zero['metrics']['return_pct']}")
    check("pack50d ZERO declares a zero cost block, no funding, and matches the engine's own zero control",
          zero["metrics"]["costs"] == "zero" and
          zero["metrics"]["fee_bps_per_side"] == 0.0 and
          zero["metrics"]["slip_bps_per_side"] == 0.0 and
          zero["metrics"]["cost_bp_roundtrip"] == 0.0 and
          zero["metrics"]["funding_charged"] is False and
          abs(zero["metrics"]["zero_cost_pf"] - zero["metrics"]["pf_pct"]) < 1e-9,
          f"zero_cost_pf {zero['metrics']['zero_cost_pf']} vs pf_pct {zero['metrics']['pf_pct']}")
    check("pack50d trade count unchanged by the cost regime",
          base["metrics"]["n_trades"] == zero["metrics"]["n_trades"],
          f"{base['metrics']['n_trades']} vs {zero['metrics']['n_trades']}")
    p = published("23010fdc3a262942")
    repro_check("pack50d P08 BASE vs published", base, "23010fdc3a262942",
                p["metrics"]["return_pct"], p["metrics"]["pf_pct"],
                "return_pct", "pf_pct")

    # ------------------------------------------------------------------ qs
    print("\n== qs (four cells) ==")
    QS = [
        ("QS-009", "SUIUSDT", "454e3e81dfa2e59c"),
        ("QS-006", "ETHUSDT", "4b12937872285f0a"),
        ("QS-003", "SOLUSDT", "4f39cf4deaaf88ab"),
    ]
    for strat, sym, rid in QS:
        par = {"strat": strat, "variant": "two-sided"}
        base = art("qs", "1h", sym, {**par, "costs": "repo", "funding": True})
        zero = art("qs", "1h", sym, {**par, "costs": "zero", "funding": False})
        pair(base, zero, f"qs-{strat}-{sym}")
        Q = fresh(os.path.join(CODE, "qs_run.py"), f"q_{strat}_{sym}")
        paths = V.ADAPTERS["qs"]["inputs"]("1h", sym)
        m_direct = Q.run_one(paths, {**par, "tf": "1h"})[0]
        check(f"qs {strat} {sym} BASE == engine with its native ladder",
              abs(m_direct["return_base_pct"] - base["metrics"]["return_base_pct"]) < 1e-9,
              f"{m_direct['return_base_pct']} vs {base['metrics']['return_base_pct']}")
        Q2 = fresh(os.path.join(CODE, "qs_run.py"), f"qz_{strat}_{sym}")
        saved = {ck: dict(c) for ck, c in Q2.E.COSTS.items()}
        Q2.E.COSTS = {ck: {"fee": 0.0, "slip": 0.0, "stop_slip_mult": c["stop_slip_mult"]}
                      for ck, c in saved.items()}
        m_zero_direct = Q2.run_one([p for p in paths if not p.endswith(".json")],
                                   {**par, "tf": "1h"})[0]
        Q2.E.COSTS = saved
        check(f"qs {strat} {sym} ZERO == ladder zeroed by hand, no funding file",
              abs(m_zero_direct["return_base_pct"] - zero["metrics"]["return_base_pct"]) < 1e-9,
              f"{m_zero_direct['return_base_pct']} vs {zero['metrics']['return_base_pct']}")
        mz = zero["metrics"]
        check(f"qs {strat} {sym} ZERO labels, no funding, cost points coincide",
              mz["fee_bps_per_side"] == 0.0 and mz["slippage_bps_per_side"] == 0.0 and
              mz["funding_charged"] is False and mz["costs_primary"] == "zero(0bps RT)" and
              mz["n_funding_events"] == 0 and mz["funding_paid"] == 0.0 and
              mz["return_base_pct"] == mz["return_adverse_pct"] == mz["return_gate_pct"])
        pub = published(rid)
        repro_check(f"qs {strat} {sym} BASE vs published", base, rid,
                    pub["metrics"]["return_base_pct"], pub["metrics"]["pf"],
                    "return_base_pct", "pf")

    # ------------------------------------------------------------- cbpackf
    print("\n== cbpackf (S10 SUI, S10 HYPE, S07 ETH) ==")
    for sym, sid, rid in (("SUIUSDT", "S10", "c1f3df39b37c1d2b"),
                          ("HYPEUSDT", "S10", "44f6ae02bb2fe93c"),
                          ("ETHUSDT", "S07", "2e823fa306c91366")):
        # S07's SIGNAL reads the funding column: at ZERO keep the column
        # (funding_signal=True) but bill nothing (charge_funding=False).
        zpar = {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False}
        if sid == "S07":
            zpar["funding_signal"] = True
        base = art("cbpackf", "1h", sym,
                   {"fee_bps": 5.0, "slippage_bps": 0.5, "funding": True})
        zero = art("cbpackf", "1h", sym, zpar)
        zero2 = art("cbpackf", "1h", sym, dict(zpar))
        pair(base, zero, f"cbpackf-{sid}-{sym}")
        b, z = base["metrics"], zero["metrics"]
        check(f"cbpackf {sid} {sym} BASE declares 5.0/0.5, funding on, settlements present",
              b["fee_bps_per_side"] == 5.0 and b["slippage_bps_per_side"] == 0.5 and
              b["funding_charged"] is True and b["n_settlements"] > 0,
              f"n_settlements {b['n_settlements']}")
        check(f"cbpackf {sid} {sym} ZERO declares 0/0, funding off, zero settlements",
              z["fee_bps_per_side"] == 0.0 and z["slippage_bps_per_side"] == 0.0 and
              z["funding_charged"] is False and z["n_settlements"] == 0)
        check(f"cbpackf {sid} {sym} ZERO deterministic",
              zero["run_id"] == zero2["run_id"] and
              json.dumps(zero["metrics"], sort_keys=True) == json.dumps(zero2["metrics"], sort_keys=True))
        if sid == "S07":
            check("cbpackf S07 ZERO keeps the signal's funding column but bills nothing",
                  z["funding_signal"] is True and z["funding_charged"] is False and
                  z["n_settlements"] == 0 and z["funding_attached"] is True,
                  f"attached {z['funding_attached']}, charged {z['funding_charged']}")
        rb = next(r for r in base["tables"] if r.get("id") == sid)
        rz = next(r for r in zero["tables"] if r.get("id") == sid)
        check(f"cbpackf {sid} {sym} ZERO row above BASE",
              rz["net_%"] > rb["net_%"] and rz["PF"] > rb["PF"],
              f"{rb['net_%']:.4f}% PF {rb['PF']:.4f} -> {rz['net_%']:.4f}% PF {rz['PF']:.4f}")
        if sid == "S07":
            check("cbpackf S07 ZERO keeps the same trade count (signal untouched)",
                  rz["trades"] == rb["trades"],
                  f"{rb['trades']} vs {rz['trades']}")
        pub = published(rid)
        pub_row = next(r for r in pub["tables"] if r.get("id") == sid)
        repro_check(f"cbpackf {sid} {sym} BASE vs published",
                    {"metrics": {"return_pct": rb["net_%"], "profit_factor": rb["PF"]}},
                    rid, pub_row["net_%"], pub_row["PF"], "return_pct", "profit_factor")

    # ------------------------------------------------------------- pack100
    print("\n== pack100 (C44-1h ETHUSDT) ==")
    base = art("pack100", "1h", "ETHUSDT",
               {"strat": "C44-1h", "costs": "repo", "funding": True})
    zcost = art("pack100", "1h", "ETHUSDT",
                {"strat": "C44-1h", "costs": "zero", "funding": True})
    zero = art("pack100", "1h", "ETHUSDT",
               {"strat": "C44-1h", "costs": "zero", "funding": False})
    pair(base, zero, "pack100-C44")
    P1 = fresh(os.path.join(CODE, "pack100_engine.py"), "p100_direct")
    paths = V.ADAPTERS["pack100"]["inputs"]("1h", "ETHUSDT")
    m_direct = P1.run_one(paths, {"strat": "C44-1h"})[0]
    check("pack100 C44 BASE == engine with its own REPO constant untouched",
          abs(m_direct["return_pct"] - base["metrics"]["return_pct"]) < 1e-9,
          f"{m_direct['return_pct']} vs {base['metrics']['return_pct']}")
    check("pack100 C44 costs=0 (funding on) == the artifact's own zero_cost_pf",
          abs(base["metrics"]["zero_cost_pf"] - zcost["metrics"]["pf_pct"]) < 1e-4,
          f"engine control {base['metrics']['zero_cost_pf']} vs adapter {zcost['metrics']['pf_pct']}")
    check("pack100 C44 ZERO declares 0 bps, no funding, funding_paid 0",
          zero["metrics"]["cost_bps_per_side"] == 0.0 and
          zero["metrics"]["funding_charged"] is False and
          zero["metrics"]["funding_paid"] == 0.0)
    pub = published("4eed428adc7d4237")
    repro_check("pack100 C44 BASE vs published", base, "4eed428adc7d4237",
                pub["metrics"]["return_pct"], pub["metrics"]["pf_pct"],
                "return_pct", "pf_pct")

    # -------------------------------------------------------------- dspack
    print("\n== dspack (ds3 SOLUSDT 1h; BASE is repo6x5, ZERO is author) ==")
    base = art("dspack", "1h", "SOLUSDT",
               {"strat": "ds3", "costs": "repo6x5", "window": "full"})
    zero = art("dspack", "1h", "SOLUSDT",
               {"strat": "ds3", "costs": "author", "window": "full"})
    pair(base, zero, "dspack-ds3")
    D = fresh(os.path.join(CODE, "dspack_engine.py"), "dsp_direct")
    paths = V.ADAPTERS["dspack"]["inputs"]("1h", "SOLUSDT")
    for regime, par in (("BASE", {"strat": "ds3", "costs": "repo6x5", "window": "full"}),
                        ("ZERO", {"strat": "ds3", "costs": "author", "window": "full"})):
        row = D.run_suite(paths, par)["tables"][0]
        target = base if regime == "BASE" else zero
        check(f"dspack ds3 {regime} == engine with the same preset",
              abs(row["ret_pct"] - target["metrics"]["return_pct"]) < 1e-9,
              f"{row['ret_pct']} vs {target['metrics']['return_pct']}")
    t = base["tables"][0]
    check("dspack ds3 BASE's in-artifact zero re-score == author headline",
          abs(t["ret_zero_pct"] - zero["metrics"]["return_pct"]) < 1e-9,
          f"ret_zero_pct {t['ret_zero_pct']} vs author {zero['metrics']['return_pct']}")
    check("dspack ds3 BASE pays real fees and lands below the author headline",
          t["fees_charged"] > 0.0 and t["ret_pct"] < zero["metrics"]["return_pct"],
          f"fees {t['fees_charged']:.2f}, {t['ret_pct']:.2f}% vs {zero['metrics']['return_pct']:.2f}%")
    check("dspack ds3 trade count unchanged by the cost regime",
          t["n_trades"] == zero["metrics"]["n_trades"],
          f"{t['n_trades']} vs {zero['metrics']['n_trades']}")
    pub = published("9513a4e7e7fc11b8")
    repro_check("dspack ds3 BASE vs published", base, "9513a4e7e7fc11b8",
                pub["metrics"]["return_pct"], pub["metrics"]["profit_factor"],
                "return_pct", "profit_factor")

    # --------------------------------------------------------------- mpv3
    print("\n== mpv3 (PORTFOLIO 1h, S10) ==")
    par = {"strat": "MP-V3-S10", "window": "full"}
    base = art("mpv3", "1h", "PORTFOLIO", {**par, "costs": "repo"})
    zero = art("mpv3", "1h", "PORTFOLIO", {**par, "costs": "zero"})
    pair(base, zero, "mpv3-S10")
    M = fresh(os.path.join(CODE, "mpv3_engine.py"), "mpv3_direct")
    paths = V.ADAPTERS["mpv3"]["inputs"]("1h", "PORTFOLIO")
    m_direct = M.run_mpv3(paths, {**par, "costs": "repo"})[0]
    check("mpv3 BASE == engine with its native repo preset",
          abs(m_direct["return_pct"] - base["metrics"]["return_pct"]) < 1e-9,
          f"{m_direct['return_pct']} vs {base['metrics']['return_pct']}")
    M2 = fresh(os.path.join(CODE, "mpv3_engine.py"), "mpv3_direct_zero")
    m_zero_direct = M2.run_mpv3(paths, {**par, "costs": "zero"})[0]
    check("mpv3 ZERO == engine with its native zero preset",
          abs(m_zero_direct["return_pct"] - zero["metrics"]["return_pct"]) < 1e-9,
          f"{m_zero_direct['return_pct']} vs {zero['metrics']['return_pct']}")
    check("mpv3 ZERO declares 0 fee/slip/RT and agrees with the engine's own cost_drag_pp",
          zero["metrics"]["costs"] == "zero" and
          zero["metrics"]["fee_bps"] == 0.0 and
          zero["metrics"]["slip_bps"] == 0.0 and
          zero["metrics"]["rt_bps"] == 0.0 and
          abs((zero["metrics"]["return_pct"] - base["metrics"]["return_pct"]) -
              base["metrics"]["cost_drag_pp"]) < 2e-4,
          f"cost_drag_pp {base['metrics']['cost_drag_pp']:.4f} pp")
    pub = published("e36bd0df664d7db5")
    repro_check("mpv3 BASE vs published", base, "e36bd0df664d7db5",
                pub["metrics"]["return_pct"], pub["metrics"]["profit_factor"],
                "return_pct", "profit_factor")

    # -------------------------------------------------------- ids and scope
    print("\n== provenance ==")
    check("BASE and ZERO differ in every regime pair",
          all(a["run_id"] != b["run_id"] for _, a, b in PAIRS) and len(PAIRS) >= 10,
          f"{len(PAIRS)} pairs, all distinct")
    check("every BASE/ZERO pair shares the same engine hash",
          all(a["core"]["engine_sha256"] == b["core"]["engine_sha256"] for _, a, b in PAIRS))

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("FAILED:", FAIL)
        sys.exit(2)
    print("ALL PASS")


if __name__ == "__main__":
    main()
