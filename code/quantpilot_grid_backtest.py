"""QUANT PILOT v2 ATR Long Grid port — SOL 15m, HTF 1h EMA200 filter.
Spec-literal: 5 post-only BUY levels below anchor (band 5xATR20, step=1xATR),
qty 25% equity notional/level, reduce-only SELL cover +1 step, hard stop
(bottom-0.5 ATR) on 15m CLOSE -> market flatten + 96-bar cooldown, rebuild
idle when close > center+1.5*half, bear-filter stand-down when flat.
Fills: resting-order touch=fill (maker 2bps); market flattens taker 5bps.
Newly placed orders can't fill same bar. Stop evaluated on bar close only
(spec-literal; intra-bar wicks not modeled — stated limitation).
Proxy: Binance SOLUSDT (spec: SOL/USDC:USDC Hyperliquid).
Usage: python quantpilot_grid_backtest.py [base|neigh|wf|ALL]
"""
import sys
import numpy as np
import pandas as pd

D1M = r"C:\Users\Lenovo\Documents\backtest-system\data\binance_klines_1m"
MAKER, TAKER = 0.0002, 0.0005
EQ0 = 10000.0


def load_15m(sym="SOLUSDT"):
    d = pd.read_csv(D1M + "\\" + sym + "_1m.csv").sort_values("open_ts").reset_index(drop=True)
    g = d.index // 15
    b = d.groupby(g).agg(open_ts=("open_ts", "first"), open=("open", "first"),
                         high=("high", "max"), low=("low", "min"),
                         close=("close", "last"), volume=("volume", "sum")).reset_index(drop=True)
    return b


def rma(x, n):
    return pd.Series(x).ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def load_ltf(sym, tfmin):
    d = pd.read_csv(D1M + "\\" + sym + "_1m.csv").sort_values("open_ts").reset_index(drop=True)
    g = d.index // tfmin
    b = d.groupby(g).agg(open_ts=("open_ts", "first"), open=("open", "first"),
                         high=("high", "max"), low=("low", "min"),
                         close=("close", "last"), volume=("volume", "sum")).reset_index(drop=True)
    return b, d


def run(sym="SOLUSDT", tfmin=15, band_mult=5.0, nlv=5, pct=0.25, cd=96, reb=1.5,
        stop_mult=0.5, verbose=True, frac=None):
    b, d1 = load_ltf(sym, tfmin)
    if frac is not None:
        a, c = frac
        i0, i1 = int(len(b) * a), int(len(b) * c)
        b = b.iloc[i0:i1].reset_index(drop=True)
    N = len(b)
    O = b.open.to_numpy(); H = b.high.to_numpy(); Lo = b.low.to_numpy(); C = b.close.to_numpy()
    pc = np.roll(C, 1); pc[0] = C[0]
    tr = np.maximum(H - Lo, np.maximum(np.abs(H - pc), np.abs(Lo - pc)))
    atr = rma(tr, 20)
    # HTF 1h EMA200 from 1m (last CLOSED 1h bar vs each LTF bar open)
    d1 = d1.copy()
    d1["hh"] = pd.to_datetime(d1.open_ts, unit="ms").dt.floor("h")
    hg = d1.groupby("hh").agg(hopen=("open_ts", "first"), hclose=("close", "last")).sort_values("hopen")
    hu = hg.hopen.to_numpy(); hc = hg.hclose.to_numpy()
    he = pd.Series(hc).ewm(span=200, adjust=False).mean().to_numpy()
    ts = b.open_ts.to_numpy()
    ji = np.searchsorted(hu, ts, side="right") - 2
    ji = np.clip(ji, 0, len(hc) - 1)
    htf_c = hc[ji]; htf_e = he[ji]

    cash = EQ0
    pos = 0.0  # base units long
    lots = []  # [qty, entry] open lots FIFO
    state = "idle"
    grid = None  # dict prices, qtys, entry_on, cover_on, cover_px, step, stop, center, half
    cd_left = 0
    gp = gl = 0.0
    closed = []  # pnl per closed lot
    peak = EQ0; mdd = 0.0
    fills = 0
    W0 = int(265 * 60 / tfmin) + 30  # HTF EMA200 settled in LTF bars

    def net_equity(px):
        return cash + pos * px

    for i in range(1, N):
        o, h_, l_, c_ = O[i], H[i], Lo[i], C[i]
        cp = C[i - 1]
        ai = atr[i - 1]
        bull = htf_c[i] > htf_e[i]
        if not (ai > 0):
            continue
        if i < W0:
            continue
        eq_mark = net_equity(c_)
        if eq_mark > peak:
            peak = eq_mark
        dd = (peak - eq_mark) / max(peak, 1e-9)
        if dd > mdd:
            mdd = dd

        if state == "cooldown":
            cd_left -= 1
            if cd_left <= 0:
                state = "idle"
            continue
        if state == "idle":
            if not bull:
                continue
            half = ai * band_mult
            step = half / nlv
            eq = net_equity(cp)
            prices = [cp - step * (k + 1) for k in range(nlv)]
            qtys = [(pct * eq) / p for p in prices]
            grid = {"prices": prices, "qtys": qtys,
                    "entry": [p < o for p in prices], "cover": [False] * nlv,
                    "fresh_entry": [False] * nlv, "fresh_cover": [False] * nlv,
                    "step": step, "stop": prices[-1] - ai * stop_mult,
                    "center": cp, "half": half}
            state = "working"
            continue
        # working
        if c_ <= grid["stop"]:
            if pos > 0:
                cash += pos * c_ * (1 - TAKER)
                # close lots FIFO at c_
                rem = pos
                for q, e in lots:
                    take = min(q, rem); rem -= take
                    pnl = (c_ * (1 - TAKER) - e) * take
                    closed.append(pnl)
                    if pnl > 0: gp += pnl
                    else: gl += abs(pnl)
                fills += 1
                pos = 0.0; lots = []
            grid = None; state = "cooldown"; cd_left = cd
            continue
        if pos == 0 and any(grid["cover"]):
            grid = None; state = "idle"
            continue
        # fills for orders resting at bar open
        for k in range(nlv):
            if grid["entry"][k] and not grid["fresh_entry"][k] and l_ <= grid["prices"][k]:
                p = grid["prices"][k]; q = grid["qtys"][k]
                cash -= q * p * (1 + MAKER)
                pos += q; lots.append([q, p * (1 + MAKER)])
                fills += 1
                grid["entry"][k] = False
                grid["cover"][k] = True; grid["fresh_cover"][k] = True
        for k in range(nlv):
            if grid["cover"][k] and not grid["fresh_cover"][k] and h_ >= grid["prices"][k] + grid["step"]:
                p = grid["prices"][k] + grid["step"]; q = grid["qtys"][k]
                cash += q * p * (1 - MAKER)
                # FIFO close
                rem = q
                li = 0
                while rem > 1e-12 and li < len(lots):
                    take = min(lots[li][0], rem)
                    pnl = (p * (1 - MAKER) - lots[li][1]) * take
                    closed.append(pnl)
                    if pnl > 0: gp += pnl
                    else: gl += abs(pnl)
                    lots[li][0] -= take; rem -= take
                    if lots[li][0] <= 1e-12:
                        li += 1
                lots = [x for x in lots if x[0] > 1e-12]
                pos = max(pos - q, 0.0)
                fills += 1
                grid["cover"][k] = False
        # re-arm completed levels
        for k in range(nlv):
            if not grid["entry"][k] and not grid["cover"][k]:
                if bull and grid["prices"][k] < c_:
                    grid["entry"][k] = True; grid["fresh_entry"][k] = True
        grid["fresh_entry"] = [False] * nlv
        grid["fresh_cover"] = [False] * nlv
        if c_ > grid["center"] + grid["half"] * reb:
            if pos > 0:
                cash += pos * c_ * (1 - TAKER)
                rem = pos
                for q, e in lots:
                    take = min(q, rem); rem -= take
                    pnl = (c_ * (1 - TAKER) - e) * take
                    closed.append(pnl)
                    if pnl > 0: gp += pnl
                    else: gl += abs(pnl)
                fills += 1
                pos = 0.0; lots = []
            grid = None; state = "idle"
            continue
        if not bull and pos == 0:
            grid = None; state = "idle"
            continue
    # liquidate at end
    eq_end = net_equity(C[-1])
    if pos > 0:
        px = C[-1] * (1 - TAKER)
        rem = pos
        for q, e in lots:
            take = min(q, rem); rem -= take
            pnl = (px - e) * take
            closed.append(pnl)
            if pnl > 0: gp += pnl
            else: gl += abs(pnl)
        cash += pos * px
        pos = 0.0
    eq_end = cash
    if eq_end > peak:
        peak = eq_end
    dd = (peak - eq_end) / max(peak, 1e-9)
    mdd = max(mdd, dd)
    n = len(closed)
    w = sum(1 for x in closed if x > 0)
    pf = gp / gl if gl > 0 else (float("inf") if gp > 0 else 0.0)
    if verbose:
        print(f"{sym} {tfmin}m band{band_mult} lv{nlv}: net {(eq_end-EQ0)/100:+.2f}% PF {pf:.2f} "
              f"WR {w/max(n,1)*100:.1f}% lots={n} fills={fills} DD {mdd*100:.1f}%", flush=True)
    return eq_end, pf, w / max(n, 1), n, mdd


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "base"
    syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "SUIUSDT", "HYPEUSDT", "SPXUSDT", "XRPUSDT"]
    if mode in ("base", "ALL"):
        print("===== base (spec params, SOL 15m) =====", flush=True)
        run()
    if mode in ("neigh", "ALL"):
        print("===== neighborhood (SOL 15m) =====", flush=True)
        for bm in (4.0, 5.0, 6.0):
            for lv in (4, 5, 6):
                run(band_mult=bm, nlv=lv)
    if mode in ("wf", "ALL"):
        print("===== walk-forward: IS first half / OOS second half (SOL 15m) =====", flush=True)
        run(frac=(0.0, 0.5))
        run(frac=(0.5, 1.0))
    if mode in ("sweep", "ALL"):
        print("===== full sweep: 7 pairs x 5m/15m/30m/1h (HTF 1h filter, cd 96 bars) =====", flush=True)
        for s in syms:
            for tf in (5, 15, 30, 60):
                try:
                    run(sym=s, tfmin=tf)
                except FileNotFoundError:
                    print(s, tf, "no data", flush=True)
    print("DONE", flush=True)
