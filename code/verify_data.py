"""Verify sui_1m.json integrity: gaps, dupes, monotonic, OHLC sanity, vs 5m."""
import json, numpy as np, pandas as pd
from pathlib import Path

rows = json.loads(Path(r"C:\Users\Lenovo\Downloads\freqtrade\sui_1m.json").read_text())
df = pd.DataFrame(rows, columns=["t","o","h","l","c","v","ct","qv","n","tb","tq","ig"])
for c in ["o","h","l","c","v"]:
    df[c] = df[c].astype(float)
df["dt"] = pd.to_datetime(df["t"], unit="ms", utc=True)
df = df.sort_values("t").reset_index(drop=True)

print("rows:", len(df))
print("monotonic ts:", df["t"].is_monotonic_increasing)
print("dupes:", df["t"].duplicated().sum())
d = df["t"].diff().dropna()
print("step ms distinct:", sorted(d.unique())[:6], "... max:", d.max())
gaps = df[df["t"].diff() > 60000]
print("gaps >1m:", len(gaps))
if len(gaps):
    g = df.loc[gaps.index, ["dt"]].copy(); g["gap_bars"] = (gaps["t"].diff()/60000).fillna(0)
    print(g.head(20).to_string())

print("\nOHLC sanity violations:")
print("  h<l:", (df["h"] < df["l"]).sum())
print("  h<max(o,c):", (df["h"] < df[["o","c"]].max(axis=1)).sum())
print("  l>min(o,c):", (df["l"] > df[["o","c"]].min(axis=1)).sum())
print("  vol<0:", (df["v"] < 0).sum())
print("  zero-vol bars:", (df["v"] == 0).sum())
print("  ct != t+60000:", (df["ct"] != df["t"] + 60000).sum())

# cross-check vs 5m feather
f = pd.read_feather(r"C:\Users\Lenovo\Downloads\freqtrade\user_data\data\binance\futures\SUI_USDT_USDT-5m-futures.feather")
f["date"] = pd.to_datetime(f["date"], utc=True)
df5 = df.set_index("dt").resample("5min").agg({"o":"first","h":"max","l":"min","c":"last","v":"sum"}).dropna()
m = df5.join(f.set_index("date"), how="inner", lsuffix="_1m", rsuffix="_f")
print("\n5m overlap rows:", len(m))
for k in ["o","h","l","c"]:
    diff = (m[f"{k}_1m"] - m[f"{k}_f"]).abs()
    print(f"  {k} max abs diff: {diff.max():.8f}  (rel {diff.max()/m[f'{k}_f'].mean()*100:.5f}%)")
print("  vol rel diff (mean %):", ((m["v_1m"]-m["v_f"]).abs()/m["v_f"].replace(0,np.nan)).mean()*100)

# basic stats
print("\nprice:", df["c"].iloc[0], "->", df["c"].iloc[-1])
print("min low:", df["l"].min(), "max high:", df["h"].max())
print("total notional (quote vol):", df["qv"].astype(float).sum()/1e6, "M USDT")
