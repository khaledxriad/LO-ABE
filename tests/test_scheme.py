"""Fast correctness tests with a small lattice dimension (n = 16).

Run with:  python -m pytest -q   (from the repository root)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from loabe import scheme as S  # noqa: E402


def _roundtrip(N, w, x, mu):
    pp = S.setup(N, seed=1)
    tk, t = S.keygen(pp, x)
    ct = S.encrypt(pp, w, mu)
    yt = S.transform(tk, ct)
    return S.finish(ct, yt, t)


def setup_module(_):
    S.configure(n_=16, lam_=40)


def teardown_module(_):
    S.configure()  # restore the benchmark parameters


def test_authorized_decryption_is_correct():
    rs = np.random.default_rng(3)
    N = 4
    for _ in range(6):
        w = [int(v) for v in rs.integers(0, 3, N)]
        x = [v if v < 2 else int(rs.integers(0, 2)) for v in w]
        mu = int(rs.integers(0, 2))
        bit, rc = _roundtrip(N, w, x, mu)
        assert bit == mu
        assert S.noise_margin(rc, mu) < 1.0


def test_satisfies_semantics():
    assert S.satisfies([0, 1, 1], [0, 2, 1])
    assert not S.satisfies([1, 1, 1], [0, 2, 1])


def test_operation_counts_are_independent_of_policy_size_on_device():
    assert S.op_counts(4)["device"] == S.op_counts(32)["device"] == S.m0
    assert S.op_counts(32)["ts"] > S.op_counts(4)["ts"]


def test_blinding_secret_is_binary_and_of_length_m0():
    pp = S.setup(2, seed=1)
    _, t = S.keygen(pp, [0, 1])
    assert t.shape == (S.m0,) and set(np.unique(t)) <= {0, 1}


if __name__ == "__main__":  # runs without pytest
    setup_module(None)
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
    teardown_module(None)
