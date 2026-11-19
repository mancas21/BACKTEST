#!/usr/bin/env python
"""_validate_spread_v2.py -- full G1-G11 battery on the SPREAD candidate id=85
(mid-day-lull mean-reversion, HYPE/SOL Kalman-beta z-score spread), the standout
of TOP_OOS_ROBUST.md (OOS PF 3.10, n=383).

The SpreadBook is a discrete two-leg book with LINEARISED spread PnL
N*side*(exit_s-entry_s) and exchange notional N*(priceA+beta*priceB). Its trades
are not persisted in the artifact, so this re-runs run_pair with an IN-MEMORY
instrumented subclass (no engine file edited) that captures gross/fees/funding/
notional/MAE per trade at close, verifies DEV parity against the stored artifact,
builds the v2 fixed-size schema (fractions of EXCHANGE notional) and runs
evaluate_gates_v2 as a NEUTRAL book (benchmark = cash, bh = 0).

CAVEAT declared: the exchange notional/equity (real leverage) far exceeds the
book's N-cap max_leverage; G9's liquidation model is per-trade MAE, not per-leg
margin. Output: results/CANDIDATE_SPREAD_V2.md / .json
"""
from __future__ import annotations
import json, os, sys, importlib.util, math
import numpy as np, pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, "code"); RUNS = os.path.join(ROOT, "results", "runs")
sys.path.insert(0, CODE)
def _load(name, fn):
    spec = importlib.util.spec_from_file_location(name, os.path.join(CODE, fn))
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m
    spec.loader.exec_module(m); return m
p100 = _load("p100_sp", "p100_screen_engine.py")
gv2 = _load("gates_sp", "_gates_v2.py")
def num(x):
    try:
        v = float(x); return v if math.isfinite(v) else None
    except (TypeError, ValueError): return None

ledger = gv2.TrialLedger(os.path.join(ROOT, "results", "_trial_ledger.jsonl"))
try: N_TRIALS = int(ledger.total_trials())
except Exception: N_TRIALS = 1486

# ── instrumented SpreadBook: capture the v2 decomposition at close ──
class InstrSpreadBook(p100.SpreadBook):
    def _funding_cost(self, j):
        c = super()._funding_cost(j)
        if self.pos is not None and c:
            self.pos["_fund"] = self.pos.get("_fund", 0.0) + c
        return c
    def _close(self, idx, exit_s, reason):
        p = self.pos; extra = None
        if p is not None:
            ei = p["entry_idx"]; N = p["N"]; side = p["side"]
            gross = N * side * (exit_s - p["entry_s"])
            cps = self._cost_per_side()
            fee_e = N * (1 + p["beta"]) * cps
            fee_x = N * (1 + self._beta_at(idx)) * cps
            notional = self._exchange_notional(ei)   # pos still set
            fund = p.get("_fund", 0.0)
            adv = max(-(N * side * (self.s[k] - p["entry_s"])) for k in range(ei, idx + 1))
            mae = max(adv, 0.0) / notional if notional else 0.0
            extra = dict(_gross=gross, _fee_e=fee_e, _fee_x=fee_x,
                         _notional=notional, _fund=fund, _mae=mae)
        t = super()._close(idx, exit_s, reason)
        if t is not None and extra:
            t.update(extra)
        return t

# allow FULL segment for the pair book (engine only defines DEV/OOS)
_orig_seg = p100._segment_bounds_idx
def _seg(ts_list, segment):
    if segment == "FULL":
        return dict(start=0, end=len(ts_list) - 1, trade_from=0, trade_to=len(ts_list) - 1)
    return _orig_seg(ts_list, segment)
p100._segment_bounds_idx = _seg
_orig_sb = p100.SpreadBook
p100.SpreadBook = InstrSpreadBook

def spread_schema(book, sym):
    rows = []; lev = []
    eq = np.asarray(book.equity_curve, float)
    for t in book.trades:
        nt = t.get("_notional")
        if not nt or nt <= 0:
            continue
        s = 1 if t["side"] == "long" else -1
        gross = t["_gross"] / nt
        cost = (t["_fee_e"] + t["_fee_x"]) / nt
        fund = t["_fund"] / nt
        rows.append(dict(entry_time=pd.Timestamp(t["entry_time"]),
                         exit_time=pd.Timestamp(t["exit_time"]), symbol=sym, side=s,
                         gross_ret=gross, cost_ret=cost, funding_ret=fund,
                         mae=float(t["_mae"]), exit_reason=t["reason"]))
        ei = t["entry_idx"]
        if ei < len(eq) and eq[ei] > 0:
            lev.append(nt / eq[ei])
    df = pd.DataFrame(rows)
    npe = float(np.median(lev)) if lev else 1.0
    return df, npe, (float(np.median(lev)) if lev else 0.0)

def parity(book, art_m):
    pn = np.array([t["pnl"] for t in book.trades], float); n = len(pn)
    gp = float(pn[pn > 0].sum()); gl = float(-pn[pn < 0].sum())
    pf = gp / gl if gl > 0 else (None if gp > 0 else 0.0)
    net = (book.cash / book.init - 1) * 100
    apf, an, aret = num(art_m.get("profit_factor")), num(art_m.get("n_trades")), num(art_m.get("return_pct"))
    ok = (an is not None and n == int(an) and apf is not None and pf is not None
          and abs(pf - apf) <= max(1e-6, abs(apf) * 1e-6)
          and aret is not None and abs(net - aret) <= max(1e-4, abs(aret) * 1e-6))
    return dict(n=n, pf=pf, net=net, art_n=an, art_pf=apf, art_ret=aret, parity=bool(ok))

# ── candidate id=85 ──
robust = json.load(open(os.path.join(ROOT, "results", "top_oos_robust.json"), encoding="utf-8"))["robust"]
cand = next(c for c in robust if c["family"] == "p100screen" and "mid-day" in c["strategy"])
art = json.load(open(os.path.join(RUNS, cand["run_id"] + ".json"), encoding="utf-8"))
sid = int(art["params"]["id"]); sym = art["symbol"]; tf = art["timeframe"]
bdev, _ = p100.run_pair(sid, sym, tf, "DEV", charge_funding=True, pack_conventions=False)
par = parity(bdev, art["metrics"])
bfull, sig = p100.run_pair(sid, sym, tf, "FULL", charge_funding=True, pack_conventions=False)
schema, npe, med_lev = spread_schema(bfull, sym)
ts = pd.to_datetime(pd.Series(bfull.ts), utc=True)
eq = np.asarray(bfull.equity_curve, float)
mtm = pd.Series(eq, index=ts.iloc[:len(eq)])
cash_bench = pd.Series(1.0, index=ts)   # neutral book benchmark = cash
ctx = gv2.GateContext(benchmark_close=cash_bench, bh_total_return=0.0, book_type="neutral",
                      inventory_book=False, equity_mtm=mtm, notional_per_equity=npe,
                      max_leverage=float(bfull.max_leverage), mmr=0.005, n_trials=N_TRIALS,
                      start_equity_usd=float(bfull.init), fee_bps=bfull.fee * 1e4, slip_bps=bfull.slip * 1e4)
ev = gv2.evaluate_gates_v2(schema, ctx)
p100.SpreadBook = _orig_sb; p100._segment_bounds_idx = _orig_seg

res = dict(strategy=cand["strategy"], sid=sid, legs=list(sig["legs"]), symbol=sym, tf=tf,
           run_id=cand["run_id"], parity=par, n_full=len(schema), notional_per_equity=npe,
           median_exchange_leverage=med_lev, max_leverage_cap=float(bfull.max_leverage),
           n_trials=N_TRIALS, policy_hash=ev["policy_hash"], backtest_pass=ev["backtest_pass"],
           failure_modes=ev["failure_modes"], gates=ev["gates"], is_pf=cand["net_pf"], oos_pf=cand["oos_pf"])
json.dump(res, open(os.path.join(ROOT, "results", "candidate_spread_v2.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1, default=str)

L = []
L.append(f"# VALIDACIÓN G1–G11 · SPREAD id={sid} {cand['strategy']}")
L.append("")
L.append(f"**Par:** {' / '.join(sig['legs'])} {tf} · z-score(100) del log-spread con beta Kalman · "
         f"entrada |z|>2, salida cruce por 0. Book neutral dollar-neutral, PnL linearizado del spread.")
L.append("")
L.append(f"- **Paridad DEV:** {'OK' if par['parity'] else 'FALLA'} (re-run n={par['n']}, PF={par['pf']:.4f}, "
         f"net={par['net']:.2f}% vs artefacto n={par['art_n']}, PF={par['art_pf']:.4f}, net={par['art_ret']:.2f}%)")
L.append(f"- **n FULL:** {len(schema)} · IS PF {cand['net_pf']} · OOS PF {cand['oos_pf']}")
L.append(f"- **Apalancamiento de exchange (mediana notional/equity): {med_lev:.1f}x** vs cap del book "
         f"{bfull.max_leverage:.0f}x (N-cap). ⚠️ El notional real de las dos patas excede el cap; "
         f"tradeability cuestionable. G9 usa MAE por-trade (no margen por-pata).")
L.append(f"- **n_trials (DSR):** {N_TRIALS} · policy_hash `{ev['policy_hash']}` · benchmark = cash (neutral).")
L.append("")
L.append(f"## backtest_pass: **{ev['backtest_pass']}** · failure_modes: {ev['failure_modes']}")
L.append("")
L.append("| Gate | pass | números clave |")
L.append("|---|---|---|")
for g, v in ev["gates"].items():
    p = v.get("pass"); ps = "✅" if p is True else ("❌" if p is False else "PENDING")
    keys = {k: (round(v[k], 5) if isinstance(v[k], float) else v[k]) for k in v
            if k != "pass" and not isinstance(v[k], (dict, list))}
    ks = ", ".join(f"{k}={val}" for k, val in list(keys.items())[:7])
    L.append(f"| {g} | {ps} | {ks} |")
L.append("")
L.append(f"- **Artefacto fuente (run_id):** `{cand['run_id']}`")
L.append("")
L.append("*Validación con SpreadBook instrumentado en memoria (engine sin modificar). Paridad DEV verificada. "
         "Esquema v2 en fracciones del notional de exchange. Datos: `results/candidate_spread_v2.json`.*")
open(os.path.join(ROOT, "results", "CANDIDATE_SPREAD_V2.md"), "w", encoding="utf-8").write("\n".join(L))
print(f"spread id={sid} {'/'.join(sig['legs'])} parity={par['parity']} n_full={len(schema)} "
      f"exchange_lev={med_lev:.1f}x backtest_pass={ev['backtest_pass']}")
print("failed gates:", [g for g, v in ev["gates"].items() if v.get("pass") is False])
print("outputs: results/CANDIDATE_SPREAD_V2.md / candidate_spread_v2.json")
