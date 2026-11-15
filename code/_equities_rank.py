#!/usr/bin/env python3
"""
_equities_rank.py — add the S&P 500 transfer cells to the strategy universe
(`code/_top100_rank.json`, the registry's input).

Same convention as the rest of the universe: one row per book. A pack-style
artifact (eqpack) contributes one row per strategy, like the repo's existing
equities rows do; a single-strategy adapter contributes one row for the cell.

The label carries the asset and the cost regime, because the same strategy on
the same symbol appears at several cost regimes and the registry must not show
them as one book.

Usage:  python code/_equities_rank.py
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
RUNS = os.path.join(ROOT, "results", "runs")
RANK = os.path.join(HERE, "_top100_rank.json")
SWEEP = os.path.join(HERE, "_equities_sweep.json")


def pick(m, *keys):
    for k in keys:
        if k in m and m[k] is not None:
            return m[k]
    return None


def main():
    rows = json.load(open(RANK, encoding="utf-8-sig"))
    sweep = json.load(open(SWEEP, encoding="utf-8"))
    # Drop the rows this script wrote on a previous pass (their labels carry
    # the asset and the cost regime in brackets) and rebuild them from the
    # current sweep, so a re-run with a corrected parameter does not leave a
    # stale cell behind in the universe.
    def _is_mine(label):
        """Rows this script wrote. Every label it writes carries the daily
        timeframe ("1d"); the repo's own pre-existing equities rows carry no
        timeframe in their label, so they are never mistaken for ours."""
        return "1d" in (label or "")

    kept = [r for r in rows if not _is_mine(r.get("label"))]
    dropped = len(rows) - len(kept)
    rows = kept
    # `have` is recomputed AFTER the drop: the dropped cells are exactly the
    # ones this pass has to re-add.
    have = {r["run_id"] for r in rows}
    added = 0
    for s in sweep:
        if not s["ok"]:
            continue
        rid = s["run_id"]
        if rid in have:
            continue
        a = json.load(open(os.path.join(RUNS, rid + ".json"), encoding="utf-8"))
        m = a["metrics"]
        base_label = f"[EQ] {s['strategy']} on {s['symbol']} 1d ({s['regime']} costs)"
        pack_rows = [t for t in (a.get("tables") or [])
                     if t.get("kind") == "strategy" and t.get("status") == "ok"]
        if pack_rows:
            for t in pack_rows:
                rows.append(dict(
                    run_id=rid, adapter=s["strategy"], symbol=s["symbol"],
                    tf="1d", label=f"[EQ] {t['id']} {t.get('name','')} "
                                   f"({s['symbol']} 1d {s['regime']})",
                    ret=t.get("net_%"), pf=t.get("PF"), n=t.get("trades"),
                    dd=t.get("maxDD_%"), bh=t.get("buy_hold_%"),
                    fee=a["metrics"].get("cost_bp_roundtrip"), slip=None,
                    funding=False, created=a.get("created_utc", "")[:10],
                    gates=None))
                added += 1
        else:
            rows.append(dict(
                run_id=rid, adapter=s["strategy"], symbol=s["symbol"], tf="1d",
                label=base_label,
                ret=pick(m, "return_pct", "ret_pct"),
                pf=pick(m, "profit_factor", "pf_strict"),
                n=pick(m, "n_trades", "n"),
                dd=pick(m, "max_dd_pct", "dd_pct"),
                bh=pick(m, "bh_return_pct", "bench_ret_pct"),
                fee=m.get("cost_bp_roundtrip"), slip=None, funding=False,
                created=a.get("created_utc", "")[:10], gates=None))
            added += 1
        have.add(rid)
    if added or dropped:
        with open(RANK, "w", encoding="utf-8", newline="") as f:
            json.dump(rows, f)
    print(f"rank: {added} rows added, {dropped} stale rows dropped, "
          f"{len(rows)} total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
