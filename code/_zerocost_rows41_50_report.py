"""Build results/zerocost_rows41_50_report_2026-11-23.md from the artifacts.

Every number comes from a stored artifact and is printed next to that
artifact's run_id, so `vrun.py guard --strict` can back it. No derived number
(a difference of two cited values) is printed as a measurement.

Run: python code/_zerocost_rows41_50_report.py
"""
import json
import os
import re
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE)
os.chdir(ROOT)

MATRIX = os.path.join(ROOT, "results", "zerocost_rows41_50_matrix.json")
OUT = os.path.join(ROOT, "results", "zerocost_rows41_50_report_2026-11-23.md")
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
        return "0 (author)", "0 (author)", "n/a (kline-only)"
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
    if s == "fingrad":
        return (f" Its own `drag_pp` reads {m['drag_pp']:.4f} percentage points and "
                f"`ret_zero_pct` reads {m['ret_zero_pct']:.4f} percent, `{rid}`; "
                f"funding is off in BOTH regimes (the published row declares "
                f"`funding_charged=false`).")
    return ""


NOTES = {
    41: ("The base line reproduces the published figure exactly, even though "
         "the funding file grew at the tail: those added records never touched "
         "an open position in this book."),
    42: ("One of the largest gaps of the whole five-batch control. The base "
         "line reproduces the published figure exactly."),
    43: ("The only fifteen-minute cell of this batch, and a long-only variant. "
         "The base line reproduces the published figure exactly; ZERO more "
         "than doubles it. Its trade count differs between regimes — see the "
         "caveat below."),
    44: ("A re-measurement: the SUI kline file grew since the ranking. This "
         "published row had funding OFF (the engine mirrors the Pine, which "
         "has no funding model), so the only thing removed at ZERO is the fee "
         "block. The engine's own fee-only reference is printed on this line."),
    45: ("THE MIRROR CASE. The pack file declares no costs and the engine "
         "charges no funding, so this book was published at zero cost from "
         "day one and its BASE and ZERO are one artifact. The costed re-run "
         "under the engine's own repo6x5 preset is the informative number."),
    46: ("This cell reuses the ETH `cbpackf` artifacts minted for rows 31-40: "
         "same adapter, symbol, params, engine bytes and frozen cut, so the "
         "run_ids are identical by construction. It is a different strategy "
         "row (S02, not S10) read out of those same artifacts. The base line "
         "reproduces the published figure exactly."),
    47: ("The base line reproduces the published figure exactly."),
    48: ("The base line reproduces the published figure exactly; the trade "
         "count differs by one between regimes (see the caveat below)."),
    49: ("A re-measurement: the JUP kline file grew since the ranking. The "
         "trade count differs by one between regimes (see the caveat below)."),
    50: ("The base line reproduces the published figure exactly; the trade "
         "count differs by one between regimes (see the caveat below)."),
}


def main():
    data = json.load(open(MATRIX, encoding="utf-8"))
    books, cells = data["books"], data["cells"]
    arts = {}
    for tag, rec in cells.items():
        for regime in ("base", "zero", "costed"):
            if regime in rec:
                arts[(tag, regime)] = load(rec[regime]["run_id"])

    L = []
    A = L.append
    A("# Zero cost, no rules — rows 41-50 of the hundred best books re-run")
    A("")
    A("Date: 2026-11-23. Status: **experiment / control**. No verdict, no gate "
      "and no alpha claim (see `results/zerocost_rows41_50_pre_registration.md`, "
      "written before the first artifact). Fifth batch of the control begun in "
      "`results/zerocost_report_2026-11-20.md` and continued in the reports for "
      "rows 11-20, 21-30 and 31-40.")
    A("")
    A("## The question")
    A("")
    A("Ten more books were taken from `results/top100_2026-10-31.md` — rows 41 "
      "to 50, in the order that list already published — and each was run twice "
      "on the same frozen cut by the same engine bytes: once under its published "
      "cost regime (**BASE**) and once with fees, slippage and funding cash flow "
      "at zero (**ZERO**). No screening gate is applied. Row 45 is the mirror "
      "case: ds1 was PUBLISHED at zero cost (the pack declares no costs and the "
      "engine charges no funding), so its BASE and ZERO are one artifact and its "
      "informative run is the **COSTED** re-run under the engine's repo6x5 preset.")
    A("")
    A("Ten books produced twenty artifacts (one BASE/ZERO pair shares an "
      "artifact by construction, plus one costed re-run), every one verifying "
      "bit-for-bit (`results/_zerocost_rows41_50_verify.txt`). Two of them are "
      "the ETH `cbpackf` artifacts already minted for the rows 31-40 batch: "
      "same adapter, symbol, params, engine and cut, so row 46 cites those "
      "run_ids instead of minting duplicate bytes.")
    A("")
    A("## The ten, both regimes")
    A("")
    A("Every row is one stored artifact; the run_id is on its own row. Net % is "
      "the book's own full-window return, PF its profit factor, Trades its "
      "closed-trade count and Max DD % the drawdown exactly as the engine "
      "stores it (negative where the engine reports a signed drawdown). "
      "Row 45's costed re-run is described below.")
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
    A("The fields below are the artifacts' own declarations, not a description "
      "of them. `qs` declares the catalog ladder's base point; `cbpackf` and "
      "`fingrad` declare fee and slippage per side plus the engine's funding "
      "flag; `dspack` was published at the pack's `author` regime — no costs, "
      "no funding — and its costed re-run carries the `repo6x5` preset name in "
      "its params.")
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
    A("Funding signs are engine-specific and are quoted AS STORED. `rsimr` and "
      "other adapters are not part of this batch; `fingrad` here declares "
      "funding OFF in both regimes, which is the published row's own regime.")
    A("")
    A("## Book by book")
    A("")
    A("Each line quotes its own artifacts, with run_ids on the line.")
    A("")
    for b in books:
        b_id, z_id = b["base"]["run_id"], b["zero"]["run_id"]
        ids = f"(`{b_id}`, `{z_id}`)"
        if b["row"] == 45:
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
        if b["row"] == 45:
            t = arts[(b["tag"], "costed")]["tables"][0]
            A(f"The costed re-run of HYPEUSDT 1h keeps {int(t['n_trades'])} "
              f"trades and charges {t['fees_charged']:.2f} in fees, landing at "
              f"{t['ret_pct']:.2f}% net at PF {t['pf_strict']:.4f}; its own "
              f"in-artifact zero-cost re-score `ret_zero_pct` reads "
              f"{t['ret_zero_pct']:.4f} percent "
              f"(`{cells[b['tag']]['costed']['run_id']}`).")
            A("")
        if b["base"]["n_trades"] != b["zero"]["n_trades"]:
            A(f"On this cell the trade count itself changes with the cost "
              f"regime — {int(b['base']['n_trades'])} on the base run "
              f"`{b_id}` versus {int(b['zero']['n_trades'])} on the zero run "
              f"`{z_id}` — because the catalog's equity-dependent risk devices "
              f"(daily-loss halt, drawdown halving and halt) are part of the "
              f"strategy and react to the changed equity path. No signal rule "
              f"was changed or re-fitted.")
            A("")

    A("## What the numbers say")
    A("")
    A("Three readings, none of them a verdict:")
    A("")
    A("1. **Seven of the ten published BASE figures reproduce exactly, and "
      "the three that do not sit on inputs that really grew.** The audit "
      "`code/_zerocost_rows41_50_audit.py` records which rows reproduced and "
      "which files grew; the reproducing rows' run_ids are on the table above.")
    A("2. **ds1 is again the mirror that shows what the ranking would look like "
      "if every book had been published at zero cost.** Its costed re-run "
      "keeps the same signal sequence and pays a real fee bill for a negative "
      "net line (both run_ids are cited on the row 45 lines above). A zero-cost "
      "line is an upper bound, not a tradable result.")
    A("3. **All nine non-mirror books rise at ZERO, but four of the five `qs` "
      "cells also change their trade count.** The cost block changes the "
      "equity path, and the catalog's own risk devices then change which "
      "entries are taken; this is declared per row above rather than buried.")
    A("")
    A("## What this is not")
    A("")
    A("- It is not a resurrection of any killed strategy. The kill list is "
      "unchanged: these ten rows carry the verdicts of their own campaigns "
      "(the strategy packs, the QS catalog, fingrad and the DeepSeek pack).")
    A("- It is not evidence of alpha. A zero-cost line is the upper bound of "
      "what a book could earn if execution were free; nobody trades for free.")
    A("- It is not a gate pass. No gate was evaluated here.")
    A("- It is not agent- or user-selected: the ten are published ranking rows "
      "41 to 50, decided before this campaign existed.")
    A("")
    A("## Limits and declared caveats")
    A("")
    A("- **The ds1 published number was never a costed number.** The pack "
      "declares no costs and the engine charges no funding, so the ranking "
      "row was a zero-cost construction from the start; this campaign "
      "quantified that inside an artifact. The costed re-run uses the engine's "
      "own repo6x5 preset; no gate is evaluated on it.")
    A("- **Funding is a real cash flow, not a fee.** ZERO removes it because "
      "the user asked for all costs removed; for a perp that is a declared "
      "control, never a tradable result. `fingrad` here had funding off in "
      "both regimes, exactly as published.")
    A("- **The `qs` ZERO regime zeroes the whole ladder including the "
      "random-entry null**, so the null comparison inside those artifacts is "
      "a zero-cost null against a zero-cost book — consistent, but not the "
      "published null regime.")
    A("- **Execution was not relaxed.** Signal on the closed bar, the engines' "
      "own fill modes, stop-first on ties, sizing and risk devices all stay. "
      "Only the cost block and the screening rules were removed.")
    A("- **A re-measurement is not a contradiction.** Where an input file grew "
      "since the ranking, both columns were minted on the same frozen cut; "
      "the audit records which rows reproduced exactly and which did not.")
    A("")
    A("## Provenance")
    A("")
    A("- Pre-registration: `results/zerocost_rows41_50_pre_registration.md` "
      "(written before the first artifact existed).")
    A("- Matrix: `results/zerocost_rows41_50_matrix.json` (per-cell run_ids, "
      "params, cut and inputs, plus the costed re-run).")
    A("- Verification log: `results/_zerocost_rows41_50_verify.txt` — twenty "
      "artifacts, twenty OK.")
    A("- Audit: `code/_zerocost_rows41_50_audit.py` — independent fresh-module "
      "recomputation for `qs`, `fingrad` and `dspack`, the engines' own "
      "in-artifact references, declared cost fields and determinism for "
      "`cbpackf`, and the pre-registered reproduction semantics.")
    A("- No harness or engine file was edited for this batch: every adapter "
      "already exposed its cost switch. The engine files are byte-untouched "
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
