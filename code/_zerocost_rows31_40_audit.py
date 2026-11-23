"""Known-answer audit for the 2026-11-23 rows 31-40 zero-cost control.

THE QUESTION THIS FILE ANSWERS, BEFORE ANY NUMBER IS PUBLISHED: when the
control says "zero", did the engine actually run at zero? And when it says
"base", did it run at its published constants?

Every adapter is checked against an INDEPENDENT invocation of the same engine
-- a freshly loaded module with its cost constants set BY HAND -- so the check
cannot pass just because the adapter agrees with itself. Where an engine
publishes its OWN zero-cost reference inside the artifact (`ret_zero_pct` for
dspack, `drag_pp` for rsimr/fingrad), that number is the reference. Where the
ranking artifact's stored input hashes still match today's files, the BASE
artifact must reproduce the published figure EXACTLY; where the bytes grew,
BASE must be a re-measurement and the audit asserts the difference.

Run:  python code/_zerocost_rows31_40_audit.py
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
    # legacy full-file cut: the direct engine calls below read the real files,
    # so the artifact must describe those same bytes
    return V.make_artifact(adapter, tf, sym, params, cut_ts=None)


def bytes_unchanged(rid):
    """True if every input file of the RANKING artifact still hashes to its
    stored sha256 today (gen-1 artifacts store full-file hashes)."""
    p = os.path.join(ROOT, "results", "runs", str(rid) + ".json")
    a = json.load(open(p, encoding="utf-8"))
    out = []
    for i in a.get("inputs") or []:
        path, sha = i.get("path"), i.get("sha256")
        if path and sha:
            h = hashlib.sha256(open(path, "rb").read()).hexdigest()
            out.append((os.path.basename(path), h == sha))
    return out


def repro_check(name, base, rid, pub_net, pub_pf, net_key, pf_key):
    """Equality to the published figure is exact reproduction -- the strongest
    possible evidence that the appended bytes (funding tail records) never
    touch an open position. Inequality is only acceptable when an input file
    really grew; with byte-unchanged inputs an inequality would be an alarm."""
    rows = bytes_unchanged(rid)
    grew = [n for n, ok in rows if not ok]
    same = (abs(base["metrics"][net_key] - pub_net) < 1e-9 and
            base["metrics"][pf_key] == pub_pf)
    if same:
        check(name + " (exact reproduction; grown inputs: "
              + (", ".join(grew) if grew else "none") + ")",
              True, f"{base['metrics'][net_key]:.4f} == published {pub_net:.4f}")
    else:
        check(name + " (re-measurement on grown inputs)",
              len(grew) > 0,
              f"grew: {', '.join(grew) if grew else 'NOTHING -- alarm'}; "
              f"{base['metrics'][net_key]:.4f} vs published {pub_net:.4f}")


def main():
    # ------------------------------------------------------------------ qs
    print("\n== qs (five cells, catalog base ladder) ==")
    QS_CELLS = [
        ("QS-009", "JUPUSDT", "fb57f0f55dca030c"),
        ("QS-004", "SOLUSDT", "1138f99c7c8da7b2"),
        ("QS-006", "SUIUSDT", "e8ef32c951ff001f"),
        ("QS-006", "HYPEUSDT", "780361ac3ceb774c"),
        ("QS-005", "ETHUSDT", "b79338b70e6e56da"),
    ]
    for strat, sym, rid in QS_CELLS:
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
        paths0 = [p for p in paths if not p.endswith(".json")]
        m_zero_direct = Q2.run_one(paths0, {**par, "tf": "1h"})[0]
        Q2.E.COSTS = saved
        check(f"qs {strat} {sym} ZERO == engine with the ladder zeroed by hand, no funding file",
              abs(m_zero_direct["return_base_pct"] - zero["metrics"]["return_base_pct"]) < 1e-9,
              f"{m_zero_direct['return_base_pct']} vs {zero['metrics']['return_base_pct']}")
        mz = zero["metrics"]
        check(f"qs {strat} {sym} ZERO labels, no funding, cost points coincide",
              mz["fee_bps_per_side"] == 0.0 and mz["slippage_bps_per_side"] == 0.0 and
              mz["funding_charged"] is False and mz["costs_primary"] == "zero(0bps RT)" and
              mz["n_funding_events"] == 0 and mz["funding_paid"] == 0.0 and
              mz["return_base_pct"] == mz["return_adverse_pct"] == mz["return_gate_pct"])
        pub = json.load(open(os.path.join(ROOT, "results", "runs", rid + ".json"),
                             encoding="utf-8"))
        repro_check(f"qs {strat} {sym} BASE vs published", base, rid,
                    pub["metrics"]["return_base_pct"], pub["metrics"]["pf"],
                    "return_base_pct", "pf")

    # ------------------------------------------------------------- cbpackf
    print("\n== cbpackf (S10 ETHUSDT 1h) ==")
    base = art("cbpackf", "1h", "ETHUSDT",
               {"fee_bps": 5.0, "slippage_bps": 0.5, "funding": True})
    zero = art("cbpackf", "1h", "ETHUSDT",
               {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False})
    zero2 = art("cbpackf", "1h", "ETHUSDT",
                {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False})
    pair(base, zero, "cbpackf-ETH-S10")
    b, z = base["metrics"], zero["metrics"]
    check("cbpackf BASE declares 5.0/0.5 and funding charged, settlements present",
          b["fee_bps_per_side"] == 5.0 and b["slippage_bps_per_side"] == 0.5 and
          b["funding_charged"] is True and b["n_settlements"] > 0,
          f"n_settlements {b['n_settlements']}")
    check("cbpackf ZERO declares 0/0 and funding not charged, zero settlements",
          z["fee_bps_per_side"] == 0.0 and z["slippage_bps_per_side"] == 0.0 and
          z["funding_charged"] is False and z["n_settlements"] == 0)
    check("cbpackf ZERO deterministic (two runs, identical artifact)",
          zero["run_id"] == zero2["run_id"] and
          json.dumps(zero["metrics"], sort_keys=True) == json.dumps(zero2["metrics"], sort_keys=True))
    rb = next(r for r in base["tables"] if r.get("id") == "S10")
    rz = next(r for r in zero["tables"] if r.get("id") == "S10")
    check("cbpackf ZERO S10 sits above BASE (cost removal in the right direction)",
          rz["net_%"] > rb["net_%"] and rz["PF"] > rb["PF"],
          f"{rb['net_%']:.4f}% PF {rb['PF']:.4f} -> {rz['net_%']:.4f}% PF {rz['PF']:.4f}")
    pub = json.load(open(os.path.join(ROOT, "results", "runs", "2e823fa306c91366.json"),
                         encoding="utf-8"))
    pub_s10 = next(r for r in pub["tables"] if r.get("id") == "S10")
    repro_check("cbpackf S10 BASE vs published", {"metrics": {"return_pct": rb["net_%"],
                "profit_factor": rb["PF"]}}, "2e823fa306c91366",
                pub_s10["net_%"], pub_s10["PF"], "return_pct", "profit_factor")

    # --------------------------------------------------------------- rsimr
    print("\n== rsimr (SOLUSDC spot 1h) ==")
    base = art("rsimr", "1h", "SOLUSDC", {"costs": "repo"})
    zero = art("rsimr", "1h", "SOLUSDC", {"costs": "zero"})
    pair(base, zero, "rsimr")
    R = fresh(os.path.join(CODE, "rsi_mr_engine.py"), "rsimr_direct")
    path = V.ADAPTERS["rsimr"]["inputs"]("1h", "SOLUSDC")[0]
    r_direct = R.run_symbol(path, {"costs": "repo"})["metrics"]
    check("rsimr BASE == engine with its native repo cost block",
          abs(r_direct["return_pct"] - base["metrics"]["return_pct"]) < 1e-9,
          f"{r_direct['return_pct']} vs {base['metrics']['return_pct']}")
    R2 = fresh(os.path.join(CODE, "rsi_mr_engine.py"), "rsimr_direct_zero")
    r_zero_direct = R2.run_symbol(path, {"costs": "zero"})["metrics"]
    check("rsimr ZERO == engine with COSTS[zero] (0/0)",
          abs(r_zero_direct["return_pct"] - zero["metrics"]["return_pct"]) < 1e-9,
          f"{r_zero_direct['return_pct']} vs {zero['metrics']['return_pct']}")
    check("rsimr ZERO declares 0 RT and agrees with the engine's own drag measurement",
          zero["metrics"]["cost_bp_roundtrip"] == 0.0 and
          abs((zero["metrics"]["ret_zero_pct"] - base["metrics"]["return_pct"]) -
              base["metrics"]["drag_pp"]) < 1e-9,
          f"drag_pp {base['metrics']['drag_pp']:.4f} pp")
    check("rsimr trade count unchanged by the cost regime (signals untouched)",
          base["metrics"]["n_trades"] == zero["metrics"]["n_trades"],
          f"{base['metrics']['n_trades']} vs {zero['metrics']['n_trades']}")
    pub = json.load(open(os.path.join(ROOT, "results", "runs", "dcf66a3eb320e7a7.json"),
                         encoding="utf-8"))
    repro_check("rsimr BASE vs published", base, "dcf66a3eb320e7a7",
                pub["metrics"]["return_pct"], pub["metrics"]["profit_factor"],
                "return_pct", "profit_factor")

    # ------------------------------------------------------------- fingrad
    print("\n== fingrad (ETHUSDT 1h, preset day) ==")
    base = art("fingrad", "1h", "ETHUSDT",
               {"funding": True, "preset": "day", "costs": "author"})
    zero = art("fingrad", "1h", "ETHUSDT",
               {"funding": False, "preset": "day", "costs": "zero"})
    pair(base, zero, "fingrad")
    F = fresh(os.path.join(CODE, "fingrad_engine.py"), "fingrad_direct")
    paths = V.ADAPTERS["fingrad"]["inputs"]("1h", "ETHUSDT")
    f_direct = F.run_symbol(paths, {"tf": "1h", "funding": True, "preset": "day",
                                    "costs": "author"})["metrics"]
    check("fingrad BASE == engine with its native author block and funding on",
          abs(f_direct["return_pct"] - base["metrics"]["return_pct"]) < 1e-9,
          f"{f_direct['return_pct']} vs {base['metrics']['return_pct']}")
    F2 = fresh(os.path.join(CODE, "fingrad_engine.py"), "fingrad_direct_zero")
    f_zero_direct = F2.run_symbol(paths, {"tf": "1h", "funding": False, "preset": "day",
                                          "costs": "zero"})["metrics"]
    check("fingrad ZERO == engine with costs=zero and funding=false, by hand",
          abs(f_zero_direct["return_pct"] - zero["metrics"]["return_pct"]) < 1e-9,
          f"{f_zero_direct['return_pct']} vs {zero['metrics']['return_pct']}")
    check("fingrad ZERO declares 0 bps, funding off and no funding events",
          zero["metrics"]["fee_bps_per_side"] == 0.0 and
          zero["metrics"]["slip_bps_per_side"] == 0.0 and
          zero["metrics"]["cost_bp_roundtrip"] == 0.0 and
          zero["metrics"]["funding_charged"] is False and
          zero["metrics"]["n_funding_events"] == 0 and
          zero["metrics"]["funding_paid"] is None,
          f"base funding_paid {base['metrics']['funding_paid']}")
    check("fingrad trade count unchanged by the cost regime (signals untouched)",
          base["metrics"]["n_trades"] == zero["metrics"]["n_trades"],
          f"{base['metrics']['n_trades']} vs {zero['metrics']['n_trades']}")
    pub = json.load(open(os.path.join(ROOT, "results", "runs", "98d8a73f90eb898f.json"),
                         encoding="utf-8"))
    repro_check("fingrad BASE vs published", base, "98d8a73f90eb898f",
                pub["metrics"]["return_pct"], pub["metrics"]["profit_factor"],
                "return_pct", "profit_factor")

    # -------------------------------------------------------------- dspack
    print("\n== dspack (ds1 BNBUSDT / DOGEUSDT 1h; author == zero) ==")
    for sym, rid in (("BNBUSDT", "75d0fc12080ef957"),
                     ("DOGEUSDT", "79ddecc6e7ea40eb")):
        par = {"strat": "ds1", "costs": "author", "window": "full"}
        base = art("dspack", "1h", sym, par)
        costed = art("dspack", "1h", sym, {"strat": "ds1", "costs": "repo6x5",
                                           "window": "full"})
        D = fresh(os.path.join(CODE, "dspack_engine.py"), f"dsp_{sym}")
        paths = V.ADAPTERS["dspack"]["inputs"]("1h", sym)
        out_direct = D.run_suite(paths, par)
        row = out_direct["tables"][0]
        check(f"dspack ds1 {sym} BASE == engine at its own author (zero) constants",
              abs(row["ret_pct"] - base["metrics"]["return_pct"]) < 1e-9,
              f"{row['ret_pct']} vs {base['metrics']['return_pct']}")
        t = costed["tables"][0]
        check(f"dspack ds1 {sym} COSTED re-score at zero cost == author headline",
              abs(t["ret_zero_pct"] - base["metrics"]["return_pct"]) < 1e-9,
              f"costed ret_zero_pct {t['ret_zero_pct']} vs author {base['metrics']['return_pct']}")
        check(f"dspack ds1 {sym} COSTED pays real fees and lands below the author headline",
              t["fees_charged"] > 0.0 and t["ret_pct"] < base["metrics"]["return_pct"],
              f"fees {t['fees_charged']:.2f}, ret {t['ret_pct']:.2f}% vs {base['metrics']['return_pct']:.2f}%")
        check(f"dspack ds1 {sym} same trade count in both regimes (signals untouched)",
              t["n_trades"] == base["metrics"]["n_trades"],
              f"{t['n_trades']} vs {base['metrics']['n_trades']}")
        pub = json.load(open(os.path.join(ROOT, "results", "runs", rid + ".json"),
                             encoding="utf-8"))
        repro_check(f"dspack ds1 {sym} BASE vs published", base, rid,
                    pub["metrics"]["return_pct"], pub["metrics"]["profit_factor"],
                    "return_pct", "profit_factor")

    # -------------------------------------------------------- ids and scope
    print("\n== provenance ==")
    check("BASE and ZERO are different run_ids in every regime pair that differs",
          all(a["run_id"] != b["run_id"] for _, a, b in PAIRS) and len(PAIRS) >= 8,
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
