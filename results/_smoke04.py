
import sys, os, numpy as np
sys.path.insert(0, r"C:\Users\Lenovo\Downloads\SCALPING INDICATORS STATEGY\python")
sys.path.insert(0, r"C:\Users\Lenovo\Documents\backtest-system\code")
from scalp_ind.core.vwap import session_vwap_bands, utc_day_session_id
import ind04_study as S
d = S.load1m("SOLUSDT", limit=200000)
sid = utc_day_session_id(d["t"])
b = session_vwap_bands(d["h"], d["l"], d["c"], d["v"], d["t"])
print("result fields:", [f for f in b.__dataclass_fields__])
ob, rv = S.alerts_from(b, d["c"])
print("bars", len(d["c"]), "sessions", len(np.unique(sid)))
print("out_of_band", int(ob.sum()), "revert_inside", int(rv.sum()))
first = np.zeros(len(sid), bool); first[0]=True; first[1:] = sid[1:]!=sid[:-1]
print("first-of-session bars:", int(first.sum()))
print("signals ON first bars:", int((ob&first).sum()))
# the sigma=0 claim
print("sigma==0 count:", int((b.sigma==0).sum()))
i0 = np.where(first)[0][:3]
for i in i0:
    print(f"  bar {i}: close={d['c'][i]:.4f} vwap={b.vwap[i]:.4f} u2={b.upper2[i]:.4f} l2={b.lower2[i]:.4f} sigma={b.sigma[i]}")
