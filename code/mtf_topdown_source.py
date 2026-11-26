#!/usr/bin/env python3
"""
mtf_topdown.py  --  4H Direction -> 1H Structure -> 15M Setup -> 5M Entry

Python port of the top-down MTF model. Everything is built from ONE 5m OHLCV
frame; higher timeframes are resampled from it and mapped back to the 5m clock
with merge_asof on bar CLOSE time, so a 5m bar only ever sees HTF bars that have
fully closed (no look-ahead). Pivots are confirmed `n` bars late. Entries fill at
the NEXT 5m open.

Rules (all knobs in Cfg):
  4H  Direction : close > EMA50 > EMA200 -> long bias; mirror -> short; else flat.
  1H  Structure : pivot swings (n=3). Bull = HH + HL and close > last swing low;
                  bear = LH + LL and close < last swing high. Must match 4H bias.
                  Last 1H swing range defines the value zone: longs only in the
                  discount (>= 50% retrace of the range), shorts in the premium.
  15M Setup     : liquidity sweep inside the 1H zone. Long = wick below the last
                  confirmed 15m swing low, close back above it. Short = mirror.
                  Setup stays armed for `setup_ttl_15m` 15m bars; cancelled if a 5m
                  close takes out the sweep extreme or 4H/1H bias flips.
  5M  Entry     : MSS after the sweep. Long = 5m close above the last confirmed 5m
                  swing high that formed after the sweep. Short = mirror.
  Risk          : SL = sweep extreme -/+ sl_atr_buf * ATR15, TP = rr * R, one
                  position at a time, risk_pct of equity per trade, leverage cap,
                  taker fee + slippage on both sides, same-bar SL/TP -> SL first.

Usage:
  python mtf_topdown.py --symbol SOLUSDT --days 180          # Binance USDT-M data
  python mtf_topdown.py --csv my_5m.csv                      # timestamp,o,h,l,c,v
  python mtf_topdown.py --synthetic                          # plumbing check only
  python mtf_topdown.py --test                               # causality tests
"""
from __future__ import annotations

import argparse
import time
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd

TF_MIN = {"5m": 5, "15m": 15, "1h": 60, "4h": 240}
OHLCV = ["open", "high", "low", "close", "volume"]


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
@dataclass
class Cfg:
    # 4H direction
    ema_fast: int = 50
    ema_slow: int = 200
    # 1H structure
    piv_1h: int = 3
    zone_min_retrace: float = 0.5      # long: close in lower 50% of last 1H swing range
    # 15M setup
    piv_15m: int = 3
    setup_ttl_15m: int = 16            # 16 x 15m = 4h
    # 5M entry
    piv_5m: int = 2
    # risk / execution
    atr_len: int = 14
    sl_atr_buf: float = 0.5            # x ATR(15m) beyond the sweep extreme
    rr: float = 2.0
    min_risk_pct: float = 0.0015       # skip stops tighter than 0.15%
    max_risk_pct: float = 0.03         # skip stops wider than 3%
    max_hold_5m: int = 288             # 24h time stop
    risk_pct: float = 0.01             # equity risked per trade
    max_leverage: float = 10.0
    fee: float = 0.0004                # taker, per side
    slip: float = 0.0001               # per side
    init_equity: float = 10_000.0
    allow_long: bool = True
    allow_short: bool = True


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
def fetch_klines(symbol: str, interval: str = "5m", days: int = 180,
                 cache_dir: str = "cache") -> pd.DataFrame:
    """Binance USDT-M futures klines, paginated, CSV-cached, closed candles only."""
    import requests

    url = "https://fapi.binance.com/fapi/v1/klines"
    step = TF_MIN[interval] * 60_000
    now = int(time.time() * 1000)
    start = now - days * 86_400_000
    path = Path(cache_dir) / f"{symbol}_{interval}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)

    cached = None
    if path.exists():
        cached = pd.read_csv(path, index_col=0, parse_dates=True)
        if len(cached):
            start = max(start, int(cached.index[-1].timestamp() * 1000) + step)

    rows = []
    while start < now:
        r = requests.get(url, params=dict(symbol=symbol, interval=interval,
                                          startTime=start, limit=1500), timeout=20)
        r.raise_for_status()
        k = r.json()
        if not k:
            break
        rows += k
        start = k[-1][0] + step
        time.sleep(0.1)

    new = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close", "volume",
                                      "ct", "qv", "n", "tb", "tq", "x"])
    if len(new):
        new["t"] = pd.to_datetime(new["t"], unit="ms")
        new = new.set_index("t")[OHLCV].astype(float)
        new = new[new.index + pd.Timedelta(milliseconds=step) <= pd.Timestamp.utcnow().tz_localize(None)]
    df = pd.concat([cached, new]) if cached is not None else new
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.index.name = "open_time"
    df.to_csv(path)
    return df[df.index >= pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=days)]


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    tcol = df.columns[0]
    ts = df[tcol]
    df.index = pd.to_datetime(ts, unit="ms") if np.issubdtype(ts.dtype, np.number) else pd.to_datetime(ts)
    df.columns = [c.lower() for c in df.columns]
    df = df[OHLCV].astype(float).sort_index()
    df.index.name = "open_time"
    return df[~df.index.duplicated()]


def synthetic_5m(days: int = 120, seed: int = 7, p0: float = 100.0) -> pd.DataFrame:
    """Regime-switching random walk with vol clustering. Plumbing tests only."""
    rng = np.random.default_rng(seed)
    n = days * 288
    drift = np.zeros(n)
    i = 0
    while i < n:
        L = int(rng.integers(288, 288 * 6))
        drift[i:i + L] = rng.choice([-1.0, 0.0, 1.0]) * 6e-5
        i += L
    vol = 9e-4 * np.exp(0.35 * np.cumsum(rng.normal(0, 0.05, n)) % 1.0)
    r = drift + vol * rng.standard_normal(n)
    c = p0 * np.exp(np.cumsum(r))
    o = np.r_[p0, c[:-1]]
    hi = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 1, n)) * vol * 0.6)
    lo = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 1, n)) * vol * 0.6)
    idx = pd.date_range("2026-01-01", periods=n, freq="5min")
    return pd.DataFrame({"open": o, "high": hi, "low": lo, "close": c,
                         "volume": rng.uniform(100, 1000, n)}, index=idx)


# --------------------------------------------------------------------------- #
# Causal multi-timeframe helpers
# --------------------------------------------------------------------------- #
def resample(df5: pd.DataFrame, tf: str) -> pd.DataFrame:
    """Left-labelled bars; incomplete bars (gaps / truncated tail) are dropped."""
    m = TF_MIN[tf]
    if m == 5:
        out = df5[OHLCV].copy()
    else:
        g = df5.resample(f"{m}min", label="left", closed="left")
        out = g.agg({"open": "first", "high": "max", "low": "min",
                     "close": "last", "volume": "sum"})
        out = out[g["close"].count() == m // 5]
    out["close_time"] = out.index + pd.Timedelta(minutes=m)
    return out


def align(base_ct: np.ndarray, htf: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Value of each HTF column as of each base bar close: latest HTF bar with
    close_time <= base close_time. Returns a frame positionally aligned to base."""
    left = pd.DataFrame({"t": base_ct})
    right = htf[["close_time"] + cols].reset_index(drop=True).sort_values("close_time")
    m = pd.merge_asof(left, right, left_on="t", right_on="close_time", direction="backward")
    return m.drop(columns=["t"])


def atr(h, l, c, n: int) -> np.ndarray:
    pc = pd.Series(c).shift(1)
    tr = pd.concat([pd.Series(h) - pd.Series(l), (pd.Series(h) - pc).abs(),
                    (pd.Series(l) - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def swings(high: np.ndarray, low: np.ndarray, n: int) -> dict:
    """Pivot highs/lows (n bars each side), CONFIRMED n bars after the pivot bar.
    Returns arrays indexed by bar j = 'what is known at the close of bar j':
      sh/sl      last confirmed swing high/low price
      shp/slp    the swing before that
      shi/sli    bar index of the last confirmed pivot"""
    N = len(high)
    hs, ls = pd.Series(high), pd.Series(low)
    ph = (hs == hs.rolling(2 * n + 1, center=True).max()).to_numpy()
    pl = (ls == ls.rolling(2 * n + 1, center=True).min()).to_numpy()

    def conf(piv, val):
        v = np.full(N, np.nan)
        ix = np.full(N, np.nan)
        v[n:] = np.where(piv[:N - n], val[:N - n], np.nan)
        ix[n:] = np.where(piv[:N - n], np.arange(N - n), np.nan)
        return v, ix

    def last_prev(v, ix):
        s = pd.Series(v)
        last = s.ffill().to_numpy()
        lasti = pd.Series(ix).ffill().to_numpy()
        prev = s.dropna().shift(1).reindex(s.index).ffill().to_numpy()
        return last, prev, lasti

    sh, shp, shi = last_prev(*conf(ph, high))
    sl, slp, sli = last_prev(*conf(pl, low))
    return dict(sh=sh, shp=shp, shi=shi, sl=sl, slp=slp, sli=sli)


def shift1(a: np.ndarray) -> np.ndarray:
    out = np.empty_like(a, dtype=float)
    out[0] = np.nan
    out[1:] = a[:-1]
    return out


# --------------------------------------------------------------------------- #
# Feature stack (4H -> 1H -> 15M -> 5M), all expressed on the 5m clock
# --------------------------------------------------------------------------- #
def build_features(df5: pd.DataFrame, cfg: Cfg) -> pd.DataFrame:
    b = resample(df5, "5m")
    base_ct = b["close_time"].to_numpy()
    h4, h1, m15 = resample(df5, "4h"), resample(df5, "1h"), resample(df5, "15m")

    # ---- 4H: direction ----------------------------------------------------- #
    c4 = h4["close"]
    ef = c4.ewm(span=cfg.ema_fast, adjust=False).mean()
    es = c4.ewm(span=cfg.ema_slow, adjust=False).mean()
    d4 = np.select([(c4 > ef) & (ef > es), (c4 < ef) & (ef < es)], [1.0, -1.0], 0.0)
    d4[:cfg.ema_slow] = 0.0                      # EMA warm-up
    h4["dir4"] = d4

    # ---- 1H: structure + value zone ---------------------------------------- #
    s1 = swings(h1["high"].to_numpy(), h1["low"].to_numpy(), cfg.piv_1h)
    c1 = h1["close"].to_numpy()
    bull = (s1["sh"] > s1["shp"]) & (s1["sl"] > s1["slp"]) & (c1 > s1["sl"])
    bear = (s1["sh"] < s1["shp"]) & (s1["sl"] < s1["slp"]) & (c1 < s1["sh"])
    h1["st1"] = np.where(bull, 1.0, np.where(bear, -1.0, 0.0))
    h1["sh1"], h1["sl1"] = s1["sh"], s1["sl"]

    # ---- 15M: sweep inside the 1H zone ------------------------------------- #
    s15 = swings(m15["high"].to_numpy(), m15["low"].to_numpy(), cfg.piv_15m)
    slk, shk = shift1(s15["sl"]), shift1(s15["sh"])          # known BEFORE this bar
    lo15, hi15, c15 = (m15[k].to_numpy() for k in ("low", "high", "close"))

    a = align(m15["close_time"].to_numpy(), h4, ["dir4"])
    a1 = align(m15["close_time"].to_numpy(), h1, ["st1", "sh1", "sl1"])
    rng = a1["sh1"].to_numpy() - a1["sl1"].to_numpy()
    sh1, sl1 = a1["sh1"].to_numpy(), a1["sl1"].to_numpy()
    long_zone = (c15 <= sh1 - cfg.zone_min_retrace * rng) & (c15 > sl1)
    short_zone = (c15 >= sl1 + cfg.zone_min_retrace * rng) & (c15 < sh1)
    sweep_l = (lo15 < slk) & (c15 > slk)
    sweep_s = (hi15 > shk) & (c15 < shk)
    d4_15, st_15 = a["dir4"].to_numpy(), a1["st1"].to_numpy()
    m15["setup_l"] = (sweep_l & long_zone & (d4_15 == 1) & (st_15 == 1)).astype(float)
    m15["setup_s"] = (sweep_s & short_zone & (d4_15 == -1) & (st_15 == -1)).astype(float)
    m15["atr15"] = atr(hi15, lo15, c15, cfg.atr_len)
    m15["sw_low"], m15["sw_high"] = lo15, hi15

    # ---- map to the 5m clock ------------------------------------------------ #
    f = b[["open", "high", "low", "close"]].copy()
    A4 = align(base_ct, h4, ["dir4"])
    A1 = align(base_ct, h1, ["st1"])
    A15 = align(base_ct, m15, ["setup_l", "setup_s", "atr15", "sw_low", "sw_high"])
    f["dir4"] = A4["dir4"].fillna(0).to_numpy()
    f["st1"] = A1["st1"].fillna(0).to_numpy()
    on_close = A15["close_time"].to_numpy() == base_ct      # fire only on the 15m close bar
    f["evt_l"] = on_close & (A15["setup_l"].fillna(0).to_numpy() == 1)
    f["evt_s"] = on_close & (A15["setup_s"].fillna(0).to_numpy() == 1)
    f["atr15"] = A15["atr15"].to_numpy()
    f["sw_low"], f["sw_high"] = A15["sw_low"].to_numpy(), A15["sw_high"].to_numpy()

    # ---- 5M: swing levels for the MSS trigger (known before this bar) -------- #
    s5 = swings(f["high"].to_numpy(), f["low"].to_numpy(), cfg.piv_5m)
    f["sh5"], f["sh5i"] = shift1(s5["sh"]), shift1(s5["shi"])
    f["sl5"], f["sl5i"] = shift1(s5["sl"]), shift1(s5["sli"])
    return f


# --------------------------------------------------------------------------- #
# Backtest engine
# --------------------------------------------------------------------------- #
def backtest(f: pd.DataFrame, cfg: Cfg) -> pd.DataFrame:
    o, h, l, c = (f[k].to_numpy() for k in ("open", "high", "low", "close"))
    d4, st1 = f["dir4"].to_numpy(), f["st1"].to_numpy()
    evt_l, evt_s = f["evt_l"].to_numpy(), f["evt_s"].to_numpy()
    swl, swh, atr15 = f["sw_low"].to_numpy(), f["sw_high"].to_numpy(), f["atr15"].to_numpy()
    sh5, sh5i, sl5, sl5i = (f[k].to_numpy() for k in ("sh5", "sh5i", "sl5", "sl5i"))
    idx = f.index
    n, ttl = len(f), cfg.setup_ttl_15m * 3

    eq, pos, armed, trades = cfg.init_equity, None, None, []

    for i in range(n):
        # ---------------- manage open position ---------------- #
        if pos is not None:
            s, px, why = pos["side"], None, None
            if s == 1:
                if l[i] <= pos["sl"]:
                    px, why = min(o[i], pos["sl"]) * (1 - cfg.slip), "sl"
                elif h[i] >= pos["tp"]:
                    px, why = pos["tp"], "tp"
            else:
                if h[i] >= pos["sl"]:
                    px, why = max(o[i], pos["sl"]) * (1 + cfg.slip), "sl"
                elif l[i] <= pos["tp"]:
                    px, why = pos["tp"], "tp"
            if px is None and i - pos["i0"] + 1 >= cfg.max_hold_5m:
                px, why = c[i], "time"
            if px is None and i == n - 1:
                px, why = c[i], "eod"
            if px is not None:
                gross = s * (px - pos["entry"]) * pos["qty"]
                fees = cfg.fee * pos["qty"] * (pos["entry"] + px)
                pnl = gross - fees
                eq += pnl
                trades.append(dict(entry_time=idx[pos["i0"]], exit_time=idx[i], side=s,
                                   entry=pos["entry"], exit=px, sl=pos["sl"], tp=pos["tp"],
                                   qty=pos["qty"], pnl=pnl, r=pnl / pos["risk_usd"],
                                   bars=i - pos["i0"] + 1, reason=why, equity=eq))
                pos, armed = None, None
            continue

        # ---------------- 15M setup (armed on the 15m close) ---------------- #
        if evt_l[i] and cfg.allow_long:
            armed = (1, i, swl[i])
        elif evt_s[i] and cfg.allow_short:
            armed = (-1, i, swh[i])
        if armed is not None:
            side, ai, ext = armed
            if (i - ai > ttl or d4[i] != side or st1[i] != side
                    or (side == 1 and c[i] < ext) or (side == -1 and c[i] > ext)):
                armed = None
        if armed is None or i + 1 >= n:
            continue

        # ---------------- 5M entry: MSS after the sweep ---------------- #
        side, ai, ext = armed
        lo_i = max(0, ai - 2)
        if side == 1:
            trig = sh5i[i] >= ai - 2 and c[i] > sh5[i]
            stop_ref = min(ext, l[lo_i:i + 1].min())
        else:
            trig = sl5i[i] >= ai - 2 and c[i] < sl5[i]
            stop_ref = max(ext, h[lo_i:i + 1].max())
        if not trig:
            continue

        entry = o[i + 1] * (1 + cfg.slip * side)
        sl = stop_ref - side * cfg.sl_atr_buf * atr15[i]
        risk = side * (entry - sl)
        armed = None
        if not (cfg.min_risk_pct * entry <= risk <= cfg.max_risk_pct * entry) or eq <= 0:
            continue
        qty = min(eq * cfg.risk_pct / risk, eq * cfg.max_leverage / entry)
        pos = dict(side=side, i0=i + 1, entry=entry, sl=sl, tp=entry + side * cfg.rr * risk,
                   qty=qty, risk_usd=qty * risk)

    return pd.DataFrame(trades)


# --------------------------------------------------------------------------- #
# Stats
# --------------------------------------------------------------------------- #
def stats(tr: pd.DataFrame, init_eq: float) -> dict:
    if tr.empty:
        return {"trades": 0}
    eq = init_eq + tr["pnl"].cumsum().to_numpy()
    peak = np.maximum.accumulate(np.r_[init_eq, eq])[1:]
    gp, gl = tr.loc[tr.pnl > 0, "pnl"].sum(), -tr.loc[tr.pnl < 0, "pnl"].sum()
    daily = pd.Series(eq, index=tr["exit_time"]).resample("1D").last().ffill().pct_change().dropna()
    return {
        "trades": len(tr),
        "long/short": f"{(tr.side == 1).sum()}/{(tr.side == -1).sum()}",
        "win_rate": round((tr.pnl > 0).mean(), 3),
        "avg_R": round(tr.r.mean(), 3),
        "profit_factor": round(gp / gl, 2) if gl > 0 else np.inf,
        "total_return_%": round((eq[-1] / init_eq - 1) * 100, 2),
        "max_dd_%": round((eq / peak - 1).min() * 100, 2),
        "sharpe_daily_ann": round(daily.mean() / daily.std() * np.sqrt(365), 2) if daily.std() > 0 else np.nan,
        "avg_bars_5m": round(tr.bars.mean(), 1),
        "exits": tr.reason.value_counts().to_dict(),
    }


def run(df5: pd.DataFrame, cfg: Cfg | None = None):
    cfg = cfg or Cfg()
    f = build_features(df5, cfg)
    tr = backtest(f, cfg)
    return tr, stats(tr, cfg.init_equity), f


# --------------------------------------------------------------------------- #
# Causality (look-ahead) tests
# --------------------------------------------------------------------------- #
def test_causality(df5: pd.DataFrame, cfg: Cfg | None = None, cuts=(0.55, 0.7, 0.85)) -> bool:
    """1) every feature at bar t is identical whether or not data after t exists.
       2) trades that fully close before the cut are identical in the truncated run."""
    cfg = cfg or Cfg()
    full_f = build_features(df5, cfg)
    full_tr = backtest(full_f, cfg)
    cols = [c for c in full_f.columns if c not in ("open", "high", "low", "close")]
    ok = True
    for q in cuts:
        k = int(len(df5) * q)
        k -= k % 48                                   # land on a 4h boundary
        sub = df5.iloc[:k]
        sub_f = build_features(sub, cfg)
        for col in cols:
            a, bb = full_f[col].to_numpy()[:k], sub_f[col].to_numpy()
            same = np.array_equal(a.astype(float), bb.astype(float), equal_nan=True)
            if not same:
                print(f"  [FAIL] feature '{col}' differs at cut {q:.2f}")
                ok = False
        sub_tr = backtest(sub_f, cfg)
        cut_t = sub.index[-1]
        a = full_tr[full_tr.exit_time < cut_t].reset_index(drop=True)
        bb = sub_tr[sub_tr.reason != "eod"].reset_index(drop=True)
        cols_t = ["entry_time", "exit_time", "side", "entry", "exit"]
        if len(a) != len(bb) or not (len(a) == 0 or a[cols_t].equals(bb[cols_t])):
            print(f"  [FAIL] trades differ at cut {q:.2f}: full={len(a)} trunc={len(bb)}")
            ok = False
    print("causality:", "PASS" if ok else "FAIL")
    return ok


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="SOLUSDT")
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--csv")
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--rr", type=float)
    ap.add_argument("--risk", type=float, help="risk per trade, fraction of equity")
    ap.add_argument("--out", default="trades.csv")
    a = ap.parse_args()

    cfg = Cfg()
    if a.rr:
        cfg.rr = a.rr
    if a.risk:
        cfg.risk_pct = a.risk

    if a.csv:
        df5 = load_csv(a.csv)
    elif a.synthetic or a.test:
        df5 = synthetic_5m(days=a.days)
    else:
        df5 = fetch_klines(a.symbol, "5m", a.days)
    print(f"{len(df5)} x 5m bars  {df5.index[0]} -> {df5.index[-1]}")

    if a.test:
        test_causality(df5, cfg)

    tr, st, _ = run(df5, cfg)
    print("\nconfig:", asdict(cfg))
    print("\nstats:")
    for k, v in st.items():
        print(f"  {k:>18}: {v}")
    if len(tr):
        tr.to_csv(a.out, index=False)
        print(f"\n{len(tr)} trades -> {a.out}")


if __name__ == "__main__":
    main()
