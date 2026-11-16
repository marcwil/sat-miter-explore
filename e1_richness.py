"""E1: how many function-preserving replacements does a random window admit?

Gate sets A, Aw (w = 2): exact enumeration of all 2-gate shapes on the window's
wires (model.equivalent_2gate); per window we record whether a shape other than
the original one is feasible (= the rewrite can change the skeleton) and the size
of the gauge orbit of the original shape.

Gate sets B, Bw (w = 2, 3): exhaustive meet-in-the-middle over the gate set on the
window's wires. Alternatives are classified as
  'perm'     : same multiset of gates, different order
  'sameskel' : same sequence of (target, controls) supports, different phi
  'newskel'  : different sequence of supports
"""
import sys, json, math, time, collections
import numpy as np
import model

OUT = "results/e1_richness.json"


def windows_from(geo, gset, m, w, nwin, rng):
    C = model.random_circuit(geo, gset, m, rng)
    out = []
    while len(out) < nwin:
        W = model.pick_window(C, w, rng)
        if W is not None:
            out.append([C[k] for k in W])
    return out


def analyse_A(geo, gset, wins):
    recs = []
    for orig in wins:
        Sw = model.window_wires(orig)
        F = model.window_function(orig, Sw)
        decs = model.equivalent_2gate(F, Sw, geo, gset)
        pos = {x: i for i, x in enumerate(Sw)}
        oshape = tuple((tuple(pos[x] for x in g[0]), tuple(pos[x] for x in g[1])) for g in orig)
        shapes = [((d["T1"], d["K1"]), (d["T2"], d["K2"])) for d in decs]
        orig_dec = [d for d, sh in zip(decs, shapes) if sh == oshape]
        assert orig_dec, "original shape not found"
        od = orig_dec[0]
        others = [(sh, d["logcount"]) for d, sh in zip(decs, shapes) if sh != oshape]
        ov = len(set(orig[0][0]) & set(orig[1][0]))  # shared target wires
        recs.append(dict(s=len(Sw), shared_targets=ov,
                         shared_any=len(model.gate_wires(orig[0]) & model.gate_wires(orig[1])),
                         gauge_log=od["logcount"], gauge_contexts=len(od["contexts"]),
                         gauge_msize=od["msize"], n_other_shapes=len(others),
                         other_shapes=[[list(map(list, a)) for a in sh] for sh, _ in others][:5]))
    return recs


def classify_xor(orig, alt):
    if sorted(alt) == sorted(orig):
        return "perm"
    if [(g[0], g[1]) for g in alt] == [(g[0], g[1]) for g in orig]:
        return "sameskel"
    return "newskel"


equivalent_xor_fast = model.equivalent_xor_fast


def _unused_equivalent_xor_fast(F, Sw, geo, gset, w):
    """Same as model.equivalent_xor but vectorised with 64-bit row hashes (verified exactly)."""
    gates = model.xor_gates_on(geo, gset, Sw)
    P = model.gate_perms(gates, Sw).astype(np.int64)
    k, N = P.shape
    Pinv = np.empty_like(P)
    Pinv[np.arange(k)[:, None], P] = np.arange(N)[None, :]
    R = np.random.default_rng(7).integers(1, 2**62, size=N, dtype=np.int64).astype(np.uint64)
    hP = (P.astype(np.uint64) * R).sum(1)
    order = np.argsort(hP); hs = hP[order]
    def lookup(rows):
        h = (rows.astype(np.uint64) * R).sum(1)
        idx = np.searchsorted(hs, h)
        idx[idx >= len(hs)] = 0
        hit = hs[idx] == h
        return hit, order[idx]
    sols = []
    G = F[Pinv]  # row i1: F o g1^-1
    if w == 2:
        hit, j = lookup(G)
        for i1 in np.nonzero(hit)[0]:
            if np.array_equal(P[j[i1]], G[i1]):
                sols.append((gates[i1], gates[j[i1]]))
    else:
        for i3 in range(k):
            H = Pinv[i3][G]
            hit, j = lookup(H)
            for i1 in np.nonzero(hit)[0]:
                if np.array_equal(P[j[i1]], H[i1]):
                    sols.append((gates[i1], gates[j[i1]], gates[i3]))
    return sols


def analyse_xor(geo, gset, wins, w):
    recs = []
    for orig in wins:
        Sw = model.window_wires(orig)
        F = model.window_function(orig, Sw)
        sols = equivalent_xor_fast(F, Sw, geo, gset, w)
        assert any(list(s) == orig for s in sols), "original not found"
        cnt = collections.Counter(classify_xor(orig, list(s)) for s in sols if list(s) != orig)
        recs.append(dict(s=len(Sw), n_alt=sum(cnt.values()), **{k: cnt.get(k, 0) for k in ("perm", "sameskel", "newskel")}))
    return recs


def summarize(recs, keys):
    n = len(recs)
    out = dict(windows=n)
    for k in keys:
        vals = np.array([r[k] for r in recs], dtype=float)
        out[k + "_frac_pos"] = float((vals > 0).mean())
        out[k + "_mean"] = float(vals.mean())
    return out


if __name__ == "__main__":
    nwin = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    nwin3 = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    res = {}
    for gset in ["A", "Aw", "B", "Bw"]:
        beta = 2.5 if gset.endswith("w") else None
        for w in ([2] if gset in ("A", "Aw") else [2, 3]):
            rng = np.random.default_rng(11)
            recs = []
            nw = nwin if w == 2 else nwin3
            t0 = time.time()
            for rep in range(nw // 50):
                geo = model.Geometry(64, 2, 8.0, seed=500 + rep, beta=beta)
                wins = windows_from(geo, gset, 512, w, 50, rng)
                recs += analyse_A(geo, gset, wins) if gset in ("A", "Aw") else analyse_xor(geo, gset, wins, w)
            key = "%s_w%d" % (gset, w)
            if gset in ("A", "Aw"):
                summ = summarize(recs, ["n_other_shapes"])
                summ["gauge_log_mean"] = float(np.mean([r["gauge_log"] for r in recs]))
                summ["frac_no_alternative"] = float(np.mean([r["gauge_log"] < 1e-9 and r["n_other_shapes"] == 0 for r in recs]))
                summ["frac_controlled_gauge"] = float(np.mean([r["gauge_contexts"] > 1 for r in recs]))
                summ["shared_targets_hist"] = dict(collections.Counter(r["shared_targets"] for r in recs))
                summ["examples_other"] = [r for r in recs if r["n_other_shapes"] > 0][:5]
            else:
                summ = summarize(recs, ["n_alt", "perm", "sameskel", "newskel"])
                summ["n_alt_hist"] = dict(collections.Counter(min(r["n_alt"], 20) for r in recs))
            summ["seconds"] = time.time() - t0
            res[key] = summ
            print(key, json.dumps({k: v for k, v in summ.items() if k != "examples_other"}), flush=True)
    json.dump(res, open(OUT, "w"), indent=1)
