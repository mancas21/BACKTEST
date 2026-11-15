"""
fvg_upgrades.py — #1 true 1m intrabar resolution, #2 DST-correct session/liquidity filters.
Drop-in extensions for fvg_system.py.  numpy + pandas only (ccxt optional).

    from fvg_system import prepare
    from fvg_upgrades import ConfigV2, FineData, SessionContext, EventEngineV2, backtest_vector_v2
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass, replace
from typing import Optional, List, Dict, Tuple

from fvg_system import (
    Config, Prepared, prepare, EventEngine, performance, monte_carlo,
    RangeExtreme, build_setup, relevant, size_and_costs, slip, TAKER_REASONS,
    validate_ohlcv, resample_ohlcv,
)

# ============================ 0. EXTENDED CONFIG ==============================
@dataclass
class ConfigV2(Config):
    # ---- #1 execution realism -------------------------------------------------
    tick_size: float = 0.1            # BTCUSDT perp = 0.1; ETH = 0.01
    fill_touch_ticks: int = 0         # require price to trade N ticks THROUGH the limit
    entry_delay_s: float = 0.0        # signal->order latency (resting stops unaffected)
    manage_on_fine: bool = True       # run BE/trailing on 1m closes (live-bot behaviour)
    fine_strict: bool = True          # demand 15 complete + matching 1m bars
    fine_ohlc_tol_bps: float = 0.5    # 1m aggregate vs 15m bar tolerance

    # ---- #2 sessions ----------------------------------------------------------
    use_sessions: bool = True
    tz_sessions: str = "America/New_York"
    kz_london: bool = True
    kz_ny_am: bool = True
    kz_ny_pm: bool = False
    kz_london_close: bool = False
    london_win: Tuple[int, int] = (120, 300)        # 02:00-05:00 NY
    ny_am_win: Tuple[int, int] = (510, 660)         # 08:30-11:00 NY
    ny_pm_win: Tuple[int, int] = (810, 960)         # 13:30-16:00 NY
    london_close_win: Tuple[int, int] = (600, 720)  # 10:00-12:00 NY
    asia_win: Tuple[int, int] = (1200, 1440)        # 20:00-24:00 NY (reference only)
    gate_touch: bool = False                        # also require the 4H touch in-session
    cancel_pending_outside_session: bool = True     # kill unfilled limits when session ends
    flat_at_session_end: bool = False               # intraday-only: flat when window closes
    skip_weekends: bool = True
    fri_cutoff_min: Optional[int] = None            # e.g. 1200 = no entries Fri after 20:00 NY

    # ---- #2 liquidity / regime ------------------------------------------------
    daily_anchor_tz: str = "UTC"      # crypto daily candles = UTC; FX would be NY
    require_asia_sweep: bool = False  # turtle soup: sweep Asian range then reclaim
    asia_sweep_lookback: int = 32
    block_obstacle: bool = False      # reject if PDH/PWH sits between entry and TP
    obstacle_min_r: float = 0.5
    require_draw: bool = False        # require a liquidity pool at/beyond TP (magnet)
    draw_max_r: float = 6.0
    vol_lookback: int = 96 * 7
    min_vol_ratio: float = 0.0        # bar volume / rolling median volume
    atr_lookback: int = 96 * 14
    min_atr_ratio: float = 0.0        # skip dead vol
    max_atr_ratio: float = 1e9        # skip chaos
    funding_blackout_min: int = 0     # block +/- N min around 00/08/16 UTC
    news_times: Optional[List] = None # list of UTC timestamps (CPI, FOMC...)
    news_blackout_min: int = 30


SESSION_NAMES = {0: "outside", 1: "asia", 2: "london", 3: "ny_am", 4: "ny_pm", 5: "ldn_close"}


# ============================ 1. FINE (1m) DATA ===============================
class FineData:
    """Pre-aligned 1-minute bars with O(1) per-15M-bar lookup + integrity audit.

    Why this exists: a pandas .loc slice per bar costs ~150us -> 20s per backtest.
    searchsorted offsets + numpy views cost ~1us. Same answer, 100x faster.
    """

    def __init__(self, df_1m: pd.DataFrame, P: Prepared, cfg: ConfigV2, verbose=True):
        df = validate_ohlcv(df_1m, "1min")
        self.cfg = cfg
        self.idx = df.index
        self.ts = df.index.values.astype("int64")
        self.o, self.h, self.l, self.c = (df[k].values for k in ("open", "high", "low", "close"))

        step = pd.Timedelta(cfg.ltf_rule).to_timedelta64().astype("int64")
        base = P.idx.values.astype("int64")
        self.start = np.searchsorted(self.ts, base, "left")
        self.end = np.searchsorted(self.ts, base + step, "left")
        cnt = self.end - self.start
        expected = int(pd.Timedelta(cfg.ltf_rule) / pd.Timedelta("1min"))

        # --- vectorised aggregate of 1m -> parent bar, for integrity checking
        m = cnt > 0
        st = self.start[m]
        en = self.end[m]
        h_ext = np.r_[self.h, -np.inf]
        l_ext = np.r_[self.l, np.inf]
        se = np.r_[st, len(self.h)]
        ah = np.maximum.reduceat(h_ext, se)[:-1]
        al = np.minimum.reduceat(l_ext, se)[:-1]
        ao = self.o[st]
        ac = self.c[en - 1]

        tol = cfg.fine_ohlc_tol_bps / 1e4
        ok = np.zeros(P.n, bool)
        ph, pl, po, pc = P.h[m], P.l[m], P.o[m], P.c[m]
        good = (np.abs(ah - ph) <= tol * ph) & (np.abs(al - pl) <= tol * pl) \
             & (np.abs(ao - po) <= tol * po) & (np.abs(ac - pc) <= tol * pc)
        tmp = np.zeros(m.sum(), bool); tmp[:] = good
        ok[m] = tmp

        complete = cnt == expected
        self.usable = (ok & complete) if cfg.fine_strict else (ok & m)
        self.mode = self.usable.astype(np.int8)
        self.stats = dict(
            fine_rows=len(df), ltf_bars=P.n,
            pct_complete=100 * complete.mean(),
            pct_integrity_ok=100 * ok.mean(),
            pct_usable=100 * self.usable.mean(),
        )
        if verbose:
            print("[fine] " + " | ".join(f"{k}={v:,.2f}" if isinstance(v, float) else f"{k}={v:,}"
                                         for k, v in self.stats.items()))
            if self.usable.mean() < 0.95:
                print("[fine] WARNING: <95% usable. Build your 15M FROM the 1m feed "
                      "(build_ltf_from_fine) so the two are guaranteed consistent.")

    def bounds(self, i) -> Tuple[int, int]:
        return int(self.start[i]), int(self.end[i])


def build_ltf_from_fine(df_1m: pd.DataFrame, cfg: ConfigV2) -> pd.DataFrame:
    """The correct way: derive 15M from 1m. Integrity is then 100% by construction."""
    return resample_ohlcv(validate_ohlcv(df_1m, "1min"), cfg.ltf_rule)


def download_binance_1m(symbol="BTC/USDT:USDT", days=120, end=None) -> pd.DataFrame:
    """1m is ~1440 rows/day. 120 days = 172k rows. Paginate patiently."""
    import ccxt
    ex = ccxt.binanceusdm({"enableRateLimit": True})
    tf_ms = 60_000
    stop = ex.milliseconds() if end is None else ex.parse8601(end)
    since = stop - days * 86400_000
    rows, last = [], None
    while since < stop:
        b = ex.fetch_ohlcv(symbol, "1m", since=since, limit=1500)
        if not b: break
        if last is not None and b[0][0] <= last: break
        rows += b
        last = b[-1][0]
        since = last + tf_ms
        if len(b) < 1500: break
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"]).drop_duplicates("ts")
    df.index = pd.to_datetime(df.ts, unit="ms", utc=True)
    return df.drop(columns="ts")


def synthetic_1m(days=210, seed=11, px=42000.0, start="2024-01-01") -> pd.DataFrame:
    """DEMO ONLY. Includes a real UTC time-of-day vol seasonality so session
    attribution has something genuine to discover. Not a tradable edge."""
    n = days * 1440
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=n, freq="1min", tz="UTC")
    base = pd.Series(np.abs(rng.normal(0, 0.0011, n))).ewm(alpha=0.02, adjust=False).mean().values
    hour = idx.hour.values + idx.minute.values / 60.0
    season = 0.55 + 0.95 * np.exp(-0.5 * ((hour - 14.0) / 3.5) ** 2) \
                  + 0.45 * np.exp(-0.5 * ((hour - 8.0) / 2.5) ** 2)
    v = np.clip(base * season, 0.00025, 0.012)
    r = rng.normal(0, 1, n) * v
    r += (rng.random(n) < 0.0015) * rng.normal(0, 1, n) * v * 6
    c = px * np.exp(np.cumsum(r)); o = np.r_[px, c[:-1]]
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, .45, n)) * v)
    l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, .45, n)) * v)
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c,
                         "volume": rng.uniform(1, 40, n) * season}, index=idx)


# ============================ 2. SESSION / LIQUIDITY ==========================
class SessionContext:
    """Point-in-time session calendar + liquidity map. All arrays are length P.n.

    DST correctness: everything is computed on NAIVE LOCAL dates, so 'yesterday'
    is a calendar day (23/25h DST days don't shift the map by an hour).
    """

    def __init__(self, P: Prepared, cfg: ConfigV2, verbose=True):
        self.cfg = cfg
        n = P.n
        idx = P.idx
        ny = idx.tz_convert(cfg.tz_sessions)
        ny_naive = ny.tz_localize(None)
        mins = ny.hour.values * 60 + ny.minute.values
        dow = ny.dayofweek.values
        day = ny_naive.normalize()

        def win(a, b): return (mins >= a) & (mins < b)

        sid = np.zeros(n, np.int8)
        sid[win(*cfg.asia_win)] = 1
        if cfg.kz_london:       sid[win(*cfg.london_win)] = 2
        if cfg.kz_london_close: sid[win(*cfg.london_close_win)] = 5
        if cfg.kz_ny_am:        sid[win(*cfg.ny_am_win)] = 3
        if cfg.kz_ny_pm:        sid[win(*cfg.ny_pm_win)] = 4
        allow = np.isin(sid, [2, 3, 4, 5])

        # ---------- blackouts (all knowable in advance or at bar close) ----------
        self.reasons = {}
        if cfg.skip_weekends:
            b = dow >= 5; allow &= ~b; self.reasons["weekend"] = int(b.sum())
        if cfg.fri_cutoff_min is not None:
            b = (dow == 4) & (mins >= cfg.fri_cutoff_min); allow &= ~b
            self.reasons["friday_cut"] = int(b.sum())
        if cfg.funding_blackout_min > 0:
            u = idx.tz_convert("UTC")
            since = (u.hour.values % 8) * 60 + u.minute.values
            b = (since < cfg.funding_blackout_min) | (since >= 480 - cfg.funding_blackout_min)
            allow &= ~b; self.reasons["funding"] = int(b.sum())
        if cfg.news_times:
            b = np.zeros(n, bool)
            tsv = idx.values.astype("int64")
            w = int(cfg.news_blackout_min * 60 * 1e9)
            for t in pd.to_datetime(list(cfg.news_times), utc=True):
                v = t.value
                b |= (tsv >= v - w) & (tsv <= v + w)
            allow &= ~b; self.reasons["news"] = int(b.sum())

        vol = getattr(P, "vol", None)
        if vol is None: vol = P.ltf.volume.values
        if cfg.min_vol_ratio > 0:
            med = pd.Series(vol).rolling(cfg.vol_lookback, min_periods=cfg.vol_lookback // 4).median().values
            b = ~(vol >= cfg.min_vol_ratio * med)
            allow &= ~b; self.reasons["thin_volume"] = int(b.sum())
        if cfg.min_atr_ratio > 0 or cfg.max_atr_ratio < 1e8:
            med = pd.Series(P.atr_l).rolling(cfg.atr_lookback, min_periods=cfg.atr_lookback // 4).median().values
            ratio = P.atr_l / med
            b = ~((ratio >= cfg.min_atr_ratio) & (ratio <= cfg.max_atr_ratio))
            allow &= ~b; self.reasons["vol_regime"] = int(b.sum())

        if not cfg.use_sessions:
            allow = np.ones(n, bool)

        self.sid, self.allow = sid, allow
        # first index >= i that is blocked  (O(1) session-bounded order expiry)
        nb = np.where(~allow, np.arange(n), n)
        self.next_block = np.r_[np.minimum.accumulate(nb[::-1])[::-1], n]

        # ---------- liquidity map (strictly point-in-time) ----------
        H = pd.Series(P.h, index=day); L = pd.Series(P.l, index=day)
        prev = day - pd.Timedelta(days=1)
        asia_mask = sid == 1
        ah = H.where(asia_mask).groupby(level=0).max()
        al = L.where(asia_mask).groupby(level=0).min()
        self.asia_hi = ah.reindex(prev).values
        self.asia_lo = al.reindex(prev).values

        anc = idx.tz_convert(cfg.daily_anchor_tz).tz_localize(None).normalize()
        dh = pd.Series(P.h, index=anc).groupby(level=0).max()
        dl = pd.Series(P.l, index=anc).groupby(level=0).min()
        aprev = anc - pd.Timedelta(days=1)
        self.pdh = dh.reindex(aprev).values
        self.pdl = dl.reindex(aprev).values
        wk = anc - pd.to_timedelta(anc.dayofweek, unit="D")
        wh = pd.Series(P.h, index=wk).groupby(level=0).max()
        wl = pd.Series(P.l, index=wk).groupby(level=0).min()
        pwk = wk - pd.Timedelta(days=7)
        self.pwh = wh.reindex(pwk).values
        self.pwl = wl.reindex(pwk).values

        # ---------- gated touch tables (only built if needed) ----------
        self.rm_low_g = self.rm_high_g = None
        if cfg.gate_touch and cfg.use_sessions:
            self.rm_low_g = RangeExtreme(np.where(allow, P.l, np.inf), "min")
            self.rm_high_g = RangeExtreme(np.where(allow, P.h, -np.inf), "max")

        if verbose:
            cov = 100 * allow.mean()
            print(f"[sess] entry-allowed {cov:.1f}% of bars | " +
                  " ".join(f"{SESSION_NAMES[k]}={100*np.mean(sid==k):.1f}%" for k in np.unique(sid)))
            if self.reasons:
                print("[sess] blackouts(bar counts, overlapping): " +
                      ", ".join(f"{k}={v:,}" for k, v in self.reasons.items()))

    def levels_above(self, i):
        return np.array([self.pdh[i], self.pwh[i], self.asia_hi[i]], float)

    def levels_below(self, i):
        return np.array([self.pdl[i], self.pwl[i], self.asia_lo[i]], float)


def setup_extra_ok(P, S, cfg, d, entry, stop, target, risk, k) -> bool:
    """Liquidity confluences. Shared by BOTH engines -> parity preserved."""
    if S is None:
        return True
    if cfg.require_asia_sweep:
        lb = cfg.asia_sweep_lookback
        s = max(0, k - lb)
        if d > 0:
            al = S.asia_lo[k]
            if not np.isfinite(al): return False
            if not (P.l[s:k + 1].min() < al and P.c[k] > al): return False
        else:
            ah = S.asia_hi[k]
            if not np.isfinite(ah): return False
            if not (P.h[s:k + 1].max() > ah and P.c[k] < ah): return False
    if cfg.block_obstacle:
        lv = S.levels_above(k) if d > 0 else S.levels_below(k)
        lv = lv[np.isfinite(lv)]
        if d > 0:
            bad = (lv > entry + cfg.obstacle_min_r * risk) & (lv < target)
        else:
            bad = (lv < entry - cfg.obstacle_min_r * risk) & (lv > target)
        if bad.any(): return False
    if cfg.require_draw:
        lv = S.levels_above(k) if d > 0 else S.levels_below(k)
        lv = lv[np.isfinite(lv)]
        far = entry + d * cfg.draw_max_r * risk
        ok = (lv >= target) & (lv <= far) if d > 0 else (lv <= target) & (lv >= far)
        if not ok.any(): return False
    return True


# ================== 3. FRAMEWORK 1 v2 — VECTOR + SESSIONS =====================
def backtest_vector_v2(P: Prepared, cfg: ConfigV2, S: Optional[SessionContext] = None) -> pd.DataFrame:
    """Same event-jumping engine, plus session gates. Still O(#trades * log n).
    No 1m resolution here — that is Framework 2's job. Parity-tested against it."""
    n, act, chg = P.n, P.act, P.chg
    trades, used = [], set()
    allow = S.allow if (S is not None and cfg.use_sessions) else np.ones(n, bool)
    nb = S.next_block if S is not None else np.full(n + 1, n, int)
    tick = cfg.fill_touch_ticks * cfg.tick_size
    rm_l = S.rm_low_g if (S is not None and S.rm_low_g is not None) else P.rm_low
    rm_h = S.rm_high_g if (S is not None and S.rm_high_g is not None) else P.rm_high

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
        jt = rm_l.first_cross(i, touch) if d > 0 else rm_h.first_cross(i, touch)
        # RISK LOGIC IS NEVER SESSION-GATED:
        jv = P.rm_cmin.first_cross(i, inval) if d > 0 else P.rm_cmax.first_cross(i, inval)
        jc = next_chg(i)
        if jv <= jt or jc <= jt or jt >= n:
            i = max(i + 1, min(jv, jc)); continue

        j, deadline = jt, jt + cfg.max_wait_bars
        cand = P.bull_idx if d > 0 else P.bear_idx
        s = np.searchsorted(cand, j, "left")
        e = np.searchsorted(cand, min(deadline, jc - 1), "right")
        setup = None
        for t in range(s, e):
            k = int(cand[t])
            if k >= jv: break
            if not allow[k]: continue                      # <-- SESSION GATE (entry only)
            al = float(P.atr_l[k]); llo, lhi = float(P.ltf_lo[k]), float(P.ltf_hi[k])
            if not relevant(d, llo, lhi, zlo, zhi, al, cfg): continue
            st = build_setup(d, llo, lhi, zlo, zhi, al, cfg)
            if st is None: continue
            entry, stop, target, risk = st
            if not setup_extra_ok(P, S, cfg, d, entry, stop, target, risk, k): continue
            setup = (k, st); break
        if setup is None:
            i = max(j + 1, min(deadline + 1, jc, jv, n)); continue

        k, (entry, stop, target, _) = setup
        start = k + 1
        end = min(start + cfg.order_expiry_bars, n)
        if S is not None and cfg.cancel_pending_outside_session:
            end = min(end, int(nb[start]))                 # order dies at first blocked bar
        if start >= n: break
        thr = entry - d * tick
        f = P.rm_low.first_cross(start, thr) if d > 0 else P.rm_high.first_cross(start, thr)
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
        mae = (P.l[f:xi + 1].min() - ep) * d
        mfe = (P.h[f:xi + 1].max() - ep) * d
        trades.append(dict(entry_i=f, exit_i=xi, entry_time=P.idx[f], exit_time=P.idx[xi],
                           dir=d, entry=ep, exit=xp, stop=stop, target=target, bars=bars,
                           reason=reason, htf_id=a, mae=mae, mfe=mfe,
                           sid_setup=int(S.sid[k]) if S is not None else 0,
                           sid_entry=int(S.sid[f]) if S is not None else 0))
        if cfg.one_trade_per_htf: used.add(a)
        i = xi + 1 + cfg.cooldown_bars

    # identical accounting to v1
    eq, curve, rows = cfg.start_equity, np.full(n, cfg.start_equity), []
    for t in trades:
        sc = size_and_costs(eq, d=t["dir"], entry=t["entry"], stop=t["stop"], exit_px=t["exit"],
                            bars=t["bars"], reason=t["reason"], cfg=cfg, bar_hours=P.bar_hours)
        if sc is None: continue
        eq += sc["pnl"]
        rows.append({**t, **sc, "equity": eq,
                     "mae_r": t["mae"] / abs(t["entry"] - t["stop"]),
                     "mfe_r": t["mfe"] / abs(t["entry"] - t["stop"])})
        curve[t["exit_i"]:] = eq
    df = pd.DataFrame(rows)
    df.attrs["curve"] = pd.Series(curve, index=P.idx)
    return df


# ================== 4. FRAMEWORK 2 v2 — EVENT + 1m + SESSIONS =================
class EventEngineV2(EventEngine):
    """Full-fidelity engine: 1-minute path resolution, latency, queue penetration,
    1m management, session gates, liquidity confluences. Live-ready."""

    def __init__(self, P, cfg: ConfigV2, fine: Optional[FineData] = None,
                 sess: Optional[SessionContext] = None):
        super().__init__(P, cfg, fine=None)
        self.fine, self.S = fine, sess
        self._now_ts = int(P.idx[0].value)
        self._ltf_ns = int(pd.Timedelta(cfg.ltf_rule).value)
        self.stats = dict(fine_bars=0, coarse_bars=0, ambiguous=0,
                          session_cancels=0, session_blocks=0, liquidity_blocks=0)

    # ---- queue realism: a level merely touched to the tick may not fill you ----
    def _fill_price(self, o, h, l):
        p = self.pending; d = p["dir"]; e = p["entry"]
        k = self.cfg.fill_touch_ticks * self.cfg.tick_size
        if d > 0 and l <= e - k:
            return min(o, e) if self.cfg.gap_fill_better else e
        if d < 0 and h >= e + k:
            return max(o, e) if self.cfg.gap_fill_better else e
        return None

    def _open(self, i, price):
        super()._open(i, price)
        if self.pos is not None:
            self.pos["entry_ts"] = self._now_ts

    def _close(self, i, price, reason, taker):
        ets = self.pos.get("entry_ts") if self.pos else None
        n0 = len(self.trades)
        super()._close(i, price, reason, taker)
        self.next_stop = None                      # <-- v1 BUG FIX: no stale BE leak
        if len(self.trades) > n0:
            self.trades[-1]["exit_time"] = pd.Timestamp(self._now_ts, tz="UTC")
            if ets is not None:
                self.trades[-1]["entry_time"] = pd.Timestamp(ets, tz="UTC")
            self.trades[-1]["sid_entry"] = int(self.S.sid[i]) if self.S is not None else 0
            self.trades[-1]["sid_setup"] = self._sid_setup

    # ---- 1m-close management (uses LAST KNOWN 15m ATR: no look-ahead) ---------
    def _fine_manage(self, i, c):
        cfg, p = self.cfg, self.pos
        if p is None: return
        d = p["dir"]
        r_now = (c - p["entry"]) * d / p["risk"]
        a_prev = self.P.atr_l[i - 1] if i > 0 else self.P.atr_l[i]
        if cfg.be_at_r is not None and not p["be_done"] and r_now >= cfg.be_at_r:
            be = p["entry"] + d * p["entry"] * (cfg.fee_maker + cfg.fee_taker) * 1.5
            self.next_stop = max(p["stop"], be) if d > 0 else min(p["stop"], be)
            p["be_done"] = True
        if cfg.trail_at_r is not None and r_now >= cfg.trail_at_r and np.isfinite(a_prev):
            t = c - d * cfg.trail_atr * a_prev
            cand = max(p["stop"], t) if d > 0 else min(p["stop"], t)
            self.next_stop = cand if self.next_stop is None else (
                max(self.next_stop, cand) if d > 0 else min(self.next_stop, cand))

    def _process_orders(self, i):
        cfg, P, S = self.cfg, self.P, self.S
        if self.pos is not None and self.next_stop is not None:
            self.pos["stop"] = self.next_stop; self.next_stop = None

        # session cancel BEFORE any fill: the order dies at the open of a blocked bar
        if self.pending is not None and S is not None and cfg.cancel_pending_outside_session \
                and not S.allow[i]:
            self.pending = None; self.state = "WAIT_TOUCH"; self.stats["session_cancels"] += 1

        use_fine = self.fine is not None and self.fine.mode[i] == 1
        if use_fine:
            s, e = self.fine.bounds(i); F = self.fine; self.stats["fine_bars"] += 1
        else:
            s, e = 0, 1; F = None; self.stats["coarse_bars"] += 1

        for j in range(s, e):
            if use_fine:
                t, o, h, l, c = F.ts[j], F.o[j], F.h[j], F.l[j], F.c[j]
            else:
                t, o, h, l, c = int(P.idx[i].value), P.o[i], P.h[i], P.l[i], P.c[i]
            self._now_ts = int(t)

            if use_fine and cfg.manage_on_fine and self.pos is not None and self.next_stop is not None:
                self.pos["stop"] = self.next_stop; self.next_stop = None

            if self.pending is not None and i >= self.pending["active_from"] \
                    and t >= self.pending["ready_ts"]:
                fp = self._fill_price(o, h, l)
                if fp is not None:
                    self._open(i, fp)
                    if self.pos is None: break
                    d = self.pos["dir"]
                    if (d > 0 and o <= self.pos["stop"]) or (d < 0 and o >= self.pos["stop"]):
                        self._close(i, o, "gap_stop", True); break

            if self.pos is not None:
                p = self.pos; d = p["dir"]
                hs = (l <= p["stop"]) if d > 0 else (h >= p["stop"])
                ht = (h >= p["target"]) if d > 0 else (l <= p["target"])
                hp = p["partial"] is not None and ((h >= p["partial"]) if d > 0 else (l <= p["partial"]))
                if hs and (ht or hp): self.stats["ambiguous"] += 1
                if hs:                                        # still conservative at 1m
                    self._close(i, p["stop"], "stop", True); break
                if hp: self._partial(i, p["partial"])
                if ht:
                    self._close(i, p["target"], "target", False); break

            if use_fine and cfg.manage_on_fine and self.pos is not None:
                self._fine_manage(i, c)

        if self.pending is not None:
            d, st = self.pending["dir"], self.pending["stop"]
            if i >= self.pending["expires"] or ((P.c[i] <= st) if d > 0 else (P.c[i] >= st)):
                self.pending = None; self.state = "WAIT_TOUCH"

    def _strategy(self, i):
        cfg, P, S = self.cfg, self.P, self.S
        if self.halted or i <= self.blocked_until: return
        if self.eq < self.day_eq * (1 - cfg.max_daily_loss_pct): return
        allow = (S.allow[i] if (S is not None and cfg.use_sessions) else True)

        a = int(P.act[i])
        if a != self.zone:
            self.zone, self.state, self.touch_i = a, "WAIT_TOUCH", -1
        if a < 0 or a in self.used: return
        d = int(P.htf_dir[a]); zlo, zhi = float(P.htf_lo[a]), float(P.htf_hi[a])
        zce = (zlo + zhi) / 2
        touch = (zce if cfg.htf_use_ce else zhi) if d > 0 else (zce if cfg.htf_use_ce else zlo)
        inval = zlo if d > 0 else zhi
        # invalidation ALWAYS evaluated, in or out of session
        if (d > 0 and P.c[i] <= inval) or (d < 0 and P.c[i] >= inval): return

        if self.state == "WAIT_FVG" and i > self.touch_i + cfg.max_wait_bars:
            self.state = "WAIT_TOUCH"
        if self.state == "WAIT_TOUCH":
            touched = (d > 0 and P.l[i] <= touch) or (d < 0 and P.h[i] >= touch)
            if touched and (allow or not cfg.gate_touch):
                self.state, self.touch_i = "WAIT_FVG", i
            else:
                return
        if self.state == "WAIT_FVG" and P.ltf_dir[i] == d and np.isfinite(P.ltf_lo[i]):
            if not allow:
                self.stats["session_blocks"] += 1; return
            al = float(P.atr_l[i]); llo, lhi = float(P.ltf_lo[i]), float(P.ltf_hi[i])
            if not relevant(d, llo, lhi, zlo, zhi, al, cfg): return
            st = build_setup(d, llo, lhi, zlo, zhi, al, cfg)
            if st is None: return
            entry, stop, target, risk = st
            if not setup_extra_ok(P, S, cfg, d, entry, stop, target, risk, i):
                self.stats["liquidity_blocks"] += 1; return
            self._sid_setup = int(S.sid[i]) if S is not None else 0
            self.pending = dict(dir=d, entry=entry, stop=stop, target=target, htf_id=a,
                                active_from=i + 1, expires=i + 1 + cfg.order_expiry_bars,
                                ready_ts=int(P.idx[i].value) + self._ltf_ns
                                         + int(cfg.entry_delay_s * 1e9))

    def _manage_on_close(self, i):
        super()._manage_on_close(i)
        cfg, S = self.cfg, self.S
        if self.pos is None or S is None or not cfg.flat_at_session_end: return
        if S.allow[i] and (i + 1 >= self.P.n or not S.allow[i + 1]):
            self._close(i, self.P.c[i], "session_flat", True)

    def run(self) -> pd.DataFrame:
        for k in self.stats: self.stats[k] = 0
        df = super().run()
        df.attrs["stats"] = dict(self.stats)
        return df


TAKER_REASONS.add("session_flat")


# ============================ 5. REPORTS & VALIDATION =========================
def parity_check_v2(P, cfg: ConfigV2, S=None, fine=None, tol=1e-6) -> bool:
    """Engines must agree when fine-resolution and management are disabled.
    Session gates stay ON — they are part of the parity contract now."""
    simple = replace(cfg, be_at_r=None, partial_at_r=None, partial_frac=0.0,
                     trail_at_r=None, min_notional=0.0, entry_delay_s=0.0,
                     manage_on_fine=False, flat_at_session_end=False,
                     max_daily_loss_pct=1.0, max_dd_stop_pct=1.0)
    v = backtest_vector_v2(P, simple, S)
    e = EventEngineV2(P, simple, fine=None, sess=S).run()
    ok = len(v) == len(e)
    if ok and len(v):
        for col in ("entry_i", "exit_i", "dir"):
            ok &= (v[col].values == e[col].values).all()
        for col in ("entry", "exit"):
            ok &= np.allclose(v[col].values, e[col].values, atol=tol, rtol=tol)
    print(f"[parity-v2] vector={len(v)} | event={len(e)} | MATCH={ok}")
    if not ok and len(v) and len(e):
        m = v.merge(e, on="entry_i", suffixes=("_v", "_e"), how="outer", indicator=True)
        print(m[m._merge != "both"].head(8)[["entry_i", "entry_time_v", "entry_time_e",
                                             "exit_i_v", "exit_i_e", "_merge"]].to_string())
    return bool(ok)


def execution_report(P, cfg: ConfigV2, S, fine: Optional[FineData]) -> pd.DataFrame:
    """How much was the conservative 'stop-first' assumption costing you?"""
    rows = []
    variants = [("15m coarse (stop-first)", None, False),
                ("1m resolved", fine, False),
                ("1m + 1-tick penetration", fine, False),
                ("1m + ticks + 200ms latency", fine, False)]
    for name, F, _ in variants:
        c = replace(cfg)
        if name.startswith("1m + 1-tick"): c = replace(cfg, fill_touch_ticks=1)
        if "latency" in name: c = replace(cfg, fill_touch_ticks=1, entry_delay_s=0.2)
        t = EventEngineV2(P, c, fine=F, sess=S).run()
        m = performance(t, P, c)
        st = t.attrs.get("stats", {})
        rows.append(dict(variant=name, trades=m.get("trades", 0),
                         ret_pct=m.get("total_return_pct", 0), pf=m.get("profit_factor", 0),
                         win_pct=m.get("win_rate_pct", 0), exp_r=m.get("expectancy_r", 0),
                         maxdd_pct=m.get("max_dd_pct", 0), sharpe=m.get("sharpe", 0),
                         ambiguous=st.get("ambiguous", 0)))
    return pd.DataFrame(rows)


def session_attribution(trades: pd.DataFrame) -> pd.DataFrame:
    """Which killzone actually pays? This is the whole point of upgrade #2."""
    if trades.empty or "sid_entry" not in trades: return pd.DataFrame()
    t = trades.copy()
    t["session"] = t.sid_entry.map(SESSION_NAMES).fillna("outside")
    g = t.groupby("session")
    out = pd.DataFrame(dict(
        trades=g.size(),
        win_pct=100 * g.apply(lambda x: (x.pnl > 0).mean(), include_groups=False),
        exp_r=g.r.mean(), total_r=g.r.sum(),
        avg_bars=g.bars.mean(),
        pf=g.apply(lambda x: x[x.pnl > 0].pnl.sum() / max(-x[x.pnl <= 0].pnl.sum(), 1e-9),
                   include_groups=False),
        net_pnl=g.pnl.sum()))
    return out.sort_values("total_r", ascending=False)


def session_sweep(P, base: ConfigV2, fine=None) -> pd.DataFrame:
    combos = [
        ("all_hours",      dict(use_sessions=False)),
        ("london_only",    dict(kz_london=True, kz_ny_am=False, kz_ny_pm=False)),
        ("ny_am_only",     dict(kz_london=False, kz_ny_am=True, kz_ny_pm=False)),
        ("london+ny_am",   dict(kz_london=True, kz_ny_am=True, kz_ny_pm=False)),
        ("london+ny_both", dict(kz_london=True, kz_ny_am=True, kz_ny_pm=True)),
        ("+no_weekend",    dict(kz_london=True, kz_ny_am=True, skip_weekends=True)),
        ("+asia_sweep",    dict(require_asia_sweep=True)),
        ("+block_obstacle",dict(block_obstacle=True)),
        ("+require_draw",  dict(require_draw=True)),
        ("+vol_filter",    dict(min_vol_ratio=0.8, min_atr_ratio=0.7)),
        ("+gate_touch",    dict(gate_touch=True)),
    ]
    rows = []
    for name, over in combos:
        c = replace(base, **over)
        S = SessionContext(P, c, verbose=False)
        t = EventEngineV2(P, c, fine=fine, sess=S).run()
        m = performance(t, P, c)
        rows.append(dict(variant=name, trades=m.get("trades", 0),
                         exp_r=m.get("expectancy_r", 0), pf=m.get("profit_factor", 0),
                         ret_pct=m.get("total_return_pct", 0), maxdd_pct=m.get("max_dd_pct", 0),
                         calmar=m.get("calmar", 0)))
    return pd.DataFrame(rows)


def walk_forward_v2(P_full: Prepared, raw_15m, base: ConfigV2, grid: List[Dict],
                    fine_df=None, train_bars=8000, test_bars=2000, embargo=96) -> pd.DataFrame:
    """FIXED: folds now inherit your real config (v1 silently reset it)."""
    out, start = [], 0
    n = len(raw_15m)
    while start + train_bars + embargo + test_bars <= n:
        tr = slice(start, start + train_bars)
        te = slice(start + train_bars + embargo, start + train_bars + embargo + test_bars)
        best, best_score = None, -np.inf
        Ptr = prepare(raw_15m.iloc[tr], base)
        for g in grid:
            c = replace(base, **g)
            S = SessionContext(Ptr, c, verbose=False)
            t = backtest_vector_v2(Ptr, c, S)
            if len(t) < 20: continue
            sc = performance(t, Ptr, c)["calmar"]
            if sc > best_score: best_score, best = sc, c
        if best is None:
            start += test_bars; continue
        Pte = prepare(raw_15m.iloc[te], base)
        S = SessionContext(Pte, best, verbose=False)
        F = FineData(fine_df, Pte, best, verbose=False) if fine_df is not None else None
        t = EventEngineV2(Pte, best, fine=F, sess=S).run()
        out.append(dict(test_start=Pte.idx[0], test_end=Pte.idx[-1],
                        params={k: getattr(best, k) for k in grid[0]},
                        **performance(t, Pte, best)))
        start += test_bars
    return pd.DataFrame(out)


# ============================ 6. DEMO =========================================
if __name__ == "__main__":
    pd.set_option("display.width", 200)
    cfg = ConfigV2()

    print("=== building consistent 1m -> 15m demo data (SYNTHETIC) ===")
    m1 = synthetic_1m(days=210)
    raw15 = build_ltf_from_fine(m1, cfg)
    P = prepare(raw15, cfg)
    P.vol = P.ltf.volume.values
    print(f"[data] 1m={len(m1):,} | 15m={P.n:,} | 4h={len(P.htf):,}")

    fine = FineData(m1, P, cfg)
    S = SessionContext(P, cfg)

    assert parity_check_v2(P, cfg, S), "ENGINES DISAGREE — fix before trusting numbers."

    print("\n=== #1 EXECUTION FIDELITY: what does resolving intrabar change? ===")
    print(execution_report(P, cfg, S, fine).to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    evt = EventEngineV2(P, cfg, fine=fine, sess=S).run()
    print("\n=== FINAL (1m + sessions + full management) ===")
    for k, v in performance(evt, P, cfg).items():
        print(f"  {k:>20}: {v:,.4f}" if isinstance(v, float) else f"  {k:>20}: {v}")
    print("  engine stats:", evt.attrs["stats"])

    print("\n=== #2 SESSION ATTRIBUTION: who pays, who bleeds ===")
    print(session_attribution(evt).to_string(float_format=lambda x: f"{x:,.3f}"))

    print("\n=== #2 FILTER ABLATION (event engine, 1m fills) ===")
    print(session_sweep(P, cfg, fine).to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\n=== MONTE CARLO ===")
    for k, v in monte_carlo(evt, cfg).items(): print(f"  {k:>22}: {v:,.4f}")

    evt.to_csv("trades_v2.csv", index=False)
    evt.attrs["curve"].to_csv("equity_v2.csv")
    print("\nSaved trades_v2.csv / equity_v2.csv")
