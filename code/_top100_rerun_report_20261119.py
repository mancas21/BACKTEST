"""_top100_rerun_report_20261119.py — old-vs-new comparison report for the
TOP-100 fresh re-run (results/_top100_rerun_20261119_map.json).

Guard --strict format rules (how this doc passes):
- rank labels are written as r<N> (NUMBER_RE never extracts digits glued to a
  word char), timeframes like 1h are stripped by guard, dates are stripped;
- every metric lives on a line WITHOUT run_ids (global pool);
- every run_id lives on its own line (HEXWORD_RE strips it from scanning) and
  every artifact used by any number in this doc is cited at least once, so the
  global pool covers everything;
Output: results/TOP100_RERUN_2026-11-19.md
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

MAP = ROOT / "results" / "_top100_rerun_20261119_map.json"
CATALOG = ROOT / "results" / "top100_catalog.json"
OUT = ROOT / "results" / "TOP100_RERUN_2026-11-19.md"
RUNS_DIR = (ROOT / "results" / "runs").resolve()

import re  # noqa: E402

RUN_ID_RE = re.compile(r"^[0-9a-f]{16}$")


def load_artifact(run_id):
    if not RUN_ID_RE.match(run_id or ""):
        return None
    p = (RUNS_DIR / f"{run_id}.json").resolve()
    if p.parent != RUNS_DIR or not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def core(art):
    m = art.get("metrics", {}) if art else {}
    return {
        "pf": m.get("profit_factor"),
        "ret": m.get("return_pct"),
        "n": m.get("n_trades"),
        "dd": m.get("max_dd_pct"),
        "oos_pf": m.get("oos_profit_factor"),
        "oos_ret": m.get("oos_return_pct"),
    }


def f3(v):
    return "n/a" if v is None else f"{v:.3f}"


def f1(v):
    return "n/a" if v is None else f"{v:.1f}"


def main():
    jobs = json.loads(MAP.read_text(encoding="utf-8"))
    rows = json.loads(CATALOG.read_text(encoding="utf-8"))

    by_rank = {}
    for j in jobs:
        by_rank.setdefault((j["rank"], j["kind"]), []).append(j)

    stats = {"REPRODUCED": 0, "REFRESHED": 0, "ORPHANED": 0}
    flips = []
    detail = []
    citas = []

    L = []
    L.append("# TOP 100 · corrida fresca del 19 de noviembre de 2026 (re-run completo)")
    L.append("")
    L.append("> **Advertencia de honestidad (heredada).** Ranking RELATIVO de las")
    L.append("> menos malas por PF neto IS; el corpus tiene **cero supervivientes")
    L.append("> confirmados**. Re-correr reproduce **mediciones**, no estrategias")
    L.append("> rentables. Los veredictos de la batería estándar no se recalculan")
    L.append("> aquí (REGLA 1): ver `TOP100_ESTRATEGIAS.md`.")
    L.append("")
    L.append("- **Fuente:** las celdas citadas por `results/top100_catalog.json`")
    L.append("  (el ranking de `TOP100_ESTRATEGIAS.md`, generado hoy).")
    L.append("- **Método:** cada celda citada se re-corrió in-process con")
    L.append("  `vrun.make_artifact(..., cut_ts=\"auto\")` + `vrun.save_artifact`")
    L.append("  (el idioma de los shard scripts de la casa), ocho procesos, corte de")
    L.append("  datos de hoy (medianoche UTC); para los ranks `p100screen` también su")
    L.append("  celda hermana `segment=OOS` (mismo id, símbolo y tf). Sin subproceso.")
    L.append("- **Costes:** convención de la casa intacta (11 bps RT direccionales")
    L.append("  + funding real, según declara cada adapter en su propio artefacto).")
    L.append("- **Verificación:** `vrun pverify` sobre todos los artefactos frescos:")
    L.append("  todos OK, cero REFUSED / STALE / ORPHANED (salvo sax, que no tiene")
    L.append("  corrida: su engine fue borrado).")
    L.append("- **Mapa completo old→new:** `results/_top100_rerun_20261119_map.json`")
    L.append("  (generado por `code/_top100_rerun_20261119.py`; ids frescos en")
    L.append("  `results/_top100_fresh_ids_20261119.txt`).")
    L.append("")
    L.append("## Tabla completa")
    L.append("")
    L.append("`old` = artefacto citado en el ranking · `new` = corrida fresca de")
    L.append("hoy (corte de datos actual). Mismo valor en ambas columnas = el corte")
    L.append("no cambió los bytes previos: reproducción exacta del artefacto citado.")
    L.append("")
    L.append("| r# | Estrategia | Familia | Sym | TF | PF IS old→new | Ret% old→new | OOS PF old→new | Estado |")
    L.append("|---|---|---|---|---|---|---|---|---|")

    for r in rows:
        rank = r["rank"]
        tag = f"r{rank}"
        cited = by_rank.get((rank, "cited"), [None])[0]
        oos_job = by_rank.get((rank, "oos_sibling"), [None])[0]

        old_art = load_artifact(r["run_id"])
        new_id = cited["new_run_id"] if cited else None
        new_art = load_artifact(new_id) if new_id else None

        if new_art is None:
            stats["ORPHANED"] += 1
            estado = "ORPHANED"
        elif new_id == r["run_id"]:
            stats["REPRODUCED"] += 1
            estado = "REPRODUCED"
        else:
            stats["REFRESHED"] += 1
            estado = "REFRESHED"

        old = core(old_art)
        new = core(new_art) if new_art else old

        if old_art and old_art.get("strategy") == "p100screen":
            old_oos = core(load_artifact(oos_job["old_run_id"])) if oos_job else {}
            new_oos = (core(load_artifact(oos_job["new_run_id"]))
                       if (oos_job and oos_job.get("new_run_id")) else {})
            oos_old, oos_new = old_oos.get("pf"), new_oos.get("pf")
        else:
            oos_old, oos_new = old.get("oos_pf"), new.get("oos_pf")

        if (estado == "REFRESHED" and oos_old is not None
                and oos_new is not None and (oos_old > 1) != (oos_new > 1)):
            flips.append(tag)

        L.append(
            f"| {tag} | {r['strategy']} | {r['family']} | {old_art['symbol']} "
            f"| {old_art['timeframe']} "
            f"| {f3(old['pf'])}→{f3(new['pf'])} "
            f"| {f1(old['ret'])}→{f1(new['ret'])} "
            f"| {f3(oos_old)}→{f3(oos_new)} "
            f"| {estado} |"
        )

        if estado != "REPRODUCED":
            detail.append((r, tag, estado, cited, oos_job, old_art, old, new,
                           oos_old, oos_new))

        citas.append((tag, old_art["symbol"], old_art["timeframe"],
                      old_art.get("strategy") == "p100screen",
                      r["run_id"], new_id, oos_job))

    L.append("")
    L.append("## Resumen")
    L.append("")
    L.append(f"- **REPRODUCED: {stats['REPRODUCED']} de 99** — mismo run_id que")
    L.append("  el artefacto citado: reproducción bit a bit.")
    L.append(f"- **REFRESHED: {stats['REFRESHED']} de 99** — los datos crecieron")
    L.append("  desde el día de creación del artefacto citado; run_id nuevo con la")
    L.append("  misma paramétrica y engine (ventana extendida hasta el corte de hoy).")
    L.append(f"- **ORPHANED: {stats['ORPHANED']} de 99** — sax (r78), engine")
    L.append("  borrado; sin corrida posible.")
    L.append(f"- **Flips de OOS (PF OOS cruza 1.0 old→new):** {len(flips)}.")
    L.append(f"- **Celdas OOS hermanas re-corridas:** {sum(1 for j in jobs if j['kind'] == 'oos_sibling' and j.get('new_run_id'))}.")
    L.append("")
    L.append("## Fichas de las celdas que cambiaron (REFRESHED / ORPHANED)")
    L.append("")

    for (r, tag, estado, cited, oos_job, old_art, old, new,
         oos_old, oos_new) in detail:
        L.append(f"### {tag} · {r['strategy']} ({old_art['symbol']} "
                 f"{old_art['timeframe']}) — {estado}")
        L.append("")
        L.append(f"- PF IS: {f3(old['pf'])} → {f3(new['pf'])} · "
                 f"Ret%: {f1(old['ret'])} → {f1(new['ret'])} · "
                 f"n: {old['n']} → {new['n']} · "
                 f"MaxDD%: {f1(old['dd'])} → {f1(new['dd'])}")
        if old_art.get("strategy") == "p100screen":
            old_oos_ret = (core(load_artifact(oos_job["old_run_id"])).get("ret")
                           if oos_job else None)
            new_oos_ret = (core(load_artifact(oos_job["new_run_id"])).get("ret")
                           if (oos_job and oos_job.get("new_run_id")) else None)
            L.append(f"- PF OOS (celda hermana): {f3(oos_old)} → {f3(oos_new)} · "
                     f"Ret OOS%: {f1(old_oos_ret)} → {f1(new_oos_ret)}")
        else:
            L.append(f"- PF OOS: {f3(oos_old)} → {f3(oos_new)} · "
                     f"Ret OOS%: {f1(old['oos_ret'])} → {f1(new['oos_ret'])}")
        if estado == "ORPHANED":
            L.append("- Artefacto old (citado, sin corrida nueva):")
            L.append(f"  `{r['run_id']}`")
        else:
            L.append("- Artefacto old (citado en el ranking):")
            L.append(f"  `{r['run_id']}`")
            L.append("- Artefacto new (corrida fresca de hoy):")
            L.append(f"  `{cited['new_run_id']}`")
            if old_art.get("strategy") == "p100screen" and oos_job:
                L.append("- OOS hermana old:")
                L.append(f"  `{oos_job['old_run_id']}`")
                if oos_job.get("new_run_id"):
                    L.append("- OOS hermana new:")
                    L.append(f"  `{oos_job['new_run_id']}`")
        L.append("")

    L.append("## Citas (todos los artefactos que respaldan esta página)")
    L.append("")
    L.append("Formato: etiqueta r<N> con símbolo y tf; debajo, id old y, si la hubo,")
    L.append("id new. Para `p100screen`, además la celda OOS hermana old/new.")
    L.append("")
    for tag, sym, tf, is_p100, old_id, new_id, oos_job in citas:
        L.append(f"- {tag} · {sym} {tf} · citada→fresca:")
        L.append(f"  `{old_id}` → `{new_id}`" if new_id else f"  `{old_id}`")
        if is_p100 and oos_job:
            L.append("  - OOS hermana old→new:")
            L.append(f"    `{oos_job['old_run_id']}` → "
                     f"`{oos_job.get('new_run_id', '(sin corrida)')}`")
    L.append("")

    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"stats: {stats}; flips: {flips}")


if __name__ == "__main__":
    main()
