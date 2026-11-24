"""Consistency checks for data/results.json and the numbers behind every figure.

Run with:  python tests/test_data.py
They verify the exact quantities (operation counts, sizes, downlink) against
closed-form expressions, and the measured quantities against sanity ranges.
"""
import json
import os

import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), "..")


def load(path):
    with open(path) as f:
        return json.load(f)


def tukey_box(x, whis=1.5):
    """Box statistics identical to matplotlib's default boxplot."""
    x = np.asarray(x, float)
    q1, med, q3 = np.percentile(x, [25, 50, 75])
    iqr = q3 - q1
    lo_lim, hi_lim = q1 - whis * iqr, q3 + whis * iqr
    inside = x[(x >= lo_lim) & (x <= hi_lim)]
    outl = x[(x < lo_lim) | (x > hi_lim)]
    return dict(q1=q1, med=med, q3=q3, lo=inside.min(), hi=inside.max(),
                outliers=np.sort(outl), n=len(x))


def derive(R):
    """Return a dict with everything the figures and tables need."""
    P = R["params"]
    D = {"params": P}
    rows = R["timing"]
    D["N"] = [r["N"] for r in rows]
    ms = lambda v: np.asarray(v) * 1e3
    us = lambda v: np.asarray(v) * 1e6
    def med_iqr(v):
        a = np.asarray(v, float)
        q1, md, q3 = np.percentile(a, [25, 50, 75])
        return (md, q1, q3)
    D["keygen_ms"] = [med_iqr(ms(r["keygen_s"])) for r in rows]      # (median, Q1, Q3)
    D["encrypt_ms"] = [med_iqr(ms(r["encrypt_s"])) for r in rows]
    D["transform_us"] = [med_iqr(us(r["transform_s"])) for r in rows]
    D["reps"] = {"keygen": len(rows[0]["keygen_s"]), "encrypt": len(rows[0]["encrypt_s"]),
                 "transform": len(rows[0]["transform_s"]), "finish": len(rows[0]["finish_s"]),
                 "local": len(rows[0]["local_s"])}
    D["transform_med_us"] = [float(np.median(us(r["transform_s"]))) for r in rows]
    D["finish_med_us"] = [float(np.median(us(r["finish_s"]))) for r in rows]
    D["local_med_us"] = [float(np.median(us(r["local_s"]))) for r in rows]
    D["box_finish"] = [tukey_box(us(r["finish_s"])) for r in rows]
    D["box_local"] = [tukey_box(us(r["local_s"])) for r in rows]
    D["ops"] = [r["ops"] for r in rows]
    D["ct_kib"] = [r["ct"] / 1024 for r in rows]
    D["tk_kib"] = [r["tk"] / 1024 for r in rows]
    D["pk_full_mib"] = [r["pk_full"] / 2**20 for r in rows]
    D["pk_seed_mib"] = [r["pk_seed"] / 2**20 for r in rows]
    D["rk_bytes"] = [r["rk"] for r in rows]
    D["ct_parts_kib"] = [{k: v / 1024 for k, v in r["ct_parts"].items()} for r in rows]
    # downlink: LO-ABE fetches c0, c_s and y_T only
    dl = (P["m0"] + 2) * 4 / 1024
    D["dl_lo_kib"] = [dl for _ in rows]
    # correctness / noise (one entry per policy size that was tested)
    D["corr"] = {}
    for key, c in R["correct"].items():
        mg = np.asarray(c["margins"])
        D["corr"][int(key)] = dict(N=c["N"], trials=c["trials"], ok=c["ok"], margins_pct=mg * 100,
                                   worst_pct=float(mg.max() * 100), median_pct=float(np.median(mg) * 100),
                                   p99_pct=float(np.percentile(mg, 99) * 100))
    D["setup_s"] = R["setup_s"]
    # heat maps (rows = N, cols = wildcard fraction)
    Ns = sorted({g["N"] for g in R["grid"]})
    fr = sorted({g["frac"] for g in R["grid"]})
    D["grid_N"], D["grid_frac"] = Ns, fr
    enc = np.zeros((len(Ns), len(fr)))
    ct = np.zeros_like(enc)
    ok = True
    for g in R["grid"]:
        i, j = Ns.index(g["N"]), fr.index(g["frac"])
        enc[i, j] = float(np.median(g["encrypt_s"]))
        ct[i, j] = g["ct"] / 1024
        ok &= bool(g["ok"])
    D["grid_enc_s"], D["grid_ct_kib"], D["grid_all_ok"] = enc, ct, ok
    return D


R = load(os.path.join(ROOT, "data", "results.json"))
D = derive(R)
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


def test_device_work_is_flat_and_alternatives_grow():
    dev = [o["device"] for o in D["ops"]]
    assert len(set(dev)) == 1
    v = [o["local"] for o in D["ops"]]
    assert all(b > a for a, b in zip(v, v[1:]))


def test_ciphertext_parts_add_up_to_total():
    for row, parts in zip(R["timing"], D["ct_parts_kib"]):
        assert abs(sum(parts.values()) - row["ct"] / 1024) < 1e-9
        assert row["ct"] == (M + row["ncomp"] * m + m0 + 1) * 4


def test_downlink_is_c0_cs_and_yT():
    assert abs(D["dl_lo_kib"][0] - (m0 + 2) * 4 / 1024) < 1e-12
    assert round(D["dl_lo_kib"][0], 1) == 16.6


def test_published_ratios():
    i = D["N"].index(16)
    assert round(D["ops"][i]["local"] / D["ops"][i]["device"], 1) == 18.4
    assert round(D["ct_kib"][i] / D["dl_lo_kib"][i], 1) == 18.4


def test_correctness_and_noise():
    for key, trials in (("8", 200), ("32", 60)):
        c = R["correct"][key]
        assert c["ok"] == c["trials"] == trials
        mg = np.asarray(c["margins"])
        assert len(mg) == trials and mg.min() >= 0 and mg.max() < 1.0


def test_measured_samples_are_complete():
    for row in R["timing"]:
        for key in ("keygen_s", "encrypt_s", "transform_s", "finish_s", "local_s"):
            assert len(row[key]) >= 15 if key in ("keygen_s", "encrypt_s") else len(row[key]) >= 100 and all(v > 0 for v in row[key])


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
