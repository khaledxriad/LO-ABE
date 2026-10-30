"""Compile the two TikZ diagrams (system model, protocol phases) to PDF.

    python figures/build_diagrams.py --outdir figures/pdf

Needs pdflatex with the standalone class. The Algorithm numbers shown in the
phase diagram are fixed here (Alg. 1-5) because a standalone PDF has no
cross-references; they match the order of Algorithms 1-5 in the paper.
"""
import argparse
import os
import shutil
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
WRAP = r"""\documentclass[tikz,border=3pt]{standalone}
\usepackage{amsmath,amssymb}
\usetikzlibrary{shapes,arrows,positioning,fit,backgrounds}
\newcommand{\AlgRef}[1]{\csname algnum#1\endcsname}
\def\algnumsetup{1}\def\algnumkeygen{2}\def\algnumenc{3}\def\algnumtrans{4}\def\algnumdec{5}
\begin{document}
%s
\end{document}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=os.path.join(HERE, "pdf"))
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    for name in ("fig_system_model", "fig_protocol_phases"):
        body = open(os.path.join(HERE, "diagrams", name + ".tikz"), encoding="utf-8").read()
        with tempfile.TemporaryDirectory() as td:
            tex = os.path.join(td, name + ".tex")
            open(tex, "w", encoding="utf-8").write(WRAP % body)
            subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", name + ".tex"],
                           cwd=td, check=True, stdout=subprocess.DEVNULL)
            shutil.copy(os.path.join(td, name + ".pdf"), os.path.join(a.outdir, name + ".pdf"))
        print("wrote", name)


if __name__ == "__main__":
    main()
