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


R2C = {"w3": "#2a78d6", "knead": "#eb6834", "ik": "#1baf7a"}
R2L = {"w3": "w=3 same size (round 1)", "knead": "knead 4 -> 4", "ik": "inflate 2->4 + knead + deflate"}


def plot_r2_width(csvfile, fname="r2_width.png", null=None):
    d = pd.read_csv(csvfile)
    d = d[d.gset == "B"]
    cols = [("wire_mean", "mean wire width (C_0 cut wires a C_t wire depends on)"),
            ("wire_le3", "fraction of C_t wires with width <= 3"),
            ("gate_frac", "C_0 gates surviving verbatim"),
            ("rel_frac", "gate groups with a bijective partner")]
    fig, axes = plt.subplots(1, 4, figsize=(15, 3.6))
    for ax, (col, title) in zip(axes, cols):
        for mode, c in R2C.items():
            s = d[d["mode"] == mode].groupby("tfrac")[col].agg(["mean", "min", "max"]).reset_index()
            if s.empty:
                continue
            ax.plot(s.tfrac, s["mean"], "-o", color=c, label=R2L[mode])
            ax.fill_between(s.tfrac, s["min"], s["max"], color=c, alpha=0.12, linewidth=0)
        if null and col in null:
            ax.axhline(null[col], color="#8a8984", ls="--", lw=1, label="unrelated circuit (null)")
        ax.set_xscale("log"); ax.set_xticks([0.3, 1, 3, 10]); ax.set_xticklabels(["0.3", "1", "3", "10"])
        ax.set_xlabel("rewrite steps t / gates m"); ax.set_title(title, fontsize=9)
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle("gate set B, n = 64, m = 512", fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, fname), dpi=150); plt.close(fig)


def plot_r2_long(csvfile, fname="r2_long.png", nulls={32: (20.7, 0.17), 64: (29.5, 0.16)}):
    d = pd.read_csv(csvfile)
    d = d[d.gset == "B"].copy()
    d["label"] = d.apply(lambda r: "%s, n=%d%s" % (r["mode"], r["n"], ", size 3m" if "_x3" in r["instance"] else ""), axis=1)
    pal = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
    for ax, (col, title) in zip(axes, [("wire_mean", "mean wire width"), ("wire_le3", "fraction of wires with width <= 3"),
                                       ("gate_frac", "C_0 gates surviving verbatim")]):
        for c, (lab, s) in zip(pal, sorted(d.groupby("label"), key=lambda x: x[0])):
            s = s.sort_values("tfrac")
            ax.plot(s.tfrac, s[col], "-o", color=c, label=lab)
        if col in ("wire_mean", "wire_le3"):
            for n, (wm, le3) in nulls.items():
                ax.axhline(wm if col == "wire_mean" else le3, color="#8a8984", ls="--" if n == 64 else ":", lw=1,
                           label="null, n=%d" % n)
        ax.set_xscale("log"); ax.set_xlabel("rewrite steps t / gates m"); ax.set_title(title, fontsize=10)
        if col == "wire_mean":
            ax.set_yscale("log"); ax.set_yticks([1, 2, 3, 5, 10, 20, 30]); ax.set_yticklabels(["1", "2", "3", "5", "10", "20", "30"])
    axes[0].legend(frameon=False, fontsize=7)
    fig.suptitle("long runs, gate set B, m = 8n (one seed)", fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, fname), dpi=150); plt.close(fig)


def plot_r3_solvers(ecsv="results/r3_B_e3.csv", fname="r3_solvers.png"):
    e = pd.read_csv(ecsv)
    e["n"] = e.instance.str.extract(r"_n(\d+)_").astype(int)
    e["t"] = e.instance.str.extract(r"_t(\d+)_").astype(int)
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    cols = {"cadical": "#2a78d6", "kissat": "#1baf7a", "abc_cec": "#8a8984", "abc_gcec": "#eb6834"}
    for tool, col in cols.items():
        for t, ls in ((0, "--"), (10, "-")):
            g = e[(e.tool == tool) & (e.t == t)].groupby("n").time.median()
            ax.plot(g.index, g.values, ls, marker="o", ms=3, color=col, label="%s, t = %s" % (tool, "0" if t == 0 else "10m"))
    ax.set_xscale("log", base=2); ax.set_yscale("log")
    ax.set_xlabel("n (wires)"); ax.set_ylabel("median time (s)")
    ax.set_title("miter solve time, knead, m = 8n", fontsize=10)
    ax.legend(frameon=False, fontsize=6, ncol=2)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, fname), dpi=150); plt.close(fig)


def plot_r3_scaling(bcsv="results/r3_B_width.csv", calib="results/r3_calibration.csv", fname="r3_scaling.png"):
    d = pd.read_csv(bcsv)
    c = pd.read_csv(calib)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    for ax, col, title in ((axes[0], "lcut_max_mean", "max width per cut (mean over 12 cuts)"),
                           (axes[1], "lcut_max_max", "worst cut (max over 12 cuts)")):
        g = d.groupby("n")[col]
        ax.scatter(d.n * np.exp(np.random.default_rng(0).normal(0, 0.03, len(d))), d[col], s=14, color="#eb6834", alpha=0.6)
        ax.plot(g.mean().index, g.mean().values, "-o", color="#eb6834", label="knead, t = 10m (each dot: one C_0 x walk)")
        a = c[c.label.str.startswith("A_n") & (c.P == 256)].groupby("n")[col].mean()
        ax.plot(a.index, a.values, "-s", color="#2a78d6", label="gauge-only (round-1 A, t = 10m)")
        nl = c[c.label.str.startswith("null") & (c.P == 256)].groupby("n")[col].mean()
        ax.plot(nl.index, nl.values, "--", color="#8a8984", label="unrelated circuit (null)")
        ax.set_xscale("log", base=2); ax.set_yscale("log", base=2)
        ax.set_xlabel("n (wires)"); ax.set_title(title, fontsize=10)
    ns = np.array(sorted(d.n.unique()), dtype=float)
    k, b0 = np.polyfit(np.log2(d.n), d.lcut_max_mean, 1)
    axes[0].plot(ns, k * np.log2(ns) + b0, ":", color="#eb6834", label="fit %.2f log2 n %+.2f" % (k, b0))
    axes[0].legend(frameon=False, fontsize=7)
    fig.suptitle("corrected correspondence width (layer cuts), gate set B, m = 8n", fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, fname), dpi=150); plt.close(fig)


def plot_r3u_width(wcsv="results/r3u_width.csv", calib="results/r3u_calibration.csv", fname="r3u_width.png"):
    d = pd.read_csv(wcsv)
    d = d[d.instance.str.contains("_t10_")]
    d["arm"] = [("i3free" if "Pi3free" in s else "w3") + (", uniform" if s.endswith("_U") else ", geometric") for s in d.instance]
    fig, ax = plt.subplots(figsize=(5.6, 3.8))
    sty = {"w3, geometric": ("#2a78d6", "--"), "w3, uniform": ("#2a78d6", "-"),
           "i3free, geometric": ("#eb6834", "--"), "i3free, uniform": ("#eb6834", "-")}
    for arm, (col, ls) in sty.items():
        h = d[d.arm == arm]
        g = h.groupby("n").lcut_max_mean.mean()
        ax.scatter(h.n * np.exp(np.random.default_rng(1).normal(0, 0.03, len(h))), h.lcut_max_mean, s=10, color=col, alpha=0.4)
        ax.plot(g.index, g.values, ls, marker="o", ms=4, color=col, label=arm + (" (to 3m)" if "i3free" in arm else ""))
    ax.set_xscale("log", base=2)
    ax.set_xlabel("n (wires)"); ax.set_ylabel("max width per cut (mean over 12 cuts)")
    ax.set_title("uniform vs geometric wiring, t = 10m, gate set B, m = 8n", fontsize=9)
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, fname), dpi=150); plt.close(fig)
