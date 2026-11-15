"""HMA(34) Trend — declared reconstruction of the external "hermes" pack.

SOURCE OF RECORD: code/hma_trend_sources/ (byte-identical copies of the
scratch JSONs the external session produced; sha256 in MANIFEST.json). The
session's own engine code did NOT survive — only its outputs. Everything
below was measured from those outputs (code/_hma_trend_parity.py re-measures
it): this is a DECLARED reconstruction, frozen before its first repo-market
run, not a bit-for-bit clone.

MEASURED from the source trades (JUPUSDT 1h full-2026 run, 247 trades):
  - fills: entry at open[entry_bar] (247/247) and HMA_DOWN exits at
    open[exit_bar] (229/229) -> signal on close, fill NEXT OPEN.
  - STOP exits: 18/18 fill intrabar at exactly entry - 3.0 * ATR(14, Wilder)
    evaluated at the SIGNAL bar (ratio stdev 0.0000).
  - pnl_pct == raw price delta on all 247 trades -> ZERO fees, long-only.
  - sizing: full equity per trade, compounding.
  - 4 zero-pnl same-bar trades (entry_bar == exit_bar) prove a flag-ordering
    quirk of the source engine (entry and exit flags on one close, applied
    enter-then-exit at the same open). NOT reproduced here (declared).

DECLARED (approximation, documented): the exact exit predicate of the source
engine is NOT recoverable from the 247-trade sample. No candidate family
(HMA slope on 1h/4h and 7 price sources, periods 10-50, lags 1-3, close vs
HMA, entry-relative, HMA-trailing, unrealized-PnL thresholds, price-action)
separates the 229 exit bars from the 2,952 hold bars perfectly. The declared
rule covers ~90% of the source exits per component; _hma_trend_parity.py
publishes the residual fit.

Declared spec (frozen 2026-11-14, before any repo-market run):
  - HMA(34) standard: WMA(2*WMA(close,17) - WMA(close,34), 5) (sq = int(sqrt(34))).
  - ATR(14) Wilder.
  - ENTRY (long-only, one position): HMA rising at close[i] -> fill open[i+1].
  - EXIT: HMA falling at close[i] (hm[i] < hm[i-1]) -> fill open[i+1]. This is
    the literal reading of the pack's own exit label 'HMA_DOWN'. The
    alternative reading 'close < HMA' (true at 201/229 source exits but with
    906 hold-bar violations) is available as exit_below=True (declared
    sensitivity; it trades 3.3x more often and changes the book's character).
  - STOP: entry - 3.0 * ATR(14 @ signal bar), checked intrabar with
    stop-first and gap-through-at-open (fill = min(stop, open)).
  - Sizing: 100% of current equity per trade (compounding), like the claim.
  - mode=hermes: zero fees, no funding, window sliced to the source pack's
    own per-pair 2026 windows (claim-check of the external table).
  - mode=repo: 5 bps fee + 0.5 bps slip per side, funding charged at real
    settlements on the open notional, full repo history, zero-cost control
    inside the artifact, 70/30 chronological split, thirds, top-5
    concentration, bootstrap CI, and the accounting invariant
    eq[-1] - INIT == sum(pnl) asserted inside every artifact.

RECONSTRUCTION GAP (measured, code/_hma_trend_parity.py): on the pack's OWN
bytes with its OWN fills and stop rule, the declared book reproduces the
trade count (292 vs 247) and the hold profile (12.7 vs 12.9 bars) but NOT
the return (declared +86.4% vs the claim's +890.5%, PF 1.18 vs 2.25, WR
30.8 vs 40.9). The claim's edge lives in exit timing that no defensible
reading of 'HMA(34) Trend' reproduces. The external numbers are therefore
UNREPRODUCIBLE FROM THEIR OWN OUTPUTS -- the audit conclusion, independent
of the missing source code. No parameter was fitted to the claim's trades.
"""

import bisect
import json
import math
import os
import random
import statistics

ENGINE_VERSION = "hmatrend-1"
FEE_BPS = 5.0
SLIP_BPS = 0.5
BOOT_N = 2000
BOOT_SEED = 20261114

# The source pack's per-pair 2026 windows (from hma_backtest_is_oos_all_pairs.json).
# Used only by mode=hermes when the caller does not pass start/end explicitly.
HERMES_WINDOWS = {
    "BTCUSDT": ("2026-01-01", "2026-05-06"),
    "ETHUSDT": ("2026-01-01", "2026-05-06"),
    "HYPEUSDT": ("2026-01-01", "2026-05-06"),
    "JUPUSDT": ("2026-01-01", "2026-05-06"),
    "SOLUSDT": ("2026-01-01", "2026-05-06"),
    "SUIUSDT": ("2026-01-01", "2026-05-06"),
    "XRPUSDT": ("2026-01-01", "2026-05-06"),
    "1000PEPEUSDT": ("2026-01-01", "2026-05-06"),
    "ARBUSDT": ("2026-01-01", "2026-05-06"),
    "NVDAUSDT": ("2026-03-26", "2026-07-29"),
    "SPCXUSDT": ("2026-05-21", "2026-09-22"),
}


def _wma(a, p):
    out = [None] * len(a)
    den = p * (p + 1) / 2
    for i in range(p - 1, len(a)):
        s = 0.0
        for w in range(1, p + 1):
            s += w * a[i - p + w]
        out[i] = s / den
    return out


def hma_series(x, p):
    sq = int(p ** 0.5)
    h1 = _wma(x, p // 2)
    h2 = _wma(x, p)
    raw = [(2 * a - b) if (a is not None and b is not None) else None
           for a, b in zip(h1, h2)]
    start = next(i for i, v in enumerate(raw) if v is not None)
    return [None] * start + _wma(raw[start:], sq)


def atr_wilder(h, l, c, per):
    n = len(c)
    trs = [h[0] - l[0]]
    for i in range(1, n):
        trs.append(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
    a = sum(trs[:per]) / per
    out = [None] * (per - 1) + [a]
    for i in range(per, n):
        tr = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        a = (a * (per - 1) + tr) / per
        out.append(a)
    return out


def _read_klines(path):
    """Repo kline CSV: open_ts,open,high,low,close,volume (extra cols/blanks tolerated)."""
    o, h, l, c, ts = [], [], [], [], []
    with open(path) as f:
        for line in f:
            parts = line.rstrip("\n").split(",")
            if len(parts) < 6:
                continue
            try:
                ts.append(int(parts[0]))
                o.append(float(parts[1]))
                h.append(float(parts[2]))
                l.append(float(parts[3]))
                c.append(float(parts[4]))
            except ValueError:
                continue  # header or malformed row
    return ts, o, h, l, c


def _read_funding(path):
    """data/binance_funding/<SYM>_funding.json: [{t, r, ...}] (older rows lack T)."""
    if not path or not os.path.exists(path):
        return []
    raw = json.load(open(path))
    return sorted((int(x["t"]), float(x["r"])) for x in raw)


def _iso_ms(s):
    """'YYYY-MM-DD' or ISO datetime (UTC) -> epoch ms. None passthrough."""
    if not s:
        return None
    s = s.replace("T", " ").replace("Z", "").strip()
    date, _, time = s.partition(" ")
    y, m, d = (int(v) for v in date.split("-"))
    hh = mm = 0
    if time:
        hh = int(time.split(":")[0])
        if ":" in time:
            mm = int(time.split(":")[1])
    import calendar
    return calendar.timegm((y, m, d, hh, mm, 0)) * 1000


def run_book(ts, o, h, l, c, params, funding=()):
    """One long-only book + a zero-cost twin computed on the same fills.

    Per bar i (repo conventions = the measured source conventions):
      1. fills at open[i]: gap-through stop first, then scheduled exit, then
         scheduled entry (entry only if still flat after the exit).
      2. intrabar stop while held (stop-first priority).
      3. signals on close[i] schedule next-open actions.
    """
    mode = params.get("mode", "repo")
    cost = (FEE_BPS + SLIP_BPS) / 1e4 if mode == "repo" else 0.0
    hma_p = int(params.get("hma_p", 34))
    atr_p = int(params.get("atr_p", 14))
    stop_mult = float(params.get("stop_mult", 3.0))
    init = float(params.get("init", 10000.0))
    exit_below = bool(params.get("exit_below", False))  # declared sensitivity only

    n = len(c)
    hm = hma_series(c, hma_p)
    A = atr_wilder(h, l, c, atr_p)
    fts = [t for t, _ in funding]
    frate = dict(funding)

    in_pos = False
    entry_px = qty = stop = 0.0
    entry_bar = -1
    entry_cost0 = 0.0        # cash committed at entry (equity minus entry fee)
    entry_fee = 0.0
    funding_open = 0.0       # funding accrued by the open position
    cash = init              # equity when flat
    fidx = 0
    sched_entry = sched_exit = False
    trades = []
    funding_paid = 0.0
    equity_curve = []
    n_f = len(fts)

    def _exit(i, px, reason):
        nonlocal in_pos, cash, funding_paid
        proceeds = qty * px
        fee_exit = proceeds * cost
        pnl = proceeds - fee_exit - funding_open - entry_cost0
        cash += proceeds - fee_exit - funding_open
        funding_paid += funding_open
        trades.append({
            "entry_bar": entry_bar, "exit_bar": i,
            "entry_price": entry_px, "exit_price": px,
            "exit_reason": reason, "pnl": pnl,
            "pnl_pct": (px / entry_px - 1) * 100.0,
            "funding": funding_open, "fees": entry_fee + fee_exit,
        })
        in_pos = False

    for i in range(n):
        # ---- 1. fills at open[i] ----
        if in_pos and o[i] <= stop:
            _exit(i, o[i], "STOP")            # gap-through at the open
        elif in_pos and sched_exit:
            _exit(i, o[i], "HMA_DOWN")
        sched_exit = False
        if (not in_pos) and sched_entry and o[i] > 0 and i >= 1 and A[i - 1] is not None:
            cash0 = cash
            entry_fee = cash0 * cost
            qty = (cash0 - entry_fee) / o[i]
            entry_px = o[i]
            entry_bar = i
            # the position consumes ALL the cash (the entry fee bought fewer
            # units); pnl is measured against the full committed cash so the
            # accounting invariant closes exactly.
            entry_cost0 = cash0
            stop = entry_px - stop_mult * A[i - 1]
            assert stop < entry_px, "stop must sit strictly below the entry fill"
            in_pos = True
            funding_open = 0.0
            cash = 0.0
        sched_entry = False

        # ---- 1b. funding settlements during this bar, on the post-fill state ----
        nxt = ts[i + 1] if i + 1 < n else ts[i] + 1
        while fidx < n_f and fts[fidx] < nxt:
            if in_pos:
                funding_open += frate[fts[fidx]] * qty * c[i]
            fidx += 1

        # ---- 2. intrabar stop while held ----
        if in_pos and l[i] <= stop:
            _exit(i, min(stop, o[i]), "STOP")

        # ---- 3. signals on close[i] ----
        if i >= 1 and hm[i] is not None and hm[i - 1] is not None:
            if in_pos:
                if hm[i] < hm[i - 1] or (exit_below and c[i] < hm[i]):
                    sched_exit = True
            elif hm[i] > hm[i - 1]:
                sched_entry = True
        equity_curve.append(cash + (qty * c[i] - funding_open if in_pos else 0.0))

    if in_pos:
        _exit(n - 1, c[n - 1], "END")
        # the END close happens after the loop's last equity point; that point
        # was marked while still holding (gross of the exit fee). Replace it
        # with the true post-exit equity so the invariant closes to the cent.
        equity_curve[-1] = cash

    # ---- zero-cost twin: same fills, no fees, no funding ----
    # Each trade record IS a complete round trip (fees/funding were charged
    # outside the fill prices), so the twin compounds the raw price return.
    z_cash = init
    z_trades = []
    for t in trades:
        ret = t["exit_price"] / t["entry_price"] - 1.0
        zpnl = z_cash * ret
        z_cash += zpnl
        z_trades.append({"entry_bar": t["entry_bar"],
                         "exit_bar": t["exit_bar"], "pnl": zpnl})

    return {"trades": trades, "z_trades": z_trades, "equity_curve": equity_curve,
            "funding_paid": funding_paid, "init": init}


def _metrics(trades, z_trades, equity_curve, init, n_bars, bh_final):
    n = len(trades)
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    gp = sum(t["pnl"] for t in wins)
    gl = -sum(t["pnl"] for t in losses)
    pf = (gp / gl) if gl > 0 else (float("inf") if gp > 0 else 0.0)
    final = equity_curve[-1]
    ret_pct = (final / init - 1) * 100.0

    peak, mdd = -1e18, 0.0
    for v in equity_curve:
        peak = max(peak, v)
        if peak > 0:
            mdd = max(mdd, (peak - v) / peak * 100.0)

    tot = sum(t["pnl"] for t in trades)
    top5 = (sum(sorted((t["pnl"] for t in trades), reverse=True)[:5]) / tot * 100.0) if tot else 0.0

    def _period(lo, hi, book):
        sel = [t for t in book if lo <= t["entry_bar"] < hi]
        p = sum(t["pnl"] for t in sel)
        w = [t for t in sel if t["pnl"] > 0]
        ls = [t for t in sel if t["pnl"] <= 0]
        g = sum(t["pnl"] for t in w)
        gl_ = -sum(t["pnl"] for t in ls)
        ppf = (g / gl_) if gl_ > 0 else (float("inf") if g > 0 else 0.0)
        return {"n": len(sel), "pnl": p, "pf": ppf}

    third = n_bars // 3
    thirds = [_period(0, third, trades), _period(third, 2 * third, trades),
              _period(2 * third, n_bars, trades)]
    thirds_green = sum(1 for t3 in thirds if t3["pnl"] > 0)
    split = int(n_bars * 0.7)
    oos = _period(split, n_bars, trades)

    rng = random.Random(BOOT_SEED)
    if n >= 5:
        pnls = [t["pnl"] for t in trades]
        means = []
        for _ in range(BOOT_N):
            s = 0.0
            for _j in range(n):
                s += pnls[rng.randrange(n)]
            means.append(s / n)
        means.sort()
        ci_lo = means[int(0.025 * BOOT_N)]
        ci_hi = means[int(0.975 * BOOT_N) - 1]
        mu = sum(pnls) / n
        sd = statistics.stdev(pnls) if n > 1 else 0.0
        tstat = (mu / (sd / math.sqrt(n))) if sd > 0 else 0.0
    else:
        ci_lo = ci_hi = tstat = 0.0

    z_final = init + sum(t["pnl"] for t in z_trades)
    z_ret = (z_final / init - 1) * 100.0
    zwins = [t for t in z_trades if t["pnl"] > 0]
    zl = [t for t in z_trades if t["pnl"] <= 0]
    zgp = sum(t["pnl"] for t in zwins)
    zgl = -sum(t["pnl"] for t in zl)
    zpf = (zgp / zgl) if zgl > 0 else (float("inf") if zgp > 0 else 0.0)

    m = {
        "n_trades": n,
        "n_wins": len(wins),
        "n_losses": len(losses),
        "win_rate_pct": (len(wins) / n * 100.0) if n else 0.0,
        "gross_profit": gp,
        "gross_loss": gl,
        "profit_factor": pf,
        "return_pct": ret_pct,
        "final_equity": final,
        "max_dd_pct": mdd,
        "best5_share_pct": top5,
        "thirds_green": thirds_green,
        "oos_profit_factor": oos["pf"],
        "oos_return_pct": (oos["pnl"] / init * 100.0),
        "oos_n_trades": oos["n"],
        "boot_ci_lo": ci_lo,
        "boot_ci_hi": ci_hi,
        "boot_t_stat": tstat,
        "bh_return_pct": (bh_final / init - 1) * 100.0,
        "excess_return_pct": ret_pct - (bh_final / init - 1) * 100.0,
        "zero_cost_return_pct": z_ret,
        "zero_cost_pf": zpf,
        "zero_cost_n_trades": len(z_trades),
        "cost_drag_pp": z_ret - ret_pct,
        "pnl_identity_resid": (final - init) - sum(t["pnl"] for t in trades),
    }
    return m, {"thirds": thirds, "split": split, "oos": oos}


def dispatch(paths, params):
    """Adapter entry: paths[0] = klines CSV, paths[1] (optional) = funding JSON.

    params: mode (repo|hermes), start, end (ISO dates, hermes windows default
    when mode=hermes), hma_p, atr_p, stop_mult, exit_below, init.
    """
    mode = params.get("mode", "repo")
    sym = params.get("symbol") or params.get("card", "")
    kpath = paths[0]
    fpath = paths[1] if len(paths) > 1 else None
    funding = _read_funding(fpath) if mode == "repo" else []

    ts, o, h, l, c = _read_klines(kpath)
    if not ts:
        raise RuntimeError(f"no kline rows parsed from {kpath}")

    start = end = None
    if mode == "hermes":
        w = HERMES_WINDOWS.get(sym)
        start = _iso_ms(params.get("start") or (w[0] if w else None))
        end = _iso_ms(params.get("end") or (w[1] if w else None))
    else:
        start = _iso_ms(params.get("start"))
        end = _iso_ms(params.get("end"))
    if start or end:
        keep = [i for i in range(len(ts))
                if (start is None or ts[i] >= start) and (end is None or ts[i] < end)]
        ts = [ts[i] for i in keep]; o = [o[i] for i in keep]
        h = [h[i] for i in keep]; l = [l[i] for i in keep]
        c = [c[i] for i in keep]
    n = len(ts)
    if n < 200:
        raise RuntimeError(f"window too small after slice: {n} bars ({kpath})")

    book = run_book(ts, o, h, l, c, params, funding)
    init = book["init"]
    bh_final = init * (c[-1] / c[0])
    m, extra = _metrics(book["trades"], book["z_trades"], book["equity_curve"],
                        init, n, bh_final)

    # accounting invariant: eq[-1] - INIT == sum(pnl)  (fees+funding inside pnl)
    resid = m["pnl_identity_resid"]
    tol = max(1e-6, abs(init) * 1e-9)
    assert abs(resid) < tol, f"pnl identity residual {resid} exceeds {tol}"

    split_iso = ""
    if extra["split"] < n:
        import datetime
        split_iso = datetime.datetime.utcfromtimestamp(
            ts[extra["split"]] / 1000).strftime("%Y-%m-%d")

    metrics = dict(m)
    metrics.update({
        "strategy": "HMA(34) Trend (declared reconstruction of the hermes pack)",
        "adapter": "hmatrend",
        "engine_version": ENGINE_VERSION,
        "mode": mode,
        "symbol": sym,
        "timeframe": "1h",
        "bars": n,
        "window_start_utc": datetime.datetime.utcfromtimestamp(
            ts[0] / 1000).strftime("%Y-%m-%d"),
        "window_end_utc": datetime.datetime.utcfromtimestamp(
            ts[-1] / 1000).strftime("%Y-%m-%d"),
        "split_idx": extra["split"],
        "split_date_utc": split_iso,
        "hma_p": int(params.get("hma_p", 34)),
        "atr_p": int(params.get("atr_p", 14)),
        "stop_mult": float(params.get("stop_mult", 3.0)),
        "exit_rule": "hma_falling (declared; exit_below sensitivity available)",
        "entry_rule": "hma_rising (declared)",
        "sizing": "100% equity per trade, compounding",
        "fill_model": "next_open_stop_first_gap_through",
        "cost_bp_roundtrip": (FEE_BPS + SLIP_BPS) * 2 if mode == "repo" else 0.0,
        "fee_bps_per_side": FEE_BPS if mode == "repo" else 0.0,
        "slippage_bps_per_side": SLIP_BPS if mode == "repo" else 0.0,
        "funding_model": ("real settlements on open notional" if mode == "repo"
                          else "none (hermes convention, declared)"),
        "funding_charged": mode == "repo",
        "funding_paid": book["funding_paid"],
        "reconstruction": (
            "MEASURED: next-open fills 100%, stop=entry-3.0*ATR14(signal) exact "
            "(18/18), zero fees, long-only, full-equity compounding. DECLARED: "
            "entry=hma_rising, exit=hma_falling (source engine's exact exit "
            "predicate not recoverable from the 247-trade sample; 'close<hma' "
            "kept as exit_below sensitivity; zero-pnl same-bar quirk not "
            "reproduced). See code/_hma_trend_parity.py."),
    })

    # ---- the claim's own numbers, carried INSIDE the hermes artifacts ----
    # (source-of-record JSON, already sha-bound as an adapter source; the
    # report quotes these THROUGH the artifact so guard can back them)
    if mode == "hermes":
        src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "hma_trend_sources")
        try:
            claim = json.load(open(os.path.join(
                src_dir, "hma_backtest_is_oos_all_pairs.json")))
            # index by symbol
            crow = next((v for v in claim.values()
                         if isinstance(v, dict) and v.get("symbol") == sym), None)
        except (OSError, json.JSONDecodeError):
            crow = None
        if crow:
            metrics.update({
                "claim_n_klines": crow.get("n_klines"),
                "claim_is_n_trades": crow.get("is", {}).get("n_trades"),
                "claim_is_return_pct": crow.get("is", {}).get("total_return"),
                "claim_is_pf": crow.get("is", {}).get("profit_factor"),
                "claim_oos_n_trades": crow.get("oos", {}).get("n_trades"),
                "claim_oos_return_pct": crow.get("oos", {}).get("total_return"),
                "claim_oos_pf": crow.get("oos", {}).get("profit_factor"),
                "claim_oos_bh_return_pct": crow.get("oos", {}).get("bh_return"),
                "claim_oos_excess_pct": crow.get("oos", {}).get("excess_return"),
            })
        if sym == "JUPUSDT":
            try:
                full = json.load(open(os.path.join(
                    src_dir, "hma_backtest_results.json")))
                metrics.update({
                    "claim_full_return_pct": full.get("total_return_pct"),
                    "claim_full_pf": full.get("profit_factor"),
                    "claim_full_n_trades": full.get("total_trades"),
                    "claim_full_max_dd_pct": full.get("max_drawdown_pct"),
                    "claim_full_bh_return_pct": full.get("buy_hold_return_pct"),
                })
                # parity numbers measured against the claim's own trade list
                # (same definitions as code/_hma_trend_parity.py), carried in
                # the artifact so the report can cite them. The parity book
                # runs on the claim's FULL bytes (7618 bars, all 2026), not on
                # this artifact's sliced IS/OOS window.
                st = full.get("trades") or []
                kj = json.load(open(os.path.join(src_dir, "jup_1h_2026.json")))
                p_ts = [b[0] for b in kj]
                p_o = [float(b[1]) for b in kj]
                p_h = [float(b[2]) for b in kj]
                p_l = [float(b[3]) for b in kj]
                p_c = [float(b[4]) for b in kj]
                p_book = run_book(p_ts, p_o, p_h, p_l, p_c,
                                  {"mode": "hermes"})
                if st:
                    money_wins = [t for t in st if t.get("pnl_usd", 0) > 0]
                    money_losses = [t for t in st if t.get("pnl_usd", 0) <= 0]
                    mgp = sum(t["pnl_usd"] for t in money_wins)
                    mgl = -sum(t["pnl_usd"] for t in money_losses)
                    open_bars = set()
                    for t in st:
                        open_bars.update(range(t["entry_bar"], t["exit_bar"]))
                    exit_sig = {t["exit_bar"] - 1 for t in st
                                if t["exit_reason"] == "HMA_DOWN"}
                    holds = open_bars - exit_sig
                    src_pairs = {(t["entry_bar"], t["exit_bar"]) for t in st}
                    got_pairs = {(t["entry_bar"], t["exit_bar"])
                                 for t in p_book["trades"]}
                    holds_src = (sum(t["exit_bar"] - t["entry_bar"] for t in st)
                                 / len(st))
                    holds_got = (sum(t["exit_bar"] - t["entry_bar"]
                                     for t in p_book["trades"]) / len(p_book["trades"])
                                 if p_book["trades"] else 0.0)
                    metrics.update({
                        "claim_full_bars": len(kj),
                        "claim_full_money_pf": (mgp / mgl) if mgl > 0 else None,
                        "parity_source_trades": len(st),
                        "parity_source_exit_trades": len(exit_sig),
                        "parity_source_stop_trades": sum(
                            1 for t in st if t["exit_reason"] == "STOP"),
                        "parity_source_hold_bars": len(holds),
                        "parity_declared_trades": len(p_book["trades"]),
                        "parity_shared_entry_exit_pairs": len(src_pairs & got_pairs),
                        "parity_avg_hold_source_bars": holds_src,
                        "parity_avg_hold_declared_bars": holds_got,
                    })
            except (OSError, json.JSONDecodeError):
                pass

    prov = {
        "adapter": "hmatrend",
        "engine_version": ENGINE_VERSION,
        "source": "code/hma_trend_sources/ (external hermes session outputs)",
        "declared_spec": True,
        "parity_tool": "code/_hma_trend_parity.py",
    }

    tables = [
        {"kind": "thirds",
         **{f"t{i+1}_n": t3["n"] for i, t3 in enumerate(extra["thirds"])},
         **{f"t{i+1}_pnl": round(t3["pnl"], 2) for i, t3 in enumerate(extra["thirds"])},
         **{f"t{i+1}_pf": (round(t3["pf"], 4) if math.isfinite(t3["pf"]) else 9999.0)
            for i, t3 in enumerate(extra["thirds"])}},
        {"kind": "zero_cost_control", "return_pct": round(metrics["zero_cost_return_pct"], 4),
         "pf": (round(metrics["zero_cost_pf"], 4) if math.isfinite(metrics["zero_cost_pf"])
                else 9999.0), "cost_drag_pp": round(metrics["cost_drag_pp"], 4)},
        {"kind": "split", "split_date_utc": split_iso, "oos_n": metrics["oos_n_trades"],
         "oos_pf": (round(metrics["oos_profit_factor"], 4)
                    if math.isfinite(metrics["oos_profit_factor"]) else 9999.0),
         "oos_return_pct": round(metrics["oos_return_pct"], 4)},
    ]
    return metrics, prov, tables


def run(paths, params):
    return dispatch(paths, params)
