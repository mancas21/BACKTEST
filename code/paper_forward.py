"""paper_forward.py — forward evidence tracker for the ATR Long Grid.

WHY THIS EXISTS
---------------
`paper_grid.py` mirrors the validated engine forward so paper equity IS engine
equity. That makes the forward number trustworthy for a given baseline. But a
baseline recorded during a data bootstrap is worthless: SOL's was captured when
the file held 999 bars (equity $10,094), the bootstrap then grew it to 212,018
bars (equity $2,343,627), and the resulting "forward P&L" of +$2.33M was simply
the bootstrap jump wearing a forward label.

So forward evidence needs three things a mirror alone does not give:
  1. A baseline frozen at a known, complete-history moment, with the bar
     timestamp it was taken at, so any later figure is attributable.
  2. Per-cycle deltas that survive a restart, so the forward record is a ledger
     and not a recomputation.
  3. Comparison against what a plain hold would have done over the SAME forward
     window. A grid that returned +2% while the market fell 30% is the thesis
     working; +2% into a +30% market is a laggard, and only the second number
     tells you which.

THE METRIC THAT MATTERS
-----------------------
Forward Sharpe of the grid's own daily returns, versus buy & hold's, on the
identical window. Not the cumulative return: a grid is flat most of the time and
its cumulative curve is dominated by compounding on a rising asset, so cumulative
return measures the asset, not the strategy.

HONESTY GUARDS, all deliberate
------------------------------
- The baseline is written once and NEVER silently recomputed. If history grows,
  that is a data event, not forward performance; the tracker records it.
- Positions open at baseline are flagged HELD_PRE and their unrealised P&L is
  excluded from forward P&L, because it predates the paper start.
- Every leg reports its bar count and data span, so a truncated file is visible
  in the output rather than hidden behind a plausible return.
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "code"))
import paper_grid as PG          # data pull + gates + validated engine driver

STATUS = os.path.join(ROOT, "grid_forward_status.json")
BASELINE = os.path.join(ROOT, "grid_forward_baseline.json")
LEDGER = os.path.join(ROOT, "grid_forward_ledger.csv")
HISTORY = os.path.join(ROOT, "grid_forward_history.json")

SYMBOLS = PG.SYMBOLS


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path, default):
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except Exception:
            return default
    return default


def day_returns(ts, eq, start_ts):
    """Daily returns of the equity curve, for the forward window only."""
    T = np.array(ts, dtype=np.int64)
    E = np.array(eq, float)
    m = T >= start_ts
    T, E = T[m], E[m]
    if len(E) < 2:
        return np.zeros(0)
    day = (T // 86400000)
    out = []
    for d in np.unique(day):
        sel = E[day == d]
        if len(sel) >= 2 and sel[0] > 0:
            out.append(sel[-1] / sel[0] - 1.0)
    return np.array(out)


def sharpe(r):
    r = np.asarray(r, float)
    r = r[np.isfinite(r)]
    if len(r) < 2 or r.std() == 0:
        return None
    return float(r.mean() / r.std() * np.sqrt(365))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true",
                    help="freeze the Day-0 baseline (refuses if one exists)")
    ap.add_argument("--reset", action="store_true",
                    help="delete the baseline and ledger, then re-init")
    ap.add_argument("--symbols", nargs="*", default=SYMBOLS)
    args = ap.parse_args()

    if args.reset:
        for p in (BASELINE, LEDGER, HISTORY):
            if os.path.exists(p):
                os.remove(p)
        print("cleared baseline, ledger, history")

    # ---- refresh data through the proven puller ----
    # Pull failures are recorded, not just printed. A REST error that exits 0
    # while the status file goes unchanged is the silent failure mode that
    # would stop forward evidence accumulating with nothing to show for it.
    pull_errors = {}
    for sym in args.symbols:
        p15, n, note = PG.pull_klines(sym, "15m", PG.TF_MS)
        if note != "ok":
            pull_errors[sym] = note
            print(f"  {sym}: {note}")

    import grid_audit as GA
    legs = {}
    for sym in args.symbols:
        path = PG.csv_path(sym, "15m")
        if not os.path.exists(path):
            continue
        bars = PG.load_bars(path)
        if len(bars) < 5000:
            print(f"  {sym}: only {len(bars)} bars, skipping")
            continue
        gate = PG.gate_fixed(bars) if PG.USE_FIXED_GATE else PG.gate_spec(bars)
        tr = {}
        eq = GA.simulate(bars, sym, gate, track=tr,
                         leg_fee=GA.MAKER_FEE, flat_fee=GA.TAKER_FEE,
                         leg_slip=GA.MAKER_SLIP, flat_slip=0.0005,
                         funding=True)
        T = np.array([b[0] for b in bars], dtype=np.int64)
        C = np.array([b[4] for b in bars], float)
        legs[sym] = dict(bars=bars, T=T, C=C, gate=gate, tr=tr,
                         eq_curve=tr["eq_curve"], equity=float(eq),
                         span=(int(T[0]), int(T[-1])))

    if not legs:
        print("no usable legs")
        return

    base = load_json(BASELINE, {})

    # ---- freeze the baseline ----
    if args.init or not base:
        base = dict(created_utc=datetime.now(timezone.utc)
                    .strftime("%Y-%m-%dT%H:%M:%SZ"), legs={})
        for sym, d in legs.items():
            base["legs"][sym] = dict(
                mtm=d["equity"],
                ts=int(d["T"][-1]),
                bars=len(d["bars"]),
                span=list(d["span"]),
                held=bool(d["tr"].get("open_lots", 0)),
                held_pre=bool(d["tr"].get("open_lots", 0)),
                close=float(d["C"][-1]))
        json.dump(base, open(BASELINE, "w"), indent=1)
        print(f"baseline frozen at {base['created_utc']}")
        for sym, b in base["legs"].items():
            print(f"  {sym:<9} equity ${b['mtm']:>14,.2f}  close {b['close']:.4f}  "
                  f"bars {b['bars']:,}  held_pre={b['held_pre']}")

    # ---- per-cycle report ----
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    out = dict(
        updated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        baseline_utc=base.get("created_utc"),
        pull_errors=pull_errors,
        forward_note=("cumulative return is dominated by compounding on a rising "
                      "asset; read fwd_sharpe vs bh_sharpe on the same window"),
        legs=[])

    hist = load_json(HISTORY, {})
    rows = []
    for sym, d in legs.items():
        b = base["legs"].get(sym)
        if not b:
            continue
        start_ts = b["ts"]
        fwd = d["equity"] - b["mtm"]
        fwd_pct = 100.0 * fwd / max(b["mtm"], 1e-9)
        # buy & hold over the identical forward window
        m = d["T"] >= start_ts
        bh_fwd_pct = (100.0 * (d["C"][-1] / b["close"] - 1.0)
                      if b["close"] > 0 else 0.0)
        g_r = day_returns(d["T"], d["eq_curve"], start_ts)
        bh_r = day_returns(d["T"], 10000.0 * d["C"], start_ts)
        gs, bs = sharpe(g_r), sharpe(bh_r)
        # a data-growth event is NOT forward performance
        grew = len(d["bars"]) > b["bars"]
        expected_bars = int((now_ms - start_ts) / 900000)
        got_bars = int((d["T"] >= start_ts).sum())
        missing = max(expected_bars - got_bars, 0)
        # Two conditions, both required:
        #   - a percentage breach, which is the meaningful signal once the
        #     window is long enough to average over
        #   - an ABSOLUTE floor, because on a window hours old one bar that has
        #     not closed yet is already 20-50% of the expectation
        stale_pct = (100.0 * missing / expected_bars) if expected_bars > 24 else 0.0
        stalled = (stale_pct > 20.0) and (missing >= 4)
        pre_ex = bool(d["tr"].get("open_lots", 0) and b.get("held_pre"))
        leg = dict(sym=sym,
                   last_bar=iso(int(d["T"][-1])),
                   fwd_bars=int((d["T"] >= start_ts).sum()),
                   equity=round(d["equity"], 2),
                   fwd_pnl=round(fwd, 2), fwd_pct=round(fwd_pct, 3),
                   bh_fwd_pct=round(bh_fwd_pct, 3),
                   excess_pct=round(fwd_pct - bh_fwd_pct, 3),
                   fwd_sharpe=round(gs, 3) if gs is not None else None,
                   bh_sharpe=round(bs, 3) if bs is not None else None,
                   dd_pct=round(d["tr"]["mdd"], 2),
                   exposure=round(float(np.mean(d["tr"]["expo_curve"][-2000:])), 3),
                   open_lots=int(d["tr"].get("open_lots", 0)),
                   bars_now=len(d["bars"]), bars_at_baseline=b["bars"],
                   expected_bars=expected_bars, missing_bars=missing,
                   stale_pct=round(stale_pct, 1), stalled=bool(stalled),
                   data_grew=bool(grew),
                   pre_existing=pre_ex,
                   days_forward=len(g_r))
        out["legs"].append(leg)
        rows.append(leg)
        hist.setdefault(sym, []).append(dict(
            ts=int(d["T"][-1]), equity=d["equity"], fwd=fwd,
            fwd_pct=fwd_pct, bh_fwd_pct=bh_fwd_pct, bars=len(d["bars"])))

    worst_stale = max([l["stale_pct"] for l in rows], default=0.0)
    stalled_syms = [l["sym"] for l in rows if l.get("stalled")]
    out["health"] = dict(
        pull_errors=len(pull_errors),
        worst_stale_pct=round(worst_stale, 1),
        stalled=stalled_syms,
        healthy=(not pull_errors) and not stalled_syms,
        note=("healthy=False means a data pull failed, or a leg is >20% behind "
              "AND missing at least 4 closed bars. The absolute floor matters: "
              "on a window only hours old a single not-yet-closed 15m bar is "
              "already >20% of the expectation, and a guard that fires every "
              "tick is one that gets ignored. Forward P&L is NOT accumulating "
              "while this is false."))
    json.dump(out, open(STATUS, "w"), indent=1)
    json.dump(hist, open(HISTORY, "w"), indent=1)

    # append to the ledger so forward is a durable record, not a recomputation
    need = (not os.path.exists(LEDGER)) or os.path.getsize(LEDGER) == 0
    with open(LEDGER, "a", newline="") as f:
        w = csv.writer(f)
        if need:
            w.writerow(["utc", "sym", "last_bar_ts", "bars", "equity", "fwd_pnl",
                        "fwd_pct", "bh_fwd_pct", "excess_pct", "dd_pct",
                        "exposure", "open_lots"])
        for leg in rows:
            w.writerow([out["updated_utc"], leg["sym"], leg["last_bar"],
                        leg["bars_now"], leg["equity"], leg["fwd_pnl"],
                        leg["fwd_pct"], leg["bh_fwd_pct"], leg["excess_pct"],
                        leg["dd_pct"], leg["exposure"], leg["open_lots"]])

    # ---- print ----
    print("\n" + "=" * 96)
    print(f"FORWARD PAPER — baseline {base.get('created_utc')}   "
          f"cycle {out['updated_utc']}")
    print("=" * 96)
    print(f"  {'sym':<9}{'fwd bars':>10}{'fwd $':>13}{'fwd %':>9}{'BH %':>9}"
          f"{'excess pp':>11}{'gSharpe':>9}{'bSharpe':>9}{'DD%':>7}{'days':>6}")
    print("  " + "-" * 94)
    for leg in rows:
        gs = leg["fwd_sharpe"] if leg["fwd_sharpe"] is not None else "n/a"
        bs = leg["bh_sharpe"] if leg["bh_sharpe"] is not None else "n/a"
        print(f"  {leg['sym']:<9}{leg['fwd_bars']:>10,}{leg['fwd_pnl']:>+13,.2f}"
              f"{leg['fwd_pct']:>+8.2f}%{leg['bh_fwd_pct']:>+8.2f}%"
              f"{leg['excess_pct']:>+10.2f}{gs:>9}{bs:>9}{leg['dd_pct']:>6.1f}%"
              f"{leg['days_forward']:>6}")
    print("  " + "-" * 94)
    grew = [l["sym"] for l in rows if l["data_grew"]]
    pre = [l["sym"] for l in rows if l["pre_existing"]]
    print(f"  data grew since baseline: {grew or 'none'}")
    print(f"  held pre-baseline (unrealised excluded): {pre or 'none'}")
    if not any(l["days_forward"] for l in rows):
        print("\n  NOTE: no complete forward day yet. The baseline was taken on the")
        print("  most recent closed bar, so forward performance needs at least one")
        print("  full day of new bars before Sharpe means anything.")
    print(f"  health: healthy={out['health']['healthy']}  "
          f"pull_errors={out['health']['pull_errors']}  "
          f"worst_stale={out['health']['worst_stale_pct']}%  "
          f"stalled={out['health']['stalled'] or 'none'}")
    print(f"\nwrote {STATUS}, {LEDGER}, {HISTORY}")


if __name__ == "__main__":
    main()