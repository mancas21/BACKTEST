#!/usr/bin/env python3
"""Append one 1m-accounting snapshot per pair to daily_summary_1m.csv.

Separate file from daily_summary.csv on purpose: the 15m series is an
append-only record with a fixed schema, and rewriting its header would corrupt
every earlier row. This file carries the 1m numbers next to the 15m ones so the
fill-model difference is a column, not a recollection.

Idempotent per UTC date, like the 15m summary.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone

ROOT = "/home/ubuntu/neutral-paper"
PAIRS = ["JUP", "XRP", "SOL", "HYPE", "SUI"]
OUT = os.path.join(ROOT, "daily_summary_1m.csv")
FIELDS = [
    "snapshot_date", "snapshot_utc", "pair", "symbol", "day0_utc", "last_bar",
    "equity", "forward_pct", "forward_pnl", "forward_closed_lots",
    "forward_closed_pnl", "forward_carry_pnl", "forward_pf",
    "forward_win_rate_pct", "open_lots", "day0_open_lots",
    "max_dd_pct", "max_gross_leverage", "min_margin_buffer_pct",
    "funding_paid", "kill_triggered", "kill_reason",
    "forward_coverage_pct", "forward_same_bar_covers", "forward_one_m_covers",
    "same_minute_touched", "equity_15m", "forward_pnl_delta_vs_15m",
]


def load(pair):
    path = os.path.join(ROOT, pair, "xrp_paper_bot_status_1m.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def row_for(pair, s, now):
    m = s.get("one_m") or {}
    v = s.get("vs_15m") or {}
    return {
        "snapshot_date": now.strftime("%Y-%m-%d"),
        "snapshot_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pair": pair,
        "symbol": s.get("sym"),
        "day0_utc": s.get("day0_utc"),
        "last_bar": s.get("last_bar"),
        "equity": s.get("equity"),
        "forward_pct": s.get("forward_pct"),
        "forward_pnl": s.get("forward_pnl"),
        "forward_closed_lots": s.get("forward_closed_lots"),
        "forward_closed_pnl": s.get("forward_closed_pnl"),
        "forward_carry_pnl": s.get("forward_carry_pnl"),
        "forward_pf": s.get("forward_pf"),
        "forward_win_rate_pct": s.get("forward_win_rate_pct"),
        "open_lots": s.get("open_lots"),
        "day0_open_lots": s.get("day0_open_lots"),
        "max_dd_pct": s.get("max_dd_pct"),
        "max_gross_leverage": s.get("max_gross_leverage"),
        "min_margin_buffer_pct": s.get("min_margin_buffer_pct"),
        "funding_paid": s.get("funding_paid"),
        "kill_triggered": s.get("kill_triggered"),
        "kill_reason": s.get("kill_reason"),
        "forward_coverage_pct": m.get("forward_coverage_pct"),
        "forward_same_bar_covers": m.get("forward_same_bar_covers"),
        "forward_one_m_covers": m.get("forward_one_m_covers"),
        "same_minute_touched": m.get("same_minute_touched"),
        "equity_15m": v.get("equity"),
        "forward_pnl_delta_vs_15m": v.get("forward_pnl_delta_1m_minus_15m"),
    }


def main():
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    existing = []
    if os.path.exists(OUT):
        with open(OUT, newline="", encoding="utf-8") as f:
            existing = list(csv.DictReader(f))
    already = {r["pair"] for r in existing if r.get("snapshot_date") == today}

    statuses = {p: load(p) for p in PAIRS}
    new_rows = [row_for(p, s, now) for p, s in statuses.items()
                if s is not None and p not in already]

    if new_rows and "TOTAL" not in already:
        total_eq = sum(float(r["equity"] or 0) for r in new_rows)
        total_pnl = sum(float(r["forward_pnl"] or 0) for r in new_rows)
        total_15m = sum(float(r["equity_15m"] or 0) for r in new_rows)
        new_rows.append({
            "snapshot_date": today,
            "snapshot_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pair": "TOTAL", "symbol": "5-PAIR", "day0_utc": None,
            "last_bar": None,
            "equity": round(total_eq, 4),
            "forward_pct": round(100 * (total_eq / (25.0 * len(PAIRS)) - 1), 4),
            "forward_pnl": round(total_pnl, 4),
            "forward_closed_lots": sum(int(r["forward_closed_lots"] or 0)
                                       for r in new_rows),
            "forward_closed_pnl": None,
            "forward_carry_pnl": round(sum(float(r["forward_carry_pnl"] or 0)
                                           for r in new_rows), 4),
            "forward_pf": None, "forward_win_rate_pct": None,
            "open_lots": sum(int(r["open_lots"] or 0) for r in new_rows),
            "day0_open_lots": sum(int(r["day0_open_lots"] or 0) for r in new_rows),
            "max_dd_pct": None, "max_gross_leverage": None,
            "min_margin_buffer_pct": None,
            "funding_paid": round(sum(float(r["funding_paid"] or 0)
                                      for r in new_rows), 4),
            "kill_triggered": any(str(r["kill_triggered"]) == "True" for r in new_rows),
            "kill_reason": None,
            "forward_coverage_pct": None,
            "forward_same_bar_covers": sum(int(r["forward_same_bar_covers"] or 0)
                                           for r in new_rows),
            "forward_one_m_covers": sum(int(r["forward_one_m_covers"] or 0)
                                        for r in new_rows),
            "same_minute_touched": sum(int(r["same_minute_touched"] or 0)
                                       for r in new_rows),
            "equity_15m": round(total_15m, 4),
            "forward_pnl_delta_vs_15m": round(
                sum(float(r["forward_pnl_delta_vs_15m"] or 0) for r in new_rows), 4),
        })

    if not new_rows:
        print(f"{today}: 1m snapshot already present, nothing appended")
        return

    need_header = not os.path.exists(OUT) or os.path.getsize(OUT) == 0
    with open(OUT, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if need_header:
            w.writeheader()
        w.writerows(new_rows)

    print(f"{today}: appended {len(new_rows)} rows to {OUT}")
    for r in new_rows:
        print(f"  {r['pair']:5s} eq1m={r['equity']} eq15m={r['equity_15m']} "
              f"fwd={r['forward_pnl']} cov={r['forward_coverage_pct']} "
              f"lots={r['forward_closed_lots']} kill={r['kill_triggered']}")


if __name__ == "__main__":
    main()
