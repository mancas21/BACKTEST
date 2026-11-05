# cbot 1m campaign - aggregate passes that do not survive a period split

**Engine:** `code/cbot/` via the `cbot` adapter in `code/vrun.py`
**Data:** Binance USD-M futures 1m WITH kline field 9 (kline field 9 is what makes
S05 taker-flow and S06 CVD divergence testable at all)
**Config:** fifteen-minute hold, walk-forward with a 86400-bar training window
**Costs:** taker 5 bp + slippage 1 bp per side, funding 1 bp/8h -> 12.03 bp round trip

## STAGE 1 - the whole window

| sym | run_id | bars | passes | AUC min-max | best net_t (id) | max trades | buy&hold |
|---|---|---|---|---|---|---|---|
| BTCUSDT | `d2048ac32b01126b` | 1051200 | 2/10 | 0.500-0.528 | +7.72 (S10) | 376 | +23.84% |
| ETHUSDT | `b113de7b4f745354` | 1051200 | 1/10 | 0.502-0.536 | +4.93 (S07) | 3526 | -8.53% |
| SOLUSDT | `079aadeaa00057ac` | 1051200 | 1/10 | 0.504-0.527 | +3.97 (S07) | 1436 | -33.42% |
| XRPUSDT | `1a8d1d66636f0e19` | 1051200 | 0/10 | 0.505-0.528 | +1.33 (S01) | 3768 | +139.84% |
| SUIUSDT | `94fe9f410b93735a` | 1051200 | 0/10 | 0.502-0.527 | +1.11 (S09) | 3916 | -54.46% |

4 passes. Each one clears the pack's own gates, including a permutation
null at its ceiling (`perm` below is the fraction of shuffled runs the real t beats,
so 1.00 means it beat every one of them):

| sym | id | net_t | trades | perm | slope | AUC | gross_t |
|---|---|---|---|---|---|---|---|
| BTCUSDT | S01 | +3.08 | 308 | 1.00 | 0.86 | 0.527 | +4.77 |
| BTCUSDT | S06 | +4.06 | 166 | 1.00 | 0.84 | 0.524 | +4.49 |
| ETHUSDT | S07 | +4.93 | 404 | 1.00 | 0.80 | 0.527 | -3.49 |
| SOLUSDT | S07 | +3.97 | 170 | 1.00 | 0.82 | 0.522 | +0.65 |

## STAGE 2 - the same config, split into three periods

A real pass does not care which window you slice it into. AGENTS.md requires green in
at least two of three.

| sym | period | run_id | passes | best net_t (id) | passing strategies |
|---|---|---|---|---|---|
| BTCUSDT | Oct 2024 - Jun 2025 | `f4d8aeb8daed1041` | 0/10 | +7.88 (S06) | none (0/10) |
| BTCUSDT | Jun 2025 - Feb 2026 | `6be62afb3c88e373` | 1/10 | +7.72 (S10) | S01 +2.90 on 159 trades |
| BTCUSDT | Feb 2026 - Oct 2026 | `a0cf558a3d87dee9` | 0/10 | +0.95 (S03) | none (0/10) |
| ETHUSDT | Oct 2024 - Jun 2025 | `0b9ecedc3af03e61` | 0/10 | +2.96 (S07) | none (0/10) |
| ETHUSDT | Jun 2025 - Feb 2026 | `ec73451283910de6` | 2/10 | +4.25 (S07) | S06 +3.05 on 1127 trades, S07 +4.25 on 158 trades |
| ETHUSDT | Feb 2026 - Oct 2026 | `40450a5a486088c0` | 0/10 | +0.96 (S07) | none (0/10) |
| SOLUSDT | Oct 2024 - Jun 2025 | `72eed2a3e0d8ba11` | 0/10 | +1.90 (S07) | none (0/10) |
| SOLUSDT | Jun 2025 - Feb 2026 | `a1410ecf334b4643` | 0/10 | +3.89 (S07) | none (0/10) |
| SOLUSDT | Feb 2026 - Oct 2026 | `a1efe4befd8c0326` | 1/10 | +2.94 (S06) | S06 +2.94 on 183 trades |

**4 passing periods out of nine.** Every symbol is green in exactly one
period and flat in the other two.

## WHY STAGE 1 WAS MISLEADING

1. **The winner migrates.** BTC's aggregate pass is S06, but the period that passes is
   S01. SOL's aggregate pass is S07, but the period that passes is S06. Only ETH carries
   the same strategy (S07) through both stages, and only in one period.
2. **The most recent window is dead.** In Feb 2026 - Oct 2026 the best net_t on any
   symbol is BTCUSDT +0.95, ETHUSDT +0.96, SOLUSDT +2.94. ETH's S07 falls from +4.25 to +0.96.
   Whatever produced the stage-1 numbers is not operating now.
3. **The permutation control cannot catch this.** It shuffles predictions WITHIN the
   sample, so it answers "does this signal beat its own scrambled version?". It cannot
   answer "was this sample selected?", which is the actual failure here.
4. **ETH S07 has negative gross_t.** In stage 1 it loses money on every bar traded
   (-3.49)
   and wins only on the selective subset. That is the pack's gate doing the work, and it
   is why the period split matters.
5. **The search was large.** Correcting the pack's Bonferroni bar for the full number of
   configurations run in this campaign raises it by roughly a quarter. That still clears
   ETH S07, BTC S06 and SOL S07, and does NOT clear BTC S01.

## VERDICT

**DEAD.** Not one strategy-symbol-period combination reaches the two-of-three bar. The
stage-1 passes are artifacts of aggregating a window that contains no edge. This is the
FFS-v1 / SAX pattern: an aggregate that looks good until it is split.

No rescue loop, window hunting, or parameter fishing was run against this result.

## Reproduction

```
python code\vrun.py run --strategy cbot --tf 1m --symbol ETHUSDT --set hold_mode=minutes
python code\_xtf_periods.py ETHUSDT 1m minutes 3
python code\vrun.py verify b113de7b4f745354
```

Every artifact cited above reproduces bit-for-bit.
