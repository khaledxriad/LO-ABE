"""Prototype of LO-ABE (lattice CP-ABE with blinded outsourced decryption).

Wildcard-AND policies over N binary attribute positions, single-bit KEM payload.

This is a research prototype. The preimage sampler is a gadget-based perturbed
sampler (not the exact spherical sampler of the proof), and the default
parameters are tuned for measurement, not for a proven security level.
All arithmetic is modulo q = 2^k with k = 32, carried out in int64 where the
natural wrap-around of 64-bit integers is harmless because q divides 2^64.
"""
import numpy as np

# ----------------------------------------------------------------- parameters
n = 128
k = 32
q = 1 << k
mask = q - 1
m = n * k
lam = 80
mbar = n * k + 2 * lam
M = mbar + m
m0 = n * k + 2 * lam
SIG = 3.2          # ciphertext noise width
SIG_R = 2.0        # trapdoor width
S_KEY = 512.0      # width of e_{i,2}
S_PERT = 64.0      # perturbation width

rng = np.random.default_rng(12345)


def configure(n_=128, k_=32, lam_=80, sig=3.2, sig_r=2.0, s_key=512.0,
              s_pert=64.0, seed=12345):
    """Reset the global parameters (used by the unit tests with a small n)."""
    global n, k, q, mask, mbar, m, M, lam, m0, SIG, SIG_R, S_KEY, S_PERT, rng
    n, k, lam = n_, k_, lam_
    q = 1 << k
    mask = q - 1
    m = n * k
    mbar = n * k + 2 * lam
    M = mbar + m
    m0 = n * k + 2 * lam
    SIG, SIG_R, S_KEY, S_PERT = sig, sig_r, s_key, s_pert
    rng = np.random.default_rng(seed)


def params():
    return dict(n=n, k=k, q=q, m=m, mbar=mbar, M=M, m0=m0, lam=lam,
                sigma=SIG, s_key=S_KEY, s_pert=S_PERT, sigma_R=SIG_R)


def gauss(sig, size):
    return np.rint(rng.normal(0, sig, size)).astype(np.int64)


def centered(x):
    x = x & mask
    return np.where(x >= q // 2, x - q, x)


class PP:
    """Public parameters plus the master trapdoor R."""


def setup(N, seed=777):
    pp = PP()
    pp.N = N
    pp.seed = seed
    r = np.random.default_rng(seed)
    Abar = r.integers(0, q, (n, mbar), dtype=np.int64)
    R = np.rint(r.normal(0, SIG_R, (mbar, m))).astype(np.int64)
    G = np.zeros((n, m), dtype=np.int64)
    for i in range(n):
        G[i, i * k:(i + 1) * k] = 1 << np.arange(k)
    AR = np.rint(Abar.astype(np.float64) @ R.astype(np.float64)).astype(np.int64)
    A2 = (G - AR) & mask
    pp.A = np.concatenate([Abar, A2], axis=1)
    pp.R = R              # master trapdoor
    pp.u = r.integers(0, q, n, dtype=np.int64)
    pp.A0 = r.integers(0, q, (n, m0), dtype=np.int64)
    return pp


def Bmat(pp, i, b):
    r = np.random.default_rng([pp.seed, 1000 + i, b])
    return r.integers(0, q, (n, m), dtype=np.int64)


def gadget_inv(v):
    bits = (v[:, None] >> np.arange(k)) & 1
    return bits.reshape(n * k).astype(np.int64)


def sample_pre(pp, v):
    p = gauss(S_PERT, M)
    vv = (v - pp.A @ p) & mask
    z = gadget_inv(vv)
    e = p.copy()
    e[:mbar] += pp.R @ z
    e[mbar:] += z
    return e


def keygen(pp, x):
    """Interactive key generation: returns (TK_x, RK) where RK = t stays on the device."""
    N = pp.N
    t = rng.integers(0, 2, m0, dtype=np.int64)
    T = (pp.u + pp.A0 @ t) & mask
    shares = [rng.integers(0, q, n, dtype=np.int64) for _ in range(N - 1)]
    last = T.copy()
    for sh in shares:
        last = (last - sh) & mask
    shares.append(last)
    bar_e1 = np.zeros(M, dtype=np.int64)
    e2s = []
    for i in range(N):
        B = Bmat(pp, i, x[i])
        e2 = gauss(S_KEY, m)
        v = (shares[i] - B @ e2) & mask
        e1 = sample_pre(pp, v)
        bar_e1 += e1
        e2s.append(e2)
    return dict(x=list(x), bar_e1=bar_e1, e2=e2s), t


def encrypt(pp, w, mu):
    """w[i] in {0, 1, 2}; 2 stands for the wildcard."""
    N = pp.N
    s = rng.integers(0, q, n, dtype=np.int64)
    y = gauss(SIG, M)
    yf = y.astype(np.float32)
    cA = (pp.A.T @ s + y) & mask
    comps = {}
    for i in range(N):
        allowed = [0, 1] if w[i] == 2 else [w[i]]
        for b in allowed:
            bits = np.unpackbits(rng.integers(0, 256, M * m // 8, dtype=np.uint8)).reshape(M, m).astype(np.float32)
            z = np.rint(bits.T @ yf).astype(np.int64)
            del bits
            comps[(i, b)] = (Bmat(pp, i, b).T @ s + z) & mask
    c0 = (pp.u @ s + gauss(SIG, 1)[0] + mu * (q // 2)) & mask
    cs = (pp.A0.T @ s + gauss(SIG, m0)) & mask
    return dict(w=list(w), cA=cA, comps=comps, c0=int(c0), cs=cs)


def transform(tk, ct):
    """Run by the transformation server: returns one element of Z_q."""
    acc = int(tk['bar_e1'] @ ct['cA'])
    for i, b in enumerate(tk['x']):
        acc += int(tk['e2'][i] @ ct['comps'][(i, b)])
    return acc & mask


def finish(ct, yt, t):
    """Run on the device: one binary inner product and a threshold."""
    r = (ct['c0'] - yt + int(t @ ct['cs'])) & mask
    rc = r - q if r >= q // 2 else r
    return (1 if abs(rc) > q // 4 else 0), rc


def noise_margin(rc, mu):
    """|E| / (q/4): the fraction of the decision margin consumed by noise."""
    target = mu * (q // 2)
    d = (rc - target) & mask
    d = d - q if d >= q // 2 else d
    return abs(d) / (q / 4)


def satisfies(x, w):
    return all(w[i] == 2 or w[i] == x[i] for i in range(len(x)))


def sizes(pp, w):
    N = pp.N
    ncomp = sum(2 if wi == 2 else 1 for wi in w)
    pk_full = (n * M + n + n * m0 + 2 * N * n * m) * 4
    pk_seed = (n * M + n + n * m0) * 4 + 32
    tk = M * 4 + N * m * 2
    ct = (M + ncomp * m + m0 + 1) * 4
    # modelled attribute-by-attribute layout: every component is a full (M+m)-vector
    ct_naive = (ncomp * (M + m) + m0 + 1) * 4
    ct_parts = dict(cA=M * 4, comps=ncomp * m * 4, tail=(m0 + 1) * 4)
    return dict(pk_full=pk_full, pk_seed=pk_seed, tk=tk, rk=m0 // 8, ct=ct,
                ct_naive=ct_naive, ct_parts=ct_parts, ncomp=ncomp)


def op_counts(N):
    """Exact multiply-accumulate counts (machine independent)."""
    ts = M + N * m          # transformation server: M + N*m MACs
    device = m0             # additions on the device
    local = ts + device
    naive = N * (M + m)     # modelled attribute-by-attribute layout, per-position (M+m)-vector
    return dict(ts=ts, device=device, local=local, naive=naive)
