
import sys, numpy as np, pandas as pd
sys.path.insert(0, r"C:\Users\Lenovo\Documents\backtest-system\code")
from cbot.config import BotConfig
from cbot.data import make_world
from cbot.suite import run_suite

print("=== ENGINE VALIDATION on the pack's own known-answer worlds ===")
print(f"{'world':<12}{'best strategy':<10}{'gross_t':>9}{'net_t':>8}{'trades':>8}{'PASS':>7}{'passes':>8}")
print("-"*62)
for w in ("null","momentum","meanrev","flow","season","regime_ac"):
    df = make_world(w, a=0.2, n=30000)
    res = run_suite(df, BotConfig(), n_perm=3)
    r = res.sort_values("net_t", ascending=False).iloc[0]
    print(f"{w:<12}{r['id']:<10}{r['gross_t']:>+9.1f}{r['net_t']:>+8.1f}"
          f"{r['trades']:>8}{str(bool(r['PASS'])):>7}{int(res.PASS.sum()):>8}")
