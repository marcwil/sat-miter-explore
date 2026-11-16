"""Markdown tables for REPORT.md, generated from the result CSVs."""
import os, sys
import numpy as np
import pandas as pd
from plots import parse_name

TF = [0.0, 0.1, 0.3, 1.0, 3.0, 10.0]


def load(files):
    d = pd.concat([pd.read_csv(f) for f in files if os.path.exists(f)], ignore_index=True)
    m = pd.DataFrame([parse_name(x) for x in d.instance])
    return pd.concat([d, m], axis=1)


def fmt(s):
    sol = s.status == "UNSAT"
    med = np.median(np.where(sol, s.time, np.inf))
    txt = "%.1f" % med if np.isfinite(med) else ">%g" % s.timeout.iloc[0]
    if sol.sum() < len(s):
        txt += " (%d/%d)" % (sol.sum(), len(s))
    return txt


def e3_table(files, tools, betas=(None, 2.5)):
    d = load(files)
    d = d[d.tool.isin(tools)]
    d = d[d.beta.isna() | d.beta.isin([b for b in betas if b])]
    out = ["| gate set | n | tool | " + " | ".join("t/m=%g" % t for t in TF) + " |",
           "|---|---|---|" + "---|" * len(TF)]
    for (g, n), s in d.groupby(["gset", "n"]):
        for tool in tools:
            st = s[s.tool == tool]
            if st.empty:
                continue
            cells = [fmt(st[st.tfrac == t]) if (st.tfrac == t).any() else "–" for t in TF]
            out.append("| %s | %d | %s | %s |" % (g, n, tool, " | ".join(cells)))
    return "\n".join(out)


def beta_table(files, tools, tfs=(0.0, 1.0, 3.0)):
    d = load(files)
    d = d[d.tool.isin(tools) & d.gset.isin(["Aw", "Bw"])]
    out = ["| gate set | beta | tool | " + " | ".join("t/m=%g" % t for t in tfs) + " |", "|---|---|---|" + "---|" * len(tfs)]
    for (g, b), s in d.groupby(["gset", "beta"]):
        for tool in tools:
            st = s[s.tool == tool]
            cells = [fmt(st[st.tfrac == t]) if (st.tfrac == t).any() else "–" for t in tfs]
            out.append("| %s | %g | %s | %s |" % (g, b, tool, " | ".join(cells)))
    return "\n".join(out)


def best_tool(files):
    d = load(files)
    d = d[d.status == "UNSAT"]
    b = d.groupby(["instance"]).time.min()
    return b


def e4_table(files):
    s = pd.concat([pd.read_csv(f) for f in files if os.path.exists(f)], ignore_index=True)
    m = pd.DataFrame([parse_name(x) for x in s.instance])
    s = pd.concat([s, m], axis=1)
    s["rel"] = s.verified / s.groups_t
    out = ["| gate set | n | " + " | ".join("t/m=%g" % t for t in TF) + " |", "|---|---|" + "---|" * len(TF)]
    for (g, n), x in s[s.beta.isna() | (s.beta == 2.5)].groupby(["gset", "n"]):
        cells = []
        for t in TF:
            y = x[x.tfrac == t]
            if y.empty:
                cells.append("–"); continue
            ok = (y.status == "UNSAT").all()
            cells.append("%.1f s / %.0f%%%s" % (y.t_total.median(), 100 * y.rel.median(), "" if ok else " FAIL"))
        out.append("| %s | %d | %s |" % (g, n, " | ".join(cells)))
    return "\n".join(out)


if __name__ == "__main__":
    tools = ["cadical", "kissat", "abc_cec", "abc_gcec"]
    print("## E3 n=64\n")
    print(e3_table(["results/e3_n64.csv"], tools))
    print("\n## E3 big\n")
    print(e3_table(["results/e3_big.csv"], tools))
    print("\n## E3 nocc n=64 (seed 0, 120 s)\n")
    print(e3_table(["results/e3_n64_nocc.csv"], ["cadical_nocc", "kissat_nocc"]))
    print("\n## E3 weighted beta\n")
    print(beta_table(["results/e3_n64.csv"], ["cadical", "kissat", "abc_cec"]))
    b = best_tool(["results/e3_n64.csv", "results/e3_big.csv"])
    print("\nbest-tool max: %.1f s over %d instances" % (b.max(), len(b)))
    print("\n## E4\n")
    print(e4_table(["results/e4_sweep_n64.csv", "results/e4_sweep_big.csv"]))
    if os.path.exists("results/e3_n64_clean.csv"):
        print("\n## clean re-timing n=64\n")
        print(e3_table(["results/e3_n64_clean.csv"], tools))
    if os.path.exists("results/e5_backdoor.csv"):
        print("\n## backdoor\n")
        b = pd.read_csv("results/e5_backdoor.csv")
        print("| instance | k | cubes | solved | total [s] | max cube [s] | total / unsplit |")
        print("|---|---|---|---|---|---|---|")
        for nm, x in b.groupby("instance", sort=False):
            base = x[x.k == 0].total.iloc[0]
            for _, r in x.iterrows():
                print("| %s | %d | %d | %d | %.1f | %.1f | %.1f |" % (nm, r.k, r.cubes, r.solved, r.total, r["max"], r.total / base))
