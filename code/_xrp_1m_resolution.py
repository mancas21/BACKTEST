"""_xrp_1m_resolution.py — the decisive test the external audit asked for.

The 15m OHLC fill model credits a cover whenever the SAME 15m bar's high
reaches the cover level, and the 2026-10-31 stress proved 100% of the book's
trades are such same-bar round trips. A 15m bar cannot say whether price hit
the entry level or the cover level first; 1m bars mostly can.

This probe builds code/xrp_neutral_engine_1m.py from the LOCKED engine by
span replacement (markers must each match exactly once; the locked file is
never touched). The variant keeps the ENTIRE 15m state machine — grid anchor,
ATR(20) step, 1h trend filter, funding at 15m settlements, close-based stops,
cooldown, re-anchor — and resolves ONLY the intra-bar touches in 1m temporal
order: entries and covers fill on the 1m bars inside each 15m bar, and a cover
may fill only on a STRICTLY LATER minute than its entry.

Window: 2023-01-01 .. 2026-10-01 (the 1m tape's coverage = the artifact's OOS
segment). Baseline = the ORIGINAL engine on the identical slice.
"""

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))

ENGINE = os.path.join(ROOT, "code", "xrp_neutral_engine.py")
OUT1M = os.path.join(ROOT, "code", "xrp_neutral_engine_1m.py")

SPAN_START = "        # 1. resting entries fill. The ladder was armed at the close of the"
SPAN_END = "                n_cycles += 1"
INIT_ANCHOR = "    grids_built = fills = n_cycles = 0"

MINUTE_DATA = '''    # ── 1m fill resolution (probe): bucket the 1m tape into 15m bars ──
    _m1 = os.environ.get('XRP_1M_CSV')
    K = float(os.environ.get('XRP_STRESS_K', '0')) / 1e4
    same_minute_covers = 0
    if _m1:
        import csv as _csv
        _t0 = bars[0][0]
        _step_ms = bars[1][0] - bars[0][0] if len(bars) > 1 else 900000
        _idx = {b[0]: i for i, b in enumerate(bars)}
        _acc = {}
        with open(_m1) as _f:
            _r = _csv.reader(_f)
            next(_r)
            for _row in _r:
                _ts = int(_row[0])
                _b = _t0 + ((_ts - _t0) // _step_ms) * _step_ms
                _i = _idx.get(_b)
                if _i is not None:
                    _acc.setdefault(_i, []).append((float(_row[3]), float(_row[2])))
        MLOW, MHI, GOFF = [], [], []
        _run = 0
        for i, b in enumerate(bars):
            _ch = _acc.get(i) or [(b[3], b[2])]
            MLOW.append([c[0] for c in _ch])
            MHI.append([c[1] for c in _ch])
            GOFF.append(_run)
            _run += len(_ch)
    else:
        MLOW = [[b[3]] for b in bars]
        MHI = [[b[2]] for b in bars]
        GOFF = []
        for i in range(len(bars)):
            GOFF.append(i)
    same_minute_touched = 0
'''

MINUTE_WALK = '''        # 1+2 (1m-resolved): entries and covers fill in 1m temporal order
        # inside the 15m bar. A cover may fill only on a STRICTLY LATER minute
        # than its own entry (same-minute is unresolvable; counted, banned).
        for j in range(len(MLOW[t])):
            ml, mh = MLOW[t][j], MHI[t][j]
            gm = GOFF[t] + j
            for o_ in list(orders):
                px, side, q = o_
                touched = (ml < px * (1 - K)) if side > 0 else (mh > px * (1 + K))
                if not touched:
                    continue
                fill_px = px * (1 + leg_slip * side)
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
                lots.append([side * q, fill_px, cover, f, gm])
                orders.remove(o_)
                fills += 1
                fill_times.append(int(T[t]))
                eq_now = book_equity(C[t])
                if eq_now > 0:
                    max_delta_fill_pct = max(max_delta_fill_pct,
                                             abs(qty_now() * fill_px) / eq_now * 100)
            for lot in list(lots):
                px = lot[2]
                if lot[4] >= gm:
                    if (mh >= px * (1 + K)) if lot[0] > 0 else (ml <= px * (1 - K)):
                        same_minute_touched += 1
                        if track is not None:
                            track["same_minute_touched"] = same_minute_touched
                    continue
                touched = (mh >= px * (1 + K)) if lot[0] > 0 else (ml <= px * (1 - K))
                if touched:
                    close_lot(lot, px, leg_fee, leg_slip, "cover")
                    n_cycles += 1'''


def build():
    lines = open(ENGINE, encoding="utf-8").read().splitlines(keepends=True)
    starts = [i for i, ln in enumerate(lines) if ln.rstrip("\n") == SPAN_START]
    assert len(starts) == 1, f"span start matched {len(starts)}x"
    s = starts[0]
    ends = [i for i in range(s, len(lines)) if lines[i].rstrip("\n") == SPAN_END]
    assert ends, "span end not found"
    e = ends[0]
    tail = "".join(lines[e + 1:e + 4])
    assert "# 3. hard stop" in tail, "unexpected span tail: " + repr(tail[:80])
    init_count = sum(1 for ln in lines if ln.rstrip("\n") == INIT_ANCHOR)
    assert init_count == 1, f"init anchor matched {init_count}x"
    out = lines[:s] + [MINUTE_WALK + "\n"] + lines[e + 1:]
    text = "".join(out)
    assert text.count(INIT_ANCHOR) == 1
    text = text.replace(INIT_ANCHOR,
                        "    grids_built = fills = n_cycles = same_minute_touched = 0\n"
                        + MINUTE_DATA)
    open(OUT1M, "w", encoding="utf-8").write(text)
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def load_fresh(path, name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run(module, klines, k_env="0"):
    os.environ["XRP_STRESS_K"] = k_env
    module.EQUITY_PCT = 1.0
    module.LEVERAGE = 10.0
    raw = pd.read_csv(klines)
    raw.columns = [str(c).strip().lower() for c in raw.columns]
    raw = raw.sort_values("open_ts")
    ts = pd.to_datetime(raw["open_ts"], unit="ms", utc=True)
    raw = raw[ts >= pd.Timestamp("2023-01-01", tz="UTC")]
    ts = ts.loc[raw.index]
    raw = raw[ts < pd.Timestamp("2026-10-01 13:45:00", tz="UTC")]
    bars = [(int(r.open_ts), float(r.open), float(r.high), float(r.low),
             float(r.close), float(r.volume)) for r in raw.itertuples(index=False)]
    tr = {}
    module.simulate(bars, "XRPUSDT", track=tr, init=25.0,
                    trend_band=0.10, stop_atr_mult=0.5, cover_mult=1.0,
                    delta_max_pct=2.0, leg_fee=2.0 / 1e4, flat_fee=5.0 / 1e4,
                    flat_slip=5.0 / 1e4, funding=True,
                    fund_dir=os.path.join(ROOT, "data", "binance_funding"))
    cp = np.asarray(tr["closed_pnl"], float)
    pf, win, n_tr = module.metrics(list(cp))
    eqc = np.asarray(tr["eq_curve"], float)
    pk = np.maximum.accumulate(eqc)
    mdd = float(np.max((pk - eqc) / np.maximum(pk, 1e-9)) * 100.0)
    return {
        "engine": module.__name__,
        "n_bars_15m": len(bars),
        "profit_factor": round(float(pf), 4),
        "n_trades": int(n_tr),
        "win_rate": round(float(win), 2),
        "return_pct": round(100.0 * (float(eqc[-1]) / 25.0 - 1.0), 2),
        "max_dd_pct": round(mdd, 2),
        "same_minute_touched": int(tr.get("same_minute_touched", -1)),
        "final_equity_usdt": round(float(eqc[-1]), 2),
    }


def main():
    sha = build()
    print("built xrp_neutral_engine_1m.py sha", sha, flush=True)
    klines = os.path.join(ROOT, "data", "binance_klines_15m", "XRPUSDT_15m.csv")
    out = {}
    base = load_fresh(ENGINE, "xrp_orig_1mwin")
    out["baseline_15m_model_2023plus"] = run(base, klines)
    print(json.dumps(out["baseline_15m_model_2023plus"]), flush=True)
    os.environ["XRP_1M_CSV"] = os.path.join(ROOT, "data", "binance_klines_1m",
                                            "XRPUSDT_1m.csv")
    m1 = load_fresh(OUT1M, "xrp_1m_resolved")
    out["one_minute_resolved"] = run(m1, klines)
    out["one_minute_resolved"]["engine"] = "xrp_neutral_engine_1m"
    print(json.dumps(out["one_minute_resolved"]), flush=True)
    json.dump(out, open(os.path.join(HERE, "_xrp_1m_resolution_out.json"), "w"), indent=1)
    print("WROTE code/_xrp_1m_resolution_out.json", flush=True)


if __name__ == "__main__":
    main()
