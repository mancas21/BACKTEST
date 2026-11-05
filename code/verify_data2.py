import json, numpy as np, pandas as pd
from pathlib import Path

rows = json.loads(Path(r"C:\Users\Lenovo\Downloads\freqtrade\sui_1m.json").read_text())
df = pd.DataFrame(rows, columns=["t","o","h","l","c","v","ct","qv","n","tb","tq","ig"])
for c in ["o","h","l","c","v"]:
    df[c] = df[c].astype(float)
df["dt"] = pd.to_datetime(df["t"], unit="ms", utc=True)
df = df.sort_values("t").reset_index(drop=True)
print("ct offset (ms, mode):", (df["ct"] - df["t"]).mode().tolist())

f = pd.read_feather(r"C:\Users\Lenovo\Downloads\freqtrade\user_data\data\binance\futures\SUI_USDT_USDT-5m-futures.feather")
f["date"] = pd.to_datetime(f["date"], utc=True)
df5 = df.set_index("dt").resample("5min").agg({"o":"first","h":"max","l":"min","c":"last","v":"sum"}).dropna()
g = f.set_index("date").rename(columns={"open":"o_f","high":"h_f","low":"l_f","close":"c_f","volume":"v_f"})
m = df5.join(g, how="inner")
m.columns = [c.replace("o","o_1m") if c=="o" else c for c in m.columns]
m = m.rename(columns={"o":"o_1m","h":"h_1m","l":"l_1m","c":"c_1m","v":"v_1m"})
print("overlap rows:", len(m))
for k in ["o","h","l","c"]:
    diff = (m[f"{k}_1m"] - m[f"{k}_f"]).abs()
    print(f"  {k}: max abs diff={diff.max():.8f}  mean rel={((diff/m[f'{k}_f']).mean()*100):.6f}%")
vd = ((m["v_1m"]-m["v_f"]).abs()/m["v_f"].replace(0,np.nan))
print("  vol: mean rel diff %", round(vd.mean()*100,4), " max", round(vd.max()*100,3))

print("\ncross-source conclusion: 1m resampled vs Binance 5m OHLCV match exactly?",
      all((m[f"{k}_1m"]-m[f"{k}_f"]).abs().max() < 1e-9 for k in ["o","h","l","c"]))
