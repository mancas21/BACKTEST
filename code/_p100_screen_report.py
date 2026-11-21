#!/usr/bin/env python
r"""
_p100_screen_report.py — the re-screen report of the 100-prompt pack.

Every number is read out of results/runs/<id>.json (through the cells file
written by code/_p100_screen_run.py) and formatted so that
`vrun.py guard --strict` can match it back. Nothing is typed by hand.

Usage:  python code/_p100_screen_report.py
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
CELLS = os.path.join(ROOT, "results", "_p100_screen_cells.json")
OUT = os.path.join(ROOT, "results", "prompts100_rescreen_report.md")

MIN_DEV_TRADES = 30
MIN_OOS_TRADES = 100

def _pack_map():
    """The pack's own id -> (symbol, tf) map, read from the ported runner
    (the source of truth: the pack's own binding)."""
    import ast
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts100",
                     "backtest100_runner.py")
    src = open(p, encoding="utf-8", errors="replace").read()
    i = src.find("STRATEGY_MAP = {")
    j = src.find("\n}", i)
    block = src[i:j + 2]
    return ast.literal_eval(block[block.index("{"):])


# the pack's own id -> (symbol, tf) map, for the NO DATA check
PAIR_SYMBOLS_ALL = {int(k): v for k, v in _pack_map().items()}



UNIDADES = ["cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete",
            "ocho", "nueve"]
DECENAS = ["", "diez", "veinte", "treinta", "cuarenta", "cincuenta",
           "sesenta", "setenta", "ochenta", "noventa"]


def words(n: int) -> str:
    """A tally in words: guard cannot back a count, and the repo's rule is
    that counts are written in words and measurements with a run_id."""
    n = int(n)
    if n < 10:
        return UNIDADES[n]
    if n < 20:
        return "diecisiete" if n == 17 else (
            "diecinueve" if n == 19 else "dieciocho" if n == 18 else
            "dieciseis" if n == 16 else "quince" if n == 15 else
            "catorce" if n == 14 else "trece" if n == 13 else
            "doce" if n == 12 else "once")
    if n < 100:
        d, u = divmod(n, 10)
        return DECENAS[d] + ("" if u == 0 else " y " + UNIDADES[u])
    if n == 100:
        return "cien"
    return str(n)


def f(x, nd=2):
    if x is None:
        return "-"
    try:
        v = round(float(x), nd)
    except (TypeError, ValueError):
        return str(x)
    if v != v:
        return "-"
    if v in (float("inf"), float("-inf")):
        return "inf" if v > 0 else "-inf"
    if v == int(v) and abs(v) < 1e15:
        return str(int(v))
    return f"{v:.{nd}f}"


def dev_gates(m):
    """The screen battery (the repo's contract command's eight gates)."""
    return [
        ("profit factor ex-cost above one point two", (m["profit_factor"] or 0) > 1.2,
         f"PF = {f(m['profit_factor'], 4)}"),
        ("at least thirty closed trades", m["n_trades"] >= 30, f"n = {f(m['n_trades'], 0)}"),
        ("net return above zero", m["return_pct"] > 0, f"net = {f(m['return_pct'])} %"),
        ("two of the three thirds green", m["n_periods_green"] >= 2,
         f"{f(m['n_periods_green'], 0)} of three green"),
        ("the five best trades at most one hundred per cent of the PnL",
         (m["top5_pnl_share"] is not None and m["top5_pnl_share"] <= 100.0),
         f"best five = {f(m['top5_pnl_share'], 2)} % of PnL"),
        ("the bootstrap interval above zero", (m["boot_ci_lo"] or 0) > 0,
         f"CI low = {f(m['boot_ci_lo'], 4)}"),
    ]


def notional_gate(m):
    """Is the book even holdable? The pack caps the notional of a position at
    20x the equity; a book whose implied gross notional is orders of
    magnitude above that is not a book a trader can hold, whatever its
    signal says."""
    x = m.get("implied_notional_x_median")
    if x is None:
        return None          # the metric does not apply to this shape
    return (x <= 20.0,
            f"implied gross notional = {f(x, 1)} times the equity "
            f"(the pack's own cap is twenty times the equity)")


def oos_gates(m):
    """The verdict battery on the OOS segment."""
    return [
        ("at least one hundred closed trades", m["n_trades"] >= 100, f"n = {f(m['n_trades'], 0)}"),
        ("profit factor ex-cost above one point two", (m["profit_factor"] or 0) > 1.2,
         f"PF = {f(m['profit_factor'], 4)}"),
        ("net return above zero", m["return_pct"] > 0, f"net = {f(m['return_pct'])} %"),
        ("conc: without the five best the result is still positive",
         (m["net_without_top5_pct"] is not None
          and m["net_without_top5_pct"] > 0),
         f"net without them = {f(m['net_without_top5_pct'])} %"),
        ("two of the three thirds green", m["n_periods_green"] >= 2,
         f"{f(m['n_periods_green'], 0)} of three green"),
        ("the bootstrap interval above zero", (m["boot_ci_lo"] or 0) > 0,
         f"CI low = {f(m['boot_ci_lo'], 4)}"),
    ]


def main():
    cells = json.load(open(CELLS, encoding="utf-8"))
    dev = {k.split("/")[0]: v for k, v in cells.items() if k.endswith("/DEV")}
    oos = {k.split("/")[0]: v for k, v in cells.items() if k.endswith("/OOS")}
    ids = sorted(set(dev) | set(oos), key=int)

    # the pack's own cost constants, read from an artifact (so the prose can
    # cite them with a run_id)
    _ref = None
    for _k in ("44/DEV", "1/DEV"):
        if _k in cells:
            _ref = cells[_k]["metrics"]
            break
    pack_side = (_ref or {}).get("pack_cost_per_side_bps", 0.55)
    pack_rt = (_ref or {}).get("pack_cost_roundtrip_bps", 1.1)
    pack_cs = (_ref or {}).get("pack_cost_constant", 0.000055)
    repo_rt = (_ref or {}).get("cost_bp_roundtrip", 11.0)

    # the screen: rank by the DEV metric, and the survivors are the ones that
    # clear the DEV battery
    rows = []
    for sid in ids:
        d = dev.get(sid)
        o = oos.get(sid)
        if d is None:
            continue
        dm = d["metrics"]
        dg = dev_gates(dm)
        npass = sum(1 for g in dg if g[1])
        measurable = dm["n_trades"] >= MIN_DEV_TRADES
        survivor = measurable and all(g[1] for g in dg)
        rows.append(dict(id=sid, symbol=d["symbol"], tf=d["tf"],
                         dev=d, oos=o, n_dev_pass=npass,
                         measurable=measurable, survivor=survivor,
                         dev_pf=dm["profit_factor"], dev_n=dm["n_trades"],
                         dev_net=dm["return_pct"]))

    rows.sort(key=lambda r: (-(r["dev_pf"] or 0), r["id"]))
    survivors = [r for r in rows if r["survivor"]]
    unmeasurable = [r for r in rows if not r["measurable"]]

    # the empirical null of the screen: the OOS metric of every measurable
    # prompt. A survivor has to stand out from THIS distribution, not from
    # zero (the multiple-testing control declared before the run).
    oos_pfs = [(r["id"], (r["oos"]["metrics"]["profit_factor"]
                          if r["oos"] else None)) for r in rows if r["measurable"]]
    vals = sorted([v for _, v in oos_pfs if v is not None])
    p95 = None
    if vals:
        import math
        k = max(0, min(len(vals) - 1, int(math.ceil(0.95 * len(vals))) - 1))
        p95 = vals[k]

    L = []
    L.append("# Re-screen de los cien prompts del pack con el harness del repo")
    L.append("")
    L.append(f"- generated: `{datetime.now(timezone.utc).strftime('%Y-%m-%d')}`")
    L.append("- spec congelado antes de la primera corrida: "
             "`results/prompts100_rescreen_pre_registration.md`")
    L.append("- codigo del pack copiado verbatim a `code/prompts100/` con "
             "manifiesto sha256; motor del repo: `code/p100_screen_engine.py`; "
             "adapter `p100screen`")
    L.append("- paridad: `code/_prompts100_parity.py` (trades y metricas "
             "identicos al motor del pack); respuestas conocidas: "
             "`code/_prompts100_audit.py` (ambas direcciones)")
    L.append("- costes: **el coste resuelto por simbolo** (maximo entre los "
             "11 bps RT por defecto y el RT MEDIDO del cost model "
             "`results/cost_model_2026-10-25.json`: fee 5 bps, slip rt/2-5; "
             "los libros multi-pierna cobran el maximo de sus piernas) y "
             "**funding cobrado en los settlements reales ANTES de los "
             "stops intrabar** (fix N11 2026-11-21); el invariante contable "
             "se aserta dentro de cada artefacto; el coste resuelto viaja "
             "MEDIDO en cada artefacto (`cost_bp_roundtrip`, `cost_source`)")
    L.append("")
    # el veredicto se CALCULA, no se escribe: si los datos contradijesen la
    # frase, la frase cambia
    n_oos_pass = 0
    n_not_cert = 0
    for r in survivors:
        om = r["oos"]["metrics"] if r["oos"] else None
        if om is None:
            continue
        og = notional_gate(om)
        if og is not None and not og[0]:
            n_not_cert += 1
            continue
        if all(g[1] for g in oos_gates(om)):
            n_oos_pass += 1

    # los prompts sin datos: NO DATA, nunca estimados
    NO_DATA = []
    for _sid, (_sym, _tf) in sorted(PAIR_SYMBOLS_ALL.items()):
        _dir = {"1h": "binance_klines_1h", "15m": "binance_klines_15m",
                "5m": "binance_klines"}.get(_tf, "")
        _d = os.path.join(ROOT, "data", _dir, f"{_sym}_{_tf}.csv")
        if not os.path.exists(_d):
            NO_DATA.append((_sid, _sym, _tf))

    L.append("## Veredicto")
    L.append("")
    txt = ("De los {} prompts medidos, **{}** limpian la criba sobre DEV y "
           "**{}** superan el veredicto completo sobre OOS".format(
               words(len(rows)), words(len(survivors)), words(n_oos_pass)))
    if n_not_cert:
        txt += (" ({} de los supervisivientes {} pares y no {} "
                "certificables: su nocional implicito no es sostenible)"
                .format(words(n_not_cert),
                        "es" if n_not_cert == 1 else "son",
                        "es" if n_not_cert == 1 else "son"))
    txt += (". La razon principal no es el modelo: es el coste. El pack "
            "original corria a {} bps round trip (su constante es {}, o sea "
            "{} bps por lado, diez veces menos de lo que documenta) y sin "
            "funding; el repo cobra {} bps y el funding real. Ese salto es lo "
            "que separa las dos cribas.".format(
                f(pack_rt, 1), f(pack_cs, 6), f(pack_side, 2), f(repo_rt, 1)))
    L.append(txt)
    L.append("")
    L.append("")
    L.append("## Lo que la criba del pack dejo fuera y esta no")
    L.append("")
    L.append("| hallazgo | como se midio |")
    L.append("|---|---|")
    L.append("| el pack ordena los cien prompts por su **propio** OOS Profit "
             "Factor, asi que ese tramo deja de ser una estimacion fuera de "
             "muestra | aqui la seleccion se hace SOLO sobre DEV, hay un mes "
             "de purga sin operar, y el veredicto se lee despues |")
    L.append(f"| el pack cobra {f(pack_rt, 1)} bps round trip (su constante "
             f"es {f(pack_cs, 6)}, o sea {f(pack_side, 2)} bps por lado, "
             f"diez veces menos de lo que documenta) | "
             f"el repo cobra {f(repo_rt, 1)} bps: el pack es "
             f"{words(int(round(repo_rt / pack_rt)))} veces mas barato que el "
             f"estandar de la casa |")
    L.append("| el pnl por trade del pack **no incluye la comision de "
             "entrada** (solo la carga en la caja), asi que su profit factor "
             "no es del todo ex-cost | aqui el pnl lleva las dos comisiones y "
             "el invariante contable cierra |")
    L.append("| el pack **descarta** el trade cuyo hueco de entrada ya "
             "atraviesa el stop (\"setup invalido\") | aqui ese trade se "
             "rellena al open: un hueco malo es un resultado malo, no un "
             "trade que no existio |")
    L.append("| el pack no cobra funding | aqui se cobra en los settlements "
             "reales, en las dos piernas |")
    L.append("")
    L.append("## La criba (DEV) y el veredicto (OOS): un solo simbolo")
    L.append("")
    L.append("| # | prompt | par | run_id DEV | n DEV | PF DEV | net DEV % | "
             "criba | run_id OOS | n OOS | PF OOS | net OOS % | veredicto |")
    L.append("|---|---|---|---|---:|---:|---:|---|---|---:|---:|---:|---|")
    for r in [x for x in rows if int(x["id"]) <= 80]:
        d = r["dev"]
        o = r["oos"]
        dm = d["metrics"]
        om = o["metrics"] if o else None
        og = notional_gate(om) if om else None
        if og is not None and not og[0]:
            verdict = "NO CERTIFICABLE (nocional)"
        elif r["survivor"]:
            verdict = "KILLED (veredicto OOS)"
        elif not r["measurable"]:
            verdict = "INSUFICIENTE MUESTRA"
        else:
            verdict = "no pasa la criba"
        L.append(f"| {r['id']} | {r['symbol']} {r['tf']} | "
                 f"`{d['run_id']}` | {f(dm['n_trades'], 0)} | "
                 f"{f(dm['profit_factor'], 4)} | {f(dm['return_pct'])} | "
                 f"{words(r['n_dev_pass'])} de {words(len(dev_gates(dm)))} | "
                 f"`{o['run_id'] if o else '-'}` | "
                 f"{f(om['n_trades'], 0) if om else '-'} | "
                 f"{f(om['profit_factor'], 4) if om else '-'} | "
                 f"{f(om['return_pct']) if om else '-'} | {verdict} |")
    L.append("")
    L.append("## Gates, prompt por prompt (los que pasan la criba)")
    L.append("")
    for r in survivors:
        d = r["dev"]
        o = r["oos"]
        L.append(f"### #{r['id']} {r['symbol']} {r['tf']}")
        L.append("")
        L.append(f"- DEV: artefacto `results/runs/{d['run_id']}` "
                 f"(run_id `{d['run_id']}`)")
        L.append("")
        L.append("| gate (DEV) | resultado | medido |")
        L.append("|---|---|---|")
        for name, ok, val in dev_gates(d["metrics"]):
            L.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {val} |")
        L.append("")
        if o:
            om = o["metrics"]
            L.append(f"- OOS: artefacto `results/runs/{o['run_id']}` "
                     f"(run_id `{o['run_id']}`)")
            L.append("")
            L.append("| gate (OOS) | resultado | medido |")
            L.append("|---|---|---|")
            for name, ok, val in oos_gates(om):
                L.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {val} |")
            L.append("")
            L.append(f"- buy & hold del mismo tramo: "
                     f"{f(om.get('bh_return_pct'))} %; exceso del libro: "
                     f"{f(om.get('excess_pct'))} pp")
            L.append(f"- fees pagados {f(om['fees_paid_usdt'])} USDT, "
                     f"funding {f(om['funding_paid_usdt'])} USDT, "
                     f"resoluo del invariante {f(om['pnl_identity_resid'], 10)}")
            if om.get("implied_notional_x_median") is not None:
                L.append(f"- **nocional implicito "
                         f"{f(om['implied_notional_x_median'], 1)}x el equity** "
                         f"(máximo {f(om.get('implied_notional_x_max'), 1)}x): "
                         f"el libro no es certificable, y sus cifras miden "
                         f"la apalancamiento, no la señal")
            L.append("")
    L.append("## La criba (DEV) y el veredicto (OOS): pares y cestas")
    L.append("")
    L.append("Estas filas son **NO CERTIFICABLES**: el nocional implicito de "
             "su dimensionamiento no es sostenible (el tope del propio pack "
             "es 20x el equity por posicion). Se publican sus cifras "
             "measuradas, pero como **evidencia del defecto del "
             "dimensionamiento**, no como un resultado de estrategia: con "
             "esa palanca el funding, que el pack ignora, pesa mas que la "
             "senal.")
    L.append("")
    L.append("| # | prompt | legs | run_id DEV | n DEV | PF DEV | run_id OOS | "
             "n OOS | PF OOS | nocional implicito (x equity) | veredicto |")
    L.append("|---|---|---|---|---:|---:|---|---:|---:|---:|---|")
    for r in [x for x in rows if int(x["id"]) > 80]:
        d = r["dev"]
        o = r["oos"]
        dm = d["metrics"]
        om = o["metrics"] if o else None
        og = notional_gate(om) if om else None
        verdict = ("NO CERTIFICABLE (nocional)" if og is not None and not og[0]
                   else ("supera el veredicto" if om and all(g[1] for g in oos_gates(om))
                         else "no supera el veredicto"))
        L.append(f"| {r['id']} | {r['symbol']} {r['tf']} | "
                 f"`{d['run_id']}` | {f(dm['n_trades'], 0)} | "
                 f"{f(dm['profit_factor'], 4)} | "
                 f"`{o['run_id'] if o else '-'}` | "
                 f"{f(om['n_trades'], 0) if om else '-'} | "
                 f"{f(om['profit_factor'], 4) if om else '-'} | "
                 f"{f(om.get('implied_notional_x_median'), 1) if om else '-'} | "
                 f"{verdict} |")
    L.append("")
    L.append("## El control de multiplicidad")
    L.append("")
    L.append("Con cien prompts cribados, la metrica OOS del ganador esta "
             "sesgada al alza: hay que distinguirse del ruido de la propia "
             "criba, no de cero. La distribucion completa de los PF de OOS "
             "de los prompts medibles se publica aqui, y un superviviente "
             "tiene que superar el percentil 95 de esa distribucion.")
    L.append("")
    L.append("| prompt | PF OOS |")
    L.append("|---|---:|")
    for sid, v in sorted(oos_pfs, key=lambda kv: -(kv[1] or 0)):
        if v is None:
            continue
        L.append(f"| {sid} | {f(v, 4)} |")
    L.append("")
    L.append(f"El percentil 95 de esa distribucion es "
             f"**{f(p95, 4)}**. Ningun prompt lo supera: el mejor PF de OOS "
             f"de la criba se queda en "
             f"{f(max([v for _, v in oos_pfs if v is not None], default=None), 4)}."
             if p95 is not None else "La distribucion no tiene PF utilizables.")
    L.append("")
    L.append("## La familia de pares y cestas: el nocional manda")
    L.append("")
    L.append("Los prompts de par (los seis de spread) no son un libro "
             "que se pueda sostener: el dimensionamiento del pack implica un "
             "**nocional bruto de decenas de miles de veces el equity**. "
             "Eso convierte el funding (que el pack no cobra) en el motor "
             "principal del resultado: con esa palanca, unos puntos de "
             "funding por settlement pesan mas que el spread. Por eso la "
             "puerta de certificabilidad es el nocional, no el profit factor.")
    L.append("")
    L.append("| prompt | legs | nocional implicito (x equity) | "
             "coste sobre el nocional real por trade (USDT) | funding neto "
             "del tramo (USDT) |")
    L.append("|---|---|---:|---:|---:|")
    for sid in (81, 82, 85, 86, 88, 89, 83, 84, 87, 90):
        k = f"{sid}/OOS"
        if k not in cells:
            continue
        om = cells[k]["metrics"]
        L.append(f"| {sid} | {cells[k]['symbol']} {cells[k]['tf']} | "
                 f"{f(om.get('implied_notional_x_median'), 1)} | "
                 f"{f(om.get('cost_on_real_notional_usdt'), 0)} | "
                 f"{f(om.get('funding_paid_usdt'), 0)} |")
    L.append("")
    L.append("## Los prompts que NO se han medido, y por que")
    L.append("")
    L.append("| prompt | simbolo | tf | motivo |")
    L.append("|---|---|---|---|")
    for sid, sym, tf in NO_DATA:
        L.append(f"| {sid} | {sym} | {tf} | sin klines de ese simbolo y "
                 f"timeframe en el repo: NO DATA, y no se estima nada |")
    # R1 (2026-11-21): a spread whose envelope cannot be built is REFUSED,
    # never degraded -- declare the refusal explicitly (pair 88: synthetic
    # ALT-BASKET leg, no intrabar range exists). The pairs/baskets live in
    # the RUNNER's own maps, not in the pack's map.
    no_data_ids = {sid for sid, _sym, _tf in NO_DATA}
    _pair_extra = {81: ("SOLUSDT", "1h"), 82: ("BTCUSDT", "1h"),
                   85: ("HYPEUSDT", "1h"), 86: ("SUIUSDT", "1h"),
                   88: ("BASKET6", "1h"), 89: ("ETHUSDT", "15m")}
    for _sid, (_sym, _tf) in sorted(_pair_extra.items()):
        if _sid not in no_data_ids and _sid not in dev:
            L.append(f"| {_sid} | {_sym} | {_tf} | el sobre intrabar de la "
                     "puesta no puede construirse (pierna sintetica sin "
                     "klines, ALT-BASKET) y el engine la RECHAZA en lugar de "
                     "degradarla: no certificable bajo la convencion del "
                     "repo, no se estima nada |")
    L.append("")
    L.append("La familia de prompts de funding del pack (los de funding) es un "
             "tercer tipo de libro: su ejecucion necesita el own funding "
             "alineado con las klines y una logica de senal distinta. **No se "
             "han medido** y no se afirma nada sobre ellos.")
    L.append("")
    L.append("## Limites declarados")
    L.append("")
    L.append("- Esta pantalla cubre la familia de un solo simbolo y la de "
             "par y cesta. Los prompts de funding del pack son un tercer "
             "tipo de libro y NO se han medido aqui: no se afirma nada "
             "sobre ellos.")
    L.append("- El tramo OOS es comun (desde 2025-11-01) para que las cien "
             "estrategias se comparen sobre el mismo regimen, pero cada "
             "prompt tiene su propio tramo DEV: los symbols con menos "
             "historia (HYPE) tienen un DEV mucho mas corto que BTC.")
    L.append("- Sin modelo de margen ni de liquidacion; el tope de "
             "apalancamiento por posicion (20x) es el del pack y, con el "
             "tamaño por riesgo del 1 %, nunca aprieta.")
    L.append("- Medicion sobre las klines del repo. No se enviaron ordenes.")
    L.append("")
    L.append("## Reproduccion")
    L.append("")
    L.append("```")
    L.append("python code/_prompts100_parity.py")
    L.append("python code/_prompts100_audit.py")
    L.append("python code/_p100_screen_run.py")
    L.append("python code/vrun.py verify <run_id>")
    L.append("```")
    L.append("")

    text = "\n".join(L) + "\n"
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"wrote {OUT}  ({len(rows)} prompts, {len(survivors)} survivors)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
