"""xs_factor_b_engine.py — Category B relative-value books (2026-11-02).

Reuses the machinery of xs_factor_engine.py (Category A) UNTOUCHED — its bytes
are pinned by the nine Category A artifacts — and adds two cards:

  VOLCOMP   signal = z-score (over ZWIN bars, population moments) of the
            asset's realized vol (lb bars, population ddof=0) divided by the
            cross-sectional MEDIAN of that same vol at each bar; ranked
            ascending (rank 1 = most compressed relative vol); long the k
            most compressed, short the k most elevated. Drift gate (card
            spec): a long candidate additionally needs ROC(ROCW) > 0 and a
            short candidate ROC(ROCW) < 0; failing candidates leave their
            slot in cash (the book is therefore not always fully
            dollar-neutral — declared). Held legs are NOT re-gated: the gate
            selects entries only.
  DDRELAY   event-conditional book. Trigger, evaluated at each decision bar:
            cross-sectional median of the DD_RET-bar return < `trig`
            (default -0.20), with at least min_elig symbols contributing.
            While the trigger is active: long the k least-drawn and short
            the k most-drawn from their DD_HIGH-bar high, FIXED k=2 per the
            card. When the trigger clears, the whole book closes at the next
            open and stays flat until the next trigger. Weekly decisions
            (reb=168). A decision skipped for min_elig leaves held legs
            untouched (they cannot be ranked); the trigger-off close always
            executes (data-end settlement at the last valid open).

Shared conventions (identical to Category A — see xs_factor_engine
docstring): decision on the rebalance bar's close, execution next open,
fee+slip per side charged on every fill, resize-to-target every rebalance
with average-cost basis, hysteresis (enter rank<=k, hold while rank<=2k),
minimum cross-section 8, mark-to-market on last available close, legs whose
symbol's data ends settle at the last valid open, funding NOT charged
(declared: 7 of 14 names have no funding file on disk), zero-cost control
asserted decision-identical, bootstrap seeded 42.
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xs_factor_engine as xse  # noqa: E402  (pinned by the Category A artifacts)

UNIVERSE = xse.UNIVERSE
MIN_ELIG = xse.MIN_ELIG

CARDS = {
    "VOLCOMP": {"lb": 336, "sig": "volcomp", "asc": True, "reb": 336},
    "DDRELAY": {"lb": 336, "sig": "dd", "asc": False, "reb": 168, "k_fixed": 2},
}

ZWIN = 1440    # VOLCOMP: z-score window of the relative vol (60d), declared
ROCW = 168     # VOLCOMP: drift-gate ROC window (7d), declared
DD_HIGH = 336  # DDRELAY: drawdown high window (14d), declared
DD_RET = 720   # DDRELAY: trigger return window (30d), declared
BARS_PER_YEAR = xse.BARS_PER_YEAR


def _simulate(close_w, open_w, sig_w, reb, cost_rate,
              gate_np=None, trigger=None, k_fixed=None):
    """Category B state machine: identical to Category A's plus (a) an entry
    drift gate and (b) an event trigger that closes the whole book when it
    clears. Deterministic; zero-cost runs make identical decisions."""
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
    active_decisions = 0
    first_active_pos = None
    episodes = 0
    in_episode = False

    def fill_cost(notional):
        return cost_rate * abs(notional)

    for t in range(n_bars):
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
        if trigger is not None and not bool(trigger[t]):
            closed, kept = list(legs), []
            pool, long_cands, short_cands, k = [], [], [], None
            in_episode = False
        else:
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
            if not in_episode:
                episodes += 1
            in_episode = True
            active_decisions += 1
            k = k_fixed if k_fixed else min(3, max(1, n_el // 4))
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

            def passes(j, want_pos):
                if gate_np is None:
                    return True
                g = gate_np[t, j]
                return g > 0 if want_pos else g < 0

            long_cands = sorted([j for j in pool if rank_of[j] <= k
                                 and passes(j, True)], key=lambda j: rank_of[j])
            short_cands = sorted([j for j in pool if rank_of[j] >= n_el - k + 1
                                  and passes(j, False)],
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

        if k is not None:
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
                kept.append({"sym": syms[j], "dir": 1, "units": units,
                             "basis": float(px), "realized": 0.0,
                             "leg_costs": fill_cost(target), "col": j,
                             "entry_pos": t, "entry_notional": float(target),
                             "entry_eq": float(eq[t])})
            for j in short_cands[:max(0, k - n_short_now)]:
                px = open_np[exec_t, j]
                units = target / px
                cash += units * px - fill_cost(target)
                turnover += target
                kept.append({"sym": syms[j], "dir": -1, "units": units,
                             "basis": float(px), "realized": 0.0,
                             "leg_costs": fill_cost(target), "col": j,
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
        "n_decisions": len(decisions),
        "active_decisions": active_decisions,
        "episodes": episodes,
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
        raise ValueError(f"unknown xsb card: {card!r} (use VOLCOMP|DDRELAY)")
    cfg = CARDS[card]
    lb = int(p.pop("lb", cfg["lb"]))
    reb = int(p.pop("reb", cfg["reb"]))
    fee = float(p.pop("fee_bps", 5.0))
    slip = float(p.pop("slippage_bps", 0.5))
    trig = None
    if card == "DDRELAY":
        trig = float(p.pop("trig", -0.20))
        if not -0.5 <= trig <= -0.05:
            raise ValueError("trig out of declared range (-0.5..-0.05)")
    elif "trig" in p:
        raise ValueError("trig is a DDRELAY-only param")
    if p:
        raise ValueError(f"unknown xsb params: {sorted(p)}")
    if lb < 24 or reb < 24 or lb > 4000:
        raise ValueError("lb/reb out of declared range (24..4000 / >=24)")

    idx, close_w, open_w = xse._load_frames(sorted(paths))
    logret = np.log(close_w).diff()

    gate_np = None
    trigger = None
    k_fixed = cfg.get("k_fixed")
    if card == "VOLCOMP":
        vol = logret.rolling(lb, min_periods=lb).std(ddof=0)
        med = vol.median(axis=1)
        relvol = vol.div(med, axis=0)
        mu = relvol.rolling(ZWIN, min_periods=ZWIN).mean()
        sd = relvol.rolling(ZWIN, min_periods=ZWIN).std(ddof=0)
        sig = ((relvol - mu) / sd).replace([np.inf, -np.inf], np.nan)
        gate = close_w / close_w.shift(ROCW) - 1.0
        gate_np = gate.to_numpy()
    else:
        rollmax = close_w.rolling(DD_HIGH, min_periods=DD_HIGH).max()
        sig = close_w / rollmax - 1.0  # dd <= 0; asc=False -> rank1 = least drawn
        r30 = close_w / close_w.shift(DD_RET) - 1.0
        med = r30.median(axis=1)
        cnt = r30.notna().sum(axis=1)
        trigger = ((med < trig) & (cnt >= MIN_ELIG)).to_numpy()
    sig.attrs["lb"] = lb
    sig.attrs["asc"] = cfg["asc"]

    cost_rate = (fee + slip) / 1e4
    eq_net, trades, diag = _simulate(close_w, open_w, sig, reb, cost_rate,
                                     gate_np=gate_np, trigger=trigger,
                                     k_fixed=k_fixed)
    eq_gross, trades_g, _ = _simulate(close_w, open_w, sig, reb, 0.0,
                                      gate_np=gate_np, trigger=trigger,
                                      k_fixed=k_fixed)
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
        "min_elig": MIN_ELIG,
        "zwin_declared": ZWIN if card == "VOLCOMP" else None,
        "rocw_declared": ROCW if card == "VOLCOMP" else None,
        "trig": trig,
        "k_fixed": k_fixed,
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
        "active_decisions": diag["active_decisions"],
        "episodes": diag["episodes"],
        "eligible_min": diag["eligible_min"],
        "eligible_median": diag["eligible_median"],
        "eligible_max": diag["eligible_max"],
        "deferred_fills": diag["deferred_fills"],
        "nan_mark_bars": diag["nan_mark_bars"],
        "avg_gross_exposure_pct": diag["avg_gross_exposure_pct"],
        "funding_charged": False,
        "legs_per_side_rule": ("fixed 2 (DDRELAY card)"
                               if k_fixed else "k=min(3, max(1, N_elig//4))"),
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
        "engine_version": "xsb-1",
        "universe": UNIVERSE,
        "conventions": {
            "shared_with": "xs_factor_engine.py (Category A) — same state "
                           "machine, resized-to-target legs, average-cost "
                           "basis, hysteresis, min cross-section 8, costs on "
                           "every fill, zero-cost control asserted",
            "decision": "close of rebalance bar, execution at next bar open",
            "cost_model": f"fee {fee} bps + slip {slip} bps per side = "
                          f"{fee + slip} bps round trip; charged on every fill",
            "volcomp_signal": f"z-score over {ZWIN} bars (population) of "
                              f"vol({lb}) / cross-sectional median vol({lb})",
            "volcomp_gate": f"drift gate: long candidates need ROC({ROCW}) > 0, "
                            f"short candidates ROC({ROCW}) < 0; failing "
                            f"candidates leave their slot in cash (book not "
                            f"always fully dollar-neutral — declared); held "
                            f"legs are NOT re-gated",
            "ddrelay_trigger": f"cross-sectional median of the {DD_RET}-bar "
                               f"return < {trig} with at least {MIN_ELIG} "
                               f"symbols contributing; while active the book "
                               f"ranks drawdown from the {DD_HIGH}-bar high "
                               f"(long least drawn, short most drawn, fixed "
                               f"k=2); when the trigger clears the whole book "
                               f"closes at the next open and stays flat",
            "drop_out_at_data_end": True,
            "data_end_settlement": "a leg whose symbol's data has ended is "
                                   "closed / re-sized at the symbol's last "
                                   "available open price (no zombie legs)",
            "funding": "NOT charged - 7/14 universe names have no funding file "
                       "(BTC ETH HYPE JUP SOL SUI XRP are the covered ones); "
                       "second-order for a dollar-neutral rotation book, "
                       "declared",
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
