#!/usr/bin/env python
"""_pack20_audit.py -- known answers for the pack20 engine (2026-11-08).

Hand-computed cases on synthetic bars against the pack's OWN executor
(pack20_engine.run_backtest, byte-identical copy of
Downloads/strategy_pack_20.py) plus the wrapper's pf/loader helpers.
ALL PASS is required BEFORE any real-data artifact (adapter_template
checklist step 2). Expectation bugs count against the test, not the
engine: check ranges, units and closed-vs-open trades first.

Output: results/pack20_audit_known_answers.txt
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pack20_wrap as W
import pack20_engine as P20          # same module W loads by path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "pack20_audit_known_answers.txt")

T0 = 1_600_000_000_000


def bars(rows):
    df = pd.DataFrame(rows, columns=["open_ts", "open", "high", "low",
                                     "close", "volume"])
    df["open_ts"] = pd.to_datetime(df["open_ts"], unit="ms", utc=True)
    return df.set_index("open_ts")


def sig_frame(df, **sets):
    s = P20._frame(df)
    for col, idxs in sets.items():
        if col in ("stop_long", "tp_long", "stop_short", "tp_short"):
            for i, v in idxs:
                s.iloc[i, list(s.columns).index(col)] = v
        else:
            for i in idxs:
                s.iloc[i, list(s.columns).index(col)] = True
    return s


def flat(n, px=100.0):
    return [(T0 + i * 3_600_000, px, px, px, px, 1.0) for i in range(n)]


CASES = []


def case(name):
    def deco(fn):
        CASES.append((name, fn))
        return fn
    return deco


# ── 1. no signal -> flat ──────────────────────────────────────────────────
@case("no_signal_flat")
def c1():
    df = bars(flat(40))
    s = sig_frame(df)
    tr, eq, m = P20.run_backtest(df, s, fees_bps=0.0, slippage_bps=0.0)
    return {"n_trades": len(tr) == 0,
            "eq_final_1.0": abs(float(eq.iloc[-1]) - 1.0) < 1e-12,
            "return_0": m["total_return"] == 0.0}


# ── 2. entry at NEXT open, per-side costs, exit at signal-bar close ──────
@case("entry_next_open_costs_close_exit")
def c2():
    px = [100.0, 110.0, 120.0, 90.0, 95.0, 100.0]
    df = bars([(T0 + i * 3_600_000, p, p, p, p, 1.0) for i, p in enumerate(px)])
    s = sig_frame(df, entry_long=[0], exit_long=[2])
    tr, eq, m = P20.run_backtest(df, s, fees_bps=10.0, slippage_bps=0.0)
    entry, exit_ = 110.0 * 1.001, 120.0 * 0.999        # 110.11, 119.88
    exp_cash = 1.0 + (exit_ - entry) / entry
    t = tr.iloc[0]
    return {"one_trade": len(tr) == 1,
            "entry_110.11": abs(t["entry"] - entry) < 1e-9,
            "exit_119.88": abs(t["exit"] - exit_) < 1e-9,
            "entry_at_bar1": t["entry_time"] == df.index[1],
            "exit_at_bar2": t["exit_time"] == df.index[2],
            "cash_hand": abs(float(eq.iloc[-1]) - exp_cash) < 1e-12,
            "eq_len6": len(eq) == 6}


# ── 3. SL and TP in one bar -> the STOP fills first ───────────────────────
@case("sl_first_tie")
def c3():
    df = bars(flat(6))
    df.iloc[2, df.columns.get_loc("high")] = 110.0
    df.iloc[2, df.columns.get_loc("low")] = 90.0
    s = sig_frame(df, entry_long=[0],
                  stop_long=[(0, 95.0)], tp_long=[(0, 108.0)])
    tr, eq, m = P20.run_backtest(df, s, fees_bps=0.0, slippage_bps=0.0)
    return {"exit_at_stop_95": abs(tr.iloc[0]["exit"] - 95.0) < 1e-12,
            "cash_0.95": abs(float(eq.iloc[-1]) - 0.95) < 1e-12,
            "loss": tr.iloc[0]["win"] == False}


# ── 4. TP alone fills at the level ────────────────────────────────────────
@case("tp_fill_at_level")
def c4():
    df = bars(flat(6))
    df.iloc[2, df.columns.get_loc("high")] = 109.0
    df.iloc[2, df.columns.get_loc("low")] = 99.0
    s = sig_frame(df, entry_long=[0],
                  stop_long=[(0, 95.0)], tp_long=[(0, 108.0)])
    tr, eq, m = P20.run_backtest(df, s, fees_bps=0.0, slippage_bps=0.0)
    return {"exit_at_tp_108": abs(tr.iloc[0]["exit"] - 108.0) < 1e-12,
            "cash_1.08": abs(float(eq.iloc[-1]) - 1.08) < 1e-12}


# ── 5. open gaps through the stop: fills AT THE LEVEL (declared pack
#      convention -- optimistic; the template's min(px, stop) is NOT applied)
@case("gap_through_stop_fills_at_level")
def c5():
    o = [100.0, 100.0, 90.0, 90.0, 90.0, 90.0]
    h = [100.0, 100.0, 95.0, 90.0, 90.0, 90.0]
    l = [100.0, 100.0, 89.0, 90.0, 90.0, 90.0]
    df = bars([(T0 + i * 3_600_000, o[i], h[i], l[i], o[i], 1.0)
               for i in range(6)])
    s = sig_frame(df, entry_long=[0], stop_long=[(0, 95.0)])
    tr, eq, m = P20.run_backtest(df, s, fees_bps=0.0, slippage_bps=0.0)
    return {"exit_at_level_95_NOT_open_90": abs(tr.iloc[0]["exit"] - 95.0) < 1e-12,
            "cash_0.95": abs(float(eq.iloc[-1]) - 0.95) < 1e-12}


# ── 6. signal exit fills at the signal bar's close ────────────────────────
@case("signal_exit_at_close")
def c6():
    px = [100.0, 100.0, 110.0, 110.0, 110.0, 110.0]
    df = bars([(T0 + i * 3_600_000, p, p, p, p, 1.0) for i, p in enumerate(px)])
    s = sig_frame(df, entry_long=[0], exit_long=[2])
    tr, eq, m = P20.run_backtest(df, s, fees_bps=0.0, slippage_bps=0.0)
    return {"exit_at_close_110": abs(tr.iloc[0]["exit"] - 110.0) < 1e-12,
            "cash_1.10": abs(float(eq.iloc[-1]) - 1.10) < 1e-12}


# ── 7. exit signal on the fill bar itself: open fill, same-bar close exit ─
@case("same_bar_exit_after_fill")
def c7():
    o = [100.0, 100.0, 103.0, 103.0, 103.0, 103.0]
    c = [100.0, 103.0, 103.0, 103.0, 103.0, 103.0]
    df = bars([(T0 + i * 3_600_000, o[i], c[i], o[i], c[i], 1.0)
               for i in range(6)])
    s = sig_frame(df, entry_long=[0], exit_long=[1])
    tr, eq, m = P20.run_backtest(df, s, fees_bps=0.0, slippage_bps=0.0)
    return {"exit_at_103": abs(tr.iloc[0]["exit"] - 103.0) < 1e-12,
            "cash_1.03": abs(float(eq.iloc[-1]) - 1.03) < 1e-12}


# ── 8. max_hold exits at the close of the expiry bar ──────────────────────
@case("max_hold_exit")
def c8():
    px = [100.0, 100.0, 100.0, 101.0, 101.0, 101.0]
    df = bars([(T0 + i * 3_600_000, p, p, p, p, 1.0) for i, p in enumerate(px)])
    s = sig_frame(df, entry_long=[0])
    s.attrs["max_hold"] = 2
    tr, eq, m = P20.run_backtest(df, s, fees_bps=0.0, slippage_bps=0.0)
    return {"exit_at_101": abs(tr.iloc[0]["exit"] - 101.0) < 1e-12,
            "exit_at_bar3": tr.iloc[0]["exit_time"] == df.index[3],
            "cash_1.01": abs(float(eq.iloc[-1]) - 1.01) < 1e-12}


# ── 9. short TP: pnl sign and sizing ──────────────────────────────────────
@case("short_tp")
def c9():
    o = [100.0, 100.0, 100.0, 95.0, 95.0, 95.0]
    h = [100.0, 100.0, 100.0, 95.0, 95.0, 95.0]
    l = [100.0, 100.0, 89.0, 95.0, 95.0, 95.0]
    df = bars([(T0 + i * 3_600_000, o[i], h[i], l[i], o[i], 1.0)
               for i in range(6)])
    s = sig_frame(df, entry_short=[0],
                  stop_short=[(0, 105.0)], tp_short=[(0, 90.0)])
    tr, eq, m = P20.run_backtest(df, s, fees_bps=0.0, slippage_bps=0.0)
    return {"exit_at_tp_90": abs(tr.iloc[0]["exit"] - 90.0) < 1e-12,
            "cash_1.10": abs(float(eq.iloc[-1]) - 1.10) < 1e-12,
            "win": tr.iloc[0]["win"] == True}


# ── 10. short with per-side costs ─────────────────────────────────────────
@case("short_costs")
def c10():
    o = [100.0, 100.0, 100.0, 95.0, 95.0, 95.0]
    h = [100.0, 100.0, 100.0, 95.0, 95.0, 95.0]
    l = [100.0, 100.0, 89.0, 95.0, 95.0, 95.0]
    df = bars([(T0 + i * 3_600_000, o[i], h[i], l[i], o[i], 1.0)
               for i in range(6)])
    s = sig_frame(df, entry_short=[0], tp_short=[(0, 90.0)])
    tr, eq, m = P20.run_backtest(df, s, fees_bps=10.0, slippage_bps=0.0)
    entry, exit_ = 100.0 * 0.999, 90.0 * 1.001          # 99.9, 90.09
    exp_cash = 1.0 + (entry - exit_) / entry
    return {"entry_99.9": abs(tr.iloc[0]["entry"] - entry) < 1e-9,
            "exit_90.09": abs(tr.iloc[0]["exit"] - exit_) < 1e-9,
            "cash_hand": abs(float(eq.iloc[-1]) - exp_cash) < 1e-12}


# ── 11. determinism: identical rerun ──────────────────────────────────────
@case("determinism")
def c11():
    px = [100.0, 110.0, 120.0, 90.0, 95.0, 100.0]
    df = bars([(T0 + i * 3_600_000, p, p, p, p, 1.0) for i, p in enumerate(px)])
    s = sig_frame(df, entry_long=[0], exit_long=[2])
    a = P20.run_backtest(df, s, fees_bps=10.0, slippage_bps=0.0)
    b = P20.run_backtest(df, s, fees_bps=10.0, slippage_bps=0.0)
    fa = [(r["entry"], r["exit"], r["pnl"]) for _, r in a[0].iterrows()]
    fb = [(r["entry"], r["exit"], r["pnl"]) for _, r in b[0].iterrows()]
    return {"trades_equal": fa == fb,
            "eq_equal": abs(float(a[1].iloc[-1]) - float(b[1].iloc[-1])) < 1e-15}


# ── 12. wrapper: no-losers book -> pf None + flag (never a fudged inf) ────
@case("wrapper_pf_no_losses")
def c12():
    pf, noloss = W._pf(np.array([0.05, 0.03, 0.02]))
    pf2, noloss2 = W._pf(np.array([0.05, -0.02]))
    return {"no_losers_pf_None": pf is None and noloss is True,
            "mixed_pf_2.5": abs(pf2 - 2.5) < 1e-12 and noloss2 is False}


# ── 13. loader: dedup, sort, UTC index ────────────────────────────────────
@case("loader_dedup_sort_utc")
def c13():
    import tempfile
    rows = [(T0 + 3_600_000, 101.0), (T0, 100.0), (T0 + 3_600_000, 101.0),
            (T0 + 7_200_000, 102.0)]
    txt = "open_ts,open,high,low,close,volume\n" + "\n".join(
        f"{t},{p},{p},{p},{p},1.0" for t, p in rows)
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "x.csv")
        with open(p, "w") as f:
            f.write(txt)
        d = W.load_df(p)
    return {"rows3": len(d) == 3,
            "sorted": d.index.is_monotonic_increasing,
            "utc": str(d.index.tz) == "UTC",
            "first_open_100": float(d["open"].iloc[0]) == 100.0}


def main() -> int:
    import pack20_engine as _pe  # noqa: F401  (byte-identity asserted below)
    lines = [f"pack20 known answers -- {pd.Timestamp.now(tz='UTC'):%Y-%m-%dT%H:%M:%SZ}",
             f"pandas {pd.__version__} / numpy {np.__version__}",
             f"engine sha256: {W.ENGINE_SHA256}", ""]
    fails = 0
    for name, fn in CASES:
        try:
            checks = fn()
            ok = all(checks.values())
            bad = [k for k, v in checks.items() if not v]
        except Exception as e:                     # a crash is a FAIL, never silent
            ok, bad = False, [f"EXCEPTION {type(e).__name__}: {e}"]
        if not ok:
            fails += 1
        lines.append(f"{'PASS' if ok else 'FAIL'} {name}"
                     + (f"  [{'; '.join(bad)}]" if bad else ""))
    lines += ["", f"{len(CASES)} known answers, {fails} FAIL",
              "VERDICT: " + ("ALL PASS" if fails == 0 else "BLOCKED - no real-data artifact may run")]
    text = "\n".join(lines)
    print(text)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
