"""
htf_ltf_fvg.py -- 4H FVG -> 15M tap -> new 15M FVG entry

Rules
  1. Latest confirmed 4H FVG = active zone (bullish -> long, bearish -> short).
     A newer 4H FVG replaces it.
  2. Wait for a 15M bar to trade into the zone (touch).
  3. After the touch bar, wait for a NEW 15M FVG in the trade direction to complete.
  4. Enter on it:
       limit  : resting order at entry_frac across the 15M FVG (0 = proximal edge,
                0.5 = CE/midpoint, 1 = distal edge), alive for limit_expiry bars
       market : next 15M open after the FVG-completing bar
     SL = extreme of the 3 candles that built the 15M FVG (+ buffer), TP = rr * risk.
  One trade per 4H zone. Zone is killed by a 15M close through it, or by max_zone_age.

Engines (same rules, same fills -> trades must match 1:1; `--engine both` checks it)
  vector : numpy/pandas signal generation, per-trade array scan for fills/exits
  event  : bar-by-bar loop, incremental 15M->4H aggregator, Strategy/Broker objects

No-lookahead conventions
  * A 4H FVG is known only at 4H close -> usable from the first 15M bar after it.
  * FVG on bar i uses candles i-2..i, signal acts at close of i (fills from i+1).
  * SL and TP both inside one bar -> SL first. On a limit-fill bar TP is ignored.
  * Gaps: stops fill at min(open, SL) (long), targets at max(open, TP).
  * Fees: maker on limit entry/TP, taker otherwise. Slippage on market-type fills only.
  * Sizing: risk_pct of current equity per trade, capped by max_leverage. One position at a time.

Usage
  python htf_ltf_fvg.py --symbol SOLUSDT --days 180
  python htf_ltf_fvg.py --csv sol_15m.csv --entry-mode market --rr 3
  python htf_ltf_fvg.py --synthetic
"""
from __future__ import annotations

import argparse
from collections import deque, namedtuple
from dataclasses import dataclass, fields
from typing import Optional

import numpy as np
import pandas as pd

Bar = namedtuple("Bar", "ts o h l c i")  # ts = epoch ns of bar open


# --------------------------------------------------------------------------- params
@dataclass
class Params:
    htf: str = "4h"
    ltf: str = "15min"
    entry_mode: str = "limit"        # limit | market
    entry_frac: float = 0.5          # limit: 0 proximal edge .. 1 distal edge of 15M FVG
    limit_expiry: int = 8            # bars the limit order stays alive
    rr: float = 2.0
    sl_buffer_bps: float = 0.0
    min_htf_gap_bps: float = 0.0     # ignore tiny 4H FVGs
    min_ltf_gap_bps: float = 0.0     # ignore tiny 15M FVGs
    max_zone_age: int = 0            # 15M bars since zone confirmed; 0 = off
    max_hold: int = 96               # 15M bars (96 = 24h)
    risk_pct: float = 0.01
    max_leverage: float = 5.0
    fee_taker_bps: float = 5.0
    fee_maker_bps: float = 2.0
    slippage_bps: float = 1.0
    init_equity: float = 10_000.0


@dataclass
class Order:
    side: int
    sl: float
    level: Optional[float]   # limit price; None = market
    tp: Optional[float]      # planned TP for limit orders; market TP is set at fill


# --------------------------------------------------------------------------- shared logic
def fvg3(b0, b1, b2, min_gap_bps):
    """Scalar FVG test on 3 consecutive bars -> (dir, top, bot, sl_ref) | None."""
    if b2.l > b0.h and (b2.l - b0.h) / b1.c * 1e4 >= min_gap_bps:
        return 1, b2.l, b0.h, min(b0.l, b1.l, b2.l)
    if b2.h < b0.l and (b0.l - b2.h) / b1.c * 1e4 >= min_gap_bps:
        return -1, b0.l, b2.h, max(b0.h, b1.h, b2.h)
    return None


def detect_fvg(df: pd.DataFrame, min_gap_bps: float = 0.0) -> pd.DataFrame:
    """Vectorized FVG detection. Row i = FVG completed by candle i (uses i-2, i-1, i)."""
    n = len(df)
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    d = np.zeros(n, np.int8)
    top, bot, slr = (np.full(n, np.nan) for _ in range(3))
    if n >= 3:
        h0, l0 = h[:-2], l[:-2]
        h1, l1, c1 = h[1:-1], l[1:-1], c[1:-1]
        h2, l2 = h[2:], l[2:]
        bull = (l2 > h0) & ((l2 - h0) / c1 * 1e4 >= min_gap_bps)
        bear = (h2 < l0) & ((l0 - h2) / c1 * 1e4 >= min_gap_bps)
        d[2:] = np.where(bull, 1, np.where(bear, -1, 0))
        top[2:] = np.where(bull, l2, np.where(bear, l0, np.nan))
        bot[2:] = np.where(bull, h0, np.where(bear, h2, np.nan))
        slr[2:] = np.where(bull, np.minimum(np.minimum(l0, l1), l2),
                           np.where(bear, np.maximum(np.maximum(h0, h1), h2), np.nan))
    return pd.DataFrame({"dir": d, "top": top, "bot": bot, "sl_ref": slr}, index=df.index)


def make_order(side, top, bot, sl_ref, p: Params) -> Order:
    buf = p.sl_buffer_bps / 1e4
    sl = sl_ref * (1 - buf) if side > 0 else sl_ref * (1 + buf)
    if p.entry_mode == "limit":
        prox, dist = (top, bot) if side > 0 else (bot, top)
        level = prox + p.entry_frac * (dist - prox)
        tp = level + side * p.rr * abs(level - sl)
        return Order(side, sl, level, tp)
    return Order(side, sl, None, None)


def bar_exit(side, o, h, l, sl, tp, check_tp):
    """SL before TP inside a bar. Returns (raw_px, reason) or None."""
    if side > 0:
        if l <= sl:
            return min(o, sl), "sl"
        if check_tp and h >= tp:
            return max(o, tp), "tp"
    else:
        if h >= sl:
            return max(o, sl), "sl"
        if check_tp and l <= tp:
            return min(o, tp), "tp"
    return None


def settle(side, entry, fee_in, px, reason, sl, equity, p: Params) -> dict:
    """Apply exit slippage/fees, size by risk, return PnL fields."""
    if reason == "tp":
        exit_px, fee_out = px, p.fee_maker_bps
    else:
        exit_px, fee_out = px * (1 - side * p.slippage_bps / 1e4), p.fee_taker_bps
    risk_u = abs(entry - sl)
    qty = min(equity * p.risk_pct / risk_u, equity * p.max_leverage / entry)
    fees = qty * (entry * fee_in + exit_px * fee_out) / 1e4
    pnl = side * (exit_px - entry) * qty - fees
    return dict(exit=exit_px, qty=qty, fees=fees, pnl=pnl, r=pnl / (qty * risk_u))


TRADE_COLS = ["side", "signal_time", "entry_time", "exit_time", "entry", "exit", "sl", "tp",
              "reason", "qty", "fees", "pnl", "r", "equity", "bars"]


def make_htf(ltf: pd.DataFrame, p: Params) -> pd.DataFrame:
    ratio = int(pd.Timedelta(p.htf) / pd.Timedelta(p.ltf))
    htf = ltf.resample(p.htf, label="left", closed="left").agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"), n=("close", "size"))
    return htf[htf["n"] == ratio].drop(columns="n")  # only complete buckets


# =========================================================================== FRAMEWORK 1: VECTOR
def vector_signals(ltf: pd.DataFrame, p: Params) -> pd.DataFrame:
    """All entry signals, fully vectorized. One row per 4H zone (first qualifying 15M FVG)."""
    empty = pd.DataFrame(columns=["i", "side", "top", "bot", "sl_ref"])
    hf = detect_fvg(make_htf(ltf, p), p.min_htf_gap_bps)
    hf = hf[hf["dir"] != 0]
    if hf.empty:
        return empty

    # latest 4H FVG whose close time <= each 15M bar open
    avail = (hf.index + pd.Timedelta(p.htf)).to_numpy("datetime64[ns]")
    zid = np.searchsorted(avail, ltf.index.to_numpy("datetime64[ns]"), side="right") - 1
    ok = zid >= 0
    zc = np.where(ok, zid, 0)
    zdir = np.where(ok, hf["dir"].to_numpy()[zc], 0)
    ztop, zbot = hf["top"].to_numpy()[zc], hf["bot"].to_numpy()[zc]

    hi, lo, cl = (ltf[k].to_numpy(float) for k in ("high", "low", "close"))
    touch = ok & (lo <= ztop) & (hi >= zbot)
    inval = ok & np.where(zdir > 0, cl < zbot, cl > ztop)

    df = pd.DataFrame({"z": zid, "touch": touch.astype(int), "inval": inval.astype(int)})
    g = df.groupby("z")
    touched_before = ((g["touch"].cumsum() - df["touch"]) > 0).to_numpy()  # strictly earlier bar
    dead = (g["inval"].cumsum() > 0).to_numpy()                            # inclusive of this bar
    age = g.cumcount().to_numpy()
    age_ok = np.ones(len(df), bool) if p.max_zone_age <= 0 else age < p.max_zone_age

    lf = detect_fvg(ltf, p.min_ltf_gap_bps)
    cand = ok & touched_before & ~dead & age_ok & (lf["dir"].to_numpy() == zdir)
    first = cand & (pd.Series(cand.astype(int)).groupby(df["z"]).cumsum().to_numpy() == 1)

    idx = np.flatnonzero(first)
    return pd.DataFrame({"i": idx, "side": zdir[idx], "top": lf["top"].to_numpy()[idx],
                         "bot": lf["bot"].to_numpy()[idx], "sl_ref": lf["sl_ref"].to_numpy()[idx]})


def vector_backtest(ltf: pd.DataFrame, p: Params) -> pd.DataFrame:
    sig = vector_signals(ltf, p)
    o, h, l, c = (ltf[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    n, ts = len(ltf), ltf.index
    equity, busy_until, rows = p.init_equity, -1, []

    for s, side, top, bot, slref in sig.itertuples(index=False):
        if s < busy_until:                     # broker still occupied
            continue
        side = int(side)
        od = make_order(side, top, bot, slref, p)

        if od.level is None:                   # ---- market: next open
            f = s + 1
            if f >= n:
                continue
            entry = o[f] * (1 + side * p.slippage_bps / 1e4)
            if (side > 0 and entry <= od.sl) or (side < 0 and entry >= od.sl):
                continue                       # gapped through the stop
            tp, fee_in, tp_first = entry + side * p.rr * abs(entry - od.sl), p.fee_taker_bps, True
        else:                                  # ---- limit: first fill/miss inside the expiry window
            w0, w1 = s + 1, min(s + 1 + p.limit_expiry, n)
            if w0 >= w1:
                continue
            lo_w, hi_w = l[w0:w1], h[w0:w1]
            if side > 0:
                fill, miss = lo_w <= od.level, hi_w >= od.tp
            else:
                fill, miss = hi_w >= od.level, lo_w <= od.tp
            ev = fill | miss
            if not ev.any():
                busy_until = w1 - 1            # expired unfilled
                continue
            k = int(ev.argmax())
            if not fill[k]:
                busy_until = w0 + k            # TP reached before fill -> cancelled
                continue
            f = w0 + k
            entry = min(o[f], od.level) if side > 0 else max(o[f], od.level)
            tp, fee_in, tp_first = od.tp, p.fee_maker_bps, False

        # ---- exit scan (vectorized over the holding window)
        last_allowed = f + p.max_hold - 1
        last = min(last_allowed, n - 1)
        lo_w, hi_w = l[f:last + 1], h[f:last + 1]
        if side > 0:
            sl_hit, tp_hit = lo_w <= od.sl, hi_w >= tp
        else:
            sl_hit, tp_hit = hi_w >= od.sl, lo_w <= tp
        if not tp_first:
            tp_hit[0] = False
        ev = sl_hit | tp_hit
        if ev.any():
            j = f + int(ev.argmax())
            px, reason = bar_exit(side, o[j], h[j], l[j], od.sl, tp, tp_first or j > f)
        else:
            j, px = last, c[last]
            reason = "time" if last_allowed <= n - 1 else "eod"

        res = settle(side, entry, fee_in, px, reason, od.sl, equity, p)
        equity += res["pnl"]
        busy_until = j
        rows.append(dict(side=side, signal_time=ts[s], entry_time=ts[f], exit_time=ts[j],
                         entry=entry, sl=od.sl, tp=tp, reason=reason, equity=equity,
                         bars=j - f + 1, **res))
    return pd.DataFrame(rows, columns=TRADE_COLS)


# =========================================================================== FRAMEWORK 2: EVENT
class HTFBuilder:
    """Incremental LTF -> HTF aggregator. Emits a bar only when its last LTF bar has closed."""

    def __init__(self, p: Params):
        self.h = pd.Timedelta(p.htf).value
        self.l = pd.Timedelta(p.ltf).value
        self.ratio = self.h // self.l
        self.bucket, self.buf = None, []

    def push(self, bar: Bar) -> Optional[Bar]:
        b = bar.ts // self.h
        if b != self.bucket:
            self.bucket, self.buf = b, []
        self.buf.append(bar)
        if len(self.buf) == self.ratio and bar.ts + self.l == (b + 1) * self.h:
            bs = self.buf
            return Bar(b * self.h, bs[0].o, max(x.h for x in bs), min(x.l for x in bs), bs[-1].c, -1)
        return None


class FvgStrategy:
    """State machine: ARMED (zone set) -> DONE (signal emitted) | DEAD (invalidated / expired)."""

    def __init__(self, p: Params):
        self.p = p
        self.hh, self.lh = deque(maxlen=3), deque(maxlen=3)
        self.zone, self.state, self.touched, self.age = None, "NONE", False, 0

    def on_htf_bar(self, hb: Bar):
        self.hh.append(hb)
        if len(self.hh) == 3:
            f = fvg3(*self.hh, self.p.min_htf_gap_bps)
            if f:
                self.zone = dict(dir=f[0], top=f[1], bot=f[2])
                self.state, self.touched, self.age = "ARMED", False, 0

    def on_bar(self, bar: Bar) -> Optional[Order]:
        p = self.p
        self.lh.append(bar)
        if self.state != "ARMED":
            return None
        z = self.zone
        age, self.age = self.age, self.age + 1
        if p.max_zone_age > 0 and age >= p.max_zone_age:
            self.state = "DEAD"
            return None
        if (z["dir"] > 0 and bar.c < z["bot"]) or (z["dir"] < 0 and bar.c > z["top"]):
            self.state = "DEAD"
            return None
        order = None
        if self.touched and len(self.lh) == 3:          # touch must be on an EARLIER bar
            f = fvg3(*self.lh, p.min_ltf_gap_bps)
            if f and f[0] == z["dir"]:
                order = make_order(f[0], f[1], f[2], f[3], p)
                self.state = "DONE"
        if bar.l <= z["top"] and bar.h >= z["bot"]:
            self.touched = True
        return order


class Broker:
    """Holds one pending order or one position; processes each bar before the strategy sees it."""

    def __init__(self, p: Params):
        self.p, self.equity = p, p.init_equity
        self.pending, self.pos, self.trades = None, None, []

    @property
    def busy(self) -> bool:
        return self.pending is not None or self.pos is not None

    def submit(self, order: Order, bar: Bar):
        self.pending = (order, bar.i, bar.ts)

    def _open(self, od, entry, fee_in, tp, bar, sig_ts):
        self.pos = dict(side=od.side, entry=entry, sl=od.sl, tp=tp, fee_in=fee_in,
                        bars=0, entry_ts=bar.ts, sig_ts=sig_ts)

    def _close(self, bar, px, reason):
        ps = self.pos
        res = settle(ps["side"], ps["entry"], ps["fee_in"], px, reason, ps["sl"], self.equity, self.p)
        self.equity += res["pnl"]
        self.trades.append(dict(
            side=ps["side"], signal_time=pd.Timestamp(ps["sig_ts"]), entry_time=pd.Timestamp(ps["entry_ts"]),
            exit_time=pd.Timestamp(bar.ts), entry=ps["entry"], sl=ps["sl"], tp=ps["tp"], reason=reason,
            equity=self.equity, bars=ps["bars"], **res))
        self.pos = None

    def on_bar(self, bar: Bar, is_last: bool):
        p, check_tp = self.p, True
        if self.pending is not None:
            od, sig_i, sig_ts = self.pending
            if od.level is None:                                   # market: fill at this open
                self.pending = None
                entry = bar.o * (1 + od.side * p.slippage_bps / 1e4)
                if not ((od.side > 0 and entry <= od.sl) or (od.side < 0 and entry >= od.sl)):
                    tp = entry + od.side * p.rr * abs(entry - od.sl)
                    self._open(od, entry, p.fee_taker_bps, tp, bar, sig_ts)
            else:                                                  # limit
                if od.side > 0:
                    fill, miss = bar.l <= od.level, bar.h >= od.tp
                else:
                    fill, miss = bar.h >= od.level, bar.l <= od.tp
                if fill:
                    entry = min(bar.o, od.level) if od.side > 0 else max(bar.o, od.level)
                    self.pending, check_tp = None, False
                    self._open(od, entry, p.fee_maker_bps, od.tp, bar, sig_ts)
                elif miss or bar.i - sig_i >= p.limit_expiry:
                    self.pending = None
        if self.pos is not None:
            ps = self.pos
            ps["bars"] += 1
            hit = bar_exit(ps["side"], bar.o, bar.h, bar.l, ps["sl"], ps["tp"], check_tp)
            if hit:
                self._close(bar, *hit)
            elif ps["bars"] >= p.max_hold:
                self._close(bar, bar.c, "time")
            elif is_last:
                self._close(bar, bar.c, "eod")


def event_backtest(ltf: pd.DataFrame, p: Params) -> pd.DataFrame:
    ts = ltf.index.values.astype("datetime64[ns]").astype("int64").tolist()
    o, h, l, c = (ltf[k].to_numpy(float).tolist() for k in ("open", "high", "low", "close"))
    n = len(ltf)
    htfb, strat, broker = HTFBuilder(p), FvgStrategy(p), Broker(p)
    for i in range(n):
        bar = Bar(ts[i], o[i], h[i], l[i], c[i], i)
        broker.on_bar(bar, i == n - 1)          # 1. fills / exits on this bar
        hb = htfb.push(bar)                     # 2. 4H bar may complete on this bar
        order = strat.on_bar(bar)               # 3. 15M logic with zone as of this bar
        if hb is not None:
            strat.on_htf_bar(hb)                # 4. new zone applies from NEXT 15M bar
        if order is not None and not broker.busy:
            broker.submit(order, bar)
    return pd.DataFrame(broker.trades, columns=TRADE_COLS)


# --------------------------------------------------------------------------- stats / checks
def stats(tr: pd.DataFrame, p: Params) -> dict:
    if tr.empty:
        return {"trades": 0}
    eq = np.r_[p.init_equity, tr["equity"].to_numpy()]
    dd = (eq / np.maximum.accumulate(eq) - 1).min()
    w, lz = tr.loc[tr.pnl > 0, "pnl"].sum(), -tr.loc[tr.pnl <= 0, "pnl"].sum()
    return {"trades": len(tr), "long": int((tr.side > 0).sum()), "short": int((tr.side < 0).sum()),
            "win_rate_%": round(float(100 * (tr.pnl > 0).mean()), 1), "avg_R": round(float(tr.r.mean()), 3),
            "profit_factor": round(float(w / lz), 2) if lz > 0 else float("inf"),
            "return_%": round(float(100 * (eq[-1] / eq[0] - 1)), 2), "max_dd_%": round(float(100 * dd), 2),
            "exits": {k: int(v) for k, v in tr.reason.value_counts().items()}}


def compare(tv: pd.DataFrame, te: pd.DataFrame) -> bool:
    if len(tv) != len(te):
        print(f"PARITY FAIL: trade count vector={len(tv)} event={len(te)}")
        return False
    if tv.empty:
        print("PARITY: both empty")
        return True
    keys = ["side", "signal_time", "entry_time", "exit_time", "reason"]
    same = (tv[keys].reset_index(drop=True) == te[keys].reset_index(drop=True)).all().all()
    num = np.allclose(tv[["entry", "exit", "pnl"]].to_numpy(), te[["entry", "exit", "pnl"]].to_numpy(),
                      rtol=1e-9, atol=1e-9)
    print(f"PARITY {'OK' if same and num else 'FAIL'}: {len(tv)} trades, keys_match={same}, numbers_match={num}")
    return bool(same and num)


# --------------------------------------------------------------------------- data
def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [x.lower() for x in df.columns]
    tcol = next(x for x in ("timestamp", "open_time", "time", "date", "datetime") if x in df.columns)
    t = df[tcol]
    if pd.api.types.is_numeric_dtype(t):
        t = pd.to_datetime(t, unit="ms" if t.iloc[0] > 1e11 else "s", utc=True)
    else:
        t = pd.to_datetime(t, utc=True)
    df.index = pd.DatetimeIndex(t.dt.tz_convert(None))
    df = df[["open", "high", "low", "close"]].astype(float).sort_index()
    return df[~df.index.duplicated()]


def fetch_binance(symbol: str, days: int) -> pd.DataFrame:
    """Binance USDT-M futures 15m klines (public endpoint). Needs `requests`."""
    import time
    import requests
    now = int(time.time() * 1000)
    t, rows = now - days * 86_400_000, []
    while t < now:
        r = requests.get("https://fapi.binance.com/fapi/v1/klines", timeout=20,
                         params=dict(symbol=symbol, interval="15m", startTime=t, limit=1500))
        r.raise_for_status()
        k = r.json()
        if not k:
            break
        rows += [x[:7] for x in k]
        t = k[-1][0] + 900_000
        if len(k) < 1500:
            break
    df = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close", "v", "close_t"])
    df = df[df["close_t"] < now]                            # closed candles only
    df.index = pd.to_datetime(df["t"], unit="ms")
    return df[["open", "high", "low", "close"]].astype(float)[lambda d: ~d.index.duplicated()]


def synthetic(days: int = 120, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = days * 96
    vol = np.clip(0.0025 * np.exp(np.cumsum(rng.normal(0, 0.03, n))), 0.001, 0.006)
    ret = np.sin(np.arange(n) / 700) * 0.0002 + vol * rng.standard_t(4, n) / np.sqrt(2)
    c = 100 * np.exp(np.cumsum(ret))
    o = np.r_[100.0, c[:-1]]
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.0012, n)))
    l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.0012, n)))
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c},
                        index=pd.date_range("2026-01-01", periods=n, freq="15min"))


# --------------------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv")
    ap.add_argument("--symbol")
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--engine", choices=["vector", "event", "both"], default="both")
    ap.add_argument("--out", help="write trades CSV (vector engine, or event if --engine event)")
    for f in fields(Params):
        ap.add_argument("--" + f.name.replace("_", "-"), dest=f.name, type=type(f.default), default=f.default)
    a = ap.parse_args()
    p = Params(**{f.name: getattr(a, f.name) for f in fields(Params)})

    if a.csv:
        ltf = load_csv(a.csv)
    elif a.symbol:
        ltf = fetch_binance(a.symbol, a.days)
    else:
        ltf = synthetic()
        print("(no data source given -> synthetic data)")
    print(f"{len(ltf)} bars  {ltf.index[0]} -> {ltf.index[-1]}")

    tv = te = None
    if a.engine in ("vector", "both"):
        tv = vector_backtest(ltf, p)
        print("VECTOR", stats(tv, p))
    if a.engine in ("event", "both"):
        te = event_backtest(ltf, p)
        print("EVENT ", stats(te, p))
    if a.engine == "both":
        compare(tv, te)
    if a.out:
        (tv if tv is not None else te).to_csv(a.out, index=False)


if __name__ == "__main__":
    main()
