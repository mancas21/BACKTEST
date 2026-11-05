
import sys
sys.path.insert(0, r"C:\Users\Lenovo\Documents\backtest-system\code")
import numpy as np, adxhma_strategy as M
print("--- primitive self-test ---")
M.selftest()
print()
print("--- smoke: BTC 15m, custom preset, first 60000 bars ---")
d = M.load("BTCUSDT", "15m")
print("full bars:", len(d["c"]))
d = {k: v[:60000] for k, v in d.items()}
P = M.params_for("custom", 15)
r = M.simulate(d, P, 0.0005, 0.0002)
st = M.stats(r["eq"], r["T"])
print("trades", len(r["trades"]), "net %.2f%%" % st["cum"], "DD %.1f%%" % st["mdd"],
      "PF %.2f" % M.pf_of(r["trades"]))
buyhold = (d["c"][-1]/d["c"][0]-1)*100
print("buy&hold %.1f%%" % buyhold)
ws = [t for t in r["trades"] if t["why"]=="SL"]; tp=[t for t in r["trades"] if t["why"]=="TP"]
print("by exit:", {w: sum(1 for t in r["trades"] if t["why"]==w) for w in set(t["why"] for t in r["trades"])})
