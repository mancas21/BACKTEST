
"""horizon sweep -- the pack's own SKILL predicts short horizons are not
operable and names "horizontes mayores" (longer horizons) as the normal escape.
This tests that claim directly, using their run_suite unchanged."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, r"C:\Users\Lenovo\Documents\backtest-system\code")
from dataclasses import replace
from cbot.config import BotConfig
from cbot.data import load_or_fetch
from cbot.suite import run_suite

SYMS = ["BTCUSDT","ETHUSDT","SOLUSDT"]
print("=== HORIZON SWEEP, 5m bars, taker costs, Bonferroni t>2.58 ===")
print(f"{'sym':<9}{'hold':>6}{'h(min)':>8}{'best id':>8}{'best AUC':>10}{'gross_t':>9}"
      f"{'net_t':>8}{'trades':>8}{'net%':>9}{'passes':>8}")
print("-"*76)
rows=[]
for s in SYMS:
    df = load_or_fetch(s, "5m", 730)
    for h in (3, 12, 48, 144):
        cfg = BotConfig(symbol=s, interval_min=5, horizon_bars=h)
        res = run_suite(df, cfg, n_perm=3)
        r = res.sort_values("net_t", ascending=False).iloc[0]
        npass = int(res.PASS.sum())
        print(f"{s:<9}{h:>6}{h*5:>8}{r['id']:>8}{r['AUC']:>10.3f}{r['gross_t']:>+9.1f}"
              f"{r['net_t']:>+8.1f}{r['trades']:>8}{r['net_ret']:>+8.1%}{npass:>8}")
        rows.append(dict(sym=s,h=h,auc=r['AUC'],gt=r['gross_t'],nt=r['net_t'],
                         n=r['trades'],nr=r['net_ret'],p=npass))
    print("-"*76)
best = max(rows, key=lambda r: r['nt'] if np.isfinite(r['nt']) else -9)
print(f"best net_t anywhere: {best['sym']} hold={best['h']} net_t={best['nt']:+.1f} "
      f"AUC={best['auc']:.3f} trades={best['n']} net={best['nr']:+.1%}")
print(f"total passes across the whole sweep: {sum(r['p'] for r in rows)}")
