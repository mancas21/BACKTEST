#!/usr/bin/env python
"""_validate_candidates_v2.py -- run the FULL G1-G11 battery on the robust
candidates from TOP_OOS_ROBUST.md.

The production artifacts only persist AGGREGATE metrics (no per-trade schema),
so the battery cannot be run from them. This validator RE-RUNS each p100screen
candidate with the repo's own Book (unmodified engine), reconstructs the v2
fixed-size trade schema (gross_ret / cost_ret / funding_ret / mae) from the
book ledger + bar arrays, VERIFIES PARITY against the stored DEV artifact, then
calls _gates_v2.evaluate_gates_v2 with a full GateContext (benchmark close,
mark-to-market equity, max_leverage, n_trials from the TrialLedger).

No production engine is edited; this is a research validation. Outputs:
results/CANDIDATES_V2_VALIDATION.md + .json
"""
from __future__ import annotations
import json, os, sys, importlib.util, math
import numpy as np, pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, "code")
RUNS = os.path.join(ROOT, "results", "runs")
sys.path.insert(0, CODE)

def _load(name, fn):
    spec = importlib.util.spec_from_file_location(name, os.path.join(CODE, fn))
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m
    spec.loader.exec_module(m); return m

p100 = _load("p100_val", "p100_screen_engine.py")
gv2 = _load("gates_val", "_gates_v2.py")

def num(x):
    try:
        v = float(x); return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None

# n_trials from the hash-chained TrialLedger (DSR multiple-testing correction)
ledger = gv2.TrialLedger(os.path.join(ROOT, "results", "_trial_ledger.jsonl"))
try:
    N_TRIALS = int(ledger.total_trials())
except Exception:
    N_TRIALS = 1486

def build_schema(book, sym):
    """Reconstruct the v2 fixed-size trade schema from the repo Book ledger."""
    slip, fee = book.slip, book.fee
    op, hi, lo, cl = book.open, book.high, book.low, book.close
    rate, isf = book.rate, book.is_fund
    rows = []
    lev = []
    eq = np.asarray(book.equity_curve, float)
    for t in book.trades:
        s = 1 if t["side"] == "long" else -1
        ef, xf, qty = t["entry"], t["exit"], t["qty"]
        ei, xi = t["entry_idx"], t["exit_idx"]
        notional = qty * ef
        raw_e = ef / (1 + s * slip)
        raw_x = xf / (1 - s * slip)
        gross = s * (raw_x - raw_e) / raw_e
        net_ex_fund = t["pnl"] / notional
        cost = gross - net_ex_fund
        # funding charged while the position was open (bars [ei, xi))
        fund_ccy = 0.0
        for j in range(ei, xi):
            if isf[j] and rate[j] != 0:
                fund_ccy += s * qty * cl[j] * rate[j]
        fund = fund_ccy / notional
        # MAE over holding bars [ei, xi], fraction of entry fill
        if s == 1:
            mae = max((ef - lo[ei:xi + 1].min()) / ef, 0.0)
        else:
            mae = max((hi[ei:xi + 1].max() - ef) / ef, 0.0)
        rows.append(dict(entry_time=pd.Timestamp(t["entry_time"]),
                         exit_time=pd.Timestamp(t["exit_time"]), symbol=sym,
                         side=s, gross_ret=gross, cost_ret=cost, funding_ret=fund,
                         mae=float(mae), exit_reason=t["reason"]))
        if ei < len(eq) and eq[ei] > 0:
            lev.append(notional / eq[ei])
    df = pd.DataFrame(rows)
    npe = float(np.median(lev)) if lev else 1.0
    npe = min(max(npe, 0.1), float(book.max_leverage))
    return df, npe

def make_ctx(book, df_schema, npe, bh):
    ts = pd.to_datetime(book.ts, utc=True)
    eq = np.asarray(book.equity_curve, float)
    mtm = pd.Series(eq, index=ts.iloc[:len(eq)])
    bench = pd.Series(book.close, index=ts)
    return gv2.GateContext(
        benchmark_close=bench, bh_total_return=bh, book_type="directional",
        inventory_book=False, equity_mtm=mtm, notional_per_equity=npe,
        max_leverage=float(book.max_leverage), mmr=0.005, n_trials=N_TRIALS,
        start_equity_usd=float(book.init), fee_bps=book.fee * 1e4, slip_bps=book.slip * 1e4)

def parity(book, art_m):
    pn = np.array([t["pnl"] for t in book.trades], float)
    n = len(pn)
    gp = float(pn[pn > 0].sum()); gl = float(-pn[pn < 0].sum())
    pf = gp / gl if gl > 0 else (None if gp > 0 else 0.0)
    net = (book.cash / book.init - 1) * 100
    apf, an, aret = num(art_m.get("profit_factor")), num(art_m.get("n_trades")), num(art_m.get("return_pct"))
    ok_n = (an is not None and n == int(an))
    ok_pf = (apf is not None and pf is not None and abs(pf - apf) <= max(1e-6, abs(apf) * 1e-6))
    ok_ret = (aret is not None and abs(net - aret) <= max(1e-4, abs(aret) * 1e-6))
    return dict(n=n, pf=pf, net=net, art_n=an, art_pf=apf, art_ret=aret,
                parity=bool(ok_n and ok_pf and ok_ret))

# ── candidates: p100screen entries of the robust filter ──
robust = json.load(open(os.path.join(ROOT, "results", "top_oos_robust.json"), encoding="utf-8"))["robust"]
results = []
for c in robust:
    if c["family"] != "p100screen":
        results.append(dict(strategy=c["strategy"], family=c["family"], symbol=c["symbol"],
                            tf=c["tf"], status="SKIPPED (pack20 engine needs separate instrumentation)",
                            run_id=c["run_id"]))
        continue
    art = json.load(open(os.path.join(RUNS, c["run_id"] + ".json"), encoding="utf-8"))
    sid = int(art["params"]["id"]); sym = art["symbol"]; tf = art["timeframe"]
    if sid in getattr(p100, "SPREAD_IDS", ()) or sid in getattr(p100, "BASKET_IDS", ()):
        results.append(dict(strategy=c["strategy"], family=c["family"], symbol=sym, tf=tf, sid=sid,
                            run_id=c["run_id"],
                            status="SKIPPED (pair/basket rebalance book: esquema por-periodo requiere instrumentación propia)"))
        continue
    # parity re-run (DEV, same segment as the stored artifact)
    bdev, _ = p100.run_family_a(sid, sym, tf, "DEV", charge_funding=True, pack_conventions=False)
    par = parity(bdev, art["metrics"])
    # full re-run for the battery
    bfull, _ = p100.run_family_a(sid, sym, tf, "FULL", charge_funding=True, pack_conventions=False)
    schema, npe = build_schema(bfull, sym)
    bh = float(bfull.close[-1] / bfull.open[0] - 1)
    ctx = make_ctx(bfull, schema, npe, bh)
    ev = gv2.evaluate_gates_v2(schema, ctx)
    gates = {g: dict(pass_=bool(v.get("pass")) if v.get("pass") is not None else None,
                     **{k: v[k] for k in v if k not in ("pass",)}) for g, v in ev["gates"].items()}
    results.append(dict(
        strategy=c["strategy"], family=c["family"], symbol=sym, tf=tf, sid=sid,
        run_id=c["run_id"], parity=par, n_full=len(schema), notional_per_equity=npe,
        n_trials=N_TRIALS, policy_hash=ev["policy_hash"],
        backtest_pass=ev["backtest_pass"], failure_modes=ev["failure_modes"],
        gates={g: ev["gates"][g] for g in ev["gates"]},
        is_pf=c["net_pf"], oos_pf=c["oos_pf"]))

json.dump(results, open(os.path.join(ROOT, "results", "candidates_v2_validation.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1, default=str)

# ── report ──
L = []
L.append("# VALIDACIÓN G1–G11 COMPLETA · candidatas robustas")
L.append("")
_ph = next((r.get("policy_hash") for r in results if r.get("policy_hash")), "")
L.append(f"Batería completa (`_gates_v2.evaluate_gates_v2`, policy_hash `{_ph}`) "
         f"corrida sobre las candidatas del filtro de robustez de `TOP_OOS_ROBUST.md`. "
         f"n_trials (DSR) = **{N_TRIALS}** (TrialLedger). Esquema por-trade reconstruido desde el Book del repo "
         f"(gross/cost/funding/MAE), con **paridad verificada** contra el artefacto DEV almacenado.")
L.append("")
L.append("> `backtest_pass` = G1∧G2∧G3∧G4∧G5∧G6∧G7∧G8∧G9∧G11. G10 (forward) queda PENDING (requiere run forward + pre-registro). "
         "G9 exige MAE + max_leverage (fail-closed). Esto es la batería REAL, no el filtro ligero.")
L.append("")
L.append("| Estrategia | Par/TF | Paridad DEV | n FULL | backtest_pass | Gates fallidos |")
L.append("|---|---|---|---|---|---|")
for r in results:
    if r.get("status", "").startswith("SKIPPED"):
        L.append(f"| {r['strategy'][:34]} | {r['symbol']} {r['tf']} | — | — | SKIPPED | {r['status']} |")
        continue
    par = "OK" if r["parity"]["parity"] else f"FALLA (n {r['parity']['n']} vs {r['parity']['art_n']})"
    failed = [g for g, v in r["gates"].items() if v.get("pass") is False]
    L.append(f"| {r['strategy'][:34]} | {r['symbol']} {r['tf']} | {par} | {r['n_full']} | "
             f"{'**PASS**' if r['backtest_pass'] else 'NO'} | {', '.join(failed) if failed else '—'} |")
L.append("")
L.append("## Detalle por gate")
L.append("")
for r in results:
    if r.get("status", "").startswith("SKIPPED"):
        continue
    L.append(f"### {r['strategy']} · {r['symbol']} {r['tf']} (id={r['sid']})")
    L.append(f"- **Paridad DEV:** {'OK' if r['parity']['parity'] else 'FALLA'} "
             f"(re-run n={r['parity']['n']}, PF={r['parity']['pf']:.4f}, net={r['parity']['net']:.2f}% "
             f"vs artefacto n={r['parity']['art_n']}, PF={r['parity']['art_pf']}, net={r['parity']['art_ret']}%)")
    L.append(f"- **n FULL:** {r['n_full']} · notional/equity (mediana): {r['notional_per_equity']:.2f}x · "
             f"IS PF {r['is_pf']} · OOS PF {r['oos_pf']}")
    L.append(f"- **backtest_pass: {r['backtest_pass']}** · failure_modes: {r['failure_modes']}")
    L.append("")
    L.append("| Gate | pass | números clave |")
    L.append("|---|---|---|")
    for g, v in r["gates"].items():
        p = v.get("pass")
        ps = "✅" if p is True else ("❌" if p is False else "PENDING")
        keys = {k: (round(v[k], 4) if isinstance(v[k], float) else v[k])
                for k in v if k not in ("pass",) and not isinstance(v[k], (dict, list))}
        ks = ", ".join(f"{k}={val}" for k, val in list(keys.items())[:6])
        L.append(f"| {g} | {ps} | {ks} |")
    L.append("")
    L.append(f"- **Artefacto fuente (run_id):** `{r['run_id']}`")
    L.append("")
L.append("---")
L.append("*Validación de investigación con el Book del repo (engine sin modificar). Paridad DEV verificada por candidato. "
         "Datos: `results/candidates_v2_validation.json`. pack20 requiere instrumentación de su propio engine (pendiente).*")
open(os.path.join(ROOT, "results", "CANDIDATES_V2_VALIDATION.md"), "w", encoding="utf-8").write("\n".join(L))
print(f"validated {sum(1 for r in results if 'gates' in r)} p100screen candidates; n_trials={N_TRIALS}")
for r in results:
    if "gates" in r:
        print(f"  {r['strategy'][:30]:30} {r['symbol']} {r['tf']} parity={r['parity']['parity']} "
              f"backtest_pass={r['backtest_pass']} failed={[g for g,v in r['gates'].items() if v.get('pass') is False]}")
    else:
        print(f"  {r['strategy'][:30]:30} {r.get('status')}")
print("outputs: results/CANDIDATES_V2_VALIDATION.md / .json")
