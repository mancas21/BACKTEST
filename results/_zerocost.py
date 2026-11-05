
import sys, numpy as np
sys.path.insert(0, r"C:\Users\Lenovo\Documents\backtest-system\code")
import adxhma_strategy as M

print("=== COST ARITHMETIC SANITY: one hand-checked trade ===")
d = M.load("BTCUSDT","15m")
syms = ["BTCUSDT","ETHUSDT","SOLUSDT"]
print(f"{'sym':<9}{'qty':>14}{'entry':>12}{'exit':>12}{'gross$':>10}{'fees$':>9}{'net$':>10}")
for s in syms[:1]:
    dd = M.load(s,"15m")
    P = M.params_for("custom", 15)
    r = M.simulate({k:v[:20000] for k,v in dd.items()}, P, 0.0005, 0.0002)
    t = r["trades"][0]
    print(f"  first trade: side={t['side']} entry={t['entry']:.2f} exit={t['exit']:.2f} "
          f"pnl={t['pnl']:.4f} why={t['why']}")
print()

print("=== ZERO-COST vs REAL, all presets/timeframes (zero-cost isolates SIGNAL) ===")
print(f"{'cfg':<16}{'sym':<9}{'trades':>8}{'ZERO net%':>11}{'ZERO PF':>9}"
      f"{'ZERO DD%':>10}{'real net%':>11}{'real PF':>9}")
print("-"*90)
for pn, tf in (("custom","15m"),("custom","1h"),("scalp","15m"),("day","1h")):
    for s in syms:
        dd = M.load(s, tf)
        if dd is None: continue
        P = M.params_for(pn, {"15m":15,"1h":60}[tf])
        r0 = M.simulate(dd, P, 0.0, 0.0)
        st0 = M.stats(r0["eq"], r0["T"]); pf0 = M.pf_of(r0["trades"])
        r1 = M.simulate(dd, P, 0.0005, 0.0002)
        st1 = M.stats(r1["eq"], r1["T"]); pf1 = M.pf_of(r1["trades"])
        print(f"{pn+'@'+tf:<16}{s:<9}{len(r0['trades']):>8}{st0['cum']:>+11.1f}{pf0:>9.2f}"
              f"{st0['mdd']:>10.1f}{st1['cum']:>+11.1f}{pf1:>9.2f}")
    print("-"*90)
