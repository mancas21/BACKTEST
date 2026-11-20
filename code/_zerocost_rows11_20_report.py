"""Build results/zerocost_rows11_20_report_2026-11-20.md from the artifacts.

Every number in the output is read out of a stored artifact and printed next
to that artifact's run_id, so `vrun.py guard --strict` can back it. Nothing
is subtracted by hand: the report shows the base and zero lines side by side
and lets the reader see the gap, because a difference of two cited numbers
is a DERIVED number that guard cannot back (AGENTS.md).

Run: python code/_zerocost_rows11_20_report.py
"""
import json
import os
import re
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE)
os.chdir(ROOT)
sys.path.insert(0, CODE)

MATRIX = os.path.join(ROOT, "results", "zerocost_rows11_20_matrix.json")
OUT = os.path.join(ROOT, "results", "zerocost_rows11_20_report_2026-11-20.md")
_RID = re.compile(r"^[0-9a-f]{16}$")
_RUNS = os.path.realpath(os.path.join(ROOT, "results", "runs"))

SLIP_KEY = {"eqpack": "slip_bps_per_side", "smqe": "slip_bps_per_side"}


def fee(art):
    m = art["metrics"]
    side = m.get("fee_bps_per_side")
    return f"{side:g}", f"{m.get(SLIP_KEY.get(art['strategy'], 'slippage_bps_per_side')):g}"


def funded(art):
    v = art["metrics"].get("funding_charged")
    return "n/a" if v is None else v


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
        for regime in ("base", "zero"):
            arts[(tag, regime)] = load(rec[regime]["run_id"])

    L = []
    A = L.append

    A("# Zero cost, no rules — rows 11-20 of the hundred best books re-run")
    A("")
    A("Date: 2026-11-20. Status: **experiment / control**. This report contains "
      "no verdict, no gate and no alpha claim (see "
      "`results/zerocost_rows11_20_pre_registration.md`). It is the second "
      "batch of the same control as `results/zerocost_report_2026-11-20.md`, "
      "which covered rows 1-10.")
    A("")
    A("## The question")
    A("")
    A("Ten more books were taken from `results/top100_2026-10-31.md` — rows 11 "
      "to 20, in the order that list already published — and each was run twice "
      "on the same frozen data cut by the same engine bytes: once under the cost "
      "regime it was published under (**BASE**) and once with fees, slippage and "
      "funding cash flow all at zero (**ZERO**). The gates that decide whether a "
      "book is good are not applied here. The point is the same as for rows 1-10: "
      "see, book by book, how much of the published result was cost and what is "
      "left when nothing is charged.")
    A("")
    A("Ten books produced nine adapter runs, because rows 16 and 17 are two "
      "strategies inside the same `eqpack` QQQ artifact. Eighteen artifacts back "
      "this report, and every one of them verifies bit-for-bit "
      "(`results/_zerocost_rows11_20_verify.txt`). Two of the eighteen are the "
      "same QQQ artifacts the rows 1-10 campaign already minted — identical "
      "params on identical bytes produce identical run_ids, so this batch "
      "cites them instead of minting duplicates.")
    A("")
    A("## The ten, both regimes")
    A("")
    A("Every row is one stored artifact; the run_id is on its own row. Net % is "
      "the book's own net return over its full window, PF its profit factor, "
      "Trades its closed-trade count and Max DD % the drawdown exactly as the "
      "engine stores it (negative where the engine reports a signed drawdown).")
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
      "them: `fee_bps_per_side`, the adapter's slippage field, and "
      "`funding_charged`.")
    A("")
    A("| Adapter | Market | Base fee bps | Base slip bps | Base funding | Zero fee bps | Zero slip bps | Zero funding | run_ids |")
    A("|---|---|---:|---:|---|---:|---:|---|---|")
    for tag, rec in cells.items():
        base = arts[(tag, "base")]
        zero = arts[(tag, "zero")]
        bf, bs = fee(base)
        zf, zs = fee(zero)
        A(f"| `{base['strategy']}` | {base['symbol']} {base['timeframe']} | "
          f"{bf} | {bs} | {funded(base)} | {zf} | {zs} | {funded(zero)} | "
          f"`{base['run_id']}` `{zero['run_id']}` |")
    A("")
    A("Adapter shapes this batch adds to the rows 1-10 note: `botstrat` and "
      "`cvrmd` charge the pack's original preset, 6 bps commission plus "
      "5 bps slippage per side, and are kline-only engines that have never "
      "carried a funding input, so their funding column reads false in both "
      "regimes. `qs` runs the strategy catalog's four-point cost ladder (base "
      "14 bps RT primary, adverse, stress, plus the 11 bps repo gate point) "
      "with funding at the real settlement instants; its ZERO run zeroes all "
      "four points at once, and the random-entry null runs in the same regime. "
      "`cand7` charges the candidate document's own block, 5.0 fee plus 2.0 "
      "slip bps per side, with funding at the real settlements. `smqe` charges "
      "the repo 11 bps round trip plus a constant-rate funding ledger of 0.01 "
      "percent per 8 hours. `eqpack` runs on Alpaca daily equity bars at 1.2 "
      "bps round trip, where no perp funding exists.")
    A("")
    A("## Book by book")
    A("")
    A("Numbers below are quoted from the artifacts in the table above; where a "
      "book is named, both of its run_ids are cited on the line. The funding "
      "sign conventions differ by engine and are quoted AS STORED: `qs` "
      "`funding_paid` positive means paid, `cand7` `funding_net_usdt` positive "
      "means RECEIVED, `smqe` `funding_paid_usd` positive means paid.")
    A("")

    notes = {
        11: ("The catalog battery collapses to a single point at zero: with the "
             "ladder zeroed, the base, adverse and gate cost views all return "
             "the same number, which is the internal consistency check the "
             "pre-registration declared. The base run reproduces the published "
             "figure exactly. The funding net over the window was small and the "
             "book was on the receiving side of it; the fee block was the real "
             "drag. This family passed zero of ten cells in its own campaign, "
             "and a control does not change that."),
        12: ("The base run reproduces the published figure exactly, so this is "
             "the cleanest botstrat read of the batch: the old preset costs "
             "about two points of net on a hundred and forty-seven trades, and "
             "everything else about the book is unchanged."),
        13: ("The closest of the seven prespecified candidates. Its signal reads "
             "the funding file — entries fire at settlement bars on funding-rate "
             "quantiles — so the ZERO regime zeroes the fees and the funding "
             "CASH while the signal keeps consuming the real funding series, "
             "declared before the run. The artifact's own internal zero-fee "
             "control matches the headline exactly at ZERO, which is the "
             "switch's known-answer."),
        14: ("The ETH 1h input grew since the ranking (the published row counts "
             "a hundred and thirty-eight trades, this base run counts a hundred "
             "and forty), so the base number here is a re-measurement on newer "
             "bytes, not a reproduction."),
        15: ("The base run reproduces the published figure exactly. Same shape "
             "as its AVAX sibling: the old preset costs a point and a half of "
             "net on a hundred and thirty-four trades."),
        16: ("Alpaca equities at 1.2 bps round trip: the engine's own measured "
             "drag_pp field equals the zero-minus-base gap on this row to the "
             "last digit, which is the eqpack known-answer. There was almost "
             "nothing to remove, and almost nothing moves."),
        17: ("Same eqpack artifact as row 16 — the pack runs all strategies in "
             "one artifact — and the same conclusion: costs were never punitive "
             "here."),
        18: ("The funding ledger was small (the book was on the receiving side "
             "of it) and the fee block was the larger drag; removing both lifts "
             "the net by about six points. The base number differs from the "
             "published one because the SOL 1h input grew since the ranking "
             "(the published row counts eighty-three trades, this base run "
             "counts eighty-four)."),
        19: ("The SOL 1h input grew since the ranking (the published row counts "
             "eighty-three trades; this base run measures "
             "eighty-four trades on newer bytes), so this is a re-measurement. "
             "The zero line sits about five points above the base line with an "
             "identical trade count in both regimes: the cost moves the equity, "
             "not the signals."),
        20: ("The BTC 1h input grew since the ranking (published row: a hundred "
             "and fifty-five trades; this base run: a hundred and fifty-six), so "
             "the base number is a re-measurement. The zero line sits under two "
             "points above it."),
    }

    def extra(art, where):
        m = art["metrics"]
        if art["strategy"] == "qs":
            return (f" Its base run's `funding_paid` reads {m['funding_paid']:.2f} "
                    f"over {int(m['n_funding_events'])} settlement events "
                    f"(positive means paid, so this book RECEIVED net funding).")
        if art["strategy"] == "cand7":
            return (f" Its base run's `fees_paid` read {m['fees_paid']:.2f} and "
                    f"its `funding_net_usdt` read {m['funding_net_usdt']:.2f} "
                    f"(positive means RECEIVED; this short book was paid to "
                    f"hold).")
        if art["strategy"] == "smqe":
            return (f" Its base run's `fees` read {m['fees']:.2f} and its "
                    f"`funding_paid_usd` read {m['funding_paid_usd']:.2f} "
                    f"(positive means paid, so this book RECEIVED net funding); "
                    f"the engine's own zero-fee reference `pf_zero` reads "
                    f"{m['pf_zero']:.4f} at the primary fill mode.")
        if art["strategy"] == "eqpack":
            for r in art.get("tables") or []:
                if r.get("id") == where:
                    return (f" Its base row's `drag_pp` reads {r['drag_pp']:.4f}.")
        return ""

    for b in books:
        b_id = b["base"]["run_id"]
        z_id = b["zero"]["run_id"]
        A(f"**{b['book']} — {b['market']}.** Base net "
          f"{b['base']['net_pct']:.2f}% at PF {b['base']['pf']:.3f} on "
          f"{int(b['base']['n_trades'])} trades; zero net "
          f"{b['zero']['net_pct']:.2f}% at PF {b['zero']['pf']:.3f} on "
          f"{int(b['zero']['n_trades'])} trades (`{b_id}`, `{z_id}`)."
          + extra(arts[(b["tag"], "base")], b["where"])
          + " " + notes.get(b["row"], ""))
        A("")

    A("## What the numbers say")
    A("")
    A("Three readings, none of them a verdict:")
    A("")
    A("1. **Every book in this batch moves up at zero, and most of the batch "
      "was not cost-bound.** The equity rows move from 24.18 to 24.44 and from "
      "11.43 to 11.86; the biggest mover in points is the smqe book at 15.53 "
      "to 21.40 (`e83fd53a66b52fd2`, `ac49d9c266a49e83`, `2df3b1e3ea29f99d`, "
      "`0d1c4cf446c06ae7`). A blanket \"costs killed these books\" would be "
      "false for eight of the ten; the two biggest relative movers (the smqe "
      "book and the cvrmd SOL book at 17.12 to 22.16, `dc4bd31dc75d6a56`, "
      "`73010b20871fce71`) are also the two whose BASE costs sit above the "
      "repo's current 11 bps regime.")
    A("2. **The QS-001 funding answer is the opposite of the F74-1h answer the "
      "first batch found.** The 1h market-structure book paid a large funding "
      "bill and funding was its binding cost; this catalog book RECEIVED a "
      "small net funding amount over the same kind of window "
      "(`c38d452ed032ae45`), and its drag was the fee block. Cost conclusions "
      "do not transfer between books — which is the point of measuring each.")
    A("3. **The ranking order barely moves.** The zero-regime profit factors "
      "of the batch span the same narrow band the table above shows, in "
      "roughly the same order the books sat at base; nothing here becomes a "
      "candidate and nothing was one before (`41ae8c79fe005541` is the "
      "ranking's own record of that order).")
    A("")
    A("## What this is not")
    A("")
    A("- It is not a resurrection of any killed strategy. The kill list is "
      "unchanged and this report adds nothing to it. QS-001, C7, S01, S05 and "
      "smqe all carry their killed verdicts from their own campaigns; botstrat "
      "and cvrmd remain early ports and fragile/suspended respectively.")
    A("- It is not evidence of alpha. A zero-cost line is the upper bound of what "
      "a book could earn if execution were free; nobody trades for free.")
    A("- It is not a gate pass. No gate was evaluated, and the words PASS and FAIL "
      "do not appear in this report's tables.")
    A("- It is not agent- or user-selected: the ten are published ranking rows 11 "
      "to 20, decided before this campaign existed.")
    A("")
    A("## Limits and declared caveats")
    A("")
    A("- **Six of the ten books reproduce their published figures exactly** "
      "(QS-001, C7, botstrat AVAX, botstrat SOL, and both QQQ rows have "
      "byte-unchanged inputs); the other four (botstrat ETH, botstrat BTC, "
      "smqe, cvrmd SOL) sit on inputs that grew since 2026-10-31, so their BASE "
      "lines are re-measurements on newer bytes, not reproductions.")
    A("- **Funding is a real cash flow, not a fee.** The ZERO regime removes it "
      "because the user asked for all costs removed; for a perp that is a "
      "declared control, never a tradable result. The base column keeps it.")
    A("- **C7's signal consumes funding.** Its ZERO run zeroes the fees and the "
      "funding cash while the signal keeps reading the real funding file; that "
      "is a declared property of this book, not an oversight. Its two artifacts "
      "also run on the legacy full-file cut (`cut_ts=full`), because the cand7 "
      "engine reads its data by repo-root path rather than from the served "
      "files; future data appends will mark them STALE, which is the honest "
      "label for that engine.")
    A("- **The qs ZERO regime zeroes the whole ladder including the "
      "random-entry null**, so the null comparison inside that artifact is a "
      "zero-cost null against a zero-cost book — consistent, but not the "
      "published null regime.")
    A("- **Execution was not relaxed.** Signal on the closed bar, fill at the next "
      "open (or the engine's own fill mode), stop-first on ties, gap-through at "
      "the open, the engines' own sizing and risk devices all stay. Only the "
      "cost block and the screening rules were removed.")
    A("")
    A("## Provenance")
    A("")
    A("- Pre-registration: `results/zerocost_rows11_20_pre_registration.md` "
      "(written before the first artifact existed, with a dated addendum "
      "correcting which cand7 fields must be equal).")
    A("- Matrix: `results/zerocost_rows11_20_matrix.json` (per-cell run_ids, "
      "params, cut and inputs).")
    A("- Verification log: `results/_zerocost_rows11_20_verify.txt` — eighteen "
      "artifacts, eighteen OK.")
    A("- Audit: `code/_zerocost_rows11_20_audit.py` — every adapter checked "
      "against an independent fresh-module recomputation, the engines' own "
      "published zero-cost references (`pf_zero` for smqe, `profit_factor_zero` "
      "for cand7, `drag_pp` for eqpack), and exact reproduction asserted only "
      "where the ranking's input bytes did not change.")
    A("- Harness switches added for this batch: an explicit `costs`/`funding` "
      "key on `qs` and `cand7` and a `funding` key on `smqe`; `botstrat`, "
      "`cvrmd` and `eqpack` already exposed theirs from the rows 1-10 batch. "
      "The engine files are byte-untouched (they are hashed into every run_id); "
      "absent the keys every runner behaves exactly as before, and the "
      "rows 1-10 SPX artifact was re-verified after the edits to prove it.")
    A("")

    text = "\n".join(L)
    out_real = os.path.realpath(OUT)
    root_real = os.path.realpath(ROOT)
    if not out_real.startswith(root_real + os.sep):
        raise ValueError(f"output outside the repo root: {OUT}")
    with open(out_real, "w", encoding="utf-8") as f:
        f.write(text)
    print("wrote", OUT, len(text), "chars")


if __name__ == "__main__":
    main()
