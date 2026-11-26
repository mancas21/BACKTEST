# MTF top-down (attached Python source) — SOLUSDT 5m

Date: 2026-11-26. Status: **new strategy, own verdict**. The attached Python strategy was copied byte-identically into `code/mtf_topdown_source.py` (sha `833aedf770bad9c3f7b0b7860d5cbe9d2a2a2c790319b1b175a4f62f16a2d945`) and imported by identity: the harness did NOT rewrite its signal. Grid and execution conventions are frozen in `results/mtf_topdown_pre_registration.md`.

## Proof before the number

`code/_mtf_topdown_audit.py` 9/9 PASS before any market read: source hash matches the attachment, the source's OWN `test_causality()` passes on real SOL 5m, and the harness executor reproduces the source's engine trade-for-trade on the full trade set, identically, on the same signals and its own 4+1 bps costs. Funding sign and the accounting identity are asserted inside the artifact.

## Result

**KILLED.** Base cost regime is the repo gate (5.0 fee + 0.5 slip bps per side, 11 bps RT) with real funding at settlements. Net -38.52%, PF 0.818, 353 trades, win rate 32.86%, max DD -43.15%, funding paid 32.95 USDT, run_id `787fb4b3c52450bf`.

| Regime (same signals) | Net % | PF | Trades | run_id |
|---|---:|---:|---:|---|
| BASE repo 11 bps + funding | -38.52 | 0.818 | 353 | `787fb4b3c52450bf` |
| author 4+1 bps, no funding | -38.11 | - | 353 | `787fb4b3c52450bf` |
| zero cost, no funding | -9.74 | - | 353 | `787fb4b3c52450bf` |

Buy & hold over the same window is 2626.59% and the out-of-sample half is -16.14% at PF 0.751 on 129 trades (`787fb4b3c52450bf`). The bootstrap lower bound is -20.764 and the best five trades are 5.75% of positive PnL (`787fb4b3c52450bf`), so concentration is not the problem: the book simply loses.

## Reading

Removing money improves the result but does not make it positive (the zero-cost control is still negative), so this is not a cost-only kill. The signal's own gross edge is insufficient at the declared 1%-risk sizing, and it loses badly to simply holding the symbol over a window where buy & hold multiplied many times.

The user chose SOLUSDT only. The source's default parameters were frozen; no grid, no tuning and no parameter rescue were run.

## Provenance

- Attachment: `C:\Users\Lenovo\Downloads\mtf_topdown-strategy-claude.py` (byte-identical copy in `code/mtf_topdown_source.py`).
- Adapter: `code/mtf_topdown_engine.py` (hashed into the run_id together with the source).
- Audit: `code/_mtf_topdown_audit.py` 9/9 before the market run.
- Matrix: `results/mtf_topdown_matrix.json`; verification log: `results/_mtf_topdown_verify.txt`.

