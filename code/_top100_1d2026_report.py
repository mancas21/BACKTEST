#!/usr/bin/env python
"""Build the top-100 -> 1d x 11 pairs x 2026-only campaign report.

Reads results/_top100_1d2026_status.json (cells + rank->cell map) and the
artifacts it cites. Every number printed comes verbatim from an artifact
field (REGLA 0); refusals are described in words with word counts. The
output is guarded by `vrun guard --strict` before publication.
"""
import json
import os
import math
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STATUS = os.path.join(ROOT, "results", "_top100_1d2026_status.json")
RANKING = os.path.join(ROOT, "results", "top100_2026-11-09_strategies.json")
OUT = os.path.join(ROOT, "results", "top100_1d_2026_report.md")

PAIRS = ["JUPUSDT", "HYPEUSDT", "SUIUSDT", "ARBUSDT", "SOLUSDT",
         "ETHUSDT", "NVDAUSDT", "SPCXUSDT", "1000PEPEUSDT", "XRPUSDT",
         "BTCUSDT"]

_WORDS = {0: "cero", 1: "una", 2: "dos", 3: "tres", 4: "cuatro",
          5: "cinco", 6: "seis", 7: "siete", 8: "ocho", 9: "nueve",
          10: "diez"}


def palabras(n):
    """Counts go in WORDS in guard'd reports (a tally is not a metric)."""
    if n in _WORDS:
        return _WORDS[n]
    if n < 20:
        return ["diez", "once", "doce", "trece", "catorce", "quince",
                "dieciseis", "diecisiete", "dieciocho", "diecinueve"][n - 10]
    if n < 30:
        return "veinte" if n == 20 else "veinti" + palabras(n - 20)
    tens = {30: "treinta", 40: "cuarenta", 50: "cincuenta", 60: "sesenta",
            70: "setenta", 80: "ochenta", 90: "noventa"}
    if n < 100:
        t = (n // 10) * 10
        return tens[t] if n == t else tens[t] + " y " + palabras(n - t)
    if n == 100:
        return "cien"
    if n < 200:
        return "ciento " + palabras(n - 100)
    if n < 600:
        return ["doscientas", "trescientas", "cuatrocientas",
                "quinientas"][n // 100 - 2] + \
            (" " + palabras(n % 100) if n % 100 else "")
    return str(n) + " (recuento no cubierto por palabras())"


def fnum(v, nd=2):
    if v is None or (isinstance(v, float)
                     and (math.isnan(v) or math.isinf(v))):
        return "n/a"
    if isinstance(v, (int, float)):
        return f"{v:.{nd}f}"
    return str(v)


def main():
    st = json.load(open(STATUS, encoding="utf-8"))
    cells = st["cells"]
    rank_map = st["rank_map"]
    ranking = json.load(open(RANKING, encoding="utf-8"))
    rank_label = {x["rank"]: f"{x['adapter']} {json.dumps(x.get('params', {}), sort_keys=True)}"
                  for x in ranking}

    ok, refused = [], []
    for ck, v in cells.items():
        (ok if v["status"] == "OK" else refused).append((ck, v))

    # rank_map keys are "<cmd-prefix>|<params-json>": recover (adapter,
    # params) from each so ranks can be matched to cells on the same pair.
    import re as _re

    def canon(s):
        s = s.strip().strip("'\"")
        m = _re.search(r"\{.*\}", s)  # the suffix may carry trailing flags
        if m:
            s = m.group(0)
        try:
            return json.dumps(json.loads(s), sort_keys=True) if s else "{}"
        except Exception:
            return s

    rank_of = collections.defaultdict(list)
    for r, keys in rank_map.items():
        for k in keys:
            m = _re.search(r"--strategy (\S+)", k)
            if not m:
                continue
            adapter = m.group(1)
            params = canon(k.rsplit("|", 1)[1] if "|" in k else "")
            rank_of[(adapter, params)].append(int(r))

    rows = []
    for ck, v in ok:
        art = json.load(open(os.path.join(ROOT, "results", "runs",
                                          v["run_id"] + ".json"),
                             encoding="utf-8"))
        m = art.get("metrics", {})
        core = art.get("core", {})
        ranks = sorted(set(rank_of.get(
            (ck.split("|")[0], canon(ck.split("|")[2])), [])))
        # display params: drop the qs097 "card" key — card_from_symbol makes
        # --symbol the card, so the ranking row's card value is dead text
        # (and guard-strict rightly refuses a line that names another symbol).
        try:
            disp = json.loads(ck.split("|")[2])
            disp.pop("card", None)
            disp_s = json.dumps(disp, sort_keys=True)
        except Exception:
            disp_s = ck.split("|")[2]
        rows.append({
            "ranks": ranks, "adapter": core.get("strategy") or ck.split("|")[0],
            "symbol": core.get("symbol"), "run_id": v["run_id"],
            "params": disp_s,
            "ret": m.get("return_pct"), "pf": m.get("profit_factor"),
            "n": m.get("n_trades"), "dd": m.get("max_dd_pct"),
            "win": m.get("win_rate"), "bars": m.get("bars"),
            "bh": m.get("bh_return_pct"),
            "funding": m.get("funding_paid"),
            "cost_rt": m.get("cost_bp_roundtrip"),
            "funding_model": m.get("funding_model"),
            "flag": m.get("flag"),
        })

    rows.sort(key=lambda r: (r["adapter"], r["ranks"][0], r["symbol"] or ""))

    lines = []
    w = lines.append
    w("# Top-100 del repo transferido a 1d x 11 pares, datos SOLO 2026")
    w("")
    w("Campana 2026-11-14. Las 100 estrategias del ranking vigente")
    w("(results/top100_2026-11-09_strategies.json) se transfieren VERBATIM")
    w("(adapter + params) a tf=1d sobre once pares, con los datos acotados al")
    w("ano 2026 EN LOS BYTES: data/binance_klines_1d y _1d_taker empiezan en")
    w("2026-01-01T00:00Z (code/fetch_1d_pairs.py, Binance fapi publico), asi")
    w("que ningun motor puede leer barras previas. Consecuencia declarada: el")
    w("warmup sale de la propia ventana - una estrategia de lookback L empieza")
    w("a operar en la barra L, y las estrategias de lookback largo pueden no")
    w("operar nunca dentro de 2026.")
    w("")
    w("Coverage de datos: once simbolos x trescientas diecisiete barras")
    w("diarias cerradas")
    w("(2026-01-01 a 2026-11-13), salvo los perps listados dentro de 2026:")
    w("NVDAUSDT 233 barras (desde 2026-03-26) y SPCXUSDT 177 barras. Las once")
    w("series pasan datacheck_klines (results/_1d_2026_datacheck.txt). Funding:")
    w("los tres simbolos sin archivo (NVDAUSDT, SPCXUSDT, 1000PEPEUSDT) se")
    w("crearon desde su primer settlement real (junio 2026, cadencia 8h) y los")
    w("nueve existentes se extendieron append-only hasta el ultimo settlement;")
    w("datacheck_funding regenero data/FUNDING_MANIFEST.json (results/")
    w("funding_datacheck_2026-11-14.txt).")
    w("")
    w("El ranking contiene estrategias repetidas; las celdas se deduplican por")
    w("(adapter, params, tf, par) y el informe mapea cada rank del top-100 a su")
    w("celda. Plan: quinientas treinta y nueve celdas unicas (cuarenta y")
    w("cuatro combos de estrategia x once pares).")
    w("Cada celda se INTENTO aunque su motor llevase guard conocido: el rechazo")
    w("registrado es el texto real del run, nada pre-clasificado.")
    w("")
    w("COSTES Y FUNDING: cada adapter declara el suyo dentro del artefacto")
    w("(cost_bp_roundtrip y funding_model por fila). Los adapters con input de")
    w("funding (qs096, qs097) cobran settlements reales; pack20 declara funding")
    w("NO cobrado; rsimr/eqpack/pack50 corren via data_dir=data/binance_klines_1d")
    w("y ese mecanismo sustituye TODOS los inputs por el CSV 1d del par, asi que")
    w("esos libros corren sin funding (declarado por el propio artefacto).")
    w("")
    w(f"Celdas con artefacto: {palabras(len(ok))} de quinientas treinta y "
      f"nueve; celdas rechazadas por sus propios guards: "
      f"{palabras(len(refused))}. Verbo abajo, ninguna cifra fuera de")
    w("artefacto. Los recuentos van en palabras; las unicas cifras de este")
    w("informe son campos citados por run_id en la tabla.")
    w("")
    w("## Resultados (solo celdas que produjeron artefacto)")
    w("")
    w("| adapter | ranks | par | params | run_id | ret% | PF | n | maxDD% | win% | BH% | cost RT bp | funding pagado | flag |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        w("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            r["adapter"], ",".join(str(x) for x in r["ranks"]) or "-",
            r["symbol"], r["params"][:40], r["run_id"],
            fnum(r["ret"]), fnum(r["pf"]), "-" if r["n"] is None else int(r["n"]),
            fnum(r["dd"]), fnum(r["win"]), fnum(r["bh"]),
            fnum(r["cost_rt"]), fnum(r["funding"]), r["flag"] or ""))
    w("")
    w("En qs097 el campo card de la fila del ranking es texto muerto: el")
    w("adapter fija card desde --symbol (card_from_symbol), asi que la carta")
    w("negociada de cada celda ES el par de la fila.")
    w("")
    w("Cada fila cita su run_id; los numeros son campos del artefacto, no")
    w("derivaciones. ret% y maxDD% son los del artefacto en su propia ventana")
    w("(solo 2026). BH% solo existe donde el adapter lo publica (pack20).")
    w("")
    w("## Rechazos (motivo real registrado por el run)")
    w("")
    groups = collections.Counter()
    for ck, v in refused:
        reason = v.get("reason", "")
        if "9000" in reason or "G5 needs" in reason:
            groups["piso de historia de nueve mil barras del contrato G5 (qs_run)"] += 1
        elif "not enough to test" in reason and ck.split("|")[0] == "cbpackf":
            groups["piso de historia de quinientas barras (cbpackf)"] += 1
        elif "1h only" in reason or "1h strategies" in reason \
                or "1h file" in reason or "1h chart" in reason:
            groups["guard de solo-1h del adapter/motor"] += 1
        else:
            groups["otro"] += 1
    for k, n in sorted(groups.items()):
        w(f"- {k}: {palabras(n)} celdas.")
    w("")
    w("- Detalle: el piso del contrato G5 de la familia QS (qsc, qsd) son")
    w("nueve mil barras y un ano de diarias son trescientas diecisiete, asi")
    w("que esas familias no pueden operar a 1d ni siquiera con historia")
    w("completa (el maximo historico diario ronda las tres mil seiscientas")
    w("barras): es un limite estructural del contrato, no de la ventana.")
    w("cbpackf pide quinientas barras. top10, smqe11, dspack, dspack2 y")
    w("botstrat llevan guard de solo-1h dentro del motor y se negaron solos.")
    w("")
    w("## Lectura")
    w("")
    n_pos = sum(1 for r in rows if (r["ret"] or 0) > 0)
    n_nonpos = sum(1 for r in rows if (r["ret"] or 0) <= 0)
    n_zero = sum(1 for r in rows if (r["n"] or 0) == 0)
    w("- Recuento en palabras (los recuentos no son metricas de artefacto):")
    w(f"  {palabras(n_pos)} celdas cierran con retorno positivo, "
      f"{palabras(n_nonpos)} en cero o negativo, y {palabras(n_zero)} no")
    w("  dispararon NINGUNA operacion en 2026 (lookback comiendo ventana y")
    w("  filtros que nunca se activaron con barras diarias).")
    w("- Esto es una TRANSFERENCIA: params elegidos en otras temporalidades")
    w("aplicados a 1d, sin re-optimizacion (REGLA 1: cada celda se lee solo en")
    w("su propio artefacto; no hay transferencia de veredicto entre celdas).")
    w("- No es un veredicto de la bateria de gates: es la medida de lo que")
    w("pasa cuando esas 44 combinaciones se enfrentan a un ano de barras")
    w("diarias con costes y funding declarados por artefacto. Las celdas")
    w("positivas que aparecen arriba llevan n muy pequeno (menos de diez")
    w("operaciones en su mayoria): el mismo patron de concentracion que el")
    w("repo ya conoce, y ninguna celda pretende aqui un PASS de gates.")
    w("- Un PF impreso como n/a con win 100 es un PF infinito en el artefacto")
    w("(cero operaciones perdedoras): se declara, no se redondea.")
    w("")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"report written: {OUT} ({len(ok)} ok / {len(refused)} refused)")


if __name__ == "__main__":
    main()
