#!/usr/bin/env python
"""Selftest for the generation-2 data cuts in vrun.py (2026-11-06).

Contract under test (AGENTS.md/STATUS: "congelar cortes de datos"):
  * an APPEND after the cut changes nothing: prefix bytes, prefix sha and
    slice bar count are identical before and after appending;
  * an EDIT inside the cut changes the sha;
  * a cut at/after the last row reproduces the full-file hash (compatibility
    with legacy full-file artifacts);
  * funding JSON: canonical serialization of records with t < cut, order- and
    whitespace-proof, and appending records after the cut changes nothing;
  * the served slice file is byte-exact (CSV) / canonical (JSON) and its own
    sha256 equals the recorded input hash -- the hash covers exactly the bytes
    the engine consumes.

Run:  python code/_cut_hash_selftest.py   (or pytest code/_cut_hash_selftest.py)
All data is built in a temp dir; no repo data file is touched.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))
import vrun  # noqa: E402


def _kline_csv(tmp: str, name: str, n: int, t0_ms: int = 1_570_000_000_000,
               step_ms: int = 3_600_000) -> str:
    lines = ["open_ts,open,high,low,close,volume"]
    price = 100.0
    for i in range(n):
        price *= 1.0 + ((i * 7919) % 13 - 6) / 500.0
        lines.append(f"{t0_ms + i * step_ms},{price:.2f},{price + 1:.2f},"
                     f"{price - 1:.2f},{price:.2f},1.5")
    p = os.path.join(tmp, name)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return p


def _funding_json(tmp: str, name: str, n: int, t0_ms: int = 1_570_000_000_000,
                  step_ms: int = 8 * 3_600_000) -> str:
    recs = [{"t": t0_ms + i * step_ms, "r": 0.0001 + i / 1e6} for i in range(n)]
    p = os.path.join(tmp, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(recs, f)
    return p


def _append_kline(p: str, n: int, t0_ms: int, step_ms: int = 3_600_000):
    price = 200.0
    with open(p, "a", encoding="utf-8", newline="\n") as f:
        for i in range(n):
            price *= 1.01
            f.write(f"{t0_ms + i * step_ms},{price:.2f},{price + 1:.2f},"
                    f"{price - 1:.2f},{price:.2f},1.5\n")


def test_append_after_cut_changes_nothing():
    """THE property the whole redesign buys: a data append cannot stale an
    artifact whose cut is before the appended rows."""
    with tempfile.TemporaryDirectory() as tmp:
        p = _kline_csv(tmp, "X_1h.csv", 500)
        cut = vrun._norm_cut_ts(1_570_000_000_000 + 300 * 3_600_000)  # after row 300
        rec_before, served_before = vrun._slice_serve(p, cut)
        n_before, sha_before = rec_before["bars"], rec_before["sha256"]
        # append ten rows strictly AFTER the cut
        _append_kline(p, 10, 1_570_000_000_000 + 600 * 3_600_000)
        rec_after, served_after = vrun._slice_serve(p, cut)
        assert rec_after["bars"] == n_before, "append leaked into the cut"
        assert rec_after["sha256"] == sha_before, "append changed the cut hash"
        with open(served_before, "rb") as a, open(served_after, "rb") as b:
            assert a.read() == b.read(), "served slice bytes moved"


def test_edit_inside_cut_changes_hash():
    with tempfile.TemporaryDirectory() as tmp:
        p = _kline_csv(tmp, "X_1h.csv", 500)
        cut = vrun._norm_cut_ts(1_570_000_000_000 + 300 * 3_600_000)
        sha_before = vrun._slice_serve(p, cut)[0]["sha256"]
        # rewrite the file with row 10 edited (same length, different price)
        with open(p, encoding="utf-8") as f:
            lines = f.read().splitlines()
        parts = lines[11].split(",")
        parts[1] = "999.99"
        lines[11] = ",".join(parts)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        sha_after = vrun._slice_serve(p, cut)[0]["sha256"]
        assert sha_after != sha_before, "an edit inside the cut was not caught"


def test_cut_at_end_equals_full_file_hash():
    """Compatibility: a cut beyond the last row hashes the whole file, so a
    legacy full-file artifact and a generation-2 one describe the same bytes."""
    with tempfile.TemporaryDirectory() as tmp:
        p = _kline_csv(tmp, "X_1h.csv", 500)
        full = vrun._sha256_file(p)
        rec, served = vrun._slice_serve(p, "2099-01-01")
        assert rec["bars"] == 500
        assert rec["sha256"] == full
        assert vrun._sha256_file(served) == full


def test_csv_slice_matches_pandas_truth():
    with tempfile.TemporaryDirectory() as tmp:
        p = _kline_csv(tmp, "X_1h.csv", 1000)
        cut_ms = 1_570_000_000_000 + 654 * 3_600_000
        rec, served = vrun._slice_serve(p, vrun._norm_cut_ts(cut_ms))
        df = pd.read_csv(p, usecols=["open_ts"])
        expect = int((df["open_ts"] < cut_ms).sum())
        assert rec["bars"] == expect, f"{rec['bars']} != pandas truth {expect}"
        got = pd.read_csv(served, usecols=["open_ts"])
        assert len(got) == expect
        assert int(got["open_ts"].max()) < cut_ms


def test_funding_json_cut_canonical_and_append_proof():
    with tempfile.TemporaryDirectory() as tmp:
        p = _funding_json(tmp, "X_funding.json", 100)
        cut_ms = 1_570_000_000_000 + 60 * 8 * 3_600_000
        cut = vrun._norm_cut_ts(cut_ms)
        rec1, served1 = vrun._slice_serve(p, cut)
        assert rec1["bars"] == 60
        with open(p, encoding="utf-8") as f:
            recs = json.load(f)
        # same records, same order, different whitespace -> same canonical hash
        with open(p, "w", encoding="utf-8") as f:
            json.dump(recs, f, indent=4)
        vrun._SLICE_CACHE.clear()
        rec3, _ = vrun._slice_serve(p, cut)
        assert rec3["sha256"] == rec1["sha256"], "whitespace moved the cut hash"
        assert rec3["bars"] == rec1["bars"]
        # appended settlements after the cut change nothing
        with open(p, "w", encoding="utf-8") as f:
            json.dump(recs + [{"t": cut_ms + 8 * 3_600_000 * 500, "r": 0.0002}], f)
        vrun._SLICE_CACHE.clear()
        rec4, served4 = vrun._slice_serve(p, cut)
        assert rec4["bars"] == 60 and rec4["sha256"] == rec1["sha256"]
        assert len(json.load(open(served4))) == 60


def test_served_record_path_points_at_original():
    with tempfile.TemporaryDirectory() as tmp:
        p = _kline_csv(tmp, "BTCUSDT_1h.csv", 300)
        rec, served = vrun._slice_serve(p, vrun._norm_cut_ts(1_570_000_000_000 + 100 * 3_600_000))
        assert rec["path"] == os.path.abspath(p)
        # the served file must carry the EXACT original basename (engines
        # reconstruct filenames from the serving dir: the neutral book joins
        # fund_dir + "{sym}_funding.json"; cvrmd extracts tf from the suffix)
        assert os.path.basename(served) == "BTCUSDT_1h.csv"
        assert rec["cut_ts"].endswith("+00:00")


def test_served_funding_filename_reconstruction():
    """The xrpneutral wrapper passes fund_dir = dirname(funding_path) and the
    engine joins f"{sym}_funding.json" — the 2026-11-06 bug where funding was
    silently charged zero (n_funding_events 0) because the slice name carried
    a .cut suffix. This test pins the fix."""
    with tempfile.TemporaryDirectory() as tmp:
        p = _funding_json(tmp, "XRPUSDT_funding.json", 100)
        cut = vrun._norm_cut_ts(1_570_000_000_000 + 50 * 8 * 3_600_000)
        rec, served = vrun._slice_serve(p, cut)
        sym = "XRPUSDT"
        reconstructed = os.path.join(os.path.dirname(served), f"{sym}_funding.json")
        assert os.path.exists(reconstructed), \
            "engine filename reconstruction must find the served slice"
        assert os.path.abspath(reconstructed) == os.path.abspath(served)


def test_resolve_cut_modes():
    assert vrun._resolve_cut(None) is None
    assert vrun._resolve_cut("full") is None
    assert vrun._resolve_cut("auto") == vrun._default_cut_ts()
    iso = vrun._resolve_cut("2026-11-06")
    assert iso.startswith("2026-11-06T00:00:00+00:00")
    assert vrun._resolve_cut("2026-11-06T12:00:00Z") == "2026-11-06T12:00:00+00:00"


def test_binary_search_monotone_sweep():
    with tempfile.TemporaryDirectory() as tmp:
        p = _kline_csv(tmp, "X_1h.csv", 400)
        base_ms = 1_570_000_000_000
        prev = -1
        for k in range(0, 401, 25):
            cut = vrun._norm_cut_ts(base_ms + k * 3_600_000)
            rec, _ = vrun._slice_serve(p, cut)
            assert rec["bars"] == k, f"cut at row {k}: got {rec['bars']}"
            assert rec["bars"] >= prev
            prev = rec["bars"]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} checks ALL PASS")
