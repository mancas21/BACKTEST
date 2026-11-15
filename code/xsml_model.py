#!/usr/bin/env python
r"""
xsml_model.py — the `xsml` model: one fit on DEV, predictions for OOS.

Runs under the pybroker venv (sklearn lives there):

    & "$HOME\.venvs\pybroker\Scripts\python.exe" code/xsml_model.py --variant v2

VARIANTS (all declared in results/xsml_variants_pre_registration.md BEFORE
any of them was run; each is a separate book with its own artifact):

  v1  label = 24-bar forward return, demeaned cross-sectionally
      (the original book; its artifact is a2fc128ff0f42f5d)
  v2  label = the payoff the book REALLY REALIZES with stop 2x ATR and
      target 2x ATR, in R units (the stop is the unit) -- the objective is
      aligned with the execution
  v3  label = 72-bar forward return, demeaned (fewer, richer turns)
  v4  label = the realized payoff with stop 1x ATR and target 3x ATR
      (asymmetric reward:risk)

WHAT IS FIXED HERE AND WHY IT IS NOT TUNED
-----------------------------------------
The estimator and its hyper-parameters are declared and fitted ONCE on DEV.
There is no grid, no Optuna, no model selection by score: a second fit would
be a second trial, and the repo counts trials.

THE LABEL IS BUILT HERE, NOT IN THE FEATURE FILE
-----------------------------------------------
The forward return (or the realized payoff) is computed here so that
`data/xsml_features_1h.csv` can never carry future information.

PURITY / EMBARGO
-----------------
The label horizon is HORIZON bars, so the last HORIZON DEV bars of every
symbol are DROPPED from the fit: their label window reaches into OOS.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))

_spec = importlib.util.spec_from_file_location(
    "xsml_repo_primitives", os.path.join(HERE, "scalp_wave_engine.py"))
_repo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_repo)

FEATS = os.path.join(ROOT, "data", "xsml_features_1h.csv")
META = os.path.join(HERE, "_xsml_model_meta.json")

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT",
           "SUIUSDT", "ARBUSDT", "JUPUSDT", "HYPEUSDT"]
FEATURES = ["mom_24", "mom_72", "mom_1d", "vol_pct", "vol_ratio", "chop",
            "vol_z", "vwap_dist", "fund_last", "fund_avg3"]
DEV_END = "2026-04-30"
OOS_START = "2026-05-01"
SEED = 42
MODEL_KW = dict(max_iter=200, learning_rate=0.05, max_depth=3,
                 min_samples_leaf=20, l2_regularization=1.0,
                 random_state=SEED)

# variant -> (horizon bars, label kind, stop mult, target mult)
VARIANTS = {
    "v1": dict(horizon=24, label="fwd", stop_mult=2.0, target_mult=2.0),
    "v2": dict(horizon=24, label="payoff", stop_mult=2.0, target_mult=2.0),
    "v3": dict(horizon=72, label="fwd", stop_mult=2.0, target_mult=2.0),
    "v4": dict(horizon=24, label="payoff", stop_mult=1.0, target_mult=3.0),
}


def _to_ms(values):
    return np.asarray(values).astype("datetime64[ms]").astype("int64")


def load_klines(sym: str):
    p = os.path.join(ROOT, "data", "binance_klines_1h", f"{sym}_1h.csv")
    df = pd.read_csv(p)
    df.columns = [c.strip().lower() for c in df.columns]
    df["ms"] = _to_ms(pd.to_datetime(df["open_ts"], unit="ms", utc=True))
    df = df.sort_values("ms").drop_duplicates("ms").reset_index(drop=True)
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    lo = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    atr = _repo.atr(h, lo, c, 14)
    with np.errstate(invalid="ignore", divide="ignore"):
        atr_bps = atr / c * 1e4
    return dict(ms=df["ms"].to_numpy(np.int64), open=o, high=h, low=lo,
                close=c, atr_bps=atr_bps)


def payoff_label(k: dict, horizon: int, stop_mult: float,
                 target_mult: float) -> np.ndarray:
    """The payoff the book REALIZES from a signal bar, in R units (the stop
    distance is the unit).

    Same rules as the engine: entry at the NEXT bar's open; stop-first on
    ties; a bar that opens beyond the stop fills at the OPEN; the target is
    filled at the target level; if neither is touched within the horizon the
    position is closed at the horizon's close.

    A LONG is the reference; the short side is the mirror (the engine shorts
    the bottom of the rank, and for a demeaned cross-sectional label the
    short payoff is the negative of the long payoff of the mirrored path).
    """
    n = len(k["close"])
    out = np.full(n, np.nan)
    o, h, lo, c, atr = (k["open"], k["high"], k["low"], k["close"], k["atr_bps"])
    for t in range(n - 1):
        a = atr[t]
        if not np.isfinite(a) or a <= 0:
            continue
        entry = o[t + 1]
        stop_dist = entry * a * stop_mult / 1e4
        if stop_dist <= 0:
            continue
        stop = entry - stop_dist
        target = entry + target_mult * a * entry / 1e4
        payoff = None
        for j in range(t + 1, min(n, t + 1 + horizon)):
            # STOP FIRST on ties; a gap through the stop fills at the open
            if lo[j] <= stop:
                payoff = (min(o[j], stop) - entry) / stop_dist
                break
            if h[j] >= target:
                payoff = (target - entry) / stop_dist
                break
        if payoff is None:
            j = min(n - 1, t + horizon)
            payoff = (c[j] - entry) / stop_dist
        out[t] = payoff
    return out


def build_label(feats: pd.DataFrame, variant: str, klines: dict) -> pd.DataFrame:
    cfg = VARIANTS[variant]
    horizon = cfg["horizon"]
    feats = feats.sort_values(["symbol", "open_ts"]).reset_index(drop=True)
    if cfg["label"] == "fwd":
        feats["fwd_raw"] = feats.groupby("symbol")["close"].shift(-horizon) / \
            feats["close"] - 1.0
    else:
        # the realized payoff, per symbol, on its own bars
        cols = {}
        for sym, g in feats.groupby("symbol"):
            k = klines[sym]
            pos = np.clip(np.searchsorted(k["ms"], g["open_ts"].to_numpy(np.int64)),
                          0, len(k["ms"]) - 1)
            hit = k["ms"][pos] == g["open_ts"].to_numpy(np.int64)
            lab = payoff_label(k, horizon, cfg["stop_mult"], cfg["target_mult"])
            cols[sym] = (pos, hit, lab)
        raw = np.full(len(feats), np.nan)
        for sym, g in feats.groupby("symbol"):
            pos, hit, lab = cols[sym]
            idx = g.index.to_numpy()
            ok = hit & np.isfinite(lab[pos])
            raw[idx[ok]] = lab[pos[ok]]
        feats["fwd_raw"] = raw
    day = feats["date"].dt.floor("D")
    feats["y"] = feats["fwd_raw"] - feats.groupby(day)["fwd_raw"].transform("mean")
    return feats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="v1", choices=sorted(VARIANTS))
    args = ap.parse_args()
    variant = args.variant
    cfg = VARIANTS[variant]
    horizon = cfg["horizon"]

    if not os.path.exists(FEATS):
        print("REFUSED: no feature file; run code/xsml_features.py first")
        return 2
    feats = pd.read_csv(FEATS)
    feats["date"] = pd.to_datetime(feats["date"], utc=True)
    klines = {s: load_klines(s) for s in SYMBOLS}
    feats = build_label(feats, variant, klines)

    dev_end = pd.Timestamp(DEV_END, tz="UTC")
    oos_start = pd.Timestamp(OOS_START, tz="UTC")
    feats["split"] = np.where(feats["date"] >= oos_start, "OOS",
                              np.where(feats["date"] <= dev_end, "DEV", "OOS"))

    # PURGE: the last HORIZON DEV bars of each symbol carry a label window that
    # reaches into the OOS window.
    feats["bar_no"] = feats.groupby("symbol").cumcount()
    last_dev_bar = (feats[feats["split"] == "DEV"]
                     .groupby("symbol")["bar_no"].max())
    last_dev_bar = last_dev_bar.reindex(feats["symbol"]).to_numpy(float)
    feats["is_last_dev_label"] = (
        (feats["split"] == "DEV") &
        (feats["bar_no"].to_numpy(float) >= last_dev_bar - horizon + 1))

    train = feats[(feats["split"] == "DEV") & (~feats["is_last_dev_label"]) &
                  feats["y"].notna() & feats[FEATURES].notna().all(axis=1)]
    print(f"variant {variant}: train rows {len(train)}  symbols {train['symbol'].nunique()}"
          f"  purged {int(feats['is_last_dev_label'].sum())}")

    X = train[FEATURES].to_numpy(float)
    y = train["y"].to_numpy(float)
    print(f"  label: mean {y.mean():.4e} std {y.std():.4e} "
          f"min {y.min():.4f} max {y.max():.4f}")

    model = HistGradientBoostingRegressor(**MODEL_KW)
    model.fit(X, y)
    insample = model.predict(X)
    ss_res = float(((y - insample) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot else float("nan")
    corr = float(np.corrcoef(insample, y)[0, 1]) if len(y) > 2 else float("nan")
    print(f"  DEV in-sample: R2 {r2:.4f}  corr(pred, y) {corr:.4f}")

    ok = feats[FEATURES].notna().all(axis=1)
    feats["pred"] = np.nan
    feats.loc[ok, "pred"] = model.predict(
        feats.loc[ok, FEATURES].to_numpy(float))

    oos = feats[(feats["split"] == "OOS") & feats["y"].notna() &
                feats["pred"].notna()]
    oc = float(np.corrcoef(oos["pred"], oos["y"])[0, 1]) if len(oos) > 2 \
        else float("nan")
    print(f"  OOS: {len(oos)} rows  corr(pred, y) {oc:.4f}")

    out_name = "xsml_preds.csv" if variant == "v1" else f"xsml_preds_{variant}.csv"
    out_path = os.path.join(ROOT, "data", out_name)
    feats[["symbol", "open_ts", "date", "pred", "y", "split"]].to_csv(
        out_path, index=False)
    meta = dict(variant=variant, features=FEATURES, horizon_bars=horizon,
                label=cfg["label"], stop_mult=cfg["stop_mult"],
                target_mult=cfg["target_mult"], dev_end=DEV_END,
                oos_start=OOS_START, seed=SEED,
                model="HistGradientBoostingRegressor", model_kw=MODEL_KW,
                train_rows=int(len(train)),
                purged_dev_rows=int(feats["is_last_dev_label"].sum()),
                dev_insample_r2=r2, dev_insample_corr=corr,
                oos_rows=int(len(oos)), oos_corr=oc,
                preds_file=out_name)
    meta_name = ("_xsml_model_meta.json" if variant == "v1"
                 else f"_xsml_model_meta_{variant}.json")
    with open(os.path.join(HERE, meta_name), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    print(f"  escrito {out_path}  {len(feats)} filas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
