"""Round 3 / B: per-wire distribution of |D(w)| at the chosen layer cuts.
Tests whether the max over wires is the extreme value of an n-independent per-wire tail.
  JOBS=2 python r3_tail.py out.json dir1 [dir2 ...]   (t=10m instances only)"""
import sys, os, glob, json, re
import numpy as np
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))


def one(path, ncuts=12, P=256, span=0.12, min_span=3):
    sys.path.insert(0, HERE)
    import instance, width
    inst = instance.load(path)
    n = inst["params"]["n"]
    C0L, b0 = width.layered(inst["C0"]); CtL, bt = width.layered(inst["Ct"])
    L0, Lt = len(b0) - 1, len(bt) - 1
    pf = width.Prefixes(C0L, CtL, n, P, 0)
    sizes, maxes = [], []
    for q in range(1, ncuts + 1):
        lt = int(round(q * Lt / (ncuts + 1))); c = lt * L0 / Lt
        s = max(min_span, int(round(span * L0)))
        best = None
        for l0 in range(max(0, int(c) - s), min(L0, int(c) + s + 1) + 1):
            sz = pf.deps(b0[l0], bt[lt]).sum(1)
            key = (int(sz.max()), float(sz.mean()))
            if best is None or key < best[0]:
                best = (key, sz)
        sizes.extend(int(v) for v in best[1]); maxes.append(int(best[1].max()))
    return dict(instance=os.path.basename(path)[:-5], n=n, sizes=sizes, maxes=maxes)


if __name__ == "__main__":
    out, dirs = sys.argv[1], sys.argv[2:]
    paths = [p for d in dirs for p in sorted(glob.glob(os.path.join(d, "*_t10_*.json")))]
    with ProcessPoolExecutor(int(os.environ.get("JOBS", 2))) as ex:
        res = list(ex.map(one, paths))
    json.dump(res, open(out, "w"))
    for r in res:
        print(r["instance"], np.bincount(r["sizes"]).tolist(), flush=True)
