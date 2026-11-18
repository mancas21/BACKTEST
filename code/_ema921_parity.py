#!/usr/bin/env python
"""Parity: the repo port (code/ema921_engine.py) vs the source of record
(code/ema921_source.py, byte-identical to
`Downloads/ema_9_21_backtest-claude.py`).

Parity proves the SIGNAL and the EXECUTION are unchanged: the port runs with
the source's own cost regime (4.0 bps fee + 1.0 bps slip per side) and funding
OFF, so every trade and every equity point must match bit-for-bit. What the
repo adds (11 bps RT, funding at settlements, the accounting assertion) is
declared and measured in the real artifacts, never inside this check.

Run:  python code/_ema921_parity.py
Writes results/_ema921_parity.json; exits non-zero on any mismatch.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))

import ema921_engine as E  # noqa: E402


def load_source():
    path = os.path.join(ROOT, "code", "ema921_source.py")
    spec = importlib.util.spec_from_file_location("ema921_source", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ema921_source"] = mod       # dataclasses need the module here
    spec.loader.exec_module(mod)
    return mod


SRC = load_source()

CELLS = [
    ("BTCUSDT", "1h", "data/binance_klines_1h/BTCUSDT_1h.csv"),
    ("ETHUSDT", "15m", "data/binance_klines_15m/ETHUSDT_15m.csv"),
    ("SUIUSDT", "5m", "data/binance_klines_5m/SUIUSDT_5m.csv"),
    ("XRPUSDT", "1d", "data/binance_klines_1d/XRPUSDT_1d.csv"),
]
FIELDS = ["side", "entry", "exit", "sl", "tp", "qty", "bars", "pnl", "reason"]


def main() -> int:
    sp = SRC.Params()                        # 4.0 / 1.0, the source's own
    pp = E.Params(fee_bps=sp.fee_bps, slip_bps=sp.slip_bps, funding=False)
    out, failures = [], []
    for sym, tf, rel in CELLS:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            print(f"SKIP {sym} {tf}: no file {rel}")
            continue
        df = E.load_klines(path)
        st, se = SRC.run_backtest(df, sp)
        pt, pe, _ = E.run_backtest(df, pp)

        n_s, n_p = len(st), len(pt)
        eq_same = np.array_equal(se.to_numpy(float), pe.to_numpy(float))
        fields_ok, first_bad = n_s == n_p, None
        if n_s and n_s == n_p:
            for f in FIELDS:
                a, b = st[f], pt[f]
                if f in ("side", "reason"):
                    ok = list(a) == list(b)
                else:
                    ok = np.allclose(a.to_numpy(float), b.to_numpy(float),
                                     rtol=0, atol=1e-12)
                if not ok:
                    fields_ok = False
                    first_bad = f
                    break
            tt_ok = (list(st["entry_time"]) == list(pt["entry_time"]) and
                     list(st["exit_time"]) == list(pt["exit_time"]))
        else:
            tt_ok = False
        ms = SRC.metrics(st, se, sp)
        mp = E.metrics(pt, pe, pp)
        ret_ok = abs(ms["total_return_%"] - mp["return_pct"]) < 1e-9
        pf_ok = abs(float(ms.get("profit_factor", 0.0)) -
                    float(mp.get("profit_factor", 0.0))) < 1e-9
        ok = bool(n_s == n_p and eq_same and tt_ok and fields_ok and ret_ok and pf_ok)
        row = {
            "symbol": sym, "tf": tf, "bars": int(len(df)),
            "trades_source": n_s, "trades_port": n_p,
            "return_pct_source": float(ms["total_return_%"]),
            "return_pct_port": float(mp["return_pct"]),
            "pf_source": float(ms.get("profit_factor", 0.0)),
            "pf_port": float(mp.get("profit_factor", 0.0)),
            "equity_identical": bool(eq_same),
            "timestamps_identical": bool(tt_ok),
            "fields_identical": bool(fields_ok),
            "first_mismatched_field": first_bad,
            "pass": ok,
        }
        out.append(row)
        print(("PASS " if ok else "FAIL ") +
              f"{sym:10} {tf:>3} bars={len(df):8} trades={n_p:6} "
              f"ret%={mp['return_pct']:9.4f} PF={mp.get('profit_factor', 0):.4f}"
              + ("" if ok else f"  eq={eq_same} ts={tt_ok} fields={fields_ok} "
                                 f"bad={first_bad} ret={ret_ok} pf={pf_ok}"))
        if not ok:
            failures.append(sym + " " + tf)

    path = os.path.join(ROOT, "results", "_ema921_parity.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"cells": out, "failures": failures}, f, indent=1)
    print(f"\n{len(out) - len(failures)}/{len(out)} cells PASS -> {path}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
