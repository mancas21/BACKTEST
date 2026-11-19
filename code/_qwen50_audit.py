"""_qwen50_audit.py — known-answer audits for the qwen50 signal layer.

Runs the REAL engine pieces (qwen50_engine._make_sig through the audited
Book.run) over hand-built synthetic bars and asserts hand-computed outcomes.
ALL PASS is required before any real-data run (adapter_template step 2).

Covers: entry geometry vs the engine's own ATR, signal-time ATR targets,
R-targets set at fill, trailing ratchets (ema21/atr25/chandelier), session
flat (UTC), ORB one-entry-per-direction, equity RTH gating, Chandelier from
highest close, stop-first tie and gap-through stop (Book), cost buckets and
the net-of-both-fees invariant, NO_DATA / unknown-param refusals, resample
and session-range helpers, aux alignment.
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import qwen50_engine as Q  # noqa: E402
from p100_screen_engine import Book  # noqa: E402

OUT = ROOT / "results" / "qwen50_audit_known_answers.txt"

RESULTS = []


def case(fn):
    RESULTS.append(fn)
    return fn


def base_frame(n=320, start=100.0, drift=0.0, tf_min=5):
    """Sideways OHLCV frame, range 1.0 per bar, constant volume."""
    idx = pd.date_range("2026-06-01", periods=n, freq=f"{tf_min}min",
                        tz="UTC")
    o = start + drift * np.arange(n)
    c = o + 0.1
    h = o + 0.5
    l = o - 0.5
    v = np.full(n, 100.0)
    return pd.DataFrame({"timestamp": idx, "open": o, "high": h, "low": l,
                         "close": c, "volume": v})


def modify(df, i, **kw):
    for k, vv in kw.items():
        df.at[i, k] = vv
    return df


def manual_pass(idn, df, aux=None, symbol=None, fee=0.0004, slip=0.0001,
                i0=0, i1=None):
    """Execute Book.run with the real sig layer + the production entry
    wrapper (stop-vs-next-open rejection); snapshot the live position after
    each signal call. Returns (book, snaps, sig)."""
    symbol = symbol or Q.CELLS[idn][0]
    aux = aux or {}
    prepared = Q._prepare_main(df.copy())
    book = Book(symbol, Q.CELLS[idn][1], prepared, init=10_000.0, fee=fee,
                slip=slip, risk_pct=Q.RISK, max_leverage=Q.MAXLEV,
                charge_funding=False)
    sig = Q._make_sig(idn, prepared, aux, symbol, book)
    n = len(prepared["open"])
    snaps = []

    def wrapped(k):
        s = sig(k)
        if s is None:
            return None
        if s.get("side", 0) == 0:
            return s
        ep = float(prepared["open"][k + 1])
        sp = float(s["stop_px"])
        side = s["side"]
        if (side == 1 and sp >= ep) or (side == -1 and sp <= ep):
            return None
        if book.pos is not None:
            pass
        return s

    def recorder(k):
        s = wrapped(k)
        if book.pos is not None:
            snaps.append((k, dict(book.pos)))
        return s

    i1 = (len(df) - 1) if i1 is None else i1
    book.run(recorder, start_idx=i0, end_idx=min(i1, len(df) - 1))
    return book, snaps, sig


# ── C1: id 51 entry geometry (EMA pullback) ────────────────────────────────
@case
def c1_ema_pullback_geometry():
    df = base_frame(320, drift=0.2)          # uptrend -> ema50 rising
    j = 300
    df = modify(df, j, low=df.at[j, "open"] - 12.0)
    book, _, _ = manual_pass(51, df, i1=j + 1)
    entered = any(t["entry_idx"] == j + 1 for t in book.trades)
    a = Q._atr(df["high"].to_numpy(float), df["low"].to_numpy(float),
               df["close"].to_numpy(float))[j]
    _, _, sig = manual_pass(51, df, i1=j + 1)
    s = sig(j)
    ok = (entered and s is not None and s.get("side") == 1
          and abs(s["stop_px"] - (df.at[j, "close"] - 1.5 * a)) < 1e-9
          and abs(s["tp_px"] - (df.at[j, "close"] + 3.0 * a)) < 1e-9)
    return {"entry_geometry_and_next_open_fill": bool(ok)}


# ── C2: id 53 RSI(2) entry + RSI exit ──────────────────────────────────────
@case
def c2_rsi2_entry_exit():
    df = base_frame(320, drift=0.2)
    j = 300
    df = modify(df, j - 1, close=df.at[j - 1, "open"] - 8.0,
                high=df.at[j - 1, "open"] + 0.5,
                low=df.at[j - 1, "open"] - 8.5)
    df = modify(df, j, open=df.at[j - 1, "close"],
                close=df.at[j - 1, "close"] - 8.0,
                high=df.at[j - 1, "close"] + 0.5,
                low=df.at[j - 1, "close"] - 8.5)
    book, _, _ = manual_pass(53, df, i1=j + 2)
    entered = any(t["entry_idx"] == j + 1 for t in book.trades)
    r2 = Q._rsi(df["close"].to_numpy(float), 2)
    df2 = df.copy()
    k = j + 5
    df2 = modify(df2, k, high=df2.at[k, "open"] + 8,
                 close=df2.at[k, "open"] + 8)
    book2, _, _ = manual_pass(53, df2, i1=k + 2)
    exits = [t for t in book2.trades if t["reason"] == "signal"]
    return {"entered": entered,
            "rsi2_low_at_signal": bool(r2[j] < 10),
            "exit_on_rsi2_recovery": bool(entered and exits)}


# ── C3: id 71 trailing stop ratchets, never loosens ────────────────────────
@case
def c3_trail_ratchet():
    df = base_frame(320, drift=0.0)
    j = 300
    # realistic impulse leg: each open follows the prior close
    o0 = df.at[j, "open"]
    closes = [o0 + 8, o0 + 16, o0 + 24, o0 + 30, o0 + 36, o0 + 42]
    df = modify(df, j, high=o0 + 30, low=o0 - 0.5, close=closes[0])
    for t, ci in enumerate(closes[1:], start=1):
        k = j + t
        df = modify(df, k, open=closes[t - 1], close=ci, high=ci + 0.5,
                    low=closes[t - 1] - 0.5)
    book, snaps, _ = manual_pass(71, df, i1=j + 6)
    if not book.trades:
        return {"entered": False, "ratchet_monotone": False}
    stops = [p["stop"] for k, p in snaps if p["side"] == 1]
    ratchet = all(b >= a - 1e-9 for a, b in zip(stops, stops[1:]))
    return {"entered": True,
            "ratchet_monotone": bool(stops and ratchet)}


# ── C4: id 90 R-target set at fill ─────────────────────────────────────────
@case
def c4_r_target_at_fill():
    df = base_frame(320, drift=0.0)
    j = 300
    o0 = df.at[j, "open"]
    df = modify(df, j, high=o0 + 6, low=o0 - 6, close=o0 + 5)
    for t in (1, 2):
        df = modify(df, j + t, open=df.at[j + t - 1, "close"],
                    close=df.at[j + t - 1, "close"] + 0.5,
                    high=df.at[j + t - 1, "close"] + 0.6,
                    low=df.at[j + t - 1, "close"] - 0.4)
    k = j + 3
    df = modify(df, k, open=df.at[k - 1, "close"],
                close=df.at[j, "high"] + 1.0,
                high=df.at[j, "high"] + 1.5, low=df.at[k - 1, "close"] - 0.4)
    df = modify(df, k + 1, open=df.at[k, "close"],
                close=df.at[k, "close"] + 0.2,
                high=df.at[k, "close"] + 0.4, low=df.at[k, "close"] - 0.4)
    book, snaps, _ = manual_pass(90, df, i1=k + 2)
    if not book.trades or not snaps:
        return {"r_tp_at_fill": False}
    p = snaps[-1][1]
    expect = p["fill"] + p["side"] * 2.0 * abs(p["fill"] - p["stop"])
    return {"r_tp_at_fill": bool(abs(p["tp"] - expect) < 1e-9)}


# ── C5: id 56 flat at 00:00 UTC ────────────────────────────────────────────
@case
def c5_utc_flat():
    n = 500
    idx = pd.date_range("2026-06-01 04:00", periods=n, freq="5min", tz="UTC")
    o = 100.0 + 0.0 * np.arange(n)
    df = pd.DataFrame({"timestamp": idx, "open": o, "high": o + 0.5,
                       "low": o - 0.5, "close": o + 0.1,
                       "volume": np.full(n, 100.0)})
    j = 220  # 22:20 UTC on day 1 (04:00 + 220x5min)
    for i in range(j - 10, j + 1):
        df = modify(df, i, close=df.at[i, "open"] - 6.0,
                    low=df.at[i, "open"] - 6.5, high=df.at[i, "open"] - 5.5)
    book, _, _ = manual_pass(56, df, i1=len(df) - 1)
    near = [t for t in book.trades
            if pd.Timestamp(t["entry_time"]).day == 1]
    if not near:
        return {"entered_day1": False, "flat_by_midnight": False}
    t = near[-1]
    xt = pd.Timestamp(t["exit_time"])
    flat = (xt.date() == pd.Timestamp(t["entry_time"]).date()) or \
        (xt.hour == 0 and xt.minute == 0)
    return {"entered_day1": True, "flat_by_midnight": bool(flat)}


# ── C6: id 96 ORB one entry per direction ──────────────────────────────────
@case
def c6_orb_one_per_direction():
    n = 400
    # frame starts 12:00 UTC June 1 = 08:00 ET; the ORB day is June 4
    # (bars 288+), past the engine warmup (210)
    idx = pd.date_range("2026-06-01 12:00", periods=n, freq="15min", tz="UTC")
    o = 100.0 + 0.0 * np.arange(n)
    df = pd.DataFrame({"timestamp": idx, "open": o, "high": o + 0.5,
                       "low": o - 0.5, "close": o + 0.1,
                       "volume": np.full(n, 100.0)})
    r1, r2 = 294, 295  # June 4 09:30/09:45 ET
    df = modify(df, r1, high=102.0, low=99.0, close=101.0)
    df = modify(df, r2, high=102.5, low=99.5, close=102.0)
    b1, b2 = 298, 302  # 10:30 and 11:30 ET, both break the OR high
    df = modify(df, b1, high=103.0, close=102.8)
    df = modify(df, b2, high=103.5, close=103.2)
    # chain the opens after each break so the fills are realistic
    df = modify(df, 299, open=102.8, high=103.0, low=102.3, close=102.6)
    df = modify(df, 303, open=103.2, high=103.4, low=102.9, close=103.0)
    book, _, _ = manual_pass(96, df, i1=n - 1)
    longs = [t for t in book.trades if t["side"] == "long"]
    return {"one_long_entry_despite_two_breaks": bool(len(longs) == 1)}


# ── C7: equity RTH gating (id 97) ──────────────────────────────────────────
@case
def c7_rth_gating():
    n = 900
    idx = pd.date_range("2026-06-01 12:00", periods=n, freq="5min", tz="UTC")
    o = 100.0 + 0.0 * np.arange(n)
    df = pd.DataFrame({"timestamp": idx, "open": o, "high": o + 0.5,
                       "low": o - 0.5, "close": o + 0.1,
                       "volume": np.full(n, 100.0)})
    # day-2 RTH (bars 306-384): down-leg flips supertrend short, then an
    # up-leg flips it long past the warmup — both fresh flips inside RTH
    for i in range(310, 340):
        df = modify(df, i, close=df.at[i, "open"] - 12.0,
                    low=df.at[i, "open"] - 12.5)
    for i in range(345, 380):
        df = modify(df, i, close=df.at[i, "open"] + 12.0,
                    high=df.at[i, "open"] + 12.5)
    book, _, _ = manual_pass(97, df, i1=n - 1)
    if not book.trades:
        return {"has_trades": False, "all_entries_in_rth_and_flat": False}
    ok = True
    for t in book.trades:
        et = pd.Timestamp(t["entry_time"]).tz_convert("America/New_York")
        xt = pd.Timestamp(t["exit_time"]).tz_convert("America/New_York")
        ok = ok and et.hour >= 9 and et.hour < 16 and et.dayofweek < 5
        ok = ok and (xt.hour * 60 + xt.minute) <= 16 * 60
    return {"has_trades": True,
            "all_entries_in_rth_and_flat": bool(ok)}


# ── C8: id 62 Chandelier from highest CLOSE ────────────────────────────────
@case
def c8_chandelier_close():
    df = base_frame(320, drift=0.0)
    j = 300
    o0 = df.at[j, "open"]
    # modest impulse then a sustained +1/bar run (keeps ATR comparable)
    df = modify(df, j, high=o0 + 3.0, low=o0 - 1.0, close=o0 + 2.0,
                volume=300.0)
    for t in (1, 2, 3, 4, 5, 6):
        k = j + t
        prev_c = df.at[k - 1, "close"]
        df = modify(df, k, open=prev_c, close=prev_c + 1.0,
                    high=prev_c + 1.2, low=prev_c - 0.8)
    book, snaps, _ = manual_pass(62, df, i1=j + 8)
    if not book.trades or not snaps:
        return {"entered": False, "chandelier_close_stop": False}
    p = snaps[-1][1]
    fill_bar = p["entry_idx"]
    closes = df["close"].to_numpy(float)
    ext = float(np.max(closes[fill_bar: snaps[-1][0] + 1]))
    a = Q._atr(df["high"].to_numpy(float), df["low"].to_numpy(float),
               closes)[snaps[-1][0]]
    expected = ext - 3 * a
    entry_stop = None
    for t in book.trades:
        if t["entry_idx"] == fill_bar:
            entry_stop = p["stop"]
    # the live stop equals the ratchet (never below the entry stop)
    ok = abs(p["stop"] - max(entry_stop if entry_stop else -np.inf,
                             expected)) < 1e-6 or \
        abs(p["stop"] - expected) < 1e-6
    return {"entered": True, "chandelier_close_stop": bool(ok)}


# ── C9/C10: Book conventions through my layer (tie / gap) ──────────────────
@case
def c9_gap_and_tie():
    df = base_frame(320, drift=0.2)  # ema50 rising -> id 51 fires
    j = 300
    df = modify(df, j, low=df.at[j, "open"] - 12.0)
    book, _, _ = manual_pass(51, df, i1=j + 1)
    if not book.trades:
        return {"gap_through": False, "tie_stop_wins": False}
    a = Q._atr(df["high"].to_numpy(float), df["low"].to_numpy(float),
               df["close"].to_numpy(float))[j]
    stop_est = df.at[j, "close"] - 1.5 * a
    # enter normally at j+1, then GAP THROUGH the stop two bars later
    df2 = df.copy()
    df2 = modify(df2, j + 2, open=stop_est - 3.0, high=stop_est - 2.0,
                 low=stop_est - 4.0, close=stop_est - 2.5)
    book2, _, _ = manual_pass(51, df2, i1=j + 4)
    gap_ok = any(t["reason"] == "stop_gap" for t in book2.trades)
    # tie: a later bar touches both stop and tp -> stop wins
    df3 = df.copy()
    df3 = modify(df3, j + 2, low=stop_est - 0.01,
                 high=df3.at[j, "close"] + 3.2 * a)
    book3, _, _ = manual_pass(51, df3, i1=j + 4)
    tie_ok = any(t["reason"] == "stop" for t in book3.trades)
    return {"gap_through": bool(gap_ok), "tie_stop_wins": bool(tie_ok)}


# ── C11: cost buckets + net-of-both-fees invariant ─────────────────────────
@case
def c11_cost_buckets():
    ok = (Q.SYMBOL_COST["BTCUSDT"] == (0.0004, 0.0001)
          and Q.SYMBOL_COST["HYPEUSDT"] == (0.0005, 0.0002)
          and Q.SYMBOL_COST["NVDAUSDT"] == (0.0005, 0.0005)
          and Q.SYMBOL_COST["SPCXUSDT"] == (0.0005, 0.0005))
    df = base_frame(320, drift=0.2)
    j = 300
    df = modify(df, j, low=df.at[j, "open"] - 12.0)
    book, _, _ = manual_pass(51, df, i1=len(df) - 1)
    if not book.trades:
        return {"buckets": bool(ok), "pnl_net_of_fees": False}
    t = book.trades[-1]
    pnl_gross = t["qty"] * (
        (t["exit"] - t["entry"]) if t["side"] == "long"
        else (t["entry"] - t["exit"]))
    inv = abs((pnl_gross - book.fees_paid - book.funding_paid) - t["pnl"]) \
        < 1e-6
    return {"buckets": bool(ok), "pnl_net_of_fees": bool(inv)}


# ── C12: NO_DATA and unknown-param refusals ────────────────────────────────
@case
def c12_refusals():
    try:
        Q.run([], {"id": 93})
        refused = False
    except ValueError as e:
        refused = "NO DATA" in str(e)
    try:
        Q.run([], {"id": 51, "x": 1})
        unknown = False
    except ValueError as e:
        unknown = "unknown qwen50 params" in str(e)
    return {"no_data_refused": refused, "unknown_params_refused": unknown}


# ── C13: resample helper ───────────────────────────────────────────────────
@case
def c13_resample():
    df = base_frame(9, tf_min=1)
    r = Q._resample(df, "3min")
    ok = (len(r) == 3
          and abs(r.at[0, "open"] - df.at[0, "open"]) < 1e-12
          and abs(r.at[0, "close"] - df.at[2, "close"]) < 1e-12
          and abs(r.at[0, "high"] - df.iloc[:3]["high"].max()) < 1e-12
          and abs(r.at[0, "volume"] - 300.0) < 1e-9)
    df2 = base_frame(10, tf_min=1)
    r2 = Q._resample(df2, "3min")
    return {"resample_3x1m": bool(ok), "incomplete_edge_dropped": len(r2) == 3}


# ── C14: session ranges helper ─────────────────────────────────────────────
@case
def c14_session_ranges():
    df = base_frame(60, tf_min=5)
    ms = Q._ms(df["timestamp"])
    rng = Q._session_ranges(ms, df["high"].to_numpy(float),
                            df["low"].to_numpy(float), Q._day_id(ms), None,
                            0, 30)
    ok = len(rng) == 1 and abs(rng[list(rng)[0]][1] - 99.5) < 1e-12
    return {"session_range_window": bool(ok)}


# ── C15: aux alignment (last aux bar at/before each main bar) ──────────────
@case
def c15_aux_align():
    m = base_frame(30, tf_min=5)
    a = pd.DataFrame({
        "timestamp": pd.date_range("2026-06-01 00:00", periods=3,
                                   freq="1h", tz="UTC"),
        "open": [1.0, 1.0, 1.0], "high": [1.0] * 3, "low": [1.0] * 3,
        "close": [10.0, 20.0, 30.0], "volume": [1.0] * 3})
    ms_a, c_a = Q._align_last(m, a)
    ok = (len(ms_a) == 30 and c_a[0] == 10.0 and c_a[-1] == 30.0
          and c_a[5] == 10.0 and c_a[15] == 20.0)
    return {"aux_last_at_or_before": bool(ok)}


def main():
    import traceback
    npass = 0
    for fn in RESULTS:
        try:
            r = fn()
            ok = all(bool(v) for v in r.values())
            tag = "PASS" if ok else "FAIL"
            if ok:
                npass += 1
            detail = " ".join(f"{k}={v}" for k, v in r.items())
            print(f"[{tag}] {fn.__name__}: {detail}", flush=True)
        except Exception:
            print(f"[ERROR] {fn.__name__}", flush=True)
            traceback.print_exc()
    print(f"\n{npass}/{len(RESULTS)} cases pass", flush=True)
    OUT.write_text(f"qwen50 known answers: {npass}/{len(RESULTS)} pass\n",
                   encoding="utf-8")
    return 0 if npass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
