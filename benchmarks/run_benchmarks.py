"""Benchmark driver for the LO-ABE prototype.

Writes data/results.json with raw samples, so that every table and figure of
the paper can be regenerated from one file:

    python benchmarks/run_benchmarks.py --out data/results.json

Experiments
  correct   : randomized end-to-end trials at N = 8 (noise margin per trial)
  unauth    : decryption attempts with a key that does not satisfy the policy
  timing    : repeated timings of every algorithm for N in {4, 8, 16, 32}
  grid      : encryption time and ciphertext size over N x wildcard fraction
"""
import argparse
import json
import os
import platform
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from loabe import scheme as S  # noqa: E402


def timed(f, reps, warmup=1):
    """Run f once (untimed) to warm caches and BLAS threads, then time `reps` runs."""
    out, ts = None, []
    for _ in range(warmup):
        out = f()
    for _ in range(reps):
        t0 = time.perf_counter()
        out = f()
        ts.append(time.perf_counter() - t0)
    return ts, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/results.json")
    ap.add_argument("--trials", type=int, default=120)
    ap.add_argument("--unauth", type=int, default=20)
    ap.add_argument("--quick", action="store_true", help="tiny run for smoke tests")
    ap.add_argument("--reuse", help="keep the correctness/unauthorized results of an earlier JSON file and redo only timing and grid")
    a = ap.parse_args()
    if a.quick:
        a.trials, a.unauth = 4, 2
    Ns = [4, 8, 16, 32] if not a.quick else [4, 8]
    rs = np.random.default_rng(5)
    res = {"params": S.params(),
           "env": {"python": platform.python_version(), "numpy": np.__version__,
                   "machine": platform.machine(), "cpus": os.cpu_count()}}

    if a.reuse:
        old = json.load(open(a.reuse))
        for k in ("correct", "unauth"):
            res[k] = old[k]
    else:
        # -------------------------------------------------- correctness + noise
        N = 8
        t0 = time.perf_counter()
        pp = S.setup(N)
        res["setup_s"] = time.perf_counter() - t0
        margins, ok = [], 0
        for _ in range(a.trials):
            w = [int(v) for v in rs.integers(0, 3, N)]
            x = [v if v < 2 else int(rs.integers(0, 2)) for v in w]
            mu = int(rs.integers(0, 2))
            sk, t = S.keygen(pp, x)
            ct = S.encrypt(pp, w, mu)
            got, rc = S.finish(ct, S.transform(sk, ct), t)
            ok += int(got == mu)
            margins.append(S.noise_margin(rc, mu))
        res["correct"] = {"N": N, "trials": a.trials, "ok": ok, "margins": margins}
        print("correct", ok, "/", a.trials, "worst", max(margins), flush=True)

        # -------------------------------------------------- unauthorized key
        bad = 0
        for _ in range(a.unauth):
            w = [int(v) for v in rs.integers(0, 2, N)]
            x = list(w)
            x[0] ^= 1
            mu = int(rs.integers(0, 2))
            sk, t = S.keygen(pp, x)
            ct = S.encrypt(pp, w, mu)
            tk2 = dict(sk)
            tk2["x"] = list(w)   # best honest-looking attempt: use the components of the policy bits
            got, _ = S.finish(ct, S.transform(tk2, ct), t)
            bad += int(got == mu)
        res["unauth"] = {"trials": a.unauth, "recovered": bad}
        print("unauth", bad, "/", a.unauth, flush=True)


    # -------------------------------------------------- setup time (median of 5, N = 8)
    st, _ = timed(lambda: S.setup(8), 5, warmup=1)
    res["setup_s"] = float(np.median(st))

    # -------------------------------------------------- timing sweep
    # Measurements are interleaved: every round visits all values of N once, so a
    # noisy period on a shared machine hits all settings alike instead of one of them.
    ctx = {}
    for N in Ns:
        pp = S.setup(N)
        w = [int(v) for v in rs.integers(0, 2, N)]
        sk, t = S.keygen(pp, w)
        ct = S.encrypt(pp, w, 1)          # warm-up and a ciphertext/key pair for the fast operations
        yt = S.transform(sk, ct)
        ctx[N] = dict(pp=pp, w=w, sk=sk, t=t, ct=ct, yt=yt,
                      keygen_s=[], encrypt_s=[], transform_s=[], finish_s=[], local_s=[])
    ROUNDS = 7 if not a.quick else 2
    for r in range(ROUNDS):
        for N in Ns:
            c = ctx[N]
            (kg,), _ = timed(lambda: S.keygen(c["pp"], c["w"]), 1, warmup=0)
            (en,), _ = timed(lambda: S.encrypt(c["pp"], c["w"], 1), 1, warmup=0)
            c["keygen_s"].append(kg)
            c["encrypt_s"].append(en)
            tr, _ = timed(lambda: S.transform(c["sk"], c["ct"]), 30, warmup=2)
            fi, _ = timed(lambda: S.finish(c["ct"], c["yt"], c["t"]), 150, warmup=2)
            lo, _ = timed(lambda: S.finish(c["ct"], S.transform(c["sk"], c["ct"]), c["t"]), 30, warmup=2)
            c["transform_s"] += tr
            c["finish_s"] += fi
            c["local_s"] += lo
        print("timing round", r + 1, "/", ROUNDS, flush=True)
    rows = []
    for N in Ns:
        c = ctx[N]
        row = {"N": N, "keygen_s": c["keygen_s"], "encrypt_s": c["encrypt_s"], "transform_s": c["transform_s"],
               "finish_s": c["finish_s"], "local_s": c["local_s"]}
        z = S.sizes(c["pp"], c["w"])
        row.update({k: v for k, v in z.items() if k != "ct_parts"})
        row["ct_parts"] = z["ct_parts"]
        row["ops"] = S.op_counts(N)
        rows.append(row)
    res["timing"] = rows

    # -------------------------------------------------- N x wildcard grid (interleaved passes)
    fracs = [0.0, 0.25, 0.5, 0.75]
    cells = []
    for N in Ns:
        pp = S.setup(N)
        for fr in fracs:
            nw = int(fr * N)
            w = [2] * nw + [int(v) for v in rs.integers(0, 2, N - nw)]
            x = [int(rs.integers(0, 2)) if v == 2 else v for v in w]
            sk, t = S.keygen(pp, x)
            ct = S.encrypt(pp, w, 1)      # warm-up
            got, _ = S.finish(ct, S.transform(sk, ct), t)
            z = S.sizes(pp, w)
            cells.append(dict(N=N, frac=fr, pp=pp, w=w, sk=sk, ct=ct, ok=int(got == 1),
                              ctsize=z["ct"], ncomp=z["ncomp"], encrypt_s=[], transform_s=[]))
    for r in range(5 if not a.quick else 2):
        for c in cells:
            (en,), _ = timed(lambda: S.encrypt(c["pp"], c["w"], 1), 1, warmup=0)
            c["encrypt_s"].append(en)
        print("grid pass", r + 1, flush=True)
    for c in cells:
        tr, _ = timed(lambda: S.transform(c["sk"], c["ct"]), 50, warmup=2)
        c["transform_s"] = tr
    res["grid"] = [{"N": c["N"], "frac": c["frac"], "encrypt_s": c["encrypt_s"], "transform_s": c["transform_s"],
                    "ok": c["ok"], "ct": c["ctsize"], "ncomp": c["ncomp"]} for c in cells]

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(res, open(a.out, "w"), indent=1)
    print("done")


if __name__ == "__main__":
    main()
