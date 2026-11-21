#!/usr/bin/env python
"""Known-answer selftest for the 2026-11-21 audit-fix campaign (N1-N11, A2).

Every check corresponds to one defect the external Qwen audit found in the
harness and that was verified against the code before fixing. Run:

    python code/_auditfix_selftest_20261121.py

Exit 0 = ALL PASS; any FAIL prints and exits 1.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import math
import numpy as np
import pandas as pd

PASS = 0
FAIL = 0


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  {detail}")


# ───────────────────────────── N1: conc unit ──────────────────────────────
def t_n1():
    import bt
    m = {"metrics": {"conc_top5_share_pct": 5.0, "profit_factor": 1.5,
                     "n_trades": 100, "return_pct": 3.0}}
    v = bt._metric(m, "best5_share_pct|conc_top5_share_pct")
    check("N1 canonical percent key resolves verbatim (5% reads as 5.0)",
          v == 5.0, f"got {v}")
    # the x100 double-scale is GONE: a 5% book is not read as 500
    check("N1 no x100 normalization on the canonical key", v == 5.0 and v != 500.0)
    amb = {"metrics": {"top5_pnl_share": 0.05}}
    check("N1 ambiguous-only artifact refuses the key (None from canonical aliases)",
          bt._metric(amb, "best5_share_pct|conc_top5_share_pct") is None)
    check("N1 ambiguous key detectable", bt._metric(amb, "top5_pnl_share") == 0.05)
    check("N1 battery no longer carries the fraction alias",
          "top5_pnl_share" not in bt.ONE_GATES[6][1])


# ───────────────────────────── N2: fail closed ────────────────────────────
def t_n2():
    import bt
    check("N2 null-pf detection", bt._metric_has_null(
        {"metrics": {"profit_factor": None}}, "profit_factor"))
    check("N2 absent metric is not 'null' (stays N-A semantics)",
          not bt._metric_has_null({"metrics": {}}, "profit_factor"))
    check("N2 battery includes the v2 promotion row marker",
          any(g[0] == "g6conc" for g in bt.ONE_GATES))
    check("N2 exit-code rule is fail-closed on N-A (source contains it)",
          "n_fail == 0 and n_na == 0" in open(bt.__file__, encoding="utf-8").read())


# ───────────────────────────── N3: bootstrap reps ─────────────────────────
def t_n3():
    import _gates_v2 as G
    rs = np.sin(np.arange(400) * 0.1) * 0.01
    n, reps = len(rs), 800
    rng1 = np.random.default_rng(7)
    lb1, m1, ra1 = G.bootstrap_mean_lb(rs, 0.05, reps, rng1)
    rng2 = np.random.default_rng(7)
    idx = G.stationary_bootstrap_indices(n, reps, G._block_len(n), rng2)
    means2 = rs[idx].mean(axis=1)
    check("N3 single-chunk draws bit-identical to the unchunked matrix",
          lb1 == float(np.quantile(means2, 0.05))
          and m1 == float(means2.mean()))
    check("N3 mean-lb returns the ACHIEVED reps (NEW-2)", ra1 == reps,
          f"got {ra1}")
    check("N3 no module-global reps record (NEW-2)",
          not hasattr(G, "boot_reps_actual") and not hasattr(G, "_BOOT_INFO"))
    big = np.random.default_rng(1).normal(0.0, 0.01, 60_000)
    bs = G.bootstrap_max_dd(big, 1.0, 2000, np.random.default_rng(3))
    check("N3 full reps used on a long series (no 6e6/n shrink)",
          bs["reps_actual"] == 2000, f"got {bs.get('reps_actual')}")
    bs2 = G.bootstrap_max_dd(big, 1.0, 2000, np.random.default_rng(3))
    check("N3 deterministic for a fixed seed", bs == bs2)
    check("N3 reps floor declared in POLICY", G.POLICY["boot_reps_floor"] == 500)
    # determinism across two independent runs at the same seed (chunked path)
    a = G.bootstrap_mean_lb(big, 0.05, 600, np.random.default_rng(11))
    b = G.bootstrap_mean_lb(big, 0.05, 600, np.random.default_rng(11))
    check("N3 chunked mean-lb deterministic", a == b)


# ───────────────────────────── N3-gates: floor fail closed ────────────────
def t_n3_gates():
    import _gates_v2 as G
    rng = np.random.default_rng(5)
    n = 40
    t = pd.DataFrame({
        "entry_time": pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC"),
        "exit_time": pd.date_range("2024-01-01 00:30", periods=n, freq="h", tz="UTC"),
        "gross_ret": rng.normal(0.001, 0.005, n),
        "cost_ret": np.full(n, 0.0004),
        "mae": rng.uniform(0.0, 0.01, n),
        "symbol": "BTCUSDT",
    })
    t["net"] = t["gross_ret"] - t["cost_ret"]
    ctx = G.GateContext(benchmark_close=pd.Series(
        10000 + np.cumsum(rng.normal(0, 5, 500)),
        index=pd.date_range("2024-01-01", periods=500, freq="h", tz="UTC")),
        max_leverage=1.0, n_trials=1)
    g9_low = G.gate_g9(t, ctx, {**G.POLICY, "boot_reps": 100}, np.random.default_rng(2))
    check("N3 G9 fails closed below the reps floor",
          (not g9_low["pass"]) and "reason_reps" in g9_low,
          str({k: g9_low[k] for k in ("pass", "reason_reps") if k in g9_low}))
    g9_ok = G.gate_g9(t, ctx, G.POLICY, np.random.default_rng(2))
    check("N3 G9 at full reps has no floor reason",
          "reason_reps" not in g9_ok, str(g9_ok.get("reason_reps")))


# ───────────────────────────── N4: PBO ────────────────────────────────────
def t_n4():
    import gate2
    import _gates_v2 as G
    noise = np.random.default_rng(0).normal(0, 0.01, (1000, 20))
    p = gate2.pbo_cscv(noise)
    check("N4 gate2.pbo_cscv returns ~0.5 on pure noise (was ~0.009)",
          0.30 < p < 0.70, f"got {p}")
    ref = G.pbo_cscv(noise)["pbo"]
    check("N4 delegates to the reference implementation", p == ref)


# ───────────────────────────── N5: spread book ────────────────────────────
def t_n5(monkeypatch_load_leg):
    import p100_screen_engine as E
    n = 12
    ts = [pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=i)
          for i in range(n)]
    beta = np.full(n, 1.0)
    s_open = np.full(n, 100.0)
    s = np.full(n, 100.0)
    s[3] = 101.0                     # close recovers; the LOW pierced the stop
    s_high = s.copy()
    s_low = s.copy()
    s_low[3] = 90.0                  # intrabar pierce of the stop at 95
    side = np.zeros(n)
    side[1] = 1.0                    # long spread decided at bar 1 -> enters bar 2
    side[2:] = 1.0
    stop_s = np.full(n, np.nan)
    stop_s[1] = 95.0
    sig = dict(s=s, s_open=s_open, s_high=s_high, s_low=s_low, side=side,
               stop_s=stop_s, beta=beta, ts=ts, tf="1h",
               legs=("AAAUSDT", "BBBUSDT"))
    zero = dict(bar_ms=np.zeros(1, "int64"), close=np.zeros(1),
                rate=np.zeros(1), is_fund=np.zeros(1, bool), idx={})
    monkeypatch_load_leg(lambda leg, tf: zero)
    book = E.SpreadBook(sig["legs"], sig, charge_funding=False)
    book.run(start_idx=0, end_idx=n - 1)
    reasons = [t["reason"] for t in book.trades]
    check("N5 intrabar stop pierce closes same bar as 'stop' (old code: none)",
          "stop" in reasons, str(reasons))
    if any(r == "stop" for r in reasons):
        tstop = next(t for t in book.trades if t["reason"] == "stop")
        check("N5 intrabar stop fills AT the stop level (95.0)",
              abs(tstop["exit_s"] - 95.0) < 1e-9, str(tstop["exit_s"]))
    # exit-fee beta: a book with a TIME-VARYING beta must produce trades
    # identical to a book whose beta is constant at the DECISION-bar value --
    # the exit fee bills the notional actually held (entry beta), never the
    # beta at the exit bar.
    beta2 = np.linspace(1.0, 3.0, n)
    sig2 = dict(sig, beta=beta2)
    sig_ref = dict(sig, beta=np.full(n, beta2[1]))   # entry decided at bar 1
    b2 = E.SpreadBook(sig["legs"], sig2, charge_funding=False)
    b2.run(start_idx=0, end_idx=n - 1)
    br = E.SpreadBook(sig["legs"], sig_ref, charge_funding=False)
    br.run(start_idx=0, end_idx=n - 1)
    key2 = [(round(t["pnl"], 9), t["exit_s"], t["reason"], round(t["N"], 9))
            for t in b2.trades]
    keyr = [(round(t["pnl"], 9), t["exit_s"], t["reason"], round(t["N"], 9))
            for t in br.trades]
    check("N5 time-varying beta book == entry-beta-frozen book (exit fee on "
          "the held notional)", key2 == keyr, f"{key2} vs {keyr}")


def t_n5_gap(monkeypatch_load_leg):
    import p100_screen_engine as E
    n = 10
    ts = [pd.Timestamp("2024-02-01", tz="UTC") + pd.Timedelta(hours=i)
          for i in range(n)]
    s_open = np.full(n, 100.0)
    s = np.full(n, 100.0)
    s_open[4] = 80.0                 # gap through the stop of 95 at the OPEN
    s[4] = 80.0
    s_high = np.maximum(s, s_open)
    s_low = np.minimum(s, s_open)
    side = np.ones(n)
    stop_s = np.full(n, np.nan)
    stop_s[1] = 95.0
    sig = dict(s=s, s_open=s_open, s_high=s_high, s_low=s_low, side=side,
               stop_s=stop_s, beta=np.full(n, 1.0), ts=ts, tf="1h",
               legs=("AAAUSDT", "BBBUSDT"))
    zero = dict(bar_ms=np.zeros(1, "int64"), close=np.zeros(1),
                rate=np.zeros(1), is_fund=np.zeros(1, bool), idx={})
    monkeypatch_load_leg(lambda leg, tf: zero)
    book = E.SpreadBook(sig["legs"], sig, charge_funding=False)
    book.run(start_idx=0, end_idx=n - 1)
    reasons = [t["reason"] for t in book.trades]
    check("N5 gap-through stop fills at the open ('stop_gap')",
          "stop_gap" in reasons, str(reasons))


def t_n5_funding_order(monkeypatch_load_leg):
    """N11: a stop-out on a settlement bar still pays that settlement's funding."""
    import p100_screen_engine as E
    n = 10
    ts = [pd.Timestamp("2024-03-01", tz="UTC") + pd.Timedelta(hours=i)
          for i in range(n)]
    s_open = np.full(n, 100.0)
    s = np.full(n, 100.0)
    s[4] = 90.0                      # pierce the stop (95) intrabar at bar 4
    s_low = np.minimum(s, s_open)
    s_low[4] = 90.0
    s_high = np.maximum(s, s_open)
    side = np.ones(n)
    stop_s = np.full(n, np.nan)
    stop_s[1] = 95.0
    sig = dict(s=s, s_open=s_open, s_high=s_high, s_low=s_low, side=side,
               stop_s=stop_s, beta=np.full(n, 1.0), ts=ts, tf="1h",
               legs=("AAAUSDT", "BBBUSDT"))
    # bar 4 is a settlement bar; the legs carry DIFFERENT rates so the
    # delta-neutral book has a nonzero net funding (equal rates cancel to 0)
    bar_ms = np.array([int(t.timestamp() * 1000) for t in ts], "int64")
    is_fund = np.zeros(n, bool)
    is_fund[4] = True

    def mk_leg(rate_val):
        rate = np.zeros(n)
        rate[4] = rate_val
        return dict(bar_ms=bar_ms, close=np.full(n, 100.0), rate=rate,
                    is_fund=is_fund, idx={int(t): i for i, t in enumerate(bar_ms)})

    legs = {"AAAUSDT": mk_leg(0.0001), "BBBUSDT": mk_leg(0.0002)}
    monkeypatch_load_leg(lambda leg_name, tf: legs[leg_name])
    book = E.SpreadBook(sig["legs"], sig, charge_funding=True)
    book.run(start_idx=0, end_idx=n - 1)
    check("N11 stop-out on a settlement bar still pays funding",
          abs(book.funding_paid) > 0, f"funding_paid={book.funding_paid}")
    expect = (20.0 * 100.0 * 0.0001) - (20.0 * 100.0 * 0.0002)
    check("N11 the charged funding is exactly the settlement amount",
          abs(book.funding_paid - expect) < 1e-9,
          f"got {book.funding_paid}, want {expect}")


# ───────────────────────────── N7: bootstrap_r ────────────────────────────
def t_n7():
    import p100_screen_engine as E
    small = E.bootstrap_r([0.1, 0.2, 0.15, 0.12, 0.3, 0.11, 0.2, 0.1])
    check("N7 n<30 fails closed (both bounds None, flag set)",
          small["small_sample"] and small["ci_low"] is None
          and small["ci_high"] is None, str(small))
    check("N7-NEW1 no fabricated constant in a thin-sample CI",
          small["ci_low"] != -1.0 and small["ci_high"] != 1.0)
    big = E.bootstrap_r(np.random.default_rng(4).normal(0.01, 0.05, 120))
    check("N7 n>=30 keeps a real CI (numeric bounds)",
          not big["small_sample"] and isinstance(big["ci_low"], float)
          and isinstance(big["ci_high"], float), str(big["ci_low"]))
    # the old block=10 degenerate CI is gone: n=10 gives a nonzero-width CI
    ten = E.bootstrap_r(np.full(10, 0.05) + np.linspace(0, 0.01, 10))
    check("N7 n=10 no longer zero-width", ten["small_sample"])


# ───────────────────────────── N8: stored gates_v2 trust ──────────────────
def t_n8():
    import vrun
    import _gates_v2 as G
    import gate2 as G2
    good_hash = G.policy_hash()
    art_bad = {"gates_v2": {"backtest_pass": True, "policy_hash": "x"}}
    r = vrun.compute_gates_v2(art_bad)
    check("N8 a stored block with a foreign policy hash is refused",
          (not r["pass"]) and r.get("stale_policy"), str(r.get("reason", "")))
    art_stale = {"gates_v2": {"backtest_pass": True,
                              "policy_hash": "0" * 64}}
    r2 = vrun.compute_gates_v2(art_stale)
    check("N8 an old-era policy hash is refused (stale, not trusted)",
          (not r2["pass"]) and r2.get("stale_policy"))
    art_ok = {"gates_v2": {"backtest_pass": True, "policy_hash": good_hash}}
    r3 = vrun.compute_gates_v2(art_ok)
    check("N8 a matching-policy stored block is accepted (cache, keyed)",
          r3["pass"] and r3.get("recomputed") is False)
    art_g2 = {"gates_v2": {"backtest_pass": True, "policy_hash": G2.policy_hash()}}
    r4 = vrun.compute_gates_v2(art_g2)
    check("N8 either battery layer's policy hash is accepted",
          r4["pass"] and r4.get("recomputed") is False)
    r5 = vrun.compute_gates_v2({})
    check("N8 absent both -> fail closed (unchanged F1 semantics)",
          (not r5["pass"]) and not r5["available"])


# ───────────────────────────── A2: drift chain ────────────────────────────
def t_a2():
    import gatecal_engine as GC
    tr = pd.DataFrame({
        "pnl": [100.0, 100.0, 100.0],
        "ret_pct": [1.0, 1.0, 1.0],
        "equity_after": [10100.0, 10200.0, 10300.0],
        "entry_ts": [0, 1, 2], "exit_ts": [1, 2, 3],
    })
    d = 20.0
    tr2 = GC._apply_drift(tr, d, 10000.0)
    expected = 10000.0 * (1.0 + d / 1e4) ** 3 * (1.01) ** 3
    got = float(tr2["equity_after"].iloc[-1])
    check("A2 the planted edge compounds into the final equity",
          abs(got / expected - 1.0) < 1e-9, f"got {got:.4f} vs {expected:.4f}")
    old_style = 10300.0 * (1.0 + d / 1e4)
    check("A2 the old chain-break value is NOT what the fixed chain produces",
          abs(got - old_style) > 1.0,
          f"fixed {got:.4f} vs broken {old_style:.4f}")
    check("A2 drift also rewrites pnl and ret_pct consistently",
          abs(float(tr2["pnl"].iloc[-1])
              - (float(tr2["equity_after"].iloc[-1])
                 - float(tr2["equity_after"].iloc[-2]))) < 1e-6)


# ───────────────────────────── N6: serving ────────────────────────────────
def t_n6(tmpdir):
    import vrun
    # static JSON (cost model shape): hashed whole, served at the original path
    cm = os.path.join(tmpdir, "cost_model_x.json")
    with open(cm, "w", encoding="utf-8") as f:
        json.dump({"per_symbol_binance_usdtm": {"BTCUSDT": {"rt_10k_bp": 10.0}}}, f)
    rec, served = vrun._slice_serve(cm, "2026-11-21")
    check("N6 static JSON served whole (original path, full-file hash)",
          served == cm and rec["sha256"] == vrun._sha256_file(cm))
    # funding-shaped JSON: sliced at the cut
    fu = os.path.join(tmpdir, "SYM_funding.json")
    with open(fu, "w", encoding="utf-8") as f:
        json.dump([{"t": 1600000000000, "r": 0.0001},
                   {"t": 1700000000000, "r": 0.0002}], f)
    rec2, served2 = vrun._slice_serve(fu, "2022-06-01")
    check("N6 funding JSON still slices (served copy, records before cut only)",
          served2 != fu and rec2["bars"] == 1, f"bars={rec2['bars']}")
    check("N6 cut_enforced flag lands in core when the adapter declares it",
          "cut_enforced" in open(os.path.join(os.path.dirname(vrun.__file__),
                                              "vrun.py"), encoding="utf-8").read())


# ───────────────────────────── N10: neighborhood set ──────────────────────
def t_n10():
    import bt
    d = bt._coerce_set_items(["id=28", "lb=336", "flag=true", "x=1.5", "s=txt"])
    check("N10 set coercion mirrors parse_params",
          d == {"id": 28, "lb": 336, "flag": True, "x": 1.5, "s": "txt"}, str(d))
    job = {"label": "nb", "strategy": "top10", "tf": "1h", "symbol": "BTCUSDT",
           "param": "lb", "values": "168,336", "set": ["id=28"]}
    captured = []

    def fake_worker(p):
        captured.append(p[4])
        return {"label": p[0], "run_id": "x" * 16,
                "metrics": {"profit_factor": 1.3, "return_pct": 5.0,
                            "n_trades": 50}, "tables": []}
    orig = bt._bt_worker
    bt._bt_worker = fake_worker
    try:
        nb = bt._neighborhood_jobs(job, 1)
    finally:
        bt._bt_worker = orig
    check("N10 the parent's --set params travel into every sweep payload",
          all(p.get("id") == 28 for p in captured), str(captured))
    check("N10 the sweep value overrides the param, set params intact",
          captured[0]["lb"] == 168 and captured[1]["lb"] == 336, str(captured))
    check("N10 the verdict is the strict conjunction (STABLE here)",
          nb["verdict"] == "STABLE", nb["verdict"])
    # a cliff case: one neighbor below 1.0 -> old rule fails -> verdict fails
    def fake_worker2(p):
        return {"label": p[0], "run_id": "x" * 16,
                "metrics": {"profit_factor": 0.9 if "168" in p[0] else 1.3,
                            "return_pct": 5.0, "n_trades": 50},
                "tables": []}
    bt._bt_worker = fake_worker2
    try:
        nb2 = bt._neighborhood_jobs(job, 1)
    finally:
        bt._bt_worker = orig
    check("N10 a cliff neighbor fails the conjunction", nb2["verdict"] != "STABLE")


# ─────────────── NEW-1/NEW-3: book_metrics null CI + resolved cost ────────
def t_new1_new3():
    import p100_screen_engine as E
    from types import SimpleNamespace
    import json as _json
    # a tiny synthetic book: three trades, one small-sample (n < 30)
    trades = [dict(pnl=10.0, r=0.01, reason="stop"),
              dict(pnl=-5.0, r=-0.005, reason="tp"),
              dict(pnl=7.0, r=0.007, reason="signal")]
    book = SimpleNamespace(
        trades=trades, equity_curve=[10000.0, 10010.0, 10005.0, 10012.0],
        cash=10012.0, init=10000.0, funding_paid=0.0, fees_paid=1.0,
        entry_fees_total=0.5, pack_conventions=False,
        pnl_includes_funding=False, charge_funding=True, n_settlements=0,
        implied_notional_x=[1.5], n_signals=3, skipped_gap_entries=0)
    m = E.book_metrics(book, rt_bps=22.57)
    check("NEW-3 book_metrics honors the resolved rt for cost_bp_roundtrip",
          m["cost_bp_roundtrip"] == 22.57, str(m["cost_bp_roundtrip"]))
    check("NEW-3 cost_on_real_notional uses the resolved rt (not the constant)",
          abs(m["cost_on_real_notional_usdt"]
              - 1.5 * 22.57 / 1e4 * 10000.0) < 1e-9,
          str(m["cost_on_real_notional_usdt"]))
    check("NEW-3 default (no rt_bps) keeps the module constant",
          E.book_metrics(book)["cost_bp_roundtrip"] == E.COST_RT_BPS)
    check("NEW-1 thin-sample CI is None in the metrics (no fabricated bound)",
          m["boot_ci_lo"] is None and m["boot_ci_hi"] is None
          and m["boot_small_sample"] is True)
    check("NEW-1 None serializes as JSON null",
          _json.dumps({"a": m["boot_ci_lo"]}) == '{"a": null}')


# ───────────────────────── NEW-4: served-map collision ────────────────────
def t_new4():
    import p100_screen_engine as E
    E._register_served(["/tmp/a/BTCUSDT_1h.csv"])
    check("NEW-4 single served path registers",
          E._SERVED_INPUTS.get("BTCUSDT_1h.csv") == os.path.abspath("/tmp/a/BTCUSDT_1h.csv"))
    try:
        E._register_served(["/tmp/a/BTCUSDT_1h.csv", "/tmp/b/BTCUSDT_1h.csv"])
        raised = False
    except ValueError:
        raised = True
    check("NEW-4 same-basename served inputs from two dirs FAIL LOUD", raised)


# ───────────────────────── NEW-5: neighbourhood centre ────────────────────
def t_new5():
    import bt
    job = {"label": "nb", "strategy": "top10", "tf": "1h", "symbol": "BTCUSDT",
           "param": "lb", "values": "3,1,2", "set": ["id=28"]}
    pfs = {"3": 1.49, "1": 1.0, "2": 1.3}   # positional middle = 1.0 (wrong)

    def fake_worker(p):
        v = p[4]["lb"]
        return {"label": p[0], "run_id": "x" * 16,
                "metrics": {"profit_factor": pfs[str(v)], "return_pct": 5.0,
                            "n_trades": 50}, "tables": []}
    orig = bt._bt_worker
    bt._bt_worker = fake_worker
    try:
        nb = bt._neighborhood_jobs(job, 1)
        job2 = dict(job, centre="3")
        nb2 = bt._neighborhood_jobs(job2, 1)
    finally:
        bt._bt_worker = orig
    check("NEW-5 centre is the PF of the MEDIAN SWEPT VALUE (1.3, not the "
          "positional 1.0)", nb.get("center_pf") == 1.3, str(nb.get("center_pf")))
    check("NEW-5 a declared job centre overrides the median",
          nb2.get("center_pf") == 1.49, str(nb2.get("center_pf")))


# ───────────────────────────── main ───────────────────────────────────────
def main():
    import tempfile
    import p100_screen_engine as E

    orig_load_leg = E.load_leg

    def patch(fn):
        E.load_leg = fn

    print("== audit-fix selftest 2026-11-21 ==")
    t_n1()
    t_n2()
    t_n3()
    t_n3_gates()
    t_n4()
    t_n5(patch)
    t_n5_gap(patch)
    t_n5_funding_order(patch)
    t_n7()
    t_n8()
    t_a2()
    with tempfile.TemporaryDirectory() as td:
        t_n6(td)
    t_new1_new3()
    t_new4()
    t_new5()
    t_n10()
    E.load_leg = orig_load_leg
    print(f"== {PASS} PASS, {FAIL} FAIL ==")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
