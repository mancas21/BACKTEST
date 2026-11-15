"""_s101_closeout.py — campaign close-out for the s101 pack (run AFTER
verify completes): report already rendered by _s101_report.py; this script
logs REPORTS.md, adds registry rows, and appends the AGENTS.md verdict.

Reads results/_s101_verify.txt to assert every cited artifact verified
before anything is published (REGLA 0).
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

NO_DATA = {
    111: "liquidation tape", 113: "open interest", 114: "no ETH spot",
    132: "no macro calendar", 136: "no tick data", 137: "no order book",
    142: "no NVDA 1m", 143: "no NVDA 3m (needs 1m)", 145: "no SMH",
    146: "no SPCX 1m", 147: "no SPY (trigger)", 148: "no VIX",
    149: "no breadth",
}


def main():
    # 1) REGLA 0 gate: every cited artifact must have verified
    verify = open(os.path.join(ROOT, "results", "_s101_verify.txt"),
                  encoding="utf-8").read()
    ok_n = verify.count("OK:")
    ids = [line.split()[0] for line in
           open(os.path.join(ROOT, "results", "_s101_ids.txt"),
                encoding="utf-8") if line.strip()]
    if ok_n != len(ids):
        sys.exit(f"REFUSED: only {ok_n} of {len(ids)} artifacts verified — "
                 f"finish the verify sweep before publishing.")
    print(f"verify gate: {ok_n} artifacts OK")

    # 2) REPORTS.md
    rep = os.path.join(ROOT, "results", "REPORTS.md")
    with open(rep, "a", encoding="utf-8") as fh:
        fh.write("\n| `s101_report.md` | STRATEGIES 101-150 pack (37 celdas "
                 "intradía: estructura/traps/sesiones/flujo/RV; 13 NO-DATA "
                 "saltadas por la regla #19 del pack) | KILLED — cero de "
                 "treinta y siete PASS; ruina por costes en intradía (37 "
                 "artifacts verify OK) | **OK (strict)** |\n")
    print("REPORTS.md logged")

    # 3) registry rows + family mapping
    rows = json.load(open(os.path.join(HERE, "_top100_rank.json"),
                          encoding="utf-8"))
    have = {r["run_id"] for r in rows}
    added = 0
    ids_list = [line.split()[0] for line in
                open(os.path.join(ROOT, "results", "_s101_ids.txt"),
                     encoding="utf-8") if line.strip()]
    # map run_id -> cell via the artifacts
    rid_cell = {}
    for rid in ids_list:
        d = json.load(open(os.path.join(ROOT, "results", "runs",
                                        rid + ".json"), encoding="utf-8"))
        rid_cell[rid] = (d["metrics"]["id"], d["metrics"]["symbol"],
                         d["metrics"]["tf"], d["metrics"])
    for rid in ids_list:
        if rid in have:
            continue
        idn, sym, tf, m = rid_cell[rid]
        rows.append({
            "run_id": rid, "adapter": "s101", "symbol": sym, "tf": tf,
            "label": f"s101 prompt {idn}",
            "ret": m["return_pct"], "pf": m["profit_factor"],
            "n": m["n_trades"], "dd": m["max_dd_pct"],
            "bh": None, "window": None,
            "fee": m.get("fee_per_side_bps", 5.0),
            "slip": m.get("slip_per_side_bps", 0.5), "funding": False,
            "created": "2026-11-13", "gates": None,
        })
        added += 1
    json.dump(rows, open(os.path.join(HERE, "_top100_rank.json"), "w"),
              ensure_ascii=False)
    print(f"index rows added: {added}")

    rsrc = open(os.path.join(HERE, "strategy_registry.py"),
                encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in rsrc else "\n"
    a1 = '    "fvgup": ("fvg_system", "maker_1m_resolved"),'
    if '    "s101": (' not in rsrc:
        assert rsrc.count(a1) == 1
        rsrc = rsrc.replace(a1, a1 + nl
                            + '    "s101": ("strategies_101_150", '
                              '"taker_next_open"),')
    a2 = ('    "fvgup": "KILLED 0/4 (muestra, concentracion y B&H; el coste '
          'consume el filo bruto; paridad dual-motor del pack falla en BTC - '
          'declarada)",')
    if '"s101": "KILLED' not in rsrc:
        assert rsrc.count(a2) == 1
        rsrc = rsrc.replace(a2, a2 + nl
                            + '    "s101": "KILLED 0/37 (ruina por costes en '
                              'intradia; ninguna celda pasa la bateria '
                              'estandar)",')
    open(os.path.join(HERE, "strategy_registry.py"), "w",
         encoding="utf-8", newline="").write(rsrc)
    print("registry mappings added")

    # 4) AGENTS.md verdict
    src = open(os.path.join(ROOT, "AGENTS.md"), encoding="utf-8",
               newline="").read()
    nl2 = "\r\n" if "\r\n" in src else "\n"
    anchor = ("## Current kills (from STATUS.md — read it for the full list)"
              + nl2 + nl2)
    assert src.count(anchor) == 1
    entry = (
        "- **STRATEGIES 101-150 pack (2026-11-13 attachment; adapter `s101`, 37 "
        "of 50 prompts runnable, 13 NO-DATA skips per the pack's own rule #19): "
        "KILLED — zero of 37 cells pass the screen battery; the dominant "
        "pattern is intraday cost ruin.** Sources of record byte-identical "
        "(`code/prompts_101_150.txt`, sha `ba1b3491…`); engine "
        "`code/s101_engine.py` over the audited p100 `Book` (signal on close, "
        "enter next open, stop-first, repo 11 bps RT, 0.5% risk/trade, the "
        "pack's daily counters — 3 losses/day and 6 trades/day on 1m-3m, "
        "MEASURED binding after a day-bucket unit bug was fixed: the constant "
        "was 8.64e10 ns instead of 8.64e13, so caps never accumulated), "
        "funding at real settlements for the perps (NVDA/SPCX none, "
        "declared), 70/30 chronological. Screen via bt.py: thirty-seven "
        "artifacts verify bit-for-bit (`results/_s101_verify.txt`); report "
        "`results/s101_report.md` (guard OK strict); pre-registration "
        "`results/s101_pre_registration.md`. Headline cells: 101 BTC 5m "
        "structure-retest `e7b92b1b89d5f276` net -100% (PF 0.14, 5207 "
        "trades); 103 BTC 1m failed-breakout `5f7997379c6c67b2` net -100% "
        "(PF 0.02); 117/118 pairs (SOL/BTC cointegration, SOL/ETH spread) "
        "net -100% PF 0.28/0.15 — mean-reversion pairs join the measured "
        "cost-wall families; best cell 138 JUP 15m stop-run "
        "`46a8ce34bf84ad03` net -12.65% PF 0.868 — still fails. 128 (wick >= "
        "2 ATR) measured dead by construction: zero trades in the window, "
        "declared as the prompt asked. NO-DATA: 111/113/114/132/136/137/142/"
        "143/145/146/147/148/149 (liquidations, OI, spot ETH, calendar, "
        "ticks, order book, NVDA 1m, SMH, SPCX 1m, SPY, VIX, breadth). "
        "**PIPELINE FIXES shipped with this campaign:** pre-flight validator "
        "`code/_s101_preflight.py` (37/37 cells on 60-day slices in minutes "
        "— would have caught every failed screen pass of this session), "
        "bt.py `_metric` now tolerates dict-form tables (one line), "
        "trap-checklist for adapter_template pending. The three failed "
        "screen passes of this session (86 min each) were all port-bug "
        "classes that the pre-flight now catches in minutes."
    ) + nl2 + nl2
    src = src.replace(anchor, anchor + entry)
    open(os.path.join(ROOT, "AGENTS.md"), "w", encoding="utf-8",
         newline="").write(src)
    print("AGENTS.md verdict added")


if __name__ == "__main__":
    main()
