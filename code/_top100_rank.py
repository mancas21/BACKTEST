"""_top100_rank.py — rank every tested strategy in results/runs/ by its
artifact-measured net return. Read-only over the artifact store: every number
it emits comes from one artifact JSON, cited by run_id.

Excluded on purpose (not single strategies): gatecal (null calibration),
q10diag (diagnostics), gate2 (re-scoring of pack50b prompts), mp20/mps20/cbot
(pack-level aggregates), cbpack (same pack as cbpackf, WITHOUT funding —
cbpackf is the honest representation of those cells).

Output: code/_top100_rank.json (all rows) + stdout top-N table.
"""

import glob
import json
import os

RUNS = os.path.join(os.path.dirname(__file__), "..", "results", "runs")

EXCLUDE_ADAPTERS = {"gatecal", "q10diag", "gate2", "mp20", "mps20", "cbot", "cbpack"}

# XRP neutral: the two memory-cited citable artifacts; other xrpneutral
# artifacts are scale/refresh variants of the same book and are folded away.
XRP_CITABLE = {"295c21687960fadd", "fe5c359a22c8dffe"}


def strategy_label(m, d, fallback):
    for k in ("strategy_name", "name"):
        v = m.get(k)
        if isinstance(v, str) and v:
            code = m.get("prompt_code") or m.get("strategy_id") or ""
            return f"{code} {v}".strip() if isinstance(code, str) and code else v
    for k in ("strategy_id", "prompt_code", "strat", "card"):
        v = m.get(k)
        if isinstance(v, str) and v:
            return v
    p = d.get("params") or {}
    for k in ("strat", "id", "name", "card"):
        v = p.get(k)
        if v is not None:
            return f"{k}={v}"
    return fallback


def net_return(m):
    for k in ("return_pct", "return_base_pct", "ret_pct", "full_pct"):
        v = m.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    # top10 adapter: full_pct is a dict of percent mirrors
    fp = m.get("full_pct")
    if isinstance(fp, dict) and isinstance(fp.get("net_pct"), (int, float)):
        return float(fp["net_pct"])
    return None


def profit_factor(m):
    for k in ("profit_factor", "pf", "PF", "is_pf", "holdout_pf", "pf_strict"):
        v = m.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    full = m.get("full")
    if isinstance(full, dict) and isinstance(full.get("pf"), (int, float)):
        return float(full["pf"])
    return None


def trades(m):
    for k in ("n_trades", "trades", "n", "is_n", "holdout_n"):
        v = m.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def max_dd(m):
    for k in ("max_dd_pct", "maxDD_%", "dd_pct", "p95_dd_pct"):
        v = m.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    fp = m.get("full_pct")
    if isinstance(fp, dict) and isinstance(fp.get("mdd_pct"), (int, float)):
        return float(fp["mdd_pct"])
    return None


def gates_passed(m, adapter):
    if adapter == "top10":
        # campaign gate set of results/top10_report.md: screen full+OOS,
        # concentration, thirds, bootstrap significance — all artifact fields
        fp = m.get("full_pct") or {}
        flags = [
            bool(m.get("gate_full") and m.get("gate_oos")),
            m.get("top5_pnl_share") is not None and m["top5_pnl_share"] < 1.0
            and m.get("net_without_top5") is not None and m["net_without_top5"] > 0,
            m.get("thirds_green") is not None and m["thirds_green"] >= 2,
            bool(m.get("bootstrap")) and m["bootstrap"].get("ci_low") is not None
            and m["bootstrap"]["ci_low"] > 0,
        ]
        return (sum(flags), len(flags))
    if adapter in ("pack50", "pack50b", "pack50c", "pack50d"):
        flags = [m.get(f"g{i}_pf" if i == 1 else f"g{i}_{n}") for i, n in
                 ((1, "pf"), (2, "n"), (3, "halves"), (4, "years"), (5, "beats_bh"), (6, "conc"))]
        flags = [f for f in flags if isinstance(f, bool)]
        return (sum(flags), len(flags)) if flags else None
    if adapter == "qs":
        g = m.get("gates") or {}
        vals = [v for k, v in g.items() if isinstance(v, bool) and k.startswith("g")]
        return (sum(vals), len(vals)) if vals else None
    return None


def bench(m):
    for k in ("bh_return_pct", "bench_ret_pct"):
        v = m.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def extract(adapter, d):
    m = d.get("metrics", {})
    rows = []
    if adapter in ("cbpackf", "eqpack"):
        for t in d.get("tables", []):
            if not isinstance(t, dict) or t.get("status", "ok") not in ("ok", None):
                continue
            net = t.get("net_%")
            if not isinstance(net, (int, float)):
                continue
            rows.append({
                "ret": float(net),
                "label": f"{t.get('id', '?')} {t.get('name', '')}".strip(),
                "pf": t.get("PF"),
                "n": t.get("trades"),
                "dd": t.get("maxDD_%"),
                "bh": t.get("buy_hold_%"),
            })
        return rows
    ret = net_return(m)
    if ret is None:
        return []
    rows.append({
        "ret": ret,
        "label": strategy_label(m, d, d.get("strategy", adapter)),
        "pf": profit_factor(m),
        "n": trades(m),
        "dd": max_dd(m),
        "bh": bench(m),
    })
    return rows


def main():
    out = []
    for path in sorted(glob.glob(os.path.join(RUNS, "*.json"))):
        rid = os.path.basename(path)[:-5]
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            continue
        # the top-level `strategy` key is the ADAPTERS key that built the
        # artifact (set by make_artifact) — the truthful adapter; the
        # provenance copy is hardcoded to "qs" inside qs_run.run_one, which
        # misfiled the qsf/qsb/qsc generations.
        adapter = d.get("strategy") or (d.get("provenance") or {}).get("adapter") \
            or "?"
        if adapter in EXCLUDE_ADAPTERS:
            continue
        if adapter == "xrpneutral":
            if rid not in XRP_CITABLE:
                continue
            m = d.get("metrics", {})
            ret = net_return(m)
            if ret is None:
                continue
            out.append({
                "run_id": rid, "adapter": adapter,
                "symbol": d.get("symbol"), "tf": d.get("timeframe"),
                "label": "XRP delta-neutral grid "
                         + ("v1 (10k, 0.25x/lvl)" if rid == "295c21687960fadd" else "v2 (25 USDT x 10x)"),
                "ret": ret, "pf": profit_factor(m), "n": trades(m), "dd": max_dd(m),
                "bh": m.get("bh_return_pct"),
                "fee": m.get("fee_bps_per_side"), "slip": m.get("slippage_bps_per_side"),
                "funding": m.get("funding_charged", True),
                "created": d.get("created_utc"),
                "gates": gates_passed(m, adapter),
            })
            continue
        symbol = d.get("symbol")
        tf = d.get("timeframe")
        m = d.get("metrics", {})
        if adapter == "pack100" and str(strategy_label(m, d, "")).startswith("F68"):
            # pack100_report.md: the one passer was DISQUALIFIED as a sizing
            # artifact (inverted short stop + ~100:1 one-candle-stop sizing).
            # Its return is a documented bug, not a measurement.
            continue
        for r in extract(adapter, d):
            out.append({
                "run_id": rid, "adapter": adapter, "symbol": symbol, "tf": tf,
                "label": r["label"], "ret": r["ret"], "pf": r["pf"], "n": r["n"],
                "dd": r["dd"], "bh": r["bh"], "window": m.get("window"),
                "fee": m.get("fee_bps_per_side") or m.get("cost_bps_per_side"),
                "slip": m.get("slippage_bps_per_side") or m.get("slip_bps_per_side"),
                "funding": m.get("funding_charged"),
                "created": d.get("created_utc"),
                "gates": gates_passed(m, adapter),
            })

    # dedupe: (adapter, label, symbol, tf) -> one artifact per strategy.
    # A 'full'-window artifact beats a slice (no window-picking: the full
    # history IS the widest measurement); ties break on return.
    best = {}
    for r in out:
        key = (r["adapter"], str(r["label"]), str(r["symbol"]), str(r["tf"]))
        cur = best.get(key)
        if cur is None:
            best[key] = r
            continue
        r_full = r.get("window") == "full"
        c_full = cur.get("window") == "full"
        if r_full != c_full:
            if r_full:
                best[key] = r
        elif (r["ret"] or -1e18) > (cur["ret"] or -1e18):
            best[key] = r

    # a one-trade artifact is not a tested strategy
    rows = [r for r in best.values()
            if not isinstance(r.get("n"), (int, float)) or r["n"] >= 10]
    rows = sorted(rows, key=lambda r: r["ret"] or -1e18, reverse=True)
    with open(os.path.join(os.path.dirname(__file__), "_top100_rank.json"), "w") as f:
        json.dump(rows, f, indent=1)
    print(f"strategies after dedupe: {len(rows)}")
    for i, r in enumerate(rows[:110], 1):
        g = f"{r['gates'][0]}/{r['gates'][1]}" if r["gates"] else "-"
        pf = f"{r['pf']:.2f}" if isinstance(r["pf"], (int, float)) else "-"
        n = f"{int(r['n'])}" if isinstance(r["n"], (int, float)) else "-"
        print(f"{i:4d} {r['ret']:>12.2f}%  PF {pf:>6}  n {n:>6}  {r['adapter']:10s} "
              f"{str(r['symbol'])[:12]:12s} {str(r['tf']):5s} G{g:4s} {r['label'][:44]:44s} {r['run_id']}")


if __name__ == "__main__":
    main()
