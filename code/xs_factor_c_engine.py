"""xs_factor_c_engine.py — Category C funding-filtered books (2026-11-02).

Reuses the machinery of xs_factor_engine.py (Category A) UNTOUCHED — its bytes
are pinned by the Category A artifacts — and adds two cards on the SEVEN
funding-covered names (BTC ETH HYPE JUP SOL SUI XRP). Unlike A and B, funding
here is BOTH the signal filter AND a charged cost: the repo lesson is that an
attached funding column is not a charged cost, so every sim bills funding at
the real settlement instants read from data/binance_funding/*.json.

  FUNDGATE  base book = ROC(336h) ranked descending, k=2 per side (card
            spec). Funding-sign gate on entries: a long candidate is kept
            only if the latest funding rate (normalized per 8h) is <= 0 (it
            receives or is neutral); a short candidate only if > 0 (it
            receives). Failing candidates leave their slot in cash (the book
            is not always fully dollar-neutral — declared). Held legs are
            NOT re-gated.
  FUNDTAIL  base book = realized vol (lb bars, population) ranked ascending
            (the Category-A low-vol book restricted to the 7-name universe),
            k=2 per side. Extreme-funding exclusion (card spec, one
            threshold `cap` per 8h, default 0.0005): a long candidate is
            excluded if rate > cap (it would pay), a short candidate if
            rate < -cap. Held legs are NOT re-gated.

Funding mechanics (declared, all measured in the artifact):
  * Billing: at every settlement event of a held leg's symbol inside the bar
    window (prev bar open, this bar open], cash changes by
    -dir * units * open_price * raw_rate. Longs pay positive rates, shorts
    receive them. The raw file rate is billed (JUP and HYPE settle every 4h:
    two real settlements, not one doubled one). A leg is billed for
    settlements at or after its entry instant.
  * Gate normalization: the gate compares rates per 8h — raw rate *
    (8h / modal spacing of that symbol), spacing inferred from the
    settlement timestamps.
  * Eligibility additionally requires a funding observation (the gate matrix
    is NaN before a symbol's first settlement), so the book starts when the
    six non-HYPE names have funding (JUP's first settlement is 2024-10-01 —
    its 1h klines start 243 days earlier, the FUNDING_MANIFEST head_gap) and
    HYPE joins at its own first bar (2025-05-30). Minimum cross-section 6 of
    7 (declared; the C universe is 7 names by design).
  * JUP's funding file ends 2.46 days before its 1h klines do (manifest
    tail_gap): the gate carries the last rate forward there and those bars
    bill nothing — declared.
  * Three sims per run, identical decisions (asserted): net (trading costs +
    funding), gross_tc (no trading costs, funding charged — the ex-cost
    control), gross_nf (no trading costs, NO funding — isolates the funding
    contribution: funding_pnl_pct = gross_tc - gross_nf).

Shared conventions with A/B: decision on the rebalance bar's close,
execution next open, fee+slip per side on every fill, resize-to-target
every rebalance with average-cost basis, hysteresis (enter rank<=k, hold
while rank<=2k), mark-to-market on last available close, data-end
settlement at last valid open, zero-cost control asserted
decision-identical, bootstrap seeded 42.
"""

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xs_factor_engine as xse  # noqa: E402  (pinned by the Category A artifacts)

UNIVERSE = ["BTCUSDT", "ETHUSDT", "HYPEUSDT", "JUPUSDT", "SOLUSDT",
            "SUIUSDT", "XRPUSDT"]
MIN_ELIG = 6  # the C universe is 7 names by design; 6 of 7 to fire

CARDS = {
    "FUNDGATE": {"lb": 336, "sig": "roc", "asc": False, "reb": 336, "k_fixed": 2},
    "FUNDTAIL": {"lb": 336, "sig": "vol", "asc": True, "reb": 336, "k_fixed": 2},
}

CAP_DEFAULT = 0.0005  # FUNDTAIL extreme-funding threshold, per 8h (declared)
BARS_PER_YEAR = xse.BARS_PER_YEAR


def _load_funding(paths, idx):
    """paths = the 7 funding JSONs. Returns {sym: (ts int64 array, rate
    float64 array, spacing_h float)} plus per-8h gate DataFrame on idx."""
    bysym = {}
    for p in paths:
        sym = os.path.basename(p).split("_")[0]
        recs = json.load(open(p, encoding="utf-8"))
        ts = np.array([int(r["t"]) for r in recs], dtype="int64")
        rate = np.array([float(r["r"]) for r in recs], dtype="float64")
        order = np.argsort(ts, kind="stable")
        ts, rate = ts[order], rate[order]
        # modal spacing in hours from the settlement timestamps
        if len(ts) > 2:
            diffs = np.diff(ts)
            modal = np.bincount(diffs).argmax()
        else:
            modal = 28800000
        spacing_h = float(modal) / 3600000.0
        bysym[sym] = (ts, rate, spacing_h)
    # per-8h normalized last-rate matrix (ffill), NaN before first settlement
    gate = pd.DataFrame(index=idx, columns=UNIVERSE, dtype="float64")
    for sym, (ts, rate, spacing_h) in bysym.items():
        s = pd.Series(rate * (8.0 / spacing_h), index=pd.Index(ts, dtype="int64"))
        gate[sym] = s.reindex(idx).ffill()
    return bysym, gate[UNIVERSE]


def _load_frames_7(paths):
    """Wide open/close frames for the 7-name C universe. Local copy —
    xse._load_frames is hard-pinned to the 14-name A universe."""
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


def _simulate(close_w, open_w, sig_w, reb, cost_rate,
              long_ok=None, short_ok=None, funded=None, funding=None,
              charge_funding=True):
    """Category C state machine: Category A's machine plus (a) per-side
    boolean entry gates and (b) funding billed at real settlement instants.
    Deterministic; the three cost regimes make identical decisions."""
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
    lok_np = long_ok.to_numpy() if long_ok is not None else None
    shok_np = short_ok.to_numpy() if short_ok is not None else None
    fund_np = funded.to_numpy() if hasattr(funded, "to_numpy") else funded
    open_ts = close_w.index.to_numpy()
    syms = list(close_w.columns)
    nsym = len(syms)
    col_of = {s: j for j, s in enumerate(syms)}

    cash = 1.0
    legs = []
    eq = np.ones(n_bars, dtype="float64")
    trades = []
    turnover = 0.0
    funding_paid = 0.0  # >0 = net paid by the book
    deferred = 0
    nan_mark_bars = 0
    gross_sum = 0.0
    gross_n = 0
    elig_counts = []
    first_active_pos = None
    fund_events_billed = 0

    def fill_cost(notional):
        return cost_rate * abs(notional)

    for t in range(n_bars):
        # ---- funding settlements in (open_ts[t-1], open_ts[t]] ----
        if funding is not None and charge_funding and t > 0:
            lo = open_ts[t - 1]
            hi = open_ts[t]
            for lg in legs:
                ts_arr, rate_arr, _ = funding[syms[lg["col"]]]
                a = np.searchsorted(ts_arr, lo, side="right")
                b = np.searchsorted(ts_arr, hi, side="right")
                if b > a:
                    px = open_np[t, lg["col"]]
                    if np.isnan(px):
                        px = openm_np[t, lg["col"]]
                    pay = float(np.sum(rate_arr[a:b])) * lg["units"] * px
                    cash -= lg["dir"] * pay
                    funding_paid += lg["dir"] * pay
                    fund_events_billed += int(b - a)

        # ---- mark-to-market ----
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
            if funded is not None and not funded[t, j]:
                continue  # no funding observation yet: not eligible
            elig.append(j)
        n_el = len(elig)
        elig_counts.append(n_el)
        if n_el < MIN_ELIG:
            continue
        if first_active_pos is None:
            first_active_pos = t
        k = 2  # both C cards run fixed k=2 on the 7-name universe
        scores = sig_np[t, elig]
        if not sig_w.attrs.get("asc", True):
            scores = -scores
        order = np.lexsort((np.array(elig), scores))
        rank_of = {}
        for r_i, j in enumerate(order):
            rank_of[elig[j]] = r_i + 1

        kept, closed = [], []
        for lg in legs:
            j = lg["col"]
            if lg["dir"] > 0:
                stay = j in rank_of and rank_of[j] <= 2 * k
            else:
                stay = j in rank_of and rank_of[j] >= n_el - 2 * k + 1
            (kept if stay else closed).append(lg)

        pool = [j for j in elig if all(lg["col"] != j for lg in kept)]
        long_cands = sorted([j for j in pool if rank_of[j] <= k
                             and (lok_np is None or lok_np[t, j])],
                            key=lambda j: rank_of[j])
        short_cands = sorted([j for j in pool if rank_of[j] >= n_el - k + 1
                              and (shok_np is None or shok_np[t, j])],
                             key=lambda j: -rank_of[j])

        exec_t = t + 1
        for lg in closed:
            px = open_np[exec_t, lg["col"]]
            if np.isnan(px):
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
            if du < 0:  # units shrink = partial close (either side)
                lg["realized"] += (-du) * lg["dir"] * (px - lg["basis"])
            else:       # units grow = add: average the basis
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
    eq[last] = cash

    return eq, trades, {
        "turnover_notional": float(turnover),
        "funding_paid_usd": float(funding_paid),
        "fund_events_billed": int(fund_events_billed),
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
    return xse._pf(rets)


def _max_dd(eq):
    return xse._max_dd(eq)


def run(paths, params):
    p = dict(params)
    card = str(p.pop("card", "")).upper()
    if card not in CARDS:
        raise ValueError(f"unknown xsc card: {card!r} (use FUNDGATE|FUNDTAIL)")
    cfg = CARDS[card]
    lb = int(p.pop("lb", cfg["lb"]))
    reb = int(p.pop("reb", cfg["reb"]))
    fee = float(p.pop("fee_bps", 5.0))
    slip = float(p.pop("slippage_bps", 0.5))
    cap = None
    if card == "FUNDTAIL":
        cap = float(p.pop("cap", CAP_DEFAULT))
        if not 0.00005 <= cap <= 0.005:
            raise ValueError("cap out of declared range (0.00005..0.005)")
    elif "cap" in p:
        raise ValueError("cap is a FUNDTAIL-only param")
    if p:
        raise ValueError(f"unknown xsc params: {sorted(p)}")
    if lb < 24 or reb < 24 or lb > 4000:
        raise ValueError("lb/reb out of declared range (24..4000 / >=24)")

    klines = sorted(x for x in paths if str(x).endswith("_1h.csv"))
    fund_files = sorted(x for x in paths if str(x).endswith("_funding.json"))
    if len(klines) != len(UNIVERSE) or len(fund_files) != len(UNIVERSE):
        raise ValueError(f"expected {len(UNIVERSE)} klines + {len(UNIVERSE)} "
                         f"funding files, got {len(klines)} + {len(fund_files)}")

    idx, close_w, open_w = _load_frames_7(klines)
    close_w = close_w[UNIVERSE]
    open_w = open_w[UNIVERSE]
    logret = np.log(close_w).diff()
    funding, rate8h = _load_funding(fund_files, idx)

    if cfg["sig"] == "roc":
        sig = close_w / close_w.shift(lb) - 1.0
    else:
        sig = logret.rolling(lb, min_periods=lb).std(ddof=0)

    if card == "FUNDGATE":
        long_ok = rate8h <= 0.0     # long only if it receives / is neutral
        short_ok = rate8h > 0.0     # short only if it receives
    else:
        long_ok = rate8h <= cap     # exclude longs that would pay > cap
        short_ok = rate8h >= -cap   # exclude shorts that would pay > cap
    sig.attrs["lb"] = lb
    sig.attrs["asc"] = cfg["asc"]

    funded = rate8h.notna().to_numpy()
    cost_rate = (fee + slip) / 1e4
    eq_net, trades, diag = _simulate(close_w, open_w, sig, reb, cost_rate,
                                     long_ok=long_ok, short_ok=short_ok,
                                     funded=funded, funding=funding,
                                     charge_funding=True)
    eq_gtc, trades_g, _ = _simulate(close_w, open_w, sig, reb, 0.0,
                                    long_ok=long_ok, short_ok=short_ok,
                                    funded=funded, funding=funding,
                                    charge_funding=True)
    eq_gnf, trades_n, _ = _simulate(close_w, open_w, sig, reb, 0.0,
                                    long_ok=long_ok, short_ok=short_ok,
                                    funded=funded, funding=funding,
                                    charge_funding=False)
    if len({len(trades), len(trades_g), len(trades_n)}) != 1:
        raise AssertionError("cost regime changed decisions — state machine is "
                             "not cost-independent; engine is broken")

    n_bars = len(idx)
    years = n_bars / BARS_PER_YEAR
    net_ret_pct = float((eq_net[-1] - 1.0) * 100.0)
    gross_ret_pct = float((eq_gtc[-1] - 1.0) * 100.0)
    gross_nf_pct = float((eq_gnf[-1] - 1.0) * 100.0)
    funding_pnl_pct = gross_ret_pct - gross_nf_pct
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

    # all window stats are measured on the ACTIVE window: the C books start
    # in late 2024 (JUP's first funding), so a union-index 70/30 split would
    # put every trade in the OOS half and five flat years into the yearly
    # gate. first_active_pos is the first decision the book actually took.
    act = diag["first_active_pos"]
    span = n_bars - act

    ts_years = pd.to_datetime(idx, unit="ms", utc=True).year
    yearly = {}
    for y in sorted(set(ts_years[act:])):
        pos_y = [i for i in range(act, n_bars) if ts_years[i] == y]
        first_pos, last_pos = pos_y[0], pos_y[-1]
        base = eq_net[first_pos - 1] if first_pos > 0 else 1.0
        yearly[str(y)] = float((eq_net[last_pos] / base - 1.0) * 100.0)
    n_years = len(yearly)
    green_years = sum(1 for v in yearly.values() if v > 0)

    thirds = []
    for c in range(3):
        a, b = act + span * c // 3, act + span * (c + 1) // 3
        base = eq_net[a - 1] if a > 0 else 1.0
        thirds.append(float((eq_net[b - 1] / base - 1.0) * 100.0))
    halves = []
    for c in range(2):
        a, b = act + span * c // 2, act + span * (c + 1) // 2
        base = eq_net[a - 1] if a > 0 else 1.0
        halves.append(float((eq_net[b - 1] / base - 1.0) * 100.0))

    split = act + int(span * 0.7)
    is_ret = float((eq_net[split] / eq_net[act] - 1.0) * 100.0)
    oos_ret = float((eq_net[-1] / eq_net[split] - 1.0) * 100.0)
    is_trades = [t for t in trades if t["exit_pos"] < split]
    oos_trades = [t for t in trades if t["exit_pos"] >= split]
    is_pf = _pf([t["net_ret_notional_bps"] for t in is_trades])
    oos_pf = _pf([t["net_ret_notional_bps"] for t in oos_trades])

    pnl_eq = sorted([t["pnl_eq_pct"] for t in trades], reverse=True)
    total_pnl = sum(pnl_eq)
    top5 = sum(pnl_eq[:5]) if len(pnl_eq) >= 5 else total_pnl
    conc_share = float(top5 / total_pnl * 100.0) if total_pnl > 0 else None
    net_without_top5 = net_ret_pct - (top5 if len(pnl_eq) >= 5 else 0.0)

    boot_lo = boot_hi = None
    p_le0 = None
    if n_tr >= 5:
        arr = np.array(net_bps, dtype="float64")
        rng = np.random.default_rng(42)
        boots = arr[rng.integers(0, n_tr, size=(10000, n_tr))].mean(axis=1)
        boot_lo = float(np.percentile(boots, 2.5))
        boot_hi = float(np.percentile(boots, 97.5))
        p_le0 = float((boots <= 0).mean() * 100.0)

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
        "card": card, "signal": cfg["sig"], "lb": lb, "reb": reb,
        "fee_bps": fee, "slippage_bps": slip, "cost_rt_bps": fee + slip,
        "min_elig": MIN_ELIG, "k_fixed": 2,
        "cap_per_8h": cap,
        "funding_charged": True,
        "funding_pnl_pct": funding_pnl_pct,
        "funding_paid_usd": diag["funding_paid_usd"],
        "fund_events_billed": diag["fund_events_billed"],
        "gross_no_funding_pct": gross_nf_pct,
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
        "legs_per_side_rule": "fixed 2 (7-name C universe)",
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
        "engine_version": "xsc-1",
        "universe": UNIVERSE,
        "funding_note": "JUP 1h head_gap 243.25 days and tail_gap 2.46 days "
                        "per data/FUNDING_MANIFEST.json; HYPE and JUP settle "
                        "every 4h (raw rates billed per real event); gate "
                        "rates normalized per 8h",
        "conventions": {
            "shared_with": "xs_factor_engine.py (Category A) — same state "
                           "machine, resized-to-target legs, average-cost "
                           "basis, hysteresis, costs on every fill, "
                           "zero-cost control asserted decision-identical",
            "decision": "close of rebalance bar, execution at next bar open",
            "cost_model": f"fee {fee} bps + slip {slip} bps per side = "
                          f"{fee + slip} bps round trip; charged on every fill",
            "funding_billing": "every settlement event of a held leg inside "
                               "(prev bar open, this bar open] bills "
                               "-dir * units * open * raw_rate; longs pay "
                               "positive rates; JUP/HYPE 4h cadence billed as "
                               "two real settlements; a leg is billed for "
                               "events at or after its entry instant",
            "funding_sims": "net = costs + funding; gross_tc = no trading "
                            "costs, funding charged (ex-cost control); "
                            "gross_nf = no trading costs, no funding "
                            "(funding_pnl_pct = gross_tc - gross_nf)",
            "fundgate_gate": "long candidate kept only if latest per-8h "
                             "rate <= 0 (receives); short candidate only if "
                             "> 0 (receives); failing candidates leave their "
                             "slot in cash (book not always fully "
                             "dollar-neutral — declared); held legs NOT "
                             "re-gated",
            "fundtail_gate": f"long candidate excluded if per-8h rate > {cap} "
                             f"(it would pay); short candidate excluded if "
                             f"rate < -{cap}; failing candidates leave their "
                             f"slot in cash; held legs NOT re-gated",
            "eligibility": "signal non-NaN at decision bar + close at t + "
                           "open at t+1 + a funding observation (gate "
                           "non-NaN), so the book starts when the six "
                           "non-HYPE names have funding",
            "min_elig": "6 of 7 (the C universe is 7 names by design)",
            "drop_out_at_data_end": True,
            "data_end_settlement": "a leg whose symbol's data has ended is "
                                   "closed / re-sized at the symbol's last "
                                   "available open price (no zombie legs)",
            "concentration": "pnl_eq_pct = net trade pnl / equity at entry; "
                             "conc_net_without_top5_pct is an arithmetic "
                             "decomposition of return_pct",
            "bootstrap": "default_rng(42), 10000 resamples, percentile 2.5/97.5",
            "bh": "equal-weight long-only of names priced at the first active "
                  "execution bar, no rebalancing, no costs",
            "active_window_stats": "thirds, halves, yearly returns and the "
                                   "70/30 IS/OOS split are measured on the "
                                   "ACTIVE window (from first_active_pos), "
                                   "not on the union index — the C books "
                                   "start in late 2024",
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
