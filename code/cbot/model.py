"""walk_forward -- expanding/rolling logistic calibration of p(up in h bars).

CONTRACT (from suite.py)
    p = walk_forward(feats, cfg, cols)   ->  a per-bar probability, aligned to feats.index

METHOD
    For each test block, fit a logistic regression on a trailing window and
    predict the block. Two things keep it honest:

    EMBARGO = h+1 bars. The label at bar i is built from bars i..i+h, so the last
    training bar must satisfy j+h < t0. Training stops at t0-(h+1) exclusive,
    leaving h+1 bars of clearance between the last training label and the first
    test bar. Without this, the last training labels overlap the first test bars
    and the model is fitted on its own answer.

    Standardisation is fitted on TRAIN ONLY and applied to test. Fitting the
    scaler on the whole sample leaks the test distribution's location and scale
    into training.

Output is NaN outside the first testable block; the backtest ignores those bars.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


def walk_forward(feats: pd.DataFrame, cfg, cols) -> pd.Series:
    n = len(feats)
    p = np.full(n, np.nan)
    h = cfg.horizon_bars
    embargo = h + 1                      # see module docstring
    y = feats["y"].to_numpy(float)
    X = feats[cols].to_numpy(float)
    # a column that is entirely NaN carries nothing and breaks the scaler
    good = ~np.all(np.isnan(X), axis=0)
    X = X[:, good]
    if X.shape[1] == 0:
        return pd.Series(p, index=feats.index)

    first = cfg.train_bars + embargo + 1
    for t0 in range(first, n, cfg.refit_every):
        tr_end = t0 - embargo            # exclusive
        tr_start = max(0, tr_end - cfg.train_bars)
        te_end = min(t0 + cfg.refit_every, n)
        if tr_end - tr_start < cfg.min_train:
            continue
        xtr = X[tr_start:tr_end]
        ytr = y[tr_start:tr_end]
        m = (~np.isnan(ytr)) & np.isfinite(xtr).all(axis=1)
        if m.sum() < cfg.min_train or len(np.unique(ytr[m])) < 2:
            continue
        xtr, ytr = xtr[m], ytr[m]
        xte = X[t0:te_end]
        ok = np.isfinite(xte).all(axis=1)
        if not ok.any():
            continue
        sc = StandardScaler().fit(xtr)
        clf = LogisticRegression(C=1.0, max_iter=1000, solver="lbfgs")
        try:
            clf.fit(sc.transform(xtr), ytr)
        except Exception:
            continue
        block = np.full(te_end - t0, np.nan)
        block[ok] = clf.predict_proba(sc.transform(xte[ok]))[:, 1]
        p[t0:te_end] = block
    return pd.Series(p, index=feats.index)


def calibration(y: np.ndarray, p: np.ndarray) -> dict:
    """AUC and calibration slope.

    The slope is the coefficient of logit(p) when logit(y) is regressed on it --
    i.e. how much the model's own log-odds must be stretched to match outcomes.
    A well-calibrated model has slope ~1; suite.py accepts 0.7-1.3.
    Clipping p before the logit keeps +-inf out on confident misses.
    """
    m = np.isfinite(p) & np.isfinite(y)
    y, p = y[m], p[m]
    out = {"auc": float("nan"), "slope": float("nan"), "brier": float("nan"), "n": int(m.sum())}
    if len(y) < 50 or len(np.unique(y)) < 2:
        return out
    # AUC by the rank (Mann-Whitney) statistic
    r = pd.Series(p).rank().to_numpy()
    n1 = (y == 1).sum()
    n0 = (y == 0).sum()
    out["auc"] = float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
    out["brier"] = float(np.mean((p - y) ** 2))
    eps = 1e-6
    pc = np.clip(p, eps, 1 - eps)
    lg = np.log(pc / (1 - pc)).reshape(-1, 1)
    try:
        cal = LogisticRegression(C=1e6, max_iter=2000).fit(lg, y)
        out["slope"] = float(cal.coef_[0][0])
    except Exception:
        pass
    return out
