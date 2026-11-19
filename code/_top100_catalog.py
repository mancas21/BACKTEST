#!/usr/bin/env python
"""_top100_catalog.py -- Top-100 strategy catalog from VERIFIED artifacts.

Ranking: best net profit_factor cell per DISTINCT strategy (family,name), n>=30,
clean metrics (no compounding-overflow garbage). Every number is pulled from the
artifact cited by run_id (RULE 0). Descriptions from the pack specs (p100/s101)
or the descriptive strategy name + family context. OOS from the artifact's
oos_* fields, or the separate OOS-segment cell for p100screen.

HONESTY: the corpus has 0 confirmed survivors. This is a RELATIVE ranking of the
least-bad in-sample performers, NOT a list of profitable/validated strategies.
Outputs: results/top100_catalog.json / .csv / TOP100_ESTRATEGIAS.md
"""
from __future__ import annotations
import json, os, re, csv, math, glob, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "results", "runs")
REG = os.path.join(ROOT, "results", "registry", "strategies.jsonl")
P100_SPEC = os.path.join(ROOT, "content", "spec_sources", "strategy_prompts_100-sonnet-claude.md")
S101_SPEC = os.path.join(ROOT, "code", "prompts_101_150.txt")
CELLS = os.path.join(ROOT, "results", "_p100_cells")

def num(x):
    try:
        v = float(x); return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None

# ── descriptions: p100 headers "**NN · desc · sym**" ──
p100_desc = {}
if os.path.exists(P100_SPEC):
    txt = open(P100_SPEC, encoding="utf-8").read()
    for m in re.finditer(r"\*\*\s*(\d{1,3})\s*[·.]\s*(.+?)\s*[·.]\s*([A-Z0-9/]+)\s*\*\*", txt):
        p100_desc[int(m.group(1))] = m.group(2).strip()
# ── descriptions: s101 "NNN. Build a ..." ──
s101_desc = {}
if os.path.exists(S101_SPEC):
    for line in open(S101_SPEC, encoding="utf-8"):
        m = re.match(r"\s*(\d{3})\.\s+(.*)", line)
        if m:
            d = m.group(2).strip()
            d = re.sub(r"^Build\s+(a|an)\s+", "", d, flags=re.I)
            s101_desc[int(m.group(1))] = d[0].upper() + d[1:] if d else d

# ── p100screen OOS metrics + DEV run_id from the cell cache ──
# p100screen runs DEV (in-sample) and OOS as SEPARATE cells. Rank by DEV only
# (selecting max-PF across DEV/OOS would leak OOS into the ranking); show OOS apart.
p100_oos = {}
p100_dev_run = {}
if os.path.isdir(CELLS):
    for fn in os.listdir(CELLS):
        if fn.endswith("_OOS.json"):
            try:
                d = json.load(open(os.path.join(CELLS, fn), encoding="utf-8"))
                p100_oos[(d["id"], d["symbol"], d["tf"])] = d.get("metrics", {})
            except Exception:
                pass
        elif fn.endswith("_DEV.json"):
            try:
                d = json.load(open(os.path.join(CELLS, fn), encoding="utf-8"))
                p100_dev_run[(d["id"], d["symbol"], d["tf"])] = d["run_id"]
            except Exception:
                pass

FAMILY_DESC = {
    "p100screen": "Pack de 100 prompts (familias A-H: reversión, tendencia, rupturas, momentum, volumen/VWAP, price action/SMC, sesiones, regímenes/derivados), re-screened con el execution del repo.",
    "strategies_101_150": "Pack 101-150: estructura de mercado, trampas de liquidez, sesiones, flujo y valor relativo.",
    "risk_sized_book": "Libro QS risk-sized: estrategias con sizing por riesgo (1% equity / distancia al stop), apalancamiento capado.",
    "llm_pack": "Pack generado por LLM: rupturas, momentum, mean-reversion y filtros de volumen/flujo.",
    "llm_pack_shortlist": "Shortlist del pack LLM preseleccionada para validación ampliada.",
    "pack_S01-S10_taker_flow": "Pack S01-S10 de flujo taker (Donchian+flow, momentum time-series vol-targeted, HTF trend pullback).",
    "pack20": "Pack de 20 estrategias intradía (VWAP fade, ATR/vol breakout, TTM squeeze, etc.).",
    "scalp_ma_suite": "Suite de 20 scalps de medias móviles (EMA/TEMA/HMA/ZLEMA/KAMA, ribbons, VWAP, Supertrend, MACD, squeeze).",
    "qs096": "Motor qs096: estrategia cuantitativa con filtros de régimen y sizing por riesgo.",
    "qs097": "Motor qs097: variante cuantitativa con filtros de régimen.",
    "pivot_box_breakout": "Botstrat: ruptura de caja de pivotes con confirmación.",
    "smc_composite": "Compuesto SMC (smart money concepts): order blocks, FVG, liquidez.",
    "smqe11": "Motor smqe11: variante SMC cuantitativa.",
    "vwap_cvd_divergence": "Divergencia VWAP / CVD (cumulative volume delta) con confirmación de flujo.",
    "trend_ema_crossover": "Cruce de EMAs 9/21 con filtro de tendencia.",
    "trend_ema_adx": "Cruce de EMAs con filtro ADX de fuerza de tendencia.",
    "trend_hma_simple": "Tendencia con HMA (Hull MA) simple.",
    "trend_hma_ao_adx": "Tendencia HMA + Awesome Oscillator + ADX.",
    "deepseek_ds1-ds5": "Pack DeepSeek DS1-DS5 generado por LLM.",
    "deepseek_ds6-ds10": "Pack DeepSeek DS6-DS10 generado por LLM.",
    "htffvg": "HTF FVG: fair value gaps en temporalidad superior.",
    "ffs": "Motor ffs: estrategia de flujo/ruptura.",
    "sax_scalper": "Scalper SAX (symbolic aggregate approximation).",
    "qwen_cards": "Tarjetas de estrategia generadas por Qwen.",
    "xs_funding_filter": "Cross-sectional con filtro de funding.",
    "xs_relative_value": "Valor relativo cross-sectional.",
    "xs_factor": "Factor cross-sectional.",
    "ml_cross_sectional": "ML cross-sectional.",
    "grid_neutral": "Grid delta-neutral.",
    "portfolio_momentum": "Momentum de portfolio.",
    "capfloor": "Estructura cap/floor.",
    "ewexh": "Motor ewexh.",
    "smcrot": "Rotación SMC.",
    "rsi_mean_reversion": "Reversión a la media con RSI.",
    "prespecified_candidates": "Candidatos pre-especificados.",
    "fvg_system": "Sistema de fair value gaps.",
}

def humanize(name):
    n = re.sub(r"^\d+[_\s]*", "", name)          # strip leading NN_
    n = n.replace("_", " ").strip()
    return n

def describe(family, name, symbol, tf):
    if family == "p100screen":
        m = re.search(r"id=(\d+)", name)
        if m and int(m.group(1)) in p100_desc:
            return p100_desc[int(m.group(1))]
        return f"Prompt {name} del pack 100"
    if family == "strategies_101_150":
        m = re.search(r"id=(\d+)", name)
        if m and int(m.group(1)) in s101_desc:
            return s101_desc[int(m.group(1))]
        return f"Estrategia {name} del pack 101-150"
    base = humanize(name)
    if name.startswith("card="):
        return FAMILY_DESC.get(family, family)
    if re.fullmatch(r"ds\d+", base, re.I):
        return f"DeepSeek {base.upper()} (pack LLM DeepSeek)"
    if base.lower() in ("qs096", "qs097", "botstrat", "smqe", "smqe11", "cvrmd", "ema921", "ewexh", "smcrot", "fingrad", "cand7"):
        return f"{FAMILY_DESC.get(family, family)} (motor/candidato {base})"
    return base

# ── rank distinct strategies by best ARTIFACT net PF (n>=30, clean) ──
# Rank AND display use the SAME artifact metric (the registry manifest pf can
# mix declared/repo sources; loading the artifact keeps ranking consistent).
rows = [json.loads(l) for l in open(REG, encoding="utf-8")]
best = {}
n_loaded = 0
for r in rows:
    ap = os.path.join(RUNS, r["run_id"] + ".json")
    # p100screen: always rank/cite the DEV (in-sample) cell, never the OOS cell.
    if r["family"] == "p100screen":
        mm = re.search(r"id=(\d+)", r["name"])
        dev_run = p100_dev_run.get((int(mm.group(1)), r["symbol"], r["tf"])) if mm else None
        if not dev_run:
            continue
        ap = os.path.join(RUNS, dev_run + ".json")
        r = dict(r); r["run_id"] = dev_run
    if not os.path.exists(ap):
        continue
    a = json.load(open(ap, encoding="utf-8")); m = a.get("metrics", {})
    n_loaded += 1
    pf, n = num(m.get("profit_factor")), num(m.get("n_trades"))
    ret, dd = num(m.get("return_pct")), num(m.get("max_dd_pct"))
    if pf is None or n is None or n < 30:
        continue
    if (ret is not None and abs(ret) > 1e6) or (dd is not None and abs(dd) > 1e4):
        continue   # compounding-overflow garbage
    k = (r["family"], r["name"])
    if k not in best or pf > best[k][3]:
        best[k] = (r, a, m, pf)
cand = sorted(best.values(), key=lambda t: -t[3])   # ALL distinct clean strategies

all_records = []
for (r, a, m, pf) in cand:
    ret, dd = num(m.get("return_pct")), num(m.get("max_dd_pct"))
    n = num(m.get("n_trades"))
    rid = r["run_id"]
    fam, name, sym, tf = r["family"], r["name"], r["symbol"], r["tf"]
    # OOS
    oos_pf = num(m.get("oos_profit_factor")); oos_ret = num(m.get("oos_return_pct")); oos_n = num(m.get("oos_n_trades"))
    if fam == "p100screen":
        mm = re.search(r"id=(\d+)", name)
        if mm:
            om = p100_oos.get((int(mm.group(1)), sym, tf), {})
            oos_pf = num(om.get("profit_factor")); oos_ret = num(om.get("return_pct")); oos_n = num(om.get("n_trades"))
    inp = (a.get("inputs") or [{}])
    win = ""
    if isinstance(inp, list) and inp and isinstance(inp[0], dict):
        s, e = inp[0].get("start", ""), inp[0].get("end", "")
        if s and e:
            win = f"{str(s)[:10]} → {str(e)[:10]}"
    all_records.append({
        "strategy": describe(fam, name, sym, tf),
        "name": name, "family": fam, "symbol": sym, "tf": tf,
        "family_desc": FAMILY_DESC.get(fam, fam),
        "net_pf": round(pf, 4), "net_return_pct": round(ret, 2) if ret is not None else None,
        "n_trades": int(n), "win_rate_pct": round(num(m.get("win_rate")), 2) if num(m.get("win_rate")) is not None else None,
        "max_dd_pct": round(-abs(dd), 2) if dd is not None else None,
        "oos_pf": round(oos_pf, 4) if oos_pf is not None else None,
        "oos_return_pct": round(oos_ret, 2) if oos_ret is not None else None,
        "oos_n_trades": int(oos_n) if oos_n is not None else None,
        "bh_return_pct": round(num(m.get("bh_return_pct")), 2) if num(m.get("bh_return_pct")) is not None else None,
        "cost_rt_bps": num(m.get("cost_bp_roundtrip")) or r.get("cost_rt_bps"),
        "funding_charged": m.get("funding_charged", r.get("funding_charged")),
        "boot_ci_lo": round(num(m.get("boot_ci_lo")), 4) if num(m.get("boot_ci_lo")) is not None else None,
        "window": win, "verdict": r.get("verdict", ""), "run_id": rid,
    })

# assign IS rank; main catalog = top-100 by IS net PF
all_records.sort(key=lambda z: -z["net_pf"])
for i, x in enumerate(all_records):
    x["rank"] = i + 1
records = all_records[:100]

# ── outputs ──
os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
json.dump(records, open(os.path.join(ROOT, "results", "top100_catalog.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
with open(os.path.join(ROOT, "results", "top100_catalog.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(records[0].keys())); w.writeheader(); w.writerows(records)

n_oos_gt1 = sum(1 for x in records if x["oos_pf"] is not None and x["oos_pf"] > 1)
n_oos_avail = sum(1 for x in records if x["oos_pf"] is not None)
n_pf_gt12 = sum(1 for x in records if x["net_pf"] > 1.2)
n_pf_gt1 = sum(1 for x in records if x["net_pf"] > 1)
fam_count = collections.Counter(x["family"] for x in records)

L = []
L.append("# TOP 100 ESTRATEGIAS · ranking relativo por profit_factor neto")
L.append("")
L.append("> **ADVERTENCIA DE HONESTIDAD (leer primero).** El corpus completo (2370 celdas; "
         "295 estrategias distintas con n≥30 y métricas limpias) tiene **CERO supervivientes confirmados**: ninguna estrategia "
         "pasó la batería de validación completa (IS/OOS + bootstrap + concentración + costes + B&H). "
         "Este documento es un **ranking RELATIVO de las menos malas por PF neto in-sample**, NO una "
         "lista de estrategias rentables ni recomendaciones de trading. Un PF alto en IS con muestra "
         "pequeña, drawdown profundo u OOS fallido **no es invertible**. La cola del top-100 baja hasta "
         f"PF≈{records[-1]['net_pf']:.2f} (marginal). **Solo {n_pf_gt1} de las 100 tienen PF neto >1** en su artefacto verificado; las {100-n_pf_gt1} restantes pierden dinero a costes de la casa y se incluyen solo para completar el top-100 relativo. El ranking usa el **PF NETO del artefacto** (execution repo, 11 bps round-trip + funding real), NO el PF declarado/optimista del registry. Costes de la casa: 11 bps round-trip + funding real.")
L.append("")
L.append(f"- **Criterio de ranking:** mejor celda (mayor PF neto) por estrategia distinta `(familia, nombre)`, con `n_trades ≥ 30` y métricas limpias (se excluyen celdas con explosión de compounding, p.ej. return ~1e58).")
L.append(f"- **Fuente:** cada número proviene del artefacto verificado citado por `run_id` (RULE 0). PF/return/DD/win-rate del artefacto; OOS del campo `oos_*` o, en p100screen, de la celda OOS separada.")
L.append(f"- **Cobertura OOS:** {n_oos_avail}/100 tienen PF OOS disponible; de ellos, **{n_oos_gt1}** con OOS PF>1 (el resto falla out-of-sample).")
L.append(f"- **PF neto >1 en IS (artefacto verificado):** {n_pf_gt1}/100; **>1.2:** {n_pf_gt12}/100. Las {100-n_pf_gt1} restantes tienen PF neto <1 (pierden a costes repo). Familias representadas: {dict(fam_count.most_common())}.")
L.append("")
L.append("## Tabla resumen")
L.append("")
L.append("| # | Estrategia | Familia | Símbolo | TF | PF neto | Ret % | n | WR % | MaxDD % | OOS PF | Veredicto |")
L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
for x in records:
    v = (x["verdict"][:28] + "…") if len(x["verdict"]) > 28 else x["verdict"]
    oos = f"{x['oos_pf']:.3f}" if x["oos_pf"] is not None else "n/a"
    ret = f"{x['net_return_pct']:.1f}" if x["net_return_pct"] is not None else "n/a"
    wr = f"{x['win_rate_pct']:.1f}" if x["win_rate_pct"] is not None else "n/a"
    dd = f"{x['max_dd_pct']:.1f}" if x["max_dd_pct"] is not None else "n/a"
    strat = x["strategy"][:46]
    L.append(f"| {x['rank']} | {strat} | {x['family']} | {x['symbol']} | {x['tf']} | {x['net_pf']:.3f} | {ret} | {x['n_trades']} | {wr} | {dd} | {oos} | {v} |")
L.append("")
L.append("## Fichas detalladas")
L.append("")
for x in records:
    L.append(f"### {x['rank']}. {x['strategy']}")
    L.append("")
    L.append(f"- **Familia:** `{x['family']}` — {x['family_desc']}")
    L.append(f"- **Nombre/celda:** `{x['name']}` · **Símbolo:** {x['symbol']} · **TF:** {x['tf']}")
    L.append(f"- **Descripción:** {x['strategy']}")
    wrs = f"{x['win_rate_pct']:.2f}%" if x['win_rate_pct'] is not None else "n/a"
    rets = f"{x['net_return_pct']:.2f}%" if x['net_return_pct'] is not None else "n/a"
    dds = f"{x['max_dd_pct']:.2f}%" if x['max_dd_pct'] is not None else "n/a"
    L.append(f"- **PF neto (IS):** {x['net_pf']:.4f} · **Return neto:** {rets} · **n trades:** {x['n_trades']} · **Win rate:** {wrs} · **Max DD:** {dds}")
    oparts = []
    if x["oos_pf"] is not None:
        oparts.append(f"PF {x['oos_pf']}")
    if x["oos_return_pct"] is not None:
        oparts.append(f"ret {x['oos_return_pct']}%")
    if x["oos_n_trades"] is not None:
        oparts.append(f"n {x['oos_n_trades']}")
    L.append(f"- **OOS:** {' · '.join(oparts) if oparts else 'no disponible'}")
    if x["bh_return_pct"] is not None:
        L.append(f"- **Buy & Hold (contexto):** {x['bh_return_pct']}%")
    costs = f"{x['cost_rt_bps']} bps round-trip" if x['cost_rt_bps'] is not None else "no registrado (casa: 11 bps RT)"
    fund = x['funding_charged']
    funds = ("sí" if fund else "no") if fund is not None else "no registrado"
    L.append(f"- **Costes:** {costs} · **Funding cobrado:** {funds}")
    if x["boot_ci_lo"] is not None:
        L.append(f"- **Bootstrap CI lower (mean R):** {x['boot_ci_lo']}")
    if x["window"]:
        L.append(f"- **Ventana:** {x['window']}")
    L.append(f"- **Veredicto:** {x['verdict']}")
    L.append(f"- **Artefacto (run_id):** `{x['run_id']}`")
    L.append("")
L.append("---")
L.append("*Generado por `code/_top100_catalog.py` desde artefactos verificados. Ranking relativo dentro de un corpus con 0 supervivientes; no es asesoramiento ni una lista de estrategias rentables. Datos: `results/top100_catalog.json` / `.csv`.*")
open(os.path.join(ROOT, "results", "TOP100_ESTRATEGIAS.md"), "w", encoding="utf-8").write("\n".join(L))
print(f"catalog: {len(records)} strategies | OOS avail {n_oos_avail}, OOS>1 {n_oos_gt1} | PF>1.2 {n_pf_gt12}")
print(f"PF range: {records[0]['net_pf']:.3f} .. {records[-1]['net_pf']:.3f}")
print("families:", dict(fam_count.most_common()))
print("p100 descriptions parsed:", len(p100_desc), "| s101:", len(s101_desc), "| p100 OOS cells:", len(p100_oos))
print("outputs: results/TOP100_ESTRATEGIAS.md, top100_catalog.json, top100_catalog.csv")

# ── ALTERNATIVE VIEW: OOS-ranked + robustness filter (FULL corpus) ──
oos_avail = [x for x in all_records if x["oos_pf"] is not None]
oos_ranked = sorted(oos_avail, key=lambda z: -z["oos_pf"])
for i, x in enumerate(oos_ranked):
    x["oos_rank"] = i + 1
# robustness filter: IS n>=100, net IS PF>1, OOS PF>1, OOS n>=30, bootstrap CI lo>0
robust = [x for x in all_records
          if x["n_trades"] >= 100 and x["net_pf"] > 1
          and x["oos_pf"] is not None and x["oos_pf"] > 1
          and x["oos_n_trades"] is not None and x["oos_n_trades"] >= 30
          and x["boot_ci_lo"] is not None and x["boot_ci_lo"] > 0]
robust.sort(key=lambda z: -z["oos_pf"])
oos_holds = [x for x in oos_ranked
             if x["oos_pf"] > 1 and x["oos_n_trades"] is not None and x["oos_n_trades"] >= 30]
json.dump({"oos_ranked": oos_ranked, "robust": robust, "oos_holds": oos_holds},
          open(os.path.join(ROOT, "results", "top_oos_robust.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

M = []
M.append("# ESTRATEGIAS POR VALIDEZ OUT-OF-SAMPLE + FILTRO DE ROBUSTEZ")
M.append("")
M.append("> **Versión alternativa al top-100 por IS PF.** El ranking aquí es por **PF neto OOS** "
         "(validez out-of-sample) y se aplica un **filtro de robustez** para aislar las candidatas que "
         "realmente merecen seguimiento. Mismo corpus (0 supervivientes confirmados por la batería "
         "completa): esto es una **priorización de investigación**, NO una lista de estrategias rentables "
         "validadas ni recomendaciones de trading. Regla de la casa: OOS con n<200 se etiqueta FRÁGIL.")
M.append("")
M.append(f"- **Universo:** {len(all_records)} estrategias distintas (n≥30 IS, métricas limpias, artefacto verificado).")
M.append(f"- **Con OOS PF disponible:** {len(oos_avail)} · **con OOS PF>1 y OOS n≥30:** {len(oos_holds)}.")
M.append(f"- **Filtro de robustez** (IS n≥100 · PF neto IS>1 · OOS PF>1 · OOS n≥30 · bootstrap CI lower>0): **{len(robust)} pasan**.")
M.append("")
M.append("## A) Filtro de robustez — candidatas que merecen seguimiento")
M.append("")
if robust:
    M.append("| # | Estrategia | Familia | Símbolo | TF | PF IS | PF OOS | OOS ret% | OOS n | n IS | boot CI lo | Veredicto | run_id |")
    M.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for i, x in enumerate(robust, 1):
        frag = " ⚠FRÁGIL" if (x["oos_n_trades"] or 0) < 200 else ""
        M.append(f"| {i} | {x['strategy'][:38]} | {x['family']} | {x['symbol']} | {x['tf']} | {x['net_pf']:.3f} | {x['oos_pf']:.3f} | {x['oos_return_pct']} | {x['oos_n_trades']}{frag} | {x['n_trades']} | {x['boot_ci_lo']} | {x['verdict'][:22]} | `{x['run_id']}` |")
else:
    M.append("**NINGUNA estrategia pasa el filtro de robustez completo.** Ni una sola combina muestra "
             "IS≥100, PF neto IS>1, OOS PF>1 con OOS n≥30 y bootstrap CI lower>0. Resultado honesto: "
             "no hay candidata con evidencia estadística out-of-sample sólida en el corpus.")
M.append("")
M.append("**Importante — esto NO es la batería completa.** El filtro de arriba es un SUBCONJUNTO "
         "ligero de G1-G11. Las candidatas listadas **NO son supervivientes validadas**: les falta el "
         "estrés a **2× coste**, el **Deflated Sharpe (DSR** por múltiples pruebas), la **concentración** "
         "(top-5 trades), el **P95 de drawdown**, el **alfa t>2** y la comparación **B&H**. La mayoría "
         "están `SIN VEREDICTO` (nunca se juzgaron con la batería completa). Un PF OOS apenas >1 (p.ej. "
         "1.01-1.08) con turnover alto muere casi seguro al doblar costes. Son una **priorización para "
         "investigar**, no edges confirmados.")
M.append("")
M.append("## B) Ranking por PF neto OOS (top 50 con OOS disponible)")
M.append("")
M.append("*Ranking CRUDO por OOS PF: incluye celdas con OOS n<30 (ruido — un OOS PF alto con ~20 trades "
         "no es evidencia) y celdas con IS pésimo, bootstrap CI negativo o veredicto KILLED. Solo como "
         "panorama; las listas accionables son la A (filtro de robustez) y la C (OOS PF>1 con OOS n≥30).*")
M.append("")
M.append("| #OOS | Estrategia | Familia | Símbolo | TF | PF IS | PF OOS | OOS ret% | OOS n | n IS | boot CI lo | Veredicto |")
M.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
for x in oos_ranked[:50]:
    bci = f"{x['boot_ci_lo']}" if x["boot_ci_lo"] is not None else "n/a"
    oret = f"{x['oos_return_pct']}" if x["oos_return_pct"] is not None else "n/a"
    on = x["oos_n_trades"] if x["oos_n_trades"] is not None else "n/a"
    M.append(f"| {x['oos_rank']} | {x['strategy'][:38]} | {x['family']} | {x['symbol']} | {x['tf']} | {x['net_pf']:.3f} | {x['oos_pf']:.3f} | {oret} | {on} | {x['n_trades']} | {bci} | {x['verdict'][:22]} |")
M.append("")
M.append(f"## C) Fichas de las que sostienen OOS (OOS PF>1, OOS n≥30): {len(oos_holds)}")
M.append("")
for x in oos_holds:
    frag = " · **⚠FRÁGIL (OOS n<200)**" if (x["oos_n_trades"] or 0) < 200 else ""
    M.append(f"### {x['strategy']}")
    M.append(f"- `{x['family']}` · {x['symbol']} {x['tf']} · celda `{x['name']}`{frag}")
    M.append(f"- **IS:** PF {x['net_pf']:.4f} · ret {x['net_return_pct']}% · n {x['n_trades']} · DD {x['max_dd_pct']}%")
    M.append(f"- **OOS:** PF {x['oos_pf']:.4f} · ret {x['oos_return_pct']}% · n {x['oos_n_trades']}")
    M.append(f"- **Bootstrap CI lower (mean R):** {x['boot_ci_lo']}")
    M.append(f"- **Veredicto:** {x['verdict']}")
    M.append(f"- **Artefacto (run_id):** `{x['run_id']}`")
    M.append("")
M.append("---")
M.append("*Generado por `code/_top100_catalog.py` (vista OOS/robustez) desde artefactos verificados. Datos: `results/top_oos_robust.json`. Priorización de seguimiento, no recomendación rentable.*")
open(os.path.join(ROOT, "results", "TOP_OOS_ROBUST.md"), "w", encoding="utf-8").write("\n".join(M))
print(f"OOS view: {len(oos_avail)} con OOS | OOS holds {len(oos_holds)} | ROBUST filter {len(robust)}")
print("outputs: results/TOP_OOS_ROBUST.md, top_oos_robust.json")
