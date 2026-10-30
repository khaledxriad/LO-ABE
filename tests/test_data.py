"""Consistency checks for data/results.json and the numbers behind every figure.

Run with:  python tests/test_data.py
They verify the exact quantities (operation counts, sizes, downlink) against
closed-form expressions, and the measured quantities against sanity ranges.
"""
import os
import sys

import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "figures"))
import common as C  # noqa: E402

R = C.load(os.path.join(ROOT, "data", "results.json"))
D = C.derive(R)
P = R["params"]
n, k, m, M, m0 = P["n"], P["k"], P["m"], P["M"], P["m0"]


def test_parameters():
    assert (n, k, m, M, m0) == (128, 32, 4096, 8352, 4256)
    assert P["q"] == 2 ** 32


def test_exact_operation_counts():
    for N, o in zip(D["N"], D["ops"]):
        assert o["ts"] == M + N * m
        assert o["device"] == m0
        assert o["local"] == o["ts"] + m0
        assert o["naive"] == N * (M + m)


def test_device_work_is_flat_and_alternatives_grow():
    dev = [o["device"] for o in D["ops"]]
    assert len(set(dev)) == 1
    for key in ("local", "naive"):
        v = [o[key] for o in D["ops"]]
        assert all(b > a for a, b in zip(v, v[1:]))


def test_ciphertext_parts_add_up_to_total():
    for row, parts in zip(R["timing"], D["ct_parts_kib"]):
        assert abs(sum(parts.values()) - row["ct"] / 1024) < 1e-9
        assert row["ct"] == (M + row["ncomp"] * m + m0 + 1) * 4
        assert row["ct_naive"] == (row["ncomp"] * (M + m) + m0 + 1) * 4


def test_downlink_is_c0_cs_and_yT():
    assert abs(D["dl_lo_kib"][0] - (m0 + 2) * 4 / 1024) < 1e-12
    assert round(D["dl_lo_kib"][0], 1) == 16.6


def test_published_ratios():
    i = D["N"].index(16)
    assert round(D["ct_naive_kib"][i] / D["ct_kib"][i], 1) == 2.6
    assert round(D["ops"][i]["local"] / D["ops"][i]["device"], 1) == 18.4
    assert round(D["ops"][i]["naive"] / D["ops"][i]["device"], 1) == 46.8


def test_correctness_and_noise():
    assert D["ok"] == D["trials"] == 120
    mg = np.asarray(R["correct"]["margins"])
    assert len(mg) == D["trials"] and mg.min() >= 0 and mg.max() < 1.0


def test_measured_samples_are_complete():
    for row in R["timing"]:
        for key in ("keygen_s", "encrypt_s", "transform_s", "finish_s", "local_s"):
            assert len(row[key]) >= 7 and all(v > 0 for v in row[key])


def test_measured_trends():
    kg = [x[0] for x in D["keygen_ms"]]
    en = [x[0] for x in D["encrypt_ms"]]
    assert all(b > a for a, b in zip(kg, kg[1:])) and all(b > a for a, b in zip(en, en[1:]))
    # device step stays within a factor of two over all N; local decryption grows
    fin = D["finish_med_us"]
    assert max(fin) / min(fin) < 2.0
    assert D["local_med_us"][-1] > 3 * D["local_med_us"][0]


def test_heat_map_grid():
    assert D["grid_all_ok"]
    ct = D["grid_ct_kib"]
    assert np.all(np.diff(ct, axis=0) > 0) and np.all(np.diff(ct, axis=1) > 0)
    # each wildcard position adds one 16 KiB component
    i16 = D["grid_N"].index(16)
    assert abs((ct[i16, 1] - ct[i16, 0]) - 4 * m * 4 / 1024) < 1e-9


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
