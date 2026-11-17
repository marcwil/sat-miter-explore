"""Uniform-wiring side study: summary tables from results/r3u_*.csv (printed as markdown)."""
import re
import numpy as np
import pandas as pd


def arm(nm):
    mode = "i3free" if "Pi3free" in nm else "w3"
    return "%s, %s" % (mode, "uniform" if nm.endswith("_U") else "geometric")


def key(df, col="instance"):
    df["n"] = df[col].str.extract(r"_n(\d+)_").astype(int)
    df["t"] = df[col].str.extract(r"_t(\d+)_").astype(int)
    df["arm"] = df[col].map(arm)
    return df


def md(df):
    cols = list(df.columns)
    print("| " + " | ".join(map(str, cols)) + " |")
    print("|" + "---|" * len(cols))
    for _, r in df.iterrows():
        print("| " + " | ".join(("%.2f" % v if isinstance(v, float) else str(v)) for v in r.values) + " |")
    print()


if __name__ == "__main__":
    w = key(pd.read_csv("results/r3u_width.csv"))
    g = w.groupby(["arm", "t", "n"]).agg(inst=("instance", "count"), m_t=("m_t", "mean"),
                                         width=("lcut_max_mean", "mean"), sd=("lcut_max_mean", "std"),
                                         worst=("lcut_max_max", "max"), wire_mean=("lcut_mean", "mean"),
                                         survival=("gate_frac", "mean")).reset_index()
    md(g)
    for (a, t), h in w[w.t == 10].groupby(["arm", "t"]):
        k, b = np.polyfit(np.log2(h.n), h.lcut_max_mean, 1)
        kp, _ = np.polyfit(np.log2(h.n), np.log2(h.lcut_max_mean), 1)
        print("%s t=10m: width fit %.2f log2 n %+.2f, power exponent %.2f" % (a, k, b, kp))
    print()
    try:
        nf = key(pd.read_csv("results/r3u_nonflat.csv"))
        md(nf.groupby(["arm", "n"]).agg(flat=("flat_max", "mean"), varying=("best_max", "mean"),
                                         perwire=("perwire_min_max", "mean"), spread=("tau_spread", "mean")).reset_index())
    except FileNotFoundError:
        pass
    e = key(pd.read_csv("results/r3u_e3.csv"))
    print("statuses", e.status.value_counts().to_dict())
    p = e.pivot_table(index=["instance", "arm", "n", "t"], columns="tool", values="time", aggfunc="first").reset_index()
    p["best"] = p[["cadical", "kissat", "abc_cec", "abc_gcec"]].min(axis=1)
    # t = 0 instances belong to the w3 runs; share them with the i3free arm of the same wiring
    t0 = p[p.t == 0].copy()
    extra = t0.copy(); extra["arm"] = extra.arm.str.replace("w3", "i3free")
    p = pd.concat([p[p.t > 0], t0, extra])
    s = key(pd.read_csv("results/r3u_sweep.csv"))
    s["verified_frac"] = s.verified / s.groups_t
    s0 = s[s.t == 0].copy(); ex = s0.copy(); ex["arm"] = ex.arm.str.replace("w3", "i3free")
    s = pd.concat([s[s.t > 0], s0, ex])
    q = p.groupby(["arm", "n", "t"])[["cadical", "kissat", "abc_cec", "abc_gcec", "best"]].median()
    q = q.join(s.groupby(["arm", "n", "t"])[["t_total", "verified_frac"]].median()).reset_index()
    md(q)
