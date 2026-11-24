# LO-ABE: Lattice-based Outsourced-decryption ABE

Research prototype, benchmarks and figure scripts for **LO-ABE: Lattice-Based Outsourced-Decryption
Attribute-Based Encryption for Mobile Clouds**.

LO-ABE is a ciphertext-policy attribute-based encryption scheme for AND-policies with wildcards over
`N` binary attributes. It is based on standard LWE. The user blinds the key target with a short binary
secret, a cloud server turns the ciphertext into a single element of `Z_q`, and the device finishes with
one binary inner product. The device cost therefore does not grow with the policy size.

> **Status.** This is a measurement prototype, not a library. The preimage sampler is a gadget-based
> perturbed sampler whose Gaussian perturbation is not spherical, so the security argument for the exact
> sampler does not apply to it. The benchmark parameters (`n = 128`, `q = 2^32`) are not secure and do not
> meet the proof's width and noise conditions beyond small policy sizes. The lattice estimator was not run;
> the article gives a projected parameter set with an estimate from a core-SVP model, and its costs are
> computed from the scheme's formulas, not measured. The payload is one bit. Do not use this code to
> protect real data. Each limitation is discussed in the accompanying article.

## Repository layout

```
src/loabe/scheme.py            Setup, KeyGen, Encrypt, Transform, Decrypt (NumPy), sizes and operation counts
tests/test_scheme.py           fast correctness tests with a small lattice dimension (n = 16)
tests/test_data.py             consistency checks for data/results.json and the numbers behind the figures
benchmarks/run_benchmarks.py   benchmark driver; writes raw samples to data/results.json
benchmarks/device_microbench.c native C timing of the device step and of local decryption
data/results.json              raw measurements behind every table and figure
figures/pdf/                   all figures of the article as PDF (data figures also as PNG)
```

## Quick start

```bash
pip install -r requirements.txt
python tests/test_scheme.py                    # about 30 seconds
python benchmarks/run_benchmarks.py --quick    # smoke test, about a minute
```

Full benchmark (about 10 minutes on a 2-vCPU server; needs about 1 GB of memory):

```bash
python benchmarks/run_benchmarks.py --out data/results.json
```

## Figures

All figures of the article are provided as PDF files in `figures/pdf/`, and the data figures also as PNG.
They are drawn from `data/results.json`. The consistency of that file and of the numbers behind the figures
can be checked with:

```bash
python tests/test_data.py
```

## Native microbenchmark

```bash
gcc -O2 -o device_microbench benchmarks/device_microbench.c
./device_microbench 32 128 32 80 16 200        # word bits, n, log2 q, lambda, N, repetitions
```

It prints one JSON line with the median and quartiles, in nanoseconds, of the device step (additions only)
and of local decryption (multiply-accumulates plus the device step).

## Experiments

| Experiment | What it measures | Figure |
|---|---|---|
| correctness | 200 randomized end-to-end trials at `N = 8` and 60 at `N = 32`; decryption noise as a percentage of `q/4` | histogram |
| timing | KeyGen and Encrypt (15 runs), Transform (450), device step (2250), local decryption (450) for `N = 4..32`; medians and interquartile ranges | line plot, box plot |
| sizes and operations | exact byte counts and operation counts (additions and multiply-accumulates reported separately) | stacked bars, line plot, grouped bars |
| wildcard grid | encryption time and ciphertext size over `N` x wildcard fraction | heat maps |
| native microbenchmark | device step and local decryption in C, with and without vectorization | table in the article |

The only baseline is the local-decryption variant of LO-ABE, implemented here and measured at identical
parameters. No published scheme is re-implemented. Python timings include interpreter overhead and are used
for growth trends; the conclusions rest on operation counts, bytes and the C timings. No ARM device or
energy measurements are included.

## Citation

If you use this code, please cite the article (details to be added after publication).

## License

MIT, see `LICENSE`.
