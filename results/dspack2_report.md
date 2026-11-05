# dspack2 pack (DeepSeek strats six through nine) — verdict report

Built exclusively from `results/runs` artifacts of strategy `dspack2` (artifact count in words: **eighty-one**). Every literal number below is artifact-stored at its printed rounding; counted quantities are spelled out because counts are not stored anywhere.

- harness: `code/vrun.py`, adapter `dspack2`, engine `dspack2-1` (sources hashed into every run_id: `deepseek_pack2.py`, `dspack_engine.py`, `dspack2_engine.py`)
- author attachment copied byte-identical to `code/deepseek_pack2.py` (sha256 `bba9c6d61b57b370b4256dc9cadb802502fff4c9bcf9d39c740cbd1705f4b60d`)
- known-answer audit ran BEFORE any real-data run: `code/_dspack2_audit.py` → `results/dspack2_audit_known_answers.txt` — cases passed in words: **thirty-six**, failures in words: zero
- costs preset scored everywhere: `repo6x5` (six basis points taker fee plus five basis points slippage per side); every artifact also embeds the author's implicit zero-cost re-run (`ret_zero_pct`, `pf_zero`, `drag_pp = ret_zero − scored`)
- gates are the repo G-set: G1 strict profit factor above one-point-two; G2 at least thirty closed units; G3 both half-window profit factors above one; G4 green complete years two of three (full windows only); G5 beats buy and hold on the scored span; G6 the book stays green without its best five units.

## Verdict

**No strategy of this pack survives. All four are killed.**
- `ds6` (BB z-score reversion, ADX-gated): dead everywhere, both windows. Full window: **thirteen** of **thirteen** cells lost money; strict profit factors all below one (largest values in the table stay under it).
- `ds7` (RSI-2 Connors-style long book): the only pack member with positive cells under fees, but none pass the gates — the zero-cost signal is real yet fee-destroyed (details under `ds7 full` and the zero-cost section).
- `ds8` (BTC/ETH log-spread pairs, period accounting): negative in both windows under fees; at author costs the book still bleeds (zero-cost profit factor barely under one — no signal even gross).
- `ds9` (VWAP-deviation reversion): dead everywhere, both windows; the fee drag is catastrophic (roughly all of the notional in the worst cells).

## Data coverage (one-hour files; one row per symbol)

| run_id | file | bars | start | end |
|---|---|---:|---|---|
| 2e7b513e56bae8d9 | binance_klines_1h\ADAUSDT_1h.csv | 58836 | 2020-01-31 | 2026-10-17 |
| 16307043892ba806 | binance_klines_1h\AVAXUSDT_1h.csv | 53173 | 2020-09-23 | 2026-10-17 |
| 068738bad1d7bb57 | binance_klines_1h\BNBUSDT_1h.csv | 58596 | 2020-02-10 | 2026-10-17 |
| 1acd0fd6bf204925 | binance_klines_1h\BTCUSDT_1h.csv | 62307 | 2019-09-08 | 2026-10-17 |
| 2d7e8de58c50544f | binance_klines_1h\DOGEUSDT_1h.csv | 54971 | 2020-07-10 | 2026-10-17 |
| 05cff542c0f0064e | binance_klines_1h\ETHUSDT_1h.csv | 60397 | 2019-11-27 | 2026-10-17 |
| 6ce876d103e03e32 | binance_klines_1h\HYPEUSDT_1h.csv | 11624 | 2025-05-30 | 2026-09-26 |
| 3ff27adbf16bbf16 | binance_klines_1h\LINKUSDT_1h.csv | 59172 | 2020-01-17 | 2026-10-17 |
| 6283feea158ba8fb | binance_klines_1h\NEARUSDT_1h.csv | 52644 | 2020-10-15 | 2026-10-17 |
| 1a34d4913db8f73e | binance_klines_1h\SOLUSDT_1h.csv | 53389 | 2020-09-14 | 2026-10-17 |
| 0d8b2f00aa22b3b0 | binance_klines_1h\SPXUSDT_1h.csv | 15726 | 2024-12-10 | 2026-09-26 |
| 253c4211be5684cf | binance_klines_1h\SUIUSDT_1h.csv | 30316 | 2023-05-03 | 2026-10-17 |
| 3dc4af02c24e31a5 | binance_klines_1h\XRPUSDT_1h.csv | 59436 | 2020-01-06 | 2026-10-17 |

## ds6 — Bollinger z reversion, ADX gate — full

| run_id | symbol | n | ret_pct | PF | pf_h1 | pf_h2 | ret_zero_pct | drag_pp | net_wo_top5_pct | gates_all |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| e303e9f913f9ac34 | ADAUSDT | 697 | -89.48 | 0.4559 | 0.4607 | 0.4401 | -51.22 | 38.26 | -99.99 | False |
| 88e438bd901c6377 | AVAXUSDT | 655 | -82.48 | 0.6902 | 0.7555 | 0.4618 | -25.93 | 56.55 | -99.98 | False |
| 0921926cba254297 | BNBUSDT | 659 | -90.36 | 0.3143 | 0.3194 | 0.2933 | -58.90 | 31.46 | -96.24 | False |
| 8ac4b0d47a9ab218 | BTCUSDT | 772 | -86.33 | 0.3917 | 0.4526 | 0.2179 | -25.23 | 61.10 | -99.64 | False |
| a1656c996bc20423 | DOGEUSDT | 648 | -76.20 | 0.6331 | 0.6554 | 0.5882 | -0.91 | 75.29 | -100.85 | False |
| 05cff542c0f0064e | ETHUSDT | 708 | -89.68 | 0.3933 | 0.3998 | 0.3670 | -50.97 | 38.71 | -99.20 | False |
| 96664c3f70a5206a | HYPEUSDT | 168 | -30.16 | 0.6241 | 0.8352 | 0.4469 | 1.09 | 31.25 | -39.80 | False |
| ddf34f6fde856d40 | LINKUSDT | 717 | -91.14 | 0.4916 | 0.5460 | 0.3344 | -57.08 | 34.07 | -104.02 | False |
| 6283feea158ba8fb | NEARUSDT | 714 | -83.36 | 0.6496 | 0.6200 | 0.7112 | -19.87 | 63.49 | -102.89 | False |
| e917dd60fa38a494 | SOLUSDT | 623 | -86.38 | 0.5033 | 0.5341 | 0.3958 | -46.32 | 40.06 | -101.79 | False |
| b5beb1b7f6a4f086 | SPXUSDT | 212 | -33.35 | 0.8140 | 0.9194 | 0.6536 | 6.29 | 39.63 | -54.85 | False |
| d1da40a20f4aeaa2 | SUIUSDT | 393 | -57.22 | 0.6595 | 0.7642 | 0.5229 | 1.62 | 58.84 | -70.80 | False |
| 76af36f653015376 | XRPUSDT | 704 | -83.67 | 0.5160 | 0.5456 | 0.4187 | -23.08 | 60.59 | -101.77 | False |

Cells positive under fees in words: **zero**. Cells passing G1 in words: **zero**. ds6 positions are STATELESS — nonzero only on trigger bars (audit-pinned), so each trigger pays a full round-trip on a one-bar hold; the fee drag column shows the zero-cost book was already unprofitable in most cells, and fees finish it.

## ds6 — Bollinger z reversion, ADX gate — last6mo

| run_id | symbol | n | ret_pct | PF | pf_h1 | pf_h2 | ret_zero_pct | drag_pp | net_wo_top5_pct | gates_all |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 5d5c2c6e64ac33d4 | ADAUSDT | 54 | -15.10 | 0.3683 | 0.2461 | 0.5650 | -4.39 | 10.72 | -19.87 | False |
| 4e5812a99f5253f2 | AVAXUSDT | 56 | -12.05 | 0.4749 | 0.5707 | 0.4208 | -0.52 | 11.54 | -16.09 | False |
| bd47abdb7d85eac7 | BNBUSDT | 58 | -17.99 | 0.1374 | 0.1952 | 0.0631 | -6.82 | 11.17 | -17.44 | False |
| 2a617cb993e40c34 | BTCUSDT | 67 | -21.06 | 0.1542 | 0.1923 | 0.1219 | -8.52 | 12.54 | -22.50 | False |
| 2d7e8de58c50544f | DOGEUSDT | 56 | -9.22 | 0.4957 | 0.5003 | 0.4915 | 2.69 | 11.91 | -12.75 | False |
| 62c3b0f8275c08c0 | ETHUSDT | 54 | -11.12 | 0.3523 | 0.3639 | 0.3489 | 0.10 | 11.22 | -12.41 | False |
| 766ffec827d3f35c | HYPEUSDT | 61 | -19.42 | 0.4065 | 0.3055 | 0.7160 | -7.84 | 11.58 | -22.77 | False |
| de24fb0c184a6a83 | LINKUSDT | 62 | -21.53 | 0.2518 | 0.1648 | 0.3791 | -10.05 | 11.47 | -23.35 | False |
| c5018d63b9f22ecc | NEARUSDT | 72 | -26.88 | 0.4189 | 0.7552 | 0.1662 | -14.32 | 12.56 | -34.02 | False |
| 1a34d4913db8f73e | SOLUSDT | 55 | -8.55 | 0.5317 | 0.6152 | 0.3874 | 3.22 | 11.77 | -13.64 | False |
| 0d8b2f00aa22b3b0 | SPXUSDT | 67 | -9.28 | 0.7745 | 0.5248 | 1.0960 | 5.14 | 14.42 | -18.60 | False |
| a9d014b1affeb70b | SUIUSDT | 59 | -15.38 | 0.4350 | 0.3357 | 0.5524 | -3.64 | 11.74 | -17.54 | False |
| f457b933d64ad708 | XRPUSDT | 59 | -9.52 | 0.3537 | 0.2848 | 0.4332 | 3.02 | 12.55 | -12.60 | False |

Cells positive under fees in words: **zero**. Cells passing G1 in words: **zero**. ds6 positions are STATELESS — nonzero only on trigger bars (audit-pinned), so each trigger pays a full round-trip on a one-bar hold; the fee drag column shows the zero-cost book was already unprofitable in most cells, and fees finish it.

## ds7 — RSI-2 long book (stateful) — full

| run_id | symbol | n | ret_pct | PF | pf_h1 | pf_h2 | ret_zero_pct | drag_pp | net_wo_top5_pct | gates_all |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2e7b513e56bae8d9 | ADAUSDT | 1081 | -25.09 | 0.9646 | 1.0168 | 0.8988 | 709.02 | 734.11 | -50.57 | False |
| 5b4b9ecba4bf8833 | AVAXUSDT | 946 | -31.65 | 0.9801 | 1.1592 | 0.6887 | 448.37 | 480.02 | -148.52 | False |
| 068738bad1d7bb57 | BNBUSDT | 1277 | -65.73 | 0.8803 | 0.9405 | 0.7009 | 469.83 | 535.56 | -104.63 | False |
| af15eaa4067d9bbb | BTCUSDT | 1300 | -84.90 | 0.7149 | 0.7890 | 0.4555 | 164.02 | 248.93 | -104.76 | False |
| b5c18361f8cb3659 | DOGEUSDT | 889 | 43.69 | 1.0308 | 1.2834 | 0.8198 | 916.89 | 873.21 | -108.83 | False |
| 2505de48ce3af35a | ETHUSDT | 1232 | -88.07 | 0.7982 | 0.8412 | 0.5485 | 79.62 | 167.69 | -113.58 | False |
| b852eb4fb2f1501f | HYPEUSDT | 234 | -27.14 | 0.8018 | 0.7654 | 0.8369 | 21.95 | 49.09 | -42.43 | False |
| 686beb73e0fe2fcc | LINKUSDT | 1173 | -53.56 | 0.9300 | 0.9347 | 0.9159 | 514.15 | 567.71 | -95.70 | False |
| d9bab10e9203cd71 | NEARUSDT | 1023 | 32.66 | 1.0214 | 1.0880 | 0.9606 | 1160.92 | 1128.26 | -55.83 | False |
| de5a02eb67f6100a | SOLUSDT | 1110 | 39.46 | 1.0218 | 1.1365 | 0.8919 | 1505.41 | 1465.95 | -96.49 | False |
| b898dfed4e6f2395 | SPXUSDT | 296 | 44.97 | 1.1078 | 1.7597 | 0.6618 | 178.13 | 133.16 | -5.84 | False |
| 253c4211be5684cf | SUIUSDT | 474 | -17.61 | 0.9602 | 1.3898 | 0.5648 | 133.89 | 151.50 | -55.78 | False |
| a997c21e68d16aea | XRPUSDT | 1067 | -64.65 | 0.8725 | 0.8943 | 0.8166 | 270.22 | 334.86 | -98.95 | False |

Cells positive under fees (count in words: **four**): DOGEUSDT `b5c18361f8cb3659` (43.69 pct, PF 1.0308, pf_zero 1.2329, drag 873.21 pp), NEARUSDT `d9bab10e9203cd71` (32.66 pct, PF 1.0214, pf_zero 1.2220, drag 1128.26 pp), SOLUSDT `de5a02eb67f6100a` (39.46 pct, PF 1.0218, pf_zero 1.2391, drag 1465.95 pp), SPXUSDT `b898dfed4e6f2395` (44.97 pct, PF 1.1078, pf_zero 1.3163, drag 133.16 pp). Every one of them fails the gate set: strict profit factor stays far below G1, the half-window profit factors are unbalanced (G3), the fee drag column shows the raw zero-cost gain being eaten, and G5/G6 fail as well — `gates_all` is False on the whole grid (cells passing ALL gates in words: **zero**).

## ds7 — RSI-2 long book (stateful) — last6mo

| run_id | symbol | n | ret_pct | PF | pf_h1 | pf_h2 | ret_zero_pct | drag_pp | net_wo_top5_pct | gates_all |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 8faf6de044b0b2db | ADAUSDT | 78 | -1.48 | 0.9171 | 0.5925 | 1.1179 | 16.85 | 18.33 | -11.28 | False |
| 9f5c0a075c81089a | AVAXUSDT | 77 | -13.29 | 0.6369 | 0.2501 | 1.0005 | 2.61 | 15.90 | -17.14 | False |
| 4cafbe15463624fd | BNBUSDT | 110 | -14.25 | 0.6031 | 0.6919 | 0.5176 | 9.13 | 23.37 | -21.89 | False |
| 1cac08451c6a902e | BTCUSDT | 89 | -8.65 | 0.5057 | 0.6743 | 0.3819 | 11.00 | 19.65 | -11.84 | False |
| f8f1e1324a3fb94f | DOGEUSDT | 66 | -17.44 | 0.4864 | 0.2592 | 0.6673 | -4.64 | 12.80 | -20.17 | False |
| c15fd411893c2613 | ETHUSDT | 77 | -12.78 | 0.5190 | 0.3506 | 0.6641 | 3.22 | 16.00 | -15.35 | False |
| 6ce876d103e03e32 | HYPEUSDT | 103 | -6.94 | 0.8707 | 0.8421 | 0.9290 | 16.74 | 23.68 | -17.40 | False |
| 3ff27adbf16bbf16 | LINKUSDT | 89 | -13.73 | 0.6721 | 0.5338 | 0.7450 | 4.83 | 18.56 | -17.32 | False |
| ad092bdd514d8a79 | NEARUSDT | 91 | -11.87 | 0.8243 | 0.7465 | 0.8987 | 7.55 | 19.43 | -33.42 | False |
| 8409916af996dab2 | SOLUSDT | 88 | -12.21 | 0.6283 | 0.4276 | 0.8524 | 6.43 | 18.65 | -15.37 | False |
| 3c452ce0461985e9 | SPXUSDT | 80 | -14.32 | 0.7954 | 0.8850 | 0.6375 | 2.18 | 16.50 | -26.13 | False |
| 845ba381619c69ef | SUIUSDT | 62 | -18.52 | 0.5685 | 0.3030 | 0.8702 | -6.71 | 11.81 | -25.41 | False |
| 8a53248395de55e6 | XRPUSDT | 60 | -12.39 | 0.5342 | 0.4186 | 0.6167 | -0.13 | 12.26 | -20.05 | False |

No cell recovers its costs in this window.

## ds8 — BTC/ETH pairs book (symbol PAIRS_BTC_ETH)

| run_id | costs | symbol | n | ret_pct | PF | pf_h1 | pf_h2 | ret_zero_pct | drag_pp | net_wo_top5_pct | gates_all |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| bccaa612918c561b | author | PAIRS_BTC_ETH | 10590 | -59.47 | 0.9671 | 0.9669 | 0.9674 | -59.47 | 0.00 | -122.73 | False |
| 895d1a4e7a266993 | repo6x5 | PAIRS_BTC_ETH | 10590 | -97.84 | 0.8407 | 0.8560 | 0.8195 | -59.47 | 38.36 | -152.64 | False |
| e1f3b5eeb118da36 | repo6x5 | PAIRS_BTC_ETH | 760 | -23.60 | 0.7818 | 0.7880 | 0.7719 | -6.74 | 16.86 | -33.49 | False |

The `author`-cost run `bccaa612918c561b` and the repo-fee run `895d1a4e7a266993` agree to the printed precision on the zero-cost columns — the embedded zero control and a real zero-cost run are the same computation, which is the parity proof for the drag bookkeeping. At zero costs the pairs book is still negative with a profit factor just under one: even gross, the log-spread trigger has no edge here. Cells passing all gates in words: **zero**.

## ds9 — VWAP-deviation reversion — full

| run_id | symbol | n | ret_pct | PF | pf_h1 | pf_h2 | ret_zero_pct | drag_pp | net_wo_top5_pct | gates_all |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 82578e4048eb888e | ADAUSDT | 3096 | -99.72 | 0.8430 | 0.8514 | 0.6231 | 159.55 | 259.26 | -146.81 | False |
| 801803b176683d77 | AVAXUSDT | 2852 | -98.32 | 0.9124 | 0.9298 | 0.6924 | 798.08 | 896.40 | -177.82 | False |
| 28903bf4e45815d7 | BNBUSDT | 3136 | -99.78 | 0.7024 | 0.7064 | 0.5258 | 123.39 | 223.17 | -124.35 | False |
| 1acd0fd6bf204925 | BTCUSDT | 3395 | -99.96 | 0.4469 | 0.4481 | 0.3660 | -32.50 | 67.47 | -111.77 | False |
| ceaa506a554bbdd1 | DOGEUSDT | 2990 | -99.33 | 0.7714 | 0.7720 | 0.7613 | 383.84 | 483.17 | -131.38 | False |
| 30bcb3b2ee975302 | ETHUSDT | 3258 | -99.92 | 0.6701 | 0.6732 | 0.4962 | 4.35 | 104.27 | -120.13 | False |
| 810e8328d4f95c49 | HYPEUSDT | 616 | -58.19 | 0.7867 | 1.0201 | 0.5177 | 62.25 | 120.44 | -82.19 | False |
| c3c4224788c9727f | LINKUSDT | 3115 | -99.82 | 0.8129 | 0.8197 | 0.6225 | 74.82 | 174.63 | -138.75 | False |
| d8291de31a75dc21 | NEARUSDT | 2732 | -99.71 | 0.8496 | 0.8596 | 0.6563 | 16.89 | 116.60 | -149.49 | False |
| 330ad867bd1f8d9f | SOLUSDT | 2880 | -99.63 | 0.7708 | 0.7700 | 0.8000 | 108.78 | 208.41 | -130.70 | False |
| 711f5bfe353cceeb | SPXUSDT | 820 | -69.54 | 0.8514 | 0.8742 | 0.8100 | 85.18 | 154.73 | -96.72 | False |
| f93a18ba85ea5b9d | SUIUSDT | 1609 | -97.62 | 0.7690 | 0.8130 | 0.5381 | -17.69 | 79.93 | -117.77 | False |
| 3dc4af02c24e31a5 | XRPUSDT | 3205 | -99.63 | 0.8305 | 0.8406 | 0.6004 | 334.31 | 433.93 | -138.05 | False |

Cells positive under fees in words: **zero**. Cells passing G1 in words: **zero**. ds9 is stateless too (audit-pinned; the twelve-bar hold the author wrote is a dead no-op because nothing is NaN), and it churns roughly one trade every couple of bars on the full window — the drag column shows fees removing tens of percentage points to essentially the whole notional, on top of a zero-cost book that was already negative.

## ds9 — VWAP-deviation reversion — last6mo

| run_id | symbol | n | ret_pct | PF | pf_h1 | pf_h2 | ret_zero_pct | drag_pp | net_wo_top5_pct | gates_all |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 7fada13032a9d489 | ADAUSDT | 221 | -46.47 | 0.4894 | 0.5117 | 0.4676 | -12.83 | 33.64 | -33.75 | False |
| 16307043892ba806 | AVAXUSDT | 223 | -39.66 | 0.5375 | 0.5769 | 0.5039 | -1.32 | 38.35 | -35.59 | False |
| f3ed315f365300cf | BNBUSDT | 241 | -40.49 | 0.2929 | 0.3419 | 0.2483 | 1.16 | 41.64 | -31.38 | False |
| 3c457e5c131f89fd | BTCUSDT | 245 | -36.97 | 0.3545 | 0.3925 | 0.3132 | 8.09 | 45.06 | -28.91 | False |
| 63c50f2db02e3966 | DOGEUSDT | 215 | -28.72 | 0.5872 | 0.6815 | 0.5122 | 14.43 | 43.14 | -26.92 | False |
| 787b2c6f820cb6a7 | ETHUSDT | 226 | -45.53 | 0.2906 | 0.3182 | 0.2638 | -10.42 | 35.11 | -34.27 | False |
| f9d4c3169c71517b | HYPEUSDT | 239 | -47.13 | 0.5020 | 0.5840 | 0.3687 | -10.53 | 36.60 | -43.56 | False |
| c0f5db55c303969b | LINKUSDT | 211 | -43.67 | 0.3900 | 0.3371 | 0.4378 | -10.37 | 33.30 | -31.63 | False |
| 7659b0cda19b4fc6 | NEARUSDT | 227 | -51.16 | 0.5871 | 0.5540 | 0.6280 | -19.51 | 31.65 | -39.51 | False |
| e63466f75f84babc | SOLUSDT | 226 | -32.79 | 0.5078 | 0.5045 | 0.5109 | 10.54 | 43.32 | -23.90 | False |
| 7cfd2926dbc0ae7a | SPXUSDT | 219 | -37.77 | 0.7198 | 0.7958 | 0.6443 | 0.78 | 38.55 | -35.54 | False |
| dde3ed41dbbcefe5 | SUIUSDT | 221 | -33.53 | 0.6004 | 0.5755 | 0.6287 | 8.11 | 41.64 | -28.53 | False |
| a827f5dc2adb034c | XRPUSDT | 226 | -40.41 | 0.4310 | 0.3974 | 0.4611 | -2.00 | 38.41 | -37.86 | False |

Cells positive under fees in words: **zero**. Cells passing G1 in words: **zero**. ds9 is stateless too (audit-pinned; the twelve-bar hold the author wrote is a dead no-op because nothing is NaN), and it churns roughly one trade every couple of bars on the full window — the drag column shows fees removing tens of percentage points to essentially the whole notional, on top of a zero-cost book that was already negative.

## Zero-cost signal audit (is there ANY gross edge?)

The `ret_zero_pct` / `pf_zero` columns answer directly:
- `ds6`: zero-cost profit factors below one nearly everywhere — no gross signal at this parameter set.
- `ds7`: the zero-cost book is enormously positive in four full-window cells (raw gains of many hundreds of percent are visible in the table), with zero-cost profit factors near one-point-two-something — a REAL but thin tendency consistent with the RSI-2 mean-reversion-in-an-uptrend literature. It is ground up by round-trip fees at this trade frequency (thousands of one-to-few-bar holds), leaving plateaued scored returns and failing G1/G3/G5/G6.
- `ds8`: zero-cost profit factor just under one — nothing gross.
- `ds9`: zero-cost profit factors below one — nothing gross.

Fixing ds7 would mean cutting the round-trip cost (higher timeframe, fewer entries, maker-only) — parameter surgery is out of scope for this verdict; the pack is recorded killed as-is.

