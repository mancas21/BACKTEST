
import sys, numpy as np, pandas as pd
sys.path.insert(0, r"C:\Users\Lenovo\Documents\backtest-system\code")
from cbot.config import BotConfig
from cbot.data import make_world
from cbot.suite import run_suite
for w in ("volshock","regime_ac","null"):
    try:
        df = make_world(w, a=1.0, n=30000)
        print(f"{w}: price min {df.close.min():.2f} max {df.close.max():.2f} finite={np.isfinite(df.close).all()}")
        res = run_suite(df, BotConfig(), n_perm=2)
        r = res.sort_values("gross_t", ascending=False).iloc[0]
        print(f"   -> top {r['id']} gross_t {r['gross_t']:+.1f}  passes {int(res.PASS.sum())}")
    except Exception as e:
        import traceback; traceback.print_exc()
