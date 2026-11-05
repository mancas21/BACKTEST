#!/usr/bin/env python3
"""Print the XRP paper bot status in one line. Used on the VPS and locally."""
import json
import os
import sys

p = sys.argv[1] if len(sys.argv) > 1 else "xrp_paper_bot_status.json"
if not os.path.exists(p):
    print("NO STATUS FILE at", p)
    raise SystemExit(1)
d = json.load(open(p, encoding="utf-8"))
keys = ["updated_utc", "last_bar", "bars", "equity", "net_from_inception_pct",
        "forward_pnl", "forward_pct", "pf_all_closed", "n_closed", "win_rate_pct",
        "max_dd_pct", "fees_paid", "funding_paid", "funding_prints",
        "NEUTRALITY_avg_abs_delta_pct", "open_lots", "buyhold_pct"]
print(" | ".join(f"{k}={d.get(k)}" for k in keys))
