"""_top100_v2.py — corrected top-100 after the external audit (2026-10-31).

Corrections applied to the refresh ranking:
  1. dspack ds1/ds3/ds5 rows re-run at the repo6x5 cost preset (6 bps fee +
     5 bps slip per side = 11 bps RT) — the ranking rows were cost-ZERO
     ("author" preset) and are replaced by the honest artifacts.
  2. botstrat 15m row dropped: the engine hardcodes the 1h file, so the 15m
     artifact is a duplicate of the 1h one with false provenance.
  3. qs rows carry their own artifact verdict (INCONCLUSIVE), not the pack's.
  4. New columns: window years, return per year, realized cost regime, funding
     charged flag.

Writes results/top100_v2_2026-10-31.csv (+ .md). Numbers only from artifacts;
window years / ret-per-year are DERIVED and marked as such.
"""

import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from _top100_refresh import describe, PACK_NOTE  # descriptions + pack verdicts

TF_MIN = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}

cur = list(csv.DictReader(
    open(os.path.join(ROOT, "results", "top100_ranking_refresh_2026-10-31.csv"),
         encoding="utf-8-sig")))
rerun = json.load(open(os.path.join(HERE, "_top100_rerun_map.json")))
dsp = json.load(open(os.path.join(HERE, "_dspack_repo_map.json")))

# dspack repo6x5 artifacts keyed by (strat, symbol)
dsp_repo = {}
for o in dsp:
    if not o["new_run_id"]:
        continue
    d = json.load(open(os.path.join(ROOT, "results", "runs", o["new_run_id"] + ".json")))
    dsp_repo[(d["params"]["strat"], d["symbol"])] = o["new_run_id"]

rows = []
for r in cur:
    adapter = r["pack"]
    key = (adapter, r["estrategia"], r["simbolo"], r["tf"])
    if adapter == "botstrat" and r["tf"] == "15m":
        continue  # engine hardcodes 1h; duplicate of the 1h row
    if adapter == "dspack":
        nid = dsp_repo.get((r["estrategia"], r["simbolo"]))
        if not nid:
            continue
        m = json.load(open(os.path.join(ROOT, "results", "runs", nid + ".json")))["metrics"]
        d = json.load(open(os.path.join(ROOT, "results", "runs", nid + ".json")))
        rows.append({**r, "run_id": nid, "artifact": f"results/runs/{nid}.json",
                     "ret_neto_pct": round(m["return_pct"], 2),
                     "bh_pct": round(m.get("bench_ret_pct"), 2) if m.get("bench_ret_pct") is not None else "—",
                     "profit_factor": round(m["profit_factor"], 2) if m.get("profit_factor") else "—",
                     "n_ops": m.get("n_trades"), "max_dd_pct": round(m["max_dd_pct"], 2),
                     "costos": "11 bps RT (repo6x5)", "verificacion": "OK", "funding_charged": False})
        continue
    d = json.load(open(os.path.join(ROOT, "results", "runs", r["run_id"] + ".json")))
    m = d.get("metrics", {})
    cost = r.get("cost_rt_bps")
    funding = m.get("funding_charged")
    if adapter == "fingrad":
        funding = False
    verd = PACK_NOTE.get(adapter, "—")
    if adapter == "qs" and m.get("verdict"):
        verd = f"fila: {m['verdict']}"
    if adapter == "xrpneutral":
        verd = ("KILLED por resolucion 1m (2026-10-31): con los toques resueltos en "
                "orden temporal de minutos sobre el segmento OOS 2023+ el PF cae "
                "1.30 -> 0.93 y el retorno a -74.2% (sonda _xrp_1m_resolution.py)")
    rows.append({**r, "veredicto_pack": verd, "costos": f"{cost} bps RT"
                 if cost and cost != "—" else "—",
                 "funding_charged": funding})

# window years + return per year (DERIVED, from artifact bars x tf)
for r in rows:
    d = json.load(open(os.path.join(ROOT, "results", "runs", r["run_id"] + ".json")))
    bars = d.get("metrics", {}).get("bars")
    mins = TF_MIN.get(r["tf"])
    if isinstance(bars, (int, float)) and mins:
        yrs = bars * mins / 525960.0
        r["ventana_anos"] = round(yrs, 2)
        ret = r.get("ret_neto_pct")
        r["ret_por_ano_pct"] = round((1.0 + float(ret) / 100.0) ** (1.0 / yrs) - 1.0, 1) * 1.0 \
            if isinstance(ret, (int, float)) and float(ret) > -100 else "—"
    else:
        r["ventana_anos"], r["ret_por_ano_pct"] = "—", "—"

rows.sort(key=lambda r: float(r["ret_neto_pct"]), reverse=True)
rows = rows[:100]

HDR = ["rank", "run_id", "artifact", "estrategia", "que_hace", "pack",
       "veredicto", "simbolo", "tf", "ventana_anos", "ret_neto_pct",
       "ret_por_ano_pct_DERIVADO", "bh_pct", "profit_factor", "n_ops",
       "max_dd_pct", "costos_reales", "funding_cobrado", "verificacion"]
with open(os.path.join(ROOT, "results", "top100_v2_2026-10-31.csv"), "w",
          newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=",")
    w.writerow(HDR)
    for i, r in enumerate(rows, 1):
        w.writerow([i, r["run_id"], r["artifact"], r["estrategia"], r["que_hace"],
                    r["pack"], r["veredicto_pack"], r["simbolo"], r["tf"],
                    r["ventana_anos"], r["ret_neto_pct"], r["ret_por_ano_pct"],
                    r["bh_pct"], r["profit_factor"], r["n_ops"], r["max_dd_pct"],
                    r["costos"], r.get("funding_charged", "—"), r["verificacion"]])
print("CSV ->", os.path.join(ROOT, "results", "top100_v2_2026-10-31.csv"))
print("top:", rows[0]["estrategia"], rows[0]["ret_neto_pct"], "| boundary:",
      rows[-1]["ret_neto_pct"])
print("dspack rows now:", [(r["estrategia"], r["simbolo"], r["ret_neto_pct"])
                           for r in rows if r["pack"] == "dspack"])
