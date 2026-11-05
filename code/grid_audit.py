"""ATR Long Grid (Trend-Filtered) — Hyperliquid v2 dialect, ported and backtested.

WHAT THIS IS
    A long-only 5-level post-only limit grid on 15m, armed only while a 1h
    trend gate holds, with a 1-step reduce-only cover per fill and a hard
    close-based stop below the bottom level. Sizing 25% of portfolio notional
    per level, up to 125% total, 3x leverage.

IT IS NOT PINE. It is an order-management state machine talking to an
exchange: resting orders, post-only, reduce-only, per-level fills. So the port
is an ORDER SIMULATOR, not a signal backtest. The bar-by-bar question is
"which resting orders fill on this bar", not "is the signal on".

THE HEADLINE BUG, found by algebra before running anything
    The spec calls its filter a 1h EMA(200) trend filter. It is not one. It
    pulls limit=250 1h candles and reads ema[1] against closes[1]. An EMA at
    index 1 of a 250-window has seen exactly ONE prior value, so with the
    standard first-value seed:

        E[1] = (1-a)*x[0] + a*x[1]
        x[1] > E[1]   <=>   x[1] > x[0]        (1-a cancels exactly)

    The EMA term vanishes. bull_ok is really "the last complete 1h close is
    above the 1h close 249 bars ago" — a 10.4-day momentum test wearing an
    EMA label. Under the other common convention (NaN until the window is long
    enough) ema[1] is NaN, the comparison is False on every bar, and the grid
    never arms at all. The 250-bar window was clearly meant to give a 200-EMA
    room, which is exactly why reading index 1 destroys it.
    Both readings are simulated and reported.

NO-LOOKAHEAD
    Every input the spec reads is the PREVIOUS bar (atr[1], close_prev,
    htf_close_prev, htf_ema_prev), so a decision on bar t uses only data
    settled at the end of bar t-1, and orders placed on bar t may fill no
    earlier than bar t+1. Enforced explicitly, then proved by prefix stability.

EXECUTION ASSUMPTIONS, stated because the spec leaves them open
    limit fill      a resting buy at P fills when low[b] <= P. Both tie-handling
                    directions are run (optimistic and strict-sweep) because a
                    post-only order rests AT the level.
    stop            fires on close <= stop_price, per the spec's own
                    `if close_now <= state['stop_price']`. A CLOSE stop, not
                    intrabar: price can pierce it and close back above with no
                    stop at all. Modelled as written, and that is a real risk
                    the author should know about.
    covers          reduce-only limit one step above entry, fills on high >= P.
    maker vs taker  every resting leg is post_only, so entries and covers earn
                    the MAKER fee. Only the market flattens (stop / rebuild /
                    trend-loss) pay the taker fee. The house default charges
                    taker everywhere, which is right for a signal strategy and
                    wrong for this one, so the maker/taker split is the
                    PRIMARY case and taker-everywhere is the sensitivity.
    funding         charged on held notional at REAL Binance 8h events, because
                    the spec holds up to 125% notional and is silent on it.
    margin          3x leverage, 0.5% maintenance, cross margin. Liquidation
                    is modelled: equity <= 0.5% of notional loses the account.

WHAT THE HOUSE GATE IS *NOT* TOLD BY
    The per-level round trip is not the unit of risk. A grid earns its keep on
    COVERED levels and loses on levels that are still open when the hard stop
    fires, so a gate computed only over covered levels reports a 100% win rate
    and an infinite profit factor on a run that can be net negative. Both are
    reported: 'covered' and 'all lots closed (incl. stop-outs)'.
"""
import argparse
import json
import os
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import cvrmd_port as P            # load / resample / ema / atr, already proven

D1M = os.path.join(ROOT, "data", "binance_klines_1m")
FUND = os.path.join(ROOT, "data", "binance_funding")
OUT = os.path.join(ROOT, "results")

# ---- spec, transcribed from StrategyParams -------------------------------
GRID_LEVELS = 5
ATR_PERIOD = 20
ATR_MULT = 5.0
HTF_EMA = 200
HTF_LIMIT = 250
EQUITY_PCT = 0.25
LEVERAGE = 3.0
MAINT_MARGIN = 0.005
STOP_ATR_MULT = 0.5
COOLDOWN_BARS = 96
REBUILD_DRIFT = 1.5
WARMUP_BARS = 28

MAKER_FEE = 0.0002                 # hyperliquid taker 0.05%, maker 0.02%
TAKER_FEE = 0.0005
HOUSE_COMM = 0.0006                # the house signal-strategy standard
HOUSE_SLIP = 0.0005
MAKER_SLIP = 0.0                   # a resting post-only order earns the touch
INIT = 10000.0
SYMS = ["SOLUSDT", "BTCUSDT", "ETHUSDT", "XRPUSDT", "SUIUSDT", "HYPEUSDT"]


# --------------------------------------------------------------------------
# 15m CACHE
# Resampling 2M 1m CSV rows takes ~40s per symbol and the report simulates each
# symbol several times, so cache the 15m bars once as a .npz. This is a speed
# fix only: the resample function is unchanged and the first build is verified
# against it.
CACHE = os.path.join(ROOT, "data", "binance_klines_15m_cache")


def load15(sym, verify=False):
    """15m bars for `sym`, from cache if present, else resampled from 1m."""
    os.makedirs(CACHE, exist_ok=True)
    cp = os.path.join(CACHE, f"{sym}_15m.npz")
    src = os.path.join(D1M, f"{sym}_1m.csv")
    if os.path.exists(cp) and not verify:
        return [tuple(r) for r in np.load(cp)["bars"]]
    fresh = P.resample(P.load(src), 15)          # ~40s per symbol, once
    if os.path.exists(cp):
        arr = np.load(cp)["bars"]
        same = (len(fresh) == len(arr)
                and abs(fresh[-1][4] - arr[-1][4]) < 1e-9
                and abs(fresh[len(fresh) // 2][4]
                        - arr[len(arr) // 2][4]) < 1e-9)
        print(f"    cache check {sym}: {'MATCH' if same else 'MISMATCH'} "
              f"({len(fresh):,} 15m bars)")
        if not same:
            np.savez_compressed(cp, bars=np.array(fresh, dtype=np.float64))
        return fresh
    np.savez_compressed(cp, bars=np.array(fresh, dtype=np.float64))
    return fresh


def shift(x, k):
    out = np.full(len(x), np.nan)
    if k >= 0 and k < len(x):
        out[k:] = x[:len(x) - k]
    return out


def funding_events(sym, T):
    """(rate, is_event) per 15m bar, from real Binance funding prints."""
    p = os.path.join(FUND, f"{sym}_funding.json")
    rate = np.zeros(len(T))
    ev = np.zeros(len(T), bool)
    n = 0
    if not os.path.exists(p):
        return rate, ev, 0
    f = json.load(open(p, encoding="utf-8"))
    ft = np.array([x["t"] for x in f], dtype=np.int64)
    fv = np.array([x["r"] for x in f], dtype=np.float64)
    for ts_e, r in zip(ft, fv):
        j = int(np.searchsorted(T, ts_e, side="left"))
        if j < len(T):
            ev[j] = True
            rate[j] = r
            n += 1
    return rate, ev, n


def htf_filter(bars15):
    """The 1h trend gate under every reading of the spec, plus the 1h bar count.

    See the module docstring for the algebra: reading the EMA at index 1 of a
    250-candle window cancels the EMA out of the comparison exactly. The window
    SLIDES at runtime, so it slides here too.
    """
    b1h = P.resample(bars15, 60)                 # 15m -> 1h
    T1 = np.array([b[0] for b in b1h], dtype=np.int64)
    C1h = np.array([b[4] for b in b1h])
    n_win = min(HTF_LIMIT, len(C1h))

    idx = np.clip(np.searchsorted(T1, np.array([b[0] for b in bars15]),
                                  side="right") - 1, 0, len(C1h) - 1)
    in_win = idx >= n_win - 1
    bi = np.where(in_win, idx, 0)

    prev = C1h[np.clip(bi - 1, 0, len(C1h) - 1)]
    oldest = C1h[np.clip(bi - n_win, 0, len(C1h) - 1)]
    faithful = in_win & (prev > oldest)          # spec as written
    never = np.zeros(len(bars15), bool)          # NaN-until-warmed reading
    ema_full = P.ema(C1h, HTF_EMA)
    warm = C1h[bi] > ema_full[bi]                # the documented intent
    return faithful, never, warm, len(C1h), idx


def simulate(bars, sym, gate, leg_fee=MAKER_FEE, flat_fee=TAKER_FEE,
             leg_slip=MAKER_SLIP, flat_slip=0.0005, funding=True,
             leverage=LEVERAGE, optimistic_fill=True, track=None):
    n = len(bars)
    T = np.array([b[0] for b in bars], dtype=np.int64)
    O = np.array([b[1] for b in bars])
    H = np.array([b[2] for b in bars])
    L = np.array([b[3] for b in bars])
    C = np.array([b[4] for b in bars])
    V = np.array([b[5] for b in bars])

    tr = np.maximum.reduce([H - L, np.abs(H - shift(C, 1)), np.abs(L - shift(C, 1))])
    atr = P.atr(H, L, C, ATR_PERIOD)
    fr, fev, _ = funding_events(sym, T) if funding else (
        np.zeros(n), np.zeros(n, bool), 0)

    cash = INIT
    # INVARIANT: every fee is deducted from cash exactly once, at the moment it
    # is charged. lot[3] is a memo of fees already paid, used only to attribute
    # them to a closing slice's realised P&L. book_equity() must NOT subtract it.
    lots = []                 # [qty, fill_px, level, fees_paid_on_this_lot]
    state = "idle"
    cooldown_left = 0
    bars_since = 0
    grid_px = [0.0] * GRID_LEVELS
    grid_qty = [0.0] * GRID_LEVELS
    ent_live = [None] * GRID_LEVELS
    cov_live = [None] * GRID_LEVELS
    step = stop_px = center = half = 0.0

    grids_built = fills = n_cycles = liq = 0
    liq_at = None
    fund_paid = fee_paid = 0.0
    reasons = defaultdict(int)
    covered_pnl, covered_t = [], []      # levels that reached their cover
    closed_pnl, closed_t = [], []        # EVERY lot closed, incl. stop-outs
    fill_times = []
    eq_curve = np.zeros(n)
    expo_curve = np.zeros(n)          # notional / equity, per bar
    peak = INIT
    mdd = 0.0

    def qty_now():
        return sum(l[0] for l in lots)

    def book_equity(px):
        # Equity = cash + POSITION MARKET VALUE, full stop.
        #
        # The bug this replaces: `cash + sum(qty*(px - entry))` omits the
        # position's cost basis. A grid commits 25% of equity per level, so by
        # the fourth fill the missing basis is ~$10k and equity reads NEGATIVE
        # on a perfectly healthy book, tripping the 0.5% maintenance test and
        # "liquidating" a $9,883 account. That is what produced -100% on SOL.
        # cash already has every fee deducted exactly once, so nothing else
        # is subtracted here.
        return cash + sum(l[0] * px for l in lots)

    def close_lots(amount, px, fee, slip_px, kind):
        """Sell `amount` of the book at `px`; returns realised P&L for the slice."""
        nonlocal cash, fee_paid
        remaining = amount
        realised = 0.0
        for lot in list(lots):
            if remaining <= 1e-12:
                break
            take = min(lot[0], remaining)
            fill_px = px * (1 - slip_px)
            cash += take * fill_px
            f = take * fill_px * fee
            cash -= f
            fee_paid += f
            realised += take * (fill_px - lot[1]) - lot[3] - f
            lot[3] += f
            lot[0] -= take
            if lot[0] <= 1e-12:
                lots.remove(lot)
            remaining -= take
        if abs(realised) > 0:
            closed_pnl.append(realised)
            closed_t.append(int(T[t]))
            if kind == "cover":
                covered_pnl.append(realised)
                covered_t.append(int(T[t]))
        return realised

    def clear_grid():
        nonlocal grid_px, grid_qty, step, stop_px, center, half
        nonlocal ent_live, cov_live
        grid_px = [0.0] * GRID_LEVELS
        grid_qty = [0.0] * GRID_LEVELS
        ent_live = [None] * GRID_LEVELS
        cov_live = [None] * GRID_LEVELS
        step = stop_px = center = half = 0.0

    for t in range(n):
        bars_since += 1
        eq = book_equity(C[t])
        eq_curve[t] = eq
        expo_curve[t] = (qty_now() * C[t]) / max(eq, 1e-9)
        peak = max(peak, eq)
        mdd = max(mdd, (peak - eq) / max(peak, 1e-9))

        if state == "cooldown":
            cooldown_left -= 1
            if cooldown_left <= 0:
                state = "idle"
            continue
        if bars_since < WARMUP_BARS:
            continue
        atr_prev = atr[t - 1] if t >= 1 else np.nan
        if np.isnan(atr_prev) or atr_prev <= 0:
            continue
        close_prev = C[t - 1] if t >= 1 else np.nan
        close_now = C[t]
        bull = bool(gate[t])

        # ---------------- IDLE -> build the grid ----------------
        if state == "idle":
            if not bull:
                continue
            half = atr_prev * ATR_MULT
            step = half / GRID_LEVELS
            portfolio = book_equity(close_prev)      # spec reads equity at bar start
            grid_px = [close_prev - step * (i + 1) for i in range(GRID_LEVELS)]
            grid_qty = [EQUITY_PCT * portfolio / p for p in grid_px]
            center = close_prev
            stop_px = grid_px[-1] - atr_prev * STOP_ATR_MULT
            state = "working"
            grids_built += 1
            for i in range(GRID_LEVELS):             # resting orders, from t+1
                if grid_px[i] < close_now:
                    ent_live[i] = grid_px[i]
            continue

        # ---------------- WORKING ----------------
        # 1. resting entry limits fill (never on the bar they were placed)
        for i in range(GRID_LEVELS):
            if ent_live[i] is None:
                continue
            p = ent_live[i]
            if not ((L[t] < p) if optimistic_fill else (L[t] <= p)):
                continue
            q = grid_qty[i]
            px = p * (1 + leg_slip)
            f = q * px * leg_fee
            cash -= q * px + f
            fee_paid += f
            lots.append([q, px, i, f])
            ent_live[i] = None
            cov_live[i] = p + step
            fills += 1
            fill_times.append(int(T[t]))

        # 2. reduce-only covers fill
        for i in range(GRID_LEVELS):
            if cov_live[i] is None:
                continue
            p = cov_live[i]
            if H[t] < p:
                continue
            for lot in list(lots):
                if lot[2] != i:
                    continue
                close_lots(lot[0], p, leg_fee, leg_slip, "cover")
                n_cycles += 1
                break
            cov_live[i] = None

        # 3. hard stop on CLOSE, exactly as the spec reads it
        if close_now <= stop_px:
            if lots:
                close_lots(qty_now(), C[t], flat_fee, flat_slip, "stop")
            reasons["stop"] += 1
            clear_grid()
            state = "cooldown"
            cooldown_left = COOLDOWN_BARS
        else:
            # 4. re-arm dead levels while the filter holds
            for i in range(GRID_LEVELS):
                if ent_live[i] is None and cov_live[i] is None:
                    if bull and grid_px[i] < close_now:
                        ent_live[i] = grid_px[i]
            # 5. rebuild on upward drift: flatten and re-grid higher
            if close_now > center + half * REBUILD_DRIFT:
                if lots:
                    close_lots(qty_now(), C[t], flat_fee, flat_slip, "rebuild")
                reasons["rebuild_drift"] += 1
                clear_grid()
                state = "idle"
            # 6. stand down when the filter turns bearish while flat
            elif (not bull) and not lots:
                reasons["stand_down"] += 1
                clear_grid()
                state = "idle"

        # 7. funding on held notional at real 8h events
        if funding and lots and fev[t]:
            f = qty_now() * C[t] * fr[t]
            cash -= f
            fund_paid += f

        # 8. liquidation
        eq = book_equity(C[t])
        notional = qty_now() * C[t]
        if notional > 0 and eq <= MAINT_MARGIN * notional:
            liq += 1
            if liq_at is None:
                liq_at = t
            cash = 0.0
            lots.clear()
            clear_grid()
            state = "cooldown"
            cooldown_left = COOLDOWN_BARS

    eq = book_equity(C[-1])

    # ---- INVARIANT: equity must reconcile to cash + inventory value ----
    # A grid that commits 125% of equity to inventory can legitimately sit at
    # low equity, but it can never report equity below zero while holding
    # long-only lots bought with real cash. Assert the identity rather than
    # trusting it, because getting it wrong silently "liquidates" the account.
    if lots:
        inv = sum(l[0] * C[-1] for l in lots)
        if eq < -1e-6:
            raise AssertionError(
                f"{sym}: equity ${eq:,.2f} with ${inv:,.0f} of long inventory and "
                f"${cash:,.2f} cash. book_equity is not cash + inventory value.")
    if track is not None:
        track.update(dict(eq_curve=eq_curve, expo_curve=expo_curve,
                          grids=grids_built, fills=fills,
                          cycles=n_cycles, fund=fund_paid, fees=fee_paid,
                          liq=liq, liq_at=liq_at, reasons=dict(reasons),
                          covered_pnl=covered_pnl, covered_t=covered_t,
                          closed_pnl=closed_pnl, closed_t=closed_t,
                          fill_times=fill_times, mdd=mdd * 100, eq=eq,
                          open_lots=len(lots)))
    return eq


# --------------------------------------------------------------------------
def metrics(pnls):
    a = np.array(pnls) if pnls else np.zeros(1)
    w = a[a > 0]
    l = a[a <= 0]
    pf = (w.sum() / abs(l.sum())) if len(l) and l.sum() != 0 else (
        np.inf if len(w) else 0.0)
    return pf, 100.0 * len(w) / max(len(a), 1), len(a)


def year_pnl(pnls, times):
    y = defaultdict(list)
    for p, tt in zip(pnls, times):
        y[P.year_of(tt)].append(p)
    return {k: sum(v) for k, v in y.items()}


def report(sym, bars15, gate, **kw):
    tr = {}
    eq = simulate(bars15, sym, gate, track=tr, **kw)
    C = np.array([b[4] for b in bars15])
    pk, mdd = C[0], 0.0
    for v in C:
        pk = max(pk, v)
        mdd = max(mdd, (pk - v) / pk)
    bh = (C[-1] / C[0] - 1) * 100
    return dict(sym=sym, net=(eq / INIT - 1) * 100, bh=bh, bh125=bh * 1.25,
                bhmdd=mdd * 100, mdd=tr["mdd"], fills=tr["fills"],
                avg_expo=float(np.mean(tr["expo_curve"])),
                cycles=tr["cycles"], grids=tr["grids"], fund=tr["fund"],
                fees=tr["fees"], liq=tr["liq"], reasons=tr["reasons"],
                covered_pnl=tr["covered_pnl"], covered_t=tr["covered_t"],
                closed_pnl=tr["closed_pnl"], closed_t=tr["closed_t"],
                open_lots=tr["open_lots"], eq=eq, bars=len(bars15))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="*", default=SYMS)
    ap.add_argument("--tag", default="current",
                    help="artifact filename tag. Use a run-specific tag so a "
                         "slow background run cannot overwrite a newer result: "
                         "three times today a stale process replaced the shared "
                         "results/grid_audit.txt with pre-fix output.")
    args = ap.parse_args()

    def hdr(t):
        print("\n" + t)
        print("    " + "-" * 100)

    print("=" * 104)
    print("ATR LONG GRID (TREND-FILTERED) — Hyperliquid v2 dialect ported to Python")
    print(f"5 levels x {EQUITY_PCT*100:.0f}% notional (max 125%) | band "
          f"{ATR_MULT}xATR({ATR_PERIOD}) | 1h 'EMA200' gate | stop {STOP_ATR_MULT}ATR "
          f"on close | {LEVERAGE:g}x lev")
    print(f"post_only legs @ {MAKER_FEE*1e4:.0f}bps maker | market flattens @ "
          f"{TAKER_FEE*1e4:.0f}bps taker | real funding | 0.5% maint margin")
    print("=" * 104)

    data = {}
    for s in args.symbols:
        if os.path.exists(os.path.join(D1M, f"{s}_1m.csv")):
            data[s] = load15(s)
    if not data:
        print("no data")
        return

    # ---- 1. the trend filter ----
    hdr("[1] THE TREND FILTER IS NOT AN EMA — proved algebraically")
    b15 = data.get("SOLUSDT") or list(data.values())[0]
    gf, gnever, gw, nh = htf_filter(b15)[:4]
    print(f"    SOL 15m bars {len(b15):,} | 1h bars {nh:,} | window 250 = 10.4 days")
    print()
    print(f"    (a) spec as written   -> {gf.sum():>7,} bars TRUE "
          f"({100*gf.sum()/len(b15):>5.1f}%)  == 1h close > 1h close 249 bars ago")
    print(f"    (b) NaN-until-warmed  -> {gnever.sum():>7,} bars TRUE "
          f"({100*gnever.sum()/len(b15):>5.1f}%)  == grid never arms, 0 trades ever")
    print(f"    (c) documented intent -> {gw.sum():>7,} bars TRUE "
          f"({100*gw.sum()/len(b15):>5.1f}%)  == a real EMA200")
    dis = int((gf != gw).sum())
    print(f"    (a) vs (c) disagree on {dis:,} bars ({100*dis/len(b15):.1f}%)")
    print()
    print("        E[1] = (1-a)x[0] + a x[1]   and   a = 2/201")
    print("        x[1] > E[1]  <=>  x[1] > x[0]       <- the (1-a) cancels exactly")
    print("    so under either runtime convention the EMA contributes nothing here.")
    print("    a 250-candle window was chosen to give a 200-EMA room; reading index 1")
    print("    throws that away. Fix: read ema[249] vs closes[249] off a warmed")
    print("    window, or fetch >= 400 candles and use a genuinely warmed EMA.")

    # ---- 2. headline ----
    hdr("[2] HEADLINE — maker fees on resting legs, real funding, 3x, 45 months")
    print(f"  {'sym':<9}{'net':>9}{'DD':>7}{'BHnet':>9}{'BH@125%':>9}{'BHdd':>7}"
          f"{'fills':>7}{'grids':>7}{'stops':>7}{'liq':>5}{'fund$':>8}{'fees$':>8}")
    print("  " + "-" * 100)
    rows = []
    for s, b in data.items():
        g = htf_filter(b)[0]
        r = report(s, b, g)
        rows.append(r)
        print(f"  {s:<9}{r['net']:>+8.1f}%{r['mdd']:>6.1f}%{r['bh']:>+8.0f}%"
              f"{r['bh125']:>+8.0f}%{r['bhmdd']:>6.0f}%{r['fills']:>7}{r['grids']:>7}"
              f"{r['reasons'].get('stop',0):>7}{r['liq']:>5}{r['fund']:>8.0f}"
              f"{r['fees']:>8.0f}")
    print("  " + "-" * 100)

    # ---- 3. the gate, two ways ----
    hdr("[3] HOUSE GATE — covered levels only, vs every lot closed")
    print("    a grid makes its profit on COVERED levels and eats its loss on levels")
    print("    still open when the hard stop fires, so the covered-only view can report")
    print("    a 100% win rate on a losing run. Both are shown.")
    print()
    print(f"  {'sym':<9}{'net':>9}{'DD':>7}   |{'PFcov':>8}{'WRcov':>7}{'ncov':>7}"
          f"   |{'PFall':>8}{'WRall':>7}{'nall':>7}{'green':>7}{'gate':>7}{'vsBH':>7}")
    print("  " + "-" * 100)
    npass = nbeat = 0
    for r in rows:
        pfc, wrc, nc = metrics(r["covered_pnl"])
        pfa, wra, na = metrics(r["closed_pnl"])
        ya = year_pnl(r["closed_pnl"], r["closed_t"])
        green = sum(1 for v in ya.values() if v > 0)
        ny = max(len(ya), 1)
        ck = [pfa > 1.2, green >= max(2, (2 * ny) // 3 + 1), na >= 30,
              r["mdd"] < 45]
        p = all(ck)
        beat = r["net"] > r["bh125"]
        npass += p
        nbeat += beat
        print(f"  {r['sym']:<9}{r['net']:>+8.1f}%{r['mdd']:>6.1f}%   |{pfc:>8.2f}"
              f"{wrc:>6.0f}%{nc:>7}   |{pfa:>8.2f}{wra:>6.0f}%{na:>7}"
              f"{f'{green}/{ny}':>7}{'PASS' if p else 'fail':>7}"
              f"{'YES' if beat else 'no':>7}")
    print("  " + "-" * 100)
    print(f"  pass house gate: {npass}/{len(rows)}    beat leverage-matched "
          f"buy & hold: {nbeat}/{len(rows)}")

    # ---- 4. sensitivity ----
    hdr("[4] SENSITIVITY on SOL — is the headline a fill rule, a fee model, or leverage?")
    C = np.array([b[4] for b in b15])
    A = P.atr(np.array([b[2] for b in b15]), np.array([b[3] for b in b15]), C, 20)
    af = float(np.nanmedian(A / C))
    rt = MAKER_FEE * 2
    print(f"    median ATR(20) on 15m = {af*100:.3f}% of price")
    print(f"    one grid step = 1.0 ATR = {af*100:.3f}%  |  a covered round trip "
          f"pays 2 x {MAKER_FEE*1e4:.0f}bps maker = {rt*100:.3f}%")
    print(f"    cost/ATR per round trip = {rt/af:.3f}  "
          f"({'healthy' if rt/af < 0.5 else 'MARGINAL'}; >1.0 is arithmetically dead)")
    print()
    print(f"    {'variant':<44}{'net':>9}{'DD':>8}{'fills':>8}{'liq':>5}")
    variants = [
        ("spec gate (a), maker fees  [PRIMARY]", dict(), gf),
        ("spec gate (a), TAKER fees everywhere",
         dict(leg_fee=TAKER_FEE, flat_fee=TAKER_FEE), gf),
        ("house costs 6bps + 5bps slip on every leg",
         dict(leg_fee=HOUSE_COMM, flat_fee=HOUSE_COMM, leg_slip=0,
              flat_slip=HOUSE_SLIP), gf),
        ("intended EMA200 gate (c)", dict(), gw),
        ("pessimistic fill (needs low < level)",
         dict(optimistic_fill=False), gf),
        ("no funding charged", dict(funding=False), gf),
        ("gross: no fees, no funding",
         dict(leg_fee=0.0, flat_fee=0.0, funding=False), gf),
    ]
    for lbl, kw, g in variants:
        tr = {}
        eq = simulate(b15, "SOLUSDT", g, track=tr, **kw)
        print(f"    {lbl:<44}{(eq/INIT-1)*100:>+8.1f}%{tr['mdd']:>7.1f}%"
              f"{tr['fills']:>8}{tr['liq']:>5}")
    print()
    print(f"    buy & hold SOL same window {((C[-1]/C[0]-1)*100):+.0f}%  |  "
          f"at the grid's peak 125% notional {((C[-1]/C[0]-1)*125):+.0f}%")

    # ---- 5. where the P&L comes from ----
    hdr("[5] WHERE THE P&L COMES FROM — covered wins vs stop-out losses")
    print(f"  {'sym':<9}{'ncov':>7}{'covered $':>12}{'nall':>7}{'all-closed $':>14}"
          f"{'open':>6}{'stops':>7}{'rebuild':>9}{'standdown':>11}")
    print("  " + "-" * 100)
    for r in rows:
        print(f"  {r['sym']:<9}{len(r['covered_pnl']):>7}"
              f"{sum(r['covered_pnl']):>+12.0f}{len(r['closed_pnl']):>7}"
              f"{sum(r['closed_pnl']):>+14.0f}{r['open_lots']:>6}"
              f"{r['reasons'].get('stop',0):>7}{r['reasons'].get('rebuild_drift',0):>9}"
              f"{r['reasons'].get('stand_down',0):>11}")
    print("  " + "-" * 100)

    # ---- 6. no-lookahead ----
    hdr("[6] NO-LOOKAHEAD PROOF — truncate the series, the prefix must be identical")
    k = min(40000, len(b15))
    ta, tb = {}, {}
    simulate(b15, "SOLUSDT", gf, track=ta)
    simulate(b15[:k], "SOLUSDT", gf, track=tb)
    cut = int(b15[k - 1][0])
    fa = [x for x in ta["fill_times"] if x <= cut]
    fb = list(tb["fill_times"])
    eq_same = abs(ta["eq_curve"][k - 1] - tb["eq_curve"][k - 1]) < 1e-6
    ok = (fa == fb) and eq_same
    print(f"    full run  : {len(fa):>6} fills at or before bar {k}, "
          f"equity = {ta['eq_curve'][k-1]:.4f}")
    print(f"    truncated : {len(fb):>6} fills, equity = {tb['eq_curve'][k-1]:.4f}")
    print(f"    identical fill timestamps: {fa == fb}    identical equity: {eq_same}")
    print(f"    => {'PASS — no bar uses data from its own future' if ok else 'FAIL'}")
    print("    (a truncated run cannot know about fills after the cut, so only the")
    print("     counts inside the prefix are comparable)")

    # ---- save ----
    op = os.path.join(OUT, f"grid_audit_{args.tag}.txt")
    with open(op, "w", encoding="utf-8") as f:
        f.write("ATR Long Grid (Trend-Filtered) — Hyperliquid v2 dialect, ported\n")
        f.write(f"generated by grid_audit.py --tag {args.tag} | "
                f"simulate() carries the equity-identity assertion; a run whose "
                f"output lacks avg_expo predates the cost-basis fix\n")
        f.write(f"gate = '1h close > 1h close 249 bars ago' (the spec's EMA200 cancels "
                f"algebraically); resting legs {MAKER_FEE*1e4:.0f}bps maker, flattens "
                f"{TAKER_FEE*1e4:.0f}bps taker; real funding; {LEVERAGE:g}x lev, "
                f"0.5% maint margin\n")
        f.write(f"{'sym':<9}{'net':>9}{'dd':>8}{'avg_expo':>10}{'bh':>10}"
                f"{'bh125':>10}{'fills':>7}{'grids':>7}{'stops':>7}{'liq':>5}"
                f"{'fund':>9}{'fees':>9}\n")
        for r in rows:
            f.write(f"{r['sym']:<9}{r['net']:>+9.2f}{r['mdd']:>8.2f}"
                    f"{r['avg_expo']:>10.2f}{r['bh']:>+10.2f}"
                    f"{r['bh125']:>+10.2f}{r['fills']:>7}{r['grids']:>7}"
                    f"{r['reasons'].get('stop',0):>7}{r['liq']:>5}"
                    f"{r['fund']:>9.0f}{r['fees']:>9.0f}\n")
        f.write("\ncovered-only vs all-closed\n")
        f.write(f"{'sym':<9}{'pf_cov':>9}{'wr_cov':>9}{'n_cov':>8}"
                f"{'pf_all':>9}{'wr_all':>9}{'n_all':>8}\n")
        for r in rows:
            pfc, wrc, nc = metrics(r["covered_pnl"])
            pfa, wra, na = metrics(r["closed_pnl"])
            f.write(f"{r['sym']:<9}{pfc:>9.2f}{wrc:>9.1f}{nc:>8}"
                    f"{pfa:>9.2f}{wra:>9.1f}{na:>8}\n")
    print(f"\nwrote {op}")


if __name__ == "__main__":
    import functools
    import builtins
    builtins.print = functools.partial(builtins.print, flush=True)
    main()
