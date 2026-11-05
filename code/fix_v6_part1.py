import re

p = r"C:\Users\Lenovo\Downloads\ELLIOT WAVE ANALIZER\ew-quant-v6-draft.txt"
src = open(p, encoding="utf-8").read()
orig_len = len(src)

def rep(old, new, count=1):
    global src
    assert src.count(old) == count, f"count={src.count(old)} for: {old[:70]!r}"
    src = src.replace(old, new)

# 1. Global twoSided/modeClr right after inputs (before STATE section)
rep('// ═══════════ STATE ═══════════',
    'isPerp = str.contains(syminfo.ticker, ".P") or str.contains(syminfo.ticker, ":")\n'
    'twoSided = i_twoSided or isPerp\n'
    'modeClr = twoSided ? color.orange : #00E676\n'
    '\n'
    '// ═══════════ STATE ═══════════')

# 2. Drop bestSub assignments (undeclared, unused)
rep('        bestSub  := sDia\n', '')
rep('        bestSub  := sTri\n', '')
rep('        bestSub  := sFlt\n', '')

# 3. flatName/triName via captured sFlt/sTri
rep('            flatName = gSub != "" ? gSub : "Flat"\n'
    '            [cEB, cEL, cEH] = f_corrMark(sz - 4, sz - 1, flatName, i_cFlt, true)',
    '            flatName = sFlt != "" ? sFlt : "Flat"\n'
    '            [cEB, cEL, cEH] = f_corrMark(sz - 4, sz - 1, flatName, i_cFlt, true)')
rep('            triName = gSub != "" ? gSub : "Triangle"\n'
    '            [cEB, cEL, cEH] = f_corrMark(sz - 6, sz - 1, triName, i_cTri, true)',
    '            triName = sTri != "" ? sTri : "Triangle"\n'
    '            [cEB, cEL, cEH] = f_corrMark(sz - 6, sz - 1, triName, i_cTri, true)')

# 4. Remove local isPerp/twoSided (now global)
rep('    isPerp = str.contains(syminfo.ticker, ".P") or str.contains(syminfo.ticker, ":")\n'
    '    twoSided = i_twoSided or isPerp\n', '')

# 5. Reset signal globals at section start (avoid stale signals)
rep('    // ── Build limit plans: fib zone entry, ATR stop, R:R gate, invalidation ──',
    '    // ── Build limit plans: fib zone entry, ATR stop, R:R gate, invalidation ──\n'
    '    gSig := "HOLD"\n'
    '    gEnt := na\n'
    '    gStp := na\n'
    '    gTgt1 := na\n'
    '    gInv := na\n'
    '    gRR := na\n'
    '    gSellBot := na\n'
    '    gSellTop := na\n'
    '    gBuyBot := na\n'
    '    gBuyTop := na')

# 6. Parenthesize (A or B) ternaries
rep('zTop = bestType == 1 or bestType == 5 ? refHigh - waveRange * 0.5 : refLow',
    'zTop = (bestType == 1 or bestType == 5) ? refHigh - waveRange * 0.5 : refLow')
rep('zBot = bestType == 1 or bestType == 5 ? refHigh - waveRange * 0.618 : refLow - atrBuf',
    'zBot = (bestType == 1 or bestType == 5) ? refHigh - waveRange * 0.618 : refLow - atrBuf')
rep('tgt = bestType == 1 or bestType == 5 ? refHigh : refLow + waveRange * 0.618',
    'tgt = (bestType == 1 or bestType == 5) ? refHigh : refLow + waveRange * 0.618')
rep('zTop = bestType == 1 or bestType == 5 ? refLow + waveRange * 0.618 : refHigh',
    'zTop = (bestType == 1 or bestType == 5) ? refLow + waveRange * 0.618 : refHigh')
rep('zBot = bestType == 1 or bestType == 5 ? refLow + waveRange * 0.5 : refHigh - atrBuf',
    'zBot = (bestType == 1 or bestType == 5) ? refLow + waveRange * 0.5 : refHigh - atrBuf')
rep('tgt = bestType == 1 or bestType == 5 ? refLow : refHigh - waveRange * 0.618',
    'tgt = (bestType == 1 or bestType == 5) ? refLow : refHigh - waveRange * 0.618')

# 7. Fib tuple loop -> indexed (v6 has no tuple unpacking in for)
rep('            for [m, nm] in [[0.236, "23.6%"], [0.382, "38.2%"], [0.5, "50.0%"], [0.618, "61.8%"], [0.786, "78.6%"]]\n'
    '                lvl = refLow + rng * m',
    '            fibMs  = array.from(0.236, 0.382, 0.5, 0.618, 0.786)\n'
    '            fibNms = array.from("23.6%", "38.2%", "50.0%", "61.8%", "78.6%")\n'
    '            for fi = 0 to 4\n'
    '                lvl = refLow + rng * array.get(fibMs, fi)\n'
    '                nm = array.get(fibNms, fi)')
open(p, "w", encoding="utf-8").write(src)
print("part1 OK, delta:", len(src) - orig_len)
