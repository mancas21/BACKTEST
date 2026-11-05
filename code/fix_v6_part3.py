p = r"C:\Users\Lenovo\Downloads\ELLIOT WAVE ANALIZER\ew-quant-v6-draft.txt"
src = open(p, encoding="utf-8").read()


def rep(old, new, count=1):
    global src
    assert src.count(old) == count, f"count={src.count(old)} for: {old[:70]!r}"
    src = src.replace(old, new)


# FIX 1: restore dropped txtAlpha definition
rep("        lnAlpha = isPrimary ? 40 : 65\n",
    "        lnAlpha = isPrimary ? 40 : 65\n"
    "        txtAlpha = isPrimary ? 15 : 45\n")

# FIX 2: global phase tag (panel cannot see block-local bestType)
rep('var int    gPhase   = 0\n',
    'var int    gPhase   = 0\n'
    'var string gPhaseTag = ""\n')

# FIX 3: set tag alongside phase mapping
rep("""    if bestType == 1
        gPhase := 5
    else if bestType == 2
        gPhase := 3
    else if bestType == 3
        gPhase := 3
    else if bestType == 4
        gPhase := 5
    else if bestType == 5
        gPhase := 5
    else
        gPhase := 0""",
    """    if bestType == 1
        gPhase := 5
        gPhaseTag := "5-done"
    else if bestType == 2
        gPhase := 3
        gPhaseTag := "C-done"
    else if bestType == 3
        gPhase := 3
        gPhaseTag := "C-done"
    else if bestType == 4
        gPhase := 5
        gPhaseTag := "E-watch"
    else if bestType == 5
        gPhase := 5
        gPhaseTag := "5-done"
    else
        gPhase := 0
        gPhaseTag := ""
    if gPhase == 0
        gPhaseTag := "—""")

# FIX 4: panel uses the global tag
rep('    phaseStr = gPhase > 0 ? str.tostring(gPhase) + (bestType == 1 ? "-done" : bestType == 2 or bestType == 3 ? "-done" : "-watch") : "—"',
    '    phaseStr = gPhase > 0 ? str.tostring(gPhase) + gPhaseTag : "—"')

open(p, "w", encoding="utf-8").write(src)
print("fixes applied OK")
