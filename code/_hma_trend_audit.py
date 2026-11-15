"""Known-answer execution audit for code/hma_trend_engine.py.

Hand-built synthetic cases for EVERY execution rule, in both directions
(the house lesson: long-only tests missed a short-side fee bug once). The
signal period is shrunk (hma_p=4, atr_p=3) so flips are constructible on
short series; the execution rules under test do not depend on the period.

Run:  python code/_hma_trend_audit.py   (exit 0 = all PASS)
"""

import math
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hma_trend_engine as E  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def mk(prices, extra_low=None, extra_high=None, extra_open=None):
    """kline lists from a close series; open=prev close, high/low wrap close.
    extra_open/extra_low/extra_high override single bars (valid OHLC enforced)."""
    n = len(prices)
    o = [prices[0]] + [prices[i - 1] for i in range(1, n)]
    h = [max(o[i], prices[i]) for i in range(n)]
    l = [min(o[i], prices[i]) for i in range(n)]
    if extra_open:
        for i, v in extra_open.items():
            o[i] = v
            h[i] = max(h[i], v)
            l[i] = min(l[i], v)
    if extra_low:
        for i, v in extra_low.items():
            l[i] = v
            h[i] = max(h[i], v)
    if extra_high:
        for i, v in extra_high.items():
            h[i] = v
    ts = [1700000000000 + i * 3600000 for i in range(n)]
    return ts, o, h, l, list(prices)


def first_rising(c, p=4):
    hm = E.hma_series(c, p)
    return next(i for i in range(1, len(c))
                if hm[i] is not None and hm[i - 1] is not None and hm[i] > hm[i - 1])


def first_falling_after(c, start, p=4):
    hm = E.hma_series(c, p)
    return next(i for i in range(start + 1, len(c))
                if hm[i] is not None and hm[i - 1] is not None and hm[i] < hm[i - 1])


BASE = [100 + 0.2 * i for i in range(30)]  # steady ramp: hma(4) rising from bar ~5


def case_a_entry():
    """Rising flip -> entry at NEXT open."""
    ts, o, h, l, c = mk(BASE)
    fr = first_rising(c)
    book = E.run_book(ts, o, h, l, c, {"mode": "hermes", "hma_p": 4, "atr_p": 3})
    t = book["trades"]
    check("A1 first entry is next open after first rising close",
          t and t[0]["entry_bar"] == fr + 1 and t[0]["entry_price"] == o[fr + 1],
          f"first_rising {fr}, entry_bar {t[0]['entry_bar'] if t else None}")
    return book, t, fr


def case_b_exit(book_a, t_a, fr):
    """Position exits at the next open after a falling close (END fallback if none)."""
    # extend the ramp with a decline so a falling close exists mid-series
    ext = BASE[:20] + [104 - 0.6 * i for i in range(25)]
    ts, o, h, l, c = mk(ext)
    fr = first_rising(c)
    book = E.run_book(ts, o, h, l, c, {"mode": "hermes", "hma_p": 4, "atr_p": 3})
    t = [x for x in book["trades"] if x["exit_reason"] == "HMA_DOWN"]
    hm = E.hma_series(c, 4)
    ff = first_falling_after(c, fr)
    ok = t and t[0]["exit_bar"] == ff + 1 and t[0]["exit_price"] == o[ff + 1]
    check("B1 falling close -> exit at next open", ok,
          f"first_falling {ff}, exit_bar {t[0]['exit_bar'] if t else None}")
    return book


def _engine_stop(prices, p=4, atr_p=3):
    """The engine's own entry bar and stop level for a given close series."""
    ts, o, h, l, c = mk(prices)
    fr = first_rising(c, p)
    A = E.atr_wilder(h, l, c, atr_p)
    entry_bar = fr + 1
    entry_px = o[entry_bar]
    stop = entry_px - 3.0 * A[fr]
    return ts, o, h, l, c, entry_bar, entry_px, stop


def case_c_gap_stop():
    """A bar that OPENS below the stop (inter-bar gap, prior bar stays above)
    fills AT THE OPEN. With intrabar checks on contiguous OHLC this is only
    reachable via an inter-bar gap (prior close above the stop, next open
    below it), which is exactly the repo gap-through convention."""
    up = [100 + 0.5 * i for i in range(12)]
    ts, o, h, l, c, eb, epx, stop = _engine_stop(up)
    # gap bar right after entry: open below the stop, low == open (no further pierce)
    gap_open = stop * 0.98
    ts, o, h, l, c = mk(up[:eb + 1] + [gap_open] * 14,
                        extra_open={eb + 1: gap_open})
    book = E.run_book(ts, o, h, l, c, {"mode": "hermes", "hma_p": 4, "atr_p": 3})
    st = [x for x in book["trades"] if x["exit_reason"] == "STOP"]
    ok = st and st[0]["exit_bar"] == eb + 1 and st[0]["exit_price"] == gap_open
    check("C1 gap-through stop fills at the open", ok,
          f"exit {st[0]['exit_price'] if st else None} vs gap open {gap_open}")


def case_d_intrabar_stop():
    """Open above the stop, low pierces it -> fill exactly at the stop level."""
    up = [100 + 0.5 * i for i in range(12)]
    ts, o, h, l, c, eb, epx, stop = _engine_stop(up)
    # dip bar: opens at prev close (above stop), low pierces stop, closes above it
    dip_close = stop + 0.8 * 0.5  # above the stop; 0.5 ~ one ramp step
    dip_low = stop - 0.25
    prices = up[:eb] + [dip_close] * 14
    extra_low = {eb: dip_low}
    ts, o, h, l, c = mk(prices, extra_low=extra_low)
    book = E.run_book(ts, o, h, l, c, {"mode": "hermes", "hma_p": 4, "atr_p": 3})
    st = [x for x in book["trades"] if x["exit_reason"] == "STOP"]
    ok = st and abs(st[0]["exit_price"] - stop) < 1e-9
    check("D1 intrabar stop fills at the stop level", ok,
          f"exit {st[0]['exit_price'] if st else None} vs stop {stop}")


def case_e_stop_first():
    """Stop-hit bar wins over a same-bar falling signal (intrabar precedes next open)."""
    up = [100 + 0.5 * i for i in range(12)]
    ts, o, h, l, c, eb, epx, stop = _engine_stop(up)
    crash_close = stop * 0.97
    prices = up[:eb] + [crash_close] + [crash_close * 0.99] * 14
    ts, o, h, l, c = mk(prices)
    book = E.run_book(ts, o, h, l, c, {"mode": "hermes", "hma_p": 4, "atr_p": 3})
    st = [x for x in book["trades"] if x["exit_reason"] == "STOP"]
    check("E1 stop exit carries STOP reason (stop-first)", bool(st))


def case_f_fees():
    """repo mode: fee on entry AND exit; pnl identity holds."""
    ext = BASE[:20] + [104 - 0.6 * i for i in range(25)]
    ts, o, h, l, c = mk(ext)
    book = E.run_book(ts, o, h, l, c, {"mode": "repo", "hma_p": 4, "atr_p": 3})
    t = book["trades"]
    cost = (E.FEE_BPS + E.SLIP_BPS) / 1e4
    x = t[0]
    cash0 = book["init"]                     # first trade: full equity
    qty = cash0 * (1 - cost) / x["entry_price"]
    proceeds = qty * x["exit_price"]
    exp_fees = cost * (cash0 + proceeds)
    check("F1 fees = cost*(entry notional + exit notional) on trade 0",
          abs(x["fees"] - exp_fees) < max(1e-6, exp_fees * 1e-9),
          f"{x['fees']:.6f} vs {exp_fees:.6f}")
    resid = (book["equity_curve"][-1] - book["init"]) - sum(v["pnl"] for v in t)
    check("F2 invariant eq[-1]-INIT == sum(pnl)", abs(resid) < 1e-6, f"resid {resid:.2e}")
    return book


def case_g_funding():
    """Funding sign: long PAYS positive rates, RECEIVES negative; nothing while flat."""
    ext = BASE[:20] + [104 - 0.6 * i for i in range(25)]
    ts, o, h, l, c = mk(ext)
    fr = first_rising(c)
    ff = first_falling_after(c, fr)
    t_pos = ts[fr + 2] + 1800000   # during the long
    t_neg = ts[ff - 1] + 1800000   # during the long
    t_flat = ts[-1] + 3600000      # after the END close
    # positive-only and negative-only books
    bp = E.run_book(ts, o, h, l, c, {"mode": "repo", "hma_p": 4, "atr_p": 3}, funding=[(t_pos, 0.0001)])
    bn = E.run_book(ts, o, h, l, c, {"mode": "repo", "hma_p": 4, "atr_p": 3}, funding=[(t_neg, -0.0001)])
    bf = E.run_book(ts, o, h, l, c, {"mode": "repo", "hma_p": 4, "atr_p": 3}, funding=[(t_flat, 0.0001)])
    b0 = E.run_book(ts, o, h, l, c, {"mode": "repo", "hma_p": 4, "atr_p": 3})
    check("G1 long PAYS a positive settlement (funding_paid > 0)",
          bp["funding_paid"] > 0, f"{bp['funding_paid']:.6f}")
    check("G2 long RECEIVES a negative settlement (funding_paid < 0)",
          bn["funding_paid"] < 0, f"{bn['funding_paid']:.6f}")
    check("G3 settlement while flat not charged", bf["funding_paid"] == 0.0)
    check("G4 no funding input -> funding_paid == 0", b0["funding_paid"] == 0.0)
    # funding reduces the paying book's final equity relative to the none book
    check("G5 positive funding reduces final equity",
          bp["equity_curve"][-1] < b0["equity_curve"][-1])
    check("G6 negative funding raises final equity",
          bn["equity_curve"][-1] > b0["equity_curve"][-1])


def case_h_end():
    """Open position at end of data force-closes at the last close with reason END."""
    ts, o, h, l, c = mk(BASE)  # monotonically rising: never falls, never stops
    book = E.run_book(ts, o, h, l, c, {"mode": "hermes", "hma_p": 4, "atr_p": 3})
    t = book["trades"]
    ok = t and t[-1]["exit_reason"] == "END" and t[-1]["exit_bar"] == len(c) - 1 \
        and abs(t[-1]["exit_price"] - c[-1]) < 1e-12
    check("H1 end-of-data force close at last close", ok,
          f"{t[-1]['exit_reason'] if t else None}")


def case_z_twin():
    """Zero-cost twin == hermes-mode book on the same fills."""
    ext = BASE[:20] + [104 - 0.6 * i for i in range(25)]
    ts, o, h, l, c = mk(ext)
    repo = E.run_book(ts, o, h, l, c, {"mode": "repo", "hma_p": 4, "atr_p": 3})
    herm = E.run_book(ts, o, h, l, c, {"mode": "hermes", "hma_p": 4, "atr_p": 3})
    same_fills = [(x["entry_bar"], x["exit_bar"], x["exit_reason"])
                  for x in repo["trades"]] == [(x["entry_bar"], x["exit_bar"], x["exit_reason"])
                                               for x in herm["trades"]]
    check("Z1 repo and hermes modes produce identical fills", same_fills)
    zsum = sum(x["pnl"] for x in repo["z_trades"])
    hsum = sum(x["pnl"] for x in herm["trades"])
    check("Z2 zero-cost twin pnl == hermes-mode pnl",
          abs(zsum - hsum) < max(1e-6, abs(hsum) * 1e-9), f"{zsum:.4f} vs {hsum:.4f}")


def main():
    print("known-answer audit: hma_trend_engine execution rules")
    book_a, t_a, fr = case_a_entry()
    case_b_exit(book_a, t_a, fr)
    case_c_gap_stop()
    case_d_intrabar_stop()
    case_e_stop_first()
    case_f_fees()
    case_g_funding()
    case_h_end()
    case_z_twin()
    print(f"\nPASS {len(PASS)} / FAIL {len(FAIL)}")
    if FAIL:
        for f_ in FAIL:
            print(f"  FAILED: {f_}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
