# Repository Audit — `backtest-system`

**Date:** 2026-11-19 · **Auditor stance:** quant researcher / algorithmic-trading developer / ML engineer
**Mode:** READ-ONLY. No code, data, artifact, or doc was modified. This document is the deliverable; fixes are proposed, not applied.
**Scope:** execution engines, the statistical gate layer, the harness (`vrun.py`, `bt.py`), data provenance manifests, funding math, and the protocol docs (`AGENTS.md`, `GATES_AND_RULES.md`, `VALIDATION_PROTOCOL.md`, `RUNBOOK.md`).

---

## 0. Executive summary

The repo's **anti-fabrication discipline is genuinely strong**: content-hashed `run_id`, bit-for-bit `verify`, byte-identical source preservation, signal parity proofs, known-answer execution audits, an asserted accounting invariant, cut-based data hashing, and a hash-chained artifact store. Those are not cosmetic — they caught real bugs historically and they hold up under inspection.

The defects are concentrated in **four areas**, and the first is the most consequential:

1. **The documented v2 gate contract (G1–G11) is not uniformly enforced.** The main orchestrator (`bt.py`) and most modern adapters judge candidates at the weaker **v1 screen floor** (PF>1.2, n≥30, thirds, OOS, concentration, bootstrap). The full statistical battery lives in `gate2.py` / `_gates_v2.py` but is invoked only by a subset of older pack adapters and the calibration harness. A "PASS" from `bt.py` is **not** a v2-certified verdict.
2. **Funding is under-charged on coarse timeframes and silently zero across internal data holes.** Settlements collapse onto one bar on 1d data, and `funding_covers_bars` only checks endpoints, so a 21-day funding hole (PUMP) still reports "covered".
3. **Provenance/verification tooling has robustness and binding gaps.** `pverify --strategy` aborts on any unrelated corrupt artifact; `guard` matches numbers against a *global* pool, so a row can carry another cell's number and still pass.
4. **Data attestation and ops docs are stale/partial.** `KLINES_MANIFEST.json` covers only daily files; `cadence_deviations` is inflated by ±1 ms timestamp jitter; `RUNBOOK.md` still describes retired VPS bots as live.

None of these imply fabricated results. They imply **some verdicts are weaker than documented, some perp costs are understated, and some tooling can mislead or block**. Severity counts: **5 High, 7 Medium, 8 Low/Note**.

| ID | Sev | Category | Title | Primary location |
|---|---|---|---|---|
| F1 | HIGH | Gates / architecture | v2 battery (G1–G11) not enforced by `bt.py`/most adapters | `bt.py:18-31`, `vrun.py:3586`, `scalpma20_engine.py:744-752` |
| F2 | HIGH | Math / funding | Funding settlements collapse on 1d bars (under-charge) | `p100_screen_engine.py:584-590` |
| F3 | HIGH | Data / funding | `funding_covers_bars` endpoint-only; internal holes pass | `scalpma20_engine.py:720-721`, `FUNDING_MANIFEST.json` |
| F4 | HIGH | Code / robustness | `pverify --strategy` aborts on any corrupt artifact | `vrun.py:3998-4001` |
| F5 | HIGH | Statistics / provenance | `guard` global number pool → cross-cell contamination | `vrun.py:4126-4155` |
| F6 | MED | Data | `KLINES_MANIFEST` covers only 1d/1d_taker | `data/KLINES_MANIFEST.json`, `datacheck_klines.py:49-51` |
| F7 | MED | Statistics / data | `cadence_deviations` inflated by ±1 ms jitter | `FUNDING_MANIFEST.json` |
| F8 | MED | Math / gates | G4 worst-bucket threshold scale ambiguity | `_gates_v2.py:432-442` |
| F9 | MED | Statistics / gates | G9 bootstrap P95 on trade sequence, not MTM bars | `_gates_v2.py:196-209, 544-556` |
| F10 | MED | Docs / architecture | `RUNBOOK.md` describes retired bots as active | `RUNBOOK.md:3-55` vs `AGENTS.md:96-142` |
| F11 | MED | Code | Missing-engine fallback to constant `SAX_ENGINE_SHA` | `vrun.py:3590-3593` |
| F12 | MED | Performance | scalpma20 bootstrap is a 20 000-iteration Python loop | `scalpma20_engine.py:645-646` |
| F13 | LOW | Math / gates | G3 split axis mixes entry-min and exit-max | `_gates_v2.py:409-410` |
| F14 | LOW | Code / memory | `_safe_reps` floor overrides the memory cap | `_gates_v2.py:179-180` |
| F15 | LOW | Statistics | `effective_n` clamps ρ₁≥0 (conservative) | `_gates_v2.py:328-334` |
| F16 | LOW | Gates / calibration | G11 excluded from null-calibration joint | `_gates_v2.py:751` |
| F17 | LOW | Math / execution | No intra-run margin/liquidation simulation | `p100_screen_engine.py:691, 734-740` |
| F18 | LOW | Provenance | `guard` ignores `core`/`provenance` numbers | `vrun.py:4128-4136` |
| F19 | LOW | Architecture | Heterogeneous hand-rolled gate booleans per adapter | many `*_engine.py` |
| F20 | LOW | Reporting | `inf` PF on tiny OOS samples renders as pass-like | `_gates_v2.py:157-163`, scalpma20 `94bf64ef…` |

---

## 1. HIGH severity

### F1 — The v2 gate contract is not uniformly enforced (gates / architecture)

**Evidence.**
- `GATES_AND_RULES.md:36-57` defines the binding contract as **G1–G11**: expectancy bootstrap LB>0, **n≥100** (+30/symbol, effective-N), purged 70/30 split **and** 5 purged folds (≥70% green), ≥6 scored calendar buckets (≥60% green, worst ≥−15%), benchmark **alpha t>2** (HAC) / beats B&H, concentration (top-5% + best month + best ISO week), **DSR≥0.95 / PBO≤0.5**, **PF>1 at 2× cost** + breakeven, **P95 bootstrapped MTM DD≤35%** + liquidation-distance, pre-registration, win-rate margin.
- `bt.py:18-31` declares its "STANDARD BATTERY" as: `pf>1.2, n>=30, net>0, thirds>=2/3, oos_pf>1.2, oos_net>0, conc<=100%` (+ bootstrap CI in plans). This is the **v1 screen floor**, not v2.
- `vrun.make_artifact` (`vrun.py:3586`) calls `a["run"](...)` and persists whatever metrics that adapter returns; it does **not** call `evaluate_gates_v2`.
- Grep for `evaluate_gates_v2` / `import _gates_v2`: only `gatecal_engine.py`, `_gates_v2.py`, `_gates_v2_selftest.py`, `_artifact_chain.py`, `_trial_ledger.py`. Grep for `gate2.` usage: `cand7`, `pack50c`, `pack50d`, `pack100`, `gatecal` (older packs).
- Modern adapters hand-roll gates: `scalpma20_engine.py:744-752` builds `gate_all` from `gate_pf/gate_n/gate_net/gate_thirds/gate_oos/gate_conc/gate_boot_ci` — **no G2 n≥100, no G3 folds, no G4 buckets, no G5 alpha, no G7 DSR, no G8 2× cost, no G9 P95 DD, no G11**.

**Why it matters.** `AGENTS.md:326-331` itself says the screen floor is v1 and "anyone judging a candidate applies THAT [v2] battery, not the screen floor alone." But the pipeline that actually produces verdicts (`bt.py`, `vrun run`) applies v1. So campaigns such as `scalpma20` (0/120), `ema921` (0/101), and the `top10` shortlist are judged at a **weaker gate than the documented contract**. The kill verdicts are still safe (they fail even v1), but any future **PASS** would be over-claimed: it would not have cleared n≥100, DSR, 2× cost, P95 DD, or the benchmark alpha test.

**Impact.** Governance/correctness of *promotion* decisions. A candidate could be promoted on v1 while failing v2 (e.g., n=40, PF=1.3, but DSR<0.95 or P95 DD>35%). This is exactly the "green-cell-that-dissolves" risk the protocol exists to prevent.

**Fix (proposed).** Make v2 the single source of truth: either (a) call `_gates_v2.evaluate_gates_v2` inside `make_artifact` (or a mandatory `bt.py` post-screen stage for every survivor) and persist its `gates`/`backtest_pass`/`policy_hash` in the artifact; or (b) if v1 is the intended operational gate, **downgrade `GATES_AND_RULES.md`** to state that v2 is advisory/calibration-only. Do not leave the document and the pipeline disagreeing. Unify the per-adapter gate booleans behind one function (see F19).

---

### F2 — Funding settlements collapse on coarse timeframes (math / funding)

**Evidence.** `p100_screen_engine.py:584-590`:
```python
for x in recs:
    t = int(x["t"])
    j = int(np.searchsorted(bar_ms, t, side="left"))
    if j < len(bar_ms):
        ev[j] = True
        rate[j] = float(x["r"])   # OVERWRITES, does not accumulate
        n += 1
```
A settlement maps to the first bar whose **open ≥ t**. When the bar interval exceeds the funding interval, **multiple settlements land on the same bar `j`** and `rate[j]` keeps only the **last** one; `ev[j]` is a single boolean, so the book charges funding **once** for that bar.

**Worked example (1d bars, 8h funding).** Bar opens at `day0 00:00`, `day1 00:00`, … Settlements `day0 00:00 (r0)`, `day0 08:00 (r1)`, `day0 16:00 (r2)`, `day1 00:00 (r3)`:
- `r0 → bar0`; `r1 → bar1`; `r2 → bar1` (overwrites r1); `r3 → bar1` (overwrites r2).
- Charged: `r0` on bar0, `r3` on bar1. **Lost: r1, r2.** Over two days, 4 settlements → 2 charged (**~50% under-charge**). With 4h funding (6/day) the loss is larger.

**Why it matters.** `AGENTS.md` declares the 1d approximation ("charges a mid-day settlement at the next daily open") but **not the collapse of multiple settlements into one**. Any 1d perp book that holds across days under-pays funding materially. On majors, cumulative funding is worth tens of percent over years (the repo's own notes cite +81–98%); a 2–5× under-charge on the funding leg is not a rounding error.

**Impact.** Overstated equity / PF for 1d (and any tf ≥ funding interval) perp backtests. Intraday tf (1m/5m/15m/1h) are unaffected because bar interval < funding interval (no collision).

**Fix (proposed).** Accumulate per bar: `rate[j] += float(x["r"])` and charge the summed rate once (the book already multiplies by notional), **or** iterate settlements within each bar and charge each. Add a known-answer test: a 1d bar spanning three 8h settlements must debit the sum of all three. Re-run any 1d perp artifacts after the fix (their `run_id` will change).

---

### F3 — `funding_covers_bars` is endpoint-only; internal holes pass as "covered" (data / funding)

**Evidence.** `scalpma20_engine.py:720-721`:
```python
funding_covers = bool(f_arr is not None and f_first is not None
                      and f_first <= bar_ms[WARM] and f_last >= bar_ms[-1] - 8*3600*1000)
```
This checks only that the **first** settlement precedes the traded window start and the **last** follows its end. It does **not** inspect internal spacing.

`FUNDING_MANIFEST.json` documents real internal holes:
- **PUMPUSDT**: `missing_settlements: 126`, `max_cadence_multiple: 126.0` → a gap of 126 × 4h ≈ **21 days** with no funding records.
- BTCUSDT `missing_settlements: 5`; ETHUSDT `4`; SOLUSDT `2` (+101 interval switches); HYPEUSDT `4` (`max_cadence_multiple: 3`); SPXUSDT `5`.

**Why it matters.** `funding_events` (F2) assigns `rate=0, ev=False` to bars with no settlement record. Across an internal hole the book charges **zero funding** while `funding_covers_bars` reports **True** because the endpoints are fine. The repo's own AGENTS lesson ("a backtest with half funding is another backtest", the JUP 243-day head_gap) is about *head* gaps; this is the *internal*-gap variant, and the coverage flag does not catch it.

**Impact.** Silent cost understatement for any perp book whose window spans an internal funding hole (PUMP especially). The artifact looks fully funded but is not.

**Fix (proposed).** Compute coverage from the manifest's `missing_settlements` / `max_cadence_multiple`, or scan settlement spacing inside the traded window and fail/flag when a gap exceeds ~2× the modal interval. Publish `funding_internal_gap_days` and make `funding_covers_bars` require it ≈ 0. Until fixed, treat PUMP (and any symbol with `missing_settlements>0`) perp results as **funding-incomplete**.

---

### F4 — `pverify --strategy` aborts on any corrupt artifact (code / robustness)

**Evidence.** `vrun.py:3995-4001`:
```python
for p in sorted(glob.glob(os.path.join(RUNS, "*.json"))):
    if os.path.basename(p).startswith("_"): continue
    with open(p, encoding="utf-8") as f:
        art = json.load(f)          # no try/except
    if art.get("strategy") == args.strategy:
        run_ids.append(art["run_id"])
```
To filter by strategy it parses **every** artifact. Four pre-existing truncated `fvgup` artifacts (`33dd230e8ff47cb2`, `3b616925794d87b6`, `9b7a96308aa46a22`, `a0c1aff75f64db48`, ~7.3 KB each, cut mid-array) raise `json.JSONDecodeError`, which propagates out of `cmd_pverify` → the whole batch exits `REFUSED` (2) **before verifying a single intended cell**.

**Why it matters.** A clean campaign's verification is blocked by unrelated damaged files. This was hit live during the scalpma20 campaign; the workaround was `pverify --ids <120 ids>`. The damaged files are append-only history and must not be deleted, so the tooling must tolerate them.

**Impact.** Verification availability; risk that an operator reads the `REFUSED` as "this campaign failed verification" when it never ran.

**Fix (proposed).** Wrap the filter's `json.load` in `try/except (JSONDecodeError, OSError)`, count and warn on unparseable files, and continue. Optionally add a `pverify --repair-report` that lists damaged artifacts for separate archival. The per-id verify path (`_pverify_one`) already isolates exceptions; the *selection* path does not.

---

### F5 — `guard` matches numbers against a global pool → cross-cell contamination (statistics / provenance)

**Evidence.** `vrun.py:4126-4155`:
```python
values = []
for a in backers:                      # ALL cited artifacts
    _collect_numbers(a.get("metrics"), values)
    ...
for tok in NUMBER_RE.findall(scan):
    ...
    if any(abs(round(v, dps) - val) < 1e-9 for v in values): continue   # ANY artifact
    if any(abs(v - val) <= tol for v in values): continue               # ANY artifact
```
`--strict` (`4112-4124`) only checks that **symbol tokens** on a line match the cited `run_id`'s symbol. It does **not** check that the *number* on that line belongs to the *specific* `run_id` cited there.

**Why it matters.** In a 120-row table where every row cites its own `run_id`, all 120 artifacts are in `backers`, so `values` is the union of every cell's metrics. A row citing cell A (SOLUSDT 5m) can print cell B's PF (also SOLUSDT 5m, different id) and **pass guard**: the symbol matches A, and the number matches B somewhere in the pool. The provenance guarantee is therefore "this number exists in *some* cited artifact", not "this number is *this row's* result".

**Impact.** A report can silently mis-attribute numbers across cells of the same symbol/tf and still be "guard OK". This is weaker than REGLA 0's intent ("a number is a result only if *its* artifact backs it"). The repo already acknowledges guard is provenance-not-correctness, but this specific binding hole is not declared.

**Fix (proposed).** In `--strict`, bind numbers per line: for each line, collect the `run_id`s cited **on that line** and require every numeral on the line to match one of **those** artifacts (not the global pool). Keep the global pool only for non-strict mode. Add a self-test: a table row citing A but printing B's metric must REFUSE under strict.

---

## 2. MEDIUM severity

### F6 — `KLINES_MANIFEST.json` attests only daily files (data)

**Evidence.** The persisted manifest (`asof 2026-11-14`) contains exactly two dirs: `binance_klines_1d` and `binance_klines_1d_taker` (11 files each, 3 263 rows). `datacheck_klines.py:49-51` defaults to **all** `binance_klines*` dirs, so the on-disk manifest is a **partial scan** (`--dirs` was used). The intraday dirs (`1m`, `5m`, `15m`, `1h`, and their `_taker` variants) — which the overwhelming majority of strategies actually read — have **no gap/duplicate/bad-OHLC/NaN attestation** in this manifest.

**Impact.** Data-quality provenance gap for the bulk of the corpus. A truncated or gap-ridden intraday file would not be flagged by the manifest (though `vrun stale`/cut-hash catches byte changes, not OHLC validity).

**Fix.** Re-run `python code/datacheck_klines.py` with default dirs to attest every `binance_klines*` directory; refresh the manifest and its report.

### F7 — `cadence_deviations` inflated by ±1 ms timestamp jitter (statistics / data)

**Evidence.** `FUNDING_MANIFEST.json`: ADA `cadence_deviations: 4622` of 7 484 settlements; BTC `4691`/7862; BNB `4604`/7419; LINK `4624`/7491. `modal_spacing_ms: 28800000` (8h) yet `first_t` values end in `…001` (e.g. `1780272000001`). The deviation counter evidently flags every spacing ≠ modal **exactly**, so ±1 ms jitter on settlement timestamps is counted as a cadence break. `interval_switches: 0` for these same files confirms the cadence is actually stable.

**Impact.** A misleading data-quality signal: thousands of "deviations" that are pure timestamp jitter. This can mask real interval switches (the metric is saturated) or trigger false alarms in any consumer that thresholds on `cadence_deviations`.

**Fix.** Tolerance the comparison (e.g. `abs(spacing - modal) <= 1000 ms`, or round timestamps to seconds) before counting deviations; keep `interval_switches` as the real structural signal. Re-build the manifest.

### F8 — G4 worst-bucket threshold scale ambiguity (math / gates)

**Evidence.** `_gates_v2.py:432-442`: buckets are `groupby(exit_month)["net"].sum()`, and `worst = scored["sum"].min()` is compared to `g4_worst_bucket_min = -0.15`. The trade schema (`_gates_v2.py:12-22`) defines `net` as a **fixed-size per-trade fraction of notional, not compounded**. `GATES_AND_RULES.md:50` describes the bound as "−15% of starting capital".

**Why it matters.** A *sum* of per-trade fractions over a month equals a capital fraction only when `notional_per_equity == 1` and trades are non-overlapping. For a levered book (`notional_per_equity = 20`) the true equity impact is ~20× the unscaled sum; for a high-frequency book the sum grows with trade count. The −0.15 bound is therefore **size- and count-dependent**, not a uniform capital-drawdown bound.

**Impact.** G4's worst-bucket gate means different things across leverage/frequency; a 20× book could pass G4 while its worst month is −300% of equity (G9 would catch ruin, but G4's stated semantics are wrong).

**Fix.** Scale bucket sums by `ctx.notional_per_equity` before comparing to −0.15, or restate the threshold explicitly in per-trade-fraction-sum units and document the leverage dependence.

### F9 — G9 bootstrap P95 is on the trade sequence, not the MTM bar series (statistics / gates)

**Evidence.** `_gates_v2.py:544-556`: `bs = bootstrap_max_dd(r = t["net"], size, ...)` bootstraps the **closed-trade** sequence and compounds it (`196-209`). The actual MTM drawdown is checked separately (`552-556`) only if `ctx.equity_mtm` is supplied. `GATES_AND_RULES.md:55` says G9 is "P95 of the bootstrapped max drawdown … on the **mark-to-market** series". The cross-check note (`104-106`) declares the reference layer bootstraps the trade sequence while "this repo's uses the mark-to-market bar series" and "the stricter reading wins" — but the **bootstrap tail gate itself** is trade-sequence based.

**Why it matters.** For inventory/grid books, open positions can be deeply underwater *between* closes; the closed-trade sequence misses that intra-hold drawdown. The bootstrapped P95 then **understates** the true MTM tail. The separate MTM point-check helps, but the *probabilistic* tail gate (the one calibrated against a null) is the optimistic one.

**Impact.** Grid/martingale books can clear the P95 tail gate while their real MTM tail is worse — precisely the failure mode that killed the XRP neutral book on 1m resolution.

**Fix.** For `inventory_book` / when `equity_mtm` exists, bootstrap the **MTM bar return series** for the P95 gate (or take `max(trade_seq_p95, mtm_p95)`). Keep the trade-sequence bootstrap only for flat-to-flat directional books.

### F10 — `RUNBOOK.md` describes retired VPS bots as active (docs / architecture)

**Evidence.** `RUNBOOK.md:3-55` gives a full operational layout and cron schedule for the 5-pair `~/neutral-paper` bot (15m + 1m runners, per-pair locks, daily/weekly summaries). `AGENTS.md:96-142` states **all** VPS trading bots were deleted on 2026-11-16, the crontab is empty, and `neutral-paper` was removed even earlier. The two documents directly contradict.

**Impact.** An agent or operator following RUNBOOK would try to operate dead infrastructure, or worse, re-deploy retired bots. Stale ops docs are a live hazard in a repo that prides itself on "no number without an artifact".

**Fix.** Mark the RUNBOOK bot sections **RETIRED (2026-11-16)** with a pointer to the AGENTS tombstone and the backup tarballs, or rewrite RUNBOOK to the current state (data readers + scanner only).

### F11 — Missing-engine fallback to a constant hash (code)

**Evidence.** `vrun.py:3590-3593`:
```python
if os.path.exists(a["sources"][0]) and all(os.path.exists(s) for s in a["sources"]):
    prov["engine_sha256"] = _sha256_engine(a["sources"])
else:
    prov["engine_sha256"] = SAX_ENGINE_SHA      # a fixed constant
```
When any engine source is missing, the artifact is bound to the **old SAX constant hash** rather than failing.

**Impact.** Two different missing-engine strategies whose params+inputs coincide would **collide on `run_id`** (same constant engine hash). `verify` later returns ORPHANED (4), so it is caught before publication — but `make_artifact` still emits an artifact carrying a bogus, non-identifying engine hash.

**Fix.** Fail loudly (`FileNotFoundError`) when a declared source is missing, instead of substituting a constant. Keep the ORPHANED path for *already-stored* legacy artifacts only.

### F12 — scalpma20 bootstrap is a slow Python loop (performance)

**Evidence.** `scalpma20_engine.py:645-646`:
```python
boot = np.array([rng.choice(pnls, n, replace=True).mean() for _ in range(20000)])
```
For the busiest cell (n = 61 951 closed trades) this is 20 000 × 61 951 ≈ **1.24 × 10⁹** samples in a Python loop. It dominates the 551 s screen runtime and risks timeouts on large-n cells. `_gates_v2.stationary_bootstrap_indices` already does this vectorized.

**Impact.** Runtime/scalability, not correctness. Large-n cells may hit per-job timeouts; the i.i.d. `rng.choice` bootstrap also ignores serial correlation (the stationary bootstrap in `_gates_v2` is the better estimator).

**Fix.** Replace with a vectorized index-matrix bootstrap (reuse `_gates_v2.bootstrap_mean_lb`), which is both faster and autocorrelation-aware.

---

## 3. LOW severity / notes

- **F13 — G3 split axis.** `_gates_v2.py:409-410`: `t0 = min(entry_time)`, `t1 = max(exit_time)`, `split = t0 + (t1-t0)*0.70` applied on the **entry** axis. Mixing entry-min with exit-max slightly skews the 70% boundary. Use a consistent axis (e.g., entry-max) or the bar-time span. Cosmetic for long windows.
- **F14 — `_safe_reps` memory floor.** `_gates_v2.py:179-180`: `max(200, min(reps, 6_000_000//n))`. The `max(200, …)` **overrides** the memory cap for large n: at n = 10⁶ it forces a 200 × 10⁶ int64 matrix (~1.6 GB). Clamp the floor by the cap, or chunk the bootstrap.
- **F15 — `effective_n` ρ₁ clamp.** `_gates_v2.py:328-334` clamps ρ₁ ≥ 0, so negative autocorrelation (which would *raise* effective N) is ignored. Conservative and declared as a heuristic; fine, but note it biases N_eff downward for mean-reverting trade sequences.
- **F16 — G11 outside calibration.** `_gates_v2.py:751` calibrates the joint over G1–G9 only; G11 is excluded (declared at `584-586`). The calibrated false-positive rate therefore omits a constraint that only *tightens* the gate — conservative direction, but the calibration should be re-run with G11 folded in (the doc already promises this).
- **F17 — No intra-run liquidation.** `p100_screen_engine.py:691` debits full notional from cash (a fully-funded synthetic accounting; `mark_to_market` at `734-740` is **correct** — verified: long `cash + qty*close`, short `cash - qty*close`, both net the entry fee). Cash can go negative for levered longs but MTM nets out. There is **no intra-bar margin-call/liquidation simulation**; the only liquidation guard is G9's post-hoc MAE-vs-`1/lev − mmr` check. A real perp can liquidate intra-bar on a gap before the stop fills. Declared limitation; keep it explicit in any levered verdict.
- **F18 — guard ignores `core`/`provenance`.** `vrun.py:4128-4136` collects numbers only from `metrics/tables/inputs/params`. A numeral living only in `core` (e.g. `cut_ts`) is not backed. Minor; add `core` if reports quote cut dates.
- **F19 — Heterogeneous gate booleans.** Each adapter hand-rolls `gate_pf/gate_n/gate_all/...` with subtly different definitions (scalpma20 vs ema921 vs xrpneutral vs the gate2-based packs). This is the repo's own historically-flagged "two conflicting pipelines" issue, still present. Consolidate behind one gate function (ties to F1).
- **F20 — `inf` PF on tiny samples.** `_gates_v2.py:157-163` returns `inf` when there are no losers. The scalpma20 cell `94bf64ef6f3a2c16` (SOL 1m id18, **16 trades**) prints OOS PF `inf` because its OOS subset has no losing trades. It fails the n-floor and every other gate, but `inf` renders as a pass-like number in a table. **Reporting rule:** never quote a PF without its n; suppress/flag `inf` when n < the floor. (This was handled correctly in the scalpma20 report; make it a guard/report convention.)

---

## 4. What is SOUND (verified, not assumed)

- **Accounting invariant** `(cash − INIT) == sum(pnl) − funding_paid` is asserted inside artifacts; scalpma20's max residual across 120 cells was ~1.2 × 10⁻¹⁰ USDT. `mark_to_market` long/short signs are correct.
- **Execution conventions** in `p100.Book.run`: signal on closed bar → fill next open; **stop-first** on ties; gap-through fills at the open; time stop; signal exits; opposite-signal reverse at the *same* next open (no close-at-close/open-at-open time travel); funding on the settlement bar against the held position; end-of-data force close. These match the declared spec.
- **Cut-based data hashing (gen 2)** correctly freezes `[0, cut_ts)` bytes so appends cannot stale artifacts; `verify` re-derives the artifact's own cut and checks the core→run_id binding **before** re-running (tamper-evident).
- **Signal parity discipline**: scalpma20's 20 signals were proven byte-identical to the attached source on 100 real-data cells; the engine self-test (40 known answers + causality truncation) passes.
- **DSR math** (`_gates_v2.deflated_sharpe`): variance multiplier `1 − γ3·SR + (γ4−1)/4·SR²` uses **raw** kurtosis (γ4=3 for normal → 0.5), which is the correct Bailey–López de Prado form; `sr0` expected-max-Sharpe under `n_eff` trials is standard.
- **Stationary bootstrap** (Politis–Romano) index generation is correct (jump prob `1/block`, circular continuation).
- **G8 breakeven**: although `m_star` is computed and not separately asserted, `pf_at_2x > 1` is enforced, which (given PF monotone-decreasing in the cost multiplier) is equivalent to breakeven ≥ 2×. Not a decoration bug.
- **`bt.py._eval_gate`** fails closed on a missing metric and rejects booleans-as-numbers — correct.

---

## 5. Prioritized remediation plan (proposed — NOT applied)

**P0 — correctness of costs & verdicts**
1. **F2** funding accumulation per bar + known-answer test (1d, 3 settlements). Re-run affected 1d perp artifacts.
2. **F3** internal-gap-aware `funding_covers_bars`; flag PUMP & any `missing_settlements>0` symbol as funding-incomplete until fixed.
3. **F1** wire `evaluate_gates_v2` into the survivor path (or downgrade the documented contract). Single source of truth for gates (F19).

**P1 — tooling integrity**
4. **F4** tolerant artifact selection in `pverify --strategy` (skip+warn corrupt).
5. **F5** per-line number→run_id binding in `guard --strict` + self-test.
6. **F11** fail loudly on missing engine source.

**P2 — data & docs hygiene**
7. **F6** full `datacheck_klines` scan → refresh manifest.
8. **F7** jitter-tolerant `cadence_deviations` → refresh funding manifest.
9. **F10** mark RUNBOOK bot sections RETIRED.

**P3 — statistical refinement & performance**
10. **F9** MTM-series bootstrap for inventory books' G9 tail.
11. **F8** scale G4 buckets by notional (or restate units).
12. **F12** vectorize scalpma20 bootstrap (reuse `_gates_v2`).
13. **F13/F14/F16/F18/F20** minor cleanups; re-run null calibration with G11.

**Re-verification after any fix:** every changed engine invalidates its artifacts' `run_id` (engine bytes are hashed). Re-run → `pverify` → `guard --strict` → regenerate registry → STATUS entry. Do not hand-edit stored artifacts (append-only).

---

## 6. Read-only reproduction commands

```bash
cd C:/Users/Lenovo/Documents/backtest-system
PY="C:/Users/Lenovo/AppData/Local/Programs/Python/Python312/python.exe"

# F1: who actually calls the v2 battery
grep -rn "evaluate_gates_v2\|import _gates_v2\|gate2\." code/*.py

# F4: the corrupt artifacts that abort pverify --strategy
"$PY" - <<'PY'
import glob, json
for f in glob.glob('results/runs/*.json'):
    try: json.load(open(f, encoding='utf-8'))
    except Exception as e: print('CORRUPT', f, e)
PY

# F2/F3: funding holes already measured in the manifest
"$PY" - <<'PY'
import json
m = json.load(open('data/FUNDING_MANIFEST.json', encoding='utf-8'))
for k, v in m['files'].items():
    if v.get('missing_settlements') or v.get('max_cadence_multiple', 1) > 2:
        print(k, 'missing=', v['missing_settlements'], 'max_mult=', v['max_cadence_multiple'])
PY

# F6: manifest scope
"$PY" -c "import json;print(list(json.load(open('data/KLINES_MANIFEST.json'))['dirs']))"
```

---

## 7. Fix application & re-verification (2026-11-19, post-audit)

After this report was delivered, **all fixes were applied and re-verified** (user
instruction). Nothing was applied before the report. Evidence:

| Fix | Status | Verification |
|---|---|---|
| F1 v2 promotion gate | APPLIED | `vrun.compute_gates_v2` + `bt.py` screen-survivor filter (fail-closed); `_audit_fixes_selftest` F1 cases PASS; documented in GATES_AND_RULES.md |
| F2 funding accumulation | APPLIED | `p100.funding_events` `rate[j]+=r`; selftest 3-settlements-on-1d-bar accumulates to 0.005 (was 0.003); intraday unchanged |
| F3 internal-gap coverage | APPLIED | scalpma20 re-run: `funding_covers_bars` 120→40, `funding_internal_hole` on 80 (HYPE 0/40 covered) |
| F4 tolerant pverify | APPLIED | `pverify --strategy scalpma20` skips the 4 corrupt fvgup files and continues (was: abort) |
| F5 guard per-line binding | APPLIED | selftest: row citing A printing B's PF → REFUSED; correct row → OK; real report guard --strict OK |
| F6 full klines manifest | APPLIED | re-scan: 12 dirs / 180 files / ~25M rows (was 2 daily dirs) |
| F7 cadence jitter tolerance | APPLIED | ADA deviations 4622→0, BTC 4691→5 (real gaps kept), PUMP missing=126 kept |
| F8 G4 notional scale | APPLIED | `_gates_v2_selftest` all PASS |
| F9 G9 MTM bootstrap | APPLIED | `_gates_v2_selftest` all PASS (inventory fail-closed intact) |
| F10 RUNBOOK retired | APPLIED | neutral-paper section banner RETIRED (2026-11-16) |
| F11 fail-loud missing engine | APPLIED | `make_artifact` raises FileNotFoundError; ORPHANED verify path preserved |
| F12 vectorized bootstrap | APPLIED | selftest n=60k: ~12s, memory-bounded chunk≤2M elems, CI finite |
| F13 G3 split axis | APPLIED | entry-axis consistent; selftest PASS |
| F14 _safe_reps memory cap | APPLIED | cap binding; selftest PASS |
| F15 effective_n clamp | NOTE | conservative heuristic, declared; no change needed |
| F16 G11 in calibration | APPLIED | null joint now includes G11; selftest PASS |
| F17 liquidation limitation | APPLIED | declared in `p100.Book` docstring |
| F18 guard scans core | APPLIED | core added to number collection |
| F19 heterogeneous gates | MITIGATED | single v2 promotion gate (F1); per-adapter v1 booleans are screen-only |
| F20 degenerate inf PF | APPLIED | `oos_pf_degenerate` flag; re-run flags the 16-trade inf cell |
| **F21 (NEW)** datacheck NaN false-positive | APPLIED | `datacheck_klines` counted the string `timestamp` column as numeric NaN (nan_values==row_count on 8 clean files); fixed to audit only genuinely numeric columns → **files_with_issues=0** |
| **F22 (NEW)** p100screen 5m input binding | APPLIED | harness `TF_DIR["5m"]`=stub `binance_klines` but the engine (`p100_screen_engine.load_klines`, own `TF_DIRS`) reads `binance_klines_5m` and ignores the harness paths → artifact hashed the WRONG file (provenance mismatch) and crashed for symbols absent from the stub (JUP 5m ids 18/43/62). `_p100screen_inputs` now mirrors the engine dirs; 46 5m cells re-run, inputs bind the real full history (e.g. ETH bars=730563 since 2019), JUP now runs. Metrics unchanged (engine always read the real data) |
| **F23 (NEW)** neutral-benchmark G5 singularity | APPLIED | `alpha_beta_hac` returned (0,0,0) for a zero-variance benchmark (cash, for a market-neutral book) because `inv(X'X)` is singular → G5 false-failed every neutral book. Fixed: alpha=mean(y), beta=0, Newey-West t-stat on the mean. Spread id=85 G5 now passes (alpha t=3.90). `_gates_v2_selftest` all PASS (no regression) |

**Self-tests:** `_audit_fixes_selftest.py` **12/12 PASS**; `scalpma20_engine.py`
**40/40 PASS**; `_gates_v2_selftest.py` **all PASS** (null FP joint 0.017, planted
edge power 0.90, G11 included).

**Campaign re-verification (scalpma20, representative):** re-run with fixed engines
→ **120 new artifacts** (engine_sha256 `cbe3954b…`), **0/120 pass** (KILLED verdict
robust; PF 0.321–0.937 unchanged, intraday unaffected by F2). `guard --strict` OK on
the regenerated report. The 120 pre-fix artifacts are orphaned by engine-drift
(append-only, kept); supersession recorded in `_engine_lock.json`
(`known_superseded.scalpma20_engine.py`: `7ded8133…` → `cbe3954b…`, n=120). Registry
manifest updated to the new run_ids; registry regenerated (`scalp_ma_suite`, 120 rows).

**Corpus restoration (completed):** `p100_screen_engine.py` is also hashed by the
`p100screen` and `s101` adapters, so the F2/F17 engine edit orphaned their artifacts.
Both were **re-run and re-verified** on 2026-11-19: `p100screen` 174 cells
(87 prompts × DEV/OOS, `_p100_screen_run.py`, cache cleared, runner now uses
`sys.executable`) → **174 OK / 0 REFUSED bit-for-bit**; `s101` 37 cells
(`bt.py --plan s101.json`) → **37 OK** (96 historical orphans REFUSED by design),
0 survivors. The registry manifest was repointed by cell identity: **123/123**
entries now cite fixed-engine run_ids with correct inputs. The 3 `JUPUSDT 5m OOS`
cells (ids 18/43/62) initially could not run because of **F22** (the harness declared
the stub `binance_klines/JUPUSDT_5m.csv` while the engine reads `binance_klines_5m`);
after fixing `_p100screen_inputs` to mirror the engine dirs, all 46 p100screen 5m
cells were re-run with correct full-history inputs and the 3 JUP cells now run
(KILLED, PF<1). Supersessions recorded in `_engine_lock.json`. Verdicts unchanged
(intraday/1h packs; F2 only affects 1d funding, F22 is provenance-only). All three
engine-affected campaigns (scalpma20, p100screen, s101) are now re-run and
bit-for-bit verified on their current artifacts. Other historical adapters not
hashing the edited engines were not touched.

---

*Audit delivered read-only first; fixes applied and re-verified afterwards per user instruction. All findings cite file:line evidence. New finding F21 was discovered during the F6 full re-scan and fixed in the same pass.*
