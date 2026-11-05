
import sys, numpy as np
sys.path.insert(0, r"C:\Users\Lenovo\Documents\backtest-system\code")
import adxhma_strategy as M

print("=== THRESHOLD CONTROL: does the ADX gate add anything over a bare HMA cross? ===")
print("    zero cost, so only SIGNAL quality is measured. thr=0 = no ADX filter at all.")
print(f"    {'sym':<9}{'thr':>6}{'trades':>9}{'net%':>10}{'PF':>7}{'WR%':>6}{'avg win$':>10}{'avg loss$':>11}")
print("    "+"-"*70)
for s in ("BTCUSDT","ETHUSDT","SOLUSDT"):
    d = M.load(s, "15m")
    for thr in (0.0, 15.0, 25.0, 35.0, 50.0):
        P = M.params_for("custom", 15)
        P["adx_thr"] = thr
        r = M.simulate(d, P, 0.0, 0.0)
        st = M.stats(r["eq"], r["T"]); pf = M.pf_of(r["trades"])
        w = [t["pnl"] for t in r["trades"] if t["pnl"]>0]
        ls = [t["pnl"] for t in r["trades"] if t["pnl"]<=0]
        wr = 100*len(w)/max(len(r["trades"]),1)
        print(f"    {s:<9}{thr:>6.0f}{len(r['trades']):>9}{st['cum']:>+10.1f}{pf:>7.2f}"
              f"{wr:>5.0f}%{np.mean(w) if w else 0:>10.2f}{np.mean(ls) if ls else 0:>11.2f}")
    print("    "+"-"*66)

print()
print("=== BOTH-SIDES TEST: is there ANY directional information at all? ===")
print("    If the signal were informative, LONG trades and SHORT trades would differ")
print("    in mean return. Zero cost, so costs cannot mask it.")
print(f"    {'sym':<9}{'side':<7}{'n':>8}{'mean pnl$':>11}{'median':>10}{'PF':>7}{'hits%':>7}")
print("    "+"-"*62)
for s in ("BTCUSDT","ETHUSDT","SOLUSDT"):
    d = M.load(s,"15m")
    P = M.params_for("custom", 15)
    r = M.simulate(d, P, 0.0, 0.0)
    for side in ("L","S"):
        ts = [t["pnl"] for t in r["trades"] if t["side"]==side]
        if not ts: continue
        ts = np.array(ts)
        w = ts[ts>0].sum(); ls = abs(ts[ts<=0].sum())
        pf = w/ls if ls>0 else float("inf")
        print(f"    {s:<9}{side:<7}{len(ts):>8}{ts.mean():>11.3f}{np.median(ts):>10.3f}"
              f"{pf:>7.2f}{100*(ts>0).mean():>6.0f}%")
    print("    "+"-"*58)
