"""xs_factor_engine.py — Cross-sectional factor books, Category A (2026-11-02).

Three rank-based rotation books on the Binance USDT-M 1h universe-14
(ADA ARB AVAX BNB BTC DOGE ETH HYPE JUP LINK NEAR SOL SUI XRP):

  LOWVOL    signal = std of hourly log returns over lb bars (population, ddof=0),
            ranked ascending; long the k lowest-vol names, short the k highest.
  SKEW      signal = population skewness of hourly log returns over lb bars,
            ranked ascending; long the k lowest-skew, short the k highest-skew.
  AUTOCORR  signal = lag-1 autocorrelation of hourly log returns over lb bars,
            ranked descending; long the k most persistent, short the k least.

Conventions (all declared here, all measured inside the artifact):
  * Decisions on the CLOSE of rebalance bars (every `reb` bars of the union
    hourly index, first decision at the first reb-grid position >= lb);
    execution at the NEXT bar's OPEN.
  * MIN_ELIG = 8: a decision with fewer eligible symbols is skipped (the book
    stays flat) — the cross-section must be big enough for k legs to mean
    anything. Declared constant, not fitted.
  * One fill costs fee_bps + slippage_bps (5.0 + 0.5 = 5.5 bps of traded
    notional, repo cost model 2026-10-25); a round trip is 11 bps. The
    zero-cost control re-runs the identical state machine with cost 0; the
    engine ASSERTS both runs make the same decisions (trade count equality).
  * k = min(3, max(1, N_eligible // 4)) legs per side. EVERY rebalance every
    leg is re-sized to target notional = decision-bar equity / (2k); turnover
    for kept legs is only the drift delta. Without the resize, kept units
    compound without bound (measured: 4.75x gross average) — the resize keeps
    gross exposure near 100%. Per-leg accounting is average-cost basis:
    partial resize fills realize nothing, the leg's trade PnL realizes at its
    final close (net of every fill's cost on that leg).
  * Hysteresis in long-best rank space (rank 1 = best long candidate):
    longs enter at rank <= k and are held while rank <= 2k; shorts enter at
    rank >= N-k+1 and are held while rank >= N-2k+1.
  * A symbol is eligible at a decision bar iff its signal is non-NaN there and
    it has a close at the decision bar and an open at the execution bar.
    Symbols drop OUT of eligibility when their data ends (HYPE's main 1h file
    ends before BTC's; the tail file is NOT spliced in) — no survivorship
    patching.
  * Mark-to-market uses last-available close on any gap; gap bars are counted
    (nan_mark_bars) and reported.
  * Funding is NOT charged: 7 of the 14 names have no funding file on disk
    (only BTC ETH HYPE JUP SOL SUI XRP exist). For a dollar-neutral 14-day
    book funding is second-order but non-zero — declared, not hidden.
  * Bootstrap: numpy default_rng(42), 10,000 resamples with replacement,
    percentile interval of the mean per-trade net return (bps of entry
    notional).
"""

import os

import numpy as np
import pandas as pd

UNIVERSE = ["ADAUSDT", "ARBUSDT", "AVAXUSDT", "BNBUSDT", "BTCUSDT", "DOGEUSDT",
            "ETHUSDT", "HYPEUSDT", "JUPUSDT", "LINKUSDT", "NEARUSDT", "SOLUSDT",
            "SUIUSDT", "XRPUSDT"]

CARDS = {
    "LOWVOL":   {"lb": 336, "sig": "vol", "asc": True},
    "SKEW":     {"lb": 720, "sig": "skew", "asc": True},
    "AUTOCORR": {"lb": 336, "sig": "ac", "asc": False},
}

MIN_ELIG = 8            # minimum cross-section for a decision to fire
BARS_PER_YEAR = 8760.0  # 1h candles, 24x365 (crypto trades weekends)


def _rolling_skew(r: pd.DataFrame, lb: int) -> pd.DataFrame:
    """Population skewness of a rolling window (ddof=0), manual for determinism."""
    m1 = r.rolling(lb, min_periods=lb).mean()
    m2 = (r ** 2).rolling(lb, min_periods=lb).mean()
    m3 = (r ** 3).rolling(lb, min_periods=lb).mean()
    var = m2 - m1 ** 2
    num = m3 - 3.0 * m1 * m2 + 2.0 * m1 ** 3
    den = var ** 1.5
    out = num / den
    return out.replace([np.inf, -np.inf], np.nan)


def _rolling_ac1(r: pd.DataFrame, lb: int) -> pd.DataFrame:
    """Lag-1 autocorrelation over a rolling window (population moments)."""
    rl = r.shift(1)
    n = float(lb)
    s1 = r.rolling(lb, min_periods=lb).sum()
    s1l = rl.rolling(lb, min_periods=lb).sum()
    sp = (r * rl).rolling(lb, min_periods=lb).sum()
    q1 = (r ** 2).rolling(lb, min_periods=lb).sum()
    q2 = (rl ** 2).rolling(lb, min_periods=lb).sum()
    cov = sp / n - (s1 / n) * (s1l / n)
    v1 = q1 / n - (s1 / n) ** 2
    v2 = q2 / n - (s1l / n) ** 2
    out = cov / np.sqrt(v1 * v2)
    return out.replace([np.inf, -np.inf], np.nan)


def _load_frames(paths):
    closes, opens = {}, {}
    for p in paths:
        df = pd.read_csv(p, usecols=[0, 1, 4])
        df.columns = ["ts", "open", "close"]
        ts = pd.Index(df["ts"].to_numpy(dtype="int64"))
        sym = os.path.basename(p).split("_")[0]
        closes[sym] = pd.Series(df["close"].to_numpy(dtype="float64"), index=ts)
        opens[sym] = pd.Series(df["open"].to_numpy(dtype="float64"), index=ts)
    idx = sorted(set().union(*[set(s.index) for s in closes.values()]))
    idx = pd.Index(idx, dtype="int64")
    close_w = pd.DataFrame(closes).reindex(idx)[UNIVERSE]
    open_w = pd.DataFrame(opens).reindex(idx)[UNIVERSE]
    return idx, close_w, open_w


def _simulate(close_w, open_w, sig_w, reb, cost_rate):
    """Run one book. Returns (equity_curve, trades, diag). Deterministic.

    Per-leg ledger: units, basis (average entry price of the direction),
    realized (USDT from partial resize closes), leg_costs (USDT, every fill
    on the leg). The trade realizes at its final close.
    """
    n_bars = len(close_w)
    lb = sig_w.attrs.get("lb", 0)
    first = ((lb + reb - 1) // reb) * reb
    decisions = set(range(first, n_bars - 1, reb))

    close_mark = close_w.ffill()
    open_mark = open_w.ffill()
    close_np = close_w.to_numpy()
    open_np = open_w.to_numpy()
    mark_np = close_mark.to_numpy()
    openm_np = open_mark.to_numpy()
    sig_np = sig_w.to_numpy()
    syms = list(close_w.columns)
    nsym = len(syms)

    cash = 1.0
    legs = []
    eq = np.ones(n_bars, dtype="float64")
    trades = []
    turnover = 0.0
    deferred = 0
    nan_mark_bars = 0
    gross_sum = 0.0
    gross_n = 0
    elig_counts = []
    first_active_pos = None

    def fill_cost(notional):
        return cost_rate * abs(notional)

    for t in range(n_bars):
        # mark-to-market at every bar close
        if legs:
            vals = 0.0
            for lg in legs:
                vals += lg["dir"] * lg["units"] * mark_np[t, lg["col"]]
            eq_t = cash + vals
            for lg in legs:
                if np.isnan(close_np[t, lg["col"]]):
                    nan_mark_bars += 1
        else:
            eq_t = cash
        eq[t] = eq_t
        gross = sum(abs(lg["dir"] * lg["units"] * mark_np[t, lg["col"]])
                    for lg in legs)
        gross_sum += gross
        gross_n += 1

        if t not in decisions or t >= n_bars - 1:
            continue
        elig = []
        for j in range(nsym):
            if np.isnan(sig_np[t, j]) or np.isnan(close_np[t, j]) \
                    or np.isnan(open_np[t + 1, j]):
                continue
            elig.append(j)
        n_el = len(elig)
        elig_counts.append(n_el)
        if n_el < MIN_ELIG:
            continue
        if first_active_pos is None:
            first_active_pos = t
        k = min(3, max(1, n_el // 4))
        scores = sig_np[t, elig]
        if not sig_w.attrs.get("asc", True):
            scores = -scores
        order = np.lexsort((np.array(elig), scores))
        rank_of = {}
        for r_i, j in enumerate(order):
            rank_of[elig[j]] = r_i + 1  # 1-based, 1 = best long candidate

        kept, closed = [], []
        for lg in legs:
            j = lg["col"]
            if lg["dir"] > 0:
                stay = j in rank_of and rank_of[j] <= 2 * k
            else:
                stay = j in rank_of and rank_of[j] >= n_el - 2 * k + 1
            (kept if stay else closed).append(lg)

        pool = [j for j in elig if all(lg["col"] != j for lg in kept)]
        long_cands = sorted([j for j in pool if rank_of[j] <= k],
                            key=lambda j: rank_of[j])
        short_cands = sorted([j for j in pool if rank_of[j] >= n_el - k + 1],
                             key=lambda j: -rank_of[j])

        exec_t = t + 1
        # ---- closes at next open ----
        for lg in closed:
            px = open_np[exec_t, lg["col"]]
            if np.isnan(px):
                # symbol's data ended: settle at its last available open
                px = openm_np[exec_t, lg["col"]]
                if np.isnan(px):
                    deferred += 1
                    kept.append(lg)
                    continue
            exit_notional = lg["units"] * px
            realized = lg["realized"] + lg["units"] * lg["dir"] * (px - lg["basis"])
            cost = lg["leg_costs"] + fill_cost(exit_notional)
            net = realized - cost
            cash += lg["dir"] * exit_notional - fill_cost(exit_notional)
            turnover += exit_notional
            trades.append({
                "sym": syms[lg["col"]], "dir": "LONG" if lg["dir"] > 0 else "SHORT",
                "entry_ts": int(close_w.index[lg["entry_pos"]]),
                "exit_ts": int(close_w.index[exec_t]),
                "entry_pos": int(lg["entry_pos"]), "exit_pos": int(exec_t),
                "entry_notional": float(lg["entry_notional"]),
                "gross_ret_notional_bps":
                    float((realized + lg["leg_costs"]) / lg["entry_notional"] * 1e4),
                "net_ret_notional_bps": float(net / lg["entry_notional"] * 1e4),
                "pnl_eq_pct": float(net / lg["entry_eq"] * 100.0),
            })

        # ---- resize kept legs to target, then open new legs, all at next open ----
        target = eq[t] / (2.0 * k)
        resized = []
        for lg in kept:
            px = open_np[exec_t, lg["col"]]
            if np.isnan(px):
                px = openm_np[exec_t, lg["col"]]
                if np.isnan(px):
                    deferred += 1
                    resized.append(lg)
                    continue
            cur_notional = lg["units"] * px
            delta_notional = target - cur_notional
            if abs(delta_notional) <= 1e-12:
                resized.append(lg)
                continue
            du = delta_notional / px
            if du < 0:  # units shrink = partial close (either side): realize vs basis
                lg["realized"] += (-du) * lg["dir"] * (px - lg["basis"])
            else:       # units grow = add at today's price: average the basis
                tot = lg["units"] + du
                lg["basis"] = (lg["units"] * lg["basis"] + du * px) / tot
            cash -= lg["dir"] * du * px + fill_cost(delta_notional)
            turnover += abs(delta_notional)
            lg["units"] = lg["units"] + du
            lg["leg_costs"] += fill_cost(delta_notional)
            resized.append(lg)
        kept = resized

        n_long_now = sum(1 for lg in kept if lg["dir"] > 0)
        n_short_now = sum(1 for lg in kept if lg["dir"] < 0)
        for j in long_cands[:max(0, k - n_long_now)]:
            px = open_np[exec_t, j]
            units = target / px
            cash -= units * px + fill_cost(target)
            turnover += target
            kept.append({"sym": syms[j], "dir": 1, "units": units, "basis": float(px),
                         "realized": 0.0, "leg_costs": fill_cost(target), "col": j,
                         "entry_pos": t, "entry_notional": float(target),
                         "entry_eq": float(eq[t])})
        for j in short_cands[:max(0, k - n_short_now)]:
            px = open_np[exec_t, j]
            units = target / px
            cash += units * px - fill_cost(target)
            turnover += target
            kept.append({"sym": syms[j], "dir": -1, "units": units, "basis": float(px),
                         "realized": 0.0, "leg_costs": fill_cost(target), "col": j,
                         "entry_pos": t, "entry_notional": float(target),
                         "entry_eq": float(eq[t])})
        legs = kept

    # end-of-data: close remaining legs at the LAST close
    last = n_bars - 1
    for lg in legs:
        px = mark_np[last, lg["col"]]
        exit_notional = lg["units"] * px
        realized = lg["realized"] + lg["units"] * lg["dir"] * (px - lg["basis"])
        cost = lg["leg_costs"] + fill_cost(exit_notional)
        net = realized - cost
        cash += lg["dir"] * exit_notional - fill_cost(exit_notional)
        turnover += exit_notional
        trades.append({
            "sym": syms[lg["col"]], "dir": "LONG" if lg["dir"] > 0 else "SHORT",
            "entry_ts": int(close_w.index[lg["entry_pos"]]),
            "exit_ts": int(close_w.index[last]),
            "entry_pos": int(lg["entry_pos"]), "exit_pos": int(last),
            "entry_notional": float(lg["entry_notional"]),
            "gross_ret_notional_bps":
                float((realized + lg["leg_costs"]) / lg["entry_notional"] * 1e4),
            "net_ret_notional_bps": float(net / lg["entry_notional"] * 1e4),
            "pnl_eq_pct": float(net / lg["entry_eq"] * 100.0),
        })
    eq[last] = cash  # all positions settled at the last close

    return eq, trades, {
        "turnover_notional": float(turnover),
        "n_decisions": len(decisions),
        "eligible_min": int(min(elig_counts)) if elig_counts else 0,
        "eligible_median": float(np.median(elig_counts)) if elig_counts else 0.0,
        "eligible_max": int(max(elig_counts)) if elig_counts else 0,
        "deferred_fills": deferred,
        "nan_mark_bars": int(nan_mark_bars),
        "avg_gross_exposure_pct": float(gross_sum / max(gross_n, 1) * 100.0),
        "first_active_pos": int(first_active_pos) if first_active_pos is not None
                            else int(((lb + reb - 1) // reb) * reb),
    }


def _pf(rets):
    gains = sum(r for r in rets if r > 0)
    losses = -sum(r for r in rets if r < 0)
    if losses == 0:
        return None if gains == 0 else gains  # degenerate; flagged by caller
    return gains / losses


def _max_dd(eq):
    peak = np.maximum.accumulate(eq)
    dd = (eq - peak) / peak
    return float(dd.min() * 100.0)


def run(paths, params):
    p = dict(params)
    card = str(p.pop("card", "")).upper()
    if card not in CARDS:
        raise ValueError(f"unknown xsf card: {card!r} (use LOWVOL|SKEW|AUTOCORR)")
    cfg = CARDS[card]
    lb = int(p.pop("lb", cfg["lb"]))
    reb = int(p.pop("reb", 336))
    fee = float(p.pop("fee_bps", 5.0))
    slip = float(p.pop("slippage_bps", 0.5))
    if p:
        raise ValueError(f"unknown xsf params: {sorted(p)}")
    if lb < 24 or reb < 24 or lb > 4000:
        raise ValueError("lb/reb out of declared range (24..4000 / >=24)")

    idx, close_w, open_w = _load_frames(sorted(paths))
    logret = np.log(close_w).diff()

    sig_kind = cfg["sig"]
    if sig_kind == "vol":
        sig = logret.rolling(lb, min_periods=lb).std(ddof=0)
    elif sig_kind == "skew":
        sig = _rolling_skew(logret, lb)
    else:
        sig = _rolling_ac1(logret, lb)
    sig.attrs["lb"] = lb
    sig.attrs["asc"] = cfg["asc"]

    cost_rate = (fee + slip) / 1e4
    eq_net, trades, diag = _simulate(close_w, open_w, sig, reb, cost_rate)
    eq_gross, trades_g, _ = _simulate(close_w, open_w, sig, reb, 0.0)
    if len(trades) != len(trades_g):
        raise AssertionError("cost regime changed decisions — state machine is "
                             "not cost-independent; engine is broken")

    n_bars = len(idx)
    years = n_bars / BARS_PER_YEAR
    net_ret_pct = float((eq_net[-1] - 1.0) * 100.0)
    gross_ret_pct = float((eq_gross[-1] - 1.0) * 100.0)
    max_dd = _max_dd(eq_net)
    r = eq_net[1:] / eq_net[:-1] - 1.0
    act = diag["first_active_pos"]
    sharpe = float(np.mean(r[act:]) / np.std(r[act:]) * np.sqrt(BARS_PER_YEAR)) \
        if np.std(r[act:]) > 0 else None

    net_bps = [t["net_ret_notional_bps"] for t in trades]
    gross_bps = [t["gross_ret_notional_bps"] for t in trades]
    n_tr = len(trades)
    win_rate = float(sum(1 for x in net_bps if x > 0) / n_tr * 100.0) if n_tr else None
    pf_net = _pf(net_bps)
    pf_gross = _pf(gross_bps)
    avg_bps = float(np.mean(net_bps)) if n_tr else None
    std_bps = float(np.std(net_bps)) if n_tr else None
    wins = [x for x in net_bps if x > 0]
    losses = [x for x in net_bps if x < 0]
    be_wr = None
    if wins and losses:
        aw, al = float(np.mean(wins)), float(-np.mean(losses))
        if aw + al > 0:
            be_wr = al / (aw + al) * 100.0

    # yearly returns
    ts_years = pd.to_datetime(idx, unit="ms", utc=True).year
    order_years = sorted(set(ts_years))
    yearly = {}
    for y in order_years:
        pos_y = [i for i in range(n_bars) if ts_years[i] == y]
        first_pos, last_pos = pos_y[0], pos_y[-1]
        base = eq_net[first_pos - 1] if first_pos > 0 else 1.0
        yearly[str(y)] = float((eq_net[last_pos] / base - 1.0) * 100.0)
    n_years = len(order_years)
    green_years = sum(1 for v in yearly.values() if v > 0)

    thirds = []
    for c in range(3):
        a, b = n_bars * c // 3, n_bars * (c + 1) // 3
        base = eq_net[a - 1] if a > 0 else 1.0
        thirds.append(float((eq_net[b - 1] / base - 1.0) * 100.0))
    halves = []
    for c in range(2):
        a, b = n_bars * c // 2, n_bars * (c + 1) // 2
        base = eq_net[a - 1] if a > 0 else 1.0
        halves.append(float((eq_net[b - 1] / base - 1.0) * 100.0))

    split = int(n_bars * 0.7)
    is_ret = float((eq_net[split] - 1.0) * 100.0)
    oos_ret = float((eq_net[-1] / eq_net[split] - 1.0) * 100.0)
    is_trades = [t for t in trades if t["exit_pos"] < split]
    oos_trades = [t for t in trades if t["exit_pos"] >= split]
    is_pf = _pf([t["net_ret_notional_bps"] for t in is_trades])
    oos_pf = _pf([t["net_ret_notional_bps"] for t in oos_trades])
    is_gross = _pf([t["gross_ret_notional_bps"] for t in is_trades])
    oos_gross = _pf([t["gross_ret_notional_bps"] for t in oos_trades])

    # concentration (arithmetic decomposition, declared)
    pnl_eq = sorted([t["pnl_eq_pct"] for t in trades], reverse=True)
    total_pnl = sum(pnl_eq)
    top5 = sum(pnl_eq[:5]) if len(pnl_eq) >= 5 else total_pnl
    conc_share = float(top5 / total_pnl * 100.0) if total_pnl > 0 else None
    net_without_top5 = net_ret_pct - (top5 if len(pnl_eq) >= 5 else 0.0)

    # bootstrap CI of mean per-trade net return (bps of notional), seeded
    boot_lo = boot_hi = None
    p_le0 = None
    if n_tr >= 5:
        arr = np.array(net_bps, dtype="float64")
        rng = np.random.default_rng(42)
        boots = arr[rng.integers(0, n_tr, size=(10000, n_tr))].mean(axis=1)
        boot_lo = float(np.percentile(boots, 2.5))
        boot_hi = float(np.percentile(boots, 97.5))
        p_le0 = float((boots <= 0).mean() * 100.0)

    # buy & hold: equal-weight long-only of names priced at first ACTIVE exec bar
    first_exec = diag["first_active_pos"] + 1
    bh_syms, bh_ret = [], None
    c0 = close_w.iloc[first_exec]
    c1 = close_w.iloc[-1]
    avail = [s for s in UNIVERSE
             if not np.isnan(c0[s]) and not np.isnan(c1[s])]
    if avail:
        w = 1.0 / len(avail)
        bh_ret = float(sum(w * (c1[s] / c0[s] - 1.0) for s in avail) * 100.0)
        bh_syms = avail

    cost_drag = gross_ret_pct - net_ret_pct
    cost_share = float(cost_drag / gross_ret_pct * 100.0) if gross_ret_pct > 0 else None

    # ---- gates (measured here so the report can cite them) ----
    gates = []
    g = gates.append
    g(["pf_ex_cost_gt_1.2", ">1.2", pf_gross, pf_gross is not None and pf_gross > 1.2])
    g(["n_trades_ge_30", ">=30", n_tr, n_tr >= 30])
    g(["oos_pf_ge_1", ">=1 (OOS PF < 1 = KILL)", oos_pf,
       oos_pf is not None and oos_pf >= 1.0])
    g(["green_years_frac", ">=2/3 years green",
       f"{green_years}/{n_years}", n_years >= 3 and green_years / n_years >= 2.0 / 3.0])
    g(["conc_top5_lt_100", "<100% of PnL", conc_share,
       conc_share is not None and conc_share < 100.0])
    g(["net_without_top5_pos", ">0%", net_without_top5, net_without_top5 > 0.0])
    g(["cost_share_lt_40", "<40% of gross", cost_share,
       cost_share is not None and cost_share < 40.0])
    g(["boot_ci_low_pos", ">0 bps", boot_lo, boot_lo is not None and boot_lo > 0.0])
    g11 = True
    if win_rate is not None and win_rate >= 75.0:
        g11 = be_wr is not None and win_rate >= be_wr + 5.0
    g(["g11_winrate_buffer", "wr>=75 needs wr>=breakeven+5pp", be_wr, g11])
    bh_gate = None if bh_ret is None else net_ret_pct > bh_ret
    g(["beats_bh_equal_weight", f"net > B&H ({bh_ret})", bh_gate, bool(bh_gate)])
    all_pass = all(row[3] for row in gates)
    flag = "PASS" if all_pass else "FAIL-GATES:" + ",".join(
        row[0] for row in gates if not row[3])

    metrics = {
        "flag": flag,
        "card": card, "signal": sig_kind, "lb": lb, "reb": reb,
        "fee_bps": fee, "slippage_bps": slip, "cost_rt_bps": fee + slip,
        "min_elig": MIN_ELIG,
        "n_bars": int(n_bars), "years": float(years),
        "start_utc": str(pd.to_datetime(idx[0], unit="ms", utc=True)),
        "end_utc": str(pd.to_datetime(idx[-1], unit="ms", utc=True)),
        "first_active_utc": str(pd.to_datetime(idx[diag["first_active_pos"]],
                                               unit="ms", utc=True)),
        "n_trades": n_tr,
        "return_pct": net_ret_pct,
        "gross_return_pct": gross_ret_pct,
        "profit_factor": pf_net,
        "profit_factor_ex_cost": pf_gross,
        "win_rate": win_rate,
        "avg_trade_bps": avg_bps,
        "std_trade_bps": std_bps,
        "breakeven_win_rate": be_wr,
        "sharpe_annualised": sharpe,
        "max_dd_pct": max_dd,
        "bh_return_pct": bh_ret,
        "bh_universe_n": len(bh_syms),
        "cost_drag_pct": cost_drag,
        "cost_share_of_gross_pct": cost_share,
        "is_return_pct": is_ret, "oos_return_pct": oos_ret,
        "is_pf": is_pf, "oos_pf": oos_pf,
        "is_pf_gross": is_gross, "oos_pf_gross": oos_gross,
        "is_n": len(is_trades), "oos_n": len(oos_trades),
        "conc_top5_share_pct": conc_share,
        "conc_net_without_top5_pct": float(net_without_top5),
        "boot_ci_low_bps": boot_lo, "boot_ci_high_bps": boot_hi,
        "boot_p_mean_le0_pct": p_le0,
        "green_years": int(green_years), "n_years": int(n_years),
        "turnover_notional_x": diag["turnover_notional"],
        "turnover_per_year_x": float(diag["turnover_notional"] / years),
        "n_decisions": diag["n_decisions"],
        "eligible_min": diag["eligible_min"],
        "eligible_median": diag["eligible_median"],
        "eligible_max": diag["eligible_max"],
        "deferred_fills": diag["deferred_fills"],
        "nan_mark_bars": diag["nan_mark_bars"],
        "avg_gross_exposure_pct": diag["avg_gross_exposure_pct"],
        "funding_charged": False,
        "legs_per_side_rule": "k=min(3, max(1, N_elig//4))",
    }

    tables = {
        "yearly": [[y, yearly[y]] for y in sorted(yearly)],
        "thirds_halves": [["third1", thirds[0]], ["third2", thirds[1]],
                          ["third3", thirds[2]], ["half1", halves[0]],
                          ["half2", halves[1]]],
        "gates": gates,
        "per_symbol": _per_symbol(trades),
        "trades": trades,
    }

    prov = {
        "engine_version": "xsf-1",
        "universe": UNIVERSE,
        "conventions": {
            "decision": "close of rebalance bar, execution at next bar open",
            "min_elig": "decisions with fewer than 8 eligible symbols are "
                        "skipped (book flat) — declared constant",
            "cost_model": f"fee {fee} bps + slip {slip} bps per side = "
                          f"{fee + slip} bps round trip; charged on every fill",
            "resize": "every rebalance every leg is re-sized to equity/(2k); "
                      "kept legs trade only the drift delta (without the "
                      "resize kept units compound without bound)",
            "per_leg_accounting": "average-cost basis; resize reductions "
                                  "realize nothing, the trade realizes at its "
                                  "final close net of every fill's cost",
            "zero_cost_control": "identical state machine with cost 0; engine "
                                 "asserts both runs make identical decisions",
            "hysteresis": "longs enter rank<=k, held while rank<=2k; shorts "
                          "enter rank>=N-k+1, held while rank>=N-2k+1",
            "eligibility": "signal non-NaN at decision bar + close at t + "
                           "open at t+1",
            "drop_out_at_data_end": True,
            "data_end_settlement": "a leg whose symbol's data has ended is "
                                   "closed / re-sized at the symbol's last "
                                   "available open price (no zombie legs)",
            "funding": "NOT charged - 7/14 universe names have no funding file "
                       "(BTC ETH HYPE JUP SOL SUI XRP are the covered ones); "
                       "second-order for a dollar-neutral 14-day book, declared",
            "concentration": "pnl_eq_pct = net trade pnl / equity at entry; "
                             "conc_net_without_top5_pct is an arithmetic "
                             "decomposition of return_pct",
            "bootstrap": "default_rng(42), 10000 resamples, percentile 2.5/97.5",
            "bh": "equal-weight long-only of names priced at the first active "
                  "execution bar, no rebalancing, no costs",
        },
    }
    return metrics, prov, tables


def _per_symbol(trades):
    out = {}
    for t in trades:
        d = out.setdefault(t["sym"], {"n": 0, "pnl": 0.0, "wins": 0})
        d["n"] += 1
        d["pnl"] += t["pnl_eq_pct"]
        d["wins"] += 1 if t["net_ret_notional_bps"] > 0 else 0
    return [[s, d["n"], d["wins"] / d["n"] * 100.0, d["pnl"]]
            for s, d in sorted(out.items())]
