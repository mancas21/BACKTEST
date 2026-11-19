"""qwen50_engine.py — STRATEGIES 51-100 pack (2026-11-19 attachment, source of
record code/prompts_51_100.txt).

50 prompt-specified scalping/day-trading strategies (Qwen pack, ids 51-100):
40 crypto-perp cells (BTC/ETH/SOL/HYPE/SUI/JUP) + 10 equity-style cells on the
NVDAUSDT/SPCXUSDT perp tape with New York RTH masks (the s101 precedent).
Execution core is the audited p100_screen_engine.Book; this file adds only the
per-id signal layer. NO DATA refusals are declared, never silent.

DECLARED CONVENTIONS (every ambiguity resolution in one place)
  signal / fills : signal on the close of bar j, fill at the open of bar j+1
                   (Book). Opposite-side signal reverses at the same open.
  ties           : stop first (Book); gap-through stop fills at the open.
  entry ref      : ATR-multiple stops/targets are measured from the SIGNAL-BAR
                   close (the fill differs by the next open's gap; declared).
                   R-multiple / vwap / mid-band targets are set AT THE FILL
                   (exact) but become checkable from the bar AFTER the fill
                   (the Book's hook is the signal call of the entry bar).
  trailing       : strategies with a trailing stop ratchet the LIVE stop in
                   the wrapper (book.pos["stop"] updated on each bar close,
                   effective from the next bar; only tightened, never
                   loosened). Chandelier = extreme since entry minus mult x
                   ATR; highest CLOSE where the prompt says close (id 62),
                   highest HIGH otherwise (67/89/94).
  squeeze state  : ids 54/81 arm when the band-width percentile (rolling 200,
                   pandas rolling.rank) is under the threshold; the arm
                   persists until a band-break close (entry) or the percentile
                   exceeds 0.5 (reset).
  session VWAP   : UTC calendar day for crypto (typical price (h+l+c)/3,
                   volume-weighted, per-day reset). z of (close - vwap) is the
                   expanding within-session std, min_periods 20.
  equity cells   : NVDAUSDT/SPCXUSDT perp tape, RTH = 09:30-16:00
                   America/New_York on weekdays; prior-day H/L/C = the
                   previous RTH session on the perp tape; session VWAP from
                   the 09:30 bar; flat at the prompt's deadline (close at the
                   open of the first bar at/after the deadline); no weekend
                   sessions; one range-break entry per direction per day
                   (ORB) and one gap-fade per day (id 100).
  crypto flat    : "flat at 00:00 UTC" = close at the open of the first bar
                   of the next UTC day.
  costs          : AUTHOR-DECLARED where the prompt declares them --
                   BTC/ETH/SOL ids: 4 bps fee + 1 bp slip per side (10 bps
                   RT); HYPE/SUI/JUP ids: 5 bps fee + 2 bps slip per side
                   (14 bps RT). NVDA/SPCX ids: the prompts price in $/share,
                   undefined on a perp tape -> repo uniform 5 bps fee + 0.5
                   bps slip per side (11 bps RT), deviation declared.
  funding        : charged at real settlements for ALL eight symbols (funding
                   files exist for NVDAUSDT/SPCXUSDT too; deviation from
                   s101, which left them uncharged, declared).
  risk           : the prompts are silent -> house s101 convention: 0.5%
                   equity per trade, 3x leverage cap, INIT 10,000. No daily
                   trade caps (prompts silent; s101's pack rule #19 NOT
                   imposed).
  OOS            : 70/30 chronological, no purge; indicators warm up on the
                   full frame; the OOS book trades only from the split.
  timeframes     : 3m/30m cells resample in-engine from 1m/5m with the house
                   _resample (incomplete-edge bars dropped). "Full history
                   available" = the full file window on disk.
  windows/warmup : indicators need their lookback; no entries before the
                   warmup index (NaN-guarded), end-of-data force close (Book).
  performance    : ALL indicators and per-day structures are precomputed once
                   per pass in the signal factory (s101 pattern); the per-bar
                   closures only index arrays.
"""

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from p100_screen_engine import (  # noqa: E402
    Book, book_metrics)

ENGINE_VERSION = "qwen50-1"
INIT = 10_000.0
RISK = 0.005
MAXLEV = 3.0

COST_BTC_ETH_SOL = (0.0004, 0.0001)   # "0.04% per side, 1 bp slippage"
COST_HYPE_SUI_JUP = (0.0005, 0.0002)  # "0.05% per side, 2 bp slippage"
COST_EQUITY_PERP = (0.0005, 0.0005)   # $/share undefined on perp -> repo
SYMBOL_COST = {
    "BTCUSDT": COST_BTC_ETH_SOL, "ETHUSDT": COST_BTC_ETH_SOL,
    "SOLUSDT": COST_BTC_ETH_SOL,
    "HYPEUSDT": COST_HYPE_SUI_JUP, "SUIUSDT": COST_HYPE_SUI_JUP,
    "JUPUSDT": COST_HYPE_SUI_JUP,
    "NVDAUSDT": COST_EQUITY_PERP, "SPCXUSDT": COST_EQUITY_PERP,
}

# id -> (symbol, tf_label, tf_minutes, src_tf)
CELLS = {
    51: ("BTCUSDT", "5m", 5, "5m"),   52: ("BTCUSDT", "15m", 15, "15m"),
    53: ("BTCUSDT", "1m", 1, "1m"),   54: ("BTCUSDT", "3m", 3, "1m"),
    55: ("BTCUSDT", "30m", 30, "5m"), 56: ("BTCUSDT", "5m", 5, "5m"),
    57: ("BTCUSDT", "15m", 15, "15m"), 58: ("BTCUSDT", "15m", 15, "15m"),
    59: ("ETHUSDT", "5m", 5, "5m"),   60: ("ETHUSDT", "3m", 3, "1m"),
    61: ("ETHUSDT", "15m", 15, "15m"), 62: ("ETHUSDT", "5m", 5, "5m"),
    63: ("ETHUSDT", "1m", 1, "1m"),   64: ("ETHUSDT", "30m", 30, "5m"),
    65: ("ETHUSDT", "15m", 15, "15m"),
    66: ("SOLUSDT", "5m", 5, "5m"),   67: ("SOLUSDT", "15m", 15, "15m"),
    68: ("SOLUSDT", "1m", 1, "1m"),   69: ("SOLUSDT", "3m", 3, "1m"),
    70: ("SOLUSDT", "5m", 5, "5m"),   71: ("SOLUSDT", "15m", 15, "15m"),
    72: ("SOLUSDT", "30m", 30, "5m"),
    73: ("HYPEUSDT", "15m", 15, "15m"), 74: ("HYPEUSDT", "3m", 3, "1m"),
    75: ("HYPEUSDT", "5m", 5, "5m"),  76: ("HYPEUSDT", "1m", 1, "1m"),
    77: ("HYPEUSDT", "15m", 15, "15m"), 78: ("HYPEUSDT", "30m", 30, "5m"),
    79: ("SUIUSDT", "5m", 5, "5m"),   80: ("SUIUSDT", "1m", 1, "1m"),
    81: ("SUIUSDT", "15m", 15, "15m"), 82: ("SUIUSDT", "5m", 5, "5m"),
    83: ("SUIUSDT", "30m", 30, "5m"), 84: ("SUIUSDT", "3m", 3, "1m"),
    85: ("JUPUSDT", "15m", 15, "15m"), 86: ("JUPUSDT", "1m", 1, "1m"),
    87: ("JUPUSDT", "5m", 5, "5m"),   88: ("JUPUSDT", "15m", 15, "15m"),
    89: ("JUPUSDT", "30m", 30, "5m"), 90: ("JUPUSDT", "5m", 5, "5m"),
    91: ("NVDAUSDT", "5m", 5, "5m"),  92: ("NVDAUSDT", "5m", 5, "5m"),
    94: ("NVDAUSDT", "15m", 15, "15m"), 95: ("NVDAUSDT", "15m", 15, "15m"),
    96: ("SPCXUSDT", "15m", 15, "15m"), 97: ("SPCXUSDT", "5m", 5, "5m"),
    99: ("SPCXUSDT", "30m", 30, "5m"), 100: ("SPCXUSDT", "5m", 5, "5m"),
}

NO_DATA = {
    93: "no NVDA 1m series (3m resample needs it)",
    98: "no SPCX 1m series",
}

EQUITY_SYMS = ("NVDAUSDT", "SPCXUSDT")
# crypto ids whose prompt declares "flat at 00:00 UTC"
FLAT_UTC = {56, 65, 70, 78, 84}


# ─────────────────────────── indicators ───────────────────────────────────
def _atr(h, l, c, n=14):
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return pd.Series(tr).ewm(alpha=1 / n, adjust=False, min_periods=n).mean().values


def _ema(a, n):
    return pd.Series(a).ewm(span=n, adjust=False, min_periods=n).mean().values


def _sma(a, n):
    return pd.Series(a).rolling(n, min_periods=n).mean().values


def _roll_max(a, w):
    return pd.Series(a).rolling(w).max().values


def _roll_min(a, w):
    return pd.Series(a).rolling(w).min().values


def _roll_mean(a, w):
    return pd.Series(a).rolling(w, min_periods=w).mean().values


def _roll_std(a, w):
    return pd.Series(a).rolling(w, min_periods=w).std(ddof=0).values


def _rsi(c, n=14):
    d = np.diff(c, prepend=c[0])
    up = np.where(d > 0, d, 0.0)
    dn = np.where(d < 0, -d, 0.0)
    ru = pd.Series(up).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rd = pd.Series(dn).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = ru / rd.replace(0.0, np.nan)
    return (100 - 100 / (1 + rs)).bfill().values


def _adx(h, l, c, n=14):
    ph = np.r_[h[0], h[:-1]]
    pl = np.r_[l[0], l[:-1]]
    pc = np.r_[c[0], c[:-1]]
    plus_dm = np.where((h - ph) > (pl - l), np.maximum(h - ph, 0.0), 0.0)
    minus_dm = np.where((pl - l) > (h - ph), np.maximum(pl - l, 0.0), 0.0)
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    atr = pd.Series(tr).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    pdi = 100 * pd.Series(plus_dm).ewm(alpha=1 / n, adjust=False,
                                       min_periods=n).mean() / atr
    mdi = 100 * pd.Series(minus_dm).ewm(alpha=1 / n, adjust=False,
                                        min_periods=n).mean() / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0.0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False, min_periods=n).mean().bfill().values


def _macd(c, fast=12, slow=26, sig=9):
    ef = pd.Series(c).ewm(span=fast, adjust=False, min_periods=fast).mean()
    es = pd.Series(c).ewm(span=slow, adjust=False, min_periods=slow).mean()
    line = ef - es
    signal = line.ewm(span=sig, adjust=False, min_periods=sig).mean()
    return line.values, signal.values, (line - signal).values


def _bollinger(c, n=20, k=2.0):
    mid = _sma(c, n)
    sd = _roll_std(c, n)
    return mid - k * sd, mid, mid + k * sd


def _keltner(h, l, c, n=20, mult=1.5):
    mid = _ema(c, n)
    a = _atr(h, l, c, n)
    return mid - mult * a, mid, mid + mult * a


def _stoch(h, l, c, n=14, k_s=3, d_s=3):
    hh = _roll_max(h, n)
    ll = _roll_min(l, n)
    raw = 100 * (c - ll) / np.where(hh - ll == 0, np.nan, hh - ll)
    k = pd.Series(raw).rolling(k_s, min_periods=k_s).mean()
    d = k.rolling(d_s, min_periods=d_s).mean()
    return k.bfill().values, d.bfill().values


def _stoch_rsi(c, rsi_n=14, stoch_n=14, k_s=3, d_s=3):
    r = pd.Series(_rsi(c, rsi_n))
    lo = r.rolling(stoch_n, min_periods=stoch_n).min()
    hi = r.rolling(stoch_n, min_periods=stoch_n).max()
    raw = 100 * (r - lo) / (hi - lo).replace(0.0, np.nan)
    k = raw.rolling(k_s, min_periods=k_s).mean()
    d = k.rolling(d_s, min_periods=d_s).mean()
    return k.bfill().values, d.bfill().values


def _supertrend(h, l, c, n=10, mult=3.0):
    a = _atr(h, l, c, n)
    hl2 = (h + l) / 2.0
    ub = hl2 + mult * a
    lb = hl2 - mult * a
    n_ = len(c)
    dirn = np.ones(n_, dtype=int)
    fu = np.full(n_, np.nan)
    fl = np.full(n_, np.nan)
    finite = np.where(np.isfinite(a))[0]
    if not len(finite):
        return dirn
    start = int(finite[0])
    fu[start] = ub[start]
    fl[start] = lb[start]
    for i in range(start + 1, n_):
        fu[i] = ub[i] if (ub[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lb[i] if (lb[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        if dirn[i - 1] == 1:
            dirn[i] = -1 if c[i] < fl[i] else 1
        else:
            dirn[i] = 1 if c[i] > fu[i] else -1
    return dirn


def _psar(h, l, c, af0=0.02, amax=0.2):
    n_ = len(h)
    sar = np.full(n_, np.nan)
    bull = True
    ep = h[0]
    af = af0
    sar[0] = l[0]
    for i in range(1, n_):
        nxt = sar[i - 1] + af * (ep - sar[i - 1])
        if bull:
            nxt = min(nxt, l[i - 1], l[i - 2] if i > 1 else l[i - 1])
            if l[i] < nxt:
                bull, nxt, ep, af = False, ep, l[i], af0
            elif h[i] > ep:
                ep, af = h[i], min(amax, af + af0)
        else:
            nxt = max(nxt, h[i - 1], h[i - 2] if i > 1 else h[i - 1])
            if h[i] > nxt:
                bull, nxt, ep, af = True, ep, h[i], af0
            elif l[i] < ep:
                ep, af = l[i], min(amax, af + af0)
        sar[i] = nxt
    dirn = np.where(sar < c, 1, -1)
    flip = np.zeros(n_, dtype=int)
    flip[1:] = np.diff(dirn)
    return dirn, flip


def _ichimoku_cloud(h, l, t=9, k=26, s=52):
    tenkan = (pd.Series(h).rolling(t).max() + pd.Series(l).rolling(t).min()) / 2
    kijun = (pd.Series(h).rolling(k).max() + pd.Series(l).rolling(k).min()) / 2
    span_a = ((tenkan + kijun) / 2).shift(k)
    span_b = ((pd.Series(h).rolling(s).max()
               + pd.Series(l).rolling(s).min()) / 2).shift(k)
    top = pd.concat([span_a, span_b], axis=1).max(axis=1)
    bot = pd.concat([span_a, span_b], axis=1).min(axis=1)
    return top.bfill().values, bot.bfill().values


def _roll_pctile(a, w):
    return pd.Series(a).rolling(w, min_periods=w).rank(pct=True).values


def _day_id(ms):
    return (ms // 86_400_000).astype(int)


def _day_anchors(ms, h, l, o, day_ids=None):
    d = day_ids if day_ids is not None else _day_id(ms)
    n_ = len(ms)
    pdh = np.full(n_, np.nan)
    pdl = np.full(n_, np.nan)
    do_ = np.full(n_, np.nan)
    dh, dl, first = {}, {}, {}
    cur = None
    for i in range(n_):
        dd = d[i]
        if dd < 0:  # equity sentinel: bar outside any RTH session
            pdh[i] = np.nan
            pdl[i] = np.nan
            do_[i] = np.nan
            continue
        if dd != cur:
            pdh[i] = dh.get(dd - 1, np.nan)
            pdl[i] = dl.get(dd - 1, np.nan)
            dh[dd] = -np.inf
            dl[dd] = np.inf
            cur = dd
        else:
            pdh[i] = dh.get(dd - 1, np.nan)
            pdl[i] = dl.get(dd - 1, np.nan)
        if dd not in first:
            first[dd] = o[i]
        do_[i] = first[dd]
        dh[dd] = max(dh[dd], h[i])
        dl[dd] = min(dl[dd], l[i])
    return pdh, pdl, do_


def _vwap_session(ms, h, l, c, v, day_ids=None):
    d = day_ids if day_ids is not None else _day_id(ms)
    typ = (h + l + c) / 3.0
    pv = typ * v
    out = np.full(len(ms), np.nan)
    cv = cp = 0.0
    cur = None
    for i in range(len(ms)):
        if d[i] != cur:
            cur, cv, cp = d[i], 0.0, 0.0
        cv += v[i]
        cp += pv[i]
        out[i] = cp / cv if cv > 0 else np.nan
    return out


def _resample(df, rule):
    agg = {"open": "first", "high": "max", "low": "min", "close": "last",
           "volume": "sum"}
    g = (df.set_index("timestamp").resample(rule, label="left", closed="left")
         .agg(agg))
    cnt = (df.set_index("timestamp")["close"]
           .resample(rule, label="left", closed="left").count())
    ok = cnt.reindex(g.index).values == cnt.mode().iloc[0]
    return g[ok].dropna(subset=["open"]).reset_index()


def _session_ranges(ms, h, l, day, day_ids, start_min, end_min, mins=None):
    """Per-session-id (high, low) over [start_min, end_min) of each day.
    The window is in ET minutes-of-day when `mins` (ET minute array) is
    given (equity cells), else UTC milliseconds-of-day (crypto).
    One pass over the arrays; returns dict sid -> (hi, lo)."""
    out = {}
    d = day_ids if day_ids is not None else _day_id(ms)
    if mins is not None:
        m = (mins >= start_min) & (mins < end_min)
    else:
        dm = ms % 86_400_000
        m = (dm >= start_min * 60_000) & (dm < end_min * 60_000)
    idx = np.where(m)[0]
    for i in idx:
        sid = d[i]
        e = out.get(sid)
        if e is None:
            out[sid] = [h[i], l[i]]
        else:
            e[0] = max(e[0], h[i])
            e[1] = min(e[1], l[i])
    return out


def _rth_session_close(ms, c, sess):
    """Previous RTH session's last close, carried on each bar."""
    d = _day_id(ms)
    last_by_day = {}
    for i in np.where(sess)[0]:
        last_by_day[d[i]] = c[i]
    out = np.full(len(ms), np.nan)
    cur = -1
    prev = np.nan
    for i in np.where(sess)[0]:
        dd = d[i]
        if dd != cur:
            prev = last_by_day.get(dd - 1, np.nan)
            cur = dd
        out[i] = prev
    return out


# ─────────────────────────── frames ───────────────────────────────────────
def _pick(paths, suffix):
    return [p for p in paths
            if os.path.basename(p).endswith("_" + suffix + ".csv")]


def _frame_from(path):
    df = pd.read_csv(path)
    df.columns = [str(cc).strip().lower() for cc in df.columns]
    ts_col = "open_ts" if "open_ts" in df.columns else "timestamp"
    df["timestamp"] = pd.to_datetime(df[ts_col], unit="ms", utc=True)
    df = df.sort_values("timestamp").drop_duplicates("timestamp")
    return df.reset_index(drop=True)


def build_frame(idn, paths):
    sym, tf_label, tf_minutes, src_tf = CELLS[idn]
    f = _pick(paths, src_tf)
    if not f:
        raise ValueError(f"NO DATA: {idn}: no {sym} {src_tf} file in inputs")
    main = _frame_from(f[0])
    if tf_minutes != {"1m": 1, "5m": 5, "15m": 15}[src_tf]:
        main = _resample(main, f"{tf_minutes}min")
    aux = {}
    if idn == 64:
        fb = [x for x in paths if "BTCUSDT_5m" in os.path.basename(x)]
        if not fb:
            raise ValueError("NO DATA: 64: no BTCUSDT_5m companion in inputs")
        aux["BTCUSDT_30m"] = _resample(_frame_from(fb[0]), "30min")
    if idn in (60, 82):
        f1h = _pick(paths, "1h")
        if not f1h:
            raise ValueError(f"NO DATA: {idn}: no {sym}_1h file in inputs")
        aux["_1h"] = _frame_from(f1h[0])
    return main, aux


def _prepare_main(df):
    df = df.copy()
    ts = df["timestamp"]
    if ts.dt.tz is None:
        ts = ts.dt.tz_localize("UTC")
    df["timestamp"] = ts.dt.tz_convert("UTC")
    if "volume" not in df:
        df["volume"] = 0.0
    return df.reset_index(drop=True)


def _align_last(main, aux_df):
    """Per main bar: (aux ms, aux close) of the last aux bar at/before it."""
    ms_m = _ms(main["timestamp"])
    ms_a = _ms(aux_df["timestamp"])
    idx = np.searchsorted(ms_a, ms_m, side="right") - 1
    idx = np.clip(idx, 0, len(ms_a) - 1)
    return ms_a[idx], aux_df["close"].to_numpy(float)[idx]


def _ms(ts):
    return (ts.dt.tz_convert("UTC").dt.tz_localize(None).to_numpy()
            .astype("datetime64[ms]").astype("int64"))


# ─────────────────────────── signal layer ─────────────────────────────────
def _make_sig(idn, main, aux, symbol, book):
    """sig(j) -> None | entry dict | flat dict. Entries fill at open of j+1;
    trailing / target management mutates book.pos (ratchet only)."""
    o = main["open"].to_numpy(float)
    h = main["high"].to_numpy(float)
    l = main["low"].to_numpy(float)
    c = main["close"].to_numpy(float)
    v = main["volume"].to_numpy(float)
    ts = main["timestamp"]
    ms = _ms(ts)
    n = len(c)
    tf_minutes = CELLS[idn][2]
    a14 = _atr(h, l, c, 14)
    is_eq = symbol in EQUITY_SYMS
    warm = 210

    if is_eq:
        rth, sess = _rth_masks(ts)
        pdh, pdl, do_ = _day_anchors(ms, h, l, o, day_ids=sess)
        vwap = _vwap_session(ms, h, l, c, v, day_ids=sess)
        _, mins, _ = _ny_parts(ts)
        FLAT_MIN = {91: 955}.get(idn, 960)
        prev_close = _rth_session_close(ms, c, sess)
    else:
        pdh, pdl, do_ = _day_anchors(ms, h, l, o)
        vwap = _vwap_session(ms, h, l, c, v)
        FLAT_MIN = None
    day = _day_id(ms)
    dm = ms % 86_400_000
    tf_ms = tf_minutes * 60_000

    def flat_deadline_hit(j):
        """True when bar j+1 is the session-flat bar."""
        if j + 1 >= n:
            return True
        if is_eq:
            return mins[j + 1] >= FLAT_MIN or not rth[j + 1]
        return dm[j + 1] < tf_ms  # first bar of the next UTC day

    def session_ok(j):
        if j + 1 >= n:
            return False
        if is_eq:
            return bool(rth[j + 1]) and mins[j + 1] < FLAT_MIN
        if idn in FLAT_UTC and dm[j + 1] < tf_ms:
            return False  # fill would land on the flat bar
        return True

    def set_stop(stop_px):
        p = book.pos
        if p is None:
            return
        if p["side"] == 1:
            p["stop"] = max(p["stop"], stop_px)
        else:
            p["stop"] = min(p["stop"], stop_px)

    st = {}

    # ── precompute per-id indicator arrays / day structures ────────────────
    I = {}
    if idn in (51, 66):
        I["e20"] = _ema(c, 20)
        I["e50"] = _ema(c, 50)
    if idn == 51:
        I["e50"] = _ema(c, 50)
    if idn == 66:
        I["e100"] = _ema(c, 100)
    if idn in (52, 78):
        I["adx"] = _adx(h, l, c)
    if idn == 52:
        I["dh20"] = _roll_max(h, 20)
        I["dl20"] = _roll_min(l, 20)
    if idn == 78:
        I["dh20"] = _roll_max(h, 20)
        I["dl20"] = _roll_min(l, 20)
    if idn in (53, 68, 86):
        I["e200"] = _ema(c, 200)
        I["r2"] = _rsi(c, 2)
    if idn in (54, 81):
        lo_b, mid_b, up_b = _bollinger(c)
        I["lo_b"], I["mid_b"], I["up_b"] = lo_b, mid_b, up_b
        I["pct"] = _roll_pctile((up_b - mid_b) / mid_b, 200)
    if idn == 55:
        I["st"] = _supertrend(h, l, c)
        I["hist"] = _macd(c)[2]
    if idn in (56, 76):
        I["vwap_sd"] = pd.Series(c - vwap).expanding(min_periods=20) \
            .std(ddof=0).values
    if idn == 56:
        I["r14"] = _rsi(c, 14)
    if idn == 57:
        I["e9"], I["e21"], I["e200"] = _ema(c, 9), _ema(c, 21), _ema(c, 200)
    if idn in (71,):
        I["e21"] = _ema(c, 21)
    if idn == 76:
        I["r2"] = _rsi(c, 2)
    if idn == 58:
        I["rng"] = _session_ranges(ms, h, l, day, None, 0, 420)
    if idn == 59:
        I["roc"] = pd.Series(c).pct_change(10).values
        I["pct"] = _roll_pctile(I["roc"], 500)
    if idn == 60:
        I["e200_1h"] = _ema(aux["_1h_close_aligned"], 200)
        lo_b, mid_b, _ = _bollinger(c)
        I["lo_b"], I["mid_b"] = lo_b, mid_b
        I["r14"] = _rsi(c, 14)
    if idn == 61:
        I["st"] = _supertrend(h, l, c)
        I["adx"] = _adx(h, l, c)
    if idn == 62:
        _, I["kcmid"], I["kch"] = _keltner(h, l, c, 20, 1.5)
        _, _, I["kcl"] = _keltner(h, l, c, 20, 1.5)
        I["vavg"] = _roll_mean(v, 20)
    if idn == 63:
        I["k"], I["d"] = _stoch(h, l, c)
        I["e200"] = _ema(c, 200)
    if idn == 64:
        I["ratio_e50"] = _ema(aux["ratio"], 50)
        I["hh20"] = _roll_max(h, 20)
        I["ll20"] = _roll_min(l, 20)
    if idn == 65:
        I["adx"] = _adx(h, l, c)
        I["r14"] = _rsi(c, 14)
    if idn == 67:
        I["dh55"] = _roll_max(h, 55)
        I["dl55"] = _roll_min(l, 55)
        I["aavg"] = _roll_mean(a14, 20)
    if idn == 69:
        I["hist"] = _macd(c)[2]
        I["vavg"] = _roll_mean(v, 20)
    if idn == 70:
        I["above"] = c - vwap
    if idn == 84:
        I["above"] = c - vwap  # precomputed: the entry closure slices it
    if idn == 71:
        I["hh10"] = _roll_max(h, 10)
        I["ll10"] = _roll_min(l, 10)
        I["aavg"] = _roll_mean(a14, 50)
    if idn == 72:
        I["dirn"], I["flip"] = _psar(h, l, c)
        I["e200"] = _ema(c, 200)
    if idn == 73:
        I["st"] = _supertrend(h, l, c)
        I["adx"] = _adx(h, l, c)
    if idn == 74:
        lo_b, mid_b, up_b = _bollinger(c)
        I["lo_b"], I["mid_b"], I["up_b"] = lo_b, mid_b, up_b
        I["adx"] = _adx(h, l, c)
    if idn == 75:
        I["vavg"] = _roll_mean(v, 20)
    if idn == 77:
        I["e20"], I["e50"] = _ema(c, 20), _ema(c, 50)
        I["roc"] = pd.Series(c).pct_change(10).values
    if idn in (79,):
        I["e9"], I["e21"], I["e200"] = _ema(c, 9), _ema(c, 21), _ema(c, 200)
    if idn == 80:
        I["k"], I["d"] = _stoch_rsi(c)
        I["e200"] = _ema(c, 200)
    if idn == 82:
        I["e50_1h"] = _ema(aux["_1h_close_aligned"], 50)
        lo_b, mid_b, _ = _bollinger(c)
        I["lo_b"], I["mid_b"] = lo_b, mid_b
        I["r14"] = _rsi(c, 14)
    if idn == 83:
        I["cloud_top"], I["cloud_bot"] = _ichimoku_cloud(h, l)
        I["hh26"] = _roll_max(h, 26)
        I["ll26"] = _roll_min(l, 26)
    if idn == 85:
        I["st"] = _supertrend(h, l, c)
        I["e50"] = _ema(c, 50)
    if idn == 87:
        I["dh20"] = _roll_max(h, 20)
        I["dl20"] = _roll_min(l, 20)
        I["vavg"] = _roll_mean(v, 20)
    if idn == 88:
        I["kcl"], I["kcmid"], I["kch"] = _keltner(h, l, c, 20, 2.0)
        I["adx"] = _adx(h, l, c)
    if idn == 89:
        line, sig_l, _ = _macd(c)
        I["line"], I["sig"] = line, sig_l
        I["adx"] = _adx(h, l, c)
    if idn == 91:
        I["orb"] = _session_ranges(ms, h, l, day, sess, 570, 585, mins=mins)
        I["vavg"] = _roll_mean(v, 20)
    if idn == 92:
        I["e9"] = _ema(c, 9)
    if idn == 94:
        I["vavg"] = _roll_mean(v, 20)
    if idn == 95:
        lo_b, mid_b, up_b = _bollinger(c)
        I["lo_b"], I["mid_b"], I["up_b"] = lo_b, mid_b, up_b
        I["adx"] = _adx(h, l, c)
    if idn == 96:
        I["orb"] = _session_ranges(ms, h, l, day, sess, 570, 600, mins=mins)
    if idn == 97:
        I["st"] = _supertrend(h, l, c)
    if idn == 99:
        I["e20"], I["e50"] = _ema(c, 20), _ema(c, 50)
        I["adx"] = _adx(h, l, c)
    if idn == 100:
        I["orb15"] = _session_ranges(ms, h, l, day, sess, 570, 585, mins=mins)

    # ---- per-id entry conditions (only when flat) -------------------------
    def entry(j):
        if j < warm or j + 1 >= n:
            return None
        if not session_ok(j):
            return None
        a = a14[j]
        if not np.isfinite(a) or a <= 0:
            return None

        if idn == 51:
            e20, e50 = I["e20"], I["e50"]
            if e50[j] > e50[j - 1] and l[j] <= e20[j] and c[j] > o[j] \
                    and c[j] > e20[j]:
                return dict(side=1, stop_px=c[j] - 1.5 * a, tp_px=c[j] + 3 * a)
            if e50[j] < e50[j - 1] and h[j] >= e20[j] and c[j] < o[j] \
                    and c[j] < e20[j]:
                return dict(side=-1, stop_px=c[j] + 1.5 * a, tp_px=c[j] - 3 * a)
            return None

        if idn == 52:
            if I["adx"][j] > 20:
                dh, dl = I["dh20"][j - 1], I["dl20"][j - 1]
                if c[j] > dh:
                    return dict(side=1, stop_px=c[j] - 2 * a,
                                tp_px=c[j] + 4 * a)
                if c[j] < dl:
                    return dict(side=-1, stop_px=c[j] + 2 * a,
                                tp_px=c[j] - 4 * a)
            return None

        if idn == 53:
            if c[j] > I["e200"][j] and I["r2"][j] < 10:
                return dict(side=1, stop_px=c[j] - 1 * a, tp_px=None,
                            max_hold=15, exit_rsi=60)
            return None

        if idn in (54, 81):
            pct = I["pct"][j]
            if not np.isfinite(pct):
                return None
            thr = 0.20 if idn == 54 else 0.15
            armed = st.get("armed", False)
            if pct <= thr:
                st["armed"] = True
                armed = True
            elif pct > 0.5:
                st["armed"] = False
                return None
            if not armed:
                return None
            tpk = 2.5 if idn == 54 else 3.0
            if c[j] > I["up_b"][j]:
                st["armed"] = False
                return dict(side=1, stop_px=c[j] - 1.5 * a,
                            tp_px=c[j] + tpk * a)
            if c[j] < I["lo_b"][j]:
                st["armed"] = False
                return dict(side=-1, stop_px=c[j] + 1.5 * a,
                            tp_px=c[j] - tpk * a)
            return None

        if idn == 55:
            dirn, hist = I["st"], I["hist"]
            up = dirn[j] == 1 and hist[j] > 0
            dn = dirn[j] == -1 and hist[j] < 0
            pu = dirn[j - 1] == 1 and hist[j - 1] > 0
            pdn = dirn[j - 1] == -1 and hist[j - 1] < 0
            if up and not pu:
                return dict(side=1, stop_px=c[j] - 2 * a, tp_px=c[j] + 3 * a)
            if dn and not pdn:
                return dict(side=-1, stop_px=c[j] + 2 * a, tp_px=c[j] - 3 * a)
            return None

        if idn == 56:
            vw, sd, r14 = vwap[j], I["vwap_sd"][j], I["r14"][j]
            if np.isfinite(vw) and np.isfinite(sd):
                if c[j] <= vw - 2 * sd and r14 < 30:
                    return dict(side=1, stop_px=c[j] - 1.5 * a, tp_at="vwap")
                if c[j] >= vw + 2 * sd and r14 > 70:
                    return dict(side=-1, stop_px=c[j] + 1.5 * a, tp_at="vwap")
            return None

        if idn == 57:
            e9, e21, e200 = I["e9"], I["e21"], I["e200"]
            cross_up = e9[j] > e21[j] and e9[j - 1] <= e21[j - 1]
            cross_dn = e9[j] < e21[j] and e9[j - 1] >= e21[j - 1]
            if cross_up and c[j] > e200[j]:
                return dict(side=1, stop_px=c[j] - 2 * a, tp_px=c[j] + 3 * a,
                            trail="ema21_r")
            if cross_dn and c[j] < e200[j]:
                return dict(side=-1, stop_px=c[j] + 2 * a, tp_px=c[j] - 3 * a,
                            trail="ema21_r")
            return None

        if idn == 58:
            sid = day[j]
            if dm[j] < 7 * 3_600_000 or dm[j] >= 21 * 3_600_000:
                return None
            rr = I["rng"].get(sid)
            if not rr:
                return None
            rh, rl = rr
            if not st.get(("dl", sid)) and c[j] > rh:
                st[("dl", sid)] = True
                return dict(side=1, stop_px=max(rl, c[j] - 1.5 * a),
                            tp_px=None, r_tp=2.0)
            if not st.get(("ds", sid)) and c[j] < rl:
                st[("ds", sid)] = True
                return dict(side=-1, stop_px=min(rh, c[j] + 1.5 * a),
                            tp_px=None, r_tp=2.0)
            return None

        if idn == 59:
            pct, vw = I["pct"][j], vwap[j]
            if not (np.isfinite(pct) and np.isfinite(vw)):
                return None
            if pct >= 0.9 and c[j] > vw:
                return dict(side=1, stop_px=c[j] - 1.5 * a, tp_px=c[j] + 2 * a)
            if pct <= 0.1 and c[j] < vw:
                return dict(side=-1, stop_px=c[j] + 1.5 * a,
                            tp_px=c[j] - 2 * a)
            return None

        if idn == 60:
            if l[j] <= I["lo_b"][j] and I["r14"][j] < 30 \
                    and c[j] > I["e200_1h"][j]:
                return dict(side=1, stop_px=c[j] - 1.2 * a, tp_at="mid")
            return None

        if idn == 61:
            if I["adx"][j] > 25:
                dirn = I["st"]
                if dirn[j] == 1 and dirn[j - 1] != 1:
                    return dict(side=1, stop_px=c[j] - 2 * a,
                                tp_px=c[j] + 4 * a)
                if dirn[j] == -1 and dirn[j - 1] != -1:
                    return dict(side=-1, stop_px=c[j] + 2 * a,
                                tp_px=c[j] - 4 * a)
            return None

        if idn == 62:
            va = I["vavg"]
            if j >= 20 and np.isfinite(va[j - 1]) and v[j] > 1.5 * va[j - 1]:
                if c[j] > I["kch"][j]:
                    return dict(side=1, stop_px=c[j] - 1.5 * a,
                                tp_px=c[j] + 3 * a, trail="chand_close")
                if c[j] < I["kcl"][j]:
                    return dict(side=-1, stop_px=c[j] + 1.5 * a,
                                tp_px=c[j] - 3 * a, trail="chand_close")
            return None

        if idn == 63:
            k, d = I["k"], I["d"]
            ku = k[j] > d[j] and k[j - 1] <= d[j - 1] and k[j - 1] < 20
            kd = k[j] < d[j] and k[j - 1] >= d[j - 1] and k[j - 1] > 80
            if ku and c[j] > I["e200"][j]:
                return dict(side=1, stop_px=c[j] - 0.8 * a,
                            tp_px=c[j] + 1.2 * a, max_hold=10)
            if kd and c[j] < I["e200"][j]:
                return dict(side=-1, stop_px=c[j] + 0.8 * a,
                            tp_px=c[j] - 1.2 * a, max_hold=10)
            return None

        if idn == 64:
            ratio = aux["ratio"]
            if j >= 20:
                if ratio[j] > I["ratio_e50"][j] and c[j] > I["hh20"][j - 1]:
                    return dict(side=1, stop_px=c[j] - 2 * a,
                                tp_px=c[j] + 3 * a)
                if ratio[j] < I["ratio_e50"][j] and c[j] < I["ll20"][j - 1]:
                    return dict(side=-1, stop_px=c[j] + 2 * a,
                                tp_px=c[j] - 3 * a)
            return None

        if idn == 65:
            if I["adx"][j] < 20 and np.isfinite(pdh[j]) and np.isfinite(pdl[j]):
                r14 = I["r14"][j]
                if l[j] <= pdl[j] and r14 < 30:
                    return dict(side=1, stop_px=pdl[j] - 1 * a,
                                tp_px=(pdh[j] + pdl[j]) / 2)
                if h[j] >= pdh[j] and r14 > 70:
                    return dict(side=-1, stop_px=pdh[j] + 1 * a,
                                tp_px=(pdh[j] + pdl[j]) / 2)
            return None

        if idn == 66:
            e20, e50, e100 = I["e20"], I["e50"], I["e100"]
            if e20[j] > e50[j] > e100[j] and l[j] <= e20[j] and c[j] > e20[j]:
                return dict(side=1, stop_px=c[j] - 1.5 * a, tp_px=c[j] + 3 * a)
            if e20[j] < e50[j] < e100[j] and h[j] >= e20[j] and c[j] < e20[j]:
                return dict(side=-1, stop_px=c[j] + 1.5 * a,
                            tp_px=c[j] - 3 * a)
            return None

        if idn == 67:
            aa = I["aavg"]
            if j >= 55 and np.isfinite(aa[j - 1]) and a14[j] > aa[j - 1]:
                if c[j] > I["dh55"][j - 1]:
                    return dict(side=1, stop_px=c[j] - 2 * a,
                                tp_px=c[j] + 4 * a, trail="chand_high")
                if c[j] < I["dl55"][j - 1]:
                    return dict(side=-1, stop_px=c[j] + 2 * a,
                                tp_px=c[j] - 4 * a, trail="chand_high")
            return None

        if idn == 68:
            if c[j] > I["e200"][j] and I["r2"][j] < 5:
                return dict(side=1, stop_px=c[j] - 1 * a, tp_px=None,
                            max_hold=20, exit_rsi=50)
            return None

        if idn == 69:
            va = I["vavg"]
            if j >= 20 and np.isfinite(va[j - 1]) and v[j] > 1.5 * va[j - 1]:
                hist = I["hist"]
                if hist[j] > 0 and hist[j - 1] <= 0:
                    return dict(side=1, stop_px=c[j] - 1.5 * a,
                                tp_px=c[j] + 2.5 * a)
                if hist[j] < 0 and hist[j - 1] >= 0:
                    return dict(side=-1, stop_px=c[j] + 1.5 * a,
                                tp_px=c[j] - 2.5 * a)
            return None

        if idn == 70:
            ab = I["above"]
            if not np.isfinite(vwap[j]):
                return None
            if j >= 29:
                hold30 = np.all(ab[j - 29: j + 1] > 0)
                below30 = np.all(ab[j - 29: j + 1] < 0)
                if hold30 and l[j] <= vwap[j] and c[j] > vwap[j]:
                    return dict(side=1, stop_px=c[j] - 1.2 * a,
                                tp_px=c[j] + 2.4 * a)
                if below30 and h[j] >= vwap[j] and c[j] < vwap[j]:
                    return dict(side=-1, stop_px=c[j] + 1.2 * a,
                                tp_px=c[j] - 2.4 * a)
            return None

        if idn == 71:
            aa = I["aavg"]
            if j >= 50 and np.isfinite(aa[j - 1]) and a14[j] > 1.5 * aa[j - 1]:
                if c[j] > I["hh10"][j - 1]:
                    return dict(side=1, stop_px=c[j] - 2 * a,
                                tp_px=c[j] + 3 * a, trail="ema21")
                if c[j] < I["ll10"][j - 1]:
                    return dict(side=-1, stop_px=c[j] + 2 * a,
                                tp_px=c[j] - 3 * a, trail="ema21")
            return None

        if idn == 72:
            flip, dirn = I["flip"], I["dirn"]
            if flip[j] == 1 and c[j] > I["e200"][j]:
                return dict(side=1, stop_px=c[j] - 2 * a, tp_px=c[j] + 3 * a)
            if flip[j] == -1 and c[j] < I["e200"][j]:
                return dict(side=-1, stop_px=c[j] + 2 * a, tp_px=c[j] - 3 * a)
            return None

        if idn == 73:
            if I["adx"][j] > 20:
                dirn = I["st"]
                if dirn[j] == 1 and dirn[j - 1] != 1:
                    return dict(side=1, stop_px=c[j] - 2.5 * a,
                                tp_px=c[j] + 4 * a)
                if dirn[j] == -1 and dirn[j - 1] != -1:
                    return dict(side=-1, stop_px=c[j] + 2.5 * a,
                                tp_px=c[j] - 4 * a)
            return None

        if idn == 74:
            if I["adx"][j] < 20:
                if c[j] < I["lo_b"][j]:
                    return dict(side=1, stop_px=c[j] - 1.2 * a, tp_at="mid")
                if c[j] > I["up_b"][j]:
                    return dict(side=-1, stop_px=c[j] + 1.2 * a, tp_at="mid")
            return None

        if idn == 75:
            va = I["vavg"]
            if np.isfinite(pdh[j]) and j >= 20 and np.isfinite(va[j - 1]) \
                    and v[j] > 2 * va[j - 1] and c[j] > pdh[j]:
                return dict(side=1, stop_px=c[j] - 1.5 * a,
                            tp_px=c[j] + 3 * a)
            return None

        if idn == 76:
            vw, sd, r2 = vwap[j], I["vwap_sd"][j], I["r2"][j]
            if np.isfinite(vw) and np.isfinite(sd) \
                    and c[j] <= vw - 2.5 * sd and r2 < 10:
                return dict(side=1, stop_px=c[j] - 1.5 * a, tp_at="vwap",
                            max_hold=30)
            return None

        if idn == 77:
            e20, e50, roc = I["e20"], I["e50"], I["roc"]
            cross_up = e20[j] > e50[j] and e20[j - 1] <= e50[j - 1]
            cross_dn = e20[j] < e50[j] and e20[j - 1] >= e50[j - 1]
            if cross_up and roc[j] > 0:
                return dict(side=1, stop_px=c[j] - 2 * a, tp_px=c[j] + 3 * a,
                            trail="atr25")
            if cross_dn and roc[j] < 0:
                return dict(side=-1, stop_px=c[j] + 2 * a, tp_px=c[j] - 3 * a,
                            trail="atr25")
            return None

        if idn == 78:
            if I["adx"][j] < 20 and j >= 20:
                dl, dh = I["dl20"][j - 1], I["dh20"][j - 1]
                if l[j] <= dl:
                    return dict(side=1, stop_px=dl - 1 * a,
                                tp_px=(dh + dl) / 2)
                if h[j] >= dh:
                    return dict(side=-1, stop_px=dh + 1 * a,
                                tp_px=(dh + dl) / 2)
            return None

        if idn == 79:
            e9, e21, e200 = I["e9"], I["e21"], I["e200"]
            cross_up = e9[j] > e21[j] and e9[j - 1] <= e21[j - 1]
            cross_dn = e9[j] < e21[j] and e9[j - 1] >= e21[j - 1]
            if cross_up and c[j] > e200[j]:
                return dict(side=1, stop_px=c[j] - 1.5 * a,
                            tp_px=c[j] + 3 * a)
            if cross_dn and c[j] < e200[j]:
                return dict(side=-1, stop_px=c[j] + 1.5 * a,
                            tp_px=c[j] - 3 * a)
            return None

        if idn == 80:
            k, d = I["k"], I["d"]
            ku = k[j] > d[j] and k[j - 1] <= d[j - 1] and k[j - 1] < 20
            kd = k[j] < d[j] and k[j - 1] >= d[j - 1] and k[j - 1] > 80
            if ku and c[j] > I["e200"][j]:
                return dict(side=1, stop_px=c[j] - 0.8 * a,
                            tp_px=c[j] + 1.5 * a, max_hold=10)
            if kd and c[j] < I["e200"][j]:
                return dict(side=-1, stop_px=c[j] + 0.8 * a,
                            tp_px=c[j] - 1.5 * a, max_hold=10)
            return None

        if idn == 82:
            if I["r14"][j] < 25 and l[j] <= I["lo_b"][j] \
                    and c[j] > I["e50_1h"][j]:
                return dict(side=1, stop_px=c[j] - 1.5 * a, tp_at="mid")
            return None

        if idn == 83:
            top, bot = I["cloud_top"], I["cloud_bot"]
            if not np.isfinite(top[j]) or j < 26:
                return None
            if c[j] > top[j] and c[j - 1] <= top[j - 1] \
                    and c[j] > I["hh26"][j - 1]:
                return dict(side=1, stop_px=c[j] - 2 * a, tp_px=c[j] + 3 * a)
            if c[j] < bot[j] and c[j - 1] >= bot[j - 1] \
                    and c[j] < I["ll26"][j - 1]:
                return dict(side=-1, stop_px=c[j] + 2 * a, tp_px=c[j] - 3 * a)
            return None

        if idn == 84:
            if not np.isfinite(vwap[j]):
                return None
            ab = I["above"]
            w0 = max(0, j - 10)
            if np.all(ab[w0: j] > 0) and l[j] <= vwap[j] \
                    and c[j] > vwap[j]:
                return dict(side=1, stop_px=c[j] - 1.2 * a,
                            tp_px=c[j] + 2 * a)
            if np.all(ab[w0: j] < 0) and h[j] >= vwap[j] \
                    and c[j] < vwap[j]:
                return dict(side=-1, stop_px=c[j] + 1.2 * a,
                            tp_px=c[j] - 2 * a)
            return None

        if idn == 85:
            dirn, e50 = I["st"], I["e50"]
            if dirn[j] == 1 and dirn[j - 1] != 1 and e50[j] > e50[j - 1]:
                return dict(side=1, stop_px=c[j] - 2 * a, tp_px=c[j] + 4 * a)
            if dirn[j] == -1 and dirn[j - 1] != -1 and e50[j] < e50[j - 1]:
                return dict(side=-1, stop_px=c[j] + 2 * a, tp_px=c[j] - 4 * a)
            return None

        if idn == 86:
            if c[j] > I["e200"][j] and I["r2"][j] < 10:
                return dict(side=1, stop_px=c[j] - 1 * a, tp_px=None,
                            max_hold=15, exit_rsi=55)
            return None

        if idn == 87:
            va = I["vavg"]
            if j >= 20 and np.isfinite(va[j - 1]) and v[j] > 1.5 * va[j - 1]:
                if c[j] > I["dh20"][j - 1]:
                    return dict(side=1, stop_px=c[j] - 1.5 * a,
                                tp_px=c[j] + 2.5 * a)
                if c[j] < I["dl20"][j - 1]:
                    return dict(side=-1, stop_px=c[j] + 1.5 * a,
                                tp_px=c[j] - 2.5 * a)
            return None

        if idn == 88:
            if I["adx"][j] < 20:
                if l[j] <= I["kcl"][j]:
                    return dict(side=1, stop_px=c[j] - 1.5 * a,
                                tp_at="kcmid")
                if h[j] >= I["kch"][j]:
                    return dict(side=-1, stop_px=c[j] + 1.5 * a,
                                tp_at="kcmid")
            return None

        if idn == 89:
            if I["adx"][j] > 25:
                line, sg = I["line"], I["sig"]
                if line[j] > sg[j] and line[j - 1] <= sg[j - 1]:
                    return dict(side=1, stop_px=c[j] - 2 * a,
                                tp_px=c[j] + 3 * a, trail="chand_high")
                if line[j] < sg[j] and line[j - 1] >= sg[j - 1]:
                    return dict(side=-1, stop_px=c[j] + 2 * a,
                                tp_px=c[j] - 3 * a, trail="chand_high")
            return None

        if idn == 90:
            if (h[j] - l[j]) / c[j] > 0.02:
                if c[j] > o[j]:
                    st[("imp_l", j)] = (h[j], l[j], j + 12)
                else:
                    st[("imp_s", j)] = (h[j], l[j], j + 12)
            for kk in range(max(warm, j - 12), j):
                il = st.get(("imp_l", kk))
                if il and j <= il[2] and c[j] > il[0]:
                    st.pop(("imp_l", kk), None)
                    return dict(side=1, stop_px=max(il[1], c[j] - 1.5 * a),
                                tp_px=None, r_tp=2.0, max_hold=12)
                isx = st.get(("imp_s", kk))
                if isx and j <= isx[2] and c[j] < isx[1]:
                    st.pop(("imp_s", kk), None)
                    return dict(side=-1, stop_px=min(isx[0], c[j] + 1.5 * a),
                                tp_px=None, r_tp=2.0, max_hold=12)
            return None

        if idn == 91:
            return _orb(j, a, 1.5, vol_ok=True)

        if idn == 92:
            e9 = I["e9"]
            if np.isfinite(vwap[j]) and c[j] > vwap[j] and c[j - 1] > vwap[j - 1] \
                    and c[j] > e9[j] and l[j] <= e9[j] and c[j] > o[j]:
                return dict(side=1, stop_px=c[j] - 1.5 * a,
                            tp_px=c[j] + 3 * a)
            return None

        if idn == 94:
            va = I["vavg"]
            if (np.isfinite(pdh[j]) and j >= 20 and np.isfinite(va[j - 1])
                    and v[j] > 1.5 * va[j - 1] and c[j] > pdh[j]):
                return dict(side=1, stop_px=c[j] - 2 * a, tp_px=c[j] + 3 * a,
                            trail="chand_high")
            return None

        if idn == 95:
            inside = (np.isfinite(pdh[j]) and np.isfinite(pdl[j])
                      and h[j] < pdh[j] and l[j] > pdl[j])
            if inside and I["adx"][j] < 20:
                if l[j] <= I["lo_b"][j]:
                    return dict(side=1, stop_px=c[j] - 1 * a, tp_at="mid")
                if h[j] >= I["up_b"][j]:
                    return dict(side=-1, stop_px=c[j] + 1 * a, tp_at="mid")
            return None

        if idn == 96:
            return _orb(j, a, 1.5, vol_ok=False)

        if idn == 97:
            dirn = I["st"]
            if not np.isfinite(vwap[j]):
                return None
            if dirn[j] == 1 and dirn[j - 1] != 1 and c[j] > vwap[j]:
                return dict(side=1, stop_px=c[j] - 2 * a, tp_px=c[j] + 3 * a)
            if dirn[j] == -1 and dirn[j - 1] != -1 and c[j] < vwap[j]:
                return dict(side=-1, stop_px=c[j] + 2 * a, tp_px=c[j] - 3 * a)
            return None

        if idn == 99:
            e20, e50 = I["e20"], I["e50"]
            cross_up = e20[j] > e50[j] and e20[j - 1] <= e50[j - 1]
            cross_dn = e20[j] < e50[j] and e20[j - 1] >= e50[j - 1]
            if I["adx"][j] > 20:
                if cross_up:
                    return dict(side=1, stop_px=c[j] - 2 * a,
                                tp_px=c[j] + 4 * a, trail="atr25")
                if cross_dn:
                    return dict(side=-1, stop_px=c[j] + 2 * a,
                                tp_px=c[j] - 4 * a, trail="atr25")
            return None

        if idn == 100:
            sid = day[j]
            g = st.get(("gap", sid))
            if g is None and 585 <= mins[j] <= 660:  # 09:45-11:00 ET
                rr = I["orb15"].get(sid)
                pc = prev_close[j]
                if rr and np.isfinite(pc):
                    hi15, lo15 = rr
                    open_idx = np.where((day == sid) & (mins < 585)
                                        & (mins >= 570))[0]
                    gap = (o[open_idx[0]] - pc) / pc if len(open_idx) else np.nan
                    g = dict(gap=gap, mid=(hi15 + lo15) / 2, pc=pc)
                    st[("gap", sid)] = g
                else:
                    st[("gap", sid)] = -1  # marker: no setup today
                    return None
            if not isinstance(g, dict) or g.get("done"):
                return None
            gap, mid, pc = g["gap"], g["mid"], g["pc"]
            if gap > 0.005 and c[j] < mid:
                g["done"] = True
                return dict(side=-1, stop_px=c[j] + 1.5 * a, tp_px=pc,
                            max_hold=60)
            if gap < -0.005 and c[j] > mid:
                g["done"] = True
                return dict(side=1, stop_px=c[j] - 1.5 * a, tp_px=pc,
                            max_hold=60)
            return None

        return None

    def _orb(j, a, sl_mult, vol_ok):
        """Opening-range breakout on the equity tape (91/96)."""
        sid = day[j]
        if mins[j] < (585 if idn == 91 else 600):  # range still forming (ET)
            return None
        rr = I["orb"].get(sid)
        if not rr:
            return None
        rh, rl = rr
        if vol_ok:
            va = I["vavg"]
            if not (j >= 20 and np.isfinite(va[j - 1])
                    and v[j] > 1.5 * va[j - 1]):
                return None
        if not st.get(("dl", sid)) and c[j] > rh:
            st[("dl", sid)] = True
            return dict(side=1, stop_px=max(rl, c[j] - sl_mult * a),
                        tp_px=None, r_tp=2.0)
        if not st.get(("ds", sid)) and c[j] < rl:
            st[("ds", sid)] = True
            return dict(side=-1, stop_px=min(rh, c[j] + sl_mult * a),
                        tp_px=None, r_tp=2.0)
        return None

    # ---- management while in position --------------------------------------
    def manage(j):
        p = book.pos
        if p is None:
            return None
        sig = p.get("pack_sig")
        if sig is None:
            # Book builds its own pos dict; the signal extras live in the
            # factory state keyed by the fill bar (see sig()).
            sig = st.get(("psig", p["entry_idx"]))
            if sig is not None:
                p["pack_sig"] = sig
        sig = sig or {}

        if not p.get("pack_tp_set"):
            p["pack_tp_set"] = True
            fill = p["fill"]
            if sig.get("r_tp"):
                dist = abs(fill - p["stop"])
                if dist > 0:
                    p["tp"] = fill + p["side"] * sig["r_tp"] * dist
            if sig.get("tp_at") == "vwap" and np.isfinite(vwap[j]):
                p["tp"] = float(vwap[j])
            elif sig.get("tp_at") == "mid" and np.isfinite(I["mid_b"][j]):
                p["tp"] = float(I["mid_b"][j])
            elif sig.get("tp_at") == "kcmid" and np.isfinite(I["kcmid"][j]):
                p["tp"] = float(I["kcmid"][j])

        if sig.get("exit_rsi"):
            if I["r2"][j] > sig["exit_rsi"]:
                return dict(side=0)

        tr = sig.get("trail")
        if tr:
            a = a14[j]
            if tr == "ema21":
                set_stop(I["e21"][j])
            elif tr == "ema21_r":
                r_now = p["side"] * (c[j] - p["fill"])
                if r_now >= abs(p["fill"] - p["stop"]):
                    set_stop(I["e21"][j])
            elif tr == "atr25":
                set_stop(c[j] - p["side"] * 2.5 * a)
            elif tr == "chand_close":
                ext = p.get("pack_ext", c[j])
                ext = max(ext, c[j]) if p["side"] == 1 else min(ext, c[j])
                p["pack_ext"] = ext
                set_stop(ext - p["side"] * 3 * a)
            elif tr == "chand_high":
                ext = p.get("pack_ext", h[j] if p["side"] == 1 else l[j])
                ext = max(ext, h[j]) if p["side"] == 1 else min(ext, l[j])
                p["pack_ext"] = ext
                set_stop(ext - p["side"] * 3 * a)

        if (is_eq or idn in FLAT_UTC) and flat_deadline_hit(j):
            return dict(side=0)
        return None

    def sig(j):
        if j + 1 >= n:
            return None
        s = manage(j)
        if s is not None:
            return s
        e = entry(j)
        if e is not None:
            psig = {k: e[k] for k in
                    ("r_tp", "tp_at", "trail", "exit_rsi", "max_hold")
                    if k in e}
            st[("psig", j + 1)] = psig
            e["pack_sig"] = psig
        return e

    return sig


def _ny_parts(ts):
    ny = ts.dt.tz_convert("America/New_York")
    return ny, (ny.dt.hour * 60 + ny.dt.minute).to_numpy(int), \
        ny.dt.dayofweek.to_numpy(int)


def _rth_masks(ts):
    _, mins, dow = _ny_parts(ts)
    rth = (mins >= 570) & (mins < 960) & (dow < 5)
    ms = _ms(ts)
    sess = np.where(rth, _day_id(ms), -1)
    return rth, sess


# ─────────────────────────── run + dispatch ───────────────────────────────
def run(paths, params):
    p = dict(params)
    idn = int(p.pop("id"))
    if p:
        raise ValueError(f"unknown qwen50 params: {sorted(p)}")
    if idn in NO_DATA:
        raise ValueError(f"NO DATA: {idn}: {NO_DATA[idn]}")
    if idn not in CELLS:
        raise ValueError(f"unknown qwen50 cell: {idn}")

    symbol, tf_label, tf_minutes, _src = CELLS[idn]
    main, aux = build_frame(idn, paths)
    main = _prepare_main(main)
    if idn in (60, 82):
        aux["_1h_close_aligned"] = _align_last(main, aux["_1h"])[1]
    fee, slip = SYMBOL_COST[symbol]
    n = int(len(main["open"]))

    def make_book():
        return Book(symbol, tf_label, main, init=INIT, fee=fee, slip=slip,
                    risk_pct=RISK, max_leverage=MAXLEV, charge_funding=True)

    results = {}
    for tag in ("full", "oos"):
        book = make_book()
        if idn == 64:
            aux["ratio"] = main["close"].to_numpy(float) / \
                _align_last(main, aux["BTCUSDT_30m"])[1]
        sig_core = _make_sig(idn, main, aux, symbol, book)
        oos_start = int(n * 0.7)

        def signal(j, book=book, sig_core=sig_core, tag=tag,
                   oos_start=oos_start):
            if j + 1 >= n:
                return None
            s = sig_core(j)
            if s is None:
                return None
            if s.get("side", 0) == 0:
                return s
            if tag == "oos" and j + 1 < oos_start:
                return None
            ep = float(main["open"][j + 1])
            sp = float(s["stop_px"])
            side = s["side"]
            if (side == 1 and sp >= ep) or (side == -1 and sp <= ep):
                return None
            return s

        if tag == "full":
            book.run(signal, start_idx=0, end_idx=n - 1)
        else:
            book.run(signal, start_idx=0, end_idx=n - 1, trade_from=oos_start)
        results[tag] = (book, book_metrics(book))

    book, full_m = results["full"]
    _, oos_m = results["oos"]
    fee_bps, slip_bps = fee * 1e4, slip * 1e4
    metrics = dict(full_m)
    # book_metrics hardcodes the repo 11 bps RT label; the pack's costs are
    # author-declared per symbol — report the REAL round trip.
    metrics["cost_bp_roundtrip"] = (fee + slip) * 2 * 1e4
    metrics.update({
        "oos_profit_factor": oos_m["profit_factor"],
        "oos_return_pct": oos_m["return_pct"],
        "oos_n_trades": oos_m["n_trades"],
        "oos_max_dd_pct": oos_m["max_dd_pct"],
        "oos_boot_ci_lo": oos_m["boot_ci_lo"],
        "id": idn, "symbol": symbol, "tf": tf_label,
        "engine_version": ENGINE_VERSION,
        "fragile_label": bool(oos_m["n_trades"] < 200),
        "fee_per_side_bps": fee_bps, "slip_per_side_bps": slip_bps,
        "pack_rules": "signal close/enter next open; stop-first; 0.5% risk; "
                      "no daily caps (prompts silent); author costs "
                      f"({fee_bps:.1f}/{slip_bps:.1f} bps per side) for "
                      "crypto, repo 11 bps RT on the NVDA/SPCX perp tape; "
                      "trailing via live-stop ratchet; funding at real "
                      "settlements (all eight symbols)",
    })
    trades = [{"entry_time": t["entry_time"], "exit_time": t["exit_time"],
               "side": t["side"], "entry": float(t["entry"]),
               "exit": float(t["exit"]), "pnl": float(t["pnl"]),
               "reason": t["reason"]} for t in book.trades]
    tables = [{"id": f"qwen50_{idn}", "symbol": symbol, "tf": tf_label,
               "trades": trades}]
    prov = {"engine_version": ENGINE_VERSION,
            "sources_of_record": ["code/prompts_51_100.txt"],
            "core": "p100_screen_engine.Book (audited by the p100 campaign)",
            "conventions": {
                "signal": "close of bar j, fill at open of j+1",
                "ties": "stop first; gap-through stop fills at the open",
                "entry_ref": "ATR stops/targets from the signal-bar close; "
                             "R/vwap/mid targets set at the fill and "
                             "checkable from the bar after it",
                "trailing": "live-stop ratchet, tighter only, effective next "
                            "bar; Chandelier from highest close (id 62) or "
                            "highest high (67/89/94) since entry",
                "squeeze": "armed at width percentile <= thr (rolling 200), "
                           "disarm on entry or percentile > 0.5",
                "session": "UTC-day VWAP/flat for crypto (flat ids 56/65/70/"
                           "78/84); RTH 09:30-16:00 ET weekdays on the NVDA/"
                           "SPCX perp tape, prior-day anchors = previous RTH "
                           "session, one ORB entry per direction per day",
                "costs": "author-declared per prompt (10/14 bps RT crypto); "
                         "NVDA/SPCX $/share undefined on perp -> 11 bps RT",
                "risk": "0.5% equity/trade, 3x leverage cap, INIT 10k; no "
                        "daily caps (prompts silent)",
                "funding": "real settlements, all eight symbols",
                "split": "70/30 chronological, no purge",
                "fragile": "label when OOS n < 200"}}
    return metrics, prov, tables


def dispatch(paths, params):
    return run(paths, params)


if __name__ == "__main__":
    print("qwen50_engine: import-only module; run via vrun (adapter qwen50)")
