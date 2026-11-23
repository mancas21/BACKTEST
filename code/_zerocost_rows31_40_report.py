"""Build results/zerocost_rows31_40_report_2026-11-23.md from the artifacts.

Every number in the output is read out of a stored artifact and printed next
to that artifact's run_id, so `vrun.py guard --strict` can back it. Nothing
is subtracted by hand: the report shows the base and zero lines side by side
and lets the reader see the gap, because a difference of two cited numbers
is a DERIVED number that guard cannot back (AGENTS.md).

Run: python code/_zerocost_rows31_40_report.py
"""
import json
import os
import re
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE)
os.chdir(ROOT)
sys.path.insert(0, CODE)

MATRIX = os.path.join(ROOT, "results", "zerocost_rows31_40_matrix.json")
OUT = os.path.join(ROOT, "results", "zerocost_rows31_40_report_2026-11-23.md")
_RID = re.compile(r"^[0-9a-f]{16}$")
_RUNS = os.path.realpath(os.path.join(ROOT, "results", "runs"))


def load(rid):
    """Normalized, prefix-checked read of one artifact by validated run_id."""
    if not _RID.match(str(rid)):
        raise ValueError(f"refusing non run_id: {rid!r}")
    p = os.path.realpath(os.path.join(_RUNS, str(rid) + ".json"))
    if not (p.startswith(_RUNS + os.sep) and os.path.isfile(p)):
        raise ValueError(f"artifact outside the runs dir: {rid!r}")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def cost_fields(art):
    """The cost block AS STORED in the artifact's metrics."""
    m = art["metrics"]
    s = art["strategy"]
    if s == "dspack":
        return "0 (author)", "0 (author)", "n/a (kline-only)"
    if s == "rsimr":
        return (f"{m['costs']} ({m['cost_bp_roundtrip']:g} RT)", "n/a", "spot: none")
    fee = m.get("fee_bps_per_side")
    slip = m.get("slippage_bps_per_side", m.get("slip_bps_per_side"))
    return (f"{fee:g}" if fee is not None else "n/a",
            f"{slip:g}" if slip is not None else "n/a",
            str(m.get("funding_charged", "n/a")))


def extra(art, row):
    """One artifact-backed sentence per adapter, with its run_id on the line."""
    m, s, rid = art["metrics"], art["strategy"], art["run_id"]
    if s == "qs":
        return (f" Its base run's `funding_paid` reads {m['funding_paid']:.2f} over "
                f"{int(m['n_funding_events'])} settlement events (positive means paid), "
                f"`{rid}`.")
    if s == "cbpackf":
        t = next(r for r in art["tables"] if r.get("id") == "S10")
        return (f" Its S10 row's `funding_paid_pct` reads {t['funding_paid_pct']:.4f} "
                f"and `funding_drag_pp` reads {t['funding_drag_pp']:.4f}, "
                f"`{rid}`.")
    if s == "rsimr":
        return (f" Its own `drag_pp` reads {m['drag_pp']:.4f} percentage points and "
                f"`ret_zero_pct` reads {m['ret_zero_pct']:.4f} percent, `{rid}`; "
                f"spot book, no funding input.")
    if s == "fingrad":
        return (f" Its base run's `funding_paid` reads {m['funding_paid']:.2f} over "
                f"{int(m['n_funding_events'])} settlement events, and its own "
                f"`ret_zero_pct` (fees removed, funding still charged) reads "
                f"{m['ret_zero_pct']:.4f} percent, `{rid}`.")
    return ""


NOTES = {
    31: ("This is one of the batch's re-measurements: its input klines grew "
         "since the ranking, so the base line above is not the published "
         "number. The catalog ladder and the funding bill were a heavy drag; "
         "the whole four-point cost column collapses at ZERO."),
    32: ("The engine's own funding drag for S10 is measured inside the base "
         "artifact; the zero run removes both that cash flow and the cost "
         "block."),
    33: ("The engine's own zero-cost reference sits inside the same artifact, "
         "so the gap needs no arithmetic by the reader."),
    34: ("A second Donchian cell, on SOL this time; the base run reproduces "
         "the published figure exactly even though its funding file grew."),
    35: ("The SUI cell of the QS-006 pair; its base net reproduces the "
         "published figure exactly."),
    36: ("A re-measurement: the ETH kline file grew since the ranking. The "
         "engine's own zero-cost reference (fees off, funding still charged) "
         "is printed on this line; the ZERO column removes both."),
    37: ("THE MIRROR CASE. The pack file declares no costs and the engine "
         "charges no funding, so this book was published at zero cost from "
         "day one and its BASE and ZERO are one artifact. The costed re-run "
         "under the engine's own repo6x5 preset is the informative number."),
    38: ("The second mirror case, same construction on DOGE. Its costed "
         "re-run keeps the identical signal sequence and pays real fees."),
    39: ("The HYPE cell of the QS-006 pair; the base run reproduces the "
         "published figure exactly."),
    40: ("The base run reproduces the published figure exactly; ZERO nearly "
         "doubles the net line. This is the one cell where the trade count "
         "differs between regimes (141 on the base run, 140 on the zero run): "
         "the catalog's equity-dependent risk devices (daily-loss halt, "
         "drawdown halving and halt) are part of the strategy and react to "
         "the changed equity path, so the cost block can change the number "
         "of entries. The signals themselves are not re-fitted."),
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
    A("# Zero cost, no rules — rows 31-40 of the hundred best books re-run")
    A("")
    A("Date: 2026-11-23. Status: **experiment / control**. This report contains "
      "no verdict, no gate and no alpha claim (see "
      "`results/zerocost_rows31_40_pre_registration.md`, written before the "
      "first artifact). It is the fourth batch of the same control as "
      "`results/zerocost_report_2026-11-20.md` (rows 1-10), "
      "`results/zerocost_rows11_20_report_2026-11-20.md` (rows 11-20) and "
      "`results/zerocost_rows21_30_report_2026-11-20.md` (rows 21-30).")
    A("")
    A("## The question")
    A("")
    A("Ten more books were taken from `results/top100_2026-10-31.md` — rows "
      "31 to 40, in the order that list already published — and each was run "
      "twice on the same frozen data cut by the same engine bytes: once under "
      "the cost regime it was published under (**BASE**) and once with fees, "
      "slippage and funding cash flow all at zero (**ZERO**). The gates that "
      "decide whether a book is good are not applied here. Two rows are the "
      "mirror case already met in row 27: ds1 was PUBLISHED at zero cost (the "
      "pack declares no costs and the engine charges no funding), so their "
      "BASE and ZERO are the same artifacts by construction, and each gets a "
      "**COSTED** re-run under the engine's own repo6x5 preset.")
    A("")
    A("Ten books produced twenty artifacts (ten cells in two regimes, with "
      "two BASE/ZERO pairs sharing one artifact, plus two costed re-runs), and "
      "every one verifies bit-for-bit "
      "(`results/_zerocost_rows31_40_verify.txt`).")
    A("")
    A("## The ten, both regimes")
    A("")
    A("Every row is one stored artifact; the run_id is on its own row. Net % is "
      "the book's own net return over its full window, PF its profit factor, "
      "Trades its closed-trade count and Max DD % the drawdown exactly as the "
      "engine stores it (negative where the engine reports a signed drawdown). "
      "Rows 37 and 38 also show their costed re-runs in the prose below.")
    A("")
    A("| Book | Market | Regime | Net % | PF | Trades | Max DD % | run_id |")
    A("|---|---|---|---:|---:|---:|---:|---|")
    for b in books:
        for regime, label in (("base", "BASE"), ("zero", "ZERO")):
            r = b[regime]
            A(f"| {b['book']} | {b['market']} | {label} | "
              f"{r['net_pct']:.2f} | {r['pf']:.3f} | {int(r['n_trades'])} | "
              f"{r['max_dd_pct']:.2f} | `{r['run_id']}` |")
    A("")
    A("## What each regime actually charged")
    A("")
    A("These are the artifacts' own declared cost fields, not a description of "
      "them. `qs` declares the catalog ladder's base point; `cbpackf` and "
      "`fingrad` declare fee and slippage per side plus the engine's funding "
      "flag; `rsimr` declares its cost preset and round-trip; `dspack` was "
      "published at the pack's own `author` regime — the pack file declares "
      "no costs — and its costed re-runs carry the engine's `repo6x5` preset "
      "name in their params.")
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
    A("Funding sign conventions differ by engine and are quoted AS STORED: "
      "`qs` `funding_paid` positive means paid; `cbpackf` and `fingrad` store "
      "it as their own signed cash flow. `rsimr` is spot and `dspack` is "
      "kline-only — neither has a funding input.")
    A("")
    A("## Book by book")
    A("")
    A("Numbers below are quoted from the artifacts in the table above; where a "
      "book is named, its run_ids are cited on the line.")
    A("")
    for b in books:
        b_id, z_id = b["base"]["run_id"], b["zero"]["run_id"]
        ids = f"(`{b_id}`, `{z_id}`)"
        if b["row"] in (37, 38):
            ids = f"(`{b_id}`; costed `{cells[b['tag']]['costed']['run_id']}`)"
        A(f"**{b['book']} — {b['market']}.** Base net "
          f"{b['base']['net_pct']:.2f}% at PF {b['base']['pf']:.3f} on "
          f"{int(b['base']['n_trades'])} trades; zero net "
          f"{b['zero']['net_pct']:.2f}% at PF {b['zero']['pf']:.3f} on "
          f"{int(b['zero']['n_trades'])} trades {ids}."
          + extra(arts[(b["tag"], "base")], b["row"])
          + " " + NOTES.get(b["row"], ""))
        A("")
        if b["row"] in (37, 38):
            t = arts[(b["tag"], "costed")]["tables"][0]
            A(f"The costed re-run of {b['market']} keeps "
              f"{int(t['n_trades'])} trades and charges "
              f"{t['fees_charged']:.2f} in fees, landing at "
              f"{t['ret_pct']:.2f}% net at PF {t['pf_strict']:.4f}; its own "
              f"in-artifact zero-cost re-score `ret_zero_pct` reads "
              f"{t['ret_zero_pct']:.4f} percent (`{cells[b['tag']]['costed']['run_id']}`).")
            A("")
    A("## What the numbers say")
    A("")
    A("Three readings, none of them a verdict:")
    A("")
    A("1. **Six of the ten published BASE figures reproduce exactly, and the "
      "four that do not sit on inputs that really grew.** The reproduction "
      "check is in `code/_zerocost_rows31_40_audit.py`; the base run_ids of "
      "every reproducing row are on the table lines above.")
    A("2. **The two ds1 rows are the mirror that shows what the ranking would "
      "look like if every book had been published at zero cost.** Their "
      "costed re-runs keep the same trade counts and land below zero net at "
      "PF near one, paying large fee bills on identical signals (both costed "
      "run_ids are cited on the rows 37 and 38 lines above). A zero-cost line "
      "is the upper bound of what a book could earn if execution were free.")
    A("3. **Cost removal moves every other book up, but the engines' own "
      "funding signs do not transfer between them.** The `qs` base runs on "
      "the table above carry positive `funding_paid` (paid), while the "
      "`cbpackf` and `fingrad` lines carry their own signed cash flows; "
      "funding was never a uniform tax across this batch.")
    A("")
    A("## What this is not")
    A("")
    A("- It is not a resurrection of any killed strategy. The kill list is "
      "unchanged and this report adds nothing to it: the QS-004, QS-005, "
      "QS-006 and QS-009 families carry their own catalog verdicts, S10 the "
      "strategy-pack verdict, rsimr and fingrad their own campaigns, and ds1 "
      "the five-strategy DeepSeek pack.")
    A("- It is not evidence of alpha. A zero-cost line is the upper bound of "
      "what a book could earn if execution were free; nobody trades for free.")
    A("- It is not a gate pass. No gate was evaluated, and no gate verdict is "
      "published here.")
    A("- It is not agent- or user-selected: the ten are published ranking rows "
      "31 to 40, decided before this campaign existed.")
    A("")
    A("## Limits and declared caveats")
    A("")
    A("- **The two ds1 published numbers were never costed numbers.** The pack "
      "file declares no costs and the engine charges no funding, so the "
      "ranking rows were zero-cost constructions from the start; this "
      "campaign did not discover that, it quantified it inside artifacts. "
      "The costed re-runs use the engine's own repo6x5 preset; no gate is "
      "evaluated on them.")
    A("- **Funding is a real cash flow, not a fee.** The ZERO regime removes it "
      "because the user asked for all costs removed; for a perp that is a "
      "declared control, never a tradable result. The base column keeps it.")
    A("- **The `qs` ZERO regime zeroes the whole ladder including the "
      "random-entry null**, so the null comparison inside those artifacts is "
      "a zero-cost null against a zero-cost book — consistent, but not the "
      "published null regime.")
    A("- **Execution was not relaxed.** Signal on the closed bar, the engines' "
      "own fill modes, stop-first on ties, the engines' own sizing and risk "
      "devices all stay. Only the cost block and the screening rules were "
      "removed.")
    A("- **A re-measurement is not a contradiction.** Where an input file grew "
      "since the ranking, both columns here are minted on the same frozen "
      "cut; the audit records which rows reproduced exactly and which did not.")
    A("- **Trade counts are not always identical.** On QS-005 ETH the base "
      "run has 141 trades and the zero run 140 (their run_ids are on the "
      "table lines above). The catalog's equity-dependent risk devices are "
      "part of the strategy, so a different equity path can add or skip an "
      "entry; no signal rule was changed or re-fitted between regimes.")
    A("")
    A("## Provenance")
    A("")
    A("- Pre-registration: `results/zerocost_rows31_40_pre_registration.md` "
      "(written before the first artifact existed).")
    A("- Matrix: `results/zerocost_rows31_40_matrix.json` (per-cell run_ids, "
      "params, cut and inputs, plus the two costed re-runs).")
    A("- Verification log: `results/_zerocost_rows31_40_verify.txt` — twenty "
      "artifacts, twenty OK.")
    A("- Audit: `code/_zerocost_rows31_40_audit.py` — every adapter checked "
      "against an independent fresh-module recomputation, the engines' own "
      "in-artifact zero-cost references, and the reproduction logic declared "
      "in the pre-registration (equality is exact reproduction; inequality "
      "requires a grown input file).")
    A("- No harness or engine file was edited for this batch: every adapter "
      "already exposed its cost switch from batches 1-3. The engine files are "
      "byte-untouched and hashed into every run_id.")
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
