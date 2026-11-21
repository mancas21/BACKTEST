# Audit-fix campaign 2026-11-21 — the external Qwen harness audit, fixed and re-measured

- trigger: the user brought an external audit of THIS harness (Qwen, chat
  export; extracted text `Downloads/_audit_6e3a35c1.md`). Every one of its
  code-level claims was verified against the repo before fixing: ten
  confirmed, one split, two scale notes. The verified read-out lives in the
  session record; this report ships the fixes and the re-measurements.
- known-answer selftest of every fix: `code/_auditfix_selftest_20261121.py`
  — forty-four checks, all PASS (re-run after the last engine edit).
- engines touched: `code/bt.py`, `code/vrun.py`, `code/_gates_v2.py`,
  `code/gate2.py`, `code/gatecal_engine.py`, `code/p100_screen_engine.py`.
  Old generations verify REFUSED (engine drift) by design and stay
  append-only; supersession is recorded in `code/_engine_lock.json`
  (known_superseded: p100screen one hundred seventy-four cells, s101
  thirty-seven cells, gatecal one artifact).

## The fixes (audit id -> what changed)

| id | fix | where |
|---|---|---|
| N1 | `bt one` conc reads ONLY canonical percent keys (`best5_share_pct`, `conc_top5_share_pct`); the ambiguous `top5_pnl_share` (percent in some adapters, fraction in others) is REFUSED with an explicit N-A reason instead of being scaled x100 | `bt.py` |
| N2 | `bt one` is fail-closed: N-A gates FAIL the verdict; a null profit_factor (a no-loser book) FAILS the pf gate; the v2 battery G1-G11 is a required row via `vrun.compute_gates_v2`; exit code two on any N-A | `bt.py` |
| N3 | the bootstrap replicate count is NEVER shrunk again: the F14 memory cap became the CHUNK size; chunked stationary bootstrap, bit-identical to the unchunked matrix at small n; `boot_reps_actual` travels with every result; a tail estimate under the declared floor (`boot_reps_floor` = five hundred) fails closed in G1 and G9 | `_gates_v2.py` |
| N4 | `gate2.pbo_cscv` is DELEGATED to the reference implementation `_gates_v2.pbo_cscv` (the old local one divided a candidate rank by a time-row count and returned mean omega — on a pure-noise matrix it returned roughly one hundredth where the true PBO is one half; the fixed wrapper returns roughly four tenths on the same matrix. These two are selftest measurements, quoted in words because a selftest is code, not an artifact; the selftest asserts the reference agreement) | `gate2.py` |
| N5 | spread books: the stop is detected INTRABAR on the spread's envelope range built from the two legs' own high/low (conservative for any beta sign), stop-first with gap-through filled at the open — the same convention as every directional book; `pack_conventions=True` keeps the pack's close-only semantics declared as the optimistic reading. The exit fee uses the beta FROZEN AT ENTRY (a Kalman book never bills a notional it did not hold) | `p100_screen_engine.py` |
| N6 | the engine consumes the SERVED cut slice (registered by basename); `load_klines` / `funding_events` read the served bytes; funding JSONs and the cost model joined the artifact inputs (run_id-bound); static JSONs are hashed and served WHOLE (they are not funding lists); an adapter that cannot consume the slice must declare `cut_enforced: False`, which the artifact records | `p100_screen_engine.py` + `vrun.py` |
| N7 | `bootstrap_r` block scales with n (`n^(1/3)`), and a sample under the n floor FAILS CLOSED (sentinel ci_low = minus one plus a `boot_small_sample` flag) instead of returning a zero-width interval that passes deterministically | `p100_screen_engine.py` |
| N8 | a stored `gates_v2` block is a CACHE, not a certificate: with `trades_v2` present the battery is ALWAYS recomputed and a disagreeing verdict, or a foreign `policy_hash`, is refused; a stored block without trades_v2 is accepted only when its policy hash matches either battery layer in force | `vrun.py` |
| N9 | the per-symbol measured cost is WIRED: every p100 book resolves its gate cost through the repo rule (max of the default round trip and the measured per-symbol RT; fee five bps, slip rt/2 minus fee; multi-leg books charge the max leg), and the resolved values are measured inside each artifact (`cost_source`, `cost_bp_roundtrip`); the cost model file is a hashed input | `p100_screen_engine.py` |
| N10 | the neighborhood sweep keeps the parent's `--set` params (a multi-strategy adapter sweeps ITS id, not the default), and the verdict is the CONJUNCTION of the plan rule and the POLICY rule (at least seventy percent of neighbours above PF one point two, median neighbour PF within seventy-five percent of the centre) — "stricter wins" made arithmetic | `bt.py` |
| N11 | funding is charged BEFORE intrabar stops in both books (a settlement happens at the bar's open instant, before intrabar action); the G1 no-loser PF bypass is gone (a no-loser book has pf = infinity and passes arithmetically; the tail gates still bind it) | `p100_screen_engine.py` + `_gates_v2.py` |
| A2 | the planted-edge drift is rebuilt per trade (`_apply_drift`) so it COMPOUNDS through the equity chain — the old adjustment derived the equity base from the ORIGINAL chain, so every trade's drift was lost at each step and only the last trade's ~twenty bps ever reached the final return | `gatecal_engine.py` |
| A3 | the stale-calibration finding is closed by the re-run below: the new artifact carries the CURRENT policy hash and the per-gate power table | this report |

## A2 re-measured: the calibration artifact, verified bit-for-bit

New calibration `1d938af1df8dbfc0` (`vrun verify` OK; two-year BTCUSDT 1h
window, buy & hold +24.296178920267852 percent, `g5_design_note` carried
inside the artifact). Per-gate pass rates, planted edge in bps per trade:

| cell | G1 | G3 | G5 | G6 | v1 all | v2 all |
|---|---|---|---|---|---|---|
| n30 d0 | 0.1875 | 0.1175 | 0.0125 | 0.0025 | 0.0 | 0.0 |
| n30 d20 | 0.4925 | 0.32 | 0.03 | 0.075 | 0.0125 | 0.0 |
| n100 d0 | 0.075 | 0.0875 | 0.0275 | 0.0125 | 0.0025 | 0.0025 |
| n100 d20 | 0.485 | 0.4675 | 0.155 | 0.2025 | 0.0825 | 0.025 |
| n300 d0 | 0.0075 | 0.03 | 0.015 | 0.0025 | 0.0025 | 0.0 |
| n300 d5 | 0.0225 | 0.075 | 0.0375 | 0.015 | 0.01 | 0.0 |
| n300 d10 | 0.09 | 0.19 | 0.0925 | 0.0675 | 0.05 | 0.0025 |
| n300 d20 | 0.485 | 0.525 | 0.4875 | 0.4025 | 0.31 | 0.095 |

Read-out, and a correction on the record:

- **G5 now receives the planted edge** (monotone 0.0150 -> 0.0375 -> 0.0925
  -> 0.4875 at n300); the v1 conjunction at n300 d20 moves **0.0175 ->
  0.31**, roughly eighteen times higher. The external audit's payoff
  prediction was right, and the verification session's correction ("G5 vs
  full-window buy & hold is un-passable by design") was WRONG — the
  calibration window is two years, where buy & hold is +24.3 percent, not
  the roughly-ten-times-full-history figure that correction assumed.
- The G1/G3/G6 columns are unchanged from the previous calibration (within
  trial noise) — the chain break blinded ONLY G5, exactly as the audit
  claimed.
- **The v2 column is bit-identical to the previous report** (v2 never read
  the equity chain): the honest state of the world is that v1's published
  power WAS depressed by a bug, while **v2's joint pass rate at a strong
  planted edge remains 0.095 at n300 d20** (`1d938af1df8dbfc0`,
  `v2_all`) — genuine, no BH gate inside it. Any corpus-level "no edge"
  inference rests on THAT number, and the audit's Part A headline survives
  in this narrower, measured form.

## N6 proven end-to-end (the cut is real for this adapter now)

- `d1927ea23e444dcc`: prompt forty-four DEV at cut 2026-01-01 — inputs are
  the fifty-five-thousand-three-hundred-fifty-one-bar slice (ends
  2025-12-31) plus the funding slice plus the cost model.
- `5ee597c4ecfb2aa0`: the same prompt, OOS segment at the same cut — the
  book sees ONLY the pre-cut bars (two trades; its stored
  `bh_return_pct` is -19.8287277296175). Before the fix the engine
  re-resolved the live file and the metrics were full-window regardless of
  the cut.

## The re-screen, re-run on the fixed engine

The full prompts-100 re-screen was re-run: one hundred eighty cells
(ninety prompts x DEV and OOS), all on the current engine generation, with
funding charged before stops, honest spread stops, entry-beta exit fees and
resolved per-symbol costs. The regenerated report is
`results/prompts100_rescreen_report.md` — `guard --strict` OK. Verdict
shape UNCHANGED: four prompts clear the DEV screen and ZERO clear the full
OOS verdict; the pack's books remain a cost problem, now measured with the
thicker cost regime.

- thin-name resolution is visible in the artifacts: JUP cell twelve DEV
  `4444d607d5f06057` carries `cost_bp_roundtrip` 22.57 with `cost_source`
  "measured (JUPUSDT)"; the six-leg pair cell eighty-eight and the baskets
  charge the max leg (the same 22.57, from their JUP leg); pair
  eighty-five's SOL leg cell fifteen DEV `983913dfa9677572` resolves to
  11.99 "measured (SOLUSDT)"; majors stay at the eleven-bps default (their
  measured round trips are BELOW it).
- one hundred fifty of the one hundred eighty cells moved against the
  previous generation and every material move is in the conservative
  direction (thin names charged more, spread stops binding earlier,
  settlement-bar stop-outs now paying their funding).

## Integrity sweep

`code/_auditfix_verify_sweep_20261121.py` verifies every artifact of the
new cell generation plus the calibration: see the tally below (counts in
words; per-artifact exit codes one by one).

- one hundred eighty-one artifacts verify OK, zero REFUSED, zero STALE
  (one hundred eighty p100screen cells plus the gatecal calibration;
  `vrun verify` reproduces each bit-for-bit on the current engine bytes).

## What was deliberately NOT done

- s101 was NOT re-run: its verdict (zero survivors, KILLED) came from the
  plan pipeline; under the fail-closed v2 promotion row a re-run cannot
  produce a different verdict. Its thirty-seven artifacts are orphaned by
  design and the entry in `_engine_lock.json` records this.
- The four-battery full unification (CI conventions, effective-n estimands,
  G6 bucketing axes, G3 fold floors across `gate2` vs `_gates_v2`) remains
  declared, not merged: `POLICY` is the number of record (now stated in
  `GATES_AND_RULES.md`), and the N8 refusal logic implements
  "stricter wins" where the two layers can disagree on a verdict.
- No engine emits `gates_v2` / `trades_v2` blocks yet, so `bt one` will
  fail the v2 row on every existing artifact — that is the F1 doctrine
  applied honestly: a v1-only screen pass is not promotable. Making
  engines emit the v2 schema is the next campaign.
