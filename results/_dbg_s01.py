
import sys, numpy as np, pandas as pd
sys.path.insert(0, r"C:\Users\Lenovo\Documents\backtest-system\code")
from cbot.config import BotConfig
from cbot.data import make_world
from cbot.features import build_features
from cbot.strategies import strategy_frame
from cbot.model import walk_forward
from cbot.backtest import run_backtest
from dataclasses import replace

df = make_world("momentum", a=1.0, n=30000)
cfg = BotConfig()
base = build_features(df, cfg)
print("base non-nan:", {c: int(base[c].notna().sum()) for c in base.columns})
feats, cols = strategy_frame("S01", df, cfg, base)
print("S01 cols:", cols)
print("feats non-nan per col:", {c: int(feats[c].notna().sum()) for c in cols})
p = walk_forward(feats, cfg, cols)
print("p non-nan:", int(p.notna().sum()), "of", len(p))
print("p stats on non-nan: min %.4f max %.4f mean %.4f std %.4f" % (
    np.nanmin(p), np.nanmax(p), np.nanmean(p), np.nanstd(p)))
gross_cfg = replace(cfg, fee_taker=0.0, slippage=0.0, funding_8h=0.0, min_edge=0.0)
g = run_backtest(df, gross_cfg, p=p, feats=feats)
print("GROSS metrics:", {k:(round(v,4) if isinstance(v,float) else v) for k,v in g.metrics.items() if k!="calibration"})
n = run_backtest(df, cfg, p=p, feats=feats)
print("NET   metrics:", {k:(round(v,4) if isinstance(v,float) else v) for k,v in n.metrics.items() if k!="calibration"})
print("gross edge bp:", g.metrics["gross_edge_bp"], " n_trades:", g.metrics["n_trades"])
