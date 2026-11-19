# VALIDACIÓN G1–G11 · SPREAD id=85 mid-day-lull mean-reversion

**Par:** HYPEUSDT / SOLUSDT 1h · z-score(100) del log-spread con beta Kalman · entrada |z|>2, salida cruce por 0. Book neutral dollar-neutral, PnL linearizado del spread.

- **Paridad DEV:** OK (re-run n=127, PF=2.6073, net=28.10% vs artefacto n=127.0, PF=2.6073, net=28.10%)
- **n FULL:** 540 · IS PF 2.6073 · OOS PF 3.0997
- **Apalancamiento de exchange (mediana notional/equity): 36.2x** vs cap del book 20x (N-cap). ⚠️ El notional real de las dos patas excede el cap; tradeability cuestionable. G9 usa MAE por-trade (no margen por-pata).
- **n_trials (DSR):** 1486 · policy_hash `0c8bf92d19d30fac` · benchmark = cash (neutral).

## backtest_pass: **False** · failure_modes: ['COST_FAILURE (gross edge exists, net does not clear)']

| Gate | pass | números clave |
|---|---|---|
| G1 | ✅ | pf_net=1.64148, pf_gross=2.66359, expectancy_bps=0.28247, boot_lb_bps=0.15246, zero_losers=False |
| G2 | ✅ | n=540, n_eff=540.0, rho1=0.0, rho_cross=0.0 |
| G3 | ✅ | pf_is=1.61463, pf_oos=1.96863, n_is=384, n_oos=156, purged_at_split=0, folds_pass=5, folds_needed=4 |
| G4 | ✅ | frac_positive=0.88235, worst_bucket=-0.04325, scored=17, buckets=17, notional_scale=36.23288 |
| G5 | ✅ | alpha_ann=1.67842, beta=0.0, alpha_t_hac=3.89965, strategy_return=0.71633, bh_return=0.0, beats_raw_bh=True, book_type=neutral |
| G6 | ✅ | k_removed=27, net_ex_top=0.00205, net_ex_best_month=0.01166, net_ex_best_week=0.01323, net_total=0.01525 |
| G7 | ✅ | pbo=None, pbo_evaluated=False, dsr=1.0, sr=0.16281, sr0=0.05592, T=521, n_eff_trials=1486.0 |
| G8 | ❌ | pf_at_mult=0.99682, mean_bps_at_mult=-0.0018, cost_share=0.54212, breakeven_mult_pf=1.99367, breakeven_rt_bps_pf=0.56674, mean_rt_cost_bps=0.28427, pf_size_aware=0.0 |
| G9 | ✅ | boot_maxdd_p95_mtm=0.10501, boot_maxdd_p95=0.12603, ruin_frac=0.0, mtm_maxdd=0.09141, liquidation_threshold_move=0.045, liquidated_trades=0 |
| G11 | ✅ | gated=False, win_rate=0.60556, payoff=1.06922, breakeven_wr=0.48327, wr_margin_pp=12.22823 |
| G10 | PENDING | status=PENDING (needs forward run + prereg) |

- **Artefacto fuente (run_id):** `b6ebfc6ec584042f`

*Validación con SpreadBook instrumentado en memoria (engine sin modificar). Paridad DEV verificada. Esquema v2 en fracciones del notional de exchange. Datos: `results/candidate_spread_v2.json`.*