
import sys, numpy as np
sys.path.insert(0, r"C:\Users\Lenovo\Documents\backtest-system\code")
import multipair3_audit as M
btc = M.load("BTCUSDT"); b4 = M.resample4(btc)
idx = np.searchsorted(b4["t"], btc["t"], side="right") - 1
idx = np.clip(idx, 0, len(b4["t"])-1)
print("1h bars", len(btc["t"]), "4h bars", len(b4["t"]))
print("idx range", idx.min(), idx.max(), "in bounds:", idx.max() < len(b4["t"]))
print("monotone:", bool(np.all(np.diff(idx) >= 0)))
# the mapped 4h bar must never be in the FUTURE relative to its 1h bar
fut = (b4["t"][idx] > btc["t"])
print("lookahead bars (4h bar newer than its 1h bar):", int(fut.sum()))
