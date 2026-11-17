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


# ---------------------------------------------------------------- round 3: layer cuts
def asap_layers(circ):
    """ASAP layer of every gate w.r.t. the commutation rule of model.commute:
    a gate must come after earlier gates that write one of its controls, read
    one of its targets, or write one of its targets (unless both are
    single-target XOR gates, which commute). Returns a list of layers (>= 1)."""
    lw, lwn, lr = {}, {}, {}
    out = []
    for g in circ:
        T, K = g[0], g[1]
        x = model.is_xor_gate(g)
        L = 0
        for k in K:
            L = max(L, lw.get(k, 0))
        for a in T:
            L = max(L, lr.get(a, 0), lwn.get(a, 0) if x else lw.get(a, 0))
        L += 1
        for k in K:
            lr[k] = max(lr.get(k, 0), L)
        for a in T:
            lw[a] = max(lw.get(a, 0), L)
            if not x:
                lwn[a] = max(lwn.get(a, 0), L)
        out.append(L)
    return out


def layered(circ):
    """Reorder by (layer, index) -- a linear extension of the dependency order,
    hence the same function. Returns (circuit, prefix length after each layer)."""
    lay = asap_layers(circ)
    order = sorted(range(len(circ)), key=lambda i: (lay[i], i))
    L = max(lay) if lay else 0
    counts = np.bincount(lay, minlength=L + 1)
    bounds = np.cumsum(counts)  # bounds[l] = number of gates with layer <= l
    return [circ[i] for i in order], [int(b) for b in bounds]


def width_layers(C0, Ct, n, ncuts=12, P=256, seed=0, span=0.12, min_span=3):
    """Correspondence width with ASAP-layer cuts.
    For each sampled C_t layer cut lt, search C_0 layer cuts l0 near the relative
    position and take the one minimising max_w |D(w)| (ties: mean). Reports the
    max over wires at the best l0 ('cut_max'), the mean over wires there, and the
    per-wire minimum over the searched l0 (secondary)."""
    C0L, b0 = layered(C0)
    CtL, bt = layered(Ct)
    L0, Lt = len(b0) - 1, len(bt) - 1
    pf = Prefixes(C0L, CtL, n, P, seed)
    rows = []
    for q in range(1, ncuts + 1):
        lt = int(round(q * Lt / (ncuts + 1)))
        c = lt * L0 / Lt
        s = max(min_span, int(round(span * L0)))
        cand = range(max(0, int(c) - s), min(L0, int(c) + s + 1) + 1)
        best, res = None, {}
        for l0 in cand:
            sz = pf.deps(b0[l0], bt[lt]).sum(1)
            res[l0] = sz
            key = (int(sz.max()), float(sz.mean()))
            if best is None or key < best[0]:
                best = (key, l0)
        l0 = best[1]
        pw = np.min(np.stack(list(res.values())), axis=0)
        rows.append(dict(lt=lt, l0=l0, Lt=Lt, L0=L0, cut_max=int(res[l0].max()), cut_mean=float(res[l0].mean()),
                         wire_mean=float(pw.mean()), wire_max=int(pw.max())))
    return rows


def summary_layers(rows):
    cm = [r["cut_max"] for r in rows]
    return dict(lcut_max_mean=float(np.mean(cm)), lcut_max_max=int(np.max(cm)),
                lcut_max_median=float(np.median(cm)),
                lcut_mean=float(np.mean([r["cut_mean"] for r in rows])),
                lwire_mean=float(np.mean([r["wire_mean"] for r in rows])),
                L0=rows[0]["L0"], Lt=rows[0]["Lt"])


if __name__ == "__main__":
    for path in sys.argv[1:]:
        inst = instance.load(path)
        rows = width_profile(inst["C0"], inst["Ct"], inst["params"]["n"])
        print(path, json.dumps(summary(rows)))
