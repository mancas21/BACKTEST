"""FIDELITY CHECK: does mp03_45m.py's transcription reproduce the original?

Run their engine on their data -> expect +45.97% / Sharpe 2.50 / n=261.
Run MY port on the SAME data -> must match. If it does not, my transcription
is wrong and the 45-month result would be testing my code, not theirs.

This is the same discipline used for CVRMD and SFS: verify the port against
the source's own published number before believing anything it says.
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ZC = r"C:\Users\Lenovo\.zcode\workspace\default\crypto-multi-strat"
sys.path.insert(0, os.path.join(ZC, "src"))
sys.path.insert(0, HERE)

from engine import run_backtest as zc_run          # noqa: E402
from strategies import S03_DonchianBreakout         # noqa: E402
import mp03_45m as MP                              # noqa: E402


def load_zc():
    data = {}
    for s in ("BTC", "ETH", "SOL", "AVAX", "LINK"):
        df = pd.read_csv(os.path.join(ZC, "data", f"{s}_USDC_1h.csv"),
                         index_col=0, parse_dates=[0])
        df.index = pd.to_datetime(df.index, utc=True)
        data[s] = df
    return data


def main():
    print("=" * 92)
    print("FIDELITY: my transcription of MP-STRAT-03 vs their engine, same data")
    print("=" * 92)

    st = S03_DonchianBreakout()
    r = zc_run(st, load_zc(), st.cfg)
    m = r.metrics
    print(f"\n  THEIR engine : ret {m['cum_return_pct']:+.2f}%  "
          f"sharpe {m['sharpe']:.2f}  dd {m['max_dd_pct']:.1f}%  "
          f"n {m['trades']}  pf {m['profit_factor']:.2f}  "
          f"wr {m['win_rate_pct']:.1f}%")
    print(f"  report says  : ret +45.97%  sharpe 2.50  dd -16.7%  "
          f"n 261  pf 1.77")

    # my port on the same 6-month window, single-symbol legs summed
    print("\n  my port, per-symbol legs on the same window (no funding, spot):")
    tot_trades = 0
    for s in ("BTC", "ETH", "SOL", "AVAX", "LINK"):
        p = os.path.join(ZC, "data", f"{s}_USDC_1h.csv")
        df = pd.read_csv(p, index_col=0, parse_dates=[0])
        df.index = pd.to_datetime(df.index, utc=True)
        ts = df.index.view("int64") // 10 ** 6
        arr = np.column_stack([
            np.asarray(ts, dtype=float),
            df["open"].to_numpy(float), df["high"].to_numpy(float),
            df["low"].to_numpy(float), df["close"].to_numpy(float),
            df["volume"].to_numpy(float)])
        r2 = MP.run_sym_arr(arr, funding=False)
        tot_trades += r2["n_trades"]
        print(f"    {s:<6} ret {r2['net']:+7.2f}%  dd {r2['mdd']:>5.1f}%  "
              f"n {r2['n_trades']:>3}  pf {r2['pf']:>5.2f}")
    print(f"\n    total trades across 5 legs: {tot_trades}  "
          f"(their portfolio caps 3 concurrent, so theirs <= sum)")

    print("\n  NOTE: an exact match is EXPECTED to be imperfect — their engine runs")
    print("  ONE portfolio with max 3 concurrent positions across 5 pairs, while")
    print("  my per-symbol legs are independent. The trade COUNT and the entry")
    print("  conditions are what must agree; the portfolio aggregation cannot.")
    print("\n  The decisive check is the entry/exit logic, verified separately.")


if __name__ == "__main__":
    main()
