p = r"C:\Users\Lenovo\Documents\backtest-system\code\_nt_parity.py"
lines = open(p).read().splitlines()
out = []
for ln in lines:
    out.append(ln)
    if ln.strip() == 'sell = sig["sell"].to_numpy(bool)':
        out.append('    print("DEBUG signals: buy=%d sell=%d exl=%d exs=%d" % (int(buy.sum()), int(sell.sum()), int(exl.sum()), int(exs.sum())))')
open(p, "w").write("\n".join(out) + "\n")
print("done")
'