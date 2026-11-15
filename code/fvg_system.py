"""
fvg_system.py — ICT 4H FVG -> 15M FVG entry system.
Framework 1 (vector research) + Framework 2 (event-driven production).
Python 3.10+, numpy, pandas.  Optional: ccxt (download), matplotlib (plots).

DESIGN RULE #1: a bar stamped T covers [T, T+Δ). Its information exists only at T+Δ.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass, replace, asdict
from typing import Optional, List, Dict

# ============================== 0. CONFIG =====================================
@dataclass
class Config:
    htf_rule: str = "4h"
    ltf_rule: str = "15min"
    atr_n: int = 14

    # --- FVG quality filters
    min_htf_fvg_atr: float = 0.25     # 4H gap must be >= 0.25 * ATR(4H)
    min_ltf_fvg_atr: float = 0.15
    htf_max_age_bars: int = 42        # 4H bars (~7 days)
    htf_use_ce: bool = False          # require touch of 50% of the 4H zone instead of edge

    # --- LTF confirmation
    max_wait_bars: int = 16           # 16 * 15m = 4h to print a 15M FVG after the touch
    ltf_max_ext_atr: float = 1.0      # 15M FVG can't be > 1 ATR beyond the 4H proximal edge
    entry_mode: str = "proximal"      # 'proximal' | 'ce'
    order_expiry_bars: int = 8        # limit order life = 2h

    # --- risk / exits
    stop_mode: str = "ltf_fvg"        # 'ltf_fvg' | 'htf_fvg'
    stop_buf_atr: float = 0.25
    min_stop_atr: float = 0.20
    max_stop_atr: float = 3.00
    tp_r: float = 2.0
    min_reward_cost_mult: float = 3.0 # reward must be >= 3x round-trip cost
    risk_pct: float = 0.005           # 0.5% of equity per trade
    max_leverage: float = 3.0
    min_notional: float = 0.0         # set to exchange minimum for live

    # --- trade management (EVENT ENGINE ONLY)
    be_at_r: Optional[float] = 1.0
    partial_at_r: Optional[float] = 1.0
    partial_frac: float = 0.5
    trail_at_r: Optional[float] = 2.0
    trail_atr: float = 2.0
    max_hold_bars: int = 96           # 24h time stop

    # --- costs (Binance-perp-like, conservative)
    fee_maker: float = 0.0002
    fee_taker: float = 0.0005
    slip_bps: float = 1.0             # adverse slippage on stop/market exits
    funding_bps_8h: float = 1.0       # longs pay 0.01% per 8h

    # --- misc / safety
    one_trade_per_htf: bool = True
    cooldown_bars: int = 4
    allow_long: bool = True
    allow_short: bool = True
    gap_fill_better: bool = True      # limit fills at open if the bar gapped through it
    max_daily_loss_pct: float = 0.03  # kill switch: stop new entries for the day
    max_dd_stop_pct: float = 0.20     # kill switch: halt system
    start_equity: float = 10_000.0


TAKER_REASONS = {"stop", "time", "gap_stop", "eod", "kill"}


# ============================== 1. DATA =======================================
def validate_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    df = df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("index must be DatetimeIndex of bar OPEN times")
    df.index = df.index.tz_localize("UTC") if df.index.tz is None else df.index.tz_convert("UTC")
    df = df[~df.index.duplicated(keep="last")].sort_index()
    need = ["open", "high", "low", "close"]
    for c in need:
        if c not in df: raise KeyError(c)
    if "volume" not in df: df["volume"] = 0.0
    o, h, l, c = (df[k].values for k in need)
    assert (h >= np.maximum(o, c) - 1e-9).all(), "high < max(open,close)"
    assert (l <= np.minimum(o, c) + 1e-9).all(), "low > min(open,close)"
    assert (np.asarray([o, h, l, c]) > 0).all(), "non-positive prices"
    step = pd.Timedelta(rule)
    gaps = df.index.to_series().diff().dropna()
    missing = int((gaps > step).sum())
    if missing:
        print(f"[data] WARNING: {missing} gaps > {rule}. FVGs across gaps are dropped.")
    df.attrs["gaps"] = set(gaps[gaps > step].index)
    return df[["open", "high", "low", "close", "volume"]]


def resample_ohlcv(ltf: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Bar OPEN-time labels, left-closed. Incomplete trailing bars are dropped."""
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    h = ltf.resample(rule, label="left", closed="left").agg(agg)
    cnt = ltf["close"].resample(rule, label="left", closed="left").count()
    exp = int(pd.Timedelta(rule) / pd.Timedelta(ltf.index[1] - ltf.index[0]))
    return h[cnt.reindex(h.index).values == exp].dropna()


def atr(df: pd.DataFrame, n: int = 14) -> np.ndarray:
    h, l, c = df.high.values, df.low.values, df.close.values
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return pd.Series(tr).ewm(alpha=1 / n, adjust=False, min_periods=n).mean().values


def synthetic_15m(n=20000, seed=7, px=42000.0, start="2024-01-01") -> pd.DataFrame:
    """DEMO ONLY — vol-clustered GBM with displacement candles. Not a real edge."""
    rng = np.random.default_rng(seed)
    v, vol = 0.004, np.empty(n)
    for i in range(n):
        v = 0.97 * v + 0.03 * abs(rng.normal(0, 0.004)); vol[i] = max(v, 0.0015)
    r = rng.normal(0, 1, n) * vol
    r += (rng.random(n) < 0.012) * rng.normal(0, 1, n) * vol * 4.0
    c = px * np.exp(np.cumsum(r)); o = np.r_[px, c[:-1]]
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, .5, n)) * vol)
    l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, .5, n)) * vol)
    idx = pd.date_range(start, periods=n, freq="15min", tz="UTC")
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c,
                         "volume": rng.uniform(10, 500, n)}, index=idx)


def download_binance(symbol="BTC/USDT:USDT", timeframe="15m", days=400) -> pd.DataFrame:
    import ccxt  # pip install ccxt
    ex = ccxt.binanceusdm({"enableRateLimit": True})
    since = ex.milliseconds() - days * 86400_000
    rows = []
    while True:
        b = ex.fetch_ohlcv(symbol, timeframe, since=since, limit=1500)
        if not b: break
        rows += b; since = b[-1][0] + 1
        if len(b) < 1500: break
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df.index = pd.to_datetime(df.ts, unit="ms", utc=True)
    return df.drop(columns="ts")


# ============================== 2. FVG + FAST LOOKUPS =========================
def find_fvgs(df: pd.DataFrame, atr_arr: np.ndarray, min_atr_mult: float) -> Dict:
    """3-candle imbalance. Confirmed at the CLOSE of bar i (the 3rd candle)."""
    o, h, l, c = (df[k].values for k in ("open", "high", "low", "close"))
    n = len(df)
    h2 = np.full(n, np.nan); h2[2:] = h[:-2]
    l2 = np.full(n, np.nan); l2[2:] = l[:-2]
    bull = np.zeros(n, bool); bear = np.zeros(n, bool)
    bull[2:] = l[2:] > h[:-2]
    bear[2:] = h[2:] < l[:-2]
    lo = np.where(bull, h2, h)          # distal for bull, proximal for bear
    hi = np.where(bull, l, l2)          # proximal for bull, distal for bear
    ok = (bull | bear) & np.isfinite(atr_arr) & ((hi - lo) >= min_atr_mult * atr_arr)
    # never allow an FVG that straddles a data gap
    gaps = df.attrs.get("gaps", set())
    if gaps:
        gidx = df.index.get_indexer(sorted(gaps))
        for g in gidx[gidx >= 0]:
            ok[max(0, g - 2):g + 1] = False
    idx = np.flatnonzero(ok)
    return dict(idx=idx, dir=np.where(bull[idx], 1, -1),
                lo=lo[idx], hi=hi[idx], ce=(lo[idx] + hi[idx]) / 2)


class RangeExtreme:
    """Sparse table. first_cross(s, x) = first i>=s with a[i]<=x (min) / >=x (max).
    O(n log n) build, O(log n) query. This is what makes the vector engine fast."""
    def __init__(self, a, mode="min"):
        self.a = np.asarray(a, float); self.n = len(self.a); self.mode = mode
        self.tab = [self.a]; k = 1
        op = np.minimum if mode == "min" else np.maximum
        while (1 << k) <= self.n:
            p = self.tab[-1]; half = 1 << (k - 1); m = len(p) - half
            self.tab.append(op(p[:m], p[half:half + m])); k += 1

    def first_cross(self, s: int, x: float) -> int:
        n = self.n
        if s >= n: return n
        i = s
        for k in range(len(self.tab) - 1, -1, -1):
            step = 1 << k
            if i + step <= n:
                v = self.tab[k][i]
                if (v > x) if self.mode == "min" else (v < x):
                    i += step
        return i if i < n else n


# ============================== 3. POINT-IN-TIME HTF MAP ======================
def htf_active_map(htf, HF, ltf_index, cfg) -> np.ndarray:
    """For each 15M bar: id of the most recent VALID 4H FVG knowable at that bar's OPEN.
    This function is where look-ahead bias goes to die."""
    N = len(htf)
    rm_lo = RangeExtreme(htf.low.values, "min")
    rm_hi = RangeExtreme(htf.high.values, "max")
    created, dirs, los, his = HF["idx"], HF["dir"], HF["lo"], HF["hi"]
    # a bull FVG dies when a later 4H low fully fills it; bear when a high fills it
    fill = np.array([rm_lo.first_cross(k + 1, los[j]) if dirs[j] > 0
                     else rm_hi.first_cross(k + 1, his[j])
                     for j, k in enumerate(created)], dtype=int) if len(created) else np.array([], int)
    close = htf.close.values
    active = np.full(N, -1, int); alive: List[int] = []; p = 0
    for b in range(N):
        while p < len(created) and created[p] <= b:
            alive.append(p); p += 1
        alive = [j for j in alive
                 if fill[j] > b and (b - created[j]) <= cfg.htf_max_age_bars]
        for j in reversed(alive):
            d = dirs[j]
            if (d > 0 and not cfg.allow_long) or (d < 0 and not cfg.allow_short): continue
            if (d > 0 and close[b] > his[j]) or (d < 0 and close[b] < los[j]):
                active[b] = j; break
    # 4H bar b closes at open_b + 4h -> usable by 15M bars opening at >= that instant
    htf_close = htf.index.values + pd.Timedelta(cfg.htf_rule).to_timedelta64()
    pos = np.searchsorted(htf_close, ltf_index.values, side="right") - 1
    act = np.where(pos >= 0, active[np.clip(pos, 0, N - 1)], -1)
    assert (pos < 0).all() or (htf_close[np.clip(pos, 0, N - 1)] <= ltf_index.values)[pos >= 0].all()
    return act


class Prepared:  # shared, immutable feature block used by BOTH engines
    pass


def prepare(ltf_raw: pd.DataFrame, cfg: Config) -> Prepared:
    P = Prepared()
    P.ltf = validate_ohlcv(ltf_raw, cfg.ltf_rule)
    P.htf = resample_ohlcv(P.ltf, cfg.htf_rule)
    P.idx = P.ltf.index
    P.o, P.h, P.l, P.c = (P.ltf[k].values for k in ("open", "high", "low", "close"))
    P.n = len(P.ltf)
    P.atr_l = atr(P.ltf, cfg.atr_n)
    atr_h = atr(P.htf, cfg.atr_n)
    HF = find_fvgs(P.htf, atr_h, cfg.min_htf_fvg_atr)
    LF = find_fvgs(P.ltf, P.atr_l, cfg.min_ltf_fvg_atr)
    P.htf_dir, P.htf_lo, P.htf_hi = HF["dir"], HF["lo"], HF["hi"]
    P.act = htf_active_map(P.htf, HF, P.idx, cfg)
    P.chg = np.flatnonzero(np.r_[True, P.act[1:] != P.act[:-1]])
    P.ltf_dir = np.zeros(P.n, int); P.ltf_dir[LF["idx"]] = LF["dir"]
    P.ltf_lo = np.full(P.n, np.nan); P.ltf_lo[LF["idx"]] = LF["lo"]
    P.ltf_hi = np.full(P.n, np.nan); P.ltf_hi[LF["idx"]] = LF["hi"]
    P.bull_idx = LF["idx"][LF["dir"] > 0]
    P.bear_idx = LF["idx"][LF["dir"] < 0]
    P.rm_low = RangeExtreme(P.l, "min"); P.rm_high = RangeExtreme(P.h, "max")
    P.rm_cmin = RangeExtreme(P.c, "min"); P.rm_cmax = RangeExtreme(P.c, "max")
    P.bars_per_year = int(pd.Timedelta("365D") / pd.Timedelta(cfg.ltf_rule))
    P.bar_hours = pd.Timedelta(cfg.ltf_rule) / pd.Timedelta("1h")
    return P


# ============================== 4. SHARED SETUP LOGIC =========================
def relevant(d, llo, lhi, zlo, zhi, a, cfg) -> bool:
    """15M FVG must live inside / just outside the 4H zone — no chasing."""
    ext, tol = cfg.ltf_max_ext_atr * a, 0.10 * a
    return (llo >= zlo - tol and llo <= zhi + ext) if d > 0 else \
           (lhi <= zhi + tol and lhi >= zlo - ext)


def build_setup(d, llo, lhi, zlo, zhi, a, cfg):
    if d > 0:
        entry = lhi if cfg.entry_mode == "proximal" else (llo + lhi) / 2
        base = llo if cfg.stop_mode == "ltf_fvg" else zlo
        stop = base - cfg.stop_buf_atr * a
    else:
        entry = llo if cfg.entry_mode == "proximal" else (llo + lhi) / 2
        base = lhi if cfg.stop_mode == "ltf_fvg" else zhi
        stop = base + cfg.stop_buf_atr * a
    risk = (entry - stop) * d
    if risk <= 0 or not (cfg.min_stop_atr * a <= risk <= cfg.max_stop_atr * a):
        return None
    cost = (cfg.fee_maker + cfg.fee_taker + 2 * cfg.slip_bps / 1e4) * entry
    if cfg.tp_r * risk < cfg.min_reward_cost_mult * cost:
        return None
    return entry, stop, entry + d * cfg.tp_r * risk, risk


def size_and_costs(eq, d, entry, stop, exit_px, bars, reason, cfg, bar_hours):
    risk_per = abs(entry - stop)
    qty = (eq * cfg.risk_pct) / risk_per
    qty = min(qty, (eq * cfg.max_leverage) / entry)
    notional = qty * entry
    if notional < cfg.min_notional or qty <= 0:
        return None
    gross = (exit_px - entry) * qty * d
    fees = entry * qty * cfg.fee_maker + exit_px * qty * (
        cfg.fee_taker if reason in TAKER_REASONS else cfg.fee_maker)
    funding = d * notional * (cfg.funding_bps_8h / 1e4) * (bars * bar_hours / 8.0)
    net = gross - fees - funding
    return dict(qty=qty, pnl=net, fees=fees, funding=funding, r=net / (qty * risk_per))


def slip(px, d, cfg, taker):
    return px - d * px * cfg.slip_bps / 1e4 if taker else px


# ====================== 5. FRAMEWORK 1 — VECTOR ENGINE ========================
def backtest_vector(P: Prepared, cfg: Config) -> pd.DataFrame:
    """Event-jumping vector backtest. Every lookup is O(log n); no per-bar Python loop.
    Fixed SL/TP (no partials/trailing) -> use for research sweeps, verify with engine 2."""
    n, act, chg = P.n, P.act, P.chg
    trades, used = [], set()

    def next_chg(i):
        k = np.searchsorted(chg, i + 1, "left")
        return int(chg[k]) if k < len(chg) else n

    i = 0
    while i < n:
        a = int(act[i])
        if a < 0 or a in used:
            i = next_chg(i); continue
        d = int(P.htf_dir[a]); zlo, zhi = float(P.htf_lo[a]), float(P.htf_hi[a])
        zce = (zlo + zhi) / 2
        touch = (zce if cfg.htf_use_ce else zhi) if d > 0 else (zce if cfg.htf_use_ce else zlo)
        inval = zlo if d > 0 else zhi
        jt = P.rm_low.first_cross(i, touch) if d > 0 else P.rm_high.first_cross(i, touch)
        jv = P.rm_cmin.first_cross(i, inval) if d > 0 else P.rm_cmax.first_cross(i, inval)
        jc = next_chg(i)
        if jv <= jt or jc <= jt or jt >= n:            # invalidation / zone change wins ties
            i = max(i + 1, min(jv, jc)); continue

        # --- 15M confirmation FVG inside the window
        j, deadline = jt, jt + cfg.max_wait_bars
        cand = P.bull_idx if d > 0 else P.bear_idx
        s = np.searchsorted(cand, j, "left")
        e = np.searchsorted(cand, min(deadline, jc - 1), "right")
        setup = None
        for t in range(s, e):
            k = int(cand[t])
            if k >= jv: break
            al = float(P.atr_l[k]); llo, lhi = float(P.ltf_lo[k]), float(P.ltf_hi[k])
            if not relevant(d, llo, lhi, zlo, zhi, al, cfg): continue
            st = build_setup(d, llo, lhi, zlo, zhi, al, cfg)
            if st: setup = (k, st); break
        if setup is None:
            i = max(j + 1, min(deadline + 1, jc, jv, n)); continue

        k, (entry, stop, target, _) = setup
        start, end = k + 1, min(k + 1 + cfg.order_expiry_bars, n)
        if start >= n: break
        f = P.rm_low.first_cross(start, entry) if d > 0 else P.rm_high.first_cross(start, entry)
        v = P.rm_cmin.first_cross(start, stop) if d > 0 else P.rm_cmax.first_cross(start, stop)
        if f >= end or f > v:
            i = max(start, min(end, v, n)); continue

        ep = min(P.o[f], entry) if (cfg.gap_fill_better and d > 0) else \
             max(P.o[f], entry) if cfg.gap_fill_better else entry
        if (d > 0 and P.o[f] <= stop) or (d < 0 and P.o[f] >= stop):
            xi, xp, reason = f, P.o[f], "gap_stop"
        else:
            si = P.rm_low.first_cross(f, stop) if d > 0 else P.rm_high.first_cross(f, stop)
            ti = P.rm_high.first_cross(f, target) if d > 0 else P.rm_low.first_cross(f, target)
            hb = f + cfg.max_hold_bars
            xi = min(si, ti, hb, n - 1)
            if si <= ti and si <= hb: xp, reason = stop, "stop"
            elif ti <= hb:            xp, reason = target, "target"
            else:                     xp, reason = P.c[xi], ("time" if hb <= n - 1 else "eod")
        xp = slip(xp, d, cfg, reason in TAKER_REASONS)
        bars = xi - f
        mae = (P.l[f:xi + 1].min() - ep) * d if d > 0 else (ep - P.h[f:xi + 1].max())
        mfe = (P.h[f:xi + 1].max() - ep) * d if d > 0 else (ep - P.l[f:xi + 1].min())
        trades.append(dict(entry_i=f, exit_i=xi, entry_time=P.idx[f], exit_time=P.idx[xi],
                           dir=d, entry=ep, exit=xp, stop=stop, target=target, bars=bars,
                           reason=reason, htf_id=a, mae=mae, mfe=mfe))
        if cfg.one_trade_per_htf: used.add(a)
        i = xi + 1 + cfg.cooldown_bars

    return _equity_vector(trades, P, cfg)


def _equity_vector(trades, P, cfg) -> pd.DataFrame:
    eq, curve = cfg.start_equity, np.full(P.n, cfg.start_equity)
    rows = []
    for t in trades:
        sc = size_and_costs(eq, t["dir"], t["entry"], t["stop"], t["exit"],
                            t["bars"], t["reason"], cfg, P.bar_hours)
        if sc is None: continue
        eq += sc["pnl"]
        rows.append({**t, **sc, "equity": eq,
                     "mae_r": t["mae"] / abs(t["entry"] - t["stop"]),
                     "mfe_r": t["mfe"] / abs(t["entry"] - t["stop"])})
        curve[t["exit_i"]:] = eq
    df = pd.DataFrame(rows)
    df.attrs["curve"] = pd.Series(curve, index=P.idx)
    return df


# ====================== 6. FRAMEWORK 2 — EVENT ENGINE =========================
class EventEngine:
    """Chronological bar loop with resting orders, partials, BE, trailing, funding,
    kill switches, and optional 1-minute intrabar resolution. Live-ready shape."""

    def __init__(self, P: Prepared, cfg: Config, fine: Optional[pd.DataFrame] = None):
        self.P, self.cfg, self.fine = P, cfg, fine
        self.eq = cfg.start_equity
        self.pos = self.pending = None
        self.state, self.zone, self.touch_i = "WAIT_TOUCH", -2, -1
        self.used, self.trades = set(), []
        self.blocked_until = -1
        self.next_stop = None
        self.curve = np.full(P.n, cfg.start_equity)
        self.peak = cfg.start_equity
        self.day, self.day_eq = None, cfg.start_equity
        self.halted = False

    # ---------- intrabar path ----------
    def _subbars(self, i):
        if self.fine is None:
            return [(self.P.o[i], self.P.h[i], self.P.l[i], self.P.c[i])]
        t0 = self.P.idx[i]; t1 = t0 + pd.Timedelta(self.cfg.ltf_rule)
        w = self.fine.loc[t0:t1 - pd.Timedelta("1ns")]
        if len(w) == 0:
            return [(self.P.o[i], self.P.h[i], self.P.l[i], self.P.c[i])]
        return list(w[["open", "high", "low", "close"]].itertuples(index=False, name=None))

    def _fill_price(self, o, h, l):
        p, d = self.pending, self.pending["dir"]
        if d > 0 and l <= p["entry"]:
            return min(o, p["entry"]) if self.cfg.gap_fill_better else p["entry"]
        if d < 0 and h >= p["entry"]:
            return max(o, p["entry"]) if self.cfg.gap_fill_better else p["entry"]
        return None

    # ---------- order lifecycle ----------
    def _process_orders(self, i):
        cfg, P = self.cfg, self.P
        if self.pos is not None and self.next_stop is not None:
            self.pos["stop"] = self.next_stop; self.next_stop = None
        for (o, h, l, c) in self._subbars(i):
            if self.pending is not None and i >= self.pending["active_from"]:
                fp = self._fill_price(o, h, l)
                if fp is not None:
                    self._open(i, fp)
                    if self.pos is None: break
                    d = self.pos["dir"]
                    if (d > 0 and o <= self.pos["stop"]) or (d < 0 and o >= self.pos["stop"]):
                        self._close(i, o, "gap_stop", True); break
            if self.pos is not None:
                p, d = self.pos, self.pos["dir"]
                hs = (l <= p["stop"]) if d > 0 else (h >= p["stop"])
                ht = (h >= p["target"]) if d > 0 else (l <= p["target"])
                hp = (p["partial"] is not None) and (
                     (h >= p["partial"]) if d > 0 else (l <= p["partial"]))
                if hs:                                   # CONSERVATIVE: stop first
                    self._close(i, p["stop"], "stop", True); break
                if hp: self._partial(i, p["partial"])
                if ht:
                    self._close(i, p["target"], "target", False); break
        if self.pending is not None:
            d, st = self.pending["dir"], self.pending["stop"]
            dead = (i >= self.pending["expires"]) or \
                   ((P.c[i] <= st) if d > 0 else (P.c[i] >= st))
            if dead:
                self.pending = None; self.state = "WAIT_TOUCH"

    def _open(self, i, price):
        cfg, P, p = self.cfg, self.P, self.pending
        d, stop = p["dir"], p["stop"]
        sc = size_and_costs(self.eq, d, price, stop, price, 0, "target", cfg, P.bar_hours)
        if sc is None:
            self.pending = None; self.state = "WAIT_TOUCH"; return
        qty = sc["qty"]
        self.eq -= price * qty * cfg.fee_maker
        risk = abs(price - stop)
        self.pos = dict(dir=d, qty=qty, qty0=qty, entry=price, stop=stop, target=p["target"],
                        risk=risk, entry_i=i, htf_id=p["htf_id"], realized=0.0,
                        fees=price * qty * cfg.fee_maker, funding=0.0, mae=0.0, mfe=0.0,
                        partial=(price + d * cfg.partial_at_r * risk) if cfg.partial_at_r else None,
                        be_done=False)
        self.pending = None
        if cfg.one_trade_per_htf: self.used.add(p["htf_id"])

    def _partial(self, i, price):
        cfg, p = self.cfg, self.pos
        q = p["qty0"] * cfg.partial_frac
        q = min(q, p["qty"])
        if q <= 0: p["partial"] = None; return
        fee = price * q * cfg.fee_maker
        pnl = (price - p["entry"]) * q * p["dir"] - fee
        self.eq += pnl; p["realized"] += pnl; p["fees"] += fee
        p["qty"] -= q; p["partial"] = None
        if cfg.be_at_r is not None and not p["be_done"]:
            be = p["entry"] + p["dir"] * p["entry"] * (cfg.fee_maker + cfg.fee_taker) * 1.5
            self.next_stop = max(p["stop"], be) if p["dir"] > 0 else min(p["stop"], be)
            p["be_done"] = True

    def _close(self, i, price, reason, taker):
        cfg, p = self.cfg, self.pos
        d = p["dir"]
        px = slip(price, d, cfg, taker)
        fee = px * p["qty"] * (cfg.fee_taker if taker else cfg.fee_maker)
        pnl = (px - p["entry"]) * p["qty"] * d - fee
        self.eq += pnl
        total = p["realized"] + pnl
        bars = i - p["entry_i"]
        self.trades.append(dict(
            entry_i=p["entry_i"], exit_i=i, entry_time=self.P.idx[p["entry_i"]],
            exit_time=self.P.idx[i], dir=d, entry=p["entry"], exit=px, stop=p["stop"],
            target=p["target"], qty=p["qty0"], bars=bars, reason=reason, htf_id=p["htf_id"],
            pnl=total, fees=p["fees"] + fee, funding=p["funding"],
            r=total / (p["qty0"] * p["risk"]),
            mae_r=p["mae"] / p["risk"], mfe_r=p["mfe"] / p["risk"], equity=self.eq))
        self.pos = None
        self.blocked_until = i + cfg.cooldown_bars
        self.state = "WAIT_TOUCH"

    # ---------- mark, funding, management ----------
    def _mark(self, i):
        cfg, P = self.cfg, self.P
        ts = P.idx[i]
        if self.day != ts.date():
            self.day, self.day_eq = ts.date(), self.eq
        if self.pos is not None:
            p, d = self.pos, self.pos["dir"]
            if ts.hour % 8 == 0 and ts.minute == 0:
                f = p["qty"] * p["entry"] * (cfg.funding_bps_8h / 1e4) * d
                self.eq -= f; p["funding"] += f
            p["mae"] = min(p["mae"], (P.l[i] - p["entry"]) * d)
            p["mfe"] = max(p["mfe"], (P.h[i] - p["entry"]) * d)
            unreal = (P.c[i] - p["entry"]) * p["qty"] * d
        else:
            unreal = 0.0
        mark = self.eq + unreal
        self.curve[i] = mark
        self.peak = max(self.peak, mark)
        if (self.peak - mark) / self.peak >= cfg.max_dd_stop_pct:
            self.halted = True

    def _manage_on_close(self, i):
        """All close-based decisions take effect on the NEXT bar. No intrabar clairvoyance."""
        cfg, P, p = self.cfg, self.P, self.pos
        if p is None: return
        d, c = p["dir"], P.c[i]
        r_now = (c - p["entry"]) * d / p["risk"]
        if cfg.be_at_r is not None and not p["be_done"] and r_now >= cfg.be_at_r:
            be = p["entry"] + d * p["entry"] * (cfg.fee_maker + cfg.fee_taker) * 1.5
            self.next_stop = max(p["stop"], be) if p["dir"] > 0 else min(p["stop"], be)
            p["be_done"] = True
        if cfg.trail_at_r is not None and r_now >= cfg.trail_at_r:
            t = c - d * cfg.trail_atr * P.atr_l[i]
            cand = max(p["stop"], t) if p["dir"] > 0 else min(p["stop"], t)
            self.next_stop = cand if self.next_stop is None else (
                max(self.next_stop, cand) if p["dir"] > 0 else min(self.next_stop, cand))
        if i - p["entry_i"] >= cfg.max_hold_bars:
            self._close(i, c, "time", True)

    # ---------- the strategy itself (same logic as the vector engine) ----------
    def _strategy(self, i):
        cfg, P = self.cfg, self.P
        if self.halted or i <= self.blocked_until: return
        if self.eq < self.day_eq * (1 - cfg.max_daily_loss_pct): return
        a = int(P.act[i])
        if a != self.zone:
            self.zone, self.state, self.touch_i = a, "WAIT_TOUCH", -1
        if a < 0 or a in self.used: return
        d = int(P.htf_dir[a]); zlo, zhi = float(P.htf_lo[a]), float(P.htf_hi[a])
        zce = (zlo + zhi) / 2
        touch = (zce if cfg.htf_use_ce else zhi) if d > 0 else (zce if cfg.htf_use_ce else zlo)
        inval = zlo if d > 0 else zhi
        if (d > 0 and P.c[i] <= inval) or (d < 0 and P.c[i] >= inval): return
        if self.state == "WAIT_FVG" and i > self.touch_i + cfg.max_wait_bars:
            self.state = "WAIT_TOUCH"
        if self.state == "WAIT_TOUCH":
            if (d > 0 and P.l[i] <= touch) or (d < 0 and P.h[i] >= touch):
                self.state, self.touch_i = "WAIT_FVG", i
            else:
                return
        if self.state == "WAIT_FVG" and P.ltf_dir[i] == d and np.isfinite(P.ltf_lo[i]):
            al = float(P.atr_l[i]); llo, lhi = float(P.ltf_lo[i]), float(P.ltf_hi[i])
            if not relevant(d, llo, lhi, zlo, zhi, al, cfg): return
            st = build_setup(d, llo, lhi, zlo, zhi, al, cfg)
            if st is None: return
            entry, stop, target, _ = st
            self.pending = dict(dir=d, entry=entry, stop=stop, target=target, htf_id=a,
                                active_from=i + 1, expires=i + 1 + cfg.order_expiry_bars)

    def run(self) -> pd.DataFrame:
        for i in range(self.P.n):
            self._process_orders(i)
            self._mark(i)
            self._manage_on_close(i)
            if self.pos is None and self.pending is None:
                self._strategy(i)
        df = pd.DataFrame(self.trades)
        df.attrs["curve"] = pd.Series(self.curve, index=self.P.idx)
        return df


# ====================== 7. METRICS / VALIDATION ===============================
def performance(trades: pd.DataFrame, P: Prepared, cfg: Config) -> Dict:
    if trades.empty: return {"trades": 0}
    cur = trades.attrs["curve"]
    ret = cur.pct_change().fillna(0)
    yrs = len(cur) / P.bars_per_year
    dd = (cur / cur.cummax() - 1)
    wins, losses = trades[trades.pnl > 0], trades[trades.pnl <= 0]
    gp, gl = wins.pnl.sum(), -losses.pnl.sum()
    return dict(
        trades=len(trades),
        total_return_pct=100 * (cur.iloc[-1] / cfg.start_equity - 1),
        cagr_pct=100 * ((cur.iloc[-1] / cfg.start_equity) ** (1 / max(yrs, 1e-9)) - 1),
        sharpe=float(ret.mean() / (ret.std() + 1e-12) * np.sqrt(P.bars_per_year)),
        sortino=float(ret.mean() / (ret[ret < 0].std() + 1e-12) * np.sqrt(P.bars_per_year)),
        max_dd_pct=100 * dd.min(),
        calmar=float((cur.iloc[-1] / cfg.start_equity - 1) / max(abs(dd.min()), 1e-9)),
        win_rate_pct=100 * len(wins) / len(trades),
        profit_factor=float(gp / gl) if gl > 0 else np.inf,
        expectancy_r=float(trades.r.mean()),
        avg_win_r=float(wins.r.mean()) if len(wins) else 0.0,
        avg_loss_r=float(losses.r.mean()) if len(losses) else 0.0,
        exposure_pct=100 * trades.bars.sum() / len(cur),
        fees_total=float(trades.fees.sum()), funding_total=float(trades.funding.sum()),
        avg_bars=float(trades.bars.mean()),
    )


def monte_carlo(trades: pd.DataFrame, cfg: Config, n=2000, seed=1) -> Dict:
    if trades.empty: return {}
    rng = np.random.default_rng(seed)
    r = trades.r.values * cfg.risk_pct
    finals, dds = [], []
    for _ in range(n):
        s = rng.choice(r, size=len(r), replace=True)
        eq = cfg.start_equity * np.cumprod(1 + s)
        peak = np.maximum.accumulate(eq)
        finals.append(eq[-1]); dds.append(((eq - peak) / peak).min())
    q = lambda a, p: float(np.percentile(a, p))
    return dict(mc_median_equity=q(finals, 50), mc_p5_equity=q(finals, 5),
                mc_p95_equity=q(finals, 95), mc_median_maxdd_pct=100 * q(dds, 50),
                mc_worst_maxdd_pct=100 * q(dds, 1),
                prob_50pct_dd=float(np.mean(np.array(dds) < -0.5)))


def parity_check(P: Prepared, cfg: Config, tol=1e-6) -> bool:
    """THE most important test. Simple mode: engines must produce identical trades."""
    simple = replace(cfg, be_at_r=None, partial_at_r=None, partial_frac=0.0,
                     trail_at_r=None, min_notional=0.0,
                     max_daily_loss_pct=1.0, max_dd_stop_pct=1.0)
    v = backtest_vector(P, simple)
    e = EventEngine(P, simple).run()
    ok = len(v) == len(e)
    if ok and len(v):
        for col in ("entry_i", "exit_i", "dir"):
            ok &= (v[col].values == e[col].values).all()
        for col in ("entry", "exit"):
            ok &= np.allclose(v[col].values, e[col].values, atol=tol, rtol=tol)
    print(f"[parity] vector={len(v)} trades | event={len(e)} trades | MATCH={ok}")
    if not ok and len(v) and len(e):
        m = v.merge(e, on="entry_i", suffixes=("_v", "_e"), how="outer", indicator=True)
        print(m[m._merge != "both"].head(10).to_string())
    return bool(ok)


def walk_forward(P: Prepared, base: Config, grid: List[Dict],
                 train_bars=8000, test_bars=2000, embargo=96) -> pd.DataFrame:
    """Anchored-rolling WFO with purge/embargo. Only OOS results mean anything."""
    out, start = [], 0
    while start + train_bars + embargo + test_bars <= P.n:
        tr = slice(start, start + train_bars)
        te = slice(start + train_bars + embargo, start + train_bars + embargo + test_bars)
        best, best_score = None, -np.inf
        for g in grid:
            cfg = replace(base, **g)
            sub = _slice_prepared(P, tr)
            t = backtest_vector(sub, cfg)
            if len(t) < 20: continue
            score = performance(t, sub, cfg)["calmar"]
            if score > best_score: best_score, best = score, cfg
        if best is None:
            start += test_bars; continue
        sub = _slice_prepared(P, te)
        t = backtest_vector(sub, best)
        out.append(dict(test_start=P.idx[te.start], test_end=P.idx[te.stop - 1],
                        params={k: getattr(best, k) for k in grid[0]},
                        **performance(t, sub, best)))
        start += test_bars
    return pd.DataFrame(out)


def _slice_prepared(P: Prepared, sl: slice) -> Prepared:
    """Rebuild features on a slice (features are recomputed -> no cross-fold leakage)."""
    return prepare(P.ltf.iloc[sl], Config(htf_rule=P.htf.index.freqstr or "4h"))


# ============================== 8. RUN ========================================
if __name__ == "__main__":
    import os
    cfg = Config()
    path = "data/BTCUSDT_15m.csv"
    if os.path.exists(path):
        raw = pd.read_csv(path)
        tcol = "open_time" if "open_time" in raw else raw.columns[0]
        raw.index = pd.to_datetime(raw[tcol], utc=True, unit="ms" if raw[tcol].dtype != object else None)
        raw = raw.drop(columns=[tcol])
        print(f"[data] loaded {len(raw)} real bars")
    else:
        raw = synthetic_15m()
        print("[data] *** SYNTHETIC DEMO DATA — results are meaningless, plumbing only ***")

    P = prepare(raw, cfg)
    print(f"[data] 15M bars={P.n} | 4H bars={len(P.htf)} | "
          f"HTF FVGs={len(P.htf_dir)} | LTF FVGs={len(P.bull_idx)+len(P.bear_idx)}")

    assert parity_check(P, cfg), "ENGINES DISAGREE — fix before trusting any number."

    import time
    t0 = time.time(); vec = backtest_vector(P, cfg); t1 = time.time()
    evt = EventEngine(P, cfg).run();                  t2 = time.time()
    print(f"\n--- FRAMEWORK 1 (vector)  {t1-t0:.3f}s ---")
    for k, v in performance(vec, P, cfg).items(): print(f"  {k:>20}: {v:,.4f}" if isinstance(v, float) else f"  {k:>20}: {v}")
    print(f"\n--- FRAMEWORK 2 (event, full management)  {t2-t1:.3f}s ---")
    for k, v in performance(evt, P, cfg).items(): print(f"  {k:>20}: {v:,.4f}" if isinstance(v, float) else f"  {k:>20}: {v}")
    print("\n--- MONTE CARLO (trade bootstrap) ---")
    for k, v in monte_carlo(evt, cfg).items(): print(f"  {k:>22}: {v:,.4f}")
    evt.to_csv("trades_event.csv", index=False)
    evt.attrs["curve"].to_csv("equity_event.csv")
    print("\nSaved trades_event.csv / equity_event.csv")
