
import sys, numpy as np
sys.path.insert(0, r"C:\Users\Lenovo\Documents\backtest-system\code")
from cbot.config import BotConfig
from cbot.data import make_world
from cbot.suite import run_suite
# "expected" accepts the RIGHT FAMILY: these strategies feed FEATURES to a
# learned model, which can invert a sign, so a momentum world may legitimately
# be detected by S09 (autocorrelation) as well as S01.
fam = {"momentum":{"S01","S09"},"meanrev":{"S02","S09"},"flow":{"S05","S06"},
       "season":{"S10"},"volshock":{"S08"},"regime_ac":{"S09"},"null":set()}
print("=== KNOWN-ANSWER VALIDATION (a=1.0) ===")
print(f"{'world':<12}{'top by gross_t':<22}{'gross_t':>9}{'ok':>5}{'passes':>8}{'price range':>14}")
print("-"*72)
ok=0
for w,exp in fam.items():
    df = make_world(w, a=1.0, n=30000)
    res = run_suite(df, BotConfig(), n_perm=2)
    r = res.sort_values("gross_t", ascending=False).iloc[0]
    good = (r["id"] in exp) if exp else (res.gross_t.abs().max() < 5)
    ok += bool(good)
    rng_ = df.close.max()/df.close.min()
    print(f"{w:<12}{(r['id']+' '+r['strategy'][:14]):<22}{r['gross_t']:>+9.1f}"
          f"{str(bool(good)):>5}{int(res.PASS.sum()):>8}{rng_:>13.1f}x")
print("-"*72); print(f"{ok}/7 worlds behave correctly")
