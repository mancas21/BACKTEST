"""Known-answer audit for the 2026-11-23 rows 61-70 zero-cost control.

Before any number is published: did "zero" run at zero, and did "base" run at
the published constants? Independent fresh-module recomputation for every
adapter; cbpackf additionally uses its declared fields, in-artifact references
and a determinism re-run. Engine drift in old ranking artifacts (qs/pack100,
2026-11-21 audit-fix) is declared, not hidden.

Run:  python code/_zerocost_rows61_70_audit.py ; exit 0 all pass, 2 any fail.
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
    detail = f"grew: {', '.join(grew) if grew else 'none'}; drift: {drift(rid)}; " \
             f"{m[net_key]:.4f} vs {pub_net:.4f}"
    if same:
        check(name + " (exact FIGURE reproduction under current bytes)", True, detail)
    else:
        check(name + " (re-measurement: grown inputs and/or engine drift)",
              len(grew) > 0 or drift(rid), detail)


def main():
    # ------------------------------------------------------------------ qs
    print("\n== qs (five cells, one at 15m long-only) ==")
    QS = [
        ("QS-003", "two-sided", "1h", "JUPUSDT", "a4cfe2e19afc2b4b"),
        ("QS-002", "two-sided", "1h", "JUPUSDT", "bb91d2ee92a92228"),
        ("QS-001", "long-only", "15m", "SOLUSDT", "e424e72cb0d128a3"),
        ("QS-001", "two-sided", "1h", "JUPUSDT", "31a03e0d945babe4"),
        ("QS-004", "two-sided", "1h", "JUPUSDT", "59384c79e117aa2d"),
    ]
    for strat, variant, tf, sym, rid in QS:
        par = {"strat": strat, "variant": variant}
        base = art("qs", tf, sym, {**par, "costs": "repo", "funding": True})
        zero = art("qs", tf, sym, {**par, "costs": "zero", "funding": False})
        pair(base, zero, f"qs-{strat}-{sym}-{tf}")
        Q = fresh(os.path.join(CODE, "qs_run.py"), f"q_{strat}_{sym}_{tf}")
        paths = V.ADAPTERS["qs"]["inputs"](tf, sym)
        m_direct = Q.run_one(paths, {**par, "tf": tf})[0]
        check(f"qs {strat} {sym} {tf} BASE == engine with its native ladder",
              abs(m_direct["return_base_pct"] - base["metrics"]["return_base_pct"]) < 1e-9,
              f"{m_direct['return_base_pct']} vs {base['metrics']['return_base_pct']}")
        Q2 = fresh(os.path.join(CODE, "qs_run.py"), f"qz_{strat}_{sym}_{tf}")
        saved = {ck: dict(c) for ck, c in Q2.E.COSTS.items()}
        Q2.E.COSTS = {ck: {"fee": 0.0, "slip": 0.0, "stop_slip_mult": c["stop_slip_mult"]}
                      for ck, c in saved.items()}
        m_zero_direct = Q2.run_one([p for p in paths if not p.endswith(".json")],
                                   {**par, "tf": tf})[0]
        Q2.E.COSTS = saved
        check(f"qs {strat} {sym} {tf} ZERO == ladder zeroed by hand, no funding file",
              abs(m_zero_direct["return_base_pct"] - zero["metrics"]["return_base_pct"]) < 1e-9,
              f"{m_zero_direct['return_base_pct']} vs {zero['metrics']['return_base_pct']}")
        mz = zero["metrics"]
        check(f"qs {strat} {sym} {tf} ZERO labels, no funding, cost points coincide",
              mz["fee_bps_per_side"] == 0.0 and mz["slippage_bps_per_side"] == 0.0 and
              mz["funding_charged"] is False and mz["costs_primary"] == "zero(0bps RT)" and
              mz["n_funding_events"] == 0 and mz["funding_paid"] == 0.0 and
              mz["return_base_pct"] == mz["return_adverse_pct"] == mz["return_gate_pct"])
        pub = published(rid)
        repro_check(f"qs {strat} {sym} {tf} BASE vs published", base, rid,
                    pub["metrics"]["return_base_pct"], pub["metrics"]["pf"],
                    "return_base_pct", "pf")

    # ------------------------------------------------------------- cbpackf
    print("\n== cbpackf (S02 and S03 HYPEUSDT 1h, same ranking artifact) ==")
    for sid, rid in (("S02", "44f6ae02bb2fe93c"), ("S03", "44f6ae02bb2fe93c")):
        base = art("cbpackf", "1h", "HYPEUSDT",
                   {"fee_bps": 5.0, "slippage_bps": 0.5, "funding": True})
        zero = art("cbpackf", "1h", "HYPEUSDT",
                   {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False})
        zero2 = art("cbpackf", "1h", "HYPEUSDT",
                    {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False})
        pair(base, zero, f"cbpackf-{sid}-HYPE")
        b, z = base["metrics"], zero["metrics"]
        check(f"cbpackf {sid} BASE declares 5.0/0.5, funding on, settlements",
              b["fee_bps_per_side"] == 5.0 and b["slippage_bps_per_side"] == 0.5 and
              b["funding_charged"] is True and b["n_settlements"] > 0,
              f"n_settlements {b['n_settlements']}")
        check(f"cbpackf {sid} ZERO declares 0/0, funding off, zero settlements",
              z["fee_bps_per_side"] == 0.0 and z["slippage_bps_per_side"] == 0.0 and
              z["funding_charged"] is False and z["n_settlements"] == 0)
        check(f"cbpackf {sid} ZERO deterministic",
              zero["run_id"] == zero2["run_id"] and
              json.dumps(zero["metrics"], sort_keys=True) == json.dumps(zero2["metrics"], sort_keys=True))
        rb = next(r for r in base["tables"] if r.get("id") == sid)
        rz = next(r for r in zero["tables"] if r.get("id") == sid)
        check(f"cbpackf {sid} ZERO row above BASE",
              rz["net_%"] > rb["net_%"] and rz["PF"] > rb["PF"],
              f"{rb['net_%']:.4f}% PF {rb['PF']:.4f} -> {rz['net_%']:.4f}% PF {rz['PF']:.4f}")
        p = published(rid)
        pr = next(r for r in p["tables"] if r.get("id") == sid)
        repro_check(f"cbpackf {sid} BASE vs published",
                    {"metrics": {"return_pct": rb["net_%"], "profit_factor": rb["PF"]}},
                    rid, pr["net_%"], pr["PF"], "return_pct", "profit_factor")

    # ------------------------------------------------------------- dspack2
    print("\n== dspack2 (ds7 SPXUSDT 1h; BASE repo6x5 -> ZERO author) ==")
    base = art("dspack2", "1h", "SPXUSDT",
               {"strat": "ds7", "costs": "repo6x5", "window": "full"})
    zero = art("dspack2", "1h", "SPXUSDT",
               {"strat": "ds7", "costs": "author", "window": "full"})
    pair(base, zero, "dspack2-ds7")
    D = fresh(os.path.join(CODE, "dspack2_engine.py"), "dsp2_direct")
    paths = V.ADAPTERS["dspack2"]["inputs"]("1h", "SPXUSDT")
    for regime, par in (("BASE", {"strat": "ds7", "costs": "repo6x5", "window": "full"}),
                        ("ZERO", {"strat": "ds7", "costs": "author", "window": "full"})):
        row = D.run_suite(paths, par)["tables"][0]
        target = base if regime == "BASE" else zero
        check(f"dspack2 ds7 {regime} == engine with that preset",
              abs(row["ret_pct"] - target["metrics"]["return_pct"]) < 1e-9,
              f"{row['ret_pct']} vs {target['metrics']['return_pct']}")
    t = base["tables"][0]
    check("dspack2 ds7 BASE's zero re-score == author headline, fees real",
          abs(t["ret_zero_pct"] - zero["metrics"]["return_pct"]) < 1e-9 and
          t["fees_charged"] > 0 and t["ret_pct"] < zero["metrics"]["return_pct"],
          f"fees {t['fees_charged']:.2f}, zero re-score {t['ret_zero_pct']:.4f}")
    check("dspack2 ds7 trade count unchanged by cost regime",
          t["n_trades"] == zero["metrics"]["n_trades"],
          f"{t['n_trades']} vs {zero['metrics']['n_trades']}")
    repro_check("dspack2 ds7 BASE vs published", base, "b898dfed4e6f2395",
                published("b898dfed4e6f2395")["metrics"]["return_pct"],
                published("b898dfed4e6f2395")["metrics"]["profit_factor"],
                "return_pct", "profit_factor")

    # -------------------------------------------------------------- dspack
    print("\n== dspack (ds5 LINKUSDT 1h; author == zero, with costed re-run) ==")
    par = {"strat": "ds5", "costs": "author", "window": "full"}
    base = art("dspack", "1h", "LINKUSDT", par)
    costed = art("dspack", "1h", "LINKUSDT",
                 {"strat": "ds5", "costs": "repo6x5", "window": "full"})
    D1 = fresh(os.path.join(CODE, "dspack_engine.py"), "dsp_direct")
    p1 = V.ADAPTERS["dspack"]["inputs"]("1h", "LINKUSDT")
    row = D1.run_suite(p1, par)["tables"][0]
    check("dspack ds5 BASE == engine at its own author (zero) constants",
          abs(row["ret_pct"] - base["metrics"]["return_pct"]) < 1e-9,
          f"{row['ret_pct']} vs {base['metrics']['return_pct']}")
    t = costed["tables"][0]
    check("dspack ds5 COSTED re-score at zero == author headline, fees real",
          abs(t["ret_zero_pct"] - base["metrics"]["return_pct"]) < 1e-9 and
          t["fees_charged"] > 0 and t["ret_pct"] < base["metrics"]["return_pct"],
          f"fees {t['fees_charged']:.2f}, ret {t['ret_pct']:.2f}%")
    check("dspack ds5 same trade count across regimes",
          t["n_trades"] == base["metrics"]["n_trades"],
          f"{t['n_trades']} vs {base['metrics']['n_trades']}")
    pub = published("10c772d303374d26")
    repro_check("dspack ds5 BASE vs published", base, "10c772d303374d26",
                pub["metrics"]["return_pct"], pub["metrics"]["profit_factor"],
                "return_pct", "profit_factor")

    # ------------------------------------------------------------- pack100
    print("\n== pack100 (F75-15m SUIUSDT) ==")
    base = art("pack100", "15m", "SUIUSDT",
               {"strat": "F75-15m", "costs": "repo", "funding": True})
    zcost = art("pack100", "15m", "SUIUSDT",
                {"strat": "F75-15m", "costs": "zero", "funding": True})
    zero = art("pack100", "15m", "SUIUSDT",
               {"strat": "F75-15m", "costs": "zero", "funding": False})
    pair(base, zero, "pack100-F75-15m")
    P1 = fresh(os.path.join(CODE, "pack100_engine.py"), "p100_direct")
    paths = V.ADAPTERS["pack100"]["inputs"]("15m", "SUIUSDT")
    m_direct = P1.run_one(paths, {"strat": "F75-15m"})[0]
    check("pack100 F75 BASE == engine with its own REPO constant",
          abs(m_direct["return_pct"] - base["metrics"]["return_pct"]) < 1e-9,
          f"{m_direct['return_pct']} vs {base['metrics']['return_pct']}")
    check("pack100 costs=0 (funding on) == the artifact's own zero_cost_pf",
          abs(base["metrics"]["zero_cost_pf"] - zcost["metrics"]["pf_pct"]) < 1e-4,
          f"{base['metrics']['zero_cost_pf']} vs {zcost['metrics']['pf_pct']}")
    check("pack100 ZERO declares 0 bps, no funding, zero funding_paid",
          zero["metrics"]["cost_bps_per_side"] == 0.0 and
          zero["metrics"]["funding_charged"] is False and
          zero["metrics"]["funding_paid"] == 0.0)
    pub = published("213714abb98e9fcb")
    repro_check("pack100 F75 BASE vs published", base, "213714abb98e9fcb",
                pub["metrics"]["return_pct"], pub["metrics"]["pf_pct"],
                "return_pct", "pf_pct")

    # -------------------------------------------------------- ids and scope
    print("\n== provenance ==")
    check("BASE and ZERO differ in every regime pair",
          all(a["run_id"] != b["run_id"] for _, a, b in PAIRS) and len(PAIRS) >= 9,
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
