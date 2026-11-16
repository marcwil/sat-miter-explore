"""Plots for the report (static PNGs, light surface, reference categorical palette)."""
import os, re, json, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SER = {"A": "#2a78d6", "Aw": "#eb6834", "B": "#1baf7a", "Bw": "#eda100"}
TOOLC = {"cadical": "#2a78d6", "kissat": "#eb6834", "abc_cec": "#1baf7a", "abc_gcec": "#eda100",
         "cadical_nocc": "#6250d6", "kissat_nocc": "#e34948", "sweep": "#e87ba4"}
LABEL = {"A": "A (random bijections)", "Aw": "A_w (weighted controls)", "B": "B (x_a ^= phi(x_b,x_c))",
         "Bw": "B_w (weighted control)"}
OUT = "results/plots"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#e4e3df", "grid.linewidth": 0.6,
                     "axes.edgecolor": "#8a8984", "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
                     "savefig.facecolor": "#fcfcfb", "lines.linewidth": 2, "lines.markersize": 6})


def parse_name(nm):
    m = re.match(r"(\w+?)_n(\d+)_d(\d+)_m([\d.]+)_w(\d+)_t([\d.]+)_s(\d+)(?:_b([\d.]+))?", nm)
    g, n, d, mp, w, tf, s, b = m.groups()
    return dict(gset=g, n=int(n), d=int(d), tfrac=float(tf), seed=int(s), beta=float(b) if b else None)


def xpos(tf):
    # symbolic x axis: t/m = 0 drawn at 0.03 on log scale
    return np.where(np.asarray(tf) == 0, 0.03, tf)


def setx(ax):
    ax.set_xscale("log")
    ax.set_xticks([0.03, 0.1, 0.3, 1, 3, 10])
    ax.set_xticklabels(["0", "0.1", "0.3", "1", "3", "10"])
    ax.set_xlabel("rewrite steps t / gates m")


def plot_e2(csvfile):
    d = pd.read_csv(csvfile)
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), sharey=True)
    for ax, col, title in zip(axes, ["eq_frac", "rel_frac", "gate_frac"],
                              ["signals with an equal/complement signal", "gate groups with a bijective partner",
                               "gates surviving verbatim"]):
        for g, c in SER.items():
            s = d[d.gset == g].groupby("tfrac")[col].agg(["mean", "min", "max"]).reset_index()
            if s.empty:
                continue
            x = xpos(s.tfrac)
            ax.plot(x, s["mean"], "-o", color=c, label=LABEL[g])
            ax.fill_between(x, s["min"], s["max"], color=c, alpha=0.12, linewidth=0)
        setx(ax); ax.set_title(title, fontsize=10); ax.set_ylim(-0.02, 1.02)
    axes[0].set_ylabel("fraction of C_0 (n = 64, m = 8n)")
    axes[2].legend(frameon=False, fontsize=8, loc="lower left")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "e2_survival.png"), dpi=150); plt.close(fig)


def load_sweep(f):
    s = pd.read_csv(f)
    return pd.DataFrame(dict(instance=s.instance, tool="sweep", status=s.status, time=s.t_total))


def plot_e3(csvfiles, n, tools, fname, timeout, sweepfiles=()):
    d = pd.concat([pd.read_csv(f) for f in csvfiles] + [load_sweep(f) for f in sweepfiles if os.path.exists(f)])
    meta = pd.DataFrame([parse_name(x) for x in d.instance])
    d = pd.concat([d.reset_index(drop=True), meta], axis=1)
    d = d[(d.n == n) & (d.beta.isna() | (d.beta == 2.5))]
    d["t_eff"] = np.where(d.status == "UNSAT", d.time, timeout)
    gsets = [g for g in SER if g in set(d.gset)]
    fig, axes = plt.subplots(1, len(gsets), figsize=(3.3 * len(gsets), 3.4), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, g in zip(axes, gsets):
        for tool in tools:
            s = d[(d.gset == g) & (d.tool == tool)]
            if s.empty:
                continue
            a = s.groupby("tfrac").t_eff.agg(["median", "min", "max"]).reset_index()
            x = xpos(a.tfrac)
            ax.plot(x, a["median"], "-o", color=TOOLC[tool], label=tool)
            ax.fill_between(x, a["min"], a["max"], color=TOOLC[tool], alpha=0.12, linewidth=0)
        ax.axhline(timeout, color="#8a8984", lw=1, ls="--")
        setx(ax); ax.set_yscale("log"); ax.set_title(LABEL[g], fontsize=10)
    axes[0].set_ylabel("solve time [s] (median, min-max over seeds)\n dashed = timeout")
    axes[-1].legend(frameon=False, fontsize=8, loc="upper left")
    fig.suptitle("n = %d wires, m = 8n gates" % n, fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, fname), dpi=150); plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    what = sys.argv[1:]
    if "e2" in what:
        plot_e2("results/e2_stats.csv")
    if "e3" in what:
        tools = ["cadical", "kissat", "abc_cec", "abc_gcec", "sweep"]
        plot_e3(["results/e3_n64.csv"], 64, tools, "e3_n64.png", 300, ["results/e4_sweep_n64.csv"])
        if os.path.exists("results/e3_big.csv"):
            for n in (128, 256):
                plot_e3(["results/e3_big.csv"], n, tools, "e3_n%d.png" % n, 300, ["results/e4_sweep_big.csv"])
