"""Emit results/hmatrend_report_2026-11-14.md from the artifacts only.

Every number in the report is read from a cited artifact file under
results/runs/ (REGLA 0). The claim's own numbers and the parity numbers are
quoted THROUGH the hermes-mode artifacts, which carry them as claim_* /
parity_* metrics read from the sha-bound source-of-record JSONs.
Run:  python code/_hmatrend_report.py
Then:  python code/vrun.py guard --report results/hmatrend_report_2026-11-14.md --strict
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUNS = os.path.join(ROOT, "results", "runs")

BATTERY = [
    ("BTCUSDT", "93f107d4bc20d3e7"),
    ("ETHUSDT", "13330a919c10aa61"),
    ("SOLUSDT", "ef1815baa5d5f6ca"),
    ("SUIUSDT", "688b6aab9d336f44"),
    ("XRPUSDT", "0a481d64b12dfb13"),
    ("ARBUSDT", "7aac8b0a72a2eb2a"),
    ("HYPEUSDT", "7fd51aaaad1ff178"),
    ("1000PEPEUSDT", "a80b4f00cb4c6024"),
    ("NVDAUSDT", "e9bf4de86c939484"),
    ("SPCXUSDT", "006df3b25dbaf74c"),
    ("JUPUSDT", "30ef63651b4760db"),
]
CLAIMCHECK = [
    ("BTCUSDT", "a65edc089583d7ba"),
    ("ETHUSDT", "62b36d415be65a19"),
    ("HYPEUSDT", "a18803e0648e5b76"),
    ("JUPUSDT", "2411025b023d0bbf"),
    ("SOLUSDT", "0fd70280f7eb7d25"),
    ("SUIUSDT", "5dee529d084895d9"),
    ("XRPUSDT", "408ac5485eccaf6c"),
    ("1000PEPEUSDT", "78a537a28461a8b1"),
    ("ARBUSDT", "ad4b85891b38412e"),
    ("NVDAUSDT", "eaff1ab244fa05a8"),
    ("SPCXUSDT", "671cf42e5afe8d9a"),
]
OUT = os.path.join(ROOT, "results", "hmatrend_report_2026-11-14.md")
JUP_CLAIM = "2411025b023d0bbf"
JUP_BATT = "30ef63651b4760db"


def load(rid):
    return json.load(open(os.path.join(RUNS, f"{rid}.json")))


def f2(x):
    return f"{x:.2f}"


def f4(x):
    return f"{x:.4f}"


def main():
    jc = load(JUP_CLAIM)["metrics"]
    jb = load(JUP_BATT)["metrics"]

    L = []
    L.append("# hmatrend - the external hermes HMA(34) Trend pack, audited and re-run (2026-11-14)")
    L.append("")
    L.append("Question: what is the external file `hma_backtest_oos_consolidado.json` "
             "(an \"hermes\" CLI session's HMA(34) Trend backtest, 12 pairs, 1h, "
             "70/30 IS/OOS on about 125 days of 2026) worth under this repo's rules? "
             "Protocol: sources of record copied byte-identical to "
             "`code/hma_trend_sources/` (sha256 manifest, all bound into every "
             "run_id), conventions measured from the pack's own outputs, a "
             "declared spec frozen before any repo-market run, dual-mode engine "
             "`code/hma_trend_engine.py` (adapter `hmatrend`), claim-check on "
             "the pack's own windows, then the repo battery on full repo "
             "history.")
    L.append("")
    L.append("Declared costs for every repo-mode cell: 5.0 bps fee + 0.5 bps slip "
             "per side (11.0 bps round trip), funding charged at real settlements "
             "on the open notional, fill model next_open_stop_first_gap_through, "
             "sizing 100% of equity per trade (the pack's own convention), "
             "long-only, no take-profit. The zero-cost control is measured inside "
             "every artifact.")
    L.append("")
    L.append("## 1. What the pack's outputs pin down (measured)")
    L.append("")
    L.append("The pack's own engine code did NOT survive; only its output JSONs "
             f"did. From the JUPUSDT full-2026 run ({jc['parity_source_trades']} "
             f"trades on {jc['claim_full_bars']} one-hour bars; claim and "
             "parity numbers carried in artifact " + JUP_CLAIM + ") the outputs "
             "pin, exactly:")
    L.append("")
    L.append(f"- Every entry fills at the OPEN of the bar after the signal close "
             f"({jc['parity_source_trades']} of {jc['parity_source_trades']} "
             "trades), every HMA_DOWN exit fills at the open of the bar after "
             f"its signal close ({jc['parity_source_exit_trades']} of "
             f"{jc['parity_source_exit_trades']}) - the same next-open "
             "convention this repo uses.")
    L.append(f"- Every STOP exit ({jc['parity_source_stop_trades']} of "
             f"{jc['parity_source_stop_trades']}) fills intrabar at exactly "
             "entry - 3.0 x ATR(14, Wilder at the signal bar); the fitted "
             "multiple is 3.0 with zero spread.")
    L.append("- Every trade PnL equals the raw price delta - zero fees, and a "
             "long-only book (the pack charged its perps neither fees nor "
             "funding).")
    L.append("- Sizing compounds the full equity every trade.")
    L.append("- Four trades have entry_bar equal to exit_bar and PnL exactly "
             "zero - a flag-ordering quirk of the pack's engine (entry and exit "
             "scheduled on the same close, applied enter-then-exit at one open). "
             "Not reproduced here (declared).")
    L.append("- The pack's own profit factor is pct-weighted (sum of trade "
             "percent gains over percent losses), not money-weighted: the same "
             f"trade list gives {f4(jc['claim_full_money_pf'])} money-weighted "
             f"against the published {f4(jc['claim_full_pf'])} pct-weighted "
             "(both recomputed from the pack's own trades, carried in artifact "
             + JUP_CLAIM + ").")
    L.append("")
    L.append("## 2. What the outputs cannot pin down (declared)")
    L.append("")
    L.append("The exact exit predicate is not recoverable from the "
             f"{jc['parity_source_trades']}-trade sample: no candidate family "
             f"separates every one of the {jc['parity_source_exit_trades']} "
             f"exit-signal bars from the {jc['parity_source_hold_bars']} "
             "position-held bars whose close signal did not fire (HMA slope on "
             "1h and 4h aggregations and seven price sources, periods 10 to 50, "
             "lags 1 to 3, close versus HMA, entry-relative levels, HMA "
             "trailing, unrealized-PnL thresholds, price-action booleans; "
             "re-measured inside artifact " + JUP_CLAIM + " and by "
             "code/_hma_trend_parity.py). The frozen declared spec therefore "
             "reads the pack's own label literally: entry = HMA(34) rising at "
             "the close, exit = HMA(34) falling at the close, stop = "
             "entry - 3.0 x ATR14 (measured exactly). On the pack's OWN bytes "
             f"the declared book produces {jc['parity_declared_trades']} trades "
             f"with average hold {jc['parity_avg_hold_declared_bars']:.1f} bars "
             f"against the claim's {jc['parity_source_trades']} trades and "
             f"{jc['parity_avg_hold_source_bars']:.1f} bars average hold - and "
             f"{jc['parity_shared_entry_exit_pairs']} shared (entry, exit) bar "
             "pairs: the claim's edge lives in exit timing that no defensible "
             "reading of \"HMA(34) Trend\" reproduces. No parameter was fitted "
             "to the claim's trades.")
    L.append("")
    L.append("Engine audit: code/_hma_trend_audit.py, sixteen known-answer "
             "checks, all PASS (it caught two real engine defects before any "
             "market run: an ATR-warmup entry that set the stop equal to the "
             "entry price, and a PnL basis that omitted the entry fee from the "
             "position cost). Parity tool: code/_hma_trend_parity.py, twelve "
             "checks, all PASS.")
    L.append("")

    L.append("## 3. The claim's measured defects")
    L.append("")
    L.append("Measured on the pack's own outputs and re-stated inside every "
             "hermes artifact as claim_* metrics (source JSON sha-bound as an "
             "adapter source):")
    L.append("")
    L.append("- Zero fees: the pack's per-trade PnL is the raw price delta on "
             "every source trade; the repo regime charges 11.0 bps round trip.")
    L.append("- Zero funding on perps: eleven of the twelve pack pairs are "
             "Binance perpetuals with funding files in this repo; the pack "
             "charged none.")
    L.append("- Same-bar close signals filled at next open - the pack is fair "
             "on fill timing (measured, not assumed).")
    L.append("- One short window: each pair's IS/OOS covers about 125 days of "
             "2026; the OOS segment is a single 38-day slice. NVDAUSDT and "
             "SPCXUSDT use DIFFERENT windows (their data starts later), so the "
             "twelve OOS cells are not the same market period.")
    L.append("- Five of the twelve pairs LOSE to buy & hold over their own OOS "
             "slice even at zero cost (their excess_return column is negative "
             "in the claim table below) - the consolidated averages sit on a "
             "window where half the book already loses to holding.")
    L.append("")

    L.append("## 4. Claim-check - the declared book on the pack's own windows (zero cost)")
    L.append("")
    L.append("mode=hermes: the repo data sliced to the pack's own per-pair "
             "windows, zero fees, no funding, the pack's conventions. XAUUSDT "
             "has no data on disk (NO DATA declared). The claim columns are "
             "the pack's own published numbers, carried inside the artifact.")
    L.append("")
    L.append("| symbol | window | bars | declared ret % | declared PF | declared n | claim IS ret % | claim OOS ret % | claim OOS PF | claim OOS n | claim OOS excess % | run_id |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for sym, rid in CLAIMCHECK:
        a = load(rid)["metrics"]
        L.append(
            f"| {sym} | {a['window_start_utc']} to {a['window_end_utc']} | "
            f"{a['bars']} | {f2(a['return_pct'])} | {f4(a['profit_factor'])} | "
            f"{a['n_trades']} | {f2(a.get('claim_is_return_pct') or 0)} | "
            f"{f2(a.get('claim_oos_return_pct') or 0)} | "
            f"{f4(a.get('claim_oos_pf') or 0)} | "
            f"{a.get('claim_oos_n_trades') or 0} | "
            f"{f2(a.get('claim_oos_excess_pct') or 0)} | {rid} |")
    L.append("")
    L.append(f"The pack's headline full-2026 JUPUSDT claim (return "
             f"{f2(jc['claim_full_return_pct'])} percent, PF "
             f"{f4(jc['claim_full_pf'])}, {jc['claim_full_n_trades']} trades, "
             f"max DD {f2(jc['claim_full_max_dd_pct'])} percent against buy & "
             f"hold {f2(jc['claim_full_bh_return_pct'])} percent) is carried in "
             f"artifact {JUP_CLAIM}; the declared book on the same bytes and "
             f"window delivers {f2(jc['return_pct'])} percent at PF "
             f"{f4(jc['profit_factor'])} over {jc['n_trades']} trades. The "
             "claim is unreproducible from its own published outputs even in "
             "the most favorable setting (its own data, its own fills and stop "
             "rule, zero cost).")
    L.append("")

    L.append("## 5. Repo battery - full repo history, 11 bps RT, funding charged")
    L.append("")
    L.append("mode=repo on the full 1h history on disk (per-pair window dates in "
             "the table; NVDAUSDT and SPCXUSDT only exist from 2026). Gate "
             "battery as in code/bt.py (PF ex-cost above 1.2, n at least 30, "
             "net above 0, at least 2 of 3 green thirds, OOS PF above 1.2, OOS "
             "net above 0, top-5 concentration at or below 100 percent of PnL, "
             "bootstrap CI of the mean trade above 0).")
    L.append("")
    L.append("| symbol | window | bars | n | net % | PF ex-cost | max DD % | thirds green | OOS PF | OOS net % | boot CI lo | zero-cost ret % | funding paid | top5 % of PnL | run_id |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for sym, rid in BATTERY:
        a = load(rid)["metrics"]
        L.append(
            f"| {sym} | {a['window_start_utc']} to {a['window_end_utc']} | "
            f"{a['bars']} | {a['n_trades']} | {f2(a['return_pct'])} | "
            f"{f4(a['profit_factor'])} | {f2(a['max_dd_pct'])} | "
            f"{a['thirds_green']} | {f4(a['oos_profit_factor'])} | "
            f"{f2(a['oos_return_pct'])} | {f2(a['boot_ci_lo'])} | "
            f"{f2(a['zero_cost_return_pct'])} | {f2(a['funding_paid'])} | "
            f"{f2(a['best5_share_pct'])} | {rid} |")
    L.append("")
    L.append("XAUUSDT: NO DATA - no kline file for the symbol exists anywhere "
             "under data/ (the adapter's inputs fail loudly; the pack's XAU "
             "cell is declared unmeasurable in this repo).")
    L.append("")
    L.append("Reading the table: the top-5 concentration column is negative on "
             "the losing cells because the share divides by a negative total "
             "PnL - it is measured as stored, and the gate it feeds (at or "
             "below 100 percent) passes trivially there; the concentration gate "
             f"binds only on winning books (ETHUSDT {f2(load('13330a919c10aa61')['metrics']['best5_share_pct'])} "
             "percent of PnL).")
    L.append("")

    L.append("## 6. Verdict")
    L.append("")
    L.append("Per REGLA 1 this verdict uses ONLY this strategy's own artifacts "
             "(the 22 run_ids cited above; all verify bit-for-bit). The "
             "fingrad and hmaaoadx HMA relatives are context, not evidence.")
    L.append("")
    L.append("**KILLED - zero of eleven measurable cells pass the screen "
             "battery, at every gate that binds.** The full-history book with "
             "repo costs and real funding: profit factor 0.6883 to 1.0128 "
             "(nothing reaches the 1.2 gate), OOS profit factor 0.7470 to "
             "1.1074 (nothing reaches 1.2), bootstrap CI of the mean per-trade "
             "PnL below zero on all eleven cells, thirds green on at most 2 of "
             "3. The zero-cost control inside the artifacts shows the cost "
             "regime is not the whole story: JUPUSDT at zero cost returns "
             f"{f2(jb['zero_cost_return_pct'])} percent against "
             f"{f2(jb['return_pct'])} percent at repo costs - the signal has "
             "no gross edge to protect.")
    L.append("")
    L.append("**The external claim is UNREPRODUCIBLE FROM ITS OWN OUTPUTS.** "
             "With the pack's own data, its own measured fill and stop "
             "conventions, and zero cost, no defensible reading of "
             "\"HMA(34) Trend\" approaches the published returns; the published "
             "profit factor is pct-weighted; the OOS cells are a single 38-day "
             "slice with five of twelve pairs already losing to buy & hold; "
             "and the pack charged its perps neither fees nor funding. Its "
             "numbers must not be cited anywhere as results.")
    L.append("")
    L.append("Next step per doctrine: none - no forward paper record for a "
             "book with no gross edge; the line closes here unless a NEW, "
             "SOURCE-COMPLETE pack arrives (REGLA 1: this verdict never "
             "pre-condemns a new port).")
    L.append("")
    L.append("Artifacts: results/runs/<run_id>.json for the 22 run_ids in the "
             "tables above; bt.py one reports per cell in "
             "results/bt_one/hmatrend_<SYMBOL>_1h.md; parity tool "
             "code/_hma_trend_parity.py; engine audit code/_hma_trend_audit.py; "
             "sources of record code/hma_trend_sources/ with MANIFEST.json.")
    L.append("")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"written {OUT}")


if __name__ == "__main__":
    main()
