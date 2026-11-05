p = r"C:\Users\Lenovo\Documents\backtest-system\code\_nt_smoke.py"
lines = open(p).read().splitlines()
while lines and lines[-1].strip() in ("", "'"):
    lines.pop()
open(p, "w").write("\n".join(lines) + "\n")
print("lines:", len(lines))
'