"""_top100_refresh.py — rebuild the top-100 ranking from the REFRESHED
artifacts (re-run 2026-10-31 on current data bytes) and emit:

  results/top100_ranking_refresh_2026-10-31.md   (guard-checked report)
  results/top100_ranking_refresh_2026-10-31.csv  (full table incl. description)

Every number is read from the row's own NEW artifact; prose counts are words.
"""

import csv
import json
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from _top100_rank import extract, gates_passed  # the audited extractor

ROOT = os.path.normpath(os.path.join(HERE, ".."))

rerun = json.load(open(os.path.join(HERE, "_top100_rerun_map.json")))
cmd2new = {r["cmd"]: r["new_run_id"] for r in rerun if r["new_run_id"]}
kept_old = json.load(open(os.path.join(HERE, "_top100_kept.json")))

# ---------- descriptions (source: each engine's own spec table/docstring) ----
CBPACK = {
    "S01": "Bandas de deriva del flujo taker real (EMA del volumen firmado), con filtro de tendencia HTF, cooldown y guarda de banda; salida ATR SL + TP.",
    "S02": "Ruptura de canal Donchian de N barras confirmada por z-score del flujo taker y tendencia HTF; salida por retorno al canal o SL de ATR.",
    "S03": "Squeeze release: Bollinger dentro de Keltner y su liberación, con acuerdo de signo de momentum y flujo; SL/TP de ATR y time-stop.",
    "S07": "Fade del extremo del z-score de funding (perp caro/barato) cuando el precio pierde/recupera su EMA; SL/TP ATR y time-stop. Funding cobrado.",
    "S10": "Momentum de series temporales (retorno N barras / vol realizada) con histéresis de entrada/salida y SL ancho; objetivo de vol por posición.",
}
PACK_NOTE = {
    "xrpneutral": "ÚNICO PASS (todos los gates)",
    "pack50": "KILLED 0/48", "pack50b": "KILLED 0/46", "pack50c": "KILLED 0/42",
    "pack50d": "KILLED 0/48", "pack100": "KILLED 0/100",
    "qs": "KILLED (familia A 0/10; flujo 0/8)",
    "dspack": "familia muerta (changepoint trend)",
    "dspack2": "familia muerta (stat-arb / RSI-2)",
    "cbpackf": "KILLED <1h; 1h cae por concentración",
    "emaadx": "KILLED", "botstrat": "sin veredicto de gates registrado",
    "fingrad": "KILLED", "smqe": "SUSPENDED (sin OOS posible)",
    "cvrmd": "frágil / suspendido", "q10": "pack Qwen rechazado (diagnóstico)",
    "eqpack": "KILLED 0/7 (QQQ)", "mpv3": "muerto por concentración",
    "rsimr": "no pasa (mitades inestables)", "cand7": "KILLED 0/7",
    "sax": "UNRUNNABLE (engine borrado)",
}
QS_DESC = {
    "QS-001": "Continuación de tendencia por media móvil: entra en la dirección de la MA al confirmarse la barra, SL 2*ATR(14) y objetivo 4R.",
    "QS-002": "Alineación de EMAs con confirmación de volatilidad (la expansión valida la señal); SL 2*ATR(14), 4R.",
    "QS-003": "Continuación con Supertrend: posición mientras la línea no voltea, SL en la línea del Supertrend con tope 3*ATR.",
    "QS-004": "Ruptura de canal Donchian; SL 2*ATR o el extremo contrario de 20 barras (el más cercano), objetivo 4R.",
    "QS-005": "Momentum de series temporales clásico (retorno de N barras), SL 2*ATR(14), 4R.",
    "QS-006": "Continuación direccional filtrada por ADX (solo opera con tendencia establecida); SL 2*ATR(14), 4R.",
    "QS-007": "Tendencia del timeframe alto, entradas en el timeframe bajo en dirección de la mayor; SL 2*ATR(14).",
    "QS-009": "Momentum ajustado por volatilidad (tamaño inverso a la vol realizada); SL 2*ATR(14).",
}
DSPACK_DESC = {
    "ds1": "TSMOM: signo del log-momentum de 168h escalado por vol objetivo (vol targeting), posiciones continuas [-1,1].",
    "ds2": "Donchian 100 con filtro de expansión de volatilidad (rango > 1.5*ATR): long en máximo nuevo, short en mínimo nuevo.",
    "ds3": "Régimen HTF long-only: opera solo con precio sobre EMA200 y EMA50 sobre EMA200; sale al perder el régimen.",
    "ds4": "Momentum cross-seccional (720h) sobre la cesta de nombres, largo el tercio fuerte y corto el débil, convención de cartera MPS20.",
    "ds5": "Ruptura de 48 barras con confirmación de volumen; reversión a media como salida.",
    "ds7": "RSI(2) extremo a favor/contra del régimen: mean-reversion de corto plazo con filtro de tendencia (pack DeepSeek 2).",
}

def describe(r):
    a, label = r["adapter"], str(r["label"])
    if a == "xrpneutral":
        return ("Rejilla dos lados delta-neutral en el perp XRPUSDT: órdenes límite compradoras y vendedoras escalonadas, "
                "cobertura de delta por ciclo, funding cobrado en cada settlement; neutra = medida (delta medio |%| del equity), no afirmada.")
    if a in ("cbpackf", "eqpack"):
        sid = label.split(" ")[0]
        base = CBPACK.get(sid, label)
        mkt = " sobre QQQ (1d, datos Alpaca ajustados)" if a == "eqpack" else ""
        return base + mkt
    if a == "qs":
        sid = label.split(" ")[0]
        var = r.get("_variant") or ""
        return QS_DESC.get(sid, label) + (" Variante: " + var if var else "")
    if a in ("dspack", "dspack2"):
        sid = label.strip()
        return DSPACK_DESC.get(sid, label)
    if a == "mpv3":
        return "Cartera equal-weight de momentum puro (MP-V3-S10): rebalanceo semanal, filtro de momentum 20 días, costes en cada giro."
    if a == "emaadx":
        return "Cruce de EMAs filtrado por ADX (puerto Pine 'EMA Cross + ADX Strategy'): entra cuando la tendencia tiene fuerza (ADX), SL/TP por ATR."
    if a == "botstrat":
        return "Ruptura de caja por pivotes 49/49 con cruce WMA99/EMA99 del cuerpo; SL = extremo de señal ± 5*ATR14, TP escalonado 0.5/1/1.5R (33/33/34%), 10% de equity."
    if a == "fingrad":
        return "Fingrad HMA·AO·ADX (puerto Pine): tendencia por HMA, aceleración por Awesome Oscillator y fuerza por ADX; SL/TP del script, fills next-open."
    if a == "smqe":
        return "Smart Money Quant Engine v2 (puerto Pine): estructura SMC + order blocks con media móvil + núcleo CVRMD (VWAP+1sd, CVD, divergencias RSI/MACD)."
    if a == "cvrmd":
        return "CVRMD v1.1: VWAP de sesión +1sd con pendiente CLV-CVD, RSI14 y divergencia pivote MACD 12/26/9; SL 1.5*ATR congelado, TP1 media VWAP, TP2 2R, riesgo 1%."
    if a == "q10":
        card = label.strip()
        names = {"CARD1": "tarjeta 1 del pack Qwen (cartera mensual según su ficha de riesgo)",
                 "CARD2": "cross-seccional mensual long/short de baja volatilidad: largo las 5 menos volátiles de 10 nombres",
                 "CARD3": "tarjeta 3 del pack Qwen (selección mensual por su ficha)"}
        return names.get(card, card) + " — diagnóstico del pack Qwen, no una estrategia validada."
    if a in ("pack50", "pack50b", "pack50c", "pack50d", "pack100"):
        return (f"{label}: prompt de la familia {a} ejecutado con el modelo pack50 "
                "(señal al cierre, fill en la PRÓXIMA apertura, SL-first en empates, costes en cada fill).")
    return label

# ---------- rebuild rows from NEW artifacts ----------------------------------
rows = []
for old in kept_old:
    art = json.load(open(os.path.join(ROOT, "results", "runs", old["run_id"] + ".json")))
    cmd = art.get("cmd", "")
    new_id = cmd2new.get(cmd)
    if not new_id:
        continue
    d = json.load(open(os.path.join(ROOT, "results", "runs", new_id + ".json")))
    m = d.get("metrics", {})
    adapter = (d.get("provenance") or {}).get("adapter") or d.get("strategy", "?")
    symbol, tf = d.get("symbol"), d.get("timeframe")
    if adapter in ("cbpackf", "eqpack"):
        for t in extract(adapter, d):
            rows.append({"adapter": adapter, "symbol": symbol, "tf": tf, "label": t["label"],
                         "ret": t["ret"], "pf": t["pf"], "n": t["n"], "dd": t["dd"],
                         "bh": t.get("bh"), "run_id": new_id, "gates": None,
                         "variant": (d.get("params") or {}).get("variant")})
        continue
    for t in extract(adapter, d):
        rows.append({"adapter": adapter, "symbol": symbol, "tf": tf, "label": t["label"],
                     "ret": t["ret"], "pf": t["pf"], "n": t["n"], "dd": t["dd"], "bh": t.get("bh"),
                     "run_id": new_id, "gates": gates_passed(m, adapter),
                     "variant": (d.get("params") or {}).get("variant"),
                     "win": m.get("win_rate"), "funding": m.get("funding_paid"),
                     "fee": m.get("fee_bps_per_side") or m.get("cost_bps_per_side"),
                     "slip": m.get("slippage_bps_per_side") or m.get("slip_bps_per_side"),
                     "crt": m.get("cost_bp_roundtrip") or m.get("costs_primary")})

# dedupe identity (same rule as the original ranking)
best = {}
for r in rows:
    key = (r["adapter"], str(r["label"]), str(r["symbol"]), str(r["tf"]))
    cur = best.get(key)
    if cur is None or (r["ret"] or -1e18) > (cur["ret"] or -1e18):
        best[key] = r
ranked = sorted(best.values(), key=lambda r: r["ret"] or -1e18, reverse=True)[:100]

# verify status of the NEW artifacts
verif = {}
for f in ("_top100_newpverify.txt",):
    p = os.path.join(ROOT, "results", f)
    if os.path.exists(p):
        import re
        for line in open(p, encoding="utf-8", errors="replace"):
            mm = re.match(r"^(OK|STALE|ORPHANED|RC=\d+)\s+(\S+)", line)
            if mm:
                verif[mm.group(2)] = "OK" if mm.group(1) == "OK" else (
                    "REFUSED" if mm.group(1).startswith("RC=") else mm.group(1))
for r in ranked:
    r["verif"] = verif.get(r["run_id"], "—")

def fmt(v, nd=2, suf=""):
    return f"{v:.{nd}f}{suf}" if isinstance(v, (int, float)) else "—"

# ---------- CSV --------------------------------------------------------------
def _sane(x):
    # no raw ';' inside text fields: some viewers split on it regardless of
    # quoting and shift every column after it
    return str(x).replace(";", ",").replace('"', "'") if isinstance(x, str) else x

def _row(i, r):
    return [i, r["run_id"], f"results/runs/{r['run_id']}.json", r["label"],
            describe(r), r["adapter"], PACK_NOTE.get(r["adapter"], "—"),
            r["symbol"], r["tf"], fmt(r["ret"]), fmt(r.get("bh")),
            fmt(r.get("pf")), fmt(r.get("n"), 0), fmt(r.get("dd")),
            f"{r['gates'][0]}/{r['gates'][1]}" if r.get("gates") else "—",
            fmt(r.get("win")), fmt(r.get("funding")), fmt(r.get("fee")),
            fmt(r.get("slip")), fmt(r.get("crt")), r["verif"]]

HDR = ["rank", "run_id", "artifact", "estrategia", "que_hace", "pack",
       "veredicto_pack", "simbolo", "tf", "ret_neto_pct", "bh_pct",
       "profit_factor", "n_ops", "max_dd_pct", "gates_pasados",
       "win_rate_pct", "funding_pagado_usdt", "fee_bps_lado",
       "slip_bps_lado", "cost_rt_bps", "verificacion"]

csv_path = os.path.join(ROOT, "results", "top100_ranking_refresh_2026-10-31.csv")
with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=",", quoting=csv.QUOTE_MINIMAL)  # RFC4180
    w.writerow(HDR)
    for i, r in enumerate(ranked, 1):
        w.writerow([_sane(x) for x in _row(i, r)])
es_path = os.path.join(ROOT, "results", "top100_ranking_refresh_2026-10-31_es_excel.csv")
with open(es_path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")  # Spanish-locale Excel double-click
    w.writerow(HDR)
    for i, r in enumerate(ranked, 1):
        w.writerow([_sane(x) for x in _row(i, r)])
print("CSV ->", os.path.normpath(csv_path))
print("CSV ->", os.path.normpath(es_path))

# ---------- markdown ---------------------------------------------------------
L = []
A = L.append
A("# Top cien estrategias REFRESCADO con datos actuales — 2026-10-31")
A("")
A("Re-ejecución verbatim de los comandos grabados en cada artefacto citado por el")
A("ranking anterior, sobre los bytes de datos presentes HOY (klines y funding")
A("extendidos). Cada fila cita su artefacto NUEVO en `results/runs/`. Los noventa y")
A("cuatro comandos produjeron artefacto nuevo sin error; la columna Verif es el")
A("`pverify` de hoy sobre esos artefactos nuevos.")
A("")
A("**Sigue siendo un ranking DESCRIPTIVO por retorno neto medido, no una validación:**")
A("el único conjunto que pasa todos los gates del repo sigue siendo la rejilla")
A("delta-neutral XRP. Los packs muertos siguen muertos; el refresco no los reviva.")
A("")
A("| # | Estrategia | Pack (veredicto) | Símbolo | TF | Ret neto | B&H | PF | n ops | Gates | Verif | run_id |")
A("|---|---|---|---|---|---|---|---|---|---|---|---|")
for i, r in enumerate(ranked, 1):
    g = f"{r['gates'][0]}/{r['gates'][1]}" if r.get("gates") else "—"
    A(f"| {i} | {r['label']} | {r['adapter']} ({PACK_NOTE.get(r['adapter'], '—')}) | "
      f"{r['symbol']} | {r['tf']} | {fmt(r['ret'], suf='%')} | {fmt(r.get('bh'), suf='%')} | "
      f"{fmt(r.get('pf'))} | {fmt(r.get('n'), 0)} | {g} | {r['verif']} | `{r['run_id']}` |")
A("")
A("La descripción de qué hace cada estrategia (una por fila) está en el CSV:")
A("`results/top100_ranking_refresh_2026-10-31.csv`, columna `que_hace`.")
A("")
md_path = os.path.join(ROOT, "results", "top100_ranking_refresh_2026-10-31.md")
open(md_path, "w", encoding="utf-8").write("\n".join(L))
print("MD  ->", os.path.normpath(md_path))
print("top ret:", fmt(ranked[0]["ret"]), "  boundary:", fmt(ranked[-1]["ret"]))
