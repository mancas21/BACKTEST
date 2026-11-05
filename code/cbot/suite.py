"""Suite de 10 estrategias sobre el MISMO motor, costos, walk-forward y controles + correccion por pruebas multiples.
  python -m cbot.suite --world flow                                    # mundo sintetico con respuesta conocida
  python -m cbot.suite --symbol BTCUSDT --interval 5m --days 180 --cache data/btcusdt_5m.csv.gz   # datos reales de Binance
"""
from __future__ import annotations
import argparse
import math
import os
from dataclasses import replace
from statistics import NormalDist
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .backtest import permutation_control, run_backtest
from .config import BotConfig
from .data import WORLDS, load_or_fetch, make_world
from .features import build_features
from .model import walk_forward
from .report import WHY
from .strategies import REGISTRY, strategy_frame


def t_critical(n_tests: int, alpha: float = 0.05) -> float:
    """Bonferroni unilateral: con 10 estrategias un t de 2 ya no basta."""
    return NormalDist().inv_cdf(1 - alpha / n_tests)


def run_suite(df: pd.DataFrame, cfg: BotConfig, ids: Optional[List[str]] = None, n_perm: int = 5, seed: int = 0) -> pd.DataFrame:
    ids = ids or list(REGISTRY)
    base = build_features(df, cfg)
    gross_cfg = replace(cfg, fee_taker=0.0, slippage=0.0, funding_8h=0.0, min_edge=0.0)
    tcrit = t_critical(len(ids))
    rows = []
    for sid in ids:
        feats, cols = strategy_frame(sid, df, cfg, base)
        p = walk_forward(feats, cfg, cols)
        net = run_backtest(df, cfg, p=p, feats=feats)
        gross = run_backtest(df, gross_cfg, p=p, feats=feats)
        m, c = net.metrics, net.metrics["calibration"]
        perc = float("nan")
        if m["n_trades"] >= 30 and m["t_stat"] > 1.5:                 # permutaciones solo donde hay candidato (ahorra tiempo)
            perc = permutation_control(df, net, cfg, n=n_perm, seed=seed)["percentile"]
        checks = {"t>tcrit": m["t_stat"] > tcrit, "net>0": m["net_return"] > 0, "perm>=90%": perc >= 0.9,
                  "slope": 0.7 <= c["slope"] <= 1.3, "trades>=100": m["n_trades"] >= 100}
        rows.append({"id": sid, "strategy": REGISTRY[sid].name, "AUC": c["auc"], "slope": c["slope"],
                     "gross_edge_bp": m["gross_edge_bp"], "gross_t": gross.metrics["t_stat"], "trades": m["n_trades"],
                     "net_t": m["t_stat"], "avg_net_bp": m.get("avg_net_bp", 0.0), "net_ret": m["net_return"],
                     "max_dd": m.get("max_dd", 0.0), "bh_ret": m["bh_return"], "perm_pct": perc,
                     "PASS": all(checks.values()), "fails": ",".join(k for k, v in checks.items() if not v)})
    out = pd.DataFrame(rows)
    out.attrs["tcrit"] = tcrit
    return out


def render_suite(res: pd.DataFrame, cfg: BotConfig, desc: str) -> str:
    tc = res.attrs["tcrit"]
    r = res.sort_values("net_t", ascending=False)
    hdr = "| id | strategy | AUC | slope | gross edge bp | gross t | trades | net t | net bp/trade | net ret | maxDD | perm | verdict |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    body = "".join(
        f"| {x.id} | {x.strategy} | {x.AUC:.3f} | {x.slope:.2f} | {x.gross_edge_bp:.1f} | {x.gross_t:+.1f} | {x.trades} | {x.net_t:+.1f} | {x.avg_net_bp:+.1f} | "
        f"{x.net_ret:+.1%} | {x.max_dd:.1%} | {'n/a' if math.isnan(x.perm_pct) else f'{x.perm_pct:.0%}'} | "
        f"{'PASS' if x.PASS else 'FAIL: ' + x.fails} |\n" for x in r.itertuples())
    n_pass = int(res.PASS.sum())
    return "\n".join([
        f"# Strategy suite: {cfg.symbol} {cfg.interval_min}m, holding {cfg.horizon_bars} bars", "", f"Data: {desc}",
        f"Costs assumed: taker {cfg.fee_taker:.4%}/side, slippage {cfg.slippage:.4%}/side, funding {cfg.funding_8h:.4%}/8h (VERIFY).",
        f"Multiple testing: {len(res)} strategies tested, so net t must exceed {tc:.2f} (Bonferroni, alpha=0.05), plus net>0, permutation >= 90%, calibration slope 0.7-1.3, >= 100 trades.", "",
        f"**{n_pass} of {len(res)} strategies pass.** " + ("Passing = not discarded; it is NOT proof of profitability. Next: paper trading." if n_pass else "No strategy shows demonstrated edge: do NOT automate."), "",
        hdr + body, "'gross t' = same signals at zero cost (is there any alpha before fees?). A high gross t with a failing net t means costs eat the edge.", "",
        "## WHY THIS COULD STOP WORKING", *[f"{i}. {s}" for i, s in enumerate(WHY, 1)]])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--world", choices=WORLDS, default=None); ap.add_argument("--a", type=float, default=0.2)
    ap.add_argument("--symbol", default="BTCUSDT"); ap.add_argument("--interval", default="5m")
    ap.add_argument("--days", type=int, default=180); ap.add_argument("--cache", default=None)
    ap.add_argument("--n-perm", type=int, default=5); ap.add_argument("--out", default="reports")
    a = ap.parse_args()
    cfg = BotConfig(symbol=a.symbol, interval_min=int(a.interval.rstrip("m")))
    if a.world:
        df, desc, tag = make_world(a.world, a=a.a), f"SYNTHETIC world '{a.world}' (a={a.a})", f"suite_{a.world}"
    else:
        df = load_or_fetch(a.symbol, a.interval, a.days, a.cache)
        desc, tag = f"{a.symbol} {a.interval} Binance futures, {len(df)} bars, {df.index[0]} -> {df.index[-1]}", f"suite_{a.symbol}"
    res = run_suite(df, cfg, n_perm=a.n_perm)
    text = render_suite(res, cfg, desc)
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, tag + ".md")
    open(path, "w", encoding="utf-8").write(text)
    print(text, f"\n\n(saved to {path})")


if __name__ == "__main__":
    main()
