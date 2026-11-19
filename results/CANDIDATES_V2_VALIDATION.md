# VALIDACIÓN G1–G11 COMPLETA · candidatas robustas

Batería completa (`_gates_v2.evaluate_gates_v2`, policy_hash `0c8bf92d19d30fac`) corrida sobre las candidatas del filtro de robustez de `TOP_OOS_ROBUST.md`. n_trials (DSR) = **1486** (TrialLedger). Esquema por-trade reconstruido desde el Book del repo (gross/cost/funding/MAE), con **paridad verificada** contra el artefacto DEV almacenado.

> `backtest_pass` = G1∧G2∧G3∧G4∧G5∧G6∧G7∧G8∧G9∧G11. G10 (forward) queda PENDING (requiere run forward + pre-registro). G9 exige MAE + max_leverage (fail-closed). Esto es la batería REAL, no el filtro ligero.

| Estrategia | Par/TF | Paridad DEV | n FULL | backtest_pass | Gates fallidos |
|---|---|---|---|---|---|
| mid-day-lull mean-reversion | HYPEUSDT 1h | — | — | SKIPPED | SKIPPED (pair/basket rebalance book: esquema por-periodo requiere instrumentación propia) |
| atr vol breakout | ETHUSDT 1h | — | — | SKIPPED | SKIPPED (pack20 engine needs separate instrumentation) |
| vwap fade | SOLUSDT 15m | — | — | SKIPPED | SKIPPED (pack20 engine needs separate instrumentation) |
| TRIX(15) zero-cross | BTCUSDT 15m | OK | 1067 | NO | G3, G4, G5, G6, G7, G9 |
| triple EMA (8/21/55) pullback | ETHUSDT 1h | OK | 1136 | NO | G1, G3, G4, G5, G6, G7, G9 |
| impulse-bar continuation | ETHUSDT 1h | OK | 755 | NO | G1, G3, G4, G5, G6, G7, G9 |

## Detalle por gate

### TRIX(15) zero-cross · BTCUSDT 15m (id=52)
- **Paridad DEV:** OK (re-run n=877, PF=1.1320, net=393.40% vs artefacto n=877.0, PF=1.1319877572494246, net=393.39507203263196%)
- **n FULL:** 1067 · notional/equity (mediana): 1.32x · IS PF 1.132 · OOS PF 1.0705
- **backtest_pass: False** · failure_modes: []

| Gate | pass | números clave |
|---|---|---|
| G1 | ✅ | pf_net=1.2147, pf_gross=1.4547, expectancy_bps=17.2721, boot_lb_bps=0.8511, zero_losers=False |
| G2 | ✅ | n=1067, n_eff=1067.0, rho1=0.0, rho_cross=0.0 |
| G3 | ❌ | pf_is=1.3394, pf_oos=0.9024, n_is=696, n_oos=371, purged_at_split=0, folds_pass=4 |
| G4 | ❌ | frac_positive=0.5, worst_bucket=-0.2216, scored=86, buckets=87, notional_scale=1.3151 |
| G5 | ❌ | alpha_ann=0.3725, beta=0.1021, alpha_t_hac=1.6538, strategy_return=2.1643, bh_return=5.5103, beats_raw_bh=False |
| G6 | ❌ | k_removed=54, net_ex_top=-6.202, net_ex_best_month=1.4067, net_ex_best_week=1.4724, net_total=1.8429 |
| G7 | ❌ | pbo=None, pbo_evaluated=False, dsr=0.0892, sr=0.038, sr0=0.0632, T=2625 |
| G8 | ✅ | pf_at_mult=1.0695, mean_bps_at_mult=6.2529, cost_share=0.3436, breakeven_mult_pf=2.5675, breakeven_rt_bps_pf=28.2913, mean_rt_cost_bps=11.0192 |
| G9 | ❌ | boot_maxdd_p95_mtm=0.7892, boot_maxdd_p95=0.8522, ruin_frac=0.0, mtm_maxdd=0.5859, liquidation_threshold_move=0.045, liquidated_trades=4 |
| G11 | ✅ | gated=False, win_rate=0.1406, payoff=7.4258, breakeven_wr=0.1187, wr_margin_pp=2.1898 |
| G10 | PENDING | status=PENDING (needs forward run + prereg) |

- **Artefacto fuente (run_id):** `9e93753caa755c27`

### triple EMA (8/21/55) pullback · ETHUSDT 1h (id=26)
- **Paridad DEV:** OK (re-run n=942, PF=1.2622, net=319.04% vs artefacto n=942.0, PF=1.2621765384956332, net=319.03982881405454%)
- **n FULL:** 1136 · notional/equity (mediana): 0.35x · IS PF 1.2622 · OOS PF 1.0348
- **backtest_pass: False** · failure_modes: ['COST_FAILURE (gross edge exists, net does not clear)']

| Gate | pass | números clave |
|---|---|---|
| G1 | ❌ | pf_net=1.1313, pf_gross=1.2481, expectancy_bps=20.2814, boot_lb_bps=-4.5018, zero_losers=False |
| G2 | ✅ | n=1136, n_eff=1136.0, rho1=0.0, rho_cross=0.0 |
| G3 | ❌ | pf_is=1.255, pf_oos=0.8696, n_is=748, n_oos=387, purged_at_split=1, folds_pass=3 |
| G4 | ❌ | frac_positive=0.506, worst_bucket=-0.0983, scored=83, buckets=84, notional_scale=0.3544 |
| G5 | ❌ | alpha_ann=0.2406, beta=0.0157, alpha_t_hac=2.2754, strategy_return=0.7963, bh_return=14.5639, beats_raw_bh=False |
| G6 | ❌ | k_removed=57, net_ex_top=-8.9875, net_ex_best_month=1.4488, net_ex_best_week=1.7331, net_total=2.304 |
| G7 | ❌ | pbo=None, pbo_evaluated=False, dsr=0.1869, sr=0.0477, sr0=0.0648, T=2532 |
| G8 | ✅ | pf_at_mult=1.0569, mean_bps_at_mult=9.2537, cost_share=0.3043, breakeven_mult_pf=2.8391, breakeven_rt_bps_pf=31.3091, mean_rt_cost_bps=11.0277 |
| G9 | ❌ | boot_maxdd_p95_mtm=0.5147, boot_maxdd_p95=0.5901, ruin_frac=0.0, mtm_maxdd=0.2979, liquidation_threshold_move=0.045, liquidated_trades=137 |
| G11 | ✅ | gated=False, win_rate=0.265, payoff=3.1383, breakeven_wr=0.2416, wr_margin_pp=2.332 |
| G10 | PENDING | status=PENDING (needs forward run + prereg) |

- **Artefacto fuente (run_id):** `2f8f3ce69d850de1`

### impulse-bar continuation · ETHUSDT 1h (id=45)
- **Paridad DEV:** OK (re-run n=622, PF=1.2748, net=264.63% vs artefacto n=622.0, PF=1.2747938111630186, net=264.6295563399547%)
- **n FULL:** 755 · notional/equity (mediana): 0.52x · IS PF 1.2748 · OOS PF 1.0137
- **backtest_pass: False** · failure_modes: ['COST_FAILURE (gross edge exists, net does not clear)']

| Gate | pass | números clave |
|---|---|---|
| G1 | ❌ | pf_net=1.1909, pf_gross=1.3275, expectancy_bps=31.5967, boot_lb_bps=-2.5319, zero_losers=False |
| G2 | ✅ | n=755, n_eff=755.0, rho1=0.0, rho_cross=0.0 |
| G3 | ❌ | pf_is=1.2569, pf_oos=1.0077, n_is=510, n_oos=244, purged_at_split=1, folds_pass=3 |
| G4 | ❌ | frac_positive=0.4133, worst_bucket=-0.1836, scored=75, buckets=84, notional_scale=0.5248 |
| G5 | ❌ | alpha_ann=0.2246, beta=0.0386, alpha_t_hac=1.6646, strategy_return=1.182, bh_return=14.5639, beats_raw_bh=False |
| G6 | ❌ | k_removed=38, net_ex_top=-7.2359, net_ex_best_month=1.7129, net_ex_best_week=1.791, net_total=2.3856 |
| G7 | ❌ | pbo=None, pbo_evaluated=False, dsr=0.0698, sr=0.0364, sr0=0.0649, T=2532 |
| G8 | ✅ | pf_at_mult=1.1182, mean_bps_at_mult=20.568, cost_share=0.2161, breakeven_mult_pf=3.865, breakeven_rt_bps_pf=42.6254, mean_rt_cost_bps=11.0287 |
| G9 | ❌ | boot_maxdd_p95_mtm=0.6839, boot_maxdd_p95=0.7014, ruin_frac=0.0, mtm_maxdd=0.4094, liquidation_threshold_move=0.045, liquidated_trades=60 |
| G11 | ✅ | gated=False, win_rate=0.2318, payoff=3.9471, breakeven_wr=0.2021, wr_margin_pp=2.9651 |
| G10 | PENDING | status=PENDING (needs forward run + prereg) |

- **Artefacto fuente (run_id):** `df3d84f2bad4b17b`

---
*Validación de investigación con el Book del repo (engine sin modificar). Paridad DEV verificada por candidato. Datos: `results/candidates_v2_validation.json`. pack20 requiere instrumentación de su propio engine (pendiente).*