#!/usr/bin/env python3
"""
100-Prompt Backtest Pack — Funding strategies (91-100)
=====================================================
Single-pair engine with funding rates aligned to klines.

Funding mechanics
- Binance USDT-M settles every 8h (00:00 / 08:00 / 16:00 UTC).
- A bar whose open coincides with a settlement carries that settlement's rate.
- Signals that depend on a settlement are evaluated on the settlement bar and
  filled at the next bar's open, i.e. roughly one hour after settlement.
- "Exit at the next settlement" is implemented as an 8-bar (8h) time stop on 1h
  bars, plus the normal ATR stop.
- The sample is trimmed to the funding file's coverage window, because funding
  data ends before the klines do.
"""

from __future__ import annotations
import os, math, json
import numpy as np
import pandas as pd

import sys
sys.path.insert(0, r"C:\Users\Lenovo\Downloads")
from backtest100_engine import Engine, load_klines, rsi, atr, ema

DATA_DIR = r"C:\Users\Lenovo\Documents\backtest-system\data"
FUND_DIR = os.path.join(DATA_DIR, "binance_funding")
OUT_DIR = r"C:\Users\Lenovo\Downloads\backtest100_results"
os.makedirs(OUT_DIR, exist_ok=True)


def load_funding(symbol):
    path = os.path.join(FUND_DIR, symbol + "_funding.json")
    with open(path) as f:
        data = json.load(f)
    rows = [{"t": int(x["t"]), "r": float(x["r"])} for x in data if "t" in x and "r" in x]
    df = pd.DataFrame(rows).sort_values("t").drop_duplicates("t").reset_index(drop=True)
    return df


class FundingCtx:
    def __init__(self, symbol, tf="1h"):
        df = load_klines(symbol, tf)
        fund = load_funding(symbol)
        # trim to funding coverage
        start_ms = int(fund["t"].iloc[0])
        end_ms = int(fund["t"].iloc[-1])
        df = df[(df["open_ts"] >= start_ms) & (df["open_ts"] <= end_ms)].reset_index(drop=True)
        self.df = df
        self.n = len(df)

        # merge_asof: most recent settlement at or before each bar open
        left = df[["open_ts"]].copy()
        right = fund.rename(columns={"t": "open_ts", "r": "fund"})
        merged = pd.merge_asof(left.sort_values("open_ts"), right.sort_values("open_ts"),
                               on="open_ts", direction="backward")
        self.fund_last = merged["fund"].values
        # settlement exactly at this bar's open
        settle_ts = set(fund["t"].values)
        self.is_settle = np.array([t in settle_ts for t in df["open_ts"].values])

        # settlement-level series
        f = fund.copy()
        f["mean30"] = f["r"].rolling(30).mean()
        f["sd30"] = f["r"].rolling(30).std()
        f["z30"] = (f["r"] - f["mean30"]) / f["sd30"]
        f["median30"] = f["r"].rolling(30).median()
        f["max30"] = f["r"].rolling(30).max()
        neg = (f["r"] < 0).astype(int)
        pos3 = (f["r"] > 0.0003).astype(int)
        # consecutive counts ending at each settlement
        def consec(arr):
            out = np.zeros(len(arr), dtype=int)
            c = 0
            for i, v in enumerate(arr):
                c = c + 1 if v else 0
                out[i] = c
            return out
        f["consec_neg"] = consec(neg.values)
        f["consec_pos3"] = consec(pos3.values)
        f["prev_r"] = f["r"].shift(1)

        # map settlement metrics back to bars
        cols = ["z30", "median30", "max30", "consec_neg", "consec_pos3", "prev_r"]
        m2 = pd.merge_asof(left.sort_values("open_ts"),
                           f[["t"] + cols].rename(columns={"t": "open_ts"}).sort_values("open_ts"),
                           on="open_ts", direction="backward")
        for c in cols:
            setattr(self, "fund_" + c, m2[c].values)

        self.close = df["close"].values
        self.high = df["high"].values
        self.low = df["low"].values
        self.open = df["open"].values
        self.ts = df["timestamp"].values
        self.atr14 = atr(df, 14).values
        self.ema200 = ema(df["close"], 200).values
        self.rsi14 = rsi(df["close"], 14).values
        self.ret24 = df["close"].pct_change(24).values
        self.hi48 = df["high"].rolling(48).max().shift(1).values
        self.lo48 = df["low"].rolling(48).min().shift(1).values

        # higher timeframe RSI mapped onto this timeframe
        self.rsi_htf = self._htf_rsi(df, "4h" if tf == "1h" else "1h", 14) if tf == "1h" else self._htf_rsi(df, "1h", 14)

    def _htf_rsi(self, df, rule, period):
        s = df.set_index("timestamp")["close"].resample(rule).last().dropna()
        r = rsi(s, period)
        r.index = r.index + pd.to_timedelta(rule)
        right = pd.DataFrame({"ts": r.index, "val": r.values}).sort_values("ts")
        left = df[["timestamp"]].sort_values("timestamp")
        left["timestamp"] = left["timestamp"].astype("datetime64[ns, UTC]")
        right["ts"] = right["ts"].astype("datetime64[ns, UTC]")
        out = pd.merge_asof(left, right, left_on="timestamp", right_on="ts", direction="backward")
        return out["val"].values


def run(name, symbol, tf, signal_fn, ctx):
    engine = Engine(ctx.df)
    n = len(ctx.df)
    split = int(n * 0.7)
    m_is = engine.run(signal_fn, 0, split - 1)
    engine2 = Engine(ctx.df)
    m_oos = engine2.run(signal_fn, split, n - 1)
    bh = (ctx.close[-1] / ctx.close[0] - 1) * 100
    return dict(strategy=name, symbol=symbol, tf=tf,
                is_return_pct=round(m_is["total_return_pct"], 2),
                is_max_dd_pct=round(m_is["max_dd_pct"], 2),
                is_pf=None if m_is["profit_factor"] is None else round(m_is["profit_factor"], 3),
                is_trades=m_is["n_trades"], is_win_rate=round(m_is["win_rate"], 1),
                is_sharpe=round(m_is["sharpe"], 3), bh_return_pct=round(bh, 2),
                oos_return_pct=round(m_oos["total_return_pct"], 2),
                oos_max_dd_pct=round(m_oos["max_dd_pct"], 2),
                oos_pf=None if m_oos["profit_factor"] is None else round(m_oos["profit_factor"], 3),
                oos_trades=m_oos["n_trades"], oos_win_rate=round(m_oos["win_rate"], 1),
                oos_sharpe=round(m_oos["sharpe"], 3))


# ---------------------------- 91 funding extreme fade ----------------------------
def make_91(ctx):
    def sig(j, _):
        f = ctx.fund_last[j]
        atr_v = ctx.atr14[j]
        if not np.isfinite(f) or not np.isfinite(atr_v):
            return None
        if ctx.is_settle[j]:
            if f > 0.0005:
                return {"side": -1, "stop_px": ctx.close[j] + 2 * atr_v, "max_hold": 8}
            if f < -0.0002:
                return {"side": 1, "stop_px": ctx.close[j] - 2 * atr_v, "max_hold": 8}
            return {"side": 0, "stop_px": 0}
        return None
    return sig


# ---------------------------- 92 funding z-score ----------------------------
def make_92(ctx):
    def sig(j, _):
        if not ctx.is_settle[j]:
            return None
        z = ctx.fund_z30[j]
        atr_v = ctx.atr14[j]
        if not np.isfinite(z) or not np.isfinite(atr_v):
            return None
        if z > 2:
            return {"side": -1, "stop_px": ctx.close[j] + 2 * atr_v}
        if z < 0:
            return {"side": 0, "stop_px": 0}
        return None
    return sig


# ---------------------------- 93 negative-funding long ----------------------------
def make_93(ctx):
    def sig(j, _):
        if not ctx.is_settle[j]:
            return None
        cn = ctx.fund_consec_neg[j]
        f = ctx.fund_last[j]
        atr_v = ctx.atr14[j]
        if not np.isfinite(cn) or not np.isfinite(atr_v):
            return None
        if cn >= 3:
            return {"side": 1, "stop_px": ctx.close[j] - 2 * atr_v}
        if np.isfinite(f) and f > 0.0001:
            return {"side": 0, "stop_px": 0}
        return None
    return sig


# ---------------------------- 94 funding persistence ----------------------------
def make_94(ctx):
    def sig(j, _):
        if not ctx.is_settle[j]:
            return None
        cp = ctx.fund_consec_pos3[j]
        atr_v = ctx.atr14[j]
        if not np.isfinite(cp) or not np.isfinite(atr_v):
            return None
        if cp >= 3:
            return {"side": -1, "stop_px": ctx.close[j] + 1.5 * atr_v, "max_hold": 8}
        return None
    return sig


# ---------------------------- 95 price-funding divergence ----------------------------
def make_95(ctx):
    def sig(j, _):
        atr_v = ctx.atr14[j]
        if not np.isfinite(atr_v) or not np.isfinite(ctx.lo48[j]):
            return None
        if ctx.low[j] <= ctx.lo48[j] and np.isfinite(ctx.fund_max30[j]):
            f = ctx.fund_last[j]
            if np.isfinite(f) and f >= ctx.fund_max30[j]:
                return {"side": -1, "stop_px": ctx.close[j] + 2 * atr_v, "max_hold": 24}
        return None
    return sig


# ---------------------------- 96 funding with trend filter ----------------------------
def make_96(ctx):
    def sig(j, _):
        f = ctx.fund_last[j]
        atr_v = ctx.atr14[j]
        if not np.isfinite(f) or not np.isfinite(atr_v) or not np.isfinite(ctx.ema200[j]):
            return None
        if ctx.close[j] > ctx.ema200[j] and f > 0.0004:
            return {"side": -1, "stop_px": ctx.close[j] + 2 * atr_v}
        if f < 0.0001:
            return {"side": 0, "stop_px": 0}
        return None
    return sig


# ---------------------------- 97 funding-filtered reversion ----------------------------
def make_97(ctx):
    def sig(j, _):
        f = ctx.fund_last[j]
        r = ctx.rsi14[j]
        atr_v = ctx.atr14[j]
        if not np.isfinite(f) or not np.isfinite(r) or not np.isfinite(atr_v):
            return None
        if r < 35 and f < 0:
            return {"side": 1, "stop_px": ctx.close[j] - 2 * atr_v}
        if r > 60:
            return {"side": 0, "stop_px": 0}
        return None
    return sig


# ---------------------------- 98 funding vs 4h RSI ----------------------------
def make_98(ctx):
    def sig(j, _):
        r4 = ctx.rsi_htf[j]
        f = ctx.fund_last[j]
        med = ctx.fund_median30[j]
        atr_v = ctx.atr14[j]
        if not np.isfinite(r4) or not np.isfinite(f) or not np.isfinite(atr_v):
            return None
        if r4 > 70 and np.isfinite(med) and f > med:
            return {"side": -1, "stop_px": ctx.close[j] + 2 * atr_v}
        if r4 < 55:
            return {"side": 0, "stop_px": 0}
        return None
    return sig


# ---------------------------- 99 funding momentum ----------------------------
def make_99(ctx):
    def sig(j, _):
        if not ctx.is_settle[j]:
            return None
        f = ctx.fund_last[j]
        prev = ctx.fund_prev_r[j]
        r24 = ctx.ret24[j]
        atr_v = ctx.atr14[j]
        if not np.isfinite(f) or not np.isfinite(prev) or not np.isfinite(r24) or not np.isfinite(atr_v):
            return None
        if prev <= 0.0001 and f > 0.0001 and r24 > 0:
            return {"side": 1, "stop_px": ctx.close[j] - 2 * atr_v}
        if f < 0:
            return {"side": 0, "stop_px": 0}
        return None
    return sig


# ---------------------------- 100 funding harvest (15m) ----------------------------
def make_100(ctx):
    # 15m bars: signal on the :15 bar -> fill at :30, 30 minutes before the 00/08/16 settlement
    pre_settle_hours = {23, 7, 15}
    def sig(j, _):
        ts = pd.Timestamp(ctx.ts[j])
        if not (ts.minute == 15 and ts.hour in pre_settle_hours):
            return None
        r1 = ctx.rsi_htf[j]
        f = ctx.fund_last[j]
        atr_v = ctx.atr14[j]
        if not np.isfinite(r1) or not np.isfinite(atr_v):
            return None
        if r1 > 70 and np.isfinite(f) and f > 0:
            return {"side": -1, "stop_px": ctx.close[j] + 1 * atr_v, "max_hold": 4}
        return None
    return sig


def main():
    specs = [
        ("91", "BTCUSDT", "1h", make_91),
        ("92", "ETHUSDT", "1h", make_92),
        ("93", "SOLUSDT", "1h", make_93),
        ("94", "HYPEUSDT", "1h", make_94),
        ("95", "SUIUSDT", "1h", make_95),
        ("96", "JUPUSDT", "1h", make_96),
        ("97", "BTCUSDT", "1h", make_97),
        ("98", "ETHUSDT", "1h", make_98),
        ("99", "SOLUSDT", "1h", make_99),
        ("100", "HYPEUSDT", "15m", make_100),
    ]
    rows = []
    for name, symbol, tf, maker in specs:
        print("Strategy %s (%s %s)..." % (name, symbol, tf), end=" ", flush=True)
        try:
            ctx = FundingCtx(symbol, tf)
            sig = maker(ctx)
            r = run(name, symbol, tf, sig, ctx)
            rows.append(r)
            print("OK  IS %.2f%%  OOS %.2f%%  PF %s  trades %d" % (
                r["is_return_pct"], r["oos_return_pct"], r["oos_pf"], r["oos_trades"]), flush=True)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("ERROR:", str(e)[:200], flush=True)
    df = pd.DataFrame(rows)
    out = os.path.join(OUT_DIR, "results_funding_91_100.csv")
    df.to_csv(out, index=False)
    print("\nSaved", out)
    if len(df):
        print(df.to_string(index=False))


if __name__ == "__main__":
    main()
