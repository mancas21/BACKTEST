
import sys, numpy as np, pandas as pd
sys.path.insert(0, r"C:\Users\Lenovo\Documents\backtest-system\code")
from cbot.config import BotConfig
from cbot.data import make_world
from cbot.suite import run_suite
expect = {"momentum":"S01","meanrev":"S02","flow":"S05","season":"S10",
          "volshock":"S08","regime_ac":"S09","null":None}
print("=== KNOWN-ANSWER VALIDATION: a=1.0, gross t must rank the MATCHED strategy first ===")
print(f"{'world':<12}{'expected':<10}{'top by gross_t':<16}{'gross_t':>9}{'match?':>8}{'passes':>8}")
print("-"*66)
ok=0; tot=0
for w,exp in expect.items():
    df = make_world(w, a=1.0, n=30000)
    res = run_suite(df, BotConfig(), n_perm=2)
    r = res.sort_values("gross_t", ascending=False).iloc[0]
    m = (r["id"]==exp)
    if exp is None:
        m = (res.gross_t.abs().max() < 3)     # null: nothing anywhere near significant
    tot+=1; ok+=bool(m)
    print(f"{w:<12}{str(exp):<10}{r['id']+' '+r['strategy'][:12]:<16}{r['gross_t']:>+9.1f}"
          f"{str(bool(m)):>8}{int(res.PASS.sum()):>8}")
print("-"*66)
print(f"{ok}/{tot} worlds behave correctly")
