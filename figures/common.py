"""Shared data preparation for the figure scripts.

Every number plotted in the paper is computed here from data/results.json, so
the PDF figures and the LaTeX tables can never disagree.
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA = os.path.join(HERE, "..", "data", "results.json")

# Okabe-Ito colour-blind-safe palette (hex, no '#'). One colour per role,
# reused in every figure so that a reader can follow a series across plots.
PALETTE = {
    "lo":     "0072B2",   # LO-ABE, outsourced decryption
    "local":  "E69F00",   # LO-ABE decrypted locally
    "naive":  "D55E00",   # modelled naive layout
    "keygen": "009E73",   # KeyGen (TA)
    "enc":    "CC79A7",   # Encrypt (DO)
    "ts":     "56B4E9",   # Transform (TS)
    "grey":   "777777",
}


def load(path=None):
    with open(path or DEFAULT_DATA) as f:
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
    D["keygen_ms"] = [(ms(r["keygen_s"]).mean(), ms(r["keygen_s"]).std(ddof=1)) for r in rows]
    D["encrypt_ms"] = [(ms(r["encrypt_s"]).mean(), ms(r["encrypt_s"]).std(ddof=1)) for r in rows]
    D["transform_us"] = [(us(r["transform_s"]).mean(), us(r["transform_s"]).std(ddof=1)) for r in rows]
    D["transform_med_us"] = [float(np.median(us(r["transform_s"]))) for r in rows]
    D["finish_med_us"] = [float(np.median(us(r["finish_s"]))) for r in rows]
    D["local_med_us"] = [float(np.median(us(r["local_s"]))) for r in rows]
    D["box_finish"] = [tukey_box(us(r["finish_s"])) for r in rows]
    D["box_local"] = [tukey_box(us(r["local_s"])) for r in rows]
    D["ops"] = [r["ops"] for r in rows]
    D["ct_kib"] = [r["ct"] / 1024 for r in rows]
    D["ct_naive_kib"] = [r["ct_naive"] / 1024 for r in rows]
    D["tk_kib"] = [r["tk"] / 1024 for r in rows]
    D["pk_full_mib"] = [r["pk_full"] / 2**20 for r in rows]
    D["pk_seed_mib"] = [r["pk_seed"] / 2**20 for r in rows]
    D["rk_bytes"] = [r["rk"] for r in rows]
    D["ct_parts_kib"] = [{k: v / 1024 for k, v in r["ct_parts"].items()} for r in rows]
    # downlink: LO-ABE fetches c0, c_s and y_T only
    dl = (P["m0"] + 2) * 4 / 1024
    D["dl_lo_kib"] = [dl for _ in rows]
    # correctness / noise
    mg = np.asarray(R["correct"]["margins"])
    D["margins_pct"] = mg * 100
    D["trials"] = R["correct"]["trials"]
    D["ok"] = R["correct"]["ok"]
    D["worst_pct"] = float(mg.max() * 100)
    D["median_pct"] = float(np.median(mg) * 100)
    D["unauth"] = R["unauth"]
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


def hist_bins(values, nbins=12):
    lo, hi = 0.0, float(np.ceil(np.max(values) * 2) / 2)
    edges = np.linspace(lo, max(hi, 0.5), nbins + 1)
    cnt, edges = np.histogram(values, bins=edges)
    return cnt, edges
