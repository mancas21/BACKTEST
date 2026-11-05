#!/usr/bin/env python3
"""
x_spec_check.py — verify SPECS.md against the files it cites.

Doctrine: a number in a public recipe is a claim. Every numeric token in a
spec section (everything except its SOURCE line) must appear literally in the
file cited by SOURCE. Nothing may be invented; a failing check means the spec
is wrong, not the checker.

Usage: python code/x_spec_check.py
Exit codes: 0 all specs verified; 1 failures found.
"""
import io, os, re, sys, json

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPECS = os.path.join(REPO, "content", "specs.md")
NUM = re.compile(r"\d+(?:\.\d+)?")

def fail(msg):
    print("SPECCHECK: REFUSED —", msg)
    return 1

def main():
    text = io.open(SPECS, encoding="utf-8").read()
    sections = re.split(r"(?m)^## ", text)[1:]
    if not sections:
        return fail("no spec sections found")
    src_re = re.compile(r"^SOURCE:\s*(\S+)", re.M)
    failures, checked, token_total = [], 0, 0
    for sec in sections:
        lines = sec.splitlines()
        name = lines[0].strip()
        m = src_re.search(sec)
        if not m:
            failures.append(f"{name}: missing SOURCE line")
            continue
        src = m.group(1)
        src_path = os.path.join(REPO, src.split(":")[0])
        if not os.path.exists(src_path):
            failures.append(f"{name}: source file not found: {src}")
            continue
        src_text = io.open(src_path, encoding="utf-8", errors="ignore").read()
        body = sec[m.end():]          # everything after the SOURCE line
        tokens = NUM.findall(body)
        if not tokens:
            print(f"SKIP  {name} (no numeric tokens)")
            continue
        missing = []
        for tok in set(tokens):
            token_total += 1
            if tok not in src_text:
                missing.append(tok)
        if missing:
            failures.append(f"{name}: tokens not in {src}: {sorted(set(missing))}")
        else:
            checked += 1
    print(f"specs checked: {checked}/{len(sections)}; numeric tokens verified: {token_total}")
    if failures:
        for f in failures:
            print("REFUSED:", f)
        return 1
    print("SPECCHECK: OK — every numeric token in SPECS.md exists in its cited source.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
