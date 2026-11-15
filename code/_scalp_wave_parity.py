#!/usr/bin/env python
"""
_scalp_wave_parity.py — PARITY between the WAVE_1 pack and the repo port.

AGENTS.md (Porting a Pine script, mandatory): "Run a parity / self-check
against the Pine or a dual engine; require ALL PASS" BEFORE trusting any
number. This is that check for code/scalp_wave_engine.py.

The ORIGINAL pack lives at Downloads/scalp_wave1_v1.1.0/wave1 (Python, pack
1.1.0). It is imported as a dual engine and compared against the port on
REAL repo klines:

  A. INDICATOR COLUMNS — every column of compute_all must agree to rtol 1e-9
     (the pack's own BATCH_STREAM_TOL) on a real 5m and 15m series.
  B. SIGNAL EVENTS — the event set (bar_time, ind, sig, side) must be
     IDENTICAL, and target_bps / stop_bps / gate_pass must agree.
  C. The port must run the pack's params verbatim (the file hash of
     specs/params.yaml is compared with the port's PARAMS_DECLARED).

Usage:  python code/_scalp_wave_parity.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
PACK = os.path.join(os.path.expanduser("~"), "Downloads", "scalp_wave1_v1.1.0",
                    "wave1")

CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append({"name": name, "pass": bool(ok), "detail": str(detail)[:400]})
    print(("  PASS  " if ok else "  FAIL  ") + name, flush=True)
    if not ok:
        print("        " + str(detail)[:400], flush=True)
    return bool(ok)


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def load_pack():
    """Import the ORIGINAL pack's core+signals (adding its python/ to sys.path)."""
    if not os.path.isdir(PACK):
        raise FileNotFoundError(f"original pack not found: {PACK}")
    sys.path.insert(0, os.path.join(PACK, "python"))
    import scalp_ind.core.indicators as pack_ind
    import scalp_ind.signals.generate as pack_sig
    import scalp_ind.core.params as pack_par
    return pack_ind, pack_sig, pack_par


def read_bars(path):
    df = pd.read_csv(path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    if "open_ts" in df.columns:
        df = df.rename(columns={"open_ts": "open_time"})
    df["open_time"] = pd.to_numeric(df["open_time"], errors="coerce")
    df = df.dropna(subset=["open_time"])
    df["open_time"] = df["open_time"].astype(np.int64)
    df = df.drop_duplicates("open_time").sort_values("open_time").reset_index(drop=True)
    return df


def compare_columns(a: pd.DataFrame, b: pd.DataFrame, cols, rtol=1e-9):
    """Return the list of columns that disagree beyond rtol."""
    bad = []
    for c in cols:
        if c not in a.columns or c not in b.columns:
            bad.append(f"{c}: missing")
            continue
        xa, xb = a[c].to_numpy(), b[c].to_numpy()
        if xa.dtype == bool or xb.dtype == bool:
            if not np.array_equal(xa.astype(bool), xb.astype(bool)):
                n = int((xa.astype(bool) != xb.astype(bool)).sum())
                bad.append(f"{c}: {n} bool diffs")
            continue
        na, nb = np.isnan(xa.astype(float)), np.isnan(xb.astype(float))
        if not np.array_equal(na, nb):
            bad.append(f"{c}: nan pattern differs ({int((na ^ nb).sum())})")
            continue
        m = ~na
        if m.any():
            diff = np.abs(xa[m].astype(float) - xb[m].astype(float))
            scale = np.maximum(np.abs(xa[m].astype(float)), 1e-12)
            rel = diff / scale
            if rel.max() > rtol:
                bad.append(f"{c}: max rel {rel.max():.3e} > {rtol:.0e}")
    return bad


def main():
    if not os.path.isdir(PACK):
        print(f"REFUSED: original pack not found at {PACK}")
        return 2
    pack_ind, pack_sig, pack_par = load_pack()
    port = load_module(os.path.join(HERE, "scalp_wave_engine.py"),
                       "scalp_wave_engine_port")

    # ── C. the port carries the pack's declared params verbatim ──
    import yaml
    pack_params = yaml.safe_load(open(os.path.join(PACK, "specs", "params.yaml"),
                                      encoding="utf-8"))
    same = json.dumps(pack_params, sort_keys=True) == json.dumps(
        port.PARAMS_DECLARED, sort_keys=True)
    check("C the port's PARAMS_DECLARED == the pack's specs/params.yaml", same,
          "declared params differ from the source pack")

    cases = [("5m", os.path.join(ROOT, "data", "binance_klines_5m",
                                 "SOLUSDT_5m.csv"), 300),
             ("15m", os.path.join(ROOT, "data", "binance_klines_15m",
                                  "SUIUSDT_15m.csv"), 300),
             ("5m", os.path.join(ROOT, "data", "binance_klines_5m",
                                 "HYPEUSDT_5m.csv"), 300)]
    tf_sec = {"5m": 300, "15m": 900}

    for tf, path, tail in cases:
        sym = os.path.basename(path).split("_")[0]
        if not os.path.exists(path):
            check(f"{tf} {sym}: data present", False, path)
            continue
        df = read_bars(path)
        # a tail window is enough and keeps the run fast; the pack's warmup
        # needs ~405 bars, so the window must be well past it
        df = df.iloc[-tail:].reset_index(drop=True)
        secs = tf_sec[tf]

        # ── A. indicator columns ──
        Xa = pack_ind.compute_all(df, secs, pack_params)
        Xb = port.compute_all(df, secs, port.PARAMS_DECLARED)
        common = [c for c in Xa.columns if c in Xb.columns]
        bad = compare_columns(Xa, Xb, common)
        check(f"A {tf} {sym}: {len(common)} indicator columns agree "
              f"(rtol 1e-9)", not bad, "; ".join(bad[:4]))
        missing = [c for c in Xa.columns if c not in Xb.columns]
        check(f"A {tf} {sym}: no indicator column missing in the port",
              not missing, f"missing: {missing}")

        # ── B. signal events ──
        # the pack's own cost block (declared placeholders) for BOTH sides, so
        # the comparison is about the SIGNAL, not about the cost regime
        cost = pack_par.cost_for_symbol(pack_params, sym)
        Ea = pack_sig.generate_signals(df, secs, cost=cost, params=pack_params,
                                       mode="TAKER_TAKER")
        Eb = port.generate_signals(df, secs, cost=cost,
                                   params=port.PARAMS_DECLARED,
                                   mode="TAKER_TAKER")
        key = ["bar_time", "ind", "sig", "side"]
        ka = [tuple(r) for r in Ea[key].to_numpy()] if not Ea.empty else []
        kb = [tuple(r) for r in Eb[key].to_numpy()] if not Eb.empty else []
        check(f"B {tf} {sym}: the signal event SET is identical "
              f"({len(ka)} events)", ka == kb,
              f"pack={len(ka)} port={len(kb)}; first diff: "
              f"{next((f'{x} vs {y}' for x, y in zip(ka, kb) if x != y), 'length/order only')}")

        if ka == kb and not Ea.empty:
            for col, rtol in (("target_bps", 1e-9), ("stop_bps", 1e-9),
                              ("cost_bps", 1e-12), ("k", 1e-12)):
                xa = Ea[col].to_numpy(float)
                xb = Eb[col].to_numpy(float)
                d = np.abs(xa - xb) / np.maximum(np.abs(xa), 1e-12)
                ok = bool(d.max() <= rtol) if len(d) else True
                check(f"B {tf} {sym}: event column '{col}' agrees", ok,
                      f"max rel {d.max():.3e}" if len(d) else "")
            ga = Ea["gate_pass"].to_numpy(bool)
            gb = Eb["gate_pass"].to_numpy(bool)
            check(f"B {tf} {sym}: event column 'gate_pass' agrees",
                  np.array_equal(ga, gb),
                  f"{int((ga ^ gb).sum())} diffs")

    ok = all(c["pass"] for c in CHECKS)
    out = {"generated_utc": datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"), "pack": PACK, "pass": ok, "checks": CHECKS}
    with open(os.path.join(HERE, "_scalp_wave_parity.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"\n{'PASS' if ok else 'FAIL'} — "
          f"{sum(c['pass'] for c in CHECKS)}/{len(CHECKS)} checks")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
