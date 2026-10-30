# LO-ABE: Lattice-based Outsourced-decryption ABE

Research prototype, benchmarks and figure scripts for **LO-ABE: Lattice-Based Outsourced-Decryption
Attribute-Based Encryption for Mobile Clouds**.

LO-ABE is a ciphertext-policy attribute-based encryption scheme for AND-policies with wildcards over
`N` binary attributes. It is based on standard LWE. The user blinds the key target with a short binary
secret, a cloud server turns the ciphertext into a single element of `Z_q`, and the device finishes with
one binary inner product. The device cost therefore does not grow with the policy size.

> **Status.** This is a measurement prototype, not a library. The preimage sampler is a gadget-based
> perturbed sampler, the benchmark parameters (`n = 128`, `q = 2^32`) satisfy the dimension conditions of the
> proof but not its full smoothing margins, no lattice-estimator run backs a bit-security claim, and the
> payload is one bit. Do not use it to protect real data. Each limitation is discussed in the accompanying article.

## Repository layout

```
src/loabe/scheme.py          Setup, KeyGen, Encrypt, Transform, Decrypt (NumPy), sizes and operation counts
tests/test_scheme.py         fast correctness tests with a small lattice dimension (n = 16)
benchmarks/run_benchmarks.py benchmark driver; writes raw samples to data/results.json
data/results.json            raw measurements behind every table and figure
figures/common.py            shared data preparation (box statistics, histograms, heat-map matrices)
figures/make_figures.py      figures as PDF/PNG (matplotlib); themes, formats and DPI are options
figures/diagrams/*.tikz      TikZ sources of the system-model and protocol-phase diagrams
figures/build_diagrams.py    compiles the two diagrams to PDF (needs pdflatex + standalone)
figures/tikz_preamble.tex    preamble lines needed to \input the diagrams in a LaTeX document
tests/test_data.py           consistency checks for data/results.json and the figure numbers
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

## Reproducing the figures

```bash
python figures/make_figures.py                 # figures/pdf/*.pdf and *.png (matplotlib)
python figures/make_figures.py --theme gray    # other colour themes: default, gray, warm
python figures/build_diagrams.py               # figures/pdf/fig_system_model.pdf, fig_protocol_phases.pdf
python tests/test_data.py                      # checks that the data and derived numbers are consistent
```

The diagram files in `figures/diagrams/` hold a bare `tikzpicture`. Paste one into a `figure` environment, or `\input` it, after
adding the lines of `figures/tikz_preamble.tex` to your document preamble. To use the PDF versions instead,
include `figures/pdf/*.pdf` with `\includegraphics`.

## Experiments

| Experiment | What it measures | Figure |
|---|---|---|
| correctness | 120 randomized end-to-end trials at `N = 8`; decryption noise as a percentage of `q/4` | histogram |
| timing | KeyGen, Encrypt (7 runs), Transform (200), device step (1000), local decryption (200) for `N = 4..32` | line plot with error bars, box plot |
| sizes and operations | exact byte and MAC counts (machine independent) | stacked bars, line plot, grouped bars |
| wildcard grid | encryption time and ciphertext size over `N` x wildcard fraction | heat maps |

The "naive layout" in the figures is a **model** of an attribute-by-attribute lattice CP-ABE in the style of
Agrawal et al. and Zhang and Zhang (every component a full `(M + m)`-vector). It is not a re-implementation of
those schemes.

## Citation

If you use this code, please cite the article (details to be added after publication).

## License

MIT, see `LICENSE`.
