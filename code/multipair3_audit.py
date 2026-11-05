"""multipair3_audit.py — testable survivors of the 3-strategy multi-pair research.

THE DOCUMENT
    XPROP-LAG-1H-v1   BTC->altcoin lead-lag propagation
    COINT-DYN-1H-v1   dynamic cointegration pairs
    LIQ-REV-1H-v1     post-liquidation-cascade mean reversion
    It is unusually honest for a strategy document: it labels every performance
    number "illustrative", reports IS/OOS splits, DSR and Monte Carlo, and
    quotes research showing naive evaluation inflates crypto Sharpe by 3.6x.
    The numbers still have to survive real data.

DATA TRIAGE FIRST — what is testable at all, established by probing the
exchange rather than by assumption:
    XPROP-LAG   1h OHLCV for BTC + alts, 4h resampled from 1h        FULL
    COINT-DYN   1h OHLCV for pairs                                  FULL
    LIQ-REV     NEEDS liquidation volume. Probed:
                  /fapi/v1/allForceOrders    -> 404 on every base URL
                  /api/v3/rforceOrders       -> 403
                  /fapi/v1/forceOrders      -> 404
                There is NO public historical liquidation endpoint on Binance.
                Coinglass, which the document itself names as its source, is a
                paid product with no key on this machine.
                Its core trigger is L_t = liqVol / median(liqVol) > 3.0. Without
                liquidation volume that ratio cannot be computed for a single
                bar, so the strategy is not testable here.
                Open interest is available but only ~30 days
                (/futures/data/openInterestHist returns 400 beyond that), which
                covers one of its three gates and neither of its other two.
                => NOT TESTED, and the report says why rather than substituting
                   a different trigger and calling it the same strategy.

WHAT IS TESTED, and the honest deviation for each
    XPROP-LAG
      - beta eligibility uses |beta| > 0.15 on a 168h rolling regression of
        alt returns on LAGGED BTC returns. The document also requires a t-stat
        > 2.0; that is applied.
      - 4h EMA50 slope for the trend gate, resampled from 1h.
      - 1h ATR(14)/close between 0.3% and 2.5%.
      - volatility targeting at 15% annualised, 25% single-name cap.
      - 1h dollar volume > $5M liquidity gate.
      - exits: +1.2 ATR target, -0.8 ATR stop, 4h time stop, T+1 open fills.
    COINT-DYN
      - The document specifies a rolling Johansen trace statistic. Johansen is a
        matrix method over a VAR system and is expensive and unstable at 720-bar
        rolling windows; a plain OLS hedge ratio on the same window is used
        instead and THIS IS A DIFFERENT, SIMPLER ESTIMATOR. It is stated
        wherever the result appears, because a cointegration gate built from a
        different estimator tests a different strategy.
      - half-life from an AR(1) fit on the spread, gated to 4-48h.
      - Choppiness index < 45.
      - z-score entry at +/-2.0, exit at |z| < 0.5, stop at |z| > 3.5,
        time stop 3x half-life, dollar-neutral two legs.

EXECUTION
    0.05% taker + ATR slippage per leg, real funding at actual 8h prints on
    held notional, next-bar-open fills, no same-bar execution. Portfolio heat
    is capped as specified so leverage cannot silently inflate the return.
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

D1H = os.path.join(ROOT, "data", "binance_klines_1h")
FUND = os.path.join(ROOT, "data", "binance_funding")
OUT = os.path.join(ROOT, "results")

INIT = 10000.0
TAKER = 0.0005
SLIP_ATR_MULT = 0.1
ALT_COINS = ["ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT",
             "DOGEUSDT", "BNBUSDT", "NEARUSDT", "SUIUSDT"]
PAIRS = [("BTCUSDT", "ETHUSDT"), ("BTCUSDT", "SOLUSDT"), ("ETHUSDT", "SOLUSDT"),
         ("SOLUSDT", "ADAUSDT"), ("BTCUSDT", "XRPUSDT"), ("ADAUSDT", "AVAXUSDT"),
         ("LINKUSDT", "AVAXUSDT"), ("BTCUSDT", "DOGEUSDT"), ("SOLUSDT", "XRPUSDT"),
         ("ETHUSDT", "ADAUSDT"), ("BNBUSDT", "SOLUSDT"), ("NEARUSDT", "SOLUSDT"),
         ("SUIUSDT", "XRPUSDT"), ("AVAXUSDT", "DOGEUSDT"), ("BNBUSDT", "ETHUSDT")]


def load(sym):
    p = os.path.join(D1H, f"{sym}_1h.csv")
    if not os.path.exists(p):
        return None
    t, o, h, l, c, v = [], [], [], [], [], []
    with open(p) as f:
        f.readline()
        for line in f:
            a = line.split(",")
            if len(a) < 6:
                continue
            try:
                t.append(int(a[0])); o.append(float(a[1])); h.append(float(a[2]))
                l.append(float(a[3])); c.append(float(a[4])); v.append(float(a[5]))
            except ValueError:
                continue
    return dict(t=np.array(t, np.int64), o=np.array(o), h=np.array(h),
                l=np.array(l), c=np.array(c), v=np.array(v))


def ema(x, span):
    a = 2.0 / (span + 1.0)
    out = np.empty(len(x)); acc = x[0]; out[0] = acc
    for i in range(1, len(x)):
        acc += a * (x[i] - acc); out[i] = acc
    return out


def rma(x, n):
    a = 1.0 / n
    out = np.empty(len(x)); acc = x[0]; out[0] = acc
    for i in range(1, len(x)):
        acc += a * (x[i] - acc); out[i] = acc
    return out


def atr(h, l, c, n=14):
    pc = np.roll(c, 1); pc[0] = c[0]
    return rma(np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc))), n)


def roll_mean(x, n):
    cs = np.cumsum(np.insert(np.nan_to_num(x.astype(float)), 0, 0.0))
    out = np.full(len(x), np.nan)
    k = np.arange(n, len(x) + 1)
    out[k - 1] = (cs[k] - cs[k - n]) / n
    return out


def roll_std(x, n):
    m = roll_mean(x, n); m2 = roll_mean(x * x, n)
    return np.sqrt(np.maximum(m2 - m * m, 0))


def resample4(h1):
    """1h -> 4h, Binance-style. open=first, high=max, low=min, close=last."""
    n = len(h1["c"])
    k = n // 4 * 4
    # The bucket timestamp must be reduced per 4h bucket. Taking it from the
    # UNREDUCED 1h timestamps returned a `t` array of length k (61,990) while
    # every OHLCV array was length k/4 (15,497). The dict was internally
    # inconsistent, and the 4h gate was indexed against the 1h-length axis, so
    # index 61,987 was read from a 15,497-long array.
    t = ((h1["t"][:k] // (4 * 3600000)) * (4 * 3600000)).reshape(-1, 4)[:, 0]
    o = h1["o"][:k].reshape(-1, 4)[:, 0]
    h = h1["h"][:k].reshape(-1, 4).max(axis=1)
    l = h1["l"][:k].reshape(-1, 4).min(axis=1)
    c = h1["c"][:k].reshape(-1, 4)[:, -1]
    v = h1["v"][:k].reshape(-1, 4).sum(axis=1)
    out = dict(t=t, o=o, h=h, l=l, c=c, v=v)
    # every array in a bar record must be the same length
    lens = {k2: len(v2) for k2, v2 in out.items()}
    assert len(set(lens.values())) == 1, f"resample4 produced ragged bars: {lens}"
    return out


def choppiness(h, l, c, n=14):
    a = atr(h, l, c, n)
    rng = roll_mean(h - l, n)
    with np.errstate(invalid="ignore", divide="ignore"):
        ch = 100 * np.log10(np.where(rng > 0, rng, np.nan)) / \
            np.log10(np.where(a > 0, a, np.nan))
    return np.clip(ch, 0, 100)


def rolling_beta_t(y, x, n=168):
    """OLS beta of y on x over a trailing window, plus the t-stat."""
    cnt = 0
    cy = cx = cyy = cxy = 0.0
    b = np.full(len(y), np.nan)
    ts = np.full(len(y), np.nan)
    for i in range(len(y)):
        xi, yi = x[i], y[i]
        if np.isfinite(xi) and np.isfinite(yi):
            cnt += 1
            cy += yi; cx += xi; cyy += yi * yi; cxy += xi * yi
        if cnt > n:
            j = i - n
            xj, yj = x[j], y[j]
            cy -= yj; cx -= xj; cyy -= yj * yj; cxy -= xj * yj
            cnt -= 1
        if cnt >= n:
            mx, my = cx / cnt, cy / cnt
            vx = cyy - cnt * mx * mx
            vy = cyy - cnt * my * my
            cxy2 = cxy - cnt * mx * my
            if vx > 0 and vy > 0:
                beta = cxy2 / vx
                resid = vy - beta * cxy2
                se = np.sqrt(max(resid, 0) / (cnt - 2) / vx) if vx > 0 else np.nan
                b[i] = beta
                ts[i] = beta / se if se and se > 0 else np.nan
    return b, ts


def funding_map(sym, T):
    p = os.path.join(FUND, f"{sym}_funding.json")
    rate = np.zeros(len(T)); ev = np.zeros(len(T), bool)
    if not os.path.exists(p):
        return rate, ev
    f = json.load(open(p, encoding="utf-8"))
    ft = np.array([x["t"] for x in f], np.int64)
    fv = np.array([x["r"] for x in f])
    m = (ft >= T[0]) & (ft <= T[-1])
    for ts, r in zip(ft[m], fv[m]):
        j = int(np.searchsorted(T, ts, side="left"))
        if j < len(T):
            ev[j] = True; rate[j] = r
    return rate, ev


def stats(eq, T):
    r = np.diff(eq) / np.where(eq[:-1] > 0, eq[:-1], np.nan)
    r = r[np.isfinite(r)]
    dd = (np.maximum.accumulate(eq) - eq) / np.maximum.accumulate(eq)
    sh = (r.mean() / r.std() * np.sqrt(24 * 365)) if len(r) > 2 and r.std() > 0 else np.nan
    yrs = (T[-1] - T[0]) / (365 * 86400000)
    return dict(cum=(eq[-1] / eq[0] - 1) * 100,
                sharpe=sh,
                mdd=float(dd.max() * -100),
                years=yrs)


def yearly(eq, T):
    import datetime as dt
    y = defaultdict(list)
    for i in range(len(eq)):
        y[dt.datetime.fromtimestamp(T[i] / 1000, dt.timezone.utc).year].append(eq[i])
    out = {}
    for k, v in y.items():
        if len(v) >= 2:
            out[k] = (v[-1] / v[0] - 1) * 100
    return out


# ==========================================================================
def xprop_lag():
    print("\n" + "=" * 100)
    print("STRATEGY 1 — XPROP-LAG-1H-v1   BTC->altcoin lead-lag")
    print("=" * 100)
    btc = load("BTCUSDT")
    btc4 = resample4(btc)
    e50 = ema(btc4["c"], 50)
    slope = np.full(len(e50), np.nan)
    slope[8:] = (e50[8:] - e50[:-8]) / np.where(e50[:-8] > 0, e50[:-8], np.nan)
    gate4 = np.where(slope > 0.002, 1.0, np.where(slope < -0.002, -1.0, 0.0))

    A_btc = atr(btc["h"], btc["l"], btc["c"], 14)
    rb = np.zeros(len(btc["c"]))
    rb[1:] = btc["c"][1:] / btc["c"][:-1] - 1
    vol_ok_btc = (A_btc / btc["c"] > 0.003) & (A_btc / btc["c"] < 0.025)

    # The 4h gate is indexed by POSITION in resample4's output, which has
    # n//4 entries -- NOT against btc4['t'], which holds 1h timestamps.
    # Clipping against it compared 61,990 stamps against a 15,497-long gate,
    # so index 15,498 survived and read one past the end.
    idx4 = np.searchsorted(btc4["t"], btc["t"], side="right") - 1
    idx4 = np.clip(idx4, 0, len(btc4["t"]) - 1)
    # resample4() drops the trailing partial 4h bucket, so ASSERT the
    # mapping rather than trust it.
    assert idx4.max() < len(gate4), (
        f"4h gate index {idx4.max()} >= gate size {len(gate4)}")
    # and the mapped 4h bar must never postdate the 1h bar it gates
    assert not (btc4["t"][idx4] > btc["t"]).any(), "4h gate looks ahead"
    trend = gate4[idx4]

    print(f"  {'alt':<9}{'beta med':>10}{'|b|>0.15%':>11}{'t>2 %':>9}"
          f"{'net%':>9}{'DD%':>8}{'trades':>8}{'PF':>7}{'WR%':>6}"
          f"{'BH net%':>10}{'excess':>9}")
    print("  " + "-" * 96)
    rows = []
    tot_bh = tot_net = 0.0
    for alt in ALT_COINS:
        d = load(alt)
        if d is None:
            continue
        n = min(len(d["c"]), len(btc["c"]))
        T = btc["t"][:n]
        d = {k: v[:n] for k, v in d.items()}
        ra = np.zeros(n)
        ra[1:] = d["c"][1:] / d["c"][:-1] - 1
        # LAGGED BTC return: r_BTC(t-1) is the predictor
        rb_lag = np.zeros(n)
        rb_lag[1:] = rb[1:n] - rb[0:n - 1]
        beta, tstat = rolling_beta_t(ra, rb_lag, 168)
        elig = (np.abs(beta) > 0.15) & (np.abs(tstat) > 2.0) & (beta > 0)
        # vol-normalised 1-bar BTC shock
        # Slice explicitly to n-1 before shifting, rather than relying on
        # 0:n-1 matching 1:n. When the altcoin is the shorter series, n equals
        # len(btc) and 0:n-1 is one element shorter than 1:n, so the subtraction
        # failed to broadcast.
        shock = np.zeros(n)
        shock[1:] = (btc["c"][1:n] - btc["c"][0:n - 1]) / \
                    np.where(A_btc[0:n - 1] > 0, A_btc[0:n - 1], np.nan)
        A_alt = atr(d["h"], d["l"], d["c"], 14)
        dv = d["v"] * d["c"]
        dv_avg = roll_mean(dv, 24)
        liq_ok = dv_avg > 5e6
        vol_ok = (A_alt / d["c"] > 0.003) & (A_alt / d["c"] < 0.025)
        sig = np.where((shock > 1.5) & elig & liq_ok & vol_ok & vol_ok_btc[:n] & (trend[:n] > 0), 1,
                       np.where((shock < -1.5) & elig & liq_ok & vol_ok & vol_ok_btc[:n] & (trend[:n] < 0), -1, 0))

        fr, fev = funding_map(alt, T)
        cash = INIT; pos = 0; ent = 0.0; tp = sl = 0.0; bib = 0
        qty = 0.0; peak = INIT; mdd = 0.0
        eqc = np.zeros(n); pnls = []; dvol = np.zeros(n)
        for i in range(n):
            dvol[i] = np.nanstd(ra[max(0, i - 480):i]) * np.sqrt(24 * 365) if i > 60 else np.nan
            if pos != 0:
                if pos > 0 and d["l"][i] <= sl: px, why = min(d["o"][i], sl), "stop"
                elif pos < 0 and d["h"][i] >= sl: px, why = max(d["o"][i], sl), "stop"
                elif pos > 0 and d["h"][i] >= tp: px, why = tp, "target"
                elif pos < 0 and d["l"][i] <= tp: px, why = tp, "target"
                elif bib >= 4: px, why = d["c"][i], "time"
                else: px, why = None, None
                if px is not None:
                    slp = np.maximum(0.0002, SLIP_ATR_MULT * A_alt[i] / max(d["c"][i], 1e-12))
                    fill = px * (1 - slp) if pos > 0 else px * (1 + slp)
                    pnl = (fill - ent) * qty * pos
                    fee = abs(qty * fill) * TAKER
                    cash += pnl - fee
                    pnls.append(pnl - fee)
                    pos = 0; qty = 0.0
            if pos == 0 and i + 1 < n and sig[i] != 0 and np.isfinite(dvol[i]) and dvol[i] > 0:
                nxt = d["o"][i + 1]
                atrv = A_alt[i]
                if atrv > 0:
                    risk = 0.02
                    stop_d = atrv * 0.8
                    q = INIT * risk / stop_d
                    # volatility target 15%, cap 25%
                    w = min(0.15 / dvol[i], 0.25)
                    q = min(q, INIT * w / max(nxt, 1e-12))
                    if q > 0 and nxt > 0:
                        slp = np.maximum(0.0002, SLIP_ATR_MULT * atrv / max(nxt, 1e-12))
                        fill = nxt * (1 + slp) if sig[i] > 0 else nxt * (1 - slp)
                        pos = sig[i]; ent = fill; qty = q; bib = 0
                        sl = fill - atrv * 0.8 if pos > 0 else fill + atrv * 0.8
                        tp = fill + atrv * 1.2 if pos > 0 else fill - atrv * 1.2
                        cash -= abs(q * fill) * TAKER
            if pos != 0 and fev[i]:
                cash -= qty * d["c"][i] * fr[i] * pos
            e = cash + (qty * (d["c"][i] - ent) * pos if pos != 0 else 0.0)
            eqc[i] = e; peak = max(peak, e)
            mdd = max(mdd, (peak - e) / max(peak, 1e-9))
            if pos == 0: qty = 0.0
            if pos != 0: bib += 1
        st = stats(eqc, T)
        w = [x for x in pnls if x > 0]; ls = [x for x in pnls if x <= 0]
        pf = (sum(w) / abs(sum(ls))) if ls and sum(ls) != 0 else (np.inf if w else 0.0)
        wr = 100 * len(w) / max(len(pnls), 1)
        bh = (d["c"][-1] / d["c"][0] - 1) * 100
        tot_bh += bh; tot_net += st["cum"]
        print(f"  {alt:<9}{np.nanmedian(beta):>10.3f}{100*np.nanmean(elig):>10.1f}%"
              f"{100*np.nanmean(np.abs(tstat)>2):>8.0f}%{st['cum']:>+8.1f}%{st['mdd']:>7.1f}%"
              f"{len(pnls):>8}{pf:>7.2f}{wr:>5.0f}%{bh:>+9.0f}%{st['cum']-bh:>+8.0f}")
        rows.append(dict(alt=alt, st=st, n=len(pnls), pf=pf, bh=bh, pnls=pnls,
                         eq=eqc, T=T))
    print("  " + "-" * 96)
    print(f"  equal-weight basket across {len(rows)} alts: strategy {tot_net/len(rows):+.1f}% "
          f"avg vs passive {tot_bh/len(rows):+.1f}% avg")
    print(f"  document claims OOS Sharpe 1.08, PF 1.18, DD -9.1%")
    return rows


# ==========================================================================
def coint_pairs():
    print("\n" + "=" * 100)
    print("STRATEGY 2 — COINT-DYN-1H-v1   dynamic cointegration pairs")
    print("    NOTE: hedge ratio is rolling OLS, NOT the rolling Johansen trace")
    print("    statistic the document specifies. This is a DIFFERENT, simpler")
    print("    estimator and the result below is not the document's strategy.")
    print("=" * 100)
    DATA = {s: load(s) for s in set([x for pr in PAIRS for x in pr])}
    DATA = {k: v for k, v in DATA.items() if v is not None}

    print(f"\n  {'pair':<20}{'z>2 events':>12}{'net%':>9}{'DD%':>8}"
          f"{'PF':>7}{'WR%':>6}{'BH net%':>10}{'excess':>9}")
    print("  " + "-" * 82)
    rows = []
    for A, B in PAIRS:
        if A not in DATA or B not in DATA:
            continue
        da, db = DATA[A], DATA[B]
        n = min(len(da["c"]), len(db["c"]))
        T = da["t"][:n]
        ca = da["c"][:n]; cb = db["c"][:n]
        la, lb = np.log(ca), np.log(cb)
        # rolling OLS beta: la = a + b*lb
        # Running sums make this O(n). The original recomputed the variance of
        # lb over the trailing 720 bars INSIDE the per-bar loop, i.e. O(n*720)
        # per pair, which at 15 pairs x 40k bars is ~430M operations.
        cnt = 0; sa = sb = saa = sbb = sab = 0.0
        beta = np.full(n, np.nan); alpha = np.full(n, np.nan)
        W = 720
        for i in range(n):
            sa += la[i]; sb += lb[i]; saa += la[i] * la[i]
            sbb += lb[i] * lb[i]; sab += la[i] * lb[i]; cnt += 1
            if cnt > W:
                j = i - W
                sa -= la[j]; sb -= lb[j]; saa -= la[j] * la[j]
                sbb -= lb[j] * lb[j]; sab -= la[j] * lb[j]; cnt -= 1
            if cnt >= W:
                ma, mb = sa / cnt, sb / cnt
                cov = sab - cnt * ma * mb
                var = sbb - cnt * mb * mb
                if var > 1e-18:
                    b2 = cov / var
                    beta[i] = b2
                    alpha[i] = ma - b2 * mb
        spread = la - alpha - beta * lb
        mu = roll_mean(spread, 168)
        sd = roll_std(spread, 168)
        with np.errstate(invalid="ignore", divide="ignore"):
            z = (spread - mu) / sd
        # AR(1) half-life on the spread DIFFERENCE
        dz = np.full(n, np.nan)
        dz[1:] = np.nan_to_num(spread[1:] - spread[:-1])
        lam = np.full(n, np.nan)
        cnt = 0; sx = sy = sxy = sxx = 0.0
        for i in range(n):
            x = spread[i - 1] if i > 0 else np.nan
            y = dz[i]
            if np.isfinite(x) and np.isfinite(y):
                sx += x; sy += y; sxy += x * y; sxx += x * x; cnt += 1
            if cnt > 168:
                j = i - 168
                xj, yj = (spread[j - 1] if j > 0 else np.nan), dz[j]
                sx -= xj; sy -= yj; sxy -= xj * yj; sxx -= xj * xj; cnt -= 1
            if cnt >= 168:
                mx, my = sx / cnt, sy / cnt
                vxx = sxx - cnt * mx * mx
                if vxx > 1e-18:
                    lam[i] = (sxy - cnt * mx * my) / vxx
        with np.errstate(invalid="ignore", divide="ignore"):
            hl = np.where((lam < 0) & (1 + lam > 0), -np.log(2) / np.log(1 + lam), np.nan)
        ch = choppiness(da["h"][:n], da["l"][:n], da["c"][:n], 14)
        gate = (np.isfinite(hl) & (hl >= 4) & (hl <= 48) & (ch < 45))

        fr_a, fev = funding_map(A, T)
        fr_b, _ = funding_map(B, T)
        Aa = atr(da["h"][:n], da["l"][:n], ca, 14)
        Ab = atr(db["h"][:n], db["l"][:n], cb, 14)
        cash = INIT; pa = pb = 0.0; enta = entb = 0.0; qa = qb = 0.0
        hbar = 0.0; entry_i = -10 ** 9; peak = INIT; mdd = 0.0
        eqc = np.zeros(n); pnls = []; nev = int(np.nansum(np.abs(z) > 2.0))
        for i in range(n):
            if pa != 0 or pb != 0:
                zt = z[i]
                zprev = z[i - 1] if i > 0 else np.nan
                exit_ = False
                if np.isfinite(zt) and np.isfinite(zprev):
                    if abs(zt) < 0.5: exit_ = True
                    elif abs(zt) > 3.5: exit_ = True
                if hbar > 0 and (i - entry_i) >= max(3 * hbar, 3):
                                    exit_ = True            # 3x half-life
                if not np.isfinite(gate[i]):
                    exit_ = True
                if exit_:
                    for (px, sg, q, e0, cpx) in ((da["o"][i], pa, qa, enta, ca[i]),
                                                  (db["o"][i], pb, qb, entb, cb[i])):
                        if sg != 0 and q > 0:
                            fill = px * (1 - 0.0005) if sg > 0 else px * (1 + 0.0005)
                            pnl = (fill - e0) * q * sg
                            fee = abs(q * fill) * TAKER
                            cash += pnl - fee
                            pnls.append(pnl - fee)
                    pa = pb = 0.0; qa = qb = 0.0
            if pa == 0 and i + 1 < n and np.isfinite(z[i]) and abs(z[i]) > 2.0 and gate[i] and np.isfinite(beta[i]):
                nxa, nxb = da["o"][i + 1], db["o"][i + 1]
                if nxa > 0 and nxb > 0:
                    b2 = beta[i]
                    za_, zb_ = 1.0, -b2
                    gross = abs(za_) + abs(zb_)
                    qa = INIT * 0.015 / (1.5 * np.nan_to_num(Aa[i]) / max(nxa, 1e-12))
                    qa = min(qa, INIT * 0.25)
                    qb = qa * abs(b2)
                    if gross > 0 and np.isfinite(zb_):
                        scale = min(1.0, INIT * 1.0 / (qa * nxa + qb * nxb)) if (qa*nxa+qb*nxb) > INIT else 1.0
                        qa *= scale; qb *= scale
                    enta = nxa * (1 + 0.0005 if za_ > 0 else 1 - 0.0005)
                    entb = nxb * (1 + 0.0005 if zb_ > 0 else 1 - 0.0005)
                    pa, pb = za_, zb_
                    qa, qb = abs(qa), abs(qb)
                    cash -= (qa * enta + qb * entb) * TAKER
                    entry_i = i
                    hbar = hl[i] if np.isfinite(hl[i]) else 8.0
            if (pa != 0 or pb != 0) and fev[i]:
                cash -= qa * ca[i] * fr_a[i] * pa + qb * cb[i] * fr_b[i] * pb
            e = cash + (qa * (ca[i] - enta) * pa if pa else 0.0) + \
                    (qb * (cb[i] - entb) * pb if pb else 0.0)
            eqc[i] = e; peak = max(peak, e)
            mdd = max(mdd, (peak - e) / max(peak, 1e-9))
        st = stats(eqc, T)
        w = [x for x in pnls if x > 0]; ls = [x for x in pnls if x <= 0]
        pf = (sum(w) / abs(sum(ls))) if ls and sum(ls) != 0 else (np.inf if w else 0.0)
        wr = 100 * len(w) / max(len(pnls), 1)
        bh = 100 * (((ca[-1] / ca[0]) + (cb[-1] / cb[0])) / 2 - 1)
        print(f"  {A[:7]+'/'+B[:7]:<20}{nev:>12}{st['cum']:>+8.1f}%{st['mdd']:>7.1f}%"
              f"{pf:>7.2f}{wr:>5.0f}%{bh:>+9.0f}%{st['cum']-bh:>+8.0f}")
        rows.append(dict(pair=f"{A}/{B}", st=st, pf=pf, n=len(pnls), bh=bh,
                         pnls=pnls, eq=eqc, T=T))
    print("  " + "-" * 82)
    if rows:
        med = np.median([r["st"]["cum"] for r in rows])
        medbh = np.median([r["bh"] for r in rows])
        nbeat = sum(1 for r in rows if r["st"]["cum"] > r["bh"])
        print(f"  median pair: strategy {med:+.1f}%  passive {medbh:+.1f}%  "
              f"beat passive {nbeat}/{len(rows)}")
    print("  document claims OOS Sharpe 1.31, PF 1.33, DD -6.7%")
    return rows


# ==========================================================================
def liq_rev_not_tested():
    print("\n" + "=" * 100)
    print("STRATEGY 3 — LIQ-REV-1H-v1   NOT TESTED — required data unavailable")
    print("=" * 100)
    print("  Probed every public Binance endpoint for liquidation history:")
    print("    /fapi/v1/allForceOrders   404      /api/v3/rforceOrders  403")
    print("    /fapi/v1/forceOrders      404      /dapi/v1/forceOrders  404")
    print("  There is NO public historical liquidation feed. The document names")
    print("  Coinglass as its source, which is a paid product with no key here.")
    print()
    print("  Its entry trigger is L_t = liqVol(1h) / median(liqVol, 720h) > 3.0.")
    print("  Without liquidation volume that ratio is undefined for every bar, so")
    print("  the strategy cannot be evaluated as written.")
    print()
    print("  Open interest IS available at /futures/data/openInterestHist but only")
    print("  ~30 days deep (HTTP 400 beyond that), which covers one of its three")
    print("  gates and neither of the other two.")
    print()
    print("  Substituting a volume-shock proxy for the liquidation trigger would")
    print("  test a DIFFERENT strategy. Not done. Reported as untested.")


def main():
    print("=" * 100)
    print("MULTI-PAIR RESEARCH — 3 strategies: 2 testable, 1 blocked on data")
    print("All figures in the source document are labelled illustrative by the")
    print("document itself. Tested here on 45 months of real Binance 1h data.")
    print("=" * 100)
    a = xprop_lag()
    b = coint_pairs()
    liq_rev_not_tested()

    op = os.path.join(OUT, "multipair3_audit.txt")
    with open(op, "w", encoding="utf-8") as f:
        f.write("3-strategy multi-pair research — audit\n")
        f.write("=" * 60 + "\n\n")
        f.write("XPROP-LAG-1H-v1 (tested, real 1h data, 10 alts)\n")
        for r in a:
            f.write(f"  {r['alt']:<9} net {r['st']['cum']:+8.1f}%  DD {r['st']['mdd']:>6.1f}%"
                    f"  trades {r['n']:>5}  PF {r['pf']:>5.2f}  BH {r['bh']:>+7.0f}%"
                    f"  excess {r['st']['cum']-r['bh']:>+7.0f}pp\n")
        f.write("\nCOINT-DYN-1H-v1 (tested with OLS hedge, NOT Johansen)\n")
        for r in b:
            f.write(f"  {r['pair']:<20} net {r['st']['cum']:+8.1f}%  DD {r['st']['mdd']:>6.1f}%"
                    f"  trades {r['n']:>5}  PF {r['pf']:>5.2f}  BH {r['bh']:>+7.0f}%"
                    f"  excess {r['st']['cum']-r['bh']:>+7.0f}pp\n")
        f.write("\nLIQ-REV-1H-v1 — NOT TESTED\n")
        f.write("  No public Binance historical liquidation endpoint exists\n")
        f.write("  (allForceOrders/forceOrders 404, rforceOrders 403).\n")
        f.write("  Core trigger L_t > 3.0 is undefined without it. OI available\n")
        f.write("  only ~30 days. Substituting a proxy would test a different\n")
        f.write("  strategy, so it was not done.\n")
    print(f"\nwrote {op}")


if __name__ == "__main__":
    main()
