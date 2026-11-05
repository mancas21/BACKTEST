"""Fetch 1m SUIUSDT perp bars from Binance Futures REST (UTC, paginated)."""
import json, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

SYM = "SUIUSDT"
OUT = Path(r"C:\Users\Lenovo\Downloads\freqtrade\sui_1m.json")
BASE = "https://fapi.binance.com/fapi/v1/klines"

def ms(s):
    return int(datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)

def get(start_ms, end_ms):
    url = f"{BASE}?symbol={SYM}&interval=1m&startTime={start_ms}&endTime={end_ms}&limit=1500"
    req = urllib.request.Request(url, headers={"User-Agent": "grid-research/1.0"})
    return json.load(urllib.request.urlopen(req, timeout=30))

start, end = ms("2026-08-20"), ms("2026-09-26")
rows, cur, guard = [], start, 0
while cur < end and guard < 200:
    guard += 1
    try:
        batch = get(cur, end)
    except Exception as e:
        print("ERR", type(e).__name__, e); time.sleep(3); continue
    if not batch:
        cur += 1500 * 60 * 1000; continue
    rows += batch
    last = batch[-1][0]
    cur = last + 60 * 1000
    time.sleep(0.12)

seen = {r[0]: r for r in rows}
rows = [seen[k] for k in sorted(seen) if k <= end]
OUT.write_text(json.dumps(rows))
if rows:
    print("bars:", len(rows))
    print("from", datetime.fromtimestamp(rows[0][0]/1000, timezone.utc))
    print("to  ", datetime.fromtimestamp(rows[-1][0]/1000, timezone.utc))
    print("price range:", min(float(r[3]) for r in rows), "-", max(float(r[2]) for r in rows))
else:
    print("NO BARS")
