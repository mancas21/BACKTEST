#!/usr/bin/env python3
"""
x_queue.py — generate the X (@nftepml) posting pack from the strategy registry.

Doctrine (non-negotiable):
  - The tweet PUBLISHES THE STRATEGY: the rule itself (entry/exit/stop/costs),
    verbatim from content/specs.md. Performance numbers and the verdict never
    appear — the reader has to open the repo link to find out how it did.
  - Every digit in a tweet must exist in the cited artifact
    (results/runs/<run_id>.json); `vrun.py guard` must pass on each file.
  - Nothing is invented; unmapped verdicts are skipped, never guessed.

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

# ── story engine — ONE tweet per post, the verdict NEVER appears ─────────────
# Rules for every number that reaches a tweet:
#   * it must be a value that exists in the cited artifact (guard checks this);
#   * no unit conversions, no dates, no bars, no derived arithmetic;
#   * NO verdict word, ever — the result lives in the repo behind the link,
#     and the reader has to go get it (assert_clean enforces this).
SYMBOL_TAGS = {
    "BTC": "#Bitcoin #BTC", "ETH": "#Ethereum #ETH", "SOL": "#Solana #SOL",
    "XRP": "#XRP #Crypto", "BNB": "#BNB #Crypto", "ADA": "#Cardano #ADA",
    "AVAX": "#AVAX #Crypto", "DOGE": "#Dogecoin #DOGE", "HYPE": "#HYPE #Crypto",
    "SUI": "#SUI #Crypto", "JUP": "#JUP #Solana", "LINK": "#LINK #Crypto",
    "NEAR": "#NEAR #Crypto", "SPX": "#SPX #Crypto", "QQQ": "#QQQ #Trading",
}

# rotation the pack cycles through: one style per slot, in this order
HOOK_STYLES = ["curiosity", "shock", "contradiction", "cost"]

# any of these in a tweet is a build failure, not a warning
BANNED_RE = re.compile(
    r"\b(verdict|killed|killing|kill|failed|failing|fails|died|die|dying|dead|"
    r"candidate|rejected|reject|suspended|suspend|inconclusive|graveyard|loser|"
    r"losing|no edge|never works|broke|broken|survived|clears the gates)\b",
    re.IGNORECASE)

def assert_clean(text):
    hits = sorted({m.group(0).lower() for m in BANNED_RE.finditer(text)})
    if hits:
        raise ValueError("verdict language leaked into copy: %s | %s" % (hits, text[:140]))

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
        "cost_side": _first(m, "cost_bps_per_side", "fee_bps_per_side"),
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

# ── spec engine — the tweet PUBLISHES THE STRATEGY, never a result ──────────
# The body of every tweet is the strategy itself (MECHANISM / RULES / COSTS),
# verbatim from content/specs.md, adapted to the artifact's instrument:
#   * a spec that names another pair is restated on the traded pair
#     (the rule is symbol-agnostic; the artifact proves it ran there);
#   * a timeframe claim that disagrees with the artifact drops the candidate;
#   * every digit must exist in the cited artifact (numbers_backed / guard);
#   * NO verdict word and no performance number, ever (assert_clean).
SPEC_PATH = os.path.join(REPO, "content", "specs.md")
_SPECS_CACHE = None

def load_specs():
    global _SPECS_CACHE
    if _SPECS_CACHE is not None:
        return _SPECS_CACHE
    specs, cur = {}, None
    with open(SPEC_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()
            if line.startswith("## "):
                cur = line[3:].strip()
                specs[cur] = {}
            elif cur and ":" in line and line.split(":", 1)[0] in ("SOURCE", "MECHANISM", "RULES", "COSTS"):
                k, v = line.split(":", 1)
                specs[cur][k] = v.strip()
    _SPECS_CACHE = specs
    return specs

_HEX_TOK_RE = re.compile(r"(?<![\w.])[0-9a-fA-F]{8,}(?![\w.])")
_NUM_TOK_RE = re.compile(r"(?<![\w.])[+-]?\d+(?:\.\d+)?")
_NUMCACHE = {}

def _art_numbers(rid):
    """Every number guard would quote from this artifact (metrics/tables/inputs/params)."""
    if rid in _NUMCACHE:
        return _NUMCACHE[rid]
    art = load_artifact(rid) or {}
    vals = []
    def walk(o):
        if isinstance(o, dict):
            [walk(v) for v in o.values()]
        elif isinstance(o, list):
            [walk(v) for v in o]
        elif isinstance(o, bool):
            return
        elif isinstance(o, (int, float)):
            if o == o:
                vals.append(float(o))
        elif isinstance(o, str):
            for t in _NUM_TOK_RE.findall(o):
                try:
                    vals.append(float(t))
                except ValueError:
                    pass
    for k in ("metrics", "tables", "inputs", "params"):
        walk(art.get(k))
    _NUMCACHE[rid] = vals
    return vals

def numbers_backed(text, rid):
    """True when guard would accept every digit in text for this artifact."""
    vals = _art_numbers(rid)
    for tok in _NUM_TOK_RE.findall(_HEX_TOK_RE.sub(" ", text)):
        try:
            v = float(tok)
        except ValueError:
            continue
        dps = len(tok.split(".")[1]) if "." in tok else 0
        if any(abs(round(x, dps) - v) < 1e-9 for x in vals):
            continue
        tol = max(abs(v) * 1e-4, 1e-6)
        if any(abs(x - v) <= tol for x in vals):
            continue
        return False
    return True

_PAIR_TOKEN_RE = re.compile(r"\b[A-Z0-9]{3,10}(?:USDT|USDC)\b")
_TF_WORDS = {"1m": "one-minute", "5m": "five-minute", "15m": "fifteen-minute",
             "30m": "thirty-minute", "1h": "hourly", "4h": "four-hour",
             "1d": "daily", "1w": "weekly"}
# these phrases are NOT timeframe claims (a per-day breaker, a rebalance cadence,
# a fill tape) — masking them keeps honest strategies from being dropped
_TF_MASK = [r"daily[- ]loss", r"day-start", r"weekly rebalance",
            r"1m tape", r"minute by minute", r"1m record"]

def adapt_spec(text, art):
    """Restate a spec on the artifact's instrument; None when its timeframe
    claim contradicts the artifact (those are dropped, never rewritten)."""
    if not text:
        return None
    sym = str(art.get("symbol") or "").upper()
    tf = str(art.get("timeframe") or "").lower()
    if sym and not re.search(r"[+,/]", sym):
        text = _PAIR_TOKEN_RE.sub(
            lambda m: m.group(0) if m.group(0) == sym else sym, text)
    masked = text
    for pat in _TF_MASK:
        masked = re.sub(pat, " ", masked, flags=re.I)
    low = masked.lower()
    claims = {k for k, w in _TF_WORDS.items() if re.search(r"\b" + w + r"\b", low)}
    claims.update(re.findall(r"\b\d+[mhdw]\b", low))
    if any(c != tf for c in claims):
        return None
    return text

# hook per rotation style — fixed copy, ZERO digits, no verdict language
STYLE_HOOKS = {
    "curiosity": [
        "The whole rule, published. No black box: 👀",
        "What does the system actually do? Exactly this: 👀",
        "Copy it, backtest it, argue with it: 👀",
    ],
    "shock": [
        "No indicator soup. This is the entire system: 🚨",
        "One entry, one exit, nothing else: 🚨",
        "This is the whole strategy — every line of it: 🚨",
    ],
    "contradiction": [
        "Everyone shows the entry. The exit is the system: 🤯",
        "Simple entry, strict exit — that tension is the design: 🤯",
        "The entry is boring. The exit does the work: 🤯",
    ],
    "cost": [
        "The rule is free. Running it is not: 💸",
        "Before you copy it — what it costs to run: 💸",
        "Same rule, the fee is the filter: 💸",
    ],
}

def _condense_variants(rules):
    """Progressively shorter tradeable versions of a RULES line, cleanest
    first: entry/exit/stop only, then those plus fills/risk/mirror, then the
    full line. Only WHOLE clauses are dropped — no digit is ever added,
    rewritten or converted, so numbers_backed/guard stay honest."""
    if not rules:
        return []
    parts = [p.strip() for p in rules.split(";") if p.strip()]
    if len(parts) <= 1:
        return [rules]
    core_w = ("entry", "exit", "stop", "target", "trail")
    # a core clause states the rule; "stop checked intrabar..." is
    # microstructure, so it only survives in the wider tier
    core = [p for p in parts
            if any(p.lower().startswith(w + " =") or p.lower().startswith(w + "=")
                   for w in core_w)
            or p.lower().startswith(("long =", "short =", "long=", "short="))]
    wide = core + [p for p in parts
                   if p not in core and p.lower().startswith(
                       ("entry", "exit", "stop", "target", "trail", "fill",
                        "risk", "mirror", "reverse", "long", "short"))]
    out = []
    # fullest first: single_tweet takes the first variant that fits, so the
    # most complete recipe wins and shorter ones only serve as fallback
    for cand in (parts, wide, core):
        t = "; ".join(cand)
        if t and t not in out:
            out.append(t)
    return out

def style_texts(r):
    """{style: [strategy bodies]} straight from specs.md. The body IS the
    recipe (entry/exit/stop, condensed to fit a tweet); the mechanism line is
    the fallback when a parameter is not in the artifact (guard backs only
    digits the artifact carries). Every candidate is digit-backed, free of
    verdict language, and a row with NO artifact-backed rule text is dropped —
    a cost line alone never counts as publishing a strategy."""
    art = r["_art"]
    rid = str(art.get("run_id") or r.get("run_id") or "")
    sid = spec_id_for(str(r.get("adapter") or ""), r.get("name"))
    spec = load_specs().get(sid or "")
    out = defaultdict(list)
    if not spec:
        return out

    def valid(s):
        return bool(s) and len(s) >= 10 and numbers_backed(s, rid)

    mech = adapt_spec(spec.get("MECHANISM", ""), art)
    rules = adapt_spec(spec.get("RULES", ""), art)
    costs = adapt_spec(spec.get("COSTS", ""), art)
    bodies = []
    for cand in _condense_variants(rules):
        if valid(cand) and cand not in bodies:
            bodies.append(cand)
    if valid(mech) and mech not in bodies:
        bodies.append(mech)
    if not bodies:
        # no artifact-backed rule text: this row cannot publish a strategy
        return out
    for style in HOOK_STYLES:
        if style == "cost":
            continue
        out[style] = list(bodies)
    if valid(costs):
        # the cost style must actually carry the cost line — never the bare
        # rule under a "what it costs" hook (that promise would be a lie)
        combos = [f"{b} {costs}" for b in bodies]
        combos = [t for t in combos if valid(t)]
        if combos:
            out["cost"] = combos
    for k in list(out):
        out[k] = [t for t in out[k] if valid(t)]
        if not out[k]:
            del out[k]
    return out

def styles_of(r):
    a = r["_art"]
    raw = (a.get("symbol") or r.get("symbol") or "").upper()
    parts = [p.replace("USDT", "").replace("USDC", "") for p in re.split(r"[+/,]", raw) if p]
    parts = [p for p in parts if p and p not in ("PORTFOLIO", "BASKET", "BASKET5")]
    sym = " + ".join("$" + p for p in parts) if parts else "the basket"
    tfw = TF_WORD.get(str(a.get("timeframe") or r.get("tf") or "").lower(), "")
    desc = ADAPTER_DESC.get(str(r.get("adapter") or ""), ADAPTER_DESC_DEFAULT)
    return style_texts(r), (sym, tfw, desc)

LINK = "github.com/mancas21/BACKTEST"

def x_len(text):
    """X's weighted length: our fixed URL counts 23, an emoji counts 2, every
    other character counts 1 (the generated copy is ASCII outside the emoji).
    Python len() is the wrong yardstick on its own: it charges 28 for the URL
    and 1 for an emoji, which is 6 chars stricter than X per tweet."""
    n = 0
    parts = text.split(LINK)
    for i, p in enumerate(parts):
        if i:
            n += 23
        for ch in p:
            n += 2 if 0x1F000 <= ord(ch) <= 0x1FAFF else 1
    return n

def single_tweet(r, style):
    """One post = one tweet: hook + THE STRATEGY + link + tags + NFA.
    No verdict, no performance number, ever."""
    art = r["_art"]
    rid = str(art.get("run_id") or "")
    raw = (art.get("symbol") or r.get("symbol") or "").upper()
    parts = [p.replace("USDT", "").replace("USDC", "") for p in re.split(r"[+/,]", raw) if p]
    parts = [p for p in parts if p and p not in ("PORTFOLIO", "BASKET", "BASKET5")]
    tags = ((" #" + " #".join(parts[:2]) + " #Crypto") if len(parts) > 1
            else (" " + tags_for(parts[0]) if parts else " #Crypto #Trading"))
    texts, (sym, tfw, desc) = styles_of(r)
    pool = texts.get(style) or [v for k in HOOK_STYLES for v in texts.get(k, [])]
    hooks = STYLE_HOOKS.get(style) or [h for k in HOOK_STYLES for h in STYLE_HOOKS.get(k, [])]
    if not pool or not hooks:
        return ""
    # body order stays pool order (fullest recipe first); only the hook is
    # rotated, so different run_ids open differently without ever hiding the
    # most complete rule text behind a shorter variant
    rot = _stable(rid, style) % len(hooks)
    hooks = hooks[rot:] + hooks[:rot]

    for body in pool:
        # name the instrument when the rule text does not already carry it;
        # a prefix reads better than a trailing "on $SOL" after a stop clause
        if parts and parts[0] not in body.upper():
            body = f"{sym}: {body}"
        if body and body[-1] not in ".!?":
            body += "."
        for hook in hooks:
            h = f"{hook} {body}"
            # tags before CTA wording: hashtags buy reach, the CTA is cosmetic,
            # so the longest CTA is only spent when the hashtags already fit.
            # the pair-only tier keeps at least one hashtag on tweets whose
            # full recipe leaves no room for the full tag line.
            for tag_line in (tags + " #Backtest", tags,
                             (" #" + parts[0]) if parts else "", ""):
                for cta in ("Full recipe, params and artifact: " + LINK,
                            "Full recipe + artifact: " + LINK,
                            "Recipe + artifact: " + LINK,
                            "Recipe: " + LINK,
                            LINK):
                    # X's weighted count (URL 23, emoji 2), 278 keeps a
                    # margin under the 280 limit
                    tweet = " ".join(x for x in [h, cta, tag_line, "NFA"] if x)
                    if x_len(tweet) <= 278:
                        assert_clean(tweet)
                        return tweet
    return ""

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

def _styles_available(r):
    texts, _ = styles_of(r)
    return {s for s in HOOK_STYLES if texts.get(s)}

def _has_recipe(texts):
    """True when a body states the actual entry rule, not just a label —
    a mechanism line alone is not publishing the strategy."""
    for b in texts.get("curiosity", []):
        low = b.lower()
        if "entry" in low or re.match(r"^(long|short)\s*=", low):
            return True
    return False

def build(days=0, outdir=None, start=None, posts=None):
    outdir = outdir or os.path.join(REPO, "content", "posts")
    rows = load_rows()
    elig, skipped = eligibility(rows)
    ordered = order_rows(elig)
    need = (posts if posts else 0) or days * 3

    # ── rotation picker: slot i wants HOOK_STYLES[i % 4]; take the first
    # eligible row that offers that style (fallback: any style), while
    # deduping content-key AND (adapter, symbol) so no story repeats.
    picked, styles, seen, seen_pair, seen_sym, seen_spec, dup_story = [], [], set(), set(), set(), set(), 0
    pool = list(ordered)
    while len(picked) < need and pool:
        want = HOOK_STYLES[len(picked) % len(HOOK_STYLES)]
        # rank every candidate lexicographically:
        #   1. the rotated style (verify() checks the rotation order),
        #   2. a full recipe over a mechanism label (publishing the strategy
        #      IS the job — a label-only tweet is a weak post),
        #   3. a symbol not yet used in this pack (variety).
        # hard filters (posted / same artifact / same pair / same spec) apply
        # before ranking.
        chosen, chosen_style = None, None
        best_rank = None
        for r in pool:
            k = _content_key(r)
            pair_key = (r.get("adapter"), r["_art"].get("symbol"))
            sym_key = (r["_art"].get("symbol") or r.get("symbol") or "")
            # one strategy story per pack: the spec IS the story now
            spec_key = spec_id_for(str(r.get("adapter") or ""), r.get("name"))
            if k in seen or pair_key in seen_pair or \
                    (spec_key is not None and spec_key in seen_spec):
                continue
            texts, _ = styles_of(r)
            if not texts:
                continue
            if want in texts:
                style_rank, style = 0, want
            else:
                style_rank, style = 1, sorted(texts)[0]
            rank = (style_rank,
                    0 if _has_recipe(texts) else 1,
                    0 if sym_key not in seen_sym else 1)
            if best_rank is None or rank < best_rank:
                best_rank, chosen, chosen_style = rank, r, style
                if rank == (0, 0, 0):
                    break
        if chosen is None:
            break
        pool.remove(chosen)
        seen.add(_content_key(chosen))
        seen_pair.add((chosen.get("adapter"), chosen["_art"].get("symbol")))
        seen_sym.add(chosen["_art"].get("symbol") or chosen.get("symbol") or "")
        _sk = spec_id_for(str(chosen.get("adapter") or ""), chosen.get("name"))
        if _sk is not None:
            seen_spec.add(_sk)
        picked.append(chosen)
        styles.append(chosen_style)
    skipped = dict(skipped)
    skipped["duplicate_story"] = dup_story
    os.makedirs(outdir, exist_ok=True)
    now = datetime.now(timezone.utc)
    if start:
        day0 = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        day0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # three slots per day, chosen hours
    slots = [("A", 9, 0), ("B", 14, 0), ("C", 21, 0)]
    slot_times = []
    d = day0
    while len(slot_times) < len(picked):
        for slot, hh, mm in slots:
            dt = d.replace(hour=hh, minute=mm)
            if dt > now:
                slot_times.append((slot, dt))
        d += timedelta(days=1)
    manifest = []
    for r, style, (slot, dt) in zip(picked, styles, slot_times):
        tweet = single_tweet(r, style)
        if not tweet:
            raise ValueError("no tweet for %s (%s)" % (r.get("run_id"), style))
        assert_clean(tweet)
        sym = (r.get("symbol") or "").upper()
        tf = str(r.get("tf") or "").lower()
        rid = str(r.get("run_id") or "")
        slug = slugify(f"{dt:%Y-%m-%d}-{slot}-{r.get('adapter')}-{sym}-{tf}-{rid[:6]}")
        fname = f"{slug}.md"
        path = os.path.join(outdir, fname)
        label = r["_label"]
        with open(path, "w", encoding="utf-8") as f:
            # header carries NO digits — guard scans the whole file; dates live in SCHEDULE.md
            f.write(f"# Slot {slot} — {sym} — {style}\n\n")
            f.write("INSTRUCTIONS (not part of the tweet): paste the block below as ONE tweet ")
            f.write("using X's Schedule button. Numbers from artifact " + rid + "\n\n")
            f.write(tweet + "\n")
        manifest.append({
            "file": f"posts/{fname}", "datetime_utc": dt.isoformat(),
            "slot": slot, "style": style, "run_id": rid, "adapter": r.get("adapter"),
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
        f.write("Dates/times UTC. One tweet per post; paste the block from `posts/<file>` ")
        f.write("using X's Schedule button. The verdict is NOT in the tweet — it lives in the repo.\n\n")
        f.write("| When (UTC) | Slot | Style | File | Verdict |\n|---|---|---|---|---|\n")
        for mrec in manifest:
            f.write(f"| {mrec['datetime_utc'][:16].replace('T',' ')} | {mrec['slot']} | "
                    f"{mrec['style']} | `{mrec['file']}` | {mrec['verdict']} |\n")
    # one copy-paste digest with the complete text of every post
    with open(os.path.join(REPO, "content", "WEEK.md"), "w", encoding="utf-8") as f:
        f.write("# Full text — every scheduled post\n\n")
        f.write("Copy each tweet block. Times are UTC. No verdict appears in any tweet.\n\n")
        for mrec in manifest:
            p = os.path.join(outdir, os.path.basename(mrec["file"]))
            lines = open(p, encoding="utf-8").read().splitlines()
            blocks = [b for b in lines[4:] if b.strip()]
            f.write(f"## {mrec['datetime_utc'][:16].replace('T',' ')} UTC · slot {mrec['slot']} · {mrec['style']}\n\n")
            f.write(f"`{mrec['adapter']} · {mrec['symbol']} · {mrec['tf']} · artifact {mrec['run_id']}`\n\n")
            for i, b in enumerate(blocks, 1):
                f.write(f"**Tweet {i}**\n\n> {b}\n\n")
    print(f"picked {len(manifest)} posts -> {outdir}")
    print("styles:", styles)
    print("skips:", dict(skipped))

def _post_tweet(path):
    """The single tweet block of a post file (everything after the instructions line)."""
    lines = open(path, encoding="utf-8").read().splitlines()
    blocks = [b for b in lines[4:] if b.strip()]
    return blocks

def verify():
    posts_dir = os.path.join(REPO, "content", "posts")
    files = sorted(f for f in os.listdir(posts_dir) if f.endswith(".md"))
    bad = []
    hooks = {}
    styles = []
    for f in files:
        p = os.path.join(posts_dir, f)
        rc = subprocess.call([sys.executable, os.path.join(REPO, "code", "vrun.py"),
                              "guard", "--report", p], stdout=subprocess.DEVNULL)
        if rc != 0:
            bad.append(f + " (guard)")
            continue
        text = open(p, encoding="utf-8").read()
        tweets = _post_tweet(p)
        if len(tweets) != 1:
            bad.append(f + " (block-count=%d, want 1)" % len(tweets))
            continue
        tweet = tweets[0]
        try:
            assert_clean(tweet)
        except ValueError as e:
            bad.append(f + " (banned: %s)" % str(e)[:60])
            continue
        if "github.com/mancas21/BACKTEST" not in tweet:
            bad.append(f + " (no link)")
            continue
        if x_len(tweet) > 280:
            bad.append(f + " (len %d)" % x_len(tweet))
            continue
        # dedupe: same hook text or same style twice is a repetition bug
        head = tweet.split(" github.com")[0][:60]
        if head in hooks:
            bad.append(f + " (dup hook of %s)" % hooks[head])
        else:
            hooks[head] = f
        m = re.search(r"— (\w+) — (\w+)\s*$", text.splitlines()[0])
        if m:
            styles.append(m.group(2))
    # rotation check: styles must cycle curiosity/shock/contradiction/cost
    want = [HOOK_STYLES[i % len(HOOK_STYLES)] for i in range(len(styles))]
    if styles and styles != want:
        bad.append("rotation is %s, want %s" % (styles, want))
    print(f"guard OK: {len(files) - len(bad)}/{len(files)}")
    for f in bad:
        print("REFUSED:", f)
    return 1 if bad else 0

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--days", type=int, default=30)
    b.add_argument("--posts", type=int, default=None,
                   help="exact number of posts (overrides --days)")
    b.add_argument("--out", default=os.path.join(REPO, "content", "posts"))
    b.add_argument("--start", default=None, help="UTC date YYYY-MM-DD (past slots are skipped)")
    sub.add_parser("verify")
    args = ap.parse_args()
    if args.cmd == "build":
        build(args.days, args.out, args.start, args.posts)
    elif args.cmd == "verify":
        sys.exit(verify())

if __name__ == "__main__":
    main()
