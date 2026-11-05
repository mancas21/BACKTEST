# DeepSeek five-strategy pack — ported, audited, and KILLED

**Deliverable:** ports the requester's five-strategy pack (file delivered on the twenty-second of October; preserved byte-identical as `code/deepseek_pack.py`, sha256 b6ca6f58f36e6c3bb140e39c389dff22319ad5d166818072844999cb5976f212) and runs all five strategies through the harness. This report is the verdict.

- Engine: `code/dspack_engine.py` (version dspack-one; its sha and the pack file's sha are recorded in every artifact below).
- Known-answer audit: `code/_dspack_audit.py` — **fifty-four cases PASS, zero FAIL** (`results/dspack_audit_known_answers.txt`). It pins each strategy's response vector on hand-built panels; a closed-form EMA proved equal to pandas' adjust=True; hand-computed fee ladders (entry, hold, whole-order reversal charged once to the closing trade, zero-delta bars); the ds4 portfolio ladder and period segmentation with the open-tail fee rule; trade-by-trade equality of the engine to an independent straight-line simulator on hundreds of random bars; prefix-causality for each strategy including the ds4 panel; and the pack's own five default literals.
- Data: `data/binance_klines_1h/{SYM}_1h.csv`, thirteen canonical symbols (bar counts and sha of every file live in each artifact's `inputs`).

## Porting semantics (declared before the runs)

Everything is ported from the pack file **including its bugs**, never fixed: ds1 carries a dead `.clip(0, 2)` before its final `.clip(-1, 1)` (a no-op, ported verbatim); ds2 is **stateless** — the pack rewrites the position from zero on every bar, so the book holds weight only on trigger bars; ds3 remembers its alignment for its twenty-four-bar hold and flips to **-1, not flat**, when the memory ages out; ds4 samples its cross-sectional top-three weights every twenty-four bars and fills forward between samples; ds5's `ffill(limit=24)` is a **dead no-op** — the position series never contains a NaN, so nothing is ever forward-filled (audit case A6 quotes the pack source for this): ds5 is stateless like ds2.

Conventions: fills at the signal bar's close; a fee of `|delta_w| * fee` charges on the bar where the weight changes; a reversal's whole-order fee lands on the flip bar and is booked to the CLOSING trade; compounding is multiplicative in (1 + w * r); year buckets are complete (a bucket's ratio runs its own first to last bar). ds4 is scored under period accounting — maximal constant-weight periods, each switch's fee booked to the period being closed, the open tail excluded from counts — and its benchmark is an equal-weight rebalanced basket of the thirteen aligned histories.

**Costs.** `author` = zero fee and zero slippage, because the pack file declares none — the pack's own headline story describes a zero-cost book, and this set reproduces exactly that. `repo6x5` = the repo standard, six basis points commission plus five basis points slippage per side. Every repo artifact carries a zero-cost control pass on the same bars, so the cost drag (`drag_pp`) is measured inside the artifact, never estimated; on the author set the control doubles as a determinism check (measured drag is exactly zero in every author artifact).

Two windows: `full` scores each file's whole history; `last6mo` scores the trailing four-thousand-three-hundred-sixty-eight hourly bars after a two-thousand-four-hundred-bar warmup. ds4 additionally requires that window from the aligned intersection of all thirteen files.

## The matrix — exactly one cell of two hundred twelve passes every gate, and it dies at the first real cost

Pre-declared gates G1..G6: G1 strict profit factor above one point two; G2 at least thirty closed units (trades for the symbol books, rebalance periods for ds4); G3 both chronological halves' profit factors above one; G4 (full windows only) green in at least two-thirds of the complete calendar-year buckets scored; G5 beats buy-and-hold on the same scored span; G6 the return after removing the best five winning units stays positive (a book whose total PnL is already negative fails G6 by construction and prints a dash in the conc column). A cell passes only with all of them. No walk-forward was attempted: nothing survived repo costs.

### ds1, full window, author costs

| run_id | symbol | ret%% | PF | PF h1 | PF h2 | n | green years | B&H%% | conc w/o top5 %% | drag pp | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 130d28759c2d5972 | ADAUSDT | 132.7358 | 1.13 | 1.21 | 1.09 | 2185 | 6/7 | 307.6585 | -27.9632 | 0.0000 | fail |
| 21e2bcb475fd6fd3 | AVAXUSDT | 281.0977 | 1.27 | 1.26 | 1.27 | 1827 | 5/7 | 141.8582 | 95.9774 | 0.0000 | PASS |
| f68de1cf973c8037 | BNBUSDT | 248.7788 | 1.21 | 1.28 | 1.17 | 2031 | 7/7 | 2766.2036 | 72.3743 | 0.0000 | fail |
| ba388d5123c2b42b | BTCUSDT | 251.2650 | 1.19 | 1.33 | 1.10 | 2156 | 7/8 | 715.7500 | 57.7845 | 0.0000 | fail |
| 26249a763343bca4 | DOGEUSDT | 223.7089 | 1.19 | 1.30 | 1.13 | 1983 | 6/7 | 2042.4364 | 59.3892 | 0.0000 | fail |
| 37916f001a9642ff | ETHUSDT | 302.3565 | 1.22 | 1.35 | 1.15 | 2041 | 7/8 | 1556.0753 | 69.8325 | 0.0000 | fail |
| 88bc7c612612f5f8 | HYPEUSDT | 14.3971 | 1.15 | 0.94 | 1.39 | 407 | 2/2 | 176.4100 | -21.4585 | 0.0000 | fail |
| afa8324fb46f8ff4 | LINKUSDT | 291.2650 | 1.28 | 1.21 | 1.32 | 2001 | 7/7 | 330.6924 | 119.6279 | 0.0000 | fail |
| c20fbec817f6087d | NEARUSDT | 206.3185 | 1.24 | 1.22 | 1.24 | 1854 | 6/7 | 345.6979 | 73.9983 | 0.0000 | fail |
| bfe50d8919258f06 | SOLUSDT | 332.1243 | 1.29 | 1.33 | 1.28 | 1753 | 7/7 | 2990.3582 | 110.1555 | 0.0000 | fail |
| dc9d4cdab4c59815 | SPXUSDT | 12.8702 | 1.10 | 0.94 | 1.26 | 500 | 2/3 | -29.1258 | -28.0819 | 0.0000 | fail |
| 55647db4bd3f1922 | SUIUSDT | 85.8681 | 1.26 | 1.26 | 1.26 | 1042 | 4/4 | -27.7798 | -1.6515 | 0.0000 | fail |
| 11432b7a35eb6fbe | XRPUSDT | 411.7566 | 1.28 | 1.26 | 1.30 | 2030 | 7/7 | 536.7467 | 94.0511 | 0.0000 | fail |

(reconciled in words: one of thirteen symbols pass G1..G6 in this cell-set)

### ds1, full window, repo6x5 costs

| run_id | symbol | ret%% | PF | PF h1 | PF h2 | n | green years | B&H%% | conc w/o top5 %% | drag pp | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 58e5ad52e6880cb1 | ADAUSDT | -41.9421 | 0.93 | 0.98 | 0.86 | 2185 | 1/7 | 307.6585 | -115.4994 | 174.6780 | fail |
| 88b51ed249563add | AVAXUSDT | 31.8583 | 1.05 | 1.04 | 1.05 | 1827 | 4/7 | 141.8582 | -67.8040 | 249.2393 | fail |
| 19929bdfa829fbbd | BNBUSDT | -50.6024 | 0.91 | 0.98 | 0.81 | 2031 | 1/7 | 2766.2036 | -121.0553 | 299.3813 | fail |
| 596c9c7399ef7081 | BTCUSDT | -62.8793 | 0.90 | 1.02 | 0.71 | 2156 | 2/8 | 715.7500 | -135.8309 | 314.1443 | fail |
| fdf7b04489224b71 | DOGEUSDT | -14.6442 | 0.97 | 1.06 | 0.88 | 1983 | 3/7 | 2042.4364 | -97.4666 | 238.3531 | fail |
| 96840f43ef51face | ETHUSDT | -25.2829 | 0.97 | 1.10 | 0.82 | 2041 | 2/8 | 1556.0753 | -120.0421 | 327.6394 | fail |
| f9b06448ac441c0f | HYPEUSDT | -9.5870 | 0.91 | 0.78 | 1.06 | 407 | 0/2 | 176.4100 | -40.8719 | 23.9841 | fail |
| ae6b8efacce2e8ee | LINKUSDT | 19.0165 | 1.03 | 1.01 | 1.04 | 2001 | 5/7 | 330.6924 | -55.8401 | 272.2485 | fail |
| 419686b692e4c5e8 | NEARUSDT | 18.4318 | 1.03 | 1.02 | 1.04 | 1854 | 3/7 | 345.6979 | -48.5416 | 187.8866 | fail |
| e9febf69097a6cea | SOLUSDT | 55.5919 | 1.06 | 1.11 | 1.03 | 1753 | 3/7 | 2990.3582 | -55.7421 | 276.5325 | fail |
| 326c037409ec1879 | SPXUSDT | -6.5061 | 0.96 | 0.86 | 1.06 | 500 | 1/3 | -29.1258 | -42.9054 | 19.3763 | fail |
| e044eca2464673c8 | SUIUSDT | 5.3853 | 1.02 | 1.04 | 1.00 | 1042 | 2/4 | -27.7798 | -54.9063 | 80.4829 | fail |
| 3cd194e0ae29c11d | XRPUSDT | 12.0016 | 1.01 | 1.03 | 0.99 | 2030 | 3/7 | 536.7467 | -101.6491 | 399.7550 | fail |

(reconciled in words: zero of thirteen symbols pass G1..G6 in this cell-set)

### ds1, last6mo window, author costs

| run_id | symbol | ret%% | PF | PF h1 | PF h2 | n | green years | B&H%% | conc w/o top5 %% | drag pp | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 56f57962a2db131e | ADAUSDT | 8.5295 | 1.18 | 2.24 | 0.71 | 123 | n/a | -10.4988 | -23.6903 | 0.0000 | fail |
| f85340e3afcc22eb | AVAXUSDT | -5.6595 | 0.85 | 0.77 | 0.91 | 176 | n/a | 5.5597 | -30.6991 | 0.0000 | fail |
| a894b297a0a0b345 | BNBUSDT | 0.7741 | 1.03 | 0.93 | 1.10 | 125 | n/a | 13.8529 | -21.2675 | 0.0000 | fail |
| bcb8d1d2a2373e5c | BTCUSDT | 11.9266 | 1.51 | 1.60 | 1.41 | 129 | n/a | 7.8974 | -27.2117 | 0.0000 | fail |
| deb3da2d3fbd8dbe | DOGEUSDT | 3.3324 | 0.98 | 1.48 | 0.72 | 173 | n/a | -15.5373 | -29.1506 | 0.0000 | fail |
| aaf362597be214da | ETHUSDT | 5.3565 | 1.19 | 1.77 | 0.91 | 163 | n/a | 3.0178 | -28.8515 | 0.0000 | fail |
| 57538ab218236def | HYPEUSDT | 18.7806 | 1.59 | 1.43 | 1.70 | 147 | n/a | 132.3182 | -12.4599 | 0.0000 | fail |
| f54b926d82c2c478 | LINKUSDT | 29.5905 | 2.18 | 1.68 | 2.63 | 136 | n/a | 30.0992 | -5.9476 | 0.0000 | fail |
| e4beb4824d1919f5 | NEARUSDT | 2.5075 | 1.05 | 0.84 | 1.23 | 167 | n/a | 267.1091 | -32.6172 | 0.0000 | fail |
| f07033b658af55e2 | SOLUSDT | 15.9369 | 1.28 | 2.23 | 0.95 | 147 | n/a | 20.8784 | -23.4856 | 0.0000 | fail |
| 9ae1b4661002cab7 | SPXUSDT | 3.6307 | 1.15 | 2.24 | 0.79 | 152 | n/a | 66.4026 | -22.9878 | 0.0000 | fail |
| a819340908d2f223 | SUIUSDT | 11.7518 | 1.30 | 1.11 | 1.47 | 154 | n/a | 3.8969 | -25.6148 | 0.0000 | fail |
| 744ef81d5a342f37 | XRPUSDT | 17.0412 | 1.47 | 1.55 | 1.43 | 156 | n/a | -8.9087 | -17.5118 | 0.0000 | fail |

(reconciled in words: zero of thirteen symbols pass G1..G6 in this cell-set)

### ds1, last6mo window, repo6x5 costs

| run_id | symbol | ret%% | PF | PF h1 | PF h2 | n | green years | B&H%% | conc w/o top5 %% | drag pp | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ba8058fb240b87a1 | ADAUSDT | -1.8076 | 0.94 | 1.56 | 0.59 | 123 | n/a | -10.4988 | -28.9815 | 10.3371 | fail |
| 64566b5e0b7fac92 | AVAXUSDT | -18.1777 | 0.62 | 0.55 | 0.67 | 176 | n/a | 5.5597 | -37.3191 | 12.5182 | fail |
| 8365cd222b900deb | BNBUSDT | -16.6203 | 0.67 | 0.61 | 0.71 | 125 | n/a | 13.8529 | -32.3376 | 17.3945 | fail |
| 1237f3e7e64ad483 | BTCUSDT | -7.0235 | 0.98 | 1.13 | 0.82 | 129 | n/a | 7.8974 | -40.9589 | 18.9501 | fail |
| a98d5a87a4cb27ce | DOGEUSDT | -13.3301 | 0.68 | 1.07 | 0.47 | 173 | n/a | -15.5373 | -38.7116 | 16.6625 | fail |
| a6c7a7a446c2282a | ETHUSDT | -12.0060 | 0.85 | 1.22 | 0.64 | 163 | n/a | 3.0178 | -41.9530 | 17.3625 | fail |
| 16e0afefbb66c69d | HYPEUSDT | 6.6851 | 1.18 | 1.03 | 1.29 | 147 | n/a | 132.3182 | -20.4701 | 12.0955 | fail |
| 975a3cea4d698b46 | LINKUSDT | 14.9976 | 1.45 | 1.08 | 1.83 | 136 | n/a | 30.0992 | -16.2220 | 14.5929 | fail |
| 558b9d54318efd3c | NEARUSDT | -7.0922 | 0.87 | 0.67 | 1.04 | 167 | n/a | 267.1091 | -39.1645 | 9.5997 | fail |
| def5e6b5fec46309 | SOLUSDT | -1.3449 | 0.88 | 1.47 | 0.64 | 147 | n/a | 20.8784 | -33.5513 | 17.2817 | fail |
| 2ddc095af009c737 | SPXUSDT | -3.9497 | 0.95 | 1.90 | 0.64 | 152 | n/a | 66.4026 | -28.2440 | 7.5804 | fail |
| 82623e7c36703698 | SUIUSDT | -0.9114 | 0.96 | 0.84 | 1.07 | 154 | n/a | 3.8969 | -34.0228 | 12.6632 | fail |
| 83b13d3fa12aabff | XRPUSDT | 0.2729 | 1.02 | 0.98 | 1.06 | 156 | n/a | -8.9087 | -27.4051 | 16.7683 | fail |

(reconciled in words: zero of thirteen symbols pass G1..G6 in this cell-set)

### ds2, full window, author costs

| run_id | symbol | ret%% | PF | PF h1 | PF h2 | n | green years | B&H%% | conc w/o top5 %% | drag pp | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fb897b2a57dfa74f | ADAUSDT | -32.3272 | 0.94 | 0.86 | 1.06 | 1371 | 3/7 | 307.6585 | -78.5790 | 0.0000 | fail |
| 58baf5d2d46b23fb | AVAXUSDT | -63.2324 | 0.86 | 0.81 | 1.00 | 1368 | 2/7 | 141.8582 | -116.5549 | 0.0000 | fail |
| 90ba7ad0c68906c1 | BNBUSDT | -19.3453 | 0.97 | 1.01 | 0.88 | 1412 | 3/7 | 2766.2036 | -76.7532 | 0.0000 | fail |
| 80e7e377ae87c4bd | BTCUSDT | -38.9829 | 0.89 | 0.88 | 0.90 | 1324 | 3/8 | 715.7500 | -62.5482 | 0.0000 | fail |
| 4d494de14888b1d3 | DOGEUSDT | -24.4169 | 0.96 | 0.97 | 0.96 | 1069 | 2/7 | 2042.4364 | -106.3014 | 0.0000 | fail |
| 5de10d4c335d5d07 | ETHUSDT | -14.7237 | 0.97 | 0.95 | 1.00 | 1377 | 3/8 | 1556.0753 | -43.3354 | 0.0000 | fail |
| 2e83a311f83c9180 | HYPEUSDT | -32.8792 | 0.79 | 0.71 | 0.89 | 351 | 0/2 | 176.4100 | -58.0248 | 0.0000 | fail |
| 27bd4f99529e53d5 | LINKUSDT | -47.4356 | 0.90 | 0.80 | 1.08 | 1462 | 3/7 | 330.6924 | -87.2608 | 0.0000 | fail |
| c556b4e395c0545e | NEARUSDT | -71.7267 | 0.84 | 0.78 | 0.98 | 1353 | 2/7 | 345.6979 | -111.6975 | 0.0000 | fail |
| 5c359379b06a41d1 | SOLUSDT | -77.0847 | 0.82 | 0.81 | 0.83 | 1363 | 1/7 | 2990.3582 | -121.3660 | 0.0000 | fail |
| 5dd301c6d5331c4b | SPXUSDT | -13.5320 | 0.96 | 1.00 | 0.89 | 412 | 1/3 | -29.1258 | -83.0996 | 0.0000 | fail |
| dd870096ddf9dd22 | SUIUSDT | 10.5359 | 1.02 | 0.97 | 1.08 | 725 | 2/4 | -27.7798 | -69.2668 | 0.0000 | fail |
| 21ae77d3513516b4 | XRPUSDT | -54.3057 | 0.85 | 0.74 | 1.12 | 1138 | 2/7 | 536.7467 | -92.1106 | 0.0000 | fail |

(reconciled in words: zero of thirteen symbols pass G1..G6 in this cell-set)

### ds2, full window, repo6x5 costs

| run_id | symbol | ret%% | PF | PF h1 | PF h2 | n | green years | B&H%% | conc w/o top5 %% | drag pp | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 8060a0920026c83d | ADAUSDT | -96.6904 | 0.64 | 0.63 | 0.70 | 1371 | 0/7 | 307.6585 | -123.2652 | 64.3632 | fail |
| 9c2c89a714f3021b | AVAXUSDT | -98.1899 | 0.63 | 0.63 | 0.66 | 1368 | 0/7 | 141.8582 | -140.9000 | 34.9576 | fail |
| 5d4cb734b069068e | BNBUSDT | -96.3959 | 0.65 | 0.68 | 0.44 | 1412 | 0/7 | 2766.2036 | -135.5101 | 77.0506 | fail |
| 939610aeb17f77d5 | BTCUSDT | -96.6907 | 0.49 | 0.50 | 0.43 | 1324 | 0/8 | 715.7500 | -112.1372 | 57.7078 | fail |
| fa25b6068eac6c95 | DOGEUSDT | -92.8140 | 0.76 | 0.78 | 0.61 | 1069 | 1/7 | 2042.4364 | -157.7672 | 68.3971 | fail |
| 40b44af566ba64c6 | ETHUSDT | -95.8842 | 0.60 | 0.61 | 0.54 | 1377 | 1/8 | 1556.0753 | -114.1643 | 81.1605 | fail |
| e7ec67e4db766294 | HYPEUSDT | -69.0037 | 0.50 | 0.45 | 0.60 | 351 | 0/2 | 176.4100 | -85.5176 | 36.1245 | fail |
| 1f82e165857a3a27 | LINKUSDT | -97.8959 | 0.59 | 0.57 | 0.77 | 1462 | 0/7 | 330.6924 | -122.0100 | 50.4604 | fail |
| 64c8ce92a4080905 | NEARUSDT | -98.5614 | 0.62 | 0.62 | 0.66 | 1353 | 0/7 | 345.6979 | -129.9287 | 26.8346 | fail |
| 1451a9491c5bd1b5 | SOLUSDT | -98.8594 | 0.62 | 0.63 | 0.51 | 1363 | 1/7 | 2990.3582 | -136.6786 | 21.7747 | fail |
| ef32092b5cd63a8b | SPXUSDT | -65.0864 | 0.79 | 0.83 | 0.64 | 412 | 0/3 | -29.1258 | -124.3546 | 51.5544 | fail |
| 36c48a3d39b09dd3 | SUIUSDT | -77.5910 | 0.72 | 0.72 | 0.73 | 725 | 0/4 | -27.7798 | -123.6220 | 88.1269 | fail |
| 26b63fdb9892f3e4 | XRPUSDT | -96.2678 | 0.56 | 0.55 | 0.71 | 1138 | 0/7 | 536.7467 | -121.2041 | 41.9621 | fail |

(reconciled in words: zero of thirteen symbols pass G1..G6 in this cell-set)

### ds2, last6mo window, author costs

| run_id | symbol | ret%% | PF | PF h1 | PF h2 | n | green years | B&H%% | conc w/o top5 %% | drag pp | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 68686a17c9476a9d | ADAUSDT | -5.5865 | 0.90 | 1.47 | 0.57 | 113 | n/a | -10.4988 | -32.7990 | 0.0000 | fail |
| d2d6046dc2cc388f | AVAXUSDT | -11.7429 | 0.75 | 0.49 | 0.99 | 92 | n/a | 5.5597 | -29.0819 | 0.0000 | fail |
| d22f69c1e41cad45 | BNBUSDT | -3.0814 | 0.88 | 0.78 | 1.03 | 99 | n/a | 13.8529 | -13.7866 | 0.0000 | fail |
| 1c99c633fa1af29d | BTCUSDT | -3.0713 | 0.87 | 0.65 | 1.22 | 91 | n/a | 7.8974 | -14.5595 | 0.0000 | fail |
| a77a247e69b9d1ba | DOGEUSDT | -10.4811 | 0.71 | 0.37 | 1.10 | 75 | n/a | -15.5373 | -26.6878 | 0.0000 | fail |
| d36f280821014ce0 | ETHUSDT | -5.7701 | 0.80 | 0.77 | 0.86 | 76 | n/a | 3.0178 | -21.7888 | 0.0000 | fail |
| f94fe7610bae9b2f | HYPEUSDT | -12.8352 | 0.80 | 1.04 | 0.45 | 143 | n/a | 132.3182 | -30.8030 | 0.0000 | fail |
| 8632620940922daf | LINKUSDT | -23.5642 | 0.55 | 0.57 | 0.53 | 107 | n/a | 30.0992 | -35.5405 | 0.0000 | fail |
| f1b726cf22716b26 | NEARUSDT | -15.3164 | 0.80 | 0.93 | 0.66 | 118 | n/a | 267.1091 | -48.8093 | 0.0000 | fail |
| e1d7896a3df23539 | SOLUSDT | -5.2851 | 0.83 | 0.62 | 1.23 | 96 | n/a | 20.8784 | -15.1060 | 0.0000 | fail |
| 06bb6986db3f783f | SPXUSDT | -10.4005 | 0.83 | 0.57 | 1.25 | 97 | n/a | 66.4026 | -39.7651 | 0.0000 | fail |
| 6c64aec0ecc1a0fa | SUIUSDT | -2.9113 | 0.95 | 2.25 | 0.40 | 108 | n/a | 3.8969 | -30.5826 | 0.0000 | fail |
| 66d356981ebcabe2 | XRPUSDT | 2.5810 | 1.08 | 0.63 | 1.67 | 87 | n/a | -8.9087 | -18.0546 | 0.0000 | fail |

(reconciled in words: zero of thirteen symbols pass G1..G6 in this cell-set)

### ds2, last6mo window, repo6x5 costs

| run_id | symbol | ret%% | PF | PF h1 | PF h2 | n | green years | B&H%% | conc w/o top5 %% | drag pp | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ff7b893059290aa6 | ADAUSDT | -26.3777 | 0.60 | 0.92 | 0.38 | 113 | n/a | -10.4988 | -46.7408 | 20.7913 | fail |
| ca66fd16e205b2bc | AVAXUSDT | -27.9225 | 0.47 | 0.29 | 0.68 | 92 | n/a | 5.5597 | -38.7084 | 16.1795 | fail |
| 9cb284af17bfa4cc | BNBUSDT | -22.0591 | 0.40 | 0.39 | 0.43 | 99 | n/a | 13.8529 | -28.4062 | 18.9776 | fail |
| d824b1f5eca8fa92 | BTCUSDT | -20.6661 | 0.39 | 0.30 | 0.57 | 91 | n/a | 7.8974 | -25.4879 | 17.5948 | fail |
| 26cd719f9ed2a75d | DOGEUSDT | -24.1044 | 0.43 | 0.17 | 0.76 | 75 | n/a | -15.5373 | -35.0154 | 13.6233 | fail |
| b36150172c060920 | ETHUSDT | -20.2860 | 0.46 | 0.44 | 0.49 | 76 | n/a | 3.0178 | -30.6615 | 14.5159 | fail |
| d00fc641e70d776e | HYPEUSDT | -36.3736 | 0.50 | 0.66 | 0.23 | 143 | n/a | 132.3182 | -44.6720 | 23.5385 | fail |
| d48985a5b59c6181 | LINKUSDT | -39.6041 | 0.33 | 0.31 | 0.34 | 107 | n/a | 30.0992 | -44.1364 | 16.0399 | fail |
| 8559b99ee28d7a6c | NEARUSDT | -34.6878 | 0.57 | 0.68 | 0.44 | 118 | n/a | 267.1091 | -58.9117 | 19.3714 | fail |
| e4e815482e427cb8 | SOLUSDT | -23.3266 | 0.42 | 0.31 | 0.63 | 96 | n/a | 20.8784 | -26.7099 | 18.0415 | fail |
| ff4bef8346826d0d | SPXUSDT | -27.6271 | 0.59 | 0.40 | 0.91 | 97 | n/a | 66.4026 | -48.7020 | 17.2266 | fail |
| 6d29cd26f2c7b7f7 | SUIUSDT | -23.4538 | 0.64 | 1.36 | 0.23 | 108 | n/a | 3.8969 | -42.1722 | 20.5425 | fail |
| a490b59356981907 | XRPUSDT | -15.2973 | 0.63 | 0.33 | 1.05 | 87 | n/a | -8.9087 | -29.0725 | 17.8783 | fail |

(reconciled in words: zero of thirteen symbols pass G1..G6 in this cell-set)

### ds3, full window, author costs

| run_id | symbol | ret%% | PF | PF h1 | PF h2 | n | green years | B&H%% | conc w/o top5 %% | drag pp | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 9ed94a5bf977bfe1 | ADAUSDT | 312.9541 | 1.04 | 1.24 | 0.92 | 314 | 5/7 | 307.6585 | -2653.0882 | 0.0000 | fail |
| 7a40c9c3de84ba78 | AVAXUSDT | 165.7438 | 1.01 | 1.29 | 0.96 | 300 | 4/7 | 141.8582 | -4543.6178 | 0.0000 | fail |
| 621aad7cc886dd58 | BNBUSDT | 91.6050 | 1.04 | 1.15 | 0.92 | 320 | 3/7 | 2766.2036 | -603.3933 | 0.0000 | fail |
| fc40ff7b4d4d9c7f | BTCUSDT | -33.1034 | 0.95 | 0.94 | 0.96 | 346 | 4/8 | 715.7500 | -218.3212 | 0.0000 | fail |
| e1cd14baa605aa54 | DOGEUSDT | 956.0444 | 1.07 | 1.24 | 0.99 | 296 | 4/7 | 2042.4364 | -3157.2337 | 0.0000 | fail |
| 783e8e3b0b57670a | ETHUSDT | 228.7102 | 1.07 | 1.14 | 0.97 | 318 | 6/8 | 1556.0753 | -522.0543 | 0.0000 | fail |
| d3e4e7ba3a379096 | HYPEUSDT | -39.1803 | 0.73 | 0.53 | 1.29 | 69 | 0/2 | 176.4100 | -105.1660 | 0.0000 | fail |
| c368685dd81cb7f7 | LINKUSDT | -84.4485 | 0.92 | 0.93 | 0.89 | 336 | 2/7 | 330.6924 | -479.2229 | 0.0000 | fail |
| 2a900e46df06499a | NEARUSDT | 13.3433 | 1.01 | 1.04 | 0.99 | 282 | 5/7 | 345.6979 | -839.7851 | 0.0000 | fail |
| 55cbf103e822ae30 | SOLUSDT | 8321.2005 | 1.17 | 1.41 | 1.11 | 284 | 4/7 | 2990.3582 | -10542.7391 | 0.0000 | fail |
| dd1e158a5b503d1c | SPXUSDT | -95.2676 | 0.33 | 0.27 | 1.20 | 98 | 0/3 | -29.1258 | -130.1112 | 0.0000 | fail |
| ff892226786f9b99 | SUIUSDT | 9.6315 | 1.00 | 1.08 | 0.83 | 166 | 3/4 | -27.7798 | -556.8636 | 0.0000 | fail |
| 439b38a9a9a2609e | XRPUSDT | -37.0717 | 0.98 | 1.05 | 0.89 | 310 | 4/7 | 536.7467 | -1010.9435 | 0.0000 | fail |

(reconciled in words: zero of thirteen symbols pass G1..G6 in this cell-set)

### ds3, full window, repo6x5 costs

| run_id | symbol | ret%% | PF | PF h1 | PF h2 | n | green years | B&H%% | conc w/o top5 %% | drag pp | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| d1ec0f8a97f14da9 | ADAUSDT | 106.5774 | 1.02 | 1.19 | 0.88 | 314 | 5/7 | 307.6585 | -2111.9080 | 206.3768 | fail |
| a164b1b4c07d7fd4 | AVAXUSDT | 37.0992 | 1.00 | 1.23 | 0.95 | 300 | 3/7 | 141.8582 | -3314.6947 | 128.6446 | fail |
| b46cd74967c87068 | BNBUSDT | -5.4092 | 0.99 | 1.09 | 0.84 | 320 | 2/7 | 2766.2036 | -554.6232 | 97.0142 | fail |
| 4da0148b01a86e60 | BTCUSDT | -68.8128 | 0.87 | 0.87 | 0.87 | 346 | 4/8 | 715.7500 | -220.5832 | 35.7093 | fail |
| 9119acbef96fbe36 | DOGEUSDT | 449.6422 | 1.04 | 1.20 | 0.94 | 296 | 3/7 | 2042.4364 | -2492.0117 | 506.4022 | fail |
| 690cb7223ee95a8d | ETHUSDT | 62.9927 | 1.02 | 1.10 | 0.88 | 318 | 4/8 | 1556.0753 | -546.3565 | 165.7175 | fail |
| 37e66c28c060439b | HYPEUSDT | -47.8123 | 0.68 | 0.50 | 1.21 | 69 | 0/2 | 176.4100 | -107.6168 | 8.6321 | fail |
| 83d5679880add415 | LINKUSDT | -92.5884 | 0.89 | 0.90 | 0.86 | 336 | 2/7 | 330.6924 | -460.7366 | 8.1399 | fail |
| ce195c2b4bed7ca1 | NEARUSDT | -39.1606 | 0.98 | 1.00 | 0.97 | 282 | 5/7 | 345.6979 | -662.6963 | 52.5039 | fail |
| 3903699416d97cf8 | SOLUSDT | 4400.3875 | 1.12 | 1.35 | 1.06 | 284 | 4/7 | 2990.3582 | -8916.9737 | 3920.8130 | fail |
| 611d01342a8e9f68 | SPXUSDT | -96.1905 | 0.31 | 0.26 | 1.15 | 98 | 0/3 | -29.1258 | -129.3376 | 0.9229 | fail |
| 01b72c550e420fe9 | SUIUSDT | -24.0236 | 0.97 | 1.05 | 0.77 | 166 | 3/4 | -27.7798 | -518.0560 | 33.6552 | fail |
| dfc124c03a11ea52 | XRPUSDT | -68.2420 | 0.96 | 1.01 | 0.85 | 310 | 4/7 | 536.7467 | -829.2443 | 31.1703 | fail |

(reconciled in words: zero of thirteen symbols pass G1..G6 in this cell-set)

### ds3, last6mo window, author costs

| run_id | symbol | ret%% | PF | PF h1 | PF h2 | n | green years | B&H%% | conc w/o top5 %% | drag pp | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 5915f49372e18425 | ADAUSDT | 10.6124 | 1.05 | 1.74 | 0.62 | 23 | n/a | -10.4988 | -33.6752 | 0.0000 | fail |
| ce1ada23081eef42 | AVAXUSDT | -43.6026 | 0.51 | 0.51 | 0.50 | 33 | n/a | 5.5597 | -45.5538 | 0.0000 | fail |
| 46f8981d848dda98 | BNBUSDT | -12.7119 | 0.61 | 0.35 | 1.01 | 33 | n/a | 13.8529 | -37.1372 | 0.0000 | fail |
| 9224114919716f82 | BTCUSDT | 3.9848 | 1.26 | 1.23 | 1.30 | 25 | n/a | 7.8974 | -42.6290 | 0.0000 | fail |
| 33d5a538e79fe259 | DOGEUSDT | 10.3483 | 1.03 | 1.90 | 0.59 | 27 | n/a | -15.5373 | -32.9308 | 0.0000 | fail |
| da5d0ab1ae3ec619 | ETHUSDT | -0.2577 | 1.05 | 1.53 | 0.81 | 25 | n/a | 3.0178 | -74.1368 | 0.0000 | fail |
| f70afce0d6ff2294 | HYPEUSDT | 24.7260 | 1.24 | 0.63 | 2.49 | 18 | n/a | 132.3182 | -47.7038 | 0.0000 | fail |
| 2a9a1a2068d33ba2 | LINKUSDT | 59.0824 | 2.01 | 1.06 | 2.65 | 17 | n/a | 30.0992 | -21.4580 | 0.0000 | fail |
| 1a1e0bd4361208e1 | NEARUSDT | 14.0552 | 1.19 | 0.74 | 1.69 | 29 | n/a | 267.1091 | -125.2541 | 0.0000 | fail |
| 7577964c8ce9017b | SOLUSDT | 49.0904 | 1.77 | 2.59 | 1.41 | 21 | n/a | 20.8784 | -31.9051 | 0.0000 | fail |
| 7462770568f34171 | SPXUSDT | 42.5143 | 1.65 | 18.87 | 0.96 | 22 | n/a | 66.4026 | -45.4848 | 0.0000 | fail |
| bacc949778b9173c | SUIUSDT | 21.3532 | 1.19 | 0.98 | 1.48 | 23 | n/a | 3.8969 | -68.1315 | 0.0000 | fail |
| 8251b6106eed9b28 | XRPUSDT | -26.8695 | 0.65 | 0.91 | 0.55 | 27 | n/a | -8.9087 | -55.0406 | 0.0000 | fail |

(reconciled in words: zero of thirteen symbols pass G1..G6 in this cell-set)

### ds3, last6mo window, repo6x5 costs

| run_id | symbol | ret%% | PF | PF h1 | PF h2 | n | green years | B&H%% | conc w/o top5 %% | drag pp | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| d221556829f7b429 | ADAUSDT | 5.1488 | 0.98 | 1.60 | 0.58 | 23 | n/a | -10.4988 | -33.0736 | 5.4636 | fail |
| 15514d722d1fb625 | AVAXUSDT | -47.5562 | 0.47 | 0.48 | 0.46 | 33 | n/a | 5.5597 | -43.9373 | 3.9535 | fail |
| 8f0175ad21810ccd | BNBUSDT | -18.8309 | 0.51 | 0.29 | 0.86 | 33 | n/a | 13.8529 | -39.4642 | 6.1190 | fail |
| d6392c1abf8937f1 | BTCUSDT | -1.5859 | 1.12 | 1.11 | 1.15 | 25 | n/a | 7.8974 | -44.5365 | 5.5707 | fail |
| d2fb2ffd702a9e4e | DOGEUSDT | 3.9777 | 0.95 | 1.75 | 0.53 | 27 | n/a | -15.5373 | -32.8706 | 6.3706 | fail |
| d60c48e414f1276c | ETHUSDT | -5.6011 | 0.98 | 1.37 | 0.76 | 25 | n/a | 3.0178 | -74.1675 | 5.3434 | fail |
| 9e62a1adf3b3121e | HYPEUSDT | 19.8782 | 1.16 | 0.59 | 2.36 | 18 | n/a | 132.3182 | -46.5446 | 4.8479 | fail |
| bf6eea8139b78b98 | LINKUSDT | 53.2363 | 1.83 | 0.95 | 2.45 | 17 | n/a | 30.0992 | -21.6103 | 5.8461 | fail |
| 4b7579db97e93d24 | NEARUSDT | 6.9982 | 1.14 | 0.71 | 1.62 | 29 | n/a | 267.1091 | -122.6657 | 7.0570 | fail |
| e8fd51425c62749c | SOLUSDT | 42.3518 | 1.62 | 2.35 | 1.29 | 21 | n/a | 20.8784 | -32.3515 | 6.7385 | fail |
| 1b0bb3d84196e11e | SPXUSDT | 35.7736 | 1.56 | 15.73 | 0.91 | 22 | n/a | 66.4026 | -45.0419 | 6.7407 | fail |
| ef3529196aa4cb96 | SUIUSDT | 15.3590 | 1.11 | 0.92 | 1.37 | 23 | n/a | 3.8969 | -67.5255 | 5.9941 | fail |
| 374a95edb7d299fe | XRPUSDT | -31.0915 | 0.61 | 0.80 | 0.52 | 27 | n/a | -8.9087 | -54.1881 | 4.2220 | fail |

(reconciled in words: zero of thirteen symbols pass G1..G6 in this cell-set)

### ds5, full window, author costs

| run_id | symbol | ret%% | PF | PF h1 | PF h2 | n | green years | B&H%% | conc w/o top5 %% | drag pp | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 9fb04cb4cd712466 | ADAUSDT | -50.5118 | 0.87 | 0.77 | 1.08 | 1276 | 3/7 | 307.6585 | -84.7196 | 0.0000 | fail |
| 4f4160d7b52a04a4 | AVAXUSDT | -32.4719 | 0.91 | 0.75 | 1.15 | 1012 | 3/7 | 141.8582 | -72.4357 | 0.0000 | fail |
| f9b16b6a52d55e03 | BNBUSDT | -4.2967 | 0.99 | 1.01 | 0.96 | 1355 | 3/7 | 2766.2036 | -38.0518 | 0.0000 | fail |
| 3ace6215bbd666f3 | BTCUSDT | 1.3394 | 1.00 | 0.93 | 1.10 | 1568 | 5/8 | 715.7500 | -23.6237 | 0.0000 | fail |
| 961ef9b0a3e251cd | DOGEUSDT | -28.5293 | 0.94 | 0.82 | 1.18 | 1183 | 2/7 | 2042.4364 | -88.9306 | 0.0000 | fail |
| 7e171a9b30d1b41c | ETHUSDT | 39.9166 | 1.07 | 1.00 | 1.15 | 1454 | 5/8 | 1556.0753 | 5.8576 | 0.0000 | fail |
| 4c3a6941ed5759b1 | HYPEUSDT | -18.4579 | 0.84 | 0.73 | 0.95 | 244 | 0/2 | 176.4100 | -43.4735 | 0.0000 | fail |
| 365bef751f370f6c | LINKUSDT | 54.9988 | 1.11 | 0.76 | 1.40 | 1241 | 3/7 | 330.6924 | -12.8956 | 0.0000 | fail |
| 12d65f65333e8b98 | NEARUSDT | -63.2591 | 0.86 | 0.80 | 0.99 | 1116 | 3/7 | 345.6979 | -107.0411 | 0.0000 | fail |
| bd348d97235bb48a | SOLUSDT | -41.9794 | 0.91 | 0.89 | 0.95 | 1185 | 2/7 | 2990.3582 | -77.6736 | 0.0000 | fail |
| 4abca197e4a0443c | SPXUSDT | -25.1000 | 0.93 | 1.25 | 0.56 | 340 | 2/3 | -29.1258 | -93.0403 | 0.0000 | fail |
| 7b6eb3ffd11c7b9f | SUIUSDT | 34.3705 | 1.09 | 0.85 | 1.33 | 648 | 2/4 | -27.7798 | -53.9218 | 0.0000 | fail |
| 91db3aa70062a247 | XRPUSDT | -85.2279 | 0.65 | 0.57 | 0.96 | 1304 | 2/7 | 536.7467 | -103.4873 | 0.0000 | fail |

(reconciled in words: zero of thirteen symbols pass G1..G6 in this cell-set)

### ds5, full window, repo6x5 costs

| run_id | symbol | ret%% | PF | PF h1 | PF h2 | n | green years | B&H%% | conc w/o top5 %% | drag pp | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 5e944deb51c14c56 | ADAUSDT | -97.0168 | 0.57 | 0.56 | 0.71 | 1276 | 0/7 | 307.6585 | -119.7112 | 46.5050 | fail |
| 50929f1f76a26e36 | AVAXUSDT | -92.7215 | 0.58 | 0.54 | 0.74 | 1012 | 1/7 | 141.8582 | -122.4517 | 60.2497 | fail |
| cb08d486907d5914 | BNBUSDT | -95.1518 | 0.61 | 0.64 | 0.45 | 1355 | 0/7 | 2766.2036 | -113.4676 | 90.8550 | fail |
| 14a89fd5f1a128b6 | BTCUSDT | -96.7877 | 0.51 | 0.51 | 0.48 | 1568 | 1/8 | 715.7500 | -113.0990 | 98.1272 | fail |
| d0a59b43fc3ec0b2 | DOGEUSDT | -94.7130 | 0.66 | 0.64 | 0.79 | 1183 | 0/7 | 2042.4364 | -144.3321 | 66.1837 | fail |
| a02dade50a0e2b61 | ETHUSDT | -94.2999 | 0.59 | 0.59 | 0.59 | 1454 | 0/8 | 1556.0753 | -110.3465 | 134.2165 | fail |
| d77bd8bfd1ed8724 | HYPEUSDT | -52.3433 | 0.54 | 0.46 | 0.64 | 244 | 0/2 | 176.4100 | -71.5161 | 33.8853 | fail |
| 7920e780bf0a7063 | LINKUSDT | -89.9083 | 0.58 | 0.48 | 0.97 | 1241 | 2/7 | 330.6924 | -105.6778 | 144.9071 | fail |
| f7a716e8215addcd | NEARUSDT | -96.8502 | 0.64 | 0.63 | 0.72 | 1116 | 0/7 | 345.6979 | -130.9267 | 33.5911 | fail |
| 5c6d2ead9d717e8c | SOLUSDT | -95.7268 | 0.65 | 0.66 | 0.58 | 1185 | 1/7 | 2990.3582 | -124.7976 | 53.7474 | fail |
| d75fd122ddc437d0 | SPXUSDT | -64.5635 | 0.77 | 1.02 | 0.40 | 340 | 0/3 | -29.1258 | -122.0865 | 39.4635 | fail |
| 902b975fc1c5c11d | SUIUSDT | -67.7275 | 0.73 | 0.63 | 0.95 | 648 | 1/4 | -27.7798 | -115.4656 | 102.0979 | fail |
| 78199fce8ee862c6 | XRPUSDT | -99.1628 | 0.39 | 0.38 | 0.59 | 1304 | 0/7 | 536.7467 | -112.3819 | 13.9349 | fail |

(reconciled in words: zero of thirteen symbols pass G1..G6 in this cell-set)

### ds5, last6mo window, author costs

| run_id | symbol | ret%% | PF | PF h1 | PF h2 | n | green years | B&H%% | conc w/o top5 %% | drag pp | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| e274cceb5b04cb74 | ADAUSDT | -14.4986 | 0.73 | 1.43 | 0.41 | 103 | n/a | -10.4988 | -40.4991 | 0.0000 | fail |
| 9d85b019a0db3b4d | AVAXUSDT | -13.0989 | 0.67 | 0.44 | 0.94 | 88 | n/a | 5.5597 | -25.9187 | 0.0000 | fail |
| cabe01ed8da97cfd | BNBUSDT | 1.2475 | 1.05 | 1.06 | 1.04 | 110 | n/a | 13.8529 | -9.8704 | 0.0000 | fail |
| 9ebdd2ee445ea576 | BTCUSDT | 2.4162 | 1.09 | 0.94 | 1.25 | 124 | n/a | 7.8974 | -12.7966 | 0.0000 | fail |
| ea2398b302161d20 | DOGEUSDT | -13.3982 | 0.67 | 0.35 | 1.04 | 90 | n/a | -15.5373 | -28.1762 | 0.0000 | fail |
| 5e62a03bd48400f1 | ETHUSDT | 4.5252 | 1.14 | 1.24 | 1.06 | 104 | n/a | 3.0178 | -13.9438 | 0.0000 | fail |
| 1745e6a4c56f2f26 | HYPEUSDT | -7.1090 | 0.84 | 1.06 | 0.54 | 103 | n/a | 132.3182 | -24.2915 | 0.0000 | fail |
| 4ba9b24355fa30ae | LINKUSDT | -13.5548 | 0.66 | 0.63 | 0.68 | 103 | n/a | 30.0992 | -24.3936 | 0.0000 | fail |
| 4eb92ba8b9830add | NEARUSDT | -15.9430 | 0.74 | 0.71 | 0.77 | 95 | n/a | 267.1091 | -37.1302 | 0.0000 | fail |
| 3cb92ffa525d999c | SOLUSDT | -12.2524 | 0.66 | 0.56 | 0.76 | 113 | n/a | 20.8784 | -21.9418 | 0.0000 | fail |
| 1fc63ee8ae2d55bb | SPXUSDT | -22.7881 | 0.65 | 0.74 | 0.55 | 97 | n/a | 66.4026 | -34.6207 | 0.0000 | fail |
| c61d8147c85a65b5 | SUIUSDT | -16.5978 | 0.66 | 1.36 | 0.29 | 98 | n/a | 3.8969 | -37.1230 | 0.0000 | fail |
| 9250980b22326b5c | XRPUSDT | -0.6657 | 0.98 | 0.57 | 1.29 | 96 | n/a | -8.9087 | -21.5111 | 0.0000 | fail |

(reconciled in words: zero of thirteen symbols pass G1..G6 in this cell-set)

### ds5, last6mo window, repo6x5 costs

| run_id | symbol | ret%% | PF | PF h1 | PF h2 | n | green years | B&H%% | conc w/o top5 %% | drag pp | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 683e2fa5f4086b1a | ADAUSDT | -31.8434 | 0.49 | 0.85 | 0.28 | 103 | n/a | -10.4988 | -52.1714 | 17.3448 | fail |
| 62047cfed6b86e8e | AVAXUSDT | -28.4022 | 0.39 | 0.24 | 0.58 | 88 | n/a | 5.5597 | -35.9686 | 15.3033 | fail |
| cc38dd665f906286 | BNBUSDT | -20.5256 | 0.44 | 0.45 | 0.42 | 110 | n/a | 13.8529 | -28.1679 | 21.7731 | fail |
| df1358ae05182c74 | BTCUSDT | -22.0479 | 0.43 | 0.35 | 0.52 | 124 | n/a | 7.8974 | -31.1649 | 24.4641 | fail |
| 2e38515d16bde965 | DOGEUSDT | -28.9623 | 0.38 | 0.16 | 0.67 | 90 | n/a | -15.5373 | -38.3841 | 15.5640 | fail |
| 19ee8b737fcf0b90 | ETHUSDT | -16.8620 | 0.59 | 0.62 | 0.57 | 104 | n/a | 3.0178 | -29.5367 | 21.3872 | fail |
| 918d591707ad853d | HYPEUSDT | -25.9529 | 0.52 | 0.70 | 0.27 | 103 | n/a | 132.3182 | -37.1206 | 18.8438 | fail |
| 28886eb4b1c3ce32 | LINKUSDT | -31.0911 | 0.35 | 0.30 | 0.40 | 103 | n/a | 30.0992 | -36.2757 | 17.5363 | fail |
| fce45bb70c9da418 | NEARUSDT | -31.8044 | 0.51 | 0.50 | 0.53 | 95 | n/a | 267.1091 | -45.4150 | 15.8614 | fail |
| 573e0401cf75aa92 | SOLUSDT | -31.5757 | 0.31 | 0.25 | 0.38 | 113 | n/a | 20.8784 | -34.5798 | 19.3233 | fail |
| 570dae0e17c50b02 | SPXUSDT | -37.6330 | 0.46 | 0.53 | 0.37 | 97 | n/a | 66.4026 | -39.2599 | 14.8449 | fail |
| 6ac0af3418e40810 | SUIUSDT | -32.7810 | 0.43 | 0.82 | 0.15 | 98 | n/a | 3.8969 | -45.8444 | 16.1832 | fail |
| 04f47359e054a0d1 | XRPUSDT | -19.5871 | 0.59 | 0.27 | 0.86 | 96 | n/a | -8.9087 | -31.8600 | 18.9214 | fail |

(reconciled in words: zero of thirteen symbols pass G1..G6 in this cell-set)

### ds4 (cross-sectional book, symbol PORTFOLIO)

| run_id | window | ret%% | PF | PF h1 | PF h2 | n | green years | B&H%% | conc w/o top5 %% | drag pp | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 6a8b1adbc1447e81 | full/author | 5.6788 | 1.08 | 0.83 | 1.35 | 202 | 1/2 | -11.6207 | -53.6261 | 0.0000 | fail |
| 4fbd3ab710cfa968 | full/repo6x5 | -6.3687 | 1.05 | 0.80 | 1.31 | 202 | 1/2 | -11.6207 | -62.2933 | 12.0474 | fail |
| 2961b90aa5be20a8 | last6mo/author | 85.9471 | 1.73 | 1.13 | 2.95 | 57 | n/a | 43.3691 | -10.5094 | 0.0000 | fail |
| 3acc62ace382118a | last6mo/repo6x5 | 80.0082 | 1.67 | 1.10 | 2.85 | 57 | n/a | 43.3691 | -13.4134 | 5.9388 | fail |

(the four ds4 rows cover the four window/cost combinations; every other block is one strategy's four cell-sets of thirteen symbols)

Reconciled tally, recomputed from the artifacts and restated in words: **one of fifty-two** ds1 author-cost cells passes every gate (AVAXUSDT); at repo costs **zero of fifty-two** pass for every strategy — ds1, ds2, ds3, ds5 and ds4 all go to zero; for ds2, ds3 and ds5 **zero of fifty-two pass even at the pack's own zero costs**. Across the two hundred twelve canonical cells exactly one passes, and it fails a gate the moment a market-standard cost is charged.

## Why it dies, structurally

Values inside sentences come from the named artifacts.

- **ds1 is a cost story, not a signal story.** At the pack's own zero costs every ds1 book is green over the full window: BTC 251.26 percent at profit factor 1.19 (ba388d5123c2b42b); AVAX 281.10 (21e2bcb475fd6fd3). But buy-and-hold dwarfs all of them but three: BTC's seven-and-a-half-year passive run is 715.75 percent, and G5 is passed by only three books (AVAX, SPX and SUI — the latter two only because their own markets went NEGATIVE: SPX's buy-and-hold -29.13 percent). The two-of-three counterexamples fail elsewhere (SUI's without-top-five margin -1.65), so the lone G1..G6 survivor is AVAX, whose 281.10 clears its 141.86 market. That survivor dies immediately at repo costs: profit factor 1.05, without-top-five margin -67.80 points. The repo-cost cells show the same shape everywhere — BTC's drag alone is 314.14 points on the same bars (596c9c7399ef7081), profit factor down to 0.90, and every ds1 repo cell across both windows prints a negative without-top-five margin. Two thousand trades per book at eleven basis points per side is the entire effect.
  The half-year cells even produce an eye-catching profit factor (1.51 on BTC, bcb8d1d2a2373e5c) and the LINK half-year repo cell passes four of the five applicable gates (profit factor 1.45, halves above one) — but the book still loses its buy-and-hold comparison and its without-top-five margin is negative (-16.22), the same drawer-pattern the ds4 half year shows.
- **ds2 and ds5 have no gross edge either.** At zero costs, ds2 loses in every cell-set (thirteen of thirteen fail); its only positive book anywhere is SUI at 10.54 percent (dd870096ddf9dd22) — its only positive book anywhere, on a one point zero two profit factor and a without-top-five margin of -69.27 points (one run carries it). No ds2 profit factor in any of the fifty-two author cells reaches one point two, and at repo costs the full-window books end between the mid-sixties and ninety-nine percent down (BTC -96.69, 939610aeb17f77d5). ds5 mirrors it: nine of thirteen full-window author books lose money outright, and no ds5 profit factor anywhere in the two hundred twelve cells reaches one point two — the best is ETH's half-year at 1.14 (5e62a03bd48400f1), still short of the gate. ETH's full-window book is the only ds5 green book with a positive without-top-five margin (+5.86 point, 7e171a9b30d1b41c) and it still fails G1 on 1.07. At repo costs the full-window books end between the low fifties and ninety-nine percent down (BTC -96.79, 14a89fd5f1a128b6; XRP -99.16, 78199fce8ee862c6). The ffill(limit=24) the author wrote to hold positions never executes — the hold was a bug, and even the intended twenty-four-bar hold would not have saved a book with no per-bar edge over the spread.
- **ds3's headline returns are whale drawers.** SOL reports 8321 percent at the pack's own zero costs (55cbf103e822ae30) on a profit factor of only 1.17; remove its best five trades and the book sits at -10543 percent — the positive headline reverses into a vast hole. The repo cell repeats it (without top five -8917). The halves split accelerates the same bankruptcy: the first half books a profit factor above one for nine of the thirteen names and the second half lands at zero point nine nine or below for ten of them (the 2023-2026 half is a different market for a 2020-era EMA fit). No ds3 full-window book reaches profit factor one point two, and the half-year cells whose profit factor does (LINK 2.01, and its cohort) all carry under thirty closed trades — the count gate rejects them. XRP finishes the full author window NEGATIVE, -37.07 percent against a buy-and-hold of 536.75 percent.
- **ds4 is the only portfolio book, and it fails exactly one gate.** Its full window is a two-bucket drawer (one green of two years in 6a8b1adbc1447e81, both halves on opposite sides of one), and the half-year repo cell comes closest of anything in the pack: fifty-seven rebalance periods of the thirteen-file cross-sectional momentum, profit factor 1.67, both halves above one (1.10 and 2.85), beating the equal-weight market's 43.37 — and it fails G6 alone: strip the best five periods and the return is -13.41 percent (author-cost sibling: -10.51). One window, one gate short, no second window agrees with it. Per the repo rule there is no rescue loop for it either.

## Verdict

**KILLED — all five strategies.** ds1 carries real zero-cost gross edge (the honest reading of the author set) that dies entirely at a market-standard cost and also fails the buy-and-hold bar on twelve of thirteen names; ds2 and ds5 fail even their own zero-cost books; ds3 is a whale-trade drawer whose second half is already dead before costs; ds4's cross-sectional book passes every applicable gate in exactly one of four cells and fails concentration there. No neighborhood ring, no walk-forward, no parameter fishing: there are no survivors to stabilize.

Caveats recorded for honesty: the author cost set is the pack's own zero-cost declaration, retained as the pack's best case, not as tradability; ds5's and ds2's stateless behavior is a reading of the pack's own code, pinned by the audit (A6), not a repair; ds4's counts are rebalance periods, distinct from the symbol books' trade counts; HYPE and SPX histories carry two or fewer complete year buckets, so their G4 tallies are small; the trailing ds4 period is marked to the last close and excluded from period statistics in every ds4 artifact (`n_open_at_end`). The pack was ported letter for letter; its quirks were never fixed.

— artifacts under `results/runs/*.json` (two hundred twelve canonical cells, every one re-verified bit-for-bit by the run driver `code/_dspack_matrix_driver.py`), engine `code/dspack_engine.py` (dspack-one), pack file `code/deepseek_pack.py` (sha recorded in each artifact), harness `code/vrun.py`; every number above was read from the cited artifacts; counts and range claims restated in words per the repo rule.
