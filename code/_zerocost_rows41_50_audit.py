"""Known-answer audit for the 2026-11-23 rows 41-50 zero-cost control.

Before any number is published: when the control says "zero", did the engine
actually run at zero? Every adapter is checked against an INDEPENDENT
invocation of the same engine -- a freshly loaded module with its cost
constants set BY HAND -- or, for cbpackf, against its own declared cost fields,
in-artifact references and a determinism re-run. Reproduction is exact when
the ranking inputs still hash to the stored bytes; a difference is accepted
only when an input file really grew (declared in the pre-registration).

Run:  python code/_zerocost_rows41_50_audit.py
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


def bytes_unchanged(rid):
    a = json.load(open(os.path.join(ROOT, "results", "runs", str(rid) + ".json"),
                       encoding="utf-8"))
    out = []
    for i in a.get("inputs") or []:
        path, sha = i.get("path"), i.get("sha256")
        if path and sha:
            out.append((os.path.basename(path),
                        hashlib.sha256(open(path, "rb").read()).hexdigest() == sha))
    return out


def repro_check(name, base, rid, pub_net, pub_pf, net_key, pf_key):
    grew = [n for n, ok in bytes_unchanged(rid) if not ok]
    m = base["metrics"]
    same = abs(m[net_key] - pub_net) < 1e-9 and m[pf_key] == pub_pf
    if same:
        check(name + " (exact reproduction; grown inputs: "
              + (", ".join(grew) if grew else "none") + ")", True,
              f"{m[net_key]:.4f} == published {pub_net:.4f}")
    else:
        check(name + " (re-measurement on grown inputs)", len(grew) > 0,
              f"grew: {', '.join(grew) if grew else 'NOTHING -- alarm'}; "
              f"{m[net_key]:.4f} vs published {pub_net:.4f}")


def main():
    # ------------------------------------------------------------------ qs
    print("\n== qs (five cells, one at 15m long-only) ==")
    QS = [
        ("QS-001", "long-only", "15m", "BTCUSDT", "0726c6ee30c1bc68"),
        ("QS-002", "two-sided", "1h", "SOLUSDT", "7e9d9a26e6327c0a"),
        ("QS-007", "two-sided", "1h", "SUIUSDT", "100a72a352b2ed4c"),
        ("QS-006", "two-sided", "1h", "JUPUSDT", "746608af8aecf2f2"),
        ("QS-003", "two-sided", "1h", "SUIUSDT", "b84bc05f09d574d8"),
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
        paths0 = [p for p in paths if not p.endswith(".json")]
        m_zero_direct = Q2.run_one(paths0, {**par, "tf": tf})[0]
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
        pub = json.load(open(os.path.join(ROOT, "results", "runs", rid + ".json"),
                             encoding="utf-8"))
        repro_check(f"qs {strat} {sym} {tf} BASE vs published", base, rid,
                    pub["metrics"]["return_base_pct"], pub["metrics"]["pf"],
                    "return_base_pct", "pf")

    # ------------------------------------------------------------- cbpackf
    print("\n== cbpackf (S02 SUI, S03 XRP, S02 ETH) ==")
    for sym, sid, rid in (("SUIUSDT", "S02", "c1f3df39b37c1d2b"),
                          ("XRPUSDT", "S03", "db89577d5f9d9d34"),
                          ("ETHUSDT", "S02", "2e823fa306c91366")):
        base = art("cbpackf", "1h", sym,
                   {"fee_bps": 5.0, "slippage_bps": 0.5, "funding": True})
        zero = art("cbpackf", "1h", sym,
                   {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False})
        zero2 = art("cbpackf", "1h", sym,
                    {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False})
        pair(base, zero, f"cbpackf-{sid}-{sym}")
        b, z = base["metrics"], zero["metrics"]
        check(f"cbpackf {sid} {sym} BASE declares 5.0/0.5, funding on, settlements present",
              b["fee_bps_per_side"] == 5.0 and b["slippage_bps_per_side"] == 0.5 and
              b["funding_charged"] is True and b["n_settlements"] > 0,
              f"n_settlements {b['n_settlements']}")
        check(f"cbpackf {sid} {sym} ZERO declares 0/0, funding off, zero settlements",
              z["fee_bps_per_side"] == 0.0 and z["slippage_bps_per_side"] == 0.0 and
              z["funding_charged"] is False and z["n_settlements"] == 0)
        check(f"cbpackf {sid} {sym} ZERO is deterministic",
              zero["run_id"] == zero2["run_id"] and
              json.dumps(zero["metrics"], sort_keys=True) == json.dumps(zero2["metrics"], sort_keys=True))
        rb = next(r for r in base["tables"] if r.get("id") == sid)
        rz = next(r for r in zero["tables"] if r.get("id") == sid)
        check(f"cbpackf {sid} {sym} ZERO row above BASE",
              rz["net_%"] > rb["net_%"] and rz["PF"] > rb["PF"],
              f"{rb['net_%']:.4f}% PF {rb['PF']:.4f} -> {rz['net_%']:.4f}% PF {rz['PF']:.4f}")
        pub = json.load(open(os.path.join(ROOT, "results", "runs", rid + ".json"),
                             encoding="utf-8"))
        pub_row = next(r for r in pub["tables"] if r.get("id") == sid)
        repro_check(f"cbpackf {sid} {sym} BASE vs published",
                    {"metrics": {"return_pct": rb["net_%"], "profit_factor": rb["PF"]}},
                    rid, pub_row["net_%"], pub_row["PF"], "return_pct", "profit_factor")

    # ------------------------------------------------------------- fingrad
    print("\n== fingrad (SUIUSDT 1h, sig_mode=b, funding off in both regimes) ==")
    base = art("fingrad", "1h", "SUIUSDT",
               {"sig_mode": "b", "costs": "author", "funding": False})
    zero = art("fingrad", "1h", "SUIUSDT",
               {"sig_mode": "b", "costs": "zero", "funding": False})
    pair(base, zero, "fingrad-SUI-b")
    F = fresh(os.path.join(CODE, "fingrad_engine.py"), "fingrad_direct")
    paths = V.ADAPTERS["fingrad"]["inputs"]("1h", "SUIUSDT")
    par = {"tf": "1h", "sig_mode": "b", "costs": "author", "funding": False}
    f_direct = F.run_symbol(paths, dict(par))["metrics"]
    check("fingrad BASE == engine with its native author block, funding off",
          abs(f_direct["return_pct"] - base["metrics"]["return_pct"]) < 1e-9,
          f"{f_direct['return_pct']} vs {base['metrics']['return_pct']}")
    F2 = fresh(os.path.join(CODE, "fingrad_engine.py"), "fingrad_direct_zero")
    f_zero_direct = F2.run_symbol(paths, {**par, "costs": "zero"})["metrics"]
    check("fingrad ZERO == engine with costs=zero, by hand",
          abs(f_zero_direct["return_pct"] - zero["metrics"]["return_pct"]) < 1e-9,
          f"{f_zero_direct['return_pct']} vs {zero['metrics']['return_pct']}")
    check("fingrad ZERO declares 0 bps, funding off in both regimes",
          zero["metrics"]["fee_bps_per_side"] == 0.0 and
          zero["metrics"]["slip_bps_per_side"] == 0.0 and
          zero["metrics"]["cost_bp_roundtrip"] == 0.0 and
          zero["metrics"]["funding_charged"] is False and
          zero["metrics"]["n_funding_events"] == 0 and
          base["metrics"]["funding_charged"] is False,
          f"base declared funding: {base['metrics']['funding_charged']}")
    # the engine rounds both return_pct and ret_zero_pct to four decimals
    # before this difference is taken, so 2e-4 is the exact rounding bound
    check("fingrad ZERO agrees with the engine's own drag measurement (4dp rounding)",
          abs((zero["metrics"]["ret_zero_pct"] - base["metrics"]["return_pct"]) -
              base["metrics"]["drag_pp"]) < 2e-4,
          f"drag_pp {base['metrics']['drag_pp']:.4f} pp")
    check("fingrad trade count unchanged by the cost regime",
          base["metrics"]["n_trades"] == zero["metrics"]["n_trades"],
          f"{base['metrics']['n_trades']} vs {zero['metrics']['n_trades']}")
    pub = json.load(open(os.path.join(ROOT, "results", "runs", "ed06fc465283ef77.json"),
                         encoding="utf-8"))
    repro_check("fingrad BASE vs published", base, "ed06fc465283ef77",
                pub["metrics"]["return_pct"], pub["metrics"]["profit_factor"],
                "return_pct", "profit_factor")

    # -------------------------------------------------------------- dspack
    print("\n== dspack (ds1 HYPEUSDT 1h; author == zero) ==")
    par = {"strat": "ds1", "costs": "author", "window": "full"}
    base = art("dspack", "1h", "HYPEUSDT", par)
    costed = art("dspack", "1h", "HYPEUSDT",
                 {"strat": "ds1", "costs": "repo6x5", "window": "full"})
    D = fresh(os.path.join(CODE, "dspack_engine.py"), "dsp_direct")
    paths = V.ADAPTERS["dspack"]["inputs"]("1h", "HYPEUSDT")
    row = D.run_suite(paths, par)["tables"][0]
    check("dspack ds1 HYPE BASE == engine at its own author (zero) constants",
          abs(row["ret_pct"] - base["metrics"]["return_pct"]) < 1e-9,
          f"{row['ret_pct']} vs {base['metrics']['return_pct']}")
    t = costed["tables"][0]
    check("dspack ds1 HYPE COSTED re-score at zero cost == author headline",
          abs(t["ret_zero_pct"] - base["metrics"]["return_pct"]) < 1e-9,
          f"costed ret_zero_pct {t['ret_zero_pct']} vs author {base['metrics']['return_pct']}")
    check("dspack ds1 HYPE COSTED pays real fees and lands below the author headline",
          t["fees_charged"] > 0.0 and t["ret_pct"] < base["metrics"]["return_pct"],
          f"fees {t['fees_charged']:.2f}, ret {t['ret_pct']:.2f}% vs {base['metrics']['return_pct']:.2f}%")
    check("dspack ds1 HYPE same trade count in both regimes (signals untouched)",
          t["n_trades"] == base["metrics"]["n_trades"],
          f"{t['n_trades']} vs {base['metrics']['n_trades']}")
    pub = json.load(open(os.path.join(ROOT, "results", "runs", "88bc7c612612f5f8.json"),
                         encoding="utf-8"))
    repro_check("dspack ds1 HYPE BASE vs published", base, "88bc7c612612f5f8",
                pub["metrics"]["return_pct"], pub["metrics"]["profit_factor"],
                "return_pct", "profit_factor")

    # -------------------------------------------------------- ids and scope
    print("\n== provenance ==")
    check("BASE and ZERO differ in every regime pair that differs",
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
