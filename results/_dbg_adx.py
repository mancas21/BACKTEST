
import sys, numpy as np
sys.path.insert(0, r"C:\Users\Lenovo\Documents\backtest-system\code")
import adxhma_strategy as M
d = M.load("BTCUSDT","15m"); d = {k:v[:60000] for k,v in d.items()}
c,h,l = d["c"], d["h"], d["l"]
for nm in ("custom","scalp","day"):
    P = M.params_for(nm, 15)
    H = M.hma(c, P["hma_len"]); diP,diM,adx = M.dmi_pine(h,l,c,P["di_len"],P["adx_smooth"])
    A = M.atr_pine(h,l,c,14)
    thr = P["adx_thr"]
    pa = (~np.isnan(H)) & (c > H); pb = (~np.isnan(H)) & (c < H)
    ao = (~np.isnan(adx)) & (adx >= thr)
    ls = pa & ao
    lt = np.zeros(len(c),bool); lt[0]=bool(ls[0]); lt[1:]=ls[1:] & ~ls[:-1]
    print(f"{nm:<7} hma_len={P['hma_len']:<3} thr={thr:<5} use_sl={P['use_sl']} "
          f"sizing={P['sizing']:<8} risk={P['risk_pct']} maxlev={P['max_lev']}")
    print(f"        H non-nan={int((~np.isnan(H)).sum())}/{len(c)}  adx non-nan={int((~np.isnan(adx)).sum())}  "
          f"atr non-nan={int((~np.isnan(A)).sum())}")
    print(f"        price_above={int(pa.sum())} adx_ok={int(ao.sum())} longState={int(ls.sum())} longTrig={int(lt.sum())}")
    # size_qty on a sample bar
    i = int(np.argmax(lt)) if lt.sum() else 100
    eq = 10000.0
    q_fixed = eq*P["pct_eq"]/100.0/c[i]
    sd = P["sl_mult"]*A[i]
    q_risk = eq*P["risk_pct"]/100.0/sd if sd>0 else float("nan")
    q_cap = eq*P["max_lev"]/c[i]
    raw = q_risk if (P["sizing"]=="atr_risk" and P["use_sl"]) else q_fixed
    print(f"        sample i={i}: q_fixed={q_fixed:.6f} sd={sd:.4f} q_risk={q_risk} q_cap={q_cap:.6f} raw={raw} -> min={min(raw,q_cap)}")
    r = M.simulate(d, P, 0.0005, 0.0002)
    print(f"        SIMULATE -> trades={len(r['trades'])}  final eq={r['eq'][-1]:.2f}")
    print()
