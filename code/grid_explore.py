import json, numpy as np, pandas as pd
from pathlib import Path

rows = json.loads(Path(r"C:\Users\Lenovo\Downloads\freqtrade\sui_1m.json").read_text())
df = pd.DataFrame(rows, columns=["t","o","h","l","c","v","ct","qv","n","tb","tq","ig"])
for col in ["o","h","l","c","v"]:
    df[col] = df[col].astype(float)
df["date"] = pd.to_datetime(df["t"], unit="ms", utc=True)
df = df.set_index("date")

print("=== LAST PRICE / QUANTILES ===")
print("last close:", df["c"].iloc[-1])
for q in [0.01, 0.05, 0.10, 0.25, 0.5, 0.75, 0.90, 0.95, 0.99]:
    print(f"  q{q:>4}: {df['c'].quantile(q):.4f}")

print("\n=== LAST 24H ===")
d24 = df[df.index >= df.index.max() - pd.Timedelta(hours=24)]
print(f"  close min/max: {d24['c'].min():.4f} / {d24['c'].max():.4f}")
print(f"  last: {d24['c'].iloc[-1]:.4f}")

print("\n=== LAST 72H ===")
d72 = df[df.index >= df.index.max() - pd.Timedelta(hours=72)]
print(f"  close min/max: {d72['c'].min():.4f} / {d72['c'].max():.4f}")

print("\n=== 5D ===")
d5 = df[df.index >= df.index.max() - pd.Timedelta(days=5)]
print(f"  close min/max: {d5['c'].min():.4f} / {d5['c'].max():.4f}")

print("\n=== DAILY OHLC (last 14) ===")
dd = df.resample("1D").agg({"o":"first","h":"max","l":"min","c":"last"})
print(dd.tail(14).round(4).to_string())

print("\n=== ATR(1m 60) last ===")
tr = np.maximum(df["h"]-df["l"], np.maximum((df["h"]-df["c"].shift()).abs(), (df["l"]-df["c"].shift()).abs()))
print(f"  ATR60 1m: {tr.rolling(60).mean().iloc[-1]:.5f}")
print(f"  ATR 5m-equiv: {tr.rolling(300).mean().iloc[-1]:.5f}")
