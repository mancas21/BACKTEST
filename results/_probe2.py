
import sys, numpy as np
sys.path.insert(0, r"C:\Users\Lenovo\Documents\backtest-system\code")
import multipair3_audit as M
btc = M.load("BTCUSDT")
b4 = M.resample4(btc)
print("1h len", len(btc["c"]), "-> 4h len", len(b4["c"]), "ratio", len(btc["c"])/max(len(b4["c"]),1))
e50 = M.ema(b4["c"], 50)
print("gate4 len", len(e50), " b4 len", len(b4["c"]))
print("SAME?", len(e50)==len(b4["c"]))
idx = np.searchsorted(b4["t"], btc["t"], side="right")-1
idxc = np.clip(idx, 0, len(b4["t"])-1)
print("idx clipped max", idxc.max(), "vs gate4 size", len(e50))
print("LOOKAHEAD:", int((b4["t"][idxc] > btc["t"]).sum()))
