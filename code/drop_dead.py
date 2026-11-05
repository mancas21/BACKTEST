p = r"C:\Users\Lenovo\trading-engines\quant-alert-engine\quant_alert_engine.py"
lines = open(p, encoding="utf-8").read().splitlines(keepends=True)
start = next(i for i, l in enumerate(lines) if l.startswith("    def _build_snapshot(self"))
end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("    def _calc_bias"))
dead_prefixes = ("        big_trade =", "        big_side =",
                 "        bar_idx =", "        bid_vol =", "        ask_vol =")
removed = 0
for i in range(end - 1, start - 1, -1):
    if lines[i].startswith(dead_prefixes):
        del lines[i]
        removed += 1
open(p, "w", encoding="utf-8").write("".join(lines))
print("dead assignments removed:", removed)
