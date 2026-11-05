"""MP-STRAT 01..20 — ports from the SPEC TABLE of `Downloads/index.html`
(report "Twenty Multi-Pair Strategies Over a Six-Month Crypto Window").
IMPORTANT: the code shipped in the author's folder (data/mp_suite) has
DIFFERENT strategy names for the same IDs (0/20 match) — these ports
implement the report's own one-line specs, not that code.

Engine conventions (this stack):
- 1h bars, USDT-M perps, equal-weight universe, longs only (every spec in the
  report is long-only except MP-08 which is market-neutral pair).
- Costs: 6bps commission + 5bps slip per side (conservative vs report 5/5).
- Entries/exits at the CLOSE of the signal bar (no lookahead).
- 1% of equity risk per trade, stop = 2x ATR(14) initial, 2x ATR trailing
  unless the spec overrides.
- Metrics: PF on closed trades, DD on net (mark-to-market) equity, Sharpe
  annualized sqrt(24*365) on hourly portfolio returns (reported for parity
  with the report, but treated as untrustworthy — 6-month sample).
Usage: python mp20_report_ports.py [windows|full|all]
"""
import os
import sys
import csv
import math

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D1H = os.path.join(ROOT, "data", "binance_klines_1h")
UNIV = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "LINKUSDT"]
COST = 0.0006
SLIP = 0.0005
EQ0 = 10000.0
RISK = 0.01
STOP_ATR = 2.0
TRAIL_ATR = 2.0
REBAL = 168  # bars = 168h = 1 week


# ───────────────────────── data / indicators ─────────────────────────
def load_universe(syms=None):
    syms = syms or UNIV
    D = {}
    keep = None
    for s in syms:
        p = os.path.join(D1H, s + "_1h.csv")
        if not os.path.exists(p):
            print("MISSING", s, flush=True)
            continue
        rows = []
        with open(p, newline="") as f:
            for r in csv.DictReader(f):
                rows.append((int(r["open_ts"]), float(r["open"]), float(r["high"]),
                             float(r["low"]), float(r["close"]), float(r["volume"])))
        rows.sort()
        D[s] = rows
        ts = {r[0] for r in rows}
        keep = ts if keep is None else (keep & ts)
    return D, sorted(keep)


def panel(D, ts):
    """Aligned numpy arrays: index 0..N-1 over ts, per symbol dict."""
    idx = {t: i for i, t in enumerate(ts)}
    N = len(ts)
    P = {}
    for s, rows in D.items():
        O = np.zeros(N); H = np.zeros(N); L = np.zeros(N); C = np.zeros(N); V = np.zeros(N)
        for t, o, h, l, c, v in rows:
            i = idx.get(t)
            if i is None:
                continue
            O[i] = o; H[i] = h; L[i] = l; C[i] = c; V[i] = v
        P[s] = dict(O=O, H=H, L=L, C=C, V=V)
    return P


def atr(H, L, C, n=14):
    pc = np.roll(C, 1); pc[0] = C[0]
    tr = np.maximum(H - L, np.maximum(np.abs(H - pc), np.abs(L - pc)))
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()


def rsi(C, n=14):
    d = np.diff(C, prepend=C[0])
    u = np.where(d > 0, d, 0.0); dn = np.where(d < 0, -d, 0.0)
    au = pd.Series(u).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()
    ad = pd.Series(dn).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()
    return np.where(ad == 0, 100.0, 100 - 100 / (1 + au / np.where(ad == 0, 1, ad)))


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def sma(x, n):
    return pd.Series(x).rolling(n).mean().to_numpy()


def std(x, n):
    return pd.Series(x).rolling(n).std(ddof=1).to_numpy()


def adx(H, L, C, n=14):
    up = np.diff(H, prepend=H[0]); dn = -np.diff(L, prepend=L[0])
    plus = np.where((up > dn) & (up > 0), up, 0.0)
    minus = np.where((dn > up) & (dn > 0), dn, 0.0)
    pc = np.roll(C, 1); pc[0] = C[0]
    tr = np.maximum(H - L, np.maximum(np.abs(H - pc), np.abs(L - pc)))
    atr_ = pd.Series(tr).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()
    pdi = 100 * pd.Series(plus).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy() / np.maximum(atr_, 1e-12)
    mdi = 100 * pd.Series(minus).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy() / np.maximum(atr_, 1e-12)
    dx = 100 * np.abs(pdi - mdi) / np.maximum(pdi + mdi, 1e-12)
    return pd.Series(dx).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy(), pdi, mdi


def macd(C, f=12, sl=26, sig=9):
    ml = ema(C, f) - ema(C, sl)
    sg = ema(ml, sig)
    return ml, sg, ml - sg


def precompute(P, N):
    I = {}
    for s, d in P.items():
        C, H, L, V = d["C"], d["H"], d["L"], d["V"]
        a = atr(H, L, C)
        a_s, pdi, mdi = adx(H, L, C)
        ml, sg, hi = macd(C)
        e8, e21, e50, e55, e200 = (ema(C, 8), ema(C, 21), ema(C, 50), ema(C, 55), ema(C, 200))
        m20, s20, sd20 = sma(C, 20), sma(C, 20), std(C, 20)
        bbw = 4 * sd20 / np.maximum(m20, 1e-12)
        # merge ATR into the price panel: Port.manage() needs H/L/O *and* atr
        P[s]["atr"] = a
        I[s] = dict(
            O=d["O"], H=d["H"], L=d["L"], C=d["C"], V=d["V"],  # strategies read these
            atr=a, adx=a_s, pdi=pdi, mdi=mdi,
            macd=ml, macds=sg, hist=hi,
            e8=e8, e21=e21, e50=e50, e55=e55, e200=e200,
            sma20=m20, s20=s20, sd20=sd20, bbw=bbw,
            rsi2=rsi(C, 2), rsi14=rsi(C, 14),
            sma50=sma(C, 50), sma200=sma(C, 200),
            hi20=pd.Series(H).rolling(20).max().to_numpy(),
            lo10=pd.Series(L).rolling(10).min().to_numpy(),
            lo20=pd.Series(L).rolling(20).min().to_numpy(),
            kc_u=ema(C, 20) + 1.5 * a, kc_l=ema(C, 20) - 1.5 * a,
            r24=C / np.roll(C, 24) - 1.0,
        )
    I["_"] = dict(bbw_med=pd.Series([np.nan]).to_numpy())
    # cross-sectional helpers computed per-bar later
    return I


# ───────────────────────── portfolio shell ─────────────────────────
class Port:
    """Long-only per-slot book with 1%-risk sizing, ATR stop, ATR trail."""

    def __init__(self, n_slots, N, symbols):
        self.n = n_slots
        self.N = N
        self.sym = symbols
        self.slot = [dict(active=False, side=1, entry=0.0, stop=0.0, peak=0.0,
                          qty=0.0, risk=0.0, opened=-1, src="", mark=0.0,
                          sym=(symbols[j] if j < len(symbols) else ""))
                     for j in range(n_slots)]
        self.cash = EQ0
        self.equity = [EQ0] * N
        self.closed = []
        self.gp = 0.0
        self.gl = 0.0
        self.peak = EQ0
        self.mdd = 0.0

    def equity_now(self):
        m = 0.0
        for sl in self.slot:
            if sl["active"]:
                m += sl["qty"] * sl["mark"]
        return self.cash + m

    def set_marks(self, i, P):
        for sl in self.slot:
            if sl["active"]:
                sl["mark"] = P[sl["sym"]]["C"][i]

    def bind(self, k, sym):
        self.slot[k]["sym"] = sym

    def sync(self, on):
        """Clear the strategy's entry flags for slots the RISK layer just closed.

        Without this the trailing stop in manage() closes a position behind the
        strategy's back: `on[k]` stays True forever, that symbol never re-enters,
        and the book silently holds ~5 trades in 6 years. Observed on every
        non-rotation strategy before the fix (n=5..6 across all windows).
        """
        if isinstance(on, list):
            for k, sl in enumerate(self.slot):
                if not sl["active"] and k < len(on):
                    on[k] = False

    def open_slot(self, k, i, price, stop, P, src, risk=None):
        eq = self.equity_now()
        if eq <= 0:
            return False
        risk_px = abs(price - stop)
        if risk_px <= 0:
            return False
        # Three caps, in priority order:
        #  1. risk cap: 1% of equity at the ATR stop  (the report's own rule)
        #  2. per-slot notional cap 0.6x equity, so a 5-slot book cannot lever
        #     itself past 3x gross
        #  3. total gross room under 3x equity
        # Without cap 2 the FIRST slot to fire eats the whole 3x room and every
        # other symbol is starved for the rest of the run (observed: n=5 trades
        # in 6 years) — an artifact of ordering, not a strategy result.
        gross = sum(sl["qty"] * sl["mark"] for sl in self.slot if sl["active"])
        room = max(0.0, 3.0 * eq - gross)
        qty = min(eq * (RISK if risk is None else risk) / risk_px,
                  0.6 * eq / price,
                  room / price)
        if qty <= 0:
            return False
        sl = self.slot[k]
        sl.update(active=True, side=1, entry=price, stop=stop, peak=price,
                  qty=qty, opened=i, src=src, mark=price)
        self.cash -= qty * price * (1 + COST + SLIP)
        return True

    def close_slot(self, k, i, price):
        """Sell the asset back to cash.

        open_slot already debited the notional from cash, so the close must
        credit PROCEEDS (not P&L) or the notional gets subtracted twice — that
        bug alone made every book lose ~2x equity per trade.
        """
        sl = self.slot[k]
        proceeds = sl["qty"] * price * (1 - SLIP)
        pnl = proceeds - sl["qty"] * sl["entry"] * (1 + COST)
        self.cash += proceeds
        self.closed.append((i, sl["src"], pnl))
        if pnl > 0:
            self.gp += pnl
        else:
            self.gl += abs(pnl)
        sl["active"] = False
        sl["qty"] = 0.0

    def manage(self, i, P, trail=True):
        for k, sl in enumerate(self.slot):
            if not sl["active"]:
                continue
            d = P[sl["sym"]]
            sl["peak"] = max(sl["peak"], d["H"][i])
            xp = None
            if d["O"][i] <= sl["stop"]:
                xp = d["O"][i]
            elif d["L"][i] <= sl["stop"]:
                xp = sl["stop"]
            if xp is not None:
                self.close_slot(k, i, xp)
                continue
            if trail:
                a = d["atr"][i]
                if not np.isnan(a):
                    ns = sl["peak"] - TRAIL_ATR * a
                    if ns > sl["stop"]:
                        sl["stop"] = ns

    def mark_eod(self, i):
        self.equity[i] = self.equity_now()
        if self.equity[i] > self.peak:
            self.peak = self.equity[i]
        dd = (self.peak - self.equity[i]) / max(self.peak, 1e-9)
        if dd > self.mdd:
            self.mdd = dd

    def metrics(self):
        eq = self.equity[-1]
        n = len(self.closed)
        w = sum(1 for _, _, p in self.closed if p > 0)
        pf = self.gp / self.gl if self.gl > 0 else (float("inf") if self.gp > 0 else 0.0)
        r = pd.Series(self.equity).pct_change().fillna(0.0)
        sh = (r.mean() / r.std(ddof=1) * math.sqrt(24 * 365)) if r.std(ddof=1) > 0 else float("nan")
        return dict(ret=(eq / EQ0 - 1) * 100, pf=pf, wr=w / max(n, 1) * 100,
                    n=n, dd=self.mdd * 100, sharpe=sh)


def weights_rebalance(n):
    return [1.0 / n] * n


# ───────────────────────── strategies ─────────────────────────
def st01_crosssec_mom(P, I, syms, N):
    """Top-3 by 24h return, weekly rebalance, ATR*2 stop."""
    p = Port(3, N, syms[:3])
    on = []  # slot activity is read from p.slot directly (rotation rebinds)
    for i in range(260, N):
        p.set_marks(i, P)
        p.manage(i, P, trail=False)
        p.sync(on)
        if i % REBAL == 0 and i >= 24:
            rank = sorted(syms, key=lambda s: -I[s]["r24"][i])[:3]
            for k, s in enumerate(rank):
                sl = p.slot[k]
                if sl["active"] and sl["sym"] != s:
                    p.close_slot(k, i, P[sl["sym"]]["C"][i] * (1 - SLIP))
                if not sl["active"]:
                    px = P[s]["C"][i]
                    p.bind(k, s)
                    p.open_slot(k, i, px, px - STOP_ATR * I[s]["atr"][i], P, "01")
            for k in range(len(rank), len(p.slot)):
                if p.slot[k]["active"]:
                    p.close_slot(k, i, P[p.slot[k]["sym"]]["C"][i] * (1 - SLIP))
        p.mark_eod(i)
    return p


def st02_ema_cross(P, I, syms, N):
    """Long all 5 while EMA50>EMA200, exit on cross down, trailing stop."""
    n = len(syms)
    p = Port(n, N, syms)
    on = [False] * n
    for i in range(260, N):
        p.set_marks(i, P)
        p.manage(i, P, trail=False)
        p.sync(on)
        for k, s in enumerate(syms):
            bull = (not np.isnan(I[s]["e50"][i]) and not np.isnan(I[s]["e200"][i])
                    and I[s]["e50"][i] > I[s]["e200"][i])
            if bull and not on[k]:
                px = P[s]["C"][i]
                if p.open_slot(k, i, px, px - STOP_ATR * I[s]["atr"][i], P, "02"):
                    on[k] = True
            elif (not bull) and on[k] and p.slot[k]["active"]:
                p.close_slot(k, i, P[s]["C"][i] * (1 - SLIP))
                on[k] = False
        p.mark_eod(i)
    return p


def st03_donchian(P, I, syms, N):
    """20-bar Donchian breakout long; exit at 10-bar low; trail ATR."""
    n = len(syms)
    p = Port(n, N, syms)
    on = [False] * n
    for i in range(60, N):
        p.set_marks(i, P)
        p.manage(i, P, trail=False)
        p.sync(on)
        for k, s in enumerate(syms):
            d = I[s]
            brk = (not np.isnan(d["hi20"][i - 1]) and d["C"][i] > d["hi20"][i - 1])
            if brk and not on[k]:
                px = P[s]["C"][i]
                if p.open_slot(k, i, px, px - STOP_ATR * d["atr"][i], P, "03"):
                    on[k] = True
            elif on[k] and p.slot[k]["active"]:
                if (not np.isnan(d["lo10"][i]) and d["C"][i] < d["lo10"][i]):
                    p.close_slot(k, i, P[s]["C"][i] * (1 - SLIP))
                    on[k] = False
        p.mark_eod(i)
    return p


def st04_adx(P, I, syms, N):
    """Enter when ADX>25 and EMA21>EMA55; exit ADX<20 or cross down."""
    n = len(syms)
    p = Port(n, N, syms)
    on = [False] * n
    for i in range(120, N):
        p.set_marks(i, P)
        p.manage(i, P, trail=False)
        p.sync(on)
        for k, s in enumerate(syms):
            d = I[s]
            ent = (not np.isnan(d["adx"][i]) and d["adx"][i] > 25
                   and d["e21"][i] > d["e55"][i])
            ex = ((not np.isnan(d["adx"][i]) and d["adx"][i] < 20)
                  or d["e21"][i] < d["e55"][i])
            if ent and not on[k]:
                px = P[s]["C"][i]
                if p.open_slot(k, i, px, px - STOP_ATR * d["atr"][i], P, "04"):
                    on[k] = True
            elif ex and on[k] and p.slot[k]["active"]:
                p.close_slot(k, i, P[s]["C"][i] * (1 - SLIP))
                on[k] = False
        p.mark_eod(i)
    return p


def st05_triple_ema(P, I, syms, N):
    """Triple EMA 8/21/55 alignment long; exit on alignment break."""
    n = len(syms)
    p = Port(n, N, syms)
    on = [False] * n
    for i in range(120, N):
        p.set_marks(i, P)
        p.manage(i, P, trail=False)
        p.sync(on)
        for k, s in enumerate(syms):
            d = I[s]
            al = d["e8"][i] > d["e21"][i] > d["e55"][i]
            if al and not on[k]:
                px = P[s]["C"][i]
                if p.open_slot(k, i, px, px - STOP_ATR * d["atr"][i], P, "05"):
                    on[k] = True
            elif (not al) and on[k] and p.slot[k]["active"]:
                p.close_slot(k, i, P[s]["C"][i] * (1 - SLIP))
                on[k] = False
        p.mark_eod(i)
    return p


def st06_boll_mr(P, I, syms, N):
    """Long when close < lower Bollinger(20,2); exit at midline; ATR*2 stop."""
    n = len(syms)
    p = Port(n, N, syms)
    on = [False] * n
    for i in range(60, N):
        p.set_marks(i, P)
        p.manage(i, P, trail=False)
        p.sync(on)
        for k, s in enumerate(syms):
            d = I[s]
            lo2 = d["sma20"][i] - 2 * d["sd20"][i]
            if (not np.isnan(lo2) and d["C"][i] < lo2) and not on[k]:
                px = P[s]["C"][i]
                if p.open_slot(k, i, px, px - STOP_ATR * d["atr"][i], P, "06"):
                    on[k] = True
            elif on[k] and p.slot[k]["active"]:
                if d["C"][i] >= d["sma20"][i]:
                    p.close_slot(k, i, P[s]["C"][i] * (1 - SLIP))
                    on[k] = False
        p.mark_eod(i)
    return p


def st07_rsi2(P, I, syms, N):
    """Connors: long when RSI(2)<10 and close>SMA200; exit RSI(2)>70 or 24h hold."""
    n = len(syms)
    p = Port(n, N, syms)
    on = [False] * n
    for i in range(260, N):
        p.set_marks(i, P)
        p.manage(i, P, trail=False)
        p.sync(on)
        for k, s in enumerate(syms):
            d = I[s]
            if (d["rsi2"][i] < 10 and d["C"][i] > d["sma200"][i]) and not on[k]:
                px = P[s]["C"][i]
                if p.open_slot(k, i, px, px - STOP_ATR * d["atr"][i], P, "07"):
                    on[k] = True
            elif on[k] and p.slot[k]["active"]:
                sl = p.slot[k]
                if d["rsi2"][i] > 70 or i - sl["opened"] >= 24:
                    p.close_slot(k, i, P[s]["C"][i] * (1 - SLIP))
                    on[k] = False
        p.mark_eod(i)
    return p


def st08_btc_eth_spread(P, I, syms, N, a="BTCUSDT", b="ETHUSDT", zin=1.0, zout=0.2):
    """BTC/ETH cointegration spread; long spread z<-1, exit |z|<0.2; neutral."""
    if a not in P or b not in P:
        return None
    Ca, Cb = P[a]["C"], P[b]["C"]
    ratio = Ca / Cb
    ma = sma(ratio, 100); sd = std(ratio, 100)
    z = (ratio - ma) / np.maximum(sd, 1e-12)
    p = Port(1, N, [a])
    on = [False]
    for i in range(200, N):
        zz = z[i]
        if not on[0] and (not np.isnan(zz)) and zz < -zin:
            px = P[a]["C"][i]
            if p.open_slot(0, i, px, px * 0.97, P, "08"):
                on[0] = True
        elif on[0] and (not np.isnan(zz)) and abs(zz) < zout:
            p.close_slot(0, i, P[a]["C"][i] * (1 - SLIP))
            on[0] = False
        p.set_marks(i, P)
        p.manage(i, P, trail=False)
        p.sync(on)
        p.mark_eod(i)
    return p


def st09_xsec_z(P, I, syms, N, zin=1.5):
    """Cross-sectional z-score vs basket median < -1.5; long laggards."""
    n = len(syms)
    p = Port(n, N, syms)
    on = [False] * n
    for i in range(60, N):
        p.set_marks(i, P)
        p.manage(i, P, trail=False)
        p.sync(on)
        r24 = np.array([I[s]["r24"][i] for s in syms])
        if not np.isnan(r24).any():
            med = np.median(r24)
            mad = np.median(np.abs(r24 - med)) or 1e-9
            zs = (r24 - med) / (1.4826 * mad)
            for k, s in enumerate(syms):
                if zs[k] < -zin and not on[k]:
                    px = P[s]["C"][i]
                    if p.open_slot(k, i, px, px - STOP_ATR * I[s]["atr"][i], P, "09"):
                        on[k] = True
                elif on[k] and p.slot[k]["active"] and zs[k] > -0.5:
                    p.close_slot(k, i, P[s]["C"][i] * (1 - SLIP))
                    on[k] = False
        p.mark_eod(i)
    return p


def st10_zscore50(P, I, syms, N, zin=2.0):
    """50-bar z-score of close vs its own SMA; long z<-2, exit at SMA."""
    n = len(syms)
    p = Port(n, N, syms)
    on = [False] * n
    for i in range(80, N):
        p.set_marks(i, P)
        p.manage(i, P, trail=False)
        p.sync(on)
        for k, s in enumerate(syms):
            d = I[s]
            m = sma(d["C"], 50); sd = std(d["C"], 50)
            zz = (d["C"][i] - m[i]) / np.maximum(sd[i], 1e-12)
            if (not np.isnan(zz) and zz < -zin) and not on[k]:
                px = d["C"][i]
                if p.open_slot(k, i, px, px - STOP_ATR * d["atr"][i], P, "10"):
                    on[k] = True
            elif on[k] and p.slot[k]["active"] and d["C"][i] >= m[i]:
                p.close_slot(k, i, d["C"][i] * (1 - SLIP))
                on[k] = False
        p.mark_eod(i)
    return p


def st11_atr_breakout(P, I, syms, N, k=1.5):
    """Long when close > prev_close + 1.5*ATR; exit on 1*ATR reversal."""
    n = len(syms)
    p = Port(n, N, syms)
    on = [False] * n
    for i in range(60, N):
        p.set_marks(i, P)
        p.manage(i, P, trail=False)
        p.sync(on)
        for k_, s in enumerate(syms):
            d = I[s]
            trig = d["C"][i] > d["C"][i - 1] + k * d["atr"][i]
            if trig and not on[k_]:
                px = d["C"][i]
                if p.open_slot(k_, i, px, px - d["atr"][i], P, "11"):
                    on[k_] = True
            elif on[k_] and p.slot[k_]["active"]:
                if d["C"][i] < d["C"][i - 1] - 1.0 * d["atr"][i]:
                    p.close_slot(k_, i, d["C"][i] * (1 - SLIP))
                    on[k_] = False
        p.mark_eod(i)
    return p


def st12_squeeze(P, I, syms, N):
    """Bollinger squeeze (bandwidth at 50-bar min) + close>midline; exit midline loss."""
    n = len(syms)
    p = Port(n, N, syms)
    on = [False] * n
    for i in range(120, N):
        p.set_marks(i, P)
        p.manage(i, P, trail=False)
        p.sync(on)
        for k, s in enumerate(syms):
            d = I[s]
            bw = d["bbw"][i]
            hist = pd.Series(d["bbw"][:i + 1]).rolling(50).min().to_numpy()[-1] if i >= 50 else np.nan
            sq = (not np.isnan(bw)) and (not np.isnan(hist)) and bw <= hist * 1.02
            if sq and d["C"][i] > d["sma20"][i] and not on[k]:
                px = d["C"][i]
                if p.open_slot(k, i, px, px - STOP_ATR * d["atr"][i], P, "12"):
                    on[k] = True
            elif on[k] and p.slot[k]["active"] and d["C"][i] < d["sma20"][i]:
                p.close_slot(k, i, d["C"][i] * (1 - SLIP))
                on[k] = False
        p.mark_eod(i)
    return p


def st13_top2_rot(P, I, syms, N):
    """Top-2 by 24h return, weekly rotation (168h)."""
    p = Port(2, N, syms[:2])
    on = []
    for i in range(260, N):
        p.set_marks(i, P)
        p.manage(i, P, trail=False)
        p.sync(on)
        if i % REBAL == 0 and i >= 24:
            rank = sorted(syms, key=lambda s: -I[s]["r24"][i])
            for k in range(2):
                s = rank[k]
                sl = p.slot[k]
                if sl["active"] and sl["sym"] != s:
                    p.close_slot(k, i, P[sl["sym"]]["C"][i] * (1 - SLIP))
                if not sl["active"]:
                    px = P[s]["C"][i]
                    p.bind(k, s)
                    p.open_slot(k, i, px, px - STOP_ATR * I[s]["atr"][i], P, "13")
        p.mark_eod(i)
    return p


def st14_macd_x(P, I, syms, N):
    """MACD crossover long; exit on cross down; trail ATR."""
    n = len(syms)
    p = Port(n, N, syms)
    on = [False] * n
    for i in range(60, N):
        p.set_marks(i, P)
        p.manage(i, P, trail=False)
        p.sync(on)
        for k, s in enumerate(syms):
            d = I[s]
            up = (d["macd"][i] > d["macds"][i])
            prev = (d["macd"][i - 1] <= d["macds"][i - 1]) if i >= 1 else False
            dn = (d["macd"][i] < d["macds"][i])
            if up and prev and not on[k]:
                px = d["C"][i]
                if p.open_slot(k, i, px, px - STOP_ATR * d["atr"][i], P, "14"):
                    on[k] = True
            elif dn and on[k] and p.slot[k]["active"]:
                p.close_slot(k, i, d["C"][i] * (1 - SLIP))
                on[k] = False
        p.mark_eod(i)
    return p


def st15_keltner(P, I, syms, N):
    """Keltner(20,1.5ATR) squeeze + upside breakout; exit at EMA20."""
    n = len(syms)
    p = Port(n, N, syms)
    on = [False] * n
    for i in range(60, N):
        p.set_marks(i, P)
        p.manage(i, P, trail=False)
        p.sync(on)
        for k, s in enumerate(syms):
            d = I[s]
            brk = (not np.isnan(d["kc_u"][i])) and d["C"][i] > d["kc_u"][i]
            if brk and not on[k]:
                px = d["C"][i]
                if p.open_slot(k, i, px, px - STOP_ATR * d["atr"][i], P, "15"):
                    on[k] = True
            elif on[k] and p.slot[k]["active"] and d["C"][i] < d["e21"][i]:
                p.close_slot(k, i, d["C"][i] * (1 - SLIP))
                on[k] = False
        p.mark_eod(i)
    return p


def st16_inv_atr(P, I, syms, N, rebal=24):
    """Inverse-ATR volatility weighting; daily rebalance; holds all 5."""
    def wf(i, allowed):
        iv = {}
        for s in allowed:
            a = I[s]["atr"][i]
            iv[s] = 1.0 / max(a / P[s]["C"][i], 1e-9)
        tot = sum(iv.values()) or 1.0
        return {s: iv[s] / tot for s in allowed}
    p = Port(len(syms), N, syms)
    on = [False] * len(syms)
    for i in range(260, N):
        p.set_marks(i, P)
        p.manage(i, P, trail=False)
        p.sync(on)
        if i % rebal == 0:
            w = wf(i, syms)
            for k, s in enumerate(syms):
                if not on[k]:
                    px = P[s]["C"][i]
                    if p.open_slot(k, i, px, px - STOP_ATR * I[s]["atr"][i], P, "16"):
                        on[k] = True
        p.mark_eod(i)
    return p


def st17_risk_parity(P, I, syms, N, rebal=REBAL):
    """Equal-risk-contribution (risk-parity) across all 5, weekly rebalance."""
    def wf(i, allowed):
        iv = {}
        for s in allowed:
            a = I[s]["atr"][i]
            iv[s] = 1.0 / max(a / P[s]["C"][i], 1e-9)
        tot = sum(iv.values()) or 1.0
        return {s: iv[s] / tot for s in allowed}
    p = Port(len(syms), N, syms)
    on = [False] * len(syms)
    for i in range(260, N):
        p.set_marks(i, P)
        p.manage(i, P, trail=False)
        p.sync(on)
        if i % rebal == 0:
            for k, s in enumerate(syms):
                if not on[k]:
                    px = P[s]["C"][i]
                    if p.open_slot(k, i, px, px - STOP_ATR * I[s]["atr"][i], P, "17"):
                        on[k] = True
        p.mark_eod(i)
    return p


def st18_trend_gated(P, I, syms, N, top=3):
    """Top-3 momentum only when basket EMA50>EMA200; else cash."""
    n = len(syms)
    p = Port(n, N, syms)
    on = [False] * n
    for i in range(260, N):
        p.set_marks(i, P)
        p.manage(i, P, trail=False)
        p.sync(on)
        if i % REBAL == 0 and i >= 24:
            n_bull = sum(1 for s in syms if (not np.isnan(I[s]["e50"][i])) and (not np.isnan(I[s]["e200"][i])) and I[s]["e50"][i] > I[s]["e200"][i])
            allowed = syms if n_bull * 2 > len(syms) else []
            if allowed:
                rank = sorted(allowed, key=lambda s: -I[s]["r24"][i])[:top]
            else:
                rank = []
            for k, s in enumerate(syms):
                if s not in rank and on[k] and p.slot[k]["active"]:
                    p.close_slot(k, i, P[s]["C"][i] * (1 - SLIP))
                    on[k] = False
            for s in rank:
                k = syms.index(s)
                if not on[k]:
                    px = P[s]["C"][i]
                    if p.open_slot(k, i, px, px - STOP_ATR * I[s]["atr"][i], P, "18"):
                        on[k] = True
        p.mark_eod(i)
    return p


def st19_dd_control(P, I, syms, N, top=3, dd_lim=0.08):
    """Top-3 momentum; cut to 1 position when portfolio DD > 8%."""
    n = len(syms)
    p = Port(n, N, syms)
    on = [False] * n
    rank = []
    for i in range(260, N):
        p.set_marks(i, P)
        p.manage(i, P, trail=False)
        p.sync(on)
        cur_dd = (p.peak - p.equity_now()) / max(p.peak, 1e-9)
        keep = 1 if cur_dd > dd_lim else top
        if i % REBAL == 0 and i >= 24:
            rank = sorted(syms, key=lambda s: -I[s]["r24"][i])[:keep]
            for k, s in enumerate(syms):
                if s not in rank and on[k] and p.slot[k]["active"]:
                    p.close_slot(k, i, P[s]["C"][i] * (1 - SLIP))
                    on[k] = False
            for s in rank:
                k = syms.index(s)
                if not on[k]:
                    px = P[s]["C"][i]
                    if p.open_slot(k, i, px, px - STOP_ATR * I[s]["atr"][i], P, "19"):
                        on[k] = True
        elif cur_dd > dd_lim:
            # immediate de-risk between rebalances
            act = [k for k in range(n) if on[k] and p.slot[k]["active"]]  # slot indices
            for k in act[1:]:  # close all but the first active slot
                s = p.slot[k]["sym"]
                p.close_slot(k, i, P[s]["C"][i] * (1 - SLIP))
                on[k] = False
        p.mark_eod(i)
    return p


def st20_top2_fast(P, I, syms, N, rebal=72, risk=0.005):
    """Top-2 momentum, 3-day rebalance, 0.5% risk."""
    p = Port(2, N, syms[:2])
    on = []
    for i in range(260, N):
        p.set_marks(i, P)
        p.manage(i, P, trail=False)
        p.sync(on)
        if i % rebal == 0 and i >= 24:
            rank = sorted(syms, key=lambda s: -I[s]["r24"][i])
            for k in range(2):
                s = rank[k]
                sl = p.slot[k]
                if sl["active"] and sl["sym"] != s:
                    p.close_slot(k, i, P[sl["sym"]]["C"][i] * (1 - SLIP))
                if not sl["active"]:
                    px = P[s]["C"][i]
                    p.bind(k, s)
                    p.open_slot(k, i, px, px - STOP_ATR * I[s]["atr"][i], P, "20", risk=risk)
        p.mark_eod(i)
    return p


STRATS = [
    ("MP-01", "Cross-Sectional Momentum (top-3, 168h)", st01_crosssec_mom),
    ("MP-02", "EMA50/200 Golden Cross basket", st02_ema_cross),
    ("MP-03", "Donchian 20 breakout / 10-low exit", st03_donchian),
    ("MP-04", "ADX(14)>25 + EMA21/55", st04_adx),
    ("MP-05", "Triple-EMA ribbon 8/21/55", st05_triple_ema),
    ("MP-06", "Bollinger(20,2) lower-band MR", st06_boll_mr),
    ("MP-07", "RSI(2)<10 + close>SMA200 (24h hold)", st07_rsi2),
    ("MP-08", "BTC/ETH cointegration spread", st08_btc_eth_spread),
    ("MP-09", "Cross-sectional z-score <-1.5", st09_xsec_z),
    ("MP-10", "50-bar z-score <-2", st10_zscore50),
    ("MP-11", "ATR(14) 1.5x vol expansion", st11_atr_breakout),
    ("MP-12", "Bollinger squeeze + midline break", st12_squeeze),
    ("MP-13", "Relative Strength rotation top-2 (168h)", st13_top2_rot),
    ("MP-14", "MACD(12,26,9) crossover", st14_macd_x),
    ("MP-15", "Keltner(20,1.5ATR) squeeze break", st15_keltner),
    ("MP-16", "Inverse-ATR target-vol weights", st16_inv_atr),
    ("MP-17", "Equal-risk-contribution (weekly)", st17_risk_parity),
    ("MP-18", "Trend-filtered top-3 rotation", st18_trend_gated),
    ("MP-19", "DD-controlled top-3 rotation", st19_dd_control),
    ("MP-20", "Top-2 momentum, 3d rebal, 0.5% risk", st20_top2_fast),
]

REPORT_META = {
    "MP-01": (7.50, 0.59, 45, -9.56), "MP-02": (49.72, 0.65, 726, -54.52),
    "MP-03": (39.62, 0.41, 181, -47.81), "MP-04": (45.49, 0.49, 395, -52.22),
    "MP-05": (61.07, 0.50, 660, -64.92), "MP-06": (21.20, 0.88, 414, -23.84),
    "MP-07": (20.51, 0.82, 335, -25.02), "MP-08": (41.11, 0.46, 261, -41.50),
    "MP-09": (29.78, 0.82, 480, -45.42), "MP-10": (26.47, 0.73, 295, -30.21),
    "MP-11": (65.80, 0.31, 385, -69.68), "MP-12": (40.83, 0.47, 309, -42.74),
    "MP-13": (6.92, 1.67, 49, -10.13), "MP-14": (34.04, 0.58, 254, -40.77),
    "MP-15": (46.13, 0.41, 245, -53.07), "MP-16": (49.27, 0.45, 351, -51.21),
    "MP-17": (-3.41, 0.85, 57, -9.90), "MP-18": (-4.00, 0.62, 28, -9.61),
    "MP-19": (5.42, 1.51, 54, -10.32), "MP-20": (-10.58, 0.69, 119, -16.70),
}


def bench(P, N):
    """Equal-weight buy & hold of the universe, rebalanced once at entry."""
    syms = sorted(P)
    eq = EQ0
    w = EQ0 / len(syms)
    units = {s: w / P[s]["C"][0] for s in syms}
    curve = [EQ0]
    for i in range(1, N):
        eq = sum(units[s] * P[s]["C"][i] for s in syms)
        curve.append(eq)
    peak = EQ0; mdd = 0.0
    for v in curve:
        peak = max(peak, v)
        mdd = max(mdd, (peak - v) / peak)
    return dict(ret=(eq / EQ0 - 1) * 100, dd=mdd * 100, curve=curve)


def slice_ts(ts, frac):
    n = len(ts)
    a = int(n * frac[0]); b = int(n * frac[1])
    return ts[a:b]


def slice_panel(P_full, I_full, lo, hi):
    """Slice the precomputed panel to absolute index range [lo, hi).

    Indicators here are causal (rolling/ewm forward), so slicing at an offset
    introduces NO lookahead: value at j depends only on data <= j.
    """
    P = {s: {k: v[lo:hi] for k, v in d.items()} for s, d in P_full.items()}
    I = {s: {k: v[lo:hi] for k, v in d.items()}
         for s, d in I_full.items() if s != "_"}
    return P, I


def run_window(P, I, N, label):
    rows = []
    b = bench(P, N)
    for sid, name, fn in STRATS:
        try:
            p = fn(P, I, sorted(P), N)
        except Exception as e:
            if os.environ.get("MP20_TB"):
                import traceback
                traceback.print_exc()
            print(f"  {sid} ERROR {type(e).__name__} {str(e)[:90]}", flush=True)
            continue
        if p is None:
            continue
        m = p.metrics()
        m["id"] = sid; m["name"] = name; m["window"] = label
        rows.append(m)
    return rows, b


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "windows"
    D, ts = load_universe()
    syms = sorted(D)
    print(f"universe={syms} bars={len(ts)} "
          f"{pd.to_datetime(ts[0], unit='ms')} .. {pd.to_datetime(ts[-1], unit='ms')}", flush=True)
    P_full = panel(D, ts)
    I_full = precompute(P_full, len(ts))

    t_all = np.array(ts)
    WINDOWS = []
    t0 = int(pd.Timestamp("2026-03-01", tz="UTC").timestamp() * 1000)
    t1 = int(pd.Timestamp("2026-10-01", tz="UTC").timestamp() * 1000)
    lo = int(np.searchsorted(t_all, t0, "left"))
    hi = int(np.searchsorted(t_all, t1, "right"))
    WINDOWS.append(("REPORT 6mo 2026-03..09", lo, hi))
    WINDOWS.append(("FULL 2020-09..2026-09", 0, len(ts)))
    WINDOWS.append(("HALF-1", 0, len(ts) // 2))
    WINDOWS.append(("HALF-2", len(ts) // 2, len(ts)))
    # quarter windows for stability (no single regime decides)
    for q in range(4):
        WINDOWS.append((f"Q{q+1}", len(ts) * q // 4, len(ts) * (q + 1) // 4))

    allrows = []
    for label, lo, hi in WINDOWS:
        Pw, Iw = slice_panel(P_full, I_full, lo, hi)
        rows, b = run_window(Pw, Iw, hi - lo, label)
        sub = ts[lo:hi]
        print(f"\n===== {label}  bars={len(sub)}  B&H={b['ret']:+.2f}% DD {b['dd']:.1f}% =====", flush=True)
        print(f"{'ID':<6}{'ret%':>9}{'PF':>7}{'WR%':>7}{'n':>6}{'DD%':>8}{'Sharpe':>8}   name", flush=True)
        for m in rows:
            print(f"{m['id']:<6}{m['ret']:>9.2f}{m['pf']:>7.2f}{m['wr']:>7.1f}"
                  f"{m['n']:>6}{m['dd']:>8.1f}{m['sharpe']:>8.2f}   {m['name']}", flush=True)
        allrows += rows
    with open(os.path.join(ROOT, "data", "mp20_report_results.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["window", "id", "name", "ret_pct", "pf", "wr_pct", "n", "dd_pct", "sharpe"])
        for m in allrows:
            w.writerow([m["window"], m["id"], m["name"], round(m["ret"], 3), round(m["pf"], 4),
                        round(m["wr"], 2), m["n"], round(m["dd"], 2), round(m["sharpe"], 3)])
    print("\nwrote data/mp20_report_results.csv", flush=True)