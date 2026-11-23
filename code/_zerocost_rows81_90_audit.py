"""Known-answer audit for the 2026-11-23 rows 81-90 zero-cost control.

Reuses the audited helpers from earlier batches. Every adapter is checked
against an independent fresh-module recomputation with cost constants set by
hand (cbpackf: declared fields, determinism and in-artifact references).
Engine drift in old ranking artifacts is declared, not hidden.

Run:  python code/_zerocost_rows81_90_audit.py ; exit 0 all pass, 2 any fail.
"""
import sys

import _zerocost_rows71_80_audit as B

V = B.V
PASS, FAIL = B.PASS, B.FAIL
check, pair, fresh, art, published, repro_check = (
    B.check, B.pair, B.fresh, B.art, B.published, B.repro_check)


def main():
    # ------------------------------------------------------------- fingrad
    print("\n== fingrad (NEARUSDT 1h, day, funding off in both) ==")
    par = {"preset": "day", "costs": "author", "funding": False}
    base = art("fingrad", "1h", "NEARUSDT", par)
    zero = art("fingrad", "1h", "NEARUSDT", {**par, "costs": "zero"})
    pair(base, zero, "fingrad-NEAR")
    F = fresh("code/fingrad_engine.py", "fg_direct")
    paths = V.ADAPTERS["fingrad"]["inputs"]("1h", "NEARUSDT")
    p = {**par, "tf": "1h"}
    m_direct = F.run_symbol(paths, dict(p))["metrics"]
    check("fingrad BASE == engine with native author block, funding off",
          abs(m_direct["return_pct"] - base["metrics"]["return_pct"]) < 1e-9,
          f"{m_direct['return_pct']} vs {base['metrics']['return_pct']}")
    F2 = fresh("code/fingrad_engine.py", "fg_direct_zero")
    m_zero_direct = F2.run_symbol(paths, {**p, "costs": "zero"})["metrics"]
    check("fingrad ZERO == engine with costs=zero by hand",
          abs(m_zero_direct["return_pct"] - zero["metrics"]["return_pct"]) < 1e-9,
          f"{m_zero_direct['return_pct']} vs {zero['metrics']['return_pct']}")
    check("fingrad ZERO declares 0 bps, funding off, own drag measured",
          zero["metrics"]["fee_bps_per_side"] == 0.0 and
          zero["metrics"]["slip_bps_per_side"] == 0.0 and
          zero["metrics"]["cost_bp_roundtrip"] == 0.0 and
          zero["metrics"]["funding_charged"] is False and
          abs((zero["metrics"]["ret_zero_pct"] - base["metrics"]["return_pct"]) -
              base["metrics"]["drag_pp"]) < 2e-4,
          f"drag_pp {base['metrics']['drag_pp']:.4f}")
    pub = published("b01a057355b758cd")
    repro_check("fingrad BASE vs published", base, "b01a057355b758cd",
                pub["metrics"]["return_pct"], pub["metrics"]["profit_factor"],
                "return_pct", "profit_factor")

    # ------------------------------------------------------------- pack100
    print("\n== pack100 (G82-1h BTCUSDT) ==")
    base = art("pack100", "1h", "BTCUSDT",
               {"strat": "G82-1h", "costs": "repo", "funding": True})
    zcost = art("pack100", "1h", "BTCUSDT",
                {"strat": "G82-1h", "costs": "zero", "funding": True})
    zero = art("pack100", "1h", "BTCUSDT",
               {"strat": "G82-1h", "costs": "zero", "funding": False})
    pair(base, zero, "pack100-G82")
    P = fresh("code/pack100_engine.py", "p100_g82")
    paths = V.ADAPTERS["pack100"]["inputs"]("1h", "BTCUSDT")
    m_direct = P.run_one(paths, {"strat": "G82-1h"})[0]
    check("pack100 G82 BASE == engine with its own REPO constant",
          abs(m_direct["return_pct"] - base["metrics"]["return_pct"]) < 1e-9,
          f"{m_direct['return_pct']} vs {base['metrics']['return_pct']}")
    check("pack100 costs=0 (funding on) == own zero_cost_pf",
          abs(base["metrics"]["zero_cost_pf"] - zcost["metrics"]["pf_pct"]) < 1e-4,
          f"{base['metrics']['zero_cost_pf']} vs {zcost['metrics']['pf_pct']}")
    check("pack100 ZERO declares 0 bps, no funding, zero funding_paid",
          zero["metrics"]["cost_bps_per_side"] == 0.0 and
          zero["metrics"]["funding_charged"] is False and
          zero["metrics"]["funding_paid"] == 0.0)
    pub = published("71850d500d90e1c9")
    repro_check("pack100 G82 BASE vs published", base, "71850d500d90e1c9",
                pub["metrics"]["return_pct"], pub["metrics"]["pf_pct"],
                "return_pct", "pf_pct")

    # ------------------------------------------------------------------ qs
    print("\n== qs (5m long-only ETH and 1h QS-009 ETH) ==")
    for strat, variant, tf, sym, rid in (
            ("QS-001", "long-only", "5m", "ETHUSDT", "5549a39c1cc2dd74"),
            ("QS-009", "two-sided", "1h", "ETHUSDT", "9c98f479349c5b7b")):
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

    # ------------------------------------------------------------- cbpackf
    print("\n== cbpackf (S02 SOLUSDT, S01 SUIUSDT) ==")
    for sid, sym, rid in (("S02", "SOLUSDT", "ded7cca009e13445"),
                          ("S01", "SUIUSDT", "c1f3df39b37c1d2b")):
        base = art("cbpackf", "1h", sym,
                   {"fee_bps": 5.0, "slippage_bps": 0.5, "funding": True})
        zero = art("cbpackf", "1h", sym,
                   {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False})
        pair(base, zero, f"cbpackf-{sid}-{sym}")
        b, z = base["metrics"], zero["metrics"]
        check(f"cbpackf {sid} BASE declares 5.0/0.5, funding on, settlements",
              b["fee_bps_per_side"] == 5.0 and b["slippage_bps_per_side"] == 0.5 and
              b["funding_charged"] is True and b["n_settlements"] > 0)
        check(f"cbpackf {sid} ZERO declares 0/0, funding off, zero settlements",
              z["fee_bps_per_side"] == 0.0 and z["slippage_bps_per_side"] == 0.0 and
              z["funding_charged"] is False and z["n_settlements"] == 0)
        rb = next(r for r in base["tables"] if r.get("id") == sid)
        rz = next(r for r in zero["tables"] if r.get("id") == sid)
        check(f"cbpackf {sid} ZERO row above BASE",
              rz["net_%"] > rb["net_%"] and rz["PF"] > rb["PF"],
              f"{rb['net_%']:.4f}% -> {rz['net_%']:.4f}%")
        pub = published(rid)
        pr = next(r for r in pub["tables"] if r.get("id") == sid)
        repro_check(f"cbpackf {sid} BASE vs published",
                    {"metrics": {"return_pct": rb["net_%"], "profit_factor": rb["PF"]}},
                    rid, pr["net_%"], pr["PF"], "return_pct", "profit_factor")

    # -------------------------------------------------------------- dspack
    print("\n== dspack (four cells: two author mirrors, two costed) ==")
    DS = [
        ("ds3", "BNBUSDT", "author", "b1ce74d87fca38ce"),
        ("ds3", "ADAUSDT", "author", "75f27f3dd6d92914"),
        ("ds1", "AVAXUSDT", "repo6x5", "6d92238c699d176f"),
        ("ds3", "DOGEUSDT", "repo6x5", "014f6c78bcfb02d6"),
    ]
    for strat, sym, pub_cost, rid in DS:
        bpar = {"strat": strat, "costs": pub_cost, "window": "full"}
        zcost = "author" if pub_cost == "repo6x5" else "repo6x5"
        base = art("dspack", "1h", sym, bpar)
        zero = art("dspack", "1h", sym, {**bpar, "costs": zcost})
        if pub_cost == "author":
            # BASE is already the author (zero) book: ZERO is the same artifact
            zero = base
        else:
            pair(base, zero, f"dspack-{strat}-{sym}")
        D = fresh("code/dspack_engine.py", f"dsp_{strat}_{sym}")
        paths = V.ADAPTERS["dspack"]["inputs"]("1h", sym)
        row = D.run_suite(paths, bpar)["tables"][0]
        check(f"dspack {strat} {sym} BASE == engine with its own {pub_cost} preset",
              abs(row["ret_pct"] - base["metrics"]["return_pct"]) < 1e-9,
              f"{row['ret_pct']} vs {base['metrics']['return_pct']}")
        if pub_cost == "author":
            costed = zero  # replaced below with a repo6x5 re-run
            costed = art("dspack", "1h", sym,
                         {"strat": strat, "costs": "repo6x5", "window": "full"})
            t = costed["tables"][0]
            check(f"dspack {strat} {sym} COSTED re-score == author, fees real, same trades",
                  abs(t["ret_zero_pct"] - base["metrics"]["return_pct"]) < 1e-9 and
                  t["fees_charged"] > 0 and t["n_trades"] == base["metrics"]["n_trades"],
                  f"fees {t['fees_charged']:.2f}")
        else:
            t = base["tables"][0]
            check(f"dspack {strat} {sym} BASE zero re-score == author headline, fees real",
                  abs(t["ret_zero_pct"] - zero["metrics"]["return_pct"]) < 1e-9 and
                  t["fees_charged"] > 0 and t["ret_pct"] < zero["metrics"]["return_pct"],
                  f"fees {t['fees_charged']:.2f}")
        pub = published(rid)
        repro_check(f"dspack {strat} {sym} BASE vs published", base, rid,
                    pub["metrics"]["return_pct"], pub["metrics"]["profit_factor"],
                    "return_pct", "profit_factor")

    print("\n== provenance ==")
    check("BASE and ZERO differ in every regime pair",
          all(a["run_id"] != b["run_id"] for _, a, b in B.A.PAIRS) and len(B.A.PAIRS) >= 7,
          f"{len(B.A.PAIRS)} pairs")
    check("every BASE/ZERO pair shares the same engine hash",
          all(a["core"]["engine_sha256"] == b["core"]["engine_sha256"]
              for _, a, b in B.A.PAIRS))
    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("FAILED:", FAIL)
        sys.exit(2)
    print("ALL PASS")


if __name__ == "__main__":
    main()
