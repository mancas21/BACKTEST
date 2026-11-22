import json
a = json.load(open(r"results/runs/b90f59d052a85790.json"))
m = a["metrics"]
for k in ["sharpe","sortino","return_pct","cagr_pct","max_dd_pct","funding_pct",
          "price_pct","cost_pct","drag_pp","rank_ic_mean","turnover_per_year",
          "sharpe_zero","return_zero_pct","pnl_identity_resid","gate_g4_costs_bind",
          "gate_g5_funding_positive","gate_g6_traded","gate_g7_identity"]:
    print(f"{k}: {m[k]}")
