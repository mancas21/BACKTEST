import re

src = r"C:\Users\Lenovo\Downloads\ELLIOT WAVE ANALIZER\ew-quant-v6-draft.txt"
lines = open(src, encoding="utf-8").read().splitlines()
kept = []
for l in lines:
    s = l.strip()
    if not s:
        continue
    if s.startswith("//"):
        continue
    kept.append(l)
out = "\n".join(kept) + "\n"
open(r"C:\Users\Lenovo\AppData\Local\Temp\opencode\ewq6_stripped.pine", "w", encoding="utf-8").write(out)
print("orig lines:", len(lines), "stripped lines:", len(kept))
print("stripped chars:", len(out), "KB:", round(len(out) / 1024, 1))
