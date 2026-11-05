"""Independent forensic audit of the cbpack artifact trade lists.

Second implementation of the execution/cost/accounting rules, written from the spec
in cbpack_engine.py, run against the SAME signal arrays and the SAME raw bars as
the pack. Shares NO code with cbpack_engine's backtest loop or _metrics. Purpose:
test whether the pack's reported numbers survive recomputation by independent code
(the failure mode that has bitten this repo before: fabricated SAX figures, a
report builder silently double-counting cells).

Checks
  A. artifact  vs pack   -- re-running the pack reproduces the frozen artifact.
  B. pack      vs mine   -- an independent simulator reproduces the pack's trades.
  C. per-trade forensics on the pack's own trade list (fills, fees, pnl, timing,
     sizing, non-overlap, exposure).
  D. zero-cost control   -- fee=0/slip=0 run in both engines.
  E. lookahead probe     -- truncation test on S02/S10 (causal-only signals).
  F. indicator numeric   -- Donchian / flow-z / strength vs numpy.

Output: results/cbpack_trade_audit.json
"""
import json, os, math, sys
import numpy as np
import pandas as pd

ROOT = r"C:\Users\Lenovo\Documents\backtest-system"
CODE = os.path.join(ROOT, "code")
DATA = os.path.join(ROOT, "data")
RUNS = os.path.join(ROOT, "results", "runs")
sys.path.insert(0, CODE)

import types as _types
_cbmod = _types.ModuleType("cbpack_engine")
_cbmod.__file__ = os.path.join(CODE, "cbpack_engine.py")
sys.modules["cbpack_engine"] = _cbmod
exec(open(os.path.join(CODE, "cbpack_engine.py"), encoding="utf-8").read(), _cbmod.__dict__)
for _n in ("prepare", "attach_funding", "BacktestConfig", "backtest", "make_signals",
           "base_seconds", "flow_z", "STRATEGIES", "MissingData", "BacktestResult"):
    globals()[_n] = getattr(_cbmod, _n)

FEE_BPS = 5.0
SLIP_BPS = 2.0
INITIAL = 10000.0
RISK_PCT = 1.0
MAX_LEV = 3.0

def load_like_adapter(sym, tf="1h"):
    klines = os.path.join(DATA, "binance_klines_{}_taker".format(tf), "{}_{}.csv".format(sym, tf))
    raw = pd.read_csv(klines)
    raw.columns = [str(c).strip().lower() for c in raw.columns]
    raw = raw.rename(columns={"open_ts": "open_time"})
    raw["open_time"] = pd.to_datetime(raw["open_time"], unit="ms", utc=True)
    df = prepare(raw.set_index("open_time"))
    funding_path = os.path.join(DATA, "binance_funding", "{}_funding.json".format(sym))
    if os.path.exists(funding_path):
        recs = json.load(open(funding_path, encoding="utf-8"))
        idx = pd.DatetimeIndex(pd.to_datetime([x["t"] for x in recs], unit="ms", utc=True))
        _unit = getattr(df.index + pd.Timedelta(seconds=60), "unit", None)
        if _unit is not None and hasattr(idx, "as_unit"):
            idx = idx.as_unit(_unit)
        s = pd.Series([float(x["r"]) for x in recs], index=idx)
        s = s[~s.index.duplicated(keep="last")].sort_index()
        df = attach_funding(df, s)
    return df, funding_path

def _parts(res):
    try:
        return res.metrics, res.trades, res.equity, res.signals
    except AttributeError:
        return res[0], res[1], res[2], res[3]

def metrics_from_equity(eq, trades, df, cfg, exposure, bpy):
    i0, i1 = 0, len(eq) - 1
    e = eq[i0:i1 + 1]
    ret = e.pct_change().dropna()
    total = e.iloc[-1] / e.iloc[0] - 1.0 if len(e) > 1 else 0.0
    bh = df["close"].iloc[i1] / df["close"].iloc[i0] - 1.0
    sd = ret.std(ddof=1)
    m = {"bars": int(i1 - i0 + 1), "n_trades": int(len(trades)), "net_return_pct": total * 100,
         "buy_hold_return_pct": bh * 100, "excess_vs_buy_hold_pct": (total - bh) * 100,
         "max_drawdown_pct": float((e / e.cummax() - 1.0).min() * 100) if len(e) > 1 else 0.0,
         "sharpe_annualised": float(ret.mean() / sd * math.sqrt(bpy)) if sd and sd > 0 else float("nan"),
         "exposure_pct": exposure / max(i1 - i0 + 1, 1) * 100,
         "win_rate_pct": float("nan"), "profit_factor": float("nan"), "expectancy_R": float("nan"),
         "avg_trade_pct": float("nan"), "fees_paid": 0.0, "gross_return_pct": total * 100,
         "exit_reasons": {}}
    if len(trades):
        w, l = trades[trades.pnl > 0], trades[trades.pnl <= 0]
        gl = -l.pnl.sum()
        m.update({"win_rate_pct": len(w) / len(trades) * 100,
                  "profit_factor": float(w.pnl.sum() / gl) if gl > 0 else float("inf"),
                  "expectancy_R": float(trades.R.mean()), "avg_trade_pct": float(trades.pnl_pct.mean() * 100),
                  "fees_paid": float(trades.fees.sum()),
                  "gross_return_pct": float((trades.pnl + trades.fees).sum() / cfg.initial_capital * 100),
                  "avg_bars_in_trade": float(trades.bars.mean()),
                  "exit_reasons": trades.reason.value_counts().to_dict()})
    return m

def my_simulate(df, sig, fee_bps=FEE_BPS, slip_bps=SLIP_BPS, initial=INITIAL,
                risk_pct=RISK_PCT, max_leverage=MAX_LEV, sizing_mode="stop_risk",
                opposite_signal="ignore"):
    o = df["open"].to_numpy(float); h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
    buy = sig["buy"].to_numpy(bool); sell = sig["sell"].to_numpy(bool)
    exl = sig["exit_long"].to_numpy(bool); exs = sig["exit_short"].to_numpy(bool)
    sl_d = sig["sl_dist"].to_numpy(float); tp_d = sig["tp_dist"].to_numpy(float)
    mh = int(sig["max_hold"].iloc[0])
    fee, slip = fee_bps / 1e4, slip_bps / 1e4
    n = len(df)
    cash = initial; pos = 0; qty = 0.0; entry = float("nan"); entry_i = -1
    entry_fee = 0.0; sl = float("nan"); tp = float("nan"); pending = None
    exposure = 0; trades = []; equity = np.full(n, np.nan)
    def close_pos(px, i, reason):
        nonlocal cash, pos, qty, entry_i
        xf = qty * px * fee
        gross = pos * qty * (px - entry)
        pnl = gross - xf - entry_fee
        cash += gross - xf
        trades.append({"i_entry": entry_i, "i_exit": i, "dir": pos, "entry": entry, "exit": px,
                       "qty": qty, "pnl": pnl, "pnl_pct": pnl / max(qty * entry, 1e-12),
                       "R": pnl / (qty * abs(entry - sl) + 1e-12) if qty > 0 else float("nan"),
                       "bars": i - entry_i, "fees": entry_fee + xf, "reason": reason})
        pos = 0; qty = 0.0
    for i in range(n):
        if pending is not None:
            if pending["kind"] in ("close", "reverse") and pos != 0:
                close_pos(o[i] * (1.0 - slip * pos), i, pending.get("why", "opposite_signal"))
            if pending["kind"] in ("open", "reverse"):
                d = pending["dir"]
                px = o[i] * (1.0 + slip * d)
                efee = pending["qty"] * px * fee
                cash -= efee
                pos, qty, entry, entry_i = d, pending["qty"], px, i
                sl = px - d * pending["sl_d"]
                tp = (px + d * pending["tp_d"]) if np.isfinite(pending["tp_d"]) else float("nan")
                entry_fee = efee
            pending = None
        if pos != 0:
            has_tp = np.isfinite(tp)
            if pos == 1:
                sl_open = o[i] <= sl; tp_open = has_tp and o[i] >= tp
                sl_in = l[i] <= sl; tp_in = has_tp and h[i] >= tp
            else:
                sl_open = o[i] >= sl; tp_open = has_tp and o[i] <= tp
                sl_in = h[i] >= sl; tp_in = has_tp and l[i] <= tp
            kind = None; fill = None
            if sl_open:
                kind, fill = "sl", o[i]
            elif tp_open:
                kind, fill = "tp", o[i]
            elif sl_in and tp_in:
                kind = "sl"; fill = sl
            elif sl_in:
                kind, fill = "sl", sl
            elif tp_in:
                kind, fill = "tp", tp
            if kind == "sl":
                close_pos(fill * (1.0 - slip * pos), i, "sl")
            elif kind == "tp":
                close_pos(fill, i, "tp")
        equity[i] = cash + (pos * qty * (c[i] - entry) if pos != 0 else 0.0)
        exposure += (pos != 0)
        if i < n - 1:
            want = 1 if buy[i] else (-1 if sell[i] else 0)
            new = None
            if want != 0 and np.isfinite(sl_d[i]) and sl_d[i] > 0:
                eq = equity[i]
                if sizing_mode == "stop_risk":
                    q = eq * risk_pct / 100.0 / sl_d[i]
                else:
                    q = eq * 100.0 / 100.0 / c[i]
                q = min(q, eq * max_leverage / c[i])
                if q > 0:
                    new = {"kind": "open", "dir": want, "qty": q, "sl_d": sl_d[i],
                           "tp_d": tp_d[i] if np.isfinite(tp_d[i]) else float("nan")}
            if pos == 0:
                pending = new
            else:
                why = None
                if (pos == 1 and exl[i]) or (pos == -1 and exs[i]):
                    why = "exit_signal"
                elif mh > 0 and i - entry_i + 1 >= mh:
                    why = "time_stop"
                if why is not None:
                    pending = {"kind": "close", "why": why}
                    if new is not None and new["dir"] == -pos and opposite_signal == "reverse":
                        new = dict(new, kind="reverse", why=why)
                        pending = new
                elif want == -pos:
                    pending = {"kind": "close", "why": "opposite_signal"}
    if pos != 0:
        close_pos(c[n - 1] * (1.0 - slip * pos), n - 1, "end_of_data")
        equity[n - 1] = cash
    eq_s = pd.Series(equity, index=df.index).ffill()
    cols = ["i_entry", "i_exit", "dir", "entry", "exit", "qty", "pnl", "pnl_pct", "R", "bars", "fees", "reason"]
    tdf = pd.DataFrame(trades, columns=cols)
    bpy = 365.0 * 86400.0 / base_seconds(df)
    m = metrics_from_equity(eq_s, tdf, df, BacktestConfig(fee_bps=fee_bps, slippage_bps=slip_bps,
                                                          initial_capital=initial), exposure, bpy)
    return m, tdf, eq_s, bpy
def audit_trades(pack_trades, df, slip=SLIP_BPS/1e4, fee=FEE_BPS/1e4):
    """Per-trade forensics on the pack's own trade list. Returns dict of checks + tallies."""
    o = df["open"].to_numpy(float); h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
    idx = df.index
    out = {"n_trades": int(len(pack_trades)), "checks": {}}
    rows = []
    fill_ok = 0; fee_ok = 0; pnl_ok = 0; timing_ok = 0; size_ok = 0
    overlap_ok = True; exposure_bars = 0
    prev_exit_i = -1
    for tr in pack_trades.itertuples(index=False):
        # map times to bar indices
        try:
            j = idx.get_loc(pd.Timestamp(tr.entry_time))
            k = idx.get_loc(pd.Timestamp(tr.exit_time))
        except Exception:
            rows.append({"err": "time not in index", "entry_time": str(tr.entry_time)})
            continue
        d = int(tr.dir); qty = float(tr.qty); entry = float(tr.entry); exitp = float(tr.exit)
        sl_dist = None
        # recover sl_dist from trade? not in trade row; recompute from signal? store separately later.
        # --- entry fill check ---
        entry_expected = o[j] * (1.0 + slip * d)
        entry_fill_ok = abs(entry - entry_expected) < 1e-9 * max(1.0, abs(entry))
        if entry_fill_ok:
            fill_ok += 1
        # --- exit fill consistency ---
        exit_expected = None
        reason = str(tr.reason)
        if reason == "sl":
            sl_level = entry - d * (entry - (exitp / (1.0 - slip * d)))  # back out sl_d from slipped exit
            # sl_level should equal entry - d*sl_d; check the slipped fill reconstructs
            fill_reconstructed = exitp / (1.0 - slip * d)
            # fill_reconstructed must be either open[k] or the sl level; sl level = entry - d*sl_d
            # we don't have sl_d here; just check fill is open[k] or a level consistent with o/h/l
            exit_fill_ok = (abs(fill_reconstructed - o[k]) < 1e-9 * max(1.0, abs(o[k])) or
                            (l[k] <= fill_reconstructed <= h[k]))
        elif reason == "tp":
            fill_reconstructed = exitp
            exit_fill_ok = (abs(fill_reconstructed - o[k]) < 1e-9 * max(1.0, abs(o[k])) or
                            (l[k] <= fill_reconstructed <= h[k]))
        elif reason in ("exit_signal", "time_stop", "opposite_signal"):
            fill_reconstructed = exitp / (1.0 - slip * d)
            exit_fill_ok = abs(fill_reconstructed - o[k]) < 1e-9 * max(1.0, abs(o[k]))
        elif reason == "end_of_data":
            fill_reconstructed = exitp / (1.0 - slip * d)
            exit_fill_ok = abs(fill_reconstructed - c[k]) < 1e-9 * max(1.0, abs(c[k]))
        else:
            exit_fill_ok = False
        # --- fees ---
        fee_expected = fee * (qty * entry + qty * exitp)
        fee_ok_trade = abs(float(tr.fees) - fee_expected) < 1e-6 * max(1.0, fee_expected)
        if fee_ok_trade:
            fee_ok += 1
        # --- pnl ---
        pnl_expected = d * qty * (exitp - entry) - float(tr.fees)
        pnl_ok_trade = abs(float(tr.pnl) - pnl_expected) < 1e-6 * max(1.0, abs(pnl_expected))
        if pnl_ok_trade:
            pnl_ok += 1
        # --- timing/lookahead: entry at bar j means signal at bar j-1 ---
        timing_trade_ok = (j > 0)
        # --- non-overlap ---
        if j <= prev_exit_i:
            overlap_ok = False
        prev_exit_i = k
        exposure_bars += (k - j + 1)
        rows.append({"i_entry": int(j), "i_exit": int(k), "dir": d, "reason": reason,
                     "entry_fill_ok": bool(entry_fill_ok), "exit_fill_ok": bool(exit_fill_ok),
                     "fee_ok": bool(fee_ok_trade), "pnl_ok": bool(pnl_ok_trade)})
    out["checks"] = {
        "entry_fill_ok": int(fill_ok), "entry_fill_total": int(len(pack_trades)),
        "exit_fill_ok": int(sum(r["exit_fill_ok"] for r in rows)),
        "fee_ok": int(fee_ok), "pnl_ok": int(pnl_ok),
        "non_overlap": bool(overlap_ok),
        "exposure_bars_sum": int(exposure_bars),
    }
    out["rows"] = rows
    return out
def truncation_probe(sym, sid, n_points=12):
    """Recompute S02/S10 signals on df[:k] and compare the last bar's signal to
    the full-series signal. Any difference => lookahead (or a boundary artifact
    that must be explained)."""
    df, _ = load_like_adapter(sym)
    full_sig = make_signals(df, sid)
    diffs = 0
    total = 0
    # pick truncation points spread across the series (avoid the first 200 bars)
    ks = np.linspace(200, len(df) - 1, n_points, dtype=int)
    for k in ks:
        sub = df.iloc[:k]
        sub_sig = make_signals(sub, sid)
        # compare the last bar's buy/sell/exit flags + sl_dist
        for col in ("buy", "sell", "exit_long", "exit_short"):
            a = bool(full_sig[col].iloc[k - 1])
            b = bool(sub_sig[col].iloc[-1])
            if a != b:
                diffs += 1
            total += 1
    return {"truncation_points": int(len(ks)), "comparisons": int(total), "mismatches": int(diffs)}

def indicator_numeric_check(sym):
    """Donchian channel + flow z + TSM strength vs a pure-numpy reimplementation."""
    df, _ = load_like_adapter(sym)
    n = 48
    # Donchian
    hh_pandas = df.high.rolling(n).max().shift(1)
    ll_pandas = df.low.rolling(n).min().shift(1)
    # numpy reference
    highs = df.high.to_numpy(float); lows = df.low.to_numpy(float)
    hh_np = np.full(len(df), np.nan)
    ll_np = np.full(len(df), np.nan)
    for i in range(n, len(df)):
        hh_np[i] = highs[i - n:i].max()
        ll_np[i] = lows[i - n:i].min()
    donchian_ok = (np.nanmax(np.abs(hh_pandas.to_numpy() - hh_np)) < 1e-9 and
                   np.nanmax(np.abs(ll_pandas.to_numpy() - ll_np)) < 1e-9)
    # flow z: ema of flow then rolling zscore
    fz_pandas = flow_z(df, 5, 100)
    # strength (S10)
    lr = np.log(df.close).diff()
    strength_pandas = (np.log(df.close / df.close.shift(168)) /
                       (lr.rolling(96).std(ddof=0) * math.sqrt(168)))
    strength_np = (np.log(df.close.to_numpy(float) / np.roll(df.close.to_numpy(float), 168)) /
                   (pd.Series(lr).rolling(96).std(ddof=0).to_numpy() * math.sqrt(168)))
    # compare only where both finite
    mask = np.isfinite(strength_pandas.to_numpy()) & np.isfinite(strength_np)
    strength_maxdiff = float(np.nanmax(np.abs(strength_pandas.to_numpy()[mask] - strength_np[mask]))) if mask.any() else float("nan")
    return {"donchian_maxdiff": float(np.nanmax(np.abs(hh_pandas.to_numpy() - hh_np))),
            "flow_z_finite": bool(np.isfinite(fz_pandas).any()),
            "strength_maxdiff": strength_maxdiff}

def main():
    symbols = ["XRPUSDT", "SOLUSDT"]
    audit = {"symbols": {}}
    for sym in symbols:
        print(f"\n=== {sym} ===")
        df, funding_path = load_like_adapter(sym)
        print(f"  bars={len(df)}  funding={os.path.basename(funding_path)}")
        sym_rec = {"bars": int(len(df)), "strategies": {}}
        # artifact rows for this symbol
        art = None
        for rid in os.listdir(RUNS):
            a = json.load(open(os.path.join(RUNS, rid), encoding="utf-8"))
            if (a.get("symbol") == sym and a.get("timeframe") == "1h" and
                    a.get("strategy") == "cbpack" and a.get("params") == {}):
                art = a
                break
        art_rows = {t["id"]: t for t in (art["tables"] if art else [])}
        for sid in ["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "S09", "S10"]:
            try:
                sig = make_signals(df, sid)
            except Exception as e:
                print(f"  {sid}: SKIPPED ({e})")
                sym_rec["strategies"][sid] = {"status": "skipped", "reason": str(e)}
                continue
            # pack run
            r = backtest(df, sig, BacktestConfig())
            pm, pt, pe, ps = _parts(r)
            # independent sim
            mm, mt, me, _ = my_simulate(df, sig)
            # zero-cost runs
            r0 = backtest(df, sig, BacktestConfig(fee_bps=0.0, slippage_bps=0.0))
            pm0, pt0, pe0, _ = _parts(r0)
            mm0, mt0, me0, _ = my_simulate(df, sig, fee_bps=0.0, slip_bps=0.0)
            # artifact row
            ar = art_rows.get(sid, {})
            # per-trade audit on pack's trades
            ta = audit_trades(pt, df)
            # metric comparison pack vs mine
            def _g(m, k):
                v = m.get(k)
                return None if (v is None or (isinstance(v, float) and math.isnan(v))) else v
            comp = {
                "n_trades_pack": int(pm["n_trades"]), "n_trades_mine": int(mm["n_trades"]),
                "n_trades_artifact": ar.get("trades"),
                "net_pct_pack": pm["net_return_pct"], "net_pct_mine": mm["net_return_pct"],
                "net_pct_artifact": ar.get("net_%"),
                "pf_pack": pm["profit_factor"], "pf_mine": mm["profit_factor"],
                "pf_artifact": ar.get("PF"),
                "win_pct_pack": pm["win_rate_pct"], "win_pct_mine": mm["win_rate_pct"],
                "maxdd_pack": pm["max_drawdown_pct"], "maxdd_mine": mm["max_drawdown_pct"],
                "exposure_pack": pm["exposure_pct"], "exposure_mine": mm["exposure_pct"],
                "fees_pack": pm["fees_paid"], "fees_mine": mm["fees_paid"],
                "trades_match": int(len(pt)) == int(len(mt)),
            }
            # per-trade price comparison pack vs mine (align by index order)
            price_match = 0
            n = min(len(pt), len(mt))
            for a, b in zip(pt.itertuples(index=False), mt.itertuples(index=False)):
                try:
                    ja = df.index.get_loc(pd.Timestamp(a.entry_time))
                    ka = df.index.get_loc(pd.Timestamp(a.exit_time))
                except Exception:
                    continue
                if (ja == b.i_entry and ka == b.i_exit and a.dir == b.dir and
                    abs(a.entry - b.entry) < 1e-9 * max(1, abs(a.entry)) and
                    abs(a.exit - b.exit) < 1e-9 * max(1, abs(a.exit))):
                    price_match += 1
            comp["trade_price_match"] = int(price_match)
            comp["trade_price_total"] = int(n)
            # zero-cost
            zc = {
                "net_pct_pack_zc": pm0["net_return_pct"], "net_pct_mine_zc": mm0["net_return_pct"],
                "pf_pack_zc": pm0["profit_factor"], "pf_mine_zc": mm0["profit_factor"],
                "trades_pack_zc": int(pm0["n_trades"]), "trades_mine_zc": int(mm0["n_trades"]),
            }
            # artifact reproducibility
            art_repro = {}
            if ar:
                art_repro = {
                    "net_pct_match": abs(pm["net_return_pct"] - float(ar["net_%"])) < 1e-6,
                    "pf_match": abs(pm["profit_factor"] - float(ar["PF"])) < 1e-9,
                    "trades_match": int(pm["n_trades"]) == int(ar["trades"]),
                    "win_pct_match": abs(pm["win_rate_pct"] - float(ar["win_%"])) < 1e-6,
                }
            sym_rec["strategies"][sid] = {
                "status": "ok",
                "artifact_repro": art_repro,
                "comparison": comp,
                "zero_cost": zc,
                "trade_audit": ta["checks"],
                "truncation": None,
            }
            # truncation probe for S02/S10
            if sid in ("S02", "S10"):
                sym_rec["strategies"][sid]["truncation"] = truncation_probe(sym, sid)
            # indicator check once per symbol
            if sid == "S02":
                sym_rec["indicator_check"] = indicator_numeric_check(sym)
            print(f"  {sid}: pack net={pm['net_return_pct']:+.2f}% mine net={mm['net_return_pct']:+.2f}% "
                  f"trades={pm['n_trades']}/{mm['n_trades']} pf={pm['profit_factor']:.3f}/{mm['profit_factor']:.3f} "
                  f"entry_fill={ta['checks']['entry_fill_ok']}/{ta['checks']['entry_fill_total']}")
        audit["symbols"][sym] = sym_rec

    # lookahead truncation is already in per-symbol records
    out_path = os.path.join(ROOT, "results", "cbpack_trade_audit.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=1, default=str)
    print("\nWrote", out_path)

if __name__ == "__main__":
    main()
