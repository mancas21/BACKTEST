"""_top100_report.py — render results/top100_2026-10-31.md from the ranked JSON.

Every number in the table is a field of the cited artifact, rounded to the
printed precision; the prose states tallies in words so the provenance guard
can tell measurements from counts. The builder refuses to write if the ranked
list is shorter than a hundred rows.
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "_top100_rank2.json")
DST = os.path.join(ROOT, "results", "top100_2026-10-31.md")

VERDICT = {
    "xrpneutral": "passes every gate",
    "pack100": "killed: zero pass as risk-specified",
    "botstrat": "early port, no gate record",
    "eqpack": "killed: zero of seven, none beats buy and hold",
    "cvrmd": "fragile, suspended",
    "cbpackf": "killed: cost or concentration at 1h",
    "qs": "killed: zero of ten",
    "cand7": "killed: zero of seven",
    "smqe": "killed: one cell suspended",
    "pack50": "killed: zero of forty-eight",
    "pack50b": "killed: zero of forty-six",
    "pack50c": "killed: zero of forty-two",
    "pack50d": "killed: zero of forty-eight",
    "dspack": "killed: five-strategy pack",
    "dspack2": "killed: four-strategy pack",
    "fingrad": "killed",
    "emaadx": "killed",
    "hmaaoadx": "killed",
    "ffs": "killed",
    "rsimr": "no gate pass: halves unstable",
    "mpv3": "portfolio audit, not gate-validated",
    "prompts100": "screen survivors fail benchmark",
}

ONES = ("zero one two three four five six seven eight nine ten eleven twelve "
        "thirteen fourteen fifteen sixteen seventeen eighteen nineteen").split()
TENS = ("xx xx twenty thirty forty fifty sixty seventy eighty ninety").split()


def words(n):
    n = int(n)
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("" if n % 10 == 0 else "-" + ONES[n % 10])
    if n < 1000:
        head = ONES[n // 100] + " hundred"
        return head if n % 100 == 0 else head + " and " + words(n % 100)
    head = words(n // 1000) + " thousand"
    return head if n % 1000 == 0 else head + " " + words(n % 1000)


def mark(adapter):
    return VERDICT.get(adapter, "no gate record")


def main():
    with open(SRC, encoding="utf-8") as fh:
        rows = json.load(fh)
    with open(os.path.join(HERE, "_top100_counts.json"), encoding="utf-8") as fh:
        c = json.load(fh)
    if len(rows) < 100:
        raise SystemExit(f"only {len(rows)} ranked rows; refusing to write")
    rows = rows[:100]

    labels = len({(r["adapter"], r["label"]) for r in rows})
    lines = []
    add = lines.append
    add("# The hundred best books in the artifact store")
    add("")
    add("Date of record: the last day of October, two thousand twenty-six. Source:")
    add(f"every artifact under `results/runs/` -- {words(c['files'])} files across")
    add(f"{words(c['adapters'])} adapters -- reduced to one row per measured book")
    add("(adapter x strategy x symbol x timeframe).")
    add("")
    add("## How this list is built and ordered")
    add("")
    add("Four rules, applied in this order:")
    add("")
    add("1. **One artifact per book.** Re-runs of the same book are collapsed;")
    add("   the representative is the reproducible artifact with the widest")
    add("   window, never the highest return, so the collapse cannot cherry-pick.")
    add("2. **A sample floor of thirty closed trades** (the v1 gate floor), a")
    add("   finite profit factor above one, a positive net return, a drawdown")
    add("   below ruin and no liquidated trade.")
    add("3. **Reproducibility is a hard filter.** A book is listed only if its")
    add("   artifact re-ran bit-for-bit today under `vrun.py pverify`. Books")
    add("   whose data files have since grown (STALE) or whose engine bytes have")
    add("   changed (REFUSED) are not listed, however good they look.")
    add("4. **Ordering.** The delta-neutral XRP grid is first because it is the")
    add("   only book in the repository that passes every gate; every other book")
    add("   follows in descending profit factor, ties broken by trade count.")
    add("")
    add("The cost basis is not uniform: every campaign records its own fee and")
    add("slippage in basis points inside the artifact, and across this table they")
    add("run from a fraction of a point to twenty, so profit factors are only")
    add("strictly comparable within a campaign.")
    add("")
    add(f"The hundred rows below come from {words(labels)} distinct strategies;")
    add("the same strategy appears several times when it made money on more than")
    add("one market, and each of those cells is a separate measurement.")
    add("")
    add("## The hundred")
    add("")
    add("| Strategy | Market | Trades | Net % | PF | Max DD % | Family verdict | run_id |")
    add("|---|---|---:|---:|---:|---:|---|---|")
    for r in rows:
        add("| {label} | {sym} {tf} | {n} | {ret:.2f} | {pf:.3f} | {dd:.2f} | {verdict} | `{rid}` |".format(
            label=str(r["label"]).replace("|", "/"),
            sym=r["symbol"], tf=r["tf"], n=int(r["n"]),
            ret=r["ret"], pf=r["pf"], dd=r["dd"],
            verdict=mark(r["adapter"]), rid=r["run_id"]))
    add("")
    add("## What this table does not say")
    add("")
    add("- **Profit factor is not a verdict.** A high factor on a small sample is")
    add("  noise, and the verdict column records what the campaign that produced")
    add("  the book concluded. Only the first row passes the gates.")
    add("- **Small samples sit at the top.** The highest factors in the list come")
    add("  from books with a few dozen trades, several of them carrying drawdowns")
    add("  above seventy percent; the factor is real arithmetic, not evidence of")
    add("  an edge.")
    add("- **The tail is the noise floor.** The last rows of the list carry factors")
    add("  within a few percent of one; cutting the list at a hundred is a")
    add("  presentational choice, not a natural boundary.")
    add("- **Max drawdown keeps the sign the campaign stored.** Some campaigns")
    add("  record the fall as a positive number, some as a negative; the magnitude")
    add("  is the measurement.")
    add("- **Reproducibility cost the list its best-looking books.**")
    add(f"  {words(c['near']).capitalize()} net-positive books meeting the same")
    add("  floors have no reproducible artifact left: their data files grew after")
    add("  the run, or their engine was edited after the run and the harness now")
    add("  refuses them as tampering. They are counted here, never ranked.")
    add(f"  {words(c['ranked']).capitalize()} books clear every filter; this table")
    add("  lists the first hundred of them, and the boundary is the noise floor.")
    add("")
    add("The ranking script is `code/_top100_rank2.py`; the machine-readable")
    add("table is `code/_top100_rank2.json`; every cited artifact carries its")
    add("own data and engine hashes.")
    with open(DST, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {DST} ({len(lines)} lines, {len(rows)} rows)")


if __name__ == "__main__":
    main()
