p = r"C:\Users\Lenovo\Downloads\ELLIOT WAVE ANALIZER\ew-quant-v6-draft.txt"
lines = open(p, encoding="utf-8").read().splitlines(keepends=True)

# 1. alertconditions to column 0 (Pine requires global scope)
for i, l in enumerate(lines):
    if l.strip().startswith("alertcondition(") and l.startswith("    "):
        lines[i] = l[4:]

# 2. delete trailing broken SCORING block (from its header to EOF)
start = next(i for i, l in enumerate(lines) if "SCORING (pattern score" in l)
del lines[start:]

# 3. insert real scoring INSIDE main, right before the Alerts section
anchor = "    // ── Alerts: one condition per event ──\n"
assert anchor in lines, "alerts anchor missing"
scoring = [
    "    // ── Pattern score (NOT a probability — Rule 3) ──\n",
    "    score = 0.0\n",
    "    if expectUp\n",
    "        score += 3.0\n",
    "        if gScore >= 70\n",
    "            score += 1.0\n",
    "    if expectDown\n",
    "        score -= 3.0\n",
    "        if gScore >= 70\n",
    "            score -= 1.0\n",
    "    if close > ema20 and ema20 > ema50 and ema50 > ema200\n",
    "        score += 2.0\n",
    "    else if close > ema50 and ema50 > ema200\n",
    "        score += 1.0\n",
    "    else if close < ema50 and ema50 < ema200\n",
    "        score -= 1.0\n",
    "    else if close < ema20 and ema20 < ema50 and ema50 < ema200\n",
    "        score -= 2.0\n",
    "    if rsiVal < 30\n",
    "        score += 2.0\n",
    "    else if rsiVal < 40\n",
    "        score += 1.0\n",
    "    else if rsiVal > 70\n",
    "        score -= 2.0\n",
    "    else if rsiVal > 60\n",
    "        score -= 1.0\n",
    "    if nz(macdLine) > nz(macdSignal) and nz(macdHist) > 0\n",
    "        score += 1.0\n",
    "    else if nz(macdLine) > nz(macdSignal) and nz(macdHist) > nz(macdHist[1])\n",
    "        score += 0.5\n",
    "    if nz(macdLine) < nz(macdSignal) and nz(macdHist) < 0\n",
    "        score -= 1.0\n",
    "    else if nz(macdLine) < nz(macdSignal) and nz(macdHist) < nz(macdHist[1])\n",
    "        score -= 0.5\n",
    "    if nz(adxVal) > 25\n",
    "        score := score * 1.15\n",
    "    if tfAlign >= 4\n",
    "        score += 2.5\n",
    "    else if tfAlign >= 2\n",
    "        score += 1.5\n",
    "    else if tfAlign <= -4\n",
    "        score -= 2.5\n",
    "    else if tfAlign <= -2\n",
    "        score -= 1.5\n",
    "    if nz(wRsi) < 30\n",
    "        score += 1.5\n",
    "    else if nz(wRsi) < 40\n",
    "        score += 0.5\n",
    "    if nz(wRsi) > 70\n",
    "        score -= 1.5\n",
    "    else if nz(wRsi) > 60\n",
    "        score -= 0.5\n",
    "    gScore := score\n",
    "    gRec := twoSided ? (score >= 5.0 ? \"STRONG BUY\" : score >= 2.0 ? \"BUY\" : score >= -2.0 ? \"HOLD\" : score >= -5.0 ? \"SELL\" : \"STRONG SELL\") : (score >= 5.0 ? \"STRONG BUY\" : score >= 2.0 ? \"BUY\" : score >= -2.0 ? \"HOLD\" : \"ACCUMULATE\")\n",
    "\n",
]
idx = lines.index(anchor)
lines[idx:idx] = scoring

# 4. panel header: real twoSided/modeClr
old_hdr = '    table.cell(pnl, 1, r, twoSidedQ + "  ", text_color=modeClrQ, text_size=size.small, text_halign=text.align_right, bgcolor=hdrBg)\n'
assert old_hdr in lines, "panel header missing"
lines[lines.index(old_hdr)] = '    table.cell(pnl, 1, r, (twoSided ? "2-SIDED" : "SPOT") + "  ", text_color=modeClr, text_size=size.small, text_halign=text.align_right, bgcolor=hdrBg)\n'

open(p, "w", encoding="utf-8").write("".join(lines))
print("part2 OK, total lines:", len(lines))
