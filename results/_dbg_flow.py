
import sys, numpy as np
sys.path.insert(0, r"C:\Users\Lenovo\Documents\backtest-system\code")
from cbot.config import BotConfig
from cbot.data import make_world
from cbot.features import build_features
from cbot.strategies import strategy_frame
from cbot.suite import run_suite
df = make_world("flow", a=1.0, n=30000)
# verify the planted link exists in the data before blaming the engine
imb = (2.0*df.taker_buy_base/df.volume - 1.0).to_numpy()
fwd = np.log(df.close.shift(-3)/df.close).to_numpy()
m = np.isfinite(imb) & np.isfinite(fwd)
print("corr(imb_t, fwd_ret_t) = %+.4f   (must be clearly positive)" % np.corrcoef(imb[m], fwd[m])[0,1])
res = run_suite(df, BotConfig(), n_perm=2)
print(res.sort_values("gross_t", ascending=False)[["id","strategy","gross_t","net_t","trades","PASS"]].head(4).to_string(index=False))
