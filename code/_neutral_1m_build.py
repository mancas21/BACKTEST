#!/usr/bin/env python3
"""_neutral_1m_build.py — build the DUAL-MODE 1m paper engine.

Base : code/xrp_neutral_engine_paper.py  (byte-identical copy of the engine
       deployed at /home/ubuntu/neutral-paper/{JUP,XRP,SOL,HYPE,SUI}, sha256
       834f3de9f5d0dddd3a5b13f4a881995643b35d0f485200336df19d1c71b74776)
Output: code/xrp_neutral_engine_paper_1m.py

WHY DUAL MODE
-------------
The 15m OHLC model credits a cover whenever the SAME 15m bar's high reaches the
cover level. The 2026-10-31 fill audit proved that is a fabrication: 100% of the
old XRP book's trades were same-bar round trips, and resolving the touches on a
1m tape cut OOS PF 1.3019 -> 0.9326.

The live 5-pair paper book needs a forward record that does NOT rest on that
convention. But rewriting the whole history with the 1m rule is impossible — the
1m tape only starts at day-0 — and would also silently move the day-0 baseline.

So the engine resolves a bar minute by minute ONLY when its 1m tape is
COMPLETE (>= 15 distinct minutes). A bar without a complete tape keeps the
ORIGINAL same-bar model, byte for byte. Consequences, each measured by
code/_neutral_1m_audit.py:

  * no tape at all      -> bit-identical to the 15m paper engine (regression);
  * tape from day-0 on  -> every bar BEFORE the tape is bit-identical, so the
                           day-0 account baseline is untouched and the forward
                           window is the only place the fill model changes;
  * complete tape       -> entries and covers fill in 1m temporal order, and a
                           cover may fill only on a STRICTLY LATER minute than
                           its own entry. A same-minute touch is unresolvable
                           from OHLC: it is counted (same_minute_touched) and
                           banned, never assumed.

Lots carry a sixth element, the entry minute timestamp (-1 when the entry came
from a fallback bar), and trades carry entry_min_ts / exit_min_ts so the forward
event log says exactly which minute filled. The simulation itself never reads
the minute metadata: it drives ordering only.

Usage:  python code/_neutral_1m_build.py
"""
from __future__ import annotations

import hashlib
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))

BASE = os.path.join(ROOT, "code", "xrp_neutral_engine_paper.py")
OUT = os.path.join(ROOT, "code", "xrp_neutral_engine_paper_1m.py")
BASE_SHA256 = "834f3de9f5d0dddd3a5b13f4a881995643b35d0f485200336df19d1c71b74776"

BANNER = '''# GENERATED FILE - do not edit. Rebuild with: python code/_neutral_1m_build.py
# Source : code/xrp_neutral_engine_paper.py (sha256 834f3de9...)
# Fill model: 1m-resolved on bars whose 1m tape is COMPLETE (>= 15 distinct
# minutes); every other bar keeps the original same-bar model, so the historical
# replay is bit-identical and the day-0 baseline cannot move.
'''

SPAN_START = "        # 1. resting entries fill. The ladder was armed at the close of the"
SPAN_END = "                n_cycles += 1"
INIT_ANCHOR = "    grids_built = fills = n_cycles = 0"
CLOSE_DEF = "    def close_lot(lot, px, fee, slip_px, kind):"
LOT_ANCHOR = "            lots.append([side * q, fill_px, cover, f, int(T[t])])"
LOT_ANCHOR_1M = "            lots.append([side * q, fill_px, cover, f, int(T[t]), -1])"
TRADE_ANCHOR = "                           ts=int(T[t]), entry_ts=int(lot[4])))"
TRADE_ANCHOR_1M = ("                           ts=int(T[t]), entry_ts=int(lot[4]),\n"
                   "                           entry_min_ts=int(lot[5]), exit_min_ts=int(min_ts)))")
COVER_ANCHOR = ('                close_lot(lot, px, leg_fee, leg_slip, "cover")\n'
                "                n_cycles += 1")
COVER_ANCHOR_1M = ('                if int(lot[4]) == int(T[t]):\n'
                   "                    same_bar_covers += 1\n"
                   '                close_lot(lot, px, leg_fee, leg_slip, "cover")\n'
                   "                n_cycles += 1")
TRACK_ANCHOR = "            n_funding_events=n_fund, init=init))"
TRACK_ANCHOR_1M = '''            n_funding_events=n_fund, init=init,
            bars_resolved=resolved_bars, bars_partial=partial_bars,
            bars_no_tape=notape_bars, minutes_used=minutes_used,
            same_minute_touched=same_minute_touched,
            same_bar_covers=same_bar_covers, one_m_covers=one_m_covers,
            res_first_ts=int(res_first_ts), res_last_ts=int(res_last_ts),
            res_flags=RESOLVED))'''

MINUTE_DATA = '''    # ── 1m fill accounting (paper) ──────────────────────────────────────
    # A bar is RESOLVED when its 1m tape is COMPLETE: >= 15 distinct minutes.
    # Bars without a complete tape keep the ORIGINAL same-bar model, which is
    # what makes every pre-tape bar bit-identical to the 15m paper engine.
    _m1 = os.environ.get("NP_1M_CSV")
    _min_per_bar = 15
    MLOW, MHI, MTS, RESOLVED = [], [], [], []
    if _m1:
        import csv as _csv
        _t0 = bars[0][0]
        _step_ms = (bars[1][0] - bars[0][0]) if len(bars) > 1 else 900000
        if _step_ms <= 0:
            _step_ms = 900000
        _idx = {b[0]: i for i, b in enumerate(bars)}
        _acc = {}
        with open(_m1) as _f:
            _r = _csv.reader(_f)
            next(_r)
            for _row in _r:
                _ts = int(_row[0])
                _i = _idx.get(_t0 + ((_ts - _t0) // _step_ms) * _step_ms)
                if _i is not None:
                    # keyed by minute ts: a duplicated row cannot inflate the
                    # completeness test, and the walk sees unique minutes.
                    _acc.setdefault(_i, {})[_ts] = (float(_row[3]), float(_row[2]))
        for _i in range(len(bars)):
            _ch = _acc.get(_i) or {}
            _mins = sorted(_ch)
            MLOW.append([_ch[_m][0] for _m in _mins])
            MHI.append([_ch[_m][1] for _m in _mins])
            MTS.append(_mins)
            RESOLVED.append(len(_mins) >= _min_per_bar)
    else:
        MLOW = [[b[3]] for b in bars]
        MHI = [[b[2]] for b in bars]
        MTS = [[] for _ in bars]
        RESOLVED = [False] * len(bars)
    resolved_bars = sum(1 for _x in RESOLVED if _x)
    partial_bars = sum(1 for _i, _x in enumerate(RESOLVED)
                       if not _x and len(MTS[_i]) > 0)
    notape_bars = len(bars) - resolved_bars - partial_bars
    minutes_used = sum(len(_m) for _m in MTS)
    same_minute_touched = 0
    same_bar_covers = 0
    one_m_covers = 0
    _res_ix = [_i for _i, _x in enumerate(RESOLVED) if _x]
    res_first_ts = bars[_res_ix[0]][0] if _res_ix else 0
    res_last_ts = bars[_res_ix[-1]][0] if _res_ix else 0
'''

MINUTE_WALK = '''            # 1+2. Entries and covers. A COMPLETE 1m tape resolves the touches
            # in minute order inside the bar; an incomplete one keeps the
            # original same-bar model so pre-tape history cannot move.
            for _j, _mts in enumerate(MTS[t]):
                _ml, _mh = MLOW[t][_j], MHI[t][_j]
                # entries first, with the base engine's exact touch rules
                for o_ in list(orders):
                    px, side, q = o_
                    touched = (_ml < px) if side > 0 else (_mh > px)
                    if not touched:
                        continue
                    fill_px = px * (1 + leg_slip * side)
                    net_after = qty_now() + side * q
                    cap = delta_max_pct * max(book_equity(C[t]), 0.0)
                    if abs(net_after * fill_px) > cap:
                        delta_cap_hits += 1
                        continue
                    f = abs(q * fill_px) * leg_fee
                    if side > 0:
                        cash -= q * fill_px + f
                        cover = px + step * cover_mult
                    else:
                        cash += q * fill_px - f
                        cover = px - step * cover_mult
                    fee_paid += f
                    lots.append([side * q, fill_px, cover, f, int(T[t]), int(_mts)])
                    orders.remove(o_)
                    fills += 1
                    fill_times.append(int(T[t]))
                    eq_now = book_equity(C[t])
                    if eq_now > 0:
                        max_delta_fill_pct = max(max_delta_fill_pct,
                                                 abs(qty_now() * fill_px) / eq_now * 100)
                # covers: only lots whose entry minute is STRICTLY earlier.
                # lot[5] == -1 marks an entry on a fallback bar, which is
                # always earlier than any minute of a later bar.
                for lot in list(lots):
                    px = lot[2]
                    if int(lot[5]) >= int(_mts):
                        if (_mh >= px) if lot[0] > 0 else (_ml <= px):
                            same_minute_touched += 1
                        continue
                    touched = (_mh >= px) if lot[0] > 0 else (_ml <= px)
                    if touched:
                        close_lot(lot, px, leg_fee, leg_slip, "cover", int(_mts))
                        n_cycles += 1
                        one_m_covers += 1
'''


def _sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def build():
    base_sha = _sha(BASE)
    assert base_sha == BASE_SHA256, (
        f"base engine sha {base_sha} != deployed {BASE_SHA256}; refusing to build "
        f"from a file the live bot is not running")

    lines = open(BASE, encoding="utf-8").read().splitlines(keepends=True)
    assert lines[0].startswith("#!"), "base engine lost its shebang"

    starts = [i for i, ln in enumerate(lines) if ln.rstrip("\n") == SPAN_START]
    assert len(starts) == 1, f"span start matched {len(starts)}x"
    s = starts[0]
    ends = [i for i in range(s, len(lines)) if lines[i].rstrip("\n") == SPAN_END]
    assert ends, "span end not found"
    e = ends[0]
    tail = "".join(lines[e + 1:e + 4])
    assert "# 3. hard stop" in tail, "unexpected span tail: " + repr(tail[:120])

    block = "".join(lines[s:e + 1])
    assert block.count(LOT_ANCHOR) == 1, "lot anchor not unique in span"
    assert block.count(COVER_ANCHOR) == 1, "cover anchor not unique in span"
    block = block.replace(LOT_ANCHOR, LOT_ANCHOR_1M)
    block = block.replace(COVER_ANCHOR, COVER_ANCHOR_1M)
    indented = "".join(("    " + ln if ln.strip() else ln)
                       for ln in block.splitlines(keepends=True))
    new_block = "        if RESOLVED[t]:\n" + MINUTE_WALK + "        else:\n" + indented

    text = "".join(lines[:s]) + new_block + "".join(lines[e + 1:])

    # metadata patches, each exact-once
    assert text.count(CLOSE_DEF) == 1, "close_lot signature not unique"
    text = text.replace(CLOSE_DEF,
                        "    def close_lot(lot, px, fee, slip_px, kind, min_ts=-1):")
    assert text.count(TRADE_ANCHOR) == 1, "trade anchor not unique"
    text = text.replace(TRADE_ANCHOR, TRADE_ANCHOR_1M)
    assert text.count(INIT_ANCHOR) == 1, "init anchor not unique"
    text = text.replace(INIT_ANCHOR, INIT_ANCHOR + "\n" + MINUTE_DATA.rstrip("\n"))
    assert text.count(TRACK_ANCHOR) == 1, "track anchor not unique"
    text = text.replace(TRACK_ANCHOR, TRACK_ANCHOR_1M)

    # banner: comments between the shebang and the docstring are legal, the
    # docstring remains the first statement.
    head, rest = text.split("\n", 1)
    text = head + "\n" + BANNER + rest

    open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    return _sha(OUT), OUT


if __name__ == "__main__":
    sha, path = build()
    print(f"built {os.path.relpath(path, ROOT)}  sha256 {sha}")
