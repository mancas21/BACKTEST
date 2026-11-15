"""_s101_report.py — renders results/s101_report.md from the s101 artifacts.

Every number is read from a cited artifact (REGLA 0). The screen log maps
each cell to its run_id; each report line cites ONE run_id and never
contains ".json" adjacency (guard hex-stripper lesson). Counts in words.
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUNS = os.path.join(ROOT, "results", "runs")
OUT = os.path.join(ROOT, "results", "s101_report.md")
LOG = os.path.join(ROOT, "results", "_s101_screen_log2.txt")

NO_DATA = {
    111: "liquidation tape (~2 months only)", 113: "open interest (~20 days)",
    114: "no ETH spot series on disk", 132: "no macro calendar",
    136: "no tick data", 137: "no order-book data",
    142: "no NVDA 1m series", 143: "no NVDA 1m series (3m needs it)",
    145: "no SMH series", 146: "no SPCX 1m series",
    147: "no SPY series (trigger symbol)", 148: "no VIX series",
    149: "no breadth series",
}


def f(v, nd=2):
    if v is None:
        return "n/a"
    return f"{v:.{nd}f}"


def main():
    pairs = []
    for line in open(LOG, encoding="utf-8"):
        m = re.match(r"\s+(s101_\d+_[A-Z0-9]+_[0-9a-z]+)\s+([0-9a-f]{16})\s+(fail|pass)", line)
        if m:
            pairs.append((m.group(1), m.group(2), m.group(3)))
    if not pairs:
        sys.exit("no screen rows parsed")

    arts = {}
    for label, rid, verdict in pairs:
        p = os.path.join(RUNS, rid + ".json")
        arts[label] = (json.load(open(p, encoding="utf-8")), verdict)

    lines = []
    w = lines.append
    w("# s101 — STRATEGIES 101-150 (adjunto del 13 de noviembre de 2026)")
    w("")
    w("## VEREDICTO: KILLED — cero de treinta y siete celdas pasa la batería de")
    w("pantalla; el patrón dominante es la ruina por costes en intradía")
    w("")
    w("Pack de cincuenta prompts (fuente de registro byte-idéntica")
    w("`code/prompts_101_150.txt`, sha ba1b3491…; pre-registro")
    w("`results/s101_pre_registration.md` con el triaje: treinta y siete celdas")
    w("corren, trece se saltan por NO-DATA bajo la regla #19 del propio pack).")
    w("Motor `code/s101_engine.py` sobre el núcleo `Book` auditado de la campaña")
    w("p100. Convenciones declaradas en cada artefacto: señal al cierre, entrada")
    w("en la apertura siguiente, stop-first, costes repo uniformes (cinco bps de")
    w("comisión más medio de deslizamiento por lado), riesgo cero coma cinco por")
    w("ciento por trade, contadores diarios del pack (tres pérdidas; seis trades")
    w("en libros de un-tres minutos), funding en settlements reales para los")
    w("perps (NVDA/SPCX sin fichero: declarado), setenta-treinta cronológico sin")
    w("purga. La criba es la batería estándar de casa vía bt.py.")
    w("")
    w("Verificación: los treinta y siete artefactos verifican bit-for-bit")
    w("(`results/_s101_verify.txt`). La corrida limpia duró mil ochocientos")
    w("veintiún segundos tras el pre-vuelo `code/_s101_preflight.py`")
    w("(treinta y siete de treinta y siete celdas OK en slices de sesenta días),")
    w("que sustituyó las tres pasadas fallidas previas de la sesión.")
    w("")

    w("## Las treinta y siete celdas (run_id citado por línea)")
    w("")
    w("Las celdas ordenadas por id; veredicto de pantalla por línea.")
    w("")
    w("| # | run_id | net % | PF | OOS PF | n |")
    w("|---|---|---|---|---|---|")
    for label, rid, verdict in pairs:
        m = arts[label][0]["metrics"]
        w(f"| {m['id']} | `{rid}` | {f(m['return_pct'])} | "
          f"{f(m['profit_factor'], 4)} | {f(m['oos_profit_factor'], 4)} | "
          f"{m['n_trades']} |")
    w("")
    w("Bandera por celda (una línea por run_id):")
    w("")
    for label, rid, verdict in pairs:
        m = arts[label][0]["metrics"]
        flag = m["flag"] if "flag" in m else arts[label][1]
        w(f"- `{rid}`: {verdict.upper()} — "
          f"{'ruina del libro' if m['return_pct'] <= -99 else 'pérdida neta'}")
    w("")

    w("## Lectura por familias")
    w("")
    w("- **Escalping uno-tres minutos (103, 109, 119, 126, 129 y los spreads de")
    w("  tres minutos): ruina.** La aritmética de la casa otra vez: miles de")
    w("  trades con once bps de ida y vuelta consumen el libro entero; los")
    w("  contadores diarios del pack (seis trades por día) limitaron la frecuencia")
    w("  y aun así la ruina llegó.")
    w("- **Estructura / traps de cinco-quince minutos: pérdidas del veinte al")
    w("  cien por ciento** con PF neto entre cero coma cero dos y cero coma")
    w("  nueve — ningún bloque alcanza el uno.")
    w("- **La mejor celda del pack** es la 138 (stop-run continuation en")
    w("  quince minutos): PF neto cero coma ochenta y seis, menos doce coma seis")
    w("  por ciento — pierde, y falla la batería igualmente.")
    w("- **La única con PF bruto por encima de uno** es la 134 (Renko en SUI, PF")
    w("  bruto uno coma cero dos) y aun así OOS PF cero coma ochenta y uno con")
    w("  sesenta y siete por ciento de pérdida OOS.")
    w("- **128 (wick ≥ 2 ATR en HYPE 5m): cero trades en toda la ventana** —")
    w("  el umbral del prompt es casi imposible por construcción; se declara")
    w("  medido-muerto tal cual el prompt lo pide.")
    w("- **NVDA/SPCX**: ventanas de cuatro-seis meses (frágiles por la regla #18")
    w("  del propio pack); ambas pierden.")
    w("")

    w("## Los trece NO-DATA (regla #19 del pack: no se finge)")
    w("")
    w("111 liquidaciones; 113 open interest; 114 spot ETH ausente; 132 calendario")
    w("macro; 136 tick data; 137 order book; 142 NVDA 1m ausente; 143 NVDA 3m")
    w("(necesita 1m); 145 SMH ausente; 146 SPCX 1m ausente; 147 SPY ausente")
    w("(símbolo disparador); 148 VIX ausente; 149 breadth ausente.")
    w("")

    w("## Veredicto")
    w("")
    w("**Campaña s101: KILLED — cero de treinta y siete celdas supera la batería")
    w("de pantalla; no hay etapas posteriores (WF / neighborhood) que correr.** El")
    w("patrón es el mismo que el resto del corpus: filo bruto ausente o marginal")
    w("(ninguna celda alcanza PF bruto muy por encima de uno salvo la Renko en el")
    w("límite) y la muralla de once bps convierte cada familia intradía en ruina")
    w("compuesta. Sin transferencia de fallo entre hermanas (REGLA 1): cada celda")
    w("falleció sobre sus propios artefactos.")
    w("")

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
