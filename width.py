"""Correspondence width (round 2), cut-based and exact up to sampling.

For a cut j of C_t (state after its first j gates) and a cut i of C_0, the map
    Phi_{i,j} = (C_t prefix j) o (C_0 prefix i)^{-1}
is a bijection of {0,1}^n. Output bit w of Phi depends on a set D_{i,j}(w) of
input bits; we find these sets by sensitivity: P random base points, each with
all n single-bit flips (a dependency of influence >= 1/8 is missed with prob.
(7/8)^64 < 2e-4).

Cut width of C_t cut j:     min over i of  mean_w |D_{i,j}(w)|     (also: max_w)
Wire width of (j, w):       min over i of  |D_{i,j}(w)|
The minimum over i is taken over C_0 prefixes near the relative position of j
(coarse grid, then refined). Prefixes in sequence order are only some of the
cuts of C_0, so the result is an upper bound on the best correspondence.

  t = 0                      -> 1
  gauge-only rewriting       -> <= 3
  unrelated circuits         -> about the light-cone size (up to n)
"""
import sys, json
import numpy as np
import model, instance


def inverse_gate(g):
    T, K, table = g
    nT = len(T)
    inv = list(table)
    for c in range(1 << len(K)):
        for x in range(1 << nT):
            inv[(c << nT) | table[(c << nT) | x]] = x
    return (T, K, tuple(inv))


class Prefixes:
    def __init__(self, C0, Ct, n, P=64, seed=0):
        self.C0, self.Ct, self.n, self.P = C0, Ct, n, P
        self.C0inv = [inverse_gate(g) for g in C0]
        rng = np.random.default_rng(seed)
        base = (rng.random((n, P)) < 0.5).astype(np.uint8)
        # pattern block k (k = 0..n): base with bit k flipped (block n: unflipped)
        blocks = [base.copy() for _ in range(n + 1)]
        for k in range(n):
            blocks[k][k] ^= 1
        self.Y = np.concatenate(blocks, axis=1)  # (n, P*(n+1))

    def deps(self, i, j):
        """dependency matrix D[w, k] for Phi_{i,j}"""
        S = self.Y.copy()
        for g in reversed(self.C0inv[:i]):
            model.apply_gate(g, S)
        for g in self.Ct[:j]:
            model.apply_gate(g, S)
        P, n = self.P, self.n
        ref = S[:, n * P:(n + 1) * P]
        D = np.zeros((n, n), dtype=bool)
        for k in range(n):
            D[:, k] = np.any(S[:, k * P:(k + 1) * P] != ref, axis=1)
        return D


def cut_width(pf, j, m0, mt, span=0.12, coarse=8):
    """best C_0 prefix for C_t cut j; returns (mean |D|, max |D|, per-wire min |D|, best i)"""
    c = int(round(j * m0 / mt))
    lo, hi = max(0, c - int(span * m0)), min(m0, c + int(span * m0))
    cache = {}

    def ev(i):
        if i not in cache:
            D = pf.deps(i, j)
            cache[i] = D.sum(1)
        return cache[i]

    grid = list(range(lo, hi + 1, coarse))
    best = min(grid, key=lambda i: ev(i).mean())
    for i in range(max(lo, best - coarse), min(hi, best + coarse) + 1):
        ev(i)
    best = min(cache, key=lambda i: cache[i].mean())
    per_wire = np.min(np.stack(list(cache.values())), axis=0)
    return float(cache[best].mean()), int(cache[best].max()), per_wire, best


def width_profile(C0, Ct, n, ncuts=12, P=64, seed=0):
    pf = Prefixes(C0, Ct, n, P, seed)
    m0, mt = len(C0), len(Ct)
    rows = []
    for q in range(1, ncuts + 1):
        j = int(round(q * mt / (ncuts + 1)))
        mean, mx, pw, i = cut_width(pf, j, m0, mt)
        rows.append(dict(j=j, i=i, cut_mean=mean, cut_max=mx, wire_mean=float(pw.mean()),
                         wire_max=int(pw.max()), wire_le3=float((pw <= 3).mean())))
    return rows


def summary(rows):
    keys = ["cut_mean", "cut_max", "wire_mean", "wire_max", "wire_le3"]
    return {k: float(np.mean([r[k] for r in rows])) for k in keys} | {"cut_max_max": max(r["cut_max"] for r in rows)}


if __name__ == "__main__":
    for path in sys.argv[1:]:
        inst = instance.load(path)
        rows = width_profile(inst["C0"], inst["Ct"], inst["params"]["n"])
        print(path, json.dumps(summary(rows)))
