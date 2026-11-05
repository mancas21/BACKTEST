
import sys, numpy as np
sys.path.insert(0, r"C:\Users\Lenovo\Downloads\SCALPING INDICATORS STATEGY\python")
sys.path.insert(0, r"C:\Users\Lenovo\Documents\backtest-system\code")
from scalp_ind.core.sweep import liquidity_sweep
from scalp_ind.core.squeeze import squeeze_burst
import ind0607_study as M
d = M.load1m("SOLUSDT", limit=300000)
sw = liquidity_sweep(d["h"], d["l"], d["c"], d["v"], 14, 96, 2.0)
sq = squeeze_burst(d["h"], d["l"], d["c"], d["v"], 20, 2.0, 20, 1.5, 96, 2.0)
print("sweep bullish", int(sw.bullish.sum()), "bearish", int(sw.bearish.sum()))
print("squeeze release", int(sq.release.sum()), "burst", int(sq.burst.sum()))
print("release_side uniq", np.unique(sq.release_side))
print("sides: long", int((sq.release&(sq.release_side>0)).sum()),
      "short", int((sq.release&(sq.release_side<0)).sum()))
a = M.atr(d["h"], d["l"], d["c"], 14)
print("ATR14 bps median", float(np.median(a/d["c"]))*1e4)
import pandas as pd
v = pd.Series(d["v"]); med=v.rolling(96).median(); mad=(v-med).abs().rolling(96).median()
vz = ((v-med)/np.where(mad>0,1.4826*mad,np.nan)).to_numpy()
print("vol z >= 2 count", int(np.nansum(vz>=2.0)))
