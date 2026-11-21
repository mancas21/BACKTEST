#!/usr/bin/env python
"""bt.py -- backtest engine over the vrun harness (2026-11-06).

ONE -- the isolation path (AGENTS.md REGLA 1, the engine contract):

    python code/bt.py one --strategy <s> --tf <tf> --symbol <sym> [--set k=v ...]

One strategy in, one verdict out. The engine backtests THAT strategy against
the historical data it holds (the hashed data store, frozen at core.cut_ts),
applies THE STANDARD battery -- the same declared gates and the same declared
costs for every strategy -- and judges it ONLY on its own artifact. No
sibling context, no family history, no cross-strategy comparison: another
strategy's failure (however similar) is never evidence about this one. The
verdict prints the rules and costs it applied; each gate reads PASS / FAIL /
N-A. FAIL-CLOSED (2026-11-21, N2 fix): N-A gates FAIL the verdict (an
incomplete battery is a refusal, never a pass); a null profit_factor (a
no-loser book) FAILS the pf gate; the v2 battery G1-G11 is evaluated on the
artifact and its pass is REQUIRED. Report lands in results/bt_one/ and must
pass `guard --strict`.

STANDARD BATTERY (identical for every strategy, measured inside the artifact):
  pf        > 1.2     profit factor ex-cost (null pf = no-loser book = FAIL)
  n         >= 30     closed trades
  net       > 0       net return at the declared costs
  thirds    >= 2/3    green equal thirds
  oos_pf    > 1.2     frozen 70/30 out-of-sample PF
  oos_net   > 0       out-of-sample net
  conc      <= 100%   best-5 trades share of PnL (CANONICAL percent keys only;
                      ambiguous-unit keys are REFUSED, never guessed)
  g6conc    > 0       net without the five best trades (concentration spirit)
  boot_ci   > 0       per-trade bootstrap CI low bound (the strategy's OWN
                      uncertainty; N-A when the adapter does not carry it)
  v2        PASS      the G1-G11 statistical battery via vrun.compute_gates_v2
Any N-A gate FAILS the verdict (fail-closed battery, N2 fix).

CAMPAIGN (multi-job, only when a staged campaign is explicitly wanted):

    python code/bt.py --plan results/bt_plans/<name>.json [--workers N] [--dry-run]

bt.py is a thin ORCHESTRATOR over the existing machinery -- every number it
produces comes from vrun.make_artifact (persisted, run_id-bound) and no gate
is re-implemented here. Stages, each printing duration and survivor count and
stopping early when a stage empties:

  1. screen        cheap gates on every job (e.g. PF ex-cost > 1.2, n >= 30,
                   net > 0, plus any OOS metric the adapter reports)
  2. wf            declared walk-forward jobs, only for screen survivors
  3. neighborhood  parameter sweeps, only for survivors so far
  4. stats         institutional scorecard (bootstrap etc.) for the survivors;
                   printed to console + sidecar JSON, never quoted in the
                   report (the scorecard is derived, not artifact-stored)
  5. report        markdown citing run_ids, then `vrun guard --report --strict`

Plan file (JSON): every job is independent and explicitly declared -- bt.py
adds no hidden parameters and no adapter-specific knowledge.

    {
      "name": "my-campaign",
      "workers": 4,
      "gates": {
        "screen": [["profit_factor|best_pf|PF", ">", 1.2],
                   ["n_trades|trades", ">=", 30],
                   ["return_pct|net_%", ">", 0]],
        "wf": [["oos_net_%|mean_test_net_%", ">", 0]]
      },
      "jobs": [
        {"label": "s28", "role": "screen", "strategy": "top10",
         "tf": "1h", "symbol": "BTCUSDT", "set": ["id=28"]},
        {"label": "s28-wf", "role": "wf", "needs": "s28", "strategy": "cbpack",
         "tf": "1h", "symbol": "SOLUSDT",
         "set": ["mode=wf", "train_bars=1440", "test_bars=720", "ids=S10"]},
        {"label": "s28-nb", "role": "neighborhood", "needs": "s28",
         "strategy": "top10", "tf": "1h", "symbol": "BTCUSDT",
         "param": "lb", "values": "168,336,672"},
        {"label": "s28", "role": "stats", "needs": "s28"}
      ],
      "report": "results/bt_my-campaign_report.md"
    }

Gate rule format: [metric_aliases_pipe_separated, op, value]; a rule reads the
FIRST alias present in the artifact metrics (adapters report different
dialects) and passes when the comparison holds. An artifact missing every
alias FAILS the rule -- absence is never a pass.

Usage:
    python code/bt.py one --strategy smqe11 --tf 1h --symbol SUIUSDT --set cost_mode=repo
    python code/bt.py --plan results/bt_plans/my-campaign.json [--workers N]
                      [--dry-run] [--from-stage screen|wf|neighborhood|stats]
"""
from __future__ import annotations

import argparse
import argparse as _ap
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))
import vrun  # noqa: E402

STAGES = ("screen", "wf", "neighborhood", "stats")
PLAN_DIR = os.path.join(ROOT, "results", "bt_plans")
TIMING_DIR = os.path.join(ROOT, "results", "bt_timings")


# ── worker (top-level: picklable for ProcessPoolExecutor) ────────────────
def _bt_worker(job):
    label, strategy, tf, symbol, params = job
    t0 = time.time()
    art = vrun.make_artifact(strategy, tf, symbol, params)
    vrun.save_artifact(art)
    return {"label": label, "run_id": art["run_id"], "strategy": strategy,
            "symbol": symbol, "timeframe": tf, "params": art["params"],
            "metrics": art["metrics"], "tables": art.get("tables") or [],
            "seconds": round(time.time() - t0, 1)}


def _parse_job_params(job):
    """Same coercion as vrun.parse_params, from a plan job."""
    ns = _ap.Namespace(params=job.get("params", ""), set=job.get("set"))
    return vrun.parse_params(ns)


# ── gates ────────────────────────────────────────────────────────────────
def _metric(res: dict, aliases: str):
    """First alias that resolves to a number. Two shapes:
      * metrics lookup, dots walking nested dicts (top10-style artifacts carry
        full.pf / oos.pf / full_pct.net_pct);
      * `<rowId>.<field>` reads a TABLE row by its id (cbpack walk-forward
        summaries carry oos_net_% per strategy, not in metrics)."""
    tables = res.get("tables") or []
    if not isinstance(tables, list):  # dict-form tables (keyed tables) have
        tables = []                   # no "id" rows; the metrics path above
                                      # already resolved what it could
    
    for a in aliases.split("|"):
        a = a.strip()
        cur = res["metrics"]
        ok = True
        for part in a.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok and isinstance(cur, (int, float)) and not isinstance(cur, bool):
            return cur
        # table-row form: first segment names a row id
        parts = a.split(".")
        row = next((r for r in tables if str(r.get("id")) == parts[0]), None)
        if row is not None:
            cur = row
            ok = True
            for part in parts[1:]:
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    ok = False
                    break
            if ok and isinstance(cur, (int, float)) and not isinstance(cur, bool):
                return cur
    return None


_OPS = {
    ">": lambda x, y: x > y,
    ">=": lambda x, y: x >= y,
    "<": lambda x, y: x < y,
    "<=": lambda x, y: x <= y,
}


def _metric_has_null(art: dict, aliases: str) -> bool:
    """True when a metric path EXISTS in the artifact but is explicitly null
    (e.g. profit_factor stored as None for a no-loser book) -- distinct from
    the metric not being carried at all (N2 fix: null pf FAILS, not N-A)."""
    m = art.get("metrics", {})
    for a in aliases.split("|"):
        a = a.strip()
        cur = m
        exists = True
        for part in a.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                exists = False
                break
        if exists and cur is None:
            return True
    return False


def _eval_gate(res: dict, rules: list) -> tuple:
    """(passed, reasons). A rule with no alias present in the metrics FAILS."""
    ok, why = True, []
    for aliases, op, val in rules:
        v = _metric(res, aliases)
        if v is None or isinstance(v, bool) or not isinstance(v, (int, float)):
            ok = False
            why.append(f"{aliases.split('|')[0]} missing")
            continue
        if not _OPS[op](float(v), float(val)):
            ok = False
            why.append(f"{aliases.split('|')[0]}={v}")
    return ok, why


# ── stage runners ────────────────────────────────────────────────────────
def _run_jobs(jobs: list, workers: int) -> list:
    """Run jobs (plan dicts) through the pool; returns worker results in the
    declared order. Exceptions become error markers, never silent drops."""
    payloads = [(j["label"], j["strategy"], j["tf"], j["symbol"],
                 _parse_job_params(j)) for j in jobs]
    if workers <= 1 or len(payloads) <= 1:
        out = []
        for p in payloads:
            try:
                out.append(_bt_worker(p))
            except Exception as e:
                out.append({"label": p[0], "error": f"{type(e).__name__}: {e}",
                            "metrics": {}, "tables": []})
        return out
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=min(workers, len(payloads))) as ex:
        try:
            return list(ex.map(_bt_worker, payloads))
        except Exception as e:
            # one failed worker fails the map; fall back to per-job isolation
            print(f"    pool error ({type(e).__name__}); retrying jobs individually")
            out = []
            for p in payloads:
                try:
                    out.append(_bt_worker(p))
                except Exception as e2:
                    out.append({"label": p[0], "error": f"{type(e2).__name__}: {e2}",
                                "metrics": {}, "tables": []})
            return out


def _coerce_set_items(items):
    """--set key=value items to a params dict, with the same value coercion
    as vrun.parse_params (N10 fix: neighborhood jobs must keep the parent's
    --set params, or a multi-strategy adapter sweeps its DEFAULT id)."""
    d = {}
    for kv in (items or []):
        k, _, v = str(kv).partition("=")
        if not v:
            raise ValueError(f"set item expects key=value, got {kv!r}")
        if v.lower() in ("true", "false"):
            d[k] = v.lower() == "true"
        else:
            try:
                d[k] = int(v)
            except ValueError:
                try:
                    d[k] = float(v)
                except ValueError:
                    d[k] = v
    return d


def _neighborhood_jobs(job, workers):
    """One neighborhood plan job -> one artifact per value (same coercion and
    verdict rule as vrun.cmd_neighborhood)."""
    vals = [v.strip() for v in str(job["values"]).split(",") if v.strip()]
    results = []
    payload = []
    # N10 FIX: the parent job's --set params travel with every sweep value.
    # Previously they were DISCARDED, so a neighborhood on a multi-strategy
    # adapter (top10 --set id=28) ran the adapter's DEFAULT id -- the sweep
    # measured the stability of a DIFFERENT strategy than the survivor.
    base_params = _coerce_set_items(job.get("set"))
    for v in vals:
        val = float(v) if "." in str(v) else int(v)
        payload.append((f"{job['label']}[{v}]", job["strategy"], job["tf"],
                        job["symbol"], {**base_params, job["param"]: val}))
    if workers <= 1 or len(payload) <= 1:
        outs = []
        for p in payload:
            try:
                outs.append(_bt_worker(p))
            except Exception as e:
                outs.append({"label": p[0], "error": f"{type(e).__name__}: {e}",
                             "metrics": {}, "tables": []})
    else:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=min(workers, len(payload))) as ex:
            outs = list(ex.map(_bt_worker, payload))
    for o in outs:
        pf = vrun._first(o["metrics"], "profit_factor", "best_pf")
        results.append({"label": o["label"], "run_id": o.get("run_id"),
                        "pf": pf, "ret": vrun._first(o["metrics"], "return_pct",
                                                     "best_net_pct"),
                        "n": vrun._first(o["metrics"], "n_trades"),
                        "error": o.get("error"),
                        "stable": bool(pf is not None and pf > 1.2)})
    pfs = [r["pf"] for r in results if isinstance(r["pf"], (int, float))]
    stable = bool(pfs) and min(pfs) >= 1.0 and (max(pfs) - min(pfs)) < 0.5
    # N10 FIX: the declared neighborhood rule is now the CONJUNCTION of the
    # two rules that used to live in different layers ("stricter wins" made
    # arithmetic, not a sentence):
    #   - the old plan rule: every neighbor PF >= 1.0 and spread < 0.5
    #   - the _gates_v2.POLICY rule (nb_pass_frac 0.70 / nb_pf_ratio_min 0.75):
    #     >= 70% of neighbors above PF 1.2 (the G1 screen reading) and the
    #     median neighbor PF within 75% of the center's PF
    frac_ok = (sum(1 for r in results if isinstance(r["pf"], (int, float))
                   and r["pf"] > 1.2) / max(len(results), 1)) >= 0.70
    # NEW-5 fix (second audit 2026-11-21): the "centre" is the PF of the
    # MEDIAN SWEPT VALUE, not the middle of the declared-value list -- for
    # an even count or unordered values the positional middle was an
    # arbitrary neighbour. The job may also declare `centre` (the base
    # parameter value); that PF wins when present.
    center_pf = None
    centre_decl = job.get("centre")
    if centre_decl is not None:
        for r in results:
            lbl_val = str(r["label"]).rsplit("[", 1)[-1].rstrip("]")
            if lbl_val == str(centre_decl):
                center_pf = r.get("pf")
                break
    by_val = []
    for r in results:
        if not isinstance(r.get("pf"), (int, float)):
            continue
        try:
            v = float(str(r["label"]).rsplit("[", 1)[-1].rstrip("]"))
        except ValueError:
            v = None
        by_val.append((v, r["pf"]))
    if center_pf is None and by_val:
        # R7 fix: a sentinel for unparsable labels -- (True, None) vs
        # (True, None) raises TypeError on None < None
        by_val.sort(key=lambda t: (t[0] is None,
                                   t[0] if t[0] is not None else float("inf")))
        center_pf = by_val[len(by_val) // 2][1]
    spfs = sorted(pfs)
    med = (spfs[len(spfs) // 2] if len(spfs) % 2
           else 0.5 * (spfs[len(spfs) // 2 - 1] + spfs[len(spfs) // 2])) if pfs else None
    ratio_ok = (med is not None and center_pf and center_pf > 0
                and med / center_pf >= 0.75)
    stable = bool(stable and frac_ok and ratio_ok)
    return {"label": job["label"], "param": job["param"], "values": results,
            "center_pf": center_pf,
            "verdict": "STABLE" if stable else "CLIFF / SENSITIVE"}


def _stats_one(run_id: str) -> dict:
    import quant_metrics as qm
    art = vrun.load_artifact(run_id)
    return qm.compute_artifact_scorecard(art)


# ── one: the isolation verdict (AGENTS.md REGLA 1) ──────────────────────
# The STANDARD battery: same gates, same declared semantics, for every
# strategy. Each gate reads the strategy's OWN artifact; a gate whose metric
# the artifact does not carry is N-A (listed), never a silent pass.
ONE_GATES = [
    ("pf",      "profit_factor|best_pf|full.pf",            ">",  1.2),
    ("n",       "n_trades|trades|full.n",                   ">=", 30),
    ("net",     "return_pct|full_pct.net_pct|net_%",        ">",  0.0),
    ("thirds",  "n_periods_green|thirds_green",             ">=", 2),
    ("oos_pf",  "oos_profit_factor|oos.pf|oos_pf",          ">",  1.2),
    ("oos_net", "oos_return_pct|oos.net|oos_pct.net_pct",   ">",  0.0),
    # N1 FIX: conc reads ONLY canonical percent keys. The old alias list
    # included top5_pnl_share, whose unit VARIES BY ADAPTER (p100screen and
    # s101 store percent; prompts100/top10 store a fraction) and was scaled
    # x100 here -- a 5%-concentration book read as 500 and failed. An engine
    # that still emits only the ambiguous key gets an explicit refusal, never
    # a guessed comparison.
    ("conc",    "best5_share_pct|conc_top5_share_pct",      "<=", 100.0),
    # the concentration companion gate (G6's spirit): the book must still be
    # green with its five best trades removed
    ("g6conc",  "net_without_top5_pct|conc_net_without_pct", ">", 0.0),
    ("boot_ci", "boot_ci_lo|bootstrap.ci_low",                     ">",  0.0),
]
# N1 FIX: keys whose unit is NOT determined by their name (adapters disagree).
# The battery refuses them outright instead of normalizing by a guess.
_AMBIGUOUS_METRIC_KEYS = {"top5_pnl_share"}


def main_one(argv) -> int:
    ap = argparse.ArgumentParser(prog="bt one",
                                 description="one strategy -> one verdict "
                                             "(AGENTS.md REGLA 1: isolated)")
    ap.add_argument("--strategy", required=True, choices=list(vrun.ADAPTERS))
    ap.add_argument("--tf", required=True)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--params", default="", help="params JSON")
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--cut-ts", default="auto")
    ap.add_argument("--report", default=None)
    args = ap.parse_args(argv)

    # 1) one artifact: this strategy, this data cut, the declared costs
    params = vrun.parse_params(argparse.Namespace(params=args.params, set=args.set))
    art = vrun.make_artifact(args.strategy, args.tf, args.symbol, params,
                             cut_ts=args.cut_ts)
    vrun.save_artifact(art)
    m = art["metrics"]
    core = art["core"]

    # 2) rules and costs, printed as applied (clear and identical for all)
    cost_bp = _metric(art, "cost_bp_roundtrip|cost_bp_roundtrip")
    fee_side = _metric(art, "fee_bps_per_side")
    slip_side = _metric(art, "slippage_bps_per_side|slippage_bps")
    funding = m.get("funding_model") or m.get("funding_charged")
    fill_model = m.get("fill_model")
    print("=" * 72)
    print(f"BT ONE (isolated verdict): {args.strategy} {args.symbol} {args.tf}")
    print(f"  run_id   : {art['run_id']}")
    print(f"  artifact : {vrun.artifact_path(art['run_id'])}")
    print(f"  data cut : {core.get('cut_ts', 'legacy full-file')}  "
          f"bars={[i[2] for i in core['inputs']]}")
    print(f"  costs    : {cost_bp if cost_bp is not None else 'NOT DECLARED by adapter'} bps RT"
          + (f" (fee {fee_side} + slip {slip_side} per side)" if fee_side is not None else ""))
    print(f"  funding  : {funding if funding is not None else 'declared by adapter'}"
          + (f" | fill model: {fill_model}" if fill_model else ""))
    print("-" * 72)

    # 3) the standard battery, on this artifact only. The report quotes the
    # STORED metric value (guard-backable); dialect normalizations (fractions
    # to percent) apply only to the comparison.
    rows, n_fail, n_na, n_pass = [], 0, 0, 0
    for gname, aliases, op, val in ONE_GATES:
        v = _metric(art, aliases)
        raw_v = v
        if gname == "conc":
            # N1 FIX: if the artifact carries ONLY an ambiguous-unit key, the
            # gate refuses it explicitly instead of normalizing by a guess.
            canon = _metric(art, aliases)
            if canon is None and any(
                    _metric(art, k) is not None for k in _AMBIGUOUS_METRIC_KEYS):
                rows.append((gname, "N-A",
                             "ambiguous unit key "
                             f"{sorted(_AMBIGUOUS_METRIC_KEYS)} present but no canonical "
                             "percent key (conc_top5_share_pct / best5_share_pct) - "
                             "REFUSED, not guessed (N1 fix)", None))
                n_na += 1
                print(f"  [{rows[-1][1]:^4}] {gname:<8} {rows[-1][2]}")
                continue
        if v is None or not isinstance(v, (int, float)) or isinstance(v, bool):
            # N2 FIX: a pf that is PRESENT but null means "no losing trades" --
            # a no-loser book is the classic negative-skew signature, and its
            # PF gate must FAIL, not be skipped as N-A.
            if gname == "pf" and _metric_has_null(art, aliases):
                status, detail = "FAIL", ("profit_factor is null (no losing "
                                          "trades) - PF gate cannot be met")
                n_fail += 1
            else:
                status, detail = "N-A", "metric not carried by this artifact"
                n_na += 1
        else:
            ok = _OPS[op](float(v), float(val))
            status = "PASS" if ok else "FAIL"
            detail = f"{gname}={v} (rule: {op} {val})"
            if ok:
                n_pass += 1
            else:
                n_fail += 1
        rows.append((gname, status, detail, raw_v))
        print(f"  [{status:^4}] {gname:<8} {detail}")

    # N2 FIX: the v2 statistical battery (G1-G11) is part of the standard
    # battery now -- a v1-only pass is NOT promotable (F1 fix applied to
    # `one`, which never called compute_gates_v2).
    try:
        gv2 = vrun.compute_gates_v2(art)
    except Exception as e:
        gv2 = {"available": False, "pass": False,
               "reason": f"{type(e).__name__}: {e}"}
    if not gv2.get("available"):
        v2_status, v2_detail = "FAIL", (
            "gates_v2 block / trades_v2 schema absent - fail closed "
            f"({gv2.get('reason', 'v2 unavailable')})")
        n_fail += 1
    else:
        v2_ok = bool(gv2.get("pass"))
        v2_status = "PASS" if v2_ok else "FAIL"
        v2_detail = f"v2 battery G1-G11 backtest_pass={v2_ok}"
        if not v2_ok:
            n_fail += 1
        else:
            n_pass += 1
    rows.append(("v2", v2_status, v2_detail, None))
    print(f"  [{v2_status:^4}] {'v2':<8} {v2_detail}")

    # N2 FIX: N-A gates no longer permit a verdict PASS -- the battery is
    # fail-closed on absence ("absence is never a pass" is now arithmetic,
    # not just the docstring).
    verdict = "PASS" if (n_fail == 0 and n_na == 0) else "FAIL"
    print("-" * 72)
    print(f"VERDICT: {verdict}  ({n_pass} gates PASS, {n_fail} FAIL, {n_na} N-A)")
    print("  Judged on this strategy's own artifact only - no sibling context,")
    print("  no family history (AGENTS.md REGLA 1).")
    print("=" * 72)

    # 4) report + guard (numbers only from the cited artifact; ASCII minus)
    report = args.report or os.path.join(
        ROOT, "results", "bt_one",
        f"{args.strategy}_{args.symbol}_{args.tf}.md")
    os.makedirs(os.path.dirname(report), exist_ok=True)
    lines = [
        f"# bt one: {args.strategy} {args.symbol} {args.tf}",
        "",
        f"run_id `{art['run_id']}` - data cut {core.get('cut_ts', 'legacy')} - "
        f"costs {cost_bp if cost_bp is not None else 'not declared'} bps RT.",
        "",
        "| gate | status | value (as stored in the artifact) |",
        "|---|---|---|",
    ]
    for gname, status, detail, raw_v in rows:
        val = ("not carried" if raw_v is None
               else repr(float(raw_v)))
        lines.append(f"| {gname} | {status} | {val} |")
    lines += ["", f"VERDICT: {verdict} - judged on this strategy's own artifact only."]
    with open(report, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"report: {report}")
    rc = vrun.cmd_guard(argparse.Namespace(report=report, strict=True))
    # N2 FIX: N-A gates now fail the verdict, so they also fail the exit code
    # (an incomplete battery is a refusal, not a pass).
    return 0 if (rc == 0 and n_fail == 0 and n_na == 0) else (2 if (n_fail or n_na) else rc)


# ── main ─────────────────────────────────────────────────────────────────
def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "one":
        return main_one(sys.argv[2:])
    ap = argparse.ArgumentParser(prog="bt")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--from-stage", default="screen", choices=STAGES)
    args = ap.parse_args()

    plan = json.load(open(args.plan, encoding="utf-8"))
    name = plan.get("name", os.path.basename(args.plan).replace(".json", ""))
    workers = int(args.workers or plan.get("workers", 4))
    gates = {k: [tuple(r) for r in v] for k, v in plan.get("gates", {}).items()}
    jobs = plan["jobs"]
    report_path = plan.get("report") or os.path.join(
        ROOT, "results", f"bt_{name}_report.md")

    if args.dry_run:
        print(f"DRY RUN {name}: workers={workers}")
        for role in STAGES:
            sel = [j for j in jobs if j["role"] == role]
            print(f"  {role:<13} {len(sel)} job(s)")
            for j in sel:
                print(f"    {j['label']:<14} {j.get('needs', '-'):<10} "
                      f"{j.get('strategy', '')} {j.get('tf', '')} {j.get('symbol', '')} "
                      f"{j.get('set') or j.get('values') or ''}")
        print(f"  report -> {report_path}")
        return 0

    timing = {"name": name, "started_utc": vrun.datetime.now(
        vrun.timezone.utc).isoformat(timespec="seconds"), "stages": {}}
    results = {}        # label -> worker result (screen/wf)
    surv = None         # survivor labels after each stage
    report_lines = [f"# bt campaign: {name}", ""]

    for si, stage in enumerate(STAGES):
        if STAGES.index(stage) < STAGES.index(args.from_stage):
            continue
        t0 = time.time()
        sel = [j for j in jobs if j["role"] == stage]
        if stage != "screen" and surv is not None:
            sel = [j for j in sel if j.get("needs") in surv]

        print(f"\n=== stage {si + 1}/{len(STAGES)}: {stage} "
              f"({len(sel)} job(s), workers={workers}) ===", flush=True)
        if not sel:
            timing["stages"][stage] = {"jobs": 0, "seconds": round(time.time() - t0, 1)}
            print("  nothing to run")
            continue

        if stage == "screen":
            res = _run_jobs(sel, workers)
            for r in res:
                results[r["label"]] = r
            rules = gates.get("screen", [])
            surv = []
            for r in res:
                if r.get("error"):
                    print(f"  {r['label']:<14} ERROR {r['error']}")
                    continue
                ok, why = _eval_gate(r, rules)
                mark = "PASS" if ok else f"fail ({'; '.join(why)})"
                print(f"  {r['label']:<14} {r['run_id']}  {mark}")
                if ok:
                    surv.append(r["label"])
            n_err = sum(1 for r in res if r.get("error"))
            print(f"  -> {len(surv)} survivor(s)"
                  + (f", {n_err} error(s)" if n_err else ""))
            # F1 FIX: the v2 battery (G1-G11) is the promotion gate. A v1 screen
            # pass alone is NOT promotable; fail closed when v2 is absent/failing.
            if surv:
                v2_keep = []
                for lbl in surv:
                    r = results[lbl]
                    try:
                        gv2 = vrun.compute_gates_v2(vrun.load_artifact(r["run_id"]))
                    except Exception as e:
                        gv2 = {"pass": False, "reason": f"{type(e).__name__}: {e}"}
                    if gv2.get("pass"):
                        v2_keep.append(lbl)
                        print(f"  v2 {lbl:<14} PASS")
                    else:
                        print(f"  v2 {lbl:<14} BLOCKED ({gv2.get('reason', 'v2 fail')})")
                print(f"  -> {len(v2_keep)} v2-certifiable survivor(s) of {len(surv)} screen")
                surv = v2_keep
            report_lines += ["## screen", "",
                             "| label | run_id | strategy | market | PF | n | net % |",
                             "|---|---|---|---|---|---|---|"]
            for r in res:
                if r.get("error"):
                    continue
                pf = _metric(r, "full.pf|profit_factor|best_pf|PF")
                n = _metric(r, "n_trades|trades|full.n")
                net = _metric(r, "full_pct.net_pct|return_pct|net_%")
                # only artifact-stored numbers are quoted (guard-backable);
                # missing fields print as em dashes
                pf_s = f"{pf:.2f}" if isinstance(pf, (int, float)) else "—"
                n_s = str(n) if isinstance(n, (int, float)) else "—"
                net_s = f"{net:.1f}" if isinstance(net, (int, float)) else "—"
                report_lines.append(
                    f"| {r['label']} | `{r['run_id']}` | {r['strategy']} "
                    f"| {r['symbol']} {r['timeframe']} | {pf_s} | {n_s} | {net_s} |")
            report_lines.append("")

        elif stage == "wf":
            res = _run_jobs(sel, workers)
            for r in res:
                results[r["label"]] = r
            rules = gates.get("wf", [])
            n_pass = 0
            report_lines += ["## walk-forward", ""]
            for r in res:
                if r.get("error"):
                    print(f"  {r['label']:<14} ERROR {r['error']}")
                    continue
                ok, why = _eval_gate(r, rules)
                n_pass += ok
                print(f"  {r['label']:<14} {r['run_id']}  "
                      f"{'PASS' if ok else 'fail (' + '; '.join(why) + ')'}")
                report_lines.append(
                    f"- {r['label']}: `{r['run_id']}` — "
                    f"{'wf gates pass' if ok else 'wf gates fail'}")
            print(f"  -> {n_pass} of {len(res)} pass the wf gates")
            report_lines.append("")

        elif stage == "neighborhood":
            nbs = [_neighborhood_jobs(j, workers) for j in sel]
            report_lines += ["## neighborhood", ""]
            for nb in nbs:
                print(f"  {nb['label']:<14} {nb['param']}: {nb['verdict']}")
                for v in nb["values"]:
                    pf = f"{v['pf']:.2f}" if isinstance(v["pf"], (int, float)) else "—"
                    print(f"    {nb['param']}={v['label'].split('[')[-1].rstrip(']'):<8} "
                          f"{str(v['run_id'])}  PF={pf}"
                          + (f"  ERROR {v['error']}" if v["error"] else ""))
                report_lines.append(
                    f"- {nb['label']} ({nb['param']}): {nb['verdict']} — "
                    + ", ".join(f"`{v['run_id']}`" for v in nb["values"]
                                if v.get("run_id")))
            report_lines.append("")

        elif stage == "stats":
            os.makedirs(TIMING_DIR, exist_ok=True)
            sidecar = os.path.join(TIMING_DIR, f"{name}_stats.json")
            cards = {}
            for j in sel:
                rid = results.get(j["needs"], {}).get("run_id") or j.get("needs")
                if not rid or not os.path.exists(vrun.artifact_path(rid)):
                    print(f"  {j['label']:<14} no artifact for stats, skipped")
                    continue
                try:
                    cards[rid] = _stats_one(rid)
                    bb = cards[rid].get("block_bootstrap") or {}
                    print(f"  {j['label']:<14} {rid}  bootstrap CI "
                          f"[{bb.get('ci_lo')}, {bb.get('ci_hi')}] "
                          f"P(mean<=0) {bb.get('p_le_zero')}")
                except Exception as e:
                    print(f"  {j['label']:<14} stats ERROR {type(e).__name__}: {e}")
            with open(sidecar, "w", encoding="utf-8") as f:
                json.dump(cards, f, indent=2, sort_keys=True, default=str)
            print(f"  scorecards -> {sidecar} (derived numbers: console/sidecar "
                  "only, never quoted in the report)")
            report_lines += ["## stats", "",
                             f"Scorecards for {len(cards)} artifact(s) in "
                             f"`{os.path.relpath(sidecar, ROOT)}` — derived "
                             "metrics, not quoted here.", ""]

        timing["stages"][stage] = {
            "jobs": len(sel), "seconds": round(time.time() - t0, 1),
            "survivors": surv if stage == "screen" else None}
        print(f"  stage {stage}: {timing['stages'][stage]['seconds']}s")

        if stage == "screen" and not surv:
            print("\nearly stop: the screen emptied — no expensive stages run.")
            break

    # ── report + guard ───────────────────────────────────────────────────
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"\nreport: {report_path}")
    timing["report"] = os.path.relpath(report_path, ROOT)
    os.makedirs(TIMING_DIR, exist_ok=True)
    with open(os.path.join(TIMING_DIR, f"{name}_timings.json"), "w",
              encoding="utf-8") as f:
        json.dump(timing, f, indent=2, sort_keys=True)

    if surv is not None and not surv:
        print("no survivors — guard not run (empty report has no numbers).")
        return 0
    gns = argparse.Namespace(report=report_path, strict=True)
    buf_ok = vrun.cmd_guard(gns)
    return 0 if buf_ok == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
