"""Known-answer audit for the 2026-11-20 rows 21-30 zero-cost control.

THE QUESTION THIS FILE ANSWERS, BEFORE ANY NUMBER IS PUBLISHED: when the
control says "zero", did the engine actually run at zero? And when it says
"base", did the engine run at its published constants?

Every adapter is checked against an INDEPENDENT invocation of the same
engine -- a freshly loaded module with its cost constants set BY HAND -- so
the check cannot pass just because the adapter agrees with itself. Where an
engine publishes its OWN zero-cost reference inside the artifact
(`zero_cost_pf` for pack100/pack50, `drag_pp` for dspack), that number is
the reference. Where the ranking artifact's stored input hashes still match
today's files, the BASE artifact must reproduce the published figure
EXACTLY; where the bytes grew, BASE must be a re-measurement and the audit
asserts the difference.

Run:  python code/_zerocost_rows21_30_audit.py
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
    # legacy full-file cut: the direct engine calls below read the real
    # files, so the artifact must describe those same bytes
    return V.make_artifact(adapter, tf, sym, params, cut_ts=None)


def bytes_unchanged(rid):
    """True if every input file of the RANKING artifact still hashes to its
    stored sha256 today (gen-1 artifacts store full-file hashes)."""
    p = os.path.join(ROOT, "results", "runs", str(rid) + ".json")
    a = json.load(open(p, encoding="utf-8"))
    out = []
    for i in a.get("inputs") or []:
        path = i.get("path")
        sha = i.get("sha256")
        if path and sha:
            h = hashlib.sha256(open(path, "rb").read()).hexdigest()
            out.append((os.path.basename(path), h == sha))
    return out


def repro_check(name, base, rid, pub_net, pub_pf, net_key, pf_key):
    """Equality to the published figure is exact reproduction — the strongest
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
              f"grew: {', '.join(grew) if grew else 'NOTHING — alarm'}; "
              f"{base['metrics'][net_key]:.4f} vs published {pub_net:.4f}")


def main():
    # ------------------------------------------------------------- pack100
    print("\n== pack100 (B17-1h HYPEUSDT, F75-1h SUIUSDT) ==")
    for strat, sym, rid in (("B17-1h", "HYPEUSDT", "0e0d2501a65f1a81"),
                            ("F75-1h", "SUIUSDT", "30f67b5380bcd458")):
        base = art("pack100", "1h", sym, {"strat": strat, "costs": "repo", "funding": True})
        zcost = art("pack100", "1h", sym, {"strat": strat, "costs": "zero", "funding": True})
        zero = art("pack100", "1h", sym, {"strat": strat, "costs": "zero", "funding": False})
        pair(base, zero, f"pack100-{strat}")

        P = fresh(os.path.join(CODE, "pack100_engine.py"), f"p100_{strat}")
        paths = V.ADAPTERS["pack100"]["inputs"]("1h", sym)
        m_direct = P.run_one(paths, {"strat": strat})[0]
        check(f"pack100 {strat} BASE == engine with its own REPO constant untouched",
              abs(m_direct["return_pct"] - base["metrics"]["return_pct"]) < 1e-9,
              f"{m_direct['return_pct']} vs {base['metrics']['return_pct']}")
        check(f"pack100 {strat} costs=0 (funding on) == the artifact's own zero_cost_pf",
              abs(base["metrics"]["zero_cost_pf"] - zcost["metrics"]["pf_pct"]) < 1e-4,
              f"engine control {base['metrics']['zero_cost_pf']} vs adapter {zcost['metrics']['pf_pct']}")
        check(f"pack100 {strat} ZERO has funding_paid == 0 and declares 0 bps/funding off",
              zero["metrics"]["funding_paid"] == 0.0 and
              zero["metrics"]["cost_bps_per_side"] == 0.0 and
              zero["metrics"]["funding_charged"] is False,
              f"{base['metrics']['funding_paid']} -> {zero['metrics']['funding_paid']}")
        pub = json.load(open(os.path.join(ROOT, "results", "runs", rid + ".json"),
                             encoding="utf-8"))
        repro_check(f"pack100 {strat} BASE vs published", base, rid,
                    pub["metrics"]["return_pct"], pub["metrics"]["pf_pct"],
                    "return_pct", "pf_pct")

    # ------------------------------------------------------- qs and qsf
    print("\n== qs / qsf (six cells) ==")
    sys.path.insert(0, CODE)
    import qs_flow_strats  # registers the qsf specs into qs_strats.SPECS
    QS_CELLS = [("qs", "QS-004", "SUIUSDT", "b48f30800df51639"),
                ("qs", "QS-007", "HYPEUSDT", "8551ead0bf1325fc"),
                ("qs", "QS-005", "SUIUSDT", "59a513a240fff675"),
                ("qs", "QS-004", "ETHUSDT", "ec9bbc4dc8c8f218"),
                ("qs", "QS-006", "SOLUSDT", "d9d44100b54c4c40"),
                ("qsf", "QS-093", "JUPUSDT", "3630fe2670e70f15")]
    for adapter, strat, sym, rid in QS_CELLS:
        base = art(adapter, "1h", sym, {"strat": strat, "variant": "two-sided",
                                        "costs": "repo", "funding": True})
        zero = art(adapter, "1h", sym, {"strat": strat, "variant": "two-sided",
                                        "costs": "zero", "funding": False})
        pair(base, zero, f"{adapter}-{strat}-{sym}")

        Q = fresh(os.path.join(CODE, "qs_run.py"), f"q_{adapter}_{sym}")
        paths = V.ADAPTERS[adapter]["inputs"]("1h", sym)
        m_direct = Q.run_one(paths, {"strat": strat, "variant": "two-sided",
                                     "tf": "1h"})[0]
        check(f"{adapter} {strat} {sym} BASE == engine with its native COSTS ladder",
              abs(m_direct["return_base_pct"] - base["metrics"]["return_base_pct"]) < 1e-9,
              f"{m_direct['return_base_pct']} vs {base['metrics']['return_base_pct']}")

        Q2 = fresh(os.path.join(CODE, "qs_run.py"), f"qz_{adapter}_{sym}")
        saved = {ck: dict(c) for ck, c in Q2.E.COSTS.items()}
        Q2.E.COSTS = {ck: {"fee": 0.0, "slip": 0.0, "stop_slip_mult": c["stop_slip_mult"]}
                      for ck, c in saved.items()}
        paths0 = [p for p in paths if not p.endswith(".json")]
        m_zero_direct = Q2.run_one(paths0, {"strat": strat, "variant": "two-sided",
                                            "tf": "1h"})[0]
        Q2.E.COSTS = saved
        check(f"{adapter} {strat} {sym} ZERO == engine with the ladder zeroed by hand, no funding file",
              abs(m_zero_direct["return_base_pct"] - zero["metrics"]["return_base_pct"]) < 1e-9,
              f"{m_zero_direct['return_base_pct']} vs {zero['metrics']['return_base_pct']}")
        mz = zero["metrics"]
        check(f"{adapter} {strat} {sym} ZERO labels, zero funding, four cost points coincide",
              mz["fee_bps_per_side"] == 0.0 and mz["slippage_bps_per_side"] == 0.0 and
              mz["funding_charged"] is False and mz["costs_primary"] == "zero(0bps RT)" and
              mz["n_funding_events"] == 0 and mz["funding_paid"] == 0.0 and
              mz["return_base_pct"] == mz["return_adverse_pct"] == mz["return_gate_pct"])
        pub = json.load(open(os.path.join(ROOT, "results", "runs", rid + ".json"),
                             encoding="utf-8"))
        repro_check(f"{adapter} {strat} {sym} BASE vs published", base, rid,
                    pub["metrics"]["return_base_pct"], pub["metrics"]["pf"],
                    "return_base_pct", "pf")

    # -------------------------------------------------------------- pack50
    print("\n== pack50 (S46 BTCUSDT 1h) ==")
    base = art("pack50", "1h", "BTCUSDT", {"strat": 46, "costs": "repo", "funding": True})
    zero = art("pack50", "1h", "BTCUSDT", {"strat": 46, "costs": "zero", "funding": False})
    pair(base, zero, "pack50-S46")

    P5 = fresh(os.path.join(CODE, "pack50_engine.py"), "p50_direct")
    paths = V.ADAPTERS["pack50"]["inputs"]("1h", "BTCUSDT")
    m_direct = P5.run_one(paths, {"strat": 46})[0]
    check("pack50 S46 BASE == engine with its native per-symbol cost table",
          abs(m_direct["return_pct"] - base["metrics"]["return_pct"]) < 1e-9,
          f"{m_direct['return_pct']} vs {base['metrics']['return_pct']}")

    P5z = fresh(os.path.join(CODE, "pack50_engine.py"), "p50_direct_zero")
    P5z.S.costs_for = lambda sym, tf: (0.0, 0.0)
    paths0 = [p for p in paths if not p.endswith(".json")]
    m_zero_direct = P5z.run_one(paths0, {"strat": 46})[0]
    check("pack50 S46 ZERO == engine with the cost table zeroed by hand, no funding file",
          abs(m_zero_direct["return_pct"] - zero["metrics"]["return_pct"]) < 1e-9,
          f"{m_zero_direct['return_pct']} vs {zero['metrics']['return_pct']}")
    check("pack50 S46 ZERO internal zero-fee control == headline (funding off)",
          abs(zero["metrics"]["zero_cost_pf"] - zero["metrics"]["profit_factor"]) < 1e-9,
          f"zero_cost_pf {zero['metrics']['zero_cost_pf']} vs pf {zero['metrics']['profit_factor']}")
    check("pack50 S46 ZERO declares 0 bps, engine's own funding flag false",
          zero["metrics"]["fee_bps_per_side"] == 0.0 and
          zero["metrics"]["slip_bps_per_side"] == 0.0 and
          zero["metrics"]["funding_charged"] is False and
          zero["metrics"]["funding_paid"] == 0.0)
    check("pack50 S46 BASE declares the pack's published 4.0/2.0 block, funding on",
          base["metrics"]["fee_bps_per_side"] == 4.0 and
          base["metrics"]["slip_bps_per_side"] == 2.0 and
          base["metrics"]["funding_charged"] is True)
    pub = json.load(open(os.path.join(ROOT, "results", "runs", "1b13cbd18f8b00eb.json"),
                         encoding="utf-8"))
    repro_check("pack50 S46 BASE vs published", base, "1b13cbd18f8b00eb",
                pub["metrics"]["return_pct"], pub["metrics"]["profit_factor"],
                "return_pct", "profit_factor")

    # -------------------------------------------------------------- dspack
    print("\n== dspack (ds1 XRPUSDT 1h; author == zero by construction) ==")
    base = art("dspack", "1h", "XRPUSDT", {"strat": "ds1", "costs": "author", "window": "full"})
    costed = art("dspack", "1h", "XRPUSDT", {"strat": "ds1", "costs": "repo6x5", "window": "full"})

    D = fresh(os.path.join(CODE, "dspack_engine.py"), "dsp_direct")
    paths = V.ADAPTERS["dspack"]["inputs"]("1h", "XRPUSDT")
    out_direct = D.run_suite(paths, {"strat": "ds1", "costs": "author", "window": "full"})
    row = out_direct["tables"][0]
    check("dspack ds1 BASE == engine at its own author (zero) constants",
          abs(row["ret_pct"] - base["metrics"]["return_pct"]) < 1e-9,
          f"{row['ret_pct']} vs {base['metrics']['return_pct']}")
    t = costed["tables"][0]
    check("dspack ds1 COSTED re-score at zero cost == the author headline (same signals)",
          abs(t["ret_zero_pct"] - base["metrics"]["return_pct"]) < 1e-9,
          f"costed ret_zero_pct {t['ret_zero_pct']} vs author {base['metrics']['return_pct']}")
    check("dspack ds1 COSTED pays real fees and lands far below the author headline",
          t["fees_charged"] > 0.0 and t["ret_pct"] < base["metrics"]["return_pct"],
          f"fees {t['fees_charged']:.2f}, ret {t['ret_pct']:.2f}% vs {base['metrics']['return_pct']:.2f}%")
    check("dspack ds1 same trade count in both cost regimes (signals untouched)",
          t["n_trades"] == base["metrics"]["n_trades"],
          f"{t['n_trades']} vs {base['metrics']['n_trades']}")
    pub = json.load(open(os.path.join(ROOT, "results", "runs", "437c47539b4dc9ae.json"),
                         encoding="utf-8"))
    repro_check("dspack ds1 BASE vs published", base, "437c47539b4dc9ae",
                pub["metrics"]["return_pct"], pub["metrics"]["profit_factor"],
                "return_pct", "profit_factor")

    # -------------------------------------------------------- ids and scope
    print("\n== provenance ==")
    check("BASE and ZERO are different run_ids in every regime pair that differs",
          all(a["run_id"] != b["run_id"] for _, a, b in PAIRS) and len(PAIRS) >= 5,
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
