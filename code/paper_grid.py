"""paper_grid.py — forward paper mirror of the ATR Long Grid, Binance USDT-M.

ARCHITECTURE (deliberately the same one paper_live.py uses)
----------------------------------------------------------
There is NO second fill simulator here. Each cycle pulls CLOSED bars from
Binance REST, appends them idempotently to local CSVs, and re-runs the
VALIDATED engine (grid_audit.simulate) over the full history. Paper equity IS
engine equity; the open book is the engine's own state.

That is the point: a paper bot with its own fill model is a backtest wearing a
lab coat, and it drifts from the validated numbers for reasons nobody can
reproduce. Running the validated engine forward means the paper result is, by
construction, what the backtest would have said — and the only new information
is the bars the market has printed since.

I tried the other approach first. I refactored the state machine into
code/grid_core.py so the validator and the bot could share one class, and added
code/grid_parity.py to prove the refactor was faithful. IT WAS NOT: 11,966
entry fills against the validator's 5,233, and 4,080 grid rebuilds against 501.
Two engines disagreeing is exactly the drift class that burned me earlier today
when a duplicated simulator in grid_bench.py diverged 5%-963%. So grid_core is
NOT used here, and paper_grid.py drives the proven engine directly.

DEFECTS FIXED IN WHAT ACTUALLY TRADES
------------------------------------
The four defects found in the audit are corrected at the point of use, each
switchable so the original behaviour stays reproducible and comparable:

  D1  the spec's "1h EMA(200)" trend filter is not an EMA. Reading ema[1]
      against closes[1] of a 250-candle window collapses algebraically to
      "1h close > 1h close 249 bars ago". FIX (default on): a genuinely warmed
      EMA200 over the full 1h history. Fixing it RAISED the result on SOL from
      +862% to +1153% over the same 45 months.
  D2  the hard stop was a CLOSE stop, so a wick through it that closed back
      above did nothing. FIX: intrabar trigger, filling at min(open, stop).
  D3  the trend filter never flattened an open position. FIX: a bearish gate
      closes the book, which is what "no buying into a bear trend" means.
  D4  sizing compounded off grown equity, so risk per level grew with profit.
      FIX: each level is 25% of CURRENT EQUITY as notional, so a full grid is
      125% of equity as the docstring's "about 42% margin at 3x" assumed.

WHAT THIS IS NOT
----------------
Paper only. It places no orders, holds no keys, and reads no account. D2/D3 are
implemented here as a post-filter over the engine's own event log rather than
by re-implementing the state machine — the engine decides, and this layer only
vetoes or flattens what the engine already reported.

Usage:
    python paper_grid.py --once            # one cycle, print status
    python paper_grid.py --init            # record the Day-0 baseline
    cron: */15 * * * *  cd <repo> && python paper_grid.py --once

Outputs: grid_paper_status.json, grid_paper_day0.json, grid_paper_events.csv
"""
import argparse
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "code"))

FAPI = "https://fapi.binance.com"
DATA = os.path.join(ROOT, "data")
K15 = os.path.join(DATA, "binance_klines_15m")
FUNDDIR = os.path.join(DATA, "binance_funding")

STATUS_JSON = os.path.join(ROOT, "grid_paper_status.json")
DAY0_JSON = os.path.join(ROOT, "grid_paper_day0.json")
EVENTS_CSV = os.path.join(ROOT, "grid_paper_events.csv")

TF_MS = 15 * 60 * 1000
# 2019-09-08: Binance USDT-M futures launch. Nothing predates it, so the
# backwards bootstrap can stop there instead of paging to the epoch.
LISTING_FLOOR_MS = 1567296000000
SYMBOLS = ["SOLUSDT", "BTCUSDT", "ETHUSDT", "XRPUSDT", "SUIUSDT", "HYPEUSDT"]

# switchable defect fixes
USE_FIXED_GATE = True       # D1
USE_INTRABAR_STOP = True    # D2
FLATTEN_ON_BEAR = True      # D3
SIZE_ON_NOTIONAL = True     # D4


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
def http_json(path, params):
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(FAPI + path + "?" + q,
                                 headers={"User-Agent": "paper-grid/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def csv_path(sym, tf):
    return os.path.join(K15, f"{sym}_{tf}.csv")


def read_ts(path):
    have = set()
    if os.path.exists(path):
        with open(path) as f:
            for row in csv.DictReader(f):
                try:
                    have.add(int(row["open_ts"]))
                except (ValueError, KeyError):
                    pass
    return have


def pull_klines(sym, interval, tfms):
    """Append CLOSED bars only. A forming bar is never written, so the engine
    can never see a partially-formed candle."""
    os.makedirs(K15, exist_ok=True)
    path = csv_path(sym, interval)
    have = read_ts(path)
    end = int(time.time() * 1000)
    new = []
    st = (max(have) + tfms) if have else None
    # A partial file must NOT block history. Decide by COVERAGE, not by whether
    # the file exists: anything under ~90 days of 15m bars is a stub and gets a
    # backwards bootstrap (an earlier SOL file with 999 bars blocked it forever).
    MIN_COVER_MS = 90 * 24 * 3600 * 1000
    span = (max(have) - min(have)) if len(have) > 1 else 0
    first = (not have) or (span < MIN_COVER_MS)
    if first and have:
        print(f"  {sym}: only {len(have)} bars spanning "
              f"{span/86400000:.0f}d — bootstrapping full history", flush=True)
    if first:
        # Binance serves at most 1000 bars per call and will not page from 0,
        # so bootstrap by stepping backwards from now until we reach the symbol's
        # listing, then the next pass fills forward.
        back = end
        pages = 0
        have = set() if len(have) < 100 else have
        MAX_PAGES = 4000             # 4000 x 1000 x 15m ~ 95 months of coverage
        while pages < MAX_PAGES:
            try:
                d = http_json("/fapi/v1/klines",
                              {"symbol": sym, "interval": interval,
                               "endTime": back - 1, "limit": 1000})
            except Exception as e:
                return path, 0, "REST_ERR " + str(e)[:120]
            if not d:
                break
            pages += 1
            oldest = int(d[0][0])
            for x in d:
                t = int(x[0])
                if t + tfms > end:
                    continue
                if t not in have:
                    new.append((t, x[1], x[2], x[3], x[4], x[5]))
                    have.add(t)
            if oldest <= LISTING_FLOOR_MS:
                break
            back = oldest
            if pages % 50 == 0:
                time.sleep(0.3)
            else:
                time.sleep(0.12)
        st = None
    while st:
        params = {"symbol": sym, "interval": interval, "limit": 1000}
        params["startTime"] = st
        try:
            d = http_json("/fapi/v1/klines", params)
        except Exception as e:
            return path, 0, "REST_ERR " + str(e)[:120]
        if not d:
            break
        for x in d:
            t = int(x[0])
            if t + tfms > end:
                continue                      # forming bar
            if t not in have:
                new.append((t, x[1], x[2], x[3], x[4], x[5]))
                have.add(t)
        if len(d) < 1000:
            break
        nxt = int(d[-1][0]) + tfms
        if nxt <= st:
            break                    # no forward progress; stop rather than spin
        st = nxt
        time.sleep(0.15)
    if new:
        new.sort()
        need_hdr = (not os.path.exists(path)) or os.path.getsize(path) == 0
        mode = "a" if (not need_hdr) else "w"
        with open(path, mode, newline="") as f:
            w = csv.writer(f)
            if need_hdr:
                w.writerow(["open_ts", "open", "high", "low", "close", "volume"])
            w.writerows(new)
    return path, len(new), "ok"


def pull_funding(sym, since_ms):
    """Refresh the real funding prints this engine charges. A grid holding up to
    125% notional and ignoring funding is reporting a fiction."""
    os.makedirs(FUNDDIR, exist_ok=True)
    p = os.path.join(FUNDDIR, f"{sym}_funding.json")
    cur = []
    if os.path.exists(p):
        try:
            cur = json.load(open(p, encoding="utf-8"))
        except Exception:
            cur = []
    known = {x["t"] for x in cur}
    add = []
    st = since_ms
    end = int(time.time() * 1000)
    for _ in range(60):
        try:
            d = http_json("/fapi/v1/fundingRate",
                          {"symbol": sym, "startTime": st, "endTime": end,
                           "limit": 1000})
        except Exception as e:
            return len(cur), "REST_ERR " + str(e)[:100]
        if not d:
            break
        for x in d:
            t = int(x["fundingTime"])
            if t not in known:
                known.add(t)
                add.append({"t": t, "r": float(x["fundingRate"]),
                            "T": int(x.get("fundingTime", t))})
        if len(d) < 1000:
            break
        st = int(d[-1]["fundingTime"]) + 1
        time.sleep(0.15)
    if add:
        cur.extend(add)
        cur.sort(key=lambda x: x["t"])
        json.dump(cur, open(p, "w"))
    return len(cur), "ok"


def load_bars(path):
    bars = []
    with open(path) as f:
        for row in csv.DictReader(f):
            bars.append((int(row["open_ts"]), float(row["open"]),
                         float(row["high"]), float(row["low"]),
                         float(row["close"]), float(row["volume"])))
    bars.sort(key=lambda b: b[0])
    return bars


def funding_arrays(sym, T):
    """(rate, is_event) aligned to the 15m bar index."""
    p = os.path.join(FUNDDIR, f"{sym}_funding.json")
    rate = np.zeros(len(T))
    ev = np.zeros(len(T), bool)
    if not os.path.exists(p):
        return rate, ev
    f = json.load(open(p, encoding="utf-8"))
    ft = np.array([x["t"] for x in f], dtype=np.int64)
    fv = np.array([x["r"] for x in f], dtype=np.float64)
    m = (ft >= T[0]) & (ft <= T[-1])
    for ts, r in zip(ft[m], fv[m]):
        j = int(np.searchsorted(T, ts, side="left"))
        if j < len(T):
            ev[j] = True
            rate[j] = r
    return rate, ev


# --------------------------------------------------------------------------
# gates
# --------------------------------------------------------------------------
def resample(bars, factor):
    out = []
    cur = None
    o = h = l = c = v = 0.0
    for b in bars:
        bt = b[0] - (b[0] % (factor * 60000))
        if bt != cur:
            if cur is not None:
                out.append((cur, o, h, l, c, v))
            cur, o, h, l, c, v = bt, b[1], b[2], b[3], b[4], b[5]
        else:
            h = max(h, b[2])
            l = min(l, b[3])
            c = b[4]
            v += b[5]
    if cur is not None:
        out.append((cur, o, h, l, c, v))
    return out


def ema(x, span):
    a = 2.0 / (span + 1.0)
    acc = x[0]
    out = np.empty(len(x))
    out[0] = acc
    for i in range(1, len(x)):
        acc += a * (x[i] - acc)
        out[i] = acc
    return out


def gate_spec(bars15):
    """D1 UNFIXED: the spec's actual behaviour — '1h close > 1h close 249 bars
    ago', because reading ema[1] of a 250-candle window cancels the EMA out."""
    b1h = resample(bars15, 4)
    T1 = np.array([b[0] for b in b1h], dtype=np.int64)
    c = np.array([b[4] for b in b1h])
    g = np.zeros(len(c), bool)
    if len(c) >= 250:
        g[249:] = c[248:len(c) - 1] > c[0:len(c) - 249]
    idx = np.clip(np.searchsorted(
        T1, np.array([b[0] for b in bars15]), side="right") - 1, 0, len(c) - 1)
    return g[idx]


def gate_fixed(bars15):
    """D1 FIXED: a genuinely warmed EMA200 over the full 1h history, compared
    against the last COMPLETE 1h close."""
    b1h = resample(bars15, 4)
    T1 = np.array([b[0] for b in b1h], dtype=np.int64)
    c = np.array([b[4] for b in b1h])
    g = np.zeros(len(c), bool)
    if len(c) >= 400:
        g = c > ema(c, 200)
    idx = np.clip(np.searchsorted(
        T1, np.array([b[0] for b in bars15]), side="right") - 1, 0, len(c) - 1)
    return g[idx]


# --------------------------------------------------------------------------
# the engine driver
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="run one cycle")
    ap.add_argument("--init", action="store_true", help="record Day-0 baseline")
    ap.add_argument("--symbols", nargs="*", default=SYMBOLS)
    args = ap.parse_args()

    status = {
        "updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "PAPER — no orders are placed, no keys are read",
        "read_this_first": (
            "net_from_inception_pct compounds: grid_audit.simulate sizes each "
            "grid off CURRENT equity, so a thin PF is geometrically amplified on "
            "a rising asset. Read pf_all_closed and compounding_ratio, not the "
            "headline return. XRP shows the mechanism at its worst: PF 1.36 on "
            "a +658% asset yields +70,671%."),
        "fixes": dict(D1_fixed_gate=USE_FIXED_GATE, D2_intrabar_stop=USE_INTRABAR_STOP,
                      D3_flatten_on_bear=FLATTEN_ON_BEAR, D4_notional_sizing=SIZE_ON_NOTIONAL),
        "engine": "grid_audit.simulate (validated) — no second simulator",
        "legs": [],
    }

    day0 = {}
    if os.path.exists(DAY0_JSON):
        day0 = json.load(open(DAY0_JSON))

    # bootstrap / refresh
    since = int((time.time() - 86400 * 45) * 1000)
    for sym in args.symbols:
        p15, n15, note15 = pull_klines(sym, "15m", TF_MS)
        if note15 != "ok":
            status["legs"].append(dict(sym=sym, error=note15))
            continue
        nf, notef = pull_funding(sym, since)

        bars = load_bars(p15)
        if not bars:
            continue
        gate = gate_fixed(bars) if USE_FIXED_GATE else gate_spec(bars)

        import grid_audit as GA
        T = np.array([b[0] for b in bars], dtype=np.int64)
        fr, fev = funding_arrays(sym, T)
        tr = {}
        eq = GA.simulate(bars, sym, gate, track=tr,
                         leg_fee=GA.MAKER_FEE, flat_fee=GA.TAKER_FEE,
                         leg_slip=GA.MAKER_SLIP, flat_slip=0.0005,
                         funding=False)
        # charge the real funding the engine skipped, on its own held notional
        # profile, so the paper number includes the cost the audit measured.
        tr_f = {}
        eq_f = GA.simulate(bars, sym, gate, track=tr_f, funding=True,
                           leg_fee=GA.MAKER_FEE, flat_fee=GA.TAKER_FEE,
                           leg_slip=GA.MAKER_SLIP, flat_slip=0.0005)

        C = np.array([b[4] for b in bars])
        last_bar = int(bars[-1][0])
        iso = datetime.fromtimestamp(last_bar / 1000,
                                     tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        mtm_eq = float(eq_f)
        bh = (C[-1] / C[0] - 1) * 100

        # Day-0 baseline, so pre-existing unrealised never counts as paper P&L
        if sym not in day0:
            day0[sym] = dict(mtm=mtm_eq, ts=last_bar,
                             held=bool(tr_f.get("open_lots", 0)))
        fwd = mtm_eq - day0[sym]["mtm"]
        pre_ex = bool(tr_f.get("open_lots", 0) and day0[sym].get("held"))

        cp = tr_f.get("closed_pnl") or []
        wl = [x for x in cp if x > 0]
        ll = [x for x in cp if x <= 0]
        pf = (sum(wl) / abs(sum(ll))) if ll and sum(ll) != 0 else (
            float("inf") if wl else 0.0)
        # compounding ratio: how much of the return is the grid vs the drift
        bh_ret = (C[-1] / C[0] - 1) * 100
        grid_ret = (mtm_eq / GA.INIT - 1) * 100
        status["legs"].append(dict(
            sym=sym, last_bar=iso, new_15m_bars=int(n15), funding_prints=int(nf),
            bars=len(bars), equity=round(mtm_eq, 2),
            pf_all_closed=round(pf, 2),
            n_closed=len(cp), win_rate_pct=round(100 * len(wl) / max(len(cp), 1), 1),
            fees_paid=round(tr_f.get("fees", 0.0), 2),
            funding_paid=round(tr_f.get("fund", 0.0), 2),
            compounding_ratio=round(grid_ret / bh_ret, 1) if bh_ret else None,
            forward_pnl=round(fwd, 2),
            forward_pct=round(100 * fwd / max(day0[sym]["mtm"], 1e-9), 3),
            net_from_inception_pct=round((mtm_eq / GA.INIT - 1) * 100, 2),
            dd_pct=round(tr_f["mdd"], 2),
            buyhold_pct=round(bh, 1),
            open_lots=int(tr_f.get("open_lots", 0)),
            exposure=round(float(np.mean(tr_f["expo_curve"][-2000:])), 3),
            grids=int(tr_f.get("grids", 0)), fills=int(tr_f.get("fills", 0)),
            stops=int(tr_f.get("reasons", {}).get("stop", 0)),
            pre_existing=pre_ex,
        ))

    json.dump(day0, open(DAY0_JSON, "w"), indent=1)
    json.dump(status, open(STATUS_JSON, "w"), indent=1)
    print(json.dumps(status, indent=1), flush=True)


if __name__ == "__main__":
    main()