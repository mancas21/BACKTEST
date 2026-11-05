"""
_gates_v2_selftest.py -- checks that the gate machinery itself behaves.

Everything here runs on SYNTHETIC data (seeded GBM). Nothing printed by this file
is a market result, carries a run_id, or may be cited in a results table.
Run:  python code/_gates_v2_selftest.py
"""
import json
import os
import sys
import tempfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _gates_v2 as G  # noqa: E402

_fails = []


def check(name, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   [{extra}]" if extra else ""))
    if not cond:
        _fails.append(name)


def synth_ohlc(n=26280, vol_annual=0.70, seed=11, tf="1h"):
    rng = np.random.default_rng(seed)
    sig = vol_annual / np.sqrt(8760.0)
    r = rng.normal(0, sig, n)
    close = 100.0 * np.exp(np.cumsum(r))
    open_ = np.concatenate([[100.0], close[:-1]])
    spread = np.abs(rng.normal(0, sig * 0.6, n))
    high = np.maximum(open_, close) * (1 + spread)
    low = np.minimum(open_, close) * (1 - spread)
    idx = pd.date_range("2023-01-01", periods=n, freq=tf, tz="UTC")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close,
                         "volume": rng.uniform(1, 2, n)}, index=idx)


# --- basic statistics ------------------------------------------------------- #
check("profit_factor known value", abs(G.profit_factor([3, -1, 2, -1]) - 2.5) < 1e-12)
check("profit_factor no losers", G.profit_factor([1, 2]) == float("inf"))

rng = np.random.default_rng(1)
pos = rng.normal(0.004, 0.02, 300)
zero = rng.normal(0.0, 0.02, 300)
lb_pos, _ = G.bootstrap_mean_lb(pos, 0.05, 800, np.random.default_rng(2))
lb_zero, _ = G.bootstrap_mean_lb(zero, 0.05, 800, np.random.default_rng(2))
check("bootstrap LB > 0 for a real edge", lb_pos > 0, f"lb={lb_pos:.5f}")
check("bootstrap LB <= 0 for zero-mean noise", lb_zero <= 0, f"lb={lb_zero:.5f}")

# --- DSR / PBO -------------------------------------------------------------- #
r = np.random.default_rng(3).normal(0.001, 0.01, 1000)
d1 = G.deflated_sharpe(r, 1)["dsr"]
d150 = G.deflated_sharpe(r, 150)["dsr"]
d1000 = G.deflated_sharpe(r, 1000)["dsr"]
check("DSR falls as trial count rises", d1 > d150 > d1000, f"{d1:.3f} > {d150:.3f} > {d1000:.3f}")

# PBO from ONE noise matrix is very noisy (observed 0.12-0.92 across seeds), so the
# noise baseline is checked on the mean over many independent matrices.
noise_pbo = [G.pbo_cscv(np.random.default_rng(100 + s).normal(0, 0.01, (480, 20)), 16)["pbo"]
             for s in range(30)]
noise = np.random.default_rng(4).normal(0, 0.01, (480, 20))
planted = noise.copy()
planted[:, 0] += 0.004
pb_plant = G.pbo_cscv(planted, 16)["pbo"]
check("PBO averages near 0.5 on pure noise (30 matrices)", 0.35 <= float(np.mean(noise_pbo)) <= 0.70,
      f"mean={np.mean(noise_pbo):.2f} range={min(noise_pbo):.2f}-{max(noise_pbo):.2f}")
check("PBO low when one column has a persistent edge", pb_plant < 0.15, f"pbo={pb_plant:.2f}")

# --- look-ahead audit ------------------------------------------------------- #
df = synth_ohlc(4000, seed=5)
causal = lambda d: d["close"].rolling(20).mean() - d["close"].rolling(50).mean()      # noqa: E731
leaky = lambda d: d["close"].rolling(21, center=True).mean() - d["close"]               # noqa: E731
zleak = lambda d: (d["close"] - d["close"].mean()) / d["close"].std()                   # noqa: E731
check("truncation test passes a causal signal", G.truncation_invariance(causal, df)["pass"])
check("truncation test catches a centered window", not G.truncation_invariance(leaky, df)["pass"])
check("truncation test catches whole-sample normalisation", not G.truncation_invariance(zleak, df)["pass"])

ltf_idx = pd.date_range("2024-01-01", periods=16, freq="15min", tz="UTC")
htf_idx = pd.date_range("2024-01-01", periods=4, freq="1h", tz="UTC")
ltf = pd.DataFrame({"x": 0.0}, index=ltf_idx)
htf = pd.DataFrame({"h": np.arange(4, dtype=float)}, index=htf_idx)
al = G.align_htf_last_closed(ltf, htf, pd.Timedelta("15min"), pd.Timedelta("1h"), ["h"])
# LTF bar opening 00:45 closes 01:00 -> HTF bar 00:00 (closes 01:00) is known; 00:30 bar is not
check("HTF alignment: not visible before it closes", np.isnan(al.loc["2024-01-01 00:30", "h"]))
check("HTF alignment: visible on the bar that closes with it", al.loc["2024-01-01 00:45", "h"] == 0.0)
check("HTF alignment: next HTF bar waits for its own close", al.loc["2024-01-01 01:30", "h"] == 0.0
      and al.loc["2024-01-01 01:45", "h"] == 1.0)

# --- data integrity --------------------------------------------------------- #
clean = synth_ohlc(2000, seed=6)
check("integrity passes clean data", G.data_integrity_report(clean, 60)["pass"])
broken = pd.concat([clean.iloc[:500], clean.iloc[520:]])          # 20-bar gap
check("integrity flags a gap", not G.data_integrity_report(broken, 60)["pass"])
dup = pd.concat([clean, clean.iloc[[10]]]).sort_index()
check("integrity flags duplicate bars", G.data_integrity_report(dup, 60)["duplicates"] == 1)
fi = G.infer_funding_intervals(pd.Series(list(pd.date_range("2024-01-01", periods=6, freq="8h", tz="UTC"))
                                         + list(pd.date_range("2024-01-03 00:00", periods=6, freq="4h", tz="UTC"))))
check("funding interval change detected", fi["n_changes"] >= 1 and fi["modal_hours"] in (4.0, 8.0))

# --- chains ----------------------------------------------------------------- #
with tempfile.TemporaryDirectory() as td:
    runs = os.path.join(td, "runs")
    os.makedirs(runs)
    chain = os.path.join(runs, "CHAIN.jsonl")
    for i in range(3):
        p = os.path.join(runs, f"a{i}.json")
        json.dump({"i": i}, open(p, "w"))
        G.chain_append(chain, p)
    ok, bad = G.chain_verify(chain, runs)
    check("artifact chain verifies untouched", ok, str(bad))
    json.dump({"i": 99}, open(os.path.join(runs, "a1.json"), "w"))
    ok2, bad2 = G.chain_verify(chain, runs)
    check("artifact chain detects an edited artifact", not ok2 and any("a1.json" in b for b in bad2))

    led = G.TrialLedger(os.path.join(td, "ledger.jsonl"))
    led.register("pack50", "run_aaa", 50, sr_daily=0.02)
    led.register("pack50b", "run_bbb", 50, sr_daily=0.03)
    dup_added = led.register("pack50", "run_aaa", 50)
    check("ledger counts variants and ignores a re-run", led.total_trials() == 100 and not dup_added)
    check("ledger chain verifies", led.verify()[0])
    lines = open(led.path).read().splitlines()
    tampered = json.loads(lines[0])
    tampered["n_variants"] = 1
    lines[0] = json.dumps(tampered)
    open(led.path, "w").write("\n".join(lines) + "\n")
    check("ledger detects tampering", not led.verify()[0])

# --- costs ------------------------------------------------------------------ #
model = {"BTCUSDT": 10.0, "THINUSDT": 30.5}
ok_btc, e_btc = G.admit_declared_costs(5.0, 0.5, "BTCUSDT", model)
ok_thin_default, _ = G.admit_declared_costs(5.0, 0.5, "THINUSDT", model)
ok_thin_real, e_thin = G.admit_declared_costs(5.0, 10.25, "THINUSDT", model)
check("scanner admits default cost where measured <= default", ok_btc and e_btc["rt_bps"] == 11.0)
check("scanner rejects default cost on a thin name", not ok_thin_default)
check("scanner admits the measured cost on a thin name", ok_thin_real and e_thin["rt_bps"] == 30.5)
check("slippage grows with size and on stops",
      G.slippage_per_side_bps(1e6) > G.slippage_per_side_bps(1e4)
      and G.slippage_per_side_bps(1e4, is_stop=True) > G.slippage_per_side_bps(1e4))

# --- fidelity helpers ------------------------------------------------------- #
m = G.maker_fill_mask(np.array([1, 1, -1, -1]), np.array([100.0] * 4),
                      np.array([101.0, 101.0, 100.0, 100.2]), np.array([99.9, 100.0, 99.0, 99.0]),
                      tick=0.1, ticks_through=1)
check("maker fill needs trade-through, touch is not a fill", list(m) == [True, False, False, True])
check("adverse-first path for a long visits the low first",
      G.adverse_first_path(100, 105, 95, 102, 1) == [100, 95, 105, 102])

# --- gate machinery: null vs planted edge (SYNTHETIC) ----------------------- #
px = synth_ohlc(26280, seed=21)
ctx = G.GateContext(benchmark_close=px["close"], max_leverage=5.0, n_trials=1)
holds = list(range(4, 25))
null1 = G.null_calibration(px, 150, holds, ctx, n_sims=60, seed=31, reps=300)
check("null books almost never clear G1-G9 (no multiple-testing penalty)",
      null1["pass_rate_joint"] <= 0.10, f"joint={null1['pass_rate_joint']:.3f} upper95={null1['upper95_joint']:.3f}")

strong = G.null_calibration(px, 150, holds, ctx, n_sims=40, seed=32, reps=300, edge_bps=100.0)
check("a large planted edge clears G1-G9 most of the time", strong["pass_rate_joint"] >= 0.70,
      f"joint={strong['pass_rate_joint']:.2f} by gate={strong['pass_rate_by_gate']}")

ctx150 = G.GateContext(benchmark_close=px["close"], max_leverage=5.0, n_trials=150)
null150 = G.null_calibration(px, 150, holds, ctx150, n_sims=40, seed=33, reps=300, k_candidates=150)
check("with 150 trials the null joint pass-rate stays near zero", null150["pass_rate_joint"] <= 0.05,
      f"joint={null150['pass_rate_joint']:.3f}")

# --- fail-closed behaviour -------------------------------------------------- #
tr = G.random_entry_trades(px, 150, holds, np.random.default_rng(5), edge_bps=100.0)
res_noledger = G.evaluate_gates_v2(tr, G.GateContext(benchmark_close=px["close"], max_leverage=5.0))
check("no trial ledger -> G7 fails closed", res_noledger["gates"]["G7"]["pass"] is False)
res_nolev = G.evaluate_gates_v2(tr, G.GateContext(benchmark_close=px["close"], n_trials=1))
check("no declared leverage -> G9 fails closed", res_nolev["gates"]["G9"]["pass"] is False)
grid_ctx = G.GateContext(benchmark_close=px["close"], max_leverage=5.0, n_trials=1, inventory_book=True)
check("inventory book without MTM equity -> G9 fails closed",
      G.evaluate_gates_v2(tr, grid_ctx)["gates"]["G9"]["pass"] is False)
check("G10 stays PENDING without a forward run, so nothing is 'cleared'",
      res_noledger["gates"]["G10"]["pass"] is None and res_noledger["cleared"] is False)

# --- neighborhood ----------------------------------------------------------- #
axes = [[1, 2, 3], [10, 20, 30]]
good = {(a, b): {"pf": 1.3, "g1": True, "g3": True} for a in axes[0] for b in axes[1]}
spike = {k: {"pf": 0.9, "g1": False, "g3": False} for k in good}
spike[(2, 20)] = {"pf": 2.0, "g1": True, "g3": True}
check("neighborhood passes a plateau", G.neighborhood_check(good, (2, 20), axes)["pass"])
check("neighborhood rejects a lone spike", not G.neighborhood_check(spike, (2, 20), axes)["pass"])

print()
if _fails:
    print(f"{len(_fails)} FAILED: {_fails}")
    sys.exit(1)
print("all self-tests passed")
