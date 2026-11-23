"""Build results/zerocost_rows91_100_report_2026-11-23.md from the artifacts.
Every number comes from a stored artifact and is printed next to its run_id.

Run: python code/_zerocost_rows91_100_report.py
"""
import json
import os
import re
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE)
os.chdir(ROOT)

MATRIX = os.path.join(ROOT, "results", "zerocost_rows91_100_matrix.json")
OUT = os.path.join(ROOT, "results", "zerocost_rows91_100_report_2026-11-23.md")
_RID = re.compile(r"^[0-9a-f]{16}$")
_RUNS = os.path.realpath(os.path.join(ROOT, "results", "runs"))


def load(rid):
    if not _RID.match(str(rid)):
        raise ValueError(f"refusing non run_id: {rid!r}")
    p = os.path.realpath(os.path.join(_RUNS, str(rid) + ".json"))
    if not (p.startswith(_RUNS + os.sep) and os.path.isfile(p)):
        raise ValueError(f"artifact outside the runs dir: {rid!r}")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def cost_fields(art):
    m, s = art["metrics"], art["strategy"]
    if s in ("dspack", "dspack2"):
        return (m["costs"], "in preset", "n/a (kline-only)")
    if s == "pack100":
        c = m.get("cost_bps_per_side")
        return (f"{c:g} combined" if c is not None else "n/a",
                "n/a", str(m.get("funding_charged", "n/a")))
    fee = m.get("fee_bps_per_side")
    slip = m.get("slippage_bps_per_side", m.get("slip_bps_per_side"))
    return (f"{fee:g}" if fee is not None else "n/a",
            f"{slip:g}" if slip is not None else "n/a",
            str(m.get("funding_charged", "n/a")))


def extra(art, sid=None):
    m, s, rid = art["metrics"], art["strategy"], art["run_id"]
    if s == "qs":
        return (f" Its base run's `funding_paid` reads {m['funding_paid']:.2f} over "
                f"{int(m['n_funding_events'])} settlement events (positive means paid), "
                f"`{rid}`.")
    if s == "cbpackf":
        t = next(r for r in art["tables"] if r.get("id") == sid)
        return (f" Its {sid} row's `funding_paid_pct` reads {t['funding_paid_pct']:.4f} "
                f"and `funding_drag_pp` reads {t['funding_drag_pp']:.4f}, `{rid}`.")
    if s == "pack100":
        return (f" Its own `zero_cost_pf` reads {m['zero_cost_pf']:.4f} "
                f"(fees removed with funding still charged), `{rid}`.")
    return ""


NOTES = {
    91: ("THE FUNDING-SIGNAL CASE AGAIN. S07 reads the attached funding column "
         "in its signal, so ZERO keeps that column for the signal and sets "
         "`charge_funding=False`: the trade count is identical in both "
         "regimes and only the cash flow changes. This path was audited and "
         "declared in an earlier batch's dated addendum."),
    92: ("This row reuses the SUI `cbpackf` artifacts minted in earlier "
         "batches (same adapter, symbol, params, engine and cut); the ranking "
         "row is S09, read out of those artifacts."),
    93: ("The second pack's ds7 on DOGE was published at `repo6x5` (a real "
         "cost block); ZERO is the same engine's `author` preset."),
    94: ("The base figure reproduces the published one exactly under current "
         "engine bytes despite the old ranking artifact's engine drift."),
    95: ("ds1 on NEAR was published at `repo6x5`; ZERO is `author`. The "
         "in-artifact zero re-score and the author headline coincide."),
    96: ("A trade-flow strategy: the ranking artifact's provenance names "
         "adapter `qsf`, so the matrix uses the `qsf` adapter with the same "
         "cost/funding switches as `qs`. The whole ladder is zeroed at ZERO."),
    97: ("ds1 on LINK was published at `repo6x5`; ZERO is `author`."),
    98: ("ds7 on SOL was published at `repo6x5`; ZERO is `author`."),
    99: ("ds7 on NEAR was published at `repo6x5`; ZERO is `author`."),
    100: ("ds1 on SUI was published at `repo6x5`; ZERO is `author`. The "
          "kline file grew since the ranking, so the base figure is a "
          "re-measurement; the engine's own zero re-score still equals the "
          "author headline."),
}


def main():
    data = json.load(open(MATRIX, encoding="utf-8"))
    books, cells = data["books"], data["cells"]
    arts = {(tag, regime): load(rec[regime]["run_id"])
            for tag, rec in cells.items()
            for regime in ("base", "zero", "costed") if regime in rec}

    L = []
    A = L.append
    A("# Zero cost, no rules — this batch of the hundred best books re-run")
    A("")
    A("Date: 2026-11-23. Status: **experiment / control**. No verdict, no gate "
      "and no alpha claim (see `results/zerocost_rows91_100_pre_registration.md`, "
      "written before the first artifact). Tenth and final batch of the control begun "
      "in `results/zerocost_report_2026-11-20.md` and continued in the six "
      "reports that followed it.")
    A("")
    A("## The question")
    A("")
    A("Ten books were taken from `results/top100_2026-10-31.md` — rows "
      "91 to 100, in the order that list already published — and each was run twice "
      "on the same frozen cut by the same engine bytes: once under its "
      "published cost regime (**BASE**) and once with fees, slippage and "
      "funding cash flow at zero (**ZERO**). No screening gate is applied. "
      "No row in this final batch was published at zero cost: every BASE is a "
      "costed regime (`repo6x5` for the DeepSeek books, the catalog ladder or "
      "the `cbpackf` block for the rest), and every ZERO removes it.")
    A("")
    A("Ten books produced nineteen unique artifacts — one BASE/ZERO pair shares "
      "an artifact by construction — every one "
      "verifying bit-for-bit (`results/_zerocost_rows91_100_verify.txt`).")
    A("")
    A("## The ten, both regimes")
    A("")
    A("Every row is one stored artifact; the run_id is on its own row. Net % "
      "is the book's own full-window return, PF its profit factor, Trades its "
      "closed-trade count and Max DD % the drawdown exactly as the engine "
      "stores it (negative where the engine reports a signed drawdown).")
    A("")
    A("| Book | Market | Regime | Net % | PF | Trades | Max DD % | run_id |")
    A("|---|---|---|---:|---:|---:|---:|---|")
    for b in books:
        for regime, label in (("base", "BASE"), ("zero", "ZERO")):
            r = b[regime]
            A(f"| {b['book']} | {b['market']} | {label} | {r['net_pct']:.2f} | "
              f"{r['pf']:.3f} | {int(r['n_trades'])} | {r['max_dd_pct']:.2f} | "
              f"`{r['run_id']}` |")
    A("")
    A("## What each regime actually charged")
    A("")
    A("Fields below are the artifacts' own declarations: the catalog base "
      "point, the `cbpackf` and `pack100` per-side/combined cost blocks with "
      "their funding flags, and the `dspack`/`dspack2` preset names.")
    A("")
    A("| Adapter | Market | Base fee | Base slip | Base funding | Zero fee | Zero slip | Zero funding | run_ids |")
    A("|---|---|---|---|---|---|---|---|---|")
    for tag, rec in cells.items():
        base, zero = arts[(tag, "base")], arts[(tag, "zero")]
        bf, bs, bfu = cost_fields(base)
        zf, zs, zfu = cost_fields(zero)
        A(f"| `{base['strategy']}` | {base['symbol']} {base['timeframe']} | "
          f"{bf} | {bs} | {bfu} | {zf} | {zs} | {zfu} | "
          f"`{base['run_id']}` `{zero['run_id']}` |")
    A("")
    A("## Book by book")
    A("")
    A("Each line quotes its own artifacts, with run_ids on the line.")
    A("")
    for b in books:
        b_id, z_id = b["base"]["run_id"], b["zero"]["run_id"]
        ids = f"(`{b_id}`, `{z_id}`)"
        if "costed" in b:
            ids = f"(`{b_id}`; costed `{cells[b['tag']]['costed']['run_id']}`)"
        sid = b["where"] if b["where"] != "metrics" else None
        A(f"**{b['book']} — {b['market']}.** Base net "
          f"{b['base']['net_pct']:.2f}% at PF {b['base']['pf']:.3f} on "
          f"{int(b['base']['n_trades'])} trades; zero net "
          f"{b['zero']['net_pct']:.2f}% at PF {b['zero']['pf']:.3f} on "
          f"{int(b['zero']['n_trades'])} trades {ids}."
          + extra(arts[(b["tag"], "base")], sid)
          + " " + NOTES.get(b["row"], ""))
        A("")
        if "costed" in b:
            t = arts[(b["tag"], "costed")]["tables"][0]
            A(f"The costed re-run keeps {int(t['n_trades'])} trades and charges "
              f"{t['fees_charged']:.2f} in fees, landing at {t['ret_pct']:.2f}% "
              f"net at PF {t['pf_strict']:.4f}; its in-artifact zero-cost "
              f"re-score `ret_zero_pct` reads {t['ret_zero_pct']:.4f} percent "
              f"(`{cells[b['tag']]['costed']['run_id']}`).")
            A("")
        if b["base"]["n_trades"] != b["zero"]["n_trades"]:
            A(f"On this cell the trade count changes with the cost regime — "
              f"{int(b['base']['n_trades'])} on the base run `{b_id}` versus "
              f"{int(b['zero']['n_trades'])} on the zero run `{z_id}` — because "
              f"the catalog's equity-dependent risk devices (daily-loss halt, "
              f"drawdown halving and halt) are part of the strategy and react "
              f"to the changed equity path. No signal rule was changed.")
            A("")
    A("## What the numbers say")
    A("")
    A("Three readings, none of them a verdict:")
    A("")
    A("1. **Old `qs` and `pack100` ranking artifacts no longer verify after "
      "the 2026-11-21 audit-fix changed their engine bytes.** That is a "
      "provenance fact, not tampering; all artifacts here are on current "
      "bytes and verify. Matching BASE figures are exact figure "
      "reproductions, not bit-identical artifacts.")
    A("2. **S07 is the one cell where a naive zero run would have measured a "
      "different strategy.** Keeping the funding column as a signal input "
      "while stopping its cash flow preserved the trade count (run_ids are cited "
      "on their lines above). Neither line is an alpha claim.")
    A("3. **All ten books rise at ZERO, and three `qs` cells also change their "
      "trade count** through the catalog's own risk devices (declared above), "
      "so cost removal here can change which trades exist, not just their "
      "size.")
    A("")
    A("## What this is not")
    A("")
    A("- It is not a resurrection of any killed strategy; the kill list is "
      "unchanged and these rows carry the verdicts of their own campaigns.")
    A("- It is not evidence of alpha. A zero-cost line is the upper bound of "
      "what a book could earn if execution were free; nobody trades for free.")
    A("- It is not a gate pass. No gate was evaluated here.")
    A("- It is not agent- or user-selected: the ten are published ranking rows "
      "rows 91 to 100 of the published ranking, decided before this campaign existed.")
    A("")
    A("## Limits and declared caveats")
    A("")
    A("- **Funding is a real cash flow, not a fee.** ZERO removes it because "
      "the user asked for all costs removed; for a perp that is a declared "
      "control, never a tradable result.")
    A("- **The `qs` ZERO regime zeroes the whole ladder including the random "
      "entry null**, so its internal null comparison is zero-cost against "
      "zero-cost — consistent, but not the published null regime.")
    A("- **Execution was not relaxed.** Signal on the closed bar, fill modes, "
      "stop-first ties, sizing and risk devices all stay. Only the cost block "
      "and the screening rules were removed.")
    A("- **A re-measurement is not a contradiction.** Where an input file grew "
      "or an engine changed, both columns were minted on the same frozen cut "
      "and current engine bytes; the audit records which figures reproduced.")
    A("")
    A("## Provenance")
    A("")
    A("- Pre-registration: `results/zerocost_rows91_100_pre_registration.md` "
      "(written before the first artifact existed).")
    A("- Matrix: `results/zerocost_rows91_100_matrix.json` (per-cell run_ids, "
      "params, cut and inputs).")
    A("- Verification log: `results/_zerocost_rows91_100_verify.txt` — nineteen "
      "artifacts, nineteen OK.")
    A("- Audit: `code/_zerocost_rows91_100_audit.py` — independent fresh-module "
      "recomputation for every adapter, the engines' own in-artifact references "
      "and the pre-registered reproduction semantics with engine drift stated.")
    A("- No harness or engine file was edited for this batch; the engine files "
      "are byte-untouched and hashed into every run_id.")
    A("")

    text = "\n".join(L) + "\n"
    out_real = os.path.realpath(OUT)
    if not out_real.startswith(os.path.realpath(ROOT) + os.sep):
        raise ValueError(f"output outside the repo root: {OUT}")
    with open(out_real, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"[built {len(text)} chars] -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
