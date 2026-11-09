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
    "top10": "prompt-screen breakout", "xrpneutral": "delta-neutral grid",
    "xrpneutral1m": "delta-neutral grid",
    "cbpack": "ten-strategy pack", "cbpackf": "ten-strategy pack",
    "pack50": "prompt pack", "pack50b": "prompt pack",
    "pack50c": "prompt pack", "pack50d": "prompt pack",
    "pack100": "hundred-prompt pack", "prompts100": "hundred-prompt screen",
    "qs": "risk-sized book", "qsb": "risk-sized mean-reversion book",
    "qsc": "risk-sized breakout book", "qsd": "risk-sized structure book",
    "qsf": "risk-sized trade-flow book",
    "dspack": "deepseek pack", "dspack2": "deepseek pack",
    "xsf": "cross-sectional factor book", "xsb": "relative-value factor book",
    "xsc": "funding-gated factor book",
    "cbot": "bot suite", "cand7": "prespecified candidate",
    "emaadx": "EMA/ADX trend system", "hmaaoadx": "HMA/ADX trend system",
    "ffs": "FFS system", "botstrat": "bot system", "cvrmd": "momentum system",
    "smqe": "SMQE setup", "fingrad": "funding-gradient system",
    "mpv3": "portfolio audit", "rsimr": "RSI mean-reversion system",
    "eqpack": "equity pack",
    "q10": "qwen cards", "mp20": "portfolio book", "xrp100": "XRP screen",
}
ADAPTER_DESC_DEFAULT = "systematic strategy"

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
    ("sin funding en perps", "KILLED", "the edge did not survive the full gate battery"),
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
           "30m": "thirty-minute", "1h": "hourly", "4h": "four-hour",
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
    "SPCUSDT": "$SPCX", "PORTFOLIO": "a five-asset portfolio",
    "BASKET5": "a five-asset basket",
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

# ── story engine ────────────────────────────────────────────────────────────
# Every number that reaches a tweet must exist in the cited artifact:
# no unit conversions, no dates, no derived arithmetic, no filler digits.
SYMBOL_TAGS = {
    "BTC": "#Bitcoin #BTC", "ETH": "#Ethereum #ETH", "SOL": "#Solana #SOL",
    "XRP": "#XRP #Crypto", "BNB": "#BNB #Crypto", "ADA": "#Cardano #ADA",
    "AVAX": "#AVAX #Crypto", "DOGE": "#Dogecoin #DOGE", "HYPE": "#HYPE #Crypto",
    "SUI": "#SUI #Crypto", "JUP": "#JUP #Solana", "LINK": "#LINK #Crypto",
    "NEAR": "#NEAR #Crypto", "SPX": "#SPX #Crypto", "QQQ": "#QQQ #Trading",
}

def tags_for(sym):
    sym = (sym or "").lstrip("$").upper()
    return SYMBOL_TAGS.get(sym, ("#" + sym + " #Crypto") if sym else "#Crypto #Trading")

def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v

def _first(m, *keys):
    for k in keys:
        if _num(m.get(k)):
            return m[k]
    return None

def _nested(m, key, sub):
    d = m.get(key)
    if isinstance(d, dict) and _num(d.get(sub)):
        return d[sub]
    return None

def _f2(v):
    return f"{v:.2f}"

def _f1(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s

def _int(v):
    return str(int(round(v)))

def _stable(*parts):
    import zlib
    return zlib.crc32("|".join(str(p) for p in parts).encode("utf-8"))

def _choose(options, *seed):
    options = [o for o in options if o]
    if not options:
        return ""
    return options[_stable(*seed) % len(options)]

def facts_of(m):
    return {
        "pf": _first(m, "profit_factor", "pf", "pf_strict") or _nested(m, "full", "pf"),
        "n": _first(m, "n_trades", "n") or _nested(m, "full", "n"),
        "dd": _first(m, "max_dd_pct", "dd_pct"),
        "cost": _first(m, "cost_bp_roundtrip"),
        "cost_side": _first(m, "cost_bps_per_side"),
        "zc": _first(m, "zero_cost_pf"),
        "pack_pf": _first(m, "pack_pf"),
        "best_pf": _first(m, "best_pf"),
        "best_net": _first(m, "best_net_pct"),
        "nstrat": _first(m, "n_strategies", "n_run"),
        "npos": _first(m, "n_net_positive"),
        "npass": _first(m, "n_pass_all_gates"),
        "nbeat": _first(m, "n_beat_bh"),
        "best5": _first(m, "best5_share_pct"),
        "netwo": _first(m, "net_without_best5_pct"),
        "bh": _first(m, "bh_return_pct"),
        "ret": _first(m, "return_pct", "ret_pct"),
        "h1": _first(m, "pf_h1"),
        "h2": _first(m, "pf_h2"),
        "full_pf": _nested(m, "full", "pf"),
        "oos_pf": _nested(m, "oos", "pf"),
        "funding": m.get("funding_charged"),
    }

DEAD_LABELS = ("KILLED", "FAIL", "SUSPENDED", "REJECTED", "INCONCLUSIVE", "NOT VALIDATED")

def _angle_candidates(f, sym, tfw, desc, label, adapter):
    """[(priority, kind, hook)] — every number stays artifact-backed."""
    pf, n = f["pf"], f["n"]
    if pf is None:
        pf = f["pack_pf"]
    at = f"{sym} {tfw}" if tfw else sym
    out = []

    # CANDIDATE: the story is the selection, not the PF
    if label == "CANDIDATE" and pf is not None and n is not None:
        out.append((0, "candidate", _choose([
            f"{at}. PF {_f2(pf)} over {_int(n)} trades, and it passed every screen gate. Then I checked how the shortlist was picked. 👀",
            f"This {desc} on {sym} survived every screen gate: PF {_f2(pf)}, {_int(n)} trades. The way it was selected is the problem. 👀",
        ], sym, tfw, pf)))

    # fill-model kill: bar-resolution number vs one-minute replay
    if adapter in ("xrpneutral",) and label == "KILLED" and pf is not None and n is not None:
        out.append((0, "fills", _choose([
            f"{at}. PF {_f2(pf)} over {_int(n)} trades. Then I replayed every fill on one-minute candles. 👀",
            f"This {desc} on {sym} printed PF {_f2(pf)} over {_int(n)} trades. One-minute fills told a different story. 👀",
        ], sym, tfw, pf)))

    # concentration: the best five trades ARE the PnL
    if f["best5"] is not None and f["best5"] > 100 and pf is not None and n is not None:
        if f["netwo"] is not None:
            out.append((1, "concentration", _choose([
                f"{at}. PF {_f2(pf)} over {_int(n)} trades. Remove the best five and the PnL flips to {_f1(f['netwo'])}%. That is not an edge. That is five lottery tickets in a trench coat. 🕵️",
                f"This {desc} on {sym} shows PF {_f2(pf)} over {_int(n)} trades. Kill the five best trades and you get {_f1(f['netwo'])}%. Five lottery tickets in a trench coat. 🕵️",
            ], sym, tfw, pf)))
        else:
            out.append((1, "concentration", _choose([
                f"{at}. PF {_f2(pf)} over {_int(n)} trades, and the best five trades are {_f1(f['best5'])}% of the PnL. That is five lottery tickets in a trench coat. 🕵️",
            ], sym, tfw, pf)))

    # pack graveyard
    if f["nstrat"] is not None and f["npass"] is not None and f["npass"] == 0:
        bits = f"{_int(f['nstrat'])} strategies entered."
        if f["npos"] is not None:
            bits += f" {_int(f['npos'])} ended net-positive."
        bits += f" {_int(f['npass'])} cleared every gate."
        if f["nbeat"] is not None and f["nbeat"] == 0 and f["npos"] is not None:
            out.append((1, "pack", _choose([
                f"{at}. {_int(f['nstrat'])} strategies ran. {_int(f['npos'])} finished net-positive. {_int(f['nbeat'])} beat buy and hold. 📉",
                f"{at}. {_int(f['nstrat'])} strategies, {_int(f['npos'])} green, {_int(f['nbeat'])} that beat holding spot. That is the whole story. 🪦",
            ], sym, tfw, f["nstrat"])))
        else:
            out.append((1, "pack", _choose([
                f"{at}. {bits} This {desc} is a graveyard. 🪦",
                f"{at}. {bits} Same pair, same data, same costs. The thread-bros post the one cell that worked. 🪦",
            ], sym, tfw, f["nstrat"])))
    elif f["nstrat"] is not None and f["npass"] is not None and f["npass"] > 0:
        out.append((1, "packpass", _choose([
            f"{at}. {_int(f['npass'])} of {_int(f['nstrat'])} cells cleared every gate. The pack still died. One survivor is not a strategy. 👀",
            f"{at}. One cell out of {_int(f['nstrat'])} passed every gate. The pack still got killed. That is the multiple-testing tax. 💀",
        ], sym, tfw, f["nstrat"])))

    # tiny sample
    if n is not None and n < 60:
        pfx = f"PF {_f2(pf)} over " if pf is not None else ""
        out.append((2, "tiny", _choose([
            f"{at}. {pfx}{_int(n)} trades in total. You cannot validate an edge on that. You can barely call it evidence. 🔬",
            f"This {desc} on {sym} produced {_int(n)} trades in the whole window. That is not a sample. That is an anecdote with a spreadsheet. 🔬",
        ], sym, tfw, n)))

    # unstable halves
    if f["h1"] is not None and f["h2"] is not None and (f["h1"] < 1) != (f["h2"] < 1):
        out.append((2, "halves", _choose([
            f"{at}. PF {_f2(f['h1'])} in the first half. PF {_f2(f['h2'])} in the second. Same rules, same pair, opposite outcomes. That is a coin flip with extra steps. 🪙",
            f"PF {_f2(f['h1'])} in the first half, {_f2(f['h2'])} in the second. This {desc} on {sym} changed personality halfway through. 🪙",
        ], sym, tfw, f["h1"])))

    # cost cliff
    if (f["zc"] is not None and f["zc"] > 1 and pf is not None and pf < 1.2
            and f["zc"] - pf > 0.2):
        if f["cost"] is not None:
            at_cost = f"At {_int(f['cost'])} bps roundtrip"
        elif f["cost_side"] is not None:
            at_cost = f"At {_f1(f['cost_side'])} bps per side"
        else:
            at_cost = "At repo costs"
        out.append((2, "cost", _choose([
            f"{at}. Zero fees: PF {_f2(f['zc'])}. {at_cost}: PF {_f2(pf)}. The edge lived in the cost assumption, not in the market. 🧾",
            f"The gross book on {sym} made PF {_f2(f['zc'])}. {at_cost}: PF {_f2(pf)}. Fees ate the strategy. 🧾",
        ], sym, tfw, pf)))

    # beat buy and hold?
    if (f["bh"] is not None and f["ret"] is not None and f["bh"] > 0
            and f["bh"] - f["ret"] > 10 and label != "CANDIDATE"):
        out.append((3, "bh", _choose([
            f"{at}. The book returned {_f1(f['ret'])}%. Buy and hold returned {_f1(f['bh'])}%. A lot of work to underperform a spot wallet. 📉",
            f"This {desc} on {sym} returned {_f1(f['ret'])}%. Holding spot returned {_f1(f['bh'])}%. The strategy lost to doing nothing. 📉",
        ], sym, tfw, f["ret"])))

    # in-sample vs out-of-sample gap
    if f["full_pf"] is not None and f["oos_pf"] is not None and f["full_pf"] - f["oos_pf"] > 0.05:
        out.append((2, "oos", _choose([
            f"{at}. In-sample PF {_f2(f['full_pf'])}. Out-of-sample PF {_f2(f['oos_pf'])}. That gap is where accounts die. 🕳️",
            f"The {sym} backtest shows PF {_f2(f['full_pf'])} in-sample and {_f2(f['oos_pf'])} out-of-sample. The gap is the whole story. 🕳️",
        ], sym, tfw, f["full_pf"])))

    # a good PF that still died
    if pf is not None and pf >= 1 and label in DEAD_LABELS:
        nbit = f" over {_int(n)} trades" if n is not None else ""
        if label == "SUSPENDED":
            tail = "The backtest looks fine. The validation is what broke. ⚠️"
        elif label == "INCONCLUSIVE":
            tail = "No clean verdict either way. That is its own verdict. ⚠️"
        else:
            tail = "On paper it looks tradeable. Then the gates did their job. 👀"
        out.append((3, "goodpf", f"{at}. PF {_f2(pf)}{nbit}. {tail}"))

    # a losing PF
    if pf is not None and pf < 1:
        nbit = f" over {_int(n)} trades" if n is not None else ""
        out.append((4, "losspf", _choose([
            f"{at}. PF {_f2(pf)}{nbit}. That is what a losing edge looks like before someone puts a logo on it. 📉",
            f"PF {_f2(pf)}{nbit} for this {desc} on {sym}. No logo will fix that. 📉",
        ], sym, tfw, pf)))

    # fallback: never empty, never flattering
    out.append((5, "fallback", f"{at}. This {desc} has a headline number and no edge behind it. The interesting part is why. 👀"))
    return out

def hook_for(f, sym, tfw, desc, label, rid, adapter):
    cands = _angle_candidates(f, sym, tfw, desc, label, adapter)
    cands.sort(key=lambda x: (x[0], x[2]))
    top = [c for c in cands if c[0] == cands[0][0]]
    chosen = top[_stable(rid, sym, tfw) % len(top)]
    return chosen[2], chosen[1]

def _short_reason(label, adapter, reason):
    if label == "CANDIDATE":
        return "passes the screen but is selection-contaminated and unproven forward"
    if label == "INCONCLUSIVE":
        return "no cell in the pack cleared the gates"
    if adapter in ("qs", "qsb", "qsc", "qsd", "qsf"):
        return {"FAIL": "it failed the gate battery",
                "REJECTED": "the gate said no"}.get(label, str(reason).strip().rstrip("."))
    return str(reason).strip().rstrip(".")

def _stats_line(f, kind):
    bits = []
    pf = f["pf"] if f["pf"] is not None else f["pack_pf"]
    if pf is not None:
        bits.append(f"{'Full PF' if kind == 'halves' else 'PF'} {_f2(pf)}")
    elif f["best_pf"] is not None:
        bits.append(f"Best cell PF {_f2(f['best_pf'])}")
    elif f["best_net"] is not None:
        bits.append(f"Best cell {_f1(f['best_net'])}%")
    if f["n"] is not None:
        bits.append(f"{_int(f['n'])} trades")
    if f["dd"] is not None:
        bits.append(f"{_f1(f['dd'])}% max DD")
    return (" · ".join(bits) + ".") if bits else "Pack-level result."

def thread_text(r):
    art = r["_art"]; m = art.get("metrics") or {}
    raw = (art.get("symbol") or r.get("symbol") or "").upper()
    parts = [p.replace("USDT", "").replace("USDC", "") for p in re.split(r"[+/,]", raw) if p]
    parts = [p for p in parts if p and p not in ("PORTFOLIO", "BASKET", "BASKET5")]
    if parts:
        sym = " + ".join("$" + p for p in parts)
        tag_sym = parts[0]
        tags = ("#" + " #".join(parts[:2]) + " #Crypto") if len(parts) > 1 else tags_for(tag_sym)
    else:
        sym = "the basket"
        tag_sym = ""
        tags = tags_for(tag_sym)
    tfw = TF_WORD.get(str(art.get("timeframe") or r.get("tf") or "").lower(), "")
    desc = ADAPTER_DESC.get(str(r.get("adapter") or ""), ADAPTER_DESC_DEFAULT)
    label, reason = r["_label"], r["_reason"]
    rid = art.get("run_id") or ""
    adapter = str(r.get("adapter") or "")
    f = facts_of(m)

    hook, kind = hook_for(f, sym, tfw, desc, label, rid, adapter)
    if len(hook) > 270:
        hook = hook[:267].rsplit(" ", 1)[0] + "..."

    stats_line = _stats_line(f, kind)
    verdict = f"Verdict: {label} — {_short_reason(label, adapter, reason)}."

    caveats = []
    if f["funding"] is True:
        caveats.append("Funding charged.")
    elif f["funding"] is False and "funding" not in str(reason).lower():
        caveats.append("Funding not charged.")
    if label == "CANDIDATE":
        caveats.append("Forward record pending.")

    body = ""
    for tag_line in (tags + " #Backtest", tags, ""):
        for cta in ("Rules + artifact: github.com/mancas21/BACKTEST",
                    "Rules: github.com/mancas21/BACKTEST", ""):
            candidate = " ".join(x for x in [stats_line, verdict, " ".join(caveats),
                                             cta, tag_line, "NFA"] if x)
            if len(candidate) <= 270:
                body = candidate
                break
        if body:
            break
    if not body:
        body = _stats_line(f, kind) + " " + verdict
        body = body[:267].rsplit(" ", 1)[0] + "..."

    return [hook, body]

def slugify(s):
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s[:80] or "post"

def _content_key(r):
    a = r["_art"]; f = facts_of(a.get("metrics") or {})
    return (r.get("adapter"), a.get("symbol"), a.get("timeframe"), r["_label"],
            None if f["pf"] is None else round(f["pf"], 4),
            None if f["n"] is None else int(round(f["n"])),
            None if f["dd"] is None else round(f["dd"], 2),
            None if f["best5"] is None else round(f["best5"], 2),
            None if f["netwo"] is None else round(f["netwo"], 2),
            r["_reason"])

def build(days, outdir, start=None):
    rows = load_rows()
    elig, skipped = eligibility(rows)
    ordered = order_rows(elig)
    need = days * 3
    # no two posts may tell the same story with the same numbers
    picked, seen, seen_pair, dup_story = [], set(), set(), 0
    for r in ordered:
        k = _content_key(r)
        a = r["_art"]
        pair_key = (r.get("adapter"), a.get("symbol"))
        if k in seen or pair_key in seen_pair:
            dup_story += 1
            continue
        seen.add(k)
        seen_pair.add(pair_key)
        picked.append(r)
        if len(picked) >= need:
            break
    skipped = dict(skipped)
    skipped["duplicate_story"] = dup_story
    os.makedirs(outdir, exist_ok=True)
    now = datetime.now(timezone.utc)
    if start:
        day0 = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        day0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
    slots = [("A", 1, 30), ("B", 13, 0), ("C", 21, 0)]
    # never emit a post with a past timestamp: skip slots already gone
    slot_times = []
    d = day0
    while len(slot_times) < need:
        for slot, hh, mm in slots:
            dt = d.replace(hour=hh, minute=mm)
            if dt > now:
                slot_times.append((slot, dt))
        d += timedelta(days=1)
    manifest = []
    for r, (slot, dt) in zip(picked, slot_times):
        tweets = thread_text(r)
        if any(len(t) > 280 for t in tweets):
            tweets[0] = tweets[0][:277].rsplit(" ", 1)[0] + "..."
            tweets[1] = tweets[1][:277].rsplit(" ", 1)[0] + "..."
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
    # one copy-paste digest with the complete text of every post
    with open(os.path.join(REPO, "content", "WEEK.md"), "w", encoding="utf-8") as f:
        f.write("# Full text — every scheduled post\n\n")
        f.write("Copy each tweet block in order. Times are UTC.\n\n")
        for mrec in manifest:
            p = os.path.join(outdir, os.path.basename(mrec["file"]))
            lines = open(p, encoding="utf-8").read().splitlines()
            blocks = [b for b in lines[4:] if b.strip()]
            f.write(f"## {mrec['datetime_utc'][:16].replace('T',' ')} UTC · slot {mrec['slot']} · {mrec['verdict']}\n\n")
            f.write(f"`{mrec['adapter']} · {mrec['symbol']} · {mrec['tf']} · artifact {mrec['run_id']}`\n\n")
            for i, b in enumerate(blocks, 1):
                f.write(f"**Tweet {i}**\n\n> {b}\n\n")
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
    b.add_argument("--start", default=None, help="UTC date YYYY-MM-DD (past slots are skipped)")
    sub.add_parser("verify")
    args = ap.parse_args()
    if args.cmd == "build":
        build(args.days, args.out, args.start)
    elif args.cmd == "verify":
        sys.exit(verify())

if __name__ == "__main__":
    main()
