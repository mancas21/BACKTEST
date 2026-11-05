"""xs_core_fast.py — vectorized simulation core for the xs* family (2026-11-02).

The Category A/B/C engines are hash-pinned by their artifacts and CANNOT be
edited; this module is the shared core for the NEXT engines. It reproduces
the pinned state-machine semantics but replaces the per-bar Python loop with
per-exec-segment numpy operations: the decision loop only runs at the ~n/reb
decision bars; mark-to-market, funding billing and exposure aggregation run
as vectorized segment ops.

Parity: validated by code/_xsf_fast_parity.py against the pinned Category C
engine on the FUNDGATE card (structural trade equality + metric agreement).
Float bit-equality is NOT expected (segment cumsum and aggregated funding
change summation order); agreement is to ~1e-8 absolute on the equity curve.

Semantics (identical to the pinned engines, see their docstrings):
decision on the rebalance bar's close, execution at the next bar's open; one
fill costs cost_rate * notional; every leg resized to equity/(2k) at every
rebalance (average-cost basis, partial reduces realize nothing, basis
averages on adds); hysteresis enter rank<=k / hold while rank<=2k in
long-best rank space; min_elig cross-section floor; a symbol needs a funding
observation (funded mask) to be eligible when funding is used; data-end
settlement at the last valid open; funding billed per real settlement event
inside (prev bar open, this bar open] at that bar's open price with the
units in force (events at bar 0 never bill, matching the pinned loop).
"""

import numpy as np
import pandas as pd


def simulate(close_w, open_w, sig_w, reb, cost_rate,
             long_ok=None, short_ok=None, funded=None, funding=None,
             charge_funding=True, min_elig=8, k_fixed=None):
    """Run one book. Returns (equity_curve, trades, diag) — same shapes and
    keys as the pinned engines' _simulate. Deterministic."""
    n = len(close_w)
    lb = sig_w.attrs.get("lb", 0)
    first = ((lb + reb - 1) // reb) * reb
    decisions = list(range(first, n - 1, reb))

    close_mark = close_w.ffill()
    open_mark = open_w.ffill()
    close_np = close_w.to_numpy()
    open_np = open_w.to_numpy()
    mark_np = close_mark.to_numpy()
    openm_np = open_mark.to_numpy()
    sig_np = sig_w.to_numpy()
    lok = long_ok.to_numpy() if hasattr(long_ok, "to_numpy") else long_ok
    shok = short_ok.to_numpy() if hasattr(short_ok, "to_numpy") else short_ok
    fnd = funded.to_numpy() if hasattr(funded, "to_numpy") else funded
    open_ts = close_w.index.to_numpy(dtype="int64")
    syms = list(close_w.columns)
    nsym = len(syms)
    asc = sig_w.attrs.get("asc", True)

    # per-bar aggregated funding (raw rate sum + event count) per symbol
    fund_bar = np.zeros((n, nsym))
    fund_cnt = np.zeros((n, nsym))
    if funding is not None and charge_funding:
        for j, s in enumerate(syms):
            if s not in funding:
                continue
            ts, rate, _ = funding[s]
            b = np.searchsorted(open_ts, ts, side="left")
            m = (b > 0) & (b < n)  # bar 0 never bills (matches pinned loop)
            np.add.at(fund_bar[:, j], b[m], rate[m])
            np.add.at(fund_cnt[:, j], b[m], 1.0)

    cash = 1.0
    eq = np.ones(n, dtype="float64")
    trades = []
    turnover = 0.0
    funding_paid = 0.0
    events_billed = 0
    deferred = 0
    nan_mark_bars = 0
    gross_sum = 0.0
    elig_counts = []
    first_active_pos = None
    legs = []
    seg = [0]

    def fill_segment(b):
        """Vectorized mark + funding + aggregates for bars [seg, b) with the
        legs as they stand (units constant on the segment; cash constant
        apart from funding flows inside the segment)."""
        nonlocal funding_paid, events_billed, nan_mark_bars, gross_sum
        a = seg[0]
        if b <= a:
            return
        if legs:
            cols = np.array([lg["col"] for lg in legs])
            dirs = np.array([float(lg["dir"]) for lg in legs])
            units = np.array([lg["units"] for lg in legs])
            mark_seg = mark_np[a:b]
            contrib = mark_seg[:, cols] * dirs * units
            legval = contrib.sum(axis=1)
            if funding is not None and charge_funding:
                px = open_np[a:b][:, cols]
                px = np.where(np.isnan(px), openm_np[a:b][:, cols], px)
                flows = -((dirs * units) * (px * fund_bar[a:b][:, cols])).sum(axis=1)
                funding_paid += -float(flows.sum())
                events_billed += int(fund_cnt[a:b][:, cols].sum())
                cashpath = cash + np.cumsum(flows)
            else:
                cashpath = cash
            eq[a:b] = cashpath + legval
            nan_mark_bars += int(np.isnan(close_np[a:b][:, cols]).sum())
            gross_sum += float(np.abs(contrib).sum())
        else:
            eq[a:b] = cash

    def fill_cost(notional):
        return cost_rate * abs(notional)

    for t in decisions:
        elig = []
        for j in range(nsym):
            if np.isnan(sig_np[t, j]) or np.isnan(close_np[t, j]) \
                    or np.isnan(open_np[t + 1, j]):
                continue
            if fnd is not None and not fnd[t, j]:
                continue
            elig.append(j)
        n_el = len(elig)
        elig_counts.append(n_el)
        if n_el < min_elig:
            continue
        if first_active_pos is None:
            first_active_pos = t
        k = k_fixed if k_fixed else min(3, max(1, n_el // 4))
        scores = sig_np[t, elig]
        if not asc:
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
                             and (lok is None or lok[t, j])],
                            key=lambda j: rank_of[j])
        short_cands = sorted([j for j in pool if rank_of[j] >= n_el - k + 1
                              and (shok is None or shok[t, j])],
                             key=lambda j: -rank_of[j])

        # mark the segment up to the decision bar BEFORE exec (eq[t] is the
        # sizing base, exactly like the pinned loop marks eq[t] pre-exec)
        fill_segment(t + 1)
        seg[0] = t + 1

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
                "entry_ts": int(open_ts[lg["entry_pos"]]),
                "exit_ts": int(open_ts[exec_t]),
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

    fill_segment(n)
    last = n - 1
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
            "entry_ts": int(open_ts[lg["entry_pos"]]),
            "exit_ts": int(open_ts[last]),
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
        "fund_events_billed": int(events_billed),
        "n_decisions": len(decisions),
        "eligible_min": int(min(elig_counts)) if elig_counts else 0,
        "eligible_median": float(np.median(elig_counts)) if elig_counts else 0.0,
        "eligible_max": int(max(elig_counts)) if elig_counts else 0,
        "deferred_fills": deferred,
        "nan_mark_bars": int(nan_mark_bars),
        "avg_gross_exposure_pct": float(gross_sum / max(n, 1) * 100.0),
        "first_active_pos": int(first_active_pos) if first_active_pos is not None
                            else int(((lb + reb - 1) // reb) * reb),
    }
