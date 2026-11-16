"""Text summaries of solver results (E3/E4) for the report.
  python summarize.py results/e3_n64.csv [more.csv ...]"""
import sys
import numpy as np
import pandas as pd
from plots import parse_name


def load(files):
    d = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    meta = pd.DataFrame([parse_name(x) for x in d.instance])
    return pd.concat([d, meta], axis=1)


def table(d):
    d = d.copy()
    d["solved"] = d.status == "UNSAT"
    rows = []
    for (g, n, b, tool, tf), s in d.groupby(["gset", "n", d.beta.fillna(0), "tool", "tfrac"]):
        rows.append(dict(gset=g, n=n, beta=b or "", tool=tool, tfrac=tf, runs=len(s),
                         solved=int(s.solved.sum()),
                         median=float(np.median(np.where(s.solved, s.time, np.inf))),
                         max=float(np.max(np.where(s.solved, s.time, np.inf)))))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    d = load(sys.argv[1:])
    t = table(d)
    piv = t.assign(cell=lambda x: x.apply(lambda r: "%.1f" % r["median"] if r.solved == r.runs
                                          else "%.1f (%d/%d)" % (r["median"], r.solved, r.runs), axis=1))
    print(piv.pivot_table(index=["gset", "n", "beta", "tool"], columns="tfrac", values="cell", aggfunc="first").to_string())
    sat = d[d.status == "SAT"]
    print("\nSAT answers (should be none):", len(sat))
    print("UNKNOWN/ERR:", int((~d.status.isin(["UNSAT", "TIMEOUT", "SAT"])).sum()))
