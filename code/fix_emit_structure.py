p = r"C:\Users\Lenovo\trading-engines\quant-alert-engine\quant_alert_ui.py"
lines = open(p, encoding="utf-8").read().splitlines(keepends=True)

# 0-based: method block = lines 356..395 (comment+consts+def through winsound pass)
# orphaned emit_alert tail = lines 397..464 (outcome tagging .. _spawn_sender)
assert lines[356].strip().startswith("# Toast coalescing"), lines[356][:60]
assert lines[363].strip().startswith("def _toast_coalesced"), lines[363][:60]
assert lines[395].strip() == "pass", lines[395][:60]
assert "Outcome tagging" in lines[397], lines[397][:60]
assert "_spawn_sender(_post_bridge)" in lines[464], lines[464][:60]
assert lines[466].strip().startswith("def publish_snapshot"), lines[466][:60]

method = lines[356:396]
tail = lines[397:465]
rest_head = lines[:356]
rest_tail = lines[396:397] + lines[465:]  # blank line + publish_snapshot...
# new order: emit head + tail (reunified emit_alert), blank, method, blank, rest
assert rest_head[-2].strip() == "self._mark_fired(signal_id)", rest_head[-2][:60]
new = rest_head + tail + ["\n"] + method + rest_tail
open(p, "w", encoding="utf-8").write("".join(new))
print("restructure OK")
