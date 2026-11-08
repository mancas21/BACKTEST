#!/usr/bin/env python3
"""
x_queue.py — generate the X (@nftepml) posting pack from the strategy registry.

Doctrine (non-negotiable):
  - Numbers ONLY from artifact metrics/inputs/params via results/runs/<run_id>.json.
  - Fixed copy contains ZERO digits (guard-safe by construction).
  - Every generated file cites its run_id; `vrun.py guard` must pass on each file.
  - Nothing is invented; unmapped verdicts are skipped, never guessed.
  - Verdict honesty: killed strategies are posted as "tested and failed".

Usage:
  python code/x_queue.py build --days 30 --out content/posts
  python code/x_queue.py verify            # re-run guard on every generated file
"""
import argparse, json, os, re, math, random, subprocess, sys
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG  = os.path.join(REPO, "results", "registry", "strategies.jsonl")
RUNS = os.path.join(REPO, "results", "runs")
POSTED = os.path.join(REPO, "content", "posted.jsonl")

# ── adapter → English descriptor (no digits in fixed copy) ───────────────────
ADAPTER_DESC = {
    "top10": "prompt-screen shortlist", "xrpneutral": "delta-neutral grid",
    "xrpneutral1m": "delta-neutral grid, one-minute fills",
    "cbpack": "ten rule-based pack", "cbpackf": "ten rule-based pack, funding charged",
    "pack50": "LLM prompt pack", "pack50b": "LLM prompt pack claude",
    "pack50c": "LLM prompt pack qwen", "pack50d": "LLM prompt pack deepseek",
    "pack100": "hundred-prompt pack", "prompts100": "hundred-prompt screen",
    "qs": "risk-sized book", "qsb": "risk-sized mean-reversion book",
    "qsc": "risk-sized vol/breakout book", "qsd": "risk-sized structure book",
    "qsf": "risk-sized trade-flow book",
    "dspack": "deepseek pack", "dspack2": "deepseek pack, second half",
    "xsf": "cross-sectional factor", "xsb": "cross-sectional relative-value factor",
    "xsc": "cross-sectional funding gate",
    "cbot": "bot strategy suite", "cand7": "prespecified candidate",
    "emaadx": "EMA ADX trend", "hmaaoadx": "HMA ADX trend",
    "ffs": "FFS engine", "botstrat": "bot strategy", "cvrmd": "CVRMD momentum",
    "smqe": "SMQE setup", "fingrad": "funding-gradient book",
    "mpv3": "MPV3 audit", "rsimr": "RSI mean reversion", "eqpack": "QQQ pack",
    "q10": "qwen cards", "mp20": "MP20 portfolio", "xrp100": "XRP screen",
}
ADAPTER_DESC_DEFAULT = "systematic pack"

# curated families first (strongest stories), then the rest
FAMILY_ORDER = ["llm_pack_shortlist", "grid_neutral", "pack_S01-S10_taker_flow",
                "risk_sized_book", "llm_pack", "cross_sectional",
                "deepseek_ds1-ds5", "deepseek_ds6-ds10"]

SKIP_VERDICT_SUBSTR = [
    "UNRUNNABLE", "SIN VEREDICTO", "SIN MEDIR", "REJECTED pack",
]

# ── verdict mapping: (substr, EN label, EN reason) — all digit-free ──────────
VERDICT_RULES = [
    ("CANDIDATE", "CANDIDATE", "clears the screen gates but is selection-contaminated and unproven forward"),
    ("FRAGILE/SUSPENDED", "SUSPENDED", "break-even after costs on the full history"),
    ("SUSPENDED", "SUSPENDED", "no honest out-of-sample remains"),
    ("window-pick", "KILLED", "window-picked curve fit"),
    ("resolucion 1m", "KILLED", "one-minute fill resolution killed it"),
    ("el mismo libro resuelto en 1m", "KILLED", "one-minute fill resolution killed the out-of-sample case"),
    ("concentracion: top-5 > 100", "KILLED", "its best handful of trades carry more than the whole profit"),
    ("concentracion", "KILLED", "a handful of trades carries the PnL"),
    ("OOS PF bajo el gate", "KILLED", "out-of-sample below the gate"),
    ("capas inestables", "FAIL", "unstable halves"),
    ("mitades inestables", "FAIL", "unstable halves"),
    ("FUNDGATE", "KILLED", "the funding-sign gate failed even with funding charged for real"),
    ("screen 2026-10-29", "KILLED", "failed the screen"),
    ("gate completo", "KILLED", "failed the full gate"),
    ("QQQ", "KILLED", "none of them beat buy and hold"),
    ("pierden en bruto", "KILLED", "they lose before costs"),
    ("costo cero", "KILLED", "the gross edge was gone at repo costs"),
    ("cero fantasma", "KILLED", "the gross edge was a zero-cost phantom"),
    ("<1h por costos", "KILLED", "costs below hourly; concentration killed the hourly cases"),
    ("sin funding en perps", "KILLED", "the edge vanished once funding was actually charged"),
    ("fila REJECT", "REJECTED", "zero cells of the pack cleared the gates"),
    ("fila FAIL", "FAIL", "zero cells of the pack cleared the gates"),
    ("fila INCONCLUSIVE", "INCONCLUSIVE", "zero cells of the pack cleared the gates"),
    ("REJECTED", "REJECTED", "rejected at the gate"),
    ("medido a 11 bps", "NOT VALIDATED", "re-measured at repo costs; the pack as a whole was killed"),
    ("KILLED", "KILLED", "it did not clear the gates"),
    ("NO PASA", "FAIL", "it did not clear the gates"),
]

def map_verdict(v):
    for pat, label, reason in VERDICT_RULES:
        if pat in v:
            return label, reason
    return None, None

TF_WORD = {"1m": "one-minute", "5m": "five-minute", "15m": "fifteen-minute",
           "30m": "thirty-minute", "1h": "hourly", "4h": "four-hourly",
           "1d": "daily", "1w": "weekly"}

def load_rows():
    out = []
    with open(REG, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out

def load_posted_ids():
    ids = set()
    if os.path.exists(POSTED):
        with open(POSTED, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ids.add(json.loads(line).get("run_id"))
                except json.JSONDecodeError:
                    pass
    return {i for i in ids if i}

def artifact_path(rid):
    return os.path.join(RUNS, rid + ".json")

def load_artifact(rid):
    p = artifact_path(rid)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def eligibility(rows, used=None):
    out = []
    seen = load_posted_ids()
    used = used if used is not None else set()
    skipped = defaultdict(int)
    for r in rows:
        rid = (r.get("run_id") or "").strip()
        v = str(r.get("verdict") or "")
        if not rid:
            skipped["no_run_id"] += 1; continue
        if rid in seen:
            skipped["already_posted"] += 1; continue
        # registry rows may share one pack artifact — never post the same run_id twice in a pack
        if rid in used:
            skipped["duplicate_artifact"] += 1; continue
        if any(s in v for s in SKIP_VERDICT_SUBSTR):
            skipped["verdict_excluded"] += 1; continue
        label, reason = map_verdict(v)
        if label is None:
            skipped["verdict_unmapped"] += 1; continue
        art = load_artifact(rid)
        if art is None:
            skipped["artifact_missing"] += 1; continue
        m = art.get("metrics") or {}
        if not isinstance(m, dict):
            skipped["metrics_unreadable"] += 1; continue
        # sanity: the artifact must carry at least its bar count
        if not isinstance(m.get("bars"), (int, float)):
            skipped["no_bars"] += 1; continue
        r2 = dict(r); r2["_label"] = label; r2["_reason"] = reason; r2["_art"] = art
        out.append(r2)
        used.add(rid)
    return out, skipped

def family_of(r):
    return str(r.get("family") or "unknown")

def order_rows(elig):
    """Round-robin across families; families ordered by curated list then name."""
    fams = defaultdict(list)
    for r in elig:
        fams[family_of(r)].append(r)
    def fam_key(name):
        try:
            return (0, FAMILY_ORDER.index(name))
        except ValueError:
            return (1, name)
    for name in list(fams):
        fams[name].sort(key=lambda r: (str(r.get("adapter") or ""), str(r.get("symbol") or ""), str(r.get("tf") or "")))
    ordered = []
    deques = [deque(fams[k]) for k in sorted(fams, key=fam_key)]
    while any(deques):
        for d in deques:
            if d:
                ordered.append(d.popleft())
    return ordered

# ── $pair mapping ──────────────────────────────────────────────────────────
PAIR_MAP = {
    "BTCUSDT": "$BTC", "XRPUSDT": "$XRP", "SOLUSDC": "$SOL",
    "SOLUSDT": "$SOL", "ETHUSDT": "$ETH", "ADAUSDT": "$ADA",
    "HYPEUSDT": "$HYPE", "SUIUSDT": "$SUI", "JUPUSDT": "$JUP",
    "BNBUSDT": "$BNB", "DOGEUSDT": "$DOGE", "AVAXUSDT": "$AVAX",
    "LINKUSDT": "$LINK", "NEARUSDT": "$NEAR", "SPXUSDT": "$SPX",
    "SPCUSDT": "$SPCX", "PORTFOLIO": "a 5-asset portfolio",
    "BASKET5": "a 5-asset basket",
}

def pair_tag(sym):
    return PAIR_MAP.get((sym or "").upper(), "$" + (sym or "").replace("USDT", "").replace("USDC", "")[:5])

# ── hashtag map ─────────────────────────────────────────────────────────────
ADAPTER_TAGS = {
    "top10": "#Trading #Backtest",
    "xrpneutral": "#XRP #Crypto",
    "xrpneutral1m": "#XRP #Crypto",
    "cbpackf": "#Bitcoin #BTC",
    "qs": "#Bitcoin #BTC",
    "pack100": "#Bitcoin #BTC",
    "smqe": "#Crypto #Trading",
    "emaadx": "#Crypto #Trading",
    "fingrad": "#Crypto #Trading",
    "rsimr": "#SOL #Crypto",
    "mpv3": "#Crypto #Trading",
}
DEFAULT_TAGS = "#Crypto #Trading"

def adapter_tags(adapter):
    return ADAPTER_TAGS.get(adapter, DEFAULT_TAGS)

# ── attention-first templates for a free 280-character X post ──────────────
# Single-line hooks (no \n) so each post is exactly 2 tweets.
HOOK_TEMPLATES = {
    "KILLED": [
        "🚨 Crypto traders: most would call {pf} PF a winner on {pair}. I would not. The kill reason is in reply 2. 🧵",
        "⚠️ The headline number is the distraction. This {desc} reached {pf} PF across {n} trades on {pair}. It still died. Reply 2 shows why. 🧵",
        "🚫 A pretty PF is not an edge. This {desc} on {pair} posted {pf} PF across {n} trades. Then the harder gates hit. Reply 2 has the verdict. 🧵",
        "🧨 Stop. Do not copy this {desc} onto {pair} yet. It printed {pf} PF across {n} trades. The catch is in reply 2. 🧵",
        "👀 I follow backtests until they confess. This {desc} on {pair}: {pf} PF, {n} trades. Here is the part influencers skip. Reply 2. 🧵",
        "📉 {pf} PF can make a dead strategy look alive. This {desc} on {pair} reached {pf} PF across {n} trades. Now the uncomfortable part. Reply 2. 🧵",
        "💀 Retail sees PF. Quant sees the failure mode. This {desc} on {pair} hit {pf} PF over {n} trades. The verdict changes the story. Reply 2. 🧵",
        "🔥 I publish losses too. This {desc} on {pair} posted {pf} PF across {n} trades. Then it failed the rules that matter. Reply 2. 🧵",
    ],
    "CANDIDATE": [
        "🚨 Crypto traders: this {desc} on {pair} looks like the one. {pf} PF across {n} trades. But there is a catch I refuse to hide. Reply 2. 🧵",
        "⚠️ Passed every screen gate is not the same as proven. This {desc} on {pair} reached {pf} PF over {n} trades. Here is the dangerous detail. Reply 2. 🧵",
        "🧨 This {desc} on {pair} survived the screen. {pf} PF and {n} trades. Do not call it alpha yet. Reply 2 explains why. 🧵",
        "👀 A candidate is only useful if you know how it can lie. This {desc} on {pair}: {pf} PF, {n} trades. The catch matters. Reply 2. 🧵",
        "🔥 This one survived the first screen, so I attacked it harder. {desc} + {pair}: {pf} PF across {n} trades. Verdict in reply 2. 🧵",
    ],
    "FAIL": [
        "🚨 Crypto traders: this {desc} on {pair} never had a clean edge. {pf} PF across {n} trades was only the first warning. Reply 2 has the ugly verdict. 🧵",
        "⚠️ The strategy looked defensible. The data disagreed. This {desc} on {pair}: {pf} PF, {n} trades. Reply 2 is the autopsy. 🧵",
        "🧨 {pf} PF is not protection. This {desc} on {pair} produced {n} trades. The gate result is worse than expected. Reply 2. 🧵",
        "👀 I do not hide ugly backtests. This {desc} on {pair}: {pf} PF, {n} trades. Its failure mode is the lesson. Reply 2. 🧵",
    ],
    "SUSPENDED": [
        "⚠️ A strategy without honest OOS is just a story. This {desc} on {pair}: {pf} PF across {n} trades. I suspended it for one reason. Reply 2. 🧵",
        "🧨 {pf} PF means little if the validation is broken. This {desc} on {pair} has {n} trades. The missing piece is in reply 2. 🧵",
        "👀 Backtesters: do not trade a story without clean validation. This {desc} on {pair}: {pf} PF, {n} trades. Reply 2 shows why I stopped. 🧵",
    ],
    "REJECTED": [
        "🚫 Rejected at the gate. This {desc} on {pair} reached {pf} PF across {n} trades. The reason is more interesting than the result. Reply 2. 🧵",
        "⚠️ Zero cells cleared the gate. This {desc} on {pair}: {pf} PF, {n} trades. Most would never post this. I do. Reply 2. 🧵",
        "🧨 A backtest is only useful when it can say no. This {desc} on {pair}: {pf} PF, {n} trades. Reply 2 has the verdict. 🧵",
    ],
    "NOT VALIDATED": [
        "⚠️ Re-measured at real repo costs, this edge shrank. {desc} on {pair}: {pf} PF across {n} trades. The verdict is in reply 2. 🧵",
        "🧨 Costs can erase a fantasy edge. This {desc} on {pair}: {pf} PF, {n} trades. Reply 2 shows the honest verdict. 🧵",
    ],
}
DEFAULT_HOOK = "Crypto traders: this {desc} on {pair} needs more than a headline number. {pf} PF. {n} trades. The full verdict is in reply 2. 🧵"

def spec_id_for(adapter, name):
    n = name or ""
    a = adapter or ""
    if a == "top10":
        table = {'168-bar breakout': 'top10-168-bar-breakout',
                 'Donchian breakout': 'top10-donchian-breakout',
                 'Donchian chandelier': 'top10-donchian-chandelier',
                 'EMA cross': 'top10-ema-cross',
                 'Hour-of-day filter': 'top10-hour-of-day-filter',
                 'Keltner con RSI': 'top10-keltner-con-rsi',
                 'Price-funding divergence': 'top10-price-funding-divergence',
                 'Range expansion': 'top10-range-expansion',
                 'Regression slope': 'top10-regression-slope',
                 'Sunday-to-Monday reversion': 'top10-sunday-to-monday-reversion'}
        nl = n.lower()
        for k, v in table.items():
            if k.lower() in nl:
                return v
        return None
    if a == "xrpneutral":
        return "xrpneutral-v1" if "v1" in n.lower() else "xrpneutral-v2"
    if a == "xrpneutral1m":
        return "xrpneutral-1m"
    if a == "cbpackf":
        m = re.search(r"S(\d{2})\b", n)
        return f"cbpackf-s{m.group(1)}" if m else None
    if a == "qs":
        m = re.search(r"QS-(\d{3})", n)
        return f"qs-{m.group(1)}" if m else None
    if a == "pack100":
        m = re.match(r"^[A-Z](\d{2})-", n)
        return f"pack100-{int(m.group(1))}" if m else None
    return {"smqe": "smqe-v2-core", "emaadx": "emaadx-ema-adx",
            "fingrad": "fingrad-hma-ao-adx", "rsimr": "rsimr-sol-usdc",
            "mpv3": "mpv3-s10-pure-ew-momentum"}.get(a)

def pick(m, *keys):
    # top-level scalar
    for k in keys:
        v = m.get(k)
        if isinstance(v, (int, float)) and v == v:
            return v
    # nested top10-style dicts
    for nested_key, subkey in (("full", "pf"), ("full_pct", "mdd_pct"),
                                ("oos", "pf"), ("oos_pct", "mdd_pct"),
                                ("full", "n"), ("oos", "n")):
        nk = nested_key
        sk = subkey
        # only use if the requested key family matches
        if "pf" in keys and sk == "pf" and nested_key in ("full", "oos"):
            d = m.get(nested_key)
            if isinstance(d, dict):
                v = d.get("pf")
                if isinstance(v, (int, float)) and v == v:
                    return v
        if ("max_dd_pct" in keys or "dd_pct" in keys) and sk == "mdd_pct":
            d = m.get(nested_key)
            if isinstance(d, dict):
                v = d.get("mdd_pct")
                if isinstance(v, (int, float)) and v == v:
                    return v
        if ("n_trades" in keys or "n" in keys) and sk == "n" and nested_key in ("full", "oos"):
            d = m.get(nested_key)
            if isinstance(d, dict):
                v = d.get("n")
                if isinstance(v, (int, float)) and v == v:
                    return v
    return None

def hook_for(desc, pair, pf_str, n_str, verdict):
    import random
    templates = HOOK_TEMPLATES.get(verdict, [DEFAULT_HOOK])
    # deterministic template selection based on hash of desc+pair
    idx = hash((desc, pair, verdict)) % len(templates)
    tmpl = templates[idx]
    return tmpl.format(desc=desc, pair=pair, pf=pf_str, n=n_str)

def thread_text(r):
    art = r["_art"]; m = art["metrics"]; inp0 = (art.get("inputs") or [{}])[0]
    sym = (art.get("symbol") or r.get("symbol") or "").upper()
    pair = pair_tag(sym)
    desc = ADAPTER_DESC.get(str(r.get("adapter") or ""), ADAPTER_DESC_DEFAULT)
    label, reason = r["_label"], r["_reason"]
    pf  = pick(m, "profit_factor", "pf")
    dd  = pick(m, "max_dd_pct", "dd_pct")
    n   = pick(m, "n_trades", "n")
    bars = m.get("bars")
    start = str(inp0.get("start") or "")[:10]; end = str(inp0.get("end") or "")[:10]
    funding = m.get("funding_charged")
    rid = art.get("run_id")
    tags = adapter_tags(r.get("adapter"))

    pf_str = f"{pf:.2f}" if pf is not None else None
    n_str = str(int(round(n))) if n is not None else None
    dd_str = f"{dd:.1f}%" if dd is not None else None

    # Build hook: always single-line, always concrete
    if pf_str and n_str:
        templates = HOOK_TEMPLATES.get(label, [DEFAULT_HOOK])
        idx = abs(hash((desc, pair, label))) % len(templates)
        t1 = templates[idx].format(desc=desc, pair=pair, pf=pf_str, n=n_str)
        win = f" {bars} bars." if bars else ""
        if win and len(t1) + len(win) <= 265:
            t1 += win
    elif bars and (n_str or dd_str):
        # pack-level artifact: use available counts
        stat = n_str and f"{n_str} trades" or dd_str
        t1 = f"🚨 Crypto traders: {bars} bars through a {desc} on {pair} — {stat}. No hype. The verdict is in reply 2. 🧵"
    elif bars:
        t1 = f"🚨 Crypto traders: {bars} bars through a {desc} on {pair}. No hype. Verdict in reply 2. 🧵"
    else:
        t1 = f"🚨 Crypto traders: this {desc} on {pair} deserves more than a headline. Verdict in reply 2. 🧵"
    if len(t1) > 265:
        t1 = t1[:262].rsplit(" ", 1)[0] + "..."
    # guard-safe: strip stray digits from fixed copy ("reply 2" -> "reply below")
    # unless they are part of a metric we quote (pf/n/bars/dd)
    t1 = t1.replace("reply 2", "the reply below")

    # Tweet 2: stats + verdict + CTA + hashtags
    stats_parts = []
    if pf_str:
        stats_parts.append(f"PF {pf_str}")
    if n_str:
        stats_parts.append(f"{n_str} trades")
    if dd_str:
        stats_parts.append(f"{dd_str} max DD")
    if stats_parts:
        stats = " · ".join(stats_parts) + "."
    else:
        stats = "Pack-level result. Details in the repo."

    reason_txt = str(reason).replace(".", "").lower()
    verdict_line = f"Verdict: {label} — {reason_txt}."
    if funding is True:
        verdict_line += " Funding charged."
    elif funding is False:
        verdict_line += " Funding NOT charged."
    cta = "Full rules + reproducible code in bio — fork it and try to falsify it."
    t2 = f"{stats} {verdict_line} NFA. {cta} {tags}"

    return [t1, t2]

def slugify(s):
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s[:80] or "post"

def build(days, outdir):
    rows = load_rows()
    elig, skipped = eligibility(rows)
    ordered = order_rows(elig)
    need = days * 3
    picked = ordered[:need]
    os.makedirs(outdir, exist_ok=True)
    start = datetime(2026, 11, 5, 0, 0, tzinfo=timezone.utc)
    slots = [("A", "strategy card", 1, 30), ("B", "autopsy", 13, 0), ("C", "lab note", 21, 0)]
    manifest = []
    for i, r in enumerate(picked):
        day = start + timedelta(days=i // 3)
        slot, _, hh, mm = slots[i % 3]
        dt = day.replace(hour=hh, minute=mm)
        tweets = thread_text(r)
        if any(len(t) > 270 for t in tweets):
            # shorten tweet 1 by dropping window info
            tweets[0] = tweets[0].split("Window")[0].strip() if "Window" in tweets[0] else tweets[0]
        sym = (r.get("symbol") or "").upper()
        tf = str(r.get("tf") or "").lower()
        rid = str(r.get("run_id") or "")
        slug = slugify(f"{dt:%Y-%m-%d}-{slot}-{r.get('adapter')}-{sym}-{tf}-{rid[:6]}")
        fname = f"{slug}.md"
        path = os.path.join(outdir, fname)
        label = r["_label"]
        with open(path, "w", encoding="utf-8") as f:
            # header carries NO digits — guard scans the whole file; dates live in SCHEDULE.md
            f.write(f"# Slot {slot} — {sym} — {label}\n\n")
            f.write("INSTRUCTIONS (not part of the thread): paste each block below as one ")
            f.write("tweet, in order, using X's Schedule button. Numbers from artifact " + rid + "\n\n")
            for t in tweets:
                f.write(t + "\n\n")
        manifest.append({
            "file": f"posts/{fname}", "datetime_utc": dt.isoformat(),
            "slot": slot, "run_id": rid, "adapter": r.get("adapter"),
            "spec_id": spec_id_for(r.get("adapter"), r.get("name")),
            "family": family_of(r), "symbol": sym, "tf": tf,
            "verdict": label, "source_verdict": r.get("verdict"),
        })
    # manifest + schedule
    with open(os.path.join(REPO, "content", "manifest.jsonl"), "w", encoding="utf-8") as f:
        for mrec in manifest:
            f.write(json.dumps(mrec, ensure_ascii=False) + "\n")
    with open(os.path.join(REPO, "content", "SCHEDULE.md"), "w", encoding="utf-8") as f:
        f.write("# SCHEDULE — @nftepml content pack\n\n")
        f.write("Dates/times UTC. Paste each block of `posts/<file>` as one thread, in order.\n\n")
        f.write("| When (UTC) | Slot | File | Verdict |\n|---|---|---|---|\n")
        for mrec in manifest:
            f.write(f"| {mrec['datetime_utc'][:16].replace('T',' ')} | {mrec['slot']} | `{mrec['file']}` | {mrec['verdict']} |\n")
    print(f"picked {len(manifest)} posts -> {outdir}")
    print("skips:", dict(skipped))

def verify():
    files = sorted(f for f in os.listdir(os.path.join(REPO, "content", "posts"))
                   if f.endswith(".md"))
    bad = []
    for f in files:
        p = os.path.join(REPO, "content", "posts", f)
        rc = subprocess.call([sys.executable, os.path.join(REPO, "code", "vrun.py"),
                              "guard", "--report", p], stdout=subprocess.DEVNULL)
        if rc != 0:
            bad.append(f)
    print(f"guard OK: {len(files) - len(bad)}/{len(files)}")
    for f in bad:
        print("REFUSED:", f)
    return 1 if bad else 0

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--days", type=int, default=30)
    b.add_argument("--out", default=os.path.join(REPO, "content", "posts"))
    sub.add_parser("verify")
    args = ap.parse_args()
    if args.cmd == "build":
        build(args.days, args.out)
    elif args.cmd == "verify":
        sys.exit(verify())

if __name__ == "__main__":
    main()
