"""_top100_rank2.py — build the ranked table behind results/top100_2026-10-31.md.

Read-only over the artifact store. Every number the report prints comes from
one artifact; the sort key is computed here and never printed.

Universe rules (stated so the list can be audited):

  * one row = one measured book, keyed on
    (adapter, strategy label, symbol, timeframe);
  * pack-level aggregates and diagnostics are excluded: gatecal, q10diag,
    gate2, mp20, mps20, cbot, cbpack.  `cbpack` is the SAME pack as `cbpackf`
    without funding charged, so `cbpackf` is the honest copy;
  * a book needs at least thirty closed trades (the v1 gate floor);
  * profit factor finite and above one, net return positive, drawdown below
    ruin (< 100) and no liquidated trade;
  * REPRODUCIBILITY IS A HARD FILTER: a book is listed only if one of its
    artifacts re-runs bit-for-bit today (`pverify`, rc 0).  STALE (data grew
    since the artifact) and REFUSED (engine bytes changed) books are counted
    in the report but never ranked.  Among duplicates of the same book the
    pick prefers the reproducible artifact, then the widest measurement --
    never the best return.
  * the delta-neutral XRP grid is pinned to its cited v1 artifact
    (`295c21687960fadd`) because the adapter also holds parameter sweeps.

Ordering: the validated book first, then profit factor descending (tie-break
trade count).  Profit factor is a measured field in every artifact.
"""

import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "..", "results", "runs")
OUT = os.path.join(HERE, "_top100_rank2.json")
STATUS = os.path.join(HERE, "_top100_status.json")

EXCLUDE = {"gatecal", "q10diag", "gate2", "mp20", "mps20", "cbot", "cbpack"}
MIN_TRADES = 30
VALID_ID = re.compile(r"^[0-9a-f]{16}$")
XRP_PIN = {"295c21687960fadd": "v1"}


def first_num(m, keys):
    for k in keys:
        v = m.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
    return None


def code_of(m, d):
    for k in ("prompt_code", "strategy_id", "prompt_num"):
        v = m.get(k)
        if isinstance(v, str) and v:
            return v
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return str(int(v))
    p = d.get("params") or {}
    for k in ("strat", "cand", "card", "id"):
        v = p.get(k)
        if isinstance(v, str) and v:
            return v
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return str(int(v))
    return ""


def net_return(m):
    return first_num(m, ("return_pct", "return_base_pct", "ret_pct", "full_pct"))


def profit_factor(m):
    return first_num(m, ("profit_factor", "pf", "PF", "pack_pf", "pf_pct"))


def trades(m):
    return first_num(m, ("n_trades", "trades", "n", "is_n", "holdout_n"))


def drawdown(m):
    return first_num(m, ("max_dd_pct", "maxDD_%", "dd_pct", "p95_dd_pct"))


def label_of(m, d, adapter, rid):
    name = m.get("strategy_name") or m.get("name") or ""
    code = code_of(m, d)
    if adapter == "xrpneutral":
        return "XRP delta-neutral grid " + XRP_PIN.get(rid, "variant")
    if adapter == "pack50" and code:
        code = "S" + code            # the pack-50 report calls prompt 46 "S46"
    if adapter == "cand7" and code:
        return "C" + code
    if code and name and not str(name).startswith(code):
        return f"{code} {name}".strip()
    if name:
        return str(name)
    if code:
        return str(code)
    return adapter


def gates_passed(m):
    for key in ("v1", "v2", "gates"):
        g = m.get(key)
        if isinstance(g, dict):
            flags = [v for k, v in g.items() if isinstance(v, bool)]
            if flags:
                return [sum(flags), len(flags)]
    flags = [m.get(k) for k in ("g1_pf", "g2_n", "g3_halves", "g4_years",
                                "g5_beats_bh", "g6_conc")]
    flags = [f for f in flags if isinstance(f, bool)]
    return [sum(flags), len(flags)] if flags else None


def rows_of(adapter, d, rid):
    m = d.get("metrics") or {}
    sym, tf = d.get("symbol"), d.get("timeframe")
    bars = first_num(m, ("bars", "n_bars"))
    out = []
    if adapter in ("cbpackf", "eqpack"):
        for t in d.get("tables") or []:
            if not isinstance(t, dict) or t.get("status", "ok") not in ("ok", None):
                continue
            net = first_num(t, ("net_%", "net_pct", "net"))
            if net is None:
                continue
            out.append(dict(
                run_id=rid, adapter=adapter, symbol=sym, tf=tf, bars=bars,
                window=m.get("window"),
                label=(str(t.get("id", "?")) + " " + str(t.get("name", ""))).strip(),
                ret=net, pf=first_num(t, ("PF", "pf")),
                n=first_num(t, ("trades", "n_trades")),
                dd=first_num(t, ("maxDD_%", "max_dd_pct")),
                liquidated=None, gates=None,
            ))
        return out
    ret = net_return(m)
    if ret is None:
        return []
    out.append(dict(
        run_id=rid, adapter=adapter, symbol=sym, tf=tf, bars=bars,
        window=m.get("window"), label=label_of(m, d, adapter, rid),
        ret=ret, pf=profit_factor(m), n=trades(m), dd=drawdown(m),
        liquidated=first_num(m, ("liquidated_trades",)), gates=gates_passed(m),
    ))
    return out


def collect():
    raw = []
    seen_adapters = set()
    for path in sorted(glob.glob(os.path.join(RUNS, "*.json"))):
        rid = os.path.basename(path)[:-5]
        if not VALID_ID.match(rid):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                d = json.load(fh)
        except Exception:
            continue
        adapter = (d.get("provenance") or {}).get("adapter") or d.get("strategy", "?")
        seen_adapters.add(adapter)
        if adapter in EXCLUDE:
            continue
        if adapter == "xrpneutral" and rid not in XRP_PIN:
            continue
        m = d.get("metrics") or {}
        d["run_id"] = rid
        if adapter == "pack100" and "68" in str(code_of(m, d)):
            continue          # sizing artifact: inverted short stop, documented bug
        raw.extend(rows_of(adapter, d, rid))
    return raw, seen_adapters


def main():
    status = {}
    if os.path.exists(STATUS):
        with open(STATUS, encoding="utf-8") as fh:
            status = json.load(fh)
    raw, seen_adapters = collect()

    groups = {}
    for r in raw:
        key = (r["adapter"], str(r["label"]), str(r["symbol"]), str(r["tf"]))
        groups.setdefault(key, []).append(r)

    picked, unverified = [], []
    for key, cands in groups.items():
        cands.sort(key=lambda r: (
            0 if status.get(r["run_id"]) == 0 else 1,
            0 if r.get("window") == "full" else 1,
            -(r.get("bars") or 0), -(r.get("n") or 0), r["run_id"]))
        best = cands[0]
        best["n_artifacts"] = len(cands)
        best["status"] = status.get(best["run_id"])
        if best["status"] == 0:
            picked.append(best)
        else:
            unverified.append(best)

    def eligible(r):
        return (r["n"] is not None and r["n"] >= MIN_TRADES
                and r["pf"] is not None and r["pf"] > 1.0
                and r["ret"] is not None and r["ret"] > 0
                and r["dd"] is not None and abs(r["dd"]) < 100.0
                and not (r["liquidated"] or 0))

    books = [r for r in picked if eligible(r)]
    books.sort(key=lambda r: (0 if r["adapter"] == "xrpneutral" else 1,
                              -r["pf"], -(r["n"] or 0), r["run_id"]))
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(books, fh, indent=1)

    near = [r for r in unverified if eligible(r)]
    with open(os.path.join(HERE, "_top100_near.json"), "w",
              encoding="utf-8", newline="\n") as fh:
        json.dump([{k: r[k] for k in ("run_id", "adapter", "label", "symbol",
                                      "tf", "ret", "pf", "n", "status")}
                   for r in near], fh, indent=1)
    counts = dict(files=len(glob.glob(os.path.join(RUNS, "*.json"))),
                  adapters=len(seen_adapters),
                  books=len(groups), ranked=len(books), near=len(near),
                  labels=len({(r["adapter"], r["label"]) for r in books}))
    with open(os.path.join(HERE, "_top100_counts.json"), "w",
              encoding="utf-8", newline="\n") as fh:
        json.dump(counts, fh, indent=1)
    print(counts)
    print(f"books picked (one artifact per book): {len(groups)}")
    print(f"reproducible books meeting every floor: {len(books)}")
    print(f"net-positive books with no reproducible artifact: {len(near)}")
    print(f"distinct labels among the ranked books: "
          f"{len({(r['adapter'], r['label']) for r in books})}")
    for i, r in enumerate(books[:110], 1):
        print(f"{i:4d} PF {r['pf']:6.3f} n {int(r['n']):5d} ret {r['ret']:9.2f}% "
              f"dd {r['dd']:8.2f} {r['adapter']:9s} {str(r['symbol'])[:10]:10s} "
              f"{str(r['tf']):4s} {str(r['label'])[:40]:40s} {r['run_id']}")


if __name__ == "__main__":
    main()
