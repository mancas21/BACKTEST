"""Build results/zerocost_rows51_60_report_2026-11-23.md from the artifacts.

Every number comes from a stored artifact and is printed next to its run_id,
so `vrun.py guard --strict` can back it. No derived number is published as a
measurement; the two regimes are shown side by side.

Run: python code/_zerocost_rows51_60_report.py
"""
import json
import os
import re
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE)
os.chdir(ROOT)

MATRIX = os.path.join(ROOT, "results", "zerocost_rows51_60_matrix.json")
OUT = os.path.join(ROOT, "results", "zerocost_rows51_60_report_2026-11-23.md")
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
    if s == "dspack":
        return (m["costs"], "in preset", "n/a (kline-only)")
    if s == "mpv3":
        return (f"{m['fee_bps']:g}", f"{m['slip_bps']:g}", "n/a (no funding)")
    if s in ("pack100", "pack50d"):
        c = m.get("cost_bps_per_side")
        return (f"{c:g} combined" if c is not None else m["costs"],
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
    if s == "pack50d":
        return (f" Its own `zero_cost_pf` reads {m['zero_cost_pf']:.4f} and "
                f"`funding_paid` reads {m['funding_paid']:.4f}, `{rid}`.")
    if s == "pack100":
        return (f" Its own `zero_cost_pf` reads {m['zero_cost_pf']:.4f} "
                f"(fees removed with funding still charged), `{rid}`.")
    if s == "mpv3":
        return (f" Its own `cost_drag_pp` reads {m['cost_drag_pp']:.4f} percentage "
                f"points and `fees_paid` reads {m['fees_paid']:.2f}, `{rid}`.")
    return ""


NOTES = {
    51: ("A new additive `vrun.py` switch was audited for this cell before "
         "the run; the old ranking artifact predates the 2026-11-21 "
         "audit-fix and now fails `verify` on engine-hash drift, so the "
         "matching figure is a reproduction under current bytes."),
    52: ("The base figure matches the published one exactly, although the "
         "old ranking artifact's engine bytes drifted in the audit-fix "
         "campaign. Its trade count differs by one between regimes (below)."),
    53: ("This row reuses the SUI `cbpackf` artifacts minted for the previous "
         "batch: same adapter, symbol, params, engine bytes and cut. The ranking "
         "row is a different strategy (S10, not S02) read out of them."),
    54: ("The engine's own funding drag for S10 is measured inside the base "
         "artifact; the zero run removes both that cash flow and the fee."),
    55: ("The base figure matches the published one exactly under current "
         "engine bytes; its trade count differs by one (below)."),
    56: ("THE FUNDING-SIGNAL CASE. S07's signal READS the attached funding "
         "rate column, so simply withholding the JSON at ZERO made it stop "
         "trading altogether. The ZERO run keeps that column for the signal "
         "and sets `charge_funding=False`, so 34 trades occur in both "
         "regimes and only the money changes. This was found by the audit "
         "and declared in a dated addendum to the pre-registration."),
    57: ("A breakout book at the repo cost point. The old ranking artifact "
         "predates the audit-fix campaign and now fails `verify` on engine "
         "hash drift; both columns here are on current bytes."),
    58: ("The one row PUBLISHED with a real cost block (`repo6x5`): BASE is "
         "that published regime and ZERO is the engine's `author` preset. "
         "The kline file grew since the ranking, so the base figure is a "
         "re-measurement. The engine's own zero re-score and the author "
         "headline coincide."),
    59: ("The base figure matches the published one exactly under current "
         "engine bytes."),
    60: ("The only portfolio book of the five-batch control. Its kline inputs "
         "grew since the ranking, but the base figure matches the published "
         "one exactly; the engine's own cost drag is measured inside the "
         "artifact."),
}


def main():
    data = json.load(open(MATRIX, encoding="utf-8"))
    books, cells = data["books"], data["cells"]
    arts = {}
    for tag, rec in cells.items():
        for regime in ("base", "zero"):
            arts[(tag, regime)] = load(rec[regime]["run_id"])

    L = []
    A = L.append
    A("# Zero cost, no rules — rows 51-60 of the hundred best books re-run")
    A("")
    A("Date: 2026-11-23. Status: **experiment / control**. No verdict, no gate "
      "and no alpha claim (see `results/zerocost_rows51_60_pre_registration.md` "
      "and its dated addendum, both written before the market artifacts). Sixth "
      "batch of the control begun in `results/zerocost_report_2026-11-20.md` "
      "and continued in the four reports that followed it.")
    A("")
    A("## The question")
    A("")
    A("Ten more books were taken from `results/top100_2026-10-31.md` — rows 51 "
      "to 60, in the order that list already published — and each was run twice "
      "on the same frozen cut by the same engine bytes: once under its published "
      "cost regime (**BASE**) and once with fees, slippage and funding cash flow "
      "at zero (**ZERO**). No screening gate is applied. ds3 is the one "
      "book here that was published WITH a real cost block (`repo6x5`), so its "
      "ZERO uses the same engine's `author` preset.")
    A("")
    A("Ten books produced twenty artifacts (two `cbpackf` SUI artifacts reused "
      "from the rows 41-50 batch: same adapter, symbol, params, engine and cut), "
      "every one verifying bit-for-bit "
      "(`results/_zerocost_rows51_60_verify.txt`).")
    A("")
    A("## The ten, both regimes")
    A("")
    A("Every row is one stored artifact; the run_id is on its own row. Net % is "
      "the book's own full-window return, PF its profit factor, Trades its "
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
    A("The fields below are the artifacts' own declarations. `qs` declares the "
      "catalog ladder's base point; `cbpackf`, `pack100` and `pack50d` declare "
      "per-side costs plus the engine's funding flag (the latter two as one "
      "combined figure); `mpv3` declares fee, slippage and round-trip; "
      "`dspack` declares the preset name (`repo6x5` or `author`).")
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
    A("Funding signs are engine-specific and quoted AS STORED. Row 56's ZERO "
      "still ATTACHES the funding rate for the signal but declares "
      "`funding_signal: true`, `funding_charged: false` and zero settlements.")
    A("")
    A("## Book by book")
    A("")
    A("Each line quotes its own artifacts, with run_ids on the line.")
    A("")
    for b in books:
        b_id, z_id = b["base"]["run_id"], b["zero"]["run_id"]
        ids = f"(`{b_id}`, `{z_id}`)"
        sid = b["where"] if b["where"] != "metrics" else None
        A(f"**{b['book']} — {b['market']}.** Base net "
          f"{b['base']['net_pct']:.2f}% at PF {b['base']['pf']:.3f} on "
          f"{int(b['base']['n_trades'])} trades; zero net "
          f"{b['zero']['net_pct']:.2f}% at PF {b['zero']['pf']:.3f} on "
          f"{int(b['zero']['n_trades'])} trades {ids}."
          + extra(arts[(b["tag"], "base")], sid)
          + " " + NOTES.get(b["row"], ""))
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
    A("1. **The old ranking artifacts of `pack50d`, `pack100` and the `qs` "
      "rows no longer verify: the 2026-11-21 audit-fix changed their engine "
      "bytes.** That is a provenance fact, not tampering. Every artifact in "
      "this report was minted on current bytes and verifies; where a BASE "
      "figure matches the old published one, the audit calls it an exact "
      "*figure* reproduction, not a bit-identical artifact.")
    A("2. **Removing the funding JSON is not safe for a strategy whose signal "
      "reads funding.** S07's first ZERO attempt produced no trades at all; "
      "the pre-registered addendum added a signal-only funding path, and the "
      "correct ZERO run keeps the same 34 trades at a higher net line (both "
      "run_ids are cited on row 56).")
    A("3. **All ten books rise at ZERO, but the mechanism differs.** ds3's "
      "costed-to-author gap is the largest in the five batches; the portfolio "
      "book's own measured drag is cited on row 60; and two `qs` cells change "
      "trade count through the catalog's own risk devices (declared above).")
    A("")
    A("## What this is not")
    A("")
    A("- It is not a resurrection of any killed strategy. The kill list is "
      "unchanged; these rows carry the verdicts of their own campaigns (the "
      "strategy packs, the QS catalog, the DeepSeek pack and MP-V3).")
    A("- It is not evidence of alpha. A zero-cost line is the upper bound of "
      "what a book could earn if execution were free; nobody trades for free.")
    A("- It is not a gate pass. No gate was evaluated here.")
    A("- It is not agent- or user-selected: the ten are published ranking rows "
      "51 to 60, decided before this campaign existed.")
    A("")
    A("## Limits and declared caveats")
    A("")
    A("- **Funding is a real cash flow, not a fee.** ZERO removes the cash "
      "flow because the user asked for all costs removed; for a perp that is "
      "a declared control, never a tradable result. Row 56 keeps the funding "
      "column only as a signal input, never as money.")
    A("- **The `qs` ZERO regime zeroes the whole ladder including the "
      "random-entry null**, so its internal null comparison is zero-cost "
      "against zero-cost — consistent, but not the published null regime.")
    A("- **Execution was not relaxed.** Signal on the closed bar, fill modes, "
      "stop-first ties, sizing and risk devices all stay. Only the cost block "
      "and the screening rules were removed.")
    A("- **A re-measurement is not a contradiction.** Where an input file grew "
      "or an engine changed since the ranking, both columns were minted on the "
      "same frozen cut and current engine bytes; the audit records which "
      "figures reproduced exactly.")
    A("")
    A("## Provenance")
    A("")
    A("- Pre-registration: `results/zerocost_rows51_60_pre_registration.md` "
      "with its dated addendum (both written before the market artifacts).")
    A("- Matrix: `results/zerocost_rows51_60_matrix.json` (per-cell run_ids, "
      "params, cut and inputs).")
    A("- Verification log: `results/_zerocost_rows51_60_verify.txt` — twenty "
      "artifacts, twenty OK.")
    A("- Audit: `code/_zerocost_rows51_60_audit.py` — independent fresh-module "
      "recomputation for `pack50d`, `qs`, `pack100`, `dspack` and `mpv3`, "
      "declared fields and determinism for `cbpackf`, and the pre-registered "
      "reproduction semantics with engine drift stated explicitly.")
    A("- Harness changes: one additive `pack50d` costs/funding switch and one "
      "additive `cbpackf` `funding_signal` option, both in `vrun.py`, both "
      "restoring module state in `finally`. Engine files are byte-untouched "
      "and hashed into every run_id.")
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
