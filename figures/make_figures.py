"""Draw the result figures as PDF (vector) and PNG with matplotlib.

    python figures/make_figures.py --data data/results.json --outdir figures/pdf

Options let you change the colour theme, the file format and the resolution
of the PNG copies. All text is deliberately small (6-7 pt) so that figures
inserted at column width carry type smaller than the 10 pt body text.
"""
import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

W = 4.9   # inches: about the MDPI text width, so no rescaling in LaTeX
THEMES = {
    "default": {},
    "gray": {k: v for k, v in zip(C.PALETTE, ["222222", "777777", "AAAAAA", "444444", "666666", "999999", "777777"])},
    "warm": {"lo": "B2182B", "local": "EF8A62", "naive": "67A9CF", "keygen": "2166AC", "enc": "D6604D", "ts": "92C5DE"},
}


def setup_style():
    plt.rcParams.update({
        "font.family": "serif", "font.serif": ["DejaVu Serif"],
        "mathtext.fontset": "cm", "pdf.fonttype": 42, "ps.fonttype": 42,
        "font.size": 6.5, "axes.labelsize": 6.5, "axes.titlesize": 6.5,
        "xtick.labelsize": 6, "ytick.labelsize": 6, "legend.fontsize": 6,
        "axes.linewidth": 0.5, "xtick.major.width": 0.5, "ytick.major.width": 0.5,
        "xtick.major.size": 2.0, "ytick.major.size": 2.0,
        "lines.linewidth": 1.0, "lines.markersize": 3.2,
        "axes.grid": True, "grid.linestyle": ":", "grid.linewidth": 0.4,
        "grid.color": "#b0b0b0", "axes.axisbelow": True,
        "legend.frameon": False, "figure.dpi": 150, "savefig.dpi": 300,
    })


def col(name, theme):
    return "#" + THEMES.get(theme, {}).get(name, C.PALETTE[name])


def legend_below(ax, ncol, y=-0.28, **kw):
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, y), ncol=ncol,
              handlelength=1.8, columnspacing=1.4, **kw)


def fig_time(D, th):
    fig, ax = plt.subplots(figsize=(W * 0.80, 2.35))
    N = D["N"]
    for key, lab, c, mk, ls in [("encrypt_ms", "Encrypt (DO)", "enc", "s", "-"),
                                ("keygen_ms", "KeyGen (TA)", "keygen", "^", "-"),
                                ("transform_us", "Transform (TS)", "ts", "o", "--")]:
        v = np.array(D[key])
        scale = 1e-3 if key == "transform_us" else 1.0
        ax.errorbar(N, v[:, 0] * scale, yerr=v[:, 1] * scale, color=col(c, th), marker=mk,
                    ls=ls, capsize=2, elinewidth=0.6, capthick=0.6, label=lab)
    ax.set_xscale("log", base=2); ax.set_yscale("log")
    ax.set_xticks(N); ax.get_xaxis().set_major_formatter(FuncFormatter(lambda v, _: f"{int(v)}"))
    ax.set_xlabel("Number of attribute positions $N$"); ax.set_ylabel("Time (ms)")
    legend_below(ax, 3)
    return fig


def fig_box(D, th):
    fig, ax = plt.subplots(figsize=(W * 0.88, 2.45))
    N = D["N"]
    pos_a = np.arange(len(N)) * 3.0
    pos_b = pos_a + 1.0
    def draw(boxes, pos, color):
        stats = [dict(med=b["med"], q1=b["q1"], q3=b["q3"], whislo=b["lo"], whishi=b["hi"],
                      fliers=b["outliers"]) for b in boxes]
        bp = ax.bxp(stats, positions=pos, widths=0.75, patch_artist=True, showfliers=True,
                    flierprops=dict(marker=".", markersize=1.6, markerfacecolor=color,
                                    markeredgecolor=color, alpha=0.6),
                    medianprops=dict(color="black", linewidth=0.8),
                    whiskerprops=dict(linewidth=0.5), capprops=dict(linewidth=0.5),
                    boxprops=dict(linewidth=0.5))
        for p in bp["boxes"]:
            p.set_facecolor(color); p.set_alpha(0.85)
        return bp["boxes"][0]
    h1 = draw(D["box_finish"], pos_a, col("lo", th))
    h2 = draw(D["box_local"], pos_b, col("local", th))
    ax.set_yscale("log")
    ax.set_xticks(pos_a + 0.5); ax.set_xticklabels([str(n) for n in N])
    ax.set_xlabel("Number of attribute positions $N$"); ax.set_ylabel("Latency per decryption ($\\mu$s)")
    ax.legend([h1, h2], ["Device step with outsourcing", "Whole decryption on the device"],
              loc="upper center", bbox_to_anchor=(0.5, -0.28), ncol=2, handlelength=1.4)
    return fig


def fig_noise(D, th):
    fig, ax = plt.subplots(figsize=(W * 0.80, 2.2))
    cnt, edges = C.hist_bins(D["margins_pct"], 14)
    ax.bar(edges[:-1], cnt, width=np.diff(edges), align="edge", color=col("lo", th),
           edgecolor="white", linewidth=0.4)
    ax.axvline(D["median_pct"], color="black", ls="--", lw=0.7)
    ax.text(D["median_pct"], cnt.max() * 1.02, f" median {D['median_pct']:.1f}%", fontsize=5.5, va="bottom")
    ax.set_xlabel("Decryption noise as a percentage of the threshold $q/4$ (decryption fails at 100%)")
    ax.set_ylabel("Number of trials")
    ax.set_ylim(0, cnt.max() * 1.18)
    return fig


def fig_sizes(D, th):
    fig, ax = plt.subplots(figsize=(W * 0.80, 2.55))
    N = D["N"]; x = np.arange(len(N)); w = 0.55
    cA = [p["cA"] for p in D["ct_parts_kib"]]
    cm = [p["comps"] for p in D["ct_parts_kib"]]
    tl = [p["tail"] for p in D["ct_parts_kib"]]
    ax.bar(x, cA, w, color=col("lo", th), label="$\\mathbf{c}_A$ (shared)")
    ax.bar(x, cm, w, bottom=cA, color=col("ts", th), label="Position components")
    ax.bar(x, tl, w, bottom=np.add(cA, cm), color=col("local", th), label="$c_0$ and $\\mathbf{c}_s$")
    ax.plot(x, D["ct_naive_kib"], color=col("naive", th), marker="v", ls="--", label="Naive layout (modeled)")
    for xi, v in zip(x, D["ct_kib"]):
        ax.text(xi, v + 18, f"{v:.0f}", ha="center", fontsize=5.5)
    ax.set_xticks(x); ax.set_xticklabels([str(n) for n in N])
    ax.set_xlabel("Number of attribute positions $N$"); ax.set_ylabel("Ciphertext size (KiB)")
    legend_below(ax, 2, y=-0.30)
    return fig


def fig_ops(D, th):
    fig, ax = plt.subplots(figsize=(W * 0.80, 2.35))
    N = D["N"]
    ax.plot(N, [o["device"] for o in D["ops"]], color=col("lo", th), marker="s", label="LO-ABE (outsourced)")
    ax.plot(N, [o["local"] for o in D["ops"]], color=col("local", th), marker="o", label="LO-ABE decrypted locally")
    ax.plot(N, [o["naive"] for o in D["ops"]], color=col("naive", th), marker="v", ls="--", label="Naive layout (modeled)")
    ax.set_xscale("log", base=2); ax.set_yscale("log")
    ax.set_xticks(N); ax.get_xaxis().set_major_formatter(FuncFormatter(lambda v, _: f"{int(v)}"))
    ax.set_xlabel("Number of attribute positions $N$"); ax.set_ylabel("Device operations (MAC equivalents)")
    legend_below(ax, 3)
    return fig


def fig_down(D, th):
    fig, ax = plt.subplots(figsize=(W * 0.88, 2.4))
    N = D["N"]; x = np.arange(len(N)); w = 0.26
    series = [("LO-ABE", D["dl_lo_kib"], "lo"), ("LO-ABE decrypted locally", D["ct_kib"], "local"),
              ("Naive layout (modeled)", D["ct_naive_kib"], "naive")]
    for i, (lab, v, c) in enumerate(series):
        b = ax.bar(x + (i - 1) * w, v, w, color=col(c, th), label=lab)
        for r, val in zip(b, v):
            ax.text(r.get_x() + r.get_width() / 2, val * 1.08, (f"{val:.0f}" if val > 99 else f"{val:.1f}"),
                    ha="center", fontsize=4.8)
    ax.set_yscale("log"); ax.set_ylim(8, 4000)
    ax.set_xticks(x); ax.set_xticklabels([str(n) for n in N])
    ax.set_xlabel("Number of attribute positions $N$"); ax.set_ylabel("Downlink to the device (KiB)")
    legend_below(ax, 3)
    return fig


def fig_heat(D, th):
    from matplotlib.colors import LinearSegmentedColormap
    fig, axs = plt.subplots(1, 2, figsize=(W, 2.15))
    fr = [f"{int(f * 100)}" for f in D["grid_frac"]]
    cmap = LinearSegmentedColormap.from_list("heat", ["#F0F8FF", col("ts", th)])
    for ax, M_, title, fmt in [(axs[0], D["grid_enc_s"], "(a) Encryption time (s)", "{:.2f}"),
                               (axs[1], D["grid_ct_kib"], "(b) Ciphertext size (KiB)", "{:.0f}")]:
        im = ax.imshow(M_, cmap=cmap, aspect="auto", origin="lower")
        ax.set_xticks(range(len(fr))); ax.set_xticklabels(fr)
        ax.set_yticks(range(len(D["grid_N"]))); ax.set_yticklabels(D["grid_N"])
        ax.set_xlabel("Wildcard positions (%)"); ax.set_ylabel("Attribute positions $N$")
        ax.set_title(title, fontsize=6.5)
        ax.grid(False)
        for i in range(M_.shape[0]):
            for j in range(M_.shape[1]):
                ax.text(j, i, fmt.format(M_[i, j]), ha="center", va="center", fontsize=5.2)
        # white cell borders
        for k in range(len(fr) + 1):
            ax.axvline(k - 0.5, color="white", lw=0.4); ax.axhline(k - 0.5, color="white", lw=0.4)
        cb = fig.colorbar(im, ax=ax, fraction=0.05, pad=0.03)
        cb.ax.tick_params(labelsize=5, width=0.4, length=1.5); cb.outline.set_linewidth(0.4)
    fig.tight_layout(w_pad=1.0)
    return fig


FIGS = {"fig_time": fig_time, "fig_box": fig_box, "fig_noise": fig_noise, "fig_sizes": fig_sizes,
        "fig_ops": fig_ops, "fig_down": fig_down, "fig_heat": fig_heat}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=C.DEFAULT_DATA)
    ap.add_argument("--outdir", default=os.path.join(C.HERE, "pdf"))
    ap.add_argument("--only", nargs="*", default=list(FIGS))
    ap.add_argument("--format", nargs="*", default=["pdf", "png"])
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--theme", default="default", choices=list(THEMES))
    a = ap.parse_args()
    setup_style()
    D = C.derive(C.load(a.data))
    os.makedirs(a.outdir, exist_ok=True)
    for name in a.only:
        fig = FIGS[name](D, a.theme)
        for fmt in a.format:
            fig.savefig(os.path.join(a.outdir, f"{name}.{fmt}"), format=fmt, dpi=a.dpi,
                        bbox_inches="tight", pad_inches=0.03,
                        metadata={"CreationDate": None} if fmt == "pdf" else None)
        plt.close(fig)
        print("wrote", name)


if __name__ == "__main__":
    main()
