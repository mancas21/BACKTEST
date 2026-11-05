#!/usr/bin/env python
"""_gen_pack50d_engine.py -- one-shot generator: pack50d_engine.py from
pack50c_engine.py with the spec source swapped, 1h ctx for P35/P50, the
build2 (auxiliary-data) branch for P23's BTC filter, and the pair branch
for P17. Runs once; the output engine is then frozen before any artifact."""
import re

src = open("pack50c_engine.py").read()

src = src.replace(
    '"""pack50c_engine.py -- harness runner for the Qwen fifty-prompt pack\n'
    '(`Downloads/Qwen_50 strategies.txt`, numbered Q01-Q50).',
    '"""pack50d_engine.py -- harness runner for the DeepSeek fifty-prompt pack\n'
    '(`Downloads/deepseek_markdown_20261027_68930c.md`, numbered P01-P50).')
src = src.replace("import pack50c_strats as SC",
                  "import pack50d_strats as SD")
src = src.replace("SC.SPECS", "SD.SPECS").replace("SC.CODE", "SD.CODE")
src = src.replace("SC.costs_for", "SD.costs_for")

old_head = '''def run_one(paths, params):
    strat = int(params["strat"])
    spec = SD.SPECS[strat]
    if spec.get("no_data"):
        raise RuntimeError(f"prompt {SD.CODE[strat]} cannot be run: {spec['no_data']}")

    tf = spec["tf"]
    klines = [p for p in paths if p.endswith(".csv")]
    fund = [p for p in paths if p.endswith(".json")]
    funding = load_funding(fund[0]) if fund else None
    df = PE.load_base_tf(klines[0], tf)
    plan = spec["build"](df)
'''
new_head = '''def _ctx_1h(df):
    """Map fully closed 1h-bar context onto a finer book (pack50b convention)."""
    d = df.copy()
    d["ts"] = pd.to_datetime(d["ts"], utc=True)
    g = (d.set_index("ts").resample("1h", label="left", closed="left")
          .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
          .dropna()).reset_index()
    g["ready"] = g["ts"] + pd.Timedelta(hours=1)
    left = pd.DataFrame({"ts": d["ts"].sort_values()})
    left["ts"] = left["ts"].dt.as_unit("us")
    right = g.copy()
    right["ready"] = right["ready"].dt.as_unit("us")
    right = right.sort_values("ready")
    merged = pd.merge_asof(left, right, left_on="ts", right_on="ready",
                           direction="backward")
    return merged


def _ctx_for(df, strat):
    if strat == 35:
        from pack50b_engine import PE as _PE
        return _PE._ctx_for(df)
    if strat == 50:
        m = _ctx_1h(df)
        h1 = m["high"].to_numpy(float)
        l1 = m["low"].to_numpy(float)
        c1 = m["close"].to_numpy(float)
        st, _ = supertrend(h1, l1, c1, 10, 3.0)
        adx, _, _ = adx_di(h1, l1, c1, 14)
        st = pd.Series(st).ffill().fillna(0).to_numpy()
        adx = pd.Series(adx).ffill().fillna(0.0).to_numpy()
        return {"st_1h_dir": st, "adx_1h": adx}
    return {}


def run_one(paths, params):
    strat = int(params["strat"])
    spec = SD.SPECS[strat]
    if spec.get("no_data"):
        raise RuntimeError(f"prompt {SD.CODE[strat]} cannot be run: {spec['no_data']}")

    tf = spec["tf"]
    klines = [p for p in paths if p.endswith(".csv")]
    fund = [p for p in paths if p.endswith(".json")]
    funding = load_funding(fund[0]) if fund else None
    df = PE.load_base_tf(klines[0], tf)
    is_pair = "pair" in spec
    df_a = df
    pair_target = pair_note = None
    if is_pair:
        df_b = PE.load_base_tf(klines[1], tf)
        na = min(len(df_a), len(df_b))
        df_a = df_a.iloc[-na:].reset_index(drop=True)
        df_b = df_b.iloc[-na:].reset_index(drop=True)
        common = np.intersect1d(df_a["open_ts"].to_numpy(), df_b["open_ts"].to_numpy())
        df_a = df_a[df_a["open_ts"].isin(common)].reset_index(drop=True)
        df_b = df_b[df_b["open_ts"].isin(common)].reset_index(drop=True)
    if is_pair:
        def _pair_run(costs):
            tgt, note = spec["pair"](df_a, df_b)
            from pack50_core import run_pair
            return run_pair(df_a, df_b, tgt, costs, funding,
                            load_funding(fund[1]) if len(fund) > 1 else None), tgt, note
        res, pair_target, pair_note = _pair_run(REPO)
    elif "build2" in spec:
        df_b = PE.load_base_tf(klines[1], tf)
        plan = spec["build2"](df, df_b)
        res = run_plan(df, plan, REPO, funding)
    elif strat in (35, 50):
        plan = spec["build"](df, _ctx_for(df, strat))
        res = run_plan(df, plan, REPO, funding)
    else:
        plan = spec["build"](df)
        res = run_plan(df, plan, REPO, funding)

    tr = res["trades"]
    eq = res["equity"]
    if len(tr) == 0:
        raise RuntimeError(f"{SD.CODE[strat]} produced no trades at repo cost")
    r = tr["ret_pct"].to_numpy(float)
    e = tr["entry_ts"].to_numpy(np.int64)
    x = tr["exit_ts"].to_numpy(np.int64)

    sr_bar = _bar_returns(eq)
    if is_pair:
        mkt = df_a["close"].to_numpy(float) / df_b["close"].to_numpy(float)
    else:
        mkt = df["close"].to_numpy(float)
    mkt_ret = np.diff(mkt) / mkt[:-1]
    # alpha is measured on DAILY returns (the reference layer's G5 basis):
    # bar-level bootstrap on a one-million-bar book allocates gigabytes, and
    # the daily basis is the statistically meaningful one for alpha vs market
    book_df = df_a if is_pair else df
    ts_idx = pd.to_datetime(book_df["open_ts"], unit="ms", utc=True)
    eq_d = pd.Series(eq, index=ts_idx).resample("1D").last().ffill()
    mk_d = pd.Series(mkt, index=ts_idx).resample("1D").last().ffill()
    strat_daily = eq_d.pct_change().dropna().to_numpy(float)
    mkt_daily = mk_d.pct_change().dropna().to_numpy(float)

    lb, exp_bps, blk = (None, None, None)
    if len(r) > 100_000:
        lb, exp_bps = _expectancy_lb_chunked(r, n_boot=1000, seed=7)
        lb_method = "chunked_moving_block"
    else:
        lb, exp_bps, blk = G2.expectancy_lb_bps(r, n_boot=1000, seed=7)
        lb_method = "moving_block"
    eff = G2.effective_n(r)
    sp = G2.purged_split(e, x, r)
    folds, fold_frac, purged_n = G2.purged_folds(e, x, r)
    buckets = G2.period_buckets(x, r, freq="M", min_bucket_trades=5)
    alpha = G2.beta_alpha_t(strat_daily, mkt_daily, n_boot=1000, seed=11)
    conc = G2.top_frac_concentration(r, frac=0.05)
    bm = G2.best_month_removal(e, r)
    bw = G2.best_week_removal(x, r)
    dd95 = G2.p95_max_dd(sr_bar, n_boot=500, seed=13)
    ddst = G2.drawdown_stats(eq)
    pf_pct = G2.profit_factor_pct(r)

    mae_df = df_a if is_pair else df
    h = mae_df["high"].to_numpy(float)
    l = mae_df["low"].to_numpy(float)
    bar_ts = mae_df["open_ts"].to_numpy(np.int64)
    entry_px = tr["entry_px"].to_numpy(float)
    side = tr["side"].to_numpy(int)
    i_in = np.searchsorted(bar_ts, e)
    i_out = np.clip(np.searchsorted(bar_ts, x), 0, len(bar_ts) - 1)
    mae = np.zeros(len(tr))
    for k in range(len(tr)):
        lo_k = l[i_in[k]:i_out[k] + 1].min()
        hi_k = h[i_in[k]:i_out[k] + 1].max()
        mae[k] = max((entry_px[k] - lo_k) / entry_px[k], 0.0) if side[k] > 0 \
            else max((hi_k - entry_px[k]) / entry_px[k], 0.0)
    leverage_declared = 1.0
    liq_thresh = 1.0 / leverage_declared - 0.005
    liq_trades = int((mae >= liq_thresh).sum())

    gross = tr["pnl"].to_numpy(float) + tr["fees"].to_numpy(float) - tr["funding"].to_numpy(float)
    strict_gross = float(gross[gross > 0].sum())
    fees_total = float(tr["fees"].sum())
    cost_share = float(fees_total / strict_gross) if strict_gross > 0 else float("inf")

    if is_pair:
        base_fee, base_slip = SD.costs_for(spec["sym"].split("+")[0], tf)
        pack = Costs(fee_bps=base_fee, slip_bps=base_slip)
        res_pack, _, _ = _pair_run(pack)
        bh = buy_and_hold_pair(df_a, df_b)
        plan_note = pair_note
    else:
        base_fee, base_slip = SD.costs_for(spec["sym"], tf)
        pack = Costs(fee_bps=base_fee, slip_bps=base_slip)
        res_pack = run_plan(df, plan, pack, funding)
        bh = buy_and_hold(df)
        plan_note = plan.note if isinstance(plan, Plan) else ""

    def _run_at(costs):
        if is_pair:
            return _pair_run(costs)[0]
        return run_plan(df, plan, costs, funding)

    def _pf_at(costs):
        t2 = _run_at(costs)["trades"]
        return G2.profit_factor_pct(t2["ret_pct"].to_numpy(float)) if len(t2) else 0.0

    pf_2x = _pf_at(TWO_X)
    be, _ = G2.breakeven_side_cost(
        lambda t: _run_at(Costs(fee_bps=t, slip_bps=0.0))["trades"],
        lo=0.0, hi=100.0, iters=8)
    zero = _run_at(Costs(0.0, 0.0))
    zero_pf = G2.profit_factor_pct(zero["trades"]["ret_pct"].to_numpy(float)) \\
        if len(zero["trades"]) else 0.0

    v1 = _v1_gates(tr, book_df, bh["bh_return_pct"])
    sr = float(np.mean(sr_bar) / np.std(sr_bar, ddof=1)) if len(sr_bar) > 2 else float("nan")
'''
# splice: replace everything from the original run_one head through the v1 line
start = src.index("def run_one(paths, params):")
anchor_v1 = '    v1 = _v1_gates(tr, df, bh["bh_return_pct"])'
end = src.index(anchor_v1) + len(anchor_v1)
src = src[:start] + new_head + src[end:]

# remaining: alpha_basis flag, pair marker, adapter id, SD cost fns in metrics
src = src.replace('"alpha_basis": "daily",', '"alpha_basis": "daily", "is_pair": is_pair,')
src = src.replace('"adapter": "pack50c", "engine_version": "pack50c-1"',
                  '"adapter": "pack50d", "engine_version": "pack50d-1"')
src = src.replace("from pack50_core import (Costs, Plan, buy_and_hold, load_funding, run_plan)",
                  "from pack50_core import (Costs, Plan, adx_di, buy_and_hold,\n"
                  "                         buy_and_hold_pair, load_funding, run_pair,\n"
                  "                         run_plan, supertrend)")
open("pack50d_engine.py", "w").write(src)
print("pack50d_engine.py written")
