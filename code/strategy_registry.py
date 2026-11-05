"""strategy_registry.py — the strategy universe as a queryable registry.

Physical layout stays untouched (run_id = content hash; engines hash-locked;
results/runs/ and data/ append-only). This builds the LOGICAL layer on top:

  results/registry/strategies.jsonl     one row per deduped strategy
  results/registry/by_symbol/<SYM>.md   view by pair
  results/registry/by_tf/<TF>.md        view by timeframe
  results/registry/by_family/<FAM>.md   view by family/adapter
  results/registry/README.md            schema + how to regenerate

Regenerate any time (never hand-edit):
    python code/strategy_registry.py                 # rebuild everything
    python code/strategy_registry.py --symbol SOLUSDT
    python code/strategy_registry.py --tf 1h
    python code/strategy_registry.py --family dspack
    python code/strategy_registry.py --verdict KILLED
"""

import argparse
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
REG = os.path.join(ROOT, "results", "registry")

TF_MIN = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}

# adapter -> (family, fill model, notes). fill models:
#   taker_next_open : signal on close, fill next open, taker fees (conservative)
#   maker_intrabar  : resting limit fills inside the bar — NOT certifiable on
#                     OHLC >= 5m (the 2026-10-31 XRP 1m kill)
#   maker_1m        : resting limit fills resolved minute by minute on a real
#                     1m tape — the only certifiable version of a maker book
#                     (code/_neutral_1m_audit.py proves the resolution)
#   portfolio_rebalance : scheduled portfolio turnover
FAMILY = {
    "xrpneutral": ("grid_neutral", "maker_intrabar"),
    "xrpneutral1m": ("grid_neutral", "maker_1m"),
    "cbpackf": ("pack_S01-S10_taker_flow", "taker_next_open"),
    "cbpack": ("pack_S01-S10_taker_flow", "taker_next_open"),
    "eqpack": ("pack_S01-S10_taker_flow", "taker_next_open"),
    "qs": ("risk_sized_book", "taker_next_open"),
    "qsf": ("risk_sized_book", "taker_next_open"),
    "qsb": ("risk_sized_book", "taker_next_open"),
    "qsc": ("risk_sized_book", "taker_next_open"),
    "qsd": ("risk_sized_book", "taker_next_open"),
    "dspack": ("deepseek_ds1-ds5", "taker_next_open"),
    "dspack2": ("deepseek_ds6-ds10", "taker_next_open"),
    "pack50": ("llm_pack", "taker_next_open"),
    "pack50b": ("llm_pack", "taker_next_open"),
    "pack50c": ("llm_pack", "taker_next_open"),
    "pack50d": ("llm_pack", "taker_next_open"),
    "pack100": ("llm_pack", "taker_next_open"),
    "prompts100": ("llm_pack", "taker_next_open"),
    "q10": ("qwen_cards", "portfolio_rebalance"),
    "mpv3": ("portfolio_momentum", "portfolio_rebalance"),
    "emaadx": ("trend_ema_adx", "taker_next_open"),
    "fingrad": ("trend_hma_ao_adx", "taker_next_open"),
    "smqe": ("smc_composite", "taker_next_open"),
    "cvrmd": ("vwap_cvd_divergence", "taker_next_open"),
    "botstrat": ("pivot_box_breakout", "taker_next_open"),
    "xsf": ("xs_factor", "taker_next_open"),
    "xsb": ("xs_relative_value", "taker_next_open"),
    "xsc": ("xs_funding_filter", "taker_next_open"),
    "rsimr": ("rsi_mean_reversion", "taker_next_open"),
    "sax": ("sax_scalper", "taker_next_open"),
    "ffs": ("ffs", "taker_next_open"),
    "cvrmd ": ("vwap_cvd_divergence", "taker_next_open"),
    "hmaaoadx": ("trend_hma_ao_adx", "taker_next_open"),
    "cand7": ("prespecified_candidates", "taker_next_open"),
    "top10": ("llm_pack_shortlist", "taker_next_open"),
}

VERDICT = {
    "xrpneutral": "KILLED (resolucion 1m: PF 0.93 vs 1.30 en el OOS 2023+; sonda _xrp_1m_resolution.py)",
    "xrpneutral1m": "KILLED (el mismo libro resuelto en 1m cae bajo PF 1 en el OOS; artefacto 18d686932bf06f78)",
    "cbpackf": "KILLED (<1h por costos; 1h cae por concentracion con funding cobrado)",
    "eqpack": "KILLED 0/7 (QQQ; ninguna bate B&H)",
    "qs": None,  # per-row verdict from the artifact
    "dspack": None,  # per-row: cost-zero ghosts; repo6x5 numbers joined below
    "pack50": "KILLED 0/48",
    "pack50b": "KILLED 0/46",
    "pack50c": "KILLED 0/42",
    "pack50d": "KILLED 0/48",
    "pack100": "KILLED 0/100",
    "prompts100": "KILLED (screen 2026-10-29)",
    "q10": "REJECTED pack (diagnostic artifacts only)",
    "mpv3": "KILLED (concentracion: top-5 > 100% del PnL)",
    "emaadx": "KILLED",
    "fingrad": "KILLED (y sin funding en perps: SUI 17.3%->1.6% con funding)",
    "smqe": "SUSPENDED (sin OOS posible)",
    "cvrmd": "FRAGILE/SUSPENDED (PF ~1.02 historia completa)",
    "botstrat": "SIN VEREDICTO (15m = duplicado del 1h: engine hardcodea 1h)",
    "rsimr": "NO PASA (mitades inestables)",
    "sax": "UNRUNNABLE (engine borrado; 49 artefactos huerfanos)",
    "xsf": "KILLED 0/3 (senal: 2/3 PF bruto < 1; concentracion y OOS; vecindario sin rescate)",
    "xsb": "KILLED 0/2 (ambas pierden en bruto; vecindario sin rescate)",
    "xsc": "KILLED 0/2 (FUNDGATE senal, FUNDTAIL suelo de muestra; funding cobrado de verdad)",
    "ffs": "KILLED (window-pick)",
}

# dspack cells re-measured at repo6x5 (11 bps RT) on 2026-10-31
DSPACK_REPO = {}
_mp = os.path.join(HERE, "_dspack_repo_map.json")
if os.path.exists(_mp):
    for o in json.load(open(_mp)):
        if o["new_run_id"]:
            d = json.load(open(os.path.join(ROOT, "results", "runs", o["new_run_id"] + ".json")))
            DSPACK_REPO[(d["params"]["strat"], d["symbol"])] = o["new_run_id"]

EXCLUDE = {"gatecal", "q10diag", "gate2", "mp20", "mps20", "cbot", "cbpack",
           "bookreplay"}  # bookreplay: fill-model probe, not a strategy row


def window_years(bars, tf):
    if isinstance(bars, (int, float)) and tf in TF_MIN:
        return round(bars * TF_MIN[tf] / 525960.0, 2)
    return None


def _top10_verdict(m):
    """Campaign gate set of results/top10_report.md, from artifact fields."""
    conc = (m.get("top5_pnl_share") is not None and m["top5_pnl_share"] < 1.0
            and m.get("net_without_top5") is not None and m["net_without_top5"] > 0)
    thirds = (m.get("thirds_green") or 0) >= 2
    boot = m.get("bootstrap") or {}
    sig = boot.get("ci_low") is not None and boot["ci_low"] > 0
    if m.get("gate_full") and m.get("gate_oos") and conc and thirds and sig:
        return ("CANDIDATE (4 gates limpios; OOS contaminado por seleccion de la "
                "criba; registro forward pendiente)")
    if not (m.get("gate_full") and m.get("gate_oos")):
        if not m.get("gate_full"):
            return "KILLED (gate completo)"
        return "KILLED (OOS PF bajo el gate)"
    if not conc:
        return "KILLED (concentracion)"
    if not thirds:
        return "KILLED (periodos)"
    return "KILLED (significacion)"


def load_rows():
    base = json.load(open(os.path.join(HERE, "_top100_rank.json")))
    rows = []
    for r in base:
        if r["adapter"] in EXCLUDE:
            continue
        p = os.path.join(ROOT, "results", "runs", r["run_id"] + ".json")
        try:
            d = json.load(open(p))
        except Exception:
            continue
        m = d.get("metrics", {})
        adapter = r["adapter"]
        fam, fill = FAMILY.get(adapter, (adapter, "taker_next_open"))
        ret_zero = m.get("zero_cost_ret_pct") or m.get("ret_zero_pct")
        ret_repo = None
        run_repo = None
        if adapter == "dspack":
            hit = DSPACK_REPO.get((str(r["label"]).strip(), r["symbol"]))
            if hit:
                dm = json.load(open(os.path.join(ROOT, "results", "runs", hit + ".json")))["metrics"]
                ret_repo, run_repo = dm["return_pct"], hit
                ret_zero = r["ret"]  # the author-preset artifact IS the zero-cost run
        verd = VERDICT.get(adapter)
        if adapter in ("qs", "qsf", "qsb", "qsc", "qsd") and m.get("verdict"):
            verd = f"fila {m['verdict']} (pack 0/10 + 0/8 + 0/12 + 0/10 + 0/10)"
        if adapter == "top10":
            verd = _top10_verdict(m)
        if adapter == "dspack":
            if ret_repo is None:
                verd = "SIN MEDIR A COSTOS REPO (preset author = costo cero)"
            else:
                verd = f"medido a 11 bps RT: {ret_repo:+.1f}%"
        rows.append({
            "family": fam, "fill_model": fill,
            "adapter": adapter, "name": r["label"],
            "symbol": r["symbol"], "tf": r["tf"],
            "ret_declared_pct": round(r["ret"], 2),
            "ret_zero_cost_pct": round(ret_zero, 2) if isinstance(ret_zero, (int, float)) else None,
            "ret_repo_11bps_pct": round(ret_repo, 2) if ret_repo is not None else None,
            "profit_factor": round(r["pf"], 3) if isinstance(r["pf"], (int, float)) else None,
            "n_trades": int(r["n"]) if isinstance(r["n"], (int, float)) else None,
            "max_dd_pct": round(r["dd"], 2) if isinstance(r["dd"], (int, float)) else None,
            "cost_rt_bps": r.get("fee") or m.get("cost_bp_roundtrip") or m.get("costs_primary"),
            "funding_charged": m.get("funding_charged") if adapter != "fingrad" else False,
            "window_years": window_years(m.get("bars"), r["tf"]),
            "verdict": verd or "SIN VEREDICTO",
            "run_id": r["run_id"],
            "run_id_repo_11bps": run_repo,
            "created": d.get("created_utc", "")[:10],
        })
    rows.sort(key=lambda x: x["ret_declared_pct"] or -1e18, reverse=True)
    return rows


def md_table(rows, hdr):
    cols = ["tf", "name", "ret_declared_pct", "ret_zero_cost_pct", "ret_repo_11bps_pct",
            "profit_factor", "n_trades", "max_dd_pct", "window_years", "verdict", "run_id"]
    titles = ["TF", "Estrategia", "Ret declarado", "Ret costo cero", "Ret 11bps RT",
              "PF", "n", "maxDD", "Ventana (años)", "Veredicto", "run_id"]
    out = ["| # | " + " | ".join(titles) + " |",
           "|" + "---|" * (len(titles) + 1)]
    for i, r in enumerate(rows, 1):
        vals = [str(r.get(c)) if r.get(c) is not None else "—" for c in cols]
        out.append(f"| {i} | " + " | ".join(vals) + f" | `{r['run_id']}` |"
                   if False else
                   f"| {i} | " + " | ".join(vals) + " |")
    return [hdr] + out


def write_views(rows):
    os.makedirs(REG, exist_ok=True)
    with open(os.path.join(REG, "strategies.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    def group_view(key, title, fname):
        groups = defaultdict(list)
        for r in rows:
            groups[str(r[key])].append(r)
        os.makedirs(os.path.join(REG, fname.split("/{")[0]), exist_ok=True)
        for g in sorted(groups, key=lambda g: -len(groups[g])):
            body = md_table(groups[g], f"# {title}: {g} — {len(groups[g])} estrategias\n\n")
            open(os.path.join(REG, fname.format(g=g.replace('/', '_'))), "w",
                 encoding="utf-8").write("\n".join(body) + "\n")
        return sorted(groups, key=lambda g: -len(groups[g]))

    syms = group_view("symbol", "Por par", "by_symbol/{g}.md")
    tfs = group_view("tf", "Por timeframe", "by_tf/{g}.md")
    fams = group_view("family", "Por familia", "by_family/{g}.md")

    open(os.path.join(REG, "README.md"), "w", encoding="utf-8").write(f"""# Registro de estrategias — generado, no editar

Fuente: barrido de `results/runs/` deduplicado por (adaptador, estrategia, par, tf).
Cada fila cita su artefacto (`results/runs/<run_id>.json`). Regenerar:

    python code/strategy_registry.py

Vistas: `by_symbol/<PAR>.md`, `by_tf/<TF>.md`, `by_family/<FAMILIA>.md`.

Columnas clave:
- `ret_declared_pct`: retorno del artefacto canonico (costos declarados del artefacto).
- `ret_zero_cost_pct`: control de costo cero medido dentro del artefacto cuando existe.
- `ret_repo_11bps_pct`: re-medicion a 11 bps RT (dspack completo; resto = su declarado).
- `fill_model`: taker_next_open (certificable en OHLC) vs maker_intrabar
  (NO certificable sin resolucion 1m / forward — leccion XRP 2026-10-31).
- `verdict`: veredicto del pack o de la fila; nunca confundir retorno con validacion.

Dimensiones: {len(syms)} pares, {len(tfs)} timeframes, {len(fams)} familias,
{len(rows)} estrategias.
""")
    return syms, tfs, fams


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol"), ap.add_argument("--tf")
    ap.add_argument("--family"), ap.add_argument("--verdict")
    ap.add_argument("--rebuild", action="store_true")
    a = ap.parse_args()
    rows = load_rows()
    syms, tfs, fams = write_views(rows)
    if a.symbol or a.tf or a.family or a.verdict:
        for r in rows:
            if a.symbol and str(r["symbol"]) != a.symbol:
                continue
            if a.tf and str(r["tf"]) != a.tf:
                continue
            if a.family and r["family"] != a.family:
                continue
            if a.verdict and a.verdict.lower() not in r["verdict"].lower():
                continue
            print(json.dumps(r, ensure_ascii=False))
        return
    print(f"registro: {len(rows)} estrategias | {len(syms)} pares | {len(tfs)} tfs | {len(fams)} familias")
    print("por par:   ", {s: len([r for r in rows if r['symbol'] == s]) for s in syms[:8]})
    print("por tf:    ", {t: len([r for r in rows if r['tf'] == t]) for t in tfs})
    print("familias:  ", {f: len([r for r in rows if r['family'] == f]) for f in fams})


if __name__ == "__main__":
    main()
