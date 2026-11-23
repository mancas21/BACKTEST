"""Known-answer audit for the 2026-11-23 rows 91-100 zero-cost control.

Reuses the audited helpers from earlier batches. Every adapter is checked
against an independent fresh-module recomputation with cost constants set by
hand (cbpackf: declared fields, determinism, in-artifact references). S07's
funding-signal path is checked explicitly. Engine drift in old artifacts is
declared, not hidden.

Run:  python code/_zerocost_rows91_100_audit.py ; exit 0 all pass, 2 any fail.
"""
import sys

import _zerocost_rows81_90_audit as C

V = C.V
PASS, FAIL = C.PASS, C.FAIL
check, fresh, art, published, repro_check = (
    C.check, C.fresh, C.art, C.published, C.repro_check)
PAIRS = C.B.A.PAIRS


def my_pair(a, b, tag):
    PAIRS.append((tag, a, b))


def main():
    # ------------------------------------------------------------- cbpackf
    print("\n== cbpackf (S07 and S09 SUIUSDT 1h; S07 needs signal funding) ==")
    for sid in ("S07", "S09"):
        zpar = {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False}
        if sid == "S07":
            zpar["funding_signal"] = True
        base = art("cbpackf", "1h", "SUIUSDT",
                   {"fee_bps": 5.0, "slippage_bps": 0.5, "funding": True})
        zero = art("cbpackf", "1h", "SUIUSDT", zpar)
        my_pair(base, zero, f"cbpackf-{sid}-SUI")
        b, z = base["metrics"], zero["metrics"]
        check(f"cbpackf {sid} BASE declares 5.0/0.5, funding on, settlements",
              b["fee_bps_per_side"] == 5.0 and b["slippage_bps_per_side"] == 0.5 and
              b["funding_charged"] is True and b["n_settlements"] > 0)
        check(f"cbpackf {sid} ZERO declares 0/0, funding off, zero settlements",
              z["fee_bps_per_side"] == 0.0 and z["slippage_bps_per_side"] == 0.0 and
              z["funding_charged"] is False and z["n_settlements"] == 0)
        if sid == "S07":
            check("cbpackf S07 ZERO keeps funding as signal only, no billing",
                  z.get("funding_signal") is True and z["funding_attached"] is True and
                  z["funding_charged"] is False)
        rb = next(r for r in base["tables"] if r.get("id") == sid)
        rz = next(r for r in zero["tables"] if r.get("id") == sid)
        check(f"cbpackf {sid} ZERO row above BASE, same trade count",
              rz["net_%"] > rb["net_%"] and rz["trades"] == rb["trades"],
              f"{rb['net_%']:.4f}% -> {rz['net_%']:.4f}%, trades {rb['trades']}")
        pub = published("c1f3df39b37c1d2b")
        pr = next(r for r in pub["tables"] if r.get("id") == sid)
        repro_check(f"cbpackf {sid} BASE vs published",
                    {"metrics": {"return_pct": rb["net_%"], "profit_factor": rb["PF"]}},
                    "c1f3df39b37c1d2b", pr["net_%"], pr["PF"], "return_pct", "profit_factor")

    # -------------------------------------------------------- qs and qsf
    print("\n== qs / qsf (two cells) ==")
    import qs_flow_strats  # noqa: F401 -- registers QS-044 into qs_strats.SPECS
    for adapter, strat, sym, rid in (("qs", "QS-002", "HYPEUSDT", "7ae2542345801f6e"),
                                     ("qsf", "QS-044", "SOLUSDT", "93735ee1e6277fda")):
        par = {"strat": strat, "variant": "two-sided"}
        base = art(adapter, "1h", sym, {**par, "costs": "repo", "funding": True})
        zero = art(adapter, "1h", sym, {**par, "costs": "zero", "funding": False})
        my_pair(base, zero, f"{adapter}-{strat}")
        Q = fresh("code/qs_run.py", f"q_{strat}")
        paths = V.ADAPTERS[adapter]["inputs"]("1h", sym)
        m_direct = Q.run_one(paths, {**par, "tf": "1h"})[0]
        check(f"{adapter} {strat} BASE == engine with its native ladder",
              abs(m_direct["return_base_pct"] - base["metrics"]["return_base_pct"]) < 1e-9,
              f"{m_direct['return_base_pct']} vs {base['metrics']['return_base_pct']}")
        Q2 = fresh("code/qs_run.py", f"qz_{strat}")
        saved = {ck: dict(c) for ck, c in Q2.E.COSTS.items()}
        Q2.E.COSTS = {ck: {"fee": 0.0, "slip": 0.0, "stop_slip_mult": c["stop_slip_mult"]}
                      for ck, c in saved.items()}
        m_zero_direct = Q2.run_one([p for p in paths if not p.endswith(".json")],
                                   {**par, "tf": "1h"})[0]
        Q2.E.COSTS = saved
        check(f"{adapter} {strat} ZERO == ladder zeroed by hand, no funding file",
              abs(m_zero_direct["return_base_pct"] - zero["metrics"]["return_base_pct"]) < 1e-9,
              f"{m_zero_direct['return_base_pct']} vs {zero['metrics']['return_base_pct']}")
        mz = zero["metrics"]
        check(f"{adapter} {strat} ZERO labels, no funding, cost points coincide",
              mz["fee_bps_per_side"] == 0.0 and mz["slippage_bps_per_side"] == 0.0 and
              mz["funding_charged"] is False and mz["costs_primary"] == "zero(0bps RT)" and
              mz["n_funding_events"] == 0 and mz["funding_paid"] == 0.0 and
              mz["return_base_pct"] == mz["return_adverse_pct"] == mz["return_gate_pct"])
        pub = published(rid)
        repro_check(f"{adapter} {strat} BASE vs published", base, rid,
                    pub["metrics"]["return_base_pct"], pub["metrics"]["pf"],
                    "return_base_pct", "pf")

    # ------------------------------------------------- dspack2 and dspack
    print("\n== dspack2 (three ds7) and dspack (three ds1) ==")
    for adapter, strat, sym, rid in (
            ("dspack2", "ds7", "DOGEUSDT", "5e8384d3844eb3c2"),
            ("dspack2", "ds7", "SOLUSDT", "edc6c3f19c12601c"),
            ("dspack2", "ds7", "NEARUSDT", "bf44523b2cc8a6e8"),
            ("dspack", "ds1", "NEARUSDT", "007e08ccd12e6797"),
            ("dspack", "ds1", "LINKUSDT", "01f65a4b84d35744"),
            ("dspack", "ds1", "SUIUSDT", "986ae236af7e6ad5")):
        bpar = {"strat": strat, "costs": "repo6x5", "window": "full"}
        base = art(adapter, "1h", sym, bpar)
        zero = art(adapter, "1h", sym, {**bpar, "costs": "author"})
        my_pair(base, zero, f"{adapter}-{strat}-{sym}")
        eng = "dspack2_engine.py" if adapter == "dspack2" else "dspack_engine.py"
        D = fresh("code/" + eng, f"d_{adapter}_{sym}")
        paths = V.ADAPTERS[adapter]["inputs"]("1h", sym)
        for regime, par in (("BASE", bpar),
                            ("ZERO", {"strat": strat, "costs": "author",
                                      "window": "full"})):
            row = D.run_suite(paths, par)["tables"][0]
            target = base if regime == "BASE" else zero
            check(f"{adapter} {strat} {sym} {regime} == engine with that preset",
                  abs(row["ret_pct"] - target["metrics"]["return_pct"]) < 1e-9,
                  f"{row['ret_pct']} vs {target['metrics']['return_pct']}")
        t = base["tables"][0]
        check(f"{adapter} {strat} {sym} BASE zero re-score == author, fees real",
              abs(t["ret_zero_pct"] - zero["metrics"]["return_pct"]) < 1e-9 and
              t["fees_charged"] > 0 and t["ret_pct"] < zero["metrics"]["return_pct"],
              f"fees {t['fees_charged']:.2f}")
        pub = published(rid)
        repro_check(f"{adapter} {strat} {sym} BASE vs published", base, rid,
                    pub["metrics"]["return_pct"], pub["metrics"]["profit_factor"],
                    "return_pct", "profit_factor")

    print("\n== provenance ==")
    check("BASE and ZERO differ in every regime pair",
          all(a["run_id"] != b["run_id"] for _, a, b in PAIRS) and len(PAIRS) >= 10,
          f"{len(PAIRS)} pairs")
    check("every BASE/ZERO pair shares the same engine hash",
          all(a["core"]["engine_sha256"] == b["core"]["engine_sha256"]
              for _, a, b in PAIRS))
    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("FAILED:", FAIL)
        sys.exit(2)
    print("ALL PASS")


if __name__ == "__main__":
    main()
