# EMA Cross + ADX [Quant] — ported, audited, and KILLED

**Deliverable:** ports the requester's Pine (EMA Cross + ADX [Quant], Pine version six,
delivered on the twenty-second of October; the original filename is recorded in the
engine header of `code/emaadx_engine.py`) and runs it through the harness. This
report is the verdict.

- Engine: `code/emaadx_engine.py` (version emaadx-one; sha recorded in every artifact below)
- Known-answer audit: `code/_emaadx_audit.py` — **all thirty-five cases PASS**
  (written to `results/emaadx_audit_known_answers.txt`). It verifies the indicator
  primitives against hand arithmetic and a pandas holy-reference, a dual-engine DMI
  recomputation on random data, and five crafted playthroughs whose fills are
  re-derived independently of the engine: signal-bar-close fill (the Pine's
  process-orders-on-close convention), all-in sizing, a TP fill at the exact anchored
  limit, stop-first tie-breaking on a bar that spans both bracket levels, per-row fee
  reconstruction and money conservation at zero tolerance, a reversal filling both legs
  at one price, the Pine's duplicate-signal bracket re-set (proven by the later stop
  exit price matching the re-set bar's anchor rather than the entry bar's), and
  truncation parity (no lookahead).
- Data: `data/binance_klines_1h/{SYM}_1h.csv` (thirteen symbols; bar counts and sha
  of every file live in each cited artifact's `inputs`).

## Porting semantics (declared before the runs)

Entries and reversals fill at the SIGNAL bar's close (this Pine sets
process-orders-on-close), stops fill with adverse slippage, limits fill at the limit
price, a bar that touches both levels resolves stop-first, fees charge on the whole
order quantity of a reversal, and a duplicate same-direction signal while positioned
re-sets the brackets without changing size (the Pine's var-block reruns even though
pyramiding rejects the entry — reproduced deliberately; the audit proves which anchor
was used). Indicators are the Pine-letter definitions: EMA recursion seeded at the
start of the file's history but gated until full length (min-periods), Wilder DI
with the leading-na seed, ATR as Wilder-smoothed true range. The head gate means the
first scored bars of the full window start after the indicators warm; the skipped
head is a few hundred bars out of tens of thousands.

**Costs.** Author set: the Pine's five-basis-point commission per fill plus its
single tick of header slippage, which on these series is negligible; declared zero
with that justification (recorded in the engine header). Repo set: the repo standard
of six basis points commission plus five basis points slippage per fill. Every
artifact ALSO carries a zero-cost control pass on the same bars, so the drag is
measured inside the artifact (`drag_pp`), not quoted from a separate file.

**Windows.** Full scores the whole file; the half-year window scores the trailing
four-thousand-three-hundred-sixty-eight hourly bars after six hundred warmup bars.

## The matrix — zero of fifty-two canonical cells pass every gate

Pre-declared gates G1..G6: G1 profit factor (strict, fees inside trade PnL) greater
than one point two; G2 at least thirty closed trades; G3 both chronological halves'
profit factors above one; G4 (full windows only) green in at least two-thirds of the
calendar years scored (a count of years — G4 verdict only, in the rows: fail/pass);
G5 beats buy-and-hold on the same scored window; G6 concentration — book PnL
excluding the best five winners must stay positive (a book whose total PnL is
already negative fails G6 by construction; such cells print a dash in the conc
column). A cell passes only with all of them. No walk-forward was attempted:
nothing survived the gates.

### Full window, author costs

| 6250f711eafd3696 | ADAUSDT | -19.9259 | 0.9525 | 0.9582 | 0.9436 | 247 | 307.6585 | 22.4027 | 2.4974 | fail |
| 8af35224ae3770d5 | AVAXUSDT | -9.6052 | 0.9810 | 1.0422 | 0.9088 | 213 | 141.8582 | 21.4438 | 2.2546 | fail |
| 19873d70ce87189b | BNBUSDT | -23.7947 | 0.9205 | 0.8169 | 1.2593 | 245 | 2766.2036 | 21.1927 | 3.3937 | fail |
| 041e85cf248622b1 | BTCUSDT | -67.4379 | 0.7993 | 0.9059 | 0.5047 | 312 | 715.7500 | 11.9714 | 4.4157 | fail |
| b041915046dd6473 | DOGEUSDT | -79.4101 | 0.7016 | 0.7128 | 0.6623 | 228 | 2042.4364 | 5.3231 | 2.7002 | fail |
| 8ec8753e67f7bffa | ETHUSDT | 88.0416 | 1.1121 | 1.2820 | 0.9244 | 286 | 1556.0753 | 62.2728 | 3.0824 | fail |
| b301ee09abb758d6 | HYPEUSDT | -1.2034 | 0.9755 | 0.8390 | 1.1393 | 33 | 176.4100 | 3.3813 | 2.4919 | fail |
| 53eceda66d866068 | LINKUSDT | 158.9197 | 1.1344 | 1.3402 | 0.8990 | 225 | 330.6924 | 65.2025 | 2.2102 | fail |
| 7d13b9d8f0bce6a4 | NEARUSDT | -6.6855 | 0.9888 | 1.0352 | 0.9428 | 207 | 345.6979 | 21.5179 | 2.0596 | fail |
| 77dfda43aca269c7 | SOLUSDT | -53.1477 | 0.8245 | 0.7885 | 0.8842 | 233 | 2990.3582 | 12.3885 | 2.3865 | fail |
| 7f4ef32199ee451b | SPXUSDT | -56.7968 | 0.6779 | 0.6574 | 0.7268 | 58 | -29.1258 | 2.6146 | 1.7842 | fail |
| 1367b3a30728f9be | SUIUSDT | -16.4873 | 0.9130 | 0.6527 | 1.3370 | 104 | -27.7798 | 9.1562 | 2.3802 | fail |
| f49cb9cb80c36ac3 | XRPUSDT | -29.5826 | 0.9587 | 1.0655 | 0.7815 | 270 | 536.7467 | 21.8633 | 2.5388 | fail |

(reconciled in words: zero of thirteen symbols pass G1..G6 in this cell-set)

### Full window, repo costs

| 776fd5a4a10d6684 | ADAUSDT | -53.2565 | 0.8433 | 0.8364 | 0.8570 | 247 | 307.6585 | 55.7333 | 3.0218 | fail |
| 34f2eb92bd6e15f7 | AVAXUSDT | -22.5832 | 0.9533 | 1.0136 | 0.8767 | 213 | 141.8582 | 34.4219 | 2.6966 | fail |
| 18904f1c08809e2a | BNBUSDT | -36.0753 | 0.8755 | 0.7905 | 1.1744 | 245 | 2766.2036 | 33.4733 | 4.0899 | fail |
| 570a150bdf631ee5 | BTCUSDT | -73.9320 | 0.7683 | 0.8669 | 0.4694 | 312 | 715.7500 | 18.4655 | 5.3187 | fail |
| fdad6e14018c7581 | DOGEUSDT | -99.3804 | 0.1031 | 0.0924 | 0.5504 | 228 | 2042.4364 | 25.2933 | 5.6483 | fail |
| 117a696ba5816610 | ETHUSDT | 53.4293 | 1.0731 | 1.2365 | 0.8754 | 286 | 1556.0753 | 96.8851 | 3.7001 | fail |
| 0168fdb572aa840e | HYPEUSDT | -3.5646 | 0.9407 | 0.8139 | 1.0943 | 33 | 176.4100 | 5.7425 | 3.0247 | fail |
| 01857d89a643507d | LINKUSDT | 119.2592 | 1.1072 | 1.3072 | 0.8625 | 225 | 330.6924 | 104.8630 | 2.6423 | fail |
| 628a9ce629b73cb7 | NEARUSDT | -21.7452 | 0.9613 | 1.0032 | 0.9159 | 207 | 345.6979 | 36.5776 | 2.4634 | fail |
| 01facb13fac281bf | SOLUSDT | -60.5851 | 0.7898 | 0.7557 | 0.8519 | 233 | 2990.3582 | 19.8259 | 2.8753 | fail |
| 99a791a6f829a4aa | SPXUSDT | -60.2226 | 0.6583 | 0.6435 | 0.6943 | 58 | -29.1258 | 6.0405 | 2.1405 | fail |
| e0c16af0e00e55b5 | SUIUSDT | -24.9663 | 0.8662 | 0.6238 | 1.2818 | 104 | -27.7798 | 17.6351 | 2.8943 | fail |
| 2904b48cb90237dd | XRPUSDT | -50.1100 | 0.9221 | 1.0156 | 0.7379 | 270 | 536.7467 | 42.3907 | 2.9783 | fail |

(reconciled in words: zero of thirteen symbols pass G1..G6 in this cell-set)

### Half-year window, author costs

| 8472c80c7bc73134 | ADAUSDT | 11.0888 | 1.6228 | 0.6986 | 3.0129 | 13 | -10.4988 | 1.3849 | 2.1075 | fail |
| 376d13d128014908 | AVAXUSDT | -0.2816 | 0.9867 | 0.9313 | 1.0836 | 16 | 5.5597 | 1.6072 | 3.7346 | fail |
| 9071990816b033e1 | BNBUSDT | 5.7064 | 1.4480 | 6.5318 | 0.3767 | 18 | 13.8529 | 1.9190 | 5.2709 | fail |
| 4a5401b8104a2ee1 | BTCUSDT | -3.4476 | 0.7346 | 0.5990 | 0.9251 | 15 | 7.8974 | 1.4613 | 7.6953 | fail |
| 5d2d01d0b31ab4df | DOGEUSDT | -13.4349 | 0.3743 | 0.4680 | 0.3092 | 13 | -15.5373 | 1.1049 | 8.0998 | fail |
| 10d5282347586cad | ETHUSDT | -16.4827 | 0.3657 | 0.3457 | 0.3926 | 22 | 3.0178 | 1.8336 | 10.6126 | fail |
| 23a00d8be53d1d3d | HYPEUSDT | 16.0729 | 1.6608 | 1.9819 | 1.1073 | 16 | 132.3182 | 1.9298 | 2.1476 | fail |
| f15b7ddefd7df189 | LINKUSDT | 2.3466 | 1.1315 | 1.1690 | 1.0989 | 13 | 30.0992 | 1.3335 | 3.2081 | fail |
| 531f181bf3cae492 | NEARUSDT | -29.2569 | 0.2837 | 0.0000 | 0.4416 | 16 | 267.1091 | 1.1619 | 5.8722 | fail |
| eb8a1715f932d962 | SOLUSDT | -9.4865 | 0.5341 | 0.7974 | 0.3294 | 13 | 20.8784 | 1.1513 | 6.1477 | fail |
| 8c7a0f33e189d46a | SPXUSDT | -29.7874 | 0.3076 | 0.5665 | 0.0000 | 14 | 66.4026 | 1.0106 | 4.8087 | fail |
| c56b1000dfb777f1 | SUIUSDT | 2.5838 | 1.1771 | 1.9955 | 1.0396 | 9 | 3.8969 | 0.9358 | 2.6457 | fail |
| a443ca2a3359d027 | XRPUSDT | -13.6613 | 0.4401 | 0.9471 | 0.0000 | 18 | -8.9087 | 1.5372 | 8.1620 | fail |

(reconciled in words: zero of thirteen symbols pass G1..G6 in this cell-set)

### Half-year window, repo costs

| 336d33a16d58df75 | ADAUSDT | 8.3870 | 1.4353 | 0.6066 | 2.7569 | 13 | -10.4988 | 4.0866 | 2.5739 | fail |
| 416621f2e7abd7a9 | AVAXUSDT | -1.4635 | 0.9333 | 0.8806 | 1.0257 | 16 | 5.5597 | 2.7892 | 4.5596 | fail |
| dc019506f04d2384 | BNBUSDT | 4.3787 | 1.3267 | 5.9214 | 0.3418 | 18 | 13.8529 | 3.2467 | 6.5214 | fail |
| 5caf5ba66e40cfbd | BTCUSDT | -4.4582 | 0.6726 | 0.5507 | 0.8452 | 15 | 7.8974 | 2.4719 | 9.5753 | fail |
| f2847e34c2b005c6 | DOGEUSDT | -19.6714 | 0.2755 | 0.3367 | 0.2292 | 13 | -15.5373 | 7.3414 | 9.8930 | fail |
| 7535beb16e20c974 | ETHUSDT | -17.7673 | 0.3390 | 0.3240 | 0.3591 | 22 | 3.0178 | 3.1181 | 13.1597 | fail |
| 2918973d735ab768 | HYPEUSDT | 14.6937 | 1.5914 | 1.9075 | 1.0503 | 16 | 132.3182 | 3.3091 | 2.6119 | fail |
| 093e9a422b7490c6 | LINKUSDT | 1.3811 | 1.0752 | 1.1037 | 1.0502 | 13 | 30.0992 | 2.2991 | 3.9199 | fail |
| 9f6b8b933069b88e | NEARUSDT | -30.3017 | 0.2724 | 0.0000 | 0.4233 | 16 | 267.1091 | 2.2067 | 7.1536 | fail |
| 9c2e231f0ffe1355 | SOLUSDT | -10.2698 | 0.5059 | 0.7499 | 0.3132 | 13 | 20.8784 | 1.9346 | 7.5231 | fail |
| 113fac66668372f0 | SPXUSDT | -31.6046 | 0.2920 | 0.5322 | 0.0000 | 14 | 66.4026 | 2.8278 | 5.7926 | fail |
| 33466177649f140a | SUIUSDT | 1.5369 | 1.1003 | 1.8358 | 0.9742 | 9 | 3.8969 | 1.9827 | 3.2188 | fail |
| 9e96f0604623434c | XRPUSDT | -15.1801 | 0.4062 | 0.8641 | 0.0000 | 18 | -8.9087 | 3.0560 | 10.0177 | fail |

(reconciled in words: zero of thirteen symbols pass G1..G6 in this cell-set)

Reconciled tally (recomputed from the artifacts, restated in words): **zero of
thirteen symbols** pass G1..G6 in each of the four cell-sets — **zero of the
fifty-two canonical cells**. Three further artifacts exist with default params
instead of explicit window/costs keys and identical metrics
(83a6e062c85b6406, 8c1c3acceb9e957f, 4805f0fd37708b6d) — repeats, not cells.
All fifty-two canonical artifacts verify clean (the run driver re-verified each).

## Why it dies, structurally

Exit structure from the trade rows (row counts and pnl sums are re-derived from the
cited artifacts' own tables and stated in words for reconciliation):

- BTC full/author (041e85cf248622b1): 312 closed
  trades; stop rows outnumber target rows (214 to
  92 for 6 reversal closes).
  With the stop at twice ATR and the target at twice that distance, breaking even
  needs a hit rate above a third before costs; the book delivers
  30.1282 percent (artifact metric).
- ETH full/author (8ec8753e67f7bffa): 286 closed, same
  shape; and it still fails concentration (-9.2796) —
  strip the best five winners and the book goes underwater.
- The half-year cells carry too few trades to even pass the count gate (nine to
  twenty-two closes per symbol), and their concentration figures are extreme:
  HYPE (23a00d8be53d1d3d) is the best-looking cell anywhere —
  pf 1.6608 with both halves above one — but only
  16 closed trades and conc -101.4498.
  ADA half-year (8472c80c7bc73134) repeats it: pf
  1.6228 on 13 trades with conc -127.0643.
- The zero-cost control kills fees as the excuse: at zero commission and zero slip
  BTC's equity still ends at -55.4665 percent
  (11.9714 points of drag,
  artifact 041e85cf248622b1) — the signal itself is the loser.
  At the other end the drag reaches 104.8630 points
  (LINK full/repo 01857d89a643507d) — repo-standard costs turn
  even a marginal gross edge into ruin.
- G5 exposes the anti-alpha pattern twice: SUI full/author reports beating B&H
  while BOTH lose (B&H -27.7798 percent, bot
  -16.4873 percent, artifact 1367b3a30728f9be)
  — winning by losing less than a collapsing market is not edge (repo rule).
  DOGE half-year (5d2d01d0b31ab4df, bot
  -13.4349>B&H -15.5373) repeats it.
- Only LINK and ETH ended the full window with positive book PnL at author costs
  (LINK 158.9197 pf 1.1344,
  ETH 88.0416 pf 1.1121); both fail
  concentration (-6.4633 and
  -9.2796) — each was a handful of whale
  trades sitting on a pile of stop-outs. DOGE full/repo is near-total ruin: pf
  0.1031, return -99.3804 percent.

## Verdict

**KILLED. No cell, symbol, cost set or window clears the gates; the signal is
underwater before costs.** No neighborhood ring was run for the reason that rule
exists: stability checks apply to survivors, and there were none. No walk-forward,
no parameter fishing, no rescue windows.

Caveats recorded for honesty: the trailing position where one exists is marked to
the last close and excluded from closed-trade statistics (flagged in each artifact's
`n_open`; the HYPE half-year cells end with one open position); the author cost
set's tick slippage is declared zero with its magnitude argument in the engine
header; the spot-data head means EMA state carries an arbitrary seed for the first
bars, mitigated by the min-periods gate and irrelevant at this scale. The Pine was
the author's own specification, ported letter for letter.

— artifacts under `results/runs/*.json`, engine `code/emaadx_engine.py`
(emaadx-one), harness `code/vrun.py`; every number above was read from the cited
artifacts; counts and year tallies restated in words per the repo rule.
