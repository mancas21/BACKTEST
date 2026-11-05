#!/usr/bin/env python3
"""
xrp_neutral_engine.py — DELTA-NEUTRAL two-sided grid engine, Binance USDT-M perps.

Paper only. It places no orders, holds no keys and reads no account. It has NO
validated edge: the forward paper run IS the experiment.

WHY A NEW FILE AND NOT A FLAG ON grid_audit.simulate
-----------------------------------------------------
grid_audit.simulate is the VALIDATED engine behind the long-grid paper bot and
behind the research artifacts. Adding a `side` parameter to it changes its bytes,
which changes every run_id that hashed them, and silently invalidates the
forward record of a bot that is still running. This repo already paid for that
class of mistake once: the grid_core refactor produced 11,966 entry fills against
the validator's 5,233 and 4,080 grid rebuilds against 501. Two engines that
disagree is exactly the drift class that burns a paper record. So the neutral
book is a SEPARATE file, and code/xrp_neutral_audit.py proves it independently.

THE STRATEGY
------------
A two-sided grid on ONE perp, with the net delta bounded by construction:

  * LONG sub-book  : resting limit BUY at  centre - k*step, covered one step UP.
  * SHORT sub-book : resting limit SELL at centre + k*step, covered one step DOWN.
  * Same size both sides, so the book is delta-neutral whenever both sides are
    filled equally.
  * DELTA CAP: a level may not fill if it would push |net notional| past
    DELTA_MAX_PCT of equity. Neutrality is a hard bound, not a hope.
  * FUNDING is charged on the NET position, exactly as the exchange charges it.
    A balanced book therefore pays ~0 funding, which is the whole economic
    reason to be neutral on a perp: the validated long-grid bot is a funding
    PAYER ($188k on its XRP leg alone).
  * The grid RE-ANCHORS its centre when price drifts more than REBUILD_DRIFT half-
    grids away. Existing lots keep their own entry and cover prices, so re-anchoring
    costs no taker fee -- a real grid keeps its inventory.
  * A TREND OVERLAY stands the book down when the 1h price is far from its
    EMA200: a grid accumulates one-sided inventory in a trend and gets run over.
    Unlike the long grid's directional filter, this one is SYMMETRIC -- it stands
    down in a bull AND a bear, which is what keeps the book neutral.
  * A hard stop flattens BOTH sides at once.

WHAT IT REPORTS
---------------
Per-bar equity, net delta, gross notional, funding, fees, and the per-trade
closed P&L -- everything the kill criteria need.

KILL CRITERIA (repo protocol, applied to the forward record in
code/xrp_neutral_audit.py): OOS PF < 1 = KILL, no rescue loops. Ex-cost PF > 1.2
required. n >= 30 closed trades. commission/gross < 30-40%. Green in >= 2/3
periods. Walk-forward must hold.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict

import numpy as np

# ── constants ────────────────────────────────────────────────────────────────
# Identical to the validated long-grid engine wherever the quantity means the
# same thing, so the two books are comparable. New quantities are marked.
GRID_LEVELS = 5
ATR_PERIOD = 20
ATR_MULT = 5.0
HTF_EMA = 200
HTF_LIMIT = 250
EQUITY_PCT = 0.25          # per level, of CURRENT equity, as notional
LEVERAGE = 3.0
MAINT_MARGIN = 0.005
STOP_ATR_MULT = 0.5
COOLDOWN_BARS = 96
REBUILD_DRIFT = 1.5
WARMUP_BARS = 28
MAKER_FEE = 0.0002
K = float(os.environ.get('XRP_STRESS_K', '0')) / 1e4          # resting post-only earns the touch
TAKER_FEE = 0.0005
MAKER_SLIP = 0.0
FLAT_SLIP = 0.0005
INIT = 10000.0
DELTA_MAX_PCT = 0.50        # NEW: |net notional| cap, fraction of equity
TREND_BAND = 0.02           # NEW: |close1h/ema200 - 1| above this = stand down


# ── primitives (self-contained: the VPS has no cvrmd_port) ──────────────────
def rma(x, n):
    out = np.full(len(x), np.nan)
    a = 1.0 / n
    acc = np.nan
    for i, v in enumerate(x):
        if np.isnan(v):
            continue
        acc = v if np.isnan(acc) else acc + a * (v - acc)
        out[i] = acc
    return out


def atr(h, l, c, n=ATR_PERIOD):
    pc = np.roll(c, 1)
    pc[0] = c[0]
    return rma(np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc))), n)


def ema(x, span):
    a = 2.0 / (span + 1.0)
    out = np.empty(len(x))
    acc = x[0]
    out[0] = acc
    for i in range(1, len(x)):
        acc += a * (x[i] - acc)
        out[i] = acc
    return out


def resample_1h(bars15):
    """15m bars -> 1h bars, Binance-style (open=first, close=last)."""
    out = []
    cur_t = None
    o = h = l = c = v = 0.0
    for b in bars15:
        bt = b[0] - (b[0] % 3600000)
        if bt != cur_t:
            if cur_t is not None:
                out.append((cur_t, o, h, l, c, v))
            cur_t, o, h, l, c, v = bt, b[1], b[2], b[3], b[4], b[5]
        else:
            h = max(h, b[2])
            l = min(l, b[3])
            c = b[4]
            v += b[5]
    if cur_t is not None:
        out.append((cur_t, o, h, l, c, v))
    return out


def trend_strength(bars15):
    """|close_1h / ema200_1h - 1| mapped onto the 15m timeline, NaN until warm.

    The long grid's gate is DIRECTIONAL (price above the EMA200 = bull). A neutral
    book needs a SYMMETRIC risk control, so this measures DISTANCE from the EMA
    instead of SIDE of it: far from the mean in EITHER direction is the regime
    where a grid accumulates one-sided inventory and dies.
    """
    b1 = resample_1h(bars15)
    if len(b1) < HTF_LIMIT:
        return np.full(len(bars15), np.nan)
    T1 = np.array([b[0] for b in b1], dtype=np.int64)
    C1 = np.array([b[4] for b in b1])
    e = ema(C1, HTF_EMA)
    strength = np.abs(C1 / e - 1.0)
    idx = np.clip(np.searchsorted(T1, np.array([b[0] for b in bars15]), side="right") - 1,
                  0, len(T1) - 1)
    return strength[idx]


def funding_events(sym, T, fund_dir=None):
    """(rate, is_event) per bar, from real Binance funding prints.

    Convention (the grid family's): a settlement at time t is mapped to the first
    bar whose OPEN is at or after t, and charged on that bar's close against the
    NET position held -- the same convention the validated engine uses, so the
    two books carry the same funding accounting.
    """
    if fund_dir is None:
        fund_dir = os.environ.get("XRP_BOT_FUND_DIR") or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "binance_funding")
    rate = np.zeros(len(T))
    ev = np.zeros(len(T), bool)
    n = 0
    p = os.path.join(fund_dir, f"{sym}_funding.json")
    if not os.path.exists(p):
        return rate, ev, 0
    f = json.load(open(p, encoding="utf-8"))
    for x in f:
        ts_e = int(x["t"])
        j = int(np.searchsorted(T, ts_e, side="left"))
        if j < len(T):
            ev[j] = True
            rate[j] = float(x["r"])
            n += 1
    return rate, ev, n


# ── the engine ──────────────────────────────────────────────────────────────
def simulate(bars, sym, *, leg_fee=MAKER_FEE, flat_fee=TAKER_FEE,
             leg_slip=MAKER_SLIP, flat_slip=FLAT_SLIP, funding=True,
             delta_max_pct=DELTA_MAX_PCT, trend_band=TREND_BAND,
             stop_atr_mult=STOP_ATR_MULT, cover_mult=1.0,
             allow_short=True, init=INIT, fund_dir=None, track=None):
    """Run the neutral book over `bars` (15m). Returns final equity.

    bars: list of (open_ts_ms, open, high, low, close, volume), oldest first.

    stop_atr_mult : distance of the hard stop beyond the outermost level, in ATR.
    cover_mult    : a level covers at step*cover_mult away. 1.0 = the grid's own
                    spacing (small wins, big stop -> poor R:R); larger values
                    trade a bigger target against the same stop.
    allow_short   : False gives a LONG-ONLY book. It exists so the NEUTRALITY claim
                    can be falsified: if the two-sided book performs like the
                    long-only one, the neutrality is cosmetic and the result is
                    directional beta, not a neutral edge.
    """
    n = len(bars)
    T = np.array([b[0] for b in bars], dtype=np.int64)
    O = np.array([b[1] for b in bars], dtype=float)
    H = np.array([b[2] for b in bars], dtype=float)
    L = np.array([b[3] for b in bars], dtype=float)
    C = np.array([b[4] for b in bars], dtype=float)
    V = np.array([b[5] for b in bars], dtype=float)

    a = atr(H, L, C)
    fr, fev, n_fund = funding_events(sym, T, fund_dir) if funding else (
        np.zeros(n), np.zeros(n, bool), 0)
    strength = trend_strength(bars)

    cash = float(init)
    # lot = [qty(signed), fill_px, cover_px, fees_paid_on_lot]
    lots = []
    # resting entry orders: [px, side(+1 long / -1 short), qty]
    orders = []
    state = "idle"
    cooldown_left = 0
    bars_since = 0
    center = half = step = 0.0
    t = 0                                   # bar being processed (closure-visible)

    grids_built = fills = n_cycles = same_bar_covers = 0
    fund_paid = fee_paid = 0.0
    reasons = defaultdict(int)
    closed_pnl, closed_t = [], []
    covered_pnl, covered_t = [], []
    fill_times = []
    trades = []                  # one dict per CLOSED lot: the audit and the paper
                                # event log both need the actual prices, not just P&L
    eq_curve = np.zeros(n)
    delta_curve = np.zeros(n)
    gross_curve = np.zeros(n)
    expo_curve = np.zeros(n)
    peak = float(init)
    mdd = 0.0
    max_abs_delta_pct = 0.0
    max_delta_fill_pct = 0.0
    delta_cap_hits = 0
    stand_down_bars = 0

    def qty_now():
        return sum(l[0] for l in lots)

    def book_equity(px):
        # cash + signed inventory value. A short lot has negative qty, so its
        # market value is negative and the identity holds for a two-sided book.
        return cash + sum(l[0] * px for l in lots)

    def close_lot(lot, px, fee, slip_px, kind):
        """Close ONE lot in full at `px`; returns realised P&L.

        Closing lot-by-lot (never by net amount) is deliberate: a two-sided book
        has a net quantity that can be ~0 while both sides hold inventory, and
        a net-amount close would leave the book untouched.
        """
        nonlocal cash, fee_paid
        q = lot[0]
        side = 1.0 if q > 0 else -1.0
        fill_px = px * (1 - slip_px * side)
        cash += q * fill_px
        f = abs(q * fill_px) * fee
        cash -= f
        fee_paid += f
        realised = q * (fill_px - lot[1]) - lot[3] - f
        lot[3] += f
        lots.remove(lot)
        closed_pnl.append(realised)
        closed_t.append(int(T[t]))
        trades.append(dict(dir=1 if q > 0 else -1, qty=abs(q), entry=lot[1], exit=fill_px,
                           cover=lot[2], pnl=realised, fees=lot[3] + f, reason=kind,
                           ts=int(T[t])))
        if kind == "cover":
            covered_pnl.append(realised)
            covered_t.append(int(T[t]))
        return realised

    def flatten(px, fee, slip_px, kind):
        """Close every lot, each on its own side."""
        for lot in list(lots):
            close_lot(lot, px, fee, slip_px, kind)

    def ladder(center_px, equity):
        """Arm a fresh two-sided ladder around `center_px`. Returns the step."""
        new = []
        q = EQUITY_PCT * equity / center_px
        for i in range(GRID_LEVELS):
            new.append([center_px - step * (i + 1), +1, q])
            if allow_short:
                new.append([center_px + step * (i + 1), -1, q])
        return new

    for t in range(n):
        bars_since += 1
        eq = book_equity(C[t])
        eq_curve[t] = eq
        net_q = qty_now()
        delta_curve[t] = net_q * C[t]
        gross_curve[t] = sum(abs(l[0]) for l in lots) * C[t]
        expo_curve[t] = gross_curve[t] / max(eq, 1e-9)
        if eq > 0:
            max_abs_delta_pct = max(max_abs_delta_pct, abs(net_q * C[t]) / eq)
        peak = max(peak, eq)
        mdd = max(mdd, (peak - eq) / max(peak, 1e-9))

        if state == "cooldown":
            cooldown_left -= 1
            if cooldown_left <= 0:
                state = "idle"
            continue
        if bars_since < WARMUP_BARS:
            continue
        atr_prev = a[t - 1] if t >= 1 else np.nan
        if np.isnan(atr_prev) or atr_prev <= 0:
            continue
        close_now = C[t]
        st = strength[t]
        trending = (not np.isnan(st)) and st > trend_band

        # ── the symmetric risk overlay: stand down in a strong trend ──
        if trending:
            stand_down_bars += 1
            if lots:
                flatten(close_now, flat_fee, flat_slip, "trend")
                reasons["trend_flatten"] += 1
            orders = []
            state = "idle"
            continue

        # ── IDLE -> build the ladder ──
        if state == "idle":
            half = atr_prev * ATR_MULT
            step = half / GRID_LEVELS
            center = C[t - 1]
            orders = ladder(center, book_equity(center))
            state = "working"
            grids_built += 1
            continue

        # ── WORKING ──
        # 1. resting entries fill. The ladder was armed at the close of the
        #    previous bar, so nothing can fill on the bar it was placed.
        for o_ in list(orders):
            px, side, q = o_
            touched = (L[t] < px * (1 - K)) if side > 0 else (H[t] > px * (1 + K))
            if not touched:
                continue
            fill_px = px * (1 + leg_slip * side)
            # DELTA CAP: refuse the fill if it would breach the neutrality bound
            net_after = qty_now() + side * q
            cap = delta_max_pct * max(book_equity(C[t]), 0.0)
            if abs(net_after * fill_px) > cap:
                delta_cap_hits += 1
                continue
            f = abs(q * fill_px) * leg_fee
            if side > 0:
                cash -= q * fill_px + f
                cover = px + step * cover_mult
            else:
                cash += q * fill_px - f
                cover = px - step * cover_mult
            fee_paid += f
            lots.append([side * q, fill_px, cover, f, t])
            orders.remove(o_)
            fills += 1
            fill_times.append(int(T[t]))
            # delta AT the moment of the fill, against contemporaneous equity: this
            # is the quantity the cap bounds. The mark-to-market ratio reported
            # separately can exceed the cap later, because equity can fall after
            # the fill while the notional stays put.
            eq_now = book_equity(C[t])
            if eq_now > 0:
                max_delta_fill_pct = max(max_delta_fill_pct,
                                         abs(qty_now() * fill_px) / eq_now * 100)

        # 2. resting covers fill -- every touched cover, each on its own lot
        for lot in list(lots):
            px = lot[2]
            if lot[4] == t:
                same_bar_covers += 1
                if track is not None:
                    track["same_bar_covers"] = same_bar_covers
            touched = (H[t] >= px) if lot[0] > 0 else (L[t] <= px)
            if touched:
                close_lot(lot, px, leg_fee, leg_slip, "cover")
                n_cycles += 1

        # 3. hard stop: price closes beyond the outermost level by stop_atr_mult ATR
        stop_lo = (center - half) - atr_prev * stop_atr_mult
        stop_hi = (center + half) + atr_prev * stop_atr_mult
        if (close_now <= stop_lo) or (close_now >= stop_hi):
            if lots:
                flatten(close_now, flat_fee, flat_slip, "stop")
            reasons["stop"] += 1
            orders = []
            state = "cooldown"
            cooldown_left = COOLDOWN_BARS
            continue

        # 4. re-anchor the centre when price has drifted; existing lots keep
        #    their own entry and cover, so re-anchoring costs no taker fee.
        if abs(close_now - center) > half * REBUILD_DRIFT:
            center = close_now
            half = atr_prev * ATR_MULT
            step = half / GRID_LEVELS
            orders = ladder(center, book_equity(close_now))
            reasons["reanchor"] += 1

        # 5. funding on the NET held position, exactly as the exchange charges it
        if funding and lots and fev[t]:
            f = qty_now() * C[t] * fr[t]
            cash -= f
            fund_paid += f

    eq = book_equity(C[-1])
    if lots and eq < -1e-6:
        raise AssertionError(
            f"{sym}: equity ${eq:,.2f} with inventory "
            f"${sum(l[0]*C[-1] for l in lots):,.0f} and cash ${cash:,.2f}. "
            f"book_equity is not cash + inventory value.")
    if track is not None:
        track.update(dict(
            eq_curve=eq_curve, delta_curve=delta_curve, gross_curve=gross_curve,
            expo_curve=expo_curve, grids=grids_built, fills=fills, cycles=n_cycles,
            fund=fund_paid, fees=fee_paid, reasons=dict(reasons),
            closed_pnl=closed_pnl, closed_t=closed_t,
            covered_pnl=covered_pnl, covered_t=covered_t,
            fill_times=fill_times, trades=trades, mdd=mdd * 100, eq=eq, open_lots=len(lots),
            max_abs_delta_pct=max_abs_delta_pct * 100,
            max_delta_fill_pct=max_delta_fill_pct,
            delta_cap_hits=delta_cap_hits, stand_down_bars=stand_down_bars,
            n_funding_events=n_fund, init=init))
    return eq


def metrics(pnls):
    """(profit_factor, win_rate_pct, n) — the repo's convention."""
    a = np.array(pnls) if pnls else np.zeros(1)
    w = a[a > 0]
    l = a[a <= 0]
    pf = (w.sum() / abs(l.sum())) if len(l) and l.sum() != 0 else (
        float("inf") if len(w) else 0.0)
    return pf, 100.0 * len(w) / max(len(a), 1), len(a)
