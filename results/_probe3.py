
import sys, numpy as np
sys.path.insert(0, r"C:\Users\Lenovo\Documents\backtest-system\code")
import multipair3_audit as M
btc = M.load("BTCUSDT"); b4 = M.resample4(btc)
print("lens:", {k: len(v) for k,v in b4.items()})
idx = np.searchsorted(b4["t"], btc["t"], side="right")-1
idxc = np.clip(idx, 0, len(b4["t"])-1)
print("idx max", idxc.max(), "gate size", len(b4["t"]))
print("in bounds:", idxc.max() < len(b4["t"]))
print("LOOKAHEAD bars:", int((b4["t"][idxc] > btc["t"]).sum()))
print("4h spacing (h):", np.unique(np.diff(b4["t"])//3600000)[:5])
# open must equal the first 1h open of each bucket
o_ref = btc["o"][:len(b4["c"])*4].reshape(-1,4)[:,0]
print("open matches:", np.allclose(b4["o"], o_ref))
