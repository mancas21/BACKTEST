"""
RETIRADO (2026-11-16) — este fichero ya NO despliega ni corre nada.

  Que era      : la fuente del bot el lector de estado del bot XRP de una sola pareja
  Donde corria : /home/ubuntu/xrp-paper-bot en el VPS (vps-japan), ya retirado el 2026-11-04
  Que paso     : el bot se borro del VPS (directorios y lineas de cron) el
                  2026-11-16. El material borro esta archivado en el repo,
                  verificado por sha256, en
                  `backups/vps_retired_paper_mp18_20261116T213657Z.tar.gz`
                  (sha256 3f959444a88f5070f0d4716e2f68283605619dea14b8b2ee3d292db5ecf28a56).
  Como queda   : esto es el archivo del repo (append-only, no se borra). No
                  hay ninguna tarea programada ni cron que lo despliegue, y
                  no debe volver a desplegarse: el veredicto de la estrategia
                  que implementa esta en este repo esta en los artefactos, no
                  en un bot desplegado.

Print the XRP paper bot status in one line. Used on the VPS and locally."""
import json
import os
import sys

p = sys.argv[1] if len(sys.argv) > 1 else "xrp_paper_bot_status.json"
if not os.path.exists(p):
    print("NO STATUS FILE at", p)
    raise SystemExit(1)
d = json.load(open(p, encoding="utf-8"))
keys = ["updated_utc", "last_bar", "bars", "equity", "net_from_inception_pct",
        "forward_pnl", "forward_pct", "pf_all_closed", "n_closed", "win_rate_pct",
        "max_dd_pct", "fees_paid", "funding_paid", "funding_prints",
        "NEUTRALITY_avg_abs_delta_pct", "open_lots", "buyhold_pct"]
print(" | ".join(f"{k}={d.get(k)}" for k in keys))
