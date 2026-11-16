"""E2 (+ E5 conditional part): survival statistics for every instance in a directory.

Unconditional: stats.instance_stats (eq_frac, rel_frac, gate_frac).
Conditional (weighted gate sets): pick the k C_0 signals read most often as a gate
control (k = 1, 2); for each of the 2^k value combinations restrict the simulated
patterns to those where the controls take these values and recompute eq_frac on
that subset; report the mean over combinations. As a fair baseline the same number
of patterns is used unconditionally (cond_base).
"""
import sys, os, csv, glob, json, collections
import numpy as np
import model, instance, stats


def control_signals(circ, n, X):
    """C_0 signals ordered by how many gates read them as control. Returns list of
    (fanout, vector)."""
    S = X.copy()
    cur = {w: ("in", w) for w in range(n)}
    vec = {("in", w): X[w].copy() for w in range(n)}
    fan = collections.Counter()
    for gi, g in enumerate(circ):
        for w in g[1]:
            fan[cur[w]] += 1
        model.apply_gate(g, S)
        for w in g[0]:
            cur[w] = (gi, w)
            vec[cur[w]] = S[w].copy()
    return [(f, vec[s]) for s, f in fan.most_common()]


def eq_frac_on(s0, st, mask):
    tset = {stats.canon_bits(v[mask]) for v in st}
    return sum(stats.canon_bits(v[mask]) in tset for v in s0) / max(1, len(s0))


def cond_stats(inst, P=4096, seed=0):
    n = inst["params"]["n"]
    rng = np.random.default_rng(seed)
    X = (rng.random((n, P)) < 0.5).astype(np.uint8)
    s0, _ = stats.trace(inst["C0"], n, X)
    st, _ = stats.trace(inst["Ct"], n, X)
    ctrl = control_signals(inst["C0"], n, X)
    out = {}
    for k in (1, 2):
        if len(ctrl) < k:
            continue
        vals = []
        sizes = []
        for comb in range(1 << k):
            mask = np.ones(P, dtype=bool)
            for j in range(k):
                mask &= ctrl[j][1] == ((comb >> j) & 1)
            sizes.append(mask.sum())
            vals.append(eq_frac_on(s0, st, mask))
        base_mask = np.zeros(P, dtype=bool); base_mask[:min(sizes)] = True
        out["cond%d_eq" % k] = float(np.mean(vals))
        out["cond%d_base" % k] = eq_frac_on(s0, st, base_mask)
        out["cond%d_fanout" % k] = int(sum(c[0] for c in ctrl[:k]))
    return out


if __name__ == "__main__":
    d, outcsv = sys.argv[1], sys.argv[2]
    rows = []
    for path in sorted(glob.glob(os.path.join(d, "*.json"))):
        inst = instance.load(path)
        p = inst["params"]
        r = dict(instance=os.path.basename(path)[:-5], gset=p["gset"], n=p["n"], m=p["m"], t=p["t_done"],
                 tfrac=p["tfrac"], seed=p["seed"], beta=p.get("beta"))
        r.update(stats.instance_stats(inst))
        if p["gset"] in ("Aw", "Bw"):
            r.update(cond_stats(inst))
        rows.append(r)
        print(json.dumps(r), flush=True)
    keys = sorted({k for r in rows for k in r}, key=lambda k: list(rows[0]).index(k) if k in rows[0] else 99)
    with open(outcsv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader(); w.writerows(rows)
