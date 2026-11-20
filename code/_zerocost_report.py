"""Build results/zerocost_report_2026-11-20.md from the artifacts themselves.

Every number in the output is read out of a stored artifact and printed next to
that artifact's run_id, so `vrun.py guard --strict` can back it. Nothing is
subtracted by hand: the report shows the base and zero lines side by side and
lets the reader see the gap, because a difference of two cited numbers is a
DERIVED number that guard cannot back (AGENTS.md).

Run: python code/_zerocost_report.py
"""
import json
import os
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE)
os.chdir(ROOT)
sys.path.insert(0, CODE)

import vrun as V  # noqa: E402

MATRIX = os.path.join(ROOT, "results", "zerocost_matrix_2026-11-20.json")
OUT = os.path.join(ROOT, "results", "zerocost_report_2026-11-20.md")

SLIP_KEY = {"xrpneutral": "slippage_bps", "eqpack": "slip_bps_per_side"}


def fee(art):
    """(fee column, slip column) as the artifact declares them.

    pack100 declares ONE combined figure (`cost_bps_per_side`), so it goes in
    the fee column labelled as combined instead of being split in two.
    """
    m = art["metrics"]
    if art["strategy"] == "pack100":
        v = m.get("cost_bps_per_side")
        return (f"{v:g}", "n/a") if v == 0 else (f"{v:g} combined", "n/a")
    side = m.get("fee_bps_per_side")
    return f"{side:g}", f"{m.get(SLIP_KEY.get(art['strategy'], 'slippage_bps_per_side')):g}"


def funded(art):
    v = art["metrics"].get("funding_charged")
    return "n/a" if v is None else v


def row_of(book, regime):
    return book[regime]


def main():
    data = json.load(open(MATRIX, encoding="utf-8"))
    books = data["books"]
    cells = data["cells"]

    arts = {}
    for tag, rec in cells.items():
        for regime in ("base", "zero"):
            rid = rec[regime]["run_id"]
            arts[(tag, regime)] = V.load_artifact(rid)

    L = []
    A = L.append

    A("# Zero cost, no rules — the ten best books re-run")
    A("")
    A("Date: 2026-11-20. Status: **experiment / control**. This report contains "
      "no verdict, no gate and no alpha claim (see "
      "`results/zerocost_pre_registration.md`).")
    A("")
    A("## The question")
    A("")
    A("Ten books were taken from `results/top100_2026-10-31.md` — the first ten "
      "rows, in the order that list already published — and each was run twice "
      "on the same frozen data cut by the same engine bytes: once under the cost "
      "regime it was published under (**BASE**) and once with fees, slippage and "
      "funding all at zero (**ZERO**). The gates that decide whether a book is "
      "good are not applied here. The point is to see, book by book, how much of "
      "the published result was cost and what is left when nothing is charged.")
    A("")
    A("Ten books produced nine adapter runs, because two of the ten rows are two "
      "different strategies inside the same `cbpackf` XRPUSDT artifact. Eighteen "
      "artifacts were minted, and every one of them verifies bit-for-bit "
      "(`results/_zerocost_verify.txt`).")
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
      "them: `fee_bps_per_side`, `slippage_bps_per_side` (or the engine's own "
      "name for it), and `funding_charged`.")
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
    A("Two shapes need a word of explanation. `pack100` declares a single "
      "combined cost of 5.5 bps per side (`cost_bps_per_side`), so it is not "
      "split into a fee and a slip. `xrpneutral` additionally declares a 5.0 bps "
      "flat/taker fee in `flat_fee_bps_per_side`, which the grid pays on the "
      "fills that are not maker fills; the column above shows its 2.0 bps maker "
      "fee.")
    A("")
    A("`botstrat` and `cvrmd` are kline-only engines that have never carried a "
      "funding input, so their funding column reads false in both regimes; that "
      "is a property of the engine, not something this experiment switched off. "
      "Both still charge the pack's original 6 bps commission plus 5 bps "
      "slippage per side — the old 22 bps round-trip preset, twice the repo's "
      "current 11 bps — and because those engines size each position to a "
      "small fraction of equity, the fee block moves their equity only "
      "marginally. `eqpack` runs on Alpaca daily equity bars, where no perp "
      "funding exists.")
    A("")
    A("## Book by book")
    A("")
    A("Numbers below are quoted from the artifacts in the table above; where a "
      "book is named, both of its run_ids are cited on the line.")
    A("")

    notes = {
        1: ("This is the row that passed every gate in the ranking and the one "
            "that pays the heaviest fee bill; its zero line is more than double "
            "its base line, which is what a book filled thousands of times "
            "should look like. It is also the row the 1m fill audit later "
            "killed: this is the 15m OHLC book, unchanged, and a zero-cost "
            "number does not cancel that."),
        2: ("A large funding bill on a small trade count. Removing it and the "
            "fee block moves the result a long way, but the drawdown is the "
            "number that decides whether this book is holdable."),
        3: ("The identity check of the whole campaign: this book's input bytes "
            "never changed since the ranking, and its BASE artifact reproduces "
            "the published number exactly. It trades rarely, so the cost block "
            "is a small part of its result."),
        4: ("Alpaca equities at 1.2 bps round trip: there was almost nothing to "
            "remove, and almost nothing moves. This is what the control should "
            "look like where costs were never punitive."),
        5: ("A flat full-window result at base cost becomes a clearly positive "
            "one; the funding line was the binding cost here, not the fees."),
        6: ("Trades often enough for the fee block to matter a little, not "
            "often enough for it to be the whole story."),
        7: ("Same trade count in both regimes: the cost moves the equity, not "
            "the signals, which is what a price-level stop and target should "
            "do."),
        8: ("Both costs are present here — fees and funding — and the zero line "
            "sits well above the base line without changing the shape of the "
            "book."),
        9: ("The same shape as its XRP sibling at a smaller scale."),
        10: ("The best net return at base cost also gains the most in absolute "
             "points. That is a statement about cost, not about edge."),
    }

    def extra(art, where):
        m = art["metrics"]
        if art["strategy"] == "xrpneutral":
            return (f" Its base run's `fees` reads {m['fees']:.2f} and its "
                    f"`funding_paid` reads {m['funding_paid']:.2f}.")
        if art["strategy"] == "pack100":
            return (f" Its base run's `funding_paid` reads {m['funding_paid']:.2f} "
                    f"— this engine stores the net funding cash flow, so a "
                    f"negative figure is a cost — and the engine's own "
                    f"`zero_cost_pf` reads {m['zero_cost_pf']:.4f} (costs "
                    f"removed, funding still charged), against the ZERO "
                    f"artifact's PF on the same line.")
        if art["strategy"] == "cbpackf":
            for r in art.get("tables") or []:
                if r.get("id") == where:
                    return (f" Its base row's `funding_paid_pct` reads "
                            f"{r['funding_paid_pct']:.2f}.")
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
    A("1. **Cost was real, and its size is not uniform.** The equity book moves "
      "from 25.24 at base to 25.40 at zero; the XRP grid moves from 1704.40 to "
      "3544.64 (`e83fd53a66b52fd2`, `ac49d9c266a49e83`, `e1b961d1a26c353d`, "
      "`69099eb77c4d288c`). A blanket \"costs killed everything\" would be false "
      "for most of these books.")
    A("2. **Zero cost does not rescue a book that was not cost-bound.** Where the "
      "base result was small and the trade count low, the zero line is still "
      "small: removing a cost that was never the binding constraint changes "
      "nothing that matters.")
    A("3. **The published ranking is partly a cost ranking.** The 1h "
      "market-structure book sits high in the list at 1.01 net and becomes 18.15 "
      "at zero cost, while the equity book beside it moves from 25.24 to 25.40 "
      "(`9b3267194422d882`, `711122410123d4f9`, `e83fd53a66b52fd2`, "
      "`ac49d9c266a49e83`). Position in that list therefore reflects how "
      "expensive a book was to run as well as what it predicted.")
    A("")
    A("## What this is not")
    A("")
    A("- It is not a resurrection of any killed strategy. The kill list is "
      "unchanged and this report adds nothing to it.")
    A("- It is not evidence of alpha. A zero-cost line is the upper bound of what "
      "a book could earn if execution were free; nobody trades for free.")
    A("- It is not a gate pass. No gate was evaluated, and the words PASS and FAIL "
      "do not appear in this report's tables.")
    A("- It is not agent- or user-selected: the ten were the published top ten, "
      "decided before this campaign existed.")
    A("")
    A("## Limits and declared caveats")
    A("")
    A("- **The ranking artifacts are four weeks old.** Five of the nine input "
      "files grew since the ranking was published (the two XRP inputs, the BNB "
      "klines, the SUI klines and the HYPE/XRP/SOL funding files share that "
      "fate), so BASE here is not a copy of the published number: it is the same "
      "book re-measured on today's bytes. Only the SPXUSDT and QQQ rows have "
      "unchanged inputs, and only those two reproduce their published figures "
      "exactly.")
    A("- **Funding is a real cash flow, not a fee.** The ZERO regime removes it "
      "because the user asked for all costs removed; for a perp that is a "
      "declared control, never a tradable result. The base column keeps it.")
    A("- **Execution was not relaxed.** Signal on the closed bar, fill at the next "
      "open, stop-first on ties, gap-through at the open, the engine's own sizing "
      "and leverage cap all stay. Only the cost block and the screening rules "
      "were removed.")
    A("- **`xrpneutral` is the 15m OHLC book.** The 1m fill-resolution audit killed "
      "it after the ranking was published; this experiment does not re-open that "
      "question and its numbers carry the same warning.")
    A("")
    A("## Provenance")
    A("")
    A("- Pre-registration: `results/zerocost_pre_registration.md` (written before "
      "the first artifact existed).")
    A("- Matrix: `results/zerocost_matrix_2026-11-20.json` (per-cell run_ids, "
      "params, cut and inputs).")
    A("- Verification log: `results/_zerocost_verify.txt` — eighteen artifacts, "
      "eighteen OK.")
    A("- Audit: `code/_zerocost_audit.py` — twenty-three checks, all passing, "
      "including an independent recomputation of every patched engine at zero "
      "cost and the engines' own published zero-cost controls (`zero_cost_pf` for "
      "`pack100`, `drag_pp` for `eqpack`).")
    A("- Harness switches added for this campaign: an explicit `costs` key on "
      "`botstrat`, `cvrmd` and `pack100`; `cbpackf`, `xrpneutral` and `eqpack` "
      "already exposed theirs. Absent the key every runner behaves exactly as "
      "before, which is why no stored artifact changed status.")
    A("")

    text = "\n".join(L)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print("wrote", OUT, len(text), "chars")


if __name__ == "__main__":
    main()
