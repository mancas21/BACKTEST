#!/usr/bin/env python
r"""
_xsml_feature_audit.py — known-answer / causality audit of the xsml features.

Runs BEFORE any market run (AGENTS.md: "Run a parity / self-check ... BEFORE
real-data"). Four checks, all on the REAL store:

  A. BUMP-LAST-BAR (the no-lookahead test). Recompute the features after
     changing ONLY the final bar of the series and assert every EARLIER
     output is bit-identical. A feature that peeks at the future changes
     when the future changes; a causal one cannot. This is the check the
     pybroker skills recommend and the repo did not have.
  B. FUNDING AS-OF CAUSALITY. `fund_last` at a bar must equal the last
     settlement AT OR BEFORE that bar's open — never a later one.
  C. CROSS-SECTIONAL DEMEAN. The three momentum features are demeaned per
     date; the cross-section must sum to ~0 on every date with enough
     names.
  D. NO FUTURE COLUMNS. The feature file must not contain any column that
     is a function of a future price (the label lives in the model step).

Usage:  & "$HOME\.venvs\pybroker\Scripts\python.exe" code/_xsml_feature_audit.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "xsml_features", os.path.join(HERE, "xsml_features.py"))
_fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fx)

FEATS_PATH = os.path.join(ROOT, "data", "xsml_features_1h.csv")
OUT_JSON = os.path.join(HERE, "_xsml_feature_audit.json")
CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append({"name": name, "pass": bool(ok), "detail": str(detail)[:300]})
    print(("  PASS  " if ok else "  FAIL  ") + name, flush=True)
    if not ok:
        print("        " + str(detail)[:300], flush=True)
    return bool(ok)


def to_ms(values):
    return np.asarray(values).astype("datetime64[ms]").astype("int64")


def main() -> int:
    if not os.path.exists(FEATS_PATH):
        print("REFUSED: no feature file; run code/xsml_features.py first")
        return 2
    feats = pd.read_csv(FEATS_PATH)
    feats["date"] = pd.to_datetime(feats["date"], utc=True)

    # ── A. bump-last-bar ──────────────────────────────────────────────────
    bad_syms = []
    for sym in sorted(feats["symbol"].unique()):
        df = _fx.load_klines(sym)
        df = df[df["date"] >= pd.Timestamp(_fx.STUDY_START, tz="UTC")].reset_index(drop=True)
        df = df.tail(900).reset_index(drop=True)
        base = _fx._compute_row(df)
        bumped = df.copy()
        bumped.loc[bumped.index[-1], ["open", "high", "low", "close"]] *= 1.05
        bumped.loc[bumped.index[-1], "volume"] *= 3.0
        after = _fx._compute_row(bumped)
        n = len(df) - 1
        for col in _fx.BAR_FEATURES:
            b, a = base[col][:-1], after[col][:-1]
            both_nan = np.isnan(b) & np.isnan(a)
            same = np.isclose(np.where(both_nan, 0.0, b),
                              np.where(both_nan, 0.0, a),
                              rtol=1e-9, atol=1e-9, equal_nan=True)
            if not bool(same.all()):
                bad_syms.append(f"{sym}:{col}")
    check("A bump-last-bar: every earlier feature is unchanged when only the "
          "last bar moves", not bad_syms, bad_syms[:8])

    # ── B. funding as-of causality ────────────────────────────────────────
    bad = []
    for sym in sorted(feats["symbol"].unique()):
        sub = feats[feats["symbol"] == sym].sort_values("open_ts")
        fund = _fx.load_funding(sym)
        if fund.empty:
            continue
        ts = fund["t"].to_numpy(np.int64)
        rs = fund["r"].to_numpy(float)
        idx = np.searchsorted(ts, sub["open_ts"].to_numpy(np.int64),
                              side="right") - 1
        expect = np.where(idx >= 0, rs[np.clip(idx, 0, None)], np.nan) * 1e4
        got = sub["fund_last"].to_numpy(float)
        m = np.isfinite(expect) & np.isfinite(got)
        if m.any() and not np.allclose(expect[m], got[m], rtol=1e-9, atol=1e-9):
            bad.append(f"{sym}: {int((~np.isclose(expect[m], got[m], rtol=1e-9)).sum())} filas")
        # a bar BEFORE the first settlement must carry NO funding value
        if (idx < 0).any() and np.isfinite(got[idx < 0]).any():
            bad.append(f"{sym}: funding presente antes del primer settlement")
    check("B funding as-of: fund_last es el ultimo settlement <= la barra",
          not bad, bad[:6])

    # ── C. cross-sectional demean ─────────────────────────────────────────
    bad = []
    for col in _fx.DEMEAN:
        g = feats.groupby(feats["date"].dt.floor("D"))[col]
        s = g.sum(min_count=4)
        worst = float(s.abs().max()) if len(s) else 0.0
        if worst > 1e-9:
            bad.append(f"{col}: suma diaria max {worst:.3e}")
    check("C los tres momentes son cross-sectionalmente demeanados por fecha",
          not bad, bad[:6])

    # ── D. no future columns ──────────────────────────────────────────────
    forbidden = [c for c in feats.columns
                 if any(k in c.lower() for k in
                        ("fwd", "forward", "lead", "target", "label", "next"))]
    check("D el fichero de features no contiene ninguna columna de futuro",
          not forbidden, forbidden)

    # ── cobertura y sanity de escala ─────────────────────────────────────
    cov = {c: round(float(feats[c].notna().mean() * 100), 1) for c in _fx.FEATURES}
    thin = {c: v for c, v in cov.items() if v < 90}
    check("E todas las features tienen >=90% de cobertura", not thin, thin)

    out = {"pass": all(c["pass"] for c in CHECKS), "checks": CHECKS,
           "coverage_pct": cov,
           "rows": int(len(feats)),
           "symbols": sorted(feats["symbol"].unique().tolist())}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"\n{'PASS' if out['pass'] else 'FAIL'} — {len(CHECKS)} checks -> {OUT_JSON}")
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
