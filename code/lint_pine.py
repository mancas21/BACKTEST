import re

p = r"C:\Users\Lenovo\Downloads\ELLIOT WAVE ANALIZER\ew-quant-v6-draft.txt"
lines = open(p, encoding="utf-8").read().splitlines()

print("== 1. tabs ==")
bad = [(i + 1, "TAB") for i, l in enumerate(lines) if "\t" in l]
print("issues:", bad if bad else "none")
print("(NOTE: // comments are LEGAL Pine — not checked)")

print("== 2. indentation multiples of 4 ==")
bad_ind = [(i + 1, repr(l[:12])) for i, l in enumerate(lines)
           if l.strip() and (len(l) - len(l.lstrip(" "))) % 4 != 0]
print("issues:", bad_ind[:10] if bad_ind else "none")

print("== 3. := without prior declaration (new-code regions) ==")
# collect declarations: `name =`, `bool/float/int/string/color name =`, function params, for-loop vars
declared = set()
builtin_funcs = {"nz", "na", "bar_index", "close", "open", "high", "low", "volume",
                 "time", "syminfo", "barstate", "timeframe", "chart", "strategy"}
for i, l in enumerate(lines):
    s = l.strip()
    m = re.match(r"^(?:(bool|float|int|string|color)\s+)?([A-Za-z_]\w*)\s*=(?![=>])", s)
    if m and not s.startswith(("if ", "for ", "while ", "switch ")):
        declared.add(m.group(2))
    m2 = re.match(r"^for\s+([A-Za-z_]\w*)\s*=", s)
    if m2:
        declared.add(m2.group(1))
# function names + params
for i, l in enumerate(lines):
    m = re.match(r"^(\w+)\(([^)]*)\)\s*=>$", l.strip())
    if m:
        declared.add(m.group(1))
        for prm in m.group(2).split(","):
            parts = prm.strip().split()
            if parts and re.match(r"^[A-Za-z_]\w*$", parts[-1]):
                declared.add(parts[-1])
# check := targets
issues = []
for i, l in enumerate(lines):
    for m in re.finditer(r"([A-Za-z_]\w*)\s*:=", l):
        if m.group(1) not in declared:
            issues.append((i + 1, m.group(1)))
print("undeclared := targets:", issues if issues else "none")

print("== 4. inputs referenced vs defined ==")
used_inputs = set(re.findall(r"i_[A-Za-z_]\w*", "\n".join(lines)))
defined_inputs = set(re.findall(r"(i_[A-Za-z_]\w*)\s*=\s*input\.", "\n".join(lines)))
print("used-not-defined:", used_inputs - defined_inputs or "none")
