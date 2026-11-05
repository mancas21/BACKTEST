#!/usr/bin/env python
"""Re-run taker-based strategies with corrected column name."""
import sys, os, json
sys.path.insert(0, os.path.join(r"C:\Users\Lenovo\Documents\backtest-system", "code"))
from cross_sectional_fast import *

ROOT = r"C:\Users\Lenovo\Documents\backtest-system"
DATA = os.path.join(ROOT, "data")

# Load 5m taker data
taker_syms = sorted([f.replace("_5m.csv","") for f in os.listdir(os.path.join(DATA,"binance_klines_5m_taker")) if f.endswith("_5m.csv")])
cm5, vm5, hm5, lm5, om5, tm5, ts5_list, idx5 = load_matrix(taker_syms, "5m", taker=True)
fm5, funding5 = load_funding_matrix(taker_syms, idx5)
ts5 = ts5_list
print(f"Loaded 5m taker: {len(taker_syms)} symbols, {len(ts5)} bars")
print(f"Taker matrix columns: {list(tm5.columns)}")
print(f"Taker matrix non-null count: {tm5.notna().sum().sum()}")

# Check that taker data is populated
print(f"Sample taker values: {tm5.iloc[100].to_dict()}")

results = []

for name, sfn, rebal, bpy in [("S14_TakerRatio", sig_taker_ratio, 12, 12*24*365),
                                ("S15_TakerDiv", sig_taker_div, 24, 12*24*365),
                                ("S16_TakerSurprise", sig_taker_surprise, 24, 12*24*365),
                                ("S21_Ensemble", sig_ensemble, 12, 12*24*365)]:
    print(f"\nComputing {name} signal...")
    try:
        scores = sfn(cm5, vm5, hm5, lm5, om5, tm5, fm5, funding5)
        print(f"  Score non-null: {scores.notna().sum().sum()}, shape: {scores.shape}")
        print(f"  Score sample (last row): {scores.iloc[-1].to_dict()}")
        print(f"  Running backtest...")
        m = backtest_fast(name, lambda c,v,h,l,o,t,f,fd: scores, cm5, vm5, hm5, lm5, om5, tm5, fm5, funding5, ts5, rebal, bpy)
        results.append(m)
        print(f"    ret={m['total_ret']}% dd={m['max_dd']}% sharpe={m['sharpe']} oos={m['oos_ret']}% n_rebal={m['n_rebal']}")
    except Exception as e:
        print(f"    ERROR: {e}")
        import traceback; traceback.print_exc()

# Save
out_path = os.path.join(ROOT, "results", "taker_strats_results.json")
with open(out_path, "w") as f:
    json.dump(results, f, indent=2, default=str)
print(f"\nSaved to {out_path}")

# Print summary
print("\n" + "="*60)
print("TAKER STRATEGY RESULTS")
print("="*60)
for m in results:
    print(f"  {m['strategy']}: ret={m['total_ret']}% dd={m['max_dd']}% sharpe={m['sharpe']} oos={m['oos_ret']}% rebal={m['n_rebal']}")