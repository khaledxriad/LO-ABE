"""Write the result figures as pgfplots/TikZ code (one .tikz file per figure).

    python figures/make_pgfplots.py --data data/results.json --outdir figures/tikz

The files contain a bare tikzpicture, so they can be pasted into a figure
environment. They need the packages, colors and styles in figures/tikz_preamble.tex,
which use the same palette as the matplotlib script.
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

# colour names defined in the preamble
CN = {"lo": "loBlue", "local": "loOrange", "naive": "loRed", "keygen": "loGreen",
      "enc": "loPink", "ts": "loSky"}


def f(v, p=4):
    return f"{v:.{p}g}"


def coords(xs, ys, err=None):
    if err is None:
        return " ".join(f"({f(x)},{f(y)})" for x, y in zip(xs, ys))
    return " ".join(f"({f(x)},{f(y)}) +- (0,{f(e)})" for x, y, e in zip(xs, ys, err))


def logx_axis(N):
    return ("xmode=log, log basis x=2, xtick={%s}, xticklabels={%s}, minor x tick num=0"
            % (",".join(map(str, N)), ",".join(map(str, N))))


def fig_time(D):
    N = D["N"]
    out = ["\\begin{tikzpicture}",
           "\\begin{axis}[lochart, ymode=log, %s, xlabel={Number of attribute positions $N$}, ylabel={Time (ms)}]" % logx_axis(N)]
    for key, lab, c, mk, dash in [("encrypt_ms", "Encrypt (DO)", "enc", "square*", ""),
                                  ("keygen_ms", "KeyGen (TA)", "keygen", "triangle*", ""),
                                  ("transform_us", "Transform (TS)", "ts", "*", "dashed")]:
        v = np.array(D[key]); s = 1e-3 if key == "transform_us" else 1.0
        out.append("\\addplot+[color=%s, mark=%s, mark options={solid,fill=%s}, %s, error bars/.cd, y dir=both, y explicit, error bar style={line width=0.4pt}, error mark options={rotate=90, mark size=1.5pt, line width=0.4pt}] coordinates {%s};"
                   % (CN[c], mk, CN[c], dash, coords(N, v[:, 0] * s, v[:, 1] * s)))
        out.append("\\addlegendentry{%s}" % lab)
    out += ["\\end{axis}", "\\end{tikzpicture}"]
    return "\n".join(out)


def _box(b, pos, color):
    outl = "\\\\ ".join(f(v, 5) for v in b["outliers"])
    tab = ("table[row sep=\\\\, y index=0] {%s \\\\}" % outl) if len(b["outliers"]) else "coordinates {}"
    return ("\\addplot+[forget plot, fill=%s!85, draw=black, line width=0.35pt, mark=*, mark size=0.5pt, mark options={fill=%s, draw=%s}, "
            "boxplot prepared={draw position=%s, box extend=0.75, lower whisker=%s, lower quartile=%s, median=%s, upper quartile=%s, upper whisker=%s, "
            "every median/.style={line width=0.8pt}, every whisker/.style={line width=0.35pt}}] %s;"
            % (color, color, color, f(pos), f(b["lo"], 5), f(b["q1"], 5), f(b["med"], 5), f(b["q3"], 5), f(b["hi"], 5), tab))


def fig_box(D):
    N = D["N"]
    out = ["\\begin{tikzpicture}",
           "\\begin{axis}[lochart, width=0.9\\linewidth, height=5.6cm, ymode=log, xlabel={Number of attribute positions $N$}, ylabel={Latency per decryption ($\\mu$s)}, "
           "xtick={%s}, xticklabels={%s}, xmin=-1, xmax=%s, boxplot/draw direction=y, "
           "legend style={at={(0.5,-0.27)}, anchor=north, legend columns=2}]"
           % (",".join(f(i * 3 + 0.5) for i in range(len(N))), ",".join(map(str, N)), f(len(N) * 3 - 1))]
    for i, (bf, bl) in enumerate(zip(D["box_finish"], D["box_local"])):
        out.append(_box(bf, i * 3.0, CN["lo"]))
        out.append(_box(bl, i * 3.0 + 1.0, CN["local"]))
    out.append("\\addlegendimage{area legend, fill=%s!85, draw=black, line width=0.35pt}\\addlegendentry{Device step with outsourcing}" % CN["lo"])
    out.append("\\addlegendimage{area legend, fill=%s!85, draw=black, line width=0.35pt}\\addlegendentry{Whole decryption on the device}" % CN["local"])
    out += ["\\end{axis}", "\\end{tikzpicture}"]
    return "\n".join(out)


def fig_noise(D):
    cnt, edges = C.hist_bins(D["margins_pct"], 14)
    pts = [(edges[i], cnt[i]) for i in range(len(cnt))] + [(edges[-1], cnt[-1])]
    top = cnt.max() * 1.18
    out = ["\\begin{tikzpicture}",
           "\\begin{axis}[lochart, ybar interval, xlabel={Decryption noise as a percentage of the threshold $q/4$ (decryption fails at 100\\%%)}, "
           "ylabel={Number of trials}, ymin=0, ymax=%s, xmin=%s, xmax=%s]" % (f(top), f(edges[0]), f(edges[-1])),
           "\\addplot+[fill=%s, draw=white, line width=0.3pt] coordinates {%s};"
           % (CN["lo"], " ".join(f"({f(x)},{int(y)})" for x, y in pts)),
           "\\draw[dashed, line width=0.5pt] (axis cs:%s,0) -- (axis cs:%s,%s);" % (f(D["median_pct"]), f(D["median_pct"]), f(cnt.max() * 1.05)),
           "\\node[anchor=south west, font=\\fontsize{5.5}{6}\\selectfont, inner sep=1pt] at (axis cs:%s,%s) {median %.1f\\%%};"
           % (f(D["median_pct"]), f(cnt.max() * 1.0), D["median_pct"]),
           "\\end{axis}", "\\end{tikzpicture}"]
    return "\n".join(out)


def fig_sizes(D):
    N = D["N"]; x = list(range(len(N)))
    cA = [p["cA"] for p in D["ct_parts_kib"]]
    cm = [p["comps"] for p in D["ct_parts_kib"]]
    tl = [p["tail"] for p in D["ct_parts_kib"]]
    out = ["\\begin{tikzpicture}",
           "\\begin{axis}[lochart, ybar stacked, bar width=0.9cm, xtick={%s}, xticklabels={%s}, xlabel={Number of attribute positions $N$}, "
           "ylabel={Ciphertext size (KiB)}, ymin=0, enlarge x limits=0.15, legend style={at={(0.5,-0.30)}, anchor=north, legend columns=2}]"
           % (",".join(map(str, x)), ",".join(map(str, N)))]
    for ys, lab, c in [(cA, "$\\mathbf{c}_A$ (shared)", "lo"), (cm, "Position components", "ts"), (tl, "$c_0$ and $\\mathbf{c}_s$", "local")]:
        out.append("\\addplot+[fill=%s, draw=none] coordinates {%s};" % (CN[c], coords(x, ys)))
        out.append("\\addlegendentry{%s}" % lab)
    out.append("\\addplot[stack plots=false, sharp plot, fill=none, draw=%s, mark=triangle*, mark options={rotate=180, solid, fill=%s, draw=%s}, dashed, line width=0.7pt] coordinates {%s};"
               % (CN["naive"], CN["naive"], CN["naive"], coords(x, D["ct_naive_kib"])))
    out.append("\\addlegendentry{Naive layout (modeled)}")
    for xi, v in zip(x, D["ct_kib"]):
        out.append("\\node[anchor=south, font=\\fontsize{5.5}{6}\\selectfont, inner sep=1pt] at (axis cs:%d,%s) {%.0f};" % (xi, f(v + 12), v))
    out += ["\\end{axis}", "\\end{tikzpicture}"]
    return "\n".join(out)


def fig_ops(D):
    N = D["N"]
    out = ["\\begin{tikzpicture}",
           "\\begin{axis}[lochart, ymode=log, %s, xlabel={Number of attribute positions $N$}, ylabel={Device operations (MAC equivalents)}]" % logx_axis(N)]
    for key, lab, c, mk, dash in [("device", "LO-ABE (outsourced)", "lo", "square*", ""),
                                  ("local", "LO-ABE decrypted locally", "local", "*", ""),
                                  ("naive", "Naive layout (modeled)", "naive", "triangle*", "dashed")]:
        out.append("\\addplot+[color=%s, mark=%s, mark options={solid,fill=%s}, %s] coordinates {%s};"
                   % (CN[c], mk, CN[c], dash, coords(N, [o[key] for o in D["ops"]])))
        out.append("\\addlegendentry{%s}" % lab)
    out += ["\\end{axis}", "\\end{tikzpicture}"]
    return "\n".join(out)


def fig_down(D):
    N = D["N"]; x = list(range(len(N)))
    out = ["\\begin{tikzpicture}",
           "\\begin{axis}[lochart, width=0.9\\linewidth, ybar, bar width=8pt, ymode=log, ymin=8, ymax=4000, xtick={%s}, xticklabels={%s}, "
           "xlabel={Number of attribute positions $N$}, ylabel={Downlink to the device (KiB)}, enlarge x limits=0.15, "
           "point meta=explicit symbolic, nodes near coords, nodes near coords style={font=\\fontsize{4.8}{5}\\selectfont, inner sep=1pt, anchor=south, rotate=0, text=black}, "
           "legend style={at={(0.5,-0.27)}, anchor=north, legend columns=3}]" % (",".join(map(str, x)), ",".join(map(str, N)))]
    for lab, v, c in [("LO-ABE", D["dl_lo_kib"], "lo"), ("LO-ABE decrypted locally", D["ct_kib"], "local"),
                      ("Naive layout (modeled)", D["ct_naive_kib"], "naive")]:
        cs = " ".join("(%d,%s) [%s]" % (xi, f(val), ("%.0f" % val) if val > 99 else ("%.1f" % val)) for xi, val in zip(x, v))
        out.append("\\addplot+[fill=%s, draw=none] coordinates {%s};" % (CN[c], cs))
        out.append("\\addlegendentry{%s}" % lab)
    out += ["\\end{axis}", "\\end{tikzpicture}"]
    return "\n".join(out)


def _heat(M_, title, prec, name, at, ylabel=True):
    rows, cols = M_.shape
    tab = " \\\\ ".join(f"{j} {i} {M_[i, j]:.6g}" for i in range(rows) for j in range(cols)) + " \\\\"
    return ("\\begin{axis}[name=%s, %s, width=0.40\\linewidth, height=4.0cm, enlargelimits=false, axis on top, grid=none, title={%s}, "
            "title style={font=\\fontsize{6.5}{8}\\selectfont}, tick label style={font=\\figtiny}, label style={font=\\figsmall}, xlabel={Wildcard positions (\\%%)}, %s "
            "xtick={0,1,2,3}, xticklabels={0,25,50,75}, ytick={0,1,2,3}, yticklabels={4,8,16,32}, "
            "colorbar, colormap={heat}{rgb255=(240,248,255) rgb255=(86,180,233)}, colorbar style={width=0.12cm, ytick style={line width=0.3pt}, "
            "tick label style={font=\\fontsize{5}{6}\\selectfont}}, point meta=explicit, "
            "nodes near coords={\\pgfmathprintnumber[fixed,precision=%d]{\\pgfplotspointmeta}}, nodes near coords style={font=\\fontsize{5.2}{6}\\selectfont, anchor=center}]\n"
            "\\addplot[matrix plot*, mesh/rows=%d, mesh/cols=%d, point meta=explicit, draw=white, line width=0.3pt] table[row sep=\\\\, x index=0, y index=1, meta index=2] {%s};\n"
            "\\end{axis}" % (name, at, title, ("ylabel={Attribute positions $N$}," if ylabel else ""), prec, rows, cols, tab))


def fig_heat(D):
    return "\n".join(["\\begin{tikzpicture}",
                      _heat(D["grid_enc_s"], "(a) Encryption time (s)", 2, "ha", ""),
                      _heat(D["grid_ct_kib"], "(b) Ciphertext size (KiB)", 0, "hb",
                            "at={(ha.east)}, anchor=west, xshift=1.6cm", ylabel=False),
                      "\\end{tikzpicture}"])


FIGS = {"fig_time": fig_time, "fig_box": fig_box, "fig_noise": fig_noise, "fig_sizes": fig_sizes,
        "fig_ops": fig_ops, "fig_down": fig_down, "fig_heat": fig_heat}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=C.DEFAULT_DATA)
    ap.add_argument("--outdir", default=os.path.join(C.HERE, "tikz"))
    a = ap.parse_args()
    D = C.derive(C.load(a.data))
    os.makedirs(a.outdir, exist_ok=True)
    for name, fn in FIGS.items():
        with open(os.path.join(a.outdir, name + ".tikz"), "w") as fh:
            fh.write(fn(D) + "\n")
        print("wrote", name)


if __name__ == "__main__":
    main()
