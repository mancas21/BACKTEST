"""Known-answer audit for the 2026-11-23 rows 71-80 zero-cost control.

Reuses the audited helper functions from code/_zerocost_rows61_70_audit.py
(check, pair, fresh, art, published, repro_check). Every adapter is still
checked against an independent fresh-module recomputation with cost constants
set by hand; engine drift in old ranking artifacts is declared, not hidden.

Run:  python code/_zerocost_rows71_80_audit.py ; exit 0 all pass, 2 any fail.
"""
import json
import sys

import _zerocost_rows61_70_audit as A

V = A.V
PASS, FAIL = A.PASS, A.FAIL
check, pair, fresh, art, published, repro_check = (
    A.check, A.pair, A.fresh, A.art, A.published, A.repro_check)


def qs_cells():
    print("\n== qs (five cells, two at 15m) ==")
    cells = [
        ("QS-002", "long-only", "15m", "HYPEUSDT", "17717f635b546e5a"),
        ("QS-009", "two-sided", "1h", "BTCUSDT", "9dd125970b540681"),
        ("QS-005", "two-sided", "1h", "HYPEUSDT", "a9bbac68c17a46cf"),
        ("QS-007", "two-sided", "1h", "ETHUSDT", "39a492d7646eea88"),
        ("QS-001", "two-sided", "15m", "HYPEUSDT", "ce01bf9aa130b1f0"),
    ]
    for strat, variant, tf, sym, rid in cells:
        par = {"strat": strat, "variant": variant}
        base = art("qs", tf, sym, {**par, "costs": "repo", "funding": True})
        zero = art("qs", tf, sym, {**par, "costs": "zero", "funding": False})
        pair(base, zero, f"qs-{strat}-{sym}-{tf}")
        Q = fresh("code/qs_run.py", f"q_{strat}_{sym}_{tf}")
        paths = V.ADAPTERS["qs"]["inputs"](tf, sym)
        m_direct = Q.run_one(paths, {**par, "tf": tf})[0]
        check(f"qs {strat} {sym} {tf} BASE == engine with its native ladder",
              abs(m_direct["return_base_pct"] - base["metrics"]["return_base_pct"]) < 1e-9,
              f"{m_direct['return_base_pct']} vs {base['metrics']['return_base_pct']}")
        Q2 = fresh("code/qs_run.py", f"qz_{strat}_{sym}_{tf}")
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


def pack100_cells():
    print("\n== pack100 (A01-15m SPXUSDT, B25-1h SOLUSDT) ==")
    for strat, sym, tf, rid in (("A01-15m", "SPXUSDT", "15m", "0b4ac2680e4c5f0e"),
                                ("B25-1h", "SOLUSDT", "1h", "05c8d58ae410682e")):
        base = art("pack100", tf, sym,
                   {"strat": strat, "costs": "repo", "funding": True})
        zcost = art("pack100", tf, sym,
                    {"strat": strat, "costs": "zero", "funding": True})
        zero = art("pack100", tf, sym,
                   {"strat": strat, "costs": "zero", "funding": False})
        pair(base, zero, f"pack100-{strat}")
        P = fresh("code/pack100_engine.py", f"p100_{strat}")
        paths = V.ADAPTERS["pack100"]["inputs"](tf, sym)
        m_direct = P.run_one(paths, {"strat": strat})[0]
        check(f"pack100 {strat} BASE == engine with its own REPO constant",
              abs(m_direct["return_pct"] - base["metrics"]["return_pct"]) < 1e-9,
              f"{m_direct['return_pct']} vs {base['metrics']['return_pct']}")
        check(f"pack100 {strat} costs=0 (funding on) == own zero_cost_pf",
              abs(base["metrics"]["zero_cost_pf"] - zcost["metrics"]["pf_pct"]) < 1e-4,
              f"{base['metrics']['zero_cost_pf']} vs {zcost['metrics']['pf_pct']}")
        check(f"pack100 {strat} ZERO declares 0 bps, no funding, zero funding_paid",
              zero["metrics"]["cost_bps_per_side"] == 0.0 and
              zero["metrics"]["funding_charged"] is False and
              zero["metrics"]["funding_paid"] == 0.0)
        pub = published(rid)
        repro_check(f"pack100 {strat} BASE vs published", base, rid,
                    pub["metrics"]["return_pct"], pub["metrics"]["pf_pct"],
                    "return_pct", "pf_pct")


def pack50_cell():
    print("\n== pack50 (S5 SUIUSDT 4h) ==")
    base = art("pack50", "4h", "SUIUSDT", {"strat": 5, "costs": "repo", "funding": True})
    zero = art("pack50", "4h", "SUIUSDT", {"strat": 5, "costs": "zero", "funding": False})
    pair(base, zero, "pack50-S05")
    P = fresh("code/pack50_engine.py", "p50_direct")
    paths = V.ADAPTERS["pack50"]["inputs"]("4h", "SUIUSDT")
    m_direct = P.run_one(paths, {"strat": 5})[0]
    check("pack50 S5 BASE == engine with its native per-symbol cost table",
          abs(m_direct["return_pct"] - base["metrics"]["return_pct"]) < 1e-9,
          f"{m_direct['return_pct']} vs {base['metrics']['return_pct']}")
    P2 = fresh("code/pack50_engine.py", "p50_direct_zero")
    P2.S.costs_for = lambda sym, tf: (0.0, 0.0)
    m_zero_direct = P2.run_one([p for p in paths if not p.endswith(".json")],
                               {"strat": 5})[0]
    check("pack50 S5 ZERO == cost table zeroed by hand, no funding file",
          abs(m_zero_direct["return_pct"] - zero["metrics"]["return_pct"]) < 1e-9,
          f"{m_zero_direct['return_pct']} vs {zero['metrics']['return_pct']}")
    check("pack50 S5 ZERO declares 0/0, funding flag false, own control agrees",
          zero["metrics"]["fee_bps_per_side"] == 0.0 and
          zero["metrics"]["slip_bps_per_side"] == 0.0 and
          zero["metrics"]["funding_charged"] is False and
          abs(zero["metrics"]["zero_cost_pf"] - zero["metrics"]["profit_factor"]) < 1e-9,
          f"zero_cost_pf {zero['metrics']['zero_cost_pf']}")
    pub = published("1300b325a1544451")
    repro_check("pack50 S5 BASE vs published", base, "1300b325a1544451",
                pub["metrics"]["return_pct"], pub["metrics"]["profit_factor"],
                "return_pct", "profit_factor")


def dspack_cells():
    print("\n== dspack (ds1 SOL published costed; ds3 ETH published author) ==")
    # ds1: BASE repo6x5, ZERO author
    bpar = {"strat": "ds1", "costs": "repo6x5", "window": "full"}
    zpar = {"strat": "ds1", "costs": "author", "window": "full"}
    base = art("dspack", "1h", "SOLUSDT", bpar)
    zero = art("dspack", "1h", "SOLUSDT", zpar)
    pair(base, zero, "dspack-ds1")
    D = fresh("code/dspack_engine.py", "dsp_direct")
    paths = V.ADAPTERS["dspack"]["inputs"]("1h", "SOLUSDT")
    for regime, par in (("BASE", bpar), ("ZERO", zpar)):
        row = D.run_suite(paths, par)["tables"][0]
        target = base if regime == "BASE" else zero
        check(f"dspack ds1 {regime} == engine with that preset",
              abs(row["ret_pct"] - target["metrics"]["return_pct"]) < 1e-9,
              f"{row['ret_pct']} vs {target['metrics']['return_pct']}")
    t = base["tables"][0]
    check("dspack ds1 BASE's zero re-score == author headline, fees real",
          abs(t["ret_zero_pct"] - zero["metrics"]["return_pct"]) < 1e-9 and
          t["fees_charged"] > 0 and t["ret_pct"] < zero["metrics"]["return_pct"],
          f"fees {t['fees_charged']:.2f}")
    pub = published("0f752f12c7acc9fa")
    repro_check("dspack ds1 BASE vs published", base, "0f752f12c7acc9fa",
                pub["metrics"]["return_pct"], pub["metrics"]["profit_factor"],
                "return_pct", "profit_factor")
    # ds3: published author == zero; costed re-run
    par = {"strat": "ds3", "costs": "author", "window": "full"}
    base3 = art("dspack", "1h", "ETHUSDT", par)
    costed = art("dspack", "1h", "ETHUSDT",
                 {"strat": "ds3", "costs": "repo6x5", "window": "full"})
    D3 = fresh("code/dspack_engine.py", "dsp_direct3")
    p3 = V.ADAPTERS["dspack"]["inputs"]("1h", "ETHUSDT")
    row3 = D3.run_suite(p3, par)["tables"][0]
    check("dspack ds3 BASE == engine at its own author (zero) constants",
          abs(row3["ret_pct"] - base3["metrics"]["return_pct"]) < 1e-9,
          f"{row3['ret_pct']} vs {base3['metrics']['return_pct']}")
    t3 = costed["tables"][0]
    check("dspack ds3 COSTED re-score == author headline, fees real, same trades",
          abs(t3["ret_zero_pct"] - base3["metrics"]["return_pct"]) < 1e-9 and
          t3["fees_charged"] > 0 and t3["n_trades"] == base3["metrics"]["n_trades"],
          f"fees {t3['fees_charged']:.2f}, trades {t3['n_trades']}")
    pub3 = published("2bc9516fabc8ecd8")
    repro_check("dspack ds3 BASE vs published", base3, "2bc9516fabc8ecd8",
                pub3["metrics"]["return_pct"], pub3["metrics"]["profit_factor"],
                "return_pct", "profit_factor")


def main():
    qs_cells()
    pack100_cells()
    pack50_cell()
    dspack_cells()
    print("\n== provenance ==")
    check("BASE and ZERO differ in every regime pair",
          all(a["run_id"] != b["run_id"] for _, a, b in A.PAIRS) and len(A.PAIRS) >= 9,
          f"{len(A.PAIRS)} pairs, all distinct")
    check("every BASE/ZERO pair shares the same engine hash",
          all(a["core"]["engine_sha256"] == b["core"]["engine_sha256"]
              for _, a, b in A.PAIRS))
    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("FAILED:", FAIL)
        sys.exit(2)
    print("ALL PASS")


if __name__ == "__main__":
    main()
