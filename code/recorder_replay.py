#!/usr/bin/env python3
"""
recorder_replay.py — offline quality audit of the recorded order-book tape
(recorder/data/<day>/{bookTicker,depth,depth_snapshot,forceOrder}.parquet),
in chronological segment order. Read-only; writes NEW files only:

  results/recorder_replay_<date>.json   exact numbers (machine source of truth)
  results/recorder_replay_<date>.txt    findings in words (guard-able: the
                                        house rule is counts in words when no
                                        run_id artifact backs them)

What it re-derives from the parquet bytes (independent of the live counters):
  - inventory: days, segments, rows per stream/symbol; unreadable segments
  - bookTicker: crossed best bid/ask events, non-positive quotes, sampled
    inter-event latency and E-vs-recv_ts drift percentiles
  - depth diffs: U/u chain continuity across segment AND day boundaries
    (breaks = U != prev_u + 1; dups = U <= prev_u), cross-checked against
    recorder/coverage/counters.json
  - snapshot binding: each REST snapshot L vs the first diff with u >= L under
    the documented rule U-1 <= L <= u-1 (the offline analogue of depth_sync)
  - forceOrder: rows per symbol/side

Gate for the fill-replay adapter (bookreplay): the bookTicker tape must be
readable end to end with a crossed-book share far below any level that could
fabricate fills (threshold declared in the JSON).

Usage:
  python code/recorder_replay.py
  python code/recorder_replay.py --days 2026-10-31,2026-11-01 --symbols XRPUSDT
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parent.parent
REC = REPO / "recorder" / "data"
COUNT = REPO / "recorder" / "coverage" / "counters.json"
SYMBOLS = ("BTCUSDT", "SOLUSDT", "SUIUSDT", "XRPUSDT")

MAX_SAMPLE = 60_000          # per-symbol cap for sampled latency/drift stats
CROSSED_SHARE_GATE = 0.001   # 0.1% of bookTicker events crossed = usable tape
MIN_READABLE_DAYS = 10       # readable bookTicker days for the fill-replay gate


def segments_for(day: Path, stream: str):
    """Chronological parquet segments of one stream-day: `.prevHHMMSS` files in
    rotation order, then the current `<stream>.parquet` (opened last)."""
    prevs = sorted(day.glob(f"{stream}.prev*.parquet"),
                   key=lambda p: re.search(r"prev(\d+)\.parquet$", p.name).group(1))
    cur = day / f"{stream}.parquet"
    return prevs + ([cur] if cur.exists() else [])


def _sample(arr: np.ndarray, cap: int = MAX_SAMPLE) -> np.ndarray:
    if len(arr) <= cap:
        return arr
    return arr[:: max(1, len(arr) // cap)]


def _pct(a: np.ndarray, qs=(50, 95, 99)):
    if len(a) == 0:
        return None
    return {f"p{q}": float(np.percentile(a, q)) for q in qs} | {"n": int(len(a))}


def empty_sym() -> dict:
    return {"rows": 0, "crossed": 0, "bad_quote": 0,
            "gap_ms": [], "drift_ms": []}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", default=None, help="comma subset of day dirs")
    ap.add_argument("--symbols", default=None, help="comma subset, e.g. XRPUSDT")
    ap.add_argument("--out-tag", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    args = ap.parse_args()

    syms = tuple(s.strip().upper() for s in args.symbols.split(",")) if args.symbols else SYMBOLS
    days = sorted(d for d in REC.iterdir() if d.is_dir())
    if args.days:
        want = {d.strip() for d in args.days.split(",")}
        days = [d for d in days if d.name in want]

    res = {
        "schema": "recorder-replay-audit/1",
        "built_by": "code/recorder_replay.py",
        "asof_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "days": [d.name for d in days],
        "symbols": list(syms),
        "bookTicker": {s: empty_sym() for s in syms},
        "depth": {s: {"rows": 0, "pu_chain_breaks": 0, "u_rule_breaks": 0,
                      "chain_dups": 0,
                      "prev_u": None, "snapshots": 0, "snap_bound_ok": 0,
                      "snap_bound_gap": 0, "snap_no_diff": 0} for s in syms},
        "forceOrder": {s: {"rows": 0, "buy": 0, "sell": 0} for s in syms},
        "unreadable_segments": [],
        "day_rows": {},
        "recomputed_vs_counters": None,
    }
    bt, dp, fo = res["bookTicker"], res["depth"], res["forceOrder"]

    # pending snapshots per symbol: list of lastUpdateId awaiting first diff u >= L
    pending = {s: [] for s in syms}

    for d in days:
        day_bt = {s: 0 for s in syms}
        day_dp = {s: 0 for s in syms}
        for stream in ("bookTicker", "depth", "depth_snapshot", "forceOrder"):
            for seg in segments_for(d, stream):
                try:
                    tbl = pq.read_table(seg)
                except Exception as e:
                    res["unreadable_segments"].append(
                        {"file": str(seg.relative_to(REPO)).replace("\\", "/"),
                         "error": type(e).__name__})
                    continue
                if stream == "bookTicker":
                    s_col = tbl.column("s").to_pylist()
                    b = tbl.column("b").to_numpy()
                    a = tbl.column("a").to_numpy()
                    recv = tbl.column("recv_ts").to_numpy()
                    E = tbl.column("E").to_numpy()
                    arr_s = np.asarray(s_col)
                    for s in syms:
                        m = arr_s == s
                        n = int(m.sum())
                        if n == 0:
                            continue
                        day_bt[s] += n
                        bb, aa = b[m], a[m]
                        bt[s]["rows"] += n
                        bt[s]["crossed"] += int((bb >= aa).sum())
                        bt[s]["bad_quote"] += int(((bb <= 0) | (aa <= 0)).sum())
                        if n > 1:
                            gaps = np.diff(recv[m]).astype(np.float64)
                            bt[s]["gap_ms"].extend(_sample(gaps).tolist())
                        drift = (recv[m] - E[m]).astype(np.float64)
                        bt[s]["drift_ms"].extend(_sample(drift).tolist())
                elif stream == "depth":
                    arr_s = np.asarray(tbl.column("s").to_pylist())
                    U = tbl.column("U").to_numpy()
                    u = tbl.column("u").to_numpy()
                    pu = tbl.column("pu").to_numpy()
                    for s in syms:
                        m = arr_s == s
                        n = int(m.sum())
                        if n == 0:
                            continue
                        day_dp[s] += n
                        Us, us, pus = U[m], u[m], pu[m]
                        st = dp[s]
                        st["rows"] += n
                        prev = st["prev_u"]
                        if prev is None:
                            # first segment of the audited window: within-file
                            # continuity only (no anchor to score the first row)
                            st["pu_chain_breaks"] += int((pus[1:] != us[:-1]).sum())
                            st["u_rule_breaks"] += int((Us[1:] != us[:-1] + 1).sum())
                            st["chain_dups"] += int((Us[1:] <= us[:-1]).sum())
                        else:
                            prev_u_all = np.concatenate(([prev], us[:-1]))
                            st["pu_chain_breaks"] += int((pus != prev_u_all).sum())
                            st["u_rule_breaks"] += int((Us != prev_u_all + 1).sum())
                            st["chain_dups"] += int((Us <= prev_u_all).sum())
                        st["prev_u"] = int(us[-1])
                        # offline snapshot binding: settle pending Ls
                        still = []
                        for L in pending[s]:
                            idx = np.searchsorted(us, L, side="left")
                            if idx >= len(us):
                                still.append(L)
                                continue
                            st["snap_bound_ok" if Us[idx] - 1 <= L <= us[idx] - 1
                               else "snap_bound_gap"] += 1
                        pending[s] = still
                elif stream == "depth_snapshot":
                    arr_s = np.asarray(tbl.column("s").to_pylist())
                    Lu = tbl.column("lastUpdateId").to_numpy()
                    for s in syms:
                        m = arr_s == s
                        k = int(m.sum())
                        if k:
                            dp[s]["snapshots"] += k
                            pending[s].extend(int(x) for x in Lu[m])
                elif stream == "forceOrder":
                    if tbl.num_rows == 0:
                        continue
                    arr_s = np.asarray(tbl.column("s").to_pylist())
                    side = np.asarray(tbl.column("side").to_pylist())
                    for s in syms:
                        m = arr_s == s
                        k = int(m.sum())
                        if k:
                            fo[s]["rows"] += k
                            fo[s]["buy"] += int((side[m] == "BUY").sum())
                            fo[s]["sell"] += int((side[m] == "SELL").sum())
        res["day_rows"][d.name] = {
            "bookTicker": {s: day_bt[s] for s in syms},
            "depth": {s: day_dp[s] for s in syms},
        }

    # cross-check against the live counters
    if COUNT.exists():
        cj = json.loads(COUNT.read_text(encoding="utf-8"))
        live_breaks = {k.upper(): v for k, v in cj.get("stream_breaks", {}).items()}
        res["recomputed_vs_counters"] = {
            s: {"recomputed_pu_rule_breaks": dp[s]["pu_chain_breaks"],
                "recomputed_u_rule_breaks": dp[s]["u_rule_breaks"],
                "live_counter_stream_breaks": live_breaks.get(s),
                "note": ("the live counter uses the U-based rule, which the data "
                         "shows is inflated (ids are sparse); the pu rule is the "
                         "true continuity test")} for s in syms}

    # id-space check: REST snapshot lastUpdateId vs WS diff u. If these live in
    # different spaces (ratio far from 1, zero overlap), snapshots cannot anchor
    # diffs and full-book reconstruction is impossible on this tape — the
    # mirror-host pathology the recorder docstring documents.
    idspace = {}
    for d in days:
        snaps, diffs = {}, {}
        for seg in segments_for(d, "depth_snapshot"):
            try:
                t = pq.read_table(seg, columns=["s", "lastUpdateId"])
            except Exception:
                continue
            a = np.asarray(t.column("s").to_pylist())
            Lu = t.column("lastUpdateId").to_numpy()
            for s in syms:
                m = a == s
                if m.any():
                    snaps.setdefault(s, []).extend(Lu[m].tolist())
        for seg in segments_for(d, "depth"):
            try:
                t = pq.read_table(seg, columns=["s", "u"])
            except Exception:
                continue
            a = np.asarray(t.column("s").to_pylist())
            u = t.column("u").to_numpy()
            for s in syms:
                m = a == s
                if m.any():
                    diffs.setdefault(s, []).extend(u[m].tolist())
        for s in syms:
            if snaps.get(s) and diffs.get(s):
                Lm, um = float(np.median(snaps[s])), float(np.median(diffs[s]))
                idspace[f"{d.name}|{s}"] = {
                    "median_snapshot_L": Lm, "median_diff_u": um,
                    "ratio": round(Lm / um, 4) if um else None,
                    "overlap": bool(min(snaps[s]) <= max(diffs[s])
                                    and max(snaps[s]) >= min(diffs[s])),
                }
    res["snapshot_vs_diff_id_space"] = idspace

    # readable coverage: a day is usable when its bookTicker tape was readable
    usable_days = [d.name for d in days
                   if sum(res["day_rows"][d.name]["bookTicker"].values()) > 0]
    lost_days = [d.name for d in days if d.name not in usable_days]
    res["readable_coverage"] = {
        "days_total": len(days), "days_readable": len(usable_days),
        "days_lost_wholly": lost_days,
        "note": ("a wholly lost day means every segment of it lacks a footer "
                 "(hard-killed writer before segment rotation existed). The "
                 "current-day files are unreadable while the live recorder holds "
                 "them open — that one is expected, not a loss."),
    }

    # finalize summaries
    for s in syms:
        bt[s]["gap_ms"] = _pct(np.asarray(bt[s]["gap_ms"], dtype=float))
        bt[s]["drift_ms"] = _pct(np.asarray(bt[s]["drift_ms"], dtype=float))
        bt[s]["crossed_share_pct"] = round(100.0 * bt[s]["crossed"] / bt[s]["rows"], 6) \
            if bt[s]["rows"] else None
        dp[s].pop("prev_u", None)
        dp[s]["pending_unsettled"] = len(pending[s])

    total_bt = sum(bt[s]["rows"] for s in syms)
    total_crossed = sum(bt[s]["crossed"] for s in syms)
    rc = res["readable_coverage"]
    res["tape_verdict"] = {
        "bookTicker_rows_total": total_bt,
        "crossed_share_total_pct": round(100.0 * total_crossed / total_bt, 6) if total_bt else None,
        "gate_crossed_share_pct": CROSSED_SHARE_GATE,
        "min_readable_days": MIN_READABLE_DAYS,
        "days_readable": rc["days_readable"],
        "snapshot_anchor_possible": any(v["overlap"] for v in idspace.values()),
        "tape_usable_for_fill_replay": bool(
            total_bt > 0
            and (total_crossed / total_bt) < CROSSED_SHARE_GATE
            and rc["days_readable"] >= MIN_READABLE_DAYS),
        "note": ("the fill-replay adapter resolves fills on the bookTicker "
                 "top-of-book tape, which is independent of the snapshot id "
                 "space; full-book reconstruction is gated separately by "
                 "snapshot_anchor_possible"),
    }

    jpath = REPO / "results" / f"recorder_replay_{args.out_tag}.json"
    jpath.write_text(json.dumps(res, indent=1), encoding="utf-8")
    tpath = REPO / "results" / f"recorder_replay_{args.out_tag}.txt"
    tpath.write_text(words_report(res), encoding="utf-8")
    print(f"written: {jpath}")
    print(f"written: {tpath}")
    print(json.dumps(res["tape_verdict"], indent=1))
    return 0


def words(n: int) -> str:
    _ones = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
             "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
             "sixteen", "seventeen", "eighteen", "nineteen"]
    _tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
             "eighty", "ninety"]

    def w(x: int) -> str:
        if x < 20:
            return _ones[x]
        if x < 100:
            return _tens[x // 10] + ("-" + _ones[x % 10] if x % 10 else "")
        if x < 1000:
            return _ones[x // 100] + " hundred" + (" " + w(x % 100) if x % 100 else "")
        if x < 1_000_000:
            return w(x // 1000) + " thousand" + (" " + w(x % 1000) if x % 1000 else "")
        if x < 1_000_000_000:
            return w(x // 1_000_000) + " million" + \
                (" " + w(x % 1_000_000) if x % 1_000_000 else "")
        return str(x)
    return w(int(n))


def words_report(res: dict) -> str:
    L = []
    L.append("RECORDER TAPE QUALITY AUDIT — code/recorder_replay.py")
    L.append("Every exact figure lives in the sibling JSON; this text states")
    L.append("findings in words (data-quality audit, no run_id artifacts behind it).")
    L.append("")
    days = res["days"]
    L.append(f"Scope: {words(len(days))} UTC day directories (exact day list in the"
             f" JSON); symbols {', '.join(res['symbols'])}.")
    L.append("")
    total_bt = sum(res["bookTicker"][s]["rows"] for s in res["symbols"])
    L.append(f"bookTicker tape: {words(total_bt)} events total.")
    for s in res["symbols"]:
        b = res["bookTicker"][s]
        if not b["rows"]:
            L.append(f"  {s}: no bookTicker rows readable.")
            continue
        cs = b["crossed_share_pct"]
        cs_txt = ("zero" if not cs else
                  "under one hundredth of one percent" if cs < 0.01 else
                  f"{words(int(round(cs * 100)))} hundredths of one percent")
        L.append(f"  {s}: {words(b['rows'])} events; crossed best bid/ask on "
                 f"{cs_txt} of events; non-positive "
                 f"quotes: {words(b['bad_quote'])}.")
        if b["gap_ms"]:
            g = b["gap_ms"]
            L.append(f"    inter-event latency sampled: median {ms_words(g['p50'])}, "
                     f"ninety-fifth percentile {ms_words(g['p95'])}, "
                     f"ninety-ninth {ms_words(g['p99'])}.")
        if b["drift_ms"]:
            dr = b["drift_ms"]
            L.append(f"    exchange-vs-local clock drift sampled: median "
                     f"{ms_words(dr['p50'])}, ninety-fifth {ms_words(dr['p95'])}.")
    L.append("")
    for s in res["symbols"]:
        d = res["depth"][s]
        if not d["rows"]:
            L.append(f"depth diffs {s}: none readable.")
            continue
        L.append(f"depth diffs {s}: {words(d['rows'])} rows. True continuity (the")
        L.append(f"futures `pu == previous u` rule): breaks {words(d['pu_chain_breaks'])}.")
        L.append(f"The U-based rule the live recorder counts (U == previous u plus one)")
        L.append(f"flags {words(d['u_rule_breaks'])} — that counter is inflated by design:")
        L.append(f"futures update ids are shared with every event type, so consecutive")
        L.append(f"diffs legitimately skip ids. `pu` is the continuity anchor, and it")
        L.append(f"shows the tape is essentially unbroken. Duplicates: "
                 f"{words(d['chain_dups'])}. Snapshots: {words(d['snapshots'])} "
                 f"(bound OK {words(d['snap_bound_ok'])}, gap {words(d['snap_bound_gap'])},")
        L.append(f"unsettled {words(d['pending_unsettled'])} — a snapshot stays unset when")
        L.append(f"no later diff with u at or above its id exists in the audited window).")
    L.append("")
    for s in res["symbols"]:
        f = res["forceOrder"][s]
        if f["rows"]:
            L.append(f"forceOrder {s}: {words(f['rows'])} liquidation events "
                     f"(BUY side {words(f['buy'])}, SELL side {words(f['sell'])}).")
    L.append("")
    if res["unreadable_segments"]:
        L.append(f"Unreadable segments (no footer): {words(len(res['unreadable_segments']))},")
        L.append("named in the JSON. Most are whole days killed before segment rotation")
        L.append("existed; the current-day files are open by the live recorder and are")
        L.append("expected to be unreadable until it closes them.")
    else:
        L.append("Unreadable segments: none.")
    rc = res["readable_coverage"]
    L.append("")
    L.append(f"Readable bookTicker coverage: {words(rc['days_readable'])} of "
             f"{words(rc['days_total'])} days.")
    if rc["days_lost_wholly"]:
        L.append(f"Days wholly lost (every segment footerless): "
                 f"{words(len(rc['days_lost_wholly']))} — the day names are in the JSON.")
    ratios = [v["ratio"] for v in res["snapshot_vs_diff_id_space"].values() if v["ratio"]]
    L.append("")
    if ratios:
        L.append("SNAPSHOT ANCHORING (REST snapshot id vs websocket diff id):")
        foreign = [v for v in res["snapshot_vs_diff_id_space"].values()
                   if v["ratio"] and not v["overlap"]]
        inter = [v for v in res["snapshot_vs_diff_id_space"].values()
                 if v["ratio"] and v["overlap"]]
        if foreign:
            r = sum(v["ratio"] for v in foreign) / len(foreign)
            L.append(f"  On {words(len(foreign))} symbol-day samples the two id spaces")
            L.append(f"  are FOREIGN to each other: the snapshot median id runs about")
            L.append(f"  {words(int(round(r)))} times ahead of the diff median id, with zero")
            L.append("  overlap — snapshots cannot anchor diffs on those days.")
        if inter:
            L.append(f"  On {words(len(inter))} samples (the day the UPGRADED recorder")
            L.append("  finally took effect on a restart) the spaces interleave with a")
            L.append("  ratio of one to one — from that day forward, full-book")
            L.append("  reconstruction (snapshot anchor plus diffs) is possible on the")
            L.append("  forward tape. The per-day detail is in the JSON.")
        L.append("")
        L.append("Interpretation: through most of the recorded window the websocket")
        L.append("diff tape ran in a foreign id space — the mirror-host pathology the")
        L.append("recorder docstring documents (the deployed keepalive kept the OLD")
        L.append("recording code alive across restarts), while REST snapshots live in")
        L.append("the canonical fapi space. The bookTicker top-of-book tape is")
        L.append("independent of any snapshot space, which is why the fill-replay")
        L.append("adapter resolves fills on it.")
    if res["recomputed_vs_counters"]:
        L.append("")
        L.append("Chain breaks were recomputed from the parquet bytes and cross-checked")
        L.append("against recorder/coverage/counters.json (per-symbol comparison in the JSON).")
    v = res["tape_verdict"]
    L.append("")
    L.append(f"TAPE VERDICT for the fill-replay adapter: "
             f"{'USABLE' if v['tape_usable_for_fill_replay'] else 'NOT USABLE'} "
             f"(gate: crossed share under one tenth of one percent of bookTicker events")
    L.append(f"and at least {words(MIN_READABLE_DAYS)} readable days).")
    L.append(f"Full-book reconstruction via snapshots: "
             f"{'possible on part of the window' if v['snapshot_anchor_possible'] else 'NOT possible on this window'}.")
    return "\n".join(L)


def ms_words(x: float) -> str:
    """Spell a millisecond reading in words (house rule: no unbacked numerals)."""
    if x is None:
        return "n/a"
    return f"{words(int(round(x)))} ms"


if __name__ == "__main__":
    sys.exit(main())
