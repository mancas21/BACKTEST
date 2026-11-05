
import sys, numpy as np
sys.path.insert(0, r"C:\Users\Lenovo\Documents\backtest-system\code")
from cbot.config import BotConfig
from cbot.data import make_world
from cbot.suite import run_suite
df = make_world("flow", a=1.0, n=30000)
imb = (2.0*df.taker_buy_base/df.volume - 1.0).to_numpy()
fwd = np.log(df.close.shift(-3)/df.close).to_numpy()
m = np.isfinite(imb)&np.isfinite(fwd)
print("corr(imb_t, fwd_ret_3) = %+.4f" % np.corrcoef(imb[m], fwd[m])[0,1])
res = run_suite(df, BotConfig(), n_perm=2)
print(res.sort_values("gross_t", ascending=False)[["id","strategy","gross_t","net_t","trades","PASS"]].head(3).to_string(index=False))
print()
print("=== FULL KNOWN-ANSWER MATRIX (a=1.0) ===")
fam={"momentum":{"S01","S09"},"meanrev":{"S02","S09"},"flow":{"S05","S06"},
     "season":{"S10"},"regime_ac":{"S09"},"null":set()}
ok=0
for w,exp in fam.items():
    d=make_world(w,a=1.0,n=30000); R=run_suite(d,BotConfig(),n_perm=2)
    r=R.sort_values("gross_t",ascending=False).iloc[0]
    got = (r["gross_t"]>3) and ((r["id"] in exp) if exp else False)
    if not exp: got = R.gross_t.abs().max()<5
    ok+=bool(got)
    print(f"  {w:<11} top: {r['id']} {r['strategy'][:26]:<28} gross_t {r['gross_t']:>+7.1f}  {'OK' if got else 'MISS'}")
print(f"  {ok}/{len(fam)} behave correctly")
