"""Per-period robustness driver for the cbot 1m candidate.

AGENTS.md requires "green in >= 2/3 years". A single 730-day aggregate cannot show
that, and the suite was 0/10 at 5m -- so a pass at 1m has to earn its place on
period-by-period stability before it counts as anything.

Each slice keeps TRAIN_DAYS of warmup before the scored region (see run_cbot), so
slicing shrinks the evaluation window WITHOUT starving the model of training data.

Usage:  python code/_xtf_periods.py <sym> <tf> <hold_mode> [n_periods]
"""
import glob
import os
import subprocess
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYM = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
TF = sys.argv[2] if len(sys.argv) > 2 else "1m"
MODE = sys.argv[3] if len(sys.argv) > 3 else "minutes"
N = int(sys.argv[4]) if len(sys.argv) > 4 else 3

# Derive the window from the DATA, not from a hardcoded date. Newer perps (HYPE,
# JUP) list late, so a fixed 730-day window would put early periods entirely
# before the listing and silently score nothing.
path = os.path.join(ROOT, "data", f"binance_klines_{TF}_taker", f"{SYM}_{TF}.csv")
ts = pd.to_datetime(pd.read_csv(path, usecols=["open_ts"])["open_ts"], unit="ms", utc=True)
W0, W1 = ts.iloc[0].date().isoformat(), ts.iloc[-1].date().isoformat()
span_days = (pd.Timestamp(W1) - pd.Timestamp(W0)).days
print(f"{SYM} {TF}: {len(ts):,} bars, {W0} -> {W1} ({span_days}d), "
      f"split into {N} periods", flush=True)

d0 = pd.Timestamp(W0).date()
from datetime import timedelta                                           # noqa: E402
span = span_days / N
# parenthesise the addition: `d0 + timedelta(...).isoformat()` parses as
# `d0 + timedelta(...)` then `.isoformat()`, and timedelta has no isoformat.
def _d(offset):
    return (d0 + timedelta(days=round(span * offset))).isoformat()

bounds = [(_d(i), _d(i + 1)) for i in range(N)]

for i, (a, b) in enumerate(bounds, 1):
    cmd = ["python", "code/vrun.py", "run", "--strategy", "cbot", "--tf", TF,
           "--symbol", SYM, "--set", f"hold_mode={MODE}",
           "--set", f"slice_from={a}", "--set", f"slice_to={b}"]
    print(f"\n===== period {i}/{N}: {a} -> {b} =====", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    keep = [l for l in (r.stdout + r.stderr).splitlines()
            if any(k in l for k in ("run_id", "n_pass", "best_net_t", "max_trades",
                                    "n_bars", "min_auc", "max_auc", "REFUSED", "Error"))]
    print("\n".join(keep), flush=True)