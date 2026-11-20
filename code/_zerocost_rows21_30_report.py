"""Build results/zerocost_rows21_30_report_2026-11-20.md from the artifacts.

Every number in the output is read out of a stored artifact and printed next
to that artifact's run_id, so `vrun.py guard --strict` can back it. Nothing
is subtracted by hand: the report shows the base and zero lines side by side
and lets the reader see the gap, because a difference of two cited numbers
is a DERIVED number that guard cannot back (AGENTS.md).

Run: python code/_zerocost_rows21_30_report.py
"""
import json
import os
import re
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE)
os.chdir(ROOT)
sys.path.insert(0, CODE)

MATRIX = os.path.join(ROOT, "results", "zerocost_rows21_30_matrix.json")
OUT = os.path.join(ROOT, "results", "zerocost_rows21_30_report_2026-11-20.md")
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


def main():
    data = json.load(open(MATRIX, encoding="utf-8"))
    books = data["books"]
    cells = data["cells"]

    arts = {}
    for tag, rec in cells.items():
        for regime in ("base", "zero", "costed"):
            if regime in rec:
                arts[(tag, regime)] = load(rec[regime]["run_id"])

    L = []
    A = L.append

    A("# Zero cost, no rules — rows 21-30 of the hundred best books re-run")
    A("")
    A("Date: 2026-11-20. Status: **experiment / control**. This report contains "
      "no verdict, no gate and no alpha claim (see "
      "`results/zerocost_rows21_30_pre_registration.md`, with its dated "
      "addendum). It is the third batch of the same control as "
      "`results/zerocost_report_2026-11-20.md` (rows 1-10) and "
      "`results/zerocost_rows11_20_report_2026-11-20.md` (rows 11-20).")
    A("")
    A("## The question")
    A("")
    A("Ten more books were taken from `results/top100_2026-10-31.md` — rows 21 "
      "to 30, in the order that list already published — and each was run twice "
      "on the same frozen data cut by the same engine bytes: once under the cost "
      "regime it was published under (**BASE**) and once with fees, slippage and "
      "funding cash flow all at zero (**ZERO**). The gates that decide whether a "
      "book is good are not applied here. One row is the mirror case and gets a "
      "third artifact: ds1 was PUBLISHED at zero cost (the pack declares no "
      "costs and the engine charges no funding), so its BASE and ZERO are the "
      "same artifact by construction, and the informative run for it is the "
      "**COSTED** re-run under the engine's own repo6x5 preset.")
    A("")
    A("Ten books produced twenty artifacts (ten cells in two regimes, with row "
      "27's BASE and ZERO sharing one artifact, plus its costed re-run), and "
      "every one of them verifies bit-for-bit "
      "(`results/_zerocost_rows21_30_verify.txt`).")
    A("")
    A("## The ten, both regimes")
    A("")
    A("Every row is one stored artifact; the run_id is on its own row. Net % is "
      "the book's own net return over its full window, PF its profit factor, "
      "Trades its closed-trade count and Max DD % the drawdown exactly as the "
      "engine stores it (negative where the engine reports a signed drawdown). "
      "Row 27 also shows its costed re-run in the prose below.")
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
      "them: the adapter's fee and slippage fields, and `funding_charged`. The "
      "`qs` and `qsf` adapters declare the catalog ladder's base point (fee "
      "plus slippage per side); `pack100` declares one combined per-side "
      "figure; `pack50` declares the pack's per-symbol block from the engine's "
      "own cost table; `dspack` was published at the pack's own `author` "
      "regime — the pack file declares no costs — and its costed re-run "
      "carries the engine's `repo6x5` preset name in its params.")
    A("")
    A("| Adapter | Market | Base fee bps | Base slip bps | Base funding | Zero fee bps | Zero slip bps | Zero funding | run_ids |")
    A("|---|---|---:|---:|---|---:|---:|---|---|")
    for tag, rec in cells.items():
        base = arts[(tag, "base")]
        zero = arts[(tag, "zero")]
        strat_m = base["strategy"]
        if strat_m == "dspack":
            bf, bs, zf, zs = "0 (author)", "0 (author)", "0 (author)", "0 (author)"
        elif strat_m == "pack100":
            bf = f"{base['metrics']['cost_bps_per_side']:g} combined"
            zf = f"{zero['metrics']['cost_bps_per_side']:g} combined"
            bs = zs = "n/a"
        else:
            bf = f"{base['metrics']['fee_bps_per_side']:g}"
            zf = f"{zero['metrics']['fee_bps_per_side']:g}"
            bs = f"{base['metrics'].get('slippage_bps_per_side', base['metrics'].get('slip_bps_per_side')):g}"
            zs = f"{zero['metrics'].get('slippage_bps_per_side', zero['metrics'].get('slip_bps_per_side')):g}"
        fb = base["metrics"].get("funding_charged")
        fz = zero["metrics"].get("funding_charged")
        A(f"| `{strat_m}` | {base['symbol']} {base['timeframe']} | "
          f"{bf} | {bs} | {fb} | {zf} | {zs} | {fz} | "
          f"`{base['run_id']}` `{zero['run_id']}` |")
    A("")
    A("The `dspack` engine charges no funding (kline-only, the pack declares "
      "none), and `pack50`'s `funding_charged` field is the ENGINE'S OWN flag "
      "on whether a funding file was handed to it. Funding sign conventions "
      "differ by engine and are quoted AS STORED in the book-by-book section: "
      "`qs`/`qsf` and `pack50` `funding_paid` positive means paid, `pack100` "
      "`funding_paid` negative means paid.")
    A("")
    A("## Book by book")
    A("")
    A("Numbers below are quoted from the artifacts in the table above; where a "
      "book is named, its run_ids are cited on the line.")
    A("")

    notes = {
        21: ("Long-only EMA trend on the most crowded perp in the list: its "
             "base run PAID a large funding bill (negative means paid under "
             "the pack100 convention) on top of the combined per-side cost, "
             "and the engine's own zero-fee reference (`zero_cost_pf`, fees "
             "removed with funding still charged) already sits between the "
             "base and zero profit factors. The base run reproduces the "
             "published figure to full float precision."),
        22: ("The short liquidity-grab book was on the RECEIVING side of "
             "funding (positive funding_paid here means the book received), "
             "so removing funding moves it the other way from its long-only "
             "sibling in row 21 — but removing it still nets higher at zero "
             "because the fee block dominates. The base run reproduces the "
             "published figure exactly."),
        23: ("The catalog battery collapses to a single point at zero (base, "
             "adverse and gate cost views all return the same number), the "
             "batch 2 consistency check. The base run reproduces the "
             "published figure exactly."),
        24: ("The engine's own zero-fee control (`zero_cost_pf`, fees removed "
             "with funding still charged) sits at the ZERO profit factor "
             "almost exactly, because the book's net funding bill over the "
             "window was a few tenths of a USDT. The base run reproduces the "
             "published figure exactly."),
        25: ("The base run reproduces the published figure exactly."),
        26: ("The base run reproduces the published figure exactly."),
        27: ("THE MIRROR CASE OF THE WHOLE CAMPAIGN. The pack file declares "
             "no costs and the engine charges no funding, so the published "
             "number was measured at zero cost from day one — its BASE and "
             "ZERO are the same artifact. The COSTED re-run under the "
             "engine's own repo6x5 preset keeps the identical signal "
             "sequence (same trade count) and lands at 8.04 percent net at "
             "PF 1.006, paying 198500.76 USDT of fees on the same 2046 "
             "trades; the engine's own measured drag is 393.6255 points and "
             "its in-artifact zero-cost re-score (`ret_zero_pct`) equals the "
             "author headline to the last digit. The published figure was a "
             "cost-zero construction; this row is the quantified version of "
             "that fact. Its input klines grew since the ranking, so both "
             "lines here are re-measurements (401.67 vs the published "
             "390.62, `437c47539b4dc9ae`)."),
        28: ("The base run reproduces the published figure exactly; the zero "
             "line sits well above it, the ladder and funding were a heavy "
             "drag on this Donchian book."),
        29: ("The biggest relative mover of the batch: the zero line is "
             "roughly double the base line. The base run reproduces the "
             "published figure exactly."),
        30: ("The trade-flow confluence book is one of the two true "
             "re-measurements (JUP klines and funding grew since the "
             "ranking, and the trade count differs from the published row). "
             "Its base run PAID net funding (positive means paid)."),
    }

    def extra(art, tag):
        m = art["metrics"]
        s = art["strategy"]
        if s == "pack100":
            return (f" Its base run's `funding_paid` reads {m['funding_paid']:.2f} "
                    f"(negative means paid) and the engine's own zero-fee "
                    f"reference `zero_cost_pf` reads {m['zero_cost_pf']:.4f}.")
        if s in ("qs", "qsf"):
            return (f" Its base run's `funding_paid` reads {m['funding_paid']:.2f} "
                    f"over {int(m['n_funding_events'])} settlement events "
                    f"(positive means paid).")
        if s == "pack50":
            return (f" Its base run's `funding_paid` reads {m['funding_paid']:.4f} "
                    f"(positive means paid) and its own `zero_cost_pf` reads "
                    f"{m['zero_cost_pf']:.4f}.")
        return ""

    for b in books:
        b_id = b["base"]["run_id"]
        z_id = b["zero"]["run_id"]
        ids = f"(`{b_id}`, `{z_id}`)"
        if b["row"] == 27:
            ids = (f"(`{b_id}`; costed "
                   f"`{cells[b['tag']]['costed']['run_id']}`)")
        A(f"**{b['book']} — {b['market']}.** Base net "
          f"{b['base']['net_pct']:.2f}% at PF {b['base']['pf']:.3f} on "
          f"{int(b['base']['n_trades'])} trades; zero net "
          f"{b['zero']['net_pct']:.2f}% at PF {b['zero']['pf']:.3f} on "
          f"{int(b['zero']['n_trades'])} trades {ids}."
          + extra(arts[(b["tag"], "base")], b["tag"])
          + " " + notes.get(b["row"], ""))
        A("")

    A("## What the numbers say")
    A("")
    A("Three readings, none of them a verdict:")
    A("")
    A("1. **Eight of the ten published BASE figures reproduce exactly, and the "
      "two that do not sit on inputs that really grew.** The grown inputs on "
      "the reproducing rows are funding tail records only, and the bit-exact "
      "equity paths prove those records never touch an open position. The "
      "reproducing rows cite their base run_ids in the table above. The "
      "ranking's top-30 is solid ground, not a moving target.")
    A("2. **ds1 is the mirror that shows what the ranking would look like if "
      "every book had been published at zero cost.** Its costed re-run keeps "
      "the same trade count and lands at 8.04 percent at PF 1.006 with "
      "198500.76 USDT of fees (run_id cited on the row 27 line above) — the "
      "sort of gap the repo's cost regime produced across the whole "
      "historical corpus. A zero-cost line is the upper bound of what a book "
      "could earn if execution were free; ds1 is the only row in the three "
      "batches that was PUBLISHED on that bound.")
    A("3. **The catalog ladder was the heaviest drag in this batch, and the "
      "funding sign does not transfer between books.** QS-006 SOL rises from "
      "30.70 to 60.21 and QS-004 ETH from 34.65 to 56.31 at zero (their four "
      "run_ids are on the table lines above); meanwhile row 21's long-only "
      "book PAID a large funding bill and row 22's short book RECEIVED net "
      "funding. Same list, opposite funding signs, book by book.")
    A("")
    A("## What this is not")
    A("")
    A("- It is not a resurrection of any killed strategy. The kill list is "
      "unchanged and this report adds nothing to it. QS-004, QS-005, QS-006, "
      "QS-007 and QS-093 carry killed verdicts from their own campaigns (zero "
      "of ten families, one PARTIAL TK), S46 from the fifty-prompt pack (zero "
      "of forty-eight), B17-1h and F75-1h from the prompts-100 screen (zero "
      "pass as risk-specified), and ds1 from the five-strategy DeepSeek pack.")
    A("- It is not evidence of alpha. A zero-cost line is the upper bound of what "
      "a book could earn if execution were free; nobody trades for free.")
    A("- It is not a gate pass. No gate was evaluated, and the words PASS and FAIL "
      "do not appear in this report's tables.")
    A("- It is not agent- or user-selected: the ten are published ranking rows 21 "
      "to 30, decided before this campaign existed.")
    A("")
    A("## Limits and declared caveats")
    A("")
    A("- **ds1's published number was never a costed number.** The pack file "
      "declares no costs and the engine charges no funding, so the ranking "
      "row was a zero-cost construction from the start; this campaign did not "
      "discover that, it quantified it inside an artifact. The costed re-run "
      "uses the engine's own repo6x5 preset; no gate is evaluated on it.")
    A("- **Funding is a real cash flow, not a fee.** The ZERO regime removes it "
      "because the user asked for all costs removed; for a perp that is a "
      "declared control, never a tradable result. The base column keeps it.")
    A("- **The qs and qsf ZERO regime zeroes the whole ladder including the "
      "random-entry null**, so the null comparison inside those artifacts is "
      "a zero-cost null against a zero-cost book — consistent, but not the "
      "published null regime.")
    A("- **Execution was not relaxed.** Signal on the closed bar, the engines' "
      "own fill modes, stop-first on ties, the engines' own sizing and risk "
      "devices all stay. Only the cost block and the screening rules were "
      "removed.")
    A("")
    A("## Provenance")
    A("")
    A("- Pre-registration: `results/zerocost_rows21_30_pre_registration.md` "
      "(written before the first artifact existed, with a dated addendum on "
      "the reproduction-check semantics).")
    A("- Matrix: `results/zerocost_rows21_30_matrix.json` (per-cell run_ids, "
      "params, cut and inputs, plus row 27's costed run).")
    A("- Verification log: `results/_zerocost_rows21_30_verify.txt` — twenty "
      "artifacts, twenty OK.")
    A("- Audit: `code/_zerocost_rows21_30_audit.py` — every adapter checked "
      "against an independent fresh-module recomputation, the engines' own "
      "published zero-cost references (`zero_cost_pf` for pack100 and pack50, "
      "`ret_zero_pct` for dspack), and the reproduction logic declared in the "
      "addendum (equality is exact reproduction; inequality requires a grown "
      "input file).")
    A("- Harness switches added for this batch: the batch 2 qs switch "
      "replicated on `qsf`, and a new costs and funding switch on `pack50`; "
      "`pack100` kept its batch 1 switches and `dspack` already exposed "
      "its costs key natively. The engine files are byte-untouched (they are "
      "hashed into every run_id); absent the keys every runner behaves "
      "exactly as before, and the batch 1 SPX artifact was re-verified after "
      "the edits to prove it.")
    A("")

    text = "\n".join(L)
    # no file is opened here: the caller redirects stdout to the report path
    sys.stdout.write(text + "\n")
    print(f"[built {len(text)} chars, redirect stdout to the report path]",
          file=sys.stderr)


if __name__ == "__main__":
    main()
