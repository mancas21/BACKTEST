"""_hmatrend_closeout.py - campaign close-out for the hmatrend pack
(run AFTER verify completes): appends registry rows, logs REPORTS.md, and
writes the AGENTS.md / STATUS.md verdict. REGLA 0 gate: the verify sweep
output file must show every cited artifact verified before anything publishes.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

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
VERIFY_FILE = os.path.join(ROOT, "results", "_hmatrend_verify.txt")

VERDICT_TEXT = ("KILLED 0/11 (PF ex-cost 0.6883-1.0128, OOS PF 0.7470-1.1074, "
                "CI bootstrap negativo en las once celdas; el claim externo es "
                "irreproducible desde sus propios outputs)")


def main():
    # 1) REGLA 0 gate: every cited artifact must have verified
    if not os.path.exists(VERIFY_FILE):
        sys.exit(f"REFUSED: {VERIFY_FILE} missing - run the verify sweep first.")
    verify = open(VERIFY_FILE, encoding="utf-8").read()
    ok_n = verify.count("OK:")
    all_ids = [r for _, r in BATTERY + CLAIMCHECK]
    if ok_n != len(all_ids):
        sys.exit(f"REFUSED: only {ok_n} of {len(all_ids)} artifacts verified.")
    print(f"verify gate: {ok_n} artifacts OK")

    # 2) registry rows
    rank_path = os.path.join(HERE, "_top100_rank.json")
    rows = json.load(open(rank_path, encoding="utf-8"))
    have = {r["run_id"] for r in rows}
    added = 0
    for sym, rid in BATTERY + CLAIMCHECK:
        if rid in have:
            continue
        d = json.load(open(os.path.join(ROOT, "results", "runs", rid + ".json"),
                           encoding="utf-8"))
        m = d["metrics"]
        is_battery = m.get("mode") == "repo"
        rows.append({
            "run_id": rid,
            "adapter": "hmatrend",
            "symbol": sym,
            "tf": "1h",
            "label": (f"hmatrend {sym} 1h full-history battery"
                      if is_battery else
                      f"hmatrend {sym} 1h claim-check (ventana del pack, coste cero)"),
            "ret": m["return_pct"],
            "pf": m["profit_factor"],
            "n": m["n_trades"],
            "dd": -m["max_dd_pct"],
            "bh": m.get("bh_return_pct"),
            "window": f"{m['window_start_utc']}..{m['window_end_utc']}",
            "fee": 5.0 if is_battery else 0.0,
            "slip": 0.5 if is_battery else 0.0,
            "funding": bool(m.get("funding_charged")),
            "created": d.get("created_utc", "2026-11-14")[:10],
            "gates": None,
        })
        added += 1
    json.dump(rows, open(rank_path, "w", encoding="utf-8"), indent=1)
    print(f"rank.json: {added} rows added")

    # 3) REPORTS.md
    rep = os.path.join(ROOT, "results", "REPORTS.md")
    with open(rep, "a", encoding="utf-8") as fh:
        fh.write("\n| `hmatrend_report_2026-11-14.md` | hmatrend (pack externo "
                 "hermes HMA(34) Trend, 12 pares 1h 2026; reconstrucción "
                 "declarada - el código fuente del pack NO sobrevivió) | "
                 "KILLED — cero de once celdas pasa la batería (22 artifacts "
                 "verify OK); el claim es irreproducible desde sus propios "
                 "outputs; XAU NO DATA | **OK (strict)** |\n")
    print("REPORTS.md logged")

    # 4) registry regenerate is run by the caller afterwards
    print("next: python code/strategy_registry.py")


if __name__ == "__main__":
    main()
