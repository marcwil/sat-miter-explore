"""Round 3 / B follow-up: are the wide wires at a flat layer cut a misalignment effect?

A refutation may use any downward-closed set S of C_0 gates (an "ideal") as the
C_0 side of a cut, not only a flat ASAP layer. For each sampled C_t layer cut we
compare the best flat C_0 cut with spatially varying ideals built from per-wire
preferred layers tau(w) (the flat layer that minimises |D(w)| for that wire):
  (a) g in S iff layer(g) <= tau(target of g), then closed downward;
  (b) same with tau smoothed by the median over the wire's gate-neighbours;
  (c) g in S iff layer(g) <= min over g's wires of tau, then closed downward.
Reports, per cut, max_w |D(w)| for the flat cut and for the best ideal.
  JOBS=4 python r3_nonflat.py out.csv dir1 [dir2 ...]   (t=10m instances)"""
import sys, os, glob, csv, json
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))


def closure(C, lay, sel):
    """smallest ideal containing sel: add every earlier non-commuting gate on a shared wire"""
    sys.path.insert(0, HERE)
    import model
    on = {}
    for i, g in enumerate(C):
        for w in list(g[0]) + list(g[1]):
            on.setdefault(w, []).append(i)
    S = set(sel)
    stack = list(S)
    while stack:
        i = stack.pop()
        g = C[i]
        for w in list(g[0]) + list(g[1]):
            for h in on[w]:
                if h >= i:
                    break
                if h not in S and not model.commute(C[h], g):
                    S.add(h); stack.append(h)
    return sorted(S)


def deps_set(pf, S, j):
    S_ = pf.Y.copy()
    import model
    for i in reversed(S):
        model.apply_gate(pf.C0inv[i], S_)
    for g in pf.Ct[:j]:
        model.apply_gate(g, S_)
    P, n = pf.P, pf.n
    ref = S_[:, n * P:(n + 1) * P]
    D = np.zeros((n, n), dtype=bool)
    for k in range(n):
        D[:, k] = np.any(S_[:, k * P:(k + 1) * P] != ref, axis=1)
    return D.sum(1)


def one(path, ncuts=12, P=256, span=0.12, min_span=3):
    sys.path.insert(0, HERE)
    import instance, width
    inst = instance.load(path)
    n = inst["params"]["n"]
    C0L, b0 = width.layered(inst["C0"]); CtL, bt = width.layered(inst["Ct"])
    lay = width.asap_layers(C0L)  # layered order is a linear extension, layers unchanged
    L0, Lt = len(b0) - 1, len(bt) - 1
    pf = width.Prefixes(C0L, CtL, n, P, 0)
    nb = {w: {w} for w in range(n)}  # include w itself (some wires carry no gate)
    for g in C0L:
        ws = list(g[0]) + list(g[1])
        for a in ws:
            nb[a].update(ws)
    out = []
    for q in range(1, ncuts + 1):
        lt = int(round(q * Lt / (ncuts + 1))); c = lt * L0 / Lt
        s = max(min_span, int(round(span * L0)))
        cand = list(range(max(0, int(c) - s), min(L0, int(c) + s + 1) + 1))
        res = {l0: pf.deps(b0[l0], bt[lt]).sum(1) for l0 in cand}
        flat = min(cand, key=lambda l0: (int(res[l0].max()), float(res[l0].mean())))
        R = np.stack([res[l0] for l0 in cand])  # (len(cand), n)
        # per-wire preferred layer: minimise |D(w)|, ties broken towards the flat optimum
        tau = np.array([cand[min(range(len(cand)), key=lambda a: (R[a, w], abs(cand[a] - flat)))] for w in range(n)])
        taus = np.array([int(np.median([tau[v] for v in nb[w]])) for w in range(n)])
        variants = {}
        sels = {
            "a": [i for i, g in enumerate(C0L) if lay[i] <= tau[g[0][0]]],
            "b": [i for i, g in enumerate(C0L) if lay[i] <= taus[g[0][0]]],
            "c": [i for i, g in enumerate(C0L) if lay[i] <= min(tau[w] for w in list(g[0]) + list(g[1]))],
        }
        best = ("flat", res[flat])
        for name, sel in sels.items():
            S = closure(C0L, lay, sel)
            sz = deps_set(pf, S, bt[lt])
            variants[name] = int(sz.max())
            if (int(sz.max()), float(sz.mean())) < (int(best[1].max()), float(best[1].mean())):
                best = (name, sz)
        out.append(dict(lt=lt, flat_max=int(res[flat].max()), flat_mean=float(res[flat].mean()),
                        perwire_min_max=int(R.min(0).max()), perwire_min_mean=float(R.min(0).mean()),
                        a_max=variants["a"], b_max=variants["b"], c_max=variants["c"],
                        best=best[0], best_max=int(best[1].max()), best_mean=float(best[1].mean()),
                        tau_spread=int(tau.max() - tau.min())))
    nm = os.path.basename(path)[:-5]
    return [dict(instance=nm, n=n, **r) for r in out]


if __name__ == "__main__":
    out, dirs = sys.argv[1], sys.argv[2:]
    filt = os.environ.get("FILTER")  # optional regex on instance names
    paths = [p for d in dirs for p in sorted(glob.glob(os.path.join(d, "*_t10_*.json")))
             if not filt or __import__("re").search(filt, os.path.basename(p))]
    with open(out, "w", newline="") as fh, ProcessPoolExecutor(int(os.environ.get("JOBS", 4))) as ex:
        w = None
        for f in as_completed([ex.submit(one, p) for p in paths]):
            rows = f.result()
            if w is None:
                w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader()
            w.writerows(rows); fh.flush()
            r0 = rows[0]
            print(r0["instance"], "flat", np.mean([r["flat_max"] for r in rows]).round(2),
                  "best ideal", np.mean([r["best_max"] for r in rows]).round(2),
                  "per-wire-min max", np.mean([r["perwire_min_max"] for r in rows]).round(2), flush=True)
